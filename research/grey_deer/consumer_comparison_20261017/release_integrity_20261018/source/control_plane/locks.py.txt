"""control_plane.locks — advisory file locks for Mastermind jobs.

Uses ``fcntl.flock`` with LOCK_EX | LOCK_NB (non-blocking exclusive lock).
Lock files live under ``data/locks/<name>.lock``.

NAME CONVENTION
---------------
    book:<id>       per-book lock, e.g. "book:flagship"
    global:<op>     shared-op lock, e.g. "global:settle", "global:cron_maintenance"

STALE-LOCK SAFETY
-----------------
``fcntl.flock`` is advisory and process-scoped: the OS releases the lock
automatically when the file descriptor is closed or the process dies.
There are NO PID files.  A lock held by a dead process is therefore released
immediately — no stale-lock accumulation.  This is different from fcntl.lockf
or third-party lock implementations that use PID sentinels.

USAGE
-----
    lock = acquire("book:flagship")
    if lock is None:
        # another process holds it — skip or log
        return
    with lock:
        # exclusive access
        ...
    # or equivalently:
    with acquire("book:flagship") as lock:
        if lock is None:
            return  # could not acquire

NOTE: ``acquire`` returns None (not a context manager) when the lock is held
elsewhere.  Always check for None before entering the ``with`` block, or use
the convenience pattern above.
"""
from __future__ import annotations

import fcntl
import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# path resolution
# ---------------------------------------------------------------------------

def _locks_dir(root: str | Path | None = None) -> Path:
    if root is None:
        base = Path(__file__).resolve().parent.parent / "data"
    else:
        base = Path(root) / "data"
    d = base / "locks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _lock_path(name: str, root: str | Path | None = None) -> Path:
    return _locks_dir(root) / f"{name}.lock"


# ---------------------------------------------------------------------------
# Lock object
# ---------------------------------------------------------------------------

class Lock:
    """Context manager wrapper around an acquired fcntl.flock file descriptor.

    Do not construct directly; use ``acquire()``.
    """

    def __init__(self, fd: int, path: Path, name: str) -> None:
        self._fd   = fd
        self._path = path
        self._name = name

    # context-manager support
    def __enter__(self) -> "Lock":
        return self

    def __exit__(self, *_: object) -> None:
        self.release()

    def release(self) -> None:
        """Release the lock and close the file descriptor.

        Idempotent: calling release() more than once is safe.
        """
        if self._fd == -1:
            return
        try:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
        except Exception:  # noqa: BLE001
            pass
        try:
            os.close(self._fd)
        except Exception:  # noqa: BLE001
            pass
        self._fd = -1

    def __repr__(self) -> str:
        state = "held" if self._fd != -1 else "released"
        return f"<Lock name={self._name!r} {state}>"


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def acquire(
    name: str,
    *,
    root: str | Path | None = None,
) -> Optional[Lock]:
    """Try to acquire an exclusive advisory lock named ``name``.

    Parameters
    ----------
    name : str
        Lock name following the convention: "book:<id>" or "global:<op>".
    root : str | Path | None
        Project root override for tests (None = relative to this file).

    Returns
    -------
    Lock
        An acquired ``Lock`` context manager.
    None
        The lock is held by another process; caller should skip or log.

    NEVER raises — returns None on any unexpected error.
    """
    try:
        path = _lock_path(name, root)
        # open (or create) the sentinel file
        fd = os.open(str(path), os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError):
            # lock is held elsewhere
            os.close(fd)
            return None
        return Lock(fd, path, name)
    except Exception as exc:  # noqa: BLE001
        log.warning("control_plane.locks.acquire(%r) failed: %s", name, exc)
        return None


def acquire_or_log(
    name: str,
    *,
    job: str = "",
    book: str = "",
    root: str | Path | None = None,
    events_root: str | Path | None = None,
) -> Optional[Lock]:
    """``acquire`` + the masterplan's "skip+log" overlap policy in one call.

    On conflict (or unexpected acquire failure) appends a ``lock_conflict``
    run-event so an overlapping run can never pass silently, then returns
    None. Call sites still decide to skip. NEVER raises.
    """
    lock = acquire(name, root=root)
    if lock is None:
        try:
            from control_plane import run_events

            run_events.append(
                {
                    "kind": "lock_conflict",
                    "job": job,
                    "book": book,
                    "step": "acquire",
                    "status": "lock_held",
                    "severity": "ADVISORY_ONLY",
                    "actor": "system",
                    "extra": {"lock": name},
                },
                root=events_root,
            )
        except Exception:  # noqa: BLE001 — logging must never block the skip
            pass
    return lock
