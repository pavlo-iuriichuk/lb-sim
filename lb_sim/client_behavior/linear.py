from __future__ import annotations

import random

from .base import ClientBehavior


class LinearClientBehavior(ClientBehavior):
    def __init__(self, base_clients: int = 1, slope: float = 1.0) -> None:
        self.base_clients = max(0, int(base_clients))
        self.slope = float(slope)

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return max(0, int(self.base_clients + self.slope * tick))
