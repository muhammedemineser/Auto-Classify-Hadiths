"""Fuegt die Spalte source_full in die matches-DBs ein.

source_full = der vollstaendige, NICHT-extrahierte Eintrag aus
Data/Sahihah/sahihah_komplett.txt fuer die jeweilige txt_id
(Albani-Originaltext inkl. Quellenangabe).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent
KOMPLETT = BASE / "Data" / "Sahihah" / "sahihah_komplett.txt"
DBS = [
    BASE / "Data" / "hasm_matches.db",
    BASE / "Data" / "hasm_matches_out_sittah.db",
]

# Regex fuer Zeilenanfang: '123 - ...', '123- ...', '123 ـ ...'
_LEAD = re.compile(r"^(\d+)\s*[-ـ]\s*")


def load_full_entries() -> dict[str, str]:
    entries: dict[str, str] = {}
    with open(KOMPLETT, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            m = _LEAD.match(line)
            if m:
                entries[m.group(1)] = line
                continue
            # Sonderfall: ID mitten in der Zeile, z.B.
            # 'من أهوال العذاب في جهنم 3470 ـ (...)'
            for mm in re.finditer(r"(?<!\d)(\d+)\s*[-ـ]\s*", line):
                cid = mm.group(1)
                # nur uebernehmen, falls ID noch nicht bekannt und plausibel
                if cid not in entries and mm.start() > 0:
                    entries[cid] = line
                    break
    return entries


def backfill(db_path: Path, entries: dict[str, str]) -> tuple[int, list[str]]:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cols = [r[1] for r in cur.execute("PRAGMA table_info(hadiths)").fetchall()]
    if "source_full" not in cols:
        cur.execute("ALTER TABLE hadiths ADD COLUMN source_full TEXT")
        conn.commit()

    rows = cur.execute(
        "SELECT rowid, txt_id FROM hadiths WHERE source_full IS NULL"
    ).fetchall()
    updated = 0
    missing: list[str] = []
    for rowid, txt_id in rows:
        full = entries.get(str(txt_id))
        if full is None:
            missing.append(str(txt_id))
            continue
        cur.execute(
            "UPDATE hadiths SET source_full=? WHERE rowid=?", (full, rowid)
        )
        updated += 1
    conn.commit()
    conn.close()
    return updated, sorted(set(missing))


def main() -> None:
    entries = load_full_entries()
    print(f"komplett-Eintraege geparst: {len(entries)}")
    for db in DBS:
        if not db.exists():
            print(f"  {db.name}: existiert nicht, uebersprungen")
            continue
        updated, missing = backfill(db, entries)
        print(f"  {db.name}: source_full gesetzt = {updated}")
        if missing:
            print(f"    fehlende IDs ({len(missing)}): {missing[:20]}")


if __name__ == "__main__":
    main()