#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import glob
import sqlite3
import ast
import math
import time
import resource
import contextlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Any
from concurrent.futures import ProcessPoolExecutor

import regex as re
import sys

sys.path.insert(0, "/app")
from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize
from Tafsir.pipeline.analysis.sahihah import match_cache, match_logging, match_semantic, match_stanza

# =========================
# INPUT / OUTPUT PATHS
# =========================

HADITH_LINES_PATH = Path(
    "/app/Tafsir/pipeline/analysis/sahihah/sahihah_hadith_extracted_in_sittah.txt"
)

DB_GLOB = (
    "/app/tools/ML/Data/normalized_hadith/*.db"
)

DB_TABLE = "hadiths"
DB_COL = "arabic_matn"
DB_ID_COL = "hadith_number"

OUT_BEST_PARAMS_JSON = Path(
    "/app/tools/sahihah/best_ngram_params.json"
)
OUT_MATCHES_DB = Path(
    "/app/tools/fetch_ketab/sahihah/in_sittah_matches.db"
)

EVAL_SAMPLE_SIZE = None
SQL_CANDIDATE_LIMIT = 2500
MAX_WORKERS = os.cpu_count() or 2

# =========================
# CONFIG FLAGS
# =========================

CACHE_DIR = Path(os.environ.get("CACHE_DIR", "/app/tools/sahihah/cache"))
USE_DUCKDB = os.environ.get("USE_DUCKDB", "1") == "1"
ENABLE_STANZA = os.environ.get("ENABLE_STANZA", "1") == "1"
ENABLE_SEM_RERANK = os.environ.get("ENABLE_SEM_RERANK", "1") == "1"
DEBUG = os.environ.get("DEBUG", "1") == "1"
PLOT_COVERAGE = os.environ.get("PLOT_COVERAGE", "1") == "1"

MIN_CANDS = int(os.environ.get("MIN_CANDS", "25"))
MIN_ACCEPT_SCORE = float(os.environ.get("MIN_ACCEPT_SCORE", "0.75"))
META_STRENGTH = float(os.environ.get("META_STRENGTH", "1.0"))
TOPK_RERANK = int(os.environ.get("TOPK_RERANK", "20"))
ANCHOR_STRONG_K = int(os.environ.get("ANCHOR_STRONG_K", "3"))
ANCHOR_TOP_M = int(os.environ.get("ANCHOR_TOP_M", "10"))
ANCHOR_STRIDE = int(os.environ.get("ANCHOR_STRIDE", "25"))
ORDER_PRECHECK_PENALTY = float(os.environ.get("ORDER_PRECHECK_PENALTY", "0.9"))

# =========================
# PERFORMANCE / PROFILING
# =========================

PERF_ENABLED = os.environ.get("PERF", "1") == "1"
PERF_CPROFILE = os.environ.get("PERF_CPROFILE", "1") == "1"
PERF_TRACEMALLOC = os.environ.get("PERF_TRACEMALLOC", "1") == "1"
PERF_TRACEMALLOC_TOP = int(os.environ.get("PERF_TRACEMALLOC_TOP", "1"))
PERF_REPORT_PATH = os.environ.get("PERF_REPORT_PATH", "").strip()


def _read_proc_io() -> Dict[str, int]:
    out: Dict[str, int] = {}
    try:
        with open("/proc/self/io", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if ":" not in line:
                    continue
                k, v = line.split(":", 1)
                try:
                    out[k.strip()] = int(v.strip())
                except ValueError:
                    continue
    except FileNotFoundError:
        return {}
    return out


def _read_proc_stat_cpu() -> Dict[str, List[int]]:
    data: Dict[str, List[int]] = {}
    try:
        with open("/proc/stat", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.startswith("cpu"):
                    continue
                parts = line.split()
                key = parts[0]
                try:
                    nums = [int(x) for x in parts[1:]]
                except ValueError:
                    continue
                data[key] = nums
    except FileNotFoundError:
        return {}
    return data


def _cpu_usage_delta(start: Dict[str, List[int]], end: Dict[str, List[int]]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k, s in start.items():
        e = end.get(k)
        if not e or len(s) < 4 or len(e) < 4:
            continue
        total_s = sum(s)
        total_e = sum(e)
        idle_s = s[3] + (s[4] if len(s) > 4 else 0)
        idle_e = e[3] + (e[4] if len(e) > 4 else 0)
        total_d = total_e - total_s
        idle_d = idle_e - idle_s
        if total_d <= 0:
            continue
        out[k] = max(0.0, min(1.0, 1.0 - (idle_d / float(total_d))))
    return out


def _format_bytes(n: Optional[int]) -> str:
    if n is None:
        return "n/a"
    n = int(n)
    if n < 1024:
        return f"{n} B"
    for unit in ("KiB", "MiB", "GiB", "TiB"):
        n /= 1024.0
        if n < 1024.0:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} PiB"


class PerfTracker:
    def __init__(self, enabled: bool):
        self.enabled = enabled
        self.phases: Dict[str, float] = {}
        self.counts: Dict[str, int] = {}
        self._t0 = 0.0
        self._cpu0 = 0.0
        self._r0 = None
        self._io0: Dict[str, int] = {}
        self._stat0: Dict[str, List[int]] = {}
        self._tm_enabled = False
        self._tm_snapshot = None

    def start(self):
        if not self.enabled:
            return
        self._t0 = time.perf_counter()
        self._cpu0 = time.process_time()
        self._r0 = resource.getrusage(resource.RUSAGE_SELF)
        self._io0 = _read_proc_io()
        self._stat0 = _read_proc_stat_cpu()
        if PERF_TRACEMALLOC:
            try:
                import tracemalloc

                tracemalloc.start(25)
                self._tm_enabled = True
            except Exception:
                self._tm_enabled = False

    def count(self, key: str, value: int):
        if not self.enabled:
            return
        self.counts[key] = int(value)

    @contextlib.contextmanager
    def phase(self, name: str):
        if not self.enabled:
            yield
            return
        t0 = time.perf_counter()
        try:
            yield
        finally:
            dt = time.perf_counter() - t0
            self.phases[name] = self.phases.get(name, 0.0) + dt

    def finish(self) -> Dict[str, Any]:
        if not self.enabled:
            return {}
        t1 = time.perf_counter()
        cpu1 = time.process_time()
        r1 = resource.getrusage(resource.RUSAGE_SELF)
        io1 = _read_proc_io()
        stat1 = _read_proc_stat_cpu()
        cpu_usage = _cpu_usage_delta(self._stat0, stat1)

        tm_stats = None
        if self._tm_enabled:
            try:
                import tracemalloc

                cur, peak = tracemalloc.get_traced_memory()
                tm_stats = {"current": cur, "peak": peak}
                if PERF_TRACEMALLOC_TOP > 0:
                    snap = tracemalloc.take_snapshot()
                    top = snap.statistics("filename")[:PERF_TRACEMALLOC_TOP]
                    tm_stats["top"] = [(str(s.traceback[0]), s.size, s.count) for s in top]
                tracemalloc.stop()
            except Exception:
                tm_stats = None

        data = {
            "wall_time": t1 - self._t0,
            "cpu_time": cpu1 - self._cpu0,
            "cpu_usage": cpu_usage,
            "rusage_start": self._r0,
            "rusage_end": r1,
            "io_start": self._io0,
            "io_end": io1,
            "tracemalloc": tm_stats,
        }
        return data


def _render_perf_report(data: Dict[str, Any], phases: Dict[str, float], counts: Dict[str, int]) -> str:
    if not data:
        return ""
    wall = data.get("wall_time", 0.0) or 0.0
    cpu = data.get("cpu_time", 0.0) or 0.0
    cpu_ratio = (cpu / wall) if wall > 0 else 0.0
    cpu_pct = cpu_ratio * 100.0

    r0 = data.get("rusage_start")
    r1 = data.get("rusage_end")
    maxrss = None
    if r1:
        maxrss = int(r1.ru_maxrss) * 1024  # Linux reports KiB

    io0 = data.get("io_start", {})
    io1 = data.get("io_end", {})
    io_delta = {k: (io1.get(k, 0) - io0.get(k, 0)) for k in set(io0) | set(io1)}

    lines: List[str] = []
    lines.append("PERF SUMMARY")
    lines.append(f"wall={wall:.3f}s cpu={cpu:.3f}s cpu/wall={cpu_pct:.1f}%")
    lines.append(f"maxrss={_format_bytes(maxrss)} cores={os.cpu_count() or 0} loadavg={getattr(os, 'getloadavg', lambda: ('n/a',) * 3)()}")
    if io_delta:
        rbytes = io_delta.get("read_bytes", 0)
        wbytes = io_delta.get("write_bytes", 0)
        lines.append(f"io read={_format_bytes(rbytes)} write={_format_bytes(wbytes)} rchar={_format_bytes(io_delta.get('rchar', 0))} wchar={_format_bytes(io_delta.get('wchar', 0))}")

    cpu_usage = data.get("cpu_usage", {})
    if cpu_usage:
        total = cpu_usage.get("cpu")
        if total is not None:
            lines.append(f"cpu_total_util={total*100.0:.1f}%")
        per_core = [f"{k}:{v*100.0:.0f}%" for k, v in sorted(cpu_usage.items()) if k != "cpu"]
        if per_core:
            lines.append("cpu_per_core=" + ",".join(per_core))

    if phases:
        lines.append("PHASES")
        for name, dt in sorted(phases.items(), key=lambda x: x[1], reverse=True):
            pct = (dt / wall * 100.0) if wall > 0 else 0.0
            lines.append(f"{name}={dt:.3f}s ({pct:.1f}%)")

    if counts:
        lines.append("COUNTS")
        for k, v in counts.items():
            lines.append(f"{k}={v}")
        if "hadith_lines" in counts and wall > 0:
            lines.append(f"throughput_lines_per_s={counts['hadith_lines']/wall:.1f}")

    tm = data.get("tracemalloc")
    if tm:
        lines.append(f"tracemalloc_current={_format_bytes(tm.get('current'))} peak={_format_bytes(tm.get('peak'))}")
        top = tm.get("top") or []
        if top:
            lines.append("tracemalloc_top")
            for loc, size, count in top:
                lines.append(f"{loc} size={_format_bytes(size)} count={count}")

    return "\n".join(lines)

# =========================
# HADITH NUMBER PARSING (input txt)
# =========================

NUM_RE = re.compile(r"^\s*(?:[^\d]{0,80}\s*)?(\d{1,5})\b", re.UNICODE)
KUTUB_LIST_MARKER = "\tKUTUBS="
KUTUB_DB_MAP = {
    "Bukhari": "Bukhari",
    "Muslim": "Muslim",
    "AbuDaud": "AbuDaud",
    "AbuDawud": "AbuDaud",
    "Tirmizi": "Tirmizi",
    "Tirmidhi": "Tirmizi",
    "Nesai": "Nesai",
    "Nasa_i": "Nesai",
    "IbnMajah": "IbnMajah",
}


def split_kutub_list(raw_line: str) -> Tuple[str, Optional[List[str]]]:
    if KUTUB_LIST_MARKER not in raw_line:
        return raw_line, None
    base, raw = raw_line.rsplit(KUTUB_LIST_MARKER, 1)
    raw = raw.strip()
    if not raw:
        return base, None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return base, [str(x) for x in data]
    except Exception:
        return base, None
    return base, None


def parse_hadith_line(raw_line: str) -> Tuple[Optional[int], str, Optional[List[str]]]:
    line, kutub_list = split_kutub_list(raw_line)
    m = NUM_RE.match(line)  # erwartet: m != None bei regulären Zeilen (Hadith-Nummer am Zeilenanfang)
    if not m:
        return None, line, kutub_list
    num = int(m.group(1))  # erwartet: num ist die Hadith-Nummer aus der TXT (in_sittah)
    rest = line[m.end() :].strip()  # erwartet: rest ist der Hadith-Text ohne führende Nummer
    return num, rest, kutub_list


def filter_db_paths_for_kutub(
    db_paths: List[str], kutub_list: Optional[List[str]]
) -> List[str]:
    if not kutub_list:
        return db_paths
    allowed = set()
    for item in kutub_list:
        key = str(item)
        allowed.add(KUTUB_DB_MAP.get(key, key))
    return [dbp for dbp in db_paths if Path(dbp).stem in allowed]


# =========================
# TOKENIZE / NGRAMS
# =========================

WS_RE = re.compile(r"\s+", re.UNICODE)
LIST_REPR_HINT_RE = re.compile(r"(\"[^\"]+\"\s*,|'[^']+'\s*,)")
SQL_ANCHOR_MAX_WORDS = 6
ALBANI_MARKER_RE = re.compile(r"(?:قال\s+الألباني|قال\s+الالباني)")

ARABIC_FUNCTION_WORDS = {
    "هذا",
    "هذه",
    "ذلك",
    "تلك",
    "الذي",
    "التي",
    "الذين",
    "من",
    "ما",
    "لا",
    "لم",
    "لن",
    "قد",
    "ثم",
    "إذ",
    "إذا",
    "كما",
    "لان",
    "لذلك",
    "في",
    "على",
    "عن",
    "إلى",
    "مع",
    "كان",
    "كانت",
    "يكون",
    "قال",
    "يقول",
}

HONORIFICS_RX = re.compile(
    r"(?xiu)(?:"
    r"صل(?:ى|ي)\\s*الله\\s*عليه\\s*وسلم|"
    r"صلى\\s*الله\\s*عليه\\s*وسلم|"
    r"عليه\\s*الصلاة\\s*والسلام|"
    r"عليه\\s*السلام|"
    r"عليهم\\s*السلام|"
    r"رضي\\s*الله\\s*عنه|"
    r"رضي\\s*الله\\s*عنها|"
    r"رضي\\s*الله\\s*عنهم|"
    r"رضوان\\s*الله\\s*عليه|"
    r"رحمه\\s*الله|"
    r"رحمهم\\s*الله|"
    r"رحمها\\s*الله"
    r")"
)

MATN_META_RX = HONORIFICS_RX

# FIX: normalize() liefert hier offenbar nicht immer str (z.B. None/Objekt) -> immer zu str casten


def tokenize_words_from_text(s) -> List[str]:
    s = "" if s is None else str(s)  # erwartet: s ist str (nicht None/Objekt)
    m = ALBANI_MARKER_RE.search(s)
    if m:
        s = s[: m.start()].rstrip()
    s_stripped = s.strip()
    if (
        s_stripped.startswith("[")
        and s_stripped.endswith("]")
        and LIST_REPR_HINT_RE.search(s_stripped)
    ):
        try:
            parsed = ast.literal_eval(s_stripped)
            if isinstance(parsed, (list, tuple)):
                s = " ".join(str(x) for x in parsed)
            else:
                s = str(parsed)
        except (ValueError, SyntaxError):
            pass
    s = normalize(s)  # erwartet: normalize(s) liefert einen str und entfernt nur Vergleichsrauschen (nicht Input-Index relevant)
    if isinstance(s, (list, tuple)):
        s = " ".join(str(x) for x in s)
    s = "" if s is None else str(s)  # erwartet: nach normalize ebenfalls str (nicht None)
    s = WS_RE.sub(" ", s).strip()  # erwartet: WS_RE.sub bekommt str; Ergebnis nicht leer bei sinnvollem Text
    if not s:
        return []
    return s.split(" ")  # erwartet: tokens-Liste mit >0 Elementen bei Hadith-Text


def make_ngrams(words: List[str], n: int) -> List[str]:
    if n <= 0 or len(words) < n:
        return []
    return [" ".join(words[i : i + n]) for i in range(0, len(words) - n + 1)]  # erwartet: len(result) == len(words)-n+1


def meta_penalty(text: str, cap: int = 10) -> float:
    if not text:
        return 0.0
    count = 0
    for _ in MATN_META_RX.finditer(text):
        count += 1
        if count >= cap:
            break
    if count <= 0:
        return 0.0
    return 1.0 - math.exp(-count / 4.0)


def token_weight(token: str, pos: Optional[str] = None) -> float:
    if not token:
        return 0.0
    if HONORIFICS_RX.search(token):
        return 0.05
    if token in ARABIC_FUNCTION_WORDS:
        return 0.10
    w = 0.8 if len(token) >= 5 else 0.5
    if pos in {"NOUN", "PROPN"}:
        w = min(1.0, w + 0.2)
    elif pos in {"ADP", "PRON", "DET", "PART"}:
        w = max(0.05, w - 0.2)
    return w


def anchor_strength(anchor_text: str, pos_map: Optional[Dict[str, str]] = None) -> float:
    tokens = [t for t in anchor_text.split(" ") if t]
    if not tokens:
        return 0.0
    weights = []
    for tok in tokens:
        pos = pos_map.get(tok) if pos_map else None
        weights.append(token_weight(tok, pos))
    avg_weight = sum(weights) / float(len(weights))
    content_ratio = sum(1 for w in weights if w >= 0.6) / float(len(weights))
    penalty = meta_penalty(anchor_text)
    strength = (avg_weight * 0.55) + (content_ratio * 0.35) - (penalty * 0.40)
    return clamp(strength, 0.0, 1.0)


# =========================
# NGRAM PARAMS (per length)
# =========================


def get_text_category(word_count: int) -> str:
    if word_count < 8:
        return "micro"
    elif word_count < 15:
        return "very_short"
    elif word_count < 25:
        return "short"
    elif word_count < 40:
        return "short_medium"
    elif word_count < 60:
        return "medium"
    elif word_count < 90:
        return "medium_long"
    elif word_count < 130:
        return "long"
    elif word_count < 200:
        return "very_long"
    else:
        return "ultra_long"


@dataclass(frozen=True)
class NgramCategoryParams:
    x: float
    min_n: int
    max_n: int
    threshold: float
    order_threshold: float


@dataclass(frozen=True)
class Params:
    micro: NgramCategoryParams
    very_short: NgramCategoryParams
    short: NgramCategoryParams
    short_medium: NgramCategoryParams
    medium: NgramCategoryParams
    medium_long: NgramCategoryParams
    long: NgramCategoryParams
    very_long: NgramCategoryParams
    ultra_long: NgramCategoryParams


def clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


def clamp_int(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v


def calculate_n_value(word_count: int, cat_params: NgramCategoryParams) -> int:
    n = int(word_count * cat_params.x)  # erwartet: n skaliert mit Textlänge
    n = clamp_int(n, cat_params.min_n, cat_params.max_n)  # erwartet: min_n <= n <= max_n
    return n


def get_cat_params(p: Params, category: str) -> NgramCategoryParams:
    return getattr(p, category)


# =========================
# MATCHING / SCORING
# =========================


def choose_anchors(words: List[str], n: int) -> List[str]:
    if n <= 0 or len(words) < n:
        return []
    anchors: List[str] = []
    anchors.append(" ".join(words[0:n]))  # erwartet: anchor_1 ist der Satzanfang (n Wörter)
    mid = max(0, (len(words) // 2) - (n // 2))
    if mid + n <= len(words):
        anchors.append(" ".join(words[mid : mid + n]))  # erwartet: anchor_2 ist Mitte (n Wörter)
    anchors.append(" ".join(words[-n:]))  # erwartet: anchor_3 ist Satzende (n Wörter)

    stride = max(1, ANCHOR_STRIDE)
    for i in range(0, len(words) - n + 1, stride):
        anchors.append(" ".join(words[i : i + n]))

    uniq = []
    seen = set()
    for a in anchors:
        a = a.strip()
        if a and a not in seen:
            seen.add(a)
            uniq.append(a)  # erwartet: uniq enthält 1-3 sinnvolle Anker, nicht leer
    return uniq


def order_precheck(matn_norm: str, anchors: List[str]) -> bool:
    if not anchors:
        return True
    pos = -1
    for a in anchors:
        p = matn_norm.find(a)
        if p < 0:
            return False
        if p <= pos:
            return False
        pos = p
    return True


def select_anchors(
    words: List[str],
    n: int,
    pos_map: Optional[Dict[str, str]] = None,
) -> Tuple[List[Tuple[str, float]], List[str], List[str]]:
    anchors = choose_anchors(words, n)
    scored = []
    for a in anchors:
        strength = anchor_strength(a, pos_map)
        scored.append((a, strength))
    scored.sort(key=lambda x: x[1], reverse=True)

    strong = [a for a, _ in scored[:ANCHOR_STRONG_K]]
    top = [a for a, _ in scored[:ANCHOR_TOP_M]]
    return scored, strong, top


def ordered_run_ratio(h_ngrams: List[str], t_ngrams: List[str]) -> float:
    if not h_ngrams or not t_ngrams:
        return 0.0

    pos_map: Dict[str, List[int]] = {}
    for idx, g in enumerate(t_ngrams):
        pos_map.setdefault(g, []).append(idx)  # erwartet: pos_map hat Einträge für vorkommende n-grams

    best_run = 0
    run = 0
    prev_pos = -1

    for g in h_ngrams:
        positions = pos_map.get(g)
        if not positions:
            run = 0
            prev_pos = -1
            continue

        chosen = None
        if prev_pos >= 0:
            target = prev_pos + 1
            for p in positions:
                if p == target:
                    chosen = p
                    break
            if chosen is not None:
                run += 1  # erwartet: bei echten Matches wächst run zu einer längeren Sequenz
                prev_pos = chosen
                if run > best_run:
                    best_run = run
                continue

            for p in positions:
                if p > prev_pos:
                    chosen = p
                    break

        if chosen is None:
            chosen = positions[0]
            run = 1
            prev_pos = chosen
        else:
            run = 1
            prev_pos = chosen

        if run > best_run:
            best_run = run

    return best_run / float(len(h_ngrams))  # erwartet: 0.0..1.0; bei starken Treffern nahe 1.0


def score_candidate(
    h_words: List[str], t_words: List[str], n: int
) -> Tuple[float, float, float]:
    h_ngrams = make_ngrams(h_words, n)
    t_ngrams = make_ngrams(t_words, n)

    if not h_ngrams or not t_ngrams:
        return (0.0, 0.0, 0.0)

    t_set = set(t_ngrams)
    hit = 0
    for g in h_ngrams:
        if g in t_set:
            hit += 1  # erwartet: hit steigt deutlich bei echten Matches

    hit_rate = hit / float(len(h_ngrams))  # erwartet: bei starken Matches >= threshold
    order_ratio = ordered_run_ratio(h_ngrams, t_ngrams)  # erwartet: bei starken Matches >= order_threshold
    final = (0.7 * hit_rate) + (0.3 * order_ratio)  # erwartet: final hoch bei starken Matches
    return (final, hit_rate, order_ratio)


def score_candidate_multi_n(
    h_words: List[str],
    t_words: List[str],
    n0: int,
    cp: NgramCategoryParams,
) -> Tuple[float, float, float, int]:
    n_set = {n0}
    if len(h_words) <= 20:
        n_set.add(n0 - 1)
    else:
        n_set.update({n0 - 1, n0 + 1})

    best = (0.0, 0.0, 0.0, n0)
    for n in sorted(n_set):
        if n <= 0:
            continue
        n = clamp_int(n, 1, max(len(h_words), 1))
        final, hit_rate, order_ratio = score_candidate(h_words, t_words, n)
        if final > best[0]:
            best = (final, hit_rate, order_ratio, n)
    return best


# =========================
# SQLITE HELPERS (ONLY arabic_matn, id via hadith_number)
# =========================

def normalize_to_str(s: Any) -> str:
    s = normalize(s)
    if isinstance(s, (list, tuple)):
        s = " ".join(str(x) for x in s)
    return "" if s is None else str(s)


def coerce_hadith_number(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    try:
        return float(s)
    except (ValueError, TypeError):
        return s


def sql_like_escape(s: str) -> str:
    s = s.replace("\\", "\\\\")
    s = s.replace("%", "\\%")
    s = s.replace("_", "\\_")
    return s


def shorten_anchor_for_sql(s: str, max_words: int = SQL_ANCHOR_MAX_WORDS) -> str:
    s = WS_RE.sub(" ", s).strip()
    if not s:
        return s
    parts = s.split(" ")
    if len(parts) <= max_words:
        return s
    return " ".join(parts[:max_words])


def prep_anchor_for_search(anchor: str) -> str:
    a = normalize_to_str(anchor)
    a = shorten_anchor_for_sql(a)
    return a


def has_column(conn: sqlite3.Connection, table: str, col: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")  # erwartet: table existiert, liefert Spaltenliste
    col_lc = col.lower()
    for row in cur.fetchall():
        if str(row[1]).lower() == col_lc:
            return True  # erwartet: arabic_matn / hadith_number existieren wirklich
    return False


def filter_compatible_db_paths(db_paths: List[str]) -> List[str]:
    compatible = []
    for dbp in db_paths:
        try:
            conn = sqlite3.connect(dbp)
            ok = has_column(conn, DB_TABLE, DB_COL) and has_column(conn, DB_TABLE, DB_ID_COL)
            conn.close()
        except Exception:
            ok = False
        if ok:
            compatible.append(dbp)
    return compatible


def fetch_candidates(
    conn: sqlite3.Connection,
    anchors: List[str],
    limit: int,
) -> List[Tuple[float, str]]:
    cur = conn.cursor()

    params = []
    where_parts = []
    for a in anchors:
        a = (a or "").strip()
        if not a:
            continue
        a = normalize_to_str(a)  # erwartet: normalisierte Anker sind noch „suchbar“ (nicht leer)
        a = shorten_anchor_for_sql(a)
        a = sql_like_escape(a)
        where_parts.append(f"normtxt({DB_COL}) LIKE ? ESCAPE '\\'")  # erwartet: DB_COL == arabic_matn existiert
        params.append(f"%{a}%")

    if not where_parts:
        q = f"SELECT {DB_ID_COL}, {DB_COL} FROM {DB_TABLE} LIMIT ?"  # erwartet: DB_TABLE existiert, Query läuft
        cur.execute(q, (limit,))
        return [(coerce_hadith_number(r[0]), r[1]) for r in cur.fetchall() if r[0] is not None]  # erwartet: hadith_number nicht None

    where = " OR ".join(where_parts)
    q = f"SELECT {DB_ID_COL}, {DB_COL} FROM {DB_TABLE} WHERE {where} LIMIT ?"  # erwartet: Query liefert Kandidaten bei passenden Ankern
    params.append(limit)
    cur.execute(q, params)  # erwartet: params korrekt; cur.fetchall() nicht immer leer
    out = []
    for r in cur.fetchall():
        if r[0] is None:
            continue
        out.append((coerce_hadith_number(r[0]), r[1]))  # erwartet: out enthält (hadith_number, arabic_matn)
    if not out:
        # Fallback: ohne WHERE, falls Normalisierung/Diakritika SQL-LIKE-Matches verhindert
        q = f"SELECT {DB_ID_COL}, {DB_COL} FROM {DB_TABLE} LIMIT ?"
        cur.execute(q, (limit,))
        out = [(coerce_hadith_number(r[0]), r[1]) for r in cur.fetchall() if r[0] is not None]
    return out


# =========================
# WORKER GLOBALS
# =========================

_WORKER_DB_PATHS: List[str] = []
_WORKER_CONNS: Dict[str, sqlite3.Connection] = {}
_WORKER_DB_OK: Dict[str, bool] = {}
_WORKER_CACHE: Optional[match_cache.ParquetReader] = None
_WORKER_STANZA: Optional[match_stanza.StanzaCache] = None
_WORKER_SEM: Optional[match_semantic.SemanticReranker] = None
_COVERAGE_TRACKER = match_logging.CoverageTracker()
_EVAL_COUNTER = 0
_PARQUET_MAP: Dict[str, Path] = {}


def _worker_init(db_paths: List[str], parquet_map: Dict[str, Path]):
    global _WORKER_DB_PATHS, _WORKER_CONNS, _WORKER_DB_OK, _WORKER_CACHE, _WORKER_STANZA, _WORKER_SEM
    _WORKER_DB_PATHS = db_paths  # erwartet: enthält Pfade zu allen *.db Dateien
    _WORKER_CONNS = {}
    _WORKER_DB_OK = {dbp: True for dbp in db_paths}
    _WORKER_CACHE = match_cache.ParquetReader(parquet_map, use_duckdb=USE_DUCKDB)
    if ENABLE_STANZA:
        try:
            _WORKER_STANZA = match_stanza.StanzaCache(
                match_stanza.StanzaConfig(cache_path=CACHE_DIR / "stanza_cache.db"),
                normalize_func=normalize_to_str,
            )
        except Exception:
            _WORKER_STANZA = None
    if ENABLE_SEM_RERANK:
        try:
            _WORKER_SEM = match_semantic.SemanticReranker(
                match_semantic.SemanticConfig(cache_path=CACHE_DIR / "semantic_cache.db")
            )
        except Exception:
            _WORKER_SEM = None


def _get_conn(db_path: str) -> sqlite3.Connection:
    conn = _WORKER_CONNS.get(db_path)
    if conn is None:
        conn = sqlite3.connect(db_path, check_same_thread=False)  # erwartet: Datei existiert und ist gültige SQLite DB
        conn.row_factory = sqlite3.Row
        conn.create_function("normtxt", 1, normalize_to_str)
        _WORKER_CONNS[db_path] = conn
    return conn


def _db_is_compatible(db_path: str) -> bool:
    ok = _WORKER_DB_OK.get(db_path)
    if ok is not None:
        return ok
    conn = _get_conn(db_path)
    ok = has_column(conn, DB_TABLE, DB_COL) and has_column(conn, DB_TABLE, DB_ID_COL)  # erwartet: True für kompatible DBs
    _WORKER_DB_OK[db_path] = ok
    return ok


def fetch_candidates_parquet(
    db_path: str,
    *,
    strong_anchors: List[str],
    top_anchors: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    if _WORKER_CACHE is None:
        return []

    def _dedupe(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        out = []
        for r in rows:
            key = str(r.get("hadith_number_raw") or r.get("hadith_number"))
            if key in seen:
                continue
            seen.add(key)
            out.append(r)
        return out

    strong_norm = [prep_anchor_for_search(a) for a in strong_anchors if a]
    top_norm = [prep_anchor_for_search(a) for a in top_anchors if a]

    and_rows = []
    if strong_norm:
        table = _WORKER_CACHE.fetch(
            db_path, strong_norm, require_all=True, limit=limit
        )
        and_rows = table.to_pylist()

    filtered_and = []
    for r in and_rows:
        matn_norm = r.get("matn_norm") or ""
        if order_precheck(matn_norm, strong_norm):
            r["phase"] = "and"
            r["order_ok"] = True
            filtered_and.append(r)

    or_rows = []
    if len(filtered_and) < MIN_CANDS:
        table = _WORKER_CACHE.fetch(
            db_path, top_norm, require_all=False, limit=limit
        )
        or_rows = table.to_pylist()

    filtered_or = []
    for r in or_rows:
        matn_norm = r.get("matn_norm") or ""
        order_ok = order_precheck(matn_norm, strong_norm)
        r["phase"] = "or"
        r["order_ok"] = order_ok
        filtered_or.append(r)

    merged = _dedupe(filtered_and + filtered_or)

    fallback_rows = []
    if len(merged) < MIN_CANDS:
        table = _WORKER_CACHE.fetch(db_path, [], require_all=False, limit=limit)
        fallback_rows = table.to_pylist()
        for r in fallback_rows:
            r["phase"] = "fallback"
            r["order_ok"] = True
        merged = _dedupe(merged + fallback_rows)

    return merged


# =========================
# MATCH ONE HADITH AGAINST ALL DBS (MULTIPLE MATCHES)
# =========================


def match_one_hadith_all(raw_line: str, params_dict: dict) -> Dict[str, Any]:
    hadith_id, hadith_text_raw, kutub_list = parse_hadith_line(raw_line)  # erwartet: hadith_id != None bei gültiger Zeile
    if hadith_id is None:
        return {"hadith_id": None, "raw_line": raw_line, "matches": []}

    meta_p = meta_penalty(hadith_text_raw)

    h_words = tokenize_words_from_text(hadith_text_raw)  # erwartet: h_words nicht leer (sonst keine Matches möglich)
    if not h_words:
        return {"hadith_id": hadith_id, "raw_line": raw_line, "matches": []}

    p = Params(
        micro=NgramCategoryParams(**params_dict["micro"]),
        very_short=NgramCategoryParams(**params_dict["very_short"]),
        short=NgramCategoryParams(**params_dict["short"]),
        short_medium=NgramCategoryParams(**params_dict["short_medium"]),
        medium=NgramCategoryParams(**params_dict["medium"]),
        medium_long=NgramCategoryParams(**params_dict["medium_long"]),
        long=NgramCategoryParams(**params_dict["long"]),
        very_long=NgramCategoryParams(**params_dict["very_long"]),
        ultra_long=NgramCategoryParams(**params_dict["ultra_long"]),
    )

    cat = get_text_category(len(h_words))  # erwartet: Kategorie passend zur Wortanzahl
    cp = get_cat_params(p, cat)
    n = calculate_n_value(len(h_words), cp)  # erwartet: n sinnvoll (>= min_n) und nicht zu groß
    if os.environ.get("DEBUG_HADITH_BUCKETS") == "1":
        print(
            f"[bucket] id={hadith_id} words={len(h_words)} cat={cat} n={n} "
            f"threshold={cp.threshold} order_threshold={cp.order_threshold}",
            file=sys.stderr,
        )

    pos_map: Optional[Dict[str, str]] = None
    if ENABLE_STANZA and _WORKER_STANZA is not None:
        try:
            pos_map = _WORKER_STANZA.get_pos_map(hadith_id, hadith_text_raw)
        except Exception:
            pos_map = None

    anchor_infos, strong_anchors, top_anchors = select_anchors(
        h_words, max(1, n), pos_map
    )
    if DEBUG:
        match_logging.log_anchors(hadith_id, anchor_infos[: max(ANCHOR_TOP_M, ANCHOR_STRONG_K)])

    all_matches: List[Dict[str, Any]] = []

    db_paths = filter_db_paths_for_kutub(_WORKER_DB_PATHS, kutub_list)
    for dbp in db_paths:
        if not _db_is_compatible(dbp):  # erwartet: nur inkompatible DBs werden hier rausgefiltert
            continue
        candidates = fetch_candidates_parquet(
            dbp,
            strong_anchors=strong_anchors,
            top_anchors=top_anchors,
            limit=SQL_CANDIDATE_LIMIT,
        )

        if DEBUG:
            phase_counts = {"and": 0, "or": 0, "fallback": 0}
            for c in candidates:
                phase_counts[c.get("phase", "or")] = phase_counts.get(c.get("phase", "or"), 0) + 1
            match_logging.log_candidate_flow(
                hadith_id=hadith_id,
                and_count=phase_counts.get("and", 0),
                or_count=phase_counts.get("or", 0),
                fallback_count=phase_counts.get("fallback", 0),
                final_count=len(candidates),
            )

        for cand in candidates:
            t = cand.get("arabic_matn")
            if t is None:
                continue
            t_words = tokenize_words_from_text(str(t))  # erwartet: t_words nicht leer bei DB-Text
            final, hit_rate, order_ratio, best_n = score_candidate_multi_n(
                h_words, t_words, n, cp
            )  # erwartet: bei echten Matches Werte nahe 1.0

            if hit_rate < cp.threshold:  # erwartet: bei best_avg_score==0 hier oft TRUE (zu strikt / keine echten Kandidaten)
                continue
            if order_ratio < cp.order_threshold:  # erwartet: bei best_avg_score==0 hier oft TRUE (Reihenfolge/Sequenz zu schwach)
                continue

            final_adj = final * max(0.0, 1.0 - (meta_p * META_STRENGTH))
            if not cand.get("order_ok", True) and cand.get("phase") == "or":
                final_adj *= ORDER_PRECHECK_PENALTY

            all_matches.append(
                {
                    "db_path": dbp,
                    "hadith_number": coerce_hadith_number(
                        cand.get("hadith_number_raw") or cand.get("hadith_number")
                    ),  # erwartet: hadith_number stammt aus der Quell-DB (nicht rowid)
                    "score": float(final_adj),
                    "hit_rate": float(hit_rate),
                    "order_ratio": float(order_ratio),
                    "_text": str(t),
                }
            )

    all_matches.sort(key=lambda x: x["score"], reverse=True)

    if ENABLE_SEM_RERANK and _WORKER_SEM is not None and all_matches:
        topk = all_matches[:TOPK_RERANK]
        for m in topk:
            score = m["score"]
            if score < 0.60 or score >= 0.95:
                continue
            try:
                sem_score = _WORKER_SEM.similarity(
                    hadith_id=hadith_id,
                    db_path=m["db_path"],
                    hadith_number=str(m["hadith_number"]),
                    text_a=hadith_text_raw,
                    text_b=m.get("_text", ""),
                )
                m["score"] = float(score * (0.85 + (0.15 * sem_score)))
            except Exception:
                continue

        all_matches.sort(key=lambda x: x["score"], reverse=True)

    for m in all_matches:
        if "_text" in m:
            m.pop("_text", None)
    best_score = all_matches[0]["score"] if all_matches else 0.0  # erwartet: >0 nur wenn mindestens ein Match die Schwellen schafft

    return {
        "hadith_id": hadith_id,
        "raw_line": raw_line,
        "best_score": float(best_score),
        "matches": all_matches,
    }


# =========================
# OPTIMIZATION / PARAM SEARCH
# =========================


def default_params() -> Params:
    return Params(
        micro=NgramCategoryParams(
            x=0.35, min_n=2, max_n=3, threshold=0.60, order_threshold=0.55
        ),
        very_short=NgramCategoryParams(
            x=0.30, min_n=2, max_n=4, threshold=0.68, order_threshold=0.60
        ),
        short=NgramCategoryParams(
            x=0.26, min_n=3, max_n=7, threshold=0.76, order_threshold=0.70
        ),
        short_medium=NgramCategoryParams(
            x=0.24, min_n=4, max_n=9, threshold=0.82, order_threshold=0.76
        ),
        medium=NgramCategoryParams(
            x=0.22, min_n=5, max_n=14, threshold=0.85, order_threshold=0.80
        ),
        medium_long=NgramCategoryParams(
            x=0.20, min_n=6, max_n=16, threshold=0.86, order_threshold=0.80
        ),
        long=NgramCategoryParams(
            x=0.17, min_n=7, max_n=22, threshold=0.88, order_threshold=0.80
        ),
        very_long=NgramCategoryParams(
            x=0.14, min_n=8, max_n=20, threshold=0.90, order_threshold=0.78
        ),
        ultra_long=NgramCategoryParams(
            x=0.12, min_n=8, max_n=18, threshold=0.90, order_threshold=0.75
        ),
    )


def params_to_dict(p: Params) -> dict:
    return {
        "micro": asdict(p.micro),
        "very_short": asdict(p.very_short),
        "short": asdict(p.short),
        "short_medium": asdict(p.short_medium),
        "medium": asdict(p.medium),
        "medium_long": asdict(p.medium_long),
        "long": asdict(p.long),
        "very_long": asdict(p.very_long),
        "ultra_long": asdict(p.ultra_long),
    }


def tweak_params(p: Params, dx: float, dth: float, dor: float) -> Params:
    def upd(cp: NgramCategoryParams) -> NgramCategoryParams:
        return NgramCategoryParams(
            x=clamp(cp.x + dx, 0.05, 0.95),
            min_n=clamp_int(cp.min_n, 1, 60),
            max_n=clamp_int(cp.max_n, 1, 60),
            threshold=clamp(cp.threshold + dth, 0.0, 1.0),
            order_threshold=clamp(cp.order_threshold + dor, 0.0, 1.0),
        )

    return Params(
        micro=upd(p.micro),
        very_short=upd(p.very_short),
        short=upd(p.short),
        short_medium=upd(p.short_medium),
        medium=upd(p.medium),
        medium_long=upd(p.medium_long),
        long=upd(p.long),
        very_long=upd(p.very_long),
        ultra_long=upd(p.ultra_long),
    )


def evaluate_params(
    hadith_lines: List[str], db_paths: List[str], p: Params
) -> Tuple[float, float, float]:
    global _EVAL_COUNTER
    pd = params_to_dict(p)
    scores: List[float] = []

    with ProcessPoolExecutor(
        max_workers=MAX_WORKERS,
        initializer=_worker_init,
        initargs=(db_paths, _PARQUET_MAP),
    ) as ex:
        for res in ex.map(match_one_hadith_all, hadith_lines, [pd] * len(hadith_lines)):  # erwartet: res["best_score"] > 0 für einige Zeilen, sonst bleiben scores faktisch 0
            scores.append(float(res.get("best_score") or 0.0))  # erwartet: bei funktionierendem Matching sind nicht alle Einträge 0.0

    if not scores:
        return 0.0, 0.0, 0.0

    hits = [s for s in scores if s >= MIN_ACCEPT_SCORE]
    coverage = len(hits) / float(len(scores))
    avg_hit = sum(hits) / float(len(hits)) if hits else 0.0
    objective = (0.65 * coverage) + (0.35 * avg_hit)

    _EVAL_COUNTER += 1
    label = f"iter_{_EVAL_COUNTER}"
    series_label = os.environ.get("COVERAGE_LABEL", "search")
    _COVERAGE_TRACKER.add(series_label, coverage)
    match_logging.log_objective(
        label, coverage=coverage, avg_hit=avg_hit, objective=objective
    )

    return objective, coverage, avg_hit  # erwartet: >0 wenn wenigstens manche Zeilen Matches finden


def recursive_search(
    hadith_lines: List[str],
    db_paths: List[str],
    p0: Params,
    depth: int,
    dx_step: float,
    dth_step: float,
    dor_step: float,
) -> Tuple[Params, float, float, float]:
    best_p = p0
    best_objective, best_coverage, best_avg_hit = evaluate_params(
        hadith_lines, db_paths, best_p
    )  # erwartet: >0 sobald Matching grundsätzlich greift

    if depth <= 0:
        return best_p, best_objective, best_coverage, best_avg_hit

    neighbors = []
    for sgn_x in (-1, 0, 1):
        for sgn_t in (-1, 0, 1):
            for sgn_o in (-1, 0, 1):
                if sgn_x == 0 and sgn_t == 0 and sgn_o == 0:
                    continue
                neighbors.append((sgn_x * dx_step, sgn_t * dth_step, sgn_o * dor_step))

    improved = False
    for dx, dth, dor in neighbors:
        p1 = tweak_params(best_p, dx, dth, dor)
        sc1_obj, sc1_cov, sc1_avg = evaluate_params(
            hadith_lines, db_paths, p1
        )  # erwartet: sc1 kann besser/schlechter werden je nach Schwellen
        if sc1_obj > best_objective:
            best_objective = sc1_obj
            best_coverage = sc1_cov
            best_avg_hit = sc1_avg
            best_p = p1
            improved = True

    if improved:
        return recursive_search(
            hadith_lines, db_paths, best_p, depth - 1, dx_step, dth_step, dor_step
        )

    return recursive_search(
        hadith_lines,
        db_paths,
        best_p,
        depth - 1,
        dx_step * 0.5,
        dth_step * 0.5,
        dor_step * 0.5,
    )


# =========================
# OUTPUT DB CREATION (per DB column + in_sittah + per DB id column)
# =========================

IDENT_RE = re.compile(r"[^0-9a-zA-Z_]+", re.UNICODE)


def safe_ident(name: str) -> str:
    name = (name or "").strip()
    name = name.replace(".db", "")
    name = IDENT_RE.sub("_", name)
    if not name:
        name = "x"
    if name[0].isdigit():
        name = "x_" + name
    return name


def qident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def create_output_db(
    db_paths: List[str],
) -> Tuple[sqlite3.Connection, Dict[str, str], Dict[str, str]]:
    OUT_MATCHES_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUT_MATCHES_DB.exists():
        OUT_MATCHES_DB.unlink()

    conn = sqlite3.connect(str(OUT_MATCHES_DB))
    cur = conn.cursor()

    dbname_to_col: Dict[str, str] = {}
    dbname_to_idcol: Dict[str, str] = {}

    for dbp in db_paths:
        base = Path(dbp).name
        col = safe_ident(base)
        dbname_to_col[dbp] = col
        dbname_to_idcol[dbp] = col + "_id"  # erwartet: diese Spalte enthält JSON-Liste der hadith_number Treffer aus der Quell-DB

    cols_sql = []
    cols_sql.append(f"{qident('in_sittah')} INTEGER PRIMARY KEY")  # erwartet: in_sittah == Hadith-Nummer aus TXT
    cols_sql.append(f"{qident('raw_line')} TEXT")  # erwartet: komplette Originalzeile aus in_sittah.txt

    for dbp in db_paths:
        cols_sql.append(f"{qident(dbname_to_col[dbp])} TEXT")  # erwartet: JSON-Liste der Match-Objekte für diese DB
        cols_sql.append(f"{qident(dbname_to_idcol[dbp])} TEXT")  # erwartet: JSON-Liste der hadith_number IDs (aus Quell-DB) für diese DB

    cur.execute(f"CREATE TABLE results ({', '.join(cols_sql)})")
    cur.execute(f"CREATE INDEX idx_results_in_sittah ON results({qident('in_sittah')})")
    conn.commit()
    return conn, dbname_to_col, dbname_to_idcol


def write_results_to_db(
    conn: sqlite3.Connection,
    db_paths: List[str],
    dbname_to_col: Dict[str, str],
    dbname_to_idcol: Dict[str, str],
    results: List[Dict[str, Any]],
):
    cur = conn.cursor()

    insert_cols = ["in_sittah", "raw_line"]
    for dbp in db_paths:
        insert_cols.append(dbname_to_col[dbp])
        insert_cols.append(dbname_to_idcol[dbp])

    placeholders = ",".join(["?"] * len(insert_cols))
    insert_sql = f"INSERT OR REPLACE INTO results ({', '.join(qident(c) for c in insert_cols)}) VALUES ({placeholders})"

    for res in results:
        hid = res.get("hadith_id")  # erwartet: int Hadith-Nummer aus TXT
        if hid is None:
            continue

        raw_line = res.get("raw_line") or ""  # erwartet: Originalzeile (inkl. Nummer) zur Nachverfolgung
        _, raw_line, _ = parse_hadith_line(raw_line)
        matches = res.get("matches", [])  # erwartet: Liste leer wenn kein Match die thresholds schafft

        per_db_matches: Dict[str, List[Dict[str, Any]]] = {}
        per_db_ids: Dict[str, List[Any]] = {}

        for m in matches:
            dbp = m["db_path"]
            per_db_matches.setdefault(dbp, []).append(
                {
                    "hadith_number": coerce_hadith_number(m["hadith_number"]),  # erwartet: Quell-ID aus DB (hadith_number), nicht rowid
                    "score": float(m["score"]),
                    "hit_rate": float(m["hit_rate"]),
                    "order_ratio": float(m["order_ratio"]),
                }
            )
            per_db_ids.setdefault(dbp, []).append(coerce_hadith_number(m["hadith_number"]))  # erwartet: nur IDs der Treffer (hadith_number) für schnelle Lookups

        row_vals: List[Any] = []
        row_vals.append(int(hid))
        row_vals.append(raw_line)

        for dbp in db_paths:
            lst = per_db_matches.get(dbp, [])  # erwartet: pro DB 0..n Match-Objekte
            lst.sort(key=lambda x: x["score"], reverse=True)  # erwartet: beste Treffer zuerst
            row_vals.append(json.dumps(lst, ensure_ascii=False))
            ids = per_db_ids.get(dbp, [])  # erwartet: 0..n hadith_number IDs aus Quell-DB
            row_vals.append(json.dumps(ids, ensure_ascii=False))

        cur.execute(insert_sql, row_vals)  # erwartet: pro Hadith genau eine Zeile in results

    conn.commit()


# =========================
# MAIN
# =========================


def main():
    tracker = PerfTracker(PERF_ENABLED)
    tracker.start()

    with tracker.phase("validate_inputs"):
        if not HADITH_LINES_PATH.exists():
            raise FileNotFoundError(str(HADITH_LINES_PATH))

    with tracker.phase("discover_db_paths"):
        db_paths = sorted(glob.glob(DB_GLOB))  # erwartet: Liste von *.db Pfaden; leer wenn Pfad falsch oder keine .db Dateien
        if not db_paths:
            raise FileNotFoundError(DB_GLOB)
        tracker.count("db_paths", len(db_paths))

    with tracker.phase("filter_db_paths"):
        db_paths = filter_compatible_db_paths(db_paths)
        if not db_paths:
            raise FileNotFoundError("No compatible DBs found for expected columns")

    global _PARQUET_MAP
    with tracker.phase("build_parquet_cache"):
        _PARQUET_MAP, cache_stats = match_cache.build_parquet_cache_if_missing(
            db_paths,
            cache_dir=CACHE_DIR,
            table=DB_TABLE,
            id_col=DB_ID_COL,
            text_col=DB_COL,
            normalize_func=normalize_to_str,
        )
    if DEBUG:
        match_logging.log_cache_stats(
            hit=cache_stats.hit, built=cache_stats.built, total=cache_stats.total
        )

    with tracker.phase("read_hadith_lines"):
        with HADITH_LINES_PATH.open("r", encoding="utf-8", errors="replace") as f:
            raw_lines = [ln.rstrip("\n") for ln in f if ln.strip()]  # erwartet: viele Zeilen; jede beginnt typischerweise mit Hadith-Nummer
    tracker.count("hadith_lines", len(raw_lines))

    if EVAL_SAMPLE_SIZE is not None:
        eval_lines = raw_lines[: int(EVAL_SAMPLE_SIZE)]
    else:
        eval_lines = raw_lines
    tracker.count("eval_lines", len(eval_lines))

    p0 = default_params()
    with tracker.phase("param_search"):
        best_p, best_objective, best_coverage, best_avg_hit = recursive_search(
            hadith_lines=eval_lines,
            db_paths=db_paths,
            p0=p0,
            depth=6,
            dx_step=0.03,
            dth_step=0.03,
            dor_step=0.03,
        )

    best_params_dict = params_to_dict(best_p)
    with tracker.phase("write_best_params"):
        OUT_BEST_PARAMS_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_BEST_PARAMS_JSON.write_text(
            json.dumps(
                {
                    "best_objective": best_objective,
                    "best_coverage": best_coverage,
                    "best_avg_hit": best_avg_hit,
                    "best_params": best_params_dict,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    with tracker.phase("create_output_db"):
        out_conn, dbname_to_col, dbname_to_idcol = create_output_db(db_paths)

    with tracker.phase("match_all"):
        with ProcessPoolExecutor(
            max_workers=MAX_WORKERS,
            initializer=_worker_init,
            initargs=(db_paths, _PARQUET_MAP),
        ) as ex:
            all_results = list(
                ex.map(match_one_hadith_all, raw_lines, [best_params_dict] * len(raw_lines))
            )  # erwartet: all_results enthält pro Zeile hadith_id und (ggf.) matches
    tracker.count("results", len(all_results))
    tracker.count("total_matches", sum(len(r.get("matches", [])) for r in all_results))

    with tracker.phase("write_results"):
        write_results_to_db(
            conn=out_conn,
            db_paths=db_paths,
            dbname_to_col=dbname_to_col,
            dbname_to_idcol=dbname_to_idcol,
            results=all_results,
        )

    out_conn.close()

    if DEBUG and PLOT_COVERAGE:
        _COVERAGE_TRACKER.plot()

    perf_data = tracker.finish()
    report = _render_perf_report(perf_data, tracker.phases, tracker.counts)
    if report:
        if PERF_REPORT_PATH:
            with open(PERF_REPORT_PATH, "a", encoding="utf-8") as f:
                f.write(report + "\n")
        else:
            print(report, file=sys.stderr)


if __name__ == "__main__":
    if PERF_CPROFILE:
        import cProfile
        import pstats
        import io as _io

        prof = cProfile.Profile()
        prof.enable()
        try:
            main()
        finally:
            prof.disable()
            s = _io.StringIO()
            sort_by = os.environ.get("PERF_CPROFILE_SORT", "tottime")
            top_n = int(os.environ.get("PERF_CPROFILE_TOP", "30"))
            ps = pstats.Stats(prof, stream=s).sort_stats(sort_by)
            ps.print_stats(top_n)
            out = "CPROFILE\n" + s.getvalue()
            if PERF_REPORT_PATH:
                with open(PERF_REPORT_PATH, "a", encoding="utf-8") as f:
                    f.write(out + "\n")
            else:
                print(out, file=sys.stderr)
    else:
        main()
