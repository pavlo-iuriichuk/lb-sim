"""Experimental policies live here. Add new load balancing strategies by creating
modules under this package and exposing them through a registration mechanism."""

from .least_latency import LeastLatencyPolicy

__all__ = ["LeastLatencyPolicy"]
