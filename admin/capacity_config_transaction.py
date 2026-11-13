"""Shared lock for the incumbent route document and its prepared control receipt.

Native policy writers and the admin adapter use this exact lock before reading.
This helper owns no policy, configuration copy, service, queue or retries.
"""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import stat

TERMINAL = frozenset({"VALIDATED", "APPLIED", "NOT_APPLIED", "CONFLICT", "ROLLED_BACK"})

class WriterBusy(RuntimeError):
    pass

class PendingConfiguration(RuntimeError):
    pass


def acquire_writer(path, *, operation_id=None):
    path = Path(path)
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("nonregular configuration path")
    fd = os.open(path.with_name(path.name + ".admin-control.lock"),
                 os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_nlink != 1:
            raise ValueError("invalid configuration lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WriterBusy("configuration writer is active") from exc
        # The incumbent attended reload journal survives a lost process/flock.
        # Its owner removes it only after runtime reconciliation; phase names do
        # not let configuration writers resume independently of that owner.
        maintenance = path.parent / "state/reload.lock/maintenance.json"
        try:
            maintenance.lstat()
        except FileNotFoundError:
            pass
        except OSError as exc:
            raise WriterBusy("native maintenance requires reconciliation") from exc
        else:
            raise WriterBusy("native maintenance requires reconciliation")
        journal = path.with_name(path.name + ".admin-receipts.json")
        try:
            jfd = os.open(journal, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            rows = []
        else:
            try:
                meta = os.fstat(jfd)
                if not stat.S_ISREG(meta.st_mode) or not 0 < meta.st_size <= 256 * 1024:
                    raise ValueError("invalid configuration receipt store")
                rows = json.loads(os.read(jfd, 256 * 1024 + 1))
            finally:
                os.close(jfd)
        if not isinstance(rows, list) or len(rows) > 100 or any(not isinstance(r, dict) for r in rows):
            raise ValueError("invalid configuration receipts")
        if any(r.get("state") not in TERMINAL and r.get("operation_id") != operation_id for r in rows):
            raise PendingConfiguration("an existing configuration operation requires reconciliation")
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def configuration_writer(path, *, operation_id=None):
    fd = acquire_writer(path, operation_id=operation_id)
    try:
        yield
    finally:
        os.close(fd)
