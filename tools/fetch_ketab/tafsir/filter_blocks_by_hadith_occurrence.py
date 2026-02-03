#!/usr/bin/env python3
import argparse
import json
import math
import os
import re
import sqlite3
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import DefaultDict, Dict, Iterable, List, Sequence, Set, Tuple, TypedDict

from utils.config import HADITH_CONFIG

# ---------------- Normalization ----------------
try:
    from .matn_utils import (
        HADITH_META_STOPWORDS,
        STOPWORD_LOOKUP,
        extract_matn_tokens,
        is_meta_token,
        matn_tokens_for_matching,
        tokenize,
    )
except ImportError:
    from matn_utils import (
        HADITH_META_STOPWORDS,
        STOPWORD_LOOKUP,
        extract_matn_tokens,
        is_meta_token,
        matn_tokens_for_matching,
        tokenize,
    )

QURAN_PATH_DEFAULT = os.getenv('QURAN_TEXT_PATH', 'quran-simple-plain.txt')


class HadithEntry(TypedDict):
    text: str
    source: str
    line_number: int | None


RAW_MATN_SOURCE_KEYWORDS = ('muslim', 'bukhari')


def is_raw_matn_source(source: str) -> bool:
    lowered = (source or '').lower()
    return any(keyword in lowered for keyword in RAW_MATN_SOURCE_KEYWORDS)


HADITH_NUMBER_RE = re.compile(r'^\s*\d+[\s\-ـ].*$|^\s*\d+\s*$')

ANCHOR_SCALE = 0.9
# If a hadith is short (<= this token length), use the full hadith length
# as the anchor n, so that the anchor comprises the whole hadith matn.
SHORT_HADITH_MAX_TOKENS = 5

# Minimum match factor per anchor size.
# Smaller anchors get a lower factor to allow for slight variations in short texts.
# Longer references get a much higher factor to prevent false positives from
# overlapping common phrases or long, similar-looking narrations.
MIN_MATCH_FACTORS: List[Tuple[int, float]] = [
    (4, 0.3),  # Sehr kurz: 30% (erlaubt Spielraum bei Fragmenten)
    (6, 0.4),  # Standard Kurz
    (12, 0.6),  # Mittel-Kurz
    (24, 0.75),  # Mittel
    (48, 0.82),  # Lang: Erfordert über 80% Übereinstimmung
    (100, 0.90),  # Sehr lang: Erfordert 90% Exaktheit
    (250, 0.95),  # Massive Blöcke: Fast identischer Wortlaut nötig
]



def determine_anchor_size(token_len: int, anchor_override: int | None) -> int:
    if anchor_override and anchor_override > 0:
        if token_len <= 0:
            return 1
        return max(1, min(anchor_override, token_len))
    # If the hadith is very short, use the whole hadith as the anchor
    if token_len <= SHORT_HADITH_MAX_TOKENS:
        return max(1, token_len)
    gram_target = max(1, round(token_len * ANCHOR_SCALE))
    anchor_n = token_len - gram_target + 1
    return max(1, anchor_n)


def min_match_factor(anchor_n: int) -> float:
    for limit, factor in MIN_MATCH_FACTORS:
        if anchor_n <= limit:
            return factor
    return 1.0


def build_ngram_set(
    tokens: Sequence[str],
    n: int,
    require_prefix: bool = False,
    skip_span_detection: bool = False,
    working_tokens: Sequence[str] | None = None,
) -> Set[Tuple[str, ...]]:
    return set(
        build_ngram_list(
            tokens,
            n,
            require_prefix=require_prefix,
            skip_span_detection=skip_span_detection,
            working_tokens=working_tokens,
        )
    )


def build_ngram_list(
    tokens: Sequence[str],
    n: int,
    require_prefix: bool = False,
    skip_span_detection: bool = False,
    working_tokens: Sequence[str] | None = None,
) -> List[Tuple[str, ...]]:
    n = max(1, n)
    grams: List[Tuple[str, ...]] = []
    window: deque[str] = deque(maxlen=n)

    if working_tokens is not None:
        working = list(working_tokens)
    else:
        working = (
            extract_matn_tokens(tokens, allow_span_detection=not skip_span_detection)
            if require_prefix
            else list(tokens)
        )
    i = 0
    length = len(working)

    while i < length:
        token = working[i]

        matched_len = 0
        for seq in STOPWORD_LOOKUP.get(token, []):
            if working[i : i + len(seq)] == list(seq):
                matched_len = len(seq)
                break

        if matched_len:
            window.clear()
            i += matched_len
            continue

        if is_meta_token(token):
            window.clear()
            i += 1
            continue

        window.append(token)
        if len(window) == n:
            grams.append(tuple(window))

        i += 1

    return grams


# ---------------- Data loading helpers ----------------


def parse_numbered_blocks_with_line_numbers(
    lines: Iterable[str],
) -> List[Tuple[str, int]]:
    buffered = [ln.rstrip("\n") for ln in lines]
    blocks: List[Tuple[str, int]] = []
    current: List[str] = []
    current_start: int | None = None
    number_hits = 0

    for idx, line in enumerate(buffered, 1):
        stripped = line.strip()
        if not stripped:
            continue

        if HADITH_NUMBER_RE.match(stripped):
            if current:
                blocks.append((" ".join(current).strip(), current_start or idx))
            current = [stripped]
            current_start = idx
            number_hits += 1
        else:
            if not current:
                current_start = idx
            current.append(stripped)

    if current:
        blocks.append((" ".join(current).strip(), current_start or len(buffered)))

    if number_hits == 0:
        simple: List[Tuple[str, int]] = []
        for idx, line in enumerate(buffered, 1):
            stripped = line.strip()
            if stripped:
                simple.append((stripped, idx))
        return simple
    return blocks


def parse_numbered_blocks(lines: Iterable[str]) -> List[str]:
    return [text for text, _ in parse_numbered_blocks_with_line_numbers(lines)]


def _append_json_value(val, acc: List[str]) -> None:
    """Append a JSON value to the accumulator, flattening lists."""
    if isinstance(val, list):
        for item in val:
            _append_json_value(item, acc)
        return
    if isinstance(val, dict):
        # common pattern: {"text": "..."}
        if "text" in val:
            _append_json_value(val.get("text"), acc)
        else:
            acc.append(json.dumps(val, ensure_ascii=False))
        return
    acc.append(str(val) if val is not None else "")


def _append_hadith_entry_value(
    val, acc: List[HadithEntry], source: str, line_number: int
) -> None:
    """Append a hadith value with source metadata, flattening lists/dicts."""
    if isinstance(val, list):
        for item in val:
            _append_hadith_entry_value(item, acc, source, line_number)
        return
    if isinstance(val, dict):
        if "text" in val:
            _append_hadith_entry_value(val.get("text"), acc, source, line_number)
        else:
            acc.append(
                {
                    "text": json.dumps(val, ensure_ascii=False),
                    "source": source,
                    "line_number": line_number,
                }
            )
        return
    acc.append(
        {
            "text": str(val) if val is not None else "",
            "source": source,
            "line_number": line_number,
        }
    )


def load_json_like(path: Path, value_key: str = "text") -> List[str]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "blocks" in data:
        items = data["blocks"]
    else:
        items = data

    blocks: List[str] = []
    for item in items:
        if isinstance(item, dict):
            val = item.get(value_key)
            if val is None and value_key != "text":
                val = item.get("text")
            _append_json_value(val, blocks)
        else:
            _append_json_value(item, blocks)
    return blocks


def load_ndjson(path: Path, value_key: str = "text") -> List[str]:
    blocks: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError:
                blocks.append(stripped)
                continue

            if isinstance(record, dict):
                val = record.get(value_key)
                if val is None and value_key != "text":
                    val = record.get("text")
                _append_json_value(val, blocks)
            else:
                _append_json_value(record, blocks)
    return blocks


def load_hadith_entries_from_path(
    path: Path, json_value_key: str = "text"
) -> List[HadithEntry]:
    source = str(path)
    suffix = path.suffix.lower()

    if suffix == ".json":
        blocks = load_json_like(path, value_key=json_value_key)
        return [
            {"text": blk, "source": source, "line_number": idx}
            for idx, blk in enumerate(blocks, 1)
        ]

    if suffix == ".ndjson":
        entries: List[HadithEntry] = []
        with path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    record = json.loads(stripped)
                except json.JSONDecodeError:
                    entries.append(
                        {"text": stripped, "source": source, "line_number": line_no}
                    )
                    continue

                if isinstance(record, dict):
                    val = record.get(json_value_key)
                    if val is None and json_value_key != "text":
                        val = record.get("text")
                    _append_hadith_entry_value(val, entries, source, line_no)
                else:
                    _append_hadith_entry_value(record, entries, source, line_no)
        return entries

    with path.open("r", encoding="utf-8") as f:
        blocks_with_lines = parse_numbered_blocks_with_line_numbers(f)
    return [
        {"text": blk, "source": source, "line_number": line_no}
        for blk, line_no in blocks_with_lines
    ]


def load_hadith_entries(
    paths: Sequence[Path], json_value_key: str = "text"
) -> List[HadithEntry]:
    entries: List[HadithEntry] = []
    for path in paths:
        entries.extend(
            load_hadith_entries_from_path(path, json_value_key=json_value_key)
        )
    return entries


def load_blocks(
    path: Path,
    sqlite_table: str | None = None,
    sqlite_column: str = "text",
    json_value_key: str = "text",
) -> List[str]:
    suffix = path.suffix.lower()
    if suffix in {".sqlite", ".sqlite3", ".db"}:
        table = sqlite_table or "blocks"
        col = sqlite_column or "text"

        rows: List[str] = []

        with sqlite3.connect(path) as conn:
            cur = conn.execute(f"SELECT {col} FROM {table}")
            for (val,) in cur.fetchall():
                if not val:
                    continue

                # alles zwischen <p>...</p> extrahieren
                paragraphs = re.findall(r"<p>(.*?)</p>", val, flags=re.DOTALL)

                # Whitespace auf eine Zeile reduzieren
                for p in paragraphs:
                    clean = " ".join(p.split())
                    rows.append(clean)
        return rows
    if suffix == ".json":
        return load_json_like(path, value_key=json_value_key)
    if suffix == ".ndjson":
        return load_ndjson(path, value_key=json_value_key)
    with path.open("r", encoding="utf-8") as f:
        return [line.rstrip("\n") for line in f]


def load_hadith_blocks(path: Path, json_value_key: str = "text") -> List[str]:
    entries = load_hadith_entries_from_path(path, json_value_key=json_value_key)
    return [entry["text"] for entry in entries]


def load_merged_blocks(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "blocks" not in data:
        raise ValueError(
            "Expected top-level object with 'blocks' for merged tafsir input."
        )
    blocks = data["blocks"]
    if not isinstance(blocks, list):
        raise ValueError("'blocks' must be a list in merged tafsir input.")
    return blocks


# ---------------- Quran metadata helpers ----------------
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


def load_quran_metadata(path: Path) -> Dict[int, Dict]:
    mapping: Dict[int, Dict] = {}
    try:
        with path.open("r", encoding="utf-8") as f:
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
                sura_name = (
                    SURAH_NAMES[sura_num - 1]
                    if 0 < sura_num <= len(SURAH_NAMES)
                    else ""
                )
                mapping[idx] = {
                    "sura_number": sura_num,
                    "sura_name": sura_name,
                    "ayah_number": ayah_num,
                    "ayah_text": ayah_text,
                }
    except FileNotFoundError:
        print(f"WARNING: Quran text file not found at {path}, sura metadata disabled.")
    except Exception as exc:  # pragma: no cover
        print(f"WARNING: Failed to read Quran metadata from {path}: {exc}")
    return mapping


# ---------------- Matching ----------------


def index_hadith_ngrams(
    hadiths: List[str],
    require_prefix: bool = True,
    per_hadith_require_prefix: Sequence[bool] | None = None,
    per_hadith_skip_span: Sequence[bool] | None = None,
    anchor_override: int | None = None,
) -> Tuple[
    DefaultDict[Tuple[str, ...], Set[int]],
    List[str],
    Dict[str, int | None],
    List[List[Tuple[str, ...]]],
    List[int],
]:
    index: DefaultDict[Tuple[str, ...], Set[int]] = defaultdict(set)
    freq: Counter[Tuple[str, ...]] = Counter()
    per_hadith_grams: List[List[Tuple[str, ...]]] = []
    per_hadith_anchor_n: List[int] = []

    for hid, text in enumerate(hadiths):
        tokens = tokenize(text)
        use_prefix = (
            per_hadith_require_prefix[hid]
            if per_hadith_require_prefix and hid < len(per_hadith_require_prefix)
            else require_prefix
        )
        skip_span = (
            per_hadith_skip_span[hid]
            if per_hadith_skip_span and hid < len(per_hadith_skip_span)
            else False
        )
        working_tokens = matn_tokens_for_matching(tokens, use_prefix, skip_span)
        hadith_anchor_n = determine_anchor_size(len(working_tokens), anchor_override)
        per_hadith_anchor_n.append(hadith_anchor_n)
        grams = build_ngram_list(
            tokens,
            hadith_anchor_n,
            require_prefix=False,
            working_tokens=working_tokens,
        )
        per_hadith_grams.append(grams)
        for gram in set(grams):
            index[gram].add(hid)
            freq.update([gram])

    stats = {
        "unique_grams": len(freq),
        "drop_threshold": None,
        "dropped_grams": 0,
        "total_anchor_grams": sum(len(g) for g in per_hadith_grams),
    }

    return index, hadiths, stats, per_hadith_grams, per_hadith_anchor_n


def match_blocks(
    blocks: List[str],
    hadith_index: Dict[Tuple[str, ...], Set[int]],
    hadiths: List[str],
    min_words: int,
    min_matches: int,
    hit_rate_threshold: float,
    hadith_anchor_ngrams: Sequence[List[Tuple[str, ...]]],
    hadith_anchor_ns: Sequence[int],
    hadith_entries: Sequence[HadithEntry] | None = None,
    require_prefix: bool = True,
    anchor_override: int | None = None,
) -> Dict:
    anchor_descriptor = (
        anchor_override
        if anchor_override and anchor_override > 0
        else "dynamic (len 0.9)"
    )
    result = {
        "meta": {
            "anchor_ngram_size": anchor_descriptor,
            "min_matches": min_matches,
            "hit_rate_threshold": hit_rate_threshold,
            "total_blocks": len(blocks),
            "matched_blocks": 0,
            "matn_conformity": {
                "hit_rate_threshold": hit_rate_threshold,
                "anchor_ngram_size": anchor_descriptor,
                "anchor_scale": ANCHOR_SCALE,
                "require_prefix_reference_default": require_prefix,
                "require_prefix_reference_mode": "per_source",
                "require_prefix_blocks": True,
            },
        },
        "blocks": [],
    }

    if hadith_entries:
        source_counts = Counter(entry["source"] for entry in hadith_entries)
        result["meta"]["hadith_sources"] = [
            {"file": src, "count": count}
            for src, count in sorted(source_counts.items())
        ]

    unique_anchor_ns = sorted(set(hadith_anchor_ns))

    for block_id, text in enumerate(blocks, start=1):
        block_tokens = tokenize(text)
        block_ngram_cache: Dict[int, Set[Tuple[str, ...]]] = {}
        block_len = len(block_tokens)
        candidate_ids: Set[int] = set()
        for anchor_n in unique_anchor_ns:
            if anchor_n <= 0 or anchor_n > block_len:
                continue
            block_anchor_grams = block_ngram_cache.setdefault(
                anchor_n,
                set(build_ngram_list(block_tokens, anchor_n, require_prefix=True)),
            )
            for gram in block_anchor_grams:
                if gram in hadith_index:
                    candidate_ids.update(hadith_index[gram])

        if not candidate_ids:
            continue

        matched_hadiths: List[Dict] = []
        for hid in sorted(candidate_ids):
            if hid >= len(hadith_anchor_ngrams):
                continue
            hadith_grams = hadith_anchor_ngrams[hid]
            total_grams = len(hadith_grams)
            if total_grams == 0:
                continue
            hadith_anchor_size = (
                hadith_anchor_ns[hid]
                if hid < len(hadith_anchor_ns)
                else max(min_words, 1)
            )
            block_anchor_grams = block_ngram_cache.get(hadith_anchor_size, set())
            if not block_anchor_grams:
                continue
            # Only count hadith grams that match the desired anchor length (sanity filter)
            total_grams = sum(1 for g in hadith_grams if len(g) == hadith_anchor_size)
            if total_grams == 0:
                continue
            hits = sum(
                1
                for gram in hadith_grams
                if len(gram) == hadith_anchor_size and gram in block_anchor_grams
            )
            factor = min_match_factor(hadith_anchor_size)
            dynamic_target = max(1, math.ceil(min_matches * factor))
            required_hits = min(total_grams, dynamic_target)
            if hits < required_hits:
                continue

            hit_rate = hits / total_grams
            if hit_rate <= hit_rate_threshold:
                continue

            hit_info = {
                "hit_rate": round(float(hit_rate), 4),
                "anchor_hits": {"found": hits, "total": total_grams},
            }

            if hadith_entries and hid < len(hadith_entries):
                entry = hadith_entries[hid]
                matched_hadiths.append(
                    {
                        "text": entry["text"],
                        "source_file": entry.get("source"),
                        "line_number": entry.get("line_number"),
                        **hit_info,
                    }
                )
            else:
                matched_hadiths.append({"text": hadiths[hid], **hit_info})

        if matched_hadiths:
            result["blocks"].append(
                {
                    "block_id": block_id,
                    "text": text,
                    "hadiths": matched_hadiths,
                }
            )
            result["meta"]["matched_blocks"] += 1

    return result


def filter_merged_blocks(
    merged_blocks: List[Dict],
    matn_cfg: Dict[str, float | int | str],
    quran_lookup: Dict[int, Dict],
) -> Dict:
    anchor_override = int(matn_cfg.get("anchor_n", 0) or 0)
    hit_rate_threshold = float(matn_cfg.get("hit_rate_threshold", 0.0) or 0.0)
    require_prefix_reference = bool(matn_cfg.get("require_prefix", True))
    result_blocks: List[Dict] = []
    total_hadiths_checked = 0
    total_hadiths_retained = 0
    blocks_with_matches = 0

    for block in merged_blocks:
        block_text = str(block.get("text") or "")
        block_id = int(block.get("block_id") or 0)
        source = block.get("source")
        hadith_list = block.get("hadiths") or []
        if not hadith_list:
            continue

        block_tokens = tokenize(block_text)
        block_len = len(block_tokens)
        block_ngram_cache: Dict[int, Set[Tuple[str, ...]]] = {}

        matched: List[Dict] = []
        for htxt in hadith_list:
            total_hadiths_checked += 1
            hadith_tokens = tokenize(str(htxt))
            working_tokens = matn_tokens_for_matching(
                hadith_tokens, require_prefix_reference, True
            )
            hadith_anchor_n = determine_anchor_size(
                len(working_tokens), anchor_override
            )
            hadith_anchor_grams = build_ngram_list(
                hadith_tokens,
                hadith_anchor_n,
                require_prefix=True,
                working_tokens=working_tokens,
            )
            total_grams = len(hadith_anchor_grams)
            if total_grams == 0:
                continue

            if hadith_anchor_n <= 0 or hadith_anchor_n > block_len:
                block_anchor_grams = set()
            else:
                block_anchor_grams = block_ngram_cache.setdefault(
                    hadith_anchor_n,
                    set(
                        build_ngram_list(
                            block_tokens,
                            hadith_anchor_n,
                            require_prefix=True,
                        )
                    ),
                )
            hits = sum(1 for gram in hadith_anchor_grams if gram in block_anchor_grams)
            hit_rate = hits / total_grams
            if hit_rate > hit_rate_threshold:
                total_hadiths_retained += 1
                matched.append(
                    {
                        "text": htxt,
                        "hit_rate": round(float(hit_rate), 4),
                        "anchor_hits": {"found": hits, "total": total_grams},
                    }
                )

        if not matched:
            continue

        blocks_with_matches += 1
        enriched = {
            "block_id": block_id,
            "source": source,
            "text": block_text,
            "hadiths": matched,
        }
        if block_id in quran_lookup:
            enriched.update(quran_lookup[block_id])
        result_blocks.append(enriched)

    anchor_descriptor = anchor_override if anchor_override > 0 else "dynamic (len 0.9)"
    return {
        "meta": {
            "total_blocks": len(merged_blocks),
            "blocks_with_matches": blocks_with_matches,
            "total_hadiths_checked": total_hadiths_checked,
            "hadiths_retained": total_hadiths_retained,
            "matn_conformity": {
                "hit_rate_threshold": hit_rate_threshold,
                "anchor_ngram_size": anchor_descriptor,
                "anchor_scale": ANCHOR_SCALE,
                "require_prefix_reference_default": require_prefix_reference,
                "require_prefix_reference_mode": "uniform",
                "require_prefix_blocks": True,
            },
        },
        "blocks": result_blocks,
    }


# ---------------- CLI ----------------


def main():
    cfg_defaults = HADITH_CONFIG.get("matn_comparison", {})
    default_anchor_n = int(cfg_defaults.get("anchor_n", 0) or 0)
    default_hit_rate = float(cfg_defaults.get("hit_rate_threshold", 0.0) or 0.0)
    default_require_prefix = bool(cfg_defaults.get("require_prefix", True))

    parser = argparse.ArgumentParser(
        description="Filter tafsir blocks by hadith matn occurrence."
    )
    parser.add_argument(
        "--blocks",
        help="Path to blocks file (one block per line or JSON/NDJSON). Ignored if --merged-tafsir is used.",
    )
    parser.add_argument(
        "--hadith",
        action="append",
        nargs="+",
        help="Paths to hadith reference file(s). Can be repeated to combine multiple sources. Ignored if --merged-tafsir is used.",
    )
    parser.add_argument(
        "--out", default="filtered_blocks.json", help="Output JSON path."
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=default_anchor_n,
        help="Anchor n-gram size (number of words) to look for. Use 0 (default) for dynamic sizing at 0.9×Matn length, otherwise overrides the default.",
    )
    parser.add_argument(
        "--hit-rate",
        type=float,
        default=default_hit_rate,
        help="Minimum hit-rate (found anchors / hadith anchors) required for a match. Defaults to config matn_comparison.hit_rate_threshold.",
    )
    parser.add_argument(
        "--no-prefix-filter",
        action="store_true",
        help="Disable matn prefix filtering when building hadith anchors (blocks bleiben trotzdem prefix-gefiltert).",
    )
    parser.add_argument(
        "--blocks-sqlite-table",
        help="Wenn --blocks auf eine .sqlite/.db zeigt: Tabellenname (default 'blocks').",
    )
    parser.add_argument(
        "--blocks-sqlite-column",
        default="text",
        help="Wenn --blocks auf eine .sqlite/.db zeigt: Spaltenname mit Text (default 'text').",
    )
    parser.add_argument(
        "--blocks-json-key",
        default="text",
        help="Wenn --blocks auf eine JSON/NDJSON-Datei zeigt: Feldname mit dem Block-Text (default 'text').",
    )
    parser.add_argument(
        "--min-matches",
        type=int,
        default=1,
        help="Minimum distinct matching n-grams needed to accept a hadith as matching a block.",
    )
    parser.add_argument(
        "--hadith-json-key",
        default="text",
        help="Wenn --hadith auf eine JSON/NDJSON-Datei zeigt: Feldname mit den Hadith-Texten (z.B. 'hadiths' für tafsir_merged_sorted.json).",
    )
    parser.add_argument(
        "--merged-tafsir",
        help="Direkter Einstieg: Pfad zu tafsir_merged_sorted.json (nimmt 'text' als Blöcke und 'hadiths' als Hadith-Referenz).",
    )
    parser.add_argument(
        "--quran-path",
        default=QURAN_PATH_DEFAULT,
        help="Pfad zu quran-simple-plain.txt für Suren/Ayat-Referenzen (nur relevant mit --merged-tafsir).",
    )

    args = parser.parse_args()
    require_prefix_reference_default = (
        default_require_prefix and not args.no_prefix_filter
    )
    anchor_override = args.min_words if args.min_words and args.min_words > 0 else None
    min_words_for_match = anchor_override or 0
    hit_rate_threshold = max(0.0, min(float(args.hit_rate), 1.0))

    if args.merged_tafsir:
        if args.blocks or args.hadith:
            parser.error(
                "Bitte entweder --merged-tafsir oder --blocks/--hadith verwenden, nicht beides."
            )
        merged_path = Path(args.merged_tafsir)
        merged_blocks = load_merged_blocks(merged_path)
        matn_cfg = {
            "anchor_n": anchor_override or 0,
            "hit_rate_threshold": hit_rate_threshold,
            "require_prefix": require_prefix_reference_default,
        }
        quran_lookup = load_quran_metadata(Path(args.quran_path))
        result = filter_merged_blocks(merged_blocks, matn_cfg, quran_lookup)
        result["meta"]["source"] = str(merged_path)
        result["meta"]["quran_path"] = str(args.quran_path)
        with Path(args.out).open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"✔ Merged blocks read    : {len(merged_blocks)}")
        print(f"✔ Blocks with matches   : {result['meta']['blocks_with_matches']}")
        print(f"✔ Hadiths retained      : {result['meta']['hadiths_retained']}")
        print(f"✔ Output written to     : {args.out}")
        return
    else:
        hadith_args = [p for group in (args.hadith or []) for p in group]
        if not args.blocks or not hadith_args:
            parser.error(
                "--blocks und --hadith sind erforderlich, sofern nicht --merged-tafsir gesetzt ist."
            )

        blocks_path = Path(args.blocks)
        hadith_paths = [Path(p) for p in hadith_args]

        blocks = load_blocks(
            blocks_path,
            sqlite_table=args.blocks_sqlite_table,
            sqlite_column=args.blocks_sqlite_column,
            json_value_key=args.blocks_json_key,
        )
        hadith_entries = load_hadith_entries(
            hadith_paths, json_value_key=args.hadith_json_key
        )
        hadith_texts = [entry["text"] for entry in hadith_entries]

    per_hadith_require_prefix: List[bool] = []
    per_hadith_skip_span: List[bool] = []
    span_disabled_sources: Set[str] = set()
    prefix_disabled_sources: Set[str] = set()
    for entry in hadith_entries:
        source = entry.get("source") or ""
        raw_matn_source = is_raw_matn_source(source)
        use_prefix = False if raw_matn_source else require_prefix_reference_default
        skip_span = raw_matn_source
        if raw_matn_source:
            span_disabled_sources.add(Path(source).name or source)
        if not use_prefix:
            prefix_disabled_sources.add(Path(source).name or source)
        per_hadith_require_prefix.append(use_prefix)
        per_hadith_skip_span.append(skip_span)

    if not hadith_texts:
        raise SystemExit("No hadiths loaded from reference file.")

    min_matches = max(args.min_matches, 1)
    hadith_index, hadith_texts, stats, hadith_anchor_ngrams, hadith_anchor_ns = (
        index_hadith_ngrams(
            hadith_texts,
            require_prefix=require_prefix_reference_default,
            per_hadith_require_prefix=per_hadith_require_prefix,
            per_hadith_skip_span=per_hadith_skip_span,
            anchor_override=anchor_override,
        )
    )
    result = match_blocks(
        blocks,
        hadith_index,
        hadith_texts,
        min_words_for_match,
        min_matches,
        hit_rate_threshold,
        hadith_anchor_ngrams,
        hadith_anchor_ns,
        hadith_entries=hadith_entries,
        require_prefix=require_prefix_reference_default,
        anchor_override=anchor_override,
    )
    result["meta"]["max_df"] = stats["drop_threshold"]
    result["meta"]["hadith_unique_grams"] = stats["unique_grams"]
    result["meta"]["hadith_dropped_grams"] = stats["dropped_grams"]
    result["meta"]["hadith_total_anchor_grams"] = stats["total_anchor_grams"]
    result["meta"]["prefix_filter"] = {
        "reference_default": require_prefix_reference_default,
        "reference_per_source": True,
        "blocks": True,
    }
    if span_disabled_sources:
        result["meta"]["span_detection_disabled_for_sources"] = sorted(
            span_disabled_sources
        )
    if prefix_disabled_sources:
        result["meta"]["prefix_disabled_for_sources"] = sorted(prefix_disabled_sources)

    with Path(args.out).open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"✔ Blocks read           : {result['meta']['total_blocks']}")
    print(f"✔ Blocks matched        : {result['meta']['matched_blocks']}")
    print(f"✔ Hadith unique n-grams : {stats['unique_grams']}")
    print(f"✔ Min matches per hadith: {min_matches}")
    print(f"✔ Hit-rate threshold    : {hit_rate_threshold}")
    anchor_label = (
        anchor_override
        if anchor_override and anchor_override > 0
        else "dynamic (len 0.9)"
    )
    print(f"✔ Anchor size (words)   : {anchor_label}")
    print(f"✔ Output written to     : {args.out}")


if __name__ == "__main__":
    main()


# pipenv run python filter_blocks_by_hadith_occurrence.py \
#   --merged-tafsir ./data/tafsir_merged_sorted.json \
#   --quran-path ./quran-simple-plain.txt \
#   --out ./data/gefiltert.json --min-words 4

# pipenv run python filter_blocks_by_hadith_occurrence.py \
#  --blocks ./your.db --blocks-sqlite-table your_table --blocks-sqlite-column text \
#  --hadith ../sahihah/sahihah_komplett.txt \
#  --out ./data/gefiltert.json --min-words 4


# pipenv run python filter_blocks_by_hadith_occurrence.py \
#   --blocks tafsir_p_tags.txt \
#   --hadith ../sahihah/sahihah_komplett.txt \
#   --out data/gefiltert.json \
#   --min-words 4

# ALLE
# python3 filter_blocks_by_hadith_occurrence.py --hit-rate 0.95 --min-matches 3 \
#  --blocks tafsir_books/katheer.sqlite3 --blocks-sqlite-table katheer --blocks-sqlite-column text \
#  --hadith ../sahihah/sahihah_komplett.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/muslim.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/bukhari.txt \
#  --out data/gefiltert_katheer.json && \
# python3 filter_blocks_by_hadith_occurrence.py --hit-rate 0.95 --min-matches 3 \
#  --blocks tafsir_books/waseet.sqlite3 --blocks-sqlite-table waseet --blocks-sqlite-column text \
#  --hadith ../sahihah/sahihah_komplett.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/muslim.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/bukhari.txt \
#  --out data/gefiltert_waseet.json && \
# python3 filter_blocks_by_hadith_occurrence.py --hit-rate 0.95 --min-matches 3 \
#  --blocks tafsir_books/tabary.sqlite3 --blocks-sqlite-table tabary --blocks-sqlite-column text \
#  --hadith ../sahihah/sahihah_komplett.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/muslim.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/bukhari.txt \
#  --out data/gefiltert_tabary.json && \
# python3 filter_blocks_by_hadith_occurrence.py --hit-rate 0.95 --min-matches 3 \
#  --blocks tafsir_books/sa3dy.sqlite3 --blocks-sqlite-table sa3dy --blocks-sqlite-column text \
#  --hadith ../sahihah/sahihah_komplett.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/muslim.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/bukhari.txt \
#  --out data/gefiltert_sa3dy.json && \
# python3 filter_blocks_by_hadith_occurrence.py --hit-rate 0.95 --min-matches 3 \
#  --blocks tafsir_books/baghawy.sqlite3 --blocks-sqlite-table baghawy --blocks-sqlite-column text \
#  --hadith ../sahihah/sahihah_komplett.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/muslim.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/bukhari.txt \
#  --out data/gefiltert_baghawy.json && \
# python3 filter_blocks_by_hadith_occurrence.py --hit-rate 0.95 --min-matches 3 \
#  --blocks tafsir_books/qortoby.sqlite3 --blocks-sqlite-table qortoby --blocks-sqlite-column text \
#  --hadith ../sahihah/sahihah_komplett.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/muslim.txt /home/muhammed-emin-eser/desk/apps/fetch_ketab/sahihah/bukhari.txt \
#  --out data/gefiltert_qortoby.json
