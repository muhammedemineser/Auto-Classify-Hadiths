# %%
import duckdb

con = duckdb.connect()

con.execute(
    """
ATTACH '/app/Tafsir/tafsir_books_annotated/katheer_annotated.sqlite3'
AS ann (TYPE SQLITE);
"""
)

print("1) längster Eintrag")
print(con.execute("""
SELECT id FROM ann.tafsir_analysis_katheer
ORDER BY
  (length(extracted_text_normalized)
   - length(replace(extracted_text_normalized, ' ', '')) + 1) DESC
LIMIT 1
""").fetchall())

print("\n2) 10 längste Einträge")
print(con.execute("""
SELECT id FROM ann.tafsir_analysis_katheer
ORDER BY
  (length(extracted_text_normalized)
   - length(replace(extracted_text_normalized, ' ', '')) + 1) DESC
LIMIT 10
""").fetchall())

print("\n3) kleinster Quran-Anteil")
print(con.execute("""
SELECT id FROM ann.tafsir_analysis_katheer
WHERE extracted_text_normalized IS NOT NULL
  AND quran_verse IS NOT NULL
ORDER BY
  (1.0 * length(quran_verse)
   / NULLIF(length(extracted_text_normalized), 0)) ASC
LIMIT 10
""").fetchall())

print("\n4) 20 random IDs")
print(con.execute("""
SELECT id FROM ann.tafsir_analysis_katheer
ORDER BY RANDOM()
LIMIT 20
""").fetchall())


# %%
