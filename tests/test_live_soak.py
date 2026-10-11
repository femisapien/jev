import importlib.util
import json
import socket
from types import SimpleNamespace
import pytest
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


def test_windows_bridge_is_proved_before_gameplay_and_tries_another_socket(tmp_path, monkeypatch):
    broken=tmp_path/'old_interop';working=tmp_path/'new_interop'
    calls=[];checks=[]
    with socket.socket(socket.AF_UNIX) as a, socket.socket(socket.AF_UNIX) as b:
        a.bind(str(broken));b.bind(str(working))
        monkeypatch.setenv('WSL_INTEROP',str(broken))
        def probe(args, **kw):
            assert args[1]=='-c' and 'JEV_WINDOWS_READY' in args[2]
            calls.append(kw['env'].get('WSL_INTEROP'))
            return SimpleNamespace(returncode=0 if calls[-1]==str(working) else 1,
                                   stdout='JEV_WINDOWS_READY\n' if calls[-1]==str(working) else '',
                                   stderr='accept4 failed 110')
        monkeypatch.setattr(soak.subprocess,'run',probe)
        env=soak.windows_environment('native-python',sockets=tmp_path,check=checks.append)
    assert calls==[str(broken),str(working)]
    assert env['WSL_INTEROP']==str(working)
    assert [c['ok'] for c in checks]==[False,True]
    assert 'accept4' in checks[0]['error']


def test_windows_probe_timeout_does_not_start_or_retry_gameplay(tmp_path, monkeypatch):
    monkeypatch.delenv('WSL_INTEROP',raising=False)
    checks=[]
    def timeout(args, **kw):
        assert '--run' not in args
        raise soak.subprocess.TimeoutExpired(args,kw['timeout'])
    monkeypatch.setattr(soak.subprocess,'run',timeout)
    with pytest.raises(RuntimeError,match='no working Windows'):
        soak.windows_environment('native-python',sockets=tmp_path,check=checks.append)
    assert len(checks)==1 and checks[0]['ok'] is False


def test_native_rotation_preserves_all_recordings_and_failure_budgets(tmp_path):
    from tools.start_teaching import run_sessions
    root=tmp_path/'runs';root.mkdir()
    journal=tmp_path/'sessions.jsonl';monitor=soak.Monitor(0,expected_key=123)
    following=soak.NativeSessions(root,journal,monitor,'abc',tmp_path/'native.log')
    calls=[]
    def event(value):
        with journal.open('a') as f:f.write(json.dumps(value)+'\n')
    def play(args):
        calls.append(1);n=len(calls);run=root/f'run-{n}';run.mkdir()
        (run/'manifest.json').write_text(json.dumps({'environment':{
            'code':{'commit':'abc','dirty':False},'settings':{'trip_mode':'shadow'}}}))
        (run/'ticks.jsonl').write_text('\n'.join(json.dumps(r) for r in
            [row(.1*n),row(.1*n,dead=True)])+'\n')
        (run/'executions.jsonl').write_text(json.dumps({'phase':'end','operation':'fight','code':'killed'})+'\n')
        return 0 if n==1 else 7
    assert run_sessions(['--runs-dir',str(root)],sessions=0,run=play,is_done=lambda _:False,
                        events=event)==7
    assert len(calls)==2, 'a native failure must end collection'
    assert 'code 7' in following.poll(100)
    assert len(following.finished())==2
    assert len({r['native_pid'] for r in following.finished()})==1
    assert monitor.total_deaths==2 and monitor.operations[('fight','killed')]==2
    following.poll(101)
    assert monitor.total_deaths==2 and monitor.operations[('fight','killed')]==2


@pytest.mark.parametrize('fault',['wrong_commit','no_observation','exception'])
def test_native_handover_rejects_unverified_or_failed_sessions(tmp_path,fault):
    from tools.start_teaching import run_sessions
    root=tmp_path/'runs';root.mkdir();journal=tmp_path/'sessions.jsonl'
    following=soak.NativeSessions(root,journal,soak.Monitor(0),'abc',tmp_path/'native.log')
    def event(value):
        with journal.open('a') as f:f.write(json.dumps(value)+'\n')
    def play(args):
        run=root/'new';run.mkdir()
        if fault=='exception':raise RuntimeError('fixture')
        (run/'manifest.json').write_text(json.dumps({'environment':{
            'code':{'commit':'wrong' if fault=='wrong_commit' else 'abc','dirty':False},
            'settings':{'trip_mode':'shadow'}}}))
        (run/'ticks.jsonl').write_text(json.dumps(row(.1))+'\n' if fault=='wrong_commit' else '')
        return 0
    if fault=='exception':
        with pytest.raises(RuntimeError,match='fixture'):
            run_sessions(['--runs-dir',str(root)],sessions=1,run=play,is_done=lambda _:False,events=event)
    else:
        run_sessions(['--runs-dir',str(root)],sessions=1,run=play,is_done=lambda _:False,events=event)
    assert following.poll(1) is not None
    assert following.monitor.first is None


def test_polling_follows_a_live_handover_without_recounting_previous_run(tmp_path):
    root=tmp_path/'runs';root.mkdir();journal=tmp_path/'sessions.jsonl'
    monitor=soak.Monitor(0,expected_key=123)
    following=soak.NativeSessions(root,journal,monitor,'abc',tmp_path/'native.log')
    def event(value):
        with journal.open('a') as f:f.write(json.dumps(value)+'\n')
    def recording(name,xp):
        run=root/name;run.mkdir()
        (run/'manifest.json').write_text(json.dumps({'environment':{
            'code':{'commit':'abc','dirty':False},'settings':{'trip_mode':'shadow'}}}))
        (run/'ticks.jsonl').write_text(json.dumps(row(xp))+'\n')
        (run/'executions.jsonl').write_text(json.dumps({'phase':'end','operation':'fight','code':'killed'})+'\n')
    event({'event':'started','session':1,'at':1,'pid':42})
    assert following.poll(2) is None
    assert following.active.get('observed') is None
    recording('one',.1)
    assert following.poll(3) is None
    assert following.active['observed']
    event({'event':'finished','session':1,'at':4,'exit':0,'seconds':3,'runs':['one']})
    event({'event':'started','session':2,'at':4,'pid':42})
    assert following.poll(5) is None
    assert following.active['session']==2 and not following.active.get('observed')
    assert following.finished()[0]['exit']==0
    recording('two',.2)
    assert following.poll(6) is None
    assert following.active['observed'] and monitor.latest['char']['xp_pct']==.2
    assert monitor.operations[('fight','killed')]==2
