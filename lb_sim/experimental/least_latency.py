from __future__ import annotations

from typing import Any, Iterable

from lb_sim.policies.base import Policy


class LeastLatencyPolicy(Policy):
    """Experimental policy: prefer the healthiest, lowest-latency instance."""

    def select(self, instances: Iterable[Any], context: dict[str, Any] | None = None) -> Any:
        healthy = self._healthy_instances(instances)
        if not healthy:
            raise ValueError("No healthy instances available")

        return min(
            healthy,
            key=lambda instance: (
                instance.latency_ms,
                instance.current_connections,
                instance.estimated_load,
                instance.name,
            ),
        )
