from sklearn.feature_extraction.text import TfidfVectorizer
import sqlite3
from Tafsir.pipeline.analysis.sahihah import compare_txt_agains_db as pipeline
from Tafsir.pipeline.analysis.sahihah import match_cache
from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize
from sklearn.feature_extraction.text import TfidfVectorizer
from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize
import arabic_reshaper
from bidi.algorithm import get_display
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tagger.default import DefaultTagger
import evaluate
from dataclasses import dataclass
import numpy as np
from collections import Counter

@dataclass
class Config:
    db_path: str = "path/to/db"
    table: str = "my_table"
    id_col: str = "id"
    text_col: str = "text"
    ref_txt: str = "path/to/ref_txt"
    cand_txt: str = "path/to/cand_txt"
    pre_defined_stop_words: str = "path/to/pre"
    POS_WEIGHTS = {
    'noun': 1.5,
    'verb': 1.2,
    'adj':  1.0,
    'prep': 0.2,   
    'pron': 0.1,
}
config = Config()

class Utils:
    def norm(text):
        return " ".join(normalize(text))

    def ar(text):
        return get_display(arabic_reshaper.reshape(text))
    
    def get_txt_from_db(config=config):
        conn = sqlite3.connect(config.db_path)
        cur = conn.cursor()
        text = cur.execute(f"SELECT {config.text_col},{config.id_col} FROM {config.table}").fetchall()
        return text
utils = Utils()

class StopWords:
    pos_wheights = config.POS_WEIGHTS

    def p95():
        X = vec()
        ratios = np.array([
            (X[:, idx] > 0).sum() / len(docs)
            for idx in vec.vocabulary_.values()
        ])
        p95 = np.percentile(ratios, 95)
        words = list(vec.vocabulary_.keys())

        def words_above(threshold):
            return [ar(words[i]) for i, r in enumerate(ratios) if r > threshold]
        
        mled = MLEDisambiguator.pretrained()
        tagger = DefaultTagger(mled, 'pos')
        tags = tagger.tag(words_above(p95))
        tag_count = Counter(tags)
    
    def words_above(threshold):
        return [ar(words[i]) for i, r in enumerate(ratios) if r > threshold]
    
    def stopwords(custom_stop_words):
        with open(config.pre_defined_stop_words, "r", encoding="utf-8") as f:
            STOPWORDS = set(f.read().splitlines())
        return list(STOPWORDS.extend(custom_stop_words))

    def custom_stop_words():
        f1

def vec(corpus, stop_words, max_df, min_df):
    vec = TfidfVectorizer(preprocessor=utils.norm, stop_words=stop_words, max_df=max_df, min_df=min_df)
    X = vec.fit_transform(corpus)
    return X

def f1(reference, candidate, wheights:list, max_order=2):
    bleu_metric = evaluate.load("bleu")
    rouge_metric = evaluate.load("rouge")

    bleu_results = bleu_metric.compute(predictions=candidate, references=reference, max_order=max_order, wheights=wheights)
    rouge_results = rouge_metric.compute(predictions=candidate, references=reference)

    P = bleu_results['bleu']
    R = rouge_results['rougeL']
    beta = 0.7

    f1 = (1 + beta**2) * (P * R) / (beta**2 * P + R)
    print(f"BLEU (P):   {P*100:.2f}")
    print(f"ROUGE-L (R): {R*100:.2f}")
    print(f"F1 (β=0.7): {f1*100:.2f}")


class Ranking:
    pass

class TopLevel(Ranking):
    def is_equal(A,B):
        if A == B or A.source:
            pass
    def like_equal(A,B):
        if len(set(A)^set(B)) < 10:
            pass
    
class Medium(Ranking):
    def includes(A,B):
        if A in B:
            pass

    def part_of(A,B):
        if B in A:
            pass

class Low(Ranking):
    def like():
        pass