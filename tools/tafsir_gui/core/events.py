from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Dict, List, Optional


class EventType(str, enum.Enum):
    START = "start"
    PROGRESS = "progress"
    LOG = "log"
    WARNING = "warning"
    ERROR = "error"
    RETRY_SCHEDULED = "retry_scheduled"
    COMPLETED = "completed"
    STATE = "state"


@dataclass
class PipelineEvent:
    type: EventType
    message: str
    step: Optional[str] = None
    progress: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=lambda: time.time())


class EventBus:
    """Very small synchronous pub/sub bus for UI event streaming."""

    def __init__(self) -> None:
        self._subscribers: List[Callable[[PipelineEvent], None]] = []
        self._lock = Lock()

    def publish(self, event: PipelineEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for sub in subscribers:
            try:
                sub(event)
            except Exception:
                # Keep bus resilient; UI can ignore failed listeners.
                pass

    def subscribe(self, callback: Callable[[PipelineEvent], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)


__all__ = ["EventBus", "PipelineEvent", "EventType"]
