import time
from concurrent.futures import ThreadPoolExecutor
import pyautogui
import pyperclip
import regex
from bs4 import BeautifulSoup
from sqlalchemy import MetaData, Table, create_engine, select, text
from ocr import OCRWatcher

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05
PRIMARY_TAGS = {
    "isnad": "Die Übertragungskette von Personen, die zur eigentlichen Aussage (Hadith Matn) führt.",
    "matn": "Der eigentliche Wortlaut oder Haupttext einer überlieferten Aussage (Hadith), abzüglich der Übertragungskette.",
    "source": "Die explizite Nennung eines Werkes bzw. Primärquellen-Gebers (z. B. 'Überliefert bei Buchari').",
    "quran_verse": "Direktes Zitat aus dem Koran im arabischen Originalwortlaut.",
}

SECONDARY_TAGS = {
    "command_and_prohibition": "Textstellen, die explizite Gebote (Amr) oder Verbote (Nahy) aus dem Vers ableiten.",
    "chain_evaluation": "Fachliche Bewertung der Qualität einer Überlieferungskette (z. B. Sahih, Da'if, Hassan).",
    "narrator_criticism": "Detaillierte Analyse oder Kritik einzelner Personen innerhalb einer Übertragungskette (Ilm al-Rijal).",
    "asbab_al_nuzul": "Berichte über den spezifischen historischen Anlass oder den Kontext der Offenbarung eines Verses.",
    "hadith_support": "Einbeziehung prophetischer Überlieferungen zur Untermauerung der Exegese.",
    "opinions_of_scholars": "Zusammenfassung oder direktes Zitat von Deutungen klassischer Exegeten (Tafsir-Gelehrte).",
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

BLOCK_TAG = "tafsir_section_block"
CHUNK_TAG = "tafsir_chunk"

watcher_a = OCRWatcher(17, 146, 712, 842)
watcher_b = OCRWatcher(38, 2, 83, 35)


def cleanup_cycle(
    batch,
    executor,
    engine_out,
    section_table,
    block_table,
    chunk_table,
    flush_batch=False,
):
    """
    Fetch the current response, optionally flush the batch, then hard-refresh and reset
    devtools/clipboard to keep the browser snappy.
    """
    extracted_text = get_code_from_devtools()
    if extracted_text:
        batch.append(extracted_text)

    if flush_batch and batch:
        executor.submit(
            bulk_insert_tafsir,
            engine_out,
            section_table,
            block_table,
            chunk_table,
            list(batch),
        )
        batch.clear()

    pyautogui.click(x=220, y=1053)
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "shift", "r")
    watcher_window_reload = watcher_b.run()
    if watcher_window_reload is True:
        pyautogui.moveTo(x=1274, y=940, duration=0.15)
        time.sleep(0.5)
        pyautogui.click()
        pyautogui.moveTo(x=1377, y=869, duration=0.15)
        time.sleep(0.5)
        pyautogui.click()
        print("Antwort gespeichert. Nächster Durchgang...")
    pyperclip.copy("")  # free clipboard buffer
    time.sleep(0.5)
    pyautogui.click(x=220, y=1053)
    return extracted_text


def get_code_from_devtools():
    pyautogui.hotkey("ctrl", "f")
    time.sleep(0.5)
    # ChatGPT
    # search_term = "overflow-visible! px-0!"
    search_term = "code-container formatted ng-tns-"
    pyperclip.copy(search_term)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(1)
    pyautogui.moveTo(x=1421, y=1005)
    time.sleep(0.5)
    pyautogui.click()
    pyautogui.moveTo(x=814, y=124, duration=0.15)
    time.sleep(0.5)
    pyautogui.click()
    pyautogui.moveTo(x=1000, y=121, duration=0.15)
    time.sleep(0.5)
    pyautogui.click()
    time.sleep(0.5)
    pyautogui.hotkey("ctrl", "c")
    time.sleep(0.3)
    pyautogui.hotkey("ctrl", "shift", "i")
    time.sleep(0.3)
    pyautogui.click(x=220, y=1053)

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


def extract_section_blocks(xml, tafsir_section_id):
    if not xml:
        return []

    try:
        soup = BeautifulSoup(xml, "xml")
    except Exception:
        return []

    blocks = soup.find_all(BLOCK_TAG)
    if not blocks:
        return []

    block_rows = []
    for block in blocks:
        block_rows.append(
            {
                "tafsir_section_id": tafsir_section_id,
                "block": str(block),
            }
        )

    return block_rows


def extract_block_chunks(block_xml, tafsir_block_id):
    if not block_xml:
        return []

    try:
        soup = BeautifulSoup(block_xml, "xml")
    except Exception:
        return []

    chunks = soup.find_all(CHUNK_TAG)
    if not chunks:
        return []

    chunk_rows = []
    for chunk in chunks:
        chunk_rows.append(
            {
                "tafsir_chunks": tafsir_block_id,
                "chunk": str(chunk),
            }
        )
    return chunk_rows


def setup_analysis_tables(engine_out, section_table, block_table, chunk_table):
    with engine_out.begin() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL"))
        conn.execute(text("PRAGMA foreign_keys=ON"))
        cols_sql = ", ".join(f"{c} TEXT" for c in ALL_COLUMNS)
        sql = f"""
        CREATE TABLE IF NOT EXISTS {section_table} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {cols_sql},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        conn.execute(text(sql))

        block_sql = f"""
        CREATE TABLE IF NOT EXISTS {block_table} (
            tafsir_section_id INTEGER NOT NULL,
            block TEXT NOT NULL,
            FOREIGN KEY (tafsir_section_id) REFERENCES {section_table}(id) ON DELETE CASCADE
        );
        """
        conn.execute(text(block_sql))
        index_sql = f"""
        CREATE INDEX IF NOT EXISTS idx_{block_table}_section
        ON {block_table} (tafsir_section_id);
        """
        conn.execute(text(index_sql))

        chunk_sql = f"""
        CREATE TABLE IF NOT EXISTS {chunk_table} (
            tafsir_chunks INTEGER NOT NULL,
            chunk TEXT NOT NULL,
            FOREIGN KEY (tafsir_chunks) REFERENCES {block_table}(rowid) ON DELETE CASCADE
        );
        """
        conn.execute(text(chunk_sql))
        chunk_index_sql = f"""
        CREATE INDEX IF NOT EXISTS idx_{chunk_table}_block
        ON {chunk_table} (tafsir_chunks);
        """
        conn.execute(text(chunk_index_sql))


def bulk_insert_tafsir(engine, section_table, block_table, chunk_table, raw_texts):
    rows = [t for t in raw_texts if t]
    if not rows:
        return

    section_cols = ", ".join(ALL_COLUMNS)
    section_vals = ", ".join(f":{c}" for c in ALL_COLUMNS)
    section_stmt = text(
        f"INSERT INTO {section_table} ({section_cols}) VALUES ({section_vals})"
    )

    block_stmt = text(
        f"INSERT INTO {block_table} (tafsir_section_id, block) VALUES (:tafsir_section_id, :block)"
    )

    chunk_stmt = text(
        f"INSERT INTO {chunk_table} (tafsir_chunks, chunk) VALUES (:tafsir_chunks, :chunk)"
    )

    block_total = 0
    chunk_total = 0
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        for raw in rows:
            section_row = extract_nested_data(raw)
            section_result = conn.execute(section_stmt, section_row)
            section_id = section_result.lastrowid
            if section_id is None:
                section_id = conn.exec_driver_sql("SELECT last_insert_rowid()").scalar()

            block_rows = extract_section_blocks(raw, section_id)
            if not block_rows:
                block_rows = [
                    {"tafsir_section_id": section_id, "block": raw},
                ]

            for block_row in block_rows:
                block_result = conn.execute(block_stmt, block_row)
                block_id = block_result.lastrowid
                if block_id is None:
                    block_id = conn.exec_driver_sql(
                        "SELECT last_insert_rowid()"
                    ).scalar()

                block_total += 1
                chunk_rows = extract_block_chunks(block_row["block"], block_id)
                if not chunk_rows:
                    chunk_rows = [
                        {"tafsir_chunks": block_id, "chunk": block_row["block"]}
                    ]

                conn.execute(chunk_stmt, chunk_rows)
                chunk_total += len(chunk_rows)

    print(f"Erfolg: {len(rows)} Datensätze in {section_table} eingefügt.")
    print(
        f"Erfolg: {block_total} Tafsir_section_block-Einträge in {block_table} eingefügt."
    )
    print(f"Erfolg: {chunk_total} Tafsir_chunk-Einträge in {chunk_table} eingefügt.")


PROMPT_PREFIX = f"""
Rolle: Daten-Analyst für Koranexegese (Tafsir).
Auftrag: Analyse und Annotation eines Exegese-Abschnitts unter strikter Einhaltung einer XML-Struktur.

INSTRUKTIONEN:
1. Analysiere den bereitgestellten Text tiefgreifend und zerlege ihn in seine funktionalen Bestandteile.
2. Kennzeichne JEDEN Bestandteil ausschließlich mit den Elementen aus der folgenden Variable:
3. Segmentiere die <tafsir_section> in <tafsir_section_block>-Elemente basierend auf strikter **semantischer Geschlossenheit**. WICHTIG: Vermeide kleinteilige Fragmentierung. Fasse zusammengehörige Inhalte (z. B. komplette Hadith-Erörterungen inklusive Isnad/Matn/Bewertung, abgeschlossene juristische Herleitungen oder volle thematische Einheiten) in einem einzigen, großen Block zusammen. Der `innerText` jedes Blocks muss für sich alleinstehend inhaltlich verständlich und der Kontext gewahrt bleiben.
4. Bewahre die Originalreihenfolge der Passage und ordne jedes <tafsir_section_block> eindeutig seiner übergeordneten <tafsir_section> zu (Many-to-One-Zuordnung ohne inhaltliche Überschneidung zwischen Blöcken).
5. Unterteile jede <tafsir_section_block> weiter in <tafsir_chunk>-Elemente, wobei jedes Chunk genau eine inhaltliche Einheit abbildet (z.B. ein Isnad, der zugehörige Hadith/Matn, Meinungen, erklärende Passagen). Reihenfolge beibehalten, keine Überschneidungen zwischen Chunks.

"Kategorie der 'Null-Toleranz'. Diese Elemente bilden das Skelett jeder Exegese. Eine Fehlklassifizierung oder das Auslassen bei eindeutigem Vorkommen gilt als struktureller Fehler."
"Erzwinge höchste Präzision. Jeder Korantext MUSS als <quran_verse> markiert sein. Jede Namenskette MUSS als <isnad> gekennzeichnet werden. Jede namentliche Nennung eines Werkes, Autors oder Primärquellen-Gebers MUSS als <source> identifiziert werden. Jede direkte oder indirekte Deutung klassischer Exegeten MUSS <opinions_of_scholars> umschließen. Der eigentliche inhaltliche Wortlaut einer Überlieferung abzüglich der Kette MUSS als <matn> definiert werden."
{PRIMARY_TAGS}
"Funktionale Erweiterungen, die den Gehalt der Kern-Elemente präzisieren. Sie sollen markiert werden, wenn die Indikatoren (z.B. 'wegen...', 'das bedeutet rechtlich...', 'sprachlich...') explizit im Text stehen.",
{SECONDARY_TAGS}
"Spezialkategorien für tiefe Fachanalysen. Diese Tags dürfen NUR verwendet werden, wenn der Treffer zu 100% eindeutig ist (z.B. explizite Erwähnung von Rhetorik, Abrogation oder wissenschaftlichen Fakten). Im Zweifelsfall weglassen, um Rauschen zu vermeiden.",
"Threshold-Maximum. Nutze diese Tags nur als 'Scharfschütze'. Ein False-Positive in dieser Kategorie wiegt schwerer als ein fehlender Tag."
{REMAINING_ALL_TAGS}


STRIKTE REGELN FÜR DIE AUSGABE:
- Format: Gib die komplette Antwort ausschließlich innerhalb eines ```xml``` Codeblocks zurück.
- Literal Execution: Entferne, verändere oder kürze NIEMALS den Originalinhalt.
- Rekursion: Verschachtele Tags, wenn ein Element (z. B. <argument>) andere Elemente (z. B. <source>) enthält.
- Vollständigkeit: Der gesamte Input muss Teil der Antwort sein (Input ist Teilmenge des Outputs).
- Reinheit: Keine Einleitungen, Erklärungen oder Meta-Kommentare. Nur der annotierte Text.
- Validierung: Führe vor jeder Ausgabe eine vollständige Prüfung der XML-Struktur auf Wohlförmigkeit durch.
- Exklusivität: Die Antwort darf ausschließlich aus wohlgeformtem, syntaktisch korrektem XML bestehen; keinerlei zusätzlicher Text, Einleitungen oder Zusätze sind zulässig.
- Schema-Treue: Nutze ausschließlich die Tags, die in der Variable RX_TAFSIR_XML definiert sind.
- Rekursive Deduplizierung: Das Speichern identischer, ineinander verschachtelter Elemente in derselben Datenkategorie (Ziel-Spalte) ist untersagt. 
- Wenn ein Element (Tag + Inhalt) bereits in der Ziel-Variable existiert, darf es trotz rekursiver Treffer kein zweites Mal konkateniert werden. 
- Dies gilt insbesondere für Selbstreferenzierung: Wenn ein Tag in sich selbst verschachtelt ist, wird nur die äußerste Instanz für diese spezifische Kategorie gewertet, während der Inhalt zur weiteren Extraktion nachgeordneter Tags rekursiv verarbeitet wird.

In meiner Nachricht die ich an dich sende, ist der Abschnitt einer Koranexegese:

"""

DBS = ["katheer", "waseet", "tabary", "sa3dy", "qortoby", "baghawy"]


def automate_gemini(db):
    i = 0
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
    block_table = f"{target_table}_blocks"
    chunk_table = f"{target_table}_chunks"
    setup_analysis_tables(engine_out, target_table, block_table, chunk_table)

    with engine_in.connect() as connection, ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        results = connection.execute(select(tafsir_table.c.text))
        batch = []

        for row in results:
            i += 1
            extracted_text = None
            original_text = row[0]
            if not original_text:
                continue
            pyperclip.copy(
                PROMPT_PREFIX
                + " ".join(
                    original_text.replace("<p>", " ").replace("</p>", " ").split()
                )
            )
            pyautogui.click(x=220, y=1053)  # open browser

            # ChatGPT
            # pyautogui.click(x=597, y=933)
            # Gemini
            time.sleep(1.5)
            pyautogui.hotkey("ctrl", "end")
            time.sleep(1.0)

            # 1. Maus stabil auf Zielposition bringen und Fokus erzwingen
            for _ in range(3):
                pyautogui.moveTo(927, 891, duration=0.15)
                pyautogui.click()
                time.sleep(0.2)

            # 2. Sicherstellen, dass ein Eingabefeld aktiv ist
            pyautogui.hotkey("ctrl", "a")
            time.sleep(0.1)
            pyautogui.press("backspace")
            time.sleep(0.2)

            # 3. Inhalt einfügen
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.6)

            # 4. Absenden (Enter mehrfach + Delay)
            for _ in range(2):
                pyautogui.press("enter")
                time.sleep(0.2)

            time.sleep(5)

            print("Warte auf Antwort von Gemini...")
            pyautogui.hotkey("ctrl", "shift", "i")
            time.sleep(1.5)
            pyautogui.moveTo(x=733, y=351, duration=0.15)
            pyautogui.click()
            pyautogui.hotkey("ctrl", "end")
            time.sleep(2)
            pyautogui.moveTo(x=972, y=99, duration=0.15)
            pyautogui.click()

            watcher_gemini_response = watcher_a.run()
            if watcher_gemini_response is True:
                if i % 5 == 0:
                    extracted_text = cleanup_cycle(
                        batch,
                        executor,
                        engine_out,
                        target_table,
                        block_table,
                        chunk_table,
                        flush_batch=i % 5 == 0,
                    )
                else:
                    extracted_text = get_code_from_devtools()
                    if extracted_text:
                        batch.append(extracted_text)

            if not extracted_text:
                print("Kein Code gefunden.")
                break

            print("Antwort gespeichert. Nächster Durchgang...")

        if batch:
            executor.submit(
                bulk_insert_tafsir,
                engine_out,
                target_table,
                block_table,
                chunk_table,
                list(batch),
            )


if __name__ == "__main__":
    try:
        for db_name in DBS:
            automate_gemini(db_name)
    except KeyboardInterrupt:
        print("\nAbgebrochen durch Benutzer.")
