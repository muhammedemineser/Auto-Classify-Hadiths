# -*- coding: utf-8 -*-
"""
Created on Mon Dec 16 12:06:08 2019
This is a starter code to facilitate reading information from the Leeds and King Saud University Hadith Corpus
@author: Shatha Altammami
"""

import pandas
import glob
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine, Integer, String
import pandas as pd
import re

# 1. Verbindung herstellen (hier eine lokale SQLite-Datei)
engine = create_engine(
    "sqlite:////home/muhammed-emin-eser/desk/apps/classify/Hadith/Hadith.db"
)

books = ["Tirmizi", "Nesai", "Muslim", "Bukhari", "IbnMaja", "AbuDaud"]
path = "/home/muhammed-emin-eser/desk/apps/classify/Hadith/Sorted"  # Path of the corpus file


def chapter_key(path):
    return int(Path(path).stem.replace("Chapter", ""))


for book in books:
    ordner = Path(
        f"/home/muhammed-emin-eser/desk/apps/classify/Leeds_KSU-Hadith-Corpus/{book}"
    )
    anzahl = sum(1 for p in ordner.iterdir() if p.is_file())

    colnames = [
        "Chapter_Number",
        "Chapter_English",
        "Chapter_Arabic",
        "Section_Number",
        "Section_English",
        "Section_Arabic",
        "Hadith_number",
        "English_Hadith",
        "English_Isnad",
        "English_Matn",
        "Arabic_Hadith",
        "Arabic_Isnad",
        "Arabic_Matn",
        "Arabic_Comment",
        "English_Grade",
        "Arabic_Grade",
    ]

    # if you want to read all corpus files

    book_filenames = sorted(glob.glob(f"{path}/{book}/*.csv"), key=chapter_key)

    # If you want to read all files in the corpus.
    for book_filename in book_filenames:
        print("Reading '{0}'...".format(book_filename))

        data = pandas.read_csv(book_filename, names=colnames, skiprows=1)
        all_strings = {col: String for col in data.columns}
        data.to_sql(
            f"{book}",
            con=engine,
            if_exists="append",
            dtype=all_strings,
            index=False,
            index_label="id",
        )
    # --------------------------------------------------------
    # Else if only one book is requried, use the following code to read its files
    # for example, to read Albukhari book
    # base = (
    #     Path("/home/muhammed-emin-eser/desk/apps/classify/Leeds_KSU-Hadith-Corpus")
    #     / book
    # )

    # for x in range(1, anzahl + 1):
    #     path = base / f"Chapter{x}.csv"

    #     # Then save every column you will use in a dedicated list.
    #     Chapter_Num = data.Chapter_Number.tolist()
    #     Chapter_Title_E = data.Chapter_English.tolist()
    #     Chapter_Title_Ar = data.Chapter_Arabic.tolist()

    #     Section_Num = data.Section_Number.tolist()
    #     Section_En = data.Section_English.tolist()
    #     Section_Ar = data.Section_Arabic.tolist()

    #     Hadith_num = data.Hadith_number.tolist()

    #     En_hadith = data.English_Hadith.tolist()
    #     En_Isnad = data.English_Isnad.tolist()
    #     En_Matn = data.English_Matn.tolist()

    #     Ar_Hadith = data.Arabic_Hadith.tolist()
    #     Ar_Isnad = data.Arabic_Isnad.tolist()
    #     Ar_Matn = data.Arabic_Matn.tolist()

    #     Ar_Comment = data.Arabic_Comment.tolist()
    #     En_Grade = data.English_Grade.tolist()
    #     Ar_Grade = data.Arabic_Grade.tolist()

    #     # Do the requried processing.. a simple example: print
    #     with sqlite3.connect(
    #         f"/home/muhammed-emin-eser/desk/apps/classify/Hadith/Sunan.sqlite3"
    #     ) as conn:
    #         cursor = conn.cursor()

    #         cursor.execute(
    #             f"""
    #         CREATE TABLE IF NOT EXISTS {book} (
    #             id INTEGER PRIMARY KEY AUTOINCREMENT,
    #         )
    #         """
    #         )

    #         for col in colnames:
    #             cursor.execute(
    #                 f"""
    #             ALTER TABLE {book}
    #             ADD COLUMN {col} TEXT
    #             """
    #             )

    #         for i, hadith in enumerate(En_Matn):
    #             cursor.execute(
    #                 """
    #                 INSERT INTO Hadith
    #                 (Hadith_Number, Hadith_English, Hadith_English_Grade)
    #                 VALUES (?, ?, ?)
    #                 """,
    #                 (
    #                     str(Hadith_num[i]),  # alles wird STRING
    #                     hadith,
    #                     En_Grade[i],
    #                 ),
    #             )
    #         for i, hadith in enumerate(Ar_Matn):
    #             cursor.execute(
    #                 """
    #                 UPDATE Hadith
    #                 SET Hadith_Arabic = ?, Hadith_Arabic_Grade = ?
    #                 WHERE id = ?
    #                 """,
    #                 (
    #                     hadith,
    #                     Ar_Grade[i],
    #                     i + 1,  # AUTOINCREMENT startet bei 1
    #                 ),
    #             )
