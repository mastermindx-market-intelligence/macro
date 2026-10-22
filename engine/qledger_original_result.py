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
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from types import MappingProxyType

from engine.qledger_store import NativeClaimsWrite
from engine.qledger_store_native import NativeClaimsIntent, NativeClaimsSession, _sync_dir, _sync_file, _write_all
from engine.qledger_store_protocol import (
    ROOT_PATH, InMemorySource, ProtocolLimits, SnapshotIntegrityError,
    restore_original_plan, validate_plan, verify_snapshot, decode_root,
)
from engine.qledger_store_sources import _absolute, _file_identity, _member_limit, _open_directory
from scripts.ci import qledger_conversion_candidate as git_candidate
from scripts.ci.qledger_publication import NativeOperationReceipt, classify_pending

_SCHEMA = "qledger-original-result/v1"
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


@dataclass(frozen=True, init=False)
class RetainedOriginalResult:
    owner_root: Path
    result_path: Path
    result_id: str
    manifest_digest: str
    write: NativeClaimsWrite
    native_operation_receipt: NativeOperationReceipt
    candidate_oid: str
    limits: ProtocolLimits
    _seal: object


def _target(path):
    path = _absolute(path)
    if path.parts[-3:] != ("data", "qledger", "claims.jsonl"):
        _fail("an explicit canonical claims path is required")
    return path


def prepare_original_result(write, *, candidate, result_id, limits):
    """Read qualified Git inputs and prepare ONE causal write's original result.

    This cannot retain/reclassify older tails, combine operations or mint IDs.
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
    receipt, _ = git_candidate.read_native_operation_candidate(
        write.claims_path.parents[2], candidate_oid=candidate.candidate_oid,
        accepted_tip_oid=candidate.continuity.accepted_tip_oid,
        operation_id=write.intent.operation_id, lane_id=write.intent.lane_id,
        authorized_transaction_ids=(write.intent.transaction_id,),
        commit_metadata=candidate.commit_metadata,
        target_ref=candidate.continuity.publication.target_ref, limits=limits)
    if (receipt.original_base_snapshot.root_bytes != write.plan._before.root_bytes
            or receipt.original_candidate_snapshot.root_bytes != write.plan.snapshot.root_bytes):
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
    raw = _json(manifest)
    if (len(objects) > limits.snapshot_members or sum(map(len, objects.values())) + len(raw) > limits.snapshot_bytes
            or len(raw) > _manifest_bound(limits)):
        _fail("original result exceeds existing inventory/byte bounds")
    return PreparedOriginalResult(result_id, write, limits, raw, sha256(raw).hexdigest(),
                                  MappingProxyType(objects), _SEAL)


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
        expected_claims_path=prepared.write.claims_path, expected_intent=prepared.write.intent, limits=prepared.limits)


def read_original_result(*, owner_root, result_path, expected_result_id, expected_manifest_digest,
                         expected_claims_path, expected_intent, limits):
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
        raw = _read(result_fd, "manifest.json", _manifest_bound(limits), identities)
        if sha256(raw).hexdigest() != expected_manifest_digest:
            _fail("original manifest differs from expected immutable identity")
        manifest = json.loads(raw)
        if (type(manifest) is not dict or _json(manifest) != raw
                or set(manifest) != {"schema", "result_id", "claims_path", "intent", "limits", "base", "candidate", "git"}
                or manifest["schema"] != _SCHEMA or manifest["result_id"] != expected_result_id
                or manifest["claims_path"] != str(expected_claims_path)
                or manifest["intent"] != asdict(expected_intent) or manifest["limits"] != asdict(limits)):
            _fail("foreign or noncanonical original-result manifest")
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
        names = _entries(members_fd, limits.snapshot_members)
        if len(names) > limits.snapshot_members or set(names) != set(maxima):
            _fail("incomplete or unexpected original object inventory")
        total = 0
        for digest in names:
            total += os.stat(digest, dir_fd=members_fd, follow_symlinks=False).st_size
        if total + len(raw) > limits.snapshot_bytes:
            _fail("original object inventory/manifest exceeds byte bound")
        objects = {}
        remaining = limits.snapshot_bytes - len(raw)
        for digest, maximum in maxima.items():
            # Metadata census is only an early refusal. Bound actual allocation
            # even if a member grows before its stable no-follow read begins.
            payload = _read(members_fd, digest, min(maximum, remaining), identities)
            remaining -= len(payload)
            if sha256(payload).hexdigest() != digest:
                _fail("original member hash mismatch")
            objects[digest] = payload
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
            candidate_oid=git["candidate_oid"], limits=limits, _seal=_SEAL).items():
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
        expected_claims_path=write.claims_path, expected_intent=write.intent, limits=retained.limits)
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
