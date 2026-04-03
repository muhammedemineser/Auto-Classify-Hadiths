from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import difflib
from google import genai
from google.genai import types

from Tafsir.config import paths as cfg
from Tafsir.pipeline.gemini_common import (
    ALL_COLUMNS,
    NORMALIZED_COL,
    _normalize_guard_tokens,
    _normalize_to_string,
    evaluate_guard,
    extract_block_chunks,
    extract_nested_data,
    extract_section_blocks,
    clean_wrapped_xml,
)
from Tafsir.pipeline.analysis import check_divergent_rows
from Tafsir.pipeline.analysis.compare_tafsir_texts import (
    get_anomalies as compare_anomalies,
)
from Tafsir.pipeline.analysis.data_cleaning import (
    duplicated,
)

REQUIRED_ENV_KEYS = ["GEMINI_API_KEY_ROLLBACK", "GEMINI_API_KEY_ROLLBACK_CACHE"]
# Human-readable guidance kept for client-cache; prompts themselves send only category keys.
PROMPT_GUIDANCE = {
    "minor": (
        "Task: align annotated XML to exactly match the source text; keep tags, no paraphrasing, "
        "only minimal edits to synchronize text and tags."
    ),
    "medium": (
        "Task: differences are moderate; analyse causes, then regenerate faithful XML. "
        "Preserve meaning, avoid hallucinations, prioritize source wording."
    ),
    "divergent": (
        "Task: large divergence; regenerate full XML from source text with correct tags, "
        "no extra content."
    ),
}


def _load_env_strict() -> bool:
    """
    Load .env from repo root.
    Fails fast when
    - python-dotenv is missing,
    - the .env file is missing/unreadable,
    - required keys are absent after loading.
    """
    try:
        from dotenv import load_dotenv
    except ImportError as exc:  # noqa: B904
        raise RuntimeError(
            "python-dotenv ist nicht installiert. Bitte `pip install python-dotenv` im aktiven venv ausführen."
        ) from exc

    # rollback_pipeline.py sits under: classify/Tafsir/pipeline/analysis/data_cleaning
    # Repo-Root (classify) is parents[4]
    env_path = Path(__file__).resolve().parents[4] / ".env"
    if not env_path.exists():
        raise RuntimeError(f".env nicht gefunden unter {env_path}")

    loaded = load_dotenv(env_path)
    if not loaded:
        raise RuntimeError(f".env konnte nicht geladen werden ({env_path})")

    missing = [k for k in REQUIRED_ENV_KEYS if not os.getenv(k)]
    if missing:
        raise RuntimeError(
            f".env geladen, aber folgende Schlüssel fehlen: {', '.join(missing)}"
        )
    return True


_ENV_LOADED = _load_env_strict()


@dataclass(frozen=True)
class GeminiSession:
    client: genai.Client
    config: types.GenerateContentConfig
    model: str = "models/gemini-2.5-pro"

    def generate(self, prompt: str) -> Optional[str]:
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                cached_content=self.config.cached_content
            ),
        )
        return resp.text if resp and getattr(resp, "text", None) else None


def _sqlite_connect(path: Path, *, pragmas: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    if pragmas:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def _chunked(iterable: Iterable[Any], n: int) -> Iterable[List[Any]]:
    buf: List[Any] = []
    for x in iterable:
        buf.append(x)
        if len(buf) >= n:
            yield buf
            buf = []
    if buf:
        yield buf


class TafsirRollbackPipeline:
    def __init__(
        self, book: str = cfg.DEFAULT_TAFSIR, base_path: Path | str = cfg.PROJECT_ROOT
    ):
        self.regen_ids: Set[int] = set()
        self.medium_ids: Set[int] = set()
        self.divergent_ids: Set[int] = set()
        self.missing_ids: Set[int] = set()
        self.unknown_ids: Set[int] = set()
        self.minor_deltas: List[Dict[str, Any]] = []
        self.priorities: Dict[int, int] = {}
        self.book = book
        self.base_path = Path(base_path)
        self._gemini: Optional[GeminiSession] = None
        self.log_path = Path(cfg.LOGS_DIR) / "rollback_pipeline.log"
        self.jsonl_path: Optional[Path] = None
        self._jsonl_queue: List[Tuple[int, str]] = []

    def _log(self, event: str, **data: Any) -> None:
        entry = {"event": event, "book": self.book, "ts": time.time()}
        entry.update(data)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"LOG ENTRY: {event} {data}")
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def load_from_jsonl(self, path: Path):
        """
        Resume processing from an existing fine_diff JSONL.
        Only categories present in the file are loaded; typical fields: id, category.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"JSONL not found: {p}")
        count = 0
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                rid = rec.get("id")
                cat = (rec.get("category") or "").lower()
                if rid is None or not cat:
                    continue
                rid = int(rid)
                if cat in {"minimal", "minor"}:
                    self.minor_deltas.append({"id": rid, "category": cat})
                elif cat == "medium":
                    self.medium_ids.add(rid)
                elif cat == "divergent":
                    self.divergent_ids.add(rid)
                count += 1
                self._jsonl_queue.append((rid, line))
        self.jsonl_path = p
        print(f"-> loaded {count} records from JSONL {p}")
        self._log("loaded_jsonl", path=str(p), records=count)

    def _flush_jsonl_queue(self) -> None:
        if not self.jsonl_path:
            return
        with self.jsonl_path.open("w", encoding="utf-8") as f:
            for _, line in self._jsonl_queue:
                f.write(line.rstrip("\n") + "\n")

    def _remove_processed_jsonl_entry(self, rid: int) -> None:
        if not self._jsonl_queue or self.jsonl_path is None:
            return
        remaining = [(i, line) for i, line in self._jsonl_queue if i != rid]
        if len(remaining) == len(self._jsonl_queue):
            return
        self._jsonl_queue = remaining
        self._flush_jsonl_queue()

    def _get_gemini(self) -> GeminiSession:
        if self._gemini is not None:
            return self._gemini
        api_key = os.getenv("GEMINI_API_KEY_ROLLBACK")
        cache_name = os.getenv("GEMINI_API_KEY_ROLLBACK_CACHE")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY_ROLLBACK fehlt.")
        if not cache_name:
            raise RuntimeError("GEMINI_API_KEY_ROLLBACK_CACHE fehlt.")
        self._gemini = GeminiSession(
            client=genai.Client(api_key=api_key),
            config=types.GenerateContentConfig(cached_content=cache_name),
        )
        return self._gemini

    def log_anomaly(self, row_id, priority: int = 3):
        if row_id is not None:
            rid = int(row_id)
            self.regen_ids.add(rid)
            current = self.priorities.get(rid, priority)
            self.priorities[rid] = min(current, priority)

    def log_unknown(self, row_id):
        if row_id is not None:
            self.unknown_ids.add(int(row_id))

    def _src_db_path(self) -> Path:
        return self.base_path / "tafsir_books" / f"{self.book}.sqlite3"

    def _ann_db_path(self) -> Path:
        return (
            self.base_path / "tafsir_books_annotated" / f"{self.book}_annotated.sqlite3"
        )

    def _ann_table(self) -> str:
        return f"tafsir_analysis_{self.book}"

    def run_script(self, script_path, args=None):
        cmd = [sys.executable, script_path]
        if args:
            cmd.extend(args)
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            print(f"Fehler beim Ausführen von {script_path}: {e.stderr}")
            return None

    def check_id_gaps(self):
        print("-> Prüfe auf ID-Lücken...")
        ann_db = self._ann_db_path()
        src_db = self._src_db_path()
        ann_table = self._ann_table()

        with _sqlite_connect(ann_db) as conn:
            conn.execute("ATTACH DATABASE ? AS srcdb;", (str(src_db),))
            missing = conn.execute(
                f"""
                SELECT s.id
                FROM srcdb.{self.book} s
                LEFT JOIN main.{ann_table} a ON a.id = s.id
                WHERE a.id IS NULL AND s.id IS NOT NULL
                ORDER BY s.id ASC
                """
            ).fetchall()

        if not missing:
            print("   Keine Lücken gefunden.")
            return

        # Lücken protokollieren und zur Regeneration vormerken, damit blocks_to_xml_api sie erzeugen kann.
        for (mid,) in missing:
            mid_id = int(mid)
            self.missing_ids.add(mid_id)
            self._log("missing_id", id=mid_id)
            self.log_anomaly(mid_id)
        print(f"   Lücken gefunden: {len(missing)}")

    def check_duplicates(self):
        print("-> Prüfe auf Duplikate...")
        ids = duplicated.get_anomalies(str(self._ann_db_path()), self._ann_table())
        for rid in ids:
            self.log_anomaly(rid)

    def handle_divergence(self):
        print("-> Prüfe Text-Divergenz...")
        ann_db = str(self._ann_db_path())
        ann_table = self._ann_table()

        divergent_ids = set(check_divergent_rows.get_anomalies(ann_db, ann_table))
        for rid in divergent_ids:
            self.log_anomaly(rid)

    def handle_id_null(self):
        print("-> Prüfe auf ID=NULL...")
        with _sqlite_connect(self._ann_db_path()) as conn:
            remaining = conn.execute(
                f"SELECT rowid FROM {self._ann_table()} WHERE id IS NULL"
            ).fetchall()

        if remaining:
            rowids = [int(r[0]) for r in remaining]
            print(
                f"   Kritischer Fehler: {len(rowids)} Zeilen ohne ID (rowid): {rowids}"
            )
            raise RuntimeError(
                "ID=NULL rows found. Please repair IDs manually before running rollback_pipeline."
            )

    def run_fine_comparison(self):
        print("-> Starte Feinarbeit (klassifizierte Deltas)...")
        ann_db = self._ann_db_path()
        src_db = self._src_db_path()
        ann_table = self._ann_table()

        log_path = Path(cfg.LOGS_DIR) / "fine_diff.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        def classify(src_tokens: List[str], ann_tokens: List[str]) -> str:
            if not src_tokens and not ann_tokens:
                return "minimal"
            matcher = difflib.SequenceMatcher(a=src_tokens, b=ann_tokens)
            rr = matcher.real_quick_ratio()
            if rr < 0.75:
                return "divergent"
            qr = matcher.quick_ratio()
            if qr < 0.75:
                return "divergent"
            ratio = matcher.ratio()
            if ratio >= 0.97:
                ops = matcher.get_opcodes()
                diff_tokens = sum(
                    (i2 - i1) + (j2 - j1)
                    for tag, i1, i2, j1, j2 in ops
                    if tag != "equal"
                )
                return "minimal" if diff_tokens <= 2 else "minor"
            if ratio >= 0.9:
                ops = matcher.get_opcodes()
                diff_tokens = sum(
                    (i2 - i1) + (j2 - j1)
                    for tag, i1, i2, j1, j2 in ops
                    if tag != "equal"
                )
                return "minor" if diff_tokens <= 10 else "medium"
            if ratio >= 0.75:
                ops = matcher.get_opcodes()
                diff_tokens = sum(
                    (i2 - i1) + (j2 - j1)
                    for tag, i1, i2, j1, j2 in ops
                    if tag != "equal"
                )
                return "medium" if diff_tokens <= 30 else "divergent"
            return "divergent"

        minor_records: List[Dict[str, Any]] = []

        with _sqlite_connect(ann_db) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("ATTACH DATABASE ? AS srcdb;", (str(src_db),))
            cur = conn.execute(
                f"""
                SELECT ann.id AS id,
                       ann.extracted_text_full AS ann_text,
                       src.text AS src_text
                FROM main.{ann_table} ann
                JOIN srcdb.{self.book} src ON src.id = ann.id
                """
            )

            with log_path.open("w", encoding="utf-8") as log_f:
                while True:
                    batch = cur.fetchmany(2000)
                    if not batch:
                        break
                    for row in batch:
                        src_tokens = _normalize_guard_tokens(row["src_text"])  # type: ignore
                        ann_tokens = _normalize_guard_tokens(row["ann_text"])  # type: ignore
                        category = classify(src_tokens, ann_tokens)
                        rid = int(row["id"])
                        if category in {"minimal", "minor"}:
                            minor_records.append({"id": rid, "category": category})
                        elif category == "medium":
                            self.medium_ids.add(rid)
                            self.log_anomaly(rid, priority=2)
                        else:  # divergent
                            self.divergent_ids.add(rid)
                            self.log_anomaly(rid, priority=1)

                        # unified logging (JSONL + event log)
                        json.dump(
                            {
                                "id": rid,
                                "category": category,
                                "src_len": len(src_tokens),
                                "ann_len": len(ann_tokens),
                            },
                            log_f,
                            ensure_ascii=False,
                        )
                        log_f.write("\n")
                        self._log(
                            "classified",
                            id=rid,
                            category=category,
                            src_len=len(src_tokens),
                            ann_len=len(ann_tokens),
                        )

        self.minor_deltas.extend(minor_records)

    def process_with_gemini(self):
        # Reihenfolge: divergent -> medium -> minor
        if self.divergent_ids:
            ids = sorted(self.divergent_ids)
            print(
                f"-> Erzeuge {len(ids)} divergente IDs neu (blocks_to_xml_api Style)..."
            )
            for target_id in ids:
                try:
                    print(f"   regenerate divergent {target_id}")
                    self.regenerate_id(target_id, category="divergent")
                    self._log("regenerated", id=target_id, category="divergent")
                    self._remove_processed_jsonl_entry(target_id)
                except Exception as exc:  # noqa: BLE001
                    print(f"Regeneration fehlgeschlagen für ID {target_id}: {exc}")
                    self.log_unknown(target_id)

        if self.medium_ids:
            mids = sorted(self.medium_ids)
            print(f"-> Analysiere + regeneriere {len(mids)} medium-Deltas...")
            for target_id in mids:
                try:
                    print(f"   diagnose/regenerate medium {target_id}")
                    self.diagnose_id(target_id)
                    self._log("diagnosed", id=target_id, category="medium")
                except Exception as exc:  # noqa: BLE001
                    print(f"Diagnose fehlgeschlagen für ID {target_id}: {exc}")
                try:
                    self.regenerate_id(target_id, category="medium")
                    self._log("regenerated", id=target_id, category="medium")
                    self._remove_processed_jsonl_entry(target_id)
                except Exception as exc:  # noqa: BLE001
                    print(f"Regeneration fehlgeschlagen für ID {target_id}: {exc}")
                    self.log_unknown(target_id)

        self.align_minor_deltas()

        if self.unknown_ids:
            diag_sorted = sorted(self.unknown_ids)
            print(f"!!! Starte Diagnose-Phase für {len(diag_sorted)} IDs !!!")
            for target_id in diag_sorted:
                print(f"Diagnose ID {target_id} via Gemini API...")
                self.diagnose_id(target_id)
                self._log("diagnosed", id=target_id, category="diagnostic")

    def _build_alignment_prompt(self, src_text: str, ann_xml: str) -> str:
        header = "[CATEGORY=MINOR]"
        return (
            f"{header}\n\n"
            "You are aligning an annotated tafsir XML to its source text. "
            "Goal: produce XML that is exactly the source text plus correct XML tags; "
            "do not add, remove, or paraphrase any content. "
            "Keep all existing XML structure (<tafsir_section>, blocks, chunks, tags) "
            "but ensure the plain text matches the source 1:1. "
            "If you must choose, prefer preserving source wording over annotation fluff.\n\n"
            f"Source (plain text):\n{src_text}\n\n"
            f"Current annotated XML:\n{ann_xml}\n\n"
            "Return only the corrected XML."
        )

    def align_minor_deltas(self):
        if not self.minor_deltas:
            return
        print(f"-> Angleiche {len(self.minor_deltas)} kleine Deltas via Gemini...")
        self._log("align_minor_start", count=len(self.minor_deltas))

        gem = self._get_gemini()
        ann_db = self._ann_db_path()
        src_db = self._src_db_path()
        ann_table = self._ann_table()

        with _sqlite_connect(ann_db) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("ATTACH DATABASE ? AS srcdb;", (str(src_db),))

            for batch in _chunked(self.minor_deltas, 20):
                processed_ids: List[int] = []
                conn.execute("BEGIN IMMEDIATE")
                try:
                    for entry in batch:
                        target_id = int(entry["id"])
                        print(f"   aligning id {target_id}")
                        src_row = conn.execute(
                            f"SELECT text FROM srcdb.{self.book} WHERE id=?",
                            (target_id,),
                        ).fetchone()
                        ann_row = conn.execute(
                            f"SELECT extracted_text_full FROM main.{ann_table} WHERE id=?",
                            (target_id,),
                        ).fetchone()
                        if not src_row or not ann_row:
                            continue

                        src_text = src_row["text"] or ""
                        ann_xml = ann_row["extracted_text_full"] or ""
                        prompt = self._build_alignment_prompt(src_text, ann_xml)

                        xml_new = gem.generate(prompt)
                        if not xml_new:
                            continue

                        guard = evaluate_guard(src_text, xml_new)
                        if guard.get("decision") != "pass":
                            self.log_anomaly(target_id)
                            self._log(
                                "align_guard_fail",
                                id=target_id,
                                decision=guard.get("decision"),
                            )
                            continue

                        conn.execute(
                            f"""
                            UPDATE main.{ann_table}
                            SET extracted_text_full = ?, {NORMALIZED_COL} = ?
                            WHERE id = ?
                            """,
                            (
                                xml_new,
                                _normalize_to_string(xml_new),
                                target_id,
                            ),
                        )
                        self._log("aligned", id=target_id, category="minor")

                        block_table = f"{ann_table}_blocks"
                        chunk_table = f"{ann_table}_chunks"

                        conn.execute(
                            f"""
                            DELETE FROM main.{chunk_table}
                            WHERE tafsir_block_id IN (
                                SELECT id FROM main.{block_table} WHERE tafsir_section_id = ?
                            )
                            """,
                            (target_id,),
                        )
                        conn.execute(
                            f"DELETE FROM main.{block_table} WHERE tafsir_section_id = ?",
                            (target_id,),
                        )
                        processed_ids.append(target_id)

                    conn.commit()
                    for pid in processed_ids:
                        self._remove_processed_jsonl_entry(pid)
                except Exception:  # noqa: BLE001
                    conn.rollback()
                    raise

        self.minor_deltas.clear()

    def _ensure_analysis_tables_sqlite(
        self, conn: sqlite3.Connection
    ) -> Tuple[str, str, str, List[str]]:
        target_table = self._ann_table()
        block_table = f"{target_table}_blocks"
        chunk_table = f"{target_table}_chunks"
        all_columns: List[str] = list(ALL_COLUMNS)

        cols_sql = ", ".join(f"{c} TEXT" for c in all_columns)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {target_table} (
                id INTEGER PRIMARY KEY,
                {cols_sql},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {block_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tafsir_section_id INTEGER NOT NULL,
                block TEXT NOT NULL
            )
            """
        )
        chunk_column_defs = ", ".join(f"{c} TEXT" for c in all_columns)
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {chunk_table} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tafsir_block_id INTEGER NOT NULL,
                chunk TEXT NOT NULL,
                {chunk_column_defs},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        return target_table, block_table, chunk_table, all_columns

    def _delete_existing_section(
        self,
        conn: sqlite3.Connection,
        section_id: int,
        target_table: str,
        block_table: str,
        chunk_table: str,
    ) -> None:
        conn.execute(
            f"""
            DELETE FROM {chunk_table}
            WHERE tafsir_block_id IN (
                SELECT id FROM {block_table} WHERE tafsir_section_id = ?
            )
            """,
            (section_id,),
        )
        conn.execute(
            f"DELETE FROM {block_table} WHERE tafsir_section_id = ?", (section_id,)
        )
        conn.execute(f"DELETE FROM {target_table} WHERE id = ?", (section_id,))

    def _insert_generated_xml(
        self,
        conn: sqlite3.Connection,
        section_id: int,
        xml: str,
        target_table: str,
        block_table: str,
        chunk_table: str,
        all_columns: List[str],
    ) -> None:
        section_row = extract_nested_data(xml)
        section_row["id"] = section_id

        cols = ["id"] + all_columns
        placeholders = ", ".join(["?"] * len(cols))
        values = [section_row.get(c) for c in cols]
        conn.execute(
            f"INSERT INTO {target_table} ({', '.join(cols)}) VALUES ({placeholders})",
            values,
        )

        blocks = list(extract_section_blocks(xml))
        if not blocks:
            return

        block_ids = []
        for block_text in blocks:
            result = conn.execute(
                f"INSERT INTO {block_table} (tafsir_section_id, block) VALUES (?, ?)",
                (section_id, block_text),
            )
            lastrow = result.lastrowid
            if lastrow is None:
                lastrow = conn.exec_driver_sql("SELECT last_insert_rowid()").scalar()
            block_ids.append(int(lastrow))

        chunk_cols = ["tafsir_block_id", "chunk"] + all_columns
        chunk_sql = f"INSERT INTO {chunk_table} ({', '.join(chunk_cols)}) VALUES ({', '.join(['?'] * len(chunk_cols))})"

        chunk_values: List[Tuple[Any, ...]] = []
        for block_text, block_id in zip(blocks, block_ids):
            chunk_rows = extract_block_chunks(block_text, block_id)
            for chunk in chunk_rows:
                row_vals = [block_id, chunk.get("chunk")] + [
                    chunk.get(c) for c in all_columns
                ]
                chunk_values.append(tuple(row_vals))

        if chunk_values:
            conn.executemany(chunk_sql, chunk_values)

    def regenerate_id(self, target_id: int, category: str = "divergent"):
        src_db = self._src_db_path()
        ann_db = self._ann_db_path()

        with _sqlite_connect(src_db, pragmas=False) as conn_src:
            row = conn_src.execute(
                f"SELECT text FROM {self.book} WHERE id=?", (target_id,)
            ).fetchone()

        if not row or not row[0]:
            raise RuntimeError(f"Kein Source-Text in SRC_DB fuer ID {target_id}.")

        src_text = row[0]
        prompt_body = " ".join(
            src_text.replace("<p>", " ").replace("</p>", " ").split()
        )
        header = f"[CATEGORY={category.upper()}]"
        prompt = f"{header}\n\n{prompt_body}"

        gem = self._get_gemini()
        xml = gem.generate(prompt)
        if not xml:
            self.log_unknown(target_id)
            self._log("regen_fail_no_response", id=target_id, category=category)
            raise RuntimeError(f"Gemini lieferte keine Antwort fuer ID {target_id}.")

        cleaned_xml = clean_wrapped_xml(xml) or xml
        guard = evaluate_guard(prompt, cleaned_xml)
        if guard.get("decision") != "pass":
            self.log_unknown(target_id)
            self._log(
                "regen_guard_fail",
                id=target_id,
                category=category,
                decision=guard.get("decision"),
                coverage=guard.get("token_coverage"),
                overlap=guard.get("ngram_overlap"),
            )
            raise RuntimeError(
                f"Guard nicht bestanden fuer ID {target_id} "
                f"(decision={guard.get('decision')}, "
                f"coverage={guard.get('token_coverage'):.2f}, "
                f"overlap={guard.get('ngram_overlap'):.2f})"
            )

        with _sqlite_connect(ann_db) as conn:
            try:
                conn.execute("BEGIN IMMEDIATE")
                target_table, block_table, chunk_table, all_columns = (
                    self._ensure_analysis_tables_sqlite(conn)
                )
                self._delete_existing_section(
                    conn, target_id, target_table, block_table, chunk_table
                )
                self._insert_generated_xml(
                    conn,
                    target_id,
                    cleaned_xml,
                    target_table,
                    block_table,
                    chunk_table,
                    all_columns,
                )
                conn.commit()
            except Exception:  # noqa: BLE001
                conn.rollback()
                raise

    def _ensure_diag_table(self, conn: sqlite3.Connection) -> str:
        table = f"tafsir_diagnostics_{self.book}"
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER,
                category TEXT,
                source_text TEXT,
                annotated_text TEXT,
                response_text TEXT,
                guard_decision TEXT,
                token_coverage REAL,
                ngram_overlap REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        return table

    def classify_ids(self, ids: Iterable[int]):
        """Classify specific IDs only (bypasses full pipeline)."""
        ann_db = self._ann_db_path()
        src_db = self._src_db_path()
        ann_table = self._ann_table()

        def classify(src_tokens: List[str], ann_tokens: List[str]) -> str:
            if not src_tokens and not ann_tokens:
                return "minimal"
            matcher = difflib.SequenceMatcher(a=src_tokens, b=ann_tokens)
            rr = matcher.real_quick_ratio()
            if rr < 0.75:
                return "divergent"
            qr = matcher.quick_ratio()
            if qr < 0.75:
                return "divergent"
            ratio = matcher.ratio()
            ops = matcher.get_opcodes()
            diff_tokens = sum(
                (i2 - i1) + (j2 - j1) for tag, i1, i2, j1, j2 in ops if tag != "equal"
            )
            if ratio >= 0.97:
                return "minimal" if diff_tokens <= 2 else "minor"
            if ratio >= 0.9:
                return "minor" if diff_tokens <= 10 else "medium"
            if ratio >= 0.75:
                return "medium" if diff_tokens <= 30 else "divergent"
            return "divergent"

        with _sqlite_connect(ann_db) as conn_ann, _sqlite_connect(src_db) as conn_src:
            print(f"-> Classifying {len(ids)} explicit IDs")
            for rid in ids:
                ann_row = conn_ann.execute(
                    f"SELECT extracted_text_full FROM {ann_table} WHERE id=?",
                    (rid,),
                ).fetchone()
                src_row = conn_src.execute(
                    f"SELECT text FROM {self.book} WHERE id=?",
                    (rid,),
                ).fetchone()

                if not src_row:
                    self._log("classify_missing_src", id=rid)
                    self.missing_ids.add(int(rid))
                    continue
                if not ann_row:
                    self._log("classify_missing_ann", id=rid)
                    self.missing_ids.add(int(rid))
                    continue

                src_tokens = _normalize_guard_tokens(src_row[0])  # type: ignore
                ann_tokens = _normalize_guard_tokens(ann_row[0])  # type: ignore
                category = classify(src_tokens, ann_tokens)
                if category in {"minimal", "minor"}:
                    self.minor_deltas.append({"id": rid, "category": category})
                elif category == "medium":
                    self.medium_ids.add(int(rid))
                else:
                    self.divergent_ids.add(int(rid))
                print(f"   classified {rid} as {category}")
                self._log(
                    "classified_manual",
                    id=int(rid),
                    category=category,
                    src_len=len(src_tokens),
                    ann_len=len(ann_tokens),
                )

    def diagnose_id(self, target_id: int):
        src_db = self._src_db_path()
        ann_db = self._ann_db_path()

        with _sqlite_connect(src_db, pragmas=False) as conn_src:
            src_row = conn_src.execute(
                f"SELECT text FROM {self.book} WHERE id=?", (target_id,)
            ).fetchone()
        src_text = src_row[0] if src_row else None

        with _sqlite_connect(ann_db, pragmas=False) as conn_ann:
            ann_row = conn_ann.execute(
                f"SELECT extracted_text_full FROM {self._ann_table()} WHERE id=?",
                (target_id,),
            ).fetchone()
        ann_text = ann_row[0] if ann_row else None

        prompt = (
            "[CATEGORY=MEDIUM]\n\n"
            "Analyse einer unerwarteten annotierten Tafsir-Zeile.\n"
            "Liefere eine strukturierte JSON-Antwort mit den Feldern:\n"
            "{\n"
            '  "analysis": <kurze technische Ursachenanalyse>,\n'
            '  "root_cause": <wahrscheinlichste Ursache>,\n'
            '  "proposed_fix_xml": <korrigierter XML-Auszug oder null>,\n'
            '  "notes": <optionale Hinweise>\n'
            "}\n\n"
            f"Source (plain text): {src_text}\n"
            f"Annotated (current XML): {ann_text}\n"
            "Beurteile Konsistenz, fehlende Tags, falsche Reihenfolge oder OCR/Parsing-Probleme. "
            "Wenn kein valider Fix möglich ist, setze proposed_fix_xml auf null."
        )

        gem = self._get_gemini()
        response_text = gem.generate(prompt)
        self._log(
            "diagnosis_result", id=target_id, response_present=bool(response_text)
        )

        with _sqlite_connect(ann_db) as conn:
            table = self._ensure_diag_table(conn)
            conn.execute(
                f"""
                INSERT INTO {table} (id, category, source_text, annotated_text, response_text,
                                     guard_decision, token_coverage, ngram_overlap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    target_id,
                    "diagnostic",
                    src_text,
                    ann_text,
                    response_text,
                    None,
                    None,
                    None,
                ),
            )

    def run_pipeline(self):
        print(f"=== Starte Rollback Pipeline für {self.book} ===")
        steps = [
            ("ID-Luecken", self.check_id_gaps),
            ("Duplikate", self.check_duplicates),
            ("ID-NULL Patch", self.handle_id_null),
            ("Divergenz", self.handle_divergence),
            ("Feinvergleich", self.run_fine_comparison),
        ]
        for name, fn in steps:
            try:
                fn()
            except KeyboardInterrupt:
                raise
            except Exception as exc:  # noqa: BLE001
                print(
                    f"ABBRUCH: Schritt '{name}' fehlgeschlagen ({exc.__class__.__name__}: {exc})"
                )
                raise

        print(
            f"Anomalie-Liste erstellt: regen={len(self.regen_ids)}, diagnose={len(self.unknown_ids)}"
        )
        if self.missing_ids:
            print(
                f"Hinweis: {len(self.missing_ids)} IDs fehlen in ANN. "
                "blocks_to_xml_api.py ausführen, um sie zu erzeugen."
            )
        try:
            self.process_with_gemini()
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001
            print(
                f"ABBRUCH: Gemini-Insert fehlgeschlagen ({exc.__class__.__name__}: {exc})"
            )
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Rollback/repair pipeline")
    parser.add_argument("--book", default=cfg.DEFAULT_TAFSIR, help="Tafsir book name")
    parser.add_argument(
        "--ids",
        nargs="+",
        type=int,
        help="Nur diese IDs bearbeiten (skip globale Checks)",
    )
    parser.add_argument(
        "--jsonl",
        type=str,
        help="Pfad zu bestehender fine_diff JSONL; überspringt Checks und nutzt nur diese Einträge",
    )
    args = parser.parse_args()

    pipeline = TafsirRollbackPipeline(book=args.book)
    if args.jsonl:
        pipeline.load_from_jsonl(Path(args.jsonl))
        pipeline.process_with_gemini()
    elif args.ids:
        pipeline.classify_ids(args.ids)
        pipeline.process_with_gemini()
    else:
        pipeline.run_pipeline()
