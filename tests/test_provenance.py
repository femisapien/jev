import subprocess

import pytest

from jev.learn.provenance import _git_command, _windows_gitdir, code


@pytest.mark.parametrize('server', ['wsl.localhost', 'WSL$'])
def test_windows_wsl_worktree_uses_owning_distro_git_without_a_shell(server):
    root = rf'\\{server}\Ubuntu-24.04\home\ash\candidate with spaces'
    assert _git_command(root, windows=True) == [
        'wsl.exe', '--distribution', 'Ubuntu-24.04', '--exec', 'git', '-C',
        '/home/ash/candidate with spaces']


def test_native_checkouts_use_native_git():
    for root, windows in [('/home/ash/repo', False), (r'C:\repo', True),
                          (r'\\fileserver\share\repo', True)]:
        assert _git_command(root, windows=windows) == ['git', '-C', root]


def test_native_git_resolves_linux_worktree_pointer_inside_its_own_unc_share():
    root = r'\\wsl.localhost\Ubuntu-24.04\home\ash\candidate'
    assert _windows_gitdir(root, 'gitdir: /home/ash/main/.git/worktrees/candidate\n') == (
        r'\\wsl.localhost\Ubuntu-24.04\home\ash\main\.git\worktrees\candidate')
    assert _windows_gitdir(root, 'gitdir: .git-internal\n') == root + r'\.git-internal'
    with pytest.raises(ValueError):
        _windows_gitdir(root, 'not a worktree pointer')


def test_git_receives_closed_pipe_instead_of_inheriting_detached_console_stdin(monkeypatch,tmp_path):
    from jev.learn import provenance
    calls=[]
    def check(command,**kwargs):
        calls.append(kwargs)
        return b'abc\n' if command[-2:]==['rev-parse','HEAD'] else b''
    monkeypatch.setattr(provenance.subprocess,'check_output',check)
    code.cache_clear()
    assert code(tmp_path)['commit']=='abc'
    assert all(call['input']==b'' for call in calls)


def test_identity_detects_tracked_and_untracked_source_changes(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args])
    git('init', '-q')
    source = tmp_path / 'tools' / 'run.py'
    source.parent.mkdir()
    source.write_text('print(1)\n')
    git('add', '.')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
        'commit', '-qm', 'initial')
    clean = code(tmp_path)
    assert not clean['dirty'] and clean['commit'] == git('rev-parse', 'HEAD').decode().strip()
    source.write_text('print(2)\n')
    code.cache_clear()
    dirty = code(tmp_path)
    assert dirty['dirty'] and dirty['tracked_diff_sha256'] != clean['tracked_diff_sha256']
    source.write_text('print(1)\n')
    (source.parent / 'extra.py').write_text('print(3)\n')
    code.cache_clear()
    assert code(tmp_path)['dirty']
