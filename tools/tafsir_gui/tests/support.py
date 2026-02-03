from __future__ import annotations

from typing import Callable

from tools.tafsir_gui.integrations.gemini import GeminiErrorInfo


class FakeGeminiClient:
    def __init__(self, *, behavior: str = "ok"):
        self.behavior = behavior
        self.cache_counter = 0

    def test_call(self) -> str:
        if self.behavior == "ok":
            return "pong"
        if self.behavior == "rate":
            raise RuntimeError("Mock rate limit 429")
        raise RuntimeError("Mock invalid key")

    def ensure_cache(self, prompt_prefix: str, ttl: str = "7200s") -> str:
        if self.behavior != "ok":
            raise RuntimeError("Cache cannot be created")
        self.cache_counter += 1
        return f"cache/{self.cache_counter}"

    def parse_error(self, exc: Exception) -> GeminiErrorInfo:
        text = str(exc).lower()
        if "rate" in text:
            return GeminiErrorInfo(
                code="rate_limit",
                message="Mock rate limit",
                action="Retry later; auto-resume scheduled.",
                retry_after=5,
            )
        if "invalid" in text:
            return GeminiErrorInfo(
                code="invalid_key",
                message="Mock invalid key",
                action="Provide a valid API key.",
                fatal=True,
            )
        return GeminiErrorInfo(
            code="unknown",
            message="Generic failure",
            action="Check network or key.",
        )


def patch_gemini_clients(monkeypatch, behavior: str = "ok") -> Callable[[], FakeGeminiClient]:
    """Ensure both preflight and integration clients return the same fake."""

    def factory(*args, **kwargs) -> FakeGeminiClient:
        return FakeGeminiClient(behavior=behavior)

    monkeypatch.setattr("tools.tafsir_gui.core.preflight.GeminiClient", factory)
    monkeypatch.setattr("tools.tafsir_gui.integrations.gemini.GeminiClient", factory)
    return factory
