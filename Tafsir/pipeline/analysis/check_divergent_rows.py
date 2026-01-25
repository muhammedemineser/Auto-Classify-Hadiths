#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import List, Set

import regex
import unicodedata

from Tafsir.pipeline.gemini_gui.blocks_to_xml_gui import evaluate_guard


RX_PREFIX_STANDALONE = regex.compile(r"(?<!\S)(و|ف|ب|ك|ل|س|لي)\s+(?=\S)", regex.UNICODE)
TAG_RE = re.compile(r"<[^>]+>")
NORMALIZED_COL = "extracted_text_normalized"

# ── Harakat, Quranische Zeichen, kombinierende Marks
ARABIC_DIACRITICS = regex.compile(
    r"[\p{M}\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]+"
)

# Tatweel (Kashida)
TATWEEL = "\u0640"

# Alles außer arabischen Buchstaben + Leerzeichen
NON_ARABIC = regex.compile(r"[^\p{Arabic} ]+")

# Mehrfach-Leerzeichen
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


def _derive_paths(db_path: Path, table_name: str) -> tuple[Path, str, str]:
    """
    Derive source DB path and column names from annotated DB path + table name.
    """
    book = table_name.replace("tafsir_analysis_", "")
    base_dir = db_path.parent.parent  # .../tafsir_books_annotated -> ../..
    source_db = base_dir / "tafsir_books" / f"{book}.sqlite3"
    annotated_column = "extracted_text_full"
    return source_db, book, annotated_column


def _ensure_normalized_column(conn: sqlite3.Connection, table_name: str) -> None:
    cols = [
        row[1]
        for row in conn.execute(f"PRAGMA ann.table_info('{table_name}')").fetchall()
    ]
    if NORMALIZED_COL not in cols:
        conn.execute(f"ALTER TABLE ann.{table_name} ADD COLUMN {NORMALIZED_COL} TEXT")


def get_anomalies(
    db_path: str,
    table_name: str,
    start_id: int | None = None,
    end_id: int | None = None,
) -> List[int]:
    """
    Uses evaluate_guard to flag divergences between source and annotated text.
    Returns list of source ids whose comparison decision is 'retry' or 'log'.
    """
    annotated_db = Path(db_path)
    source_db, source_table, annotated_column = _derive_paths(annotated_db, table_name)

    mismatched_ids: Set[int] = set()
    with sqlite3.connect(source_db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("ATTACH DATABASE ? AS ann", (str(annotated_db),))
        _ensure_normalized_column(conn, table_name)

        where_clauses = []
        params: list[int] = []
        if start_id is not None:
            where_clauses.append("src.id >= ?")
            params.append(start_id)
        if end_id is not None:
            where_clauses.append("src.id <= ?")
            params.append(end_id)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        rows = conn.execute(
            f"""
            SELECT
                src.id   AS source_id,
                src.text AS source_text,
                ann.id   AS annotated_id,
                ann.{annotated_column} AS annotated_text,
                ann.{NORMALIZED_COL} AS annotated_normalized
            FROM {source_table} src
            INNER JOIN ann.{table_name} ann
                ON src.id = ann.id
            {where_sql}
            ORDER BY src.id
            """,
            params,
        )

        pending_updates = []
        for row in rows:
            src_words = normalize(row["source_text"])
            ann_norm = row["annotated_normalized"]
            ann_words = ann_norm.split() if ann_norm else []
            if not ann_words:
                ann_words = normalize(row["annotated_text"])
                pending_updates.append(
                    {"id": row["annotated_id"], "norm": " ".join(ann_words)}
                )
            result = evaluate_guard(src_words, ann_words, pre_normalized=True)
            decision = result.get("decision", "retry")
            if decision in {"retry", "log"}:
                mismatched_ids.add(int(row["source_id"]))

        if pending_updates:
            conn.executemany(
                f"UPDATE ann.{table_name} SET {NORMALIZED_COL} = :norm WHERE id = :id",
                pending_updates,
            )
            conn.commit()

    return list(mismatched_ids)


def compare_tables(
    book: str, base_dir: Path, start_id: int | None = None, end_id: int | None = None
) -> None:
    annotated_db = (
        base_dir / "Tafsir" / "tafsir_books_annotated" / f"{book}_annotated.sqlite3"
    )
    anomalies = get_anomalies(
        str(annotated_db), f"tafsir_analysis_{book}", start_id=start_id, end_id=end_id
    )
    if start_id is not None or end_id is not None:
        print(
            f"Filtered IDs from {start_id if start_id is not None else '-inf'} to "
            f"{end_id if end_id is not None else '+inf'} -> "
            f"{len(anomalies)} mismatches"
        )
    else:
        print(f"Rows with mismatches: {len(anomalies)}")
    if anomalies:
        print("IDs:", anomalies)


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    book_name = "katheer"
    start_arg: int | None = None
    end_arg: int | None = None

    if args:
        try:
            # If the first argument is a number, treat positional args as start/end IDs.
            start_arg = int(args[0])
            if len(args) >= 2:
                end_arg = int(args[1])
        except ValueError:
            # Otherwise first argument is the book name.
            book_name = args[0].lower()
            if len(args) >= 2:
                start_arg = int(args[1])
            if len(args) >= 3:
                end_arg = int(args[2])

    compare_tables(
        book_name,
        Path(__file__).resolve().parents[4],
        start_id=start_arg,
        end_id=end_arg or start_arg,
    )
