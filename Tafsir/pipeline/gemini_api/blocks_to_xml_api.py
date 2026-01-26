import os
import sys
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
    exported GEMINI_* variables. Only sets keys that are currently missing.
    """
    env_path = cfg.CONFIG_DIR / ".env"
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


def _write_log(path, entry):
    log_path = Path(path).expanduser()
    if log_path.is_absolute():
        anchor = log_path.anchor
        if anchor:
            log_path = log_path.relative_to(anchor)
    target_path = REPO_ROOT / log_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


_GEMINI_CLIENT = None
_GENAI_TYPES = None
MODEL_ID = os.getenv("GEMINI_MODEL_ID")
GEMINI_CACHE_NAME = os.getenv("GEMINI_CACHE_NAME")

# Globale Variablen initialisieren
_GEMINI_CLIENT = None
_GENAI_TYPES = None

# Diese müssen irgendwo definiert sein (z.B. in deiner .env oder global)
GEMINI_CACHE_NAME = os.getenv("GEMINI_CACHE_NAME")
MODEL_ID = os.getenv("GEMINI_MODEL_ID")


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

    if not GEMINI_CACHE_NAME:
        raise RuntimeError("GEMINI_CACHE_NAME ist nicht gesetzt.")
    if not MODEL_ID:
        raise RuntimeError("MODEL_ID ist nicht gesetzt.")

    try:
        config = types.GenerateContentConfig(
            cached_content=GEMINI_CACHE_NAME,
        )

        response = client.models.generate_content(
            model=MODEL_ID,
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
    _write_log(
        "logs/bulk_insert.log",
        f"{section_table}: sections={len(rows)}, "
        f"blocks={block_total}, chunks={chunk_total}",
    )


DBS = ["katheer", "waseet", "tabary", "sa3dy", "qortoby", "baghawy"]
DEFAULT_START_ID = None


def automate_gemini(db, start_id=DEFAULT_START_ID, exact_ids=None, repair=False):
    """
    Default: verarbeitet alle Zeilen ab ``start_id`` (inkl.) wie bisher.
    Neu: Wenn ``exact_ids`` angegeben ist, werden ausschließlich diese IDs
    (einzeln) abgearbeitet – nützlich für gezielte Nachträge / Rollbacks.
    """

    i = 0
    db_path_in = cfg.BOOKS_DIR / f"{db}.sqlite3"
    db_path_out = cfg.ANNOTATED_DIR / f"{db}_annotated.sqlite3"

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

    def fetch_rows(conn, offset=0):
        return conn.execute(
            select(tafsir_table.c.id, tafsir_table.c.text)
            .where(text("text IS NOT NULL AND text != ''"))
            .where(tafsir_table.c.id >= start_id)
            .order_by(tafsir_table.c.id)
            .offset(offset)
        )

    with engine_in.connect() as connection, ThreadPoolExecutor(
        max_workers=4
    ) as executor:
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

                if exact_ids is not None and row_id not in exact_ids:
                    continue

                attempts = 0
                while attempts <= GUARD_MAX_RETRIES:
                    attempts += 1

                    prompt = " ".join(
                        original_text.replace("<p>", " ").replace("</p>", " ").split()
                    )

                    print("Warte auf Antwort von Gemini (API)...")
                    _write_log("logs/progress.log", f"row={i}: waiting for response")
                    extracted_text = None
                    try:
                        extracted_text = request_gemini_response(prompt)
                    except Exception as exc:  # noqa: BLE001
                        _write_log(
                            "logs/errors.log",
                            f"row={i}: gemini request failed ({exc.__class__.__name__}: {exc})",
                        )

                    if not extracted_text:
                        print(
                            "Keine Antwort von der Gemini API erhalten; erneut versuchen."
                        )
                        _write_log(
                            "logs/progress.log",
                            f"row={i}: empty response, attempt={attempts}",
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
                    log_line = (
                        f"row={i}, decision={decision}, "
                        f"coverage={guard['token_coverage']:.2f}, "
                        f"overlap={guard['ngram_overlap']:.2f}"
                    )
                    if decision == "retry":
                        log_line += f", attempt={attempts}"
                    _write_log("logs/guard.log", log_line)

                    if decision == "retry":
                        if attempts <= GUARD_MAX_RETRIES:
                            print(
                                f"Guard verlangt Wiederholung (Versuch {attempts}/{GUARD_MAX_RETRIES + 1})."
                            )
                            continue
                        print(
                            "Maximale Guard-Versuche erreicht; Eintrag wird übersprungen."
                        )
                        _write_log(
                            "logs/guard.log",
                            f"row={i}, decision=skip, reason=guard_limit, "
                            f"coverage={guard['token_coverage']:.2f}, "
                            f"overlap={guard['ngram_overlap']:.2f}",
                        )
                        insert_empty_section(engine_out, target_table, row_id)
                        skipped_rows += 1
                        processed += 1
                        break

                    if decision == "log":
                        print(
                            "Guard im Grenzbereich; Eintrag wird protokolliert, aber nicht eingefügt."
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
                        f"row={i}: response accepted, total_processed={total_processed}",
                    )
                    break

            return batch, processed

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
                _write_log(
                    "logs/progress.log",
                    f"{db}: no additional records processed this run",
                )
                break

            offset += processed_this_run

        wait_for_pending()

    with engine_out.connect() as out_conn:
        final_saved_rows = (
            out_conn.execute(text(f"SELECT COUNT(*) FROM {target_table}")).scalar() or 0
        )
    print(f"Abgeschlossen: {db} ({final_saved_rows}/{expected_rows} Einträge im Ziel).")
    _write_log(
        "logs/progress.log",
        f"{db}: finished {final_saved_rows}/{expected_rows} entries stored",
    )


if __name__ == "__main__":
    try:
        for db_name in DBS:
            automate_gemini(db_name)
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
