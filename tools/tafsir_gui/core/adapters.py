from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .scheduler import ResumeScheduler
from ..integrations.gemini import GeminiClient
from ..integrations import tafsir_pipeline, universal_pipeline


class GeminiFactory:
    def create(self, *, api_key: str, cache_name: Optional[str], model_id: Optional[str]):
        raise NotImplementedError


class DefaultGeminiFactory(GeminiFactory):
    def create(self, *, api_key: str, cache_name: Optional[str], model_id: Optional[str]):
        return GeminiClient(api_key=api_key, cache_name=cache_name, model_id=model_id)


class PipelineAdapter:
    def run(self, **kwargs):
        raise NotImplementedError


class LegacyPipelineAdapter(PipelineAdapter):
    def run(
        self,
        *,
        logical_name: str,
        source_dir: Path,
        annotated_dir: Path,
        start_id: Optional[int],
        exact_ids: Optional[List[int]],
        repair: bool,
    ):
        return tafsir_pipeline.run_main_pipeline(
            logical_name=logical_name,
            source_dir=source_dir,
            annotated_dir=annotated_dir,
            start_id=start_id,
            exact_ids=exact_ids,
            repair=repair,
        )


class UniversalPipelineAdapter(PipelineAdapter):
    def run(
        self,
        *,
        input_path: Path,
        project_root: Path,
        api_key: str,
        cache_name: Optional[str],
        model_id: Optional[str],
    ):
        return universal_pipeline.run_universal_pipeline(
            input_path=input_path,
            project_root=project_root,
            api_key=api_key,
            cache_name=cache_name,
            model_id=model_id,
        )


class Clock:
    def now(self):
        raise NotImplementedError

    def sleep(self, seconds: float):
        raise NotImplementedError


class SystemClock(Clock):
    def now(self):
        import time

        return time.time()

    def sleep(self, seconds: float):
        import time

        time.sleep(seconds)


__all__ = [
    "GeminiFactory",
    "DefaultGeminiFactory",
    "PipelineAdapter",
    "LegacyPipelineAdapter",
    "UniversalPipelineAdapter",
    "Clock",
    "SystemClock",
]
