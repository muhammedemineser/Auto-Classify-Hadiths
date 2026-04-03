import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, UTC
from pathlib import Path

from sqlalchemy import MetaData, Table, create_engine, select, text

from google import genai
from google.genai import types

from Tafsir.config import paths as cfg
from Tafsir.pipeline.gemini_common import (
    ALL_COLUMNS,
    GUARD_MAX_RETRIES,
    GUARD_MIN_LEN_RATIO,
    GUARD_NGRAM_SIZE,
    NORMALIZED_COL,
    RAW_COL,
    RX_RECURSIVE,
    _normalize_guard_tokens,
    _normalize_to_string,
    backfill_normalized,
    clean_wrapped_xml,
    evaluate_guard,
    extract_block_chunks,
    extract_nested_data,
    extract_section_blocks,
    insert_empty_section,
)


# When executed as ``python path/to/blocks_to_xml_api.py`` Python sets
# ``sys.path[0]`` to this file's directory (…/Tafsir/pipeline/gemini_api) which
# does not include the repository root. Ensure the repo root is on sys.path so
# ``import Tafsir`` works both as a module and as a stand‑alone script.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_env():
    """
    Lightweight .env loader so the script works even when the shell hasn't
    exported GEMINI_* variables. Only reads from /app/.env.
    """
    env_path = cfg.PROJECT_ROOT.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        if key and key not in os.environ:
            os.environ[key] = val


_load_env()

REPO_ROOT = cfg.PROJECT_ROOT


def _resolve_output_db_path(
    db: str,
    exact_ids=None,
    explicit_path: str | Path | None = None,
    model_suffix: str | None = None,
) -> Path:
    """
    Pick the output SQLite path.

    - default: <db>_annotated.sqlite3
    - when exact_ids are provided: <db>_annotated_subset[_{model_suffix}].sqlite3
    - explicit path overrides both
    """

    if explicit_path:
        return Path(explicit_path)

    suffix = f"_{model_suffix}" if model_suffix else ""
    if exact_ids:
        return cfg.ANNOTATED_DIR / f"{db}_annotated_subset{suffix}.sqlite3"
    return cfg.ANNOTATED_DIR / f"{db}_annotated{suffix}.sqlite3"


def _discover_model_configs() -> list[tuple[str, dict[str, str]]]:
    """
    Collect available GEMINI model configurations from the environment.

    Supported patterns:
      - default keys: GEMINI_API_KEY, GEMINI_MODEL_ID, GEMINI_CACHE_NAME
      - numbered/suffixed keys: GEMINI_<LABEL>_API_KEY, GEMINI_<LABEL>_MODEL_ID, GEMINI_<LABEL>_CACHE_NAME
    """

    configs: list[tuple[str, dict[str, str]]] = []

    base_cfg = {
        "API_KEY": os.getenv("GEMINI_API_KEY"),
        "MODEL_ID": os.getenv("GEMINI_MODEL_ID"),
        "CACHE_NAME": os.getenv("GEMINI_CACHE_NAME"),
    }
    if base_cfg["API_KEY"] and base_cfg["MODEL_ID"]:
        configs.append(("default", base_cfg))

    grouped: dict[str, dict[str, str]] = {}
    label_order: list[str] = []
    for key, val in os.environ.items():
        if not key.startswith("GEMINI_"):
            continue
        parts = key.split("_", 2)
        if len(parts) != 3:
            continue
        _, label, field = parts
        if field not in {"API_KEY", "MODEL_ID", "CACHE_NAME"}:
            continue
        norm_label = label.lower()
        if norm_label not in grouped:
            grouped[norm_label] = {"_label_raw": label}
            label_order.append(norm_label)
        grouped[norm_label][field] = val

    # Preserve .env order (first seen wins) after optional default.
    for norm_label in label_order:
        cfg_fields = grouped[norm_label]
        if cfg_fields.get("API_KEY") and cfg_fields.get("MODEL_ID"):
            cfg_fields.setdefault("CACHE_NAME", os.getenv("GEMINI_CACHE_NAME") or "")
            raw_label = cfg_fields.pop("_label_raw", norm_label)
            configs.append((raw_label, cfg_fields))

    return configs


def _apply_model_env(model_cfg: dict[str, str]):
    """
    Set environment for a specific model and reset the cached Gemini client.
    """

    for field, val in model_cfg.items():
        os.environ[f"GEMINI_{field}"] = val
    _reset_gemini_client()


LOGS_DIR = REPO_ROOT / "logs"
_LOG_LOCK = threading.Lock()
_CURRENT_LOG_JSON_PATH = LOGS_DIR / "structured_logs_default.json"


def _sanitize_label(label: str | None) -> str:
    if not label:
        return "default"
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(label))
    return safe or "default"


def _set_log_target(model_label: str | None) -> None:
    """
    Set the per-model structured log file so parallel model runs do not
    overwrite each other. File name pattern:
    logs/structured_logs_<model>.json
    """
    global _CURRENT_LOG_JSON_PATH
    suffix = _sanitize_label(model_label)
    _CURRENT_LOG_JSON_PATH = LOGS_DIR / f"structured_logs_{suffix}.json"


def _format_row_ids(row_id):
    """Normalize a single row identifier for JSON logging."""

    if row_id is None or isinstance(row_id, (list, tuple, set, dict)):
        raise ValueError("row_id must be a single value")
    try:
        return str(int(row_id))
    except (TypeError, ValueError) as exc:  # noqa: B904
        raise ValueError("row_id must be convertible to int") from exc


def _write_log(path, entry, *, row_id):
    """
    Append a log entry into the unified JSON log, grouped by row_id then log type.

    JSON shape:
    {
      "<ROW_ID>": {
        "<log_type>": ["entry1", "entry2", ...]
      }
    }
    """

    rid = _format_row_ids(row_id)
    log_type = Path(path).stem  # e.g., responses, guard, progress, errors

    _CURRENT_LOG_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    with _LOG_LOCK:
        try:
            data = json.loads(_CURRENT_LOG_JSON_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            data = {}
        except json.JSONDecodeError:
            data = {}

        log_bucket = data.setdefault(rid, {})
        log_bucket.setdefault(log_type, []).append(entry)

        tmp_path = _CURRENT_LOG_JSON_PATH.with_suffix(".tmp")
        tmp_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        tmp_path.replace(_CURRENT_LOG_JSON_PATH)


def _guard_reason(decision, guard):
    """Describe which criteria failed (or succeeded) for this evaluation."""

    falls = []
    if guard["token_coverage"] < 0.85:
        falls.append("coverage<0.85")
    if guard["ngram_overlap"] < 0.6:
        falls.append("overlap<0.6")
    if guard["length_ratio"] < GUARD_MIN_LEN_RATIO:
        falls.append(f"length_ratio<{GUARD_MIN_LEN_RATIO}")

    if decision == "pass":
        return "all_thresholds_met"
    if decision == "skip":
        return "max_retries_exceeded"
    if falls:
        return ",".join(falls)

    if decision == "log":
        return "guard_logged"
    return "retry_thresholds_pending"


def _log_guard_entry(row_id, guard, attempt, response, decision, model_label):
    """Log detailed guard metadata plus the model response for traceability."""

    entry = {
        "decision": decision,
        "attempt": attempt,
        "criteria": {
            "coverage": guard["token_coverage"],
            "overlap": guard["ngram_overlap"],
            "length_ratio": guard["length_ratio"],
        },
        "thresholds": {
            "pass_coverage": 0.85,
            "pass_overlap": 0.6,
            "min_length_ratio": GUARD_MIN_LEN_RATIO,
            "max_retries": GUARD_MAX_RETRIES,
        },
        "response": {
            "status": "accepted" if decision == "pass" else "rejected",
            "text": response,
        },
        "reason": _guard_reason(decision, guard),
        "source": f"row={row_id}",
        "model_label": model_label,
    }

    _write_log("logs/guard.log", entry, row_id=row_id)


_GEMINI_CLIENT = None
_GENAI_TYPES = None


def _reset_gemini_client():
    """Force a fresh client on next request (e.g., when switching models)."""
    global _GEMINI_CLIENT, _GENAI_TYPES
    _GEMINI_CLIENT = None
    _GENAI_TYPES = None


def _get_gemini_client():
    global _GEMINI_CLIENT, _GENAI_TYPES
    if _GEMINI_CLIENT is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY fehlt.")

        # Initialisierung des neuen Clients
        _GEMINI_CLIENT = genai.Client(api_key=api_key)
        _GENAI_TYPES = types
    return _GEMINI_CLIENT, _GENAI_TYPES


def request_gemini_response(prompt):
    client, types = _get_gemini_client()

    cache_name = os.getenv("GEMINI_CACHE_NAME")
    model_id = os.getenv("GEMINI_MODEL_ID")
    if not cache_name:
        raise RuntimeError("GEMINI_CACHE_NAME ist nicht gesetzt.")
    if not model_id:
        raise RuntimeError("MODEL_ID ist nicht gesetzt.")

    try:
        config = types.GenerateContentConfig(
            cached_content=cache_name,
        )

        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=config,
        )

        if not response.candidates:
            print("Keine Antwort von der Gemini API erhalten; Abbruch.")
            sys.exit(1)

        return response.text

    except Exception as e:
        msg = str(e)
        print(f"Fehler bei der Gemini-Anfrage: {msg}")

        if "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota" in msg.lower():
            sys.exit(130)

        return None


def cleanup_cycle(
    batch,
    executor,
    engine_out,
    section_table,
    block_table,
    chunk_table,
    flush_batch=False,
    pending_futures=None,
    prefetched_record=None,
    append_to_batch=True,
):
    """
    Manage batching and optional flushing; UI interactions removed in API mode.
    """
    record = prefetched_record if prefetched_record is not None else None
    if append_to_batch and record:
        batch.append(record)

    if flush_batch and batch:
        future = executor.submit(
            bulk_insert_tafsir,
            engine_out,
            section_table,
            block_table,
            chunk_table,
            list(batch),
        )
        if pending_futures is not None:
            pending_futures.append(future)
        batch.clear()
    return record


def _walk(xml, row):
    """Recursively collect every tag (including nested tags) into the flat row."""
    if not xml:
        return

    for match in RX_RECURSIVE.finditer(xml):
        tag = match.group("tag")
        full = match.group(0)
        content = match.group("content")

        if row[tag] is None:
            row[tag] = full
        elif full not in row[tag]:
            row[tag] += "\n" + full

        _walk(content, row)


def _build_block_id_mapping(conn, block_table):
    mapping = {}
    for row in conn.execute(text(f"SELECT rowid, id FROM {block_table}")):
        mapping[row[0]] = [row[1]]
    return mapping


def _migrate_block_table(conn, block_table, block_sql):
    temp_table = f"{block_table}_old_migration"
    conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))
    conn.execute(text(f"ALTER TABLE {block_table} RENAME TO {temp_table}"))
    conn.execute(text(block_sql))
    mapping = {}
    for row in conn.execute(
        text(f"SELECT rowid, tafsir_section_id, block FROM {temp_table}")
    ):
        block_texts = extract_section_blocks(row[2])
        if not block_texts:
            block_texts = [row[2]]
        new_ids = []
        for block_text in block_texts:
            insert = conn.execute(
                text(
                    f"INSERT INTO {block_table} (tafsir_section_id, block) "
                    "VALUES (:tafsir_section_id, :block)"
                ),
                {"tafsir_section_id": row[1], "block": block_text},
            )
            new_id = insert.lastrowid
            if new_id is None:
                new_id = conn.exec_driver_sql("SELECT last_insert_rowid()").scalar()
            new_ids.append(new_id)
        mapping[row[0]] = new_ids
    conn.execute(text(f"DROP TABLE {temp_table}"))
    return mapping


def _migrate_chunk_table(conn, chunk_table, chunk_sql, block_id_mapping):
    temp_table = f"{chunk_table}_old_migration"
    conn.execute(text(f"DROP TABLE IF EXISTS {temp_table}"))
    conn.execute(text(f"ALTER TABLE {chunk_table} RENAME TO {temp_table}"))
    conn.execute(text(chunk_sql))
    chunk_cols = ", ".join(ALL_COLUMNS)
    chunk_vals = ", ".join(f":{c}" for c in ALL_COLUMNS)
    insert_stmt = text(
        f"INSERT INTO {chunk_table} (tafsir_block_id, chunk, {chunk_cols}) "
        f"VALUES (:tafsir_block_id, :chunk, {chunk_vals})"
    )
    for row in conn.execute(text(f"SELECT tafsir_chunks, chunk FROM {temp_table}")):
        new_block_ids = block_id_mapping.get(row[0], [])
        if not new_block_ids:
            continue
        chunk_text = row[1]
        for new_block_id in new_block_ids:
            extracted_chunks = extract_block_chunks(chunk_text, new_block_id)
            if not extracted_chunks:
                chunk_data = extract_nested_data(chunk_text)
                chunk_data["tafsir_block_id"] = new_block_id
                chunk_data["chunk"] = chunk_text
                conn.execute(insert_stmt, chunk_data)
            else:
                for chunk_row in extracted_chunks:
                    conn.execute(insert_stmt, chunk_row)
    conn.execute(text(f"DROP TABLE {temp_table}"))


def setup_analysis_tables(engine_out, section_table, block_table, chunk_table):
    cols_sql = ", ".join(f"{c} TEXT" for c in ALL_COLUMNS)

    section_sql = f"""
    CREATE TABLE IF NOT EXISTS {section_table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {cols_sql},
        {NORMALIZED_COL} TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    block_sql = f"""
    CREATE TABLE IF NOT EXISTS {block_table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tafsir_section_id INTEGER NOT NULL,
        block TEXT NOT NULL,
        FOREIGN KEY (tafsir_section_id) REFERENCES {section_table}(id) ON DELETE CASCADE
    );
    """
    block_index_sql = f"""
    CREATE INDEX IF NOT EXISTS idx_{block_table}_section
    ON {block_table} (tafsir_section_id);
    """

    chunk_column_defs = ", ".join(f"{c} TEXT" for c in ALL_COLUMNS)
    chunk_sql = f"""
    CREATE TABLE IF NOT EXISTS {chunk_table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tafsir_block_id INTEGER NOT NULL,
        chunk TEXT NOT NULL,
        {chunk_column_defs},
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (tafsir_block_id) REFERENCES {block_table}(id) ON DELETE CASCADE
    );
    """
    chunk_index_sql = f"""
    CREATE INDEX IF NOT EXISTS idx_{chunk_table}_block
    ON {chunk_table} (tafsir_block_id);
    """

    with engine_out.begin() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA foreign_keys=OFF"))

        conn.execute(text(section_sql))
        conn.execute(text(block_sql))
        conn.execute(text(block_index_sql))
        conn.execute(text(chunk_sql))
        conn.execute(text(chunk_index_sql))

        conn.execute(text("PRAGMA foreign_keys=ON"))


def _now_ts():
    # timezone-aware, UTC-normalized timestamp without microseconds
    return datetime.now(UTC).replace(microsecond=0).isoformat(" ")


def repair_analysis_tables(engine_out, section_table, block_table, chunk_table):
    """
    Rebuild the tafsir analysis tables to ensure:
      - integer primary keys with AUTOINCREMENT
      - created_at defaults
      - normalized column present on the section table
      - foreign keys remain consistent
    """
    with engine_out.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))

        section_rows = []
        block_rows = []
        chunk_rows = []

        if conn.dialect.has_table(conn, section_table):
            section_rows = list(
                conn.execute(
                    text(f"SELECT rowid AS _rowid, * FROM {section_table}")
                ).mappings()
            )
        if conn.dialect.has_table(conn, block_table):
            block_rows = list(
                conn.execute(
                    text(f"SELECT rowid AS _rowid, * FROM {block_table}")
                ).mappings()
            )
        if conn.dialect.has_table(conn, chunk_table):
            chunk_rows = list(
                conn.execute(
                    text(f"SELECT rowid AS _rowid, * FROM {chunk_table}")
                ).mappings()
            )

        conn.execute(text(f"DROP TABLE IF EXISTS {chunk_table}"))
        conn.execute(text(f"DROP TABLE IF EXISTS {block_table}"))
        conn.execute(text(f"DROP TABLE IF EXISTS {section_table}"))

        cols_sql = ", ".join(f"{c} TEXT" for c in ALL_COLUMNS)
        section_sql = f"""
        CREATE TABLE IF NOT EXISTS {section_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {cols_sql},
            {NORMALIZED_COL} TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        block_sql = f"""
        CREATE TABLE IF NOT EXISTS {block_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tafsir_section_id INTEGER NOT NULL,
            block TEXT NOT NULL,
            FOREIGN KEY (tafsir_section_id) REFERENCES {section_table}(id) ON DELETE CASCADE
        );
        """
        block_index_sql = f"""
        CREATE INDEX IF NOT EXISTS idx_{block_table}_section
        ON {block_table} (tafsir_section_id);
        """
        chunk_column_defs = ", ".join(f"{c} TEXT" for c in ALL_COLUMNS)
        chunk_sql = f"""
        CREATE TABLE IF NOT EXISTS {chunk_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tafsir_block_id INTEGER NOT NULL,
            chunk TEXT NOT NULL,
            {chunk_column_defs},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tafsir_block_id) REFERENCES {block_table}(id) ON DELETE CASCADE
        );
        """
        chunk_index_sql = f"""
        CREATE INDEX IF NOT EXISTS idx_{chunk_table}_block
        ON {chunk_table} (tafsir_block_id);
        """

        conn.execute(text(section_sql))
        conn.execute(text(block_sql))
        conn.execute(text(block_index_sql))
        conn.execute(text(chunk_sql))
        conn.execute(text(chunk_index_sql))

        desired_section_cols = ["id"] + ALL_COLUMNS + [NORMALIZED_COL, "created_at"]
        section_insert = text(
            f"INSERT INTO {section_table} ({', '.join(desired_section_cols)}) "
            f"VALUES ({', '.join(':' + c for c in desired_section_cols)})"
        )

        section_rowid_to_id = {}
        for row in section_rows:
            new_id = row.get("id") or row["_rowid"]
            section_rowid_to_id[row["_rowid"]] = new_id
            payload = {c: row.get(c) for c in ALL_COLUMNS}
            payload["id"] = new_id
            normalized = row.get(NORMALIZED_COL) or _normalize_to_string(
                row.get(RAW_COL)
            )
            payload[NORMALIZED_COL] = normalized
            payload["created_at"] = row.get("created_at") or _now_ts()
            conn.execute(section_insert, payload)

        block_insert = text(
            f"INSERT INTO {block_table} (id, tafsir_section_id, block) "
            f"VALUES (:id, :tafsir_section_id, :block)"
        )
        block_rowid_to_id = {}
        for row in block_rows:
            old_rowid = row["_rowid"]
            new_id = old_rowid
            block_rowid_to_id[old_rowid] = new_id
            mapped_section = section_rowid_to_id.get(
                row.get("tafsir_section_id"), row.get("tafsir_section_id")
            )
            conn.execute(
                block_insert,
                {
                    "id": new_id,
                    "tafsir_section_id": mapped_section,
                    "block": row.get("block"),
                },
            )

        chunk_cols = ["id", "tafsir_block_id", "chunk"] + ALL_COLUMNS + ["created_at"]
        chunk_insert = text(
            f"INSERT INTO {chunk_table} ({', '.join(chunk_cols)}) "
            f"VALUES ({', '.join(':' + c for c in chunk_cols)})"
        )
        for row in chunk_rows:
            new_chunk_id = row.get("id") or row["_rowid"]
            new_block_id = block_rowid_to_id.get(
                row.get("tafsir_block_id"), row.get("tafsir_block_id")
            )
            payload = {c: row.get(c) for c in ALL_COLUMNS}
            payload.update(
                {
                    "id": new_chunk_id,
                    "tafsir_block_id": new_block_id,
                    "chunk": row.get("chunk"),
                    "created_at": row.get("created_at") or _now_ts(),
                }
            )
            conn.execute(chunk_insert, payload)

        conn.execute(text("PRAGMA foreign_keys=ON"))


def bulk_insert_tafsir(engine, section_table, block_table, chunk_table, records):
    """
    Persist a batch of parsed Tafsir rows.
    Each record is expected to be a dict containing:
      - id: desired primary key for the section row (pre-assigned in the caller)
      - text: the extracted tafsir block text to parse/insert
    """
    rows = [r for r in records if r and r.get("text")]
    if not rows:
        return

    section_cols = ", ".join(["id"] + ALL_COLUMNS + [NORMALIZED_COL, "created_at"])
    section_vals = ", ".join(
        [":id"] + [f":{c}" for c in ALL_COLUMNS] + [f":{NORMALIZED_COL}", ":created_at"]
    )
    section_stmt = text(
        f"INSERT INTO {section_table} ({section_cols}) VALUES ({section_vals})"
    )

    block_stmt = text(
        f"INSERT INTO {block_table} (tafsir_section_id, block) VALUES (:tafsir_section_id, :block)"
    )

    chunk_cols = ", ".join(ALL_COLUMNS + ["created_at"])
    chunk_vals = ", ".join(f":{c}" for c in ALL_COLUMNS + ["created_at"])
    chunk_stmt = text(
        f"INSERT INTO {chunk_table} (tafsir_block_id, chunk, {chunk_cols}) VALUES (:tafsir_block_id, :chunk, {chunk_vals})"
    )

    block_total = 0
    chunk_total = 0
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        for record in rows:
            raw = record["text"]
            section_id = record["id"]

            section_row = extract_nested_data(raw)
            section_row["id"] = section_id
            section_row[NORMALIZED_COL] = _normalize_to_string(raw)
            section_row["created_at"] = _now_ts()
            conn.execute(section_stmt, section_row)

            block_texts = extract_section_blocks(raw)

            for block_text in block_texts:
                block_result = conn.execute(
                    block_stmt,
                    {"tafsir_section_id": section_id, "block": block_text},
                )
                block_id = block_result.lastrowid
                if block_id is None:
                    block_id = conn.exec_driver_sql(
                        "SELECT last_insert_rowid()"
                    ).scalar()

                block_total += 1
                chunk_rows = extract_block_chunks(block_text, block_id)

                if chunk_rows:
                    ts = _now_ts()
                    for row in chunk_rows:
                        row["created_at"] = ts
                    conn.execute(chunk_stmt, chunk_rows)
                    chunk_total += len(chunk_rows)

    print(f"Erfolg: {len(rows)} Datensätze in {section_table} eingefügt.")
    print(f"Erfolg: {block_total} Blocks in {block_table} eingefügt.")
    print(f"Erfolg: {chunk_total} Chunks in {chunk_table} eingefügt.")


DBS = ["katheer", "waseet", "tabary", "sa3dy", "qortoby", "baghawy"]
DEFAULT_START_ID = None


def automate_gemini(
    db,
    start_id=DEFAULT_START_ID,
    exact_ids=None,
    repair=False,
    output_db_path=None,
    multiple_models: bool = False,
):
    """
    Default: verarbeitet alle Zeilen ab ``start_id`` (inkl.) wie bisher.
    Neu: Wenn ``exact_ids`` angegeben ist, werden ausschließlich diese IDs
    (einzeln) abgearbeitet – nützlich für gezielte Nachträge / Rollbacks.
    In diesem Modus wird automatisch eine Sidecar-DB
    ``<db>_annotated_subset.sqlite3`` verwendet (oder der per ``output_db_path``
    übergebene Pfad), um die Hauptdatenbank nicht zu verändern.
    """

    # Multi-model fan-out (only meaningful when a finite ID list is provided)
    if multiple_models and not exact_ids:
        print("--multiple-models erfordert eine ID-Liste (--exact-id). Flag wird ignoriert.")

    if multiple_models and exact_ids:
        models = _discover_model_configs()
        if not models:
            raise RuntimeError(
                "Keine GEMINI_* Modellkonfiguration gefunden. "
                "Erwarte Variablen wie GEMINI_1_API_KEY, GEMINI_1_MODEL_ID, GEMINI_1_CACHE_NAME."
            )
        for label, cfg_fields in models:
            print(f"\n=== Modell {label} wird verarbeitet ===")
            _apply_model_env(cfg_fields)
            per_model_out = _resolve_output_db_path(
                db, exact_ids, output_db_path, model_suffix=None if label == "default" else label
            )
            _run_single_model(
                db=db,
                start_id=start_id,
                exact_ids=exact_ids,
                repair=repair,
                output_db_path=per_model_out,
                model_label=label,
            )
        return

    _reset_gemini_client()

    _run_single_model(
        db=db,
        start_id=start_id,
        exact_ids=exact_ids,
        repair=repair,
        output_db_path=_resolve_output_db_path(db, exact_ids, output_db_path),
        model_label="default",
    )


def _run_single_model(db, start_id, exact_ids, repair, output_db_path, model_label):
    # Ensure logs for this model go into a dedicated JSON file to avoid key clashes
    _set_log_target(model_label)

    i = 0
    db_path_in = cfg.BOOKS_DIR / f"{db}.sqlite3"
    db_path_out = Path(output_db_path)

    engine_in = create_engine(f"sqlite:///{db_path_in}")
    metadata_in = MetaData()
    tafsir_table = Table(db, metadata_in, autoload_with=engine_in)

    engine_out = create_engine(
        f"sqlite:///{db_path_out}", connect_args={"check_same_thread": False}
    )
    target_table = f"tafsir_analysis_{db}"
    block_table = f"{target_table}_blocks"
    chunk_table = f"{target_table}_chunks"
    setup_analysis_tables(engine_out, target_table, block_table, chunk_table)
    # Keine destruktiven Rebuilds mehr; nur non-destruktive Backfills.
    backfill_normalized(engine_out, target_table)

    with engine_out.connect() as connection:
        existing_max = connection.execute(
            text(f"SELECT MAX(id) FROM {target_table}")
        ).scalar()
        max_id = (existing_max or 0) + 1
        # IDs sollen 1:1 zum Quell-Korpus bleiben; daher nutzen wir den Quell-id.
        start_id = start_id if start_id is not None else max_id
    pending_futures = []

    def wait_for_pending():
        for future in pending_futures:
            future.result()
        pending_futures.clear()

    with engine_in.connect() as connection, ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        def fetch_rows(conn, offset=0):
            return conn.execute(
                select(tafsir_table.c.id, tafsir_table.c.text)
                .where(text("text IS NOT NULL AND text != ''"))
                .where(tafsir_table.c.id >= start_id)
                .order_by(tafsir_table.c.id)
                .offset(offset)
            )

        expected_rows = (
            connection.execute(
                text(
                    f"SELECT COUNT(*) FROM {db} "
                    "WHERE text IS NOT NULL AND text != '' AND id >= :start"
                ),
                {"start": start_id},
            ).scalar()
            or 0
        )
        total_processed = 0
        skipped_rows = 0

        def process_rows(rows_iterable):
            nonlocal i, total_processed, skipped_rows
            batch = []
            processed = 0

            for row in rows_iterable:
                i += 1
                row_id = row[0]
                original_text = row[1]
                if not original_text:
                    continue

                attempts = 0
                while attempts <= GUARD_MAX_RETRIES:
                    attempts += 1

                    prompt = " ".join(
                        original_text.replace("<p>", " ").replace("</p>", " ").split()
                    )

                    print("Warte auf Antwort von Gemini (API)...")
                    _write_log(
                        "logs/progress.log",
                        "waiting for response",
                        row_id=row_id,
                    )
                    extracted_text = None
                    try:
                        extracted_text = request_gemini_response(prompt)
                    except Exception as exc:  # noqa: BLE001
                        _write_log(
                            "logs/errors.log",
                            f"gemini request failed ({exc.__class__.__name__}: {exc})",
                            row_id=row_id,
                        )

                    if not extracted_text:
                        print(
                            "Keine Antwort von der Gemini API erhalten; erneut versuchen."
                        )
                        _write_log(
                            "logs/progress.log",
                            f"empty response, attempt={attempts}",
                            row_id=row_id,
                        )
                        if attempts <= GUARD_MAX_RETRIES:
                            time.sleep(1.0)
                            continue
                        skipped_rows += 1
                        processed += 1
                        break

                    cleaned_text = clean_wrapped_xml(extracted_text) or extracted_text
                    source_tokens = _normalize_guard_tokens(original_text)
                    response_tokens = _normalize_guard_tokens(cleaned_text)
                    guard = evaluate_guard(
                        source_tokens,
                        response_tokens,
                        pre_normalized=True,
                    )
                    decision = guard["decision"]
                    print(
                        f"Guard: coverage={guard['token_coverage']:.2f}, overlap={guard['ngram_overlap']:.2f}, decision={decision}"
                    )
                    _log_guard_entry(
                        row_id=row_id,
                        guard=guard,
                        attempt=attempts,
                        response=cleaned_text,
                        decision=decision,
                        model_label=model_label,
                    )

                    if decision == "retry":
                        if attempts <= GUARD_MAX_RETRIES:
                            print(
                                f"Guard verlangt Wiederholung (Versuch {attempts}/{GUARD_MAX_RETRIES + 1})."
                            )
                            continue
                        print(
                            "Maximale Guard-Versuche erreicht; Eintrag wird übersprungen."
                        )
                        _log_guard_entry(
                            row_id=row_id,
                            guard=guard,
                            attempt=attempts,
                            response=cleaned_text,
                            decision="skip",
                            model_label=model_label,
                        )
                        insert_empty_section(engine_out, target_table, row_id)
                        skipped_rows += 1
                        processed += 1
                        break

                    if decision == "log":
                        if attempts <= GUARD_MAX_RETRIES:
                            print(
                                f"Guard im Grenzbereich; Wiederholung (Versuch {attempts}/{GUARD_MAX_RETRIES + 1})."
                            )
                            _write_log(
                                "logs/progress.log",
                                f"guard borderline, retry attempt={attempts}",
                                row_id=row_id,
                            )
                            continue
                        print(
                            "Guard im Grenzbereich; maximale Versuche erreicht – Eintrag wird protokolliert, aber nicht eingefügt."
                        )
                        _log_guard_entry(
                            row_id=row_id,
                            guard=guard,
                            attempt=attempts,
                            response=cleaned_text,
                            decision="skip",
                            model_label=model_label,
                        )
                        insert_empty_section(engine_out, target_table, row_id)
                        skipped_rows += 1
                        processed += 1
                        break

                    # Persist section rows with a fixed starting PK that increments per accepted batch
                    record = {
                        # kritischer Fix: ID immer aus dem Quell-Korpus übernehmen,
                        # damit Guard-Skips die Alignment nicht verschieben.
                        "id": row_id,
                        "text": cleaned_text,
                        NORMALIZED_COL: (
                            " ".join(response_tokens) if response_tokens else None
                        ),
                    }
                    batch.append(record)
                    processed += 1
                    total_processed += 1

                    if i % 5 == 0:
                        cleanup_cycle(
                            batch,
                            executor,
                            engine_out,
                            target_table,
                            block_table,
                            chunk_table,
                            flush_batch=True,
                            pending_futures=pending_futures,
                            prefetched_record=record,
                            append_to_batch=False,
                        )

                    print("Antwort gespeichert. Nächster Durchgang...")
                    _write_log(
                        "logs/responses.log",
                        f"response accepted, total_processed={total_processed}",
                        row_id=row_id,
                    )
                    break

            return batch, processed

        # --- Modus 1: gezielte Einzel-IDs ----------------------------------
        if exact_ids:
            ids = sorted({int(x) for x in exact_ids})
            if not ids:
                print("Keine gültigen IDs angegeben; Abbruch.")
                return

            rows_to_process = []
            with engine_out.connect() as out_conn:
                for target_id in ids:
                    already = out_conn.execute(
                        text(f"SELECT 1 FROM {target_table} WHERE id = :id"),
                        {"id": target_id},
                    ).fetchone()
                    if already:
                        print(f"Überspringe ID {target_id}: bereits vorhanden.")
                        continue

                    row = connection.execute(
                        select(tafsir_table.c.id, tafsir_table.c.text)
                        .where(text("text IS NOT NULL AND text != ''"))
                        .where(tafsir_table.c.id == target_id)
                    ).fetchone()

                    if row:
                        rows_to_process.append(row)
                    else:
                        print(
                            f"Keine Quellzeile für ID {target_id} gefunden – übersprungen."
                        )

            batch, processed = process_rows(rows_to_process)

            if batch:
                pending_futures.append(
                    executor.submit(
                        bulk_insert_tafsir,
                        engine_out,
                        target_table,
                        block_table,
                        chunk_table,
                        list(batch),
                    )
                )

            wait_for_pending()
            print(
                f"Einzelmodus: {processed}/{len(rows_to_process)} IDs verarbeitet (db={db})."
            )
            return

        offset = 0
        while True:
            wait_for_pending()
            rows = fetch_rows(connection, offset=offset)
            batch, processed_this_run = process_rows(rows)

            if batch:
                pending_futures.append(
                    executor.submit(
                        bulk_insert_tafsir,
                        engine_out,
                        target_table,
                        block_table,
                        chunk_table,
                        list(batch),
                    )
                )

            if processed_this_run == 0:
                print(
                    "Keine zusätzlichen Einträge verarbeitet; stoppe, um Endlosschleife zu vermeiden."
                )
                break

            offset += processed_this_run

        wait_for_pending()

    with engine_out.connect() as out_conn:
        final_saved_rows = (
            out_conn.execute(text(f"SELECT COUNT(*) FROM {target_table}")).scalar() or 0
        )
    print(
        f"Abgeschlossen [{model_label}]: {db} ({final_saved_rows}/{expected_rows} Einträge im Ziel)."
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Automatisierte Tafsir-Annotation via Gemini API."
    )
    parser.add_argument(
        "--db",
        dest="dbs",
        action="append",
        choices=DBS,
        default=None,
        help="Nur diese DB verarbeiten (kann mehrfach angegeben werden). "
        "Ohne Angabe werden alle verarbeitet.",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=DEFAULT_START_ID,
        help="Start-ID für den normalen Lauf (Standard: erster fehlender Eintrag).",
    )
    parser.add_argument(
        "--exact-id",
        dest="exact_ids",
        action="append",
        type=int,
        help="Nur die angegebenen IDs verarbeiten (kann mehrfach angegeben werden).",
    )
    parser.add_argument(
        "--out-db",
        dest="out_db",
        help="Optional expliziter Pfad für die Ausgabedatenbank.",
    )
    parser.add_argument(
        "--multiple-models",
        dest="multiple_models",
        action="store_true",
        help="Bei ID-Listen: alle in .env definierten GEMINI_* Modelle nacheinander verwenden "
        "und pro Modell eine eigene Zieldatenbank schreiben.",
    )

    args = parser.parse_args()
    targets = args.dbs if args.dbs else DBS

    try:
        for db_name in targets:
            automate_gemini(
                db_name,
                start_id=args.start_id,
                exact_ids=args.exact_ids,
                output_db_path=args.out_db,
                multiple_models=args.multiple_models,
            )
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
