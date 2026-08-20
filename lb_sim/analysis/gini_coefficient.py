from __future__ import annotations

from typing import Sequence


def gini_coefficient(values: Sequence[float]) -> float:
    """0.0 = perfectly even distribution, approaches 1.0 as load concentrates on fewer instances."""
    ordered = sorted(float(v) for v in values)
    n = len(ordered)
    total = sum(ordered)
    if n == 0 or total <= 0:
        return 0.0
    cumulative = sum((index + 1) * value for index, value in enumerate(ordered))
    return max(0.0, (2 * cumulative) / (n * total) - (n + 1) / n)
