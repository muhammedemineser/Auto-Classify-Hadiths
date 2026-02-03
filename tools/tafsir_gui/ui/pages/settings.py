from __future__ import annotations

from pathlib import Path
from typing import Callable

from nicegui import ui


def project_settings(state, on_change: Callable[[], None]):
    ui.label("Project & Output").classes("text-lg font-semibold")
    ui.input(
        "Project name",
        value=state.project_name,
        on_change=lambda e: _set(state, "project_name", e.value, on_change),
        placeholder="e.g., katheer_run",
    ).props("clearable")
    ui.input(
        "Output directory",
        value=str(state.output_dir),
        on_change=lambda e: _set_dir(state, e.value, on_change),
        placeholder="Absolute path where results will be stored",
    ).props("clearable")
    ui.input(
        "Optional start ID",
        value=str(state.start_id or ""),
        on_change=lambda e: _set_int(state, "start_id", e.value, on_change),
        placeholder="Leave blank for beginning",
    )
    ui.input(
        "Optional explicit IDs (comma separated)",
        value=",".join(str(i) for i in state.exact_ids or []),
        on_change=lambda e: _set_ids(state, e.value, on_change),
        placeholder="e.g., 1,2,3",
    )


def api_settings(state, on_change: Callable[[], None]):
    ui.label("API & Model").classes("text-lg font-semibold")
    ui.input(
        "Gemini API key",
        value=state.api_key,
        password=True,
        on_change=lambda e: _set(state, "api_key", e.value, on_change),
        placeholder="Paste your Gemini API key",
    )
    ui.input(
        "Gemini Model ID",
        value=state.model_id,
        on_change=lambda e: _set(state, "model_id", e.value, on_change),
        placeholder="models/gemini-2.5-pro",
    )
    ui.input(
        "Rollback API key (optional)",
        value=state.rollback_api_key or "",
        password=True,
        on_change=lambda e: _set(state, "rollback_api_key", e.value, on_change),
    )
    ui.input(
        "Rollback cache name (optional)",
        value=state.rollback_cache or "",
        on_change=lambda e: _set(state, "rollback_cache", e.value, on_change),
    )


def cache_settings(state, on_change: Callable[[], None], on_generate):
    ui.label("Cache").classes("text-lg font-semibold")
    ui.input(
        "Cache name",
        value=state.cache_name or "",
        on_change=lambda e: _set(state, "cache_name", e.value, on_change),
        placeholder="Will be generated if empty",
    )
    ui.button(
        "Generate cache with current API key",
        on_click=on_generate,
    ).props("outline")


def _set(state, attr, value, on_change):
    setattr(state, attr, value)
    on_change()


def _set_dir(state, value, on_change):
    try:
        setattr(state, "output_dir", Path(value))
    finally:
        on_change()


def _set_int(state, attr, value, on_change):
    try:
        val = int(value) if value else None
    except ValueError:
        val = None
    setattr(state, attr, val)
    on_change()


def _set_ids(state, value, on_change):
    ids = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError:
            continue
    setattr(state, "exact_ids", ids or None)
    on_change()


__all__ = ["project_settings", "api_settings", "cache_settings"]
