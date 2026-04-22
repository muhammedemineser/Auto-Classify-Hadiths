# KSU-Hadith-Corpus — Data Processing Branch

This branch documents the operations applied to the
[LK-Hadith-Corpus](https://github.com/ShathaTm/LK-Hadith-Corpus)
to produce clean, normalized SQLite databases suitable for downstream NLP tasks.

---

## Source

**LK-Hadith-Corpus** — Leeds University & King Saud University Bilingual Hadith Corpus  
Authors: Altammami, S., Atwell, E., Alsalka, A.

Six canonical Hadith books, each split into per-chapter CSV files:

| Book     | Chapters |
|----------|----------|
| Bukhari  | 97       |
| Muslim   | 57       |
| Nesai    | 51       |
| Tirmizi  | 49       |
| AbuDaud  | 43       |
| IbnMaja  | 38       |

Each row in the source CSVs carries 16 columns:

```
Chapter_Number, Chapter_English, Chapter_Arabic,
Section_Number, Section_English, Section_Arabic,
Hadith_number,
English_Hadith, English_Isnad, English_Matn,
Arabic_Hadith,  Arabic_Isnad,  Arabic_Matn,
Arabic_Comment,
English_Grade, Arabic_Grade
```

---

## Process

### Step 1 — Sort CSVs numerically (`Hadith/Sorted/`)

The original corpus filenames (`Chapter1.csv` … `Chapter97.csv`) sort
lexicographically by default, placing `Chapter10` before `Chapter2`.
Each book's CSVs were copied into `Hadith/Sorted/<Book>/` and read in
correct numeric order using a key function:

```python
def chapter_key(path):
    return int(Path(path).stem.replace("Chapter", ""))
```

This fixed a bug in the upstream `starter.py` that caused rows to be
inserted in wrong chapter order.

### Step 2 — Ingest into SQLite (`utils/starter.py`)

All sorted CSVs per book are appended into a single flat table
inside `Hadith/Hadith.db` (one table per book, all columns as TEXT)
via SQLAlchemy. No data is dropped or modified at this stage.

### Step 3 — Normalize into relational tables (`utils/normalize_db.py`)

Each book's flat table is decomposed into three normalized tables:

**`chapters`**
```
Chapter_Number | Chapter_English | Chapter_Arabic | chapter_id
```

**`sections`**
```
Chapter_Number | Section_Number | Section_English | Section_Arabic | chapter_id | section_id
```

**`hadiths`**
```
Chapter_Number | Section_Number | Hadith_number |
English_Hadith | English_Isnad | English_Matn  |
Arabic_Hadith  | Arabic_Isnad  | Arabic_Matn   |
Arabic_Comment | English_Grade | Arabic_Grade  |
section_id | hadith_id
```

Duplicate text columns (`chapter_english`, `chapter_arabic`) were
subsequently dropped from the `sections` table, as this data is
already held in `chapters`.

> **Note:** The semantic distinction between `Section_ID` and
> `Section_Number`, and between `Chapter_ID` and `Chapter_Number`,
> remains unresolved in the source corpus and was left unchanged.

---

## Output

`Hadith/normalized_dbs/` — one SQLite database per book:

```
Bukhari.db  Muslim.db  Nesai.db  Tirmizi.db  AbuDaud.db  IbnMaja.db
```

Each database contains the three relational tables described above.
All text values are stored as TEXT. Integer surrogate keys
(`chapter_id`, `section_id`, `hadith_id`) are added as join handles.

`Hadith/Sorted/` — intermediate per-book folders with
numerically-ordered chapter CSVs (used as ingestion input).

---

## Accessibility

The upstream README warns that Excel cannot render the CSV files correctly
and recommends Numbers (Mac) or Google Sheets as workarounds.
This pipeline eliminates that problem entirely: the normalized SQLite
databases are queryable with any SQL client, Python (`sqlite3`), or
DB browser (e.g. DB Browser for SQLite) — no spreadsheet application needed.
