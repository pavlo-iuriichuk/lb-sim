from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from lb_sim.policies.base import Policy

if TYPE_CHECKING:
    from lb_sim.domain import Instance


class LeastLatencyPolicy(Policy):
    """Experimental policy: prefer the healthiest, lowest-latency instance."""

    def select(self, instances: Iterable[Instance], context: dict[str, Any] | None = None) -> Instance:
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
