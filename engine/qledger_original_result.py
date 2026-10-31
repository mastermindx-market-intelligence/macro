"""Inactive immutable original-result extension for an explicit QLedger owner.

No root discovery/creation fallback, native selector, journal, mutable HEAD,
Git ref, publisher or clock. Caller-supplied roots still need real host/retention
policy and producer admission. Local barriers/readback prove mechanical storage
facts, not those grants. Partial or ambiguous installation never admits apply;
reconciliation reads/syncs the SAME explicit completed result without overwrite.
The result retains original claims inputs, not the repository's complete history.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType
from threading import Lock, get_ident

from engine.qledger_store import NativeClaimsWrite, _NativeClaimsBinding
from engine.qledger_store_native import NativeClaimsIntent, NativeClaimsSession, _sync_dir, _sync_file, _write_all
from engine.qledger_store_protocol import (
    ROOT_PATH, InMemorySource, ProtocolLimits, SnapshotIntegrityError,
    restore_original_plan, validate_plan, verify_snapshot, decode_root,
)
from engine.qledger_store_sources import _absolute, _file_identity, _member_limit, _open_directory
from scripts.ci import qledger_conversion_candidate as git_candidate
from scripts.ci.qledger_publication import NativeOperationReceipt, classify_pending

_SCHEMA = "qledger-original-result/v1"
_CAUSAL_SCHEMA = "qledger-original-result/v2"
_SEAL = object()
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_RESULT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def _fail(message):
    raise SnapshotIntegrityError("ORIGINAL_RESULT_UNPROVEN", message)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _manifest_bound(limits):
    return min(limits.snapshot_bytes, limits.snapshot_members * 512)


@dataclass(frozen=True)
class PreparedOriginalResult:
    result_id: str
    write: NativeClaimsWrite
    limits: ProtocolLimits
    manifest_bytes: bytes
    manifest_digest: str
    objects: object
    _seal: object
    predecessors: tuple = ()


@dataclass(frozen=True, init=False)
class RetainedOriginalResult:
    owner_root: Path
    result_path: Path
    result_id: str
    manifest_digest: str
    write: NativeClaimsWrite
    native_operation_receipt: NativeOperationReceipt
    candidate_oid: str
    accepted_tip_oid: str
    commit_metadata: git_candidate.CandidateCommitMetadata
    target_ref: str
    limits: ProtocolLimits
    predecessors: tuple
    retained_bytes: int
    retained_members: int
    retained_visits: int
    _seal: object


def _target(path):
    path = _absolute(path)
    if path.parts[-3:] != ("data", "qledger", "claims.jsonl"):
        _fail("an explicit canonical claims path is required")
    return path


def _descriptor(retained):
    return dict(owner_root=str(retained.owner_root), result_path=str(retained.result_path),
                result_id=retained.result_id, manifest_digest=retained.manifest_digest,
                intent=asdict(retained.write.intent))


def _prefix(predecessors, *, claims_path, intent, limits, accepted_tip_oid=None, target_ref=None):
    """Check caller-named typed originals; never discover or follow disk paths."""
    if type(limits) is not ProtocolLimits or type(intent) is not NativeClaimsIntent:
        _fail("explicit original profile/intent required")
    if type(predecessors) is not tuple or len(predecessors) >= limits.history_operations:
        _fail("finite ordered typed predecessor originals required")
    seen_paths, seen_ids = set(), {intent.transaction_id}
    for index, previous in enumerate(predecessors):
        if type(previous) is not RetainedOriginalResult or previous._seal is not _SEAL:
            _fail("typed retained predecessor required")
        if (previous.write.claims_path != claims_path or previous.limits != limits
                or (previous.write.intent.operation_id, previous.write.intent.lane_id)
                != (intent.operation_id, intent.lane_id)
                or previous.result_path in seen_paths or previous.write.intent.transaction_id in seen_ids
                or tuple(map(_descriptor, previous.predecessors)) != tuple(map(_descriptor, predecessors[:index]))
                or (accepted_tip_oid is not None and previous.accepted_tip_oid != accepted_tip_oid)
                or (target_ref is not None and previous.target_ref != target_ref)):
            _fail("foreign, missing, duplicate or reordered causal predecessor")
        if index and not _same_snapshot(predecessors[index - 1].write.plan.snapshot, previous.write.plan._before):
            _fail("causal predecessor before-root differs")
        seen_paths.add(previous.result_path)
        seen_ids.add(previous.write.intent.transaction_id)


def _same_snapshot(left, right):
    return left.root_bytes == right.root_bytes and left._members == right._members


def _receipt(write, predecessors, limits):
    _prefix(predecessors, claims_path=write.claims_path, intent=write.intent, limits=limits)
    if predecessors and not _same_snapshot(predecessors[-1].write.plan.snapshot, write.plan._before):
        _fail("exact causal predecessor before-root required")
    receipt = NativeOperationReceipt(write.intent.operation_id, write.intent.lane_id,
        predecessors[0].write.plan._before if predecessors else write.plan._before,
        write.plan.snapshot,
        tuple(p.write.intent.transaction_id for p in predecessors) + (write.intent.transaction_id,), limits)
    classify_pending(write.plan.snapshot, native_operation_receipt=receipt)
    return receipt


def _fresh_prefix(predecessors, *, claims_path, intent, limits):
    _prefix(predecessors, claims_path=claims_path, intent=intent, limits=limits)
    if not predecessors:
        return ()
    last = predecessors[-1]
    checked = read_original_result(owner_root=last.owner_root, result_path=last.result_path,
        expected_result_id=last.result_id, expected_manifest_digest=last.manifest_digest,
        expected_claims_path=claims_path, expected_intent=last.write.intent, limits=limits,
        predecessors=predecessors[:-1])
    return checked.predecessors + (checked,)


def prepare_original_result(write, *, candidate, result_id, limits, predecessors=()):
    """Read qualified Git inputs and prepare ONE causal write's original result.

    Explicit predecessors retain each original separately; no discovery or new IDs.
    Git readback verifies the source before the manifest binds its object ID.
    """
    if type(write) is not NativeClaimsWrite or type(write.intent) is not NativeClaimsIntent:
        _fail("explicit original write/intent required")
    write.intent.__post_init__()
    _target(write.claims_path)
    if type(result_id) is not str or not _RESULT_ID.fullmatch(result_id):
        _fail("explicit immutable result identity required")
    validate_plan(write.plan, limits=limits)
    if write.plan.transaction is None or write.plan.transaction.transaction_id != write.intent.transaction_id:
        _fail("original plan/intent mismatch")
    if type(candidate) is not git_candidate.PreparedNativeOperationCandidate:
        _fail("explicit prepared native Git candidate required")
    predecessors = _fresh_prefix(predecessors, claims_path=write.claims_path, intent=write.intent, limits=limits)
    _prefix(predecessors, claims_path=write.claims_path, intent=write.intent, limits=limits,
            accepted_tip_oid=candidate.continuity.accepted_tip_oid,
            target_ref=candidate.continuity.publication.target_ref)
    original = _receipt(write, predecessors, limits)
    receipt, _ = git_candidate.read_native_operation_candidate(
        write.claims_path.parents[2], candidate_oid=candidate.candidate_oid,
        accepted_tip_oid=candidate.continuity.accepted_tip_oid,
        operation_id=write.intent.operation_id, lane_id=write.intent.lane_id,
        authorized_transaction_ids=original.authorized_transaction_ids,
        commit_metadata=candidate.commit_metadata,
        target_ref=candidate.continuity.publication.target_ref, limits=limits)
    if (not _same_snapshot(receipt.original_base_snapshot, original.original_base_snapshot)
            or not _same_snapshot(receipt.original_candidate_snapshot, write.plan.snapshot)):
        _fail("Git candidate differs from exact original write")
    objects = {}
    def object_id(payload):
        digest = sha256(payload).hexdigest()
        if digest in objects and objects[digest] != payload:
            _fail("immutable object digest conflict")
        objects[digest] = payload
        return digest
    def snapshot(value):
        return {"root": object_id(value.root_bytes),
                "members": {path: object_id(payload) for path, payload in value._members.items()},
                "original_source_id": value.receipt.source_id}
    commit = git_candidate._native_commit_bytes(candidate.tree_oid, candidate.continuity.accepted_tip_oid,
        write.intent.operation_id, write.intent.lane_id, candidate.commit_metadata)
    manifest = {"schema": _SCHEMA, "result_id": result_id, "claims_path": str(write.claims_path),
        "intent": asdict(write.intent), "limits": asdict(limits),
        "base": snapshot(write.plan._before), "candidate": snapshot(write.plan.snapshot),
        "git": {"candidate_oid": candidate.candidate_oid, "tree_oid": candidate.tree_oid,
                "accepted_tip_oid": candidate.continuity.accepted_tip_oid,
                "target_ref": candidate.continuity.publication.target_ref,
                "metadata": asdict(candidate.commit_metadata), "commit": object_id(commit)}}
    if predecessors:
        manifest["schema"] = _CAUSAL_SCHEMA
        manifest["predecessors"] = list(map(_descriptor, predecessors))
    raw = _json(manifest)
    if (len(objects) + sum(p.retained_members for p in predecessors) > limits.snapshot_members
            or sum(map(len, objects.values())) + len(raw)
            + sum(p.retained_bytes for p in predecessors) > limits.snapshot_bytes
            or len(raw) > _manifest_bound(limits)):
        _fail("original result exceeds existing inventory/byte bounds")
    visits = write.plan._before.receipt.reference_visits + write.plan.snapshot.receipt.reference_visits
    if visits + sum(p.retained_visits for p in predecessors) > limits.reference_visits:
        _fail("aggregate original retention exceeds reference bound")
    return PreparedOriginalResult(result_id, write, limits, raw, sha256(raw).hexdigest(),
                                  MappingProxyType(objects), _SEAL, predecessors)


def _owner(root, path, result_id, claims_path):
    root, path = _absolute(root), _absolute(path)
    if (path.parent != root or path.name != result_id or not _RESULT_ID.fullmatch(result_id)
            or root.is_relative_to(_target(claims_path).parents[2])):
        _fail("result must be an explicit immediate child of an owner root outside the checkout")
    fd = _open_directory(root)  # Existing root only; no symlinked ancestor.
    info = os.fstat(fd)
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
        os.close(fd)
        _fail("owner evidence root ownership/mode is unsafe")
    return fd


def _same(parent, name, fd):
    actual, held = os.stat(name, dir_fd=parent, follow_symlinks=False), os.fstat(fd)
    if (not stat.S_ISDIR(actual.st_mode) or actual.st_uid != os.geteuid()
            or stat.S_IMODE(actual.st_mode) & 0o022
            or (actual.st_dev, actual.st_ino) != (held.st_dev, held.st_ino)):
        _fail("result directory changed during readback")


def _stable_owner(root, fd):
    other = _open_directory(root)
    try:
        a, b = os.fstat(fd), os.fstat(other)
        if ((a.st_dev, a.st_ino) != (b.st_dev, b.st_ino)
                or b.st_uid != os.geteuid() or stat.S_IMODE(b.st_mode) & 0o022):
            _fail("owner evidence root changed")
    finally:
        os.close(other)


def _open_child(parent, name):
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    info = os.fstat(fd)
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o022:
        os.close(fd)
        _fail("unsafe original-result directory ownership/mode")
    return fd


def _entries(fd, maximum):
    names = set()
    with os.scandir(fd) as entries:
        for entry in entries:
            if len(names) >= maximum:
                _fail("original-result directory exceeds entry bound")
            names.add(entry.name)
    return names


def _write(parent, name, payload):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o600, dir_fd=parent)
    try:
        _write_all(fd, payload)
        _sync_file(fd)
    finally:
        os.close(fd)


def _read(parent, name, maximum, identities):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) & 0o022 or info.st_size > maximum):
            _fail("unsafe or oversized original-result file")
        value = bytearray()
        while len(value) < info.st_size:
            # Metadata/identity checks detect growth without allocating an
            # extra probe byte beyond the admitted remaining budget.
            block = os.read(fd, min(1024 * 1024, info.st_size - len(value)))
            if not block:
                break
            value.extend(block)
        if len(value) != info.st_size or _file_identity(info) != _file_identity(os.fstat(fd)):
            _fail("original-result file changed while reading")
        _sync_file(fd)  # Re-establish barriers after a lost installation return.
        identities.append((parent, name, _file_identity(info)))
        return bytes(value)
    finally:
        os.close(fd)


def retain_original_result(*, owner_root, result_path, prepared):
    """Install once, member barriers before manifest; never overwrite/retry.

    Failure may leave an incomplete result at this exact path. Preserve it.
    Only completed exact readback can reconcile an ambiguous installation.
    """
    if type(prepared) is not PreparedOriginalResult or prepared._seal is not _SEAL:
        _fail("prepared original result required")
    predecessors = _fresh_prefix(prepared.predecessors, claims_path=prepared.write.claims_path,
                                 intent=prepared.write.intent, limits=prepared.limits)
    if (len(prepared.objects) + sum(p.retained_members for p in predecessors) > prepared.limits.snapshot_members
            or len(prepared.manifest_bytes) + sum(map(len, prepared.objects.values()))
            + sum(p.retained_bytes for p in predecessors) > prepared.limits.snapshot_bytes):
        _fail("aggregate original retention exceeds existing bounds")
    root_fd = result_fd = members_fd = None
    try:
        root_fd = _owner(owner_root, result_path, prepared.result_id, prepared.write.claims_path)
        os.mkdir(result_path.name, 0o700, dir_fd=root_fd)
        result_fd = _open_child(root_fd, result_path.name)
        _sync_dir(root_fd)
        os.mkdir("members", 0o700, dir_fd=result_fd)
        members_fd = _open_child(result_fd, "members")
        for digest, payload in prepared.objects.items():
            _write(members_fd, digest, payload)
        _sync_dir(members_fd)
        _write(result_fd, "manifest.json", prepared.manifest_bytes)
        _sync_dir(result_fd)
        _same(root_fd, result_path.name, result_fd)
        _stable_owner(owner_root, root_fd)
        _sync_dir(root_fd)
    except (OSError, ValueError, TypeError) as exc:
        raise SnapshotIntegrityError("ORIGINAL_RESULT_UNPROVEN", "original result installation unproven; preserve the exact path") from exc
    finally:
        for fd in (members_fd, result_fd, root_fd):
            if fd is not None:
                os.close(fd)
    return read_original_result(owner_root=owner_root, result_path=result_path,
        expected_result_id=prepared.result_id, expected_manifest_digest=prepared.manifest_digest,
        expected_claims_path=prepared.write.claims_path, expected_intent=prepared.write.intent, limits=prepared.limits,
        predecessors=predecessors)


def read_original_result(*, owner_root, result_path, expected_result_id, expected_manifest_digest,
                         expected_claims_path, expected_intent, limits, predecessors=()):
    """Read the explicit ordered prefix once, then this result under ONE budget.

    No recursive disk discovery, mutable head or second retention store. Old v1
    records require no predecessors and retain their exact original semantics.
    """
    _prefix(predecessors, claims_path=expected_claims_path, intent=expected_intent, limits=limits)
    budget = dict(bytes=limits.snapshot_bytes, members=limits.snapshot_members, visits=limits.reference_visits)
    checked = ()
    for previous in predecessors:
        item = _read_original_result_one(owner_root=previous.owner_root, result_path=previous.result_path,
            expected_result_id=previous.result_id, expected_manifest_digest=previous.manifest_digest,
            expected_claims_path=expected_claims_path, expected_intent=previous.write.intent,
            limits=limits, predecessors=checked, budget=budget)
        checked += (item,)
    return _read_original_result_one(owner_root=owner_root, result_path=result_path,
        expected_result_id=expected_result_id, expected_manifest_digest=expected_manifest_digest,
        expected_claims_path=expected_claims_path, expected_intent=expected_intent,
        limits=limits, predecessors=checked, budget=budget)


def _read_original_result_one(*, owner_root, result_path, expected_result_id, expected_manifest_digest,
                              expected_claims_path, expected_intent, limits, predecessors, budget):
    """Bounded exact readback/re-barrier of one explicit original result.

    No overwrite, root creation, Git requirement or automatic application.
    Original source IDs remain provenance metadata, not current source claims.
    """
    if (type(limits) is not ProtocolLimits or type(expected_intent) is not NativeClaimsIntent
            or type(expected_manifest_digest) is not str or not _HASH.fullmatch(expected_manifest_digest)):
        _fail("explicit original result binding required")
    expected_intent.__post_init__()
    root_fd = result_fd = members_fd = None
    identities = []
    try:
        root_fd = _owner(owner_root, result_path, expected_result_id, expected_claims_path)
        result_fd = _open_child(root_fd, result_path.name)
        if _entries(result_fd, 2) != {"members", "manifest.json"}:
            _fail("incomplete or unexpected original-result entries")
        raw = _read(result_fd, "manifest.json", min(_manifest_bound(limits), budget["bytes"]), identities)
        if sha256(raw).hexdigest() != expected_manifest_digest:
            _fail("original manifest differs from expected immutable identity")
        manifest = json.loads(raw)
        if (type(manifest) is not dict or _json(manifest) != raw
                or set(manifest) != ({"schema", "result_id", "claims_path", "intent", "limits", "base", "candidate", "git"}
                                     | ({"predecessors"} if predecessors else set()))
                or manifest["schema"] != (_CAUSAL_SCHEMA if predecessors else _SCHEMA)
                or (predecessors and manifest["predecessors"] != list(map(_descriptor, predecessors)))
                or manifest["result_id"] != expected_result_id
                or manifest["claims_path"] != str(expected_claims_path)
                or manifest["intent"] != asdict(expected_intent) or manifest["limits"] != asdict(limits)):
            _fail("foreign or noncanonical original-result manifest")
        _prefix(predecessors, claims_path=expected_claims_path, intent=expected_intent, limits=limits,
                accepted_tip_oid=manifest["git"]["accepted_tip_oid"], target_ref=manifest["git"]["target_ref"])
        if any(p.result_path == result_path for p in predecessors):
            _fail("duplicate original result location")
        maxima = {}
        def reference(digest, maximum):
            if type(digest) is not str or not _HASH.fullmatch(digest):
                _fail("malformed original object identity")
            maxima[digest] = min(maxima.get(digest, maximum), maximum)
        for label in ("base", "candidate"):
            desc = manifest[label]
            if (type(desc) is not dict or set(desc) != {"root", "members", "original_source_id"}
                    or type(desc["members"]) is not dict or len(desc["members"]) > limits.snapshot_members
                    or type(desc["original_source_id"]) is not str):
                _fail("malformed original snapshot descriptor")
            reference(desc["root"], limits.root_bytes)
            for path, digest in desc["members"].items():
                reference(digest, _member_limit(path, limits))
        git = manifest["git"]
        if type(git) is not dict or set(git) != {"candidate_oid", "tree_oid", "accepted_tip_oid", "target_ref", "metadata", "commit"}:
            _fail("malformed original Git binding")
        reference(git["commit"], 4096)
        members_fd = _open_child(result_fd, "members")
        names = _entries(members_fd, budget["members"])
        if len(names) > budget["members"] or set(names) != set(maxima):
            _fail("incomplete or unexpected original object inventory")
        total = 0
        for digest in names:
            total += os.stat(digest, dir_fd=members_fd, follow_symlinks=False).st_size
        if total + len(raw) > budget["bytes"]:
            _fail("original object inventory/manifest exceeds byte bound")
        objects = {}
        remaining = budget["bytes"] - len(raw)
        for digest, maximum in maxima.items():
            # Metadata census is only an early refusal. Bound actual allocation
            # even if a member grows before its stable no-follow read begins.
            payload = _read(members_fd, digest, min(maximum, remaining), identities)
            remaining -= len(payload)
            if sha256(payload).hexdigest() != digest:
                _fail("original member hash mismatch")
            objects[digest] = payload
        retained_bytes = budget["bytes"] - remaining
        budget["bytes"] = remaining
        budget["members"] -= len(names)
        snapshots = []
        for label in ("base", "candidate"):
            desc = manifest[label]
            members = {path: objects[digest] for path, digest in desc["members"].items()}
            source = InMemorySource(members, snapshot_id="original-result:" + expected_manifest_digest + ":" + label)
            snapshot = verify_snapshot(source, decode_root(objects[desc["root"]], limits=limits), limits=limits)
            if set(snapshot._members) != set(members):
                _fail("snapshot descriptor contains unreferenced native members")
            snapshots.append(snapshot)
        base, candidate = snapshots
        retained_visits = base.receipt.reference_visits + candidate.receipt.reference_visits
        if retained_visits > budget["visits"]:
            _fail("aggregate original readback exceeds reference bound")
        budget["visits"] -= retained_visits
        receipt = NativeOperationReceipt(expected_intent.operation_id, expected_intent.lane_id,
            base, candidate, (expected_intent.transaction_id,), limits)
        classify_pending(candidate, native_operation_receipt=receipt)
        metadata = git_candidate.CandidateCommitMetadata(**git["metadata"])
        # Preserve the explicit original operation-to-Git-object binding after
        # checkout/GC, without claiming this artifact contains complete Git history.
        git_candidate.publication._native_binding(git_candidate.publication.NativePublicationBinding(
            expected_intent.operation_id, expected_intent.lane_id, git["target_ref"],
            git["accepted_tip_oid"], candidate.receipt.root_digest))
        git_candidate.publication._oid(git["tree_oid"])
        commit = git_candidate._native_commit_bytes(git["tree_oid"], git["accepted_tip_oid"],
            expected_intent.operation_id, expected_intent.lane_id, metadata)
        if objects[git["commit"]] != commit or git_candidate._commit_identity(commit, git["accepted_tip_oid"]) != git["candidate_oid"]:
            _fail("original operation-to-object binding mismatch")
        plan = restore_original_plan(base, candidate, transaction_id=expected_intent.transaction_id, limits=limits)
        write = NativeClaimsWrite(expected_intent, plan, expected_claims_path)
        receipt = _receipt(write, predecessors, limits)
        _sync_dir(members_fd)
        _sync_dir(result_fd)
        _sync_dir(root_fd)
        for parent, name, identity in identities:
            if _file_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != identity:
                _fail("original result changed after verification")
        if _entries(members_fd, limits.snapshot_members) != set(maxima):
            _fail("original object inventory changed")
        _same(result_fd, "members", members_fd)
        _same(root_fd, result_path.name, result_fd)
        _stable_owner(owner_root, root_fd)
        retained = object.__new__(RetainedOriginalResult)
        for key, value in dict(owner_root=owner_root, result_path=result_path, result_id=expected_result_id,
            manifest_digest=expected_manifest_digest, write=write, native_operation_receipt=receipt,
            candidate_oid=git["candidate_oid"], accepted_tip_oid=git["accepted_tip_oid"],
            commit_metadata=metadata, target_ref=git["target_ref"], limits=limits, predecessors=predecessors,
            retained_bytes=retained_bytes, retained_members=len(names), retained_visits=retained_visits, _seal=_SEAL).items():
            object.__setattr__(retained, key, value)
        return retained
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        raise SnapshotIntegrityError("ORIGINAL_RESULT_UNPROVEN", "original result readback unproven; no apply admitted") from exc
    finally:
        for fd in (members_fd, result_fd, root_fd):
            if fd is not None:
                os.close(fd)


def require_retained_original(write, retained):
    if type(retained) is not RetainedOriginalResult or getattr(retained, "_seal", None) is not _SEAL:
        _fail("verified original-result readback required before apply")
    if type(write) is not NativeClaimsWrite:
        _fail("explicit original write required")
    validate_plan(write.plan, limits=retained.limits)
    checked = read_original_result(owner_root=retained.owner_root, result_path=retained.result_path,
        expected_result_id=retained.result_id, expected_manifest_digest=retained.manifest_digest,
        expected_claims_path=write.claims_path, expected_intent=write.intent, limits=retained.limits,
        predecessors=retained.predecessors)
    if (checked.write.plan._before.root_bytes != write.plan._before.root_bytes
            or checked.write.plan.snapshot.root_bytes != write.plan.snapshot.root_bytes
            or checked.write.plan.transaction != write.plan.transaction):
        _fail("retained original differs from this exact write")
    return checked


def apply_retained_original(session, write, retained):
    """Explicit inert owner seam; no selector, fresh identity, clocks or publisher."""
    require_retained_original(write, retained)
    if (not isinstance(session, NativeClaimsSession)
            or session.location != write.claims_path.parents[2] or session.intent != write.intent):
        _fail("native session differs from retained target/intent")
    return session.apply_prepared(write.plan)


@dataclass(frozen=True)
class OriginalResultTarget:
    """Owner-predeclared location/source/metadata for ONE explicit write intent."""

    owner_root: Path
    result_path: Path
    result_id: str
    accepted_tip_oid: str
    accepted_ref: str
    target_ref: str
    commit_metadata: git_candidate.CandidateCommitMetadata
    predecessor_intents: tuple = ()


class OriginalResultClaimsBinding(_NativeClaimsBinding):
    """Inactive owner bridge; no factories, source retargeting or enrollment.

    The finite mapping is explicit caller input. Host/retention/launch policy,
    original budget and real failure consumption remain owner obligations.
    Prepared-result facts are task-local, not another durable operation ledger.
    """

    def __init__(self, explicit_claims_path, *, operation_id, lane_id, limits,
                 original_result_targets, lock_timeout=30):
        from contextvars import ContextVar

        git_candidate.publication._profile(limits)
        super().__init__(explicit_claims_path, operation_id=operation_id,
                         lane_id=lane_id, limits=limits, lock_timeout=lock_timeout)
        # Capture before any original native attempt. A later publication
        # wrapper must not adopt inherited parent evidence after a fork.
        self._original_process_id = os.getpid()
        if (type(original_result_targets) not in (dict, MappingProxyType)
                or len(original_result_targets) > limits.history_operations):
            _fail("finite predeclared original-result targets required; no factory")
        targets, paths = {}, set()
        for intent, target in original_result_targets.items():
            self._check_intent(intent)
            if type(target) is not OriginalResultTarget:
                _fail("explicit immutable original-result target required")
            root, path = _absolute(target.owner_root), _absolute(target.result_path)
            if (path.parent != root or path.name != target.result_id
                    or type(target.result_id) is not str or not _RESULT_ID.fullmatch(target.result_id)
                    or root.is_relative_to(self.repo_root) or path in paths):
                _fail("foreign, duplicate or unsafe original-result target")
            git_candidate.publication._native_binding(git_candidate.publication.NativePublicationBinding(
                operation_id, lane_id, target.target_ref, target.accepted_tip_oid, "0" * 64))
            if (type(target.accepted_ref) is not str or not target.accepted_ref.startswith("refs/")
                    or type(target.commit_metadata) is not git_candidate.CandidateCommitMetadata):
                _fail("exact accepted source and fixed metadata required")
            target.commit_metadata.git_identity()
            prefix = target.predecessor_intents
            if type(prefix) is not tuple or len(prefix) >= limits.history_operations or len(set(prefix)) != len(prefix):
                _fail("finite ordered predeclared predecessor intents required")
            for index, predecessor in enumerate(prefix):
                self._check_intent(predecessor)
                if predecessor not in targets:
                    _fail("predecessor must be an earlier predeclared original")
                previous = targets[predecessor]
                if (previous.predecessor_intents != prefix[:index]
                        or previous.accepted_tip_oid != target.accepted_tip_oid
                        or previous.accepted_ref != target.accepted_ref or previous.target_ref != target.target_ref):
                    _fail("incomplete causal prefix or changed accepted source")
            targets[intent] = target
            paths.add(path)
        self.original_result_targets = MappingProxyType(targets)
        self._prepared_results = ContextVar("qledger_owner_prepared_results", default=())
        # Actual binding ownership, shared across ContextVar/thread views. It
        # records local entry provenance only, never runtime admission/recovery.
        self._original_entry_guard = Lock()
        self._original_entry_seen = False
        self._original_entry_owner = None
        self._original_entry_context = ContextVar("qledger_original_invocation", default=None)

    @contextmanager
    def _fresh_original_invocation(self):
        """Atomically exclude other same-binding producers through completion.

        Admission is checked here, not when a future callback is constructed.
        Earlier activity is sticky across task/thread ContextVar views. Existing
        unscoped direct originals remain supported, but cannot later be borrowed
        by a fresh engine invocation. Nothing here grants host/resource authority.
        """
        if os.getpid() != self.original_process_id:
            _fail("original process differs; inherited native binding cannot transfer")
        if not self._original_entry_guard.acquire(blocking=False):
            _fail("same-binding original invocation is already active")
        token = None
        try:
            if (self._original_entry_seen or self.attempts or self.prepared_original_results
                    or self.pre_attempt_failure is not None):
                _fail("fresh original invocation cannot borrow earlier producer activity")
            owner = (object(), os.getpid(), get_ident())
            self._original_entry_owner = owner
            token = self._original_entry_context.set(owner)
            # Entering the original is not retried, including when no rows were
            # emitted or response/clock/resource completion remains unknown.
            self._original_entry_seen = True
            yield
        finally:
            if token is not None:
                self._original_entry_context.reset(token)
            self._original_entry_owner = None
            self._original_entry_guard.release()

    def _require_original_entry_owner(self):
        owner = self._original_entry_owner
        if (owner is None or self._original_entry_context.get() is not owner
                or (os.getpid(), get_ident()) != owner[1:]):
            _fail("another producer owns this same-binding original invocation")

    @property
    def original_process_id(self):
        """Actual binding creator PID; no host/version or admission claim."""
        return self._original_process_id

    @property
    def prepared_original_results(self):
        return self._prepared_results.get()

    def _target_for(self, intent):
        try:
            return self.original_result_targets[intent]
        except (KeyError, TypeError):
            _fail("write intent has no predeclared original-result target")

    def _settled(self, write):
        if os.getpid() != self.original_process_id or self.pre_attempt_failure is not None:
            _fail("original process or pre-attempt evidence is unresolved")
        attempts = [a for a in self.attempts if self._same_original_write(a.write, write)]
        if not attempts or any(a.outcome is None or a.outcome.status not in ("materialized", "noop", "already_applied")
                or a.outcome.clock_status == "uncertain" or a.outcome.durability_status == "uncertain"
                or a.outcome.root_visibility == "unknown" for a in attempts):
            _fail("causal predecessor native effect/clock remains unresolved")

    def _predecessors_for(self, target):
        if os.getpid() != self.original_process_id:
            _fail("original process differs; inherited native binding cannot transfer")
        predecessors = ()
        for intent in target.predecessor_intents:
            matches = [(w, p) for w, p in self.prepared_original_results if w.intent == intent]
            if len(matches) != 1:
                _fail("missing or duplicate original predecessor result")
            write, _ = matches[0]
            self._settled(write)
            checked = self.read_original_write_result(write)
            if tuple(map(_descriptor, checked.predecessors)) != tuple(map(_descriptor, predecessors)):
                _fail("original predecessor result order differs")
            predecessors += (checked,)
        return predecessors

    def _admit(self, intent, *, original=None):
        if os.getpid() != self.original_process_id:
            _fail("original process differs; inherited native binding cannot transfer")
        if self._original_entry_owner is not None:
            self._require_original_entry_owner()
            return self._admit_original(intent, original=original)
        # An unscoped writer racing fresh callback admission either owns this
        # guard first (making later entry non-fresh), or refuses before effect.
        if not self._original_entry_guard.acquire(blocking=False):
            _fail("same-binding original invocation is already active")
        try:
            self._original_entry_seen = True
            return self._admit_original(intent, original=original)
        finally:
            self._original_entry_guard.release()

    def _admit_original(self, intent, *, original=None):
        super()._admit(intent, original=original)
        target = self._target_for(intent)
        self._predecessors_for(target)

    def _apply_original_write(self, session, write):
        if self._original_entry_owner is not None:
            self._require_original_entry_owner()
        target = self._target_for(write.intent)
        predecessors = self._predecessors_for(target)
        receipt = _receipt(write, predecessors, self.limits)
        candidate = git_candidate.prepare_native_operation_candidate(
            self.repo_root, accepted_tip_oid=target.accepted_tip_oid,
            accepted_ref=target.accepted_ref, native_operation_receipt=receipt,
            commit_metadata=target.commit_metadata, target_ref=target.target_ref, limits=self.limits)
        prepared = prepare_original_result(write, candidate=candidate,
                                            result_id=target.result_id, limits=self.limits, predecessors=predecessors)
        self._prepared_results.set(self.prepared_original_results + ((write, prepared),))
        retained = retain_original_result(owner_root=target.owner_root,
                                         result_path=target.result_path, prepared=prepared)
        return apply_retained_original(session, write, retained)

    def read_original_write_result(self, write, *, retained_original=None):
        """Read the SAME result; never re-prepare claims/candidates/locations.

        After process loss the owner must supply explicit retained readback with
        original custody/budget; this does not mint a fresh binding or discover
        a replacement. Missing/partial retention remains unproven.
        """
        if type(write) is not NativeClaimsWrite:
            _fail("explicit original write required")
        validate_plan(write.plan, limits=self.limits)
        self._check_intent(write.intent)
        target = self._target_for(write.intent)
        if retained_original is None:
            prepared = next((value for previous, value in reversed(self.prepared_original_results)
                             if self._same_original_write(previous, write)), None)
            if prepared is None:
                _fail("original retention unknown; explicit owner readback required")
            retained_original = read_original_result(owner_root=target.owner_root,
                result_path=target.result_path, expected_result_id=target.result_id,
                expected_manifest_digest=prepared.manifest_digest,
                expected_claims_path=self.claims_path, expected_intent=write.intent, limits=self.limits,
                predecessors=prepared.predecessors)
        checked = require_retained_original(write, retained_original)
        if (checked.owner_root != target.owner_root or checked.result_path != target.result_path
                or checked.result_id != target.result_id or checked.accepted_tip_oid != target.accepted_tip_oid
                or checked.commit_metadata != target.commit_metadata or checked.target_ref != target.target_ref):
            _fail("retained original differs from exact predeclared owner target/source")
        if tuple(p.write.intent for p in checked.predecessors) != target.predecessor_intents:
            _fail("retained original causal prefix differs from predeclared intents")
        for previous in checked.predecessors:
            expected = self._target_for(previous.write.intent)
            if (previous.owner_root, previous.result_path, previous.result_id, previous.accepted_tip_oid,
                    previous.target_ref, previous.commit_metadata) != (expected.owner_root, expected.result_path,
                    expected.result_id, expected.accepted_tip_oid, expected.target_ref, expected.commit_metadata):
                _fail("retained predecessor differs from predeclared original target")
        return checked

    def read_original_write_chain(self, writes, *, retained_original=None):
        """Complete explicit same-process sequence; no automatic result aggregation."""
        if type(writes) is not tuple or not writes or len(writes) > self.limits.history_operations:
            _fail("complete ordered original writes required")
        for write in writes:
            if type(write) is not NativeClaimsWrite:
                _fail("explicit original write required")
            self._settled(write)
        checked = self.read_original_write_result(writes[-1], retained_original=retained_original)
        originals = tuple(p.write for p in checked.predecessors) + (checked.write,)
        if len(writes) != len(originals) or not all(self._same_original_write(a, b) for a, b in zip(writes, originals)):
            _fail("missing, duplicate, reordered or foreign original write chain")
        return checked

    def reconcile_original_write(self, write, *, retained_original=None):
        self.read_original_write_result(write, retained_original=retained_original)
        return super().reconcile_original_write(write)

    def prepare_publication_candidate(self, write, *, accepted_tip_oid, accepted_ref,
                                      commit_metadata, retained_original=None):
        """Retain original authority; prepare, never execute, current publication.

        Original apply/clock uncertainty is not cleared by this representation
        check. Caller must consume actual owner failure and release gates.
        """
        checked = self.read_original_write_result(write, retained_original=retained_original)
        return git_candidate.prepare_native_publication_candidate(self.repo_root,
            accepted_tip_oid=accepted_tip_oid, accepted_ref=accepted_ref,
            native_operation_receipt=checked.native_operation_receipt, commit_metadata=commit_metadata,
            target_ref=checked.target_ref, limits=self.limits)

    def check_publication_candidate(self, write, *, candidate_oid, expected_tree_oid, accepted_tip_oid,
                                    accepted_ref, retained_original=None):
        """Fresh binding for the incumbent's actual complete frozen candidate.

        This neither substitutes the claims-only prepared tree nor publishes.
        Native apply/clock outcomes and all release gates remain independent.
        """
        checked = self.read_original_write_result(write, retained_original=retained_original)
        return git_candidate.bind_current_native_publication(self.repo_root,
            candidate_oid=candidate_oid, expected_tree_oid=expected_tree_oid,
            accepted_tip_oid=accepted_tip_oid, accepted_ref=accepted_ref,
            native_operation_receipt=checked.native_operation_receipt, target_ref=checked.target_ref, limits=self.limits)
