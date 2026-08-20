from __future__ import annotations

from typing import Any, Iterable

from ..instance import Instance
from .base import Policy


class LeastConnectionsPolicy(Policy):
    def select(
        self, instances: Iterable[Instance], context: dict[str, Any] | None = None
    ) -> Instance:
        healthy = self._healthy_instances(instances)
        if not healthy:
            raise ValueError("No healthy instances available")

        return min(
            healthy,
            key=lambda instance: (
                instance.current_connections,
                instance.estimated_load,
            ),
        )
