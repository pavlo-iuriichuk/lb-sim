from __future__ import annotations

import random

from .base import ClientBehavior


class ConstantClientBehavior(ClientBehavior):
    def __init__(self, base_clients: int = 1) -> None:
        self.base_clients = max(0, int(base_clients))

    def generate_count(self, tick: int, rng: random.Random) -> int:
        return self.base_clients
