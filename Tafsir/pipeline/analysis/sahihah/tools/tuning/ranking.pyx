from sklearn.feature_extraction.text import TfidfVectorizer
import sqlite3
from Tafsir.pipeline.analysis.sahihah import compare_txt_agains_db as pipeline
from Tafsir.pipeline.analysis.sahihah import match_cache
from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize

from Tafsir.pipeline.gemini_common import _normalize_to_string, _normalize_guard_tokens, _ngram_set

def get_txt_db(db_path: str):
    db_path = "path/to/db"
    table = "my_table"
    id_col = "id"
    text_col = "text"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    text = normalize(cur.execute(f"SELECT {text_col},{id_col} FROM {table}").fetchall())
    return text

vec = TfidfVectorizer(preprocessor=normalize)


class Ranking:


class TopLevel(Ranking):
    def is_equal(A,B):
        if A == B or A.source:
            pass
    def like_equal(A,B):
        if len(set(A)^set(B)) < 10:
            pass
        # token coverage and words wheight with "sklearn.feature_extraction.text TfidfVectorizer"

    
class Medium(Ranking):
    def includes():
    
    def part_of():

class Low(Ranking):
    def like():