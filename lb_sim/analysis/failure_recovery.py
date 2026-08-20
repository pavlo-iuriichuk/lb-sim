from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .common import Snapshot, StatSummary, stat_summary
from .failure_events import FailureEvent, detect_failure_events


@dataclass(frozen=True)
class FailureRecoveryReport:
    events: List[FailureEvent]
    total_events: int
    recovered_events: int
    unresolved_events: int
    recovery_ticks: StatSummary
    outage_tick_count: int
    dropped_requests_total: int
    dropped_requests_during_outages: int


def summarize_failure_recovery(snapshots: List[Snapshot]) -> FailureRecoveryReport:
    """How failures were handled: how many, how long instances stayed down, and traffic lost."""
    events = detect_failure_events(snapshots)
    recovered = [event for event in events if event.recovered]
    durations = [event.duration_ticks for event in recovered]

    outage_ticks = {
        snapshot["tick"]
        for snapshot in snapshots
        if any(not inst.get("is_healthy", True) for inst in snapshot.get("instances", []))
    }
    dropped_total = sum(snapshot.get("dropped_requests", 0) for snapshot in snapshots)
    dropped_during_outages = sum(
        snapshot.get("dropped_requests", 0) for snapshot in snapshots if snapshot.get("tick") in outage_ticks
    )

    return FailureRecoveryReport(
        events=events,
        total_events=len(events),
        recovered_events=len(recovered),
        unresolved_events=len(events) - len(recovered),
        recovery_ticks=stat_summary(durations),
        outage_tick_count=len(outage_ticks),
        dropped_requests_total=dropped_total,
        dropped_requests_during_outages=dropped_during_outages,
    )
