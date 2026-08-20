from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .common import StatSummary, stat_summary


@dataclass(frozen=True)
class StressAggregate:
    mean_estimated_load: StatSummary
    max_estimated_load: StatSummary
    load_spread: StatSummary
    jains_index_load: StatSummary
    gini_load: StatSummary
    failure_recovery_ticks_mean: StatSummary
    dropped_requests_total: StatSummary
    spike_count: StatSummary
    spike_recovery_ticks_mean: StatSummary


def aggregate_stress_runs(run_summaries: List[Dict[str, Any]]) -> StressAggregate:
    """Cross-run statistics (mean/stdev/min/max) for the key characteristics across a stress-test suite.

    Each run summary is the plain JSON-shaped dict produced by Simulator._summarize (i.e. already
    flattened via dataclasses.asdict), not a PatternReport, so lookups walk it as nested dicts.
    """

    def extract(path: List[str]) -> List[float]:
        values: List[float] = []
        for summary in run_summaries:
            node: Any = summary
            for key in path:
                if not isinstance(node, dict) or key not in node:
                    node = None
                    break
                node = node[key]
            if isinstance(node, (int, float)):
                values.append(float(node))
        return values

    return StressAggregate(
        mean_estimated_load=stat_summary(extract(["mean_estimated_load"])),
        max_estimated_load=stat_summary(extract(["max_estimated_load"])),
        load_spread=stat_summary(extract(["fairness", "load_spread"])),
        jains_index_load=stat_summary(extract(["patterns", "fairness", "mean_jains_index_load"])),
        gini_load=stat_summary(extract(["patterns", "fairness", "mean_gini_load"])),
        failure_recovery_ticks_mean=stat_summary(
            extract(["patterns", "failure_recovery", "recovery_ticks", "mean"])
        ),
        dropped_requests_total=stat_summary(extract(["patterns", "failure_recovery", "dropped_requests_total"])),
        spike_count=stat_summary(extract(["patterns", "spikes", "spike_count"])),
        spike_recovery_ticks_mean=stat_summary(extract(["patterns", "spikes", "recovery_ticks", "mean"])),
    )
