import duckdb
from pathlib import Path

TARGET_DB = Path("/app/daten.sqlite3")
REF_DB = Path("/app/Tafsir/tafsir_books/katheer.sqlite3")


con = duckdb.connect()

# Attach reference and target DBs
con.execute(f"ATTACH '{REF_DB}' AS ref (TYPE SQLITE);")
con.execute(f"ATTACH '{TARGET_DB}' AS tgt (TYPE SQLITE);")

# All tables in daten.sqlite3 (SQLite attaches as schema 'main' inside DuckDB)
tables = [
    row[0]
    for row in con.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
          AND table_type = 'BASE TABLE'
        """
    ).fetchall()
    if row[0].startswith("katheer_annotated_subset_")
]

for table in tables:
    # add column if missing
    try:
        con.execute(f'ALTER TABLE tgt."{table}" ADD COLUMN src_text TEXT;')
    except Exception:
        pass  # column already exists

    # update from reference DB via id
    con.execute(
        f'''
        UPDATE tgt."{table}" AS s
        SET src_text = r.text
        FROM ref.katheer AS r
        WHERE s.id = r.id;
        '''
    )

con.execute("DETACH tgt;")
con.execute("DETACH ref;")
con.close()
