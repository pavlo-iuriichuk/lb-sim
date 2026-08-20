from __future__ import annotations

import importlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .domain import Client, Instance, LoadBalancer
from .experimental import LeastLatencyPolicy
from .policies import (
    LeastConnectionsPolicy,
    PickTwoRandomThenLeastLoadedPolicy,
    Policy,
    RoundRobinPolicy,
)


POLICY_MAP = {
    "round_robin": RoundRobinPolicy,
    "least_connections": LeastConnectionsPolicy,
    "pick_two_random": PickTwoRandomThenLeastLoadedPolicy,
    "experimental.least_latency:LeastLatencyPolicy": LeastLatencyPolicy,
    "experimental.least_latency": LeastLatencyPolicy,
}


@dataclass
class SimulationConfig:
    machines: int = 3
    ticks: int = 10
    clients_per_tick: int = 3
    policy_name: str = "round_robin"
    client_workload_mean: float = 1.0
    client_workload_stddev: float = 0.5
    failure_rate: float = 0.0
    unhealthy_instances: str = ""
    seed: int = 0
    output_dir: str = "output"


@dataclass
class SimulationResult:
    config: SimulationConfig
    snapshots: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def save(self, directory: str | Path) -> None:
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "timeline.json").write_text(json.dumps(self.snapshots, indent=2))
        (output_dir / "summary.json").write_text(json.dumps(self.summary, indent=2))

        if self.snapshots:
            ticks = [snapshot["tick"] for snapshot in self.snapshots]
            names = [inst["name"] for inst in self.snapshots[0]["instances"]]
            connection_series = {
                name: [snapshot["instances"][idx]["current_connections"] for snapshot in self.snapshots]
                for idx, name in enumerate(names)
            }
            load_series = {
                name: [snapshot["instances"][idx]["estimated_load"] for snapshot in self.snapshots]
                for idx, name in enumerate(names)
            }

            fig, ax = plt.subplots(figsize=(10, 5))
            for name, values in connection_series.items():
                ax.plot(ticks, values, label=name)
            ax.set_title("Client connections by instance")
            ax.set_xlabel("tick")
            ax.set_ylabel("connections")
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(output_dir / "connections_timeline.png")
            plt.close(fig)

            fig, ax = plt.subplots(figsize=(10, 5))
            for name, values in load_series.items():
                ax.plot(ticks, values, label=name)
            ax.set_title("Estimated load by instance")
            ax.set_xlabel("tick")
            ax.set_ylabel("estimated load")
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(output_dir / "load_timeline.png")
            plt.close(fig)


class Simulator:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = random.Random(config.seed)
        self.policy = self._create_policy(config.policy_name)

    def _create_policy(self, policy_name: str) -> Policy:
        name = policy_name.strip()

        if ":" in name:
            module_path, class_name = name.split(":", 1)
            for candidate in (module_path, f"lb_sim.{module_path}"):
                try:
                    module = importlib.import_module(candidate)
                    policy_cls = getattr(module, class_name)
                    return self._instantiate_policy(policy_cls)
                except (ImportError, AttributeError):
                    continue
            raise ValueError(f"Unsupported policy: {policy_name}")

        if name in POLICY_MAP:
            policy_cls = POLICY_MAP[name]
            return self._instantiate_policy(policy_cls)

        for candidate in (name, f"lb_sim.{name}"):
            try:
                module = importlib.import_module(candidate)
                break
            except ModuleNotFoundError:
                continue
        else:
            raise ValueError(f"Unsupported policy: {policy_name}")

        if hasattr(module, "Policy"):
            policy_cls = module.Policy
            return self._instantiate_policy(policy_cls)

        candidates = [getattr(module, obj) for obj in dir(module) if obj.lower().endswith("policy")]
        if not candidates:
            raise ValueError(f"Unsupported policy: {policy_name}")
        policy_cls = candidates[0]
        return self._instantiate_policy(policy_cls)

    def _instantiate_policy(self, policy_cls: type[Policy]) -> Policy:
        if policy_cls.__name__ == "PickTwoRandomThenLeastLoadedPolicy":
            return policy_cls(rng_seed=self.config.seed)
        return policy_cls()

    def build_instances(self) -> List[Instance]:
        unhealthy_names = {name.strip() for name in self.config.unhealthy_instances.split(",") if name.strip()}
        instances: List[Instance] = []
        for index in range(self.config.machines):
            machine_name = f"machine-{index}"
            failure_rate = self.config.failure_rate if index % 2 == 0 else self.config.failure_rate * 0.5
            instance = Instance(
                name=machine_name,
                capacity=10.0 + index,
                estimated_load=0.0,
                failure_rate=failure_rate,
            )
            if machine_name in unhealthy_names or (index == 0 and self.config.failure_rate >= 1.0):
                instance.is_healthy = False
            instances.append(instance)
        return instances

    def run(self) -> SimulationResult:
        lb = LoadBalancer(self.policy, self.build_instances())
        snapshots: List[Dict[str, Any]] = []

        for tick in range(self.config.ticks):
            for _ in range(self.config.clients_per_tick):
                workload = max(0.1, self.rng.gauss(self.config.client_workload_mean, self.config.client_workload_stddev))
                client = Client(
                    client_id=f"client-{tick}-{_}",
                    arrival_tick=tick,
                    workload=workload,
                    duration_ticks=max(1, int(self.rng.randint(1, 4))),
                )
                lb.dispatch(client)

            state = {
                "tick": tick,
                "instances": [instance.snapshot() for instance in lb.instances],
                "selection_history": list(lb.selection_history),
            }
            snapshots.append(state)

        summary = self._summarize(snapshots)
        result = SimulationResult(config=self.config, snapshots=snapshots, summary=summary)
        result.save(self.config.output_dir)
        return result

    def _summarize(self, snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
        last_snapshot = snapshots[-1] if snapshots else {"instances": []}
        workloads = [instance["estimated_load"] for instance in last_snapshot["instances"]]
        connections = [instance["current_connections"] for instance in last_snapshot["instances"]]

        mean_load = sum(workloads) / len(workloads) if workloads else 0.0
        mean_connections = sum(connections) / len(connections) if connections else 0.0
        max_load = max(workloads) if workloads else 0.0
        selected_count = len(last_snapshot["selection_history"]) if last_snapshot.get("selection_history") else 0

        return {
            "machines": len(last_snapshot["instances"]),
            "mean_estimated_load": mean_load,
            "mean_connections": mean_connections,
            "max_estimated_load": max_load,
            "selection_count": selected_count,
            "fairness": {
                "load_spread": max_load - min(workloads) if workloads else 0.0,
                "connection_spread": max(connections) - min(connections) if connections else 0.0,
            },
        }
