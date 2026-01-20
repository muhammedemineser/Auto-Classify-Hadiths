import time
import pyperclip
import pyautogui
import regex
from bs4 import BeautifulSoup
from sqlalchemy import MetaData, Table, create_engine, select, text


ALL_TAGS = [
    "isnad",
    "matn",
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


def get_code_from_devtools():
    pyautogui.hotkey("ctrl", "shift", "c")
    time.sleep(2)

    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    # ChatGPT
    # search_term = "overflow-visible! px-0!"
    search_term = "code-container formatted ng-tns-"
    pyperclip.copy(search_term)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.click(x=1396, y=1000)
    time.sleep(2)
    pyautogui.click(x=814, y=124)
    time.sleep(1)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "shift", "i")

    html_content = pyperclip.paste()
    soup = BeautifulSoup(html_content, "html.parser")
    if soup:
        return soup.get_text()
    return ""


def _walk(xml, row):
    """Recursively collect every tag (including nested tags) into the flat row."""
    if not xml:
        return

    for match in RX_RECURSIVE.finditer(xml):
        tag = match.group("tag")
        full = match.group(0)
        content = match.group("content")

        if row[tag] is None:
            row[tag] = full
        elif full not in row[tag]:
            row[tag] += "\n" + full

        _walk(content, row)


def extract_nested_data(xml):
    row = {tag: None for tag in ALL_TAGS}
    if xml:
        _walk(xml, row)
    return row


def setup_analysis_table(engine_out, table_name):
    cols_sql = ", ".join(f"{c} TEXT" for c in ALL_TAGS)
    sql = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {cols_sql},
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine_out.begin() as conn:
        conn.execute(text(sql))


def bulk_insert_tafsir(engine, table_name, raw_texts):
    rows = [extract_nested_data(t) for t in raw_texts if t]
    if not rows:
        return

    cols = ", ".join(ALL_TAGS)
    vals = ", ".join(f":{c}" for c in ALL_TAGS)
    stmt = text(f"INSERT INTO {table_name} ({cols}) VALUES ({vals})")

    with engine.begin() as conn:
        conn.execute(stmt, rows)

    print(f"Erfolg: {len(rows)} Datensätze in {table_name} eingefügt.")


PROMPT_PREFIX = """
Rolle: Daten-Analyst für Koranexegese (Tafsir).
Auftrag: Analyse und Annotation eines Exegese-Abschnitts unter strikter Einhaltung einer XML-Struktur.

INSTRUKTIONEN:
1. Analysiere den bereitgestellten Text tiefgreifend und zerlege ihn in seine funktionalen Bestandteile.
2. Kennzeichne JEDEN Bestandteil ausschließlich mit den Elementen aus der folgenden Variable:

import regex

RX_TAFSIR_XML = regex.compile(
    r"(?s)<(?P<tag>"
    r"isnad|matn|quran_verse|asbab_al_nuzul|linguistic_analysis|qiraat|"
    r"cross_references|hadith_support|opinions_of_scholars|fiqh_implications|"
    r"theological_points|historical_context|explanation|source|"
    r"balagha_analysis|nasikh_wa_mansukh|grammatical_parsing|etymology|"
    r"parabolic_meaning|sectarian_perspective|spiritual_lessons|"
    r"biographies_of_narrators|ijma_status|"
    r"reason_for_revelation_variants|legal_maxims|maqasid_al_sharia|"
    r"variant_interpretations|minority_opinions|majority_opinions|"
    r"literal_interpretation|metaphorical_interpretation|"
    r"contextual_scope|general_vs_specific|absolute_vs_restricted|"
    r"command_and_prohibition|rhetorical_devices|semantic_fields|"
    r"synonym_analysis_homonym_antonym_analysis|"
    r"chronological_order|meccan_medinan|"
    r"intertextual_links|israiliyyat|"
    r"philosophical_reflections|ethical_implications|"
    r"creedal_implications|aqidah_classification|"
    r"scientific_allusions|cosmological_notes|"
    r"social_norms|political_implications|"
    r"pedagogical_lessons|daawah_applications|"
    r"practical_guidance|ritual_implications|"
    r"disputed_terms|technical_definitions|"
    r"textual_variants|manuscript_evidence|"
    r"chain_evaluation|narrator_criticism|"
    r"comparative_tafsir|methodological_notes|"
    r"argument|summary|conclusion"
    r")>(?P<content>(?:[^<]|(?R))*?)</(?P=tag)>"
)

STRIKTE REGELN FÜR DIE AUSGABE:
- Literal Execution: Entferne, verändere oder kürze NIEMALS den Originalinhalt.
- Rekursion: Verschachtele Tags, wenn ein Element (z. B. <argument>) andere Elemente (z. B. <source>) enthält.
- Vollständigkeit: Der gesamte Input muss Teil der Antwort sein (Input ist Teilmenge des Outputs).
- Reinheit: Keine Einleitungen, Erklärungen oder Meta-Kommentare. Nur der annotierte Text.
- Schema-Treue: Nutze ausschließlich die Tags, die in der Variable RX_TAFSIR_XML definiert sind.
- Rekursive Deduplizierung: Das Speichern identischer, ineinander verschachtelter Elemente in derselben Datenkategorie (Ziel-Spalte) ist untersagt. 
- Wenn ein Element (Tag + Inhalt) bereits in der Ziel-Variable existiert, darf es trotz rekursiver Treffer kein zweites Mal konkateniert werden. 
- Dies gilt insbesondere für Selbstreferenzierung: Wenn ein Tag in sich selbst verschachtelt ist, wird nur die äußerste Instanz für diese spezifische Kategorie gewertet, während der Inhalt zur weiteren Extraktion nachgeordneter Tags rekursiv verarbeitet wird.

Hier folgt der Abschnitt einer Koranexegese:

"""

DBS = ["katheer", "waseet", "tabary", "sa3dy", "qortoby", "baghawy"]


def automate_gemini(db):
    db_path_in = (
        f"/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books/{db}.sqlite3"
    )
    db_path_out = f"/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books_annotated/{db}_annotated.sqlite3"

    engine_in = create_engine(f"sqlite:///{db_path_in}")
    metadata_in = MetaData()
    tafsir_table = Table(db, metadata_in, autoload_with=engine_in)

    engine_out = create_engine(f"sqlite:///{db_path_out}")
    target_table = f"tafsir_analysis_{db}"
    setup_analysis_table(engine_out, target_table)

    extracted_payloads = []

    with engine_in.connect() as connection:
        results = connection.execute(select(tafsir_table.c.text))

        for row in results:
            original_text = row[0]
            if not original_text:
                continue
            original_text = original_text.replace("<p>", "").replace("</p>", "")
            full_text = PROMPT_PREFIX + original_text
            pyperclip.copy(full_text)

            pyautogui.click(x=220, y=1053)
            # ChatGPT
            # pyautogui.click(x=597, y=933)
            # Gemini
            pyautogui.click(x=711, y=879)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.5)
            pyautogui.press("enter")

            print("Warte auf Antwort von Gemini...")
            time.sleep(20)

            extracted_text = get_code_from_devtools()

            if not extracted_text:
                print("Kein Code gefunden.")
                break

            extracted_payloads.append(extracted_text)
            print("Antwort gespeichert. Nächster Durchgang...")

    bulk_insert_tafsir(engine_out, target_table, extracted_payloads)


if __name__ == "__main__":
    try:
        for db_name in DBS:
            automate_gemini(db_name)
            break
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
