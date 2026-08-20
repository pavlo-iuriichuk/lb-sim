from lb_sim.analysis import (
    aggregate_stress_runs,
    analyze_run,
    coefficient_of_variation,
    detect_failure_events,
    detect_spikes,
    gini_coefficient,
    jains_fairness_index,
    selection_distribution,
    summarize_failure_recovery,
    summarize_spike_response,
)


def test_jains_fairness_index_is_one_when_perfectly_even():
    assert jains_fairness_index([5.0, 5.0, 5.0, 5.0]) == 1.0


def test_jains_fairness_index_drops_when_skewed_to_one_instance():
    even = jains_fairness_index([5.0, 5.0, 5.0, 5.0])
    skewed = jains_fairness_index([20.0, 0.0, 0.0, 0.0])
    assert skewed < even
    assert skewed == 1 / 4


def test_jains_fairness_index_handles_empty_and_zero_load():
    assert jains_fairness_index([]) == 1.0
    assert jains_fairness_index([0.0, 0.0, 0.0]) == 1.0


def test_gini_coefficient_is_zero_when_even_and_positive_when_skewed():
    assert gini_coefficient([5.0, 5.0, 5.0]) == 0.0
    assert gini_coefficient([10.0, 0.0, 0.0]) > 0.0


def test_coefficient_of_variation_zero_for_identical_values():
    assert coefficient_of_variation([3.0, 3.0, 3.0]) == 0.0
    assert coefficient_of_variation([1.0, 3.0]) > 0.0


def test_detect_failure_events_tracks_down_and_recovered_instances():
    snapshots = [
        {"tick": 0, "instances": [{"name": "a", "is_healthy": True}, {"name": "b", "is_healthy": True}]},
        {"tick": 1, "instances": [{"name": "a", "is_healthy": False}, {"name": "b", "is_healthy": True}]},
        {"tick": 2, "instances": [{"name": "a", "is_healthy": False}, {"name": "b", "is_healthy": True}]},
        {"tick": 3, "instances": [{"name": "a", "is_healthy": True}, {"name": "b", "is_healthy": False}]},
    ]

    events = detect_failure_events(snapshots)

    a_event = next(e for e in events if e["instance"] == "a")
    b_event = next(e for e in events if e["instance"] == "b")
    assert a_event["recovered"] is True
    assert a_event["duration_ticks"] == 2
    assert b_event["recovered"] is False
    assert b_event["duration_ticks"] == 0


def test_summarize_failure_recovery_counts_dropped_requests_during_outages():
    snapshots = [
        {"tick": 0, "dropped_requests": 0, "instances": [{"name": "a", "is_healthy": True}]},
        {"tick": 1, "dropped_requests": 3, "instances": [{"name": "a", "is_healthy": False}]},
        {"tick": 2, "dropped_requests": 0, "instances": [{"name": "a", "is_healthy": True}]},
    ]

    summary = summarize_failure_recovery(snapshots)

    assert summary["total_events"] == 1
    assert summary["recovered_events"] == 1
    assert summary["dropped_requests_total"] == 3
    assert summary["dropped_requests_during_outages"] == 3


def test_detect_spikes_flags_transient_burst_but_not_steady_baseline():
    steady = [{"tick": t, "arrivals": 3} for t in range(10)]
    assert detect_spikes(steady) == []

    bursty = [{"tick": t, "arrivals": a} for t, a in enumerate([2, 2, 2, 2, 20, 2, 2, 2, 2, 2])]
    spikes = detect_spikes(bursty)
    assert len(spikes) == 1
    assert spikes[0]["tick"] == 4


def test_summarize_spike_response_reports_recovery_ticks():
    snapshots = []
    for tick, arrivals in enumerate([2, 2, 2, 2, 20, 2, 2, 2, 2, 2]):
        loads = [1.0, 1.0] if tick != 4 else [9.0, 1.0]
        snapshots.append(
            {
                "tick": tick,
                "arrivals": arrivals,
                "dropped_requests": 0,
                "instances": [
                    {"name": "a", "estimated_load": loads[0], "current_connections": 0, "is_healthy": True},
                    {"name": "b", "estimated_load": loads[1], "current_connections": 0, "is_healthy": True},
                ],
                "selection_history": [],
            }
        )

    response = summarize_spike_response(snapshots)

    assert response["spike_count"] == 1
    assert response["spikes"][0]["recovery_ticks"] == 1


def test_selection_distribution_reports_chi_square_for_uneven_split():
    snapshots = [
        {
            "tick": 0,
            "instances": [
                {"name": "a", "capacity": 10.0},
                {"name": "b", "capacity": 10.0},
            ],
            "selection_history": ["a", "a", "a", "a", "b"],
        }
    ]

    result = selection_distribution(snapshots)

    assert result["observed_counts"] == {"a": 4, "b": 1}
    assert result["total_selections"] == 5
    assert result["chi_square"] > 0.0


def test_analyze_run_combines_all_reports():
    snapshots = [
        {
            "tick": 0,
            "arrivals": 2,
            "dropped_requests": 0,
            "instances": [
                {"name": "a", "capacity": 10.0, "estimated_load": 1.0, "current_connections": 1, "is_healthy": True},
                {"name": "b", "capacity": 10.0, "estimated_load": 1.0, "current_connections": 1, "is_healthy": True},
            ],
            "selection_history": ["a", "b"],
        }
    ]

    report = analyze_run(snapshots)

    assert set(report) == {"fairness", "failure_recovery", "spikes", "selection_distribution"}


def test_aggregate_stress_runs_computes_cross_run_statistics():
    run_summaries = [
        {"mean_estimated_load": 10.0, "patterns": {"fairness": {"mean_jains_index_load": 0.9}}},
        {"mean_estimated_load": 20.0, "patterns": {"fairness": {"mean_jains_index_load": 0.7}}},
    ]

    aggregate = aggregate_stress_runs(run_summaries)

    assert aggregate["mean_estimated_load"]["mean"] == 15.0
    assert aggregate["jains_index_load"]["min"] == 0.7
    assert aggregate["jains_index_load"]["max"] == 0.9
