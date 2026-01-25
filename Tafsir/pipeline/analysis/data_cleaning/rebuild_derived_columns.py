"""
Rebuild all derived tag columns from the canonical XML (`extracted_text_full`).

Use this when some rows store derived columns with stray enclosing tags or
mixed formats. The script overwrites the tag columns with the inner contents
extracted from the XML, keeping the XML itself untouched. It does NOT change
blocks/chunks.

Usage:
    python -m Tafsir.pipeline.analysis.data_cleaning.rebuild_derived_columns --db katheer
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Dict, Optional

from bs4 import BeautifulSoup

from Tafsir.pipeline.gemini_gui.TAGS import (
    PRIMARY_TAGS,
    SECONDARY_TAGS,
    REMAINING_ALL_TAGS,
)
from Tafsir.pipeline.analysis.data_cleaning.reconcile_mismatches import (
    _derive_paths,
)

ALL_TAGS = (
    list(PRIMARY_TAGS.keys())
    + list(SECONDARY_TAGS.keys())
    + list(REMAINING_ALL_TAGS.keys())
)
RAW_COL = "extracted_text_full"


def extract_tag_values(xml: Optional[str]) -> Dict[str, Optional[str]]:
    """Return inner XML for each tag; join multiple occurrences with newlines."""
    data = {tag: None for tag in ALL_TAGS}
    if not xml:
        return data
    soup = BeautifulSoup(xml, "html.parser")
    for tag in ALL_TAGS:
        elements = soup.find_all(tag)
        if elements:
            data[tag] = "\n".join(e.decode_contents() for e in elements)
    return data


def rebuild(db: str, table_name: str) -> None:
    db_path = Path(db)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    rows = cur.execute(f"SELECT rowid, {RAW_COL} FROM {table_name}").fetchall()
    set_clause = ", ".join(f"{tag} = ?" for tag in ALL_TAGS)
    payload = []
    for rowid, raw_xml in rows:
        values = extract_tag_values(raw_xml)
        payload.append(tuple(values[tag] for tag in ALL_TAGS) + (rowid,))

    cur.executemany(f"UPDATE {table_name} SET {set_clause} WHERE rowid = ?", payload)
    conn.commit()
    conn.close()


def rebuild_for_book(book: str) -> None:
    annotated_db = (
        Path(__file__).resolve().parents[4]
        / "tafsir_books_annotated"
        / f"{book}_annotated.sqlite3"
    )
    table_name = f"tafsir_analysis_{book}"
    rebuild(str(annotated_db), table_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rebuild derived tag columns from extracted_text_full."
    )
    parser.add_argument(
        "--db",
        default="katheer",
        help="Logical book name, e.g. katheer",
    )
    args = parser.parse_args()
    rebuild_for_book(args.db)
