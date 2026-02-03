import regex

MATN_BASE = [
    "قال رسول الله",
    "قال النبي",
    "قال نبي الله",
    "يقول رسول الله",
    "يقول النبي",
    "سمعت رسول الله",
    "سمعت النبي",
    "سمعنا رسول الله",
    "حدثنا رسول الله",
    "حدثني رسول الله",
    "أخبرنا رسول الله",
    "أخبرني رسول الله",
    "عن رسول الله قال",
    "عن النبي قال",
    "عن رسول الله أنه قال",
    "عن النبي أنه قال",
    "أن رسول الله قال",
    "أن النبي قال",
    "إن رسول الله قال",
    "إن النبي قال",
    "كان رسول الله",
    "كان النبي",
    "فعل رسول الله",
    "فعل النبي",
    "أمر رسول الله",
    "نهى رسول الله",
    "سئل رسول الله",
    "سئل النبي",
    "رأيت رسول الله",
    "رأيت النبي",
    "شهدت رسول الله",
    "شهدت النبي",
    "جاء رسول الله",
    "أتى رسول الله",
    "خرج رسول الله",
    "دخل رسول الله",
    "رُوي عن رسول الله",
    "روى رسول الله",
    "قال الله",
    "يقول الله",
    "قال ربكم",
    "قال رب العزة",
    "فيما يرويه عن ربه",
]


MATN_REGEX = regex.compile(
    r"""
    ^
    (?:
      # ── Allah / Qudsi
      (?:قال|يقول)\s++الله
        (?:\s++(?:تعالى|عز\s++وجل|سبحانه\s++وتعالى|تبارك\s++وتعالى))?
      |
      قال\s++(?:ربكم|رب\s++العزة)
      |
      فيما\s++يرويه\s++عن\s++ربه
      |
      # ── Prophetisch
      (?:
        قال|يقول|سمعت|سمعنا|حدثنا|حدثني|أخبرنا|أخبرني|
        عن|أن|إن|كان|فعل|أمر|نهى|سئل|رأيت|شهدت|
        جاء|أتى|خرج|دخل|رُوي|روى
      )
      \s++
      (?>
        رسول\s++الله|
        النبي|
        نبي\s++الله
      )
      (?:\s*+(?:ﷺ|صلى\s++الله\s++عليه\s++وسلم|عليه\s++الصلاة\s++والسلام|\(ص\)))?
      (?:\s++(?:قال|يقول))?
    )
    \s*+[:،]?
    """,
    regex.VERBOSE | regex.UNICODE,
)

import regex

# Kompilierte Regex zur Erkennung von Hadith-Matn-Anfängen
MATN_REGEX = regex.compile(
    r"""
    ^                                   # Match NUR am Zeilenanfang (Matn-Prefix)
    (?:
      # ── Abschnitt 1: Göttliche / Qudsi-Überlieferungen
      (?:قال|يقول)\s++الله              # "قال الله" / "يقول الله"
        (?:                             # optionale Gottesattribute
          \s++
          (?:تعالى|عز\s++وجل|سبحانه\s++وتعالى|تبارك\s++وتعالى)
        )?
      |
      قال\s++(?:ربكم|رب\s++العزة)       # "قال ربكم" / "قال رب العزة"
      |
      فيما\s++يرويه\s++عن\s++ربه        # Hadith Qudsi-Formel
      |
      # ── Abschnitt 2: Prophetische Überlieferungen
      (?:
        قال|يقول|سمعت|سمعنا|حدثنا|حدثني|أخبرنا|أخبرني|  # Rede- & Hörverben
        عن|أن|إن|كان|فعل|أمر|نهى|سئل|رأيت|شهدت|          # Berichtskonstruktionen
        جاء|أتى|خرج|دخل|رُوي|روى                         # Kontext-/Bewegungsverben
      )
      \s++                              # mind. ein Leerzeichen (possessive → kein Backtracking)
      (?>                               # ATOMIC GROUP: verhindert Backtracking
        رسول\s++الله|                  # "رسول الله"
        النبي|                          # "النبي"
        نبي\s++الله                    # "نبي الله"
      )
      (?:                               # optionale Ṣalāt-Formel
        \s*+
        (?:ﷺ|
           صلى\s++الله\s++عليه\s++وسلم|
           عليه\s++الصلاة\s++والسلام|
           \(ص\)
        )
      )?
      (?:                               # optionale Ergänzung: "قال" / "يقول"
        \s++
        (?:قال|يقول)
      )?
    )
    \s*+                                # optionaler Whitespace (possessive)
    [:،]?                               # optionaler Doppelpunkt oder arabisches Komma
    """,
    regex.VERBOSE | regex.UNICODE,  # VERBOSE: Kommentare/Whitespace erlaubt
    # UNICODE: volle Unicode-Unterstützung
)
