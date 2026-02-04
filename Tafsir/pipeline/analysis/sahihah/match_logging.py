from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

DEBUG_ENABLED = os.environ.get("DEBUG", "1") == "1"


def _emit(msg: str) -> None:
    if not DEBUG_ENABLED:
        return
    print(msg, file=sys.stderr)


def section(title: str, icon: str = "") -> None:
    if not DEBUG_ENABLED:
        return
    line = "=" * 72
    _emit(line)
    _emit(f"{icon} {title}".strip())
    _emit(line)


def log_anchors(hadith_id: int, anchors: Iterable[Tuple[str, float]]) -> None:
    if not DEBUG_ENABLED:
        return
    section(f"Anchors for {hadith_id}", "⚓")
    for text, strength in anchors:
        _emit(f"- {strength:.3f} | {text}")


def log_candidate_flow(
    hadith_id: int,
    *,
    and_count: int,
    or_count: int,
    fallback_count: int,
    final_count: int,
) -> None:
    if not DEBUG_ENABLED:
        return
    section(f"Candidate Flow {hadith_id}", "🔍")
    _emit(f"- AND-phase: {and_count}")
    _emit(f"- OR-phase: {or_count}")
    _emit(f"- Fallback: {fallback_count}")
    _emit(f"- Final: {final_count}")


def log_cache_stats(hit: int, built: int, total: int) -> None:
    if not DEBUG_ENABLED:
        return
    section("Cache Stats", "💾")
    _emit(f"- total: {total}")
    _emit(f"- hit: {hit}")
    _emit(f"- built: {built}")


def log_objective(
    label: str,
    *,
    coverage: float,
    avg_hit: float,
    objective: float,
) -> None:
    if not DEBUG_ENABLED:
        return
    section(f"Objective {label}", "📈")
    _emit(f"- coverage: {coverage:.4f}")
    _emit(f"- avg_hit: {avg_hit:.4f}")
    _emit(f"- objective: {objective:.4f}")


@dataclass
class CoverageTracker:
    series: Dict[str, List[float]] = field(default_factory=dict)

    def add(self, label: str, value: float) -> None:
        self.series.setdefault(label, []).append(value)

    def plot(self, title: str = "Coverage Over Iterations", outfile: str | None = None) -> None:
        if not DEBUG_ENABLED:
            return
        try:
            import matplotlib.pyplot as plt  # type: ignore
        except Exception:
            _emit("matplotlib not available; skipping plot")
            return

        if not self.series:
            _emit("No coverage data to plot")
            return

        plt.figure(figsize=(10, 5))
        for label, values in self.series.items():
            plt.plot(range(1, len(values) + 1), values, label=label)
        plt.title(title)
        plt.xlabel("Iteration")
        plt.ylabel("Coverage")
        plt.grid(True, alpha=0.3)
        plt.legend()
        if outfile:
            plt.savefig(outfile, bbox_inches="tight")
        else:
            plt.show()
