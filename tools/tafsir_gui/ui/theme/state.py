from __future__ import annotations

import json
from typing import Literal

from nicegui import ui

ColorMode = Literal["dark", "light"]
PipelineMode = Literal["legacy", "universal"]

_COLOR_MODES: tuple[ColorMode, ...] = ("dark", "light")
_PIPELINE_MODES: tuple[PipelineMode, ...] = ("legacy", "universal")

_color_mode: ColorMode = "dark"
_pipeline_mode: PipelineMode = "legacy"


def _apply_color_mode_js(mode: ColorMode, persist: bool = True) -> None:
    storage_line = (
        "localStorage.setItem('tafsir_theme', mode);"
        if persist
        else ""
    )
    ui.run_javascript(
        f"""
        const mode = {json.dumps(mode)};
        const root = document.documentElement;
        root.dataset.theme = mode;
        root.classList.remove('theme-dark', 'theme-light');
        root.classList.add('theme-' + mode);
        document.body.classList.toggle('light', mode === 'light');
        {storage_line}
        """
    )


def _apply_color_mode(mode: ColorMode, persist: bool = True) -> None:
    global _color_mode
    _color_mode = mode
    _apply_color_mode_js(mode, persist=persist)


def _apply_pipeline_mode_js(mode: PipelineMode) -> None:
    ui.run_javascript(
        f"""
        const mode = {json.dumps(mode)};
        const root = document.documentElement;
        root.dataset.pipelineMode = mode;
        root.classList.remove('mode-legacy', 'mode-universal');
        root.classList.add('mode-' + mode);
        """
    )


def _apply_pipeline_mode(mode: PipelineMode) -> None:
    global _pipeline_mode
    _pipeline_mode = mode
    _apply_pipeline_mode_js(mode)


def set_color_mode(mode: ColorMode) -> None:
    if mode not in _COLOR_MODES:
        return
    _apply_color_mode(mode)


def toggle_color_mode() -> None:
    next_mode = "light" if _color_mode == "dark" else "dark"
    _apply_color_mode(next_mode)


def set_pipeline_mode(mode: PipelineMode) -> None:
    if mode not in _PIPELINE_MODES:
        return
    _apply_pipeline_mode(mode)


def initialize() -> None:
    """Apply the default theme and pipeline mode when the UI is built."""
    def _apply_defaults():
        _apply_color_mode(_color_mode, persist=False)
        _apply_pipeline_mode(_pipeline_mode)

    ui.timer(0, lambda: _apply_defaults(), once=True)


def current_color_mode() -> ColorMode:
    return _color_mode


def current_pipeline_mode() -> PipelineMode:
    return _pipeline_mode


__all__ = [
    "ColorMode",
    "PipelineMode",
    "current_color_mode",
    "current_pipeline_mode",
    "set_color_mode",
    "set_pipeline_mode",
    "toggle_color_mode",
    "initialize",
]
