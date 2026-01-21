#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Tuple
import regex
import unicodedata


TAG_RE = re.compile(r"<[^>]+>")

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

    # 1) Unicode-Kompatibilitätsnormalisierung
    text = unicodedata.normalize("NFKD", text)

    # 2) Entferne Harakat / Diakritika
    text = ARABIC_DIACRITICS.sub("", text)

    # 3) Entferne Tatweel
    text = text.replace(TATWEEL, "")

    # 4) Orthographische Vereinheitlichung
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

    # 5) Entferne alles Nicht-Arabische (Zahlen, Satzzeichen, Latin etc.)
    text = NON_ARABIC.sub(" ", text)

    # 6) Leerzeichen normalisieren
    text = MULTI_SPACE.sub(" ", text).strip()

    # 7) Finale Unicode-Rekomposition
    text = unicodedata.normalize("NFKC", text)

    return text


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

        src = " ".join(src_words[i1:i2])
        ann = " ".join(ann_words[j1:j2])

        if tag == "delete":
            diffs.append(f"Missing words: '{src}'")
        elif tag == "insert":
            diffs.append(f"Extra words: '{ann}'")
        elif tag == "replace":
            diffs.append(f"Order/divergence mismatch: '{src}' -> '{ann}'")

    return diffs


def compare_tables(book: str, base_dir: Path) -> None:
    source_db = base_dir / "tafsir_books" / f"{book}.sqlite3"
    annotated_db = base_dir / "tafsir_books_annotated" / f"{book}_annotated.sqlite3"

    source_table = book
    annotated_table = f"tafsir_analysis_{book}"
    annotated_column = "extracted_text_full"

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
            INNER JOIN ann.{annotated_table} ann
                ON src.id = ann.id
            ORDER BY src.id
            """
        )

        total = 0
        mismatches = 0

        for row in rows:
            total += 1
            src_words = normalize(row["source_text"])
            ann_words = normalize(row["annotated_text"])

            diffs = compare_sequences(src_words, ann_words)
            if diffs:
                mismatches += 1
                print(
                    f"\nRow id {row['source_id']} (source={row['source_id']}, annotated={row['annotated_id']}):"
                )
                for d in diffs:
                    print(f"  - {d}")

        print(f"\nCompared {total} rows")
        print(f"Rows with mismatches: {mismatches}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: compare_tafsir.py <book>")
        sys.exit(1)

    compare_tables(sys.argv[1].lower(), Path(__file__).resolve().parent.parent)
