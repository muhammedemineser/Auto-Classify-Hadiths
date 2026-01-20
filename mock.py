import regex
from sqlalchemy import create_engine, text

db_name = "tafsir_database"
engine_out = create_engine(f"sqlite:///GPT_seperator_for_{db_name}.db")

ALL_TAGS = [
    "isnad",
    "hadith",
    "quran_verse",
    "asbab_al_nuzul",
    "linguistic_analysis",
    "qiraat",
    "cross_references",
    "hadith_support",
    "opinions_of_scholars",
    "fiqh_implications",
    "theological_points",
    "historical_context",
    "explanation",
    "source",
    "balagha_analysis",
    "nasikh_wa_mansukh",
    "grammatical_parsing",
    "etymology",
    "parabolic_meaning",
    "sectarian_perspective",
    "spiritual_lessons",
    "biographies_of_narrators",
    "ijma_status",
    "reason_for_revelation_variants",
    "legal_maxims",
    "maqasid_al_sharia",
    "variant_interpretations",
    "minority_opinions",
    "majority_opinions",
    "literal_interpretation",
    "metaphorical_interpretation",
    "contextual_scope",
    "general_vs_specific",
    "absolute_vs_restricted",
    "command_and_prohibition",
    "rhetorical_devices",
    "semantic_fields",
    "synonym_analysis_homonym_antonym_analysis",
    "chronological_order",
    "meccan_medinan",
    "intertextual_links",
    "israiliyyat",
    "philosophical_reflections",
    "ethical_implications",
    "creedal_implications",
    "aqidah_classification",
    "scientific_allusions",
    "cosmological_notes",
    "social_norms",
    "political_implications",
    "pedagogical_lessons",
    "daawah_applications",
    "practical_guidance",
    "ritual_implications",
    "disputed_terms",
    "technical_definitions",
    "textual_variants",
    "manuscript_evidence",
    "chain_evaluation",
    "narrator_criticism",
    "comparative_tafsir",
    "methodological_notes",
    "argument",
    "summary",
    "conclusion",
]

RX_RECURSIVE = regex.compile(
    r"(?s)<(?P<tag>" + "|".join(ALL_TAGS) + r")>(?P<content>(?:[^<]|(?R))*)</(?P=tag)>"
)


def _walk(xml, row):
    for m in RX_RECURSIVE.finditer(xml):
        tag = m.group("tag")
        full = m.group(0)
        row[tag] = full if row[tag] is None else row[tag] + "\n" + full
        _walk(m.group("content"), row)


def extract_nested_data(xml):
    row = {tag: None for tag in ALL_TAGS}
    if xml:
        _walk(xml, row)
    return row


def bulk_insert_tafsir(engine, raw_texts):
    rows = [extract_nested_data(t) for t in raw_texts if t]
    cols = ", ".join(ALL_TAGS)
    vals = ", ".join(f":{c}" for c in ALL_TAGS)
    stmt = text(f"INSERT INTO tafsir_analysis ({cols}) VALUES ({vals})")
    with engine.begin() as conn:
        conn.execute(stmt, rows)


def setup_database():
    cols_sql = ", ".join(f"{c} TEXT" for c in ALL_TAGS)
    with engine_out.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS tafsir_analysis"))
        conn.execute(
            text(
                f"""
            CREATE TABLE tafsir_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {cols_sql},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
            )
        )


def count_recursive(xml, counter):
    for m in RX_RECURSIVE.finditer(xml):
        tag = m.group("tag")
        counter[tag] = counter.get(tag, 0) + 1
        count_recursive(m.group("content"), counter)


def print_column_counts(xml):
    counter = {}
    count_recursive(xml, counter)
    print("Column counts:", len(counter))
    for tag in sorted(counter):
        print(f"{tag}: {counter[tag]}")


mock_raw_texts = [
    # Fall 1: Der Standard-Fall (dein Original)
    """
    <explanation>
        <source>Tafsir al-Jalalayn</source>
        <linguistic_analysis>
            <etymology>Allah</etymology>
            <grammatical_parsing>Genitiv</grammatical_parsing>
        </linguistic_analysis>
        <theological_points>Tawhid</theological_points>
    </explanation>
    """,
    # Fall 2: Mehrfache Vorkommen desselben Tags (Konkatenierungstest)
    """
    <isnad>Kette 1: Malik -> Nafi -> Ibn Umar</isnad>
    <isnad>Kette 2: Schafi'i -> Malik</isnad>
    <hadith>Handlungen sind entsprechend der Absichten.</hadith>
    <had_support>
        <source>Sahih Bukhari</source>
        <source>Sahih Muslim</source>
    </had_support>
    """,
    # Fall 3: Extreme Rekursion & Verschachtelung
    """
    <argument>
        Die sprachliche Struktur ist komplex.
        <linguistic_analysis>
            Die Wurzel ist: <etymology>S-L-M</etymology>.
            Dies führt zu:
            <balagha_analysis>
                Ein rhetorisches Mittel wird genutzt: 
                <rhetorical_devices>Iltifat</rhetorical_devices>
            </balagha_analysis>
        </linguistic_analysis>
        Daraus folgt eine rechtliche Einordnung:
        <fiqh_implications>Es ist obligatorisch (Wajib).</fiqh_implications>
    </argument>
    """,
    # Fall 4: "Siblings" und leere Inhalte
    """
    <quran_verse>قُلْ هُوَ اللَّهُ أَحَدٌ</quran_verse>
    <asbab_al_nuzul></asbab_al_nuzul>
    <theological_points>Absoluter Monotheismus.</theological_points>
    <summary>Der Vers beschreibt die Ikhlas.</summary>
    <conclusion></conclusion>
    """,
]

# Integration in den Testlauf
if __name__ == "__main__":
    setup_database()

    print(f"Starte Testlauf mit {len(mock_raw_texts)} kritischen Fällen...")
    bulk_insert_tafsir(engine_out, mock_raw_texts)

    # Stichprobe für Fall 2 (Konkatenierung von 'isnad')
    with engine_out.connect() as conn:
        print("\n--- Prüfung Konkatenierung (Fall 2) ---")
        res = conn.execute(
            text("SELECT isnad FROM tafsir_analysis WHERE hadith LIKE '%Absichten%'")
        ).fetchone()
        if res and res[0]:
            lines = res[0].split("\n")
            print(f"Anzahl gefundener Isnad-Einträge in einer Zelle: {len(lines)}")
            for line in lines:
                print(f" -> {line}")

        print("\n--- Prüfung Tiefe Verschachtelung (Fall 3) ---")
        res = conn.execute(
            text(
                "SELECT etymology, rhetorical_devices FROM tafsir_analysis WHERE etymology IS NOT NULL"
            )
        ).fetchone()
        if res:
            print(f"Gefundene Etymologie: {res[0]}")
            print(f"Gefundenes rhetorisches Mittel (tief verschachtelt): {res[1]}")
