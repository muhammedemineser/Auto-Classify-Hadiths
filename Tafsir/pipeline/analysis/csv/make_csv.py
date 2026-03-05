import os
import duckdb
from pathlib import Path

SRC_DIR = Path("/app/Tafsir/tafsir_books_annotated")
REF_DB = "/app/tools/ML/quran.db"
LOGS_DIR = Path(os.getenv("STRUCTURED_LOGS_DIR", "/app/Tafsir/logs"))
LOGS_OVERRIDE = os.getenv("STRUCTURED_LOGS_PATH")
OUT_DIR = Path("/app/output_csvs")

OUT_DIR.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()

# Reference-DB anhängen
con.execute(f"""
ATTACH '{REF_DB}' AS ref (TYPE SQLITE);
""")

def _log_path_for_db(db_path: Path) -> Path:
    if LOGS_OVERRIDE:
        return Path(LOGS_OVERRIDE)

    suffix = db_path.stem.split("_")[-1]
    # e.g. suffix 3FLASH, 2.5FLASH, 3PRO
    candidates = [
        LOGS_DIR / f"structured_logs_{suffix}.json",
        LOGS_DIR / "structured_logs.filtered.json",
        LOGS_DIR / "structured_logs_all.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"Keine strukturierte Log-Datei für '{db_path.name}' ({suffix}) gefunden in {LOGS_DIR}"
    )

def _refresh_logs_view(log_path: Path) -> None:
    con.execute(f"""
    CREATE OR REPLACE VIEW logs AS
    SELECT
      CAST(j.key AS INTEGER) AS id,
      j.value AS log_json
    FROM (
      SELECT json
      FROM read_json_objects('{log_path.as_posix()}')
    ) t,
    json_each(t.json) AS j;
    """)


for i, db_path in enumerate(sorted(SRC_DIR.glob("*.sqlite3"))):
    if "katheer" not in db_path.stem:
        continue  # skip databases with different schema
    alias = f"src{i}"
    out_csv = OUT_DIR / f"{db_path.stem}.csv"

    con.execute(f"""
    ATTACH '{db_path}' AS {alias} (TYPE SQLITE);
    """)

    log_path = _log_path_for_db(db_path)
    _refresh_logs_view(log_path)
    model_label = db_path.stem.split("_")[-1]

    con.execute(f"""
    COPY (
        SELECT
            s.*,
            r.*,
            json_object(
              'progress', coalesce((
                SELECT to_json(array_agg(p.value ORDER BY try_cast(p.key AS INTEGER)))
                FROM json_each(l.log_json -> 'progress') AS p
                WHERE try_cast(p.key AS INTEGER) IN (
                  SELECT try_cast(g.key AS INTEGER)
                  FROM json_each(l.log_json -> 'guard') AS g
                  WHERE g.value ->> 'model_label' = '{model_label}'
                )
              ), '[]'),
              'guard', coalesce((
                SELECT to_json(array_agg(g.value ORDER BY try_cast(g.key AS INTEGER)))
                FROM json_each(l.log_json -> 'guard') AS g
                WHERE g.value ->> 'model_label' = '{model_label}'
              ), '[]'),
              'responses', coalesce((
                SELECT to_json(array_agg(r.value ORDER BY try_cast(r.key AS INTEGER)))
                FROM json_each(l.log_json -> 'responses') AS r
                WHERE try_cast(r.key AS INTEGER) IN (
                  SELECT try_cast(g.key AS INTEGER)
                  FROM json_each(l.log_json -> 'guard') AS g
                  WHERE g.value ->> 'model_label' = '{model_label}'
                )
              ), '[]')
            ) AS log_json
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
