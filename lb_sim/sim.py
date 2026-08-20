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

from .client_behavior import ClientBehavior, create_client_behavior
from .domain import Client, Instance, LoadBalancer
from .experimental import LeastLatencyPolicy
from .metrics import load_metrics_source, validate_metrics_source
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
    client_behavior: str = "constant"
    client_behaviour: str | None = None
    client_workload_mean: float = 1.0
    client_workload_stddev: float = 0.5
    failure_rate: float = 0.0
    unhealthy_instances: str = ""
    metrics_source: str | None = None
    metrics_format: str | None = None
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
        self.behavior = self._create_behavior(config.client_behavior or config.client_behaviour or "constant")
        self.policy = self._create_policy(config.policy_name)
        self.metrics = (
            validate_metrics_source(load_metrics_source(config.metrics_source, format_name=config.metrics_format))
            if config.metrics_source
            else []
        )

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

    def _create_behavior(self, behavior_name: str) -> ClientBehavior:
        if behavior_name == "constant":
            return create_client_behavior("constant", base_clients=self.config.clients_per_tick)
        if behavior_name == "linear":
            return create_client_behavior("linear", base_clients=self.config.clients_per_tick, slope=1.0)
        if behavior_name == "exponential":
            return create_client_behavior("exponential", base_clients=self.config.clients_per_tick, growth_factor=2.0)
        if behavior_name == "random":
            return create_client_behavior("random", min_clients=0, max_clients=max(1, self.config.clients_per_tick * 2))
        return create_client_behavior(behavior_name, base_clients=self.config.clients_per_tick)

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

        if self.metrics:
            for tick_record in self.metrics:
                tick = int(tick_record.get("tick", len(snapshots)))
                arrivals = int(tick_record.get("arrivals", 0))
                instance_state = tick_record.get("instances", [])

                for item in instance_state:
                    name = item.get("name")
                    instance = next((candidate for candidate in lb.instances if candidate.name == name), None)
                    if instance is None:
                        continue
                    instance.current_connections = int(item.get("current_connections", instance.current_connections))
                    instance.estimated_load = float(item.get("estimated_load", instance.estimated_load))
                    instance.is_healthy = bool(item.get("is_healthy", instance.is_healthy))
                    instance.cpu_usage = float(item.get("cpu_usage", instance.cpu_usage))
                    instance.latency_ms = float(item.get("latency_ms", instance.latency_ms))

                for _ in range(arrivals):
                    workload = max(0.1, self.rng.gauss(self.config.client_workload_mean, self.config.client_workload_stddev))
                    client = Client(
                        client_id=f"replay-client-{tick}-{_}",
                        arrival_tick=tick,
                        workload=workload,
                        duration_ticks=max(1, int(self.rng.randint(1, 4))),
                    )
                    lb.dispatch(client)

                state = {
                    "tick": tick,
                    "arrivals": arrivals,
                    "instances": [instance.snapshot() for instance in lb.instances],
                    "selection_history": list(lb.selection_history),
                }
                snapshots.append(state)
        else:
            for tick in range(self.config.ticks):
                arrivals = self.behavior.generate_count(tick, self.rng)
                for index in range(arrivals):
                    workload = max(0.1, self.rng.gauss(self.config.client_workload_mean, self.config.client_workload_stddev))
                    client = Client(
                        client_id=f"client-{tick}-{index}",
                        arrival_tick=tick,
                        workload=workload,
                        duration_ticks=max(1, int(self.rng.randint(1, 4))),
                    )
                    lb.dispatch(client)

                state = {
                    "tick": tick,
                    "arrivals": arrivals,
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


def compare_policies(policy_names: Iterable[str], config: SimulationConfig | None = None) -> dict[str, dict[str, Any]]:
    base_config = config or SimulationConfig()
    summaries: dict[str, dict[str, Any]] = {}
    for policy_name in policy_names:
        cfg = SimulationConfig(
            machines=base_config.machines,
            ticks=base_config.ticks,
            clients_per_tick=base_config.clients_per_tick,
            policy_name=policy_name,
            client_behavior=base_config.client_behavior,
            client_behaviour=base_config.client_behaviour,
            client_workload_mean=base_config.client_workload_mean,
            client_workload_stddev=base_config.client_workload_stddev,
            failure_rate=base_config.failure_rate,
            unhealthy_instances=base_config.unhealthy_instances,
            seed=base_config.seed,
            output_dir=base_config.output_dir,
            metrics_source=base_config.metrics_source,
        )
        summaries[policy_name] = Simulator(cfg).run().summary
    return summaries
