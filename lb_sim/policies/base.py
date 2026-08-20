from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, List

from ..instance import Instance


class Policy(ABC):
    @abstractmethod
    def select(
        self, instances: Iterable[Instance], context: dict[str, Any] | None = None
    ) -> Instance:
        raise NotImplementedError

    def _healthy_instances(self, instances: Iterable[Instance]) -> List[Instance]:
        return [
            instance for instance in instances if getattr(instance, "is_healthy", True)
        ]
