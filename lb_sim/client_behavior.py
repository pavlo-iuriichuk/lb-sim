from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Iterable, Optional


class ClientBehavior(ABC):
    @abstractmethod
    def generate_count(self, tick: int, rng: random.Random) -> int:
        raise NotImplementedError


class ConstantClientBehavior(ClientBehavior):
    def __init__(self, base_clients: int = 1) -> None:
        self.base_clients = max(0, int(base_clients))

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return self.base_clients


class LinearClientBehavior(ClientBehavior):
    def __init__(self, base_clients: int = 1, slope: float = 1.0) -> None:
        self.base_clients = max(0, int(base_clients))
        self.slope = float(slope)

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return max(0, int(self.base_clients + self.slope * tick))


class ExponentialClientBehavior(ClientBehavior):
    def __init__(self, base_clients: int = 1, growth_factor: float = 2.0) -> None:
        self.base_clients = max(0, int(base_clients))
        self.growth_factor = max(1.0, float(growth_factor))

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return max(0, int(self.base_clients * (self.growth_factor ** max(0, tick))))


class RandomClientBehavior(ClientBehavior):
    def __init__(self, min_clients: int = 0, max_clients: int = 10) -> None:
        self.min_clients = max(0, int(min_clients))
        self.max_clients = max(self.min_clients, int(max_clients))

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return rng.randint(self.min_clients, self.max_clients)


BEHAVIOR_MAP = {
    "constant": ConstantClientBehavior,
    "linear": LinearClientBehavior,
    "exponential": ExponentialClientBehavior,
    "random": RandomClientBehavior,
}


def create_client_behavior(name: str, **kwargs: Any) -> ClientBehavior:
    behavior_cls = BEHAVIOR_MAP.get(name)
    if behavior_cls is None:
        raise ValueError(f"Unsupported client behavior: {name}")
    return behavior_cls(**kwargs)
