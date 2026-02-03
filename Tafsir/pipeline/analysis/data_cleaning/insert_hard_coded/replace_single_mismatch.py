from sqlalchemy import MetaData, Table, create_engine, text
from bs4 import BeautifulSoup
import regex

from Tafsir.pipeline.gemini_gui.PROMPT_PREFIX import PROMPT_PREFIX
from Tafsir.pipeline.gemini_gui.TAGS import (
    PRIMARY_TAGS,
    SECONDARY_TAGS,
    REMAINING_ALL_TAGS,
)

"""
replace number 89 with number to replace and hard_coded_response with your hard coded response
"""
ALL_TAGS = (
    list(PRIMARY_TAGS.keys())
    + list(SECONDARY_TAGS.keys())
    + list(REMAINING_ALL_TAGS.keys())
)
RAW_COL = "extracted_text_full"
ALL_COLUMNS = ALL_TAGS + [RAW_COL]

BLOCK_TAG = "tafsir_section_block"
CHUNK_TAG = "tafsir_chunk"


# --- DEINE HELPER FUNKTIONEN (Unverändert) ---
def extract_nested_data(xml):
    row = {tag: None for tag in ALL_TAGS}
    if not xml:
        row[RAW_COL] = xml
        return row
    soup = BeautifulSoup(xml, "html.parser")
    for tag in ALL_TAGS:
        elements = soup.find_all(tag)
        if elements:
            row[tag] = "\n".join([e.decode_contents() for e in elements])
    row[RAW_COL] = xml
    return row


def extract_section_blocks(xml):
    if not xml:
        return []
    soup = BeautifulSoup(xml, "html.parser")
    blocks = soup.find_all(BLOCK_TAG)
    if blocks:
        return [str(block) for block in blocks]
    return [xml]


def extract_block_chunks(block_xml, tafsir_block_id):
    if not block_xml:
        return []
    soup = BeautifulSoup(block_xml, "html.parser")
    chunks = soup.find_all(CHUNK_TAG)
    chunk_rows = []
    if not chunks:
        chunk_data = extract_nested_data(block_xml)
        chunk_data["tafsir_block_id"] = tafsir_block_id
        chunk_data["chunk"] = block_xml
        return [chunk_data]
    for chunk in chunks:
        chunk_text = str(chunk)
        chunk_data = extract_nested_data(chunk_text)
        chunk_data["tafsir_block_id"] = tafsir_block_id
        chunk_data["chunk"] = chunk_text
        chunk_rows.append(chunk_data)
    return chunk_rows


# --- DIE KORRIGIERTE UPDATE FUNKTION ---
def update_specific_tafsir_entry(
    engine, section_table, block_table, chunk_table, raw_text, target_id=89
):
    if not raw_text:
        return

    section_cols = "id, " + ", ".join(ALL_COLUMNS)
    section_vals = ":id, " + ", ".join(f":{c}" for c in ALL_COLUMNS)

    section_stmt = text(
        f"INSERT OR REPLACE INTO {section_table} ({section_cols}) VALUES ({section_vals})"
    )
    delete_old_blocks_stmt = text(
        f"DELETE FROM {block_table} WHERE tafsir_section_id = :target_id"
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

        # 1. Cleanup
        conn.execute(delete_old_blocks_stmt, {"target_id": target_id})

        # 2. Section Update (ID erzwingen)
        section_row = extract_nested_data(raw_text)
        section_row["id"] = target_id
        conn.execute(section_stmt, section_row)

        # 3. Blocks & Chunks einfügen
        block_texts = extract_section_blocks(raw_text)
        for block_text in block_texts:
            res = conn.execute(
                block_stmt, {"tafsir_section_id": target_id, "block": block_text}
            )
            block_id = (
                res.lastrowid
                if res.lastrowid
                else conn.exec_driver_sql("SELECT last_insert_rowid()").scalar()
            )

            block_total += 1
            chunk_rows = extract_block_chunks(block_text, block_id)
            if chunk_rows:
                conn.execute(chunk_stmt, chunk_rows)
                chunk_total += len(chunk_rows)

    print(
        f"SUCCESS: ID {target_id} updated. Blocks: {block_total}, Chunks: {chunk_total}"
    )


# --- HAUPTPROGRAMM (Nur einmal ausführen) ---

# Der XML String, den du einfügen willst
hard_coded_response = """<tafsir_section>
  <tafsir_section_block>
    <tafsir_chunk>
      <isnad>وقال <source>محمد بن إسحاق</source> : حدثني محمد ، عن سعيد أو عكرمة عن ابن عباس : </isnad>
    </tafsir_chunk>
    <tafsir_chunk>
      <quran_verse>( والذين آمنوا وعملوا الصالحات أولئك أصحاب الجنة هم فيها خالدون ) </quran_verse>
    </tafsir_chunk>
    <tafsir_chunk>
      <opinions_of_scholars>أي من آمن بما كفرتم به ، وعمل بما تركتم من دينه ، فلهم الجنة خالدين فيها . </opinions_of_scholars>
    </tafsir_chunk>
    <tafsir_chunk>
      <opinions_of_scholars>
        <theological_points>يخبرهم أن الثواب بالخير والشر مقيم على أهله ، لا انقطاع له أبدا .</theological_points>
      </opinions_of_scholars>
    </tafsir_chunk>
  </tafsir_section_block>
</tafsir_section>"""

# Wähle hier die EINE Datenbank aus, in der der Fehler ist (z.B. katheer)
target_db = "katheer"
db_path_out = f"/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books_annotated/{target_db}_annotated.sqlite3"

target_table = f"tafsir_analysis_{target_db}"
block_table = f"{target_table}_blocks"
chunk_table = f"{target_table}_chunks"

if __name__ == "__main__":
    engine_out = create_engine(f"sqlite:///{db_path_out}")

    print(f"Repariere ID 89 in {target_db}...")

    update_specific_tafsir_entry(
        engine_out,
        target_table,
        block_table,
        chunk_table,
        hard_coded_response,
        target_id=89,
    )
