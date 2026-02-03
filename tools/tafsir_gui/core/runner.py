from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional

from loguru import logger

from Tafsir.pipeline.gemini_gui.PROMPT_PREFIX import PROMPT_PREFIX

from .events import EventBus, EventType, PipelineEvent
from .preflight import all_checks_green
from .scheduler import ResumeScheduler
from .state import RunContext, StepState, StepStatus
from ..integrations.gemini import GeminiClient, GeminiErrorInfo
from ..integrations import tafsir_pipeline, universal_pipeline
from ..utils import db as db_utils
from ..utils import env as env_utils
from .adapters import (
    GeminiFactory,
    DefaultGeminiFactory,
    PipelineAdapter,
    LegacyPipelineAdapter,
    UniversalPipelineAdapter,
    Clock,
    SystemClock,
)


class RetryLater(Exception):
    def __init__(self, seconds: int, info: GeminiErrorInfo | None = None):
        super().__init__(f"Retry after {seconds}s")
        self.seconds = seconds
        self.info = info


@dataclass
class PipelineStep:
    name: str
    title: str
    action: Callable[[RunContext], None]
    status: StepState


class PipelineRunner:
    def __init__(
        self,
        bus: EventBus,
        scheduler: ResumeScheduler,
        *,
        gemini_factory: GeminiFactory | None = None,
        legacy_adapter: PipelineAdapter | None = None,
        universal_adapter: PipelineAdapter | None = None,
        clock: Clock | None = None,
        test_mode: bool = False,
    ):
        self.bus = bus
        self.scheduler = scheduler
        self.gemini_factory = gemini_factory or DefaultGeminiFactory()
        self.legacy_adapter = legacy_adapter or LegacyPipelineAdapter()
        self.universal_adapter = universal_adapter or UniversalPipelineAdapter()
        self.clock = clock or SystemClock()
        self.test_mode = test_mode
        self._thread: threading.Thread | None = None
        self._cancelled = False
        self._paused = False
        self._ctx: RunContext | None = None

    # ---- public controls -------------------------------------------------
    def start(self, ctx: RunContext, checks) -> None:
        if self._thread and self._thread.is_alive():
            logger.warning("Pipeline already running")
            return
        if not all_checks_green(checks):
            raise RuntimeError("Preflight must be green before starting.")
        self._ctx = ctx
        self._cancelled = False
        self._paused = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        if self._thread and self._thread.is_alive():
            return
        if self._ctx:
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def cancel(self) -> None:
        self._cancelled = True

    # ---- internal execution ---------------------------------------------
    def _emit(self, type_: EventType, message: str, **data):
        self.bus.publish(PipelineEvent(type_, message, data=data))

    def _wait_if_paused(self):
        while self._paused and not self._cancelled:
            time.sleep(0.5)

    def _steps(self, ctx: RunContext) -> List[PipelineStep]:
        if ctx.mode == "universal":
            return [
                PipelineStep("ingest", "Ingest Input", lambda c=ctx: self._step_ingest(c), StepState("ingest")),
                PipelineStep("discover", "Discovery", lambda c=ctx: self._step_discovery(c), StepState("discover")),
                PipelineStep("schema", "Schema Synthesis", lambda c=ctx: self._step_schema_universal(c), StepState("schema")),
                PipelineStep("validate", "Validation & Guards", lambda c=ctx: self._step_validate(c), StepState("validate")),
                PipelineStep("finish", "Finalize", lambda c=ctx: self._step_finalize(c), StepState("finish")),
            ]
        return [
            PipelineStep(
                "ingest",
                "Ingest Input",
                lambda c=ctx: self._step_ingest(c),
                StepState("ingest"),
            ),
            PipelineStep(
                "sample",
                "Sample & Prompt",
                lambda c=ctx: self._step_sample_prompt(c),
                StepState("sample"),
            ),
            PipelineStep(
                "schema",
                "Schema Prep",
                lambda c=ctx: self._step_schema(c),
                StepState("schema"),
            ),
            PipelineStep(
                "gemini",
                "Run Gemini Pipeline",
                lambda c=ctx: self._step_main_pipeline(c),
                StepState("gemini"),
            ),
            PipelineStep(
                "finish",
                "Finalize",
                lambda c=ctx: self._step_finalize(c),
                StepState("finish"),
            ),
        ]

    def _run(self):
        ctx = self._ctx
        if not ctx:
            return
        steps = self._steps(ctx)
        self._emit(EventType.START, "Pipeline started", step="all")
        for step in steps:
            if self._cancelled:
                self._emit(EventType.WARNING, "Pipeline cancelled", step=step.name)
                break
            self._wait_if_paused()
            step.status.status = StepStatus.RUNNING
            self._emit(EventType.STATE, f"Step {step.title} started", step=step.name)
            try:
                step.action(ctx)
                step.status.status = StepStatus.SUCCESS
                self._emit(EventType.PROGRESS, f"{step.title} complete", step=step.name, progress=1.0)
            except RetryLater as retry_exc:
                self._paused = True
                self._emit(
                    EventType.RETRY_SCHEDULED,
                    f"Auto resume scheduled in {retry_exc.seconds} seconds",
                    step=step.name,
                    data={"retry_after": retry_exc.seconds},
                )
                self.scheduler.schedule_in(retry_exc.seconds, self.resume)
                step.status.status = StepStatus.PAUSED
                return
            except Exception as exc:
                step.status.status = StepStatus.ERROR
                self._emit(
                    EventType.ERROR,
                    f"{step.title} failed: {exc}",
                    step=step.name,
                )
                logger.exception("Step %s failed", step.name)
                return
        else:
            self._emit(EventType.COMPLETED, "Pipeline finished", step="all")

    # ---- individual steps ----------------------------------------------
    def _project_root(self, ctx: RunContext) -> Path:
        assert ctx.output_dir, "output_dir missing"
        root = ctx.output_dir / ctx.project_name
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _step_ingest(self, ctx: RunContext) -> None:
        assert ctx.input_path, "Input file required"
        project_root = self._project_root(ctx)
        source_dir = project_root / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        db_path = tafsir_pipeline.ingest_input_file(
            ctx.input_path, ctx.project_name, source_dir
        )
        ctx.preflight["source_db"] = str(db_path)
        self._emit(
            EventType.LOG,
            f"Ingested input into {db_path}",
            step="ingest",
            data={"db_path": str(db_path)},
        )

    def _step_sample_prompt(self, ctx: RunContext) -> None:
        project_root = self._project_root(ctx)
        source_db = Path(
            ctx.preflight.get(
                "source_db", project_root / "source" / f"{ctx.project_name}.sqlite3"
            )
        )
        sample = tafsir_pipeline.sample_source_row(source_db, ctx.project_name)
        if not sample:
            raise RuntimeError("No sample text found in source database.")

        client = self.gemini_factory.create(api_key=ctx.api_key or "", cache_name=ctx.cache_name, model_id=ctx.model_id)
        prompt = (
            "You are deriving structural rules for a tafsir corpus. "
            "Inspect the following excerpt and summarise the structural markers and table fields "
            "needed to store it safely:\n\n"
            f"{sample}\n\nReturn a concise bullet list."
        )
        try:
            rules = client.generate(prompt, use_cache=bool(ctx.cache_name))
            ctx.structure_rules = rules
        except Exception as exc:
            info = client.parse_error(exc)
            if isinstance(info, GeminiErrorInfo) and info.code == "rate_limit":
                raise RetryLater(info.retry_after or 60, info)
            raise
        ctx.dynamic_prompt = f"{PROMPT_PREFIX}\n\nUser-specific notes:\n{rules or 'n/a'}"
        prompt_path = project_root / "dynamic_prompt.txt"
        prompt_path.write_text(ctx.dynamic_prompt, encoding="utf-8")
        self._emit(
            EventType.LOG,
            "Generated dynamic prompt and structure rules.",
            step="sample",
            data={"structure_rules": rules, "prompt_path": str(prompt_path)},
        )

    def _step_discovery(self, ctx: RunContext) -> None:
        # Placeholder: discovery handled inside universal pipeline orchestration.
        self._emit(EventType.LOG, "Discovery triggered.", step="discover")

    def _step_schema_universal(self, ctx: RunContext) -> None:
        project_root = self._project_root(ctx)
        # ensure env for downstream Gemini
        if ctx.api_key:
            os.environ["GEMINI_API_KEY"] = ctx.api_key
        if ctx.cache_name:
            os.environ["GEMINI_CACHE_NAME"] = ctx.cache_name
        artifacts = self.universal_adapter.run(
            input_path=ctx.input_path,
            project_root=project_root,
            api_key=ctx.api_key or "",
            cache_name=ctx.cache_name,
            model_id=ctx.model_id or "",
        )
        ctx.artifacts.update(artifacts)
        self._emit(
            EventType.LOG,
            "Universal schema synthesized and data generated.",
            step="schema",
            data={"artifacts": {k: str(v) for k, v in artifacts.items()}},
        )

    def _step_validate(self, ctx: RunContext) -> None:
        self._emit(EventType.LOG, "Validation completed (see artifacts).", step="validate")

    def _step_schema(self, ctx: RunContext) -> None:
        project_root = self._project_root(ctx)
        annotated_dir = project_root / "annotated"
        annotated_dir.mkdir(parents=True, exist_ok=True)
        target_db = annotated_dir / f"{ctx.project_name}_annotated.sqlite3"
        db_utils.ensure_sqlite_writable(target_db)
        self._emit(
            EventType.LOG,
            f"Schema location ready at {target_db}",
            step="schema",
        )

    def _step_main_pipeline(self, ctx: RunContext) -> None:
        project_root = self._project_root(ctx)
        source_dir = project_root / "source"
        annotated_dir = project_root / "annotated"
        # propagate secrets into environment for downstream modules
        if ctx.api_key:
            os.environ["GEMINI_API_KEY"] = ctx.api_key
        if ctx.cache_name:
            os.environ["GEMINI_CACHE_NAME"] = ctx.cache_name
        if ctx.model_id:
            os.environ["GEMINI_MODEL_ID"] = ctx.model_id
        if ctx.mode == "legacy":
            self.legacy_adapter.run(
                logical_name=ctx.project_name,
                source_dir=source_dir,
                annotated_dir=annotated_dir,
                start_id=ctx.start_id,
                exact_ids=ctx.exact_ids,
                repair=False,
            )
            self._emit(EventType.LOG, "Main pipeline completed.", step="gemini")

    def _step_finalize(self, ctx: RunContext) -> None:
        env_updates = {}
        if ctx.api_key:
            env_updates["GEMINI_API_KEY"] = ctx.api_key
        if ctx.cache_name:
            env_updates["GEMINI_CACHE_NAME"] = ctx.cache_name
        if ctx.model_id:
            env_updates["GEMINI_MODEL_ID"] = ctx.model_id
        if env_updates:
            env_utils.write_env(env_updates)
        self._emit(EventType.LOG, "Configuration persisted to .env", step="finish")


__all__ = ["PipelineRunner", "PipelineStep", "RetryLater"]
