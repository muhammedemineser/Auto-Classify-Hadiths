import sqlite3

from Tafsir.config import paths as cfg

conn = sqlite3.connect(cfg.ANNOTATED_DIR / f"{cfg.DEFAULT_TAFSIR}_annotated.sqlite3")
correct_last = 682
false_first = 1039
cur = conn.cursor()

cur.execute(
    f"""
WITH renumber AS (
    SELECT
        rowid AS rid,
        {correct_last} + ROW_NUMBER() OVER (ORDER BY id) AS new_id
    FROM tafsir_analysis_katheer
    WHERE id >= {false_first}
)
UPDATE tafsir_analysis_katheer
SET id = (
    SELECT new_id
    FROM renumber
    WHERE renumber.rid = tafsir_analysis_katheer.rowid
)
WHERE rowid IN (SELECT rid FROM renumber);
"""
)

conn.commit()
conn.close()
