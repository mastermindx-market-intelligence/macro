"""Load config.yml once; expose read-only source identity, not a reload service."""
from __future__ import annotations

import hashlib
import os
import stat
import threading
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_snapshot_lock = threading.RLock()
_MAX_OBSERVER_BYTES = 2 * 1024 * 1024


def _load_dotenv() -> None:
    """Local runs read secrets from a gitignored .env; CI uses real env vars,
    which always win over the file."""
    p = ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()


@lru_cache(maxsize=1)
def _load_source() -> tuple[dict, str, Path]:
    # One existing cache, now retaining the identity of its exact input bytes.
    root = ROOT.resolve()
    raw = (root / "config.yml").read_bytes()
    return yaml.safe_load(raw), hashlib.sha256(raw).hexdigest(), root


def load() -> dict:
    with _snapshot_lock:
        return _load_source()[0]


def _clear_load_cache() -> None:
    with _snapshot_lock:
        _load_source.cache_clear()


# Preserve the public lru_cache controls used by existing callers/tests.
load.cache_clear = _clear_load_cache
load.cache_info = _load_source.cache_info
load.cache_parameters = _load_source.cache_parameters
load.__wrapped__ = lambda: _load_source.__wrapped__()[0]


def _source_stamp(info) -> tuple:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _observed_source(path: Path) -> tuple[bytes | None, str | None]:
    """Bounded regular-file read; never follow a symlink or block on a pipe."""
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode):
            return None, "SOURCE_UNAVAILABLE"
        flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
        with os.fdopen(os.open(path, flags), "rb") as handle:
            opened = os.fstat(handle.fileno())
            if _source_stamp(opened) != _source_stamp(before):
                return None, "SOURCE_CHANGED_DURING_OBSERVATION"
            raw = handle.read(_MAX_OBSERVER_BYTES + 1)
            after = os.fstat(handle.fileno())
        current = path.lstat()
        if _source_stamp(current) != _source_stamp(after) or _source_stamp(after) != _source_stamp(opened):
            return None, "SOURCE_CHANGED_DURING_OBSERVATION"
        if len(raw) > _MAX_OBSERVER_BYTES:
            return None, "SOURCE_TOO_LARGE"
        return raw, None
    except (OSError, ValueError):
        return None, "SOURCE_UNAVAILABLE"


def configuration_adoption() -> dict:
    """Observe this process's loaded source versus disk, without loading/reloading.

    Matching hashes are source-byte evidence only, not effective runtime model,
    credentials, remote-worker adoption, admission or capacity authority.
    """
    result = {
        "schema": "mastermind.config_source_adoption.v1",
        "state": "NOT_LOADED", "scope": "current_process_source_snapshot",
        "source": "config.yml", "observed_at": datetime.now(timezone.utc).isoformat(),
        "loaded_sha256": None, "installed_sha256": None, "source_bytes_match": None,
        "not_covered": ["other_config_files", "environment", "credentials",
                        "runtime_overrides", "retained_config_references", "remote_processes", "provider_usage",
                        "execution_admission"],
    }
    try:
        with _snapshot_lock:
            root = ROOT.resolve()
            snapshot = _load_source() if _load_source.cache_info().currsize else None
            if snapshot is not None:
                result["loaded_sha256"] = snapshot[1]
            raw, error = _observed_source(root / "config.yml")
            if error:
                result["state"] = error
                return result
            result["installed_sha256"] = hashlib.sha256(raw).hexdigest()
            if snapshot is None:
                return result
            if snapshot[2] != root:
                result["state"] = "SOURCE_ROOT_CHANGED"
                return result
            matches = snapshot[1] == result["installed_sha256"]
            result["source_bytes_match"] = matches
            result["state"] = "MATCHING_SOURCE" if matches else "SOURCE_CHANGED"
            return result
    except Exception:
        result["state"] = "OBSERVATION_UNAVAILABLE"
        result["source_bytes_match"] = None
        return result


def data_dir() -> Path:
    return ROOT / load()["storage"]["data_dir"]


def site_dir() -> Path:
    return ROOT / load()["storage"]["site_dir"]


def secret(name: str) -> str | None:
    """Secrets come from env (GitHub Actions secrets locally via shell env)."""
    v = os.environ.get(name, "").strip()
    return v or None
