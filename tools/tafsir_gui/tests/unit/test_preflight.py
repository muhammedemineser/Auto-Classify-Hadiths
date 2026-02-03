from pathlib import Path

import pytest

from tools.tafsir_gui.core import preflight
from tools.tafsir_gui.tests.support import patch_gemini_clients
from tools.tafsir_gui.utils import file_detect


def _run_preflight(monkeypatch, sample: Path, behavior: str = "ok"):
    patch_gemini_clients(monkeypatch, behavior=behavior)
    return preflight.run_preflight(
        input_path=sample,
        output_dir=sample.parent,
        api_key="k",
        model_id="m",
        cache_name="c",
        prompt_prefix="p",
        db_name="demo",
        mode="legacy",
    )


def test_preflight_valid(monkeypatch, tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text("hello")
    results = _run_preflight(monkeypatch, sample, behavior="ok")
    assert preflight.all_checks_green(results)


def test_preflight_invalid_key(monkeypatch, tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text("hello")
    results = _run_preflight(monkeypatch, sample, behavior="invalid")
    api_res = next(r for r in results if r.name == "api_key")
    assert not api_res.ok
    assert "Provide a valid API key" in api_res.remediation


def test_preflight_rate_limit(monkeypatch, tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text("hello")
    results = _run_preflight(monkeypatch, sample, behavior="rate")
    api_res = next(r for r in results if r.name == "api_key")
    assert not api_res.ok
    assert "auto-resume" in api_res.remediation.lower()


@pytest.mark.parametrize(
    "fixture_name, expected_kind",
    [
        ("sample.txt", "text"),
        ("sample.csv", "csv"),
        ("sample.db", "sqlite"),
        ("sample.pdf", "pdf"),
    ],
)
def test_check_file_input_detects_types(sample_files, fixture_name, expected_kind, monkeypatch):
    target = sample_files[fixture_name]
    if fixture_name.endswith(".pdf"):
        # Avoid needing a real PDF parser by patching the sampler.
        monkeypatch.setattr(file_detect, "sample_pdf", lambda *_args, **_kwargs: "PDF sample")
    result = preflight.check_file_input(target)
    assert result.data and result.data.get("kind") == expected_kind
