import time
from concurrent.futures import ThreadPoolExecutor
import pyautogui
import pyperclip
import regex
from bs4 import BeautifulSoup
from sqlalchemy import MetaData, Table, create_engine, select, text
from ocr import OCRWatcher
from PROMPT_PREFIX import PROMPT_PREFIX
from TAGS import PRIMARY_TAGS, SECONDARY_TAGS, REMAINING_ALL_TAGS
from pathlib import Path

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


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
ALL_COLUMNS = ALL_TAGS + [RAW_COL]

RX_RECURSIVE = regex.compile(
    r"(?s)<(?P<tag>" + "|".join(ALL_TAGS) + r")>(?P<content>(?:[^<]|(?R))*)</(?P=tag)>"
)

BLOCK_TAG = "tafsir_section_block"
CHUNK_TAG = "tafsir_chunk"
RX_BLOCK = regex.compile(rf"(?s)<{BLOCK_TAG}>(?P<content>(?:[^<]|(?R))*)</{BLOCK_TAG}>")
RX_CHUNK = regex.compile(rf"(?s)<{CHUNK_TAG}>(?P<content>(?:[^<]|(?R))*)</{CHUNK_TAG}>")

watcher_a = OCRWatcher(17, 146, 712, 842)
watcher_b = OCRWatcher(38, 2, 83, 35)

GUARD_NGRAM_SIZE = 3
GUARD_MAX_RETRIES = 2


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


def _ngram_set(tokens, n):
    if not tokens:
        return set()
    n = max(1, min(n, len(tokens)))
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def evaluate_guard(source_text, response_text, n=GUARD_NGRAM_SIZE):
    """
    Lightweight guard to detect technical failures (missing/partial/other text).
    Returns metrics and decision: pass | retry | log.
    """
    source_tokens = _normalize_guard_tokens(source_text)
    response_tokens = _normalize_guard_tokens(response_text)

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

    if token_coverage >= 0.85 and ngram_overlap >= 0.6:
        decision = "pass"
    elif token_coverage < 0.7 or ngram_overlap < 0.4:
        decision = "retry"
    else:
        decision = "log"

    return {
        "token_coverage": token_coverage,
        "ngram_overlap": ngram_overlap,
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
    prefetched_text=None,
    append_to_batch=True,
):
    """
    Fetch the current response, optionally flush the batch, then hard-refresh and reset
    devtools/clipboard to keep the browser snappy.
    """
    extracted_text = (
        prefetched_text if prefetched_text is not None else get_code_from_devtools()
    )
    if append_to_batch and extracted_text:
        batch.append(extracted_text)

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

    pyautogui.click(x=220, y=1053)
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "shift", "r")
    watcher_window_reload = watcher_b.run()
    if watcher_window_reload is True:
        pyautogui.moveTo(x=1274, y=940, duration=0.15)
        time.sleep(0.5)
        pyautogui.click()
        pyautogui.moveTo(x=1377, y=869, duration=0.15)
        time.sleep(0.5)
        pyautogui.click()
        print("Antwort gespeichert. Nächster Durchgang...")
        _write_log("logs/responses.log", "cycle refreshed, response stored")
    pyperclip.copy("")  # free clipboard buffer
    time.sleep(0.5)
    pyautogui.click(x=220, y=1053)
    return extracted_text


def get_code_from_devtools():
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    # ChatGPT
    # search_term = "overflow-visible! px-0!"
    search_term = "code-container formatted ng-tns-"
    pyperclip.copy(search_term)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1)
    pyautogui.moveTo(x=1699, y=969)  # go first
    time.sleep(0.5)
    pyautogui.click()
    pyautogui.moveTo(x=814, y=124, duration=0.15)
    time.sleep(0.5)
    pyautogui.click()
    pyautogui.moveTo(x=1000, y=121, duration=0.15)
    time.sleep(0.5)
    pyautogui.click()
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "shift", "i")
    time.sleep(0.3)
    pyautogui.click(x=220, y=1053)

    html_content = pyperclip.paste()
    soup = BeautifulSoup(html_content, "html.parser")
    if soup:
        return soup.get_text()
    return ""


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


def bulk_insert_tafsir(engine, section_table, block_table, chunk_table, raw_texts):
    rows = [t for t in raw_texts if t]
    if not rows:
        return

    section_cols = ", ".join(ALL_COLUMNS)
    section_vals = ", ".join(f":{c}" for c in ALL_COLUMNS)
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
        for raw in rows:
            section_row = extract_nested_data(raw)
            section_result = conn.execute(section_stmt, section_row)
            section_id = section_result.lastrowid
            if section_id is None:
                section_id = conn.exec_driver_sql("SELECT last_insert_rowid()").scalar()

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

    print(f"Erfolg: {len(rows)} Datensätze in {section_table} eingefügt.")
    print(f"Erfolg: {block_total} Blocks in {block_table} eingefügt.")
    print(f"Erfolg: {chunk_total} Chunks in {chunk_table} eingefügt.")
    _write_log(
        "logs/bulk_insert.log",
        f"{section_table}: sections={len(rows)}, "
        f"blocks={block_total}, chunks={chunk_total}",
    )


DBS = ["katheer", "waseet", "tabary", "sa3dy", "qortoby", "baghawy"]
DEFAULT_START_ID = 149


def automate_gemini(db, start_id=DEFAULT_START_ID, exact_ids=None):
    """
    Default: verarbeitet alle Zeilen ab ``start_id`` (inkl.) wie bisher.
    Neu: Wenn ``exact_ids`` angegeben ist, werden ausschließlich diese IDs
    (einzeln) abgearbeitet – nützlich für gezielte Nachträge / Rollbacks.
    """

    i = 0
    db_path_in = (
        f"/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books/{db}.sqlite3"
    )
    db_path_out = f"/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books_annotated/{db}_annotated.sqlite3"

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
                original_text = row[0]
                if not original_text:
                    continue

                attempts = 0
                while attempts <= GUARD_MAX_RETRIES:
                    attempts += 1
                    extracted_text = None
                    pyperclip.copy(
                        PROMPT_PREFIX
                        + " ".join(
                            original_text.replace("<p>", " ")
                            .replace("</p>", " ")
                            .split()
                        )
                    )
                    pyautogui.click(x=220, y=1053)  # open browser

                    # ChatGPT
                    # pyautogui.click(x=597, y=933)
                    # Gemini
                    time.sleep(0.5)
                    pyautogui.hotkey("ctrl", "end")
                    time.sleep(1.0)

                    # 1. Maus stabil auf Zielposition bringen und Fokus erzwingen
                    for _ in range(3):
                        pyautogui.moveTo(927, 891, duration=0.15)
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
                    pyautogui.moveTo(x=733, y=351, duration=0.15)
                    pyautogui.click()
                    pyautogui.hotkey("ctrl", "end")
                    time.sleep(2)
                    pyautogui.moveTo(x=972, y=99, duration=0.15)
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

                    guard = evaluate_guard(original_text, extracted_text)
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

                    batch.append(extracted_text)
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
                            prefetched_text=extracted_text,
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
                        select(tafsir_table.c.text)
                        .where(text("text IS NOT NULL AND text != ''"))
                        .where(tafsir_table.c.id == target_id)
                    ).fetchone()

                    if row:
                        rows_to_process.append(row)
                    else:
                        print(f"Keine Quellzeile für ID {target_id} gefunden – übersprungen.")

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
                select(tafsir_table.c.text)
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
    targets = args.dbs or DBS

    try:
        for db_name in targets:
            automate_gemini(db_name, start_id=args.start_id, exact_ids=args.exact_ids)
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
