from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path

from HASM.ranking import Utils
import arabic_reshaper
from bidi.algorithm import get_display
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tagger.default import DefaultTagger
import numpy as np
from collections import Counter
from typing import Any, Iterable, Optional

import evaluate
import json
from dataclasses import dataclass, field


BASE_DIR = Path(__file__).resolve().parent
path_to_cand = BASE_DIR / "Data" / "Sahihah" / "sahihah_hadith_extracted_in_sittah.txt"
path_to_stop_words = BASE_DIR / "Data" / "Sahihah" / "stop-words.txt"
with open(path_to_cand, "r", encoding="utf-8") as f:
    docs = f.read().splitlines()


class OldStuff:

    def stopwords(custom_stop_words):
        with open(path_to_stop_words, "r", encoding="utf-8") as f:
            STOPWORDS = set(f.read().splitlines())
        return list(STOPWORDS.extend(custom_stop_words))

    def ar(text):
        return get_display(arabic_reshaper.reshape(text))

    def norm(text):
        return Utils.norm(text)

    def pos_tags(self, docs):
        vec = TfidfVectorizer(preprocessor=self.norm)

        X = vec.fit_transform(docs)

        ratios = np.array(
            [(X[:, idx] > 0).sum() / len(docs) for idx in vec.vocabulary_.values()]
        )

        # Robuster als max(): 95. Perzentil ignoriert Ausreißer
        p95 = np.percentile(ratios, 95)

        words = list(vec.vocabulary_.keys())

        def words_above(threshold):
            return [ar(words[i]) for i, r in enumerate(ratios) if r > threshold]

        mled = MLEDisambiguator.pretrained()
        tagger = DefaultTagger(mled, "pos")
        tags = tagger.tag(words_above(p95))

        tag_count = Counter(tags)


@dataclass
class Config:
    db_path: str = str(BASE_DIR / "Data" / "Hadith")
    dbs: tuple[str, ...] = (
        "Bukhari.db",
        "Muslim.db",
        "AbuDaud.db",
        "Tirmizi.db",
        "Nesai.db",
        "IbnMaja.db",
    )
    table: str = "hadiths"
    id_col: str = "Hadith_number"
    text_col: str = "Arabic_Matn"
    normalized_col: str = "normalized"
    pos_col: str = "pos"
    hadith_txt: str = str(
        BASE_DIR / "Data" / "Sahihah" / "sahihah_hadith_extracted_in_sittah.txt"
    )
    pre_defined_stop_words: str = "path/to/pre"
    POS_WEIGHTS: dict[str, float] = field(
        default_factory=lambda: {
            # Content-heavy POS
            "noun": 1.5,
            "noun_prop": 1.6,
            "noun_quant": 1.2,
            "verb": 1.3,
            "verb_pseudo": 0.9,
            "adj": 1.1,
            "adv": 0.9,
            "adv_rel": 0.7,
            "adv_interrog": 0.7,
            "interj": 0.6,
            # Pronouns / determiners
            "pron": 0.2,
            "pron_dem": 0.3,
            "pron_rel": 0.3,
            # Function words / particles
            "prep": 0.2,
            "conj": 0.2,
            "conj_sub": 0.2,
            "part": 0.2,
            "part_verb": 0.2,
            "part_neg": 0.25,
            "part_focus": 0.25,
            "part_interrog": 0.25,
            "part_voc": 0.15,
            # Misc
            "abbrev": 0.4,
        }
    )


config = Config()


def _pos_weight(pos_tag: str) -> float:
    tag = (pos_tag or "").lower()
    return config.POS_WEIGHTS.get(tag, 1.0)


def _parse_pos(pos_value: Any) -> list[str]:
    if pos_value is None:
        raise ValueError("POS value cannot be None.")
    if isinstance(pos_value, (list, tuple)):
        return [str(x) for x in pos_value]
    if isinstance(pos_value, str) and pos_value.strip():
        try:
            parsed = json.loads(pos_value)
        except json.JSONDecodeError as exc:
            raise ValueError("POS must be stored as a JSON array string.") from exc
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        raise ValueError("POS JSON must decode to an array.")
    raise TypeError(
        "Unsupported POS payload type. Expected JSON array string or list/tuple."
    )


def _dynamic_bleu_weights(
    max_order: int,
    reference_pos: Optional[Iterable[str]] = None,
) -> list[float]:
    if reference_pos is None:
        raise ValueError(
            "reference_pos is required. Compute POS once during initialization and pass it to f1()."
        )
    pos_tags = _parse_pos(reference_pos)
    if not pos_tags:
        raise ValueError(
            "reference_pos is empty. POS must be precomputed in initialization stage."
        )

    token_weights = [_pos_weight(tag) for tag in pos_tags] or [1.0]
    avg_weight = float(sum(token_weights) / len(token_weights))
    order_scores = [
        (avg_weight**n) / np.sqrt(float(n)) for n in range(1, max_order + 1)
    ]
    total = float(sum(order_scores))

    return [float(x / total) for x in order_scores]


def f1(
    reference,
    candidate,
    wheights: Optional[list[float]] = None,
    max_order=2,
    reference_pos: Optional[Iterable[str]] = None,
):
    bleu_metric = evaluate.load("bleu")
    rouge_metric = evaluate.load("rouge")
    if wheights is None:
        wheights = _dynamic_bleu_weights(
            max_order=max_order,
            reference_pos=reference_pos,
        )
    if len(wheights) != max_order:
        raise ValueError(f"Length of weights must match max_order ({max_order}).")

    bleu_results = bleu_metric.compute(
        predictions=candidate,
        references=reference,
        max_order=max_order,
        weights=wheights,
    )
    rouge_results = rouge_metric.compute(predictions=candidate, references=reference)

    P = bleu_results["bleu"]
    R = rouge_results["rougeL"]
    beta = 0.7

    denom = (beta**2 * P + R) or 1e-12
    f1_score = (1 + beta**2) * (P * R) / denom
    print(f"BLEU (P):   {P*100:.2f}")
    print(f"ROUGE-L (R): {R*100:.2f}")
    print(f"F1 (β=0.7): {f1_score*100:.2f}")
    return {"bleu": P, "rougeL": R, "f1": f1_score, "weights": wheights}


f1(docs, docs)


if __name__ == "__main__":
    f1(docs, docs)
