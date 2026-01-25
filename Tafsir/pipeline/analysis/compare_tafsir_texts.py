#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Set, Tuple

import regex
import unicodedata

RX_PREFIX_STANDALONE = regex.compile(r"(?<!\S)(و|ف|ب|ك|ل|س|لي)\s+(?=\S)", regex.UNICODE)
TAG_RE = re.compile(r"<[^>]+>")
ARABIC_DIACRITICS = regex.compile(
    r"[\p{M}\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]+"
)
TATWEEL = "\u0640"
NON_ARABIC = regex.compile(r"[^\p{Arabic} ]+")
MULTI_SPACE = regex.compile(r"\s+")


def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = ARABIC_DIACRITICS.sub("", text)
    text = text.replace(TATWEEL, "")
    text = text.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ى": "ي",
                "ئ": "ي",
                "ؤ": "و",
                "ة": "ه",
                "ء": "",
                "گ": "ك",
                "ڤ": "ف",
                "پ": "ب",
                "چ": "ج",
            }
        )
    )
    text = NON_ARABIC.sub(" ", text)
    text = MULTI_SPACE.sub(" ", text).strip()
    text = RX_PREFIX_STANDALONE.sub(r"\1", text)
    return unicodedata.normalize("NFKC", text)


def normalize(text: str | None) -> List[str]:
    text = text or ""
    text = TAG_RE.sub(" ", text)
    text = " ".join(text.split())
    text = normalize_arabic(text)
    return text.split(" ") if text else []


def compare_sequences(src_words: List[str], ann_words: List[str]) -> List[str]:
    if src_words == ann_words:
        return []

    diffs: List[str] = []
    matcher = SequenceMatcher(a=src_words, b=ann_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            diffs.append("delete")
        elif tag == "insert":
            diffs.append("insert")
        elif tag == "replace":
            diffs.append("replace")
    return diffs


def _derive_paths(db_path: Path, table_name: str) -> Tuple[Path, str, str]:
    book = table_name.replace("tafsir_analysis_", "")
    base_dir = db_path.parent.parent
    source_db = base_dir / "tafsir_books" / f"{book}.sqlite3"
    annotated_column = "extracted_text_full"
    return source_db, book, annotated_column


def get_anomalies(db_path: str, table_name: str) -> List[int]:
    """
    Returns IDs whose token-by-token comparison differs.
    """
    annotated_db = Path(db_path)
    source_db, source_table, annotated_column = _derive_paths(annotated_db, table_name)
    mismatched: Set[int] = set()

    with sqlite3.connect(source_db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("ATTACH DATABASE ? AS ann", (str(annotated_db),))
        rows = conn.execute(
            f"""
            SELECT
                src.id   AS source_id,
                src.text AS source_text,
                ann.id   AS annotated_id,
                ann.{annotated_column} AS annotated_text
            FROM {source_table} src
            INNER JOIN ann.{table_name} ann
                ON src.id = ann.id
            ORDER BY src.id
            """
        )
        for row in rows:
            src_words = normalize(row["source_text"])
            ann_words = normalize(row["annotated_text"])
            if compare_sequences(src_words, ann_words):
                mismatched.add(int(row["source_id"]))

    return list(mismatched)


def compare_tables(book: str, base_dir: Path) -> None:
    annotated_db = base_dir / "tafsir_books_annotated" / f"{book}_annotated.sqlite3"
    anomalies = get_anomalies(str(annotated_db), f"tafsir_analysis_{book}")
    print(f"Rows with mismatches: {len(anomalies)}")
    if anomalies:
        print("IDs:", anomalies)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: compare_tafsir_texts.py <book>")
        sys.exit(1)

    compare_tables(sys.argv[1].lower(), Path(__file__).resolve().parent.parent)
