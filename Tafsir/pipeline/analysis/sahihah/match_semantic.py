from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    from sklearn.metrics.pairwise import cosine_similarity  # type: ignore
except Exception:  # pragma: no cover
    SentenceTransformer = None
    cosine_similarity = None


@dataclass
class SemanticConfig:
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    cache_path: Path = Path("/app/tools/sahihah/cache/semantic_cache.db")


def _ensure_hf_cache_env() -> Path:
    cache_root = Path(os.environ.get("HF_CACHE_DIR", "/work/.cache/huggingface"))
    if not cache_root.exists():
        cache_root = Path("/app/tools/sahihah/cache/huggingface")
    cache_root.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("HF_HOME", str(cache_root))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_root / "transformers"))
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(cache_root / "sentence_transformers"))
    token = os.environ.get("HF_TOKEN")
    if token and not os.environ.get("HUGGINGFACE_HUB_TOKEN"):
        os.environ["HUGGINGFACE_HUB_TOKEN"] = token
    return cache_root


class SemanticReranker:
    def __init__(self, config: SemanticConfig):
        self.config = config
        self._model = None
        self._conn = sqlite3.connect(str(config.cache_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS semantic_cache (
                hadith_id INTEGER,
                db_path TEXT,
                hadith_number TEXT,
                score REAL,
                PRIMARY KEY (hadith_id, db_path, hadith_number)
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        if SentenceTransformer is None:
            raise RuntimeError("sentence-transformers is not available")
        cache_root = _ensure_hf_cache_env()
        local_only = os.environ.get("HF_HUB_OFFLINE") == "1"
        try:
            self._model = SentenceTransformer(
                self.config.model_name,
                cache_folder=os.environ.get("SENTENCE_TRANSFORMERS_HOME"),
                local_files_only=local_only,
            )
        except TypeError:
            self._model = SentenceTransformer(
                self.config.model_name,
                cache_folder=os.environ.get("SENTENCE_TRANSFORMERS_HOME"),
            )

    def _cache_get(self, hadith_id: int, db_path: str, hadith_number: str) -> Optional[float]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT score FROM semantic_cache WHERE hadith_id=? AND db_path=? AND hadith_number=?",
            (hadith_id, db_path, hadith_number),
        )
        row = cur.fetchone()
        return float(row[0]) if row else None

    def _cache_put(self, hadith_id: int, db_path: str, hadith_number: str, score: float) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO semantic_cache (hadith_id, db_path, hadith_number, score) VALUES (?, ?, ?, ?)",
            (hadith_id, db_path, hadith_number, float(score)),
        )
        self._conn.commit()

    def similarity(self, hadith_id: int, db_path: str, hadith_number: str, text_a: str, text_b: str) -> float:
        cached = self._cache_get(hadith_id, db_path, hadith_number)
        if cached is not None:
            return cached

        self._ensure_model()
        if cosine_similarity is None:
            raise RuntimeError("scikit-learn is required for cosine similarity")

        emb_a = self._model.encode([text_a])
        emb_b = self._model.encode([text_b])
        score = float(cosine_similarity(emb_a, emb_b)[0][0])
        self._cache_put(hadith_id, db_path, hadith_number, score)
        return score
