#!/usr/bin/env python3
from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import List
import regex
import unicodedata
from blocks_to_xml_ai import evaluate_guard


RX_PREFIX_STANDALONE = regex.compile(r"(?<!\S)(و|ف|ب|ك|ل|س|لي)\s+(?=\S)", regex.UNICODE)

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

    text = RX_PREFIX_STANDALONE.sub(r"\1", text)

    # 7) Finale Unicode-Rekomposition
    text = unicodedata.normalize("NFKC", text)

    return text


def normalize(text: str | None) -> List[str]:
    text = text or ""
    text = TAG_RE.sub(" ", text)
    text = " ".join(text.split())
    text = normalize_arabic(text)
    return text.split(" ") if text else []


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

            result = evaluate_guard(src_words, ann_words)
            for k, v in result.items():
                if v == "retry" or v == "log":
                    print(f"{k}: {v}")
                    print(
                        f"\nRow id {row['source_id']} (source={row['source_id']}, annotated={row['annotated_id']}):"
                    )
                    print(f"  - {row['source_text']}")
                    print(f"  - {row['annotated_text']}")
                    mismatches += 1

        print(f"\nCompared {total} rows")
        print(f"Rows with mismatches: {mismatches}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: compare_tafsir.py <book>")
        sys.exit(1)

    compare_tables(sys.argv[1].lower(), Path(__file__).resolve().parent.parent)
