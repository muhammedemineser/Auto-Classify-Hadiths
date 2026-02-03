from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger

from Tafsir.config import paths as cfg
from Tafsir.pipeline.gemini_api import blocks_to_xml_api
from Tafsir.pipeline.analysis.data_cleaning.rollback_pipeline import (
    TafsirRollbackPipeline,
)

from ..utils import db as db_utils
from ..utils import file_detect


@contextmanager
def override_paths(source_dir: Path, annotated_dir: Path):
    """Temporarily override cfg paths so pipeline writes to user-provided dirs."""
    original_source = cfg.BOOKS_DIR
    original_ann = cfg.ANNOTATED_DIR
    cfg.BOOKS_DIR = source_dir
    cfg.ANNOTATED_DIR = annotated_dir
    try:
        yield
    finally:
        cfg.BOOKS_DIR = original_source
        cfg.ANNOTATED_DIR = original_ann


def _rows_from_pdf(path: Path) -> List[tuple[int, str]]:
    text = file_detect.sample_pdf(path, max_pages=50)
    chunks = [t.strip() for t in text.split("\n\n") if t.strip()]
    return list(enumerate(chunks, start=1))


def _rows_from_csv(path: Path) -> List[tuple[int, str]]:
    import csv

    rows: List[tuple[int, str]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        if "text" in reader.fieldnames or "content" in reader.fieldnames:
            key = "text" if "text" in reader.fieldnames else "content"
            for i, row in enumerate(reader, start=1):
                rows.append((i, row.get(key, "")))
        else:
            f.seek(0)
            reader_plain = csv.reader(f)
            for i, row in enumerate(reader_plain, start=1):
                rows.append((i, " ".join(row)))
    return rows


def ingest_input_file(path: Path, logical_name: str, source_dir: Path) -> Path:
    """Normalize supported input file types into a SQLite DB the pipeline expects."""
    kind = file_detect.detect_kind(path)
    db_path = source_dir / f"{logical_name}.sqlite3"
    if kind == "sqlite":
        return db_utils.clone_sqlite(path, db_path)

    rows: List[tuple[int, str]]
    if kind == "pdf":
        rows = _rows_from_pdf(path)
    elif kind == "csv":
        rows = _rows_from_csv(path)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")
        rows = list(enumerate(text.splitlines(), start=1))

    engine = db_utils.create_sqlite_engine(db_path)
    ddl = f"CREATE TABLE IF NOT EXISTS {logical_name} (id INTEGER PRIMARY KEY, text TEXT);"
    with engine.begin() as conn:
        conn.execute(ddl)
    db_utils.insert_rows(engine, logical_name, rows)
    return db_path


def run_main_pipeline(
    *,
    logical_name: str,
    source_dir: Path,
    annotated_dir: Path,
    start_id: Optional[int] = None,
    exact_ids: Optional[List[int]] = None,
    repair: bool = False,
) -> None:
    # Propagate env values to the API module globals so calls reflect UI config.
    if "GEMINI_API_KEY" in os.environ:
        blocks_to_xml_api._GEMINI_CLIENT = None  # reset client cache
    if "GEMINI_CACHE_NAME" in os.environ:
        blocks_to_xml_api.GEMINI_CACHE_NAME = os.getenv("GEMINI_CACHE_NAME")
    if "GEMINI_MODEL_ID" in os.environ:
        blocks_to_xml_api.MODEL_ID = os.getenv("GEMINI_MODEL_ID")

    source_dir.mkdir(parents=True, exist_ok=True)
    annotated_dir.mkdir(parents=True, exist_ok=True)
    with override_paths(source_dir, annotated_dir):
        logger.info("Starting automate_gemini for {}", logical_name)
        blocks_to_xml_api.automate_gemini(
            logical_name, start_id=start_id, exact_ids=exact_ids, repair=repair
        )


def run_rollback(
    *,
    book: str,
    base_path: Path,
    ids: Optional[List[int]] = None,
    jsonl: Optional[Path] = None,
) -> None:
    pipe = TafsirRollbackPipeline(book=book, base_path=base_path)
    if jsonl:
        pipe.load_from_jsonl(jsonl)
        pipe.process_with_gemini()
        return
    if ids:
        pipe.classify_ids(ids)
        pipe.process_with_gemini()
        return
    pipe.run_pipeline()


def sample_source_row(db_path: Path, table: str) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(f"SELECT text FROM {table} WHERE text IS NOT NULL LIMIT 1").fetchone()
        return row[0] if row else ""


__all__ = [
    "ingest_input_file",
    "run_main_pipeline",
    "run_rollback",
    "sample_source_row",
    "override_paths",
]
