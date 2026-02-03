# %%
import duckdb

con = duckdb.connect()

con.execute(
    """
ATTACH '/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books_annotated/katheer_annotated.sqlite3'
AS ann (TYPE SQLITE);
ATTACH '/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books/katheer.sqlite3'
AS srcc (TYPE SQLITE);
"""
)

df = con.execute(
    """
WITH binned AS (
  SELECT
    best_ann_id,
    CASE
      WHEN delta_len = 0 THEN 0
      ELSE CAST((delta_len - 1) / 10 AS INTEGER) + 1
    END AS delta_bin
  FROM src.katheer
)
SELECT
  best_ann_id,
  delta_bin,
  COUNT(*) AS count
FROM binned
GROUP BY best_ann_id, delta_bin
ORDER BY best_ann_id, delta_bin;

"""
).df()

df


# %%
