from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def metadata_path(project_root: Path) -> Path:
    return project_root / "metadata.json"


def load_metadata(project_root: Path) -> Dict[str, Any]:
    path = metadata_path(project_root)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_metadata(project_root: Path, data: Dict[str, Any]) -> None:
    path = metadata_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


__all__ = ["load_metadata", "save_metadata", "metadata_path"]
