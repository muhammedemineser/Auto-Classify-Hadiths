"""
Dieses Skript dokumentiert den Aufbau der Meta-Datenbank für Tafsir-Projekte.

Reihenfolge:
1. Verbindung zur Datenbank
2. Anlegen der Kern-Tabellen (sura, vers, tafsir, tafsir_text)
3. Einfügen der Sura-Namen
4. Import der Qur'an-Texte (nur Text, AUTOINCREMENT-ID)
5. Setzen von sura_id und aya anhand der bekannten Aya-Anzahlen
6. Bereinigung der Verse (Entfernung von Ziffern)
7. Manuelles Hinzufügen von Tafsir-Metadaten
"""

import sqlite3
import re
from pathlib import Path

DB_PATH = "/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_new/meta.sqlite"
file_path = Path(
    "/home/muhammed-emin-eser/desk/apps/classify/quran-simple-plain.txt"
)  # jede Zeile = ein Vers (Reihenfolge!)


from pathlib import Path
import sqlite3
import re

sura_names = {
    1: ("الفاتحة", "al-Fātiḥa"),
    2: ("البقرة", "al-Baqara"),
    3: ("آل عمران", "Āl ʿImrān"),
    4: ("النساء", "an-Nisāʾ"),
    5: ("المائدة", "al-Māʾida"),
    6: ("الأنعام", "al-Anʿām"),
    7: ("الأعراف", "al-Aʿrāf"),
    8: ("الأنفال", "al-Anfāl"),
    9: ("التوبة", "at-Tawba"),
    10: ("يونس", "Yūnus"),
    11: ("هود", "Hūd"),
    12: ("يوسف", "Yūsuf"),
    13: ("الرعد", "ar-Raʿd"),
    14: ("إبراهيم", "Ibrāhīm"),
    15: ("الحجر", "al-Ḥijr"),
    16: ("النحل", "an-Naḥl"),
    17: ("الإسراء", "al-Isrāʾ"),
    18: ("الكهف", "al-Kahf"),
    19: ("مريم", "Maryam"),
    20: ("طه", "Ṭā-Hā"),
    21: ("الأنبياء", "al-Anbiyāʾ"),
    22: ("الحج", "al-Ḥajj"),
    23: ("المؤمنون", "al-Muʾminūn"),
    24: ("النور", "an-Nūr"),
    25: ("الفرقان", "al-Furqān"),
    26: ("الشعراء", "ash-Shuʿarāʾ"),
    27: ("النمل", "an-Naml"),
    28: ("القصص", "al-Qaṣaṣ"),
    29: ("العنكبوت", "al-ʿAnkabūt"),
    30: ("الروم", "ar-Rūm"),
    31: ("لقمان", "Luqmān"),
    32: ("السجدة", "as-Sajda"),
    33: ("الأحزاب", "al-Aḥzāb"),
    34: ("سبإ", "Sabaʾ"),
    35: ("فاطر", "Fāṭir"),
    36: ("يس", "Yā-Sīn"),
    37: ("الصافات", "aṣ-Ṣāffāt"),
    38: ("ص", "Ṣād"),
    39: ("الزمر", "az-Zumar"),
    40: ("غافر", "Ghāfir"),
    41: ("فصلت", "Fuṣṣilat"),
    42: ("الشورى", "ash-Shūrā"),
    43: ("الزخرف", "az-Zukhruf"),
    44: ("الدخان", "ad-Dukhān"),
    45: ("الجاثية", "al-Jāthiya"),
    46: ("الأحقاف", "al-Aḥqāf"),
    47: ("محمد", "Muḥammad"),
    48: ("الفتح", "al-Fatḥ"),
    49: ("الحجرات", "al-Ḥujurāt"),
    50: ("ق", "Qāf"),
    51: ("الذاريات", "adh-Dhāriyāt"),
    52: ("الطور", "aṭ-Ṭūr"),
    53: ("النجم", "an-Najm"),
    54: ("القمر", "al-Qamar"),
    55: ("الرحمن", "ar-Raḥmān"),
    56: ("الواقعة", "al-Wāqiʿa"),
    57: ("الحديد", "al-Ḥadīd"),
    58: ("المجادلة", "al-Mujādila"),
    59: ("الحشر", "al-Ḥashr"),
    60: ("الممتحنة", "al-Mumtaḥina"),
    61: ("الصف", "aṣ-Ṣaff"),
    62: ("الجمعة", "al-Jumuʿa"),
    63: ("المنافقون", "al-Munāfiqūn"),
    64: ("التغابن", "at-Taghābun"),
    65: ("الطلاق", "aṭ-Ṭalāq"),
    66: ("التحريم", "at-Taḥrīm"),
    67: ("الملك", "al-Mulk"),
    68: ("القلم", "al-Qalam"),
    69: ("الحاقة", "al-Ḥāqqa"),
    70: ("المعارج", "al-Maʿārij"),
    71: ("نوح", "Nūḥ"),
    72: ("الجن", "al-Jinn"),
    73: ("المزمل", "al-Muzzammil"),
    74: ("المدثر", "al-Muddaththir"),
    75: ("القيامة", "al-Qiyāma"),
    76: ("الإنسان", "al-Insān"),
    77: ("المرسلات", "al-Mursalāt"),
    78: ("النبأ", "an-Nabaʾ"),
    79: ("النازعات", "an-Nāziʿāt"),
    80: ("عبس", "ʿAbasa"),
    81: ("التكوير", "at-Takwīr"),
    82: ("الانفطار", "al-Infiṭār"),
    83: ("المطففين", "al-Muṭaffifīn"),
    84: ("الانشقاق", "al-Inshiqāq"),
    85: ("البروج", "al-Burūj"),
    86: ("الطارق", "aṭ-Ṭāriq"),
    87: ("الأعلى", "al-Aʿlā"),
    88: ("الغاشية", "al-Ghāshiya"),
    89: ("الفجر", "al-Fajr"),
    90: ("البلد", "al-Balad"),
    91: ("الشمس", "ash-Shams"),
    92: ("الليل", "al-Layl"),
    93: ("الضحى", "aḍ-Ḍuḥā"),
    94: ("الشرح", "ash-Sharḥ"),
    95: ("التين", "at-Tīn"),
    96: ("العلق", "al-ʿAlaq"),
    97: ("القدر", "al-Qadr"),
    98: ("البينة", "al-Bayyina"),
    99: ("الزلزلة", "az-Zalzala"),
    100: ("العاديات", "al-ʿĀdiyāt"),
    101: ("القارعة", "al-Qāriʿa"),
    102: ("التكاثر", "at-Takāthur"),
    103: ("العصر", "al-ʿAṣr"),
    104: ("الهمزة", "al-Humaza"),
    105: ("الفيل", "al-Fīl"),
    106: ("قريش", "Quraysh"),
    107: ("الماعون", "al-Māʿūn"),
    108: ("الكوثر", "al-Kawthar"),
    109: ("الكافرون", "al-Kāfirūn"),
    110: ("النصر", "an-Naṣr"),
    111: ("المسد", "al-Masad"),
    112: ("الإخلاص", "al-Ikhlāṣ"),
    113: ("الفلق", "al-Falaq"),
    114: ("الناس", "an-Nās"),
}

# fmt: off
ayah_counts = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109,
    123, 111, 43, 52, 99, 128, 111, 110, 98, 135,
    112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85,
    54, 53, 89, 59, 37, 35, 38, 29, 18, 45,
    60, 49, 62, 55, 78, 96, 29, 22, 24, 13,
    14, 11, 11, 18, 12, 12, 30, 52, 52, 44,
    28, 28, 20, 56, 40, 31, 50, 40, 46, 42,
    29, 19, 36, 25, 22, 17, 19, 26, 30, 20,
    15, 21, 11, 8, 8, 19, 5, 8, 8, 11,
    11, 8, 3, 9, 5, 4, 7, 3, 6, 3,
    5, 4, 5, 6
]
# fmt: on

with sqlite3.connect(DB_PATH) as conn:
    c = conn.cursor()

    c.execute(
        """
    CREATE TABLE IF NOT EXISTS sura (
        sura_id INTEGER PRIMARY KEY,
        name_ar TEXT NOT NULL,
        name_translit TEXT NOT NULL
    )
    """
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS vers (
        versnummer INTEGER PRIMARY KEY AUTOINCREMENT,
        sura_id INTEGER,
        aya INTEGER,
        text TEXT NOT NULL,
        FOREIGN KEY (sura_id) REFERENCES sura(sura_id)
    )
    """
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS tafsir (
        tafsir_id INTEGER PRIMARY KEY,
        name TEXT NOT NULL
    )
    """
    )
    c.execute(
        """
    CREATE TABLE IF NOT EXISTS tafsir_text (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tafsir_id INTEGER NOT NULL,
        versnummer INTEGER NOT NULL,
        text TEXT NOT NULL,
        FOREIGN KEY (tafsir_id) REFERENCES tafsir(tafsir_id),
        FOREIGN KEY (versnummer) REFERENCES vers(versnummer)
    )
    """
    )

    for sid, (ar, tr) in sura_names.items():
        c.execute(
            "INSERT OR IGNORE INTO sura (sura_id, name_ar, name_translit) VALUES (?, ?, ?)",
            (sid, ar, tr),
        )

    file_path = Path("texts/quran.txt")

    with file_path.open(encoding="utf-8") as f:
        for line in f:
            text = line.strip()
            if not text:
                continue

            c.execute(
                "INSERT INTO vers (text) VALUES (?)",
                (text,),
            )

    sura_aya_list = []

    for sura_id, count in enumerate(ayah_counts, start=1):
        for aya in range(1, count + 1):
            sura_aya_list.append((sura_id, aya))

    c.execute("SELECT versnummer FROM vers ORDER BY versnummer")
    versnummern = [row[0] for row in c.fetchall()]

    assert len(versnummern) == len(sura_aya_list)

    for versnummer, (sura_id, aya) in zip(versnummern, sura_aya_list):
        c.execute(
            "UPDATE vers SET sura_id = ?, aya = ? WHERE versnummer = ?",
            (sura_id, aya, versnummer),
        )

    c.execute("SELECT versnummer, text FROM vers")
    rows = c.fetchall()

    for versnummer, text in rows:
        if text is None:
            continue

        cleaned = re.sub(r"\d+", "", text)
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()

        c.execute(
            "UPDATE vers SET text = ? WHERE versnummer = ?",
            (cleaned, versnummer),
        )

    while True:
        tafsir_id = input("Tafsir-ID (leer = Ende): ").strip()
        if not tafsir_id:
            break

        name = input("Tafsir-Name: ").strip()
        if not name:
            print("Name darf nicht leer sein")
            continue

        try:
            tafsir_id = int(tafsir_id)
            c.execute(
                "INSERT INTO tafsir (tafsir_id, name) VALUES (?, ?)",
                (tafsir_id, name),
            )
            print(f"✔ Eingefügt: {tafsir_id} – {name}")
        except ValueError:
            print("ID muss eine Zahl sein")
        except sqlite3.IntegrityError:
            print("ID existiert bereits")
