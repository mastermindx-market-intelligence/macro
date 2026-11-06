"""The incumbent sealed-window and irreversible peek ledger.

All participating writers serialize on one fixed lock and reload the full history.
Consumption spends access before a separate trusted evaluator can release labels; it
is neither caller authentication nor a label reader. An independently held history
anchor detects replacement of accepted history. Advisory locks cannot exclude an
uncooperative writer, so actual dataset/OS custody is a separate qualification.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, fields
from datetime import datetime, timezone
import fcntl
from functools import wraps
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import threading
import uuid

_SEALS = ("data", "vault", "seals.json")
_PEEKLOG = ("data", "vault", "peek_log.jsonl")
_GENESIS = "0" * 64
_MAX_LOG = 16 * 1024 * 1024
_MAX_SEALS = 1024 * 1024
_LOCK = ".holdout-vault.lock"


class VaultError(RuntimeError):
    """Integrity or durability is unproved; do not release labels or mint a retry ID."""


def _sha(obj) -> str:
    # Preserve the original ledger's hash serialization for existing plain JSON.
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _text(value, name, limit=256, *, empty=False):
    if type(value) is not str or len(value) > limit or (not value and not empty):
        raise VaultError(f"invalid {name}")
    if any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise VaultError(f"invalid {name}")


def _hash(value, name):
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise VaultError(f"invalid {name}")


def _plain(value, depth=0, budget=None):
    """Reject custom hooks, cycles, nonfinite numbers and unbounded JSON before use."""
    if budget is None:
        budget = [100_000]
    budget[0] -= 1
    if depth > 32 or budget[0] < 0:
        raise VaultError("JSON exceeds bounds")
    kind = type(value)
    if value is None or kind is bool:
        return
    if kind is int:
        if value.bit_length() > 256:
            raise VaultError("integer exceeds bounds")
    elif kind is float:
        if not math.isfinite(value):
            raise VaultError("nonfinite JSON")
    elif kind is str:
        if len(value) > 65536 or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise VaultError("invalid JSON string")
    elif kind is list:
        for item in value:
            _plain(item, depth + 1, budget)
    elif kind is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise VaultError("JSON object key must be text")
            _plain(key, depth + 1, budget)
            _plain(item, depth + 1, budget)
    else:
        raise VaultError("plain JSON required")


def _decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise VaultError("duplicate JSON key")
            result[key] = value
        return result
    def constant(_):
        raise VaultError("nonfinite JSON")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
        _plain(value)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise VaultError("invalid JSON") from exc


@dataclass(frozen=True)
class VaultHistoryAnchor:
    seals_sha256: str
    peek_prefix_sha256: str
    peek_prefix_bytes: int
    peek_prefix_head_sha256: str

    def __post_init__(self):
        for name in ("seals_sha256", "peek_prefix_sha256", "peek_prefix_head_sha256"):
            _hash(getattr(self, name), name)
        if type(self.peek_prefix_bytes) is not int or not 0 <= self.peek_prefix_bytes <= _MAX_LOG:
            raise VaultError("invalid prefix length")


@dataclass(frozen=True)
class VaultConsumptionRequest:
    request_id: str
    original_root_id: str
    original_family_id: str
    hypothesis_id: str
    window_id: str
    source_sha256: str
    protocol_sha256: str
    seal_sha256: str

    def __post_init__(self):
        for name in ("request_id", "original_root_id", "original_family_id", "hypothesis_id", "window_id"):
            _text(getattr(self, name), name)
        for name in ("source_sha256", "protocol_sha256", "seal_sha256"):
            _hash(getattr(self, name), name)


@dataclass(frozen=True)
class VaultConsumptionReceipt:
    request: VaultConsumptionRequest
    record_sha256: str
    peek_count: int
    snapshot_sha256: str
    snapshot_bytes: int
    consumption_state: str


def _request_dict(request):
    if type(request) is not VaultConsumptionRequest:
        raise VaultError("exact consumption request required")
    VaultConsumptionRequest.__post_init__(request)
    return {field.name: getattr(request, field.name) for field in fields(VaultConsumptionRequest)}


def _identity(info):
    return info.st_dev, info.st_ino


def _version(info):
    return _identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise VaultError("Vault file must be regular and have one link")
    return info


def _same_path(directory, name, fd):
    info = os.stat(name, dir_fd=directory, follow_symlinks=False)
    if _identity(info) != _identity(_regular(fd)) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise VaultError("Vault path identity changed")


@contextmanager
def _directory(path, *, create):
    """Walk from / with no symlink traversal and retain each directory binding."""
    opened = [os.open("/", os.O_RDONLY | os.O_DIRECTORY)]
    bindings = []
    try:
        for name in path.parts[1:]:
            parent = opened[-1]
            if create:
                try:
                    os.mkdir(name, mode=0o700, dir_fd=parent)
                    os.fsync(parent)
                except FileExistsError:
                    pass
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            opened.append(child)
            bindings.append((parent, name, child))
        def check():
            for parent, name, child in bindings:
                info = os.stat(name, dir_fd=parent, follow_symlinks=False)
                if not stat.S_ISDIR(info.st_mode) or _identity(info) != _identity(os.fstat(child)):
                    raise VaultError("Vault directory identity changed")
        check()
        yield opened[-1], check
        check()
    finally:
        for fd in reversed(opened):
            os.close(fd)


def _read(directory, name, limit):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        return None
    try:
        before = _regular(fd)
        if before.st_size > limit:
            raise VaultError("Vault file exceeds bounds")
        chunks, size = [], 0
        while True:
            chunk = os.read(fd, min(65536, limit + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > limit:
                raise VaultError("Vault file exceeds bounds")
        _same_path(directory, name, fd)
        if _version(before) != _version(os.fstat(fd)):
            raise VaultError("Vault file changed during read")
        return b"".join(chunks)
    finally:
        os.close(fd)


def _serialized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        # Keep final cached-state publication ordered with this instance's writes.
        # The separate file lock still serializes other instances and processes.
        with self._instance_lock:
            return method(self, *args, **kwargs)
    return call


class HoldoutVault:
    def __init__(self, root: str | Path | None = None, *, seals=_SEALS, peeklog=_PEEKLOG) -> None:
        # Reject foreign path hooks before any filesystem/path conversion.
        if root is not None and type(root) not in (str, type(Path("."))):
            raise VaultError("exact owner root path required")
        # Resolve the owner's root once, not candidate-supplied path components.
        base = Path(root if root is not None else ".").resolve()
        for parts in (seals, peeklog):
            if type(parts) not in (tuple, list) or not parts:
                raise VaultError("invalid Vault path")
            for part in parts:
                if type(part) is not str or part in ("", ".", "..") or "/" in part or "\0" in part:
                    raise VaultError("invalid Vault path")
        self.seals_path = base.joinpath(*seals)
        self.peeklog_path = base.joinpath(*peeklog)
        if self.seals_path.parent != self.peeklog_path.parent or self.seals_path.name == self.peeklog_path.name:
            raise VaultError("Vault seals and history require distinct files in one owner directory")
        if _LOCK in (self.seals_path.name, self.peeklog_path.name):
            raise VaultError("reserved Vault lock path")
        self._instance_lock = threading.RLock()
        self._known_history = False
        self._adopt({}, [])
        self._load_error = False
        self._load()

    def _adopt(self, seals, records):
        if seals or records:
            self._known_history = True
        self._seals, self._records = seals, records
        self._head = records[-1]["record_hash"] if records else _GENESIS
        self._peeks, self._retired = {}, {}
        for rec in records:
            if rec["kind"] == "retire":
                self._retired[rec["hypothesis_id"]] = rec["reason"]
            else:
                window = rec["window_id"]
                self._peeks[window] = self._peeks.get(window, 0) + 1
        self._load_error = False

    @contextmanager
    def _locked(self, *, create=False, read_only=False):
        try:
            with _directory(self.peeklog_path.parent, create=create) as (directory, check):
                new_lock = False
                flags = (os.O_RDONLY if read_only else os.O_RDWR) | os.O_NOFOLLOW | os.O_NONBLOCK
                if read_only:
                    lock = os.open(_LOCK, flags, dir_fd=directory)
                else:
                    try:
                        lock = os.open(_LOCK, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
                        new_lock = True
                    except FileExistsError:
                        lock = os.open(_LOCK, flags, dir_fd=directory)
                try:
                    _regular(lock)
                    fcntl.flock(lock, fcntl.LOCK_SH if read_only else fcntl.LOCK_EX)
                    _same_path(directory, _LOCK, lock)
                    check()
                    yield directory, check, new_lock
                    _same_path(directory, _LOCK, lock)
                    check()
                finally:
                    os.close(lock)
        except OSError as exc:
            raise VaultError(f"Vault I/O or durability failure: {exc.strerror}") from exc

    def _load(self):
        # Tolerant construction/read compatibility; every mutation reloads strictly.
        try:
            with _directory(self.peeklog_path.parent, create=False) as (directory, _):
                seals, records, _, _ = self._snapshot(directory, fresh=True)
            self._adopt(seals, records)
        except (VaultError, OSError):
            self._load_error = True

    def _records_from(self, raw, seals):
        if raw and not raw.endswith(b"\n"):
            raise VaultError("torn Vault history")
        records, head, retired, requests = [], _GENESIS, set(), set()
        common = {"kind", "hypothesis_id", "ts", "prev_hash", "record_hash"}
        for line in raw.splitlines():
            rec = _decode(line)
            if type(rec) is not dict:
                raise VaultError("Vault history row must be an object")
            kind = rec.get("kind")
            if kind == "peek":
                expected = common | {"window_id", "window_hash", "result", "commit"}
                if "consumption_request" in rec:
                    expected.add("consumption_request")
            elif kind == "retire":
                expected = common | {"reason"}
            else:
                raise VaultError("unknown Vault history kind")
            if set(rec) != expected:
                raise VaultError("unexpected Vault history fields")
            _text(rec["hypothesis_id"], "hypothesis_id")
            _text(rec["ts"], "timestamp", 64)
            try:
                timestamp = datetime.fromisoformat(rec["ts"])
                if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
                    raise ValueError("UTC required")
            except ValueError as exc:
                raise VaultError("invalid Vault timestamp") from exc
            _hash(rec["record_hash"], "record hash")
            if rec["prev_hash"] != head or rec["record_hash"] != _sha({k: v for k, v in rec.items() if k != "record_hash"}):
                raise VaultError("Vault hash chain mismatch")
            if kind == "retire":
                _text(rec["reason"], "reason", 65536, empty=True)
                retired.add(rec["hypothesis_id"])
            else:
                _text(rec["window_id"], "window_id")
                _hash(rec["window_hash"], "window hash")
                if seals.get(rec["window_id"]) != rec["window_hash"]:
                    raise VaultError("peek seal mismatch")
                if rec["hypothesis_id"] in retired:
                    raise VaultError("peek follows retirement")
                if rec["commit"] is not None:
                    _text(rec["commit"], "commit")
                if "consumption_request" in rec:
                    data = rec["consumption_request"]
                    if type(data) is not dict or set(data) != {f.name for f in fields(VaultConsumptionRequest)}:
                        raise VaultError("invalid consumption metadata")
                    req = VaultConsumptionRequest(**data)
                    if (req.hypothesis_id != rec["hypothesis_id"] or req.window_id != rec["window_id"]
                            or req.seal_sha256 != rec["window_hash"] or rec["result"] is not None
                            or rec["commit"] is not None or req.request_id in requests):
                        raise VaultError("inconsistent or duplicate consumption metadata")
                    requests.add(req.request_id)
            records.append(rec)
            head = rec["record_hash"]
        return records

    def _snapshot(self, directory, *, fresh=False, anchor=None):
        seals_raw = _read(directory, self.seals_path.name, _MAX_SEALS)
        raw = _read(directory, self.peeklog_path.name, _MAX_LOG)
        if seals_raw is None or raw is None:
            if fresh and seals_raw is None and raw is None:
                return {}, [], None, None
            raise VaultError("missing Vault seals or history; genesis cannot be inferred")
        seals = _decode(seals_raw)
        if type(seals) is not dict:
            raise VaultError("invalid seals")
        for window, digest in seals.items():
            _text(window, "window_id")
            _hash(digest, "seal")
        records = self._records_from(raw, seals)
        if anchor is not None:
            if type(anchor) is not VaultHistoryAnchor:
                raise VaultError("exact history anchor required")
            VaultHistoryAnchor.__post_init__(anchor)
            prefix = raw[:anchor.peek_prefix_bytes]
            if (_digest(seals_raw) != anchor.seals_sha256 or len(prefix) != anchor.peek_prefix_bytes
                    or _digest(prefix) != anchor.peek_prefix_sha256):
                raise VaultError("accepted history anchor mismatch")
            prefix_records = self._records_from(prefix, seals)
            head = prefix_records[-1]["record_hash"] if prefix_records else _GENESIS
            if head != anchor.peek_prefix_head_sha256:
                raise VaultError("accepted history head mismatch")
        return seals, records, seals_raw, raw

    def _write_seals(self, directory, seals, *, expected):
        raw = json.dumps(seals, indent=2, sort_keys=True).encode("utf-8")
        if len(raw) > _MAX_SEALS:
            raise VaultError("seals exceed bounds")
        temp = f".seals-{uuid.uuid4().hex}.tmp"
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            self._write_all(fd, raw)
            os.fsync(fd)
            _same_path(directory, temp, fd)
            if _read(directory, self.seals_path.name, _MAX_SEALS) != expected:
                raise VaultError("Vault seals changed before publication")
            os.replace(temp, self.seals_path.name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
            _same_path(directory, self.seals_path.name, fd)
        finally:
            os.close(fd)
            # Failed writes are retained for owner diagnosis; never erase evidence.

    @staticmethod
    def _write_all(fd, raw):
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise VaultError("short Vault write")
            offset += written

    def _initialize(self, directory):
        fd = os.open(self.peeklog_path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        try:
            os.fsync(fd)
            os.fsync(directory)
        finally:
            os.close(fd)
        self._write_seals(directory, {}, expected=None)

    def _append(self, directory, rec, seals, records, raw):
        rec = {**rec, "ts": datetime.now(timezone.utc).isoformat(),
               "prev_hash": records[-1]["record_hash"] if records else _GENESIS}
        rec["record_hash"] = _sha(rec)
        encoded = (json.dumps(rec, allow_nan=False) + "\n").encode("utf-8")
        if len(raw) + len(encoded) > _MAX_LOG:
            raise VaultError("Vault history exceeds bounds")
        # Validate the exact row before persisting it, including bounded legacy input.
        self._records_from(raw + encoded, seals)
        fd = os.open(self.peeklog_path.name, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        try:
            _same_path(directory, self.peeklog_path.name, fd)
            if _read(directory, self.peeklog_path.name, _MAX_LOG) != raw:
                raise VaultError("Vault history changed before append")
            self._write_all(fd, encoded)
            os.fsync(fd)
            os.fsync(directory)
            _same_path(directory, self.peeklog_path.name, fd)
        finally:
            os.close(fd)
        return rec, raw + encoded

    def _cold_adopt(self, directory, expected, *, anchor=None):
        seals, records, _, raw = self._snapshot(directory, anchor=anchor)
        if raw != expected:
            raise VaultError("Vault cold readback mismatch")
        return seals, records, raw

    @_serialized
    def seal(self, window_id: str, content) -> str:
        _text(window_id, "window_id")
        _plain(content)
        digest = _sha(content)
        with self._locked(create=True) as (directory, check, new_lock):
            seals, records, seals_raw, raw = self._snapshot(directory, fresh=new_lock and not self._known_history)
            previous = seals.get(window_id)
            if previous is not None and previous != digest:
                raise VaultError("window re-sealed with different content — holdout tamper")
            if raw is None:
                self._initialize(directory)
                raw = b""
                seals_raw = b"{}"
            updated = {**seals, window_id: digest}
            self._write_seals(directory, updated, expected=seals_raw)
            check()
            loaded, loaded_records, _ = self._cold_adopt(directory, raw)
            if loaded != updated:
                raise VaultError("seal cold readback mismatch")
        self._adopt(loaded, loaded_records)
        return digest

    @_serialized
    def is_sealed(self, window_id: str) -> bool:
        return window_id in self._seals

    @_serialized
    def is_retired(self, hypothesis_id: str) -> bool:
        return hypothesis_id in self._retired

    @_serialized
    def peek_count(self, window_id: str | None = None) -> int:
        return sum(self._peeks.values()) if window_id is None else self._peeks.get(window_id, 0)

    @staticmethod
    def _eligible(seals, records, hypothesis_id, window_id):
        if window_id not in seals:
            raise VaultError(f"window {window_id!r} is not sealed — cannot peek the holdout")
        if any(r["kind"] == "retire" and r["hypothesis_id"] == hypothesis_id for r in records):
            raise VaultError(f"hypothesis {hypothesis_id!r} is retired — no re-peeking the holdout")

    @_serialized
    def peek(self, hypothesis_id: str, *, window_id: str, result, commit: str | None = None) -> dict:
        _text(hypothesis_id, "hypothesis_id")
        _text(window_id, "window_id")
        _plain(result)
        if commit is not None:
            _text(commit, "commit")
        with self._locked(create=True) as (directory, check, new_lock):
            seals, records, _, raw = self._snapshot(directory, fresh=True)
            self._eligible(seals, records, hypothesis_id, window_id)
            rec, expected = self._append(directory, {"kind": "peek", "hypothesis_id": hypothesis_id,
                "window_id": window_id, "window_hash": seals[window_id], "result": result, "commit": commit},
                seals, records, raw)
            check()
            loaded, loaded_records, _ = self._cold_adopt(directory, expected)
        self._adopt(loaded, loaded_records)
        return {**rec, "peek_n": self._peeks[window_id]}

    @_serialized
    def retire(self, hypothesis_id: str, reason: str = "") -> dict:
        _text(hypothesis_id, "hypothesis_id")
        _text(reason, "reason", 65536, empty=True)
        with self._locked(create=True) as (directory, check, new_lock):
            seals, records, _, raw = self._snapshot(directory, fresh=new_lock and not self._known_history)
            if raw is None:
                self._initialize(directory)
                raw = b""
            rec, expected = self._append(directory, {"kind": "retire", "hypothesis_id": hypothesis_id,
                                                     "reason": reason}, seals, records, raw)
            check()
            loaded, loaded_records, _ = self._cold_adopt(directory, expected)
        self._adopt(loaded, loaded_records)
        return rec

    @_serialized
    def verify_chain(self) -> bool:
        return not self._load_error

    @staticmethod
    def _find(request_data, records):
        for rec in records:
            data = rec.get("consumption_request")
            if data is not None and data["request_id"] == request_data["request_id"]:
                if data != request_data:
                    raise VaultError("consumption request ID reused with different identity")
                return rec
        return None

    @staticmethod
    def _receipt(request, record, records, raw, state):
        count = sum(r["kind"] == "peek" and r["window_id"] == request.window_id for r in records)
        return VaultConsumptionReceipt(request, record["record_hash"], count, _digest(raw), len(raw), state)

    def _consumption(self, request, anchor, *, mode):
        data = _request_dict(request)
        if type(anchor) is not VaultHistoryAnchor:
            raise VaultError("exact history anchor required")
        VaultHistoryAnchor.__post_init__(anchor)
        with self._locked(read_only=mode == "reconcile") as (directory, check, _):
            seals, records, _, raw = self._snapshot(directory, anchor=anchor)
            if seals.get(request.window_id) != request.seal_sha256:
                raise VaultError("requested seal mismatch")
            found = self._find(data, records)
            if mode == "reconcile":
                return None if found is None else self._receipt(request, found, records, raw, "DURABILITY_UNPROVEN")
            self._eligible(seals, records, request.hypothesis_id, request.window_id)
            if mode == "recover":
                if found is None:
                    raise VaultError("same consumption is absent; recovery cannot append")
                fd = os.open(self.peeklog_path.name, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
                try:
                    _same_path(directory, self.peeklog_path.name, fd)
                    os.fsync(fd)
                    os.fsync(directory)
                    _same_path(directory, self.peeklog_path.name, fd)
                finally:
                    os.close(fd)
                state = "DURABLE_RECONCILED"
            elif found is not None:
                return self._receipt(request, found, records, raw, "DURABILITY_UNPROVEN")
            else:
                found, raw = self._append(directory, {"kind": "peek", "hypothesis_id": request.hypothesis_id,
                    "window_id": request.window_id, "window_hash": request.seal_sha256, "result": None,
                    "commit": None, "consumption_request": data}, seals, records, raw)
                state = "DURABLE_CONSUMED"
            check()
            loaded, records, raw = self._cold_adopt(directory, raw, anchor=anchor)
            if self._find(data, records) != found:
                raise VaultError("consumption cold readback mismatch")
            receipt = self._receipt(request, found, records, raw, state)
        self._adopt(loaded, records)
        return receipt

    @_serialized
    def consume_authorization(self, request, *, history_anchor):
        """Spend once. Existing exact requests return DURABILITY_UNPROVEN, not a grant."""
        return self._consumption(request, history_anchor, mode="consume")

    @_serialized
    def reconcile_consumption(self, request, *, history_anchor):
        """Read only; an existing row does not prove durability or permit labels."""
        return self._consumption(request, history_anchor, mode="reconcile")

    @_serialized
    def recover_consumption(self, request, *, history_anchor):
        """Explicit same-ID sync and cold readback; never append or recharge."""
        return self._consumption(request, history_anchor, mode="recover")


__all__ = ["HoldoutVault", "VaultError", "VaultHistoryAnchor", "VaultConsumptionRequest", "VaultConsumptionReceipt"]
