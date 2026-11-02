"""Durable, bounded reservation accounting for the existing E0 study owner.

This is storage, not admission. Paths, Python objects and matching hashes do not
grant permission. The installed caller must authorize every access, including
cached disclosure, and create the private directory. Only NEW identifies the
first reservation; a pending operation must never be replayed or refunded.

Like the existing Market Memory stores, use a directory flock and immutable
records selected by an atomic head. Journal events, rather than cumulative
snapshots, keep validation linear in at most 2,049 small records. Result bytes
are checked only when explicitly read; snapshot/reserve do not disclose them.
An orphan or partial publication is retained and refuses further access. This
module intentionally has no repair, cancellation or implicit initialization API.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

MAX_LOOKS = 1024
MAX_RESULT_BYTES = 1024 * 1024
MAX_INTENT_BYTES = 64 * 1024
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_HASH = re.compile(r"[a-f0-9]{64}")
_SCHEMA = "research_factory.market_memory_e0_reservations.v1"
_BINDING_IDS = {"study_id", "installation_id", "installation_epoch"}
_BINDING_HASHES = {"registration_sha256", "publication_sha256"}


class ReservationError(ValueError):
    """Stable reason only; never include caller data or result bytes."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ReservationError(reason)


def _identifier(value: object) -> str:
    _require(type(value) is str and _ID.fullmatch(value) is not None, "invalid_identifier")
    return value


def _digest(value: object) -> str:
    _require(type(value) is str and _HASH.fullmatch(value) is not None, "invalid_digest")
    return value


def _canonical(value: object, limit: int = MAX_INTENT_BYTES) -> bytes:
    active: set[int] = set()
    nodes = 0

    def visit(item: object, depth: int) -> None:
        nonlocal nodes
        nodes += 1
        _require(nodes <= 4096 and depth <= 16, "json_complexity_limit")
        if item is None or type(item) in (bool, int):
            return
        if type(item) is str:
            _require(len(item) <= limit, "json_byte_limit")
            return
        if type(item) is float:
            _require(math.isfinite(item), "nonfinite_number")
            return
        _require(type(item) in (dict, list), "exact_json_types_required")
        _require(id(item) not in active, "cyclic_json")
        active.add(id(item))
        if type(item) is dict:
            for key, child in item.items():
                _require(type(key) is str, "exact_string_keys_required")
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            for child in item:
                visit(child, depth + 1)
        active.remove(id(item))

    visit(value, 0)
    try:
        body = json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, OverflowError) as exc:
        raise ReservationError("invalid_json") from exc
    _require(len(body) <= limit, "json_byte_limit")
    return body


def _parse(body: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    try:
        value = json.loads(body, object_pairs_hook=pairs)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ReservationError("invalid_persisted_json") from exc
    _require(type(value) is dict, "persisted_object_required")
    _require(_canonical(value, 8192) == body, "noncanonical_persisted_json")
    return value


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _private(info, *, directory=False) -> None:
    kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    _require(kind and info.st_uid == os.geteuid()
             and stat.S_IMODE(info.st_mode) == (0o700 if directory else 0o600)
             and (directory or info.st_nlink == 1), "unsafe_storage_object")


def _same_object(left, right) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


class ReservationStore:
    """One private study namespace. Construction performs no I/O or admission."""

    def __init__(self, directory: str | Path, binding: dict):
        _require(type(binding) is dict
                 and set(binding) == _BINDING_IDS | _BINDING_HASHES, "invalid_binding")
        for key in _BINDING_IDS:
            _identifier(binding[key])
        for key in _BINDING_HASHES:
            _digest(binding[key])
        self._binding_bytes = _canonical(binding)
        self.directory = Path(directory)

    @property
    def binding(self) -> dict:
        return json.loads(self._binding_bytes)

    def _check_directory(self, fd: int) -> None:
        held = os.fstat(fd)
        named = os.stat(self.directory, follow_symlinks=False)
        _private(held, directory=True)
        _private(named, directory=True)
        _require(_same_object(held, named), "directory_identity_changed")

    @contextmanager
    def _locked(self):
        fd = None
        try:
            fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            self._check_directory(fd)
            fcntl.flock(fd, fcntl.LOCK_EX)
            self._check_directory(fd)
            yield fd
            self._check_directory(fd)
        except OSError as exc:
            # May represent an uncertain publication. Preserve every byte.
            raise ReservationError("storage_io_failure") from exc
        finally:
            if fd is not None:
                os.close(fd)  # also releases the directory lock

    def _read(self, fd: int, name: str, limit: int) -> bytes:
        opened = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=fd)
        try:
            before = os.fstat(opened)
            _private(before)
            _require(0 < before.st_size <= limit, "storage_byte_limit")
            chunks = []
            remaining = limit + 1
            while remaining:
                chunk = os.read(opened, min(remaining, 65536))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            after = os.fstat(opened)
            named = os.stat(name, dir_fd=fd, follow_symlinks=False)
            _private(after)
            _private(named)
            _require(_same_object(before, named)
                     and before.st_size == after.st_size
                     and before.st_mtime_ns == after.st_mtime_ns
                     and before.st_ctime_ns == after.st_ctime_ns, "storage_changed_during_read")
            body = b"".join(chunks)
            _require(len(body) == before.st_size and len(body) <= limit, "storage_byte_limit")
            return body
        finally:
            os.close(opened)

    def _write_new(self, fd: int, name: str, body: bytes) -> None:
        opened = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                         0o600, dir_fd=fd)
        try:
            _private(os.fstat(opened))
            view = memoryview(body)
            while view:
                size = os.write(opened, view)
                _require(size > 0, "short_storage_write")
                view = view[size:]
            os.fsync(opened)
        finally:
            os.close(opened)

    def _names(self, fd: int) -> set[str]:
        names = set()
        with os.scandir(fd) as entries:
            for entry in entries:
                names.add(entry.name)
                _require(len(names) <= 3 * MAX_LOOKS + 3, "storage_entry_limit")
        return names

    def _load(self, fd: int) -> dict | None:
        names = self._names(fd)
        if not names:
            return None
        _require("HEAD.json" in names and "HEAD.next" not in names, "uncertain_publication")
        head = _parse(self._read(fd, "HEAD.json", 8192))
        _require(set(head) == {"sequence", "sha256"}, "invalid_head")
        sequence = head["sequence"]
        _require(type(sequence) is int and 0 <= sequence <= 2 * MAX_LOOKS, "invalid_sequence")
        _digest(head["sha256"])
        previous = None
        operations = {}
        expected = {"HEAD.json"}
        maximum = None
        for index in range(sequence + 1):
            name = f"event-{index:04d}.json"
            expected.add(name)
            body = self._read(fd, name, 8192)
            event = _parse(body)
            common = {"schema", "sequence", "previous", "action"}
            _require(event.get("schema") == _SCHEMA
                     and type(event.get("sequence")) is int and event["sequence"] == index
                     and event.get("previous") == previous, "invalid_event_chain")
            action = event.get("action")
            if index == 0:
                _require(set(event) == common | {"binding", "maximum_looks"}
                         and action == "initialize", "invalid_initial_event")
                _require(_canonical(event["binding"]) == self._binding_bytes, "binding_conflict")
                maximum = event["maximum_looks"]
                _require(type(maximum) is int and 1 <= maximum <= MAX_LOOKS, "invalid_maximum_looks")
            else:
                _require(action in ("reserve", "finish"), "invalid_event_action")
                keys = common | {"operation_id", "intent_sha256"}
                if action == "finish":
                    keys |= {"result"}
                _require(set(event) == keys, "invalid_event_fields")
                op = _identifier(event["operation_id"])
                intent = _digest(event["intent_sha256"])
                if action == "reserve":
                    _require(op not in operations and len(operations) < maximum, "invalid_reservation_history")
                    operations[op] = {"operation_id": op, "intent_sha256": intent, "result": None}
                else:
                    _require(op in operations and operations[op]["intent_sha256"] == intent
                             and operations[op]["result"] is None, "invalid_completion_history")
                    result = event["result"]
                    _require(type(result) is dict and set(result) == {"sha256", "bytes"}, "invalid_result_reference")
                    _digest(result["sha256"])
                    _require(type(result["bytes"]) is int
                             and 1 <= result["bytes"] <= MAX_RESULT_BYTES, "invalid_result_reference")
                    result_name = self._result_name(op)
                    expected.add(result_name)
                    info = os.stat(result_name, dir_fd=fd, follow_symlinks=False)
                    _private(info)
                    _require(info.st_size == result["bytes"], "result_size_mismatch")
                    operations[op]["result"] = result
            previous = _sha(body)
        _require(previous == head["sha256"], "head_digest_mismatch")
        _require(names == expected, "uncertain_publication")
        return {"sequence": sequence, "sha256": previous, "maximum_looks": maximum,
                "operations": operations}

    def _publish(self, fd: int, state: dict | None, fields: dict) -> None:
        self._check_directory(fd)
        sequence = 0 if state is None else state["sequence"] + 1
        event = {"schema": _SCHEMA, "sequence": sequence,
                 "previous": None if state is None else state["sha256"], **fields}
        body = _canonical(event, 8192)
        self._write_new(fd, f"event-{sequence:04d}.json", body)
        os.fsync(fd)
        self._write_new(fd, "HEAD.next", _canonical({"sequence": sequence, "sha256": _sha(body)}))
        self._check_directory(fd)
        os.replace("HEAD.next", "HEAD.json", src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
        self._check_directory(fd)

    @staticmethod
    def _result_name(operation_id: str) -> str:
        return "result-" + _sha(operation_id.encode("ascii")) + ".bin"

    @staticmethod
    def _intent(intent: dict) -> str:
        _require(type(intent) is dict, "intent_object_required")
        return _sha(_canonical(intent))

    @staticmethod
    def _operation(state: dict, operation_id: str, digest: str) -> dict | None:
        op = state["operations"].get(operation_id)
        _require(op is None or op["intent_sha256"] == digest, "operation_intent_conflict")
        return op

    def initialize(self, maximum_looks: int) -> dict:
        _require(type(maximum_looks) is int and 1 <= maximum_looks <= MAX_LOOKS, "invalid_maximum_looks")
        with self._locked() as fd:
            state = self._load(fd)
            if state is None:
                self._publish(fd, None, {"action": "initialize", "binding": self.binding,
                                         "maximum_looks": maximum_looks})
                state = self._load(fd)
            _require(state["maximum_looks"] == maximum_looks, "initialization_conflict")
            return self._snapshot(state)

    def reserve(self, operation_id: str, intent: dict) -> dict:
        op_id, digest = _identifier(operation_id), self._intent(intent)
        with self._locked() as fd:
            state = self._load(fd)
            _require(state is not None, "uninitialized_store")
            op = self._operation(state, op_id, digest)
            if op is None:
                _require(len(state["operations"]) < state["maximum_looks"], "look_budget_exhausted")
                self._publish(fd, state, {"action": "reserve", "operation_id": op_id,
                                          "intent_sha256": digest})
                state = self._load(fd)
                status = "NEW"
            else:
                status = "COMPLETE" if op["result"] is not None else "EXISTING_PENDING"
            return {"status": status, "binding": self.binding, "sequence": state["sequence"],
                    **state["operations"][op_id]}

    def finish(self, operation_id: str, intent: dict, result_bytes: bytes) -> dict:
        op_id, digest = _identifier(operation_id), self._intent(intent)
        _require(type(result_bytes) is bytes and 1 <= len(result_bytes) <= MAX_RESULT_BYTES,
                 "bounded_result_bytes_required")
        ref = {"sha256": _sha(result_bytes), "bytes": len(result_bytes)}
        with self._locked() as fd:
            state = self._load(fd)
            _require(state is not None, "uninitialized_store")
            op = self._operation(state, op_id, digest)
            _require(op is not None, "reservation_required")
            if op["result"] is None:
                self._write_new(fd, self._result_name(op_id), result_bytes)
                os.fsync(fd)
                self._publish(fd, state, {"action": "finish", "operation_id": op_id,
                                          "intent_sha256": digest, "result": ref})
                state = self._load(fd)
            else:
                _require(op["result"] == ref, "result_conflict")
                _require(self._read(fd, self._result_name(op_id), MAX_RESULT_BYTES) == result_bytes,
                         "result_digest_mismatch")
            return {"status": "COMPLETE", "binding": self.binding, "sequence": state["sequence"],
                    **state["operations"][op_id]}

    def read_completed(self, operation_id: str, intent: dict) -> bytes:
        op_id, digest = _identifier(operation_id), self._intent(intent)
        with self._locked() as fd:
            state = self._load(fd)
            _require(state is not None, "uninitialized_store")
            op = self._operation(state, op_id, digest)
            _require(op is not None and op["result"] is not None, "completed_result_unavailable")
            body = self._read(fd, self._result_name(op_id), MAX_RESULT_BYTES)
            _require(len(body) == op["result"]["bytes"] and _sha(body) == op["result"]["sha256"],
                     "result_digest_mismatch")
            return body

    def _snapshot(self, state: dict) -> dict:
        consumed = sum(op["result"] is not None for op in state["operations"].values())
        return {"binding": self.binding, "sequence": state["sequence"],
                "maximum_looks": state["maximum_looks"], "consumed_looks": consumed,
                "reserved_looks": len(state["operations"]) - consumed}

    def snapshot(self) -> dict:
        with self._locked() as fd:
            state = self._load(fd)
            _require(state is not None, "uninitialized_store")
            return self._snapshot(state)
