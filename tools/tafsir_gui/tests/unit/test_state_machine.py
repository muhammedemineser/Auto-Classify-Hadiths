from types import SimpleNamespace

from tools.tafsir_gui.core.state import RunContext, StepState, StepStatus
from tools.tafsir_gui.core.runner import PipelineRunner, RetryLater
from tools.tafsir_gui.core.events import EventBus, EventType
from tools.tafsir_gui.core.scheduler import ResumeScheduler


class DummyScheduler(ResumeScheduler):
    def __init__(self):
        super().__init__()
        self.scheduled = 0

    def schedule_in(self, seconds, action):
        self.scheduled += 1


def test_start_requires_preflight_green():
    bus = EventBus()
    sched = DummyScheduler()
    runner = PipelineRunner(bus, sched)
    ctx = RunContext(project_name="p")
    try:
        runner.start(ctx, [SimpleNamespace(ok=False)])
        assert False, "Expected RuntimeError"
    except RuntimeError:
        pass


def test_retrylater_pauses_and_schedules(monkeypatch):
    bus = EventBus()
    sched = DummyScheduler()
    runner = PipelineRunner(bus, sched)
    ctx = RunContext(project_name="p")

    def failing_step(_ctx):
        raise RetryLater(5)

    runner._steps = lambda c: []  # type: ignore
    runner._emit = lambda *a, **k: None  # silence
    # monkeypatch steps to our single failing step
    runner._steps = lambda c: [
        SimpleNamespace(
            name="x",
            title="X",
            action=failing_step,
            status=SimpleNamespace(status=StepStatus.PENDING),
        )
    ]
    runner.start(ctx, [SimpleNamespace(ok=True)])
    runner._thread.join(1)
    assert sched.scheduled == 1


def test_runner_emits_allowed_transitions(monkeypatch):
    bus = EventBus()
    sched = DummyScheduler()
    runner = PipelineRunner(bus, sched)
    ctx = RunContext(project_name="p")
    captured = []

    def listener(event):
        captured.append(event)

    bus.subscribe(listener)

    statuses = [StepState("ingest"), StepState("finish")]
    runner._steps = lambda c: [
        SimpleNamespace(name="ingest", title="Ingest", action=lambda *_: None, status=statuses[0]),
        SimpleNamespace(name="finish", title="Finalize", action=lambda *_: None, status=statuses[1]),
    ]

    runner.start(ctx, [SimpleNamespace(ok=True)])
    runner._thread.join(1)

    assert any(e.type == EventType.START for e in captured)
    assert any(e.type == EventType.COMPLETED for e in captured)
    assert all(s.status == StepStatus.SUCCESS for s in statuses)
