import os
import duckdb
from pathlib import Path

SRC_DIR = Path("/app/2.5FLASH")
REF_DB  = "/app/tools/ML/quran.db"
LOGS    = "/app/2.5FLASH/structured_logs_2.5FLASH.json"

OUT_DIR = Path("/app/output_csvs")

OUT_DIR.mkdir(parents=True, exist_ok=True)

def model_label_from_db(db_path: Path) -> str:
    # e.g. katheer_annotated_subset_3FLASH.sqlite3 -> 3FLASH
    return db_path.stem.split("_")[-1].replace("flash", "FLASH").replace("pro", "BASE")

con = duckdb.connect()

# Reference DB anhängen
con.execute(f"""
ATTACH '{REF_DB}' AS ref (TYPE SQLITE);
""")

# Structured logs als {id, log_json} verfügbar machen
con.execute(f"""
CREATE OR REPLACE VIEW logs AS
SELECT
  CAST(j.key AS INTEGER) AS id,
  j.value AS log_json
FROM (
  SELECT json
  FROM read_json_objects('{LOGS}')
) t,
json_each(t.json) AS j;
""")

for i, db_path in enumerate(sorted(SRC_DIR.glob("*.sqlite3"))):
    alias = f"src{i}"
    out_csv = OUT_DIR / f"{db_path.stem}.csv"
    model_label = model_label_from_db(db_path)

    con.execute(f"""
    ATTACH '{db_path}' AS {alias} (TYPE SQLITE);
    """)

    con.execute(f"""
    COPY (
        SELECT
            s.*,
            r.*,
            (
              -- export all guard entries for this model_label, preserving order
              SELECT to_json(array_agg(g.value ORDER BY TRY_CAST(g.key AS INTEGER)))
              FROM json_each(l.log_json -> 'guard') AS g
              WHERE g.value ->> 'model_label' = '{model_label}'
            ) AS guard_entry
        FROM {alias}.tafsir_analysis_katheer AS s
        JOIN ref.ayah_metadata_new AS r
          ON s.id = r.id
        LEFT JOIN logs AS l
          ON s.id = l.id
    )
    TO '{out_csv}'
    (HEADER, DELIMITER ',');
    """)

    con.execute(f"DETACH {alias};")

con.close()
