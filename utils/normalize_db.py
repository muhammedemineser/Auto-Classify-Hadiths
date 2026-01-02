# import sqlite3
# import pandas as pd

# conn = sqlite3.connect("/home/muhammed-emin-eser/desk/apps/classify/Hadith/Hadith.db")

# tables = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)[
#     "name"
# ].tolist()

# print(tables)


# def normalize_table(df):
#     # Chapters
#     chapters = (
#         df[["Chapter_Number", "Chapter_English", "Chapter_Arabic"]]
#         .drop_duplicates()
#         .reset_index(drop=True)
#     )
#     chapters["chapter_id"] = chapters.index + 1

#     # Sections
#     sections = (
#         df[["Chapter_Number", "Section_Number", "Section_English", "Section_Arabic"]]
#         .drop_duplicates()
#         .merge(chapters, on="Chapter_Number")
#         .reset_index(drop=True)
#     )
#     sections["section_id"] = sections.index + 1

#     # Hadiths
#     hadiths = df.merge(
#         sections[["section_id", "Chapter_Number", "Section_Number"]],
#         on=["Chapter_Number", "Section_Number"],
#     ).drop(
#         columns=[
#             "Chapter_English",
#             "Chapter_Arabic",
#             "Section_English",
#             "Section_Arabic",
#         ]
#     )
#     hadiths["hadith_id"] = hadiths.index + 1

#     return chapters, sections, hadiths


# from pathlib import Path

# out_dir = Path("/home/muhammed-emin-eser/desk/apps/classify/Hadith/normalized_dbs")
# out_dir.mkdir(exist_ok=True)

# for table in tables:
#     print(f"Processing {table}")

#     df = pd.read_sql(f"SELECT * FROM {table}", conn)

#     chapters, sections, hadiths = normalize_table(df)

#     out_db = out_dir / f"{table}.db"
#     out_conn = sqlite3.connect(out_db)

#     chapters.to_sql("chapters", out_conn, index=False, if_exists="replace")
#     sections.to_sql("sections", out_conn, index=False, if_exists="replace")
#     hadiths.to_sql("hadiths", out_conn, index=False, if_exists="replace")

#     out_conn.close()

import sqlite3
from pathlib import Path

DB_DIR = Path("/home/muhammed-emin-eser/desk/apps/classify/Hadith/normalized_dbs")

for db_path in DB_DIR.glob("*.db"):
    print(f"Processing {db_path.name}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        cur.execute("ALTER TABLE sections DROP COLUMN chapter_english;")
        cur.execute("ALTER TABLE sections DROP COLUMN chapter_arabic;")
        conn.commit()
        print("  -> columns dropped")
    except sqlite3.OperationalError as e:
        print(f"  !! skipped ({e})")

    conn.close()
