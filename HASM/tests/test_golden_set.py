"""Regressionstests auf dem manuell verifizierten Golden Set.

Jeder Eintrag wurde von einem Menschen geprueft:
- label 'accept': txt-Hadith IST dieser DB-Hadith (der Matn ist der Kern)
- label 'reject': txt-Hadith ist NICHT dieser DB-Hadith (Edge-Case, der
  mit naiven Metriken einen hohen Score erzielen wuerde)

Die Parameter kommen aus tests/optimized_params.json (empirisch per
Feedback-Loop bestimmt, siehe optimize_params.py).
"""

import json
from pathlib import Path

import pytest

from scoring import ScoringParams, score_pair_with_params
from utils import utils

BASE = Path(__file__).resolve().parent.parent
GOLDEN = BASE / "tests" / "golden_set.json"
PARAMS = BASE / "tests" / "optimized_params.json"


def _load_params() -> ScoringParams:
    with open(PARAMS, encoding="utf-8") as f:
        data = json.load(f)
    return ScoringParams(**data["params"])


@pytest.fixture(scope="module")
def golden():
    with open(GOLDEN, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def params():
    return _load_params()


def _load_pair(txt_id, source, hadith_id):
    txt_text = None
    with open(BASE / "Data" / "Sahihah" / "sahihah_hadith_extracted_in_sittah.txt", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) == 3 and parts[0] == txt_id:
                txt_text = parts[1]
                break
    assert txt_text, f"txt_id {txt_id} nicht gefunden"

    import sqlite3
    conn = sqlite3.connect(str(BASE / "Data" / "Hadith" / f"{source}.db"))
    row = conn.execute(
        "SELECT Arabic_Matn FROM hadiths WHERE hadith_id=?", (hadith_id,)
    ).fetchone()
    conn.close()
    assert row and row[0], f"hadith {source}/{hadith_id} nicht gefunden"
    return txt_text, row[0]


def _score(golden_entry, params):
    txt_text, matn = _load_pair(
        golden_entry["txt_id"], golden_entry["source"], golden_entry["hadith_id"]
    )
    cand_norm = utils.norm(txt_text)
    ref_norm = utils.norm(matn)
    if not cand_norm.strip():
        return 0.0
    cand_pos = utils.tag_pos_tokens(cand_norm.split())
    ref_pos = utils.tag_pos_tokens(ref_norm.split())
    score, _ = score_pair_with_params(
        cand_norm,
        cand_pos,
        ref_norm,
        ref_pos,
        stop_words=set(),
        stop_word_weight=0.25,
        params=params,
    )
    return score


def test_accept_ueber_schwelle(golden, params):
    """Alle manuell verifizierten Positiv-Faelle muessen akzeptiert werden."""
    for g in [e for e in golden if e["label"] == "accept"]:
        s = _score(g, params)
        assert s >= params.threshold, (
            f"accept erwartet aber abgelehnt: txt={g['txt_id']} "
            f"{g['source']}/h{g['hadith_id']} score={s:.3f} < {params.threshold}"
        )


def test_reject_unter_schwelle(golden, params):
    """Alle manuell verifizierten Edge-Cases muessen abgelehnt werden."""
    for g in [e for e in golden if e["label"] == "reject"]:
        s = _score(g, params)
        assert s < params.threshold, (
            f"reject erwartet aber akzeptiert: txt={g['txt_id']} "
            f"{g['source']}/h{g['hadith_id']} score={s:.3f} >= {params.threshold}"
        )