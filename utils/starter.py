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

book = input("Which book do you want to read? ")


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
path = "/home/muhammed-emin-eser/desk/apps/classify/Leeds_KSU-Hadith-Corpus"  # Path of the corpus file
book_filenames = sorted(
    glob.glob(path + "//**//*.csv", recursive=True)
)  # read all csv files in all books

# If you want to read all files in the corpus.
for book_filename in book_filenames:
    print("Reading '{0}'...".format(book_filename))
    data = pandas.read_csv(book_filename, names=colnames, skiprows=1)


# --------------------------------------------------------
# Else if only one book is requried, use the following code to read its files
# for example, to read Albukhari book
base = (
    Path("/home/muhammed-emin-eser/desk/apps/classify/Leeds_KSU-Hadith-Corpus") / book
)

for x in range(1, anzahl + 1):
    path = base / f"Chapter{x}.csv"

    # Then save every column you will use in a dedicated list.
    Chapter_Num = data.Chapter_Number.tolist()
    Chapter_Title_E = data.Chapter_English.tolist()
    Chapter_Title_Ar = data.Chapter_Arabic.tolist()

    Section_Num = data.Section_Number.tolist()
    Section_En = data.Section_English.tolist()
    Section_Ar = data.Section_Arabic.tolist()

    Hadith_num = data.Hadith_number.tolist()

    En_hadith = data.English_Hadith.tolist()
    En_Isnad = data.English_Isnad.tolist()
    En_Matn = data.English_Matn.tolist()

    Ar_Hadith = data.Arabic_Hadith.tolist()
    Ar_Isnad = data.Arabic_Isnad.tolist()
    Ar_Matn = data.Arabic_Matn.tolist()

    Ar_Comment = data.Arabic_Comment.tolist()
    En_Grade = data.English_Grade.tolist()
    Ar_Grade = data.Arabic_Grade.tolist()

    # Do the requried processing.. a simple example: print
    with sqlite3.connect(
        f"/home/muhammed-emin-eser/desk/apps/classify/Hadith/{book}.sqlite"
    ) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS Hadith (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Hadith_Number TEXT,
            Hadith_English TEXT,
            Hadith_Arabic TEXT,
            Hadith_English_Grade TEXT,
            Hadith_Arabic_Grade TEXT
        )
        """
        )

        for i, hadith in enumerate(En_Matn):
            cursor.execute(
                """
                INSERT INTO Hadith
                (Hadith_Number, Hadith_English, Hadith_English_Grade)
                VALUES (?, ?, ?)
                """,
                (
                    str(Hadith_num[i]),  # alles wird STRING
                    hadith,
                    En_Grade[i],
                ),
            )
        for i, hadith in enumerate(Ar_Matn):
            cursor.execute(
                """
                UPDATE Hadith
                SET Hadith_Arabic = ?, Hadith_Arabic_Grade = ?
                WHERE id = ?
                """,
                (
                    hadith,
                    Ar_Grade[i],
                    i + 1,  # AUTOINCREMENT startet bei 1
                ),
            )
