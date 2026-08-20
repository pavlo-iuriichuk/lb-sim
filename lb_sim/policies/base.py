from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, List


class Policy(ABC):
    @abstractmethod
    def select(self, instances: Iterable[Any], context: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError

    def _healthy_instances(self, instances: Iterable[Any]) -> List[Any]:
        return [instance for instance in instances if getattr(instance, "is_healthy", True)]
