import pytest


def _normalize_color(value: str) -> str:
    value = value.strip()
    if value.startswith("rgb"):
        nums = [int(x) for x in value.lstrip("rgb(").rstrip(")").split(",")]
        return "#{:02x}{:02x}{:02x}".format(*nums)
    return value.lower()


def _get_css_variable(page, name: str) -> str:
    return page.evaluate(
        f"return getComputedStyle(document.documentElement).getPropertyValue('{name}');"
    ).strip()


@pytest.mark.e2e
@pytest.mark.parametrize("app_server", ["happy"], indirect=True)
def test_theme_mode_reactivity(page, app_server):
    page.goto(app_server, wait_until="networkidle")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert not page.evaluate("document.body.classList.contains('light')")
    assert _normalize_color(_get_css_variable(page, "--ink")) == "#f2e8d5"
    heading_color = _normalize_color(
        page.get_by_text("Tafsir Pipeline GUI").evaluate(
            "el => getComputedStyle(el).color"
        )
    )
    assert heading_color == "#f2e8d5"

    page.get_by_role("button", name="Toggle theme").click()
    page.wait_for_timeout(400)
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
    assert page.evaluate("document.body.classList.contains('light')")
    assert _normalize_color(_get_css_variable(page, "--ink")) == "#0f172a"

    assert page.evaluate("document.documentElement.dataset.pipelineMode") == "legacy"
    page.get_by_role("button", name="Universal").click()
    page.wait_for_timeout(200)
    assert page.evaluate("document.documentElement.dataset.pipelineMode") == "universal"
    assert page.evaluate(
        "document.documentElement.classList.contains('mode-universal')"
    )
    page.get_by_role("button", name="Legacy").click()
    page.wait_for_timeout(200)
    assert page.evaluate("document.documentElement.dataset.pipelineMode") == "legacy"
    assert page.evaluate(
        "document.documentElement.classList.contains('mode-legacy')"
    )

    assert (
        page.evaluate("getComputedStyle(document.documentElement).direction") == "ltr"
    )
