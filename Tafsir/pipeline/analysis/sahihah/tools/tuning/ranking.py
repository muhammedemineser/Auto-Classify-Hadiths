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
from multiprocessing import Pool
from dataclasses import field
from collections import defaultdict

@dataclass
class Config:
    db_path: str = "/home/muhammed-emin-eser/desk/apps/Auto-Classify-Hadiths/hadith/"
    dbs = ["Bukhari.db", "Muslim.db", "AbuDaud.db", "Tirmizi.db", "Nesai.db", "IbnMaja.db"]
    table: str = "hadiths"
    id_col: str = "Hadith_number"
    text_col: str = "Arabic_Matn"
    hadith_txt: str = "/home/muhammed-emin-eser/desk/apps/Auto-Classify-Hadiths/Tafsir/pipeline/analysis/sahihah/sahihah_hadith_extracted_in_sittah.txt"
    pre_defined_stop_words: str = "path/to/pre"
    POS_WEIGHTS = {
    'noun': 1.5,
    'verb': 1.2,
    'adj':  1.0,
    'prep': 0.2,   
    'pron': 0.1,
}
config = Config()

@dataclass
class Instances:
    top_level: TopLevel = field(default_factory=TopLevel)
    medium: Medium = field(default_factory=Medium)
    low: Low = field(default_factory=Low)

instances = Instances()

class Utils:
    def norm(text):
        return " ".join(normalize(text))

    def ar(text):
        return get_display(arabic_reshaper.reshape(text))
    
    def get_txt_from_db(current_db, config=config):
        conn = sqlite3.connect(config.db_path + f"/{current_db}")
        cur = conn.cursor()
        text = cur.execute(f"SELECT {config.text_col},{config.id_col} FROM {config.table}").fetchall()
        return text
    def get_cand_txt():
        global cand_txt
        with open(config.hadith_txt, "r") as f:
            txt = f.readlines()
        cand_txt = defaultdict(list)
        for i, line in enumerate(txt):
            cand_txt[line].append(i)
        dict(cand_txt)

    def run():
        with Pool(initializer=Utils.get_cand_txt) as pool:
            result = pool.map_async(utils.get_txt_from_db, config.dbs)
            bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah = result.get()
            pool.join()
            pool.map_async(
                instances.match(bukhari.get()),
                cand_txt
            )
            pool.map_async(
                instances.match(muslim.get()),
                cand_txt
            )
            pool.map_async(
                instances.match(abudawud.get()),
                cand_txt
            )
            pool.map_async(
                instances.match(tirmidhi.get()),
                cand_txt
            )
            pool.map_async(
                instances.match(nasai.get()),
                cand_txt
            )
            pool.map_async(
                instances.match(ibnmajah.get()),
                cand_txt
            )

utils = Utils()

class StopWords:
    pos_wheights = config.POS_WEIGHTS

    def stop_words():
        X = vec()
        ratios = np.array([
            (X[:, idx] > 0).sum() / len(docs)
            for idx in vec.vocabulary_.values()
        ])
        p95 = np.percentile(ratios, 95)
        words = list(vec.vocabulary_.keys())

        def words_above(threshold):
            return [Utils.ar(words[i]) for i, r in enumerate(ratios) if r > threshold]
        
        mled = MLEDisambiguator.pretrained()
        tagger = DefaultTagger(mled, 'pos')
        tags = tagger.tag(words_above(p95))
        tag_count = Counter(tags)

def vec(corpus, stop_words, max_df):
    vec = TfidfVectorizer(preprocessor=utils.norm, stop_words=stop_words, max_df=max_df)
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
    def __init__(self, top, medium, low):
        self.top: list[tuple[int, int]] = top
        self.medium: list[tuple[int, int]] = medium
        self.low: list[tuple[int, int]] = low

    def match(self, db, cand_txt):
        for cand in cand_txt:   
            for row in db:
                if self.TopLevel.is_equal(row[0], cand[0]):
                    self.top += (cand[1], row[1])
                elif self.TopLevel.like_equal(row[0], cand[0]):
                    self.top += (cand[1], row[1])
                elif self.Medium.includes(row[0], cand[0]):
                    self.medium += (cand[1], row[1])
                elif self.Medium.part_of(row[0], cand[0]):
                    self.medium += (cand[1], row[1])
                elif self.Low.like(row[0], cand[0]):
                    self.low += (cand[1], row[1])

class TopLevel(Ranking):
    def is_equal(db, txt):
            return True
    def like_equal(db, txt):
        if len(set(A)^set(B)) < 10:
            return True
    
class Medium(Ranking):
    def includes(db, txt):
        if A in B:
            return True

    def part_of(db, txt):
        if B in A:
            return True

class Low(Ranking):
    def like():
        return True

def main():
    Utils.run()

if __name__ == "__main__":
    main()