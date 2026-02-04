from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys

sys.path.insert(0, "/app")
from Tafsir.pipeline.analysis.sahihah import compare_txt_agains_db as pipeline
from Tafsir.pipeline.analysis.sahihah import match_cache


@dataclass
class RunStats:
    timings: List[float]
    candidate_counts: List[int]
    fallback_counts: List[int]
    rank1_hits: int
    total: int

    def to_report(self) -> Dict[str, Any]:
        timings_sorted = sorted(self.timings)
        return {
            "total": self.total,
            "rank1_hits": self.rank1_hits,
            "rank1_rate": self.rank1_hits / float(self.total) if self.total else 0.0,
            "timings": {
                "p50": _percentile(timings_sorted, 50),
                "p95": _percentile(timings_sorted, 95),
                "max": timings_sorted[-1] if timings_sorted else 0.0,
                "avg": sum(self.timings) / float(len(self.timings)) if self.timings else 0.0,
            },
            "candidates": {
                "avg": sum(self.candidate_counts) / float(len(self.candidate_counts)) if self.candidate_counts else 0.0,
                "max": max(self.candidate_counts) if self.candidate_counts else 0,
            },
            "fallback": {
                "avg": sum(self.fallback_counts) / float(len(self.fallback_counts)) if self.fallback_counts else 0.0,
                "rate": sum(1 for x in self.fallback_counts if x > 0) / float(len(self.fallback_counts)) if self.fallback_counts else 0.0,
            },
        }


def _percentile(sorted_vals: List[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if pct <= 0:
        return sorted_vals[0]
    if pct >= 100:
        return sorted_vals[-1]
    k = (len(sorted_vals) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    d0 = sorted_vals[f] * (c - k)
    d1 = sorted_vals[c] * (k - f)
    return d0 + d1


def _snapshot_process_stats() -> Dict[str, Any]:
    pid = os.getpid()
    try:
        out = subprocess.check_output(
            ["ps", "-o", "pid,pcpu,pmem,cmd", "-p", str(pid)],
            text=True,
        )
        return {"ps": out.strip()}
    except Exception:
        return {}


def _load_gold_sample(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _prepare_cache(db_paths: List[str]) -> Dict[str, Path]:
    p0 = pipeline.default_params()
    max_ngram_n = pipeline.max_ngram_n_for_params(p0)
    parquet_map, _ = match_cache.build_parquet_cache_if_missing(
        db_paths,
        cache_dir=pipeline.CACHE_DIR,
        table=pipeline.DB_TABLE,
        id_col=pipeline.DB_ID_COL,
        text_col=pipeline.DB_COL,
        normalize_func=pipeline.normalize_to_str,
        tokenize_func=pipeline.tokenize_words_from_text,
        max_ngram_n=max_ngram_n,
    )
    return parquet_map


def run_gold_sample(
    *,
    sample_rows: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not sample_rows:
        return [], {}

    proc_start = _snapshot_process_stats()
    db_paths = sorted({row["db_path"] for row in sample_rows})
    parquet_map = _prepare_cache(db_paths)
    pipeline._worker_init(db_paths, parquet_map)

    params_dict = pipeline.params_to_dict(pipeline.default_params())

    timings: List[float] = []
    candidate_counts: List[int] = []
    fallback_counts: List[int] = []
    rank1_hits = 0
    results = []

    for row in sample_rows:
        qid = int(row["qid"])
        raw = row["query_raw"]
        db_stem = Path(row["db_path"]).stem
        raw_line = f"{qid} {raw}\tKUTUBS={json.dumps([db_stem])}"
        t0 = time.perf_counter()
        res = pipeline.match_one_hadith_all(raw_line, params_dict)
        dt = time.perf_counter() - t0
        timings.append(dt)
        perf = res.get("_perf") or {}
        candidate_counts.append(int(perf.get("cand_dedup") or 0))
        fallback_counts.append(int(perf.get("cand_fallback") or 0))
        results.append(res)

        matches = res.get("matches") or []
        if matches:
            best = matches[0]
            if str(best.get("hadith_number")) == str(row["target_row_id"]):
                rank1_hits += 1

    stats = RunStats(
        timings=timings,
        candidate_counts=candidate_counts,
        fallback_counts=fallback_counts,
        rank1_hits=rank1_hits,
        total=len(sample_rows),
    )
    report = {
        "pipeline": os.environ.get("CANDIDATE_PIPELINE", ""),
        "candidate_topk": pipeline.CANDIDATE_TOPK,
        "candidate_min_topk": pipeline.CANDIDATE_MIN_TOPK,
        "max_fallback_cands": pipeline.MAX_FALLBACK_CANDS,
        "stats": stats.to_report(),
        "process": {
            "start": proc_start,
            "end": _snapshot_process_stats(),
        },
    }

    return results, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run gold sample through pipeline")
    parser.add_argument("--sample", type=str, default=None)
    parser.add_argument("--report", type=str, default=None)
    parser.add_argument("--db-glob", type=str, default=None)
    args = parser.parse_args()

    cache_dir = Path(os.environ.get("CACHE_DIR", str(pipeline.CACHE_DIR)))
    sample_path = Path(args.sample) if args.sample else cache_dir / "gold" / "gold_sample.jsonl"
    if not sample_path.exists():
        raise FileNotFoundError(str(sample_path))

    if args.db_glob:
        os.environ["DB_GLOB"] = args.db_glob

    rows = _load_gold_sample(sample_path)
    _, report = run_gold_sample(sample_rows=rows)

    report_path = Path(args.report) if args.report else cache_dir / "gold" / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"report written: {report_path}")


if __name__ == "__main__":
    main()
