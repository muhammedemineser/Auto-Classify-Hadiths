from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.parametrize("app_server", ["invalid_key"], indirect=True)
def test_flow_invalid_key(page, app_server):
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    page.goto(app_server, wait_until="networkidle")
    page.get_by_label("Gemini API key").fill("bad-key")
    page.get_by_label("Existing file path").fill(str(fixtures / "sample.txt"))
    page.get_by_role("button", name="Run pre-flight checks").click()
    expect(page.get_by_text("Key status: Invalid")).to_be_visible(timeout=5000)
    start_button = page.get_by_role("button", name="Start")
    expect(start_button).to_be_disabled()
