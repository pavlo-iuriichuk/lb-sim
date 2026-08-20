from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .common import Snapshot


@dataclass(frozen=True)
class SelectionDistribution:
    observed_counts: Dict[str, int]
    expected_share: Dict[str, float]
    total_selections: int
    chi_square: float


def selection_distribution(snapshots: List[Snapshot]) -> SelectionDistribution:
    """Observed selection share per instance vs. the share its capacity would predict."""
    if not snapshots:
        return SelectionDistribution(observed_counts={}, expected_share={}, total_selections=0, chi_square=0.0)

    last = snapshots[-1]
    history = last.get("selection_history", [])
    observed_counts: Dict[str, int] = {}
    for name in history:
        observed_counts[name] = observed_counts.get(name, 0) + 1

    instances = last.get("instances", [])
    total_capacity = sum(inst.get("capacity", 0.0) for inst in instances) or 1.0
    total_selections = len(history)

    expected_share = {inst["name"]: inst.get("capacity", 0.0) / total_capacity for inst in instances}
    chi_square = 0.0
    for name, share in expected_share.items():
        expected_count = share * total_selections
        observed_count = observed_counts.get(name, 0)
        if expected_count > 0:
            chi_square += ((observed_count - expected_count) ** 2) / expected_count

    return SelectionDistribution(
        observed_counts=observed_counts,
        expected_share=expected_share,
        total_selections=total_selections,
        chi_square=chi_square,
    )
