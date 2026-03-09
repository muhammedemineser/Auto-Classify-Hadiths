from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from typing import Any, Callable


def _ensure_cached_columns(conn: sqlite3.Connection, config) -> None:
    cur = conn.cursor()
    cols = {
        row[1]
        for row in cur.execute(f"PRAGMA table_info({config.table})").fetchall()
    }
    if config.normalized_col not in cols:
        cur.execute(f"ALTER TABLE {config.table} ADD COLUMN {config.normalized_col} TEXT")
    if config.pos_col not in cols:
        cur.execute(f"ALTER TABLE {config.table} ADD COLUMN {config.pos_col} TEXT")
    conn.commit()

def ensure_cached_columns(
    current_db: str,
    config,
    *,
    norm_fn: Callable[[str], str],
    tag_pos_tokens_fn: Callable[[list[str]], list[str]],
) -> None:
    conn = sqlite3.connect(config.db_path + f"/{current_db}")
    try:
        _ensure_cached_columns(conn, config=config)
        _backfill_cache_columns(
            conn,
            config=config,
            norm_fn=norm_fn,
            tag_pos_tokens_fn=tag_pos_tokens_fn,
        )
    finally:
        conn.close()

def _backfill_cache_columns(
    conn: sqlite3.Connection,
    config,
    *,
    norm_fn: Callable[[str], str],
    tag_pos_tokens_fn: Callable[[list[str]], list[str]],
) -> None:
    def _is_json_pos_array(value: str) -> bool:
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return False
        return isinstance(parsed, list)

    cur = conn.cursor()
    rows = cur.execute(
        f"""
        SELECT rowid, {config.text_col}, {config.normalized_col}, {config.pos_col}
        FROM {config.table}
        """
    ).fetchall()
    for rowid, raw_text, normalized_cached, pos_cached in rows:
        text = raw_text or ""
        normalized_value = normalized_cached
        if not normalized_value:
            normalized_value = norm_fn(text)
            cur.execute(
                f"""
                UPDATE {config.table}
                SET {config.normalized_col}=?
                WHERE rowid=?
                """,
                (normalized_value, rowid),
            )
        if not pos_cached or not _is_json_pos_array(pos_cached):
            pos_tags = tag_pos_tokens_fn(normalized_value.split())
            cur.execute(
                f"""
                UPDATE {config.table}
                SET {config.pos_col}=?
                WHERE rowid=?
                """,
                (json.dumps(pos_tags, ensure_ascii=False), rowid),
            )
    conn.commit()


def get_txt_from_db(
    current_db: str,
    config,
    *,
    norm_fn: Callable[[str], str],
    tag_pos_tokens_fn: Callable[[list[str]], list[str]],
):
    ensure_cached_columns(
        current_db,
        config=config,
        norm_fn=norm_fn,
        tag_pos_tokens_fn=tag_pos_tokens_fn,
    )
    conn = sqlite3.connect(config.db_path + f"/{current_db}")
    try:
        cur = conn.cursor()
        rows = cur.execute(
            f"""
            SELECT
                {config.text_col},
                {config.id_col},
                {config.normalized_col},
                {config.pos_col}
            FROM {config.table}
            """
        ).fetchall()
        return rows
    finally:
        conn.close()


def build_candidate_cache(
    hadith_txt: str,
    *,
    norm_fn: Callable[[str], str],
    tag_pos_tokens_fn: Callable[[list[str]], list[str]],
) -> tuple[dict[str, list[int]], dict[str, dict[str, Any]]]:
    cand_txt: dict[str, list[int]] = defaultdict(list)
    with open(hadith_txt, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        cand_txt[line].append(i)

    cand_meta: dict[str, dict[str, Any]] = {}
    for line in cand_txt.keys():
        normalized_value = norm_fn(line)
        cand_meta[line] = {
            "normalized": normalized_value,
            "pos": tag_pos_tokens_fn(normalized_value.split()),
        }
    return cand_txt, cand_meta
