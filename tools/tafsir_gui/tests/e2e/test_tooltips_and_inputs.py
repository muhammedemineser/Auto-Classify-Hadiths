import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
@pytest.mark.parametrize("app_server", ["happy"], indirect=True)
def test_tooltip_and_input_width(page, app_server):
    page.goto(app_server, wait_until="networkidle")
    # Walk the stepper to the API settings so the input is visible.
    for _ in range(3):
        page.get_by_role("button", name="Next").click()
    legacy_btn = page.get_by_role("button", name="Legacy")
    legacy_btn.hover()
    tooltip = page.locator("#tafsir-mode-tooltip")
    expect(
        tooltip,
        "Tooltip should show the Legacy description",
    ).to_have_text(
        "Legacy mode uses the tafsir-specific modules and existing pipeline",
        timeout=5000,
    )
    expect(tooltip).to_have_css("opacity", "1", timeout=2000)

    gemini_input = page.get_by_label("Gemini API key")
    width = gemini_input.evaluate(
        "el => parseFloat(window.getComputedStyle(el).width, 10)"
    )
    parent_width = gemini_input.evaluate(
        "el => parseFloat(window.getComputedStyle(el.parentElement).width, 10)"
    )
    assert abs(width - parent_width) <= 1, "Inputs should stretch to their container"
