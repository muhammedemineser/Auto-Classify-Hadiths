from __future__ import annotations

from typing import Callable

from nicegui import ui


def toggle(options, value=None, on_change: Callable | None = None):
    comp = ui.toggle(options, value=value)
    if on_change:
        bind_change(comp, on_change)
    return comp


def checkbox(label: str, value=False, on_change: Callable | None = None):
    comp = ui.checkbox(label, value=value)
    if on_change:
        bind_change(comp, on_change)
    return comp


def bind_change(component, handler: Callable):
    """Compatibility wrapper for NiceGUI value change events."""
    if hasattr(component, "on_value_change"):
        component.on_value_change(handler)
    elif hasattr(component, "on"):
        component.on("update:model-value", handler)
    else:  # pragma: no cover
        raise AttributeError("Component does not support change events")


__all__ = ["toggle", "checkbox", "bind_change"]
