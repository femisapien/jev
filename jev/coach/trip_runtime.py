"""Build trip opportunities from the same graph and observations the scripted guide uses."""
from __future__ import annotations

import json
import math
import time

from jev.coach import policy
from jev.coach.trips import Opportunity, Planner, record
from jev.world.journey import Cost
from jev.world.state_v1 import StepKind


class TripController:
    def __init__(self, mode="shadow", *, planner=None):
        if mode not in ("off", "shadow", "active"):
            raise ValueError("trip mode must be off, shadow, or active")
        self.mode = mode
        self.planner = planner or Planner()
        self.last_at = -math.inf
        self.pending = None

    def choose(self, runtime, state, node):
        if self.mode == "off" or state.t - self.last_at < (30 if self.mode == "shadow" else 5):
            return None
        self.last_at = state.t
        floor = policy.decide(state, node, context=runtime.policy_context)
        if (state.quests is None or state.char.level is None or runtime.finished
                or not state.sense.addon_ok or state.vitals.combat is not False
                or floor.rule.startswith(("preempt.", "fight.", "sense.", "recover."))):
            return None
        here = runtime.trip_position(state) if runtime.trip_position else state.pos.world
        if here is None or runtime.trip_map_id is None:
            return None
        began = time.perf_counter()
        held = {q.quest_id: q for q in state.quests}
        facts = {f"done:{q}" for q in runtime.completed}
        facts |= {f"held:{q}" for q in held}
        facts |= {f"complete:{q}" for q, v in held.items() if v.complete is True}
        ready = state.vitals.hp is not None and state.vitals.hp >= .6
        if ready and (state.bags.durability_min is not None and state.bags.durability_min > .05):
            facts.add("ready")
        options, nodes, service_plans = [], {}, {}
        rewards = {n.quest_id: float(n.xp_est or 0) for n in runtime.graph.nodes
                   if n.kind is StepKind.QUEST_TURNIN}
        objectives_by_quest = {}
        for candidate in runtime.graph.nodes:
            if candidate.kind is StepKind.QUEST_OBJECTIVE:
                objectives_by_quest.setdefault(candidate.quest_id, []).append(candidate.id)
        for candidate in runtime.graph.nodes:
            q = candidate.quest_id
            if (q is None or q in runtime.completed or candidate.id in runtime._retried
                    or candidate.route_blocked_reason or candidate.world is None
                    or candidate.map_id != runtime.trip_map_id
                    or not set(candidate.skills) <= runtime.available_skills
                    or not candidate.level[0] <= state.char.level <= candidate.level[1] + 2
                    or runtime.policy_context.step_waiting(candidate.id, state.t) is not None):
                continue
            kind = candidate.kind
            requires, adds, reward, seconds, slots = (), frozenset(), 0.0, 5.0, 0
            if kind is StepKind.QUEST_ACCEPT and q not in held and len(held) < 20:
                requires = tuple(frozenset(f"done:{p}" for p in group)
                                 for group in candidate.quest_prerequisites) or (frozenset(),)
                adds = frozenset({f"held:{q}"})
            elif kind is StepKind.QUEST_OBJECTIVE and not (q in held and held[q].complete is True):
                requires = (frozenset({f"held:{q}", "ready"}),)
                adds = frozenset({f"worked:{candidate.id}"})
                # Conservative fallback until a measured complete objective cost is available.
                seconds = min(candidate.timeout_s, max(30.0, sum(
                    (o.required_count or 1) * 40 for o in candidate.objective_targets)))
                slots = 1 if any(o.kind == "loot" for o in candidate.objective_targets) else 0
            elif kind is StepKind.QUEST_TURNIN:
                objectives = objectives_by_quest.get(q, [])
                requires = (frozenset({f"complete:{q}"}),)
                if objectives:
                    requires += (frozenset({f"held:{q}", *(f"worked:{k}" for k in objectives)}),)
                adds = frozenset({f"done:{q}"})
                reward = float(candidate.xp_est or 0)
            else:
                continue
            risk = 0.0
            if runtime.values is not None and kind is StepKind.QUEST_OBJECTIVE:
                value = runtime.values.quest(q, state.char.level, state.char.cls)
                if value and value.xp_h > 0 and (value.hours or 0) >= .5:
                    # This estimate already includes the recorded encounter/recovery cycle.
                    seconds = max(seconds, rewards.get(q, 0) / value.xp_h * 3600
                                  / max(1, len(objectives_by_quest.get(q, ()))))
                    if value.deaths_h is not None and math.isfinite(value.deaths_h):
                        risk = 1 - math.exp(-max(0, value.deaths_h) * seconds / 3600)
            option = Opportunity(candidate.id, candidate.world[:2], reward,
                                 Cost(interaction=seconds), requires, adds, slots=slots, risk=risk,
                                 kind=kind.value,
                                 forbids=frozenset({f"done:{q}"}) | (
                                     frozenset({f"held:{q}"}) if kind is StepKind.QUEST_ACCEPT
                                     else frozenset({f"worked:{candidate.id}"})
                                     if kind is StepKind.QUEST_OBJECTIVE else frozenset()),
                                 quest_slots=1 if kind is StepKind.QUEST_ACCEPT else
                                 -1 if kind is StepKind.QUEST_TURNIN else 0,
                                 chain=f"quest:{q}")
            options.append(option)
            nodes[candidate.id] = candidate
        if runtime.trip_services is not None:
            for option, plan in runtime.trip_services(state):
                options.append(option)
                service_plans[option.key] = plan
        total = len(options)
        options = self.planner.select(options, here[:2])
        proposal = self.planner.plan(options, here=here[:2], facts=frozenset(facts),
                                     copper=state.bags.money_copper or 0,
                                     slots=state.bags.free or 0,
                                     travel=runtime.trip_travel, quest_slots=20 - len(held))
        evidence = record(proposal, options, state=state, mode=self.mode,
                          elapsed_ms=(time.perf_counter() - began) * 1000)
        evidence["baseline_step"] = runtime.tracker.step_id
        evidence["available_opportunities"] = total
        evidence["cost_basis"] = "estimated; validate against completed actions before promotion"
        with (runtime.recorder.dir / "trips.jsonl").open("a") as stream:
            stream.write(json.dumps(evidence, default=lambda v: sorted(v)) + "\n")
        if proposal:
            key = proposal.actions[0]
            if self.mode == "active" or key == runtime.tracker.step_id:
                self.pending = {"step_id": key, "at": state.t, "mode": self.mode,
                                "proposed_trip_seconds": proposal.seconds,
                                "proposed_actions": proposal.actions}
        if self.mode != "active" or not proposal:
            return None
        key = proposal.actions[0]
        # Required services keep their existing priority. The challenger can propose a
        # voluntary service only when the ordinary guide is ready to do non-urgent work.
        if floor.rule.startswith("service."):
            return None
        if key in service_plans:
            plan = service_plans[key]
            return plan if runtime._verify(plan.decision, state).ok else None
        selected = nodes.get(key)
        if (selected is None or selected.id == runtime.tracker.step_id
                or not runtime._doable(selected, state.char.level, held,
                                       runtime._lost_quests(state), strict=True)):
            return None
        # Enter one eligible step. No simulated completion is persisted. Ordinary tracker
        # progress and the observed log control the return to the original guide.
        runtime.tracker.enter(selected.id, state, rejoin_to=runtime.tracker.step_id)
        runtime._progress()
        return None

    def finish(self, runtime, state, arm, outcome):
        if self.pending is None or arm is None:
            return
        pending, self.pending = self.pending, None
        matched = pending["step_id"] == arm.step_id or pending["step_id"] == "service:" + arm.decision.skill
        row = {"kind": "trip.first_action_outcome", **pending, "matched": matched,
               "actual_step": arm.step_id, "seconds": max(0, state.t - arm.at),
               "skill_outcome": outcome.value,
               "whole_trip_completed": False,
               "counterfactual_outcomes_observed": False}
        with (runtime.recorder.dir / "trips.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")
