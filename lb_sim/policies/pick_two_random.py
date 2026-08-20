from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any, Iterable

from .base import Policy

if TYPE_CHECKING:
    from ..domain import Instance


class PickTwoRandomThenLeastLoadedPolicy(Policy):
    def __init__(self, rng_seed: int | None = None) -> None:
        self._rng = random.Random(rng_seed)

    def select(self, instances: Iterable[Instance], context: dict[str, Any] | None = None) -> Instance:
        healthy = self._healthy_instances(list(instances))
        if not healthy:
            raise ValueError("No healthy instances available")

        if len(healthy) == 1:
            return healthy[0]

        left, right = self._rng.sample(healthy, 2)
        return min((left, right), key=lambda instance: (instance.current_connections, instance.estimated_load, instance.name))
