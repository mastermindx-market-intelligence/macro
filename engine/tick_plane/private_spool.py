"""Crash-safe, private local T.* spool for the existing TP-1 source owner.

Source-only private data, never a public data product or parallel market-data
store. Quote Q.* payloads are NEVER persisted here; only a bounded in-flight
NBBO ring holds quote updates. No R2 upload, network connection, credential,
scheduler, replay controller or publication authority exists in this module.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from engine.tick_plane.stream_events import SCHEMA as SOURCE_SCHEMA, _SESSION, _SYMBOL

SPOOL_SCHEMA = "equity.tick_plane.private_part/v0"
MAX_RECORDS = 2000
MAX_PART_BYTES = 4 * 1024 * 1024
_TRADE_FIELDS = frozenset({
    "schema", "ticker", "session", "source", "event_type", "native_sequence",
    "sip_timestamp_ns", "participant_timestamp_ns", "source_timestamp_precision",
    "original_frame_received_ns", "source_receipt_id", "source_frame_sha256",
    "frame_event_index", "source_status", "correction_status",
    "eligible_for_pressure", "conditions_rules_ref", "market_tape",
    "trade_id", "dedup_key", "price", "size_integer_shares",
    "decimal_size_shares", "trade_conditions", "exchange", "trf_id",
    "trf_timestamp_ns", "venue_class", "trade_action",
})


class PrivateSpoolRefusal(ValueError):
    pass


class PrivateSpoolBusy(PrivateSpoolRefusal):
    code = "SPOOL_BUSY"


@dataclass(frozen=True)
class SpoolLimits:
    """Caller-owned admission limits; bytes are logical file lengths, not blocks."""

    max_stored_bytes: int = 256 * 1024 * 1024
    max_parts: int = 256
    min_free_bytes: int = 1024 * 1024 * 1024
    max_inventory_entries: int = 4096

    def __post_init__(self):
        for name in ("max_stored_bytes", "max_parts", "min_free_bytes",
                     "max_inventory_entries"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise PrivateSpoolRefusal("finite positive integer spool limits required")


DEFAULT_LIMITS = SpoolLimits()
_PART_NAME = re.compile(r"[0-9a-f]{64}\.jsonl")
_PENDING_NAME = re.compile(r"\.pending-[a-z0-9_]{8,32}")
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _private_info(info, *, directory, device=None):
    if (not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077
            or (device is not None and info.st_dev != device)
            or (not directory and info.st_nlink != 1)):
        raise PrivateSpoolRefusal(
            "spool entry is not a private owned same-filesystem directory or single-link file")


def _private_root(root):
    path = Path(root)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise PrivateSpoolRefusal("pre-existing real absolute private directory required")
    canonical = path.resolve()
    source_repo = Path(__file__).resolve().parents[2]
    if canonical == source_repo or source_repo in canonical.parents:
        raise PrivateSpoolRefusal("refuse any private-source spool inside repository")
    if stat.S_IMODE(canonical.stat().st_mode) & 0o077:
        raise PrivateSpoolRefusal("private spool directory has group/other access")
    return canonical


@contextmanager
def _locked_root(base):
    fd = os.open(base, _DIR_FLAGS)
    try:
        _private_info(os.fstat(fd), directory=True)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise PrivateSpoolBusy("SPOOL_BUSY: another same-host writer owns admission") from exc
        # Closing this independently opened descriptor releases the OS lock,
        # including on failure. No persistent lock file or retry loop is needed.
        yield fd
    finally:
        os.close(fd)


def _valid_date(value):
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _inventory(root_fd, limits):
    """Bound traversal by entries and fixed date/session/ticker depth."""
    device = os.fstat(root_fd).st_dev
    entries = parts = stored_bytes = 0
    directories = set()

    def visit(fd, components):
        nonlocal entries, parts, stored_bytes
        with os.scandir(fd) as listing:
            for entry in listing:
                entries += 1
                if entries > limits.max_inventory_entries:
                    raise PrivateSpoolRefusal("spool inventory entry ceiling exceeded")
                info = entry.stat(follow_symlinks=False)
                depth = len(components)
                name = entry.name
                if depth < 3:
                    valid = (_valid_date(name) if depth == 0 else
                             name in ("RTH", "PRE", "POST") if depth == 1 else
                             _SYMBOL.fullmatch(name) is not None)
                    if not valid:
                        raise PrivateSpoolRefusal("unknown spool inventory directory")
                    _private_info(info, directory=True, device=device)
                    child = os.open(name, _DIR_FLAGS, dir_fd=fd)
                    try:
                        current = os.fstat(child)
                        _private_info(current, directory=True, device=device)
                        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino):
                            raise PrivateSpoolRefusal("spool directory changed during inventory")
                        path = components + (name,)
                        directories.add(path)
                        visit(child, path)
                    finally:
                        os.close(child)
                else:
                    if not (_PART_NAME.fullmatch(name) or _PENDING_NAME.fullmatch(name)):
                        raise PrivateSpoolRefusal("unknown spool inventory file")
                    _private_info(info, directory=False, device=device)
                    # Orphan pending files consume both bytes and an admission slot.
                    parts += 1
                    stored_bytes += info.st_size

    visit(root_fd, ())
    return stored_bytes, parts, entries, directories


def _partition_fd(root_fd, components, *, create=False):
    fd = os.dup(root_fd)
    device = os.fstat(root_fd).st_dev
    try:
        for name in components:
            if create:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=fd)
                    os.fsync(fd)
                except FileExistsError:
                    pass
            try:
                child = os.open(name, _DIR_FLAGS, dir_fd=fd)
            except FileNotFoundError:
                if create:
                    raise
                return None
            os.close(fd)
            fd = child
            _private_info(os.fstat(fd), directory=True, device=device)
        result, fd = fd, None
        return result
    finally:
        if fd is not None:
            os.close(fd)


def _same_payload(fd, name, payload):
    try:
        source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                         dir_fd=fd)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(source)
        _private_info(info, directory=False, device=os.fstat(fd).st_dev)
        if info.st_size != len(payload) or info.st_size > MAX_PART_BYTES:
            return False
        with os.fdopen(source, "rb", closefd=False) as fh:
            return fh.read(MAX_PART_BYTES + 1) == payload
    finally:
        os.close(source)


def _check_free(root_fd, limits, *, incoming_bytes=0, new_directories=0):
    space = os.fstatvfs(root_fd)
    block = space.f_frsize
    if block <= 0:
        raise PrivateSpoolRefusal("unknown filesystem allocation unit")
    # Admission estimate only: this does not reserve space against other users
    # of the filesystem. Recheck after writing and before publication.
    allowance = ((incoming_bytes + block - 1) // block) * block
    allowance += (new_directories + 1) * block if incoming_bytes else 0
    if space.f_bavail * block - allowance < limits.min_free_bytes:
        raise PrivateSpoolRefusal("spool minimum free-space reserve would be breached")


def _validated_record(record, *, session, ticker):
    if not isinstance(record, dict) or set(record) != _TRADE_FIELDS:
        raise PrivateSpoolRefusal("unrecognized or extra source fields; refuse raw credentials/payloads")
    if (record["schema"] != SOURCE_SCHEMA or record["event_type"] != "T"
            or record["session"] != session or record["ticker"] != ticker):
        raise PrivateSpoolRefusal("only same-session normalized trades may be spooled")
    if record["correction_status"] != "STREAM_PROVISIONAL_UNRECONCILED":
        raise PrivateSpoolRefusal("do not falsely finalize a live-stream trade")
    if not isinstance(record["dedup_key"], str) or not record["dedup_key"]:
        raise PrivateSpoolRefusal("missing native trade identity")
    if (type(record["sip_timestamp_ns"]) is not int or
            type(record["original_frame_received_ns"]) is not int or
            record["original_frame_received_ns"] < record["sip_timestamp_ns"]):
        raise PrivateSpoolRefusal("invalid source event/receipt clocks")
    if not isinstance(record["source_frame_sha256"], str) or len(record["source_frame_sha256"]) != 64:
        raise PrivateSpoolRefusal("missing raw-source digest")
    return dict(record)


def write_private_trade_part(*, root, session, ticker, events, limits=DEFAULT_LIMITS):
    """Append one immutable private part within a root-wide admission transaction.

    Caller owns one consistent limits policy and source custody for this root.
    Cooperative same-host writers serialize through nonblocking directory flock;
    contention refuses with PrivateSpoolBusy. Logical bytes include orphan pending
    files. An OS error after linking can leave a committed part: reconcile its
    exact digest through readback/idempotent retry; an exception is not no-effect
    proof. No pruning, upload, lease, scheduler or production policy is introduced.
    """
    if type(limits) is not SpoolLimits:
        raise PrivateSpoolRefusal("explicit validated SpoolLimits required")
    base = _private_root(root)
    if (not isinstance(session, str) or _SESSION.fullmatch(session) is None or
            not _valid_date(session.split(":")[0]) or
            not isinstance(ticker, str) or _SYMBOL.fullmatch(ticker) is None):
        raise PrivateSpoolRefusal("invalid session or symbol partition")
    if not isinstance(events, (tuple, list)) or not 1 <= len(events) <= MAX_RECORDS:
        raise PrivateSpoolRefusal("bounded nonempty source part required")
    unique = {}
    for item in events:
        e = _validated_record(item, session=session, ticker=ticker)
        old = unique.get(e["dedup_key"])
        if old is not None and old != e:
            raise PrivateSpoolRefusal("conflicting duplicate native print identity")
        unique[e["dedup_key"]] = e
    records = sorted(unique.values(), key=lambda r: (
        r["sip_timestamp_ns"], r["native_sequence"], r["dedup_key"]))
    payload = b"".join(
        (json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()
        for x in records
    )
    if len(payload) > MAX_PART_BYTES:
        raise PrivateSpoolRefusal("source part exceeds byte budget")
    digest = hashlib.sha256(payload).hexdigest()
    components = (*session.split(":"), ticker)
    output = base.joinpath(*components)
    target_name = digest + ".jsonl"
    receipt = {"schema": SPOOL_SCHEMA, "state": "ALREADY_PRESENT",
               "sha256": digest, "n": len(records), "bytes": len(payload),
               "path_private_only": str(output / target_name)}
    with _locked_root(base) as root_fd:
        stored_bytes, parts, entries, directories = _inventory(root_fd, limits)
        output_fd = _partition_fd(root_fd, components)
        try:
            present = _same_payload(output_fd, target_name, payload) if output_fd is not None else None
            if present is not None:
                if not present:
                    raise PrivateSpoolRefusal("immutable part target differs; no overwrite")
                # No allocation: retry at capacity still verifies the whole inventory.
                return receipt
            missing = sum(components[:i] not in directories for i in range(1, 4))
            if stored_bytes + len(payload) > limits.max_stored_bytes:
                raise PrivateSpoolRefusal("spool stored-byte ceiling exceeded")
            if parts + 1 > limits.max_parts:
                raise PrivateSpoolRefusal("spool part-count ceiling exceeded")
            # Reserve both transient pending/final names and newly created folders.
            if entries + missing + 2 > limits.max_inventory_entries:
                raise PrivateSpoolRefusal("spool inventory entry ceiling would be exceeded")
            _check_free(root_fd, limits, incoming_bytes=len(payload), new_directories=missing)
            if output_fd is None:
                output_fd = _partition_fd(root_fd, components, create=True)
            pending_name = ".pending-" + os.urandom(16).hex()
            pending_info = None
            try:
                pending_fd = os.open(pending_name, os.O_WRONLY | os.O_CREAT |
                                     os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=output_fd)
                pending_info = os.fstat(pending_fd)
                with os.fdopen(pending_fd, "wb") as fh:
                    os.fchmod(fh.fileno(), 0o600)
                    fh.write(payload)
                    fh.flush()
                    os.fsync(fh.fileno())
                    if os.fstat(fh.fileno()).st_size != len(payload):
                        raise PrivateSpoolRefusal("incomplete private spool write")
                _check_free(root_fd, limits)
                try:
                    os.link(pending_name, target_name, src_dir_fd=output_fd,
                            dst_dir_fd=output_fd, follow_symlinks=False)
                    receipt["state"] = "PART_CREATED"
                except FileExistsError:
                    if _same_payload(output_fd, target_name, payload) is not True:
                        raise PrivateSpoolRefusal("immutable part collision; never overwrite")
                os.fsync(output_fd)
            finally:
                if pending_info is not None:
                    current = os.stat(pending_name, dir_fd=output_fd, follow_symlinks=False)
                    if (current.st_dev, current.st_ino) != (pending_info.st_dev, pending_info.st_ino):
                        raise PrivateSpoolRefusal("pending identity changed; refuse foreign cleanup")
                    os.unlink(pending_name, dir_fd=output_fd)
                    os.fsync(output_fd)
        finally:
            if output_fd is not None:
                os.close(output_fd)
    return receipt
