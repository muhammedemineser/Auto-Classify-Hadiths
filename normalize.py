import regex
import unicodedata


# ── Harakat, Quranische Zeichen, kombinierende Marks
ARABIC_DIACRITICS = regex.compile(
    r"[\p{M}\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]+"
)

# Tatweel (Kashida)
TATWEEL = "\u0640"

# Alles außer arabischen Buchstaben + Leerzeichen
NON_ARABIC = regex.compile(r"[^\p{Arabic} ]+")

# Mehrfach-Leerzeichen
MULTI_SPACE = regex.compile(r"\s+")

# Definierte Präfixe
# Erlaubt auch Kombinationen wie وبالـ (wa-bi-al-)
prefixes = r"([أوفبلك]{0,2})"

def normalize_arabic(text: str) -> str:

    if not text:
        return ""

    # 1) Unicode-Kompatibilitätsnormalisierung
    text = unicodedata.normalize("NFKD", text)

    # 2) Entferne Harakat / Diakritika
    text = ARABIC_DIACRITICS.sub("", text)

    # 3) Entferne Tatweel
    text = text.replace(TATWEEL, "")

    # 4) Orthographische Vereinheitlichung
    text = text.translate(
        str.maketrans(
            {
                "أ": "ا",
                "إ": "ا",
                "آ": "ا",
                "ٱ": "ا",
                "ى": "ي",
                "ئ": "ي",
                "ؤ": "و",
                "ة": "ه",
                "ء": "",
                "گ": "ك",
                "ڤ": "ف",
                "پ": "ب",
                "چ": "ج",
            }
        )
    )
    # 5) ibn -> bin (erhält Präfixe)
    # Wir suchen nach dem Wortstamm 'ابن'
    text = regex.sub(
        r"(?<![\p{Arabic}])" + prefixes + r"ابن(?![\p{Arabic}])", 
        r"\1بن", 
        text
    )

    # 6) Aby -> Abu (erhält Präfixe)
    text = regex.sub(
        r"(?<![\p{Arabic}])" + prefixes + r"ابي(?![\p{Arabic}])", 
        r"\1ابو", 
        text
    )

    # 7) Entferne alles Nicht-Arabische (Zahlen, Satzzeichen, Latin etc.)
    text = NON_ARABIC.sub(" ", text)

    # 8) Leerzeichen normalisieren
    text = MULTI_SPACE.sub(" ", text).strip()

    # 9) Finale Unicode-Rekomposition
    text = unicodedata.normalize("NFKC", text)

    return text
