# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -e '.[dev]'  # install lb-sim + its CLI entry point + pytest/mypy in editable mode

python -m pytest -q                          # run full test suite
python -m pytest tests/test_policies.py -q   # run one test file
python -m pytest tests/test_policies.py::test_round_robin_cycles_instances -q  # run a single test

python -m mypy           # type-check lb_sim, examples, and tests (config lives in pyproject.toml)

lb-sim run --machines 4 --ticks 50 --policy round_robin        # run a simulation, writes to ./output
lb-sim compare --policy round_robin --policy least_connections # compare policies head-to-head
lb-sim replay --metrics-source metrics.json --policy round_robin  # replay captured metrics
lb-sim analyze --timeline output/timeline.json                 # fairness/failure/spike report on a saved run
lb-sim stress-test --policy least_connections --runs 20 --failure-rate 0.1  # many-seed statistical stress test
lb-sim list-policies                                            # list built-in + experimental policies
```

There is no separate lint command; mypy is the only static check configured. `[tool.mypy]` in `pyproject.toml` runs in `strict` mode for `lb_sim`/`examples`, with an override relaxing `disallow_untyped_defs`/`disallow_incomplete_defs` for the three top-level test modules (`test_analysis`, `test_cli`, `test_policies` — they have no `__init__.py`, so mypy sees them as top-level module names, not `tests.*`).

## Architecture

The simulation has a fixed pipeline: `Simulator` (`lb_sim/sim.py`) owns a `LoadBalancer` (`lb_sim/domain.py`) which holds `Instance`s and delegates each `Client` dispatch to a `Policy` (`lb_sim/policies/`). Each tick, a `ClientBehavior` (`lb_sim/client_behavior/`) decides how many clients arrive; the `Simulator` dispatches them and records a snapshot. After the run, `lb_sim/analysis/` computes statistical reports over the full snapshot timeline, and `SimulationResult.save()` writes `timeline.json`, `summary.json`, and two matplotlib PNGs to the output directory.

**`Instance` and `Policy` type-hint each other across a package boundary, resolved via `TYPE_CHECKING`.** `domain.py` (`LoadBalancer.policy: Policy`) and `policies/base.py` (`Policy.select(...) -> Instance`) each need the other module's class purely for annotations, but a real (non-`TYPE_CHECKING`) import either direction would be circular. Both files guard the cross-import with `if TYPE_CHECKING: from ...`, which `from __future__ import annotations` makes safe at runtime (annotations are never evaluated) while still letting mypy resolve the names. Follow the same pattern in any new module that needs both types — importing `Instance` for real (not under `TYPE_CHECKING`) from `policies/` would reintroduce the cycle.

**Two simulation modes, one entry point.** `Simulator.run()` either generates synthetic ticks (`_simulate_ticks`) or replays a captured metrics file tick-by-tick (`_replay_metrics`), chosen by whether `config.metrics_source` is set. Both paths converge on the same `_build_snapshot`/`_summarize` logic, so replay and live simulation produce identically-shaped output.

**Pluggable policies and behaviors share one loading convention.** Both `Simulator._create_policy` and `create_client_behavior` (`lb_sim/client_behavior/registry.py`) resolve a name three ways, in order: (1) the built-in map (`POLICY_MAP` in `sim.py` / `BEHAVIOR_MAP` in `registry.py`), (2) a `module.path:ClassName` string, importing either as given or prefixed with `lb_sim.`, or (3) a bare module path whose module is scanned for a `Policy`/`ClientBehavior` class or any class whose name ends in `Policy`/`Behavior`. This is how `lb_sim.experimental.*` modules (e.g. `experimental.least_latency:LeastLatencyPolicy`, `experimental.traffic_spike:SpikeClientBehavior`) get loaded without being registered anywhere — new experimental policies/behaviors just need to live under `lb_sim/experimental/` and follow the naming convention.

**Dynamic health, not just initial state.** `Instance.failure_rate` is checked every tick during synthetic simulation via `Simulator._update_instance_health`, which calls `instance.update_health(rng.random())` — this is what makes instances fail and recover mid-run. Instances explicitly named in `--unhealthy-instances` are excluded from this per-tick roll and stay down for the whole run (a permanent/forced failure, distinct from the probabilistic `--failure-rate` mechanism). Dispatch to an instance with no healthy targets raises inside `Policy.select`/`LoadBalancer.dispatch`; `Simulator._dispatch_client` catches this and counts the request as dropped (`dropped_requests` in each snapshot) rather than crashing the run. Metrics-replay mode does *not* run dynamic health rolls — it applies `is_healthy` exactly as given in the captured record via `_apply_metric_snapshot`.

**`selection_history` on `LoadBalancer` is cumulative, not per-tick.** It grows across the whole run; `lb_sim/analysis/selection_distribution.py`'s `selection_distribution()` reads it only from the final snapshot. Anything that needs per-tick selection counts must diff consecutive snapshots' list lengths.

**Metrics format loaders are an open registry**, not a fixed enum: `register_metrics_format(name, loader)` in `lb_sim/metrics.py` adds a loader keyed by name; `load_metrics_source` picks a loader by explicit `--metrics-format` or by file suffix. `lb_sim/client_behavior/metrics.py` (`MetricsClientBehavior`) is a separate consumer of the same metrics files, used to drive arrival counts (`{"tick": ..., "arrivals": ...}`) rather than instance state — the two loaders read overlapping files for different purposes.

**`lb_sim/analysis/` is one module per analysis function, each returning a frozen dataclass, not a dict.** It operates purely on the snapshot list (`Simulator.run()`'s `snapshots`, i.e. the contents of `timeline.json`) and has no dependency on `Simulator`/`Policy` classes — this is why `lb-sim analyze` can run against any previously saved `timeline.json` file standalone. `patterns.py`'s `analyze_run()` is the single entry point, composing `fairness.py` (Jain's index, Gini coefficient per tick → `FairnessReport`), `failure_recovery.py` (built from `failure_events.py`'s down/recovered events → `FailureRecoveryReport`), `spike_response.py` (built from `spike_detection.py`'s z-score outlier ticks, with post-spike recovery timing → `SpikeReport`), and `selection_distribution.py` (chi-square vs. capacity-weighted expectation) into one `PatternReport`. `stress.py`'s `aggregate_stress_runs()` produces a `StressAggregate` across many seeds. Every module's report dataclass nests the previous layer's dataclasses (e.g. `PatternReport.fairness: FairnessReport`) rather than flattening to dicts — dict conversion happens exactly once, at the JSON-serialization boundary in `sim.py`/`cli.py`, via `dataclasses.asdict()`. Don't call `analyze_run()` (or any report function) expecting a dict back; consume it by attribute, and only `asdict()` right before `json.dumps()`.
