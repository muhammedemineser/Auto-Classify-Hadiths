from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import List, Optional, Tuple

from Tafsir.pipeline.gemini_gui.blocks_to_xml_gui import evaluate_guard  # type: ignore


def _find_repo_root() -> Path:
    """Walk upwards to locate the project root (where run_active_as_module.py lives)."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "run_active_as_module.py").exists():
            return parent
    # Fallback to the current layout (five levels up from this file).
    return Path(__file__).resolve().parents[5]


REPO_ROOT = _find_repo_root()


def _derive_paths(db_path: Path, table_name: str) -> Tuple[Path, str]:
    """Resolve source DB path from annotated DB path + table name."""
    book = table_name.replace("tafsir_analysis_", "")
    source_db = db_path.parent.parent / "tafsir_books" / f"{book}.sqlite3"
    return source_db, book


def _find_best_match(
    ann_text: str | None, source_tuples: List[Tuple[int, str]]
) -> Optional[int]:
    best_id, best_score = None, 0.0
    if not ann_text:
        return None

    for src_id, src_text in source_tuples:
        guard = evaluate_guard(src_text, ann_text)
        score = guard.get("token_coverage", 0.0) + guard.get("ngram_overlap", 0.0)
        if score > best_score:
            best_score = score
            best_id = src_id

    return best_id if best_score > 1.1 else None


def get_anomalies(db_path: str, table_name: str) -> List[int]:
    """
    Patch rows where id IS NULL in-place.
    Returns rowids that could not be matched (Gemini fallback).
    """
    annotated_db = Path(db_path)
    source_db, book = _derive_paths(annotated_db, table_name)

    with sqlite3.connect(source_db) as src_conn:
        source_tuples = src_conn.execute(f"SELECT id, text FROM {book}").fetchall()

    unresolved: List[int] = []
    with sqlite3.connect(annotated_db) as ann_conn:
        ann_conn.row_factory = sqlite3.Row
        rows = ann_conn.execute(
            f"SELECT rowid, extracted_text_full FROM {table_name} WHERE id IS NULL"
        ).fetchall()

        for row in rows:
            rowid = row["rowid"]
            target_id = _find_best_match(row["extracted_text_full"], source_tuples)
            if target_id is None:
                unresolved.append(int(rowid))
                continue
            ann_conn.execute(
                f"UPDATE {table_name} SET id = ? WHERE rowid = ?", (target_id, rowid)
            )
        ann_conn.commit()

    return unresolved


def patch(db_path: str, table_name: str) -> List[int]:
    """Alias for pipeline-style patching."""
    return get_anomalies(db_path, table_name)


def patch_database(db: str) -> List[int]:
    annotated_db = (
        REPO_ROOT / "Tafsir" / "tafsir_books_annotated" / f"{db}_annotated.sqlite3"
    )
    table_name = f"tafsir_analysis_{db}"
    return get_anomalies(str(annotated_db), table_name)


def main():
    parser = argparse.ArgumentParser(
        description="Patch rows where id is NULL and return unresolved rowids."
    )
    parser.add_argument(
        "--db", default="katheer", help="Logical book name, e.g. katheer"
    )
    args = parser.parse_args()
    unresolved = patch_database(args.db)
    print(f"Unresolved rows: {len(unresolved)}")
    if unresolved:
        print(unresolved)


if __name__ == "__main__":
    main()
