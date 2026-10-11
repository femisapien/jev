#!/usr/bin/env python3
"""Run a bounded, supervised candidate soak after explicit operator authorization.

Uses the configured native Windows entrypoint; never starts servers or selects a character.
The normal supervisor owns input, focus, readiness and recovery. This outer monitor stops
on repeated deaths, unchanged failed operations, missing telemetry, or a hard deadline.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
import fcntl
import json
import os
import signal
import socket
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jev.learn.provenance import artifact, code
from jev.persist import atomic_json
from tools.start_teaching import load_config, option


def notify_service(message):
    """Heartbeats go to the independent service manager, not the agent session."""
    address = os.environ.get('NOTIFY_SOCKET')
    if not address:
        return
    if address.startswith('@'):
        address = '\0' + address[1:]
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.sendto(message.encode(), address)


def interrupted(signum, frame):
    raise RuntimeError(f'supervisor received {signal.Signals(signum).name}')


class Reader:
    def __init__(self, path):
        self.path, self.offset = path, 0

    def rows(self):
        if not self.path.exists():
            return
        with self.path.open() as stream:
            stream.seek(self.offset)
            while line := stream.readline():
                if not line.endswith('\n'):
                    break
                row = json.loads(line)
                self.offset = stream.tell()
                yield row


def verify_environment(manifest, commit):
    """The controller's revision alone does not prove which code the client loaded."""
    environment = manifest.get('environment') or {}
    identity = environment.get('code') or {}
    if identity.get('commit') != commit or identity.get('dirty') is not False:
        return 'client did not record the clean expected candidate revision'
    if (environment.get('settings') or {}).get('trip_mode') != 'shadow':
        return 'client did not record shadow trip mode'
    return None


class Monitor:
    def __init__(self, now, expected_key=None):
        self.started = self.last_tick = self.last_progress = now
        self.first = self.latest = None
        self.deaths = deque()
        self.dead = None
        self.operations = Counter()
        self.completed = 0
        self.max_level_xp = None
        self.quest_progress = {}
        self.expected_key = expected_key
        self.identity_error = None
        self.total_deaths = 0
        self.failures = Counter()

    def tick(self, row, now):
        state = row.get('state') or {}
        if not (state.get('sense') or {}).get('addon_ok'):
            return
        char = state.get('char') or {}
        if self.expected_key is not None and char.get('key') != self.expected_key:
            self.identity_error = 'observed character does not match the authorized character'
            return
        self.last_tick = now
        if self.first is None:
            self.first = state
        self.latest = state
        level, xp = char.get('level'), char.get('xp_pct')
        if isinstance(level, int) and isinstance(xp, (int,float)):
            value = (level, xp)
            if self.max_level_xp is None or value > self.max_level_xp:
                self.last_progress, self.max_level_xp = now, value
                self.failures.clear()
        for q in state.get('quests') or ():
            if q.get('quest_id') is None:
                continue
            value = (bool(q.get('complete')), sum(o.get('have',0) for o in q.get('objectives') or ()))
            old = self.quest_progress.get(q['quest_id'])
            if old is not None and value > old:
                self.last_progress = now
                self.failures.clear()
            self.quest_progress[q['quest_id']] = value
        dead = (state.get('vitals') or {}).get('dead')
        if isinstance(dead,bool):
            if dead and self.dead is False:
                self.deaths.append(now)
                self.total_deaths += 1
            self.dead = dead
        while self.deaths and self.deaths[0] < now-3600:
            self.deaths.popleft()

    def event(self, row):
        if row.get('phase') == 'end':
            self.operations[(row.get('operation'),row.get('code'))] += 1
            key = (row.get('operation'), row.get('step_id'), row.get('code'))
            if row.get('code') in {'no_supplier', 'nothing_sold', 'unworkable', 'unsupported'}:
                self.failures[key] += 1

    def stop_reason(self, now):
        if self.identity_error:
            return self.identity_error
        if now-self.last_tick > 300:
            return 'no fresh recorded observation for five minutes'
        if sum(t >= now-900 for t in self.deaths) >= 5 or len(self.deaths) >= 8:
            return 'death rate exceeded the supervised soak limit'
        if now-self.last_progress > 1800:
            return 'no observed XP or quest progress for thirty minutes'
        if any(count >= 20 for count in self.failures.values()):
            return 'repeated unchanged failed operation'
        return None

    def report(self):
        def summary(s):
            if not s: return None
            return {'char':s.get('char'),'vitals':s.get('vitals'), 'bags':s.get('bags'),
                    'guide':s.get('guide')}
        return {'first':summary(self.first), 'latest':summary(self.latest),
                'deaths_last_hour':len(self.deaths),
                'deaths_total':self.total_deaths,
                'operations':{'|'.join(str(v) for v in k):n for k,n in self.operations.items()}}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--hours',type=float,default=6)
    p.add_argument('--windows-python',default='/mnt/c/forever-win/Scripts/python.exe')
    p.add_argument('--lock',type=Path,required=True,help='existing live loop lock')
    p.add_argument('--session-seconds',type=int,default=900)
    p.add_argument('--expected-key',type=lambda v:int(v,16),required=True,
                   help='authorized character key, hexadecimal')
    args=p.parse_args(argv)
    if not 0 < args.hours <= 8 or not 60 <= args.session_seconds <= 900:
        p.error('soak must last at most eight hours with bounded sessions')
    os.chdir(ROOT)
    identity=code()
    if identity.get('dirty') or 'commit' not in identity:
        p.error('commit candidate code before live qualification')
    config_path=ROOT/'var'/'teaching-launch.json'
    config=load_config(config_path)
    trip_mode=option(config['args'],'--trip-mode','shadow')
    if trip_mode != 'shadow':
        p.error('this exploratory soak requires the trip planner in shadow mode')
    config_identity=artifact(config_path)
    area=ROOT/'var'/'live-test';area.mkdir(parents=True,exist_ok=True)
    stop=area/'STOP';control_stop=ROOT/'captures'/'teaching'/'STOP'
    if stop.exists() or control_stop.exists():
        p.error('an existing stop file prevents this test from starting')
    args.lock.parent.mkdir(parents=True,exist_ok=True)
    lock=args.lock.open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    began=time.time();deadline=began+args.hours*3600
    monitor=Monitor(began,args.expected_key);session=0;reason=None;child=None;finished=[]
    status={'pid':os.getpid(),'commit':identity['commit'],'started_at':began,
            'deadline':deadline,'checkout':str(ROOT),'trip_mode':trip_mode,
            'expected_key':f'{args.expected_key:08x}','launch_config':config_identity}
    def publish(state, **extra):
        atomic_json(area/'status.json',{**status,'state':state,'at':time.time(),
                    'session':session,'metrics':monitor.report(),'finished':finished,**extra})
        notify_service('READY=1\nWATCHDOG=1\nSTATUS=' + state)
    def drain(readers):
        if readers:
            now=time.time()
            for row in readers[0].rows():monitor.tick(row,now)
            for row in readers[1].rows():monitor.event(row)
    def stop_child():
        notify_service('STOPPING=1')
        control_stop.parent.mkdir(parents=True,exist_ok=True)
        control_stop.touch()
        if child is not None and child.poll() is None:
            try:
                child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                child.terminate()
                child.wait(timeout=60)
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        while time.time()<deadline and not reason:
            code.cache_clear()
            if code()!=identity:
                reason='candidate code changed during the soak';break
            if artifact(config_path)!=config_identity:
                reason='launch configuration changed during the soak';break
            if stop.exists():reason='operator stop';break
            session+=1
            known=set((ROOT/'runs').glob('*')) if (ROOT/'runs').exists() else set()
            log=ROOT/'captures'/f'live-soak-{int(began)}-{session}.log'
            readers=[];run=None;session_started=time.time();environment_checked=False
            with log.open('w') as output:
                child=subprocess.Popen([args.windows_python,'-u','tools/start_teaching.py','--run',
                       '--dispatch','hybrid','--session-seconds',str(args.session_seconds)],
                       cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT)
                while child.poll() is None:
                    now=time.time()
                    if run is None and (ROOT/'runs').exists():
                        new=[x for x in (ROOT/'runs').iterdir() if x not in known and x.is_dir()]
                        if new:
                            run=max(new,key=lambda x:x.stat().st_mtime)
                            readers=[Reader(run/'ticks.jsonl'),Reader(run/'executions.jsonl')]
                    environment_error=None
                    if run is not None and not environment_checked and (run/'ticks.jsonl').exists():
                        environment_error=verify_environment(
                            json.loads((run/'manifest.json').read_text()),identity['commit'])
                        environment_checked=environment_error is None
                    drain(readers)
                    reason=('operator stop' if stop.exists() or control_stop.exists() else
                            'hard test deadline reached' if now>=deadline else
                            'session exceeded its supervision deadline' if now-session_started>args.session_seconds+180
                            else environment_error or monitor.stop_reason(now))
                    state='playing' if monitor.last_tick>session_started else 'starting'
                    publish(state if reason is None else 'stopping',run=str(run) if run else None,reason=reason)
                    if reason:
                        stop_child()
                        break
                    time.sleep(10)
                rc=child.wait(timeout=60)
                drain(readers)
                finished.append({'session':session,'run':str(run) if run else None,'exit':rc,
                                 'seconds':time.time()-session_started,'log':str(log)})
                if rc and reason is None:reason=f'supervisor exited with code {rc}'
                if reason is None and monitor.last_tick<=session_started:
                    reason='session ended without a verified gameplay observation'
            publish('between sessions',reason=reason)
        publish('stopped',reason=reason or 'test duration completed')
        return 0 if reason in (None,'hard test deadline reached','operator stop') else 1
    except Exception as exc:
        reason=f'monitor failed: {type(exc).__name__}: {exc}'
        publish('stopping',reason=reason)
        raise
    finally:
        if child is not None and child.poll() is None:
            stop_child()
        publish('stopped',reason=reason or 'test duration completed')
        lock.close()


if __name__=='__main__':
    raise SystemExit(main())
