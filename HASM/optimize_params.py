"""Evaluations-Harness + Parameter-Optimierung (Feedback-Loop).

Bewertet das parametrisierte Scoring auf dem Golden Set und sucht per
Koordinaten-/Gitter-Abstieg die Parameter, die:
- alle 'accept'-Faelle ueber der Schwelle halten (Recall/Praezision)
- alle 'reject'-Edge-Cases unter der Schwelle halten (keine False Positives)

Metrik: Gewichteter F1 auf der accept/reject-Klassifikation, mit harter
Bevorzugung von 'reject' (False Positives sind hier schlimmer als
False Negatives, da es sich um heilige Texte handelt).
"""

from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

from scoring import ScoringParams, score_pair_with_params
from utils import utils

BASE = Path(__file__).resolve().parent
GOLDEN = BASE / "tests" / "golden_set.json"


def load_golden():
    with open(GOLDEN, encoding="utf-8") as f:
        return json.load(f)


def load_txt_map():
    m = {}
    with open(BASE / "Data" / "Sahihah" / "sahihah_hadith_extracted_in_sittah.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3:
                m[parts[0]] = parts[1]
    return m


def _matn(db_file: str, hadith_id) -> str | None:
    conn = sqlite3.connect(str(BASE / "Data" / "Hadith" / db_file))
    try:
        row = conn.execute(
            "SELECT Arabic_Matn FROM hadiths WHERE hadith_id=?", (hadith_id,)
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row else None


class GoldenEvaluator:
    def __init__(self):
        self.golden = load_golden()
        self.txt_map = load_txt_map()
        # vorberechnete (cand_norm, cand_pos, ref_norm, ref_pos)
        self.pairs = []
        for g in self.golden:
            txt = self.txt_map.get(g["txt_id"])
            matn = _matn(f"{g['source']}.db", g["hadith_id"])
            if txt is None or matn is None:
                continue
            cand_norm = utils.norm(txt)
            ref_norm = utils.norm(matn)
            if not cand_norm.strip():
                continue
            cand_pos = utils.tag_pos_tokens(cand_norm.split())
            ref_pos = utils.tag_pos_tokens(ref_norm.split())
            self.pairs.append((g["label"], g, cand_norm, cand_pos, ref_norm, ref_pos))

    def evaluate(self, params: ScoringParams) -> dict:
        tp = fp = tn = fn = 0
        scores = []
        for label, g, cand_norm, cand_pos, ref_norm, ref_pos in self.pairs:
            s, _ = score_pair_with_params(
                cand_norm, cand_pos, ref_norm, ref_pos,
                stop_words=set(), stop_word_weight=0.25, params=params,
            )
            scores.append((s, g, label))
            pred = s >= params.threshold
            if label == "accept":
                if pred:
                    tp += 1
                else:
                    fn += 1
            else:
                if pred:
                    fp += 1
                else:
                    tn += 1
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        # False Positives (reject als accept) sind heilige-Texte-Kritisch:
        # stark bestrafen.
        score = 0.6 * recall - 1.5 * (fp / max(1, tn + fp)) + 0.3 * precision
        return {
            "score": score,
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            "precision": precision, "recall": recall,
            "reject_fp": fp,
            "accept_fn": fn,
        }


def optimize():
    evaluator = GoldenEvaluator()
    print(f"Golden Paare: {len(evaluator.pairs)}", flush=True)

    best_params = ScoringParams()
    best = evaluator.evaluate(best_params)
    print("Baseline:", best, flush=True)

    # Koordinaten-Abstieg mit Gitter: jeder Parameter separat durchlaufen.
    grid = {
        "threshold": [0.35, 0.40, 0.45, 0.50],
        "percentage_factor": [0.7, 0.8, 0.9, 1.0],
        "frame_weight": [0.0, 0.05, 0.1, 0.2],
        "f1_boost": [1.0, 1.1, 1.2],
        "f1_beta": [1.5, 1.7, 1.9],
        "coverage_weight": [0.0, 0.1, 0.2, 0.3, 0.4],
        "kern_floor": [0.0, 0.6, 0.7, 0.8, 0.9],
    }
    improved = True
    while improved:
        improved = False
        for attr, values in grid.items():
            cur = getattr(best_params, attr)
            for v in values:
                if abs(v - cur) < 1e-9:
                    continue
                cand = ScoringParams()
                for a in ScoringParams.__slots__:
                    setattr(cand, a, getattr(best_params, a))
                setattr(cand, attr, v)
                res = evaluator.evaluate(cand)
                if res["score"] > best["score"]:
                    best = res
                    best_params = cand
                    improved = True
                    print(f"  verbessert {attr}={v} -> score={res['score']:.3f} "
                          f"tp={res['tp']} fp={res['fp']} fn={res['fn']}", flush=True)

    print("\n=== Bester Parametersatz ===", flush=True)
    print(best_params.to_dict(), flush=True)
    print(best, flush=True)
    return best_params, best


if __name__ == "__main__":
    p, r = optimize()
    with open(BASE / "tests" / "optimized_params.json", "w") as f:
        json.dump({"params": p.to_dict(), "result": r}, f, ensure_ascii=False, indent=1)
    print("gespeichert: tests/optimized_params.json")