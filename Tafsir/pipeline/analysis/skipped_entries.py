#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import duckdb
from Tafsir.config import paths as cfg    

# === CONFIG ===
SQLITE_PATH = str(cfg.ANNOTATED_DIR / "katheer_annotated.sqlite3")
TABLE_NAME = "tafsir_analysis_katheer"           
ID_COLUMN = "id"                           
LOG_PATH = "missing_ids.log"          

def main() -> int:
    if not os.path.isfile(SQLITE_PATH):
        sys.stderr.write(f"SQLite-Datei nicht gefunden: {SQLITE_PATH}\n")
        return 2

    con = duckdb.connect(database=":memory:")

    try:
        con.execute("INSTALL sqlite_scanner;")
        con.execute("LOAD sqlite_scanner;")

        query = f"""
            WITH ids AS (
                SELECT CAST({ID_COLUMN} AS BIGINT) AS id
                FROM sqlite_scan(?, ?)
                WHERE {ID_COLUMN} IS NOT NULL
            ),
            bounds AS (
                SELECT MIN(id) AS min_id, MAX(id) AS max_id FROM ids
            ),
            missing AS (
                SELECT s.i AS missing_id
                FROM bounds b
                JOIN generate_series(b.min_id, b.max_id) s(i) ON TRUE
                LEFT JOIN ids ON ids.id = s.i
                WHERE ids.id IS NULL
                ORDER BY s.i
            )
            SELECT missing_id FROM missing;
        """

        rows = con.execute(query, [SQLITE_PATH, TABLE_NAME]).fetchall()
        missing_ids = [r[0] for r in rows]

        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write(f"sqlite_path={SQLITE_PATH}\n")
            f.write(f"table={TABLE_NAME}\n")
            f.write(f"id_column={ID_COLUMN}\n")
            f.write(f"missing_count={len(missing_ids)}\n")
            for mid in missing_ids:
                f.write(f"{mid}\n")

        return 0

    except Exception as e:
        sys.stderr.write(f"Fehler: {e}\n")
        return 1
    finally:
        try:
            con.close()
        except Exception:
            pass

if __name__ == "__main__":
    raise SystemExit(main())
