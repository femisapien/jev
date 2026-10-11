"""Content identities for replay and release evidence. Never reads credential files."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_VERSION = 1


def _git_command(root: str | Path, *, windows: bool) -> list[str]:
    """Use the owning distro's Git for a WSL checkout, including linked worktrees."""
    path = PureWindowsPath(root)
    share = path.drive.split('\\')
    if windows and len(share) == 4 and share[2].lower() in {'wsl$', 'wsl.localhost'}:
        linux_path = '/' + '/'.join(path.parts[1:])
        return ['wsl.exe', '--distribution', share[3], '--exec', 'git', '-C', linux_path]
    return ['git', '-C', str(root)]


def _windows_gitdir(root, gitfile):
    """Translate a linked worktree's Linux gitdir into its owning UNC share."""
    path = PureWindowsPath(root)
    if not gitfile.startswith('gitdir: '):
        raise ValueError('invalid worktree Git directory pointer')
    target = gitfile[len('gitdir: '):].strip()
    if target.startswith('/'):
        return str(PureWindowsPath(path.anchor, *target.strip('/').split('/')))
    return str(path / PureWindowsPath(target))


def _native_wsl_git(root):
    """Read WSL files with native Git when available, without another interop hop.

    Windows cannot observe Unix executable bits through this share. Content and
    untracked-source checks still run; the result explicitly reports that limitation.
    """
    share = PureWindowsPath(root).drive.split('\\')
    if len(share) != 4 or share[2].lower() not in {'wsl$', 'wsl.localhost'}:
        return None
    executable = shutil.which('git')
    if executable is None:
        candidate = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Git/cmd/git.exe'
        if candidate.is_file():
            executable = str(candidate)
    if executable is None:
        return None
    pointer = root / '.git'
    gitdir = _windows_gitdir(root, pointer.read_text()) if pointer.is_file() else str(pointer)
    return [executable, '-c', 'core.autocrlf=false', '-c', 'core.filemode=false',
            '--git-dir', gitdir, '--work-tree', str(root)]


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     default=str).encode()).hexdigest()


@lru_cache(maxsize=256)
def _hash(path: str, size: int, mtime_ns: int) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def artifact(path: str | Path) -> dict:
    p = Path(path).resolve()
    try:
        st = p.stat()
        return {"path": str(p), "bytes": st.st_size,
                "sha256": _hash(str(p), st.st_size, st.st_mtime_ns)}
    except OSError:
        return {"path": str(p), "missing": True}


@lru_cache(maxsize=8)
def code(root: str | Path = ROOT) -> dict:
    """Pin the checkout at process startup, including tracked local edits."""
    root = Path(root).resolve()
    try:
        native = _native_wsl_git(root) if sys.platform == 'win32' else None
        command = native or _git_command(root, windows=sys.platform == 'win32')
        def git(*args):
            return subprocess.check_output(
                [*command, *args],
                input=b'', stderr=subprocess.DEVNULL, timeout=10,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        patch = git("diff", "--no-ext-diff", "--no-textconv", "HEAD", "--", ".")
        extra = git("ls-files", "--others", "--exclude-standard", "--",
                    "jev/*.py", "hive/*.py", "tools/*.py", "addons/*.lua").decode().splitlines()
        untracked = {name: artifact(root / name).get("sha256") for name in extra}
        return {"root": str(root), "commit": git("rev-parse", "HEAD").decode().strip(),
                "tracked_diff_sha256": hashlib.sha256(patch).hexdigest(),
                "untracked_source_sha256": digest(untracked), "dirty": bool(patch or extra),
                "unix_modes_checked": native is None,
                "git_backend": 'native-windows-wsl-share' if native else 'owning-filesystem'}
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        return {"root": str(root), "unavailable": True, "error": type(exc).__name__}


def manifest(*, tier: str, graph=None, artifacts=(), **settings) -> dict:
    return {"contract_version": CONTRACT_VERSION, "tier": tier, "code": code(),
            "python": platform.python_version(), "platform": platform.system(),
            "graph_sha256": digest(graph.model_dump(mode="json")) if graph is not None else None,
            "artifacts": [artifact(p) for p in artifacts if p is not None],
            "settings": settings}
