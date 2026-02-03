from __future__ import annotations

from typing import Callable

from nicegui import ui

from ...core.events import EventBus, EventType, PipelineEvent
from ...utils.logging import ui_log_buffer


class RunPanel:
    def __init__(
        self,
        *,
        on_start: Callable[[], None],
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        on_cancel: Callable[[], None],
        bus: EventBus,
    ):
        self.start_button = ui.button("Start", on_click=on_start, color="green")
        with ui.row():
            ui.button("Pause", on_click=on_pause)
            ui.button("Resume", on_click=on_resume)
            ui.button("Cancel", on_click=on_cancel, color="red")
        self.progress = ui.linear_progress(value=0).classes("w-full")
        self.status = ui.label("Idle")
        self.log_area = (
            ui.textarea(label="Live logs", value="")
            .classes("w-full h-64")
            .props("readonly autogrow")
        )
        ui.timer(1.5, self._refresh_logs)
        bus.subscribe(self._handle_event)

    def set_start_enabled(self, enabled: bool):
        if enabled:
            self.start_button.enable()
        else:
            self.start_button.disable()

    def _handle_event(self, event: PipelineEvent):
        def _update():
            if event.type == EventType.PROGRESS and event.progress is not None:
                self.progress.value = min(1.0, max(0.0, event.progress))
            if event.type in {EventType.ERROR, EventType.WARNING, EventType.LOG}:
                self.log_area.value += f"[{event.type.value.upper()}] {event.message}\n"
            if event.type == EventType.RETRY_SCHEDULED:
                self.status.text = f"Paused; will resume in {event.data.get('retry_after', '?')}s"
            if event.type == EventType.COMPLETED:
                self.status.text = "Completed"
            else:
                self.status.text = event.message

        ui.run.later(_update)

    def _refresh_logs(self):
        lines = "\n".join(ui_log_buffer.snapshot()[-80:])
        self.log_area.value = lines


__all__ = ["RunPanel"]
