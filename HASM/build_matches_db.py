from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from scoring import ScoringParams, score_pair_with_params
from utils import StopWords, config, utils

BASE_DIR = Path(__file__).resolve().parent

NAME_TO_FILE = {
    "AbuDaud": "AbuDaud.db",
    "Bukhari": "Bukhari.db",
    "IbnMajah": "IbnMaja.db",
    "Muslim": "Muslim.db",
    "Nesai": "Nesai.db",
    "Tirmizi": "Tirmizi.db",
}

HADITHS_COLUMNS = [
    "Chapter_Number",
    "Section_Number",
    "Hadith_number",
    "English_Hadith",
    "English_Isnad",
    "English_Matn",
    "Arabic_Hadith",
    "Arabic_Isnad",
    "Arabic_Matn",
    "Arabic_Comment",
    "English_Grade",
    "Arabic_Grade",
    "section_id",
    "hadith_id",
    "normalized",
    "pos",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def load_txt_lines(hadith_txt: str) -> list[tuple[str, str, list[str]]]:
    lines: list[tuple[str, str, list[str]]] = []
    with open(hadith_txt, "r", encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue
            tid, text, kutub_raw = parts
            if not kutub_raw.startswith("KUTUBS="):
                continue
            try:
                kutubs = json.loads(kutub_raw.split("=", 1)[1])
            except json.JSONDecodeError:
                continue
            lines.append((tid, text, kutubs))
    return lines


def load_db_rows(db_file: str) -> tuple[list, list]:
    rows = utils.get_txt_from_db(current_db=db_file, config=config)
    conn = sqlite3.connect(str(Path(config.db_path) / db_file))
    try:
        full = conn.execute("SELECT * FROM hadiths").fetchall()
    finally:
        conn.close()
    return full, rows


def build_token_index(norm_list: list[str]) -> dict[str, list[int]]:
    idx: dict[str, list[int]] = defaultdict(list)
    for i, norm in enumerate(norm_list):
        if not norm:
            continue
        for tok in set(norm.split()):
            idx[tok].append(i)
    return idx


def main():
    parser = argparse.ArgumentParser(description="HASM matches -> sqlite3")
    parser.add_argument("-txt", "--hadith-txt", default=config.hadith_txt)
    parser.add_argument("-o", "--output", default=str(BASE_DIR / "Data" / "hasm_matches.db"))
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--top-n", type=int, default=40)
    parser.add_argument("--params-json", default=str(BASE_DIR / "tests" / "optimized_params.json"))
    args = parser.parse_args()

    config.hadith_txt = args.hadith_txt

    t_start = time.time()
    txt_lines = load_txt_lines(args.hadith_txt)
    log(f"txt-Zeilen: {len(txt_lines)}")

    cand_txt, cand_meta = utils.get_cand_txt()
    log(f"Kandidaten (unique): {len(cand_meta)} ({time.time()-t_start:.0f}s)")

    db_full: dict[str, list] = {}
    db_rows: dict[str, list] = {}
    corpus_docs: list[str] = []
    for name, db_file in NAME_TO_FILE.items():
        full, rows = load_db_rows(db_file)
        db_full[name] = full
        db_rows[name] = rows
        corpus_docs.extend(r[2] for r in rows if r and r[2])
        log(f"geladen {name}: {len(rows)} ({time.time()-t_start:.0f}s)")

    corpus_docs.extend(meta["normalized"] for meta in cand_meta.values())

    stop_words_info = StopWords.stop_words(corpus=corpus_docs)
    stop_words = set(stop_words_info.get("stop_words") or [])
    stop_word_weight = float(stop_words_info.get("stop_word_weight", 0.25))
    log(f"Stop words: {len(stop_words)} ({time.time()-t_start:.0f}s)")

    if args.params_json:
        with open(args.params_json, encoding="utf-8") as pf:
            pdata = json.load(pf)
        params = ScoringParams(**pdata["params"])
        if args.threshold is not None:
            params.threshold = args.threshold
    else:
        params = ScoringParams(threshold=args.threshold if args.threshold is not None else 0.5)
    log(f"Scoring-Parameter: {params.to_dict()}")

    db_index: dict[str, dict[str, list[int]]] = {}
    db_norm: dict[str, list[str]] = {}
    db_pos: dict[str, list[str]] = {}
    db_tokset: dict[str, list[set[str]]] = {}
    for name in NAME_TO_FILE:
        rows = db_rows[name]
        norm_list = [r[2] for r in rows]
        pos_list = [r[3] for r in rows]
        db_norm[name] = norm_list
        db_pos[name] = pos_list
        db_tokset[name] = [set(n.split()) if n else set() for n in norm_list]
        db_index[name] = build_token_index(norm_list)
    log(f"Indizes aufgebaut ({time.time()-t_start:.0f}s)")

    conn = sqlite3.connect(args.output)
    cur = conn.cursor()
    cols = HADITHS_COLUMNS + ["albani", "source", "txt_id", "score"]
    cur.execute(
        "CREATE TABLE IF NOT EXISTS hadiths ("
        + ", ".join(f'"{c}" TEXT' for c in cols)
        + ")"
    )
    conn.commit()

    n_matches = 0
    n_by_db: dict[str, int] = defaultdict(int)
    n_lines_with_match = 0
    t_loop = time.time()

    for li, (tid, text, kutubs) in enumerate(txt_lines):
        meta = cand_meta.get(text)
        if meta is not None:
            cand_norm = meta["normalized"]
            cand_pos = meta["pos"]
        else:
            cand_norm = utils.norm(text)
            cand_pos = json.dumps(
                utils.tag_pos_tokens(cand_norm.split()), ensure_ascii=False
            )

        if not cand_norm.strip():
            continue

        cand_tokens = cand_norm.split()
        cand_tokset = set(cand_tokens)

        best_overall = None
        for k in kutubs:
            name = k if k in NAME_TO_FILE else k
            if name not in db_rows:
                continue
            full = db_full[name]
            norm_list = db_norm[name]
            pos_list = db_pos[name]
            tokset_list = db_tokset[name]
            idx = db_index[name]

            # Cheap prefilter: candidate rows sharing >=2 tokens with overlap ratio
            counts: dict[int, int] = defaultdict(int)
            for tok in cand_tokset:
                for pos in idx.get(tok, []):
                    counts[pos] += 1
            if not counts:
                continue
            # rank by shared-token count, keep top-n
            ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[: args.top_n]

            cand = []
            for pos_i, cnt in ranked:
                ref_norm = norm_list[pos_i]
                if not ref_norm:
                    continue
                # quick guard: candidate tokens must be largely present in ref
                inter = len(cand_tokset & tokset_list[pos_i])
                if inter < max(2, int(len(cand_tokset) * 0.4)):
                    continue
                ref_pos = pos_list[pos_i]
                s, _ = score_pair_with_params(
                    cand_norm, cand_pos, ref_norm, ref_pos,
                    stop_words, stop_word_weight, params,
                )
                cand.append((s, pos_i))
            if not cand:
                continue
            cand.sort(reverse=True, key=lambda x: x[0])
            best_score, best_pos = cand[0]
            if best_score >= params.threshold:
                row = full[best_pos]
                row_dict = {col: row[i] for i, col in enumerate(HADITHS_COLUMNS)}
                values = [row_dict[c] for c in HADITHS_COLUMNS] + [
                    text,
                    NAME_TO_FILE[name],
                    tid,
                    round(float(best_score), 4),
                ]
                cur.execute(
                    "INSERT INTO hadiths ("
                    + ", ".join(f'"{c}"' for c in cols)
                    + ") VALUES ("
                    + ", ".join("?" for _ in cols)
                    + ")",
                    values,
                )
                n_matches += 1
                n_by_db[name] += 1
                if best_overall is None or best_score > best_overall[0]:
                    best_overall = (best_score, name)
        if best_overall is not None:
            n_lines_with_match += 1

        if (li + 1) % 100 == 0:
            log(f"  [{li+1}/{len(txt_lines)}] matches={n_matches} ({time.time()-t_loop:.0f}s)")
            t_loop = time.time()
            conn.commit()

    conn.commit()
    conn.close()

    log(f"Matches gesamt: {n_matches}")
    log(f"Zeilen mit >=1 Match: {n_lines_with_match} / {len(txt_lines)}")
    for name in NAME_TO_FILE:
        if n_by_db[name]:
            log(f"  {name}: {n_by_db[name]}")
    log(f"Output: {args.output} ({time.time()-t_start:.0f}s)")


if __name__ == "__main__":
    main()