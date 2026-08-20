from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .instance import Client, Instance
from .policies.base import Policy

__all__ = ["Client", "Instance", "LoadBalancer", "Policy"]


class LoadBalancer:
    def __init__(self, policy: Policy, instances: Optional[Iterable[Instance]] = None):
        self.policy = policy
        self.instances: List[Instance] = list(instances or [])
        self.selection_history: List[str] = []

    def add_instance(self, instance: Instance) -> None:
        self.instances.append(instance)

    def remove_instance(self, instance_name: str) -> None:
        self.instances = [
            instance for instance in self.instances if instance.name != instance_name
        ]

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
