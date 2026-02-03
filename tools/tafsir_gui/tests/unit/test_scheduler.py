from types import SimpleNamespace

from tools.tafsir_gui.core.scheduler import ResumeScheduler
from tools.tafsir_gui.core.runner import PipelineRunner, RetryLater
from tools.tafsir_gui.core.events import EventBus
from tools.tafsir_gui.core.state import RunContext, StepState


def test_scheduler_replaces_job():
    sched = ResumeScheduler()
    def action():
        pass

    sched.schedule_in(60, action)
    sched.schedule_in(30, action)  # should replace
    jobs = sched._scheduler.get_jobs()
    sched.shutdown()
    assert len(jobs) == 1


def test_retrylater_leaves_runner_paused():
    bus = EventBus()
    sched = ResumeScheduler()
    runner = PipelineRunner(bus, sched)
    ctx = RunContext(project_name="ctx")

    def failing_step(_ctx):
        raise RetryLater(1)

    runner._steps = lambda c: [
        SimpleNamespace(
            name="retry",
            title="Retry Step",
            action=failing_step,
            status=StepState("retry"),
        )
    ]
    runner._emit = lambda *a, **k: None
    runner.start(ctx, [SimpleNamespace(ok=True)])
    runner._thread.join(1)
    sched.shutdown()
    assert runner._paused
