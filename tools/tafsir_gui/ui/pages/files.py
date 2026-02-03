from __future__ import annotations

from pathlib import Path
from typing import Callable

from nicegui import ui

from ...utils import file_detect


def file_inputs(state, on_change: Callable[[], None]):
    ui.label("Input file").classes("text-lg font-semibold")
    preview = ui.markdown("").classes("text-sm")

    def refresh_preview(path_str: str):
        if not path_str:
            preview.set_content("No file selected.")
            return
        result = file_detect.validate_file(Path(path_str))
        state.file_preview = result
        badge = "✅" if result.ok else "❌"
        preview.set_content(f"{badge} {result.details}\n\nKind: {result.kind}\n\nSample:\n```\n{(result.sample or '')[:800]}\n```")

    ui.input(
        "Existing file path",
        value=str(state.input_path or ""),
        on_change=lambda e: _set_path(state, e.value, on_change, refresh_preview),
        placeholder="Path to PDF / CSV / SQLite / text file",
    ).props("clearable")

    upload = ui.upload(
        label="Or upload a file",
        auto_upload=True,
        on_upload=lambda e: _handle_upload(e, state, on_change, refresh_preview),
    )
    upload.props("accept=.pdf,.csv,.sqlite,.sqlite3,.db,.txt")


def _set_path(state, value, on_change, refresh):
    state.input_path = Path(value) if value else None
    on_change()
    refresh(value)


def _handle_upload(event, state, on_change, refresh):
    target_dir = Path(state.output_dir) / state.project_name / "uploads"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / event.name
    event.save(target)
    state.input_path = target
    on_change()
    refresh(str(target))


__all__ = ["file_inputs"]
