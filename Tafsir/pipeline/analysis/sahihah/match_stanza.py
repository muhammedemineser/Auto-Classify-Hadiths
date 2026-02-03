from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    import stanza  # type: ignore
except Exception:  # pragma: no cover
    stanza = None  # type: ignore


@dataclass
class StanzaConfig:
    cache_path: Path = Path("/app/tools/sahihah/cache/stanza_cache.db")


class StanzaCache:
    def __init__(self, config: StanzaConfig, normalize_func: Callable[[Any], str]):
        self.config = config
        self._normalize = normalize_func
        self._conn = sqlite3.connect(str(config.cache_path))
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS stanza_cache (
                hadith_id INTEGER PRIMARY KEY,
                pos_map TEXT
            )
            """
        )
        self._conn.commit()
        self._nlp = None

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def _ensure_nlp(self) -> None:
        if self._nlp is not None:
            return
        if stanza is None:
            raise RuntimeError("stanza is not available")
        self._nlp = stanza.Pipeline(
            "ar",
            processors="tokenize,pos",
            tokenize_no_ssplit=True,
            verbose=False,
        )

    def _cache_get(self, hadith_id: int) -> Optional[Dict[str, str]]:
        cur = self._conn.cursor()
        cur.execute(
            "SELECT pos_map FROM stanza_cache WHERE hadith_id=?",
            (hadith_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except Exception:
            return None

    def _cache_put(self, hadith_id: int, pos_map: Dict[str, str]) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO stanza_cache (hadith_id, pos_map) VALUES (?, ?)",
            (hadith_id, json.dumps(pos_map, ensure_ascii=False)),
        )
        self._conn.commit()

    def get_pos_map(self, hadith_id: int, text: str) -> Dict[str, str]:
        cached = self._cache_get(hadith_id)
        if cached is not None:
            return cached

        self._ensure_nlp()
        doc = self._nlp(text)
        pos_counts: Dict[str, Dict[str, int]] = {}
        for sent in doc.sentences:
            for word in sent.words:
                norm = self._normalize(word.text)
                if not norm:
                    continue
                for token in norm.split():
                    pos_counts.setdefault(token, {})
                    pos_counts[token][word.upos] = pos_counts[token].get(word.upos, 0) + 1

        pos_map: Dict[str, str] = {}
        for token, counts in pos_counts.items():
            pos_map[token] = max(counts.items(), key=lambda kv: kv[1])[0]

        self._cache_put(hadith_id, pos_map)
        return pos_map
