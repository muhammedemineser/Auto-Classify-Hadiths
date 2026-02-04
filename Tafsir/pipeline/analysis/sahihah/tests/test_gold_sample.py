from __future__ import annotations

import glob
import importlib
import os
import sys
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _reload(name: str):
    if name in sys.modules:
        del sys.modules[name]
    return importlib.import_module(name)


def _prepare_env(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    os.environ["CACHE_DIR"] = str(cache_dir)
    os.environ["DEBUG"] = "0"
    os.environ["PLOT_COVERAGE"] = "0"
    os.environ["MAX_WORKERS"] = "1"
    os.environ["CANDIDATE_PIPELINE"] = "bm25"
    os.environ["CANDIDATE_TOPK"] = "80"
    os.environ["CANDIDATE_MIN_TOPK"] = "25"
    os.environ["BM25_PREBUILD"] = "0"


def _db_glob_or_skip() -> str:
    db_glob = os.environ.get(
        "DB_GLOB",
        "/app/tools/ML/Data/normalized_hadith/Bukhari.db",
    )
    if not glob.glob(db_glob):
        pytest.skip(f"No DBs found for {db_glob}")
    return db_glob


def test_gold_sample_builds(tmp_path: Path):
    _prepare_env(tmp_path)
    db_glob = _db_glob_or_skip()
    os.environ["DB_GLOB"] = db_glob
    os.environ["EVAL_SAMPLE_SIZE"] = "5"

    sys.path.insert(0, "/app")
    pipeline = _reload("Tafsir.pipeline.analysis.sahihah.compare_txt_agains_db")
    builder = _reload("Tafsir.pipeline.analysis.sahihah.tools.tuning.build_gold_sample")

    db_paths = sorted(glob.glob(db_glob))
    sample = builder.build_gold_sample(
        db_paths=db_paths,
        size=5,
        cache_dir=Path(os.environ["CACHE_DIR"]),
        table=pipeline.DB_TABLE,
        id_col=pipeline.DB_ID_COL,
        text_col=pipeline.DB_COL,
    )
    out_path = Path(os.environ["CACHE_DIR"]) / "gold" / "gold_sample.jsonl"
    assert out_path.exists()
    assert len(sample) == 5

    seen_norms = set()
    for item in sample:
        assert item.query_norm == item.target_text_norm
        assert pipeline.normalize_to_str(item.query_raw) == item.query_norm
        assert item.query_norm not in seen_norms
        seen_norms.add(item.query_norm)


def test_pipeline_gold_sample_runs_fast(tmp_path: Path):
    _prepare_env(tmp_path)
    db_glob = _db_glob_or_skip()
    os.environ["DB_GLOB"] = db_glob
    os.environ["EVAL_SAMPLE_SIZE"] = "5"

    sys.path.insert(0, "/app")
    pipeline = _reload("Tafsir.pipeline.analysis.sahihah.compare_txt_agains_db")
    builder = _reload("Tafsir.pipeline.analysis.sahihah.tools.tuning.build_gold_sample")
    runner = _reload("Tafsir.pipeline.analysis.sahihah.tools.tuning.run_gold_sample")

    db_paths = sorted(glob.glob(db_glob))
    sample = builder.build_gold_sample(
        db_paths=db_paths,
        size=5,
        cache_dir=Path(os.environ["CACHE_DIR"]),
        table=pipeline.DB_TABLE,
        id_col=pipeline.DB_ID_COL,
        text_col=pipeline.DB_COL,
    )
    rows = [
        {
            "qid": s.qid,
            "query_raw": s.query_raw,
            "query_norm": s.query_norm,
            "db_path": s.db_path,
            "target_row_id": s.target_row_id,
            "target_text_norm": s.target_text_norm,
            "type": s.type,
        }
        for s in sample
    ]

    t0 = time.perf_counter()
    _, report = runner.run_gold_sample(sample_rows=rows)
    dt = time.perf_counter() - t0
    assert dt < 60.0
    assert report["stats"]["total"] == 5


def test_pipeline_gold_sample_rank1(tmp_path: Path):
    _prepare_env(tmp_path)
    db_glob = _db_glob_or_skip()
    os.environ["DB_GLOB"] = db_glob
    os.environ["EVAL_SAMPLE_SIZE"] = "5"

    sys.path.insert(0, "/app")
    pipeline = _reload("Tafsir.pipeline.analysis.sahihah.compare_txt_agains_db")
    builder = _reload("Tafsir.pipeline.analysis.sahihah.tools.tuning.build_gold_sample")
    runner = _reload("Tafsir.pipeline.analysis.sahihah.tools.tuning.run_gold_sample")

    db_paths = sorted(glob.glob(db_glob))
    sample = builder.build_gold_sample(
        db_paths=db_paths,
        size=5,
        cache_dir=Path(os.environ["CACHE_DIR"]),
        table=pipeline.DB_TABLE,
        id_col=pipeline.DB_ID_COL,
        text_col=pipeline.DB_COL,
    )
    rows = [
        {
            "qid": s.qid,
            "query_raw": s.query_raw,
            "query_norm": s.query_norm,
            "db_path": s.db_path,
            "target_row_id": s.target_row_id,
            "target_text_norm": s.target_text_norm,
            "type": s.type,
        }
        for s in sample
    ]

    results, _ = runner.run_gold_sample(sample_rows=rows)
    for res, row in zip(results, rows):
        matches = res.get("matches") or []
        assert matches, f"no matches for qid={row['qid']}"
        assert str(matches[0].get("hadith_number")) == str(row["target_row_id"])
