from __future__ import annotations

import os
from pathlib import Path

# Repo layout
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # .../Tafsir
REPO_ROOT = PROJECT_ROOT.parent  # repository root (classify)

# Centralized directories (override via environment if needed)
BOOKS_DIR = Path(os.getenv("SOURCE_DIR", PROJECT_ROOT / "tafsir_books"))
ANNOTATED_DIR = Path(os.getenv("ANNOTATED_DIR", PROJECT_ROOT / "tafsir_books_annotated"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", PROJECT_ROOT / "logs"))
CONFIG_DIR = Path(os.getenv("CONFIG_DIR", PROJECT_ROOT / "config"))

# Defaults for tafsir selection
DEFAULT_TAFSIR = os.getenv("DEFAULT_TAFSIR", "katheer")

# Ensure commonly-used directories exist (no-op if already present)
for _path in (LOGS_DIR, CONFIG_DIR):
    try:
        _path.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Creation is best-effort; failures are tolerated to keep imports cheap.
        pass

