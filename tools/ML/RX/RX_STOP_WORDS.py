# tafsir_student/data/hadith_meta_stopwords.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Literal, Optional, Tuple
import math
import regex


Mode = Literal["strict", "loose"]


RX_ARABIC_DIACRITICS = regex.compile(
    r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]+",
    regex.UNICODE,
)
RX_TATWEEL = regex.compile(r"\u0640+", regex.UNICODE)
RX_WS = regex.compile(r"\s+", regex.UNICODE)


def normalize_text(text: str, mode: Mode = "loose") -> str:
    if not text:
        return ""
    t = text
    t = RX_TATWEEL.sub("", t)
    t = RX_ARABIC_DIACRITICS.sub("", t)
    if mode == "loose":
        t = RX_WS.sub(" ", t).strip()
    else:
        t = t.strip()
    return t


HONORIFICS_PAT = r"""
(?xiu)
(?:
    # Prophet / Messenger
    صلى\s+الله\s+عليه\s+وسلم|
    صل(?:ى|ي)\s+الله\s+عليه\s+وسلم|
    عليه\s+الصلاة\s+والسلام|
    عليه\s+السلام|
    عليهم\s+السلام|
    # Companions / Scholars
    رضي\s+الله\s+عنه|
    رضي\s+الله\s+عنها|
    رضي\s+الله\s+عنهم|
    رضوان\s+الله\s+عليه|
    رحمه\s+الله|
    رحمهم\s+الله|
    رحمها\s+الله
)
"""

GRADING_PAT = r"""
(?xiu)
(?:
    # Explicit grading frames (high-precision)
    إسناد(?:ه|ها)?\s+(?:صحيح|حسن|ضعيف|منكر|باطل|موضوع)\b|
    سند(?:ه|ها)?\s+(?:صحيح|حسن|ضعيف|منكر|باطل|موضوع)\b|
    رجاله\s+ثقات\b|
    رجال(?:ه|ها)?\s+(?:ثقات|صحيح|حسن|ضعيف)\b|
    على\s+شرط\s+(?:الشيخين|البخاري|مسلم)\b|
    شرط\s+(?:الشيخين|البخاري|مسلم)\b|
    لا\s+يصح(?:\s+إسناد(?:ه|ها)?)?\b|
    لا\s+يثبت\b|
    لا\s+أصل\s+له\b|
    يصحح(?:ه|ها)?\b|
    صحح(?:ه|ها)?\b|
    حسّن(?:ه|ها)?\b|
    ضعّف(?:ه|ها)?\b|
    شاذ\b|
    غريب\b|
    منكر\b|
    باطل\b|
    موضوع\b|
    مرسل(?:ا)?\b|
    منقطع\b|
    موقوف(?:ا)?\b|
    مقطوع(?:ا)?\b|
    مدلس\b|
    تفرد\b|
    شاهد\b|
    متابع(?:ة)?\b
)
"""

CITATION_VERBS_PAT = r"""
(?xiu)
(?:
    # Scholarly citation / takhrij verbs (high-precision)
    أخرجه\b|
    خرجه\b|
    رواه\b|
    روى\b|
    ذكره\b|
    حكاه\b|
    حكى\b|
    نقله\b|
    أسنده\b|
    أورده\b|
    عزاه\b|
    تابعه\b|
    تابع\b|
    انظر\b|
    أشار\s+إليه\b|
    مخرّج\b|
    تخريج\b|
    تخريجه\b|
    طريق\b|
    بإسناد\b|
    بإسناده\b|
    بإسناد(?:ه|ها)?\b
)
"""

COMMENTARY_PAT = r"""
(?xiu)
(?:
    # Editorial / commentary frames (moderate precision)
    وفي\s+(?:رواية|لفظ|الصحيح|السنن|المسند|الموطأ|المستدرك)\b|
    هكذا\s+رواه\b|
    وقد\s+رواه\b|
    ورواه\s+أيض(?:ا)?\b|
    ثم\s+قال\b|
    كما\s+(?:تقدم|سبق|ذكر)\b|
    وسيأتي\b|
    سيأتي\b|
    سيأتي\s+بيانه\b|
    والله\s+أعلم\b|
    وهذا\s+لفظ\b|
    وفي\s+هذا\s+السياق\b|
    وفي\s+صحته\b|
    وفي\s+إسناده\b|
    وفيه\s+(?:نظر|دليل|إشارة)\b|
    والراجح\b|
    والأصح\b|
    والصحيح\b|
    واختلف(?:وا)?\b
)
"""

SOURCE_ANCHORS_PAT = r"""
(?xiu)
(?:
    # Anchor words that usually introduce sources (reduces accidental matches)
    (?:عند|في|خرجه|أخرجه|رواه|روى|ذكره|حكاه|نقله)\s+
    (?:
        # Core hadith collections / compilers
        (?:ال)?بخاري|
        (?:ال)?مسلم|
        ابو\s+داود|
        (?:ال)?ترمذي|
        (?:ال)?نسائي|
        بن\s+ماجه|
        مالك(?:\s+بن\s+انس)?|
        احمد(?:\s+بن\s+حنبل)?|
        (?:ال)?شافعي|
        عبد\s+الرزاق|
        بن\s+ابي\s+شيبه|
        (?:ال)?دارمي|
        (?:ال)?بيهقي|
        (?:ال)?طبراني|
        (?:ال)?حاكم|
        (?:ال)?دارقطني|
        بن\s+حبان|
        بن\s+خزيمه|
        (?:ال)?ذهبي|
        (?:ال)?نووي|
        (?:ال)?هيثمي|
        (?:ال)?خطيب(?:\s+البغدادي)?
    )
)
"""

STRUCTURE_FRAMES_PAT = r"""
(?xiu)
(?:
    # Structural narrator frames (avoid single "قال"/"عن"; use multiword)
    قال\s+الراوي\b|
    قال\s+الحافظ\b|
    قال\s+الإمام\b|
    قال\s+الشيخ\b|
    عن\s+أبيه\b|
    عن\s+أمه\b|
    عن\s+جده\b|
    عن\s+جدته\b
)
"""


HADITH_META_STOPWORDS = regex.compile(
    rf"""
(?xiu)
(?:
    (?P<honorific>{HONORIFICS_PAT})|
    (?P<grading>{GRADING_PAT})|
    (?P<citation>{CITATION_VERBS_PAT})|
    (?P<commentary>{COMMENTARY_PAT})|
    (?P<source_anchor>{SOURCE_ANCHORS_PAT})|
    (?P<structure>{STRUCTURE_FRAMES_PAT})
)
""",
    regex.VERBOSE | regex.UNICODE,
)


META_WEIGHTS: Dict[str, float] = {
    "grading": 0.55,
    "citation": 0.45,
    "source_anchor": 0.30,
    "commentary": 0.20,
    "structure": 0.15,
    "honorific": 0.06,
}

META_CAPS: Dict[str, int] = {
    "grading": 6,
    "citation": 8,
    "source_anchor": 6,
    "commentary": 8,
    "structure": 8,
    "honorific": 10,
}


@dataclass(frozen=True)
class MetaHit:
    kind: str
    span: Tuple[int, int]
    text: str


def iter_meta_hits(text: str, *, mode: Mode = "loose") -> Iterable[MetaHit]:
    t = normalize_text(text, mode=mode)
    for m in HADITH_META_STOPWORDS.finditer(t):
        kind = m.lastgroup or "unknown"
        yield MetaHit(kind=kind, span=(m.start(), m.end()), text=m.group(0))


def meta_counts(text: str, *, mode: Mode = "loose") -> Dict[str, int]:
    counts: Dict[str, int] = {k: 0 for k in META_WEIGHTS.keys()}
    for hit in iter_meta_hits(text, mode=mode):
        if hit.kind in counts:
            counts[hit.kind] += 1
    return counts


def meta_penalty(text: str, *, mode: Mode = "loose") -> float:
    """
    Returns penalty in [0.0, 1.0]:
      0.0 -> no meta-noise evidence
      1.0 -> strong meta-noise evidence
    """
    counts = meta_counts(text, mode=mode)
    raw = 0.0
    for k, w in META_WEIGHTS.items():
        c = counts.get(k, 0)
        cap = META_CAPS.get(k, 6)
        raw += w * float(min(c, cap))
    # Saturating transform (keeps small penalties small)
    p = 1.0 - math.exp(-raw / 3.0)
    if p < 0.0:
        return 0.0
    if p > 1.0:
        return 1.0
    return p


def meta_negative_factor(text: str, *, mode: Mode = "loose") -> float:
    """
    Multiplicative factor in [0.0, 1.0]:
      1.0 -> no reduction
      0.0 -> maximal reduction
    """
    p = meta_penalty(text, mode=mode)
    f = 1.0 - p
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def apply_meta_penalty(score: float, text: str, *, strength: float = 1.0, mode: Mode = "loose") -> float:
    """
    score: any continuous score (e.g., logit, heuristic score)
    strength: scaling multiplier for the penalty
    """
    p = meta_penalty(text, mode=mode)
    return score - (strength * p)


__all__ = [
    "Mode",
    "MetaHit",
    "HADITH_META_STOPWORDS",
    "normalize_text",
    "iter_meta_hits",
    "meta_counts",
    "meta_penalty",
    "meta_negative_factor",
    "apply_meta_penalty",
]
