from sklearn.feature_extraction.text import TfidfVectorizer
from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize
import arabic_reshaper
from bidi.algorithm import get_display
from camel_tools.disambig.mle import MLEDisambiguator
from camel_tools.tagger.default import DefaultTagger
import numpy as np



path = "/home/muhammed/apps/classify/Tafsir/pipeline/analysis/sahihah/sahihah_hadith_extracted_in_sittah.txt"

with open(path, "r", encoding="utf-8") as f:
    docs = f.read().splitlines()


def stopwords(custom_stop_words):
    with open("/home/muhammed/apps/classify/Tafsir/pipeline/analysis/sahihah/stop-words.txt", "r", encoding="utf-8") as f:
        STOPWORDS = set(f.read().splitlines())
    return list(STOPWORDS.extend(custom_stop_words))


def ar(text):
    return get_display(arabic_reshaper.reshape(text))

def norm(text):
    return " ".join(normalize(text))


vec = TfidfVectorizer(preprocessor=norm)

X = vec.fit_transform(docs)

ratios = np.array([
    (X[:, idx] > 0).sum() / len(docs)
    for idx in vec.vocabulary_.values()
])

# Robuster als max(): 95. Perzentil ignoriert Ausreißer
p95 = np.percentile(ratios, 95)

words = list(vec.vocabulary_.keys())

def words_above(threshold):
    return [ar(words[i]) for i, r in enumerate(ratios) if r > threshold]

mled = MLEDisambiguator.pretrained()
tagger = DefaultTagger(mled, 'pos')
tags = tagger.tag(words_above(p95))

from collections import Counter
tag_count = Counter(tags)

POS_WEIGHTS = {
    'noun': 1.5,
    'verb': 1.2,
    'adj':  1.0,
    'prep': 0.2,   
    'pron': 0.1,
}