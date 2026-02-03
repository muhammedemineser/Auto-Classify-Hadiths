from pathlib import Path

import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.parametrize("app_server", ["happy"], indirect=True)
def test_flow_file_errors(page, app_server):
    fixtures = Path(__file__).resolve().parents[1] / "fixtures"
    page.goto(app_server, wait_until="networkidle")
    page.get_by_label("Gemini API key").fill("ok-key")
    page.get_by_label("Existing file path").fill("/tmp/nonexistent-file.txt")
    page.get_by_role("button", name="Run pre-flight checks").click()
    expect(page.get_by_text("File not found")).to_be_visible(timeout=5000)
    start_button = page.get_by_role("button", name="Start")
    expect(start_button).to_be_disabled()
