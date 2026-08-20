# lb-sim
Load Balancer policies stochastic simulator.

## Overview

`lb-sim` models traffic distribution across instances under different load-balancing policies, failure conditions, and traffic patterns. It can simulate synthetic workloads or replay previously captured metrics to compare policy decisions against real incidents.

## CLI usage

```bash
lb-sim run \
  --machines 4 \
  --ticks 50 \
  --clients-per-tick 10 \
  --policy round_robin \
  --client-behavior linear \
  --failure-rate 0.02

lb-sim compare \
  --machines 4 \
  --ticks 50 \
  --policy round_robin \
  --policy least_connections

lb-sim replay \
  --metrics-source metrics.json \
  --policy round_robin
```

## Metrics source format

The simulator accepts replay data as a list of records. Each record represents one tick and contains the observed instance state for that moment.

Required schema:

```json
[
  {
    "tick": 0,
    "arrivals": 10,
    "instances": [
      {"name": "machine-0", "current_connections": 4, "estimated_load": 8.0},
      {"name": "machine-1", "current_connections": 2, "estimated_load": 5.5}
    ]
  }
]
```

The `tick` field is required and must be present for every record. The `instances` field must be a list. Each item in `instances` must include a `name` field. Extra fields such as `estimated_load`, `current_connections`, or `is_healthy` are allowed and can be used by later replay or visualization code.

JSON and CSV/TSV files are supported automatically. Text files are also supported via the `text` loader if each row follows a simple `tick|instance_a|instance_b` shape.

## Extending metrics formats

New metric loaders can be registered at runtime without changing the simulator logic. The registry lives in `lb_sim.metrics` and is intentionally extensible.

```python
from lb_sim.metrics import register_metrics_format, validate_metrics_source
from pathlib import Path


def my_format_loader(source):
    records = []
    for line in Path(source).read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        tick, instance_name = line.split(",")
        records.append({
            "tick": int(tick),
            "instances": [{"name": instance_name.strip()}],
        })
    return validate_metrics_source(records)


register_metrics_format("custom", my_format_loader)
```

You can then use it explicitly:

```bash
lb-sim replay --metrics-source my-export.csv --metrics-format custom
```

This pattern keeps the replay pipeline stable while making it easy to plug in new sources later.

## Example custom adapter

A ready-to-run example is provided in `examples/custom_metrics_adapter.py`. It registers a `jsonl` loader for newline-delimited JSON metrics.

```bash
python examples/custom_metrics_adapter.py
```

## Policies and behaviors

The simulator ships with classic policies:

- `round_robin`
- `least_connections`
- `pick_two_random`
- `least_loaded`

It also supports traffic behaviors:

- `constant`
- `linear`
- `exponential`
- `random`

Experimental policies can be loaded from the `lb_sim.experimental` package or from an import path such as:

```bash
lb-sim run --policy experimental.least_latency:LeastLatencyPolicy
```
