from __future__ import annotations
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import json
import os
import re
from collections import OrderedDict, defaultdict
from threading import Lock
from time import monotonic
from typing import Dict, Iterable, List, Tuple

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DATA_PATH = os.getenv("TAFSIR_DATA", "data/tafsir_merged_sorted.json")
QURAN_PATH = os.getenv("QURAN_TEXT_PATH", "quran-simple-plain.txt")
CACHE_TTL_SECONDS = int(os.getenv("TAFSIR_CACHE_TTL", "300"))
CACHE_MAXSIZE = int(os.getenv("TAFSIR_CACHE_SIZE", "256"))


# ---------------- Quran metadata ----------------

SURAH_NAMES = [
    "الفاتحة",
    "البقرة",
    "آل عمران",
    "النساء",
    "المائدة",
    "الأنعام",
    "الأعراف",
    "الأنفال",
    "التوبة",
    "يونس",
    "هود",
    "يوسف",
    "الرعد",
    "إبراهيم",
    "الحجر",
    "النحل",
    "الإسراء",
    "الكهف",
    "مريم",
    "طه",
    "الأنبياء",
    "الحج",
    "المؤمنون",
    "النور",
    "الفرقان",
    "الشعراء",
    "النمل",
    "القصص",
    "العنكبوت",
    "الروم",
    "لقمان",
    "السجدة",
    "الأحزاب",
    "سبأ",
    "فاطر",
    "يس",
    "الصافات",
    "ص",
    "الزمر",
    "غافر",
    "فصلت",
    "الشورى",
    "الزخرف",
    "الدخان",
    "الجاثية",
    "الأحقاف",
    "محمد",
    "الفتح",
    "الحجرات",
    "ق",
    "الذاريات",
    "الطور",
    "النجم",
    "القمر",
    "الرحمن",
    "الواقعة",
    "الحديد",
    "المجادلة",
    "الحشر",
    "الممتحنة",
    "الصف",
    "الجمعة",
    "المنافقون",
    "التغابن",
    "الطلاق",
    "التحريم",
    "الملك",
    "القلم",
    "الحاقة",
    "المعارج",
    "نوح",
    "الجن",
    "المزمل",
    "المدثر",
    "القيامة",
    "الإنسان",
    "المرسلات",
    "النبأ",
    "النازعات",
    "عبس",
    "التكوير",
    "الانفطار",
    "المطففين",
    "الانشقاق",
    "البروج",
    "الطارق",
    "الأعلى",
    "الغاشية",
    "الفجر",
    "البلد",
    "الشمس",
    "الليل",
    "الضحى",
    "الشرح",
    "التين",
    "العلق",
    "القدر",
    "البينة",
    "الزلزلة",
    "العاديات",
    "القارعة",
    "التكاثر",
    "العصر",
    "الهمزة",
    "الفيل",
    "قريش",
    "الماعون",
    "الكوثر",
    "الكافرون",
    "النصر",
    "المسد",
    "الإخلاص",
    "الفلق",
    "الناس",
]


def load_quran_metadata(path: str) -> Dict[int, Dict]:
    """Create a lookup from global ayah index to sura/ayah metadata."""
    mapping: Dict[int, Dict] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, raw_line in enumerate(f, 1):
                line = raw_line.strip()
                if not line:
                    continue
                parts = line.split("|", 2)
                if len(parts) < 3:
                    continue
                try:
                    sura_num = int(parts[0])
                    ayah_num = int(parts[1])
                except ValueError:
                    continue

                ayah_text = parts[2]
                sura_name = SURAH_NAMES[sura_num - 1] if 0 < sura_num <= len(SURAH_NAMES) else ""
                mapping[idx] = {
                    "sura_number": sura_num,
                    "sura_name": sura_name,
                    "ayah_number": ayah_num,
                    "ayah_text": ayah_text,
                }
    except FileNotFoundError:
        print(f"WARNING: Quran text file not found at {path}, sura metadata disabled.")
    except Exception as exc:  # pragma: no cover - best effort logging
        print(f"WARNING: Failed to read Quran metadata from {path}: {exc}")

    return mapping


# ---------------- Normalization ----------------

ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
TATWEEL = "\u0640"
PUNCT_RE = re.compile(r"[^\w\s\u0600-\u06FF]")
WHITESPACE_RE = re.compile(r"\s+")


def normalize(text: str) -> str:
    text = text.replace(TATWEEL, "")
    text = ARABIC_DIACRITICS_RE.sub("", text)
    text = PUNCT_RE.sub(" ", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip().lower()


# ---------------- TTL Cache ----------------


class TTLCache:
    """Tiny thread-safe TTL cache for search results."""

    def __init__(self, maxsize: int = 256, ttl: int = 300):
        self.maxsize = maxsize
        self.ttl = ttl
        self._store: "OrderedDict[str, Tuple[float, object]]" = OrderedDict()
        self._lock = Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def _purge_expired(self, now: float) -> None:
        expired_keys = [k for k, (exp, _) in self._store.items() if exp < now]
        for key in expired_keys:
            self._store.pop(key, None)

    def get(self, key: str):
        now = monotonic()
        with self._lock:
            self._purge_expired(now)
            if key not in self._store:
                self.misses += 1
                return None
            exp, value = self._store.pop(key)  # pop to move to end
            if exp < now:
                self.misses += 1
                return None
            self.hits += 1
            self._store[key] = (exp, value)
            return value

    def set(self, key: str, value) -> None:
        now = monotonic()
        with self._lock:
            self._purge_expired(now)
            if key in self._store:
                self._store.pop(key, None)
            elif len(self._store) >= self.maxsize:
                self._store.popitem(last=False)
                self.evictions += 1
            self._store[key] = (now + self.ttl, value)

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "size": len(self._store),
            "maxsize": self.maxsize,
            "ttl_seconds": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
        }


# ---------------- Data loading ----------------


def load_blocks(path: str, quran_meta: Dict[int, Dict] | None = None) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    arr = raw["blocks"] if isinstance(raw, dict) and "blocks" in raw else raw
    blocks = []
    for i, item in enumerate(arr, 1):
        if isinstance(item, dict):
            text = str(item.get("text", ""))
            # Probiere verschiedene ID-Keys
            block_id = item.get("id") or item.get("block_id") or i

            # Probiere verschiedene Source-Keys
            source = (
                item.get("source")
                or item.get("book")
                or item.get("tafsir")
                or "unbekannt"
            )

            hadiths = item.get("hadiths", [])
        else:
            text, block_id, source, hadiths = str(item), i, "unbekannt", []

        block_data = {"id": block_id, "text": text, "source": source, "hadiths": hadiths}

        if quran_meta:
            try:
                meta = quran_meta.get(int(block_id))  # type: ignore[arg-type]
            except (TypeError, ValueError):
                meta = None
            if meta:
                block_data.update(meta)

        blocks.append(block_data)
        print(f"DEBUG: Erster Block geladen: {blocks[0] if blocks else 'KEINE DATEN'}")
    return blocks


# ---------------- Search Engine ----------------


class SearchEngine:
    def __init__(self, blocks: List[Dict]):
        self.blocks = blocks
        self.by_id = {b["id"]: b for b in blocks}
        self.total = len(blocks)
        self.cache = TTLCache(maxsize=CACHE_MAXSIZE, ttl=CACHE_TTL_SECONDS)

        self.normalized: Dict[int, str] = {}
        self.index: Dict[str, set] = defaultdict(set)

        for block in blocks:
            bid = block["id"]
            norm_text = normalize(block["text"])
            self.normalized[bid] = norm_text

            for token in set(norm_text.split()):
                if token:
                    self.index[token].add(bid)

    def slice(self, offset: int, limit: int) -> List[Dict]:
        if offset < 0 or limit < 0:
            raise ValueError("offset and limit must be non-negative")
        return [dict(self.by_id[b["id"]]) for b in self.blocks[offset : offset + limit]]

    def _rank_candidates(
        self, candidate_ids: Iterable[int], tokens: List[str], norm_query: str
    ) -> List[int]:
        scored: List[Tuple[int, int]] = []
        for bid in candidate_ids:
            text = self.normalized.get(bid, "")
            score = sum(1 for tok in tokens if tok and tok in text)
            if not score and norm_query in text:
                score = 1
            scored.append((score, bid))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [bid for _, bid in scored]

    def _compute_ordered_ids(self, tokens: List[str], norm_query: str) -> List[int]:
        if not tokens and not norm_query:
            return []

        token_sets = [self.index.get(tok, set()) for tok in tokens if tok]
        candidate_ids: set

        if token_sets and all(token_sets):
            candidate_ids = set.intersection(*token_sets)
        else:
            candidate_ids = set()

        if not candidate_ids and token_sets:
            candidate_ids = set().union(*token_sets)

        if not candidate_ids and norm_query:
            candidate_ids = {
                bid for bid, text in self.normalized.items() if norm_query in text
            }

        return self._rank_candidates(candidate_ids, tokens, norm_query)

    def search(self, query: str, limit: int = 50, offset: int = 0) -> Dict:
        if not query.strip():
            raise ValueError("query must not be empty")
        if limit < 1 or offset < 0:
            raise ValueError("limit must be >=1 and offset >=0")

        norm_query = normalize(query)
        if len(norm_query) < 2:
            raise ValueError("query too short; provide at least 2 letters")

        cached = self.cache.get(norm_query)
        cache_hit = cached is not None

        start = monotonic()
        if cached is None:
            tokens = [tok for tok in norm_query.split() if tok]
            ordered_ids = self._compute_ordered_ids(tokens, norm_query)
            cached = {"ordered_ids": ordered_ids}
            self.cache.set(norm_query, cached)
        else:
            ordered_ids = cached["ordered_ids"]

        total = len(ordered_ids)
        sliced_ids = ordered_ids[offset : offset + limit]
        results = [dict(self.by_id[bid]) for bid in sliced_ids if bid in self.by_id]
        took_ms = round((monotonic() - start) * 1000, 2)

        return {
            "query": query,
            "normalized_query": norm_query,
            "total": total,
            "offset": offset,
            "limit": limit,
            "returned": len(results),
            "cached": cache_hit,
            "took_ms": took_ms,
            "results": results,
        }


# ---------------- App setup ----------------

app = FastAPI(title="Tafsir Search API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

QURAN_META = load_quran_metadata(QURAN_PATH)
engine = SearchEngine(load_blocks(DATA_PATH, quran_meta=QURAN_META))

# Static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Data files (json)
app.mount("/data", StaticFiles(directory="data"), name="data")


@app.get("/")
async def root():
    return FileResponse("static/viewer.html")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "total_blocks": engine.total,
        "cache": engine.cache.stats,
        "data_path": DATA_PATH,
    }


@app.get("/api/blocks")
async def get_blocks(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=200),
):
    try:
        items = engine.slice(offset, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return {
        "offset": offset,
        "limit": limit,
        "total": engine.total,
        "returned": len(items),
        "results": items,
    }


@app.get("/api/search")
async def search(
    q: str = Query(..., description="Search query"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        return engine.search(q, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/block/{block_id}")
async def get_block(block_id: int):
    block = engine.by_id.get(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="block not found")
    return block


# Gunicorn/Uvicorn entrypoint helper:
def get_app():
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
