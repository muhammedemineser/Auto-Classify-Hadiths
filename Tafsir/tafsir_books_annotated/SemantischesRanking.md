# Semantisches Ranking der Wortarten (POS) im Arabischen

Dieses Ranking ordnet die Wortarten nach ihrer **lexikalischen Dichte** und ihrem Beitrag zur **Proposition** (Aussagegehalt) eines Satzes. Im Arabischen ist dies besonders relevant, da die Semantik stark an das Wurzel-Schema (Radikale) gebunden ist.

Mathematische Grundlage auf der das folgende ausgeführt wird ist jeweils: $Anteil  = Anteil_Dezimalzahl(z.B. 0.4)^ (- Häufigkeit des Wortes / Alle Wörter dieser Wortart)^ (Alle Wörter dieser Wortart / Häufigkeit des Wortes)

## 1. Das Verb (al-Fiʿl / الفعل) – Der Bedeutungsträger
**Anteil_Dezimalzahl:** ~40–50% (Sehr hoch)
**Begründung:**
* **Wurzelträger:** Das Verb enthält fast immer die semantische dreikonsonantige Wurzel (J-D-R), die die Kernbedeutung definiert.
* **Satzkern:** In verbalen Sätzen (die im Arabischen Standard sind) regiert das Verb die gesamte Struktur. Es diktiert, welche Akteure (Subjekt, Objekt) notwendig sind (Valenz).
* **Synthetische Dichte:** Ein einzelnes arabisches Verb enthält oft Informationen, die in anderen Sprachen mehrere Wörter benötigen: Handlung (Lexem), Zeit (Tempus), Person, Genus, Numerus und oft sogar das Objekt (durch Suffixe).
Stanza erkennt korrekt: **أكلتها** (akaltuhā) = "Ich habe sie gegessen" : (Original: ﺖﻠﻛﺃ | Lemma: ﻞﻛﺃ | POS: VERB
Original: ﺎﻫ | Lemma: ﻮﻫ | POS: PRON). das kann man Ausnutzen, indem man Kombinationen aus mehreren Wörtern aufwertet, da es die Wahrscheinlichkeit auf einen Treffer erhöht.

## 2. Das Nomen / Substantiv (al-Ism / الاسم) – Die Entität
**Anteil_Dezimalzahl:** ~30–35% (Hoch)
**Begründung:**
* **Referenz:** Es benennt die konkreten Akteure und Gegenstände. Ohne Nomen ist die Handlung des Verbs abstrakt und ziellos.
* **Semantische Stabilität:** Nomen tragen wie Verben die Semantik der Wurzel, sind aber statisch. In Nominalsätzen (Sätze ohne Verb) rücken sie auf Platz 1 der Wichtigkeit.
* **Iḍāfa-Konstruktionen:** Nomen können durch Genitivverbindungen komplexe Bedeutungen erzeugen, die spezifischer sind als einzelne Verben.
Auch Genitivverbindungen kann man mit Stanza herausstellen, um die betroffenen Tokens aufzuwerten: (for sentence in doc.sentences:
    words = sentence.words
    for i in range(len(words) - 1):
        current_word = words[i]
        next_word = words[i+1]
        
        # Prüfung auf Idāfa-Merkmal
        # 1. Wort: Kein Artikel (Indefinite/Cons) & oft Noun
        # 2. Wort: Genitiv (Case=Gen)
        is_mudaf = "Definite=Cons" in str(current_word.feats)
        is_mudaf_ilayh = "Case=Gen" in str(next_word.feats)
        
        if is_mudaf and is_mudaf_ilayh:
            print(f"Gefundene Genitivverbindung: {current_word.text} + {next_word.text}")
        
        # Debug-Ausgabe der Features
        printa(f"Wort: {current_word.text} | POS: {current_word.upos} | Feats: {current_word.feats}"))
Die erweiterte Iḍāfa-Kette (Silsilat al-Iḍāfa / سلسلة الإضافة)
Nicht nur zwei Wörter, sondern ganze Ketten können eine Einheit bilden (z.B. „Der Schlüssel der Tür des Hauses des Nachbarn“).

Muster: NOUN(Cons) + NOUN(Gen) + NOUN(Gen) ...

Ranking-Logik: Das erste Nomen ist der semantische „Besitz“, alle folgenden sind notwendige Spezifizierungen. Ohne die Kette ist das erste Wort zu vage.

NLP-Signal: nmod Verknüpfungen, die kaskadieren (A hängt an B, B hängt an C).

Somit werden Tokens nicht mehr Wortweise gewertet sondern teilweise in paaren, wodurch ihr Wert in der Bewertung erhöht wird und die Chance auf false positives verringert wird. Ein Token liefert also Kontext mit.
Wertung: Exponent += 1 für jedes folgende Nomen in der Kette. wobei für jedes Wort jeweils die Formel von $Anteil gilt 

## 3. Das Adjektiv (as-Sifa / الصفة) – Der Modifikator
**Anteil_Dezimalzahl:** ~10–15% (Mittel)
**Begründung:**
* **Qualifizierung:** Adjektive verfeinern die Bedeutung des Nomens, sind aber für den *Wahrheitswert* der Kernaussage oft nicht zwingend erforderlich (adjunktive Funktion).
* **Morphologische Abhängigkeit:** Im Arabischen folgt das Adjektiv dem Nomen in allen grammatischen Kategorien (Kongruenz), was seinen Status als "Diener" des Nomens unterstreicht.

## 4. Das Adverb / Umstandswort (az-Zarf / الظرف) – Der Kontext
**Anteil_Dezimalzahl:** ~5–10% (Gering bis Mittel)
**Begründung:**
* **Situierung:** Es verankert die Handlung in Zeit und Raum (z. B. "heute", "dort"). Es trägt Information bei, ändert aber selten die Kernhandlung selbst (außer bei verneinenden Partikeln, die manchmal hier eingeordnet werden).
* **Semantische Randstellung:** Es beantwortet das "Wann" oder "Wo", nicht das "Was" oder "Wer".

## 5. Die Partikel / Präposition (al-Harf / الحرف) – Der Klebstoff
**Anteil_Dezimalzahl:** < 5% (Gering / Rein Funktional)
**Begründung:**
* **Keine eigenständige Semantik:** Ein Harf (z. B. "fī" = in, "wa" = und) hat ohne Kontext keine lexikalische Bedeutung. Es existiert nur, um Beziehungen zwischen Nomen und Verben herzustellen.
* **Geschlossene Klasse:** Während Verben und Nomen unendlich erweitert werden können, ist die Anzahl der Partikel begrenzt und statisch. Ihre Funktion ist rein grammatikalisch-strukturell.
Alleine sind sie als Token unwichtig und nicht bewertbar, jedoch sind sie mit dem Begriff auf den sie sich beziehen Bedeutungsträger. Im Haus (fil bayt) ist etwas ganz anderes als auf dem Haus (alal bayt). Deshalb wird effizient der Klebstoff mit seinem Objekt gemeinsam tokenisiert.


Kandidatenranking:
Am Ende muss das Kandidaten Ranking so aussehen:
Top Level:
1. A=B
2. A=B mit minimalen Abweichungen.
Ca. 85-99% Identisch (Schätzung nur zur Veranschaulichung, da die 15% die entscheiden ob ein Kandidat raus fliegt nicht linear sind. Erklärung folgt). Prozentanteil / Anzahl der Token bzw. 0.15 * len(tokens). Einzelner Token * Gewichtung (Art des Wortes): wobei (fehlende oder zusätzliche) wichtige Worte schneller die 15% erreichen um den Kandidaten rauszukicken, während unwichtige exponentiell unwichtig wirken und alleine niemals 15% erreichen können.
Darin gibt es Szenarien wo die
Sequenz die selbe ist + etwas vorne und oder hinten
Oder selbe Sequenz - etwas vorne und oder hinten
Oder + und/oder - etwas dazwischen vias verca.
und falls: wieviel ist "mehr" und/oder "weniger" dazwischen?

Medium:
3. B beinhaltet A
Höhste Stufe innerhalb Stufe 3 ist A ist vollständig in B enthalten.
Darin gibt es aber auch Szenarien wo 
die Sequenz von A in B die selbe ist + etwas vorne und oder hinten
Oder selbe Sequenz - etwas vorne/und oder hinten
Oder etwas mehr und/oder weniger etwas dazwischen vias verca.
Wieviel +  und/oder - dazwischen?
Ca. 85-99% Identisch. Prozentanteil / Anzahl der Token. Einzelnes Wort * Gewichtung (Art des Wortes), wobei (fehlende oder zusätzliche) wichtige Worte schneller die 15% erreichen um den Kandidaten rauszukicken, während unwichtige exponentiell unwichtig wirken und alleine niemals 15% erreichen.
=> für kürzere Tokenanzahl von B höherer Rank, da die Länge die Ähnlichkeit beeinflusst

4. B ist eine Teilmenge von A
Die Szenarien bleiben gleich
5. Die selbe Tokensequenz von A kommt mit Unterbrechungen in B vor.
Die Szenarien bleiben gleich
6. B beinhaltet eine Teilmenge von A
Die Szenarien bleiben gleich

Wir produzieren jetzt: 
1. Den nötigen Code um einmal mit Stanza alles was wir brauchen auszurechnen und in einer Datenbank mit Referenz zur Quelle, sprich output ist:
Neue DB
Jede Hadith db eigener table und die txt auch eigener table
jeder table hat cols mit id (foreign key auf hadith db mit many (tokens) to one (hadith) beziehung), token, stanza analyseergebnissen für diesen token, seinem wert berechneten "wert" und ggf. seinem Kontext (Kette/Genitivverbindung/Adjektiv/Partikel...)
token selbst hat einen wert und die kontext-n-grams haben einen (logisch höheren) wert und sind logisch voneinander getrennt, sodass sie jeweils differenziert und unabhängig voneinander betrachtet werden können.
2. Den nötigen Code um die Mock Daten herzustellen, mit denen man die Situationen aus "Kandidatenranking" prüfen kann und das erwartete Verhalten verifizieren kann.
Z.B. 1 zu 1 wäre db gegen db selbst (gold_sample).
1 zu 1 wäre db +/- etwas Text gegen db selbst (gold sample[i]+gold sample[i-1][:5]). Also kleine Textmanipulation um eine leicht andere Version zu mocken. 
usw.
Das Sample bzw. die Mock Daten enthalten alle Gruppen
(
        if word_count < 8:
        return "micro"
    elif word_count < 15:
        return "very_short"
    elif word_count < 25:
        return "short"
    elif word_count < 40:
        return "short_medium"
    elif word_count < 60:
        return "medium"
    elif word_count < 90:
        return "medium_long"
    elif word_count < 130:
        return "long"
    elif word_count < 200:
        return "very_long"
    else:
        return "ultra_long"
)
3. Mit diesen Daten werden in unterschiedlichen Runs Schritt für Schrifft "Niedrigere" Fälle dazu geholt. Nur wenn alle bestehenden Ergebnisse so bleiben folgen weitere Fälle. Ziel ist: An den Parametern der Pipeline herumzuschrauben bis das Ergebnis genau das ist was in "Kandidatenranking" definiert wurde. Konkret:
Pipeline gibt für A=B Rang 1 -> weiter
Pipeline gibt für A=B Rang 1 und für A=B mit minimalen Abweichungen Rang 2 -> weiter
Pipeline gibt für A=B Rang 1 und für A=B mit minimalen unwichtigen Abweichungen Rang 2 und für A=B mit wichtigeren Abweichungen gradientweise niedrigere Ränge -> weiter
Pipeline gibt für A=B Rang 2 -> XXXXX STOP! FEHLER. Zurück!
Alles wird dokumentiert um die Entscheidungslogik zurückverfolgen zu können und debuggen zu können.
Das Ziel ist es in diesem Schritt die Parameter so lange zu optimieren bis sie genau auf das erwartete Ergebniss zugeschnitten sind.
