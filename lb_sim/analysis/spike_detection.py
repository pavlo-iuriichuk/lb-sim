from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import List

from .common import Snapshot


@dataclass(frozen=True)
class SpikeEvent:
    tick: int
    arrivals: int
    baseline_mean: float
    z_score: float


def detect_spikes(
    snapshots: List[Snapshot], z_threshold: float = 2.0
) -> List[SpikeEvent]:
    """Flag ticks whose arrival count is a statistical outlier vs. the run's own baseline."""
    arrivals = [snapshot.get("arrivals", 0) for snapshot in snapshots]
    if len(arrivals) < 3:
        return []

    baseline_mean = statistics.fmean(arrivals)
    stdev = statistics.pstdev(arrivals)
    spikes: List[SpikeEvent] = []
    for snapshot, count in zip(snapshots, arrivals):
        if count <= baseline_mean:
            continue
        z_score = (count - baseline_mean) / stdev if stdev > 0 else float("inf")
        if z_score >= z_threshold:
            spikes.append(
                SpikeEvent(
                    tick=int(snapshot["tick"]),
                    arrivals=count,
                    baseline_mean=baseline_mean,
                    z_score=z_score,
                )
            )
    return spikes
