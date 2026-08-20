from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .base import Policy

if TYPE_CHECKING:
    from ..domain import Instance


class RoundRobinPolicy(Policy):
    def __init__(self) -> None:
        self._counter = 0

    def select(
        self, instances: Iterable[Instance], context: dict[str, Any] | None = None
    ) -> Instance:
        healthy = self._healthy_instances(instances)
        if not healthy:
            raise ValueError("No healthy instances available")

        instance = healthy[self._counter % len(healthy)]
        self._counter += 1
        return instance
