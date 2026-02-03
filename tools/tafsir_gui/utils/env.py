"""Environment utilities for the Tafsir GUI layer.

This module is read-only with respect to the existing codebase; it only writes
to the `.env` file when explicitly requested by the GUI. Secrets are masked
whenever they are echoed to logs or the UI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv

REPO_MARKERS = {".git", "README.md", "Tafsir"}


def find_repo_root(start: Optional[Path] = None) -> Path:
    """Return the repository root by walking upward until markers are found."""
    current = (start or Path(__file__).resolve()).expanduser()
    for parent in [current, *current.parents]:
        if any((parent / marker).exists() for marker in REPO_MARKERS):
            return parent
    return current


REPO_ROOT = find_repo_root()
ENV_PATH = REPO_ROOT / ".env"


def mask_secret(value: str | None, visible: int = 4) -> str:
    """Return a masked version of a secret for safe display."""
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}***{value[-visible:]}"


def load_env(path: Path = ENV_PATH) -> Dict[str, str]:
    """Load .env into os.environ and return the resulting mapping."""
    if path.exists():
        load_dotenv(path)
    return {k: v for k, v in os.environ.items()}


def read_env(path: Path = ENV_PATH) -> Dict[str, str]:
    """Parse the .env file into a dict without mutating os.environ."""
    data: Dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def write_env(updates: Dict[str, str], path: Path = ENV_PATH) -> Path:
    """
    Merge `updates` into the .env file. Existing keys are updated, new keys are
    appended. The function preserves simple KEY=VALUE format.
    """
    existing = read_env(path)
    existing.update({k: v for k, v in updates.items() if v is not None})
    lines = [f"{k}={v}" for k, v in existing.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


__all__ = [
    "ENV_PATH",
    "REPO_ROOT",
    "find_repo_root",
    "load_env",
    "read_env",
    "write_env",
    "mask_secret",
]
