from __future__ import annotations

import random

from .base import ClientBehavior


class ExponentialClientBehavior(ClientBehavior):
    def __init__(self, base_clients: int = 1, growth_factor: float = 2.0) -> None:
        self.base_clients = max(0, int(base_clients))
        self.growth_factor = max(1.0, float(growth_factor))

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return max(0, int(self.base_clients * (self.growth_factor ** max(0, tick))))
