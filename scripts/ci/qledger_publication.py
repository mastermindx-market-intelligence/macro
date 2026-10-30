"""Explicit QLedger publication checks for the existing publication owners.

The production entry point always asks the claims owner's hard-legacy selector.
The native APIs accept explicit verified inputs; they neither discover a format,
grant custody, mutate a Git ref/index/worktree, nor run registration or clocks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import selectors
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.qledger_store_protocol import (  # noqa: E402
    BASE_PATH, BlobInfo, ProtocolLimits, RebasePlan, SnapshotIntegrityError,
    VerifiedSnapshot, open_logical_bytes, rebase_verified_pending, validate_publication,
)
from engine.qledger_store_sources import (  # noqa: E402
    GitTreeSource, read_legacy_claims_blob, verify_source_snapshot,
)

_OID = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_REF = re.compile(r"refs/heads/[A-Za-z0-9][A-Za-z0-9._/-]{0,220}\Z")
_GIT_TIMEOUT = 30.0
_MAX_BASELINES = 128


def _fail(code: str, message: str) -> None:
    raise SnapshotIntegrityError(code, message)


def _oid(value: str) -> str:
    if type(value) is not str or not _OID.fullmatch(value):
        _fail("PUBLICATION_INPUT", "an explicit full Git object identity is required")
    return value


def _profile(limits: ProtocolLimits) -> None:
    if type(limits) is not ProtocolLimits:
        _fail("PUBLICATION_INPUT", "an exact protocol limit profile is required")
    # Reconstructing invokes the supported-ceiling checks on every public field.
    if ProtocolLimits(**asdict(limits)).fingerprint != limits.fingerprint:
        _fail("PUBLICATION_INPUT", "profile identity changed")


def _repo(repo: Path) -> Path:
    if not isinstance(repo, Path) or not repo.is_absolute():
        _fail("PUBLICATION_INPUT", "an explicit absolute repository root is required")
    return repo


def _git(
    repo: Path, args: list[str], *, output_limit: int,
    input_bytes: bytes | None = None, allowed_codes: tuple[int, ...] = (0,),
) -> tuple[bytes, int]:
    """Read bounded local Git output without lazy fetch or replacement objects."""
    _repo(repo)
    env = dict(os.environ)
    for key in (
        "GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_NAMESPACE", "GIT_REPLACE_REF_BASE", "GIT_SHALLOW_FILE",
    ):
        env.pop(key, None)
    # Inventory literal commit ancestry. Replacement refs, local/environment
    # grafts, and supplemental commit graphs must not hide introduced objects.
    # The repository's actual shallow marker remains authoritative.
    env.update({"GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1",
                "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
                "GIT_GRAFT_FILE": os.devnull})
    command = ["git", "--no-replace-objects", "-c", "protocol.allow=never",
               "-c", "core.commitGraph=false", "-c", "advice.graftFileDeprecated=false",
               "-C", str(repo), *args]
    # A bounded file avoids a stdin/stdout pipe deadlock for batch-check input.
    with tempfile.TemporaryFile() as supplied:
        if input_bytes is not None:
            supplied.write(input_bytes)
            supplied.seek(0)
        try:
            proc = subprocess.Popen(command, stdin=supplied, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, env=env)
        except OSError as exc:
            raise SnapshotIntegrityError("GIT_READ", "local Git could not start") from exc
        data = bytearray()
        deadline = time.monotonic() + _GIT_TIMEOUT
        try:
            assert proc.stdout is not None
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        _fail("GIT_READ", "bounded local Git read timed out")
                    ready = selector.select(remaining)
                    if not ready:
                        _fail("GIT_READ", "bounded local Git read timed out")
                    for key, _event in ready:
                        chunk = os.read(key.fd, min(65536, output_limit - len(data) + 1))
                        if not chunk:
                            selector.unregister(key.fileobj)
                            continue
                        if len(data) + len(chunk) > output_limit:
                            _fail("NONRETRYABLE_CAPACITY", "Git output exceeds the inventory budget")
                        data.extend(chunk)
            try:
                code = proc.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                raise SnapshotIntegrityError("GIT_READ", "local Git did not finish") from exc
            if code not in allowed_codes:
                _fail("GIT_READ", "local Git could not prove the requested object inventory")
            return bytes(data), code
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if proc.stdout is not None:
                proc.stdout.close()


def _complete_repository(repo: Path) -> None:
    raw, _ = _git(repo, ["rev-parse", "--is-shallow-repository"], output_limit=128)
    if raw != b"false\n":
        _fail("INCOMPLETE", "shallow or indeterminate history cannot prove publication ancestry")


def _object_type(repo: Path, oid: str, expected: str) -> None:
    _oid(oid)
    raw, _ = _git(repo, ["cat-file", "-t", oid], output_limit=128)
    if raw != expected.encode("ascii") + b"\n":
        _fail("PUBLICATION_INPUT", "the supplied Git identity has the wrong object type")


def _commit_tree(repo: Path, commit_oid: str, *, limits: ProtocolLimits) -> str:
    _object_type(repo, commit_oid, "commit")
    raw_size, _ = _git(repo, ["cat-file", "-s", commit_oid], output_limit=128)
    if not re.fullmatch(rb"[0-9]+\n", raw_size):
        _fail("GIT_READ", "invalid commit object size")
    size = int(raw_size)
    if size > limits.page_bytes:
        _fail("NONRETRYABLE_CAPACITY", "commit metadata exceeds the supported budget")
    raw, _ = _git(repo, ["cat-file", "commit", commit_oid], output_limit=size)
    digest = hashlib.sha1 if len(commit_oid) == 40 else hashlib.sha256
    if len(raw) != size or digest(b"commit " + str(size).encode() + b"\0" + raw).hexdigest() != commit_oid:
        _fail("HASH_MISMATCH", "commit bytes do not match the supplied identity")
    first = raw.split(b"\n", 1)[0]
    if not first.startswith(b"tree "):
        _fail("INCOMPLETE", "commit has no explicit root tree")
    try:
        tree = _oid(first[5:].decode("ascii"))
    except UnicodeError as exc:
        raise SnapshotIntegrityError("INCOMPLETE", "invalid commit root tree") from exc
    _object_type(repo, tree, "tree")
    return tree


def _baselines(repo: Path, values: Iterable[str], *, limits: ProtocolLimits) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        _fail("PUBLICATION_INPUT", "baseline identities must be an explicit finite sequence")
    out: list[str] = []
    seen: set[str] = set()
    try:
        iterator = iter(values)
    except TypeError as exc:
        raise SnapshotIntegrityError("PUBLICATION_INPUT", "baseline sequence is missing") from exc
    for value in iterator:
        if len(out) >= min(_MAX_BASELINES, limits.reference_visits):
            _fail("NONRETRYABLE_CAPACITY", "accepted baseline inventory exceeds the budget")
        value = _oid(value)
        if value in seen:
            _fail("PUBLICATION_INPUT", "duplicate accepted baseline")
        seen.add(value)
        _commit_tree(repo, value, limits=limits)
        out.append(value)
    if not out:
        _fail("PUBLICATION_INPUT", "accepted baseline identities are required")
    # Excluding accepted tips prunes their old objects from the introduced walk.
    # Prove their complete local history first, without reclassifying accepted
    # blobs as newly introduced or applying the new-blob size ceiling to them.
    baselines = tuple(out)
    _reachable_metadata(repo, baselines, (), limits=limits)
    return baselines


def _ancestor(repo: Path, ancestor: str, descendant: str) -> None:
    _raw, code = _git(repo, ["merge-base", "--is-ancestor", _oid(ancestor), _oid(descendant)],
                     output_limit=4096, allowed_codes=(0, 1))
    if code:
        _fail("CONFLICT", "the accepted target tip is not an ancestor of the candidate")


def _reachable_metadata(
    repo: Path, roots: tuple[str, ...], excluded: tuple[str, ...], *, limits: ProtocolLimits,
) -> tuple[tuple[str, bytes, int], ...]:
    """Prove bounded local object presence before using a reachability inventory."""
    args = ["rev-list", "--objects", "--no-object-names", "--missing=print", *roots]
    if excluded:
        args.extend(["--not", *excluded])
    raw, _ = _git(repo, args, output_limit=limits.publication_objects * 66)
    if raw and not raw.endswith(b"\n"):
        _fail("INCOMPLETE", "truncated reachable-object inventory")
    objects: list[str] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        if len(objects) >= limits.publication_objects:
            _fail("NONRETRYABLE_CAPACITY", "reachable-object count exceeds the budget")
        try:
            oid = line.decode("ascii")
        except UnicodeError as exc:
            raise SnapshotIntegrityError("GIT_READ", "invalid reachable-object identity") from exc
        if oid.startswith("?"):
            _fail("INCOMPLETE", "a reachable object is missing locally")
        _oid(oid)
        if oid in seen:
            _fail("INCOMPLETE", "duplicate reachable-object inventory row")
        seen.add(oid)
        objects.append(oid)
    if not objects:
        return ()
    supplied = ("\n".join(objects) + "\n").encode("ascii")
    raw, _ = _git(repo, ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                  input_bytes=supplied, output_limit=len(objects) * 100)
    if not raw.endswith(b"\n"):
        _fail("INCOMPLETE", "truncated reachable-object metadata")
    rows = raw.splitlines()
    if len(rows) != len(objects):
        _fail("INCOMPLETE", "reachable-object metadata is incomplete")
    metadata: list[tuple[str, bytes, int]] = []
    for wanted, row in zip(objects, rows):
        fields = row.split(b" ")
        if len(fields) != 3 or fields[0] != wanted.encode() or not re.fullmatch(rb"[0-9]+", fields[2]):
            _fail("INCOMPLETE", "missing or malformed reachable-object metadata")
        if fields[1] not in (b"commit", b"tree", b"blob", b"tag"):
            _fail("INCOMPLETE", "unknown reachable object type")
        metadata.append((wanted, fields[1], int(fields[2])))
    return tuple(metadata)


def _introduced(
    repo: Path, roots: tuple[str, ...], baselines: tuple[str, ...], *, limits: ProtocolLimits,
) -> tuple[BlobInfo, ...]:
    blobs: list[BlobInfo] = []
    for oid, kind, size in _reachable_metadata(repo, roots, baselines, limits=limits):
        if kind == b"blob":
            if size > limits.git_blob_bytes:
                _fail("NONRETRYABLE_OVERSIZE", "a newly reachable blob exceeds the publication bound")
            blobs.append(BlobInfo(oid, size))
    return tuple(blobs)


def enumerate_introduced_blobs(
    repo: Path, *, candidate_oid: str, accepted_baseline_oids: Iterable[str],
    limits: ProtocolLimits,
) -> tuple[BlobInfo, ...]:
    """Check the full newly reachable history, not only the final candidate tree."""
    _profile(limits)
    _complete_repository(repo)
    _commit_tree(repo, candidate_oid, limits=limits)
    baselines = _baselines(repo, accepted_baseline_oids, limits=limits)
    return _introduced(repo, (_oid(candidate_oid),), baselines, limits=limits)


@dataclass(frozen=True)
class NativePublicationBinding:
    operation_id: str
    lane_id: str
    target_ref: str
    accepted_tip_oid: str
    expected_root_digest: str


@dataclass(frozen=True)
class PublicationGateResult:
    status: str
    tree_oid: str | None = None
    candidate_oid: str | None = None
    parent_commit_oid: str | None = None
    target_ref: str | None = None
    accepted_baseline_oids: tuple[str, ...] = ()
    root_digest: str | None = None
    introduced_blobs: int | None = None
    operation_id: str | None = None
    lane_id: str | None = None
    effect: str = "not_attempted"


def _native_binding(binding: object) -> bool:
    from engine.qledger_store import LegacyClaimsBinding

    if type(binding) is LegacyClaimsBinding:
        return False
    if type(binding) is not NativePublicationBinding:
        _fail("PUBLICATION_INPUT", "an explicit owner binding is required")
    for tag in (binding.operation_id, binding.lane_id):
        if type(tag) is not str or not _TAG.fullmatch(tag):
            _fail("PUBLICATION_INPUT", "invalid native operation or lane tag")
    if (type(binding.target_ref) is not str or not _REF.fullmatch(binding.target_ref)
            or ".." in binding.target_ref or "//" in binding.target_ref or binding.target_ref.endswith("/")
            or any(x.endswith((".", ".lock")) or x.startswith(".") for x in binding.target_ref.split("/"))):
        _fail("PUBLICATION_INPUT", "an exact supported target branch ref is required")
    _oid(binding.accepted_tip_oid)
    if type(binding.expected_root_digest) is not str or not _DIGEST.fullmatch(binding.expected_root_digest):
        _fail("PUBLICATION_INPUT", "an explicit expected claims root digest is required")
    return True


def _candidate_snapshot(repo: Path, tree_oid: str, binding: NativePublicationBinding, *, limits: ProtocolLimits):
    source = GitTreeSource(repo, tree_oid=_oid(tree_oid), limits=limits)
    snapshot = verify_source_snapshot(source, limits=limits)
    if snapshot.receipt.root_digest != binding.expected_root_digest:
        _fail("CONFLICT", "the exact candidate carries a different claims root")
    return source, snapshot


def check_frozen_tree(
    repo: Path, *, tree_oid: str, parent_commit_oid: str,
    accepted_baseline_oids: Iterable[str], binding: object, limits: ProtocolLimits,
) -> PublicationGateResult:
    """Validate the existing commit owner's frozen tree before it installs a ref."""
    if not _native_binding(binding):
        return PublicationGateResult("LEGACY_SELECTED")
    _profile(limits)
    _complete_repository(repo)
    _object_type(repo, tree_oid, "tree")
    _commit_tree(repo, parent_commit_oid, limits=limits)
    baselines = _baselines(repo, accepted_baseline_oids, limits=limits)
    if binding.accepted_tip_oid not in baselines:
        _fail("PUBLICATION_INPUT", "accepted target tip is absent from the baseline set")
    _ancestor(repo, binding.accepted_tip_oid, parent_commit_oid)
    source, snapshot = _candidate_snapshot(repo, tree_oid, binding, limits=limits)
    # Include unpublished parent commits and the newly staged tree. An oversized
    # intermediate object is still introduced even when this tree deletes it.
    blobs = _introduced(repo, (tree_oid, parent_commit_oid), baselines, limits=limits)
    checked = validate_publication(source, snapshot.root, blobs, limits=limits)
    return PublicationGateResult(
        "NATIVE_VERIFIED", tree_oid=tree_oid, parent_commit_oid=parent_commit_oid,
        target_ref=binding.target_ref, accepted_baseline_oids=baselines,
        root_digest=checked.root_digest, introduced_blobs=checked.introduced_blobs,
        operation_id=binding.operation_id, lane_id=binding.lane_id,
    )


def check_publish_candidate(
    repo: Path, *, candidate_oid: str, accepted_baseline_oids: Iterable[str],
    target_ref: str, binding: object, limits: ProtocolLimits,
) -> PublicationGateResult:
    """Validate the named push candidate, which may be different from HEAD."""
    if not _native_binding(binding):
        return PublicationGateResult("LEGACY_SELECTED")
    _profile(limits)
    if target_ref != binding.target_ref:
        _fail("CONFLICT", "push target differs from the explicit owner binding")
    _complete_repository(repo)
    tree = _commit_tree(repo, candidate_oid, limits=limits)
    baselines = _baselines(repo, accepted_baseline_oids, limits=limits)
    if binding.accepted_tip_oid not in baselines:
        _fail("PUBLICATION_INPUT", "accepted target tip is absent from the baseline set")
    _ancestor(repo, binding.accepted_tip_oid, candidate_oid)
    source, snapshot = _candidate_snapshot(repo, tree, binding, limits=limits)
    blobs = _introduced(repo, (candidate_oid,), baselines, limits=limits)
    checked = validate_publication(source, snapshot.root, blobs, limits=limits)
    return PublicationGateResult(
        "NATIVE_VERIFIED", tree_oid=tree, candidate_oid=candidate_oid,
        target_ref=target_ref, accepted_baseline_oids=baselines,
        root_digest=checked.root_digest, introduced_blobs=checked.introduced_blobs,
        operation_id=binding.operation_id, lane_id=binding.lane_id,
    )


@dataclass(frozen=True)
class NativeOperationReceipt:
    operation_id: str
    lane_id: str
    original_base_snapshot: VerifiedSnapshot
    original_candidate_snapshot: VerifiedSnapshot
    authorized_transaction_ids: tuple[str, ...]
    limits: ProtocolLimits


def _receipt(value: NativeOperationReceipt) -> None:
    if type(value) is not NativeOperationReceipt:
        _fail("UNKNOWN_PENDING", "native pending work has no explicit operation receipt")
    for tag in (value.operation_id, value.lane_id):
        if type(tag) is not str or not _TAG.fullmatch(tag):
            _fail("UNKNOWN_PENDING", "native pending work has invalid identity tags")
    if type(value.authorized_transaction_ids) is not tuple:
        _fail("UNKNOWN_PENDING", "native ordered transaction intent must be immutable")
    _profile(value.limits)


def classify_pending(
    candidate_snapshot: VerifiedSnapshot, *, native_operation_receipt: NativeOperationReceipt,
) -> dict[str, object]:
    """Prove exact ordered pending storage intent; tags are not a custody grant."""
    receipt = native_operation_receipt
    _receipt(receipt)
    # Public D0 verification rejects forged/stale snapshots and incomplete,
    # reordered or extra IDs before reconstructing any pending plan.
    checked = rebase_verified_pending(
        receipt.original_base_snapshot,
        original_base_snapshot=receipt.original_base_snapshot,
        original_candidate_snapshot=candidate_snapshot,
        authorized_transaction_ids=receipt.authorized_transaction_ids,
        limits=receipt.limits,
    )
    expected = rebase_verified_pending(
        receipt.original_base_snapshot,
        original_base_snapshot=receipt.original_base_snapshot,
        original_candidate_snapshot=receipt.original_candidate_snapshot,
        authorized_transaction_ids=receipt.authorized_transaction_ids,
        limits=receipt.limits,
    )
    if checked.snapshot.root_bytes != expected.snapshot.root_bytes:
        _fail("UNKNOWN_PENDING", "candidate differs from the explicit pending operation")
    return {"status": "KNOWN_NATIVE_PENDING" if receipt.authorized_transaction_ids else "NATIVE_NO_PENDING",
            "operation_id": receipt.operation_id, "lane_id": receipt.lane_id,
            "root_digest": checked.snapshot.receipt.root_digest,
            "transaction_ids": receipt.authorized_transaction_ids,
            "scope": "verified snapshots and supplied native intent", "effect": "not_attempted"}


def rebase_native_pending(
    remote_snapshot: VerifiedSnapshot, *, native_operation_receipt: NativeOperationReceipt,
) -> RebasePlan:
    receipt = native_operation_receipt
    _receipt(receipt)
    return rebase_verified_pending(
        remote_snapshot,
        original_base_snapshot=receipt.original_base_snapshot,
        original_candidate_snapshot=receipt.original_candidate_snapshot,
        authorized_transaction_ids=receipt.authorized_transaction_ids,
        limits=receipt.limits,
    )


def _require_direct_candidate(
    repo: Path, candidate_oid: str, accepted_tip_oid: str, *,
    limits: ProtocolLimits, allow_already_accepted: bool = False,
) -> None:
    """Do not certify a stale anchor across unaccounted intermediate commits.

    Native no-op readback may name the already accepted commit itself. Every
    new candidate is one single-parent commit directly over the supplied tip.
    Other histories require their original owner's explicit reconciliation.
    """
    if candidate_oid == accepted_tip_oid and allow_already_accepted:
        return
    raw, _ = _git(repo, ["cat-file", "commit", _oid(candidate_oid)],
                  output_limit=limits.page_bytes)
    digest = hashlib.sha1 if len(candidate_oid) == 40 else hashlib.sha256
    if digest(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest() != candidate_oid:
        _fail("HASH_MISMATCH", "candidate ancestry bytes changed after publication validation")
    parents = [line[7:] for line in raw.split(b"\n\n", 1)[0].split(b"\n")
               if line.startswith(b"parent ")]
    if parents != [_oid(accepted_tip_oid).encode("ascii")]:
        _fail("CONFLICT", "candidate must have exactly the supplied accepted tip as its sole parent")


@dataclass(frozen=True)
class PublicationContinuityWitness:
    """Mechanical proof for explicitly supplied objects, never release authority.

    The caller still owns remote-tip acceptance, historical issuer rights,
    mixed-version writer exclusion and production admission. No returned field
    grants custody or changes the current hard-legacy production selection.
    """

    status: str
    publication: PublicationGateResult
    source_tree_oid: str
    source_logical_digest: str
    source_logical_bytes: int
    source_blob_oid: str | None
    transaction_ids: tuple[str, ...]
    accepted_tip_oid: str
    planned_transaction_ids: tuple[str, ...] = ()
    already_present_transaction_ids: tuple[str, ...] = ()
    source_assurance: str = "EXPLICIT_GIT_OBJECTS_NOT_REMOTE_ACCEPTANCE"
    source_generation_scope: str = "UNVERIFIED_EXTERNAL_AUTHORITY"
    effect: str = "not_attempted"
    eligible_for_cutover: bool = False


def check_legacy_conversion_candidate(
    repo: Path, *, candidate_oid: str, accepted_baseline_oids: Iterable[str],
    target_ref: str, binding: NativePublicationBinding,
    expected_legacy_blob_oid: str, conversion_transaction_id: str,
    limits: ProtocolLimits,
) -> PublicationContinuityWitness:
    """Bind a zero-base conversion to exact legacy Git bytes without migrating.

    Candidate integrity and object bounds are insufficient by themselves: the
    converted ordered stream must be the exact prior source, and its sole
    storage transaction must be the explicitly supplied conversion identity.
    """
    if not _native_binding(binding):
        _fail("PUBLICATION_INPUT", "conversion proof requires an explicit native binding")
    _profile(limits)
    if type(conversion_transaction_id) is not str or not _TAG.fullmatch(conversion_transaction_id):
        _fail("PUBLICATION_INPUT", "an explicit conversion transaction identity is required")
    # Reject invalid binding, inventory and ancestry before loading the legacy
    # body. A candidate may not silently skip any post-tip source commit.
    publication = check_publish_candidate(
        repo, candidate_oid=candidate_oid, accepted_baseline_oids=accepted_baseline_oids,
        target_ref=target_ref, binding=binding, limits=limits,
    )
    _require_direct_candidate(repo, candidate_oid, binding.accepted_tip_oid, limits=limits)
    source_tree = _commit_tree(repo, binding.accepted_tip_oid, limits=limits)
    original = read_legacy_claims_blob(
        repo, tree_oid=source_tree, expected_blob_oid=expected_legacy_blob_oid, limits=limits,
    )
    if not original.raw_bytes or not original.raw_bytes.endswith(b"\n"):
        _fail("CONVERSION_INPUT", "conversion requires a nonempty LF-terminated legacy source")
    _, candidate = _candidate_snapshot(repo, publication.tree_oid, binding, limits=limits)
    transactions = candidate._transactions
    if len(transactions) > 1:
        _fail("CAPACITY", "conversion supports exactly one bounded append transaction")
    if (candidate.root.base.size != 0 or candidate.root.base.digest != hashlib.sha256(b"").hexdigest()
            or len(transactions) != 1 or transactions[0].kind != "append"
            or transactions[0].transaction_id != conversion_transaction_id):
        _fail("CONFLICT", "conversion must have an empty base and the one declared append transaction")
    if (candidate.root.logical_size != original.byte_count
            or candidate.root.logical_digest != original.logical_digest):
        _fail("CONFLICT", "conversion differs from the exact legacy logical stream")
    # Compare bytes without parsing, sorting, deduplicating or allocating another
    # complete copy. Ordered raw occurrences and legacy malformed lines survive.
    original_view = memoryview(original.raw_bytes)
    offset = 0
    with open_logical_bytes(candidate) as stream:
        while chunk := stream.read(65536):
            if chunk != original_view[offset:offset + len(chunk)]:
                _fail("CONFLICT", "conversion changed the original ordered raw bytes")
            offset += len(chunk)
    if offset != original.byte_count:
        _fail("CONFLICT", "conversion did not retain the complete legacy source")
    return PublicationContinuityWitness(
        "LEGACY_CONVERSION_VERIFIED", publication, source_tree,
        original.logical_digest, original.byte_count, original.blob_oid,
        (conversion_transaction_id,), binding.accepted_tip_oid,
        planned_transaction_ids=(conversion_transaction_id,),
        source_generation_scope="ACCEPTED_PREFIX_ONLY",
    )


def check_native_operation_candidate(
    repo: Path, *, candidate_oid: str, accepted_baseline_oids: Iterable[str],
    target_ref: str, binding: NativePublicationBinding,
    native_operation_receipt: NativeOperationReceipt, limits: ProtocolLimits,
) -> PublicationContinuityWitness:
    """Connect actual Git trees to the existing exact pending/rebase contract.

    The receipt records supplied operation intent, not a claim that an external
    authority assigned it. Both the candidate and named accepted tip are read
    from immutable Git objects, never substituted from a current working tree.
    """
    if not _native_binding(binding):
        _fail("PUBLICATION_INPUT", "native continuity requires an explicit native binding")
    _profile(limits)
    _receipt(native_operation_receipt)
    receipt = native_operation_receipt
    if (receipt.operation_id != binding.operation_id or receipt.lane_id != binding.lane_id
            or receipt.limits.fingerprint != limits.fingerprint):
        _fail("CONFLICT", "operation, lane or limits differ from the explicit publisher binding")
    publication = check_publish_candidate(
        repo, candidate_oid=candidate_oid, accepted_baseline_oids=accepted_baseline_oids,
        target_ref=target_ref, binding=binding, limits=limits,
    )
    _require_direct_candidate(repo, candidate_oid, binding.accepted_tip_oid,
                              limits=limits, allow_already_accepted=True)
    source_tree = _commit_tree(repo, binding.accepted_tip_oid, limits=limits)
    accepted = verify_source_snapshot(GitTreeSource(repo, tree_oid=source_tree, limits=limits), limits=limits)
    required = rebase_native_pending(accepted, native_operation_receipt=receipt)
    _, candidate = _candidate_snapshot(repo, publication.tree_oid, binding, limits=limits)
    if candidate.root_bytes != required.snapshot.root_bytes:
        _fail("CONFLICT", "Git candidate is not the accepted prefix plus the declared pending transactions")
    return PublicationContinuityWitness(
        "NATIVE_OPERATION_VERIFIED", publication, source_tree,
        accepted.receipt.logical_digest, accepted.receipt.logical_size, None,
        receipt.authorized_transaction_ids, binding.accepted_tip_oid,
        planned_transaction_ids=required.applied,
        already_present_transaction_ids=required.already_applied,
        source_generation_scope="NATIVE_OPERATION_BOUNDED_NOT_EXTERNAL_AUTHORITY",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--boundary", choices=("frozen-tree", "publish-candidate", "pre-rebase"), required=True)
    parser.add_argument("--tree")
    parser.add_argument("--parent")
    parser.add_argument("--candidate")
    parser.add_argument("--target-ref")
    parser.add_argument("--accepted-baseline", action="append", default=[])
    parser.add_argument("--push-arg", action="append", default=[])
    parser.add_argument("--conversion-result", type=Path)
    parser.add_argument("--conversion-manifest-sha256")
    parser.add_argument("--conversion-accepted-tip")
    args = parser.parse_args(argv)
    try:
        from engine.qledger_store import LegacyClaimsBinding, _production_claims_binding, _require_legacy_namespace
        repo = _repo(args.repo)
        explicit = (args.conversion_result, args.conversion_manifest_sha256, args.conversion_accepted_tip)
        if any(value is not None for value in explicit):
            if not all(value is not None for value in explicit):
                _fail("PUBLICATION_INPUT", "complete explicit original-conversion invocation required")
            from scripts.ci.qledger_owner_invocation import load_conversion
            invocation = load_conversion(repo, result_path=args.conversion_result,
                                         manifest_digest=args.conversion_manifest_sha256)
            if args.accepted_baseline and args.accepted_baseline != [args.conversion_accepted_tip]:
                _fail("PUBLICATION_INPUT", "incumbent baseline differs from original invocation")
            result = invocation.preflight(boundary=args.boundary,
                accepted_tip_oid=args.conversion_accepted_tip, tree_oid=args.tree,
                parent_oid=args.parent, candidate_oid=args.candidate,
                target_ref=args.target_ref or "refs/heads/main", push_args=tuple(args.push_arg))
            print(json.dumps({"status": result.status, "boundary": args.boundary,
                              "effect": "validation_only"}, sort_keys=True))
            return 0
        binding = _production_claims_binding(repo / BASE_PATH)
        if type(binding) is not LegacyClaimsBinding:
            _fail("PUBLICATION_INPUT", "native publication needs a separately admitted explicit owner binding")
        _require_legacy_namespace(repo / BASE_PATH)
        # Pure default selection remains legacy. A native checkout requires
        # the separately bound owner API; this CLI never enrolls it.
        print(json.dumps({"status": "LEGACY_SELECTED", "boundary": args.boundary,
                          "effect": "not_attempted"}, sort_keys=True))
        return 0
    except SnapshotIntegrityError as exc:
        print(json.dumps({"status": "REJECTED", "code": exc.code,
                          "effect": "not_attempted"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
