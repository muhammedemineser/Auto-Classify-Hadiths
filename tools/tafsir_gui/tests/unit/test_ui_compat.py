from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.tafsir_gui.ui import compat


class DummyComponent:
    def __init__(self):
        self.called = False
        self.event_name = None

    def on_value_change(self, handler):
        self.called = True
        handler(SimpleNamespace(value="value-change"))

    def on(self, event, handler):
        self.called = True
        self.event_name = event
        handler(SimpleNamespace(value="event"))


class NoValueChangeComponent:
    def __init__(self):
        self.called = False
        self.event_name = None

    def on(self, event, handler):
        self.called = True
        self.event_name = event
        handler(SimpleNamespace(value="fallback"))


def test_bind_change_prefers_on_value_change():
    dummy = DummyComponent()
    compat.bind_change(dummy, lambda e: None)
    assert dummy.called


def test_bind_change_fallback_on_event():
    dummy = NoValueChangeComponent()
    compat.bind_change(dummy, lambda e: None)
    assert dummy.called
    assert dummy.event_name == "update:model-value"


def test_toggle_and_checkbox_use_compatibility_shim(monkeypatch):
    toggle_instance = DummyComponent()
    checkbox_instance = DummyComponent()

    monkeypatch.setattr(
        "tools.tafsir_gui.ui.compat.ui.toggle",
        lambda *a, **k: toggle_instance,
    )
    monkeypatch.setattr(
        "tools.tafsir_gui.ui.compat.ui.checkbox",
        lambda *a, **k: checkbox_instance,
    )

    toggle = compat.toggle(["legacy", "universal"], value="legacy", on_change=lambda e: None)
    checkbox = compat.checkbox("Confirm", value=True, on_change=lambda e: None)

    assert toggle is toggle_instance
    assert checkbox is checkbox_instance
    assert toggle_instance.called
    assert checkbox_instance.called


def test_no_direct_on_change_usage_in_ui_files():
    repo_root = Path(__file__).resolve().parents[3]
    for path in (repo_root / "tools" / "tafsir_gui").rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert ".on_change(" not in text or "compat" in path.name, f"Direct .on_change usage found in {path}"
