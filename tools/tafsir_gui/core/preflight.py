from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from ..integrations.gemini import GeminiClient, GeminiErrorInfo
from ..utils import db as db_utils
from ..utils import env as env_utils
from ..utils import file_detect


@dataclass
class CheckResult:
    name: str
    ok: bool
    details: str
    remediation: str = ""
    data: Dict[str, str] = None

    def as_badge(self) -> str:
        return "✅" if self.ok else "❌"


def check_api_key(api_key: str, model_id: Optional[str]) -> CheckResult:
    if not api_key:
        return CheckResult(
            "api_key",
            False,
            "API key is empty.",
            "Provide a valid Gemini API key.",
        )
    client = GeminiClient(api_key=api_key, model_id=model_id, cache_name=None)
    try:
        text = client.test_call()
        ok = bool(text)
        return CheckResult(
            "api_key",
            ok,
            "API key validated with a live ping." if ok else "Test call returned empty.",
        )
    except Exception as exc:
        info = client.parse_error(exc)
        remediation = info.action if isinstance(info, GeminiErrorInfo) else "Check the key and network."
        return CheckResult("api_key", False, str(exc), remediation)


def check_cache_key(api_key: str, cache_name: Optional[str], prompt: str) -> CheckResult:
    if not api_key:
        return CheckResult(
            "cache",
            False,
            "API key required before cache creation.",
            "Set API key first.",
        )
    client = GeminiClient(api_key=api_key, cache_name=cache_name)
    try:
        name = client.ensure_cache(prompt_prefix=prompt)
        return CheckResult(
            "cache",
            True,
            f"Cache ready: {env_utils.mask_secret(name)}",
            data={"cache_name": name},
        )
    except Exception as exc:
        info = client.parse_error(exc)
        remediation = info.action if isinstance(info, GeminiErrorInfo) else "Inspect API status or quota."
        return CheckResult("cache", False, str(exc), remediation)


def check_file_input(path: Path) -> CheckResult:
    result = file_detect.validate_file(path)
    remediation = ""
    if not result.ok:
        remediation = "Ensure the file exists, is readable, and matches a supported type (PDF, CSV, SQLite, text)."
    return CheckResult(
        "input_file",
        result.ok,
        result.details,
        remediation,
        data={"kind": result.kind, "sample": result.sample or ""},
    )


def check_output_dir(path: Path) -> CheckResult:
    try:
        path.mkdir(parents=True, exist_ok=True)
        test_file = path / ".tafsir_gui_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        free = shutil.disk_usage(path).free
        return CheckResult(
            "output_dir",
            True,
            f"Writable. Free space: {free // (1024**2)} MB.",
        )
    except Exception as exc:
        return CheckResult(
            "output_dir",
            False,
            f"Cannot write to {path}: {exc}",
            "Choose a directory with write permission.",
        )


def check_sqlite(db_path: Path) -> CheckResult:
    try:
        db_utils.ensure_sqlite_writable(db_path)
        return CheckResult("database", True, f"SQLite reachable at {db_path}")
    except Exception as exc:
        return CheckResult(
            "database",
            False,
            f"SQLite check failed: {exc}",
            "Pick another location or fix file permissions.",
        )


def run_preflight(
    *,
    input_path: Path,
    output_dir: Path,
    api_key: str,
    model_id: Optional[str],
    cache_name: Optional[str],
    prompt_prefix: str,
    db_name: str,
    mode: str = "legacy",
) -> List[CheckResult]:
    """Run all checks and return their results."""
    results: List[CheckResult] = []
    results.append(check_api_key(api_key, model_id))
    results.append(check_cache_key(api_key, cache_name, prompt_prefix))
    results.append(check_file_input(input_path))
    results.append(check_output_dir(output_dir))
    db_path = output_dir / f"{db_name}.sqlite3"
    results.append(check_sqlite(db_path))

    ok_map = {r.name: r.ok for r in results}
    logger.info("Preflight summary: {}", ok_map)
    return results


def all_checks_green(results: List[CheckResult]) -> bool:
    return all(r.ok for r in results)


__all__ = ["CheckResult", "run_preflight", "all_checks_green"]
