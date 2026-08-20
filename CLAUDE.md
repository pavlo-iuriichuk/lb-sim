# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -e .        # install lb-sim and its CLI entry point in editable mode
pip install pytest       # test runner is not in project dependencies, install separately

python -m pytest -q                          # run full test suite
python -m pytest tests/test_policies.py -q   # run one test file
python -m pytest tests/test_policies.py::test_round_robin_cycles_instances -q  # run a single test

lb-sim run --machines 4 --ticks 50 --policy round_robin        # run a simulation, writes to ./output
lb-sim compare --policy round_robin --policy least_connections # compare policies head-to-head
lb-sim replay --metrics-source metrics.json --policy round_robin  # replay captured metrics
lb-sim analyze --timeline output/timeline.json                 # fairness/failure/spike report on a saved run
lb-sim stress-test --policy least_connections --runs 20 --failure-rate 0.1  # many-seed statistical stress test
lb-sim list-policies                                            # list built-in + experimental policies
```

There is no lint/type-check command configured in this repo.

## Architecture

The simulation has a fixed pipeline: `Simulator` (`lb_sim/sim.py`) owns a `LoadBalancer` (`lb_sim/domain.py`) which holds `Instance`s and delegates each `Client` dispatch to a `Policy` (`lb_sim/policies/`). Each tick, a `ClientBehavior` (`lb_sim/client_behavior/`) decides how many clients arrive; the `Simulator` dispatches them and records a snapshot. After the run, `lb_sim/analysis.py` computes statistical reports over the full snapshot timeline, and `SimulationResult.save()` writes `timeline.json`, `summary.json`, and two matplotlib PNGs to the output directory.

**Two simulation modes, one entry point.** `Simulator.run()` either generates synthetic ticks (`_simulate_ticks`) or replays a captured metrics file tick-by-tick (`_replay_metrics`), chosen by whether `config.metrics_source` is set. Both paths converge on the same `_build_snapshot`/`_summarize` logic, so replay and live simulation produce identically-shaped output.

**Pluggable policies and behaviors share one loading convention.** Both `Simulator._create_policy` and `create_client_behavior` (`lb_sim/client_behavior/registry.py`) resolve a name three ways, in order: (1) the built-in map (`POLICY_MAP` in `sim.py` / `BEHAVIOR_MAP` in `registry.py`), (2) a `module.path:ClassName` string, importing either as given or prefixed with `lb_sim.`, or (3) a bare module path whose module is scanned for a `Policy`/`ClientBehavior` class or any class whose name ends in `Policy`/`Behavior`. This is how `lb_sim.experimental.*` modules (e.g. `experimental.least_latency:LeastLatencyPolicy`, `experimental.traffic_spike:SpikeClientBehavior`) get loaded without being registered anywhere — new experimental policies/behaviors just need to live under `lb_sim/experimental/` and follow the naming convention.

**Dynamic health, not just initial state.** `Instance.failure_rate` is checked every tick during synthetic simulation via `Simulator._update_instance_health`, which calls `instance.update_health(rng.random())` — this is what makes instances fail and recover mid-run. Instances explicitly named in `--unhealthy-instances` are excluded from this per-tick roll and stay down for the whole run (a permanent/forced failure, distinct from the probabilistic `--failure-rate` mechanism). Dispatch to an instance with no healthy targets raises inside `Policy.select`/`LoadBalancer.dispatch`; `Simulator._dispatch_client` catches this and counts the request as dropped (`dropped_requests` in each snapshot) rather than crashing the run. Metrics-replay mode does *not* run dynamic health rolls — it applies `is_healthy` exactly as given in the captured record via `_apply_metric_snapshot`.

**`selection_history` on `LoadBalancer` is cumulative, not per-tick.** It grows across the whole run; `lb_sim/analysis.py`'s `selection_distribution` reads it only from the final snapshot. Anything that needs per-tick selection counts must diff consecutive snapshots' list lengths.

**Metrics format loaders are an open registry**, not a fixed enum: `register_metrics_format(name, loader)` in `lb_sim/metrics.py` adds a loader keyed by name; `load_metrics_source` picks a loader by explicit `--metrics-format` or by file suffix. `lb_sim/client_behavior/metrics.py` (`MetricsClientBehavior`) is a separate consumer of the same metrics files, used to drive arrival counts (`{"tick": ..., "arrivals": ...}`) rather than instance state — the two loaders read overlapping files for different purposes.

**`lb_sim/analysis.py` operates purely on the snapshot list** (`Simulator.run()`'s `snapshots`, i.e. the contents of `timeline.json`) and has no dependency on `Simulator`/`Policy` classes — this is why `lb-sim analyze` can run against any previously saved `timeline.json` file standalone. `analyze_run()` is the single entry point combining fairness (Jain's index, Gini coefficient per tick), failure/recovery event detection, spike detection (z-score on arrivals) with post-spike recovery timing, and selection-distribution skew (chi-square vs. capacity-weighted expectation). `sim.py`'s `_summarize()` embeds this under `summary["patterns"]`. `stress_test_policy()` runs many seeds via `Simulator.run(save=False)` (to avoid writing files per seed) and cross-run-aggregates via `aggregate_stress_runs()`.
