from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger


class ResumeScheduler:
    """APScheduler wrapper to auto-resume paused runs."""

    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler(timezone="UTC")
        self._scheduler.start()
        self._job_id = "auto_resume"

    def schedule_resume(self, when: datetime, action: Callable[[], None]) -> None:
        if self._scheduler.get_job(self._job_id):
            self._scheduler.remove_job(self._job_id)
        self._scheduler.add_job(
            action,
            trigger="date",
            id=self._job_id,
            run_date=when,
            replace_existing=True,
        )
        logger.info("Auto-resume scheduled at {}", when.isoformat())

    def schedule_in(self, seconds: int, action: Callable[[], None]) -> None:
        when = datetime.utcnow() + timedelta(seconds=seconds)
        self.schedule_resume(when, action)

    def cancel(self) -> None:
        if self._scheduler.get_job(self._job_id):
            self._scheduler.remove_job(self._job_id)

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)


__all__ = ["ResumeScheduler"]
