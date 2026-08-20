from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .common import Snapshot


@dataclass(frozen=True)
class FailureEvent:
    instance: str
    start_tick: int
    end_tick: int
    recovered: bool
    duration_ticks: int


def detect_failure_events(snapshots: List[Snapshot]) -> List[FailureEvent]:
    """Turn per-tick is_healthy flags into discrete down/recovered events per instance."""
    open_start_ticks: Dict[str, int] = {}
    closed_events: List[FailureEvent] = []

    for snapshot in snapshots:
        tick = int(snapshot["tick"])
        for instance in snapshot.get("instances", []):
            name = instance["name"]
            healthy = instance.get("is_healthy", True)
            if not healthy and name not in open_start_ticks:
                open_start_ticks[name] = tick
            elif healthy and name in open_start_ticks:
                start_tick = open_start_ticks.pop(name)
                closed_events.append(
                    FailureEvent(
                        instance=name,
                        start_tick=start_tick,
                        end_tick=tick,
                        recovered=True,
                        duration_ticks=tick - start_tick,
                    )
                )

    last_tick = int(snapshots[-1]["tick"]) if snapshots else 0
    for name, start_tick in open_start_ticks.items():
        closed_events.append(
            FailureEvent(
                instance=name,
                start_tick=start_tick,
                end_tick=last_tick,
                recovered=False,
                duration_ticks=last_tick - start_tick,
            )
        )

    closed_events.sort(key=lambda event: (event.instance, event.start_tick))
    return closed_events
