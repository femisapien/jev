"""Bounded trip planning over observed facts and existing executable skills.

The planner proposes sequences, never marks a quest complete. Only the first action can
be executed, after a fresh eligibility check; the tracker remains the completion authority.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from jev.world.journey import Cost


@dataclass(frozen=True)
class Opportunity:
    key: str
    position: tuple[float, float]
    reward: float
    cost: Cost
    requires: tuple[frozenset[str], ...] = (frozenset(),)
    adds: frozenset[str] = frozenset()
    removes: frozenset[str] = frozenset()
    copper: int = 0
    slots: int = 0                         # positive consumes; negative frees
    risk: float = 0.0
    kind: str = "quest"
    forbids: frozenset[str] = frozenset()
    quest_slots: int = 0
    chain: str | None = None

    def feasible(self, facts: frozenset[str], copper: int, slots: int) -> bool:
        return (any(group <= facts for group in self.requires)
                and not self.forbids & facts
                and 0 <= self.copper <= copper and self.slots <= slots
                and 0 <= self.risk <= 1 and self.reward >= 0
                and all(math.isfinite(v) for v in (*self.position, self.reward, self.risk)))


@dataclass(frozen=True)
class Trip:
    actions: tuple[str, ...]
    seconds: float
    reward: float
    survival: float

    @property
    def rate(self) -> float:
        return self.reward * self.survival / max(1.0, self.seconds)


class Planner:
    def __init__(self, *, depth: int = 4, beam: int = 16, candidates: int = 24,
                 horizon_s: float = 900, max_risk: float = .15):
        if not 1 <= depth <= 8 or not 1 <= beam <= 64 or not 1 <= candidates <= 64:
            raise ValueError("planner search exceeds its bounded budget")
        if not math.isfinite(horizon_s) or horizon_s <= 0 or not 0 <= max_risk <= 1:
            raise ValueError("planner horizon and risk must be finite and bounded")
        self.depth, self.beam, self.candidates = depth, beam, candidates
        self.horizon_s, self.max_risk = horizon_s, max_risk

    def plan(self, opportunities, *, here, facts=frozenset(), copper=0, slots=0,
             travel=None, quest_slots=20) -> Trip | None:
        travel = travel or (lambda a, b: Cost(travel=math.dist(a, b) / 7))
        choices = self.select(opportunities, here)
        # path, seconds, reward, survival, position, facts, money, slots
        frontier = [((), 0.0, 0.0, 1.0, here, facts, copper, slots, quest_slots)]
        best = None
        for _ in range(self.depth):
            expanded = []
            for path, seconds, reward, survival, at, known, money, free, log_free in frontier:
                for option in choices:
                    if (option.key in path or not option.feasible(known, money, free)
                            or option.quest_slots > log_free):
                        continue
                    leg = travel(at, option.position)
                    if leg is None:
                        continue
                    elapsed = seconds + leg.seconds + option.cost.seconds
                    alive = survival * (1 - option.risk)
                    if elapsed > self.horizon_s or 1 - alive > self.max_risk:
                        continue
                    new = ((*path, option.key), elapsed, reward + option.reward, alive,
                           option.position, (known - option.removes) | option.adds,
                           money - option.copper, free - option.slots,
                           log_free - option.quest_slots)
                    expanded.append(new)
                    trip = Trip(*new[:4])
                    if trip.reward > 0 and (best is None or trip.rate > best.rate):
                        best = trip
            # Zero-reward prerequisite actions retain a place, ordered by travel cost.
            frontier = sorted(expanded, key=lambda r: (-r[2] * r[3] / max(1, r[1]),
                                                       r[1], r[0]))[:self.beam]
            if not frontier:
                break
        return best

    def select(self, opportunities, here):
        """Keep complete quest chains within the bound, including a distant hand-in."""
        groups = {}
        for option in opportunities:
            groups.setdefault(option.chain or option.key, []).append(option)
        ranked = sorted(groups.values(), key=lambda group: (
            min(math.dist(here, o.position) for o in group), group[0].key))
        selected = []
        for group in ranked:
            if len(selected) + len(group) <= self.candidates:
                selected.extend(group)
        return selected


def record(proposal: Trip | None, opportunities, *, state, mode: str, elapsed_ms: float) -> dict:
    return {"kind": "trip.proposal", "at": state.t, "mode": mode,
            "proposal": asdict(proposal) if proposal else None,
            "alternatives": [asdict(o) for o in opportunities], "runtime_ms": elapsed_ms,
            "selection": "deterministic bounded search", "selection_probability": 1.0,
            "counterfactual_outcomes_observed": False}
