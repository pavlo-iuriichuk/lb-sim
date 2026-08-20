from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .common import Snapshot, mean
from .gini_coefficient import gini_coefficient
from .jains_fairness_index import jains_fairness_index


@dataclass(frozen=True)
class FairnessSnapshot:
    tick: int
    jains_index_load: float
    jains_index_connections: float
    gini_load: float
    load_spread: float
    connection_spread: float
    healthy_instances: int


@dataclass(frozen=True)
class FairnessReport:
    timeline: List[FairnessSnapshot]
    mean_jains_index_load: float
    min_jains_index_load: float
    mean_gini_load: float
    mean_load_spread: float
    max_load_spread: float


def analyze_fairness(snapshots: List[Snapshot]) -> FairnessReport:
    """How evenly load/connections are spread across instances, tick by tick."""
    timeline: List[FairnessSnapshot] = []
    for snapshot in snapshots:
        instances = snapshot.get("instances", [])
        loads = [inst["estimated_load"] for inst in instances]
        connections = [inst["current_connections"] for inst in instances]
        healthy_count = sum(1 for inst in instances if inst.get("is_healthy", True))
        timeline.append(
            FairnessSnapshot(
                tick=snapshot.get("tick"),
                jains_index_load=jains_fairness_index(loads),
                jains_index_connections=jains_fairness_index(connections),
                gini_load=gini_coefficient(loads),
                load_spread=(max(loads) - min(loads)) if loads else 0.0,
                connection_spread=(max(connections) - min(connections)) if connections else 0.0,
                healthy_instances=healthy_count,
            )
        )

    jains_series = [point.jains_index_load for point in timeline]
    gini_series = [point.gini_load for point in timeline]
    spread_series = [point.load_spread for point in timeline]

    return FairnessReport(
        timeline=timeline,
        mean_jains_index_load=mean(jains_series),
        min_jains_index_load=min(jains_series) if jains_series else 1.0,
        mean_gini_load=mean(gini_series),
        mean_load_spread=mean(spread_series),
        max_load_spread=max(spread_series) if spread_series else 0.0,
    )
