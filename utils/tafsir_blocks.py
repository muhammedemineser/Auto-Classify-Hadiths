import sqlite3
from pathlib import Path


tafsir = input("Which tafsir do you want to read? ")
id = input("increase tafsir id by 1")

src_db = (
    f"/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books/{tafsir}.sqlite3"
)
dst_db = (
    f"/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_new/{tafsir}.sqlite3"
)

with sqlite3.connect(src_db) as src, sqlite3.connect(dst_db) as dst:
    src.row_factory = sqlite3.Row
    sc = src.cursor()
    dc = dst.cursor()

    tafsir_id = f"{id}"

    sc.execute(f"SELECT Id, sura, aya, text FROM {tafsir}")

    dc.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {tafsir} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tafsir_id TEXT,
            versnummer TEXT,
            text TEXT
        )
        """
    )

    for row in sc:
        tafsir_versnummer = row["id"]
        sura = row["sura"]
        aya = row["aya"]
        text = row["text"]

        if not text:
            continue

        # Text splitten (NICHT reverse!)
        parts = text.split("</p><p>")

        for part in parts:
            clean = part.replace("<p>", "").replace("</p>", "").strip()

            if not clean:
                continue

            dc.execute(
                f"""
                INSERT INTO {tafsir} (tafsir_id, versnummer, text)
                VALUES (?, ?, ?)
                """,
                (tafsir_id, tafsir_versnummer, clean),
            )
