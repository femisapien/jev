import json

import pytest
from test_runtime_records import graph, seen

from jev.clients.source import ScriptedSource
from jev.coach.trips import Opportunity, Planner
from jev.learn.episode import Recorder
from jev.learn.provenance import artifact, manifest
from jev.orch.runtime import ClientRuntime
from jev.world.journey import Cost, Edge, route
from jev.world.state_v1 import Bags, Char, Quest, Vitals


def test_trip_bundles_a_prerequisite_and_two_rewards_at_one_hub():
    options = [Opportunity("accept", (0, 0), 0, Cost(interaction=5),
                           adds=frozenset({"held"})),
               Opportunity("work", (70, 0), 100, Cost(interaction=10),
                           requires=(frozenset({"held"}),), adds=frozenset({"worked"})),
               Opportunity("handin", (0, 0), 1000, Cost(interaction=5),
                           requires=(frozenset({"worked"}),)),
               Opportunity("bad", (700, 0), 10, Cost(interaction=90))]
    trip = Planner().plan(options, here=(0, 0))
    assert trip.actions == ("accept", "work", "handin")
    assert trip.seconds == 40 and trip.reward == 1100


def test_trip_rejects_resource_death_and_unreachable_shortcuts():
    good = Opportunity("good", (0, 0), 10, Cost(interaction=10))
    options = [good, Opportunity("costly", (0, 0), 1000, Cost(), copper=100),
               Opportunity("deadly", (0, 0), 1000, Cost(), risk=.9),
               Opportunity("full", (0, 0), 1000, Cost(), slots=1),
               Opportunity("logfull", (0, 0), 1000, Cost(), quest_slots=1)]
    assert Planner().plan(options, here=(0, 0), quest_slots=0).actions == ("good",)
    assert Planner().plan([good], here=(0, 0), travel=lambda a,b: None) is None


def test_hub_service_can_unlock_a_loot_trip_but_done_rewards_cannot_repeat():
    options = [Opportunity("sell", (0, 0), 0, Cost(interaction=5), slots=-2),
               Opportunity("loot", (7, 0), 100, Cost(interaction=5), slots=1,
                           adds=frozenset({"done"}), forbids=frozenset({"done"})),
               Opportunity("duplicate", (7, 0), 100, Cost(interaction=5), slots=1,
                           adds=frozenset({"done"}), forbids=frozenset({"done"}))]
    result = Planner().plan(options, here=(0,0), slots=0)
    assert result.actions[0] == "sell" and result.reward == 100


def test_journey_includes_access_wait_price_and_recovery():
    edges = (Edge("a", "z", "walk", Cost(travel=100), verified=True),
             Edge("a", "b", "walk", Cost(travel=10), verified=True),
             Edge("b", "z", "flight", Cost(travel=15, wait=10,
                  failure_probability=.2, failure_recovery=100), copper=50,
                  requires=frozenset({"discovered"}), verified=True),
             Edge("a", "z", "boat", Cost(travel=1), verified=False))
    kw = dict(known=frozenset({"discovered"}), modes=frozenset({"walk", "flight", "boat"}))
    assert len(route(edges,"a","z",copper=50,**kw)) == 2
    assert len(route(edges,"a","z",copper=49,**kw)) == 1
    assert sum(e.cost.seconds for e in route(edges,"a","z",copper=50,**kw)) == 55
    with pytest.raises(ValueError): Cost(travel=float("nan"))


def test_run_environment_is_immutable_and_hashes_artifact_content(tmp_path):
    source = tmp_path / "catalog.json"
    source.write_text('{"a":1}')
    rec = Recorder(tmp_path / "runs")
    evidence = manifest(tier="offline-replay", graph=graph(), artifacts=[source])
    rec.environment(evidence)
    rec.environment(evidence)
    source.write_text('{"a":2}')
    assert artifact(source)["sha256"] != evidence["artifacts"][0]["sha256"]
    with pytest.raises(ValueError): rec.environment({"tier":"different"})
    assert json.loads((rec.dir/"manifest.json").read_text())["environment"] == evidence


@pytest.mark.parametrize("mode", ["shadow", "active"])
def test_runtime_records_proposals_without_inventing_completion_or_overriding_combat(tmp_path, mode):
    g = graph()
    g = g.model_copy(update={"nodes":tuple(n.model_copy(update={"map_id":0,
                                "world":(0.,0.,0.), "xp_est":500}) for n in g.nodes)})
    state = seen(100, char=Char(level=5), quests=(Quest(quest_id=1, complete=True),),
                 bags=Bags(free=10, money_copper=100, durability_min=1))
    rt = ClientRuntime("c", g, ScriptedSource([state]), Recorder(tmp_path),
                       trip_mode=mode, trip_map_id=0, trip_position=lambda s:(0,0))
    rt.tick()
    assert not rt.completed
    proposal = json.loads((rt.recorder.dir/"trips.jsonl").read_text().splitlines()[0])
    assert proposal["proposal"]["actions"] == ["turnin"]
    rt.finish(__import__('jev.learn.episode',fromlist=['SkillOutcome']).SkillOutcome.ABORTED)
    rt.tick(state=state.model_copy(update={"t":110,"vitals":Vitals(combat=True,hp=.1)}))
    assert rt.armed.rule.startswith(("preempt.","fight."))
