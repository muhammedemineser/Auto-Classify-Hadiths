"""
Ensure every intentionally bundled dependency can be imported so a Docker build
that runs ``pip install ...`` and ``pipenv install --system`` will succeed.
"""

import importlib
from typing import Iterable, List

import pytest


REQUIRED_MODULES: List[str] = [
    "duckdb",
    "sqlalchemy",
    "tenacity",
    "apscheduler",
    "loguru",
    "dotenv",
    "pypdf",
    "google.genai",
    "nicegui",
    "playwright",
    "pyautogui",
    "pyperclip",
]


@pytest.mark.parametrize("module_name", REQUIRED_MODULES)
def test_required_module_import(module_name: str):
    """
    Import each dependency that the Docker stack expects before the build runs.
    """
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise AssertionError(
            f"{module_name} cannot be imported; make sure it is listed under "
            "the installation requirements (Pipfile/requirements.txt)."
        ) from exc
