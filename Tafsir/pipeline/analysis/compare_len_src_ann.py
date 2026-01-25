"""
Utility: 1) erstellt/fuellt eine Spalte ``text_normalisiert`` im SRC-Korpus
mit normalize(text) und 2) berechnet fuer jede SRC-Zeile die ANN-Zeile mit
dem kleinsten Laengen-Delta zu ``extracted_text_normalized``.

Output: Pandas DataFrame mit src_id, ann_id_best, delta_len, len_src, len_ann.
Kein Write in die ANN-DB, nur Read + optional Write der neuen SRC-Spalte.
"""

# %%
from __future__ import annotations

import sqlite3
from pathlib import Path

import duckdb
import pandas as pd

from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize


SRC_DB = Path("Tafsir/tafsir_books/katheer.sqlite3")
ANN_DB = Path("Tafsir/tafsir_books_annotated/katheer_annotated.sqlite3")
SRC_TABLE = "katheer"
ANN_TABLE = "tafsir_analysis_katheer"
SRC_NORM_COL = "text_normalisiert"
ANN_NORM_COL = "extracted_text_normalized"


def ensure_src_normalized(src_db: Path, table: str = SRC_TABLE) -> None:
    """Add+populate src.text_normalisiert with normalized text, if missing/empty."""
    conn = sqlite3.connect(src_db)
    cur = conn.cursor()
    cols = {r[1]: r for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if SRC_NORM_COL not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {SRC_NORM_COL} TEXT")
    rows = cur.execute(
        f"SELECT rowid, text FROM {table} "
        f"WHERE {SRC_NORM_COL} IS NULL OR {SRC_NORM_COL} = ''"
    ).fetchall()
    if rows:
        payload = [(" ".join(normalize(txt)), rid) for rid, txt in rows if txt]
        cur.executemany(
            f"UPDATE {table} SET {SRC_NORM_COL} = ? WHERE rowid = ?",
            payload,
        )
    conn.commit()
    conn.close()


def smallest_length_matches(
    src_db: Path = SRC_DB, ann_db: Path = ANN_DB
) -> pd.DataFrame:
    """
    For each src row, find the ann row with the minimal abs(length) delta
    between normalized texts. Returns a DataFrame.
    """
    con = duckdb.connect()
    con.execute("INSTALL sqlite_scanner;")
    con.execute("LOAD sqlite_scanner;")
    con.execute(f"ATTACH '{src_db}' AS src (TYPE SQLITE);")
    con.execute(f"ATTACH '{ann_db}' AS ann (TYPE SQLITE);")

    query = f"""
    WITH src_norm AS (
        SELECT id AS src_id,
               {SRC_NORM_COL} AS src_norm,
               length({SRC_NORM_COL}) AS len_src
        FROM src.{SRC_TABLE}
        WHERE {SRC_NORM_COL} IS NOT NULL AND {SRC_NORM_COL} != ''
    ),
    ann_norm AS (
        SELECT id AS ann_id,
               {ANN_NORM_COL} AS ann_norm,
               length({ANN_NORM_COL}) AS len_ann
        FROM ann.{ANN_TABLE}
        WHERE {ANN_NORM_COL} IS NOT NULL AND {ANN_NORM_COL} != ''
    ),
    ranked AS (
        SELECT
            s.src_id,
            a.ann_id,
            abs(s.len_src - a.len_ann) AS delta_len,
            s.len_src,
            a.len_ann,
            row_number() OVER (PARTITION BY s.src_id ORDER BY abs(s.len_src - a.len_ann), a.ann_id) AS rn
        FROM src_norm s
        CROSS JOIN ann_norm a
    )
    SELECT src_id, ann_id AS best_ann_id, delta_len, len_src, len_ann
    FROM ranked
    WHERE rn = 1
    ORDER BY delta_len ASC, src_id ASC;
    """
    return con.execute(query).df()


def ensure_ann_normalized(
    ann_db: Path, table: str = ANN_TABLE, raw_col: str = "extracted_text_full"
) -> None:
    """Populate ann.extracted_text_normalized with normalized raw text."""
    conn = sqlite3.connect(ann_db)
    cur = conn.cursor()
    cols = {r[1]: r for r in cur.execute(f"PRAGMA table_info({table})").fetchall()}
    if ANN_NORM_COL not in cols:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ANN_NORM_COL} TEXT")
        cols[ANN_NORM_COL] = True
    rows = cur.execute(
        f"SELECT rowid, {raw_col} FROM {table} "
        f"WHERE {ANN_NORM_COL} IS NULL OR {ANN_NORM_COL} = ''"
    ).fetchall()
    if rows:
        payload = [
            (" ".join(normalize(txt)), rid) for rid, txt in rows if txt
        ]
        cur.executemany(
            f"UPDATE {table} SET {ANN_NORM_COL} = ? WHERE rowid = ?",
            payload,
        )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    ensure_src_normalized(SRC_DB, SRC_TABLE)
    ensure_ann_normalized(ANN_DB, ANN_TABLE)
    df = smallest_length_matches(SRC_DB, ANN_DB)
    pd.set_option("display.max_rows", 20)
    pd.set_option("display.max_columns", None)
    print(df.head(20))
    df
    # %%
