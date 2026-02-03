from __future__ import annotations

from typing import Callable, Iterable, Mapping, Sequence

from nicegui import ui

from .tokens import COLOR_MODES, RADIUS, SHADOWS, SPACING, TYPOGRAPHY


def themed_button(
    label: str,
    *,
    on_click: Callable | None = None,
    variant: str = "default",
    icon: str | None = None,
    tooltip: str | None = None,
    **kwargs,
) -> ui.button:
    """Create a NiceGUI button that follows the viewer.html theme."""

    variant_classes = {
        "default": "themed-button border border-slate-200 hover:bg-slate-50 transition-all duration-200 shadow-sm",
        "primary": "themed-button bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:opacity-90 shadow-md",
        "ghost": "themed-button q-btn--flat hover:bg-slate-100/50 backdrop-blur-sm",
        "danger": "themed-button q-btn--negative bg-red-50 hover:bg-red-100 text-red-600 border border-red-200",
    }

    button = ui.button(label, on_click=on_click, icon=icon, **kwargs)
    button.classes(variant_classes.get(variant, "themed-button"))
    if tooltip:
        button.props(f"title={tooltip}")
    return button


def themed_card(
    content: Callable[[ui.card], None] | None = None,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    actions: Iterable[Callable[[], None]] | None = None,
    **kwargs,
) -> ui.card:
    """Return a themed card. Pass content that receives the card to render inside."""

    card = ui.card(**kwargs).classes("themed-card")
    with card:
        if title:
            ui.label(title).classes("text-lg font-semibold")
        if subtitle:
            ui.label(subtitle).classes("text-sm viewer-muted")
        if content:
            content(card)
        if actions:
            with ui.row().classes("justify-end gap-2"):
                for action in actions:
                    action()
    return card


def themed_badge(text: str, *, variant: str = "default") -> ui.label:
    """Render a badge/chip that matches viewer colors."""

    badge = ui.label(text).classes("themed-badge")
    badge_color = {
        "default": COLOR_MODES["dark"].badge,
        "accent": COLOR_MODES["dark"].accent,
        "success": "#22c55e",
        "warning": "#f59e0b",
        "error": "#ef4444",
    }
    badge.style(f"background: {badge_color.get(variant, COLOR_MODES['dark'].badge)};")
    return badge


def themed_input(
    label: str,
    *,
    value: str | None = None,
    placeholder: str | None = None,
    on_change: Callable[[ui.Element], None] | None = None,
    error: str | None = None,
    **kwargs,
) -> ui.row:
    """Return an input row (label + field) styled like viewer.html."""

    with ui.row().classes("themed-input column gap-1"):
        ui.label(label).classes("text-sm viewer-muted")
        field = ui.input(
            value=value,
            placeholder=placeholder,
            on_change=on_change,
            **kwargs,
        )
        field.classes("themed-input")
        if error:
            ui.label(error).classes("text-red-400 text-xs")
    return field


def themed_section(
    title: str,
    content: Callable[[], None],
    *,
    description: str | None = None,
    actions: Sequence[ui.Button] | None = None,
) -> None:
    """Compose a section with header + content block."""

    with ui.column().classes("gap-2"):
        with ui.row().classes("justify-between items-center"):
            ui.label(title).classes("text-lg font-semibold viewer-heading")
            if actions:
                with ui.row().classes("gap-2"):
                    for action in actions:
                        action()
        if description:
            ui.label(description).classes("text-sm viewer-muted")
        content()


def arabic_text(content: str) -> ui.label:
    """Render Arabic text with RTL direction and Amiri typography."""

    label = ui.label(content).classes("arabic-text")
    label.props("dir=rtl")
    return label
