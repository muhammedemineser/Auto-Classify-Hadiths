from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional


class ArtifactStore:
    """Versioned artifact storage under a project folder."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root / "artifacts"
        self.root.mkdir(parents=True, exist_ok=True)

    def _next_version(self, stem: str, ext: str) -> Path:
        existing = sorted(self.root.glob(f"{stem}_v*.{ext}"))
        if not existing:
            return self.root / f"{stem}_v1.{ext}"
        last = existing[-1].stem
        try:
            version = int(last.split("_v")[-1]) + 1
        except Exception:
            version = len(existing) + 1
        return self.root / f"{stem}_v{version}.{ext}"

    def save_json(self, stem: str, data: Dict[str, Any]) -> Path:
        path = self._next_version(stem, "json")
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def save_text(self, stem: str, text: str) -> Path:
        path = self._next_version(stem, "txt")
        path.write_text(text, encoding="utf-8")
        return path

    def latest(self, stem: str) -> Optional[Path]:
        candidates = sorted(self.root.glob(f"{stem}_v*.*"))
        return candidates[-1] if candidates else None


__all__ = ["ArtifactStore"]
