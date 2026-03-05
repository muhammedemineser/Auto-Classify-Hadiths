import importlib
import json
import os
import sqlite3
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


class ImmediateExecutor:
    """Synchronous drop-in for ThreadPoolExecutor used in tests."""

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def submit(self, fn, *args, **kwargs):
        result = fn(*args, **kwargs)

        class _Future:
            def result(self_inner):
                return result

        return _Future()


def _setup_runtime(tmp_path, monkeypatch, name):
    """
    Create an isolated runtime rooted at ``tmp_path/name`` and point all
    pipeline directories to it via environment variables.
    """
    base = tmp_path / name
    books = base / "tafsir_books"
    annotated = base / "tafsir_books_annotated"
    logs = base / "logs"
    config_dir = base / "config"
    for path in (books, annotated, logs, config_dir):
        path.mkdir(parents=True, exist_ok=True)

    env = {
        "SOURCE_DIR": str(books),
        "ANNOTATED_DIR": str(annotated),
        "LOGS_DIR": str(logs),
        "CONFIG_DIR": str(config_dir),
    }
    for key, val in env.items():
        monkeypatch.setenv(key, val)

    monkeypatch.syspath_prepend(str(REPO_ROOT))
    return base, books, annotated, logs, config_dir


def _seed_source_db(books_dir: Path, db_name: str, rows: list[tuple[int, str]]):
    db_path = books_dir / f"{db_name}.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"CREATE TABLE {db_name} (id INTEGER PRIMARY KEY, text TEXT)")
        conn.executemany(f"INSERT INTO {db_name} (id, text) VALUES (?, ?)", rows)
    return db_path


def _stub_google(monkeypatch):
    """
    Provide minimal ``google.genai`` stubs so the pipeline can import without the
    real dependency.
    """
    fake_types = types.SimpleNamespace(GenerateContentConfig=lambda *a, **k: None)

    class _FakeModels:
        def generate_content(self, *args, **kwargs):
            return types.SimpleNamespace(candidates=[True], text="")

    fake_genai = types.SimpleNamespace(
        Client=lambda *a, **k: types.SimpleNamespace(models=_FakeModels()),
        types=fake_types,
    )
    monkeypatch.setitem(sys.modules, "google", types.SimpleNamespace(genai=fake_genai))
    monkeypatch.setitem(sys.modules, "google.genai", fake_genai)
    monkeypatch.setitem(sys.modules, "google.genai.types", fake_types)


def _clear_pipeline_modules():
    for name in [
        "Tafsir.config.paths",
        "Tafsir.pipeline.gemini_common",
        "Tafsir.pipeline.gemini_api.blocks_to_xml_api",
        "Tafsir.pipeline.gemini_gui.blocks_to_xml_gui",
        "Tafsir.pipeline.gemini_gui.ocr",
    ]:
        sys.modules.pop(name, None)


def _read_structured_logs(log_path: Path) -> dict:
    assert log_path.exists(), "structured log file not created"
    return json.loads(log_path.read_text(encoding="utf-8"))


def _assert_log_shape(log_data: dict, expected_ids: set[str]):
    """Validate per-row JSON log structure."""
    assert set(log_data.keys()) == expected_ids
    for row_id, buckets in log_data.items():
        # Only numeric, single-row identifiers
        assert row_id.isdigit()
        assert isinstance(buckets, dict)
        assert buckets, "each row must contain at least one log bucket"
        for log_type, entries in buckets.items():
            assert isinstance(log_type, str) and log_type
            assert isinstance(entries, list)
            assert all(isinstance(e, str) for e in entries)
            # No batch/range identifiers baked into the log type
            assert "-" not in log_type and "," not in log_type


def test_api_pipeline_structured_logs_and_multimodel(tmp_path, monkeypatch):
    """
    Validate that list mode produces per-row JSON logs and that --multiple-models
    fans out to separate databases, one per GEMINI_* config.
    """
    base, books, annotated, logs, config_dir = _setup_runtime(
        tmp_path, monkeypatch, "api_structured"
    )

    # Two models: default plus a suffixed variant
    monkeypatch.setenv("GEMINI_API_KEY", "k-default")
    monkeypatch.setenv("GEMINI_MODEL_ID", "m-default")
    monkeypatch.setenv("GEMINI_CACHE_NAME", "cache-default")
    monkeypatch.setenv("GEMINI_2_API_KEY", "k-two")
    monkeypatch.setenv("GEMINI_2_MODEL_ID", "m-two")
    monkeypatch.setenv("GEMINI_2_CACHE_NAME", "cache-two")

    _stub_google(monkeypatch)
    _clear_pipeline_modules()
    api = importlib.import_module("Tafsir.pipeline.gemini_api.blocks_to_xml_api")

    # Redirect paths into the isolated runtime
    monkeypatch.setattr(api, "REPO_ROOT", base, raising=False)
    monkeypatch.setattr(api, "LOGS_DIR", logs, raising=False)
    monkeypatch.setattr(
        api, "_CURRENT_LOG_JSON_PATH", logs / "structured_logs_default.json", raising=False
    )
    monkeypatch.setattr(api.cfg, "BOOKS_DIR", books, raising=False)
    monkeypatch.setattr(api.cfg, "ANNOTATED_DIR", annotated, raising=False)
    monkeypatch.setattr(api.cfg, "CONFIG_DIR", config_dir, raising=False)
    monkeypatch.setattr(api, "ThreadPoolExecutor", ImmediateExecutor, raising=False)
    monkeypatch.setattr(api.time, "sleep", lambda *_: None, raising=False)

    def fake_request(prompt: str):
        """
        Deterministic stub:
        - If the prompt contains PASS_MARKER tokens, echo them (guard passes).
        - Otherwise return unrelated text to force guard retries -> skip.
        """
        model_id = os.getenv("GEMINI_MODEL_ID", "unknown")
        if "PASS_MARKER" in prompt:
            content = prompt.strip()
        else:
            content = "totally mismatching output"
        return (
            "<tafsir_section_block><tafsir_chunk><hadith>"
            f"{content} [{model_id}]"
            "</hadith></tafsir_chunk></tafsir_section_block>"
        )

    monkeypatch.setattr(api, "request_gemini_response", fake_request, raising=False)

    db_name = "demo"
    rows = [
        (101, "PASS_MARKER content for guard"),
        (202, "fail sample alpha"),
        (303, "fail sample beta"),
    ]
    _seed_source_db(books, db_name, rows)

    api.automate_gemini(db_name, exact_ids=[r[0] for r in rows], multiple_models=True)

    default_db = annotated / f"{db_name}_annotated_subset.sqlite3"
    model2_db = annotated / f"{db_name}_annotated_subset_2.sqlite3"
    assert default_db.exists()
    assert model2_db.exists()

    def _fetch(db_path):
        with sqlite3.connect(db_path) as conn:
            sections = conn.execute(
                "SELECT id FROM tafsir_analysis_demo ORDER BY id"
            ).fetchall()
            hadiths = conn.execute(
                "SELECT hadith FROM tafsir_analysis_demo_chunks ORDER BY id"
            ).fetchall()
        return [r[0] for r in sections], [r[0] for r in hadiths]

    ids_default, hadith_default = _fetch(default_db)
    ids_two, hadith_two = _fetch(model2_db)

    expected_ids = [101, 202, 303]
    assert ids_default == expected_ids
    assert ids_two == expected_ids

    # Only the guard-pass row should have chunk rows; their contents must be
    # tagged with the active model id to prove per-model execution.
    assert hadith_default and all("m-default" in h for h in hadith_default)
    assert hadith_two and all("m-two" in h for h in hadith_two)

    log_data_default = _read_structured_logs(logs / "structured_logs_default.json")
    log_data_model2 = _read_structured_logs(logs / "structured_logs_2.json")

    _assert_log_shape(log_data_default, {str(i) for i in expected_ids})
    _assert_log_shape(log_data_model2, {str(i) for i in expected_ids})

    # Every provided ID must have at least one log entry across any log type.
    for row_id in map(str, expected_ids):
        total_entries_default = sum(
            len(entries) for entries in log_data_default[row_id].values()
        )
        total_entries_model2 = sum(
            len(entries) for entries in log_data_model2[row_id].values()
        )
        assert total_entries_default > 0, f"default row {row_id} missing log entries"
        assert total_entries_model2 > 0, f"model2 row {row_id} missing log entries"

    # Ensure guard + progress logs exist for all rows; responses only for pass row.
    for bucket_set in (log_data_default, log_data_model2):
        for row_id, buckets in bucket_set.items():
            assert "progress" in buckets
            assert "guard" in buckets
            if row_id == "101":
                assert "responses" in buckets
            else:
                assert "responses" not in buckets


def test_gui_pipeline_structured_logs_list_mode(tmp_path, monkeypatch):
    """
    Ensure GUI list mode writes the same structured per-row logs and uses the
    subset database while processing each provided ID.
    """
    base, books, annotated, logs, config_dir = _setup_runtime(
        tmp_path, monkeypatch, "gui_structured"
    )

    # Lightweight stubs for GUI-only deps
    pyautogui = types.SimpleNamespace()

    def _noop(*_args, **_kwargs):
        return None

    pyautogui.click = _noop
    pyautogui.hotkey = _noop
    pyautogui.moveTo = _noop
    pyautogui.press = _noop
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0

    clipboard = {"value": ""}
    pyperclip = types.SimpleNamespace(
        copy=lambda val: clipboard.update({"value": val}),
        paste=lambda: clipboard["value"],
    )

    class _DummySct:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def grab(self, rect):
            return rect

    dummy_mss = types.SimpleNamespace(mss=lambda: _DummySct())
    dummy_np = types.SimpleNamespace(
        array=lambda src, copy=False: src, array_equal=lambda a, b: a == b
    )

    for name, module in (
        ("pyautogui", pyautogui),
        ("pyperclip", pyperclip),
        ("mss", dummy_mss),
        ("numpy", dummy_np),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    _clear_pipeline_modules()
    gui = importlib.import_module("Tafsir.pipeline.gemini_gui.blocks_to_xml_gui")

    # Redirect paths into the isolated runtime
    monkeypatch.setattr(gui, "REPO_ROOT", base, raising=False)
    monkeypatch.setattr(gui, "LOGS_DIR", logs, raising=False)
    monkeypatch.setattr(
        gui, "_CURRENT_LOG_JSON_PATH", logs / "structured_logs_default.json", raising=False
    )
    monkeypatch.setattr(gui.cfg, "BOOKS_DIR", books, raising=False)
    monkeypatch.setattr(gui.cfg, "ANNOTATED_DIR", annotated, raising=False)
    monkeypatch.setattr(gui.cfg, "CONFIG_DIR", config_dir, raising=False)
    monkeypatch.setattr(gui, "ThreadPoolExecutor", ImmediateExecutor, raising=False)
    monkeypatch.setattr(gui.time, "sleep", lambda *_: None, raising=False)

    # Deterministic guard: pass only for PASS_MARKER rows, retry otherwise
    def fake_guard(source_tokens, *_args, **_kwargs):
        text = (
            " ".join(source_tokens)
            if isinstance(source_tokens, (list, tuple))
            else str(source_tokens)
        )
        if "pass_marker" in text.lower():
            return {"decision": "pass", "token_coverage": 1.0, "ngram_overlap": 1.0}
        return {"decision": "retry", "token_coverage": 0.0, "ngram_overlap": 0.0}

    monkeypatch.setattr(gui, "evaluate_guard", fake_guard, raising=False)

    class DummyWatcher:
        def run(self):
            return True

    gui.watcher_a = DummyWatcher()
    gui.watcher_b = DummyWatcher()

    responses = iter(
        [
            # row 101 (pass)
            "<tafsir_section_block><tafsir_chunk><hadith>PASS_MARKER ok</hadith></tafsir_chunk></tafsir_section_block>",
            # row 202 attempts
            "<tafsir_section_block><tafsir_chunk><hadith>bad alpha</hadith></tafsir_chunk></tafsir_section_block>",
            "<tafsir_section_block><tafsir_chunk><hadith>bad alpha</hadith></tafsir_chunk></tafsir_section_block>",
            "<tafsir_section_block><tafsir_chunk><hadith>bad alpha</hadith></tafsir_chunk></tafsir_section_block>",
            # row 303 attempts
            "<tafsir_section_block><tafsir_chunk><hadith>bad beta</hadith></tafsir_chunk></tafsir_section_block>",
            "<tafsir_section_block><tafsir_chunk><hadith>bad beta</hadith></tafsir_chunk></tafsir_section_block>",
            "<tafsir_section_block><tafsir_chunk><hadith>bad beta</hadith></tafsir_chunk></tafsir_section_block>",
        ]
    )
    monkeypatch.setattr(gui, "get_code_from_devtools", lambda: next(responses, ""), raising=False)

    db_name = "demo"
    rows = [
        (101, "PASS_MARKER content for guard"),
        (202, "fail sample alpha"),
        (303, "fail sample beta"),
    ]
    _seed_source_db(books, db_name, rows)

    gui.automate_gemini(db_name, exact_ids=[r[0] for r in rows], multiple_models=False)

    subset_db = annotated / f"{db_name}_annotated_subset.sqlite3"
    default_db = annotated / f"{db_name}_annotated.sqlite3"
    assert subset_db.exists()
    assert not default_db.exists(), "list mode should avoid the default database"

    with sqlite3.connect(subset_db) as conn:
        section_ids = conn.execute(
            "SELECT id FROM tafsir_analysis_demo ORDER BY id"
        ).fetchall()
        hadith_rows = conn.execute(
            "SELECT hadith FROM tafsir_analysis_demo_chunks ORDER BY id"
        ).fetchall()

    expected_ids = [101, 202, 303]
    saved_ids = [row[0] for row in section_ids]
    assert 101 in saved_ids
    assert set(saved_ids).issubset(expected_ids)
    assert len(hadith_rows) == 1
    assert "PASS_MARKER" in hadith_rows[0][0]

    log_data = _read_structured_logs(logs / "structured_logs_default.json")
    _assert_log_shape(log_data, {str(i) for i in expected_ids})

    for row_id, buckets in log_data.items():
        assert "progress" in buckets
        assert "guard" in buckets
        if row_id == "101":
            assert "responses" in buckets
        else:
            assert "responses" not in buckets
