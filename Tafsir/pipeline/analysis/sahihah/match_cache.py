from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

try:
    import duckdb  # type: ignore
except Exception:  # pragma: no cover
    duckdb = None  # type: ignore

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None  # type: ignore


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


def _write_parquet(df, parquet_path: Path) -> None:
    if pd is not None:
        try:
            df.to_parquet(parquet_path, index=False)
            return
        except Exception:
            pass
    if duckdb is None:
        raise RuntimeError("duckdb is required to write parquet when pandas fails")
    con = duckdb.connect()
    try:
        con.register("df", df)
        con.execute(
            f"COPY df TO '{str(parquet_path)}' (FORMAT PARQUET)"
        )
    finally:
        try:
            con.close()
        except Exception:
            pass


def build_parquet_cache_if_missing(
    db_paths: Iterable[str],
    *,
    cache_dir: Optional[Path] = None,
    table: str,
    id_col: str,
    text_col: str,
    normalize_func: Callable[[Any], str],
) -> Tuple[Dict[str, Path], CacheStats]:
    if pd is None:
        raise RuntimeError("pandas is required to build parquet cache")

    cache_root = cache_dir or _default_cache_dir()
    _ensure_cache_dir(cache_root)

    stats = CacheStats()
    parquet_map: Dict[str, Path] = {}

    for db_path in db_paths:
        stats.total += 1
        parquet_path = parquet_path_for_db(db_path, cache_root)
        parquet_map[db_path] = parquet_path
        if parquet_path.exists():
            if pd is not None:
                try:
                    pd.read_parquet(
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
            df = pd.read_sql_query(
                f"SELECT {id_col} AS hadith_number_raw, {text_col} AS arabic_matn FROM {table}",
                conn,
            )
        finally:
            conn.close()

        if df.empty:
            _write_parquet(df, parquet_path)
            stats.built += 1
            continue

        df = df.dropna(subset=["arabic_matn"])
        df["arabic_matn"] = df["arabic_matn"].astype(str)
        df["hadith_number_raw"] = df["hadith_number_raw"].astype(str)

        df["hadith_number"] = pd.to_numeric(
            df["hadith_number_raw"], errors="coerce"
        )
        df["matn_norm"] = df["arabic_matn"].map(normalize_func)
        df["matn_norm"] = df["matn_norm"].fillna("").astype(str)
        df["token_count"] = df["matn_norm"].str.split().map(len)

        _write_parquet(df, parquet_path)
        stats.built += 1

    return parquet_map, stats


class ParquetReader:
    def __init__(self, parquet_map: Dict[str, Path], use_duckdb: bool = True):
        self.parquet_map = parquet_map
        self.use_duckdb = bool(use_duckdb and duckdb is not None)
        self._duck_con = duckdb.connect() if self.use_duckdb else None
        self._df_cache: Dict[str, "pd.DataFrame"] = {}

    def close(self) -> None:
        if self._duck_con is not None:
            try:
                self._duck_con.close()
            except Exception:
                pass
            self._duck_con = None
        self._df_cache.clear()

    def _load_df(self, db_path: str):
        if pd is None:
            raise RuntimeError("pandas is required for non-duckdb cache reads")
        cached = self._df_cache.get(db_path)
        if cached is not None:
            return cached
        parquet_path = self.parquet_map[db_path]
        df = pd.read_parquet(
            parquet_path,
            columns=["hadith_number", "hadith_number_raw", "arabic_matn", "matn_norm"],
        )
        self._df_cache[db_path] = df
        return df

    def fetch(
        self,
        db_path: str,
        anchors: List[str],
        *,
        require_all: bool,
        limit: int,
    ):
        parquet_path = self.parquet_map[db_path]
        if not anchors:
            where_sql = ""
            params: List[Any] = [limit]
        else:
            op = " AND " if require_all else " OR "
            conds = ["matn_norm LIKE ?"] * len(anchors)
            where_sql = "WHERE " + op.join(conds)
            params = [f"%{a}%" for a in anchors] + [limit]

        if self.use_duckdb:
            query = (
                "SELECT hadith_number, hadith_number_raw, arabic_matn, matn_norm "
                f"FROM parquet_scan('{str(parquet_path)}') {where_sql} LIMIT ?"
            )
            return self._duck_con.execute(query, params).df()

        df = self._load_df(db_path)
        if not anchors:
            return df.head(limit).copy()

        mask = None
        for anchor in anchors:
            m = df["matn_norm"].str.contains(anchor, regex=False, na=False)
            if mask is None:
                mask = m
            else:
                mask = (mask & m) if require_all else (mask | m)
        if mask is None:
            return df.head(limit).copy()
        return df[mask].head(limit).copy()
