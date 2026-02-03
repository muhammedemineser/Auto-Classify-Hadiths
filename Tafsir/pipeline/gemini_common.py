from __future__ import annotations

from typing import Sequence

import regex
from bs4 import BeautifulSoup
from sqlalchemy import text

from Tafsir.pipeline.analysis.compare_tafsir_texts import normalize as normalize_tokens
from Tafsir.pipeline.gemini_gui.TAGS import (
    PRIMARY_TAGS,
    REMAINING_ALL_TAGS,
    SECONDARY_TAGS,
)

ALL_TAGS = (
    list(PRIMARY_TAGS.keys())
    + list(SECONDARY_TAGS.keys())
    + list(REMAINING_ALL_TAGS.keys())
)
RAW_COL = "extracted_text_full"
NORMALIZED_COL = "extracted_text_normalized"
ALL_COLUMNS = ALL_TAGS + [RAW_COL]

BLOCK_TAG = "tafsir_section_block"
CHUNK_TAG = "tafsir_chunk"
RX_RECURSIVE = regex.compile(
    r"(?s)<(?P<tag>" + "|".join(ALL_TAGS) + r")>(?P<content>(?:[^<]|(?R))*)</(?P=tag)>"
)
RX_BLOCK = regex.compile(rf"(?s)<{BLOCK_TAG}>(?P<content>(?:[^<]|(?R))*)</{BLOCK_TAG}>")
RX_CHUNK = regex.compile(rf"(?s)<{CHUNK_TAG}>(?P<content>(?:[^<]|(?R))*)</{CHUNK_TAG}>")

GUARD_NGRAM_SIZE = 3
GUARD_MAX_RETRIES = 2
GUARD_MIN_LEN_RATIO = 0.5


def _normalize_guard_tokens(text: Sequence[str] | str | None) -> list[str]:
    if isinstance(text, list):
        return text
    tokens = normalize_tokens(text)
    if tokens:
        return tokens
    if not text:
        return []
    if isinstance(text, str):
        clean = regex.sub(r"<[^>]+>", " ", text)
        normalized = " ".join(clean.split()).lower()
        return normalized.split() if normalized else []
    return []


def _normalize_to_string(text: Sequence[str] | str | None) -> str | None:
    tokens = normalize_tokens(text)
    return " ".join(tokens) if tokens else None


def _ngram_set(tokens: Sequence[str], n: int) -> set[str]:
    if not tokens:
        return set()
    n = max(1, min(n, len(tokens)))
    return {" ".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def _length_ratio(tokens_a: Sequence[str], tokens_b: Sequence[str]) -> float:
    la, lb = len(tokens_a), len(tokens_b)
    if not la or not lb:
        return 0.0
    shorter, longer = (la, lb) if la <= lb else (lb, la)
    return shorter / longer


def evaluate_guard(
    source_text: Sequence[str] | str | None,
    response_text: Sequence[str] | str | None,
    *,
    n: int = GUARD_NGRAM_SIZE,
    pre_normalized: bool = False,
) -> dict[str, float | str]:
    def _to_tokens(val: Sequence[str] | str | None) -> list[str]:
        if pre_normalized:
            if isinstance(val, list):
                return val
            if val is None:
                return []
            if isinstance(val, str):
                return val.split()
            return list(val)
        return _normalize_guard_tokens(val)

    source_tokens = _to_tokens(source_text)
    response_tokens = _to_tokens(response_text)

    if not source_tokens or not response_tokens or []:
        return {"token_coverage": 0.0, "ngram_overlap": 0.0, "decision": "retry"}

    response_set = set(response_tokens)
    hits = sum(1 for t in source_tokens if t in response_set)
    token_coverage = hits / len(source_tokens)

    n = max(1, min(n, len(source_tokens), len(response_tokens)))
    source_ngrams = _ngram_set(source_tokens, n)
    response_ngrams = _ngram_set(response_tokens, n)
    ngram_overlap = (
        len(source_ngrams & response_ngrams) / len(source_ngrams)
        if source_ngrams
        else 0.0
    )

    len_ratio = _length_ratio(source_tokens, response_tokens)

    if token_coverage >= 0.85 and ngram_overlap >= 0.6:
        decision = "pass"
    elif token_coverage < 0.7 or ngram_overlap < 0.4:
        decision = "retry"
    else:
        decision = "log"

    if len_ratio < GUARD_MIN_LEN_RATIO:
        decision = "retry"

    return {
        "token_coverage": token_coverage,
        "ngram_overlap": ngram_overlap,
        "length_ratio": len_ratio,
        "decision": decision,
    }


def extract_nested_data(xml: str | None) -> dict[str, str | None]:
    row = {tag: None for tag in ALL_TAGS}
    if not xml:
        row[RAW_COL] = xml
        return row

    soup = BeautifulSoup(xml, "html.parser")
    for tag in ALL_TAGS:
        elements = soup.find_all(tag)
        if elements:
            row[tag] = "\n".join(e.decode_contents() for e in elements)

    row[RAW_COL] = xml
    return row


def extract_section_blocks(xml: str | None) -> list[str]:
    if not xml:
        return []

    soup = BeautifulSoup(xml, "html.parser")
    blocks = soup.find_all(BLOCK_TAG)
    if blocks:
        return [str(block) for block in blocks]

    return [xml]


def extract_block_chunks(
    block_xml: str | None, tafsir_block_id: int
) -> list[dict[str, str | int]]:
    if not block_xml:
        return []

    soup = BeautifulSoup(block_xml, "html.parser")
    chunks = soup.find_all(CHUNK_TAG)
    chunk_rows: list[dict[str, str | int]] = []

    if not chunks:
        chunk_data = extract_nested_data(block_xml)
        chunk_data["tafsir_block_id"] = tafsir_block_id
        chunk_data["chunk"] = block_xml
        return [chunk_data]

    for chunk in chunks:
        chunk_text = str(chunk)
        chunk_data = extract_nested_data(chunk_text)
        chunk_data["tafsir_block_id"] = tafsir_block_id
        chunk_data["chunk"] = chunk_text
        chunk_rows.append(chunk_data)

    return chunk_rows


def _get_table_columns(conn, table_name: str) -> list[str]:
    result = conn.execute(text(f"PRAGMA table_info('{table_name}')"))
    return [row[1] for row in result]


def backfill_normalized(engine_out, section_table: str) -> None:
    with engine_out.begin() as conn:
        cols = _get_table_columns(conn, section_table)
        if NORMALIZED_COL not in cols:
            conn.execute(
                text(f"ALTER TABLE {section_table} ADD COLUMN {NORMALIZED_COL} TEXT")
            )

        rows = conn.execute(text(f"SELECT id, {RAW_COL} FROM {section_table} "))
        updates = [{"id": row[0], "norm": _normalize_to_string(row[1])} for row in rows]
        if updates:
            conn.execute(
                text(
                    f"UPDATE {section_table} SET {NORMALIZED_COL} = :norm WHERE id = :id"
                ),
                updates,
            )


def insert_empty_section(engine, section_table: str, section_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                f"INSERT OR IGNORE INTO {section_table} (id) VALUES (:id)"
            ),
            {"id": section_id},
        )


def clean_wrapped_xml(text: str | None) -> str | None:
    if not text:
        return text
    cleaned = regex.sub(r"^\s*```xml\s*", "", text, flags=regex.IGNORECASE)
    cleaned = regex.sub(r"^\s*XML\s*", "", cleaned, flags=regex.IGNORECASE)
    cleaned = regex.sub(r"<\?xml[^>]+\?>", "", cleaned, flags=regex.IGNORECASE)
    cleaned = regex.sub(r"\s*```\s*$", "", cleaned, flags=regex.IGNORECASE)
    return cleaned.strip()
