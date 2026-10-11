import json
from types import SimpleNamespace

import pytest

from jev.coach.trips import Opportunity, Planner
from jev.guide.capabilities import unlock_priorities
from jev.guide.graph import Graph, InteractionSpec, Node, ObjectiveTarget
from jev.guide.objectives import select_objective
from jev.guide.route import _gap
from jev.learn.choices import ChoiceMemory, ScopedChoices
from jev.learn.comparison import compare
from jev.learn.cycles import cycles
from jev.learn.episode import SkillOutcome
from jev.run.body import LiveBody
from jev.world.journey import Cost
from jev.world.state_v1 import Quest, StepKind


def dialogue():
    return ObjectiveTarget(kind='interact', target_kind='creature', target_name='Witness',
                           world=(0,0,0), pos=(.5,.5), map_id=0,
                           interaction=InteractionSpec(gossip_lines=('Tell me what happened.',),
                               evidence_sha256='a'*64, client_build='tbc-2.4.3-8606'))


def test_dialogue_requires_explicit_recorded_contract_and_positive_completion():
    from jev.clients.choose import Chose
    from jev.clients.interact import Result as Interacted
    target=dialogue()
    node=Node(id='q', kind=StepKind.QUEST_OBJECTIVE, zone='zone', zone_id=1,
              quest_id=1, world=(0,0,0), pos=(.5,.5), map_id=0, objective_targets=(target,))
    assert _gap(node, frozenset(), frozenset()) is None
    assert select_objective(node, (Quest(quest_id=1,complete=False),)).target == target
    assert select_objective(node, None).target is None
    bare=node.model_copy(update={'objective_targets':(target.model_copy(update={'interaction':None}),)})
    assert 'no verified executor' in _gap(bare, frozenset(), frozenset())
    mixed=node.model_copy(update={'objective_targets':(target,target)})
    assert 'recorded counter identity' in _gap(mixed, frozenset(), frozenset())
    body=object.__new__(LiveBody)
    body.client=SimpleNamespace(bounds=SimpleNamespace(map_id=0))
    body._open_on=lambda *args: Interacted.GOSSIP
    body.checkpoint=lambda:None
    body.chooser=SimpleNamespace(run=lambda line:Chose.CHOSE, detail='')
    assert body._dialogue_objective(target,lambda:False).outcome is SkillOutcome.ABORTED
    assert body._dialogue_objective(target,lambda:True).outcome is SkillOutcome.SUCCEEDED


def test_context_learning_ages_without_subtracting_other_processes_records():
    now=[100.]
    base=ChoiceMemory(clock=lambda:now[0])
    a=ScopedChoices(base,'mage-low',half_life_s=100)
    b=ScopedChoices(base,'mage-newgear',half_life_s=100)
    a.record('heal','early',True,10)
    assert b.arms('heal') == {}
    now[0]=200
    assert a.arms('heal')['early'].tries == .5
    assert a.arms('heal')['early'].tries == .5
    assert base.arms(a._point('heal'))['early'].tries == 1
    a.record('heal','early',False,20)
    assert base.arms(a._point('heal'))['early'].tries == 2


def test_search_budget_keeps_distant_handin_in_a_selected_chain():
    options=[Opportunity('work',(1,0),0,Cost(),chain='q'),
             Opportunity('handin',(1000,0),100,Cost(),chain='q')]
    options += [Opportunity(str(i),(2+i,0),0,Cost()) for i in range(20)]
    selected=Planner(candidates=3).select(options,(0,0))
    assert {'work','handin'} <= {o.key for o in selected} and len(selected) == 3
    with pytest.raises(ValueError): Planner(horizon_s=float('nan'))


def test_unlock_priority_counts_descendants_without_mutating_routes():
    nodes=[]
    for q, prereq in ((1,()),(2,((1,),)),(3,((2,),))):
        nodes.append(Node(id=str(q), kind=StepKind.QUEST_TURNIN, zone='z',zone_id=1,
                          quest_id=q, quest_prerequisites=prereq, world=(0,0,0),pos=(.5,.5),
                          map_id=0, target_kind='creature',target_name='NPC',xp_est=100,
                          route_blocked_reason='dialogue contract missing' if q==1 else None))
    graph=Graph(graph_id='g',faction='alliance',entry='1',nodes=tuple(nodes))
    before=graph.model_dump_json()
    row=unlock_priorities(graph, frozenset())[0]
    assert row['quests']==[1,2,3] and row['estimated_quest_xp']==300
    assert graph.model_dump_json()==before


def test_entire_encounter_cycle_includes_rest_and_censors_last_fight():
    events=[dict(t=t,operation=op,phase=phase,code=code) for t,op,phase,code in
            [(0,'fight','begin',None),(10,'fight','end','killed'),(10,'rest','begin',None),
             (40,'rest','end','healthy'),(50,'fight','begin',None),(65,'fight','end','died')]]
    rows=cycles(events)
    assert rows[0]['seconds']==50 and rows[0]['components']['rest']==30
    assert rows[1]['censored'] and rows[1]['deaths']==1


def test_episode_comparison_cannot_pass_small_repeated_or_failed_samples():
    samples=[{'unit':i, 'candidate':{'success':True,'seconds':80.,'deaths':0},
              'control':{'success':True,'seconds':100.,'deaths':0}} for i in range(8)]
    assert compare(samples)['status']=='improved'
    assert compare(samples[:2])['status']=='inconclusive'
    with pytest.raises(ValueError): compare(samples+[samples[0]])
    samples[0]['candidate']['success']=False
    assert compare(samples)['status']=='harmful'
