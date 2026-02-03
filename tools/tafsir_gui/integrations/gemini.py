from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL_ID", "models/gemini-2.5-pro")


@dataclass
class GeminiErrorInfo:
    code: str
    message: str
    action: str
    retry_after: Optional[int] = None
    fatal: bool = False


class GeminiClient:
    """Thin wrapper around google.genai with retries and error mapping."""

    def __init__(
        self,
        *,
        api_key: str,
        model_id: Optional[str] = None,
        cache_name: Optional[str] = None,
    ) -> None:
        self.api_key = api_key
        self.model_id = model_id or DEFAULT_MODEL
        self.cache_name = cache_name
        self._client = None
        self._types = None

    def _ensure_client(self):
        if self._client:
            return self._client, self._types
        try:
            from google import genai
            from google.genai import types  # type: ignore
        except Exception as exc:  # pragma: no cover - environment specific
            raise RuntimeError(
                "google-genai is not installed. Install the official SDK to continue."
            ) from exc

        self._client = genai.Client(api_key=self.api_key)
        self._types = types
        return self._client, self._types

    def parse_error(self, exc: Exception) -> GeminiErrorInfo:
        text = str(exc)
        lower = text.lower()
        if "invalid api key" in lower or "permission" in lower:
            return GeminiErrorInfo(
                code="invalid_key",
                message=text,
                action="Verify the API key and ensure it is active.",
                fatal=True,
            )
        if "quota" in lower or "exceeded" in lower:
            return GeminiErrorInfo(
                code="quota",
                message=text,
                action="Wait for quota reset or upgrade plan.",
            )
        if "rate" in lower or "429" in lower:
            return GeminiErrorInfo(
                code="rate_limit",
                message=text,
                action="Slow down requests; auto-resume available.",
                retry_after=60,
            )
        return GeminiErrorInfo(
            code="unknown",
            message=text,
            action="Check network status or retry shortly.",
        )

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=12),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def _generate(self, prompt: str, *, use_cache: bool = True) -> str:
        client, types = self._ensure_client()
        config = None
        if use_cache and self.cache_name:
            config = types.GenerateContentConfig(cached_content=self.cache_name)
        response = client.models.generate_content(
            model=self.model_id,
            contents=prompt,
            config=config,
        )
        if not getattr(response, "candidates", None):
            return ""
        return getattr(response, "text", "") or ""

    def generate(self, prompt: str, *, use_cache: bool = True) -> str:
        try:
            return self._generate(prompt, use_cache=use_cache)
        except Exception as exc:
            info = self.parse_error(exc)
            logger.warning("Gemini call failed: {} ({})", info.message, info.code)
            raise

    def test_call(self) -> str:
        return self.generate("ping", use_cache=False)

    def ensure_cache(self, prompt_prefix: str, ttl: str = "7200s") -> str:
        client, types = self._ensure_client()
        try:
            cache = client.caches.create(
                model=self.model_id,
                config=types.CreateCachedContentConfig(
                    display_name="Tafsir_GUI_Cache",
                    system_instruction=prompt_prefix,
                    contents=[prompt_prefix],
                    ttl=ttl,
                ),
            )
            self.cache_name = cache.name
            logger.info("Cache created {}", cache.name)
            return cache.name
        except Exception as exc:
            info = self.parse_error(exc)
            logger.error("Cache creation failed: {}", info.message)
            raise


__all__ = ["GeminiClient", "GeminiErrorInfo"]
