from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pyarrow.parquet as pq

try:
    from rank_bm25 import BM25Okapi  # type: ignore
except Exception:  # pragma: no cover - import guard for optional dependency
    BM25Okapi = None


@dataclass(frozen=True)
class BM25Config:
    k1: float = 1.5
    b: float = 0.75


class BM25Index:
    def __init__(self, tokens: List[List[str]], config: BM25Config) -> None:
        if BM25Okapi is None:
            raise ImportError(
                "rank_bm25 is required for BM25 candidate generation. "
                "Install with: pip install rank-bm25"
            )
        self._bm25 = BM25Okapi(tokens, k1=config.k1, b=config.b)
        self.doc_count = len(tokens)

    def topk(self, query_tokens: Sequence[str], k: int) -> List[int]:
        if not query_tokens or self.doc_count <= 0:
            return []
        scores = self._bm25.get_scores(list(query_tokens))
        n = int(scores.shape[0])
        if n <= 0:
            return []
        k = max(1, int(k))
        if k >= n:
            order = np.lexsort((np.arange(n), -scores))
            return order.tolist()
        top = np.argpartition(scores, -k)[-k:]
        order = top[np.lexsort((top, -scores[top]))]
        return order.tolist()


def _load_tokens_from_parquet(parquet_path: Path) -> List[List[str]]:
    table = pq.read_table(str(parquet_path), columns=["tokens_norm"])
    tokens = table["tokens_norm"].to_pylist()
    return [t or [] for t in tokens]


def build_bm25_index(parquet_path: Path, config: BM25Config) -> BM25Index:
    tokens = _load_tokens_from_parquet(parquet_path)
    return BM25Index(tokens, config)


def build_bm25_indexes(
    db_paths: Iterable[str],
    parquet_map: Dict[str, Path],
    config: BM25Config,
) -> Dict[str, BM25Index]:
    indexes: Dict[str, BM25Index] = {}
    for db_path in db_paths:
        parquet_path = parquet_map.get(db_path)
        if parquet_path is None:
            continue
        indexes[db_path] = build_bm25_index(parquet_path, config)
    return indexes
