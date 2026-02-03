import importlib
import os
import subprocess
import sys


MODULES = [
    "tools.tafsir_gui.main",
    "tools.tafsir_gui.core.runner",
    "tools.tafsir_gui.core.preflight",
    "tools.tafsir_gui.core.scheduler",
    "tools.tafsir_gui.core.events",
    "tools.tafsir_gui.core.state",
    "tools.tafsir_gui.core.adapters",
    "tools.tafsir_gui.integrations.gemini",
    "tools.tafsir_gui.utils.env",
    "tools.tafsir_gui.utils.logging",
    "tools.tafsir_gui.ui.pages.gcp_setup",
    "tools.tafsir_gui.ui.pages.run",
    "tools.tafsir_gui.ui.pages.artifacts",
    "tools.tafsir_gui.utils.metadata",
]


def test_import_modules():
    for mod in MODULES:
        importlib.import_module(mod)


def test_module_entrypoint_invocation():
    env = os.environ.copy()
    env.pop("PYTEST_CURRENT_TEST", None)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "tools.tafsir_gui.main", "--test-mode"],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired as exc:
        assert "Traceback" not in (exc.stderr or "")
    else:
        assert result.returncode == 0 or "NiceGUI ready" in result.stdout
