"""
Automatisierte Nachkorrektur für Tafsir-Annotationen.

Workflow:
1) Mismatches (src vs. ann) finden und jeweils den korrekten src-Datensatz ermitteln.
2) Annotierte Zeilen auf die korrekte ID remappen (inkl. Blocks/Chunks-Kopien).
3) Fehlende IDs identifizieren und gezielt via `blocks_to_xml_continue.py` nachziehen.
4) Optional regulären Lauf ab der nächsten offenen ID fortsetzen.

Hinweis: Dieses Skript greift **nicht** auf das UI/pyautogui zu; das geschieht
über `automate_gemini` aus `blocks_to_xml_continue`.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Dict, List, Optional, Sequence, Tuple

import sqlite3

from blocks_to_xml_continue import (  # type: ignore
    DEFAULT_START_ID,
    DBS,
    automate_gemini,
    evaluate_guard,
)
from check_divergent_rows import normalize

# Laufpfad so erweitern, dass das Elternverzeichnis (utils) importierbar ist
THIS_DIR = Path(__file__).resolve().parent
PARENT_UTILS = THIS_DIR.parent
if str(PARENT_UTILS) not in sys.path:
    sys.path.insert(0, str(PARENT_UTILS))  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# --------------------------------------------------------------------------- #
# Helpers for DB access                                                       #
# --------------------------------------------------------------------------- #
def _paths_for_db(db: str) -> Tuple[Path, Path]:
    src = REPO_ROOT / "tafsir_books" / f"{db}.sqlite3"
    ann = REPO_ROOT / "tafsir_books_annotated" / f"{db}_annotated.sqlite3"
    return src, ann


def _connect_sqlite(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _columns_sqlite(conn: sqlite3.Connection, table: str) -> List[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info('{table}')")]


def _fetch_source_rows(conn: sqlite3.Connection, table: str) -> List[sqlite3.Row]:
    return list(
        conn.execute(
            f"SELECT id, text FROM {table} WHERE text IS NOT NULL AND text != ''"
        )
    )


def _detect_mismatches(
    conn_src: sqlite3.Connection,
    ann_path: Path,
    src_table: str,
    ann_table: str,
    annotated_col: str,
) -> List[Dict]:
    """
    Vergleicht src- und annotierte Tabelle direkt im selben Connection-Kontext.
    Annotierte DB wird als ATTACH eingebunden, damit der Join funktioniert.
    """
    mismatches: List[Dict] = []

    # Eindeutiger Schema-Name je Aufruf, um Mehrfach-Attach-Konflikte zu vermeiden
    attach_name = "ann_db"
    conn_src.execute("ATTACH DATABASE ? AS ann_db", (str(ann_path),))

    query = f"""
        SELECT src.id AS source_id,
               src.text AS source_text,
               ann.id AS annotated_id,
               ann.{annotated_col} AS annotated_text
        FROM {src_table} src
        INNER JOIN ann_db.{ann_table} ann ON src.id = ann.id
        ORDER BY src.id
    """

    for row in conn_src.execute(query):
        guard = evaluate_guard(row["source_text"], row["annotated_text"])
        if guard["decision"] != "pass":
            mismatches.append(
                {
                    "source_id": row["source_id"],
                    "annotated_id": row["annotated_id"],
                    "annotated_text": row["annotated_text"],
                    "guard": guard,
                }
            )

    conn_src.execute("DETACH DATABASE ann_db")
    return mismatches


def _best_source_match(
    ann_text: str, source_rows: Sequence[sqlite3.Row]
) -> Optional[int]:
    """Find the src.id with highest guard score against the annotated text."""
    best_id: Optional[int] = None
    best_cov, best_ov = 0.0, 0.0

    for src_row in source_rows:
        guard = evaluate_guard(src_row["text"], ann_text)
        cov = guard["token_coverage"]
        ovl = guard["ngram_overlap"]
        if cov > best_cov or (cov == best_cov and ovl > best_ov):
            best_cov, best_ov = cov, ovl
            best_id = src_row["id"]

    # Minimal Schwelle, um wilde Zuordnungen zu vermeiden
    if best_cov < 0.65 or best_ov < 0.35:
        return None
    return best_id


# --------------------------------------------------------------------------- #
# Remapping (kopiert Blöcke/Chunks & räumt alte Zeile auf)                   #
# --------------------------------------------------------------------------- #
def _remap_section(
    conn: sqlite3.Connection,
    section_table: str,
    block_table: str,
    chunk_table: str,
    old_id: int,
    new_id: int,
) -> bool:
    """
    Kopiert den Datensatz inkl. Blocks/Chunks auf new_id und löscht old_id.
    Kein Update-in-place, damit FK-Konsistenz gewahrt bleibt.
    """
    if old_id == new_id:
        return False

    exists = conn.execute(
        f"SELECT 1 FROM {section_table} WHERE id=:nid", {"nid": new_id}
    ).fetchone()
    if exists:
        print(f"Ziel-ID {new_id} existiert bereits – übersprungen.")
        return False

    section_row = conn.execute(
        f"SELECT * FROM {section_table} WHERE id=:oid", {"oid": old_id}
    ).fetchone()
    if not section_row:
        print(f"Quell-ID {old_id} nicht gefunden – übersprungen.")
        return False

    section_cols = _columns_sqlite(conn, section_table)
    section_vals = {col: section_row[col] for col in section_cols}
    section_vals["id"] = new_id

    placeholders = ", ".join(f":{c}" for c in section_cols)
    cols_sql = ", ".join(section_cols)
    conn.execute(
        f"INSERT INTO {section_table} ({cols_sql}) VALUES ({placeholders})",
        section_vals,
    )

    block_cols = [c for c in _columns_sqlite(conn, block_table) if c != "id"]
    block_cols_sql = ", ".join(block_cols)
    block_ph = ", ".join(f":{c}" for c in block_cols)
    block_rows = conn.execute(
        f"SELECT * FROM {block_table} WHERE tafsir_section_id=:oid",
        {"oid": old_id},
    ).fetchall()

    block_id_map: Dict[int, int] = {}
    for b in block_rows:
        data = {c: b[c] for c in block_cols}
        old_block_id = b["id"]
        data["tafsir_section_id"] = new_id
        res = conn.execute(
            f"INSERT INTO {block_table} ({block_cols_sql}) VALUES ({block_ph})", data
        )
        new_block_id = res.lastrowid
        if new_block_id is None:
            new_block_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        block_id_map[old_block_id] = new_block_id

    chunk_cols = [c for c in _columns_sqlite(conn, chunk_table) if c != "id"]
    chunk_cols_sql = ", ".join(chunk_cols)
    chunk_ph = ", ".join(f":{c}" for c in chunk_cols)

    for old_block, new_block in block_id_map.items():
        chunk_rows = conn.execute(
            f"SELECT * FROM {chunk_table} WHERE tafsir_block_id=:bid",
            {"bid": old_block},
        ).fetchall()
        for chunk in chunk_rows:
            data = {c: chunk[c] for c in chunk_cols}
            data["tafsir_block_id"] = new_block
            conn.execute(
                f"INSERT INTO {chunk_table} ({chunk_cols_sql}) VALUES ({chunk_ph})",
                data,
            )

    # Altes Section-Row löschen (FK löscht Blocks/Chunks dazu)
    conn.execute(f"DELETE FROM {section_table} WHERE id=:oid", {"oid": old_id})
    print(f"Remapped {old_id} -> {new_id}")
    return True


# --------------------------------------------------------------------------- #
# Gap detection                                                               #
# --------------------------------------------------------------------------- #
def _find_missing_ids(
    conn_src: sqlite3.Connection, conn_ann: sqlite3.Connection, db: str
) -> List[int]:
    src_ids = {
        r[0]
        for r in conn_src.execute(
            f"SELECT id FROM {db} WHERE text IS NOT NULL AND text != ''"
        )
    }
    ann_ids = {r[0] for r in conn_ann.execute(f"SELECT id FROM tafsir_analysis_{db}")}
    return sorted(src_ids - ann_ids)


# --------------------------------------------------------------------------- #
# Main pipeline                                                               #
# --------------------------------------------------------------------------- #
def reconcile_database(
    db: str, start_id: int = DEFAULT_START_ID, resume: bool = True
) -> None:
    src_path, ann_path = _paths_for_db(db)
    section_table = f"tafsir_analysis_{db}"
    block_table = f"{section_table}_blocks"
    chunk_table = f"{section_table}_chunks"
    annotated_col = "extracted_text_full"

    with _connect_sqlite(src_path) as conn_src, _connect_sqlite(ann_path) as conn_ann:
        mismatches = _detect_mismatches(
            conn_src, ann_path, db, section_table, annotated_col
        )
        print(f"{db}: {len(mismatches)} mismatches gefunden.")

        if mismatches:
            source_rows = _fetch_source_rows(conn_src, db)
            with conn_ann:
                for mm in mismatches:
                    target = _best_source_match(mm["annotated_text"], source_rows)
                    if target is None:
                        print(
                            f"ID {mm['annotated_id']}: kein belastbarer Match gefunden "
                            f"(cov={mm['guard']['token_coverage']:.2f}, "
                            f"ovl={mm['guard']['ngram_overlap']:.2f})"
                        )
                        continue
                    _remap_section(
                        conn_ann,
                        section_table,
                        block_table,
                        chunk_table,
                        old_id=mm["annotated_id"],
                        new_id=target,
                    )

        missing_ids = _find_missing_ids(conn_src, conn_ann, db)
        print(f"{db}: fehlende IDs: {missing_ids}")

    # 1) Fehlende IDs gezielt nachziehen
    if missing_ids:
        automate_gemini(db, exact_ids=missing_ids)

    # 2) Optional normalen Lauf fortsetzen ab nächster offener ID
    if resume:
        with _connect_sqlite(ann_path) as conn_ann:
            row = conn_ann.execute(f"SELECT MAX(id) FROM {section_table}").fetchone()
            max_ann = row[0] if row and row[0] is not None else start_id
        resume_id = max_ann + 1
        automate_gemini(db, start_id=resume_id)


def main():
    parser = argparse.ArgumentParser(
        description="Mismatches remappen, Lücken füllen und Lauf fortsetzen."
    )
    parser.add_argument(
        "--db",
        dest="dbs",
        action="append",
        choices=DBS,
        help="Welche DB(s) bearbeiten (kann mehrfach angegeben werden). Standard: alle.",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Nur Mismatches + Lücken behandeln, keinen regulären Fortsetzungslauf starten.",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=DEFAULT_START_ID,
        help="Fallback-Start-ID, falls keine Einträge existieren (Standard entspricht Hauptlauf).",
    )

    args = parser.parse_args()
    targets = args.dbs or DBS
    for db in targets:
        reconcile_database(db, start_id=args.start_id, resume=not args.no_resume)


if __name__ == "__main__":
    main()
