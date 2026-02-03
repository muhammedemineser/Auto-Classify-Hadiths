import regex

ISNAD_FRAME = regex.compile(
    r"""
    (?xiu)
    (?:
        قال|يقول|حدثنا|حدثني|اخبرنا|اخبرني|
        سمعت|سمعنا|روي|روى|ذكر|
        عن|ان|انما
    )
    """,
    regex.VERBOSE | regex.UNICODE,
)
QUDSI_FORMULA = regex.compile(
    r"""
    (?xiu)
    (?:
        فيما\s+يرويه\s+عن\s+ربه|
        قال\s+رسول\s+الله\s+.*?\s+فيما\s+يرويه\s+عن\s+ربه|
        قال\s+الله\s+فيما\s+يرويه\s+عنه\s+رسوله|
        يقول\s+الله\s+.*?\s+فيما\s+يرويه
    )
    """,
    regex.VERBOSE | regex.UNICODE,
)
DIVINE_SPEECH = regex.compile(
    r"""
    (?xiu)
    (?:
        قال\s+الله|
        يقول\s+الله|
        اني\s+|
        عبادي|
        يا\s+عبادي
    )
    """,
    regex.VERBOSE | regex.UNICODE,
)
QURAN_CITATION_CONTEXT = regex.compile(
    r"""
    (?xiu)
    (?:
        قوله\s+تعالى|
        كما\s+قال\s+تعالى|
        قال\s+تعالى\s+في\s+سورة|
        في\s+سورة\s+|
        الاية\s+|
        الايات\s+
    )
    """,
    regex.VERBOSE | regex.UNICODE,
)


def classify_text_segment(text: str) -> str:
    """
    Returns:
        "quran"
        "hadith_qudsi"
        "hadith"
        "unknown"
    """

    score_quran = 0
    score_qudsi = 0
    score_hadith = 0

    # 1. Harte Qudsi-Formeln
    if QUDSI_FORMULA.search(text):
        return "hadith_qudsi"

    # 2. Isnād-Rahmen vorhanden?
    if ISNAD_FRAME.search(text):
        score_hadith += 1

    # 3. Göttliche Rede
    if DIVINE_SPEECH.search(text):
        score_qudsi += 1
        score_quran += 0.5  # schwach, absichtlich

    # 4. Quran-Zitat-KONTEXT
    if QURAN_CITATION_CONTEXT.search(text):
        score_quran += 2

    # 5. Entscheidung
    if score_quran >= 2 and score_hadith == 0:
        return "quran"

    if score_qudsi >= 1 and score_hadith >= 1:
        return "hadith_qudsi"

    if score_hadith >= 1:
        return "hadith"

    return "unknown"
