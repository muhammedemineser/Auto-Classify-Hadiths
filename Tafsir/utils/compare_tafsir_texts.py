#!/usr/bin/env python3
"""
Compare raw tafsir text with its annotated extraction row by row.

The script aligns rows by `id`, strips all tags from both texts, normalizes
whitespace, and surfaces any sequence-sensitive differences (missing words,
extra words, order changes, or other divergences).
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Comparison:
    source_id: int
    annotated_id: int
    differences: List[str]
    normalized_source: str
    normalized_annotated: str


def validate_identifier(value: str, label: str) -> str:
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", value):
        raise ValueError(f"Invalid {label}: {value!r}")
    return value


def get_columns(db_path: Path, table: str) -> List[str]:
    validate_identifier(table, "table name")
    with sqlite3.connect(db_path) as conn:
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table});")]


def resolve_annotated_column(
    annotated_db: Path, annotated_table: str, override: str | None
) -> str:
    columns = set(get_columns(annotated_db, annotated_table))
    if not columns:
        raise ValueError(
            f"Table {annotated_table!r} not found in {annotated_db} (no columns discovered)."
        )

    candidates: List[str] = []
    if override:
        candidates.append(override)
    candidates.extend(["extracted_full_text", "extracted_text_full"])

    for name in candidates:
        if name in columns:
            return validate_identifier(name, "annotated column")

    raise ValueError(
        f"Annotated column not found. Candidates {candidates} not in available columns: "
        f"{', '.join(sorted(columns))}"
    )


def normalize_text(text: str | None) -> Tuple[str, List[str]]:
    """
    Remove tags, collapse whitespace, and return both the normalized string and word list.
    """
    without_tags = TAG_RE.sub(" ", text or "")
    normalized = " ".join(without_tags.split())
    words = normalized.split(" ") if normalized else []
    return normalized, words


def compare_words(
    source_words: Sequence[str], annotated_words: Sequence[str]
) -> List[str]:
    if source_words == annotated_words:
        return []

    differences: List[str] = []
    matcher = SequenceMatcher(a=source_words, b=annotated_words)

    # SequenceMatcher gives ordered operations so we can classify each difference.
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        src_slice = source_words[i1:i2]
        ann_slice = annotated_words[j1:j2]

        if tag == "delete":
            differences.append(
                f"Missing in annotated @src[{i1}:{i2}]: \"{' '.join(src_slice)}\""
            )
        elif tag == "insert":
            differences.append(
                f"Extra in annotated @ann[{j1}:{j2}]: \"{' '.join(ann_slice)}\""
            )
        elif tag == "replace":
            if src_slice and ann_slice and Counter(src_slice) == Counter(ann_slice):
                differences.append(
                    f"Order mismatch src[{i1}:{i2}] vs ann[{j1}:{j2}]: "
                    f"\"{' '.join(src_slice)}\" -> \"{' '.join(ann_slice)}\""
                )
            else:
                differences.append(
                    f"Divergence src[{i1}:{i2}] vs ann[{j1}:{j2}]: "
                    f"\"{' '.join(src_slice)}\" -> \"{' '.join(ann_slice)}\""
                )

    if not differences and source_words != annotated_words:
        differences.append(
            "Texts differ after normalization, but no granular diff found."
        )

    return differences


def iter_matched_rows(
    source_db: Path,
    annotated_db: Path,
    source_table: str,
    annotated_table: str,
    annotated_column: str,
    limit: int | None,
) -> Iterable[sqlite3.Row]:
    validate_identifier(source_table, "source table")
    validate_identifier(annotated_table, "annotated table")
    validate_identifier(annotated_column, "annotated column")

    limit_clause = " LIMIT ?" if limit is not None else ""
    params: Tuple[int, ...] = (limit,) if limit is not None else ()

    with sqlite3.connect(source_db) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("ATTACH DATABASE ? AS annotated_db", (str(annotated_db),))
        query = f"""
        SELECT
            src.id AS source_id,
            src.text AS source_text,
            ann.id AS annotated_id,
            ann.{annotated_column} AS annotated_text
        FROM {source_table} AS src
        INNER JOIN annotated_db.{annotated_table} AS ann ON src.id = ann.id
        ORDER BY src.id{limit_clause}
        """
        yield from conn.execute(query, params)


def load_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare tafsir source text to annotated extracted text row by row."
    )
    parser.add_argument(
        "book",
        help="Tafsir key (e.g. baghawy, katheer). Points to tafsir_books/<book>.sqlite3.",
    )
    parser.add_argument(
        "--source-db",
        type=Path,
        help="Override path to source DB (defaults to tafsir_books/<book>.sqlite3).",
    )
    parser.add_argument(
        "--annotated-db",
        type=Path,
        help="Override path to annotated DB (defaults to tafsir_books_annotated/<book>_annotated.sqlite3).",
    )
    parser.add_argument(
        "--source-table",
        help="Override source table name (defaults to <book>).",
    )
    parser.add_argument(
        "--annotated-table",
        help="Override annotated table name (defaults to tafsir_analysis_<book>).",
    )
    parser.add_argument(
        "--annotated-column",
        help="Override annotated column (defaults to detected extracted_full_text/extracted_text_full).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of rows compared (for quick spot checks).",
    )
    parser.add_argument(
        "--show-text",
        action="store_true",
        help="Include normalized source and annotated text in mismatch output.",
    )
    parser.add_argument(
        "--fail-on-diff",
        action="store_true",
        help="Exit with status 1 if any mismatches are found.",
    )
    return parser.parse_args()


def main() -> None:
    args = load_args()

    base_dir = Path(__file__).resolve().parent.parent
    book = args.book.lower()

    source_db = args.source_db or base_dir / "tafsir_books" / f"{book}.sqlite3"
    annotated_db = (
        args.annotated_db
        or base_dir / "tafsir_books_annotated" / f"{book}_annotated.sqlite3"
    )
    source_table = args.source_table or book
    annotated_table = args.annotated_table or f"tafsir_analysis_{book}"
    annotated_column = resolve_annotated_column(
        annotated_db, annotated_table, args.annotated_column
    )

    comparisons: List[Comparison] = []
    total_rows = 0

    for row in iter_matched_rows(
        source_db=source_db,
        annotated_db=annotated_db,
        source_table=source_table,
        annotated_table=annotated_table,
        annotated_column=annotated_column,
        limit=args.limit,
    ):
        total_rows += 1
        normalized_src, src_words = normalize_text(row["source_text"])
        normalized_ann, ann_words = normalize_text(row["annotated_text"])

        diffs = compare_words(src_words, ann_words)
        if diffs:
            comparisons.append(
                Comparison(
                    source_id=row["source_id"],
                    annotated_id=row["annotated_id"],
                    differences=diffs,
                    normalized_source=normalized_src,
                    normalized_annotated=normalized_ann,
                )
            )

    mismatch_count = len(comparisons)
    print(
        f"Compared {total_rows} matched rows from {source_db} ({source_table}.text) "
        f"against {annotated_db} ({annotated_table}.{annotated_column})."
    )
    print(f"Rows with mismatches: {mismatch_count}")

    for comp in comparisons:
        print(
            f"\nRow id {comp.source_id} (source id={comp.source_id}, annotated id={comp.annotated_id}):"
        )
        for diff in comp.differences:
            print(f"  - {diff}")
        if args.show_text:
            print(f"  source:    {comp.normalized_source}")
            print(f"  annotated: {comp.normalized_annotated}")

    if args.fail_on_diff and mismatch_count:
        sys.exit(1)


if __name__ == "__main__":
    main()
