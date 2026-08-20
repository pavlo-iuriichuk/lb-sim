from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, Sequence

Snapshot = Dict[str, Any]
"""One tick's recorded state, as produced by Simulator._build_snapshot / stored in timeline.json."""


@dataclass(frozen=True)
class StatSummary:
    mean: float
    stdev: float
    min: float
    max: float


def mean(values: Sequence[float]) -> float:
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def stat_summary(values: Sequence[float]) -> StatSummary:
    values = [float(v) for v in values]
    if not values:
        return StatSummary(mean=0.0, stdev=0.0, min=0.0, max=0.0)
    return StatSummary(
        mean=statistics.fmean(values),
        stdev=statistics.pstdev(values) if len(values) > 1 else 0.0,
        min=min(values),
        max=max(values),
    )
