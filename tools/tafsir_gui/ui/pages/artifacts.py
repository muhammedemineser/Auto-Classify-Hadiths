from __future__ import annotations

from pathlib import Path

from nicegui import ui


def render(artifacts: dict):
    ui.label("Artifacts").classes("text-lg font-semibold")
    if not artifacts:
        ui.label("No artifacts yet. Run the pipeline to generate schema, rules, and prompt versions.")
        return
    for key, path in artifacts.items():
        ui.label(f"{key}: {path}")
        if Path(path).suffix in {".json", ".txt"} and Path(path).exists():
            content = Path(path).read_text(encoding="utf-8")
            ui.expansion(key, icon="description", value=False).props("dense").slots[
                "default"
            ](lambda: ui.code(content, language="json" if path.endswith(".json") else "text", wrap=True).classes("w-full max-h-48"))


__all__ = ["render"]
