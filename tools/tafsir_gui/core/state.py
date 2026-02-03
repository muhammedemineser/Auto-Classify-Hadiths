from __future__ import annotations

import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class StepStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    PAUSED = "paused"
    BLOCKED = "blocked"


@dataclass
class StepState:
    name: str
    status: StepStatus = StepStatus.PENDING
    details: str = ""


@dataclass
class RunContext:
    project_name: str
    input_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    mode: str = "legacy"  # legacy | universal
    api_key: Optional[str] = None
    cache_name: Optional[str] = None
    model_id: Optional[str] = None
    rollback_api_key: Optional[str] = None
    rollback_cache: Optional[str] = None
    start_id: Optional[int] = None
    exact_ids: Optional[List[int]] = None
    auto_resume: bool = False
    preflight: Dict[str, bool] = field(default_factory=dict)
    dynamic_prompt: Optional[str] = None
    structure_rules: Optional[str] = None
    artifacts: Dict[str, Path] = field(default_factory=dict)
    prompt_override: Optional[str] = None


__all__ = ["RunContext", "StepState", "StepStatus"]
