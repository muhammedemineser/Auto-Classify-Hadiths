import os
import sqlite3
import pytest

from filter_blocks_by_hadith_occurrence import (
    normalize,
    tokenize,
    extract_matn_tokens,
    build_ngram_list,
    index_hadith_ngrams,
    match_blocks,
    PREFIX_LOOKUP,
)

BASE = os.path.expanduser("/home/muhammed-emin-eser/desk/apps/fetch_ketab")
BUKHARI_PATH = os.path.join(BASE, "sahihah", "bukhari.txt")
MUSLIM_PATH = os.path.join(BASE, "sahihah", "muslim.txt")
SAHIHAH_PATH = os.path.join(BASE, "sahihah", "sahihah.txt")
KATHEER_DB = os.path.join(BASE, "tafsir", "tafsir_books", "katheer.sqlite3")


def test_normalize_basic_rules():
    assert normalize("أإآ") == "ااا"
    assert normalize("على") == "علي"
    assert normalize("جامعة") == "جامعه"
    assert normalize("سلام\u0640") == "سلام"
    # Waw-gap collapsing + ta marbuta normalization: "و كلمة" -> "وكلمه"
    assert normalize("و كلمة") == "وكلمه"


def test_tokenize_and_strip_html():
    assert tokenize("<b>سلام</b>") == ["سلام"]
    toks = tokenize("مرحبا، 123!")
    assert "123" in toks
    assert any(t.strip() == "،" for t in toks) or any(t == "!" for t in toks)


def test_extract_matn_prefix_handling():
    # build a sample with a known prefix from PREFIX_LOOKUP
    sample = "قال رسول الله صلى الله عليه وسلم لا تدخلوا البيوت الا بمعرفة اهلها"
    toks = tokenize(sample)
    matn = extract_matn_tokens(toks)
    # expect the matn to start with the token after the prefix ("لا")
    assert matn, "matn should not be empty"
    assert matn[0] == "لا"
    assert "البيوت" in matn


def test_build_ngrams_and_index_matching():
    hadith = "لا تدخلوا البيوت الا بمعرفة اهلها"
    block = (
        "ومن السنة: قال رسول الله صلى الله عليه وسلم لا تدخلوا البيوت "
        "الا بمعرفة اهلها فكان ذلك تعليمًا"
    )

    # index hadiths without requiring prefixes so the full hadith is used
    index, hadiths, stats, per_grams, per_ns = index_hadith_ngrams(
        [hadith], require_prefix=False
    )
    # grams should be of the computed anchor size and present
    expected_n = per_ns[0]
    assert expected_n >= 1
    assert all(len(g) == expected_n for g in per_grams[0])

    # match the block text and expect a hit (min_matches=1, hit_rate_threshold=0.0)
    res = match_blocks(
        [block],
        index,
        [hadith],
        min_words=1,
        min_matches=1,
        hit_rate_threshold=0.0,
        hadith_anchor_ngrams=per_grams,
        hadith_anchor_ns=per_ns,
        require_prefix=False,
    )
    assert res["blocks"], "Expected at least one matched block"
    b = res["blocks"][0]
    # the match_blocks output stores hits under the 'hadiths' key
    assert b["hadiths"], "Expected matched hadiths in block"


@pytest.mark.skipif(not os.path.exists(BUKHARI_PATH), reason="bukhari.txt not present")
def test_bukhari_contains_known_snippet():
    with open(BUKHARI_PATH, "r", encoding="utf-8") as f:
        data = f.read()
    assert "كُنْتُ فِي مَجْلِسٍ" in data or "كنت في مجلس" in data


@pytest.mark.skipif(not os.path.exists(KATHEER_DB), reason="katheer sqlite not present")
def test_katheer_db_has_fatiha_text():
    conn = sqlite3.connect(KATHEER_DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(1) FROM katheer WHERE text LIKE '%الفاتحة%' OR text LIKE '%الفاتحه%'"
    )
    cnt = cur.fetchone()[0]
    conn.close()
    assert cnt > 0, "Expected at least one katheer row mentioning الفاتحة"
