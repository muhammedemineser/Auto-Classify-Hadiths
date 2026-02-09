from __future__ import annotations

import argparse
import glob
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import sys

sys.path.insert(0, "/app")
from Tafsir.pipeline.analysis.sahihah import compare_txt_agains_db as pipeline
from Tafsir.pipeline.analysis.sahihah import match_cache


@dataclass
class GoldSampleItem:
    qid: int
    query_raw: str
    query_norm: str
    db_path: str
    target_row_id: str
    target_text_norm: str
    type: str = "positive_exact"

    def to_json(self) -> str:
        return json.dumps(
            {
                "qid": self.qid,
                "query_raw": self.query_raw,
                "query_norm": self.query_norm,
                "db_path": self.db_path,
                "target_row_id": self.target_row_id,
                "target_text_norm": self.target_text_norm,
                "type": self.type,
            },
            ensure_ascii=False,
        )


def _iter_db_rows(
    db_path: str,
    *,
    table: str,
    id_col: str,
    text_col: str,
) -> Iterable[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f"SELECT {id_col}, {text_col} FROM {table}")
        for row in cur:
            yield row
    finally:
        conn.close()


def _parse_optional_int_env(name: str, default: Optional[int]) -> Optional[int]:
    """
    Parse an env var that may be an int or a sentinel for "no limit".

    - unset -> `default`
    - "", "none", "null" (case-insensitive) -> None
    - otherwise -> int(value)
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    s = str(raw).strip()
    if not s or s.lower() in {"none", "null"}:
        return None
    return int(s)


def build_gold_sample(
    *,
    db_paths: List[str],
    size: Optional[int],
    cache_dir: Path,
    table: str,
    id_col: str,
    text_col: str,
    verify_rank1: bool = True,
) -> List[GoldSampleItem]:
    if size is not None:
        size = max(1, int(size))
    counts: Dict[str, int] = {}
    info: Dict[str, tuple] = {}

    for db_path in db_paths:
        for row_id, text in _iter_db_rows(
            db_path, table=table, id_col=id_col, text_col=text_col
        ):
            if row_id is None or text is None:
                continue
            norm = pipeline.normalize_to_str(text)
            if not norm:
                continue
            cnt = counts.get(norm, 0) + 1
            counts[norm] = cnt
            if cnt == 1:
                info[norm] = (db_path, row_id, str(text))
            elif cnt == 2:
                info.pop(norm, None)

    candidates: List[GoldSampleItem] = []
    for norm, payload in info.items():
        db_path, row_id, raw_text = payload
        candidates.append(
            GoldSampleItem(
                qid=0,
                query_raw=raw_text,
                query_norm=norm,
                db_path=str(db_path),
                target_row_id=str(row_id),
                target_text_norm=norm,
            )
        )

    candidates.sort(key=lambda x: (x.db_path, x.target_row_id, x.query_norm))
    sample = candidates if size is None else candidates[:size]

    if verify_rank1 and candidates:
        p0 = pipeline.default_params()
        max_ngram_n = pipeline.max_ngram_n_for_params(p0)
        parquet_map, _ = match_cache.build_parquet_cache_if_missing(
            db_paths,
            cache_dir=cache_dir,
            table=table,
            id_col=id_col,
            text_col=text_col,
            normalize_func=pipeline.normalize_to_str,
            tokenize_func=pipeline.tokenize_words_from_text,
            max_ngram_n=max_ngram_n,
        )
        pipeline._worker_init(db_paths, parquet_map)
        params_dict = pipeline.params_to_dict(p0)
        verified: List[GoldSampleItem] = []
        for idx, item in enumerate(candidates, start=1):
            raw_line = f"{idx} {item.query_raw}"
            res = pipeline.match_one_hadith_all(raw_line, params_dict)
            matches = res.get("matches") or []
            if not matches:
                continue
            best = matches[0]
            if (
                str(best.get("hadith_number")) == str(item.target_row_id)
                and str(best.get("db_path")) == str(item.db_path)
            ):
                verified.append(item)
            if size is not None and len(verified) >= size:
                break
        sample = verified
    for i, item in enumerate(sample, start=1):
        item.qid = i

    out_dir = cache_dir / "gold"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "gold_sample.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for item in sample:
            f.write(item.to_json() + "\n")

    return sample


def main() -> None:
    parser = argparse.ArgumentParser(description="Build strict 1:1 gold sample")
    parser.add_argument("--size", type=int, default=None)
    parser.add_argument("--db-glob", type=str, default=None)
    parser.add_argument("--cache-dir", type=str, default=None)
    args = parser.parse_args()

    size = (
        args.size
        if args.size is not None
        # If EVAL_SAMPLE_SIZE is set to "None" in .env, treat it as "no limit".
        else _parse_optional_int_env("EVAL_SAMPLE_SIZE", None)
    )
    cache_dir = Path(args.cache_dir or os.environ.get("CACHE_DIR", str(pipeline.CACHE_DIR)))
    db_glob = args.db_glob or os.environ.get("DB_GLOB", pipeline.DB_GLOB)

    db_paths = sorted(glob.glob(db_glob))
    if not db_paths:
        raise FileNotFoundError(db_glob)

    sample = build_gold_sample(
        db_paths=db_paths,
        size=size,
        cache_dir=cache_dir,
        table=pipeline.DB_TABLE,
        id_col=pipeline.DB_ID_COL,
        text_col=pipeline.DB_COL,
    )

    print(f"gold_sample size={len(sample)} out={cache_dir / 'gold' / 'gold_sample.jsonl'}")


if __name__ == "__main__":
    main()
