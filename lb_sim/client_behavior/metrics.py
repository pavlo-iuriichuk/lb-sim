from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from lb_sim.metrics import load_metrics_source

from .base import ClientBehavior


class MetricsClientBehavior(ClientBehavior):
    def __init__(self, source: str | Path, *, format_name: str | None = None) -> None:
        self.source = Path(source)
        self.format_name = format_name
        self._records = self._load_records()

    def _load_records(self) -> dict[int, int]:
        path = self.source
        suffix = path.suffix.lower()

        if suffix in {".json"}:
            payload = json.loads(path.read_text())
            if isinstance(payload, dict):
                payload = [payload]
            return {
                int(record["tick"]): int(record.get("arrivals", 0))
                for record in payload
                if isinstance(record, dict) and "tick" in record
            }

        if suffix in {".csv", ".tsv"}:
            delimiter = "," if suffix == ".csv" else "\t"
            with path.open(newline="") as handle:
                rows = list(csv.DictReader(handle, delimiter=delimiter))
            return {
                int(row["tick"]): int(row.get("arrivals", 0))
                for row in rows
                if isinstance(row, dict) and "tick" in row
            }

        try:
            records = load_metrics_source(path, format_name=self.format_name)
        except ValueError as exc:
            if "instances" not in str(exc):
                raise
            records = []
            for line in path.read_text().splitlines():
                if not line.strip() or line.strip().startswith("#"):
                    continue
                if "|" in line:
                    raw_tick, raw_arrivals = (
                        part.strip() for part in line.split("|", 1)
                    )
                else:
                    raw_tick, raw_arrivals = line.strip().split(",", 1)
                records.append({"tick": int(raw_tick), "arrivals": int(raw_arrivals)})

        mapped: dict[int, int] = {}
        for record in records:
            tick_value = record.get("tick")
            tick = int(tick_value) if tick_value is not None else 0
            arrivals = int(record.get("arrivals", 0))
            mapped[tick] = arrivals
        return mapped

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return self._records.get(int(tick), 0)
