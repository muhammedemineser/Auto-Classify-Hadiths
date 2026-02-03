#!/usr/bin/env python3
"""
Match Quran verses to Hadith lines based on literal shared word sequences.

Normalization removes Arabic diacritics, tatweel, punctuation, and extra
whitespace; it also collapses standalone leading "و" onto the next token for
comparison only. Output preserves original verse and Hadith text.
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import numpy as np

from sentence_transformers import SentenceTransformer


QURAN_RE = re.compile(r"^\s*(\d+)\s*[:.|]\s*(\d+)\s*[|.\-–—]?\s*(.*)$")
HADITH_RE = re.compile(r"^\s*(\d+)\s*-\s*(.*)$")

ARABIC_DIACRITICS_RE = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
WAW_GAP_RE = re.compile(r"(^|\s)و\s+", flags=re.MULTILINE)
WHITESPACE_RE = re.compile(r"\s+")
TATWEEL = "\u0640"

PUNCTUATION_CHARS = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~""" "«»“”‘’؟؛،…ـ"
PUNCT_TRANSLATION = str.maketrans({ch: " " for ch in PUNCTUATION_CHARS})


@dataclass
class Verse:
    sura: int
    aya: int
    text: str
    tokens: Tuple[str, ...]


@dataclass
class Hadith:
    hadith_id: int
    text: str
    tokens: Tuple[str, ...]
    original_line: str


def normalize_for_match(text: str) -> str:
    """Apply normalization rules for matching without altering semantics."""
    cleaned = text.replace(TATWEEL, "")
    cleaned = ARABIC_DIACRITICS_RE.sub("", cleaned)
    cleaned = cleaned.translate(PUNCT_TRANSLATION)
    cleaned = WAW_GAP_RE.sub(r"\1و", cleaned)
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def tokenize(text: str) -> List[str]:
    normalized = normalize_for_match(text)
    if not normalized:
        return []
    return normalized.split(" ")


def generate_ngrams(tokens: Sequence[str], size: int) -> Iterable[Tuple[str, ...]]:
    if size <= 0 or len(tokens) < size:
        return
    for idx in range(len(tokens) - size + 1):
        yield tuple(tokens[idx : idx + size])


def unique_ngrams(tokens: Sequence[str], size: int) -> Iterable[Tuple[str, ...]]:
    seen: Set[Tuple[str, ...]] = set()
    for gram in generate_ngrams(tokens, size):
        if gram not in seen:
            seen.add(gram)
            yield gram


def read_quran(path: str) -> List[Verse]:
    verses: List[Verse] = []
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, 1):
            line = raw_line.rstrip("\n\r")
            if not line.strip():
                continue
            match = QURAN_RE.match(line)
            if not match:
                print(f"Skipping Quran line {lineno}: {line}", file=sys.stderr)
                continue
            sura = int(match.group(1))
            aya = int(match.group(2))
            verse_text = match.group(3)
            tokens = tuple(tokenize(verse_text))
            verses.append(Verse(sura, aya, verse_text, tokens))
    return verses


# Matn extraction patterns (order matters)
MATN_PAREN_RE = re.compile(r"\(\s*([^()]{20,}?)\s*\)")
MATN_QUOTE_RE = re.compile(r'"([^"]{20,})"')
STOP_MARKER_RE = re.compile(
    r"\s+(?:أخرجه|رواه|قال\s+(?:الألباني|الترمذي|الحاكم|الذهبي)|قلت|@|\(تنبيه|\bقال:\b)"
)


def extract_matn(text: str) -> Optional[str]:
    """
    Extract the full hadith matn by cutting ONLY at explicit
    commentary / takhrij markers. Parentheses and quotes are preserved.
    """

    # Cut at first real commentary marker
    m = STOP_MARKER_RE.search(text)
    if m:
        text = text[: m.start()]

    # Cleanup
    text = text.strip(" .،؛:-–—")

    # Reject unrealistically short remnants
    if len(text.split()) < 4:
        return None

    return text


def read_hadiths(path: str) -> List[Hadith]:
    hadiths: List[Hadith] = []
    with open(path, "r", encoding="utf-8") as handle:
        for lineno, raw_line in enumerate(handle, 1):
            line = raw_line.rstrip("\n\r")
            if not line.strip():
                continue
            match = HADITH_RE.match(line)
            if not match:
                print(f"Skipping Hadith line {lineno}: {line}", file=sys.stderr)
                continue
            hadith_id = int(match.group(1))
            full_text = match.group(2)
            matn = extract_matn(full_text)
            if not matn:
                continue

            tokens = tuple(tokenize(matn))

            hadiths.append(
                Hadith(
                    hadith_id=hadith_id,
                    text=matn,
                    tokens=tokens,
                    original_line=f"{hadith_id}- {matn}",
                )
            )

    return hadiths


def build_index(
    verses: Sequence[Verse], min_words: int
) -> Dict[Tuple[str, ...], Set[int]]:
    index: Dict[Tuple[str, ...], Set[int]] = defaultdict(set)
    for idx, verse in enumerate(verses):
        for gram in unique_ngrams(verse.tokens, min_words):
            index[gram].add(idx)
    return index


def match_hadiths_to_verses(
    verses: Sequence[Verse], hadiths: Sequence[Hadith], min_words: int
) -> Dict[int, Set[int]]:
    inverted = build_index(verses, min_words)
    matches: Dict[int, Set[int]] = defaultdict(set)
    for hadith_idx, hadith in enumerate(hadiths):
        for gram in unique_ngrams(hadith.tokens, min_words):
            for verse_idx in inverted.get(gram, ()):
                matches[verse_idx].add(hadith_idx)
    return matches


def embed_texts(
    model: "SentenceTransformer", texts: Sequence[str], batch_size: int
) -> np.ndarray:
    embeddings = model.encode(
        list(texts),
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return embeddings.astype("float32", copy=False)


def semantic_match_hadiths_to_verses(
    verses: Sequence[Verse],
    hadiths: Sequence[Hadith],
    model_name: str,
    top_k: int,
    min_similarity: float,
    batch_size: int,
) -> Dict[int, Set[int]]:
    if SentenceTransformer is None:
        raise RuntimeError(
            "sentence-transformers not installed; run `pip install sentence-transformers`"
        )

    verse_texts = [v.text for v in verses]
    hadith_texts = [h.text for h in hadiths]
    if not verse_texts or not hadith_texts:
        return {}

    model = SentenceTransformer(model_name)
    verse_emb = embed_texts(model, verse_texts, batch_size=batch_size)
    hadith_emb = embed_texts(model, hadith_texts, batch_size=batch_size)

    matches: Dict[int, Set[int]] = defaultdict(set)
    hadith_matrix = hadith_emb.T  # shape: dim x H
    dim = hadith_matrix.shape[0]
    if verse_emb.shape[1] != dim:
        raise RuntimeError("Embedding dimensions for verses and hadiths do not match.")

    # Chunk verses to limit memory when forming similarity blocks.
    chunk_size = max(1, 256)
    for start in range(0, len(verse_emb), chunk_size):
        v_chunk = verse_emb[start : start + chunk_size]  # shape: C x dim
        similarities = np.matmul(
            v_chunk, hadith_matrix
        )  # C x H, cosine because normalized
        for row_idx, sim_row in enumerate(similarities):
            verse_idx = start + row_idx
            if top_k > 0:
                k = min(top_k, sim_row.size)
                top_indices = np.argpartition(-sim_row, k - 1)[:k]
                for h_idx in top_indices:
                    if sim_row[h_idx] >= min_similarity:
                        matches[verse_idx].add(h_idx)
            else:
                hit_indices = np.flatnonzero(sim_row >= min_similarity)
                for h_idx in hit_indices:
                    matches[verse_idx].add(h_idx)
    return matches


def write_output(
    path: str,
    verses: Sequence[Verse],
    hadiths: Sequence[Hadith],
    matches: Dict[int, Set[int]],
) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(
            """<!DOCTYPE html>
    <html lang="ar">
    <head>
    <meta charset="utf-8">
    <style>
    body {
    font-family: "Amiri", serif;
    direction: rtl;
    line-height: 1.8;
    }
    .verse {
    font-weight: bold;
    margin-top: 2em;
    }
    .hadith {
    margin-right: 1.5em;
    }
    </style>
    </head>
    <body>
    """
        )

        for verse_idx, verse in enumerate(verses):
            handle.write(
                f'<div class="verse">[{verse.sura}:{verse.aya}] {verse.text}</div>\n'
            )

            hit_indices = matches.get(verse_idx)
            if hit_indices:
                sorted_hits = sorted(
                    hit_indices, key=lambda idx: hadiths[idx].hadith_id
                )
                handle.write("<ul>\n")
                for hid in sorted_hits:
                    handle.write(
                        f"<li class='hadith'>{hadiths[hid].original_line}</li>\n"
                    )
                handle.write("</ul>\n")

        handle.write("</body></html>")


def log_stats(
    verses: Sequence[Verse], hadiths: Sequence[Hadith], matches: Dict[int, Set[int]]
) -> None:
    verses_with_hits = sum(1 for hits in matches.values() if hits)
    total_pairs = sum(len(hits) for hits in matches.values())
    print(f"Verse count: {len(verses)}", file=sys.stderr)
    print(f"Hadith count: {len(hadiths)}", file=sys.stderr)
    print(f"Verses with matches: {verses_with_hits}", file=sys.stderr)
    print(f"Total verse-hadith links: {total_pairs}", file=sys.stderr)


def merge_matches(*match_dicts: Dict[int, Set[int]]) -> Dict[int, Set[int]]:
    merged: Dict[int, Set[int]] = defaultdict(set)
    for match_dict in match_dicts:
        for verse_idx, hits in match_dict.items():
            merged[verse_idx].update(hits)
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Match Quran verses to Hadith lines using literal n-gram overlap and/or "
            "semantic similarity on normalized Arabic text."
        )
    )
    parser.add_argument("--quran", required=True, help="Input Quran TXT file (UTF-8).")
    parser.add_argument(
        "--hadith", required=True, help="Input Hadith TXT file (UTF-8)."
    )
    parser.add_argument("--out", default="output.txt", help="Output file path.")
    parser.add_argument(
        "--mode",
        choices=["literal", "semantic", "both"],
        default="literal",
        help="Match strategy: literal n-gram, semantic embeddings, or both.",
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=4,
        help="Minimum n-gram length required for a match (default: 4).",
    )
    parser.add_argument(
        "--semantic-model",
        default="paraphrase-multilingual-MiniLM-L12-v2",
        help="SentenceTransformer model name for semantic matching.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top similar hadiths to keep per verse in semantic mode (0 = no limit).",
    )
    parser.add_argument(
        "--min-sim",
        type=float,
        default=0.5,
        help="Minimum cosine similarity (0-1) required in semantic mode.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for embedding computation in semantic mode.",
    )
    args = parser.parse_args()
    if args.min_words < 1:
        parser.error("--min-words must be a positive integer")
    if args.top_k < 0:
        parser.error("--top-k must be non-negative (0 means no limit)")
    if not 0.0 <= args.min_sim <= 1.0:
        parser.error("--min-sim should be between 0.0 and 1.0 for cosine similarity")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    return args


def main() -> None:
    args = parse_args()
    verses = read_quran(args.quran)
    hadiths = read_hadiths(args.hadith)
    match_sets: List[Dict[int, Set[int]]] = []

    if args.mode in ("literal", "both"):
        match_sets.append(match_hadiths_to_verses(verses, hadiths, args.min_words))

    if args.mode in ("semantic", "both"):
        match_sets.append(
            semantic_match_hadiths_to_verses(
                verses=verses,
                hadiths=hadiths,
                model_name=args.semantic_model,
                top_k=args.top_k,
                min_similarity=args.min_sim,
                batch_size=args.batch_size,
            )
        )

    matches = merge_matches(*match_sets)
    write_output(args.out, verses, hadiths, matches)
    log_stats(verses, hadiths, matches)


if __name__ == "__main__":
    main()
