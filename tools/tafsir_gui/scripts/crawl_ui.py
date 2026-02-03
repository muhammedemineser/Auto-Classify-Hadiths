#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

try:
    from playwright.sync_api import Error as PlaywrightError, sync_playwright
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Playwright is required to run this crawler. "
        "Install dependencies via "
        "`pip install -r tools/tafsir_gui/tests/requirements.txt` "
        "and `playwright install`."
    ) from exc

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_MODULE = "tools.tafsir_gui.tests.e2e.app_runner"
FIXTURE_INPUT = REPO_ROOT / "tools" / "tafsir_gui" / "tests" / "fixtures" / "sample.txt"
SCENARIOS = ("happy", "invalid_key", "rate_limit", "error")


class _OutputReader(threading.Thread):
    def __init__(self, stream):
        super().__init__(daemon=True)
        self.stream = stream
        self.lines: list[str] = []

    def run(self):
        for line in self.stream:
            cleaned = line.rstrip()
            if cleaned:
                self.lines.append(cleaned)

    def tail(self, count: int = 8) -> list[str]:
        return self.lines[-count:]


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"Timed out waiting for {url}")


def _launch_server(port: int, scenario: str) -> tuple[subprocess.Popen, _OutputReader]:
    env = os.environ.copy()
    env.update(
        APP_PORT=str(port),
        RUN_E2E="1",
        TAFSIR_TEST_SCENARIO=scenario,
        TAFSIR_TEST_INPUT=str(FIXTURE_INPUT),
    )
    proc = subprocess.Popen(
        [sys.executable, "-m", APP_MODULE],
        env=env,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    reader = _OutputReader(proc.stdout)
    reader.start()
    return proc, reader


def _crawl_buttons(page) -> tuple[list[str], list[str]]:
    clicked = []
    failures = []
    buttons = page.query_selector_all("button")
    for index, button in enumerate(buttons):
        if not button.is_visible():
            continue
        label = (button.inner_text() or f"button-{index}").strip() or f"button-{index}"
        try:
            button.scroll_into_view_if_needed()
            button.click(timeout=2500)
            clicked.append(label)
            page.wait_for_timeout(450)
        except PlaywrightError as exc:
            failures.append(f"{label}: {exc}")
        except Exception as exc:
            failures.append(f"{label}: {exc}")
    return clicked, failures


def _assert_shared_selectors(page) -> list[str]:
    missing = []
    checks = [
        ("header title", lambda pg: pg.get_by_text("Tafsir Pipeline GUI").count() > 0),
        ("legend navigation", lambda pg: pg.locator(".legend-panel").count() > 0),
        (
            "preflight checklist label",
            lambda pg: pg.get_by_text("Pre-flight checklist").count() > 0,
        ),
        ("status line", lambda pg: pg.locator(".status-line").count() > 0),
        ("styled card", lambda pg: pg.locator(".themed-card").count() > 0),
        (
            "theme stylesheet",
            lambda pg: pg.locator('head link[href$="theme.css"]').count() > 0,
        ),
    ]
    for name, test in checks:
        try:
            if not test(page):
                missing.append(name)
        except Exception as exc:
            missing.append(f"{name} (error: {exc})")
    bg_value = page.evaluate(
        "window.getComputedStyle(document.documentElement).getPropertyValue('--bg')"
    )
    if not (bg_value and bg_value.strip()):
        missing.append("CSS var --bg")
    return missing


def _run_ui_crawl(url: str, headless: bool) -> int:
    console_entries: list[tuple[str, str]] = []
    clicked_buttons: list[str] = []
    click_failures: list[str] = []
    missing_elements: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        page = browser.new_page()

        def _on_console(msg):
            console_entries.append((msg.type, msg.text))

        page.on("console", _on_console)
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1200)

        clicked_buttons, click_failures = _crawl_buttons(page)
        missing_elements = _assert_shared_selectors(page)
        browser.close()

    errors = [text for msg_type, text in console_entries if msg_type == "error"]
    warnings = [text for msg_type, text in console_entries if msg_type == "warning"]

    print("\n=== UI crawl report ===")
    print(f"Target: {url}")
    print(f"Visited buttons: {len(clicked_buttons)}")
    if click_failures:
        print(f"Button click failures ({len(click_failures)}):")
        for failure in click_failures:
            print(f"  - {failure}")
    if warnings:
        print(f"Console warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")
    if errors:
        print(f"Console errors ({len(errors)}):")
        for error in errors:
            print(f"  - {error}")
    if missing_elements:
        print("Missing UI expectations:")
        for missing in missing_elements:
            print(f"  - {missing}")

    return int(bool(click_failures or errors or missing_elements))


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl the Tafsir NiceGUI interface.")
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="happy",
        help="Runner scenario to exercise while clicking buttons.",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="Run the browser so you can see the interactions.",
    )
    args = parser.parse_args()

    port = _free_port()
    url = f"http://localhost:{port}"
    proc, reader = _launch_server(port, args.scenario)
    try:
        _wait_for_server(url)
        exit_code = _run_ui_crawl(url, headless=not args.no_headless)
    except Exception as exc:
        print(f"Failed to run crawler: {exc}")
        exit_code = 1
    finally:
        proc.terminate()
        with contextlib.suppress(Exception):
            proc.wait(5)
        reader.join(1)
        if reader.lines:
            print("\n=== UI server log (last lines) ===")
            for line in reader.tail():
                print(f"  >> {line}")

    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
