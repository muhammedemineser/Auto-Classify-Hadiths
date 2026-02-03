"""Log configuration shared by the GUI and runner."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, List

from loguru import logger

from .env import REPO_ROOT

LOG_DIR = REPO_ROOT / "tools" / "tafsir_gui" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "gui.log"


class UILogBuffer:
    """Thread-safe ring buffer for log lines that should appear in the UI."""

    def __init__(self, max_items: int = 500):
        self.max_items = max_items
        self._lines: List[str] = []
        self._lock = threading.Lock()
        self._listeners: List[Callable[[str], None]] = []

    def append(self, line: str) -> None:
        with self._lock:
            self._lines.append(line)
            if len(self._lines) > self.max_items:
                self._lines = self._lines[-self.max_items :]
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(line)
            except Exception:
                pass

    def snapshot(self) -> List[str]:
        with self._lock:
            return list(self._lines)

    def subscribe(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._listeners.append(callback)


ui_log_buffer = UILogBuffer()


def configure_logging() -> None:
    """Configure loguru sinks for file + UI buffer."""
    logger.remove()
    logger.add(LOG_PATH, rotation="1 week", encoding="utf-8", enqueue=True)
    logger.add(lambda m: ui_log_buffer.append(m.rstrip("\n")), level="INFO")


__all__ = ["configure_logging", "ui_log_buffer", "LOG_PATH", "LOG_DIR"]
