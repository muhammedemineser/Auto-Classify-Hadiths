"""Lightweight file detection and sampling helpers."""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class FileCheck:
    ok: bool
    kind: str
    details: str
    sample: Optional[str] = None


def detect_kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".sqlite", ".sqlite3", ".db"}:
        return "sqlite"
    if suffix in {".csv"}:
        return "csv"
    if suffix in {".pdf"}:
        return "pdf"
    if suffix in {".txt", ".md", ".log"}:
        return "text"
    return "unknown"


def sample_pdf(path: Path, max_pages: int = 1) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "pypdf is required for PDF ingestion. Install via `pip install pypdf`."
        ) from exc

    reader = PdfReader(str(path))
    texts: List[str] = []
    for page in reader.pages[:max_pages]:
        try:
            texts.append(page.extract_text() or "")
        except Exception:
            continue
    return "\n".join(texts).strip()


def sample_csv(path: Path, max_rows: int = 3) -> str:
    lines: List[str] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            lines.append(",".join(row))
            if i + 1 >= max_rows:
                break
    return "\n".join(lines)


def sample_sqlite(path: Path, max_rows: int = 3) -> str:
    with sqlite3.connect(path) as conn:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [r[0] for r in cursor.fetchall()]
        if not tables:
            return "Empty SQLite database (no tables found)."
        table = tables[0]
        rows = conn.execute(f"SELECT * FROM {table} LIMIT {max_rows}").fetchall()
        return f"Tables: {tables}\nSample from {table}:\n{rows}"


def sample_text(path: Path, max_chars: int = 1200) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]


def validate_file(path: Path) -> FileCheck:
    if not path.exists():
        return FileCheck(False, "missing", f"File not found: {path}")
    if not path.is_file():
        return FileCheck(False, "invalid", f"Not a file: {path}")

    kind = detect_kind(path)
    try:
        if kind == "pdf":
            sample = sample_pdf(path)
            ok = bool(sample.strip())
            msg = "PDF parsed successfully." if ok else "PDF appears empty."
        elif kind == "csv":
            sample = sample_csv(path)
            ok = True
            msg = "CSV sample loaded."
        elif kind == "sqlite":
            sample = sample_sqlite(path)
            ok = True
            msg = "SQLite opened successfully."
        elif kind == "text":
            sample = sample_text(path)
            ok = True
            msg = "Text preview ready."
        else:
            sample = sample_text(path)
            ok = True
            msg = "Unknown type; treating as raw text."
        return FileCheck(ok, kind, msg, sample)
    except Exception as exc:
        return FileCheck(False, kind, f"Validation failed: {exc}")


__all__ = ["FileCheck", "validate_file", "detect_kind", "sample_text"]
