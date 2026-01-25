from __future__ import annotations

import sqlite3
from typing import List


def get_anomalies(db_path: str, table_name: str) -> List[int]:
    """
    Return ids whose quran_verse is NULL.
    """
    query = f"SELECT DISTINCT id FROM {table_name} WHERE quran_verse IS NULL"
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(query).fetchall()
    return [int(row[0]) for row in rows if row[0] is not None]


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="List ids whose quran_verse column is NULL."
    )
    parser.add_argument("db_path", help="Path to SQLite database.")
    parser.add_argument(
        "table_name", help="Table to scan, e.g. tafsir_analysis_katheer"
    )
    args = parser.parse_args()

    anomalies = get_anomalies(args.db_path, args.table_name)
    print(json.dumps(anomalies, ensure_ascii=False, indent=2))
