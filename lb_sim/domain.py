from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Instance:
    name: str
    capacity: float = 100.0
    current_connections: int = 0
    estimated_load: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    latency_ms: float = 0.0
    failure_rate: float = 0.0
    is_healthy: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.failure_rate = max(0.0, min(1.0, float(self.failure_rate)))
        self.is_healthy = bool(self.is_healthy)
        if self.failure_rate >= 1.0:
            self.is_healthy = False

    def update_health(self, random_value: Optional[float] = None) -> bool:
        if random_value is None:
            import random

            random_value = random.random()

        self.is_healthy = random_value > self.failure_rate
        return self.is_healthy

    def utilization(self) -> float:
        """Relative load on this machine."""
        if not self.is_healthy:
            return 0.0
        base = max(self.capacity, 1.0)
        return min(1.0, (self.estimated_load / base) if base else 0.0)

    def add_connection(self, client: "Client") -> None:
        if not self.is_healthy:
            raise ValueError(f"Instance {self.name} is unhealthy and cannot take traffic")
        self.current_connections += 1
        self.estimated_load += max(0.0, getattr(client, "workload", 0.0))
        self.cpu_usage = min(1.0, self.utilization() + (self.current_connections / max(self.capacity, 1.0)))

    def remove_connection(self) -> None:
        self.current_connections = max(0, self.current_connections - 1)
        self.cpu_usage = max(0.0, min(1.0, self.cpu_usage * 0.9))

    def snapshot(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "capacity": self.capacity,
            "current_connections": self.current_connections,
            "estimated_load": self.estimated_load,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "latency_ms": self.latency_ms,
            "is_healthy": self.is_healthy,
            "failure_rate": self.failure_rate,
            "utilization": self.utilization(),
        }


@dataclass
class Client:
    client_id: str
    arrival_tick: int
    workload: float = 1.0
    burstiness: float = 1.0
    duration_ticks: int = 1
    target_instance: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.workload = max(0.0, self.workload)
        self.burstiness = max(0.0, self.burstiness)


class LoadBalancer:
    def __init__(self, policy: Any, instances: Optional[Iterable[Instance]] = None):
        self.policy = policy
        self.instances: List[Instance] = list(instances or [])
        self.selection_history: List[str] = []

    def add_instance(self, instance: Instance) -> None:
        self.instances.append(instance)

    def remove_instance(self, instance_name: str) -> None:
        self.instances = [instance for instance in self.instances if instance.name != instance_name]

    def dispatch(self, client: Client) -> Instance:
        if not self.instances:
            raise ValueError("No instances available for dispatch")

        chosen = self.policy.select(self.instances, {"client": client})
        self.selection_history.append(chosen.name)
        chosen.add_connection(client)
        client.target_instance = chosen.name
        return chosen

    def snapshot(self) -> Dict[str, Any]:
        return {
            "instances": [instance.snapshot() for instance in self.instances],
            "selection_history": list(self.selection_history),
        }
