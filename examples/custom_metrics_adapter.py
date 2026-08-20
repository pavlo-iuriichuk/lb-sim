from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lb_sim.metrics import register_metrics_format, validate_metrics_source


def jsonl_loader(source: str | Path) -> list[dict[str, Any]]:
    """Load newline-delimited JSON records.

    Each line is a JSON object with at least a tick and instances field.
    """
    records: list[dict[str, Any]] = []
    for line in Path(source).read_text().splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        records.append(payload)
    return validate_metrics_source(records)


register_metrics_format("jsonl", jsonl_loader)


if __name__ == "__main__":
    sample_path = Path("examples/sample_metrics.jsonl")
    sample_path.parent.mkdir(exist_ok=True)
    sample_path.write_text("""\
{"tick": 0, "instances": [{"name": "machine-0", "current_connections": 2, "estimated_load": 4.0}]}
{"tick": 1, "instances": [{"name": "machine-0", "current_connections": 5, "estimated_load": 8.0}]}
""")
    print(f"Registered format: jsonl")
    print(f"Loaded {len(jsonl_loader(sample_path))} records")
