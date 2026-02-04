from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq


@dataclass
class CacheStats:
    total: int = 0
    hit: int = 0
    built: int = 0


def _default_cache_dir() -> Path:
    return Path(os.environ.get("CACHE_DIR", "/app/tools/sahihah/cache"))


def parquet_path_for_db(db_path: str, cache_dir: Optional[Path] = None) -> Path:
    cache_root = cache_dir or _default_cache_dir()
    return cache_root / f"{Path(db_path).stem}.parquet"


def _ensure_cache_dir(cache_dir: Path) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)


def _write_parquet(table: pa.Table, parquet_path: Path) -> None:
    pq.write_table(table, parquet_path)


def _coerce_to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_parquet_table(
    conn: sqlite3.Connection,
    table_name: str,
    id_col: str,
    text_col: str,
    normalize_func: Callable[[Any], str],
) -> pa.Table:
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT {id_col} AS hadith_number_raw, {text_col} AS arabic_matn FROM {table_name}"
    )

    hadith_number_raw: List[str] = []
    arabic_matn: List[str] = []
    hadith_number: List[Optional[float]] = []
    matn_norm: List[str] = []
    token_count: List[int] = []

    for raw_id, raw_text in cursor:
        if raw_text is None:
            continue
        text = str(raw_text)
        norm_value = normalize_func(text)
        norm = "" if norm_value is None else str(norm_value)
        hadith_number_raw.append(str(raw_id))
        arabic_matn.append(text)
        hadith_number.append(_coerce_to_float(raw_id))
        matn_norm.append(norm)
        token_count.append(len(norm.split()))

    schema = pa.schema(
        [
            pa.field("hadith_number_raw", pa.string()),
            pa.field("arabic_matn", pa.string()),
            pa.field("hadith_number", pa.float64()),
            pa.field("matn_norm", pa.string()),
            pa.field("token_count", pa.int32()),
        ]
    )

    return pa.Table.from_arrays(
        [
            pa.array(hadith_number_raw, type=pa.string()),
            pa.array(arabic_matn, type=pa.string()),
            pa.array(hadith_number, type=pa.float64()),
            pa.array(matn_norm, type=pa.string()),
            pa.array(token_count, type=pa.int32()),
        ],
        schema=schema,
    )


def build_parquet_cache_if_missing(
    db_paths: Iterable[str],
    *,
    cache_dir: Optional[Path] = None,
    table: str,
    id_col: str,
    text_col: str,
    normalize_func: Callable[[Any], str],
) -> Tuple[Dict[str, Path], CacheStats]:
    cache_root = cache_dir or _default_cache_dir()
    _ensure_cache_dir(cache_root)

    stats = CacheStats()
    parquet_map: Dict[str, Path] = {}

    for db_path in db_paths:
        stats.total += 1
        parquet_path = parquet_path_for_db(db_path, cache_root)
        parquet_map[db_path] = parquet_path

        if parquet_path.exists():
            try:
                pq.read_table(
                    parquet_path,
                    columns=[
                        "hadith_number",
                        "hadith_number_raw",
                        "arabic_matn",
                        "matn_norm",
                        "token_count",
                    ],
                )
                stats.hit += 1
                continue
            except Exception:
                pass

        conn = sqlite3.connect(db_path)
        try:
            table_data = _build_parquet_table(
                conn, table, id_col, text_col, normalize_func
            )
        finally:
            conn.close()

        _write_parquet(table_data, parquet_path)
        stats.built += 1

    return parquet_map, stats


class ParquetReader:
    _SCAN_COLUMNS = [
        "hadith_number",
        "hadith_number_raw",
        "arabic_matn",
        "matn_norm",
        "token_count",
    ]

    _EMPTY_SCHEMA = pa.schema(
        [
            pa.field("hadith_number", pa.float64()),
            pa.field("hadith_number_raw", pa.string()),
            pa.field("arabic_matn", pa.string()),
            pa.field("matn_norm", pa.string()),
            pa.field("token_count", pa.int32()),
        ]
    )

    def __init__(self, parquet_map: Dict[str, Path], use_duckdb: bool = True):
        self.parquet_map = parquet_map
        self._dataset_cache: Dict[str, ds.Dataset] = {}

    def close(self) -> None:
        self._dataset_cache.clear()

    def fetch(
        self,
        db_path: str,
        anchors: List[str],
        *,
        require_all: bool,
        limit: int,
    ) -> pa.Table:
        if limit <= 0:
            return self._empty_table()
        dataset = self._dataset_for_db(db_path)
        scanner = dataset.scanner(columns=self._SCAN_COLUMNS, use_threads=True)
        batches: List[pa.Table] = []
        total = 0

        for record_batch in scanner.to_batches():
            if total >= limit:
                break
            batch_table = pa.Table.from_batches([record_batch])
            filtered = self._filter_table(batch_table, anchors, require_all)
            if filtered.num_rows == 0:
                continue

            remaining = limit - total
            if filtered.num_rows > remaining:
                filtered = filtered.slice(0, remaining)

            batches.append(filtered)
            total += filtered.num_rows

        if not batches:
            return self._empty_table()

        return pa.concat_tables(batches)

    def _dataset_for_db(self, db_path: str) -> ds.Dataset:
        dataset = self._dataset_cache.get(db_path)
        if dataset is None:
            dataset = ds.dataset(str(self.parquet_map[db_path]), format="parquet")
            self._dataset_cache[db_path] = dataset
        return dataset

    def _empty_table(self) -> pa.Table:
        return pa.Table.from_arrays(
            [
                pa.array([], type=pa.float64()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.string()),
                pa.array([], type=pa.int32()),
            ],
            schema=self._EMPTY_SCHEMA,
        )

    def _filter_table(
        self, table: pa.Table, anchors: List[str], require_all: bool
    ) -> pa.Table:
        if not anchors:
            return table
        mask = None
        for anchor in anchors:
            if not anchor:
                continue
            contains = pc.match_substring(table["matn_norm"], anchor)
            if mask is None:
                mask = contains
            else:
                mask = pc.and_(mask, contains) if require_all else pc.or_(mask, contains)

        if mask is None:
            return table

        return table.filter(mask)
