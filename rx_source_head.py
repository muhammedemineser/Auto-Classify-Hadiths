import regex

RX_SOURCE_HEAD = regex.compile(
    r"""
(?xiu)

    # 1) Linker Kontext: Keine arabischen Buchstaben davor
    (?<![\p{Arabic}\u0640])

    # 2) Optionale Konjunktion
    (?:و|ف)?

    # 3) Präposition + Artikel Logik
    (?:
        (?:في|من|على|عن)\s+(?:ال)? |  # freistehende Präpositionen
        لل |                           # ل + ال (Assimilation)
        ب(?:ال)? |                     # ب + (ال)
        ل(?=[\p{Arabic}])              # gebundenes ل vor Wort
    )?

    (?xiu)
    (?P<head_word>
        # ─────────────────────────────────
        # Kutub as-Sitta
        # ─────────────────────────────────
        (?:ال)?بخاري|
        (?:ال)?مسلم|
        ابو\s+داود|
        (?:ال)?ترمذي|
        (?:ال)?نسايي|
        بن\s+ماجه|

        # ─────────────────────────────────
        # Fruheste Hadith-Imame / Usul
        # ─────────────────────────────────
        مالك(?:\s+بن\s+انس)?|
        احمد(?:\s+بن\s+حنبل)?|
        (?:ال)?شافعي|
        عبد\s+الرزاق|
        بن\s+ابي\s+شيبه|
        سعيد\s+بن\s+منصور|
        (?:ال)?حميدي|
        (?:ال)?دارمي|

        # ─────────────────────────────────
        # Grosse Sammler / Masanid
        # ─────────────────────────────────
        ابو\s+يعلي|
        (?:ال)?بزار|
        (?:ال)?طيالسي|
        اسحاق\s+بن\s+راهويه|

        # ─────────────────────────────────
        # Mujam / Mustadrak / Erweiterungen
        # ─────────────────────────────────
        (?:ال)?طبراني|
        (?:ال)?حاكم|
        (?:ال)?بيهقي|
        (?:ال)?ضيا(?:\s+المقدسي)?|
        (?:ال)?دارقطني|
        ابو\s+نعيم|

        # ─────────────────────────────────
        # Sahih-Werke ausserhalb der Sitta
        # ─────────────────────────────────
        بن\s+حبان|
        بن\s+خزيمه|

        # ─────────────────────────────────
        # Zawaid / Hadith-Kompilationen
        # ─────────────────────────────────
        (?:ال)?هيثمي|

        # ─────────────────────────────────
        # Rijal- & Tabaqat-Werke (hadith-zitierend)
        # ─────────────────────────────────
        بن\s+سعد|
        خليفه\s+بن\s+خياط|
        (?:ال)?خطيب(?:\s+البغدادي)?|
        (?:ال)?فسوي|

        # ─────────────────────────────────
        # Grosse thematische Hadith-Sammlungen
        # ─────────────────────────────────
        (?:ال)?اجري|
        بن\s+ابي\s+الدنيا|
        (?:ال)?خرايطي|
        (?:ال)?ديلمي|

        # ─────────────────────────────────
        # Spatere Hadith-Kompilatoren (QUELLEN!)
        # ─────────────────────────────────
        بن\s+حجر|
        (?:ال)?نووي|
        (?:ال)?منذري|
        (?:ال)?بغوي|

        # ─────────────────────────────────
        # Weitere anerkannte Sunni-Hadith-Quellen
        # ─────────────────────────────────
        بن\s+الجارود|
        بن\s+المنذر|
        بن\s+عبد\s+البر|
        (?:ال)?طحاوي
    )

    # 5) Begrenzte Idāfa / Naʿt (max 3 Wörter)
        (?:
            \s+
            (?:ال)?
            [\p{Arabic}\u0640]{2,}
        ){0,3}

    # 6) Autorenzuschreibung
    (?:
        \s+
        (?:
            تاليف|تصنيف|للشيخ|للقاضي|للامام|للحافظ|
            # Oder das gebundene Lam direkt am Namen:
            ل[\p{Arabic}\u0640]{3,} 
        )
        (?:\s+[\p{Arabic}\u0640]{2,}){0,2}
    )?


    
""",
    regex.VERBOSE | regex.UNICODE,
)

from arabic_reshaper import reshape
from bidi.algorithm import get_display
from normalize import normalize_arabic


def d(text):
    print(get_display(reshape(text)))


with open(
    "/home/muhammed-emin-eser/desk/apps/classify/Tafsir/tafsir_books/x.rtl.txt",
    "r",
    encoding="UTF-8",
) as f:
    text = f.read()

    text = normalize_arabic(text)

    matches = RX_SOURCE_HEAD.findall(text)
    for match in matches:
        d(match)
    print("Number of matches: \t", len(matches))
