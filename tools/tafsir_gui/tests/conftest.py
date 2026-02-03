from __future__ import annotations

import shutil
from pathlib import Path
import importlib
import sys

import pytest

# Bridge for the legacy pages.compat import that incorrectly lives at ui/compat.py
_compat_module = importlib.import_module("tools.tafsir_gui.ui.compat")
_pages_pkg = importlib.import_module("tools.tafsir_gui.ui.pages")
setattr(_pages_pkg, "compat", _compat_module)
sys.modules["tools.tafsir_gui.ui.pages.compat"] = _compat_module

# Fixture directory inside tests/fixtures
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def sample_files(tmp_path: Path) -> dict[str, Path]:
    """Copies the curated fixtures into a temporary directory for tests."""
    files: dict[str, Path] = {}
    for name in ("sample.txt", "sample.csv", "sample.pdf", "sample.db"):
        source = FIXTURES_DIR / name
        target = tmp_path / name
        shutil.copy(source, target)
        files[name] = target
    return files
