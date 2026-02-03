from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.parametrize("app_server", ["happy"], indirect=True)
@pytest.mark.xfail(reason="Mode switch gating not enforced yet", strict=False)
def test_flow_mode_switch(page, app_server):
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    page.goto(app_server, wait_until="networkidle")
    page.get_by_label("Gemini API key").fill("ok-key")
    page.get_by_label("Existing file path").fill(str(fixtures / "sample.txt"))
    page.get_by_role("button", name="Run pre-flight checks").click()
    start_button = page.get_by_role("button", name="Start")
    expect(start_button).to_be_enabled(timeout=5000)
    page.get_by_text("legacy").click()
    expect(start_button).to_be_disabled(timeout=1000)
