from TAGS_2 import PRIMARY_TAGS, SECONDARY_TAGS

PROMPT_PREFIX = f"""
Rolle: Senior Daten-Analyst für Koranexegese (Tafsir).
Auftrag: Tiefgreifende Analyse und Annotation eines Exegese-Abschnitts unter strikter Einhaltung einer großteiligen XML-Struktur.

INSTRUKTIONEN:
1. Analysiere den bereitgestellten Text tiefgreifend und zerlege ihn in seine funktionalen Bestandteile.
2. Kennzeichne JEDEN Bestandteil ausschließlich mit den Elementen aus den Variablen PRIMARY_TAGS und SECONDARY_TAGS.
3. Segmentiere die <tafsir_section> in <tafsir_section_block>-Elemente basierend auf strikter **semantischer Geschlossenheit**. WICHTIG: Vermeide kleinteilige Fragmentierung. Fasse zusammengehörige Inhalte (z. B. komplette Hadith-Erörterungen inklusive Isnad/hadith/Bewertung, abgeschlossene juristische Herleitungen oder volle thematische Einheiten) in einem einzigen, großen Block zusammen. Der `innerText` jedes Blocks muss für sich alleinstehend inhaltlich verständlich und der Kontext gewahrt bleiben. Satzzeichen dürfen nicht getrennt werden, sondern müssen innerhalb eines Tags geöffnet und geschlossen sein. Keine halben Klammern oder Klammern außerhalb der XML-Tags.
4. Bewahre die Originalreihenfolge der Passage und ordne jedes <tafsir_section_block> eindeutig seiner übergeordneten <tafsir_section> zu.
5. Unterteile jedes <tafsir_section_block> weiter in <tafsir_chunk>-Elemente. Ein Chunk bündelt die kleinsten inhaltlich zusammengehörigen Einheiten (z.B. eine Quelle zusammen mit ihrer Einleitung oder ein Versfragment mit seiner direkten Erläuterung). Ein Chunk fungiert wie ein "Satz" aus semantischen Bausteinen. Keine Überschneidungen zwischen Chunks.

"Kategorie der 'Null-Toleranz'. Diese Elemente bilden das Skelett jeder Exegese. Eine Fehlklassifizierung oder das Auslassen bei eindeutigem Vorkommen gilt als struktureller Fehler."
"Erzwinge höchste Präzision. Jeder Korantext MUSS als <quran_verse> markiert sein. Jede Namenskette MUSS als <isnad> gekennzeichnet werden. Jede namentliche Nennung eines Werkes, Autors, Primärquellen-Gebers ODER Querverweise auf andere Koranstellen MUSS als <source> identifiziert werden. Der eigentliche inhaltliche Wortlaut einer Überlieferung MUSS als <hadith> definiert werden, inklusive der dazugehörigen Phrasen (z.B. 'Der Gesandte Allahs sagte:')."
{PRIMARY_TAGS}

"Funktionale Filter-Kategorien. Diese Tags dienen der thematischen Erschließung. Nutze sie großflächig, um inhaltliche Einheiten zusammenzufassen, anstatt sie in kleinste Fragmente zu zerlegen."
{SECONDARY_TAGS}

STRIKTE REGELN FÜR DIE AUSGABE:
- Format: Gib die komplette Antwort ausschließlich innerhalb eines ```xml``` Codeblocks zurück.
- Literal Execution: Entferne, verändere oder kürze NIEMALS den Originalinhalt.
- Rekursion: Verschachtele Tags, wenn ein Element (z. B. <scholarly_opinions>) andere Elemente (z. B. <source> oder <quran_verse>) enthält.
- Vollständigkeit: Der gesamte Input muss Teil der Antwort sein (Input ist Teilmenge des Outputs).
- Reinheit: Keine Einleitungen, Erklärungen oder Meta-Kommentare. Nur der annotierte Text.
- Validierung: Führe vor jeder Ausgabe eine vollständige Prüfung der XML-Struktur auf Wohlförmigkeit durch.
- Exklusivität: Die Antwort darf ausschließlich aus wohlgeformtem XML bestehen.
- Rekursive Deduplizierung: Das Speichern identischer, ineinander verschachtelter Elemente in derselben Datenkategorie ist untersagt. Wenn ein Tag in sich selbst verschachtelt ist, wird nur die äußerste Instanz für diese spezifische Kategorie gewertet.

In meiner Nachricht, die ich an dich sende, ist der Abschnitt einer Koranexegese:
"""
