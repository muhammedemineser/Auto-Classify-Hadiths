import duckdb
from pathlib import Path

SRC_DB = Path("/app/csv_tools/FINAL_CSVS/katheer_annotated_most_frequent.sqlite3")
OUT_ROOT = Path("/app/FINAL_CSVS/Frequent_Subsets")

OUT_ROOT.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute(f"ATTACH '{SRC_DB}' AS tgt (TYPE SQLITE);")

tables = [
    row[0]
    for row in con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
          AND table_type = 'BASE TABLE'
          AND table_name LIKE 'most_frequent%'
        """
    ).fetchall()
]

for table in tables:
    out_csv = OUT_ROOT / f"{table}.csv"
    con.execute(
        f"""
        COPY (
            SELECT * FROM tgt."{table}"
        )
        TO '{out_csv}'
        (HEADER, DELIMITER ',');
        """
    )

con.execute("DETACH tgt;")
con.close()
