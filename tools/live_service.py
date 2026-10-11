"""Install/start the authorized mage test as a durable user service; record abrupt exits."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from jev.persist import atomic_json

UNIT = 'jev-mage-soak.service'


def finalize(path, *, result, exit_code, exit_status):
    """ExecStopPost runs even when SIGKILL prevents the monitor's finally block."""
    path = Path(path)
    if not path.exists():
        return
    status = json.loads(path.read_text())
    status['service_exit'] = {'result': result, 'code': exit_code,
                              'status': exit_status, 'at': time.time()}
    if status.get('state') != 'stopped':
        status['last_heartbeat_at'] = status.get('at')
        status.update(state='stopped', at=time.time(),
                      reason=f'supervisor service exited: {result} ({exit_code}/{exit_status})')
    # A native Windows child may outlive the Linux launcher. Its stop file is independent
    # of Unix signals and is checked by the runtime before further actions.
    stop = path.parents[2] / 'captures' / 'teaching' / 'STOP'
    stop.parent.mkdir(parents=True, exist_ok=True)
    stop.touch()
    atomic_json(path, status)


def quote(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%') + '"'


def unit_text(root, python, lock, key, hours):
    args = [python, root / 'tools/live_soak.py', '--lock', lock,
            '--expected-key', key, '--hours', str(hours)]
    final = [python, root / 'tools/live_service.py', 'finalize']
    return '\n'.join([
        '[Unit]', 'Description=Supervised Jev mage test', '', '[Service]',
        'Type=notify', 'NotifyAccess=main', f'WorkingDirectory={quote(root)}',
        'ExecStart=/usr/bin/env -u WSL_INTEROP ' + ' '.join(map(quote, args)),
        'ExecStopPost=' + ' '.join(map(quote, final)),
        'TimeoutStartSec=120', 'TimeoutStopSec=250', 'WatchdogSec=90',
        f'RuntimeMaxSec={int(hours * 3600) + 300}',
        'KillMode=control-group', 'Restart=no',
        'StandardOutput=journal', 'StandardError=journal', '',
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['start', 'status', 'finalize'])
    parser.add_argument('--hours', type=float, default=6)
    parser.add_argument('--expected-key', default='73ce06a8')
    parser.add_argument('--lock', type=Path, default=Path('/home/ash/ForeverV2/var/loop/lock'))
    args = parser.parse_args()
    status_path = ROOT / 'var/live-test/status.json'
    if args.command == 'finalize':
        finalize(status_path, result=os.environ.get('SERVICE_RESULT', 'unknown'),
                 exit_code=os.environ.get('EXIT_CODE', 'unknown'),
                 exit_status=os.environ.get('EXIT_STATUS', 'unknown'))
        return 0
    if args.command == 'status':
        subprocess.run(['systemctl', '--user', 'status', UNIT, '--no-pager'], check=False)
        if status_path.exists():
            print(status_path.read_text())
        return 0
    if not 0 < args.hours <= 8:
        parser.error('test must last at most eight hours')
    int(args.expected_key, 16)
    active = subprocess.run(['systemctl', '--user', 'is-active', '--quiet', UNIT]).returncode == 0
    if active:
        parser.error('mage test service is already active')
    for stop in (ROOT / 'var/live-test/STOP', ROOT / 'captures/teaching/STOP'):
        if stop.exists():
            parser.error(f'existing stop file must be reviewed before a new test: {stop}')
    if status_path.exists():
        archive = status_path.with_name(f'status-before-service-{time.time_ns()}.json')
        archive.write_bytes(status_path.read_bytes())
    folder = Path.home() / '.config/systemd/user'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / UNIT).write_text(unit_text(ROOT, Path(sys.executable), args.lock,
                                       args.expected_key, args.hours))
    atomic_json(status_path, {'state': 'starting', 'at': time.time(),
                             'expected_key': args.expected_key, 'reason': None,
                             'requested_hours': args.hours, 'service': UNIT})
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'reset-failed', UNIT], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['systemctl', '--user', 'start', '--no-block', UNIT], check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
