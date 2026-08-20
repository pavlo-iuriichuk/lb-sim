from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable


def load_metrics_source(source: str | Path) -> list[dict[str, Any]]:
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Metrics source not found: {source}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            return [data]
        return list(data)

    if suffix in {".csv", ".tsv"}:
        delimiter = "," if suffix == ".csv" else "\t"
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=delimiter))
        return [dict(row) for row in rows]

    raise ValueError(f"Unsupported metrics file type: {path.suffix}")


def load_metrics_from_source(source: str | Path) -> list[dict[str, Any]]:
    return load_metrics_source(source)
