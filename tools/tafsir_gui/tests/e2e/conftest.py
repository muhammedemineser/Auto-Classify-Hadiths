import contextlib
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest


def _free_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture
def app_server(request):
    if not os.getenv("RUN_E2E"):
        pytest.skip("E2E tests are disabled; set RUN_E2E=1 to enable.")
    port = _free_port()
    env = os.environ.copy()
    env["APP_PORT"] = str(port)
    scenario = getattr(request, "param", "happy")
    env["TAFSIR_TEST_SCENARIO"] = scenario
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    env["TAFSIR_TEST_INPUT"] = str(fixtures_dir / "sample.txt")
    env.pop("PYTEST_CURRENT_TEST", None)
    proc = subprocess.Popen(
        [sys.executable, "-m", "tools.tafsir_gui.tests.e2e.app_runner"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    # wait for server to accept connections
    deadline = time.time() + 30
    url = f"http://localhost:{port}"
    while True:
        if proc.poll() is not None:
            stdout = proc.stdout.read()
            raise RuntimeError(
                "Server exited before accepting connections",
                proc.returncode,
                stdout,
            )
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            if time.time() > deadline:
                proc.terminate()
                stdout = proc.stdout.read()
                raise RuntimeError(
                    "Server failed to start in time",
                    stdout,
                )
            time.sleep(0.5)
    yield f"http://localhost:{port}"
    with contextlib.suppress(Exception):
        proc.terminate()
    with contextlib.suppress(Exception):
        proc.kill()
