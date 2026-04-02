from __future__ import annotations
import difflib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from multiprocessing import Pool
from pathlib import Path
from typing import Any, Iterable, Optional
from sacrebleu.metrics import BLEU

import arabic_reshaper
import evaluate
import numpy as np
import regex
from bidi.algorithm import get_display
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tagger.default import DefaultTagger
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from . import ranking_init
except ImportError:
    import ranking_init

BASE_DIR = Path(__file__).resolve().parent


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

cand_txt: dict[str, list[int]] = defaultdict(list)
cand_meta: dict[str, dict[str, Any]] = {}


class Utils:
    _mled: Optional[MLEDisambiguator] = None
    _tagger: Optional[DefaultTagger] = None
    RX_PREFIX_STANDALONE = regex.compile(
        r"(?<!\S)(و|ف|ب|ك|ل|س)\s+(?=\S)", regex.UNICODE
    )
    TAG_RE = re.compile(r"<[^>]+>")
    ARABIC_DIACRITICS = regex.compile(
        r"[\p{M}\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]+"
    )
    TATWEEL = "\u0640"
    NON_ARABIC = regex.compile(r"[^\p{Arabic} ]+")
    MULTI_SPACE = regex.compile(r"\s+")

    @staticmethod
    def normalize_arabic(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKD", text)
        text = Utils.ARABIC_DIACRITICS.sub("", text)
        text = text.replace(Utils.TATWEEL, "")
        text = text.translate(
            str.maketrans(
                {
                    "آ": "ا",
                    "ٱ": "ا",
                    "ى": "ي",
                    "ئ": "ي",
                    "ؤ": "و",
                    "ة": "ه",
                    "ء": "",
                    "گ": "ك",
                    "ڤ": "ف",
                    "پ": "ب",
                    "چ": "ج",
                }
            )
        )
        text = Utils.NON_ARABIC.sub(" ", text)
        text = Utils.MULTI_SPACE.sub(" ", text).strip()
        text = Utils.RX_PREFIX_STANDALONE.sub(r"\1", text)
        return unicodedata.normalize("NFKC", text)

    @staticmethod
    def normalize(text: str | None) -> list[str]:
        text = text or ""
        text = Utils.TAG_RE.sub(" ", text)
        text = " ".join(text.split())
        text = Utils.normalize_arabic(text)
        return text.split(" ") if text else []

    @staticmethod
    def norm(text):
        return " ".join(Utils.normalize(text))

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
        return cand_txt, cand_meta

    @staticmethod
    def run():
        with Pool(initializer=Utils.get_cand_txt) as pool:
            db_rows_by_book = pool.map(utils.get_txt_from_db, config.dbs)
        for db_rows in db_rows_by_book:
            instances.match(db_rows, cand_txt)
        return instances

    @staticmethod
    def char_idx_to_token_idx(tokens: str, char_idx: list) -> set:
        indexes: list[int] = []
        lengths: list[int] = []

        for idx in char_idx:
            pos = 0
            for i, token in enumerate(tokens.split()):
                pos += len(token) + 1
                if idx < pos:
                    indexes.append(i)
                    lengths.append(len(token))
                    break
        return tuple(indexes), tuple(lengths)


utils = Utils()


class StopWords:
    pos_wheights = config.POS_WEIGHTS

    @staticmethod
    def stop_words():
        docs = [meta for meta in cand_meta.keys()]
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
        ratios = np.array(
            [(tfidf_matrix[:, idx] > 0).sum() / len(docs) for idx in vocab_indices]
        )
        p95 = np.percentile(ratios, 95)
        words = list(fitted_vec.vocabulary_.keys())

        def words_above(threshold):
            return [words[i] for i, r in enumerate(ratios) if r > threshold]

        tags = Utils.tag_pos_tokens(words_above(p95))
        tag_count = Counter(tags)
        return {
            "hint": "p95 ist die dynamische Schwelle fuer sehr haeufige Woerter; "
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

    rouge_results = rouge_metric.compute(predictions=candidate, references=reference)

    bleu_obj = BLEU(max_ngram_order=max_order)
    bleu_obj.weights = wheights
    bleu_results = bleu_obj.corpus_score(candidate, [reference])
    P = bleu_results.score / 100
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

    def match(self, ref, cand):
        for cand_text, cand_ids in cand.items():
            cand_norm = cand_meta[cand_text]["normalized"]
            for row in ref:
                ref_text, ref_id, ref_norm, _ref_pos = row
                for cand_id in cand_ids:
                    if TopLevel.is_equal(ref_norm, cand_norm):
                        self.top.append((cand_id, ref_id))
                    elif TopLevel.like_equal(ref_norm, cand_norm):
                        self.top.append((cand_id, ref_id))
                    elif Medium.includes(ref_norm, cand_norm):
                        self.medium.append((cand_id, ref_id))
                    elif Medium.part_of(ref_norm, cand_norm):
                        self.medium.append((cand_id, ref_id))
                    elif Low.like(ref_norm, cand_norm):
                        self.low.append((cand_id, ref_id))


class TopLevel(Ranking):
    def is_equal(ref, cand):
        return ref == cand

    def like_equal(ref, cand):
        A = ref.split()
        B = cand.split()
        sm = difflib.SequenceMatcher(None, A, B)
        diff_len = 0

        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag != "equal":
                diff_len += max(i2 - i1, j2 - j1)

        if diff_len < len(max(A, B)) * 0.3:
            return True
        return False


class Medium(Ranking):
    def includes(ref, cand):
        if cand and cand in ref:
            return True
        return False

    def part_of(ref, cand):
        if ref and ref in cand:
            return True
        return False


class Low(Ranking):
    def like(ref, cand):
        return bool(set(ref.split()) & set(cand.split()))


instances = Ranking(top=[], medium=[], low=[])


def main():
    Utils.run()


if __name__ == "__main__":
    main()
