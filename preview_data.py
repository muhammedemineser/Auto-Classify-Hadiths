# %%
import sqlite3
import pandas as pd

# Verbindung zur SQLite-Datenbank
conn = sqlite3.connect(
    "/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books/katheer.sqlite3"
)

# Tabelle laden (DB-Reihenfolge bleibt erhalten)
df = pd.read_sql("SELECT id, sura, aya, text FROM katheer LIMIT 1000", conn)

# Alle Inhalte innerhalb {} extrahieren (mehrere pro Zeile möglich)
df["extracted"] = df["text"].str.findall(r"\(([^)]*)\)")

# Jede {}-Gruppe in eigene Zeile aufteilen
out = (
    df[["id", "sura", "aya", "extracted"]]
    .explode("extracted")  # behält Reihenfolge je DB-Zeile
    .dropna(subset=["extracted"])
    .reset_index(drop=True)
)

conn.close()
pd.set_option("display.max_rows", None)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_columns", None)

out
# %%
