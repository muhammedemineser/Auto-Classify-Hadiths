from __future__ import annotations

import os
import time
from pathlib import Path
from types import SimpleNamespace
from nicegui import ui as nice_ui

from tools.tafsir_gui.core.runner import RetryLater
from tools.tafsir_gui.core.state import StepState
from tools.tafsir_gui.tests.support import FakeGeminiClient

from tools.tafsir_gui import main as main_mod

runner = main_mod.runner
state = main_mod.state
build_ui = main_mod.build_ui


class ImmediateScheduler:
    def __init__(self):
        self.job = None

    def schedule_in(self, seconds: int, action):
        self.job = time.time() + seconds
        action()

    def schedule_resume(self, when, action):
        self.schedule_in(0, action)

    def cancel(self):
        self.job = None

    def shutdown(self):
        self.job = None


def _patch_ui_run():
    orig_run = nice_ui.run

    def patched_run(*args, **kwargs):
        port = int(os.environ.get("APP_PORT", "8080"))
        kwargs.setdefault("host", "127.0.0.1")
        kwargs.setdefault("port", port)
        return orig_run(*args, **kwargs)

    nice_ui.run = patched_run
    main_mod.ui.run = patched_run


def _configure_runner_for_scenario(scenario: str):
    runner.scheduler = ImmediateScheduler()

    def base_step(name: str):
        return SimpleNamespace(
            name=name,
            title=name,
            action=lambda *_: None,
            status=StepState(name),
        )

    if scenario == "rate_limit":
        def failing_step(_ctx):
            raise RetryLater(1)

        runner._steps = lambda ctx: [
            SimpleNamespace(
                name="rate",
                title="Rate Limit",
                action=failing_step,
                status=StepState("rate"),
            )
        ]
    elif scenario == "error":
        def failing_step(_ctx):
            raise RuntimeError("Mock failure")

        runner._steps = lambda ctx: [
            SimpleNamespace(
                name="error",
                title="Error",
                action=failing_step,
                status=StepState("error"),
            )
        ]
    else:
        runner._steps = lambda ctx: [
            base_step("ingest"),
            base_step("finalize"),
        ]


def _patch_gemini_behavior(behavior: str):
    def factory(*args, **kwargs):
        return FakeGeminiClient(behavior=behavior)

    import tools.tafsir_gui.core.preflight as preflight_mod
    import tools.tafsir_gui.integrations.gemini as gemini_mod

    preflight_mod.GeminiClient = factory
    gemini_mod.GeminiClient = factory


def _ensure_state():
    state.api_key = state.api_key or "test-key"
    if state.input_path is None:
        input_path = os.environ.get("TAFSIR_TEST_INPUT")
        if input_path:
            state.input_path = Path(input_path)


def main():
    _patch_ui_run()
    scenario = os.environ.get("TAFSIR_TEST_SCENARIO", "happy")
    _configure_runner_for_scenario(scenario)
    behavior = "ok" if scenario != "invalid_key" else "invalid"
    _patch_gemini_behavior(behavior)
    _ensure_state()
    build_ui(test_mode=True)


if __name__ == "__main__":
    main()
