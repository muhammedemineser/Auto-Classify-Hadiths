import sqlite3
import sys
from types import SimpleNamespace

import pytest

# Allow running this test file directly (python path/to/test_*.py) by ensuring
# the repository root is on sys.path. Pytest usually does this automatically.
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Stub google.genai modules if unavailable
if "google" not in sys.modules:
    genai_mod = SimpleNamespace(Client=lambda *a, **k: None)
    types_mod = SimpleNamespace(GenerateContentConfig=lambda *a, **k: None)
    genai_mod.types = types_mod
    google_mod = SimpleNamespace(genai=genai_mod)
    sys.modules["google"] = google_mod
    sys.modules["google.genai"] = genai_mod
    sys.modules["google.genai.types"] = types_mod

import Tafsir.utils.follow_up_runs.rollback_pipeline as rp  # noqa: E402


def test_log_anomaly_ignores_none():
    pipe = rp.TafsirRollbackPipeline()
    pipe.log_anomaly(3)
    pipe.log_anomaly(None)
    assert pipe.regen_ids == {3}


def test_check_id_gaps_adds_neighbors(tmp_path, monkeypatch):
    base = tmp_path / "Tafsir"
    (base / "tafsir_books").mkdir(parents=True)
    (base / "tafsir_books_annotated").mkdir(parents=True)

    src_db = base / "tafsir_books" / "katheer.sqlite3"
    with sqlite3.connect(src_db) as conn:
        conn.execute("CREATE TABLE katheer (id INTEGER PRIMARY KEY, text TEXT)")
        conn.executemany(
            "INSERT INTO katheer (id, text) VALUES (?, ?)",
            [(1, "a"), (2, "b"), (3, "c")],
        )

    ann_db = base / "tafsir_books_annotated" / "katheer_annotated.sqlite3"
    with sqlite3.connect(ann_db) as conn:
        conn.execute("CREATE TABLE tafsir_analysis_katheer (id INTEGER)")
        conn.executemany("INSERT INTO tafsir_analysis_katheer (id) VALUES (?)", [(1,), (3,)])

    pipe = rp.TafsirRollbackPipeline(book="katheer", base_path=str(base))
    pipe.check_id_gaps()

    # Missing ID 2 should be scheduled for regeneration (and it exists in src_db).
    assert pipe.regen_ids == {2}


def test_call_gemini_fix_writes_new_text(tmp_path, monkeypatch):
    # Prepare source DB with original text
    base = tmp_path / "Tafsir"
    (base / "tafsir_books").mkdir(parents=True)
    (base / "tafsir_books_annotated").mkdir(parents=True)

    src_db = base / "tafsir_books" / "katheer.sqlite3"
    with sqlite3.connect(src_db) as conn:
        conn.execute("CREATE TABLE katheer (id INTEGER PRIMARY KEY, text TEXT)")
        conn.execute(
            "INSERT INTO katheer (id, text) VALUES (?, ?)", (1, "<p>original</p>")
        )

    # Prepare annotated DB with existing rows
    ann_db = base / "tafsir_books_annotated" / "katheer_annotated.sqlite3"
    with sqlite3.connect(ann_db):
        pass

    # Stub environment for Gemini
    monkeypatch.setenv("GEMINI_API_KEY_ROLLBACK", "dummy")
    monkeypatch.setenv("GEMINI_API_KEY_ROLLBACK_CACHE", "cache-name")

    # Fake Gemini client
    class _FakeModels:
        def generate_content(self, model, contents, config):
            return SimpleNamespace(text="<tafsir_section_block>new</tafsir_section_block>")

    class _FakeClient:
        def __init__(self, *a, **k):
            self.models = _FakeModels()

    monkeypatch.setattr(rp.genai, "Client", _FakeClient)

    # Dummy types config
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
    monkeypatch.setattr(rp, "ALL_COLUMNS", ["extracted_text_full"], raising=False)

    pipe = rp.TafsirRollbackPipeline(book="katheer", base_path=str(base))
    pipe.regenerate_id(1)

    # Verify the new text is stored
    with sqlite3.connect(ann_db) as conn:
        row = conn.execute(
            "SELECT extracted_text_full FROM tafsir_analysis_katheer WHERE id = 1"
        ).fetchone()
    assert row is not None
    assert row[0] == "<tafsir_section_block>new</tafsir_section_block>"
