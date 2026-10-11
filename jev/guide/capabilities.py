"""Rank verified executor work by all quest chains it would unlock.

This is an offline capacity estimate. It changes no route or quest completion state.
"""
from collections import defaultdict

from jev.guide.route import _gap
from jev.world.state_v1 import StepKind

KINDS = frozenset({"kill", "loot", "delivery", "explore", "event"})


def unlock_priorities(graph, available_skills):
    quests = {}
    for node in graph.nodes:
        if node.quest_id is not None:
            quests.setdefault(node.quest_id, []).append(node)
    gaps = {q: {reason for n in nodes if (reason := _gap(n, available_skills, KINDS))}
            for q, nodes in quests.items()}
    def reachable(fixed=None):
        got = set()
        for q, nodes in quests.items():
            if gaps[q] - ({fixed} if fixed else set()):
                continue
            requires = nodes[0].quest_prerequisites
            if not requires or any(set(group) <= got for group in requires):
                got.add(q)
        return got
    baseline = reachable()
    result = []
    for reason in sorted(set().union(*gaps.values()) if gaps else set()):
        unlocked = reachable(reason) - baseline
        result.append({"capability": reason, "quests": sorted(unlocked),
                       "placements": sum(len(quests[q]) for q in unlocked),
                       "estimated_quest_xp": sum(n.xp_est or 0 for q in unlocked for n in quests[q]
                                                  if n.kind is StepKind.QUEST_TURNIN)})
    return sorted(result, key=lambda r: (-r["estimated_quest_xp"], -len(r["quests"]), r["capability"]))
