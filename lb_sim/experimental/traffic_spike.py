from __future__ import annotations

import random

from lb_sim.client_behavior.base import ClientBehavior


class SpikeClientBehavior(ClientBehavior):
    def __init__(
        self, base_clients: int = 1, spike_tick: int = 5, spike_multiplier: float = 2.0
    ) -> None:
        self.base_clients = max(0, int(base_clients))
        self.spike_tick = int(spike_tick)
        self.spike_multiplier = max(1.0, float(spike_multiplier))

    def generate_count(self, tick: int, rng: random.Random) -> int:
        if tick >= self.spike_tick:
            return max(0, int(self.base_clients * self.spike_multiplier))
        return self.base_clients
