from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool
from typing import Any, Iterable, Optional

import arabic_reshaper
import evaluate
import numpy as np
from bidi.algorithm import get_display
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tagger.default import DefaultTagger
from sklearn.feature_extraction.text import TfidfVectorizer

from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize
from Tafsir.pipeline.analysis.sahihah.tools.tuning import ranking_init

@dataclass
class Config:
    db_path: str = "/home/muhammed-emin-eser/desk/apps/Auto-Classify-Hadiths/hadith/"
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
    hadith_txt: str = "/home/muhammed-emin-eser/desk/apps/Auto-Classify-Hadiths/Tafsir/pipeline/analysis/sahihah/sahihah_hadith_extracted_in_sittah.txt"
    pre_defined_stop_words: str = "path/to/pre"
    POS_WEIGHTS: dict[str, float] = field(
        default_factory=lambda: {
            "noun": 1.5,
            "verb": 1.2,
            "adj": 1.0,
            "prep": 0.2,
            "pron": 0.1,
        }
    )


config = Config()

cand_txt: dict[str, list[int]] = defaultdict(list)
cand_meta: dict[str, dict[str, Any]] = {}

class Utils:
    _mled: Optional[MLEDisambiguator] = None
    _tagger: Optional[DefaultTagger] = None

    @staticmethod
    def norm(text):
        return " ".join(normalize(text))

    @staticmethod
    def ar(text):
        return get_display(arabic_reshaper.reshape(text))

    @classmethod
    def _get_pos_tagger(utils_class) -> DefaultTagger:
        if utils_class._tagger is None:
            utils_class._mled = MLEDisambiguator.pretrained()
            utils_class._tagger = DefaultTagger(utils_class._mled, "pos")
        return utils_class._tagger

    @classmethod
    def tag_pos_tokens(utils_class, tokens: list[str]) -> list[str]:
        if not tokens:
            return []
        tagger = utils_class._get_pos_tagger()
        return list(tagger.tag(tokens))

    @classmethod
    def tag_pos_text(utils_class, text: str) -> list[str]:
        return utils_class.tag_pos_tokens(Utils.norm(text).split())

    @staticmethod
    def get_txt_from_db(current_db, config=config):
        return ranking_init.get_txt_from_db(
            current_db,
            config=config,
            norm_fn=Utils.norm,
            tag_pos_tokens_fn=Utils.tag_pos_tokens,
        )

    @staticmethod
    def get_cand_txt():
        global cand_txt
        global cand_meta
        cand_txt, cand_meta = ranking_init.build_candidate_cache(
            config.hadith_txt,
            norm_fn=Utils.norm,
            tag_pos_tokens_fn=Utils.tag_pos_tokens,
        )

    @staticmethod
    def run():
        with Pool(initializer=Utils.get_cand_txt) as pool:
            db_rows_by_book = pool.map(utils.get_txt_from_db, config.dbs)
        for db_rows in db_rows_by_book:
            instances.match(db_rows, cand_txt)
        return instances

utils = Utils()

class StopWords:
    pos_wheights = config.POS_WEIGHTS

    @staticmethod
    def stop_words():
        docs = [meta["normalized"] for meta in cand_meta.values()]
        if not docs:
            # return {"p95": 0.0, "words_above_p95": [], "tag_count": {}}
            raise ValueError("No documents available to compute stop words.")
        tfidf_matrix, fitted_vec = vec(
            docs,
            stop_words=None,
            max_df=_dynamic_max_df(docs),
            return_vectorizer=True,
        )
        vocab_indices = list(fitted_vec.vocabulary_.values())
        ratios = np.array([
            (tfidf_matrix[:, idx] > 0).sum() / len(docs)
            for idx in vocab_indices
        ])
        p95 = np.percentile(ratios, 95)
        words = list(fitted_vec.vocabulary_.keys())

        def words_above(threshold):
            return [words[i] for i, r in enumerate(ratios) if r > threshold]

        tags = Utils.tag_pos_tokens(words_above(p95))
        tag_count = Counter(tags)
        return {
            "hint": 
            "p95 ist die dynamische Schwelle fuer sehr haeufige Woerter; "
            "words_above_p95 zeigt potenzielles Rauschen; "
            "tag_count zeigt die POS-Verteilung dieser haeufigen Woerter zur Plausibilisierung.",
            
            "p95": float(p95),
            "words_above_p95": words_above(p95),
            "tag_count": dict(tag_count),
        }


def _dynamic_max_df(corpus) -> float:
    docs = [utils.norm(doc).split() for doc in corpus if str(doc).strip()]
    if not docs:
        return 1.0
    doc_count = len(docs)
    df_counter = Counter()
    for tokens in docs:
        df_counter.update(set(tokens))
    if not df_counter:
        return 1.0
    ratios = np.array([count / float(doc_count) for count in df_counter.values()])
    p95 = float(np.percentile(ratios, 95))
    return min(0.99, max(0.01, p95))


def vec(corpus, stop_words=None, max_df=None, return_vectorizer=False):
    if max_df is None:
        max_df = _dynamic_max_df(corpus)
    fitted_vec = TfidfVectorizer(
        preprocessor=utils.norm, stop_words=stop_words, max_df=max_df
    )
    tfidf_matrix = fitted_vec.fit_transform(corpus)
    if return_vectorizer:
        return tfidf_matrix, fitted_vec
    return tfidf_matrix


def _coarse_pos(pos_tag: str) -> str:
    tag = (pos_tag or "").lower()
    if "noun" in tag or tag.startswith("n"):
        return "noun"
    if "verb" in tag or tag.startswith("v"):
        return "verb"
    if "adj" in tag or tag.startswith("adj"):
        return "adj"
    if "prep" in tag:
        return "prep"
    if "pron" in tag:
        return "pron"
    ValueError(f"Unknown POS tag: {pos_tag}")


def _pos_weight(pos_tag: str) -> float:
    return config.POS_WEIGHTS[_coarse_pos(pos_tag)]


def _parse_pos(pos_value: Any) -> list[str]:
    if pos_value is None:
        raise ValueError("POS value cannot be None.")
    if isinstance(pos_value, (list, tuple)):
        return [str(x) for x in pos_value]
    if isinstance(pos_value, str) and pos_value.strip():
        try:
            parsed = json.loads(pos_value)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "POS must be stored as a JSON array string."
            ) from exc
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        raise ValueError("POS JSON must decode to an array.")
    raise TypeError("Unsupported POS payload type. Expected JSON array string or list/tuple.")


def _flatten_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        out: list[str] = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            elif isinstance(item, (list, tuple)):
                out.extend(str(x) for x in item)
            else:
                out.append(str(item))
        return out
    return [str(value)]


def _dynamic_bleu_weights(
    reference: Any,
    candidate: Any,
    max_order: int,
    reference_pos: Optional[Iterable[str]] = None,
    candidate_pos: Optional[Iterable[str]] = None,
) -> list[float]:
    pos_tags: list[str] = []
    if reference_pos is not None:
        pos_tags.extend(_parse_pos(reference_pos))
    if candidate_pos is not None:
        pos_tags.extend(_parse_pos(candidate_pos))

    if not pos_tags:
        texts = _flatten_texts(reference) + _flatten_texts(candidate)
        for text in texts:
            pos_tags.extend(Utils.tag_pos_text(text))

    token_weights = [_pos_weight(tag) for tag in pos_tags] or [1.0]
    avg_weight = float(sum(token_weights) / len(token_weights))
    order_scores = [
        (avg_weight**n) / np.sqrt(float(n))
        for n in range(1, max_order + 1)
    ]
    total = sum(order_scores)
    if total == 0:
        raise ValueError("Total weight cannot be zero.")
    total = float(total)

    return [float(x / total) for x in order_scores]


def f1(
    reference,
    candidate,
    wheights: Optional[list[float]] = None,
    max_order=2,
    reference_pos: Optional[Iterable[str]] = None,
    candidate_pos: Optional[Iterable[str]] = None,
):
    bleu_metric = evaluate.load("bleu")
    rouge_metric = evaluate.load("rouge")
    if wheights is None:
        wheights = _dynamic_bleu_weights(
            reference,
            candidate,
            max_order=max_order,
            reference_pos=reference_pos,
            candidate_pos=candidate_pos,
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

class Ranking:
    def __init__(self, top=None, medium=None, low=None):
        self.top: list[tuple[int, int]] = top or []
        self.medium: list[tuple[int, int]] = medium or []
        self.low: list[tuple[int, int]] = low or []

    def match(self, db, cand_txt):
        for cand_text, cand_ids in cand_txt.items():
            cand_norm = cand_meta.get(cand_text, {}).get("normalized", utils.norm(cand_text))
            for row in db:
                db_text, db_id, db_norm, _db_pos = row
                db_norm = db_norm or utils.norm(db_text)
                for cand_id in cand_ids:
                    if TopLevel.is_equal(db_norm, cand_norm):
                        self.top.append((cand_id, db_id))
                    elif TopLevel.like_equal(db_norm, cand_norm):
                        self.top.append((cand_id, db_id))
                    elif Medium.includes(db_norm, cand_norm):
                        self.medium.append((cand_id, db_id))
                    elif Medium.part_of(db_norm, cand_norm):
                        self.medium.append((cand_id, db_id))
                    elif Low.like(db_norm, cand_norm):
                        self.low.append((cand_id, db_id))

class TopLevel(Ranking):
    def is_equal(db, txt):
        return db == txt

    def like_equal(db, txt):
        A = db.split()
        B = txt.split()
        if len(set(A) ^ set(B)) < 10:
            return True
        return False
    
class Medium(Ranking):
    def includes(db, txt):
        if txt and txt in db:
            return True
        return False

    def part_of(db, txt):
        if db and db in txt:
            return True
        return False

class Low(Ranking):
    def like(db, txt):
        return bool(set(db.split()) & set(txt.split()))


instances = Ranking(top=[], medium=[], low=[])

def main():
    Utils.run()

if __name__ == "__main__":
    main()
