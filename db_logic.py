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

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

ALL_TAGS = (
    list(PRIMARY_TAGS.keys())
    + list(SECONDARY_TAGS.keys())
    + list(REMAINING_ALL_TAGS.keys())
)
RAW_COL = "extracted_text_full"
ALL_COLUMNS = ALL_TAGS + [RAW_COL]

# Regex caused the issue because (?R) expects the inner content to match the Block pattern recursively.
# Since Chunks are inside Blocks but are NOT Blocks, the regex failed, resulting in the fallback (whole XML).
# We switched to BeautifulSoup for reliable parsing of the hierarchy.

BLOCK_TAG = "tafsir_section_block"
CHUNK_TAG = "tafsir_chunk"

watcher_a = OCRWatcher(17, 146, 712, 842)
watcher_b = OCRWatcher(38, 2, 83, 35)


def cleanup_cycle(
    batch,
    executor,
    engine_out,
    section_table,
    block_table,
    chunk_table,
    flush_batch=False,
):
    extracted_text = get_code_from_devtools()
    if extracted_text:
        batch.append(extracted_text)

    if flush_batch and batch:
        executor.submit(
            bulk_insert_tafsir,
            engine_out,
            section_table,
            block_table,
            chunk_table,
            list(batch),
        )
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
    pyperclip.copy("")
    time.sleep(0.5)
    pyautogui.click(x=220, y=1053)
    return extracted_text


def get_code_from_devtools():
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    search_term = "code-container formatted ng-tns-"
    pyperclip.copy(search_term)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1)
    pyautogui.moveTo(x=1420, y=975)
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
            # 1. Insert Section
            section_row = extract_nested_data(raw)
            section_result = conn.execute(section_stmt, section_row)
            section_id = section_result.lastrowid
            if section_id is None:
                section_id = conn.exec_driver_sql("SELECT last_insert_rowid()").scalar()

            # 2. Extract and Insert Blocks
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

                # 3. Extract and Insert Chunks
                chunk_rows = extract_block_chunks(block_text, block_id)

                if chunk_rows:
                    conn.execute(chunk_stmt, chunk_rows)
                    chunk_total += len(chunk_rows)

    print(f"Erfolg: {len(rows)} Datensätze in {section_table} eingefügt.")
    print(f"Erfolg: {block_total} Blocks in {block_table} eingefügt.")
    print(f"Erfolg: {chunk_total} Chunks in {chunk_table} eingefügt.")


DBS = ["katheer", "waseet", "tabary", "sa3dy", "qortoby", "baghawy"]


def automate_gemini(db):
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

    with engine_in.connect() as connection, ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        results = connection.execute(select(tafsir_table.c.text))
        batch = []

        for row in results:
            i += 1
            extracted_text = None

            # Using loop index to trigger mock data cycle for testing
            if i % 5 == 0:
                extracted_text = cleanup_cycle(
                    batch,
                    executor,
                    engine_out,
                    target_table,
                    block_table,
                    chunk_table,
                    flush_batch=True,
                )
            else:
                # Standard logic to collect mock data into batch
                cleanup_cycle(
                    batch,
                    executor,
                    engine_out,
                    target_table,
                    block_table,
                    chunk_table,
                    flush_batch=False,
                )

        # Process remaining batch
        if batch:
            executor.submit(
                bulk_insert_tafsir,
                engine_out,
                target_table,
                block_table,
                chunk_table,
                list(batch),
            )


if __name__ == "__main__":
    try:
        for db_name in DBS:
            automate_gemini(db_name)
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
