"""Parametrisiertes HASM-Scoring mit Frame-Maskierung.

Nutzt die unveraenderten HASM-Kernfunktionen aus seqMatcherTool
(diff_to_matrix, f1, _pos_weight, _stopword_factor, _short_candidate_bonus),
wendet aber die Isnad-Frame-Maskierung an und macht alle Gewichte/
Schwellen als Parameter verfuegbar, damit eine Optimierung (Regression,
Feedback-Loop) sie empirisch bestimmen kann.
"""

from __future__ import annotations

import json

import numpy as np

from isnad_frames import mask_frame_tokens
from seqMatcherTool import (
    _pos_weight,
    _stopword_factor,
    _short_candidate_bonus,
    diff_to_matrix,
    f1,
)


def _parse_pos(pos_value):
    if pos_value is None:
        return []
    if isinstance(pos_value, (list, tuple)):
        return [str(x) for x in pos_value]
    if isinstance(pos_value, str) and pos_value.strip():
        parsed = json.loads(pos_value)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    return []


class ScoringParams:
    """Alle empirisch bestimmbaren Parameter des Scorings."""

    __slots__ = (
        "threshold",
        "percentage_factor",
        "frame_weight",
        "f1_boost",
        "bleu_max_order",
        "f1_beta",
        "short_bonus_trigger",
        "short_bonus_max",
        "rouge_beta",
        "coverage_weight",
        "kern_floor",
    )

    def __init__(
        self,
        threshold: float = 0.5,
        percentage_factor: float = 0.9,
        frame_weight: float = 0.0,
        f1_boost: float = 1.1,
        bleu_max_order: int = 2,
        f1_beta: float = 1.9,
        short_bonus_trigger: float = 0.65,
        short_bonus_max: float = 0.30,
        rouge_beta: float = 1.2,
        coverage_weight: float = 0.0,
        kern_floor: float = 0.0,
    ):
        self.threshold = threshold
        self.percentage_factor = percentage_factor
        self.frame_weight = frame_weight
        self.f1_boost = f1_boost
        self.bleu_max_order = bleu_max_order
        self.f1_beta = f1_beta
        self.short_bonus_trigger = short_bonus_trigger
        self.short_bonus_max = short_bonus_max
        self.rouge_beta = rouge_beta
        self.coverage_weight = coverage_weight
        self.kern_floor = kern_floor

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


def score_pair_with_params(
    cand_norm: str,
    cand_pos,
    ref_norm: str,
    ref_pos,
    stop_words,
    stop_word_weight,
    params: ScoringParams,
    use_frame_masking: bool = True,
):
    """Berechne final_score fuer ein (txt, matn) Paar.

    Im Gegensatz zur Original-`score_pair` werden Frame-Tokens
    (Isnad/Narration/Ehrungsformeln) mit Gewicht `params.frame_weight`
    gewichtet statt mit ihrem POS-Gewicht, sodass sie den diff-basierten
    `percentage` kaum/noch belasten.
    """
    ref_tokens = ref_norm.split()
    cand_tokens = cand_norm.split()

    cand_mask = mask_frame_tokens(cand_tokens) if use_frame_masking else None
    ref_mask = mask_frame_tokens(ref_tokens) if use_frame_masking else None

    from difflib import SequenceMatcher as _SM

    vec1_ids, vec1_lens, vec2_ids, vec2_lens = diff_to_matrix(cand_norm, ref_norm)
    if vec1_ids is None:
        return 1.0, {}

    # Kern-Containment: wie viel vom txt (nicht-Frame) steckt im matn?
    cand_core_tokens = [t for t, m in zip(cand_tokens, cand_mask or [True]*len(cand_tokens)) if m]
    if params.coverage_weight > 0 and cand_core_tokens:
        sm = _SM(None, cand_core_tokens, ref_tokens)
        matched = sum(n for _, _, n in sm.get_matching_blocks())
        coverage = matched / len(cand_core_tokens)
    else:
        coverage = 0.0

    cand_pos_list = _parse_pos(cand_pos)
    ref_pos_list = _parse_pos(ref_pos)

    min1, max1 = min(vec1_ids), max(vec1_ids)
    min2, max2 = min(vec2_ids), max(vec2_ids)
    if min1 < 0 or max1 >= len(cand_pos_list) or min2 < 0 or max2 >= len(ref_pos_list):
        return 0.0, {}

    # Frame-Gewicht-Faktor pro Token (1 = Kern, frame_weight = Frame)
    w1 = np.array(
        [
            (params.frame_weight if cand_mask[int(v)] is False else 1.0)
            for v in vec1_ids
        ],
        dtype=np.float64,
    )
    w2 = np.array(
        [
            (params.frame_weight if ref_mask[int(v)] is False else 1.0)
            for v in vec2_ids
        ],
        dtype=np.float64,
    )

    pos_matrix_1 = np.array(
        [
            _pos_weight(cand_pos_list[int(v)])
            * _stopword_factor(cand_tokens[int(v)], stop_words, stop_word_weight)
            for v in vec1_ids
        ],
        dtype=np.float64,
    )
    pos_matrix_2 = np.array(
        [
            _pos_weight(ref_pos_list[int(v)])
            * _stopword_factor(ref_tokens[int(v)], stop_words, stop_word_weight)
            for v in vec2_ids
        ],
        dtype=np.float64,
    )

    power_v1 = np.array(vec1_lens, dtype=np.float64) * pos_matrix_1 * w1
    power_v2 = np.array(vec2_lens, dtype=np.float64) * pos_matrix_2 * w2

    pos = np.where(power_v1 > 0, power_v1, 0)
    pos = np.append(pos, np.where(power_v2 > 0, power_v2, 0))
    neg = np.where(power_v1 < 0, power_v1, 0)
    neg = np.append(neg, np.where(power_v2 < 0, power_v2, 0))

    denom = pos.sum() + (-neg.sum())
    percentage = (pos.sum() / denom) * params.percentage_factor if denom > 0 else 0.0

    f1_result = f1(
        reference=cand_norm,
        candidate=ref_norm,
        reference_pos=cand_pos,
    )
    f1_result["f1"] *= params.f1_boost
    smaller = min(percentage, f1_result["f1"])
    greater = max(percentage, f1_result["f1"])
    final_score = ((greater - smaller) / 2) + smaller
    if params.coverage_weight > 0 and coverage >= params.kern_floor:
        final_score += params.coverage_weight * coverage

    final_score = min(
        1.0,
        final_score
        + _short_candidate_bonus(
            reference=cand_norm,
            candidate=ref_norm,
            percentage=percentage,
        ),
    )

    detail = {
        "percentage": float(percentage),
        "bleu": float(f1_result["bleu"]),
        "rougeL": float(f1_result["rougeL"]),
        "f1": float(f1_result["f1"]),
        "coverage": float(coverage),
        "final": float(final_score),
    }
    return final_score, detail


def score_pair(
    cand_norm: str,
    cand_pos,
    ref_norm: str,
    ref_pos,
    stop_words,
    stop_word_weight,
    frame_weight: float = 0.0,
):
    """Kurzform mit Default-Parametersatz (frame_weight=0 -> neutral)."""
    params = ScoringParams(frame_weight=frame_weight)
    return score_pair_with_params(
        cand_norm, cand_pos, ref_norm, ref_pos, stop_words, stop_word_weight, params
    )[0]