from __future__ import annotations

import argparse
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import duckdb
import pandas as pd

from Tafsir.pipeline.gemini_gui.blocks_to_xml_gui import (
    evaluate_guard,
    _normalize_guard_tokens,  # pylint: disable=protected-access
)


def _find_repo_root() -> Path:
    """Walk upwards to locate the project root (where run_active_as_module.py lives)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "run_active_as_module.py").exists():
            return parent
    # Fallback to the current layout (five levels up from this file).
    return Path(__file__).resolve().parents[5]


REPO_ROOT = _find_repo_root()


def _derive_paths(db_path: Path, table_name: str) -> Tuple[Path, str]:
    """Return source DB path and book name derived from annotated DB + table name."""
    book = table_name.replace("tafsir_analysis_", "")
    source_db = db_path.parent.parent / "tafsir_books" / f"{book}.sqlite3"
    return source_db, book


MATCH_THRESHOLD = 1.1


def _default_workers() -> int:
    # Use a small multiplier; evaluate_guard is Python-only and can thrash the GIL
    # if we spawn too many threads.
    cpu = os.cpu_count() or 4
    return min(32, cpu * 2)


def _load_frames(
    annotated_db: Path,
    source_db: Path,
    table_name: str,
    only_ids: Optional[Iterable[int]],
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    Load annotated and source tables into pandas DataFrames using DuckDB's sqlite_scanner
    for vectorized reads. Falls back to sqlite3 + pandas if the extension is unavailable.
    Returns (ann_df, src_df, backend_label).
    """
    only_ids_list: List[int] = sorted(set(only_ids)) if only_ids else []
    book = table_name.replace("tafsir_analysis_", "")

    def _build_where(alias: str) -> Tuple[str, Sequence[int]]:
        if not only_ids_list:
            return "", []
        placeholders = ",".join(["?"] * len(only_ids_list))
        return f"WHERE id IN ({placeholders})", only_ids_list

    where_clause, where_params = _build_where("ann")

    con = None
    try:
        con = duckdb.connect()
        con.execute("INSTALL 'sqlite_scanner';")
        con.execute("LOAD 'sqlite_scanner';")
        con.execute(f"ATTACH DATABASE '{source_db}' AS src (TYPE SQLITE);")
        con.execute(f"ATTACH DATABASE '{annotated_db}' AS ann (TYPE SQLITE);")

        ann_query = (
            f"SELECT rowid, id, extracted_text_full FROM ann.{table_name} {where_clause}"
        )
        src_query = f"SELECT id, text FROM src.{book}"

        ann_df = con.execute(ann_query, where_params).df()
        src_df = con.execute(src_query).df()
        backend = "duckdb_sqlite_scanner"
    except Exception:  # pragma: no cover - conservative fallback
        ann_conn = sqlite3.connect(annotated_db)
        src_conn = sqlite3.connect(source_db)
        ann_df = pd.read_sql_query(
            f"SELECT rowid, id, extracted_text_full FROM {table_name} {where_clause}",
            ann_conn,
            params=where_params,
        )
        src_df = pd.read_sql_query(
            f"SELECT id, text FROM {book}",
            src_conn,
        )
        ann_conn.close()
        src_conn.close()
        backend = "sqlite3_fallback"
    finally:
        try:
            con.close()
        except Exception:
            pass

    return ann_df, src_df, backend


def _tokenize(series: pd.Series) -> List[List[str]]:
    return [_normalize_guard_tokens(text) for text in series.fillna("")]


def _find_best_match_tokens(
    ann_tokens: List[str], source_tokens: Sequence[Tuple[int, List[str]]]
) -> Tuple[Optional[int], Dict[str, float]]:
    best_id: Optional[int] = None
    best_score = 0.0
    best_guard: Dict[str, float] = {"token_coverage": 0.0, "ngram_overlap": 0.0}

    if not ann_tokens:
        return None, best_guard

    for src_id, src_tokens in source_tokens:
        guard = evaluate_guard(src_tokens, ann_tokens, pre_normalized=True)
        score = guard.get("token_coverage", 0.0) + guard.get("ngram_overlap", 0.0)
        if score > best_score:
            best_score = score
            best_id = src_id
            best_guard = guard

    return (best_id if best_score > MATCH_THRESHOLD else None), best_guard


def reconcile(
    db_path: str,
    table_name: str,
    only_ids: Optional[set[int]] = None,
    *,
    max_workers: Optional[int] = None,
) -> List[int]:
    """
    Reconcile rows in-place by relinking to the best source id.
    Uses DuckDB for vectorized reads, pandas for manipulation, and multithreaded
    matching. If only_ids is provided, only those section IDs are considered.
    Returns IDs that could not be matched (or collided) and need regeneration.
    """
    annotated_db = Path(db_path)
    source_db, _ = _derive_paths(annotated_db, table_name)

    ann_df, src_df, _backend = _load_frames(
        annotated_db, source_db, table_name, only_ids
    )
    if ann_df.empty or src_df.empty:
        return []

    # Normalize and cache tokens to avoid repeated work inside threads.
    source_tokenized = list(
        zip(
            src_df["id"].astype(int).tolist(),
            _tokenize(src_df["text"]),
        )
    )

    ann_df["rowid"] = ann_df["rowid"].astype(int)
    ann_df["id"] = ann_df["id"].apply(lambda x: int(x) if pd.notna(x) else None)
    ann_df["tokens"] = _tokenize(ann_df["extracted_text_full"])

    id_usage: Dict[int, set[int]] = {}
    for rowid, existing_id in ann_df[["rowid", "id"]].itertuples(index=False):
        if existing_id is not None:
            id_usage.setdefault(existing_id, set()).add(rowid)

    work = [
        (row.rowid, row.id, row.tokens)
        for row in ann_df.itertuples(index=False)
    ]

    workers = max_workers or _default_workers()
    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(_find_best_match_tokens, tokens, source_tokenized): (rowid, old_id)
            for rowid, old_id, tokens in work
        }
        for future in as_completed(future_map):
            rowid, old_id = future_map[future]
            target_id, guard = future.result()
            results.append((rowid, old_id, target_id, guard))

    updates_rowid: List[Tuple[int, int]] = []  # (target_id, rowid)
    updates_by_old: Dict[int, int] = {}  # old_id -> target_id (deduped)
    block_updates: Dict[int, int] = {}  # old_id -> target_id
    unresolved: List[int] = []

    for rowid, old_id, target_id, guard in results:
        if target_id is None:
            unresolved.append(int(old_id) if old_id is not None else int(rowid))
            continue

        target_claimants = id_usage.get(target_id, set())
        if target_claimants and (old_id is None or target_id != old_id or (target_claimants - {rowid})):
            unresolved.append(int(old_id) if old_id is not None else int(rowid))
            continue

        if old_id is None:
            updates_rowid.append((target_id, rowid))
            id_usage.setdefault(target_id, set()).add(rowid)
            continue

        if target_id == old_id:
            continue

        updates_by_old[old_id] = target_id
        block_updates[old_id] = target_id
        # Update bookkeeping so later rows notice the reassignment.
        id_usage.setdefault(target_id, set()).update(id_usage.get(old_id, set()))
        id_usage.pop(old_id, None)

    if not updates_rowid and not updates_by_old:
        return unresolved

    with sqlite3.connect(annotated_db) as ann_conn:
        ann_conn.execute("PRAGMA journal_mode=WAL;")
        ann_conn.execute("PRAGMA synchronous = NORMAL;")
        if updates_rowid:
            ann_conn.executemany(
                f"UPDATE {table_name} SET id = ? WHERE rowid = ?",
                updates_rowid,
            )

        if updates_by_old:
            ann_conn.executemany(
                f"UPDATE {table_name} SET id = ? WHERE id = ?",
                [(new_id, old_id) for old_id, new_id in updates_by_old.items()],
            )

        if block_updates:
            ann_conn.executemany(
                f"UPDATE {table_name}_blocks SET tafsir_section_id = ? WHERE tafsir_section_id = ?",
                [(new_id, old_id) for old_id, new_id in block_updates.items()],
            )
        ann_conn.commit()

    return unresolved


def get_anomalies(
    db_path: str, table_name: str, only_ids: Optional[set[int]] = None
) -> List[int]:
    # Backward-compatible pipeline entrypoint: reconcile everything or a subset.
    return reconcile(db_path, table_name, only_ids=only_ids)


def reconcile_database(db: str, only_ids: Optional[set[int]] = None) -> List[int]:
    annotated_db = (
        REPO_ROOT / "Tafsir" / "tafsir_books_annotated" / f"{db}_annotated.sqlite3"
    )
    table_name = f"tafsir_analysis_{db}"
    return get_anomalies(str(annotated_db), table_name, only_ids=only_ids)


def main():
    parser = argparse.ArgumentParser(
        description="Reconcile mismatches and return unresolved identifiers."
    )
    parser.add_argument(
        "--db", default="katheer", help="Logical book name, e.g. katheer"
    )
    parser.add_argument(
        "--ids",
        help="Comma/space separated list of annotated IDs to reconcile; defaults to all.",
    )
    args = parser.parse_args()
    only_ids: Optional[set[int]] = None
    if args.ids:
        # support comma or whitespace separated
        raw_ids = args.ids.replace(",", " ").split()
        only_ids = {int(x) for x in raw_ids}

    unresolved = reconcile_database(args.db, only_ids=only_ids)
    print(f"Unresolved entries: {len(unresolved)}")
    if unresolved:
        print(unresolved)


if __name__ == "__main__":
    main()
