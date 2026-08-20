from __future__ import annotations

import statistics
from typing import Sequence


def coefficient_of_variation(values: Sequence[float]) -> float:
    """Relative dispersion of a series (stdev / mean); 0.0 when all values are equal."""
    values = [float(v) for v in values]
    if len(values) < 2:
        return 0.0
    series_mean = statistics.fmean(values)
    if series_mean == 0:
        return 0.0
    return statistics.pstdev(values) / series_mean
