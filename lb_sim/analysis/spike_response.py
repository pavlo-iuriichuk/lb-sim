from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .common import Snapshot, StatSummary, mean, stat_summary
from .fairness import FairnessReport, analyze_fairness
from .spike_detection import detect_spikes


@dataclass(frozen=True)
class SpikeResponse:
    tick: int
    arrivals: int
    z_score: float
    baseline_jains_index: float
    load_spread_at_spike: float
    dropped_requests_at_spike: int
    recovery_ticks: Optional[int]


@dataclass(frozen=True)
class SpikeReport:
    spikes: List[SpikeResponse]
    spike_count: int
    recovery_ticks: StatSummary
    unresolved_spikes: int


def summarize_spike_response(
    snapshots: List[Snapshot],
    fairness: Optional[FairnessReport] = None,
    window: int = 3,
) -> SpikeReport:
    """How quickly fairness recovers after a traffic spike, and what it cost in dropped requests."""
    spikes = detect_spikes(snapshots)
    fairness = fairness if fairness is not None else analyze_fairness(snapshots)
    jains_by_tick = {point.tick: point.jains_index_load for point in fairness.timeline}
    spread_by_tick = {point.tick: point.load_spread for point in fairness.timeline}
    dropped_by_tick = {
        snapshot["tick"]: snapshot.get("dropped_requests", 0) for snapshot in snapshots
    }
    ticks = [snapshot["tick"] for snapshot in snapshots]

    responses: List[SpikeResponse] = []
    for spike in spikes:
        tick = spike.tick
        pre_ticks = [t for t in ticks if tick - window <= t < tick]
        baseline_jains = (
            mean([jains_by_tick[t] for t in pre_ticks]) if pre_ticks else 1.0
        )
        threshold = baseline_jains * 0.95

        recovery_ticks: Optional[int] = None
        for offset, t in enumerate((t for t in ticks if t > tick), start=1):
            if jains_by_tick.get(t, 0.0) >= threshold:
                recovery_ticks = offset
                break

        responses.append(
            SpikeResponse(
                tick=tick,
                arrivals=spike.arrivals,
                z_score=spike.z_score,
                baseline_jains_index=baseline_jains,
                load_spread_at_spike=spread_by_tick.get(tick, 0.0),
                dropped_requests_at_spike=dropped_by_tick.get(tick, 0),
                recovery_ticks=recovery_ticks,
            )
        )

    recovery_values = [
        r.recovery_ticks for r in responses if r.recovery_ticks is not None
    ]

    return SpikeReport(
        spikes=responses,
        spike_count=len(responses),
        recovery_ticks=stat_summary(recovery_values),
        unresolved_spikes=sum(1 for r in responses if r.recovery_ticks is None),
    )
