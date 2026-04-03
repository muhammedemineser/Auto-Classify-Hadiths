from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List


def get_anomalies(db_path: str, table_name: str) -> List[int]:
    """
    Return ids that appear more than once in the given table.
    No files are written; pure in-memory query.
    """
    query = f"""
        SELECT id
        FROM {table_name}
        GROUP BY id
        HAVING COUNT(id) > 1
    """
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query).fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="List ids that are duplicated in a table."
    )
    parser.add_argument(
        "db",
        help="Logical book name (e.g. katheer) or explicit path to annotated DB.",
    )
    parser.add_argument(
        "--table",
        help="Optional table name; defaults to tafsir_analysis_<db>",
    )
    args = parser.parse_args()

    # Resolve paths/names like other modules do
    if Path(args.db).is_file():
        annotated_db = Path(args.db)
        if not args.table:
            raise SystemExit("When passing an explicit DB path, --table is required.")
        table_name = args.table
    else:
        annotated_db = (
            Path(__file__).resolve().parents[4]
            / "tafsir_books_annotated"
            / f"{args.db}_annotated.sqlite3"
        )
        table_name = args.table or f"tafsir_analysis_{args.db}"

    if not annotated_db.exists():
        raise SystemExit(f"Annotated DB not found: {annotated_db}")

    anomalies = get_anomalies(str(annotated_db), table_name)
    print(json.dumps(anomalies, ensure_ascii=False, indent=2))
