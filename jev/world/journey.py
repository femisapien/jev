"""Compare complete journeys in seconds, including failures and their recovery.

Edges are supplied by verified executors and observed discoveries. Naming an unsupported
mode does not make it an edge. Estimates carry their assumptions into planner evidence.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Cost:
    travel: float = 0.0
    interaction: float = 0.0
    wait: float = 0.0
    recovery: float = 0.0
    failure_probability: float = 0.0
    failure_recovery: float = 0.0

    def __post_init__(self):
        if any(not math.isfinite(v) or v < 0 for v in self.__dict__.values()):
            raise ValueError("journey costs must be finite and nonnegative")
        if self.failure_probability > 1:
            raise ValueError("failure probability exceeds one")

    @property
    def seconds(self) -> float:
        return (self.travel + self.interaction + self.wait + self.recovery
                + self.failure_probability * self.failure_recovery)


@dataclass(frozen=True)
class Edge:
    start: str
    end: str
    mode: str
    cost: Cost
    copper: int = 0
    requires: frozenset[str] = frozenset()
    verified: bool = False


def route(edges: tuple[Edge, ...], start: str, end: str, *, copper: int,
          known: frozenset[str], modes: frozenset[str]) -> tuple[Edge, ...] | None:
    """Shortest feasible journey with a money resource; retain time/money Pareto labels."""
    queue = [(0.0, 0, start, 0, ())]
    serial = 0
    labels: dict[str, list[tuple[float, int]]] = {}
    while queue:
        seconds, _, here, spent, path = heapq.heappop(queue)
        if any(t <= seconds and c <= spent for t, c in labels.get(here, ())):
            continue
        labels[here] = [(t, c) for t, c in labels.get(here, ())
                        if not (seconds <= t and spent <= c)] + [(seconds, spent)]
        if here == end:
            return path
        for edge in edges:
            if (edge.start != here or not edge.verified or edge.mode not in modes
                    or not edge.requires <= known or edge.copper < 0
                    or spent + edge.copper > copper):
                continue
            serial += 1
            heapq.heappush(queue, (seconds + edge.cost.seconds, serial, edge.end,
                                  spent + edge.copper, (*path, edge)))
    return None
