import time
from concurrent.futures import ThreadPoolExecutor

import pyautogui
import pyperclip
import regex
from bs4 import BeautifulSoup
from sqlalchemy import MetaData, Table, create_engine, select, text


PRIMARY_TAGS = {
    "isnad": "Die Übertragungskette von Gewährspersonen, die zu einer Aussage (Hadith oder Gelehrtenmeinung) führt.",
    "matn": "Der eigentliche Wortlaut oder Haupttext einer überlieferten Aussage (Hadith), abzüglich der Übertragungskette.",
    "source": "Die explizite Nennung eines Werkes, Autors oder Primärquellen-Gebers (z. B. 'Überliefert bei Buchari' oder 'Sagt Ibn Kathir').",
    "quran_verse": "Direktes Zitat aus dem Koran im arabischen Originalwortlaut.",
    "opinions_of_scholars": "Zusammenfassung oder direktes Zitat von Deutungen klassischer Exegeten (Tafsir-Gelehrte).",
}

SECONDARY_TAGS = {
    "command_and_prohibition": "Textstellen, die explizite Gebote (Amr) oder Verbote (Nahy) aus dem Vers ableiten.",
    "chain_evaluation": "Fachliche Bewertung der Qualität einer Überlieferungskette (z. B. Sahih, Da'if, Hassan).",
    "narrator_criticism": "Detaillierte Analyse oder Kritik einzelner Personen innerhalb einer Übertragungskette (Ilm al-Rijal).",
    "asbab_al_nuzul": "Berichte über den spezifischen historischen Anlass oder den Kontext der Offenbarung eines Verses.",
    "hadith_support": "Einbeziehung prophetischer Überlieferungen zur Untermauerung der Exegese.",
    "explanation": "Allgemeiner erläuternder Kommentar des Autors zum Verständnis des Textes.",
}

REMAINING_ALL_TAGS = {
    "linguistic_analysis": "Untersuchung von Wortbedeutungen, Morphologie oder allgemeiner Sprachverwendung.",
    "qiraat": "Hinweise auf verschiedene anerkannte Lesarten des Korantextes.",
    "cross_references": "Verweise auf andere Koranstellen, die den aktuellen Vers erläutern.",
    "fiqh_implications": "Ableitung von rechtlichen Bestimmungen und juristischen Regeln aus dem Vers.",
    "theological_points": "Glaubenslehre (Aqidah) betreffende Schlussfolgerungen oder dogmatische Fragen.",
    "historical_context": "Allgemeine historische Rahmenbedingungen zur Zeit der Offenbarung (nicht spezifisch Asbab al-Nuzul).",
    "balagha_analysis": "Analyse der rhetorischen Schönheit, Eloquenz und Stilistik (Rhetorik).",
    "nasikh_wa_mansukh": "Diskussion über abrogierende (aufhebende) und abrogierte Verse.",
    "grammatical_parsing": "Syntax-Analyse (I'rab) und grammatikalische Zerlegung der Sätze.",
    "etymology": "Untersuchung des Ursprungs und der historischen Entwicklung einzelner Wörter.",
    "parabolic_meaning": "Deutung von Gleichnissen, Metaphern und allegorischen Darstellungen.",
    "sectarian_perspective": "Interpretation aus Sicht einer spezifischen theologischen Schule (z. B. Mu'tazila, Schia).",
    "spiritual_lessons": "Ethische, moralische oder sufisch-spirituelle Einsichten für das Seelenleben.",
    "biographies_of_narrators": "Biografische Informationen über die in der Isnad genannten Personen.",
    "ijma_status": "Feststellung eines Konsenses unter den Gelehrten zu einer bestimmten Auslegung.",
    "reason_for_revelation_variants": "Diskussion über unterschiedliche Berichte zum Offenbarungsanlass.",
    "legal_maxims": "Anwendung allgemeiner Rechtsgrundsätze (Qawa'id Fiqhiyya).",
    "maqasid_al_sharia": "Einordnung des Verses in die übergeordneten Ziele des islamischen Rechts.",
    "variant_interpretations": "Gegenüberstellung verschiedener, sich teils widersprechender Deutungsmöglichkeiten.",
    "minority_opinions": "Kennzeichnung von Auslegungen, die nur von einer Minderheit vertreten werden.",
    "majority_opinions": "Kennzeichnung der von der Mehrheit der Gelehrten (Jumhur) vertretenen Ansicht.",
    "literal_interpretation": "Auslegung basierend auf der rein äußerlichen, wortwörtlichen Bedeutung (Zahir).",
    "metaphorical_interpretation": "Auslegung, die eine übertragene, bildliche Bedeutung (Ta'wil) annimmt.",
    "contextual_scope": "Bestimmung des Geltungsbereichs eines Verses basierend auf dem Kontext.",
    "general_vs_specific": "Unterscheidung, ob eine Aussage allgemein ('Amm) oder spezifisch (Khass) gemeint ist.",
    "absolute_vs_restricted": "Unterscheidung zwischen uneingeschränkten (Mutlaq) und bedingten (Muqayyad) Aussagen.",
    "rhetorical_devices": "Identifikation spezifischer rhetorischer Figuren (z. B. Metonymie, Ironie).",
    "semantic_fields": "Analyse von Wortgruppen, die einen gemeinsamen Bedeutungsraum abdecken.",
    "synonym_analysis_homonym_antonym_analysis": "Vergleich von sinnverwandten, gleichlautenden oder gegensätzlichen Begriffen.",
    "chronological_order": "Einordnung des Verses in die zeitliche Abfolge der Offenbarung.",
    "meccan_medinan": "Klassifizierung, ob ein Vers in Mekka oder Medina offenbart wurde.",
    "intertextual_links": "Bezüge zu anderen religiösen Texten oder literarischen Werken.",
    "israiliyyat": "Hinweise auf Erzählungen biblischen Ursprungs oder jüdisch-christlicher Tradition.",
    "philosophical_reflections": "Abstrakte philosophische Überlegungen, die über die reine Exegese hinausgehen.",
    "ethical_implications": "Direkte Ableitung moralischer Verhaltensregeln für das Individuum.",
    "creedal_implications": "Spezifische Auswirkungen auf das Glaubensbekenntnis.",
    "aqidah_classification": "Systematische Zuordnung zu Kategorien der Glaubenslehre.",
    "scientific_allusions": "Interpretation von Versen in Bezug auf naturwissenschaftliche Erkenntnisse.",
    "cosmological_notes": "Anmerkungen zur Struktur des Universums, Himmel und Erde.",
    "social_norms": "Bezug auf gesellschaftliche Gepflogenheiten und soziale Strukturen.",
    "political_implications": "Bezüge zu Herrschaft, Staatswesen und politischer Ordnung.",
    "pedagogical_lessons": "Erziehungswissenschaftliche oder didaktische Rückschlüsse.",
    "daawah_applications": "Relevanz des Verses für die Glaubensverkündung und Mission.",
    "practical_guidance": "Konkrete Handlungsempfehlungen für den Alltag des Gläubigen.",
    "ritual_implications": "Auswirkungen auf die Durchführung gottesdienstlicher Handlungen (Ibadat).",
    "disputed_terms": "Analyse von Begriffen, deren Bedeutung unter Gelehrten stark umstritten ist.",
    "technical_definitions": "Definition von Fachbegriffen innerhalb der islamischen Wissenschaften.",
    "textual_variants": "Untersuchung von Abweichungen in verschiedenen Manuskripten oder Kodizes.",
    "manuscript_evidence": "Verweise auf physische Beweise in alten Koranhandschriften.",
    "comparative_tafsir": "Methodischer Vergleich zwischen verschiedenen Tafsir-Werken.",
    "methodological_notes": "Anmerkungen des Exegeten zu seiner eigenen methodischen Vorgehensweise.",
    "argument": "Logische Beweisführung oder dialektische Argumentation zur Stützung einer These.",
    "summary": "Kurze Zusammenfassung eines längeren Abschnitts oder einer Argumentationskette.",
    "conclusion": "Abschließendes Urteil oder Fazit am Ende einer Analyse.",
}

ALL_TAGS = (
    list(PRIMARY_TAGS.keys())
    + list(SECONDARY_TAGS.keys())
    + list(REMAINING_ALL_TAGS.keys())
)
RAW_COL = "extracted_text_full"
ALL_COLUMNS = ALL_TAGS + [RAW_COL]

RX_RECURSIVE = regex.compile(
    r"(?s)<(?P<tag>" + "|".join(ALL_TAGS) + r")>(?P<content>(?:[^<]|(?R))*)</(?P=tag)>"
)


def get_code_from_devtools():
    pyautogui.hotkey("ctrl", "shift", "i")
    time.sleep(2)

    pyautogui.hotkey("ctrl", "f")
    time.sleep(1.5)
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
    time.sleep(1.2)
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
    row[RAW_COL] = xml
    return row


def setup_analysis_table(engine_out, table_name):
    cols_sql = ", ".join(f"{c} TEXT" for c in ALL_COLUMNS)
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

    cols = ", ".join(ALL_COLUMNS)
    vals = ", ".join(f":{c}" for c in ALL_COLUMNS)
    stmt = text(f"INSERT INTO {table_name} ({cols}) VALUES ({vals})")

    with engine.begin() as conn:
        conn.execute(stmt, rows)

    print(f"Erfolg: {len(rows)} Datensätze in {table_name} eingefügt.")


PROMPT_PREFIX = f"""
Rolle: Daten-Analyst für Koranexegese (Tafsir).
Auftrag: Analyse und Annotation eines Exegese-Abschnitts unter strikter Einhaltung einer XML-Struktur.

INSTRUKTIONEN:
1. Analysiere den bereitgestellten Text tiefgreifend und zerlege ihn in seine funktionalen Bestandteile.
2. Kennzeichne JEDEN Bestandteil ausschließlich mit den Elementen aus der folgenden Variable:

"Kategorie der 'Null-Toleranz'. Diese Elemente bilden das Skelett jeder Exegese. Eine Fehlklassifizierung oder das Auslassen bei eindeutigem Vorkommen gilt als struktureller Fehler."
"Erzwinge höchste Präzision. Jeder Korantext MUSS als <quran_verse> markiert sein. Jede Namenskette MUSS als <isnad> gekennzeichnet werden. Jede namentliche Nennung eines Werkes, Autors oder Primärquellen-Gebers MUSS als <source> identifiziert werden. Jede direkte oder indirekte Deutung klassischer Exegeten MUSS <opinions_of_scholars> umschließen. Der eigentliche inhaltliche Wortlaut einer Überlieferung abzüglich der Kette MUSS als <matn> definiert werden."
{PRIMARY_TAGS}
"Funktionale Erweiterungen, die den Gehalt der Kern-Elemente präzisieren. Sie sollen markiert werden, wenn die Indikatoren (z.B. 'wegen...', 'das bedeutet rechtlich...', 'sprachlich...') explizit im Text stehen.",
{SECONDARY_TAGS}
"Spezialkategorien für tiefe Fachanalysen. Diese Tags dürfen NUR verwendet werden, wenn der Treffer zu 100% eindeutig ist (z.B. explizite Erwähnung von Rhetorik, Abrogation oder wissenschaftlichen Fakten). Im Zweifelsfall weglassen, um Rauschen zu vermeiden.",
"Threshold-Maximum. Nutze diese Tags nur als 'Scharfschütze'. Ein False-Positive in dieser Kategorie wiegt schwerer als ein fehlender Tag."
{REMAINING_ALL_TAGS}


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

    engine_out = create_engine(
        f"sqlite:///{db_path_out}", connect_args={"check_same_thread": False}
    )
    target_table = f"tafsir_analysis_{db}"
    setup_analysis_table(engine_out, target_table)

    with engine_in.connect() as connection, ThreadPoolExecutor(
        max_workers=4
    ) as executor:
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
            pyautogui.hotkey("ctrl", "a")
            pyautogui.press("backspace")
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1.5)
            pyautogui.press("enter")

            print("Warte auf Antwort von Gemini...")
            time.sleep(60)

            extracted_text = get_code_from_devtools()

            if not extracted_text:
                print("Kein Code gefunden.")
                break

            executor.submit(
                bulk_insert_tafsir, engine_out, target_table, [extracted_text]
            )
            print("Antwort gespeichert. Nächster Durchgang...")


if __name__ == "__main__":
    try:
        for db_name in DBS:
            automate_gemini(db_name)
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
