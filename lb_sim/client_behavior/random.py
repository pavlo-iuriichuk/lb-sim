from __future__ import annotations

import random

from .base import ClientBehavior


class RandomClientBehavior(ClientBehavior):
    def __init__(self, min_clients: int = 0, max_clients: int = 10) -> None:
        self.min_clients = max(0, int(min_clients))
        self.max_clients = max(self.min_clients, int(max_clients))

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return rng.randint(self.min_clients, self.max_clients)
