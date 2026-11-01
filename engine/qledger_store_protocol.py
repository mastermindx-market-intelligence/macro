"""Inactive QLedger storage protocol; explicit immutable inputs, no filesystem I/O.

No production reader imports this module. These codecs and pure planners do not
discover a root, activate a format, prepare claims, authorize a rewrite, start a
clock, materialize members, or stage/commit/push anything. InMemorySource proves
only an immutable in-memory snapshot. A future Git/local adapter must separately
prove its snapshot and inventory bindings.

A replacement changes the active byte view and retains all prior raw members.
The native regime backfill, not this module, owns its parsed-row transformation.
Storage transaction retry identity does not deduplicate business occurrences.
Verification retains referenced immutable bytes in memory; this implementation
does not claim a memory/performance improvement or production capacity.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import wraps
from hashlib import sha256
import io
import json
import re
from types import MappingProxyType
from typing import Any, BinaryIO, Iterable, Mapping, Protocol

BASE_PATH = "data/qledger/claims.jsonl"
ROOT_PATH = "data/qledger/claims.root.json"
PART_PREFIX = "data/qledger/claims.parts/"
PAGE_PREFIX = "data/qledger/claims.catalog/"
ROOT_FORMAT = "qledger-parts/v1"
PAGE_FORMAT = "qledger-page/v1"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_TXID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_SEAL = object()


class SnapshotIntegrityError(RuntimeError):
    """No successful claims value is available from this storage failure."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


def _fail(code: str, message: str) -> None:
    raise SnapshotIntegrityError(code, message)


def _typed(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except SnapshotIntegrityError:
            raise
        except Exception as exc:
            raise SnapshotIntegrityError(
                "MALFORMED", f"{function.__name__}: {type(exc).__name__}"
            ) from exc

    return checked


# Hard supported ceilings. A supplied fixture profile can only narrow them.
_CEILINGS = {
    "base_bytes": 96 * 1024 * 1024,
    "part_bytes": 64 * 1024 * 1024,
    "page_bytes": 1024 * 1024,
    "root_bytes": 16 * 1024,
    "descriptor_bytes": 4 * 1024,
    "leaf_entries": 128,
    "fanout": 128,
    "index_levels": 3,
    "history_operations": 65536,
    "reference_visits": 262144,
    "snapshot_members": 65536,
    "snapshot_bytes": 512 * 1024 * 1024,
    "logical_bytes": 512 * 1024 * 1024,
    "input_rows": 1048576,
    "publication_objects": 1048576,
    "git_blob_bytes": 96 * 1024 * 1024,
}


@dataclass(frozen=True)
class ProtocolLimits:
    """Finite supported profile; actual production base fit is unestablished."""

    base_bytes: int = _CEILINGS["base_bytes"]
    part_bytes: int = _CEILINGS["part_bytes"]
    page_bytes: int = _CEILINGS["page_bytes"]
    root_bytes: int = _CEILINGS["root_bytes"]
    descriptor_bytes: int = _CEILINGS["descriptor_bytes"]
    leaf_entries: int = _CEILINGS["leaf_entries"]
    fanout: int = _CEILINGS["fanout"]
    index_levels: int = _CEILINGS["index_levels"]
    history_operations: int = _CEILINGS["history_operations"]
    reference_visits: int = _CEILINGS["reference_visits"]
    snapshot_members: int = _CEILINGS["snapshot_members"]
    snapshot_bytes: int = _CEILINGS["snapshot_bytes"]
    logical_bytes: int = _CEILINGS["logical_bytes"]
    input_rows: int = _CEILINGS["input_rows"]
    publication_objects: int = _CEILINGS["publication_objects"]
    git_blob_bytes: int = _CEILINGS["git_blob_bytes"]

    def __post_init__(self):
        for name, value in asdict(self).items():
            minimum = 0 if name in {"base_bytes", "index_levels"} else 1
            if name == "fanout":
                minimum = 2
            if type(value) is not int or not minimum <= value <= _CEILINGS[name]:
                _fail("LIMIT", f"unsupported profile field {name}")

    @property
    def fingerprint(self) -> str:
        return _digest(_json(asdict(self)))

    @property
    def tree_capacity(self) -> int:
        return self.leaf_entries * self.fanout**self.index_levels


@dataclass(frozen=True)
class MemberRef:
    path: str
    digest: str
    size: int


@dataclass(frozen=True)
class TreeRef:
    member: MemberRef
    kind: str
    height: int
    start: int
    count: int


@dataclass(frozen=True)
class RootRecord:
    base: MemberRef
    catalog: TreeRef | None
    operation_count: int
    logical_size: int
    logical_digest: str
    limits_digest: str


@dataclass(frozen=True)
class StorageTransaction:
    transaction_id: str
    kind: str
    extents: TreeRef | None
    payload_size: int
    payload_digest: str
    expected_view_digest: str | None = None

    @property
    def digest(self) -> str:
        return _digest(_json(_transaction_obj(self)))


class PinnedSource(Protocol):
    """The owner supplies one immutable identity and a complete member inventory.

    There is no Git or locked-local implementation in this module. The verifier
    also retains verified member bytes so successful consumption never rereads a
    potentially changing external source. Inventory extraction remains separate.
    """

    @property
    def snapshot_id(self) -> str: ...

    def read_member(self, path: str) -> bytes: ...

    def iter_members(self) -> Iterable[MemberRef]: ...


@dataclass(frozen=True, init=False)
class InMemorySource:
    """An immutable copy of an explicit mapping; never reads a real path."""

    snapshot_id: str
    _members: Mapping[str, bytes] = field(repr=False)

    @_typed
    def __init__(self, members: Mapping[str, bytes], *, snapshot_id: str):
        _source_id(snapshot_id)
        copied = {}
        for path, payload in members.items():
            if type(path) is not str or type(payload) is not bytes:
                _fail("MALFORMED", "source members require string paths and bytes")
            copied[path] = payload
        object.__setattr__(self, "snapshot_id", snapshot_id)
        object.__setattr__(self, "_members", MappingProxyType(copied))

    def read_member(self, path: str) -> bytes:
        try:
            return self._members[path]
        except KeyError as exc:
            raise SnapshotIntegrityError("MISSING", f"missing member {path}") from exc

    def iter_members(self) -> Iterable[MemberRef]:
        return tuple(_member(path, value) for path, value in self._members.items())


@dataclass(frozen=True)
class IntegrityReceipt:
    source_id: str
    root_digest: str
    member_count: int
    retained_bytes: int
    reference_visits: int
    operation_count: int
    logical_size: int
    logical_digest: str
    complete: bool = True
    scope: str = "provided-root-and-all-referenced-members"


@dataclass(frozen=True, init=False)
class VerifiedSnapshot:
    root: RootRecord
    root_bytes: bytes
    receipt: IntegrityReceipt
    _members: Mapping[str, bytes] = field(repr=False)
    _transactions: tuple[StorageTransaction, ...] = field(repr=False)
    _active: tuple[MemberRef, ...] = field(repr=False)
    _limits: ProtocolLimits = field(repr=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *args, **kwargs):
        _fail("INCOMPLETE", "verify_snapshot must construct verified results")


@dataclass(frozen=True, init=False)
class PublicationPlan:
    """A verified candidate description, never a materialized/publication effect."""

    expected_root_digest: str
    snapshot: VerifiedSnapshot
    members: Mapping[str, bytes]
    transaction: StorageTransaction | None
    reason: str
    _before: VerifiedSnapshot = field(repr=False)
    _seal: object = field(default=None, repr=False, compare=False)

    def __init__(self, *args, **kwargs):
        _fail("MALFORMED", "a protocol planner must construct publication plans")

    @property
    def root_bytes(self) -> bytes:
        return self.snapshot.root_bytes

    @property
    def is_noop(self) -> bool:
        return self.transaction is None


@dataclass(frozen=True)
class RebasePlan:
    expected_remote_root_digest: str
    snapshot: VerifiedSnapshot
    members: Mapping[str, bytes]
    applied: tuple[str, ...]
    already_applied: tuple[str, ...]


@dataclass(frozen=True)
class BlobInfo:
    """Owner-supplied newly reachable Git-object metadata; no extraction here."""

    object_id: str
    size: int


@dataclass(frozen=True)
class PublicationCheck:
    source_id: str
    root_digest: str
    candidate_members: int
    introduced_blobs: int
    accepted: bool = True
    retryable: bool = False
    scope: str = "provided-candidate-inventory-and-introduced-blob-inventory"


def _sealed_result(cls, **values):
    # Opaque result construction also prevents dataclasses.replace from silently
    # attaching an earlier verification seal to changed data or transactions.
    if cls not in (VerifiedSnapshot, PublicationPlan):
        _fail("MALFORMED", "unsupported sealed result type")
    if set(values) != set(cls.__dataclass_fields__) - {"_seal"}:
        _fail("MALFORMED", "incomplete sealed result")
    result = object.__new__(cls)
    for name, value in values.items():
        object.__setattr__(result, name, value)
    object.__setattr__(result, "_seal", _SEAL)
    return result


def _digest(payload: bytes) -> str:
    return sha256(payload).hexdigest()


def _json(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _source_id(value: Any) -> str:
    if type(value) is not str or not 1 <= len(value) <= 256:
        _fail("MALFORMED", "invalid immutable source identity")
    if any(ord(c) < 33 or ord(c) > 126 for c in value):
        _fail("MALFORMED", "invalid immutable source identity")
    return value


def _integer(value: Any, maximum: int, label: str, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        _fail("LIMIT", f"invalid {label}")
    return value


def _hash(value: Any) -> str:
    if type(value) is not str or not _HEX.fullmatch(value):
        _fail("MALFORMED", "invalid digest")
    return value


def _keys(value: Any, names: set[str]) -> dict:
    if type(value) is not dict or set(value) != names:
        _fail("MALFORMED", "unknown or missing metadata fields")
    return value


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            _fail("MALFORMED", "duplicate metadata key")
        value[key] = item
    return value


def _no_number(value):
    _fail("MALFORMED", "non-integer metadata number")


def _decode(payload: bytes, maximum: int) -> dict:
    if type(payload) is not bytes:
        _fail("MALFORMED", "metadata is not bytes")
    if not payload or len(payload) > maximum:
        _fail("LIMIT", "metadata byte limit")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_pairs,
            parse_float=_no_number,
            parse_constant=_no_number,
        )
    except SnapshotIntegrityError:
        raise
    except Exception as exc:
        raise SnapshotIntegrityError("MALFORMED", "invalid metadata encoding/JSON") from exc
    if type(value) is not dict:
        _fail("MALFORMED", "metadata must be an object")
    if _json(value) != payload:
        _fail("MALFORMED", "metadata is not canonically encoded")
    return value


def _member(path: str, payload: bytes) -> MemberRef:
    return MemberRef(path, _digest(payload), len(payload))


def _member_obj(ref: MemberRef) -> dict:
    return {"path": ref.path, "digest": ref.digest, "size": ref.size}


def _read_member_ref(value: Any, kind: str, limits: ProtocolLimits) -> MemberRef:
    obj = _keys(value, {"path", "digest", "size"})
    digest = _hash(obj["digest"])
    path = obj["path"]
    if kind == "base":
        expected, maximum, minimum = BASE_PATH, limits.base_bytes, 0
    elif kind == "root":
        expected, maximum, minimum = ROOT_PATH, limits.root_bytes, 1
        if type(path) is not str:
            _fail("MALFORMED", "root member path must be an exact string")
    elif kind == "part":
        expected, maximum, minimum = PART_PREFIX + digest + ".jsonl", limits.part_bytes, 1
    elif kind == "page":
        expected, maximum, minimum = PAGE_PREFIX + digest + ".json", limits.page_bytes, 1
    else:
        _fail("MALFORMED", "unknown member kind")
    if path != expected:
        _fail("MALFORMED", "unsafe or noncanonical member path")
    return MemberRef(path, digest, _integer(obj["size"], maximum, "member size", minimum))


def _tree_obj(ref: TreeRef | None):
    if ref is None:
        return None
    return {
        "member": _member_obj(ref.member), "kind": ref.kind,
        "height": ref.height, "start": ref.start, "count": ref.count,
    }


def _read_tree_ref(value: Any, kind: str, limits: ProtocolLimits) -> TreeRef | None:
    if value is None:
        return None
    obj = _keys(value, {"member", "kind", "height", "start", "count"})
    if obj["kind"] != kind:
        _fail("MALFORMED", "tree kind mismatch")
    height = _integer(obj["height"], limits.index_levels, "index height")
    count = _integer(
        obj["count"], min(limits.reference_visits, limits.leaf_entries * limits.fanout**height),
        "tree count", 1,
    )
    start = _integer(obj["start"], limits.reference_visits, "tree start")
    if start + count > limits.reference_visits:
        _fail("LIMIT", "tree range exceeds supported references")
    return TreeRef(_read_member_ref(obj["member"], "page", limits), kind, height, start, count)


def _transaction_obj(tx: StorageTransaction) -> dict:
    return {
        "transaction_id": tx.transaction_id, "kind": tx.kind,
        "extents": _tree_obj(tx.extents), "payload_size": tx.payload_size,
        "payload_digest": tx.payload_digest, "expected_view_digest": tx.expected_view_digest,
    }


def _transaction(value: Any, limits: ProtocolLimits) -> StorageTransaction:
    obj = _keys(value, {
        "transaction_id", "kind", "extents", "payload_size",
        "payload_digest", "expected_view_digest",
    })
    if len(_json(obj)) > limits.descriptor_bytes:
        _fail("LIMIT", "transaction descriptor byte limit")
    txid = obj["transaction_id"]
    if type(txid) is not str or not _TXID.fullmatch(txid):
        _fail("MALFORMED", "invalid storage transaction identity")
    kind = obj["kind"]
    if kind not in {"append", "replace"}:
        _fail("VERSION", "unsupported storage operation")
    extents = _read_tree_ref(obj["extents"], "extents", limits)
    if extents is not None and extents.start != 0:
        _fail("INCOMPLETE", "extent root must start at zero")
    size = _integer(obj["payload_size"], limits.logical_bytes, "payload size")
    digest = _hash(obj["payload_digest"])
    expected = obj["expected_view_digest"]
    if kind == "append":
        if expected is not None or size == 0 or extents is None:
            _fail("MALFORMED", "invalid append operation")
    else:
        _hash(expected)
        if (size == 0) != (extents is None):
            _fail("INCOMPLETE", "empty replacement extent mismatch")
    if size == 0 and digest != _digest(b""):
        _fail("HASH_MISMATCH", "empty replacement digest")
    return StorageTransaction(txid, kind, extents, size, digest, expected)


def _root_obj(root: RootRecord) -> dict:
    return {
        "format": ROOT_FORMAT, "base": _member_obj(root.base),
        "catalog": _tree_obj(root.catalog), "operation_count": root.operation_count,
        "logical_size": root.logical_size, "logical_digest": root.logical_digest,
        "limits_digest": root.limits_digest,
    }


@_typed
def decode_root(payload: bytes, *, limits: ProtocolLimits) -> RootRecord:
    obj = _keys(_decode(payload, limits.root_bytes), {
        "format", "base", "catalog", "operation_count", "logical_size",
        "logical_digest", "limits_digest",
    })
    if obj["format"] != ROOT_FORMAT:
        _fail("VERSION", "unsupported root format")
    if obj["limits_digest"] != limits.fingerprint:
        _fail("LIMIT", "root profile does not match the supplied supported limits")
    base = _read_member_ref(obj["base"], "base", limits)
    catalog = _read_tree_ref(obj["catalog"], "catalog", limits)
    count = _integer(
        obj["operation_count"], min(limits.history_operations, limits.tree_capacity),
        "history operation count",
    )
    if (count == 0) != (catalog is None):
        _fail("INCOMPLETE", "catalog/count mismatch")
    if catalog is not None and (catalog.start != 0 or catalog.count != count):
        _fail("INCOMPLETE", "catalog root range mismatch")
    size = _integer(obj["logical_size"], limits.logical_bytes, "logical size")
    return RootRecord(base, catalog, count, size, _hash(obj["logical_digest"]), limits.fingerprint)


@_typed
def encode_root(root: RootRecord, *, limits: ProtocolLimits) -> bytes:
    payload = _json(_root_obj(root))
    decode_root(payload, limits=limits)
    return payload


class _Verifier:
    def __init__(self, source: PinnedSource, limits: ProtocolLimits, root_size: int):
        self.source = source
        self.source_id = _source_id(source.snapshot_id)
        self.limits = limits
        self.loaded: dict[str, bytes] = {}
        self.refs: dict[str, MemberRef] = {}
        self.visits = 0
        self.total = root_size
        self.stack: set[str] = set()

    def read(self, ref: MemberRef) -> bytes:
        self.visits += 1
        if self.visits > self.limits.reference_visits:
            _fail("LIMIT", "reference-visit budget")
        if self.source.snapshot_id != self.source_id:
            _fail("SOURCE_CHANGED", "source identity changed during verification")
        if ref.path in self.loaded:
            if self.refs[ref.path] != ref:
                _fail("CONFLICT", "same member path has conflicting identities")
            return self.loaded[ref.path]
        if len(self.loaded) >= self.limits.snapshot_members:
            _fail("LIMIT", "snapshot member budget")
        if self.total + ref.size > self.limits.snapshot_bytes:
            _fail("LIMIT", "retained snapshot byte budget")
        try:
            payload = self.source.read_member(ref.path)
        except SnapshotIntegrityError:
            raise
        except Exception as exc:
            raise SnapshotIntegrityError("MISSING", "source member is unavailable") from exc
        if type(payload) is not bytes:
            _fail("MALFORMED", "source returned mutable or non-byte member")
        if len(payload) != ref.size or _digest(payload) != ref.digest:
            _fail("HASH_MISMATCH", f"member identity mismatch {ref.path}")
        self.loaded[ref.path] = payload
        self.refs[ref.path] = ref
        self.total += ref.size
        return payload

    def tree(self, ref: TreeRef | None, kind: str) -> list[Any]:
        if ref is None:
            return []
        if ref.member.path in self.stack:
            _fail("INCOMPLETE", "catalog cycle")
        self.stack.add(ref.member.path)
        try:
            obj = _keys(_decode(self.read(ref.member), self.limits.page_bytes), {
                "format", "kind", "height", "entries",
            })
            page_height = _integer(obj["height"], self.limits.index_levels, "page height")
            if obj["format"] != PAGE_FORMAT or obj["kind"] != kind or page_height != ref.height:
                _fail("VERSION", "page/ref type or height mismatch")
            entries = obj["entries"]
            maximum = self.limits.leaf_entries if ref.height == 0 else self.limits.fanout
            if type(entries) is not list or not 1 <= len(entries) <= maximum:
                _fail("LIMIT", "page entry limit")
            result = []
            cursor = ref.start
            if ref.height == 0:
                for entry in entries:
                    value = _keys(entry, {"ordinal", "value"})
                    if type(value["ordinal"]) is not int or value["ordinal"] != cursor:
                        _fail("INCOMPLETE", "reordered or missing leaf ordinal")
                    parsed = (
                        _transaction(value["value"], self.limits)
                        if kind == "catalog"
                        else _read_member_ref(value["value"], "part", self.limits)
                    )
                    result.append(parsed)
                    cursor += 1
            else:
                for entry in entries:
                    child = _read_tree_ref(entry, kind, self.limits)
                    if child is None or child.height != ref.height - 1 or child.start != cursor:
                        _fail("INCOMPLETE", "reordered or incomplete index range")
                    result.extend(self.tree(child, kind))
                    cursor += child.count
            if cursor != ref.start + ref.count:
                _fail("INCOMPLETE", "page/ref count mismatch")
            return result
        finally:
            self.stack.remove(ref.member.path)


@_typed
def verify_snapshot(
    source: PinnedSource, root: RootRecord, *, limits: ProtocolLimits
) -> VerifiedSnapshot:
    root_bytes = encode_root(root, limits=limits)
    root = decode_root(root_bytes, limits=limits)
    verifier = _Verifier(source, limits, len(root_bytes))
    base = verifier.read(root.base)
    transactions = tuple(verifier.tree(root.catalog, "catalog"))
    if len(transactions) != root.operation_count:
        _fail("INCOMPLETE", "operation count mismatch")
    active = [root.base]
    view_hash = sha256(base)
    view_size = len(base)
    ids: set[str] = set()
    for tx in transactions:
        if tx.transaction_id in ids:
            _fail("CONFLICT", "repeated storage transaction identity in accepted catalog")
        ids.add(tx.transaction_id)
        parts = tuple(verifier.tree(tx.extents, "extents"))
        payload_hash = sha256()
        payload_size = 0
        for part in parts:
            data = verifier.read(part)
            if not data.endswith(b"\n"):
                _fail("INCOMPLETE", "continuation part is not LF terminated")
            payload_hash.update(data)
            payload_size += len(data)
        if payload_size != tx.payload_size or payload_hash.hexdigest() != tx.payload_digest:
            _fail("HASH_MISMATCH", "transaction payload identity mismatch")
        if tx.kind == "replace":
            if tx.expected_view_digest != view_hash.hexdigest():
                _fail("CONFLICT", "replacement targets a stale logical view")
            active = list(parts)
            view_hash = payload_hash
            view_size = payload_size
        else:
            for part in parts:
                view_hash.update(verifier.loaded[part.path])
            active.extend(parts)
            view_size += payload_size
        if view_size > limits.logical_bytes or len(active) > limits.reference_visits:
            _fail("LIMIT", "active logical view budget")
    if view_size != root.logical_size or view_hash.hexdigest() != root.logical_digest:
        _fail("HASH_MISMATCH", "root logical-view identity mismatch")
    if source.snapshot_id != verifier.source_id:
        _fail("SOURCE_CHANGED", "source identity changed during verification")
    receipt = IntegrityReceipt(
        verifier.source_id, _digest(root_bytes), len(verifier.loaded), verifier.total,
        verifier.visits, len(transactions), view_size, view_hash.hexdigest(),
    )
    return _sealed_result(
        VerifiedSnapshot, root=root, root_bytes=root_bytes, receipt=receipt,
        _members=MappingProxyType(dict(verifier.loaded)), _transactions=transactions,
        _active=tuple(active), _limits=limits,
    )


def _verified(snapshot: VerifiedSnapshot, limits: ProtocolLimits | None = None) -> None:
    if not isinstance(snapshot, VerifiedSnapshot) or snapshot._seal is not _SEAL:
        _fail("INCOMPLETE", "a verified snapshot is required")
    if limits is not None and snapshot._limits != limits:
        _fail("LIMIT", "snapshot/profile mismatch")


class _ByteView(io.RawIOBase):
    def __init__(self, chunks: tuple[bytes, ...]):
        super().__init__()
        self._chunks = chunks
        self._index = 0
        self._offset = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        self._checkClosed()
        target = memoryview(buffer).cast("B")
        written = 0
        while written < len(target) and self._index < len(self._chunks):
            chunk = self._chunks[self._index]
            count = min(len(target) - written, len(chunk) - self._offset)
            target[written : written + count] = chunk[self._offset : self._offset + count]
            written += count
            self._offset += count
            if self._offset == len(chunk):
                self._index += 1
                self._offset = 0
        return written


@_typed
def open_logical_bytes(snapshot: VerifiedSnapshot) -> BinaryIO:
    """Return a closing binary view over retained verified bytes, never a reread."""
    _verified(snapshot)
    return io.BufferedReader(_ByteView(tuple(snapshot._members[r.path] for r in snapshot._active)))


class _Builder:
    def __init__(self, existing: Mapping[str, bytes], limits: ProtocolLimits):
        self.existing = existing
        self.limits = limits
        self.new: dict[str, bytes] = {}

    def add(self, payload: bytes, kind: str) -> MemberRef:
        maximum = self.limits.part_bytes if kind == "part" else self.limits.page_bytes
        if not payload or len(payload) > maximum:
            _fail("CAPACITY", f"{kind} byte capacity")
        digest = _digest(payload)
        path = (PART_PREFIX + digest + ".jsonl") if kind == "part" else (PAGE_PREFIX + digest + ".json")
        if path in self.existing:
            if self.existing[path] != payload:
                _fail("CONFLICT", "immutable member would be replaced")
        elif path in self.new and self.new[path] != payload:
            _fail("CONFLICT", "conflicting planned member")
        else:
            self.new[path] = payload
        return MemberRef(path, digest, len(payload))

    def page(self, kind: str, height: int, entries: list[Any]) -> TreeRef:
        payload = _json({"format": PAGE_FORMAT, "kind": kind, "height": height, "entries": entries})
        ref = self.add(payload, "page")
        if height == 0:
            start, count = entries[0]["ordinal"], len(entries)
        else:
            start, count = entries[0]["start"], sum(e["count"] for e in entries)
        return TreeRef(ref, kind, height, start, count)

    def tree(self, kind: str, values: list[Any]) -> TreeRef | None:
        if not values:
            return None
        if len(values) > min(self.limits.tree_capacity, self.limits.reference_visits):
            _fail("CAPACITY", "tree entry capacity")
        entries = [{"ordinal": i, "value": v} for i, v in enumerate(values)]
        level = 0
        while True:
            pages = []
            batch: list[Any] = []
            maximum = self.limits.leaf_entries if level == 0 else self.limits.fanout
            for entry in entries:
                candidate = batch + [entry]
                size = len(_json({"format": PAGE_FORMAT, "kind": kind, "height": level, "entries": candidate}))
                if batch and (len(candidate) > maximum or size > self.limits.page_bytes):
                    pages.append(self.page(kind, level, batch))
                    batch = []
                batch.append(entry)
            if batch:
                pages.append(self.page(kind, level, batch))
            if len(pages) == 1:
                return pages[0]
            level += 1
            if level > self.limits.index_levels:
                _fail("CAPACITY", "supported index depth exhausted")
            entries = [_tree_obj(ref) for ref in pages]


def _rows(
    rows: Iterable[bytes], builder: _Builder, limits: ProtocolLimits
) -> tuple[TreeRef | None, int, str]:
    parts: list[MemberRef] = []
    buffer = bytearray()
    digest = sha256()
    size = 0
    count = 0
    for row in rows:
        count += 1
        if count > limits.input_rows:
            _fail("LIMIT", "serialized input row budget")
        if type(row) is not bytes or not row.endswith(b"\n") or b"\n" in row[:-1]:
            _fail("MALFORMED", "serialized row must be one LF-terminated byte record")
        if len(row) > limits.part_bytes:
            _fail("CAPACITY", "single serialized row exceeds the part bound")
        size += len(row)
        if size > limits.logical_bytes:
            _fail("LIMIT", "serialized payload byte budget")
        if buffer and len(buffer) + len(row) > limits.part_bytes:
            parts.append(builder.add(bytes(buffer), "part"))
            buffer.clear()
        buffer.extend(row)
        digest.update(row)
    if buffer:
        parts.append(builder.add(bytes(buffer), "part"))
    tree = builder.tree("extents", [_member_obj(ref) for ref in parts])
    return tree, size, digest.hexdigest()


def _noop(snapshot: VerifiedSnapshot, reason: str) -> PublicationPlan:
    return _sealed_result(
        PublicationPlan, expected_root_digest=snapshot.receipt.root_digest,
        snapshot=snapshot, members=MappingProxyType({}), transaction=None,
        reason=reason, _before=snapshot,
    )


def _finish(
    before: VerifiedSnapshot, tx: StorageTransaction, builder: _Builder, limits: ProtocolLimits
) -> PublicationPlan:
    tx = _transaction(_transaction_obj(tx), limits)
    for existing in before._transactions:
        if existing.transaction_id == tx.transaction_id:
            if existing.digest != tx.digest:
                _fail("CONFLICT", "storage transaction identity reused with different content")
            return _noop(before, "already_applied")
    if len(before._transactions) >= limits.history_operations:
        _fail("CAPACITY", "supported history operation capacity")
    transactions = before._transactions + (tx,)
    catalog = builder.tree("catalog", [_transaction_obj(item) for item in transactions])
    members = dict(before._members)
    members.update(builder.new)
    source = InMemorySource(members, snapshot_id="candidate:" + tx.digest)
    helper = _Verifier(source, limits, 0)
    parts = tuple(helper.tree(tx.extents, "extents"))
    if tx.kind == "replace":
        if tx.expected_view_digest != before.root.logical_digest:
            _fail("CONFLICT", "replacement targets a stale logical view")
        active = parts
    else:
        active = before._active + parts
    digest = sha256()
    size = 0
    for ref in active:
        data = members[ref.path]
        digest.update(data)
        size += len(data)
    root = RootRecord(
        before.root.base, catalog, len(transactions), size,
        digest.hexdigest(), limits.fingerprint,
    )
    snapshot = verify_snapshot(source, root, limits=limits)
    referenced_new = {path: value for path, value in builder.new.items() if path in snapshot._members}
    return _sealed_result(
        PublicationPlan, expected_root_digest=before.receipt.root_digest,
        snapshot=snapshot, members=MappingProxyType(referenced_new), transaction=tx,
        reason="planned", _before=before,
    )


@_typed
def plan_append(
    snapshot: VerifiedSnapshot, *, transaction_id: str,
    serialized_rows: Iterable[bytes], limits: ProtocolLimits
) -> PublicationPlan:
    _verified(snapshot, limits)
    if type(transaction_id) is not str or not _TXID.fullmatch(transaction_id):
        _fail("MALFORMED", "invalid storage transaction identity")
    builder = _Builder(snapshot._members, limits)
    extents, size, digest = _rows(serialized_rows, builder, limits)
    if size == 0:
        return _noop(snapshot, "empty_append")
    return _finish(snapshot, StorageTransaction(transaction_id, "append", extents, size, digest), builder, limits)


@_typed
def plan_replace_view(
    snapshot: VerifiedSnapshot, *, transaction_id: str, expected_view_digest: str,
    replacement_rows: Iterable[bytes], limits: ProtocolLimits
) -> PublicationPlan:
    """Plan bytes only; the caller retains all domain transformation authority."""
    _verified(snapshot, limits)
    _hash(expected_view_digest)
    builder = _Builder(snapshot._members, limits)
    extents, size, digest = _rows(replacement_rows, builder, limits)
    tx = StorageTransaction(transaction_id, "replace", extents, size, digest, expected_view_digest)
    # An exact retry must remain idempotent even after later appends.
    return _finish(snapshot, tx, builder, limits)


def _extent_members(snapshot: VerifiedSnapshot, tx: StorageTransaction) -> dict[str, bytes]:
    source = InMemorySource(snapshot._members, snapshot_id=snapshot.receipt.source_id)
    verifier = _Verifier(source, snapshot._limits, 0)
    for part in verifier.tree(tx.extents, "extents"):
        verifier.read(part)
    return verifier.loaded


@_typed
def rebase_pending(
    remote_snapshot: VerifiedSnapshot, pending_transactions: Iterable[PublicationPlan],
    *, limits: ProtocolLimits
) -> RebasePlan:
    _verified(remote_snapshot, limits)
    current = remote_snapshot
    additions: dict[str, bytes] = {}
    applied: list[str] = []
    already: list[str] = []
    previous_after: VerifiedSnapshot | None = None
    first_before: VerifiedSnapshot | None = None
    saw_new = False
    prior_remote_index = -1
    count = 0
    for plan in pending_transactions:
        count += 1
        if count > limits.history_operations:
            _fail("LIMIT", "pending transaction budget")
        if not isinstance(plan, PublicationPlan) or plan._seal is not _SEAL:
            _fail("MALFORMED", "verified pending plan required")
        _verified(plan._before, limits)
        _verified(plan.snapshot, limits)
        if plan._before.root.base != remote_snapshot.root.base:
            _fail("CONFLICT", "pending plan has a different base anchor")
        if first_before is None:
            first_before = plan._before
            prefix = remote_snapshot._transactions[: len(first_before._transactions)]
            if prefix != first_before._transactions:
                _fail("CONFLICT", "remote does not preserve the pending base prefix")
        elif plan._before.receipt.root_digest != previous_after.receipt.root_digest:
            _fail("CONFLICT", "pending plans do not form an ordered source chain")
        previous_after = plan.snapshot
        if plan.is_noop:
            continue
        tx = plan.transaction
        assert tx is not None
        found = [(i, t) for i, t in enumerate(remote_snapshot._transactions) if t.transaction_id == tx.transaction_id]
        if found:
            index, existing = found[0]
            if existing.digest != tx.digest or saw_new or index <= prior_remote_index:
                _fail("CONFLICT", "pending retry conflicts with accepted content/order")
            prior_remote_index = index
            already.append(tx.transaction_id)
            continue
        saw_new = True
        if tx.kind == "replace" and current.receipt.root_digest != plan._before.receipt.root_digest:
            _fail("CONFLICT", "stale pending rewrite requires native reconciliation")
        builder = _Builder(current._members, limits)
        for path, payload in _extent_members(plan.snapshot, tx).items():
            if path in builder.existing:
                if builder.existing[path] != payload:
                    _fail("CONFLICT", "conflicting immutable extent")
            else:
                builder.new[path] = payload
        next_plan = _finish(current, tx, builder, limits)
        additions.update(next_plan.members)
        current = next_plan.snapshot
        applied.append(tx.transaction_id)
    return RebasePlan(
        remote_snapshot.receipt.root_digest, current, MappingProxyType(additions),
        tuple(applied), tuple(already),
    )


@_typed
def validate_publication(
    candidate_source: PinnedSource, root: RootRecord, introduced_blobs: Iterable[BlobInfo],
    *, limits: ProtocolLimits
) -> PublicationCheck:
    """Validate explicit inventories; never extract Git objects or publish.

    The candidate inventory may retain bounded orphan members. It must include
    every referenced member. A real publisher must prove inventory completeness
    and supply the exact newly reachable object set after its own rebase.
    """
    snapshot = verify_snapshot(candidate_source, root, limits=limits)
    inventory: dict[str, MemberRef] = {}
    count = 0
    total = len(snapshot.root_bytes)
    for ref in candidate_source.iter_members():
        count += 1
        if count > limits.snapshot_members:
            _fail("NONRETRYABLE_CAPACITY", "candidate member inventory limit")
        if not isinstance(ref, MemberRef):
            _fail("MALFORMED", "candidate inventory requires MemberRef values")
        if ref.path in inventory:
            _fail("CONFLICT", "duplicate candidate inventory path")
        if ref.path == ROOT_PATH:
            checked = _read_member_ref(_member_obj(ref), "root", limits)
            payload = candidate_source.read_member(ROOT_PATH)
            if type(payload) is not bytes:
                _fail("MALFORMED", "candidate root must be exact immutable bytes")
            if checked != _member(ROOT_PATH, snapshot.root_bytes) or payload != snapshot.root_bytes:
                _fail("HASH_MISMATCH", "candidate root differs from supplied root")
            inventory[checked.path] = checked
            continue
        if ref.path == BASE_PATH:
            kind = "base"
        elif type(ref.path) is str and ref.path.startswith(PART_PREFIX):
            kind = "part"
        elif type(ref.path) is str and ref.path.startswith(PAGE_PREFIX):
            kind = "page"
        else:
            _fail("MALFORMED", "candidate inventory contains a non-protocol path")
        try:
            checked = _read_member_ref(_member_obj(ref), kind, limits)
        except SnapshotIntegrityError as exc:
            if exc.code == "LIMIT":
                raise SnapshotIntegrityError("NONRETRYABLE_OVERSIZE", "candidate member size limit") from exc
            raise
        payload = candidate_source.read_member(checked.path)
        if type(payload) is not bytes or _member(checked.path, payload) != checked:
            _fail("HASH_MISMATCH", "candidate inventory/member mismatch")
        total += checked.size
        if total > limits.snapshot_bytes:
            _fail("NONRETRYABLE_CAPACITY", "candidate retained byte budget")
        inventory[ref.path] = checked
    if ROOT_PATH not in inventory:
        _fail("INCOMPLETE", "candidate inventory omitted the explicit root")
    for path, payload in snapshot._members.items():
        if inventory.get(path) != _member(path, payload):
            _fail("INCOMPLETE", "candidate inventory omitted a referenced member")
    if candidate_source.snapshot_id != snapshot.receipt.source_id:
        _fail("SOURCE_CHANGED", "candidate source changed")
    introduced_count = 0
    seen_objects = set()
    for blob in introduced_blobs:
        introduced_count += 1
        if introduced_count > limits.publication_objects:
            _fail("NONRETRYABLE_CAPACITY", "introduced-object inventory limit")
        if not isinstance(blob, BlobInfo):
            _fail("MALFORMED", "introduced inventory requires BlobInfo values")
        if type(blob.object_id) is not str or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", blob.object_id):
            _fail("MALFORMED", "invalid introduced Git object identity")
        if blob.object_id in seen_objects:
            _fail("CONFLICT", "duplicate introduced Git object identity")
        seen_objects.add(blob.object_id)
        if type(blob.size) is not int or blob.size < 0:
            _fail("MALFORMED", "invalid introduced blob size")
        if blob.size > limits.git_blob_bytes:
            _fail("NONRETRYABLE_OVERSIZE", "newly reachable blob exceeds the publishing bound")
    return PublicationCheck(
        snapshot.receipt.source_id, snapshot.receipt.root_digest, count, introduced_count
    )


def _restart_plan(
    before: VerifiedSnapshot, retained: VerifiedSnapshot,
    transaction: StorageTransaction, limits: ProtocolLimits,
) -> PublicationPlan:
    """Reconstruct a pure plan without reserializing or repartitioning payloads."""
    builder = _Builder(before._members, limits)
    for path, payload in _extent_members(retained, transaction).items():
        if path in builder.existing:
            if builder.existing[path] != payload:
                _fail("CONFLICT", "conflicting retained restart extent")
        else:
            builder.new[path] = payload
    return _finish(before, transaction, builder, limits)


def _same_retained_snapshot(actual: VerifiedSnapshot, expected: VerifiedSnapshot) -> bool:
    # Comparison supplements the opaque provenance check; it does not confer a
    # verification seal on a caller-created object.
    return (
        type(actual.root_bytes) is bytes
        and encode_root(actual.root, limits=actual._limits) == expected.root_bytes
        and actual.root_bytes == expected.root_bytes
        and type(actual.receipt) is IntegrityReceipt
        and all(type(getattr(actual.receipt, name)) is int for name in (
            "member_count", "retained_bytes", "reference_visits",
            "operation_count", "logical_size",
        ))
        and actual.receipt.complete is True
        and actual.receipt == expected.receipt
        and type(actual._members) is MappingProxyType
        and all(type(k) is str and type(v) is bytes for k, v in actual._members.items())
        and actual._members == expected._members
        and type(actual._transactions) is tuple
        and actual._transactions == expected._transactions
        and type(actual._active) is tuple
        and actual._active == expected._active
    )


@_typed
def validate_plan(plan: PublicationPlan, *, limits: ProtocolLimits) -> None:
    """Check a retained planner result; grant no write, CAS or publication authority.

    Both the original snapshot and the reconstructed result are checked using
    the existing verifier/planner. No file or source discovery occurs. The
    opaque seal is an API provenance boundary, not a Python sandbox.
    """
    if type(limits) is not ProtocolLimits:
        _fail("MALFORMED", "a protocol limits profile is required")
    if type(plan) is not PublicationPlan or getattr(plan, "_seal", None) is not _SEAL:
        _fail("MALFORMED", "verified publication plan required")
    for snapshot in (plan._before, plan.snapshot):
        if type(snapshot) is not VerifiedSnapshot:
            _fail("INCOMPLETE", "a verified snapshot is required")
        _verified(snapshot, limits)
    if _hash(plan.expected_root_digest) != plan._before.receipt.root_digest:
        _fail("CONFLICT", "plan expected root differs from its original snapshot")
    if type(plan.members) is not MappingProxyType or any(
        type(path) is not str or type(payload) is not bytes
        for path, payload in plan.members.items()
    ):
        _fail("MALFORMED", "plan members must be an immutable byte mapping")
    if type(plan.reason) is not str:
        _fail("MALFORMED", "invalid plan reason")
    before = plan._before
    checked_before = verify_snapshot(
        InMemorySource(before._members, snapshot_id=before.receipt.source_id),
        before.root, limits=limits,
    )
    if not _same_retained_snapshot(before, checked_before):
        _fail("CONFLICT", "plan original snapshot metadata changed")
    if plan.transaction is None:
        if (
            plan.reason not in {"empty_append", "already_applied"}
            or plan.snapshot is not before or plan.members
        ):
            _fail("CONFLICT", "invalid no-op plan metadata")
        return None
    if type(plan.transaction) is not StorageTransaction or plan.reason != "planned":
        _fail("MALFORMED", "invalid planned transaction metadata")
    transaction = _transaction(_transaction_obj(plan.transaction), limits)
    if (
        plan.snapshot.root.base != before.root.base
        or plan.snapshot._transactions != before._transactions + (transaction,)
    ):
        _fail("CONFLICT", "plan does not extend its original history exactly once")
    rebuilt = _restart_plan(before, plan.snapshot, transaction, limits)
    if (
        rebuilt.is_noop or rebuilt.transaction != plan.transaction
        or rebuilt.members != plan.members
        or not _same_retained_snapshot(plan.snapshot, rebuilt.snapshot)
    ):
        _fail("CONFLICT", "plan metadata differs from its reconstructed result")
    return None


def _restart_prefix(before: VerifiedSnapshot, after: VerifiedSnapshot, label: str) -> None:
    if (
        after.root.base != before.root.base
        or after._members[BASE_PATH] != before._members[BASE_PATH]
        or after._transactions[:len(before._transactions)] != before._transactions
    ):
        _fail("CONFLICT", f"{label} does not preserve the exact original base/history prefix")


def _restart_work_budget(
    remote: VerifiedSnapshot, candidate: VerifiedSnapshot,
    pending: tuple[StorageTransaction, ...], new_count: int, limits: ProtocolLimits,
) -> None:
    # Conservative aggregate charges, not a peak-RAM or wall-time estimate.
    # Include raw occurrences even when their physical members are deduplicated
    # or a later replacement hides them. Charge both reconstruction and rebase
    # passes before creating any plan; retain no list of intermediate plans.
    count = len(pending)
    candidate_history_bytes = candidate.root.base.size + sum(
        transaction.payload_size for transaction in candidate._transactions
    )
    remote_history_bytes = remote.root.base.size + sum(
        transaction.payload_size for transaction in remote._transactions
    )
    pending_bytes = sum(transaction.payload_size for transaction in pending)
    byte_charge = count * (candidate.receipt.retained_bytes + candidate_history_bytes)
    byte_charge += new_count * (
        remote.receipt.retained_bytes + candidate.receipt.retained_bytes
        + remote_history_bytes + pending_bytes
    )
    reference_charge = count * (
        candidate.receipt.reference_visits + len(candidate._transactions)
    )
    reference_charge += new_count * (
        remote.receipt.reference_visits + candidate.receipt.reference_visits
        + len(remote._transactions) + len(candidate._transactions) + count
    )
    if byte_charge > limits.snapshot_bytes:
        _fail("LIMIT", "restart aggregate byte-work budget")
    if reference_charge > limits.reference_visits:
        _fail("LIMIT", "restart aggregate reference-work budget")


@_typed
def rebase_verified_pending(
    remote_snapshot: VerifiedSnapshot, *,
    original_base_snapshot: VerifiedSnapshot,
    original_candidate_snapshot: VerifiedSnapshot,
    authorized_transaction_ids: Iterable[str], limits: ProtocolLimits,
) -> RebasePlan:
    """Restart only an explicitly authorized complete stored transaction suffix.

    Inputs must be verified anew by the caller's explicit source adapter. IDs
    are storage retry identities, never claim IDs or permission to transform
    business records. The exact retained transactions/extents are reconstructed
    through the existing planner and remote-prefix rebase laws. A candidate
    whose root cannot be reproduced by those laws is rejected. This pure plan
    neither materializes members nor authorizes native reconciliation.

    Restart has a conservative aggregate work admission within the existing
    snapshot-byte/reference budgets. A series may be refused even when each
    individual snapshot fits. No history is dropped to make it fit.
    """
    if type(limits) is not ProtocolLimits:
        _fail("MALFORMED", "a protocol limits profile is required")
    for snapshot in (remote_snapshot, original_base_snapshot, original_candidate_snapshot):
        if type(snapshot) is not VerifiedSnapshot:
            _fail("INCOMPLETE", "a verified snapshot is required")
        _verified(snapshot, limits)
    base, candidate = original_base_snapshot, original_candidate_snapshot
    _restart_prefix(base, candidate, "candidate")
    _restart_prefix(base, remote_snapshot, "remote")
    pending = candidate._transactions[len(base._transactions):]
    if len(pending) > limits.history_operations:
        _fail("LIMIT", "restart pending transaction budget")
    if isinstance(authorized_transaction_ids, (str, bytes, bytearray, Mapping, set, frozenset)):
        _fail("MALFORMED", "authorized transaction IDs require an ordered iterable")
    seen: set[str] = set()
    count = 0
    for transaction_id in authorized_transaction_ids:
        if count >= len(pending):
            _fail("CONFLICT", "authorization contains extra storage transaction IDs")
        if type(transaction_id) is not str or not _TXID.fullmatch(transaction_id):
            _fail("MALFORMED", "invalid authorized storage transaction identity")
        if transaction_id in seen:
            _fail("CONFLICT", "duplicate authorized storage transaction identity")
        if transaction_id != pending[count].transaction_id:
            _fail("CONFLICT", "authorization differs from the complete ordered stored suffix")
        seen.add(transaction_id)
        count += 1
    if count != len(pending):
        _fail("CONFLICT", "authorization omits stored pending transactions")
    if not pending:
        if base.root_bytes != candidate.root_bytes:
            _fail("CONFLICT", "zero-pending candidate changed the original root")
        return rebase_pending(remote_snapshot, (), limits=limits)

    remote_ids = {
        transaction.transaction_id: (index, transaction)
        for index, transaction in enumerate(remote_snapshot._transactions)
    }
    new_count, previous_index, saw_new = 0, -1, False
    for transaction in pending:
        found = remote_ids.get(transaction.transaction_id)
        if found is None:
            new_count += 1
            saw_new = True
        else:
            index, accepted = found
            if accepted.digest != transaction.digest or saw_new or index <= previous_index:
                _fail("CONFLICT", "pending retry conflicts with accepted content/order")
            previous_index = index
    if len(remote_snapshot._transactions) + new_count > min(
        limits.history_operations, limits.tree_capacity,
    ):
        _fail("CAPACITY", "restart would exceed supported history capacity")
    _restart_work_budget(remote_snapshot, candidate, pending, new_count, limits)

    def reconstructed_plans():
        current = base
        for index, transaction in enumerate(pending):
            plan = _restart_plan(current, candidate, transaction, limits)
            if plan.is_noop or plan.transaction != transaction:
                _fail("CONFLICT", "stored suffix does not reconstruct as new original transactions")
            current = plan.snapshot
            if index == len(pending) - 1 and current.root_bytes != candidate.root_bytes:
                _fail("CONFLICT", "stored candidate root is not reproduced by the existing planner")
            yield plan

    return rebase_pending(remote_snapshot, reconstructed_plans(), limits=limits)
