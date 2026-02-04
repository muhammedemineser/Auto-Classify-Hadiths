from __future__ import annotations

import bisect
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


def _make_ngrams(tokens: List[str], n: int) -> List[str]:
    if n <= 0 or len(tokens) < n:
        return []
    return [" ".join(tokens[i : i + n]) for i in range(0, len(tokens) - n + 1)]


def _build_parquet_table(
    conn: sqlite3.Connection,
    table_name: str,
    id_col: str,
    text_col: str,
    normalize_func: Callable[[Any], str],
    *,
    tokenize_func: Optional[Callable[[Any], List[str]]] = None,
    max_ngram_n: Optional[int] = None,
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
    tokens_norm: List[List[str]] = []
    ngram_columns: Dict[int, List[List[str]]] = {}
    max_ngram_n = int(max_ngram_n or 0)
    if max_ngram_n > 0:
        for n in range(1, max_ngram_n + 1):
            ngram_columns[n] = []

    for raw_id, raw_text in cursor:
        if raw_text is None:
            continue
        text = str(raw_text)
        norm_value = normalize_func(text)
        norm = "" if norm_value is None else str(norm_value)
        if tokenize_func is not None:
            tokens = tokenize_func(text)
        else:
            tokens = norm.split()
        hadith_number_raw.append(str(raw_id))
        arabic_matn.append(text)
        hadith_number.append(_coerce_to_float(raw_id))
        matn_norm.append(norm)
        token_count.append(len(tokens))
        tokens_norm.append(tokens)
        if max_ngram_n > 0:
            for n in range(1, max_ngram_n + 1):
                ngram_columns[n].append(_make_ngrams(tokens, n))

    fields = [
        pa.field("hadith_number_raw", pa.string()),
        pa.field("arabic_matn", pa.string()),
        pa.field("hadith_number", pa.float64()),
        pa.field("matn_norm", pa.string()),
        pa.field("token_count", pa.int32()),
        pa.field("tokens_norm", pa.list_(pa.string())),
    ]
    if max_ngram_n > 0:
        for n in range(1, max_ngram_n + 1):
            fields.append(pa.field(f"ngrams_{n}", pa.list_(pa.string())))
    schema = pa.schema(fields)

    arrays: List[pa.Array] = [
        pa.array(hadith_number_raw, type=pa.string()),
        pa.array(arabic_matn, type=pa.string()),
        pa.array(hadith_number, type=pa.float64()),
        pa.array(matn_norm, type=pa.string()),
        pa.array(token_count, type=pa.int32()),
        pa.array(tokens_norm, type=pa.list_(pa.string())),
    ]
    if max_ngram_n > 0:
        for n in range(1, max_ngram_n + 1):
            arrays.append(pa.array(ngram_columns[n], type=pa.list_(pa.string())))
    return pa.Table.from_arrays(arrays, schema=schema)


def build_parquet_cache_if_missing(
    db_paths: Iterable[str],
    *,
    cache_dir: Optional[Path] = None,
    table: str,
    id_col: str,
    text_col: str,
    normalize_func: Callable[[Any], str],
    tokenize_func: Optional[Callable[[Any], List[str]]] = None,
    max_ngram_n: Optional[int] = None,
) -> Tuple[Dict[str, Path], CacheStats]:
    cache_root = cache_dir or _default_cache_dir()
    _ensure_cache_dir(cache_root)

    stats = CacheStats()
    parquet_map: Dict[str, Path] = {}

    for db_path in db_paths:
        stats.total += 1
        parquet_path = parquet_path_for_db(db_path, cache_root)
        parquet_map[db_path] = parquet_path

        required_columns = [
            "hadith_number",
            "hadith_number_raw",
            "arabic_matn",
            "matn_norm",
            "token_count",
            "tokens_norm",
        ]
        max_ngram_n = int(max_ngram_n or 0)
        if max_ngram_n > 0:
            for n in range(1, max_ngram_n + 1):
                required_columns.append(f"ngrams_{n}")

        if parquet_path.exists():
            try:
                pq.read_table(
                    parquet_path,
                    columns=required_columns,
                )
                stats.hit += 1
                continue
            except Exception:
                pass

        conn = sqlite3.connect(db_path)
        try:
            table_data = _build_parquet_table(
                conn,
                table,
                id_col,
                text_col,
                normalize_func,
                tokenize_func=tokenize_func,
                max_ngram_n=max_ngram_n,
            )
        finally:
            conn.close()

        _write_parquet(table_data, parquet_path)
        stats.built += 1

    return parquet_map, stats


ROW_IDX_COL = "_row_idx"


class ParquetReader:
    _BASE_COLUMNS = [
        "hadith_number",
        "hadith_number_raw",
        "arabic_matn",
        "matn_norm",
        "token_count",
    ]

    _BASE_SCHEMA = pa.schema(
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
        self._pf_cache: Dict[str, pq.ParquetFile] = {}
        self._row_group_offsets: Dict[str, List[Tuple[int, int, int]]] = {}
        self._row_counts: Dict[str, int] = {}

    def close(self) -> None:
        self._dataset_cache.clear()
        self._pf_cache.clear()
        self._row_group_offsets.clear()
        self._row_counts.clear()

    def fetch(
        self,
        db_path: str,
        anchors: List[str],
        *,
        require_all: bool,
        limit: int,
        extra_columns: Optional[List[str]] = None,
    ) -> pa.Table:
        if limit <= 0:
            return self._empty_table(extra_columns)
        dataset = self._dataset_for_db(db_path)
        columns = list(self._BASE_COLUMNS)
        if extra_columns:
            columns.extend([c for c in extra_columns if c not in columns])
        scanner = dataset.scanner(columns=columns, use_threads=True)
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
            return self._empty_table(extra_columns)

        return pa.concat_tables(batches)

    def _dataset_for_db(self, db_path: str) -> ds.Dataset:
        dataset = self._dataset_cache.get(db_path)
        if dataset is None:
            dataset = ds.dataset(str(self.parquet_map[db_path]), format="parquet")
            self._dataset_cache[db_path] = dataset
        return dataset

    def _parquet_file_for_db(self, db_path: str) -> pq.ParquetFile:
        pf = self._pf_cache.get(db_path)
        if pf is None:
            pf = pq.ParquetFile(str(self.parquet_map[db_path]))
            self._pf_cache[db_path] = pf
        return pf

    def _row_group_offsets_for_db(self, db_path: str) -> List[Tuple[int, int, int]]:
        offsets = self._row_group_offsets.get(db_path)
        if offsets is not None:
            return offsets
        pf = self._parquet_file_for_db(db_path)
        offsets = []
        offset = 0
        for rg in range(pf.num_row_groups):
            count = pf.metadata.row_group(rg).num_rows
            offsets.append((offset, offset + count, rg))
            offset += count
        self._row_group_offsets[db_path] = offsets
        self._row_counts[db_path] = offset
        return offsets

    def _row_count_for_db(self, db_path: str) -> int:
        count = self._row_counts.get(db_path)
        if count is not None:
            return count
        offsets = self._row_group_offsets_for_db(db_path)
        if not offsets:
            return 0
        return offsets[-1][1]

    def _empty_table(self, extra_columns: Optional[List[str]] = None) -> pa.Table:
        fields = list(self._BASE_SCHEMA)
        arrays: List[pa.Array] = [
            pa.array([], type=pa.float64()),
            pa.array([], type=pa.string()),
            pa.array([], type=pa.string()),
            pa.array([], type=pa.string()),
            pa.array([], type=pa.int32()),
        ]
        if extra_columns:
            for col in extra_columns:
                if col in self._BASE_COLUMNS:
                    continue
                if col == "tokens_norm" or col.startswith("ngrams_"):
                    fields.append(pa.field(col, pa.list_(pa.string())))
                    arrays.append(pa.array([], type=pa.list_(pa.string())))
                else:
                    fields.append(pa.field(col, pa.string()))
                    arrays.append(pa.array([], type=pa.string()))
        schema = pa.schema(fields)
        return pa.Table.from_arrays(arrays, schema=schema)

    def fetch_rows_by_index(
        self,
        db_path: str,
        indices: List[int],
        *,
        extra_columns: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if not indices:
            return []
        ordered: List[int] = []
        seen = set()
        for idx in indices:
            if idx is None:
                continue
            try:
                idx_int = int(idx)
            except (TypeError, ValueError):
                continue
            if idx_int < 0 or idx_int in seen:
                continue
            seen.add(idx_int)
            ordered.append(idx_int)
        if not ordered:
            return []
        total_rows = self._row_count_for_db(db_path)
        ordered = [i for i in ordered if i < total_rows]
        if not ordered:
            return []
        sorted_indices = sorted(ordered)
        table = self._read_rows_by_sorted_indices(
            db_path, sorted_indices, extra_columns=extra_columns
        )
        rows = table.to_pylist()
        row_map = {r.get(ROW_IDX_COL): r for r in rows}
        return [row_map[i] for i in ordered if i in row_map]

    def _read_rows_by_sorted_indices(
        self,
        db_path: str,
        sorted_indices: List[int],
        *,
        extra_columns: Optional[List[str]] = None,
    ) -> pa.Table:
        if not sorted_indices:
            return self._empty_table(extra_columns)
        pf = self._parquet_file_for_db(db_path)
        columns = list(self._BASE_COLUMNS)
        if extra_columns:
            columns.extend([c for c in extra_columns if c not in columns])
        offsets = self._row_group_offsets_for_db(db_path)
        tables: List[pa.Table] = []
        for start, end, rg in offsets:
            if sorted_indices[0] >= end:
                continue
            if sorted_indices[-1] < start:
                break
            lo = bisect.bisect_left(sorted_indices, start)
            hi = bisect.bisect_left(sorted_indices, end, lo)
            if lo >= hi:
                continue
            local = [idx - start for idx in sorted_indices[lo:hi]]
            rg_table = pf.read_row_group(rg, columns=columns)
            sel = rg_table.take(pa.array(local, type=pa.int64()))
            row_idx = pa.array([start + i for i in local], type=pa.int64())
            sel = sel.append_column(ROW_IDX_COL, row_idx)
            tables.append(sel)
        if not tables:
            return self._empty_table(extra_columns)
        return pa.concat_tables(tables)

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
