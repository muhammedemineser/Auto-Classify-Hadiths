from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List
import json

from loguru import logger
from nicegui import app, ui

# Ensure package imports work even when executed as a plain script
if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from Tafsir.pipeline.gemini_gui.PROMPT_PREFIX import PROMPT_PREFIX

from tools.tafsir_gui.core.events import EventBus
from tools.tafsir_gui.core.preflight import (
    CheckResult,
    all_checks_green,
    run_preflight,
    check_api_key,
)
from tools.tafsir_gui.core.runner import PipelineRunner
from tools.tafsir_gui.core.scheduler import ResumeScheduler
from tools.tafsir_gui.core.state import RunContext
from tools.tafsir_gui.core.adapters import (
    DefaultGeminiFactory,
    LegacyPipelineAdapter,
    UniversalPipelineAdapter,
)
from tools.tafsir_gui.integrations.gemini import GeminiClient
from tools.tafsir_gui.ui.pages import (
    onboarding,
    settings,
    files,
    run as run_page,
    artifacts as artifacts_page,
    gcp_setup,
)
from tools.tafsir_gui.ui.theme import components
from tools.tafsir_gui.ui.theme import state as theme_state
from tools.tafsir_gui.utils import env as env_utils, metadata as metadata_utils
from tools.tafsir_gui.utils.logging import configure_logging


@dataclass
class GUIState:
    project_name: str = "tafsir_gui_run"
    output_dir: Path = env_utils.REPO_ROOT / "tools" / "tafsir_gui" / "projects"
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    cache_name: str | None = os.getenv("GEMINI_CACHE_NAME", None)
    model_id: str = os.getenv("GEMINI_MODEL_ID", "models/gemini-2.5-pro")
    rollback_api_key: str | None = os.getenv("GEMINI_API_KEY_ROLLBACK", None)
    rollback_cache: str | None = os.getenv("GEMINI_API_KEY_ROLLBACK_CACHE", None)
    input_path: Path | None = None
    start_id: int | None = None
    exact_ids: List[int] | None = None
    preflight_results: List[CheckResult] = field(default_factory=list)
    file_preview: object | None = None
    mode: str = "legacy"
    api_key_status: str = "Unknown"
    gcp_project_name: str = "tafsir_gui_run"
    billing_country: str = ""
    org_folder: str = ""
    gcp_checklist: dict = field(default_factory=dict)
    gcp_instructions: object | None = None
    gcp_no_cli: bool = False
    gcp_mode: str = "Console-first"


state = GUIState()
bus = EventBus()
scheduler = ResumeScheduler()
runner = PipelineRunner(
    bus,
    scheduler,
    gemini_factory=DefaultGeminiFactory(),
    legacy_adapter=LegacyPipelineAdapter(),
    universal_adapter=UniversalPipelineAdapter(),
    test_mode=False,
)

THEME_DIR = Path(__file__).resolve().parent / "ui" / "theme"
THEME_STATIC_ROUTE: str | None = "/tafsir-theme" if THEME_DIR.is_dir() else None
if THEME_STATIC_ROUTE:
    app.add_static_files(THEME_STATIC_ROUTE, str(THEME_DIR))


def _attach_theme_link():
    if not THEME_STATIC_ROUTE or getattr(_attach_theme_link, "_attached", False):
        return
    ui.run_javascript(
        f"""
        (function() {{
            if (document.head.querySelector('link[data-tafsir-theme]')) return;
            const link = document.createElement('link');
            link.rel = 'stylesheet';
            link.dataset.tafsirTheme = '1';
            link.href = '{THEME_STATIC_ROUTE}/theme.css';
            document.head.appendChild(link);
        }})();
        """
    )
    _attach_theme_link._attached = True


def _inject_quasar_override_script():
    if getattr(_inject_quasar_override_script, "_injected", False):
        return
    ui.run_javascript(
        """
        (function() {
            if (document.head.querySelector('style[data-tafsir-override]')) return;
            const style = document.createElement('style');
            style.dataset.tafsirOverride = '1';
            style.textContent = `
                .q-tree__node-header-content,
                .q-tree__node-header-content * {
                    color: var(--ink) !important;
                }
            `;
            document.head.appendChild(style);
        })();
        """
    )
    _inject_quasar_override_script._injected = True


def _reinforce_layout_shell():
    if getattr(_reinforce_layout_shell, "_done", False):
        return
    ui.run_javascript(
        """
        (function() {
            const styleId = 'tafsir-layout-shell';
            if (document.head.querySelector(`#${styleId}`)) return;
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = `
                .layout-shell {
                    display: grid !important;
                    grid-template-columns: minmax(0, 1fr) 360px !important;
                    gap: 24px !important;
                    align-items: start !important;
                    width: 100% !important;
                }
                .cards {
    display: flex;
    flex-direction: column;
    width: 100%;
}
#c34 > div.q-stepper__step-content > div > label> div {
width:100% !important;}

.cards > * {
    width: 100%;
    flex: 1 1 auto;
}
div.q-page-container {
padding-top:0 !important;}
                @media (max-width: 1279px) {
                    .layout-shell {
                        grid-template-columns: 1fr !important;
                    }
                }
            `;
            document.head.appendChild(style);
        })();
        """
    )
    _reinforce_layout_shell._done = True


MODE_TOOLTIP_TEXT = {
    "legacy": "Legacy mode uses the tafsir-specific modules and existing pipeline",
    "universal": "Universal mode applies AI-driven schema, rules, and guards",
}

GLOBAL_INPUT_OVERRIDES = """
    /* Tooltip styling is kept in JS for positioning, but we reinforce it here for overrides. */
    #tafsir-mode-tooltip {
        position: fixed !important;
        padding: 6px 12px !important;
        font-size: 12px !important;
        border-radius: 10px !important;
        background: rgba(15, 23, 42, 0.95) !important;
        color: white !important;
        pointer-events: none !important;
        opacity: 0;
        transition: opacity 0.15s ease, transform 0.15s ease !important;
        transform: translate(-50%, -120%) !important;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.45) !important;
        white-space: normal !important;
        max-width: 240px !important;
        z-index: 9999 !important;
        text-align: center !important;
        font-weight: 500 !important;
    }
    input,
    textarea,
    select,
    .q-field,
    .q-input,
    .q-textarea,
    .q-select,
    .q-field__control,
    .q-field__native,
    .q-field__control .q-field__native,
    .q-field__control .q-field__native-input,
    .q-field__control .q-select__control,
    .themed-input * {
        width: 100% !important;
        min-width: 0 !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }

    .mode-switch-pill {
        min-width: 90px !important;
    }
"""


def _inject_mode_tooltips():
    tooltip_data = json.dumps(MODE_TOOLTIP_TEXT)
    # Create a tooltip element and watch for buttons with the data attribute.
    js = f"""
        (function() {{
            const bootstrap = () => {{
                if (window.tafsirModeTooltipInjected) return;
                window.tafsirModeTooltipInjected = true;
                const tooltipTexts = {tooltip_data};
                const tooltip = document.createElement('div');
                tooltip.id = 'tafsir-mode-tooltip';
                tooltip.setAttribute('role', 'tooltip');
                tooltip.dataset.active = 'false';
                document.body.appendChild(tooltip);

                const positionTooltip = (btn) => {{
                    const rect = btn.getBoundingClientRect();
                    const top = Math.max(70, rect.bottom + 70);
                    tooltip.style.left = `${{rect.left + rect.width / 2}}px`;
                    tooltip.style.top = `${{top}}px`;
                }};

                const showTooltip = (event) => {{
                    const btn = event.currentTarget;
                    const text = tooltipTexts[btn.dataset.tooltipMode];
                    if (!text) return;
                    tooltip.textContent = text;
                    positionTooltip(btn);
                    tooltip.dataset.active = 'true';
                    tooltip.style.opacity = '1';
                }};

                const hideTooltip = () => {{
                    tooltip.dataset.active = 'false';
                    tooltip.style.opacity = '0';
                }};

                const attachTooltipTargets = () => {{
                    document.querySelectorAll('[data-tooltip-mode]').forEach((btn) => {{
                        if (btn.tafsirModeTooltipBound) return;
                        btn.tafsirModeTooltipBound = true;
                        btn.addEventListener('mouseenter', showTooltip);
                        btn.addEventListener('focus', () => showTooltip({{ currentTarget: btn }}));
                        btn.addEventListener('mouseleave', hideTooltip);
                        btn.addEventListener('blur', hideTooltip);
                        btn.addEventListener('mousemove', () => positionTooltip(btn));
                    }});
                }};

                attachTooltipTargets();
                const observer = new MutationObserver(() => attachTooltipTargets());
                observer.observe(document.body, {{ childList: true, subtree: true }});
            }};

            const ensureReady = () => {{
                if (document.body) {{
                    bootstrap();
                }} else {{
                    requestAnimationFrame(ensureReady);
                }}
            }};

            ensureReady();
        }})();
        """
    ui.run_javascript(js)


def _inject_global_overrides():
    css = GLOBAL_INPUT_OVERRIDES.replace("`", "\\`")
    ui.run_javascript(
        f"""
        (function() {{
            if (document.head.querySelector('#tafsir-global-overrides')) return;
            const style = document.createElement('style');
            style.id = 'tafsir-global-overrides';
            style.textContent = `{css}`;
            document.head.appendChild(style);
        }})();
        """
    )


def ensure_output_dir():
    state.output_dir.mkdir(parents=True, exist_ok=True)


def project_root() -> Path:
    return state.output_dir / state.project_name


def project_changed():
    ensure_output_dir()
    state.gcp_project_name = state.project_name
    load_metadata()


def save_metadata():
    data = {
        "gcp_project_name": state.gcp_project_name,
        "billing_country": state.billing_country,
        "org_folder": state.org_folder,
        "gcp_checklist": state.gcp_checklist,
        "gcp_no_cli": state.gcp_no_cli,
        "gcp_mode": state.gcp_mode,
    }
    metadata_utils.save_metadata(project_root(), data)


def load_metadata():
    data = metadata_utils.load_metadata(project_root())
    if not data:
        return
    state.gcp_project_name = data.get("gcp_project_name", state.gcp_project_name)
    state.billing_country = data.get("billing_country", state.billing_country)
    state.org_folder = data.get("org_folder", state.org_folder)
    state.gcp_checklist = data.get("gcp_checklist", state.gcp_checklist)
    state.gcp_no_cli = data.get("gcp_no_cli", state.gcp_no_cli)
    state.gcp_mode = data.get("gcp_mode", state.gcp_mode)


def render_preflight(panel):
    panel.clear()
    with panel:
        ui.label("Pre-flight checklist").classes("text-lg font-semibold viewer-heading")
        if not state.preflight_results:
            ui.label("Run pre-flight to see status.").classes("text-sm viewer-muted")
        for res in state.preflight_results:
            variant = "success" if res.ok else "warning"
            components.themed_badge(f"{res.name}: {res.as_badge()}", variant=variant)
            ui.label(res.details).classes("text-sm viewer-muted")
            if res.remediation:
                ui.label(f"Next steps: {res.remediation}").classes(
                    "text-xs viewer-muted"
                )


def do_preflight(preflight_panel, run_panel):
    if not state.input_path:
        ui.notify("Select an input file first.", type="warning")
        return
    ensure_output_dir()
    results = run_preflight(
        input_path=state.input_path,
        output_dir=state.output_dir / state.project_name,
        api_key=state.api_key,
        model_id=state.model_id,
        cache_name=state.cache_name,
        prompt_prefix=PROMPT_PREFIX,
        db_name=state.project_name,
        mode=state.mode,
    )
    state.preflight_results = results
    _update_api_key_status_from_results(results)
    render_preflight(preflight_panel)
    all_green = all_checks_green(results)
    run_panel.set_start_enabled(all_green)
    if all_green:
        ui.notify(
            "All pre-flight checks are green. You can start the pipeline.",
            type="positive",
        )
    else:
        ui.notify("Pre-flight has issues. See checklist.", type="warning")


def generate_cache(preflight_panel):
    if not state.api_key:
        ui.notify("API key required", type="warning")
        return
    try:
        client = GeminiClient(api_key=state.api_key, cache_name=state.cache_name)
        name = client.ensure_cache(PROMPT_PREFIX)
        state.cache_name = name
        ui.notify("Cache generated", type="positive")
    except Exception as exc:
        ui.notify(f"Cache generation failed: {exc}", type="warning")
    render_preflight(preflight_panel)


def test_api_key_only():
    if not state.api_key:
        ui.notify("Paste an API key first.", type="warning")
        return
    result = check_api_key(state.api_key, state.model_id)
    _update_api_key_status_from_results([result])
    if result.ok:
        ui.notify("API key validated.", type="positive")
    else:
        ui.notify(f"API key failed: {result.details}", type="warning")


def start_pipeline():
    if not all_checks_green(state.preflight_results):
        ui.notify("Pre-flight must be green before starting.", type="warning")
        return
    ctx = RunContext(
        project_name=state.project_name,
        input_path=state.input_path,
        output_dir=state.output_dir,
        mode=state.mode,
        api_key=state.api_key,
        cache_name=state.cache_name,
        model_id=state.model_id,
        rollback_api_key=state.rollback_api_key,
        rollback_cache=state.rollback_cache,
        start_id=state.start_id,
        exact_ids=state.exact_ids,
    )
    runner.start(ctx, state.preflight_results)


def pause_pipeline():
    runner.pause()
    ui.notify("Pipeline paused.", type="warning")


def resume_pipeline():
    runner.resume()
    ui.notify("Pipeline resumed.", type="positive")


def cancel_pipeline():
    runner.cancel()
    ui.notify("Pipeline cancelled.", type="warning")


def _update_api_key_status_from_results(results: List[CheckResult]):
    status = "Unknown"
    for res in results:
        if res.name == "api_key":
            if res.ok:
                status = "Valid"
            elif "rate" in res.details.lower():
                status = "Rate-limited"
            else:
                status = "Invalid"
            break
    state.api_key_status = status
    if hasattr(state, "_key_status_label"):
        state._key_status_label.text = f"Key status: {status}"


def build_ui(test_mode: bool = False):
    configure_logging()
    env_utils.load_env()
    ensure_output_dir()
    load_metadata()
    ui.timer(
        0,
        lambda: (
            _attach_theme_link(),
            _inject_quasar_override_script(),
            _reinforce_layout_shell(),
            _inject_global_overrides(),
            _inject_mode_tooltips(),
        ),
        once=True,
    )
    theme_state.initialize()
    ui.page_title("Text Manipulation GUI")

    preflight_card_ref = {"panel": None}
    run_panel_ref = {"panel": None}

    def trigger_preflight():
        panel = preflight_card_ref.get("panel")
        runner_panel = run_panel_ref.get("panel")
        if panel and runner_panel:
            do_preflight(panel, runner_panel)

    def toggle_theme():
        theme_state.toggle_color_mode()

    def _set_mode(value: str):
        if state.mode == value:
            return
        state.mode = value
        theme_state.set_pipeline_mode(value)
        if hasattr(state, "_mode_label"):
            state._mode_label.text = f"Mode: {state.mode}"

    with ui.header().classes("q-header"):
        header_status = ui.label(f"Key status: {state.api_key_status}").classes(
            "status-line hidden"
        )
        state._key_status_label = header_status
        with ui.row().classes("header-top justify-between items-center"):
            with ui.row().classes("brand gap-2"):
                ui.label("Text Manipulation Pipeline").classes(
                    "ml-5 text-xl font-semibold"
                )
                ui.label("With XML Annotations").classes("eyebrow")
            with ui.row().classes("toolbar gap-2"):
                components.themed_button(
                    "Run pre-flight checks",
                    on_click=lambda *_: trigger_preflight(),
                    variant="primary",
                )
                components.themed_button(
                    "Toggle theme",
                    on_click=lambda *_: toggle_theme(),
                    variant="ghost",
                )
                with ui.row().classes("mode-switch"):
                    components.themed_button(
                        "Legacy",
                        on_click=lambda *_: _set_mode("legacy"),
                        variant="ghost",
                    ).classes("mode-switch-pill").props("data-tooltip-mode=legacy")
                    components.themed_button(
                        "Universal",
                        on_click=lambda *_: _set_mode("universal"),
                        variant="ghost",
                    ).classes("mode-switch-pill ml-0 mr-0").props(
                        "data-tooltip-mode=universal"
                    )
                with ui.row().classes("controls-grid toolbar-grid"):

                    with ui.row().classes("items-center gap-2"):
                        state._mode_label = ui.label(f"Mode: {state.mode}").classes(
                            "text-sm inline-block ml-0 mr-0 border-2 border-dashed border-blue-500 rounded-lg p-4 w-[160px]"
                        )
                        ui.label(f"Key status: {state.api_key_status}").classes(
                            "text-sm inline-block ml-0 mr-0 border-2 border-dashed border-blue-500 rounded-lg p-4 w-[190px]"
                        )

    stepper_ref = {"obj": None}

    def jump_to(name: str) -> None:
        stepper = stepper_ref.get("obj")
        if stepper:
            stepper.value = name  # NiceGUI stepper navigates via `.value`

    preflight_card = None
    run_panel = None
    artifacts_card = None

    with ui.element("div").classes("layout-shell mt-6 w-full white-text"):
        with ui.column().classes("main-panel gap-4 cards"):
            with ui.stepper().props("vertical") as stepper:
                stepper_ref["obj"] = stepper

                with ui.step("A", "Welcome / Guided onboarding"):
                    onboarding.render()
                    ui.button("Next", on_click=stepper.next)

                with ui.step("B", "Create project / Choose output directory"):
                    settings.project_settings(
                        state,
                        on_change=lambda *_: project_changed(),  # only fires when the user changes input
                    )
                    ui.button("Next", on_click=stepper.next)

                with ui.step("C", "Google Cloud Setup"):
                    gcp_setup.gcp_setup(state, save_metadata, test_api_key_only)
                    ui.button("Next", on_click=stepper.next)

                with ui.step("D", "API Key & Settings"):
                    settings.api_settings(state, lambda: None)
                    ui.button("Next", on_click=stepper.next)

                with ui.step("E", "Cache Key"):
                    settings.cache_settings(
                        state,
                        lambda: None,
                        lambda: generate_cache(preflight_card),
                    )
                    ui.button("Next", on_click=stepper.next)

                with ui.step("F", "Add input file"):
                    files.file_inputs(state, lambda: None)
                    ui.button("Next", on_click=stepper.next)

                with ui.step("G", "Parsing / Extraction"):
                    ui.label(
                        "Parsing is automatic once the pipeline starts. Make sure the file preview looks correct."
                    )
                    ui.button("Next", on_click=stepper.next)

                with ui.step("H", "Structure discovery via Gemini"):
                    ui.label(
                        "The runner will sample your input and ask Gemini for structure rules. No action needed."
                    )
                    ui.button("Next", on_click=stepper.next)

                with ui.step("I", "Derive DB schema + create table(s)"):
                    ui.label(
                        "Schema creation runs during pipeline; ensure output dir is writable."
                    )
                    ui.button("Next", on_click=stepper.next)

                with ui.step("J", "Run annotation / LLM pipeline"):
                    ui.label("Use the controls on the right to start, pause, resume.")
                    ui.button("Next", on_click=stepper.next)

                with ui.step("K", "Bulk inserts + finalize + export/report"):
                    ui.label(
                        "Upon completion you can inspect the annotated DB under the project folder."
                    )
                    ui.button("Back to controls", on_click=lambda: jump_to("J"))  # FIX

        section_nodes = [
            {"id": "A", "label": "A) Welcome", "value": "A"},
            {"id": "B", "label": "B) Project & Output", "value": "B"},
            {"id": "C", "label": "C) Google Cloud Setup", "value": "C"},
            {"id": "D", "label": "D) API", "value": "D"},
            {"id": "E", "label": "E) Cache", "value": "E"},
            {"id": "F", "label": "F) Input", "value": "F"},
            {"id": "G", "label": "G) Parsing", "value": "G"},
            {"id": "H", "label": "H) Structure", "value": "H"},
            {"id": "I", "label": "I) Schema", "value": "I"},
            {"id": "J", "label": "J) Annotation", "value": "J"},
            {"id": "K", "label": "K) Finalize", "value": "K"},
        ]

        with ui.column().classes("legend-panel gap-4"):
            ui.label("Navigation").classes("text-lg font-semibold")
            ui.tree(
                section_nodes,
                on_select=lambda e: jump_to(e.value),  # FIX
            )

            preflight_card = components.themed_card(
                content=lambda card: render_preflight(card)
            )
            preflight_card_ref["panel"] = preflight_card

            components.themed_button(
                "Run pre-flight checks",
                on_click=lambda *_: trigger_preflight(),
                variant="primary",
            )

            ui.separator()

            run_panel = run_page.RunPanel(
                on_start=start_pipeline,
                on_pause=pause_pipeline,
                on_resume=resume_pipeline,
                on_cancel=cancel_pipeline,
                bus=bus,
            )
            run_panel.set_start_enabled(False)
            run_panel_ref["panel"] = run_panel

            ui.separator()

            artifacts_card = components.themed_card(
                content=lambda card: artifacts_page.render(
                    getattr(state, "artifacts", {})
                )
            )

            def _bus_listener(ev):
                data = getattr(ev, "data", {}) or {}
                artifacts = data.get("artifacts")
                if artifacts:
                    state.artifacts = {k: Path(v) for k, v in artifacts.items()}
                    artifacts_card.clear()
                    with artifacts_card:
                        artifacts_page.render(state.artifacts)

            bus.subscribe(_bus_listener)

    ui.run(title="Tafsir GUI", reload=False)


@app.on_shutdown
def _shutdown():
    scheduler.shutdown()


if __name__ in {"__main__", "__mp_main__"}:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Use dummy adapters and no external calls",
    )
    args = parser.parse_args()
    if args.test_mode:
        runner.test_mode = True
    build_ui(test_mode=args.test_mode)
