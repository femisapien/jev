import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location('live_soak',Path(__file__).resolve().parents[1]/'tools/live_soak.py')
soak=importlib.util.module_from_spec(spec);spec.loader.exec_module(soak)


def row(xp=0,dead=False):
    return {'state':{'char':{'level':15,'xp_pct':xp,'key':123},
                     'vitals':{'dead':dead},'sense':{'addon_ok':True}}}


def test_soak_detects_death_spirals_without_counting_repeated_dead_frames():
    m=soak.Monitor(0);m.tick(row(),0)
    for at in range(5):
        m.tick(row(dead=True),at+1);m.tick(row(dead=True),at+1);m.tick(row(),at+1)
    assert len(m.deaths)==5 and 'death rate' in m.stop_reason(6)


def test_soak_stops_blind_or_repeating_failures_and_credits_progress():
    m=soak.Monitor(0)
    assert 'observation' in m.stop_reason(301)
    m.tick(row(.1),1790)
    assert m.stop_reason(1800) is None
    for _ in range(20):m.event({'operation':'provisions','phase':'end','code':'no_supplier'})
    assert 'repeated' in m.stop_reason(1800)


def test_reader_leaves_partial_tail_for_the_next_poll(tmp_path):
    path=tmp_path/'ticks.jsonl';path.write_text('{"n":1}\n{"n":')
    reader=soak.Reader(path)
    assert list(reader.rows())==[{'n':1}]
    with path.open('a') as f:f.write('2}\n')
    assert list(reader.rows())==[{'n':2}]


def test_soak_rejects_wrong_character_and_unread_telemetry():
    m=soak.Monitor(0,expected_key=456)
    m.tick(row(),1)
    assert 'character' in m.stop_reason(1)
    m=soak.Monitor(0,expected_key=123)
    unread=row();unread['state']['sense']['addon_ok']=False
    m.tick(unread,300)
    assert 'observation' in m.stop_reason(301)


def test_progress_resets_failure_budget_without_erasing_operation_totals():
    m=soak.Monitor(0);m.tick(row(),0)
    for _ in range(19):
        m.event({'phase':'end','operation':'provisions','step_id':'buy','code':'no_supplier'})
    m.tick(row(.1),1)
    m.event({'phase':'end','operation':'provisions','step_id':'buy','code':'no_supplier'})
    assert m.stop_reason(2) is None
    assert m.operations[('provisions','no_supplier')]==20


def test_client_must_independently_record_the_clean_candidate_and_shadow_mode():
    manifest={'environment':{'code':{'commit':'abc','dirty':False},
                             'settings':{'trip_mode':'shadow'}}}
    assert soak.verify_environment(manifest,'abc') is None
    assert 'revision' in soak.verify_environment(manifest,'def')
    manifest['environment']['code']['dirty']=True
    assert 'revision' in soak.verify_environment(manifest,'abc')
    assert 'revision' in soak.verify_environment({},'abc')
    manifest['environment']['code']['dirty']=False
    manifest['environment']['settings']['trip_mode']='active'
    assert 'shadow' in soak.verify_environment(manifest,'abc')
