import importlib.util
import json
from pathlib import Path

import pytest

from jev.learn.provenance import artifact

spec=importlib.util.spec_from_file_location('release_gate', Path(__file__).resolve().parents[1]/'tools/release_gate.py')
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def evidence(tmp_path):
    serial=[0]
    def write(value, name=None):
        serial[0]+=1
        p=tmp_path/(name or f'{serial[0]}.json')
        p.write_text(json.dumps(value))
        return artifact(p)
    commit='a'*40
    xml=tmp_path/'suite.xml'
    xml.write_text('<testsuite tests="1" errors="0" failures="0"/>')
    contract=write({'candidate':commit,'control':'b'*40,'target':{'kind':'correctness'}})
    hive=write({'protocol':2,'status':'noninferior','window':[1,999],'trial_manifest':contract['path'],
                'trial_manifest_sha256':contract['sha256']})
    record={'format':1,'commit':commit,'created_at':1000,
            'suites':[{**artifact(xml),'commit':commit,'dirty':False,'created_at':1000}],
            'hive_verdict':hive, 'client_pairs':[]}
    for scenario in sorted(gate.SCENARIOS):
        samples=[]
        for unit in range(8):
            sample={'unit':unit}
            for arm, code in [('candidate',commit),('control','b'*40)]:
                manifest=write({'run_id':f'{arm}-{unit}', 'started_at':1000, 'environment':{'tier':'live-client','code':{'commit':code,'dirty':False}}})
                trace=write({'operation':'scenario', 'result':'verified'}, name=None)
                episode=write({'manifest_sha256':manifest['sha256'],'scenario':scenario,'unit':unit,
                               'trace':trace,'started_at':0.,'ended_at':100.,'deaths':0,
                               'success':True,'conditions':{k:'matched' for k in gate.MATCH}})
                sample[arm]={'manifest':manifest,'episode':episode,'seconds':100.,'deaths':0,'success':True}
            samples.append(sample)
        record['client_pairs'].append({'scenario':scenario,'result':write({'samples':samples})})
    return record, commit, write


def test_exact_clean_candidate_can_qualify_only_with_all_matched_scenarios(tmp_path):
    record, commit, _=evidence(tmp_path)
    assert gate.check(record,commit,now=1000)['qualified']
    with pytest.raises(ValueError,match='exact commit'): gate.check(record,'c'*40,now=1000)
    record['client_pairs'].pop()
    with pytest.raises(ValueError,match='missing matched'): gate.check(record,commit,now=1000)


@pytest.mark.parametrize('defect',['tamper','wrong-code','unmatched','incomplete','slower','reused-unit','no-trace'])
def test_client_evidence_cannot_qualify_through_self_declared_status(tmp_path,defect):
    record, commit, write=evidence(tmp_path)
    pair=record['client_pairs'][0]
    result=json.loads(Path(pair['result']['path']).read_text())
    result.update(status='improved',completed=True)  # this claim is never trusted
    sample=result['samples'][0]
    measured=sample['candidate']
    if defect=='tamper':
        Path(measured['manifest']['path']).write_text('{}')
    elif defect=='wrong-code':
        measured['manifest']=write({'environment':{'tier':'live-client','code':{'commit':'x','dirty':False}}})
    elif defect=='reused-unit':
        result['samples'][1]['unit']=sample['unit']
    else:
        episode=json.loads(Path(measured['episode']['path']).read_text())
        if defect=='unmatched': episode['conditions']['gear']='different'
        if defect=='incomplete': episode['success']=False
        if defect=='slower': episode['ended_at']=10000.; measured['seconds']=10000.
        if defect=='no-trace': Path(episode['trace']['path']).unlink()
        measured['episode']=write(episode)
    pair['result']=write(result)
    with pytest.raises((ValueError,OSError)): gate.check(record,commit,now=1000)


def test_inconclusive_hive_and_dirty_suites_never_authorize_release(tmp_path):
    record,commit,write=evidence(tmp_path)
    record['suites'][0]['dirty']=True
    with pytest.raises(ValueError,match='clean candidate'): gate.check(record,commit,now=1000)
    record['suites'][0]['dirty']=False
    record['hive_verdict']=write({'protocol':2,'status':'inconclusive'})
    with pytest.raises(ValueError,match='qualified protocol'): gate.check(record,commit,now=1000)
