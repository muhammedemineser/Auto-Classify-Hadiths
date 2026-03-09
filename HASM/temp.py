from sklearn.feature_extraction.text import TfidfVectorizer
from pathlib import Path

from ranking import Utils
import arabic_reshaper
from bidi.algorithm import get_display
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tagger.default import DefaultTagger
import numpy as np
from collections import Counter


BASE_DIR = Path(__file__).resolve().parent
path_to_cand = BASE_DIR / "Data" / "Sahihah" / "sahihah_hadith_extracted_in_sittah.txt"
path_to_stop_words = BASE_DIR / "Data" / "Sahihah" / "stop-words.txt"

with open(path_to_cand, "r", encoding="utf-8") as f:
    docs = f.read().splitlines()


def stopwords(custom_stop_words):
    with open(path_to_stop_words, "r", encoding="utf-8") as f:
        STOPWORDS = set(f.read().splitlines())
    return list(STOPWORDS.extend(custom_stop_words))


def ar(text):
    return get_display(arabic_reshaper.reshape(text))


def norm(text):
    return Utils.norm(text)


vec = TfidfVectorizer(preprocessor=norm)

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

POS_WEIGHTS = {
    "noun": 1.5,
    "verb": 1.2,
    "adj": 1.0,
    "prep": 0.2,
    "pron": 0.1,
}
