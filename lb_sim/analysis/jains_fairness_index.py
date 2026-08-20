from __future__ import annotations

from typing import Sequence


def jains_fairness_index(values: Sequence[float]) -> float:
    """1.0 = perfectly even distribution, 1/n = maximally skewed towards one instance."""
    values = [float(v) for v in values]
    n = len(values)
    if n == 0:
        return 1.0
    total = sum(values)
    sum_sq = sum(v * v for v in values)
    if sum_sq <= 0:
        return 1.0
    return (total * total) / (n * sum_sq)
