#!/usr/bin/env python3
"""
ML-style matcher using TF-IDF + Kosinus-Ähnlichkeit.
Ziel: flexibler Rahmen, der allein auf dem Matn (per Prefix-Fenster) vergleicht.
"""
import argparse
import json
from pathlib import Path
from typing import List, Sequence, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from filter_blocks_by_hadith_occurrence import (
    extract_matn_tokens,
    load_blocks,
    parse_numbered_blocks,
    tokenize,
)


def tokens_to_matn_text(tokens: Sequence[str]) -> str:
    matn_tokens = extract_matn_tokens(tokens)
    if matn_tokens:
        return " ".join(matn_tokens)
    return " ".join(tokens)


def load_hadith_matn(path: Path) -> List[str]:
    if path.suffix.lower() in {".json", ".ndjson"}:
        raw_lines = load_blocks(path)
    else:
        with path.open("r", encoding="utf-8") as f:
            raw_lines = parse_numbered_blocks(f)
    return [tokens_to_matn_text(tokenize(line)) for line in raw_lines if line.strip()]


def load_block_matn(path: Path, sqlite_table: str | None = None, sqlite_column: str = "text") -> List[Tuple[int, str]]:
    raw = load_blocks(path, sqlite_table=sqlite_table, sqlite_column=sqlite_column)
    pairs: List[Tuple[int, str]] = []
    for idx, line in enumerate(raw, 1):
        text = str(line)
        matn = tokens_to_matn_text(tokenize(text))
        pairs.append((idx, matn))
    return pairs


def filter_with_tfidf(
    blocks: List[Tuple[int, str]],
    hadiths: List[str],
    sim_threshold: float,
    top_k: int,
) -> dict:
    corpus = hadiths + [b[1] for b in blocks]
    vectorizer = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        min_df=1,
    )
    tfidf = vectorizer.fit_transform(corpus)
    hadith_vecs = tfidf[: len(hadiths)]
    block_vecs = tfidf[len(hadiths) :]

    result_blocks = []
    matched_blocks = 0

    sims = linear_kernel(block_vecs, hadith_vecs)
    for (block_id, raw_matn), row in zip(blocks, sims):
        best_idx = row.argsort()[::-1]
        hits = []
        for idx in best_idx[:top_k]:
            score = row[idx]
            if score < sim_threshold:
                break
            hits.append({"hadith_id": idx + 1, "score": round(float(score), 4), "text": hadiths[idx]})
        if not hits:
            continue
        matched_blocks += 1
        result_blocks.append(
            {
                "block_id": block_id,
                "matn": raw_matn,
                "matches": hits,
            }
        )

    return {
        "meta": {
            "total_blocks": len(blocks),
            "matched_blocks": matched_blocks,
            "total_hadiths": len(hadiths),
            "sim_threshold": sim_threshold,
            "top_k": top_k,
            "vectorizer": "tfidf-word-1,2",
        },
        "blocks": result_blocks,
    }


def main():
    parser = argparse.ArgumentParser(description="TF-IDF matcher for tafsir blocks vs hadith matn.")
    parser.add_argument("--blocks", required=True, help="Path zu Blöcken (TXT/JSON/NDJSON/SQLite).")
    parser.add_argument("--blocks-sqlite-table", help="Tabellenname, falls --blocks auf SQLite zeigt (default 'blocks').")
    parser.add_argument("--blocks-sqlite-column", default="text", help="Spaltenname, falls --blocks auf SQLite zeigt (default 'text').")
    parser.add_argument("--hadith", required=True, help="Pfad zur Hadith-Sammlung (konstant: sahihah_komplett.txt).")
    parser.add_argument("--out", default="ml_matches.json", help="Output-Datei.")
    parser.add_argument("--sim-threshold", type=float, default=0.2, help="Mindest-Kosinus-Score für Treffer.")
    parser.add_argument("--top-k", type=int, default=3, help="Maximale Treffer pro Block.")
    args = parser.parse_args()

    blocks_path = Path(args.blocks)
    hadith_path = Path(args.hadith)

    hadiths = load_hadith_matn(hadith_path)
    blocks = load_block_matn(
        blocks_path,
        sqlite_table=args.blocks_sqlite_table,
        sqlite_column=args.blocks_sqlite_column,
    )

    result = filter_with_tfidf(blocks, hadiths, sim_threshold=args.sim_threshold, top_k=args.top_k)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"✔ Blocks read     : {len(blocks)}")
    print(f"✔ Hadiths read    : {len(hadiths)}")
    print(f"✔ Blocks matched  : {result['meta']['matched_blocks']}")
    print(f"✔ Output written  : {args.out}")


if __name__ == "__main__":
    main()
