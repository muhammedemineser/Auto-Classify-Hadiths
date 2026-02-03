"""Database helpers for preflight and ingestion."""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def ensure_sqlite_writable(path: Path) -> None:
    """Create and drop a sentinel table to prove write access."""
    ensure_parent(path)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS _tafsir_gui_probe (id INTEGER)")
        conn.execute("DROP TABLE _tafsir_gui_probe")


def create_sqlite_engine(path: Path) -> Engine:
    ensure_parent(path)
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


def clone_sqlite(src: Path, dest: Path) -> Path:
    ensure_parent(dest)
    shutil.copy2(src, dest)
    return dest


@contextmanager
def temp_table(engine: Engine, ddl: str):
    """Create a temporary table defined by ddl and drop afterwards."""
    table_name = "_tafsir_gui_temp"
    with engine.begin() as conn:
        conn.execute(text(ddl.format(table=table_name)))
    try:
        yield table_name
    finally:
        with engine.begin() as conn:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))


def insert_rows(engine: Engine, table: str, rows: Iterable[Tuple[int, str]]) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(f"INSERT INTO {table} (id, text) VALUES (:id, :text)"),
            [{"id": rid, "text": txt} for rid, txt in rows],
        )


__all__ = [
    "ensure_sqlite_writable",
    "create_sqlite_engine",
    "clone_sqlite",
    "insert_rows",
    "temp_table",
]
