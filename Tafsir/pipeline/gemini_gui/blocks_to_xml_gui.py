import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, UTC
from pathlib import Path

try:
    import pyautogui
except ModuleNotFoundError:  # lightweight stub for test environments

    class _Dummy:
        def __getattr__(self, _):
            return lambda *a, **k: None

    pyautogui = _Dummy()
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0

try:
    import pyperclip
except ModuleNotFoundError:  # pragma: no cover - handled by tests

    class _DummyClip:
        def copy(self, *_args, **_kwargs): ...
        def paste(self):
            return ""

    pyperclip = _DummyClip()

import regex
from bs4 import BeautifulSoup
from sqlalchemy import MetaData, Table, create_engine, select, text, inspect

from Tafsir.config import paths as cfg
from .ocr import OCRWatcher
from .PROMPT_PREFIX import PROMPT_PREFIX
from .TAGS import PRIMARY_TAGS, SECONDARY_TAGS, REMAINING_ALL_TAGS

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

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


ALL_TAGS = (
    list(PRIMARY_TAGS.keys())
    + list(SECONDARY_TAGS.keys())
    + list(REMAINING_ALL_TAGS.keys())
)
RAW_COL = "extracted_text_full"
NORMALIZED_COL = "extracted_text_normalized"
ALL_COLUMNS = ALL_TAGS + [RAW_COL]

RX_RECURSIVE = regex.compile(
    r"(?s)<(?P<tag>" + "|".join(ALL_TAGS) + r")>(?P<content>(?:[^<]|(?R))*)</(?P=tag)>"
)

BLOCK_TAG = "tafsir_section_block"
CHUNK_TAG = "tafsir_chunk"
RX_BLOCK = regex.compile(rf"(?s)<{BLOCK_TAG}>(?P<content>(?:[^<]|(?R))*)</{BLOCK_TAG}>")
RX_CHUNK = regex.compile(rf"(?s)<{CHUNK_TAG}>(?P<content>(?:[^<]|(?R))*)</{CHUNK_TAG}>")

# Screen/DOM capture regions (pixel coords)
OCR_REGION_RESPONSE = (17, 146, 712, 842)
OCR_REGION_RELOAD = (38, 2, 83, 35)

watcher_a = OCRWatcher(*OCR_REGION_RESPONSE)
watcher_b = OCRWatcher(*OCR_REGION_RELOAD)

# Common screen points (pixel coords)
POINT_OPEN_BROWSER = {"x": 585, "y": 1046}
POINT_FIRST_FIELD = {"x": 1697, "y": 968}
POINT_EDITOR_TOP = {"x": 814, "y": 124}
POINT_EMPTY_CHATSPACE = {"x": 733, "y": 351}
POINT_DEVTOOLS_ELEMENTS = {"x": 972, "y": 99}
POINT_MODEL_SELECT = {"x": 1313, "y": 929}
POINT_WHICH_MODEL = {"x": 1391, "y": 837}
POINT_INPUT_FIELD = {"x": 927, "y": 891}

GUARD_NGRAM_SIZE = 3
GUARD_MAX_RETRIES = 2
GUARD_MIN_LEN_RATIO = 0.5  # min(shorter/longer); protects against huge length drift


def _normalize_guard_tokens(text):
    if not text:
        return []
    if isinstance(text, list):
        text = " ".join(text)
    no_tags = regex.sub(r"<[^>]+>", " ", text)
    normalized = " ".join(no_tags.split()).lower()
    if not normalized:
        return []
    return normalized.split()


def _normalize_to_string(text):
    tokens = _normalize_guard_tokens(text)
    return " ".join(tokens) if tokens else None


def _ngram_set(tokens, n):
    if not tokens:
        return set()
    n = max(1, min(n, len(tokens)))
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _length_ratio(tokens_a, tokens_b):
    """Return shorter/longer length ratio; 0 if any side empty."""
    la, lb = len(tokens_a), len(tokens_b)
    if not la or not lb:
        return 0.0
    shorter, longer = (la, lb) if la <= lb else (lb, la)
    return shorter / longer


def evaluate_guard(
    source_text, response_text, n=GUARD_NGRAM_SIZE, pre_normalized=False
):
    """
    Lightweight guard to detect technical failures (missing/partial/other text).
    Returns metrics and decision: pass | retry | log.
    Now also considers length_ratio (shorter/longer). If length_ratio falls
    below GUARD_MIN_LEN_RATIO, decision becomes retry.
    """

    def _to_tokens(val):
        if pre_normalized:
            if isinstance(val, list):
                return val
            if val is None:
                return []
            if isinstance(val, str):
                return val.split()
            return list(val)
        return _normalize_guard_tokens(val)

    source_tokens = _to_tokens(source_text)
    response_tokens = _to_tokens(response_text)

    if not source_tokens or not response_tokens or []:
        return {"token_coverage": 0.0, "ngram_overlap": 0.0, "decision": "retry"}

    response_set = set(response_tokens)
    hits = sum(1 for t in source_tokens if t in response_set)
    token_coverage = hits / len(source_tokens)

    n = max(1, min(n, len(source_tokens), len(response_tokens)))
    source_ngrams = _ngram_set(source_tokens, n)
    response_ngrams = _ngram_set(response_tokens, n)
    if source_ngrams:
        ngram_overlap = len(source_ngrams & response_ngrams) / len(source_ngrams)
    else:
        ngram_overlap = 0.0

    len_ratio = _length_ratio(source_tokens, response_tokens)

    if token_coverage >= 0.85 and ngram_overlap >= 0.6:
        decision = "pass"
    elif token_coverage < 0.7 or ngram_overlap < 0.4:
        decision = "retry"
    else:
        decision = "log"

    if len_ratio < GUARD_MIN_LEN_RATIO:
        decision = "retry"

    return {
        "token_coverage": token_coverage,
        "ngram_overlap": ngram_overlap,
        "length_ratio": len_ratio,
        "decision": decision,
    }


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
    prefetched_text=None,
    append_to_batch=True,
):
    """
    Fetch the current response, optionally flush the batch, then hard-refresh and reset
    devtools/clipboard to keep the browser snappy.
    """
    record = prefetched_record if prefetched_record is not None else None
    if record is None and prefetched_text is not None:
        record = {"text": prefetched_text}
    if record is None:
        extracted_text = get_code_from_devtools()
        if extracted_text:
            record = {"text": extracted_text}
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

    pyautogui.click(**POINT_OPEN_BROWSER)  # was (220,1053)
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "shift", "r")
    watcher_window_reload = watcher_b.run()
    if watcher_window_reload is True:
        pyautogui.moveTo(**POINT_DEVTOOLS_ELEMENTS, duration=0.15)  # (x=1274, y=940)
        time.sleep(0.5)
        pyautogui.click()
        pyautogui.moveTo(**POINT_WHICH_MODEL, duration=0.15)  # (x=1377, y=869)
        time.sleep(0.5)
        pyautogui.click()
        print("Antwort gespeichert. Nächster Durchgang...")
        _write_log("logs/responses.log", "cycle refreshed, response stored")
    pyperclip.copy("")  # free clipboard buffer
    time.sleep(0.5)
    pyautogui.click(**POINT_OPEN_BROWSER)  # (x=220,1053)
    return record


def get_code_from_devtools():
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    # ChatGPT
    # search_term = "overflow-visible! px-0!"
    search_term = "code-container formatted ng-tns-"
    pyperclip.copy(search_term)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1)
    pyautogui.moveTo(**POINT_FIRST_FIELD)  # go first
    time.sleep(0.5)
    pyautogui.click()
    pyautogui.moveTo(**POINT_EDITOR_TOP, duration=0.15)
    time.sleep(0.5)
    pyautogui.click()
    pyautogui.moveTo(**POINT_EDITOR_TOP, duration=0.15)
    time.sleep(0.5)
    pyautogui.click()
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "shift", "i")
    time.sleep(0.3)
    pyautogui.click(**POINT_OPEN_BROWSER)

    html_content = pyperclip.paste()
    if not html_content or html_content == search_term:
        return ""
    if "<" in html_content and ">" in html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        if soup:
            return soup.get_text()
    return html_content


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


def extract_nested_data(xml):
    """
    Extracts tags using BeautifulSoup to ensure correct parsing even with nested structures.
    Populates all columns (ALL_TAGS) found within the XML fragment.
    """
    row = {tag: None for tag in ALL_TAGS}
    if not xml:
        row[RAW_COL] = xml
        return row

    soup = BeautifulSoup(xml, "html.parser")

    for tag in ALL_TAGS:
        elements = soup.find_all(tag)
        if elements:
            # Concatenate content if multiple tags of the same type exist
            row[tag] = "\n".join([e.decode_contents() for e in elements])

    row[RAW_COL] = xml
    return row


def extract_section_blocks(xml):
    """
    Parses the XML and returns a list of raw string content for each <tafsir_section_block>.
    Uses BeautifulSoup to correctly handle the hierarchy.
    """
    if not xml:
        return []

    soup = BeautifulSoup(xml, "html.parser")
    blocks = soup.find_all(BLOCK_TAG)

    if blocks:
        return [str(block) for block in blocks]

    # Fallback only if no specific blocks found
    return [xml]


def extract_block_chunks(block_xml, tafsir_block_id):
    """
    Extracts <tafsir_chunk> elements from a block string using BeautifulSoup.
    """
    if not block_xml:
        return []

    soup = BeautifulSoup(block_xml, "html.parser")
    chunks = soup.find_all(CHUNK_TAG)

    chunk_rows = []

    if not chunks:
        # Fallback: treat the block content as one chunk data point if no explicit chunks are found
        # but try to extract data columns from the block text itself
        chunk_data = extract_nested_data(block_xml)
        chunk_data["tafsir_block_id"] = tafsir_block_id
        chunk_data["chunk"] = block_xml
        return [chunk_data]

    for chunk in chunks:
        chunk_text = str(chunk)
        # Extract columns (source, hadith, etc.) specifically from this chunk's content
        chunk_data = extract_nested_data(chunk_text)
        chunk_data["tafsir_block_id"] = tafsir_block_id
        chunk_data["chunk"] = chunk_text
        chunk_rows.append(chunk_data)

    return chunk_rows


def _get_table_columns(conn, table_name):
    result = conn.execute(text(f"PRAGMA table_info('{table_name}')"))
    return [row[1] for row in result]


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
    Rebuild tables to enforce primary keys, timestamps and the normalized column.
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
            payload[NORMALIZED_COL] = row.get(NORMALIZED_COL) or _normalize_to_string(
                row.get(RAW_COL)
            )
            payload["created_at"] = row.get("created_at") or _now_ts()
            conn.execute(section_insert, payload)

        block_insert = text(
            f"INSERT INTO {block_table} (id, tafsir_section_id, block) "
            f"VALUES (:id, :tafsir_section_id, :block)"
        )
        block_rowid_to_id = {}
        for row in block_rows:
            old_rowid = row["_rowid"]
            new_block_id = old_rowid
            block_rowid_to_id[old_rowid] = new_block_id
            mapped_section = section_rowid_to_id.get(
                row.get("tafsir_section_id"), row.get("tafsir_section_id")
            )
            conn.execute(
                block_insert,
                {
                    "id": new_block_id,
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
            payload = {c: row.get(c) for c in ALL_COLUMNS}
            payload.update(
                {
                    "id": row.get("id") or row["_rowid"],
                    "tafsir_block_id": block_rowid_to_id.get(
                        row.get("tafsir_block_id"), row.get("tafsir_block_id")
                    ),
                    "chunk": row.get("chunk"),
                    "created_at": row.get("created_at") or _now_ts(),
                }
            )
            conn.execute(chunk_insert, payload)

        conn.execute(text("PRAGMA foreign_keys=ON"))


def backfill_normalized(engine_out, section_table):
    with engine_out.begin() as conn:
        cols = _get_table_columns(conn, section_table)
        if NORMALIZED_COL not in cols:
            conn.execute(
                text(f"ALTER TABLE {section_table} ADD COLUMN {NORMALIZED_COL} TEXT")
            )

        rows = conn.execute(
            text(
                f"SELECT id, {RAW_COL} FROM {section_table} "
                f"WHERE {NORMALIZED_COL} IS NULL OR {NORMALIZED_COL} = ''"
            )
        )
        updates = []
        for row in rows:
            updates.append({"id": row[0], "norm": _normalize_to_string(row[1])})

        if updates:
            conn.execute(
                text(
                    f"UPDATE {section_table} SET {NORMALIZED_COL} = :norm WHERE id = :id"
                ),
                updates,
            )


def bulk_insert_tafsir(engine, section_table, block_table, chunk_table, records):
    """
    Insert tafsir records (strings or dicts) into section/block/chunk tables.
    - If a record is a string, it is treated as raw XML with an auto-generated id.
    - If a record is a dict, it should contain ``text`` (or RAW_COL) and optionally ``id``.
    """
    normalized = []
    for idx, rec in enumerate(records or [], start=1):
        if not rec:
            continue
        if isinstance(rec, str):
            normalized.append({"id": idx, "text": rec})
            continue
        if isinstance(rec, dict):
            text_val = rec.get("text") or rec.get(RAW_COL)
            if not text_val:
                continue
            rec = dict(rec)
            rec.setdefault("id", idx)
            rec["text"] = text_val
            normalized.append(rec)
    if not normalized:
        return

    section_cols = ", ".join(["id"] + ALL_COLUMNS + [NORMALIZED_COL])
    section_vals = ", ".join(
        [":id"] + [f":{c}" for c in ALL_COLUMNS] + [f":{NORMALIZED_COL}"]
    )
    section_stmt = text(
        f"INSERT INTO {section_table} ({section_cols}) VALUES ({section_vals})"
    )

    block_stmt = text(
        f"INSERT INTO {block_table} (tafsir_section_id, block) VALUES (:tafsir_section_id, :block)"
    )

    chunk_cols = ", ".join(ALL_COLUMNS)
    chunk_vals = ", ".join(f":{c}" for c in ALL_COLUMNS)
    chunk_stmt = text(
        f"INSERT INTO {chunk_table} (tafsir_block_id, chunk, {chunk_cols}) VALUES (:tafsir_block_id, :chunk, {chunk_vals})"
    )

    block_total = 0
    chunk_total = 0
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        for record in normalized:
            raw = record.get("text") or record.get(RAW_COL)
            section_id = record.get("id")
            section_row = extract_nested_data(raw)
            section_row["id"] = section_id
            section_row[NORMALIZED_COL] = record.get(
                NORMALIZED_COL
            ) or _normalize_to_string(raw)
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
                    conn.execute(chunk_stmt, chunk_rows)
                    chunk_total += len(chunk_rows)

    print(f"Erfolg: {len(normalized)} Datensätze in {section_table} eingefügt.")
    print(f"Erfolg: {block_total} Blocks in {block_table} eingefügt.")
    print(f"Erfolg: {chunk_total} Chunks in {chunk_table} eingefügt.")
    _write_log(
        "logs/bulk_insert.log",
        f"{section_table}: sections={len(normalized)}, "
        f"blocks={block_total}, chunks={chunk_total}",
    )


DBS = ["katheer", "waseet", "tabary", "sa3dy", "qortoby", "baghawy"]
DEFAULT_DB = "katheer"
DEFAULT_START_ID = None


def automate_gemini(db, start_id=DEFAULT_START_ID, exact_ids=None):
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
    inspector = inspect(engine_in)
    if not inspector.has_table(db):
        print(f"Quelle {db_path_in} enthält keine Tabelle '{db}'. Abbruch.")
        return
    tafsir_table = Table(db, metadata_in, autoload_with=engine_in)

    # Fallback: if source table lacks an explicit id column, create one based on rowid
    if "id" not in tafsir_table.c:
        with engine_in.begin() as conn:
            conn.execute(text(f"ALTER TABLE {db} ADD COLUMN id INTEGER"))
            conn.execute(text(f"UPDATE {db} SET id = rowid WHERE id IS NULL"))
        metadata_in = MetaData()
        tafsir_table = Table(
            db, metadata_in, autoload_with=engine_in, extend_existing=True
        )

    engine_out = create_engine(
        f"sqlite:///{db_path_out}", connect_args={"check_same_thread": False}
    )
    target_table = f"tafsir_analysis_{db}"
    block_table = f"{target_table}_blocks"
    chunk_table = f"{target_table}_chunks"
    setup_analysis_tables(engine_out, target_table, block_table, chunk_table)
    repair_analysis_tables(engine_out, target_table, block_table, chunk_table)
    backfill_normalized(engine_out, target_table)
    with engine_out.connect() as connection:
        existing_max = connection.execute(
            text(f"SELECT MAX(id) FROM {target_table}")
        ).scalar()
        start_id = start_id if start_id is not None else (existing_max or 0) + 1
    pending_futures = []

    def wait_for_pending():
        for future in pending_futures:
            future.result()
        pending_futures.clear()

    with engine_in.connect() as connection, ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        # Initialen Stand der Zieltabelle abrufen, um den Offset korrekt zu berechnen
        # (Behebt das Problem, dass existierende Zeilen, die nicht zum ID-Filter gehören, den Offset verschieben)
        with engine_out.connect() as out_conn:
            initial_out_count = (
                out_conn.execute(text(f"SELECT COUNT(*) FROM {target_table}")).scalar()
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
                source_id, original_text = row
                if not original_text:
                    continue

                attempts = 0
                while attempts <= GUARD_MAX_RETRIES:
                    attempts += 1
                    extracted_text = None
                    pyperclip.copy(
                        "Erinnere dich an die erste Nachricht im Chat um zu wissen was zu tun ist:"
                        + "\n"
                        + " ".join(
                            original_text.replace("<p>", " ")
                            .replace("</p>", " ")
                            .split()
                        ),
                    )
                    pyautogui.click(**POINT_OPEN_BROWSER)  # open browser

                    # ChatGPT
                    # pyautogui.click(x=597, y=933)
                    # Gemini
                    time.sleep(0.5)
                    pyautogui.hotkey("ctrl", "end")
                    time.sleep(1.0)

                    # 1. Maus stabil auf Zielposition bringen und Fokus erzwingen
                    for _ in range(3):
                        pyautogui.moveTo(**POINT_INPUT_FIELD, duration=0.15)
                        pyautogui.click()
                        time.sleep(0.2)

                    # 2. Sicherstellen, dass ein Eingabefeld aktiv ist
                    pyautogui.hotkey("ctrl", "a")
                    time.sleep(0.1)
                    pyautogui.press("backspace")
                    time.sleep(0.2)

                    # 3. Inhalt einfügen
                    pyautogui.hotkey("ctrl", "v")
                    time.sleep(0.6)

                    # 4. Absenden (Enter mehrfach + Delay)
                    for _ in range(2):
                        pyautogui.press("enter")
                        time.sleep(0.2)

                    time.sleep(1.5)

                    print("Warte auf Antwort von Gemini...")
                    _write_log("logs/progress.log", f"row={i}: waiting for response")
                    pyautogui.hotkey("ctrl", "shift", "i")
                    time.sleep(1.5)
                    pyautogui.moveTo(**POINT_EMPTY_CHATSPACE, duration=0.15)
                    pyautogui.click()
                    pyautogui.hotkey("ctrl", "end")
                    time.sleep(2)
                    pyautogui.moveTo(**POINT_DEVTOOLS_ELEMENTS, duration=0.15)
                    pyautogui.click()

                    watcher_gemini_response = watcher_a.run()
                    if watcher_gemini_response is True:
                        extracted_text = get_code_from_devtools()

                    if not extracted_text:
                        print(
                            "Kein Code gefunden. Run wird pausiert, erneuter Versuch startet mit nächstem Durchlauf."
                        )
                        _write_log(
                            "logs/progress.log", f"row={i}: no response detected"
                        )
                        break

                    source_tokens = _normalize_guard_tokens(original_text)
                    response_tokens = _normalize_guard_tokens(extracted_text)
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
                        skipped_rows += 1
                        processed += 1
                        break

                    if decision == "log":
                        print(
                            "Guard im Grenzbereich; Eintrag wird protokolliert, aber nicht eingefügt."
                        )
                        skipped_rows += 1
                        processed += 1
                        break

                    record = {
                        "id": source_id,
                        "text": extracted_text,
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

            return processed

        # --- Modus 1: gezielte Einzel-IDs ----------------------------------
        if exact_ids:
            ids = sorted({int(x) for x in exact_ids})
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

            processed = process_rows(rows_to_process)
            wait_for_pending()
            print(
                f"Einzelmodus: {processed}/{len(rows_to_process)} IDs verarbeitet (db={db})."
            )
            _write_log(
                "logs/progress.log",
                f"{db}: single_ids processed={processed}, requested={len(rows_to_process)}",
            )
            return

        # --- Modus 2: normaler Sequenzlauf ab start_id ----------------------
        expected_rows = (
            connection.execute(
                text(
                    f"SELECT COUNT(*) FROM {db} "
                    "WHERE id >= :start_id AND text IS NOT NULL AND text != ''"
                ),
                {"start_id": start_id},
            ).scalar()
            or 0
        )

        while True:
            wait_for_pending()
            with engine_out.connect() as out_conn:
                saved_rows = (
                    out_conn.execute(
                        text(f"SELECT COUNT(*) FROM {target_table}")
                    ).scalar()
                    or 0
                )

            # Berechne die Anzahl der in DIESER Sitzung (oder passend zum Filter) verarbeiteten Zeilen
            effective_processed_count = max(0, saved_rows - initial_out_count)

            if effective_processed_count >= expected_rows:
                print(
                    f"Bereits vollständig: {db} ({effective_processed_count}/{expected_rows} Einträge in diesem Lauf)."
                )
                _write_log(
                    "logs/progress.log",
                    f"{db}: already complete {effective_processed_count}/{expected_rows}",
                )
                break

            # Der Offset basiert nun nur auf den neu hinzugefügten + übersprungenen Zeilen
            start_offset = effective_processed_count + skipped_rows

            results = connection.execute(
                select(tafsir_table.c.id, tafsir_table.c.text)
                .where(text("id >= :start_id AND text IS NOT NULL AND text != ''"))
                .order_by(text("id"))
                .offset(start_offset)
                .params(start_id=start_id)
            )

            processed_this_run = process_rows(results)

            if processed_this_run == 0:
                print(
                    "Keine zusätzlichen Einträge verarbeitet; stoppe, um Endlosschleife zu vermeiden."
                )
                _write_log(
                    "logs/progress.log",
                    f"{db}: no additional records processed this run",
                )
                break

        wait_for_pending()

    with engine_out.connect() as out_conn:
        final_saved_rows = (
            out_conn.execute(text(f"SELECT COUNT(*) FROM {target_table}")).scalar() or 0
        )
    print(f"Abgeschlossen: {db} ({final_saved_rows} Einträge total im Ziel).")
    _write_log(
        "logs/progress.log",
        f"{db}: finished {final_saved_rows} entries stored",
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Automatisierte Tafsir-Annotation (Gemini/Blocks)."
    )
    parser.add_argument(
        "--db",
        dest="dbs",
        action="append",
        choices=DBS,
        default=None,
        help="Nur diese DB verarbeiten (kann mehrfach angegeben werden)."
        " Ohne Angabe werden alle verarbeitet.",
    )
    parser.add_argument(
        "--start-id",
        type=int,
        default=DEFAULT_START_ID,
        help="Start-ID für den normalen Lauf (Standard: 149).",
    )
    parser.add_argument(
        "--exact-id",
        dest="exact_ids",
        action="append",
        type=int,
        help="Nur die angegebenen IDs verarbeiten (kann mehrfach angegeben werden).",
    )

    args = parser.parse_args()
    if args.dbs:
        targets = args.dbs
    else:
        targets = [DEFAULT_DB]

    try:
        for db_name in targets:
            automate_gemini(db_name, start_id=args.start_id, exact_ids=args.exact_ids)
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
