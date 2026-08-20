from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def validate_metrics_source(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        raise ValueError("Metrics source must be a list of records")

    for index, record in enumerate(data):
        if not isinstance(record, dict):
            raise ValueError(f"Record at index {index} must be a dictionary")
        if "tick" not in record:
            raise ValueError(f"Record at index {index} is missing a 'tick' field")
        if "instances" not in record:
            raise ValueError(f"Record at index {index} is missing an 'instances' field")
        if not isinstance(record["instances"], list):
            raise ValueError(f"Record at index {index} has a non-list 'instances' field")
        for instance in record["instances"]:
            if not isinstance(instance, dict):
                raise ValueError(f"Instance record in tick {record['tick']} must be a dictionary")
            if "name" not in instance:
                raise ValueError(f"Instance in tick {record['tick']} is missing a name")

    return data


def load_metrics_source(source: str | Path) -> list[dict[str, Any]]:
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Metrics source not found: {source}")

    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text())
        if isinstance(data, dict):
            data = [data]
        return validate_metrics_source(list(data))

    if suffix in {".csv", ".tsv"}:
        delimiter = "," if suffix == ".csv" else "\t"
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter=delimiter))
        return validate_metrics_source([dict(row) for row in rows])

    raise ValueError(f"Unsupported metrics file type: {path.suffix}")


def load_metrics_from_source(source: str | Path) -> list[dict[str, Any]]:
    return load_metrics_source(source)
