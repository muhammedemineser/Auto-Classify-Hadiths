from __future__ import annotations

from pathlib import Path
from typing import Callable

from nicegui import ui
from .. import compat

from ...utils import env as env_utils
from ...utils.gcp_instructions import generate_instructions


def gcp_setup(state, on_save: Callable[[], None], on_test_key: Callable[[], None]):
    ui.label("Google Cloud Setup (Gemini)").classes("text-lg font-semibold")
    with ui.row():
        ui.link(
            "Open Google Cloud Console", "https://console.cloud.google.com"
        ).classes("themed-button primary")

        compat.toggle(
            ["Console-first", "CLI-assisted"],
            value=state.gcp_mode if hasattr(state, "gcp_mode") else "Console-first",
            on_change=lambda e: setattr(state, "gcp_mode", e.value),
        )
        compat.checkbox(
            "I don’t have gcloud (show UI-only steps)",
            value=getattr(state, "gcp_no_cli", False),
            on_change=lambda e: _update_state(state, "gcp_no_cli", e.value, on_save),
        )

    with ui.row():
        ui.input(
            "Project name",
            value=getattr(state, "gcp_project_name", state.project_name),
            on_change=lambda e: _update_state(
                state, "gcp_project_name", e.value, on_save
            ),
        )
        ui.input(
            "Billing country (optional)",
            value=getattr(state, "billing_country", ""),
            on_change=lambda e: _update_state(
                state, "billing_country", e.value, on_save
            ),
        )
        ui.input(
            "Org / Folder (optional)",
            value=getattr(state, "org_folder", ""),
            on_change=lambda e: _update_state(state, "org_folder", e.value, on_save),
        )

    ui.separator()
    checklist_items = [
        "Create/select project",
        "Enable Generative Language API",
        "Create API key",
        "Paste key and Test",
        "Check quotas (if needed)",
    ]
    ui.label("Checklist (mark as Done)").classes("font-semibold")
    for item in checklist_items:
        current = getattr(state, "gcp_checklist", {}).get(item, "Not started")
        ui.select(
            ["Not started", "Done"],
            value=current,
            label=item,
            on_change=lambda e, item=item: _update_checklist(
                state, item, e.value, on_save
            ),
        )

    ui.separator()
    ui.label("Required inputs summary").classes("font-semibold")
    ui.markdown(
        f"- Project: **{getattr(state, 'gcp_project_name', state.project_name)}**\n"
        f"- API: Gemini / Generative Language\n"
        f"- Billing country: {getattr(state, 'billing_country', 'n/a') or 'n/a'}\n"
        f"- Org/Folder: {getattr(state, 'org_folder', 'n/a') or 'n/a'}"
    )

    ui.separator()
    ui.button(
        "Generate instructions", on_click=lambda: _generate_and_render(state, on_save)
    ).props("color=primary")
    instructions_area = ui.expansion("Generated instructions", value=True)
    state._gcp_instructions_area = instructions_area
    _render_instructions(state, instructions_area)

    ui.separator()
    ui.input(
        "Paste API key",
        value=state.api_key,
        password=True,
        on_change=lambda e: _paste_key(state, e.value, on_save, on_test_key),
    )
    ui.button("Test key now", on_click=on_test_key)
    if not hasattr(state, "_key_status_label"):
        state._key_status_label = ui.label(_key_status_text(state))

    ui.separator()
    ui.label("Troubleshooting").classes("font-semibold")
    with ui.expansion("API key is invalid", icon="error_outline"):
        ui.markdown(
            "- Recreate the key on the Credentials page (API keys).\n"
            "- Ensure you copied the full key without spaces.\n"
            "- Verify the key is for the correct project."
        )
    with ui.expansion("Quota exceeded / rate limited", icon="schedule"):
        ui.markdown(
            "- Open Quotas page; look for Generative Language limits.\n"
            "- Wait for reset window or reduce request rate.\n"
            "- Consider enabling billing or requesting quota increase."
        )
    with ui.expansion("API not enabled", icon="toggle_off"):
        ui.markdown("Enable Generative Language API via API Library, then retry.")
    with ui.expansion("Billing required", icon="credit_card"):
        ui.markdown(
            "Attach a billing account on Billing page. Some regions require billing before enabling the API."
        )

    ui.separator()
    ui.button("Copy diagnostics", on_click=lambda: _copy_diagnostics(state))


def _key_status_text(state):
    status = getattr(state, "api_key_status", "Unknown")
    return f"Key status: {status}"


def _copy_diagnostics(state):
    masked = env_utils.mask_secret(state.api_key or "")
    last = getattr(state, "preflight_results", [])
    payload = f"API key (masked): {masked}\nStatus: {getattr(state, 'api_key_status', 'Unknown')}\nPreflight: {last}"
    ui.run_javascript(f"navigator.clipboard.writeText(`{payload}`);")
    ui.notify("Diagnostics copied (non-sensitive).")


def _update_state(state, field, value, on_save):
    setattr(state, field, value)
    on_save()
    if field == "gcp_no_cli" and hasattr(state, "_gcp_instructions_area"):
        area = state._gcp_instructions_area
        area.clear()
        _render_instructions(state, area)


def _update_checklist(state, item, value, on_save):
    if not hasattr(state, "gcp_checklist"):
        state.gcp_checklist = {}
    state.gcp_checklist[item] = value
    on_save()


def _generate_and_render(state, on_save):
    instr = generate_instructions(
        getattr(state, "gcp_project_name", state.project_name),
        getattr(state, "billing_country", None),
        getattr(state, "org_folder", None),
    )
    state.gcp_instructions = instr
    on_save()
    if hasattr(state, "_gcp_instructions_area"):
        area = state._gcp_instructions_area
        area.clear()
        _render_instructions(state, area)


def _render_instructions(state, container):
    instr = getattr(state, "gcp_instructions", None)
    if not instr:
        return
    with container:
        ui.label("Console-first").classes("font-semibold")
        ui.code(instr.console_block, wrap=True).classes("w-full")
        ui.button(
            "Copy console instructions",
            on_click=lambda: ui.run_javascript(
                f"navigator.clipboard.writeText(`{instr.console_block}`);"
            ),
        )
        if not getattr(state, "gcp_no_cli", False):
            ui.label("CLI-assisted").classes("font-semibold")
            ui.code(instr.cli_block, wrap=True).classes("w-full")
            ui.button(
                "Copy CLI instructions",
                on_click=lambda: ui.run_javascript(
                    f"navigator.clipboard.writeText(`{instr.cli_block}`);"
                ),
            )
        ui.label("Deep links").classes("font-semibold")
        for name, url in instr.urls.items():
            ui.link(name.replace("_", " ").title(), url)


def _paste_key(state, value, on_save, on_test_key):
    state.api_key = value
    env_utils.write_env({"GEMINI_API_KEY": value})
    on_save()
    on_test_key()


__all__ = ["gcp_setup"]
