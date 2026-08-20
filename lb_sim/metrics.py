from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Callable


METRICS_FORMATS: dict[str, Callable[[str | Path], list[dict[str, Any]]]] = {}


def register_metrics_format(name: str, loader: Callable[[str | Path], list[dict[str, Any]]]) -> None:
    METRICS_FORMATS[name.lower()] = loader


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


def _json_loader(source: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(source).read_text())
    if isinstance(data, dict):
        data = [data]
    return validate_metrics_source(list(data))


def _csv_loader(source: str | Path) -> list[dict[str, Any]]:
    path = Path(source)
    delimiter = "," if path.suffix.lower() == ".csv" else "\t"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=delimiter))
    return validate_metrics_source([dict(row) for row in rows])


def _text_loader(source: str | Path) -> list[dict[str, Any]]:
    path = Path(source)
    records: list[dict[str, Any]] = []
    lines = path.read_text().splitlines()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.lower().startswith("tick|") or stripped.lower().startswith("tick,"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 2:
            continue
        tick, instances = parts[0], parts[1:]
        records.append({"tick": tick, "instances": [{"name": item} for item in instances if item]})
    return validate_metrics_source(records)


register_metrics_format("json", _json_loader)
register_metrics_format("csv", _csv_loader)
register_metrics_format("tsv", _csv_loader)
register_metrics_format("text", _text_loader)


def load_metrics_source(source: str | Path, format_name: str | None = None) -> list[dict[str, Any]]:
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Metrics source not found: {source}")

    if format_name is not None:
        loader = METRICS_FORMATS.get(format_name.lower())
        if loader is None:
            raise ValueError(f"Unsupported metrics format: {format_name}")
        return loader(path)

    suffix = path.suffix.lower().lstrip(".")
    if suffix in METRICS_FORMATS:
        return METRICS_FORMATS[suffix](path)

    if suffix in {"json", "csv", "tsv", "txt", "text"}:
        fallback_loader = METRICS_FORMATS.get(suffix, METRICS_FORMATS["text"])
        return fallback_loader(path)

    raise ValueError(f"Unsupported metrics file type: {path.suffix}")


def load_metrics_from_source(source: str | Path) -> list[dict[str, Any]]:
    return load_metrics_source(source)
