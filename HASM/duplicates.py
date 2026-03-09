from collections import defaultdict
import re
import regex
import unicodedata
from pathlib import Path
from typing import Optional
import glob, os, sqlite3
import json
from ranking import utils

BASE_DIR = Path(__file__).resolve().parent
path_to_cand = BASE_DIR / "Data" / "Sahihah" / "sahihah_hadith_extracted_in_sittah.txt"
path_to_ref = BASE_DIR / "Data" / "Hadith"


def find_duplicates_cand(path: str) -> dict[int, list[int]]:
    with open(path, "r", encoding="utf-8") as f:
        raw = f.readlines()

    ids = [line.split()[0] for line in raw]
    lines = [" ".join(utils.normalize(line.strip())) for line in raw]

    seen: dict[str, str] = {}
    duplicates: dict[str, list[str]] = defaultdict(list)

    for i, line in zip(ids, lines):
        if line in seen and seen[line] != i:
            duplicates[seen[line]].append(int(i))
        else:
            seen[line] = i
    duplicates = {int(k): set(v) for k, v in dict(duplicates).items() if len(v) > 1}
    return duplicates


def find_duplicates_ref(path: str) -> dict[int, list[str]]:
    db_files = glob.glob(os.path.join(path, "*.db"))

    seen: dict[str, str] = {}
    duplicates: dict[str, list[str]] = defaultdict(list)

    for db_file in db_files:
        conn = sqlite3.connect(db_file)
        cur = conn.cursor()
        cur.execute("SELECT Hadith_number, Arabic_Matn FROM hadiths")
        rows = cur.fetchall()
        conn.close()

        for hadith_number, matn in rows:
            if not matn:
                continue
            line = " ".join(utils.normalize(matn.strip()))
            i = f"{os.path.basename(db_file)}:{str(hadith_number)}"
            if line in seen:
                if seen[line] != i:
                    duplicates[seen[line]].append(i)
            else:
                seen[line] = i

    return {k: set(v) for k, v in duplicates.items() if len(v) > 1}


cand = find_duplicates_cand(path_to_cand)
with open("cand_duplicates.json", "w", encoding="utf-8") as f:
    json.dump({k: list(v) for k, v in cand.items()}, f, ensure_ascii=False, indent=2)

ref = find_duplicates_ref(path_to_ref)
with open("ref_duplicates.json", "w", encoding="utf-8") as f:
    json.dump({k: list(v) for k, v in ref.items()}, f, ensure_ascii=False, indent=2)
