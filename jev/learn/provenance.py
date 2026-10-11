"""Content identities for replay and release evidence. Never reads credential files."""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_VERSION = 1


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
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args],
                                           stderr=subprocess.DEVNULL, timeout=5)
        patch = git("diff", "HEAD", "--", ".")
        extra = git("ls-files", "--others", "--exclude-standard", "--",
                    "jev/*.py", "hive/*.py", "tools/*.py", "addons/*.lua").decode().splitlines()
        untracked = {name: artifact(root / name).get("sha256") for name in extra}
        return {"root": str(root), "commit": git("rev-parse", "HEAD").decode().strip(),
                "tracked_diff_sha256": hashlib.sha256(patch).hexdigest(),
                "untracked_source_sha256": digest(untracked), "dirty": bool(patch or extra)}
    except (OSError, subprocess.SubprocessError):
        return {"root": str(root), "unavailable": True}


def manifest(*, tier: str, graph=None, artifacts=(), **settings) -> dict:
    return {"contract_version": CONTRACT_VERSION, "tier": tier, "code": code(),
            "python": platform.python_version(), "platform": platform.system(),
            "graph_sha256": digest(graph.model_dump(mode="json")) if graph is not None else None,
            "artifacts": [artifact(p) for p in artifacts if p is not None],
            "settings": settings}
