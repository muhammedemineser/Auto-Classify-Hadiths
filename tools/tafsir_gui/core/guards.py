from __future__ import annotations

import math
from typing import Dict, List, Optional


def token_overlap(a_tokens: List[str], b_tokens: List[str]) -> float:
    if not a_tokens:
        return 0.0
    hits = sum(1 for t in a_tokens if t in set(b_tokens))
    return hits / len(a_tokens)


def ngram_overlap(a_tokens: List[str], b_tokens: List[str], n: int = 2) -> float:
    if not a_tokens or not b_tokens:
        return 0.0
    def grams(tokens):
        return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}
    a = grams(a_tokens)
    b = grams(b_tokens)
    if not a:
        return 0.0
    return len(a & b) / len(a)


def length_ratio(a_tokens: List[str], b_tokens: List[str]) -> float:
    if not a_tokens or not b_tokens:
        return 0.0
    shorter = min(len(a_tokens), len(b_tokens))
    longer = max(len(a_tokens), len(b_tokens))
    return shorter / longer if longer else 0.0


def evaluate_guard(
    source: List[str],
    generated: List[str],
    thresholds: Dict[str, float],
) -> Dict[str, float | str]:
    tok = token_overlap(source, generated)
    ngram = ngram_overlap(source, generated, n=thresholds.get("ngram_n", 2))
    ratio = length_ratio(source, generated)
    decision = "pass"
    if tok < thresholds.get("token_coverage", 0.7) or ngram < thresholds.get(
        "ngram_overlap", 0.5
    ):
        decision = "retry"
    if ratio < thresholds.get("length_ratio", 0.5):
        decision = "retry"
    return {
        "token_coverage": tok,
        "ngram_overlap": ngram,
        "length_ratio": ratio,
        "decision": decision,
    }


__all__ = ["evaluate_guard"]
