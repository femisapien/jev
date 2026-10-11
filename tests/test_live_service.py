import importlib.util
import json
from pathlib import Path
import socket

spec = importlib.util.spec_from_file_location('live_service', Path(__file__).resolve().parents[1] / 'tools/live_service.py')
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)


def test_abrupt_service_exit_cannot_leave_playing_status_or_an_unstopped_child(tmp_path):
    path = tmp_path / 'var/live-test/status.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'state': 'playing', 'at': 20, 'metrics': {'kills': 3}}))
    service.finalize(path, result='watchdog', exit_code='killed', exit_status='ABRT')
    got = json.loads(path.read_text())
    assert got['state'] == 'stopped' and got['last_heartbeat_at'] == 20
    assert got['metrics'] == {'kills': 3}
    assert 'watchdog' in got['reason']
    assert (tmp_path / 'captures/teaching/STOP').exists()


def test_service_finalizer_preserves_an_intentional_stop_reason(tmp_path):
    path = tmp_path / 'var/live-test/status.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'state': 'stopped', 'reason': 'operator stop'}))
    service.finalize(path, result='success', exit_code='exited', exit_status='0')
    assert json.loads(path.read_text())['reason'] == 'operator stop'


def test_monitor_heartbeat_reaches_independent_service_manager(tmp_path, monkeypatch):
    from tools.live_soak import notify_service
    path = str(tmp_path / 'notify.sock')
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
        sock.bind(path)
        sock.settimeout(1)
        monkeypatch.setenv('NOTIFY_SOCKET', path)
        notify_service('WATCHDOG=1')
        assert sock.recv(100) == b'WATCHDOG=1'
