import regex
from sqlalchemy import create_engine, text

# 1. KONFIGURATION
db_name = "tafsir_final"
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

# Rekursive Regex Definition
RX_RECURSIVE = regex.compile(
    r"(?s)<(?P<tag>" + "|".join(ALL_TAGS) + r")>(?P<content>(?:[^<]|(?R))*)</(?P=tag)>"
)


# 2. EXTRAKTIONS-LOGIK
def _walk(xml, row):
    """Durchläuft den XML-Baum rekursiv und füllt die flache Zeile."""
    if not xml:
        return
    for m in RX_RECURSIVE.finditer(xml):
        tag = m.group("tag")
        full = m.group(0)
        content = m.group("content")

        # Speichern des Fundes (mit Konkatenierung bei Mehrfachfunden)
        if row[tag] is None:
            row[tag] = full
        else:
            if full not in row[tag]:  # Vermeidung von Duplikaten durch Rekursionstiefe
                row[tag] += "\n" + full

        # Rekursiver Abstieg in den Content des aktuellen Tags
        _walk(content, row)


def extract_nested_data(xml):
    """Initialisiert eine Tabellenzeile und startet den rekursiven Walk."""
    row = {tag: None for tag in ALL_TAGS}
    if xml:
        _walk(xml, row)
    return row


# 3. DATENBANK-OPERATIONEN
def setup_database():
    """Erstellt die Tabelle mit allen 65 Spalten."""
    cols_sql = ", ".join(f"{c} TEXT" for c in ALL_TAGS)
    sql = f"""
    CREATE TABLE IF NOT EXISTS tafsir_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {cols_sql},
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine_out.begin() as conn:
        conn.execute(text(sql))


def bulk_insert_tafsir(engine, raw_texts):
    """Führt hocheffizienten Bulk-Insert aus."""
    rows = [extract_nested_data(t) for t in raw_texts if t]
    if not rows:
        return

    cols = ", ".join(ALL_TAGS)
    vals = ", ".join(f":{c}" for c in ALL_TAGS)
    stmt = text(f"INSERT INTO tafsir_analysis ({cols}) VALUES ({vals})")

    with engine.begin() as conn:
        conn.execute(stmt, rows)
    print(f"Erfolg: {len(rows)} Datensätze eingefügt.")


# 4. HILFSFUNKTION FÜR KONTROLLE
def print_column_counts(xml):
    def count_rec(inner_xml, counter):
        for m in RX_RECURSIVE.finditer(inner_xml):
            tag = m.group("tag")
            counter[tag] = counter.get(tag, 0) + 1
            count_rec(m.group("content"), counter)

    counter = {}
    count_rec(xml, counter)
    print("\n--- Gefundene Tags im Text ---")
    for tag in sorted(counter):
        print(f"{tag}: {counter[tag]}")


# 5. TESTLAUF
if __name__ == "__main__":
    setup_database()

    mock_raw_texts = [
        # Fall 1: Standard-Rekursion
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
        # Fall 2: Mehrfache Tags & Tiefe Verschachtelung
        """
        <isnad><biographies_of_narrators>Narrator A</biographies_of_narrators></isnad>
        <isnad>Kette B</isnad>
        <argument>
            Struktur-Analyse:
            <balagha_analysis>
                Metapher in: <rhetorical_devices>Istia'ara</rhetorical_devices>
            </balagha_analysis>
            Wurzel: <etymology>S-L-M</etymology>
        </argument>
        """,
    ]

    print("Starte Extraktion...")
    bulk_insert_tafsir(engine_out, mock_raw_texts)

    # Verifizierung
    with engine_out.connect() as conn:
        print("\n--- Datenbank-Check (Letzter Eintrag) ---")
        query = text(
            "SELECT etymology, rhetorical_devices, isnad FROM tafsir_analysis ORDER BY id DESC LIMIT 1"
        )
        res = conn.execute(query).fetchone()
        if res:
            print(f"Etymologie: {res[0]}")
            print(f"Rhetorik: {res[1]}")
            print(f"Isnad (konkateniert): \n{res[2]}")
