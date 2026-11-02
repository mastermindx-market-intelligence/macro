"""Native Options publication exclusion; never a source or account grant.

The canonical host checkout owns the persistent inode and the existing bounded
correction operation's receipt. No cwd/env override and no stale-lock deletion.
An outer caller holds this context across freshness read, correction and readback;
nested publisher calls join that same thread/process interval.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import threading

OPERATION = "oem-01a156f1-spy-20261016-correction-v1"
_held = threading.local()


class PublicationCustodyError(RuntimeError):
    pass


def _native_state_root():
    return Path.home() / "optionshub-ops-wt" / ".git"


def _sync_dir(path):
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def assert_admission_open():
    # The bootstrap owns this existing-boundary barrier. Presence is enough to
    # refuse; no PID/age-based cleanup or publisher escape hatch exists.
    p = _native_state_root() / "options-hub-adoption.pending"
    if p.exists() or p.is_symlink():
        raise PublicationCustodyError("publication_adoption_fenced")


def has_publication_custody():
    if getattr(_held, "lease", None) is None:
        return False
    require_custody()
    return True


def require_custody(*, installation=False):
    lease = getattr(_held, "lease", None)
    if lease is None or lease[0] != os.getpid():
        raise PublicationCustodyError("publication_custody_required")
    _, fd, path, role = lease
    if role != ("installation" if installation else "publication"):
        raise PublicationCustodyError("publication_custody_role_mismatch")
    if not installation:
        assert_admission_open()
    a, b = os.fstat(fd), path.lstat()
    if (not stat.S_ISREG(b.st_mode) or b.st_nlink != 1
            or (a.st_dev, a.st_ino) != (b.st_dev, b.st_ino)):
        raise PublicationCustodyError("publication_lock_identity_changed")
    return path.parent


@contextmanager
def publication_custody():
    with _custody(installation=False):
        yield


@contextmanager
def installation_custody():
    """Same inode, distinct non-publishing role; not legacy admission proof."""
    with _custody(installation=True):
        yield


@contextmanager
def _custody(*, installation):
    if getattr(_held, "lease", None) is not None:
        require_custody(installation=installation)  # Forked children cannot inherit admission.
        yield
        return
    if not installation:
        assert_admission_open()
    root = _native_state_root()
    if not root.is_dir() or root.is_symlink() or root.resolve() != root:
        raise PublicationCustodyError("publication_state_unavailable")
    path = root / "options-hub-publication.lock"
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
            raise PublicationCustodyError("publication_lock_identity_invalid")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise PublicationCustodyError("publication_busy") from None
        _held.lease = (os.getpid(), fd, path, "installation" if installation else "publication")
        require_custody(installation=installation)
        if installation:
            claim = _read_claim(installation=True)
            if claim is not None and claim.get("state") != "READBACK_VERIFIED":
                raise PublicationCustodyError("installation_correction_unsettled")
        yield
    finally:
        _held.lease = None
        os.close(fd)  # No unlink; closing releases only this holder's descriptor.


def _claim_dir(*, installation=False):
    return require_custody(installation=installation) / OPERATION


def _read_claim(*, installation=False):
    directory = _claim_dir(installation=installation)
    if not directory.exists() and not directory.is_symlink():
        return None
    try:
        if directory.is_symlink():
            raise ValueError()
        p = directory / "receipt.json"
        if p.is_symlink() or p.stat().st_size > 65536:
            raise ValueError()
        value = json.loads(p.read_text())
        if (value.get("operation") != OPERATION or not isinstance(value.get("binding"), dict)
                or not all(isinstance(value["binding"].get(k), str) for k in ("bucket", "key"))):
            raise ValueError()
        binding = value["binding"]
        if (value.get("state") not in ("STARTED", "DISPATCHING", "HELD", "ACKNOWLEDGED_AWAITING_READBACK", "READBACK_VERIFIED")
                or type(binding.get("input_bytes")) is not int or not 0 < binding["input_bytes"] <= 8 * 1024 * 1024
                or not re.fullmatch(r"[0-9a-f]{64}", binding.get("input_sha256", ""))):
            raise ValueError()
        return value
    except Exception:
        raise PublicationCustodyError("correction_claim_unreadable") from None


def _save_claim(record):
    directory = _claim_dir()
    temporary = directory / "receipt.tmp"
    with temporary.open("x") as stream:
        json.dump(record, stream, sort_keys=True)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, directory / "receipt.json")
    _sync_dir(directory)


def assert_target_available(bucket, key):
    claim = _read_claim()
    if claim is not None and (bucket, key) == (claim["binding"]["bucket"], claim["binding"]["key"]):
        if claim.get("state") != "READBACK_VERIFIED":
            raise PublicationCustodyError("correction_target_unsettled")


def assert_local_target_available(key):
    # Local archive bytes are shared input evidence regardless of the current
    # invocation's bucket override (including apply-only/no-publish repairs).
    claim = _read_claim()
    if claim is not None and key == claim["binding"]["key"] and claim.get("state") != "READBACK_VERIFIED":
        raise PublicationCustodyError("correction_local_target_unsettled")


def begin_correction(binding):
    directory = _claim_dir()
    try:
        directory.mkdir(mode=0o700)  # Original identity is never reused, even after success.
    except FileExistsError:
        raise PublicationCustodyError("correction_claim_exists_no_replay") from None
    _sync_dir(directory.parent)
    record = {"operation": OPERATION, "state": "STARTED", "binding": dict(binding),
              "pid": os.getpid(), "started_at": datetime.now(timezone.utc).isoformat()}
    _save_claim(record)


def mark_correction_dispatch(binding):
    record = _read_claim()
    if (record is None or record.get("state") != "STARTED"
            or record.get("pid") != os.getpid() or record.get("binding") != binding):
        raise PublicationCustodyError("correction_dispatch_not_admitted")
    record["state"] = "DISPATCHING"
    _save_claim(record)  # One durable dispatch admission, even through a direct helper call.


def retain_correction_result(result):
    record = _read_claim()
    if record is None or record.get("state") not in ("STARTED", "DISPATCHING"):
        raise PublicationCustodyError("correction_claim_not_started")
    record["state"] = "ACKNOWLEDGED_AWAITING_READBACK" if result.get("status") == "acknowledged" else "HELD"
    record["result"] = result
    _save_claim(record)


def verify_correction_readback(body):
    """Consume already-admitted bytes, never fetch/retry or clear an UNKNOWN."""
    record = _read_claim()
    if record is None or record.get("state") != "ACKNOWLEDGED_AWAITING_READBACK":
        raise PublicationCustodyError("acknowledged_correction_required")
    binding = record["binding"]
    if len(body) != binding["input_bytes"] or hashlib.sha256(body).hexdigest() != binding["input_sha256"]:
        raise PublicationCustodyError("correction_readback_mismatch")
    record["state"] = "READBACK_VERIFIED"
    _save_claim(record)
