import importlib
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from sqlalchemy import create_engine, text

from Tafsir.pipeline.gemini_common import (
    ALL_TAGS,
    RAW_COL,
    _get_table_columns,
    _normalize_to_string,
    extract_block_chunks,
    extract_nested_data,
    extract_section_blocks,
)


@pytest.fixture()
def bx(monkeypatch):
    utils_dir = Path(__file__).resolve().parent.parent / "utils"
    monkeypatch.syspath_prepend(str(utils_dir))

    pyautogui = types.SimpleNamespace()
    pyautogui.calls = []

    def _noop(*args, **kwargs):
        pyautogui.calls.append((args, kwargs))

    pyautogui.click = _noop
    pyautogui.hotkey = _noop
    pyautogui.moveTo = _noop
    pyautogui.press = _noop
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
    monkeypatch.setitem(sys.modules, "pyautogui", pyautogui)

    clipboard_state = {"value": ""}

    def copy(val):
        clipboard_state["value"] = val

    def paste():
        return clipboard_state["value"]

    pyperclip = types.SimpleNamespace(copy=copy, paste=paste)
    monkeypatch.setitem(sys.modules, "pyperclip", pyperclip)

    if "blocks_to_xml_ai" in sys.modules:
        sys.modules.pop("blocks_to_xml_ai")
    bx = importlib.import_module("blocks_to_xml_ai")

    class DummyWatcher:
        def __init__(self, results=None):
            self.results = list(results or [True])

        def run(self):
            if self.results:
                return self.results.pop(0)
            return True

    bx.watcher_a = DummyWatcher()
    bx.watcher_b = DummyWatcher()
    monkeypatch.setattr(bx.time, "sleep", lambda *_: None)
    return bx


def test_extract_nested_data_handles_empty_and_multiple_tags(bx):
    empty_row = extract_nested_data("")
    assert empty_row[RAW_COL] == ""
    assert all(empty_row[tag] is None for tag in ALL_TAGS)

    xml = "<isnad>A</isnad><isnad>B</isnad><hadith>C</hadith>"
    row = extract_nested_data(xml)
    assert row["isnad"] == "A\nB"
    assert row["hadith"] == "C"
    assert row[RAW_COL] == xml


def test_extract_section_blocks_split_and_fallback(bx):
    xml = (
        "<tafsir_section_block>One</tafsir_section_block>"
        "<tafsir_section_block>Two</tafsir_section_block>"
    )
    blocks = extract_section_blocks(xml)
    assert len(blocks) == 2
    assert all("tafsir_section_block" in b for b in blocks)

    fallback = extract_section_blocks("<p>plain</p>")
    assert fallback == ["<p>plain</p>"]
    assert extract_section_blocks("") == []
    assert extract_section_blocks(None) == []

def test_extract_block_chunks_handles_chunks_and_fallback(bx):
    block_xml = (
        "<tafsir_chunk><hadith>X</hadith></tafsir_chunk>"
        "<tafsir_chunk><isnad>Y</isnad></tafsir_chunk>"
    )
    rows = extract_block_chunks(block_xml, 11)
    assert len(rows) == 2
    assert all(r["tafsir_block_id"] == 11 for r in rows)
    assert rows[0]["hadith"] == "X"
    assert rows[1]["isnad"] == "Y"

    fallback = extract_block_chunks("no chunks here", 5)
    assert len(fallback) == 1
    assert fallback[0]["chunk"] == "no chunks here"
    assert fallback[0][RAW_COL] == "no chunks here"

    assert extract_block_chunks("", 9) == []
    assert extract_block_chunks(None, 9) == []


def test_walk_deduplicates_nested_tags(bx):
    row = {tag: None for tag in ALL_TAGS}
    xml = "<isnad><isnad>inner</isnad><isnad>inner</isnad></isnad>"
    bx._walk(xml, row)
    assert row["isnad"] == xml


def test_setup_and_bulk_insert_create_related_rows(bx, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'data.sqlite3'}")
    section_table = "sections"
    block_table = "blocks"
    chunk_table = "chunks"
    bx.setup_analysis_tables(engine, section_table, block_table, chunk_table)

    raw = (
        "<tafsir_section_block><tafsir_chunk><hadith>A</hadith></tafsir_chunk>"
        "</tafsir_section_block>"
        "<tafsir_section_block><tafsir_chunk><isnad>B</isnad></tafsir_chunk>"
        "</tafsir_section_block>"
    )
    bx.bulk_insert_tafsir(engine, section_table, block_table, chunk_table, [raw])

    with engine.connect() as conn:
        sections = conn.execute(text(f"SELECT COUNT(*) FROM {section_table}")).scalar()
        blocks = conn.execute(text(f"SELECT COUNT(*) FROM {block_table}")).scalar()
        chunks = conn.execute(text(f"SELECT hadith, isnad FROM {chunk_table}")).all()

    assert sections == 1
    assert blocks == 2
    assert len(chunks) == 2
    assert sorted([c[0] or c[1] for c in chunks]) == ["A", "B"]


def test_get_table_columns_and_mapping(bx, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'columns.sqlite3'}")
    bx.setup_analysis_tables(engine, "sections", "blocks", "chunks")
    bx.bulk_insert_tafsir(
        engine,
        "sections",
        "blocks",
        "chunks",
        [
            "<tafsir_section_block><tafsir_chunk><source>A</source></tafsir_chunk>"
            "</tafsir_section_block>"
        ],
    )

    with engine.connect() as conn:
        cols = _get_table_columns(conn, "sections")
        mapping = bx._build_block_id_mapping(conn, "blocks")

    assert {"id", "extracted_text_full"}.issubset(set(cols))
    assert len(mapping) == 1
    assert list(mapping.values())[0]  # contains new block id list


def test_migrate_tables_split_blocks_and_chunks(bx, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'migrate.sqlite3'}")
    section_table = "sections"
    block_table = "blocks"
    chunk_table = "chunks"
    with engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE {section_table} (id INTEGER PRIMARY KEY)"))
        conn.execute(text(f"INSERT INTO {section_table} (id) VALUES (1)"))
        conn.execute(
            text(
                f"CREATE TABLE {block_table} (id INTEGER PRIMARY KEY, tafsir_section_id INTEGER, block TEXT)"
            )
        )
        conn.execute(
            text(
                f"INSERT INTO {block_table} (tafsir_section_id, block) VALUES (1, "
                " '<tafsir_section_block>one</tafsir_section_block>"
                " <tafsir_section_block><tafsir_chunk><hadith>two</hadith>"
                "</tafsir_chunk></tafsir_section_block>' )"
            )
        )

        block_sql = (
            f"CREATE TABLE {block_table} ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "tafsir_section_id INTEGER NOT NULL, "
            "block TEXT NOT NULL)"
        )
        mapping = bx._migrate_block_table(conn, block_table, block_sql)
        assert mapping and list(mapping.values())[0] == [1, 2]

        conn.execute(
            text(
                f"CREATE TABLE {chunk_table} "
                "(id INTEGER PRIMARY KEY, tafsir_chunks INTEGER, chunk TEXT)"
            )
        )
        conn.execute(
            text(
                f"INSERT INTO {chunk_table} (tafsir_chunks, chunk) VALUES (1, "
                "'<tafsir_chunk><hadith>X</hadith></tafsir_chunk>"
                "<tafsir_chunk><isnad>Y</isnad></tafsir_chunk>')"
            )
        )

        chunk_column_defs = ", ".join(f"{c} TEXT" for c in bx.ALL_COLUMNS)
        chunk_sql = (
            f"CREATE TABLE {chunk_table} ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "tafsir_block_id INTEGER NOT NULL, "
            "chunk TEXT NOT NULL, "
            f"{chunk_column_defs})"
        )
        bx._migrate_chunk_table(conn, chunk_table, chunk_sql, mapping)

        rows = conn.execute(
            text(f"SELECT tafsir_block_id, chunk FROM {chunk_table}")
        ).fetchall()
        assert len(rows) == 4
        assert set(r[0] for r in rows) == {1, 2}


def test_cleanup_cycle_flushes_batch_and_inserts(bx, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'cleanup.sqlite3'}")
    section_table = "sections"
    block_table = "blocks"
    chunk_table = "chunks"
    bx.setup_analysis_tables(engine, section_table, block_table, chunk_table)

    xml = "<tafsir_section_block><tafsir_chunk><hadith>A</hadith></tafsir_chunk></tafsir_section_block>"

    class ImmediateExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def submit(self, fn, *args, **kwargs):
            result = fn(*args, **kwargs)

            class Future:
                def result(self_inner):
                    return result

            return Future()

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(bx, "get_code_from_devtools", lambda: xml)
    pending_futures = []
    executor = ImmediateExecutor()
    batch = []

    bx.cleanup_cycle(
        batch,
        executor,
        engine,
        section_table,
        block_table,
        chunk_table,
        flush_batch=True,
        pending_futures=pending_futures,
        prefetched_text=xml,
        append_to_batch=True,
    )
    for fut in pending_futures:
        fut.result()

    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {section_table}")).scalar()
    assert count == 1
    monkeypatch.undo()


def test_get_code_from_devtools_parses_html(bx, monkeypatch):
    monkeypatch.setattr(bx.pyperclip, "paste", lambda: "<div>hello</div>")
    result = bx.get_code_from_devtools()
    assert result == "hello"


def test_evaluate_guard_decisions(bx):
    source = "<tag>Hello world this is full text</tag>"
    response_good = "<tafsir_section_block>hello world this is full text</tafsir_section_block>"
    response_mid = "hello world this is text"
    response_bad = "other stuff"

    good = bx.evaluate_guard(source, response_good)
    assert good["decision"] == "pass"
    assert good["token_coverage"] >= 0.85
    assert good["ngram_overlap"] >= 0.6

    mid = bx.evaluate_guard(source, response_mid)
    assert mid["decision"] == "log"

    bad = bx.evaluate_guard(source, response_bad)
    assert bad["decision"] == "retry"


def test_automate_gemini_processes_all_rows_and_resumes(bx, tmp_path, monkeypatch):
    db = "dummy"
    input_path = tmp_path / "input.sqlite3"
    output_path = tmp_path / "output.sqlite3"
    in_engine = create_engine(f"sqlite:///{input_path}")
    with in_engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE {db} (text TEXT)"))
        for i in range(6):
            conn.execute(text(f"INSERT INTO {db} (text) VALUES (:t)"), {"t": f"row {i}"})

    out_engine = create_engine(f"sqlite:///{output_path}")
    target_table = f"tafsir_analysis_{db}"
    block_table = f"{target_table}_blocks"
    chunk_table = f"{target_table}_chunks"
    bx.setup_analysis_tables(out_engine, target_table, block_table, chunk_table)

    preprocessed = [
        "<tafsir_section_block><tafsir_chunk><hadith>P0</hadith></tafsir_chunk></tafsir_section_block>",
        "<tafsir_section_block><tafsir_chunk><hadith>P1</hadith></tafsir_chunk></tafsir_section_block>",
    ]
    bx.bulk_insert_tafsir(out_engine, target_table, block_table, chunk_table, preprocessed)

    xml_responses = [
        "<tafsir_section_block><tafsir_chunk><hadith>row 2 annotated</hadith></tafsir_chunk></tafsir_section_block>",
        "<tafsir_section_block><tafsir_chunk><hadith>row 3 annotated</hadith></tafsir_chunk></tafsir_section_block>",
        "<tafsir_section_block><tafsir_chunk><hadith>row 4 annotated</hadith></tafsir_chunk></tafsir_section_block>",
        "<tafsir_section_block><tafsir_chunk><hadith>row 5 annotated</hadith></tafsir_chunk></tafsir_section_block>",
    ]
    responses_iter = iter(xml_responses)
    monkeypatch.setattr(bx, "get_code_from_devtools", lambda: next(responses_iter, ""))

    def fake_create_engine(url, *args, **kwargs):
        if f"tafsir_books/{db}.sqlite3" in url:
            return create_engine(f"sqlite:///{input_path}")
        if f"tafsir_books_annotated/{db}_annotated.sqlite3" in url:
            return create_engine(f"sqlite:///{output_path}")
        return create_engine(url, *args, **kwargs)

    class ImmediateExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, *args, **kwargs):
            result = fn(*args, **kwargs)

            class Future:
                def result(self_inner):
                    return result

            return Future()

    bx.watcher_a.run = lambda: True
    bx.watcher_b.run = lambda: True
    monkeypatch.setattr(bx, "ThreadPoolExecutor", ImmediateExecutor)
    monkeypatch.setattr(bx, "create_engine", fake_create_engine)

    bx.automate_gemini(db)

    with out_engine.connect() as conn:
        saved = conn.execute(text(f"SELECT hadith FROM {chunk_table} ORDER BY id")).all()
    assert len(saved) == 6
    assert [row[0] for row in saved] == [
        "P0",
        "P1",
        "row 2 annotated",
        "row 3 annotated",
        "row 4 annotated",
        "row 5 annotated",
    ]


def test_automate_gemini_stops_when_no_extraction(bx, tmp_path, monkeypatch):
    db = "dry"
    input_path = tmp_path / "input2.sqlite3"
    output_path = tmp_path / "output2.sqlite3"
    in_engine = create_engine(f"sqlite:///{input_path}")
    with in_engine.begin() as conn:
        conn.execute(text(f"CREATE TABLE {db} (text TEXT)"))
        conn.execute(text(f"INSERT INTO {db} (text) VALUES ('row')"))

    out_engine = create_engine(f"sqlite:///{output_path}")
    target_table = f"tafsir_analysis_{db}"
    block_table = f"{target_table}_blocks"
    chunk_table = f"{target_table}_chunks"
    bx.setup_analysis_tables(out_engine, target_table, block_table, chunk_table)

    monkeypatch.setattr(bx, "get_code_from_devtools", lambda: "")
    bx.watcher_a.run = lambda: True
    bx.watcher_b.run = lambda: True

    def fake_create_engine(url, *args, **kwargs):
        if f"tafsir_books/{db}.sqlite3" in url:
            return create_engine(f"sqlite:///{input_path}")
        if f"tafsir_books_annotated/{db}_annotated.sqlite3" in url:
            return create_engine(f"sqlite:///{output_path}")
        return create_engine(url, *args, **kwargs)

    class ImmediateExecutor:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def submit(self, fn, *args, **kwargs):
            result = fn(*args, **kwargs)

            class Future:
                def result(self_inner):
                    return result

            return Future()

    monkeypatch.setattr(bx, "ThreadPoolExecutor", ImmediateExecutor)
    monkeypatch.setattr(bx, "create_engine", fake_create_engine)

    bx.automate_gemini(db)

    with out_engine.connect() as conn:
        saved = conn.execute(text(f"SELECT COUNT(*) FROM {target_table}")).scalar()
    assert saved == 0


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


def test_gui_bulk_insert_preserves_ids_and_relations(bx, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'gui_relations.sqlite3'}")
    section_table = "sections"
    block_table = "blocks"
    chunk_table = "chunks"
    bx.setup_analysis_tables(engine, section_table, block_table, chunk_table)

    raw_xml = (
        "<tafsir_section_block>"
        "<tafsir_chunk><hadith>Hello</hadith></tafsir_chunk>"
        "<tafsir_chunk><isnad>World</isnad></tafsir_chunk>"
        "</tafsir_section_block>"
    )
    record_id = 101
    bx.bulk_insert_tafsir(
        engine,
        section_table,
        block_table,
        chunk_table,
        [{"id": record_id, "text": raw_xml}],
    )

    _assert_section_block_chunk_relations(
        engine,
        section_table,
        block_table,
        chunk_table,
        record_id,
        raw_xml,
    )
