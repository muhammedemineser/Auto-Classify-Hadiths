"""
Fill ``extracted_text_normalized`` for rows where it is NULL/empty by normalizing
the XML in ``extracted_text_full``.

Usage:
    python -m Tafsir.pipeline.analysis.data_cleaning.backfill_normalized katheer
    python -m Tafsir.pipeline.analysis.data_cleaning.backfill_normalized \
        /path/to/db.sqlite3 --table tafsir_analysis_katheer
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import create_engine, text

from Tafsir.pipeline.gemini_common import backfill_normalized as do_backfill
from Tafsir.pipeline.analysis.data_cleaning.reconcile_mismatches import (
    _derive_paths,
)


def resolve(db_arg: str, table_arg: str | None):
    """Resolve book name or explicit path to (db_path, table_name)."""
    candidate = Path(db_arg)
    if candidate.is_file():
        if not table_arg:
            raise SystemExit("When passing a DB file, --table is required.")
        return candidate, table_arg
    # treat as logical book name
    annotated_db = (
        Path(__file__).resolve().parents[4]
        / "Tafsir"
        / "tafsir_books_annotated"
        / f"{db_arg}_annotated.sqlite3"
    )
    if not annotated_db.exists():
        raise SystemExit(f"Annotated DB not found: {annotated_db}")
    table = table_arg or f"tafsir_analysis_{db_arg}"
    return annotated_db, table


def main():
    parser = argparse.ArgumentParser(
        description="Backfill extracted_text_normalized from extracted_text_full"
    )
    parser.add_argument(
        "db",
        help="Logical book name (e.g. katheer) or explicit path to annotated DB.",
    )
    parser.add_argument(
        "--table",
        help="Optional table name; defaults to tafsir_analysis_<db> for logical names.",
    )
    args = parser.parse_args()

    db_path, table_name = resolve(args.db, args.table)
    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    do_backfill(engine, table_name)
    with engine.connect() as conn:
        remaining = conn.execute(text(f"SELECT * FROM {table_name} ")).scalar()
    print(
        f"Backfill complete for {table_name}. Remaining empty normalized rows: {remaining}"
    )


if __name__ == "__main__":
    main()
