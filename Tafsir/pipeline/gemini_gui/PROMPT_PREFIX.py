from .TAGS import PRIMARY_TAGS, SECONDARY_TAGS, REMAINING_ALL_TAGS

PROMPT_PREFIX = f"""
Rolle: Daten-Analyst für Koranexegese (Tafsir).
Auftrag: Analyse und Annotation eines Exegese-Abschnitts unter strikter Einhaltung einer XML-Struktur.

INSTRUKTIONEN:
1. Analysiere den bereitgestellten Text tiefgreifend und zerlege ihn in seine funktionalen Bestandteile.
2. Kennzeichne JEDEN Bestandteil ausschließlich mit den Elementen aus der folgenden Variable:
3. Segmentiere die <tafsir_section> in <tafsir_section_block>-Elemente basierend auf strikter **semantischer Geschlossenheit**. WICHTIG: Vermeide kleinteilige Fragmentierung. Fasse zusammengehörige Inhalte (z. B. komplette Hadith-Erörterungen inklusive Isnad/hadith/Bewertung, abgeschlossene juristische Herleitungen oder volle thematische Einheiten) in einem einzigen, großen Block zusammen anstatt sie auf ihr zutreffenden Bestandteil zuschneiden und dabei den semantischen und grammatikalisch logischen Kontext zu verlieren. Auch Satzzeichen sollen nicht getrennt werden sondern innerhalb eines tags geöffnet und geschlossen sein. Keine halben Klammern oder Klammern ausserhalb der xml Tags. Der `innerText` jedes Blocks muss für sich alleinstehend inhaltlich verständlich und der Kontext gewahrt bleiben.
4. Bewahre die Originalreihenfolge der Passage und ordne jedes <tafsir_section_block> eindeutig seiner übergeordneten <tafsir_section> zu (Many-to-One-Zuordnung ohne inhaltliche Überschneidung zwischen Blöcken).
5. Unterteile jede <tafsir_section_block> weiter in <tafsir_chunk>-Elemente, wobei jedes Chunk genau die kleinste inhaltliche/semantische Einheit abbildet (dieser Chunk zeigt bspw. worauf bezieht sich diese quelle/dieser hadith/diese Einstufung ... und gruppiert es in einen Chunk. Es bündelt diese Einzelbestandteile also wie Wörter in einem Satz). Reihenfolge beibehalten, keine Überschneidungen zwischen Chunks. Ein Chunk ist die kleinste semantische Einheit.

"Kategorie der 'Null-Toleranz'. Diese Elemente bilden das Skelett jeder Exegese. Eine Fehlklassifizierung oder das Auslassen bei eindeutigem Vorkommen gilt als struktureller Fehler."
"Erzwinge höchste Präzision. Jeder Korantext MUSS als <quran_verse> markiert sein. Jede Namenskette MUSS als <isnad> gekennzeichnet werden. Jede namentliche Nennung eines Werkes, Autors oder Primärquellen-Gebers MUSS als <source> identifiziert werden. Jede direkte oder indirekte Deutung klassischer Exegeten MUSS <opinions_of_scholars> umschließen. Der eigentliche inhaltliche Wortlaut einer Überlieferung, wenn möglich abzüglich der Kette (möglich im Sinne von: ohne den Hadith zu schneiden) MUSS als <hadith> definiert werden inkl. dem was zum Hadith dazugehört wie bspw: ' حين رقى بها الرجل السليم ، فقال له رسول الله صلى الله عليه وسلم :'."
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
- Schema-Treue: Nutze ausschließlich die Tags, die in der Dictionarydefiniert sind.
- Rekursive Deduplizierung: Das Speichern identischer, ineinander verschachtelter Elemente in derselben Datenkategorie (Ziel-Spalte) ist untersagt. 
- Wenn ein Element (Tag + Inhalt) bereits in der Ziel-Variable existiert, darf es trotz rekursiver Treffer kein zweites Mal konkateniert werden. 
- Dies gilt insbesondere für Selbstreferenzierung: Wenn ein Tag in sich selbst verschachtelt ist, wird nur die äußerste Instanz für diese spezifische Kategorie gewertet, während der Inhalt zur weiteren Extraktion nachgeordneter Tags rekursiv verarbeitet wird.

In meiner Nachricht die ich an dich sende, ist der Abschnitt einer Koranexegese:

"""

if __name__ == "__main__":
    print(PROMPT_PREFIX)
