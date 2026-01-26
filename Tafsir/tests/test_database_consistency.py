import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from sqlalchemy import create_engine, text

from Tafsir.pipeline.gemini_common import _normalize_to_string
from Tafsir.pipeline.analysis.data_cleaning import rollback_pipeline as rp
from Tafsir.pipeline.gemini_api import blocks_to_xml_api as api


def _assert_section_block_chunk_relations(
    engine, section_table, block_table, chunk_table, section_id, raw_xml
):
    expected_normalized = _normalize_to_string(raw_xml) or ""
    with engine.connect() as conn:
        section = conn.execute(
            text(f"SELECT id, extracted_text_normalized FROM {section_table} WHERE id = :id"),
            {"id": section_id},
        ).mappings().fetchone()
        assert section is not None
        assert section["id"] == section_id
        stored_norm = section["extracted_text_normalized"] or ""
        assert stored_norm == expected_normalized

        blocks = conn.execute(
            text(f"SELECT id, tafsir_section_id FROM {block_table}")
        ).mappings().fetchall()
        assert blocks
        assert all(block["tafsir_section_id"] == section_id for block in blocks)
        block_ids = {block["id"] for block in blocks}

        chunks = conn.execute(
            text(f"SELECT tafsir_block_id FROM {chunk_table}")
        ).mappings().fetchall()
        assert chunks
        assert all(chunk["tafsir_block_id"] in block_ids for chunk in chunks)


def test_api_bulk_insert_maintains_relations(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'api.sqlite3'}")
    section_table = "sections"
    block_table = "blocks"
    chunk_table = "chunks"
    api.setup_analysis_tables(engine, section_table, block_table, chunk_table)

    raw_xml = (
        "<tafsir_section_block>"
        "<tafsir_chunk><hadith>One</hadith></tafsir_chunk>"
        "<tafsir_chunk><isnad>Two</isnad></tafsir_chunk>"
        "</tafsir_section_block>"
    )
    section_id = 7
    api.bulk_insert_tafsir(
        engine,
        section_table,
        block_table,
        chunk_table,
        [{"id": section_id, "text": raw_xml}],
    )

    _assert_section_block_chunk_relations(
        engine,
        section_table,
        block_table,
        chunk_table,
        section_id,
        raw_xml,
    )


def test_rollback_pipeline_regeneration_replaces_rows(monkeypatch, tmp_path):
    base = tmp_path / "Tafsir"
    (base / "tafsir_books").mkdir(parents=True)
    (base / "tafsir_books_annotated").mkdir(parents=True)

    src_db = base / "tafsir_books" / "katheer.sqlite3"
    with sqlite3.connect(src_db) as conn:
        conn.execute("CREATE TABLE katheer (id INTEGER PRIMARY KEY, text TEXT NOT NULL)")
        conn.execute(
            "INSERT INTO katheer (id, text) VALUES (?, ?)",
            (11, "<p>source text</p>"),
        )

    ann_db = base / "tafsir_books_annotated" / "katheer_annotated.sqlite3"
    section_table = "tafsir_analysis_katheer"
    block_table = f"{section_table}_blocks"
    chunk_table = f"{section_table}_chunks"
    with sqlite3.connect(ann_db) as conn:
        conn.execute(
            "CREATE TABLE tafsir_analysis_katheer (id INTEGER PRIMARY KEY, extracted_text_full TEXT)"
        )
        conn.execute(
            "INSERT INTO tafsir_analysis_katheer (id, extracted_text_full) VALUES (?, ?)",
            (11, "<tafsir_section_block>stale</tafsir_section_block>"),
        )
        conn.execute(
            "CREATE TABLE tafsir_analysis_katheer_blocks (id INTEGER PRIMARY KEY AUTOINCREMENT, tafsir_section_id INTEGER NOT NULL, block TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO tafsir_analysis_katheer_blocks (tafsir_section_id, block) VALUES (?, ?)",
            (11, "<tafsir_section_block>old</tafsir_section_block>"),
        )
        block_id = conn.execute(
            "SELECT id FROM tafsir_analysis_katheer_blocks WHERE tafsir_section_id = ?",
            (11,),
        ).fetchone()[0]
        conn.execute(
            "CREATE TABLE tafsir_analysis_katheer_chunks (id INTEGER PRIMARY KEY AUTOINCREMENT, tafsir_block_id INTEGER NOT NULL, chunk TEXT NOT NULL, extracted_text_full TEXT)",
        )
        conn.execute(
            "INSERT INTO tafsir_analysis_katheer_chunks (tafsir_block_id, chunk, extracted_text_full) VALUES (?, ?, ?)",
            (block_id, "<tafsir_chunk>old chunk</tafsir_chunk>", "<tafsir_chunk>old chunk</tafsir_chunk>"),
        )

    monkeypatch.setenv("GEMINI_API_KEY_ROLLBACK", "dummy-key")
    monkeypatch.setenv("GEMINI_API_KEY_ROLLBACK_CACHE", "cache-name")

    class _FakeModels:
        def generate_content(self, model, contents, config):
            return SimpleNamespace(text="<tafsir_section_block>fresh</tafsir_section_block>")

    class _FakeClient:
        def __init__(self, *_, **__):
            self.models = _FakeModels()

    monkeypatch.setattr(rp.genai, "Client", _FakeClient)

    class _FakeConfig:
        def __init__(self, cached_content):
            self.cached_content = cached_content

    monkeypatch.setattr(rp.types, "GenerateContentConfig", _FakeConfig)

    monkeypatch.setattr(
        rp,
        "evaluate_guard",
        lambda src, resp: {"decision": "pass", "token_coverage": 1.0, "ngram_overlap": 1.0},
    )
    monkeypatch.setattr(rp, "extract_nested_data", lambda xml: {"extracted_text_full": xml})
    monkeypatch.setattr(rp, "extract_section_blocks", lambda xml: [xml])
    monkeypatch.setattr(
        rp,
        "extract_block_chunks",
        lambda block_xml, tafsir_block_id: [
            {
                "tafsir_block_id": tafsir_block_id,
                "chunk": block_xml,
                "extracted_text_full": block_xml,
            }
        ],
    )
    monkeypatch.setattr(rp, "ALL_COLUMNS", ["extracted_text_full"])

    pipe = rp.TafsirRollbackPipeline(book="katheer", base_path=base)
    pipe.regenerate_id(11)

    with sqlite3.connect(ann_db) as conn:
        section = conn.execute(
            f"SELECT id, extracted_text_full FROM {section_table} WHERE id = ?",
            (11,),
        ).fetchone()
        assert section is not None
        assert section[1] == "<tafsir_section_block>fresh</tafsir_section_block>"

        blocks = conn.execute(
            f"SELECT id, tafsir_section_id, block FROM {block_table}"
        ).fetchall()
        assert len(blocks) == 1
        assert blocks[0][1] == 11
        assert blocks[0][2] == "<tafsir_section_block>fresh</tafsir_section_block>"

        chunks = conn.execute(
            f"SELECT tafsir_block_id, chunk FROM {chunk_table}"
        ).fetchall()
        assert len(chunks) == 1
        assert chunks[0][0] == blocks[0][0]
        assert chunks[0][1] == "<tafsir_section_block>fresh</tafsir_section_block>"
