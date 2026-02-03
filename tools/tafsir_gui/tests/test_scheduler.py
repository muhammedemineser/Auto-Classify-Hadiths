import time

from tools.tafsir_gui.core.scheduler import ResumeScheduler


def test_schedule_resume_executes():
    scheduler = ResumeScheduler()
    flag = {"ran": False}

    def mark():
        flag["ran"] = True

    scheduler.schedule_in(0, mark)
    time.sleep(0.2)
    scheduler.shutdown()
    assert flag["ran"]
