# %%
import duckdb

con = duckdb.connect()
con.execute("ATTACH '.../katheer.sqlite3' AS src (TYPE SQLITE);")
con.execute("ATTACH '.../katheer_annotated.sqlite3' AS ann (TYPE SQLITE);")

df = con.execute(
    """
SELECT s.id, s.text_normalisiert, a.extracted_text_normalized
FROM src.katheer s
JOIN ann.tafsir_analysis_katheer a ON s.id = a.id
WHERE s.id = 168
"""
).df()

df  # Jupyter rendert RTL korrekt
