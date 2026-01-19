import stanza
import os

import arabic_reshaper
from bidi.algorithm import get_display

def printa(text):
    # 1. Shaping: Verbindet die Buchstaben (z.B. von س ل ا م zu سلام)
    reshaped_text = arabic_reshaper.reshape(text)
    # 2. BiDi: Dreht die Laufrichtung für das Terminal um
    bidi_text = get_display(reshaped_text)
    print(bidi_text)

# Pipeline initialisieren
# Pipeline laden (Sentiment für Arabisch muss verfügbar sein)
nlp = stanza.Pipeline(lang='ar', processors='tokenize,mwt,pos,lemma,sentiment')

text = "الحروف العربية ترسم لوحة فنية عند كتابتها"
doc = nlp(text)

for sentence in doc.sentences:
    # Hier war der Fehler: sentence.words statt word.words
    for word in sentence.words:
        printa(f"Original: {word.text} | Lemma: {word.lemma} | POS: {word.pos}")

texts = [
    "Das Paradies ist schön.",
    "Er lügt nicht."
]

# Hilfsfunktion für Terminal-Anzeige
def d(text):
    if not text: return ""
    return get_display(reshape(text))


# Test-Hadithe (bejaht vs. verneint)
texts = [
    "الصدق يهدي إلى البر",         # "Ehrlichkeit führt zur Rechtschaffenheit" (Positiv)
    "لا يدخل الجنة قاطع"           # "Ein Bindung-Lösender tritt nicht ins Paradies ein" (Negation)
]

for text in texts:
    doc = nlp(text)
    printa(f"\n--- Analyse für: {d(text)} ---")
    
    for sentence in doc.sentences:
        # 1. Sentiment (Gefühlswert)
        sentiment_label = {0: "NEGATIV", 1: "NEUTRAL", 2: "POSITIV"}
        printa(f"Stimmung (Sentiment): {sentiment_label[sentence.sentiment]}")
        
        # 2. Logische Negation (Suche nach Partikeln: la, lam, lan, ma)
        # Wir prüfen das Lemma, um verschiedene Schreibweisen zu fangen
        neg_particles = ["لا", "لم", "لن", "ما"]
        negations = [word.text for word in sentence.words if word.upos == 'PART' and word.lemma in neg_particles]
        
        if negations:
            printa(f"Logik: VERNEINUNG gefunden ({[d(n) for n in negations]})")
        else:
            printa("Logik: BEJAHUNG (keine Negationspartikel)")

        # 3. Einzelwort-Details
        printa(f"{'Wort':<15} | {'Lemma':<15} | {'POS':<6}")
        for word in sentence.words:
            printa(f"{d(word.text):<15} | {d(word.lemma):<15} | {word.upos:<6}")