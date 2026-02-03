from pathlib import Path

from tools.tafsir_gui.core import preflight


class _FakeClient:
    def __init__(self, api_key=None, cache_name=None, model_id=None):
        self.cache_name = cache_name or "cache/test"

    def test_call(self):
        return "ok"

    def ensure_cache(self, prompt_prefix, ttl="7200s"):
        return "cache/test"

    def parse_error(self, exc):
        return exc


def test_preflight_runs_with_fake_client(monkeypatch, tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_text("hello world")

    monkeypatch.setattr(preflight, "GeminiClient", _FakeClient)
    results = preflight.run_preflight(
        input_path=sample,
        output_dir=tmp_path,
        api_key="fake",
        model_id="model",
        cache_name="cache/test",
        prompt_prefix="prompt",
        db_name="demo",
    )
    assert preflight.all_checks_green(results)
