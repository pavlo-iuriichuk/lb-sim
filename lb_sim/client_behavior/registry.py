from __future__ import annotations

import importlib
from typing import Any, Callable, Dict

from .base import ClientBehavior
from .constant import ConstantClientBehavior
from .exponential import ExponentialClientBehavior
from .linear import LinearClientBehavior
from .metrics import MetricsClientBehavior
from .random import RandomClientBehavior

BEHAVIOR_MAP: Dict[str, Callable[..., ClientBehavior]] = {
    "constant": ConstantClientBehavior,
    "linear": LinearClientBehavior,
    "exponential": ExponentialClientBehavior,
    "random": RandomClientBehavior,
    "metrics": MetricsClientBehavior,
}


def create_client_behavior(name: str, **kwargs: Any) -> ClientBehavior:
    normalized = name.strip()

    if normalized in BEHAVIOR_MAP:
        return BEHAVIOR_MAP[normalized](**kwargs)

    if ":" in normalized:
        module_path, class_name = normalized.split(":", 1)
        for candidate in (module_path, f"lb_sim.{module_path}"):
            try:
                module = importlib.import_module(candidate)
                behavior_cls = getattr(module, class_name)
                return behavior_cls(**kwargs)  # type: ignore[no-any-return]
            except (ImportError, AttributeError):
                continue
        raise ValueError(f"Unsupported client behavior: {name}")

    for candidate in (normalized, f"lb_sim.{normalized}"):
        try:
            module = importlib.import_module(candidate)
            break
        except ModuleNotFoundError:
            continue
    else:
        raise ValueError(f"Unsupported client behavior: {name}")

    if hasattr(module, "ClientBehavior"):
        return module.ClientBehavior(**kwargs)  # type: ignore[no-any-return]

    for attr_name in dir(module):
        if attr_name.lower().endswith("clientbehavior") or attr_name.lower().endswith(
            "behavior"
        ):
            behavior_cls = getattr(module, attr_name)
            if callable(behavior_cls):
                return behavior_cls(**kwargs)  # type: ignore[no-any-return]

    raise ValueError(f"Unsupported client behavior: {name}")
