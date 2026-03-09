from __future__ import annotations

import json
import sqlite3
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
    def _get_pos_tagger(cls) -> DefaultTagger:
        if cls._tagger is None:
            cls._mled = MLEDisambiguator.pretrained()
            cls._tagger = DefaultTagger(cls._mled, "pos")
        return cls._tagger

    @classmethod
    def tag_pos_tokens(cls, tokens: list[str]) -> list[str]:
        if not tokens:
            return []
        tagger = cls._get_pos_tagger()
        return list(tagger.tag(tokens))

    @classmethod
    def tag_pos_text(cls, text: str) -> list[str]:
        return cls.tag_pos_tokens(Utils.norm(text).split())

    @staticmethod
    def _ensure_cached_columns(conn: sqlite3.Connection, config=config) -> None:
        cur = conn.cursor()
        cols = {
            row[1]
            for row in cur.execute(f"PRAGMA table_info({config.table})").fetchall()
        }
        if config.normalized_col not in cols:
            cur.execute(
                f"ALTER TABLE {config.table} ADD COLUMN {config.normalized_col} TEXT"
            )
        if config.pos_col not in cols:
            cur.execute(f"ALTER TABLE {config.table} ADD COLUMN {config.pos_col} TEXT")
        conn.commit()

    @staticmethod
    def _backfill_cache_columns(conn: sqlite3.Connection, config=config) -> None:
        cur = conn.cursor()
        rows = cur.execute(
            f"""
            SELECT rowid, {config.text_col}, {config.normalized_col}, {config.pos_col}
            FROM {config.table}
            """
        ).fetchall()
        for rowid, raw_text, normalized_cached, pos_cached in rows:
            text = raw_text or ""
            normalized_value = normalized_cached
            if not normalized_value:
                normalized_value = Utils.norm(text)
                cur.execute(
                    f"""
                    UPDATE {config.table}
                    SET {config.normalized_col}=?
                    WHERE rowid=?
                    """,
                    (normalized_value, rowid),
                )
            if not pos_cached:
                pos_tags = Utils.tag_pos_tokens(normalized_value.split())
                cur.execute(
                    f"""
                    UPDATE {config.table}
                    SET {config.pos_col}=?
                    WHERE rowid=?
                    """,
                    (json.dumps(pos_tags, ensure_ascii=False), rowid),
                )
        conn.commit()

    @staticmethod
    def ensure_cached_columns(current_db, config=config):
        conn = sqlite3.connect(config.db_path + f"/{current_db}")
        try:
            Utils._ensure_cached_columns(conn, config=config)
            Utils._backfill_cache_columns(conn, config=config)
        finally:
            conn.close()

    @staticmethod
    def get_txt_from_db(current_db, config=config):
        Utils.ensure_cached_columns(current_db, config=config)
        conn = sqlite3.connect(config.db_path + f"/{current_db}")
        try:
            cur = conn.cursor()
            rows = cur.execute(
                f"""
                SELECT
                    {config.text_col},
                    {config.id_col},
                    {config.normalized_col},
                    {config.pos_col}
                FROM {config.table}
                """
            ).fetchall()
            return rows
        finally:
            conn.close()

    @staticmethod
    def get_cand_txt():
        global cand_txt
        global cand_meta
        with open(config.hadith_txt, "r") as f:
            txt = f.readlines()
        cand_txt = defaultdict(list)
        for i, line in enumerate(txt):
            line = line.strip()
            if not line:
                continue
            cand_txt[line].append(i)
        cand_meta = {}
        for line in cand_txt.keys():
            normalized_value = Utils.norm(line)
            cand_meta[line] = {
                "normalized": normalized_value,
                "pos": Utils.tag_pos_tokens(normalized_value.split()),
            }

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
            return {"p95": 0.0, "words_above_p95": [], "tag_count": {}}
        X, fitted_vec = vec(docs, stop_words=None, max_df=1.0, return_vectorizer=True)
        vocab_indices = list(fitted_vec.vocabulary_.values())
        ratios = np.array([
            (X[:, idx] > 0).sum() / len(docs)
            for idx in vocab_indices
        ])
        p95 = np.percentile(ratios, 95)
        words = list(fitted_vec.vocabulary_.keys())

        def words_above(threshold):
            return [words[i] for i, r in enumerate(ratios) if r > threshold]

        tags = Utils.tag_pos_tokens(words_above(p95))
        tag_count = Counter(tags)
        return {
            "p95": float(p95),
            "words_above_p95": words_above(p95),
            "tag_count": dict(tag_count),
        }


def vec(corpus, stop_words=None, max_df=1.0, return_vectorizer=False):
    fitted_vec = TfidfVectorizer(
        preprocessor=utils.norm, stop_words=stop_words, max_df=max_df
    )
    X = fitted_vec.fit_transform(corpus)
    if return_vectorizer:
        return X, fitted_vec
    return X


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
    return config.POS_WEIGHTS.get(_coarse_pos(pos_tag), 1.0)


def _parse_pos(pos_value: Any) -> list[str]:
    if isinstance(pos_value, list):
        return [str(x) for x in pos_value]
    if isinstance(pos_value, str) and pos_value.strip():
        try:
            parsed = json.loads(pos_value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return pos_value.split()
    return []


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
    total = float(sum(order_scores)) or 1.0
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
        if len(wheights) > max_order:
            wheights = wheights[:max_order]
        else:
            missing = max_order - len(wheights)
            wheights = list(wheights) + ([0.0] * missing)
        total = float(sum(wheights)) or 1.0
        wheights = [float(x / total) for x in wheights]

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
