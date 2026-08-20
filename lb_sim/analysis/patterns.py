from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .common import Snapshot
from .fairness import FairnessReport, analyze_fairness
from .failure_recovery import FailureRecoveryReport, summarize_failure_recovery
from .selection_distribution import SelectionDistribution, selection_distribution
from .spike_response import SpikeReport, summarize_spike_response


@dataclass(frozen=True)
class PatternReport:
    fairness: FairnessReport
    failure_recovery: FailureRecoveryReport
    spikes: SpikeReport
    selection_distribution: SelectionDistribution


def analyze_run(snapshots: List[Snapshot]) -> PatternReport:
    """Full pattern report for one simulation run: fairness, failure recovery, spikes, selection skew."""
    fairness = analyze_fairness(snapshots)
    return PatternReport(
        fairness=fairness,
        failure_recovery=summarize_failure_recovery(snapshots),
        spikes=summarize_spike_response(snapshots, fairness=fairness),
        selection_distribution=selection_distribution(snapshots),
    )
