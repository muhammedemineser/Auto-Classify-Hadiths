"""Tests fuer die Isnad-Frame-Maskierung."""

import pytest

from isnad_frames import mask_frame_tokens


def _mask(normalized_text: str):
    return mask_frame_tokens(normalized_text.split())


def _core(normalized_text: str):
    toks = normalized_text.split()
    mask = mask_frame_tokens(toks)
    return " ".join(t for t, m in zip(toks, mask) if m)


def test_prefix_frame_erkannt():
    # 'قال رسول الله صلى الله عليه وسلم' vor dem Kern muss Frame sein
    text = "قال رسول الله صلي الله عليه وسلم ما من مسلم يغرس غرسا"
    mask = _mask(text)
    toks = text.split()
    assert not mask[0] and not mask[1] and not mask[2]  # قال رسول الله
    assert mask[-1] is True  # 'غرسا' ist Kern


def test_kern_ohne_frame_unveraendert():
    text = "لا تتخذوا الضيعه فترغبوا في الدنيا"
    assert _core(text) == text


def test_isnad_verb_frame():
    text = "حدثنا فلان عن فلان قال"
    mask = _mask(text)
    assert mask[0] is False  # حدثنا


def test_ehrungsformel_frame():
    text = "ان الله عز وجل كتب علي نفسه ان رحمتي تغلب غضبي"
    toks = text.split()
    mask = _mask(text)
    # 'عز وجل' ist Frame
    assert mask[toks.index("عز")] is False
    assert mask[toks.index("وجل")] is False
    # 'كتب' ist Kern
    assert mask[toks.index("كتب")] is True


def test_gottesspruch_rahmen():
    text = "قال الله تعالي اذا احب عبدي لقايي"
    toks = text.split()
    mask = _mask(text)
    assert mask[toks.index("قال")] is False
    assert mask[toks.index("الله")] is False
    assert mask[toks.index("اذا")] is True


def test_سمعت_rahmen():
    text = "سمعت رسول الله صلي الله عليه وسلم يقول كذا"
    toks = text.split()
    mask = _mask(text)
    # alle Frame-Tokens am Anfang False, letztes Kern
    assert mask[-1] is True
    assert all(m is False for m in mask[:-1])


def test_اللهم_bleibt_kern():
    text = "اللهم اجعل رزق ال محمد قوتا"
    toks = text.split()
    mask = _mask(text)
    assert mask[toks.index("اللهم")] is True