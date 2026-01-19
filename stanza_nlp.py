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
nlp = stanza.Pipeline(lang='ar', processors='tokenize,mwt,pos,lemma')

text = "الحروف العربية ترسم لوحة فنية عند كتابتها"
doc = nlp(text)

for sentence in doc.sentences:
    # Hier war der Fehler: sentence.words statt word.words
    for word in sentence.words:
        printa(f"Original: {word.text} | Lemma: {word.lemma} | POS: {word.pos}")
