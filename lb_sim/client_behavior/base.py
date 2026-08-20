from __future__ import annotations

import random
from abc import ABC, abstractmethod


class ClientBehavior(ABC):
    @abstractmethod
    def generate_count(self, tick: int, rng: random.Random) -> int:
        raise NotImplementedError
