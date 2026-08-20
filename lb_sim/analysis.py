from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional, Sequence


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


def gini_coefficient(values: Sequence[float]) -> float:
    """0.0 = perfectly even distribution, approaches 1.0 as load concentrates on fewer instances."""
    ordered = sorted(float(v) for v in values)
    n = len(ordered)
    total = sum(ordered)
    if n == 0 or total <= 0:
        return 0.0
    cumulative = sum((index + 1) * value for index, value in enumerate(ordered))
    return max(0.0, (2 * cumulative) / (n * total) - (n + 1) / n)


def coefficient_of_variation(values: Sequence[float]) -> float:
    values = [float(v) for v in values]
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0
    return statistics.pstdev(values) / mean


def _mean(values: Sequence[float]) -> float:
    values = list(values)
    return statistics.fmean(values) if values else 0.0


def _stat_summary(values: Sequence[float]) -> Dict[str, float]:
    values = [float(v) for v in values]
    if not values:
        return {"mean": 0.0, "stdev": 0.0, "min": 0.0, "max": 0.0}
    return {
        "mean": statistics.fmean(values),
        "stdev": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def analyze_fairness(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """How evenly load/connections are spread across instances, tick by tick."""
    timeline: List[Dict[str, Any]] = []
    for snapshot in snapshots:
        instances = snapshot.get("instances", [])
        loads = [inst["estimated_load"] for inst in instances]
        connections = [inst["current_connections"] for inst in instances]
        healthy_count = sum(1 for inst in instances if inst.get("is_healthy", True))
        timeline.append(
            {
                "tick": snapshot.get("tick"),
                "jains_index_load": jains_fairness_index(loads),
                "jains_index_connections": jains_fairness_index(connections),
                "gini_load": gini_coefficient(loads),
                "load_spread": (max(loads) - min(loads)) if loads else 0.0,
                "connection_spread": (max(connections) - min(connections)) if connections else 0.0,
                "healthy_instances": healthy_count,
            }
        )

    jains_series = [point["jains_index_load"] for point in timeline]
    gini_series = [point["gini_load"] for point in timeline]
    spread_series = [point["load_spread"] for point in timeline]

    return {
        "timeline": timeline,
        "mean_jains_index_load": _mean(jains_series),
        "min_jains_index_load": min(jains_series) if jains_series else 1.0,
        "mean_gini_load": _mean(gini_series),
        "mean_load_spread": _mean(spread_series),
        "max_load_spread": max(spread_series) if spread_series else 0.0,
    }


def detect_failure_events(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Turn per-tick is_healthy flags into discrete down/recovered events per instance."""
    open_events: Dict[str, Dict[str, Any]] = {}
    closed_events: List[Dict[str, Any]] = []

    for snapshot in snapshots:
        tick = snapshot.get("tick")
        for instance in snapshot.get("instances", []):
            name = instance["name"]
            healthy = instance.get("is_healthy", True)
            if not healthy and name not in open_events:
                open_events[name] = {"instance": name, "start_tick": tick}
            elif healthy and name in open_events:
                event = open_events.pop(name)
                event["end_tick"] = tick
                event["recovered"] = True
                event["duration_ticks"] = tick - event["start_tick"]
                closed_events.append(event)

    last_tick = snapshots[-1]["tick"] if snapshots else 0
    for event in open_events.values():
        event["end_tick"] = last_tick
        event["recovered"] = False
        event["duration_ticks"] = last_tick - event["start_tick"]
        closed_events.append(event)

    closed_events.sort(key=lambda event: (event["instance"], event["start_tick"]))
    return closed_events


def summarize_failure_recovery(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """How failures were handled: how many, how long instances stayed down, and traffic lost."""
    events = detect_failure_events(snapshots)
    recovered = [event for event in events if event["recovered"]]
    durations = [event["duration_ticks"] for event in recovered]

    outage_ticks = {
        snapshot["tick"]
        for snapshot in snapshots
        if any(not inst.get("is_healthy", True) for inst in snapshot.get("instances", []))
    }
    dropped_total = sum(snapshot.get("dropped_requests", 0) for snapshot in snapshots)
    dropped_during_outages = sum(
        snapshot.get("dropped_requests", 0) for snapshot in snapshots if snapshot.get("tick") in outage_ticks
    )

    return {
        "events": events,
        "total_events": len(events),
        "recovered_events": len(recovered),
        "unresolved_events": len(events) - len(recovered),
        "recovery_ticks": _stat_summary(durations),
        "outage_tick_count": len(outage_ticks),
        "dropped_requests_total": dropped_total,
        "dropped_requests_during_outages": dropped_during_outages,
    }


def detect_spikes(snapshots: List[Dict[str, Any]], z_threshold: float = 2.0) -> List[Dict[str, Any]]:
    """Flag ticks whose arrival count is a statistical outlier vs. the run's own baseline."""
    arrivals = [snapshot.get("arrivals", 0) for snapshot in snapshots]
    if len(arrivals) < 3:
        return []

    mean = statistics.fmean(arrivals)
    stdev = statistics.pstdev(arrivals)
    spikes = []
    for snapshot, count in zip(snapshots, arrivals):
        if count <= mean:
            continue
        z_score = (count - mean) / stdev if stdev > 0 else float("inf")
        if z_score >= z_threshold:
            spikes.append(
                {
                    "tick": snapshot.get("tick"),
                    "arrivals": count,
                    "baseline_mean": mean,
                    "z_score": z_score,
                }
            )
    return spikes


def summarize_spike_response(
    snapshots: List[Dict[str, Any]],
    fairness: Optional[Dict[str, Any]] = None,
    window: int = 3,
) -> Dict[str, Any]:
    """How quickly fairness recovers after a traffic spike, and what it cost in dropped requests."""
    spikes = detect_spikes(snapshots)
    fairness = fairness if fairness is not None else analyze_fairness(snapshots)
    jains_by_tick = {point["tick"]: point["jains_index_load"] for point in fairness["timeline"]}
    spread_by_tick = {point["tick"]: point["load_spread"] for point in fairness["timeline"]}
    dropped_by_tick = {snapshot["tick"]: snapshot.get("dropped_requests", 0) for snapshot in snapshots}
    ticks = [snapshot["tick"] for snapshot in snapshots]

    responses = []
    for spike in spikes:
        tick = spike["tick"]
        pre_ticks = [t for t in ticks if tick - window <= t < tick]
        baseline_jains = _mean([jains_by_tick[t] for t in pre_ticks]) if pre_ticks else 1.0
        threshold = baseline_jains * 0.95

        recovery_ticks: Optional[int] = None
        for offset, t in enumerate((t for t in ticks if t > tick), start=1):
            if jains_by_tick.get(t, 0.0) >= threshold:
                recovery_ticks = offset
                break

        responses.append(
            {
                "tick": tick,
                "arrivals": spike["arrivals"],
                "z_score": spike["z_score"],
                "baseline_jains_index": baseline_jains,
                "load_spread_at_spike": spread_by_tick.get(tick, 0.0),
                "dropped_requests_at_spike": dropped_by_tick.get(tick, 0),
                "recovery_ticks": recovery_ticks,
            }
        )

    recovery_values = [r["recovery_ticks"] for r in responses if r["recovery_ticks"] is not None]

    return {
        "spikes": responses,
        "spike_count": len(responses),
        "recovery_ticks": _stat_summary(recovery_values),
        "unresolved_spikes": sum(1 for r in responses if r["recovery_ticks"] is None),
    }


def selection_distribution(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Observed selection share per instance vs. the share its capacity would predict."""
    if not snapshots:
        return {"observed_counts": {}, "expected_share": {}, "total_selections": 0, "chi_square": 0.0}

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

    return {
        "observed_counts": observed_counts,
        "expected_share": expected_share,
        "total_selections": total_selections,
        "chi_square": chi_square,
    }


def analyze_run(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Full pattern report for one simulation run: fairness, failure recovery, spikes, selection skew."""
    fairness = analyze_fairness(snapshots)
    return {
        "fairness": fairness,
        "failure_recovery": summarize_failure_recovery(snapshots),
        "spikes": summarize_spike_response(snapshots, fairness=fairness),
        "selection_distribution": selection_distribution(snapshots),
    }


def aggregate_stress_runs(run_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Cross-run statistics (mean/stdev/min/max) for the key characteristics across a stress-test suite."""

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

    return {
        "mean_estimated_load": _stat_summary(extract(["mean_estimated_load"])),
        "max_estimated_load": _stat_summary(extract(["max_estimated_load"])),
        "load_spread": _stat_summary(extract(["fairness", "load_spread"])),
        "jains_index_load": _stat_summary(extract(["patterns", "fairness", "mean_jains_index_load"])),
        "gini_load": _stat_summary(extract(["patterns", "fairness", "mean_gini_load"])),
        "failure_recovery_ticks_mean": _stat_summary(
            extract(["patterns", "failure_recovery", "recovery_ticks", "mean"])
        ),
        "dropped_requests_total": _stat_summary(extract(["patterns", "failure_recovery", "dropped_requests_total"])),
        "spike_count": _stat_summary(extract(["patterns", "spikes", "spike_count"])),
        "spike_recovery_ticks_mean": _stat_summary(extract(["patterns", "spikes", "recovery_ticks", "mean"])),
    }
