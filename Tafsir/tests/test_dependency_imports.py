"""
Ensure every intentionally bundled dependency can be imported.
"""

import importlib
from typing import List

import pytest


REQUIRED_MODULES: List[str] = [
    "duckdb",
    "sqlalchemy",
    "dotenv",
    "google.genai",
    "pyautogui",
    "pyperclip",
    "mss",
    "numpy",
    "fastapi",
    "uvicorn",
    "regex",
    "bs4",
]


@pytest.mark.parametrize("module_name", REQUIRED_MODULES)
def test_required_module_import(module_name: str):
    """
    Import each dependency expected by the current project stack.
    """
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise AssertionError(
            f"{module_name} cannot be imported; make sure it is listed in requirements.txt."
        ) from exc
