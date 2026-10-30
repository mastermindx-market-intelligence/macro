"""Prepare an isolated Git conversion candidate, never a live-store cutover.

Only immutable Git objects are written. No ref, index, worktree, live claims
file, production binding or clock is changed. The explicitly named local
accepted ref is checked before and after preparation; this does not authenticate
remote acceptance, exclude launchers or settle old file descriptors. Publication
still needs a fresh remote-tip fence, complete accepted-history qualification,
coherent native readers/writers and actual old-writer exclusion.

Do not replay a rejected commit or attach its oversized ancestry here. Pending
unpublished claims retain their separate original provenance and reconciliation.
This API converts ONLY the exact claims blob in the supplied accepted parent.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
from pathlib import Path
import re
import sys

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.qledger_store_conversion import plan_legacy_conversion  # noqa: E402
from engine.qledger_store_protocol import ROOT_PATH, ProtocolLimits, SnapshotIntegrityError  # noqa: E402
from engine.qledger_store_sources import GitTreeSource, read_legacy_claims_blob, verify_source_snapshot  # noqa: E402
from scripts.ci import qledger_publication as publication  # noqa: E402


@dataclass(frozen=True)
class CandidateCommitMetadata:
    """Fixed operation bookkeeping, never a claim or publication clock.

    The assigning operation retains these explicit inputs for reconciliation.
    This module does not select a current time or borrow an accepted commit's
    date, and creates no operation ledger. Both Git identities use this value.
    """

    name: str
    email: str
    timestamp: int

    def git_identity(self) -> str:
        if (type(self.name) is not str or not 1 <= len(self.name) <= 128
                or self.name.strip() != self.name
                or any(ord(c) < 32 or ord(c) > 126 or c in "<>" for c in self.name)
                or type(self.email) is not str
                or re.fullmatch(r"[A-Za-z0-9._+~-]{1,64}@[A-Za-z0-9.-]{1,190}", self.email) is None
                or type(self.timestamp) is not int
                or not 0 <= self.timestamp <= 253402300799):
            raise SnapshotIntegrityError("PUBLICATION_INPUT", "invalid explicit Git commit metadata")
        return f"{self.name} <{self.email}> {self.timestamp} +0000"


@dataclass(frozen=True)
class AcceptedPrefixQualification:
    """Source identity, not complete-authority or production admission.

    These fields identify ONLY the source blob in the named accepted Git parent.
    The converter cannot observe unpublished appends, rejected rows, corrections,
    failed-push tails or unresolved original operations in another authoritative
    incarnation. A second later source history may yield this identical receipt.
    No caller may turn this record into COMPLETE_AUTHORITY_GENERATION.
    """

    accepted_tip_oid: str
    accepted_ref: str
    source_blob_oid: str
    source_logical_sha256: str
    source_byte_count: int
    scope: str = "ACCEPTED_PREFIX_ONLY"


def require_complete_authority_generation(source: AcceptedPrefixQualification) -> None:
    """Explicit fail-closed cutover barrier for an accepted-parent-only input.

    The real original ledger owner has not supplied an attributable complete
    source cut. Matching Git ancestry, blob bytes or immutable member hashes
    cannot substitute for that missing external authority. There is currently
    NO success path for converting this prefix receipt into current authority.
    """
    if type(source) is not AcceptedPrefixQualification or source.scope != "ACCEPTED_PREFIX_ONLY":
        raise SnapshotIntegrityError("PUBLICATION_INPUT", "exact accepted-prefix source receipt required")
    raise SnapshotIntegrityError(
        "MISSING_AUTHORITY_GENERATION_BOUNDARY",
        "accepted Git parent proves only a prefix, not all original claims and later tails",
    )


@dataclass(frozen=True)
class PreparedConversionCandidate:
    candidate_oid: str
    tree_oid: str
    accepted_ref: str
    commit_metadata: CandidateCommitMetadata
    continuity: publication.PublicationContinuityWitness
    source_qualification: AcceptedPrefixQualification
    effect: str = "unreferenced_git_objects_only"

    def require_complete_current_generation(self) -> None:
        """Never promote this prefix-only conversion by reading a cache/flag."""
        require_complete_authority_generation(self.source_qualification)


def _ref_matches(repo: Path, ref: str, expected: str) -> None:
    if type(ref) is not str or not ref.startswith("refs/"):
        raise SnapshotIntegrityError("PUBLICATION_INPUT", "an explicit full accepted ref is required")
    publication._git(repo, ["check-ref-format", ref], output_limit=128)
    value, _ = publication._git(repo, ["rev-parse", "--verify", ref + "^{commit}"],
                                output_limit=128)
    if value.strip() != expected.encode("ascii"):
        raise SnapshotIntegrityError("SOURCE_CHANGED", "accepted ref changed; candidate is not admitted")


def _write_git_object(repo: Path, args: list[str], payload: bytes) -> str:
    # Request Git's loose-object fsync using per-command configuration only.
    # This is NOT whole-repository/filesystem power-loss qualification; no ref
    # publication or consumer-visible cutover is performed or certified here.
    value, _ = publication._git(
        repo, ["-c", "core.fsync=loose-object", "-c", "core.fsyncMethod=fsync",
               "-c", "commit.gpgsign=false", *args],
        input_bytes=payload, output_limit=128,
    )
    try:
        return publication._oid(value.strip().decode("ascii"))
    except UnicodeError as exc:
        raise SnapshotIntegrityError("GIT_READ", "invalid new Git object identity") from exc


def _tree_with_members(
    repo: Path, tree_oid: str | None, changes: dict[tuple[bytes, ...], str],
    limits: ProtocolLimits,
) -> str:
    entries: dict[bytes, tuple[bytes, bytes, bytes]] = {}
    if tree_oid is not None:
        raw, _ = publication._git(
            repo, ["ls-tree", "-z", tree_oid],
            output_limit=min(limits.snapshot_bytes, limits.snapshot_members * 256),
        )
        if raw and not raw.endswith(b"\0"):
            raise SnapshotIntegrityError("INCOMPLETE", "truncated accepted Git tree")
        for row in raw.split(b"\0")[:-1]:
            try:
                header, name = row.split(b"\t", 1)
                mode, kind, oid = header.split(b" ")
                publication._oid(oid.decode("ascii"))
            except (ValueError, UnicodeError) as exc:
                raise SnapshotIntegrityError("INCOMPLETE", "malformed accepted Git tree") from exc
            if (not name or b"/" in name or name in entries
                    or (mode, kind) not in {
                        (b"040000", b"tree"), (b"100644", b"blob"),
                        (b"100755", b"blob"), (b"120000", b"blob"),
                        (b"160000", b"commit"),
                    }):
                raise SnapshotIntegrityError("INCOMPLETE", "unsupported or duplicate Git tree entry")
            entries[name] = (mode, kind, oid)
    groups: dict[bytes, dict[tuple[bytes, ...], str]] = {}
    for path, oid in changes.items():
        groups.setdefault(path[0], {})[path[1:]] = oid
    for name, nested in groups.items():
        if () in nested:
            if len(nested) != 1:
                raise SnapshotIntegrityError("CONFLICT", "conversion file/directory collision")
            old = entries.get(name)
            mode = old[0] if old and old[1] == b"blob" else b"100644"
            entries[name] = (mode, b"blob", nested[()].encode("ascii"))
        else:
            old = entries.get(name)
            if old and old[1] != b"tree":
                raise SnapshotIntegrityError("CONFLICT", "conversion directory collides with a file")
            child = _tree_with_members(repo, old[2].decode("ascii") if old else None,
                                       nested, limits)
            entries[name] = (b"040000", b"tree", child.encode("ascii"))
    if len(entries) > limits.snapshot_members:
        raise SnapshotIntegrityError("NONRETRYABLE_CAPACITY", "candidate tree entry budget")
    data = b"".join(mode + b" " + kind + b" " + oid + b"\t" + name + b"\0"
                    for name, (mode, kind, oid) in sorted(entries.items()))
    return _write_git_object(repo, ["mktree", "-z"], data)


def prepare_legacy_conversion_candidate(
    repo: Path, *, accepted_tip_oid: str, accepted_ref: str,
    expected_legacy_blob_oid: str, transaction_id: str, operation_id: str,
    lane_id: str, commit_metadata: CandidateCommitMetadata, limits: ProtocolLimits,
) -> PreparedConversionCandidate:
    """Prepare one direct child of the named local accepted tip without a ref.

    Failure can leave immutable unreferenced objects. They are not removed,
    published, retried or adopted automatically. No remote calls are made. The
    source's accepted status and actual launcher exclusion are caller obligations,
    not established by this candidate or its mechanical continuity witness.
    """
    publication._profile(limits)
    publication._repo(repo)
    publication._oid(accepted_tip_oid)
    publication._oid(expected_legacy_blob_oid)
    if type(commit_metadata) is not CandidateCommitMetadata:
        raise SnapshotIntegrityError("PUBLICATION_INPUT", "explicit fixed Git metadata is required")
    identity = commit_metadata.git_identity()
    # Validate operation/target tags before source loading or object writes.
    binding = publication.NativePublicationBinding(
        operation_id, lane_id, "refs/heads/main", accepted_tip_oid, "0" * 64,
    )
    publication._native_binding(binding)
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    publication._complete_repository(repo)
    tree = publication._commit_tree(repo, accepted_tip_oid, limits=limits)
    original = read_legacy_claims_blob(repo, tree_oid=tree,
                                      expected_blob_oid=expected_legacy_blob_oid, limits=limits)
    conversion = plan_legacy_conversion(
        original.raw_bytes, source_id=original.source_id,
        expected_byte_count=original.byte_count,
        expected_logical_digest=original.logical_digest,
        transaction_id=transaction_id, limits=limits,
    )
    changes = {
        tuple(part.encode("ascii") for part in path.split("/")):
        _write_git_object(repo, ["hash-object", "-w", "--stdin"], value)
        for path, value in conversion.members.items()
    }
    candidate_tree = _tree_with_members(repo, tree, changes, limits)
    # Encode all commit bytes explicitly. commit-tree would otherwise consult
    # process identity/time, making a post-write failure non-reconcilable from
    # the same operation inputs. No claim fields or dates are touched.
    commit_bytes = (
        f"tree {candidate_tree}\nparent {accepted_tip_oid}\n"
        f"author {identity}\ncommitter {identity}\n\n"
        f"QLedger conversion candidate {operation_id} {transaction_id}\n"
    ).encode("ascii")
    digest = sha1 if len(accepted_tip_oid) == 40 else sha256
    expected_candidate = digest(b"commit " + str(len(commit_bytes)).encode("ascii")
                                + b"\0" + commit_bytes).hexdigest()
    candidate = _write_git_object(repo, ["hash-object", "-t", "commit", "-w", "--stdin"],
                                  commit_bytes)
    if candidate != expected_candidate:
        raise SnapshotIntegrityError("HASH_MISMATCH", "prepared commit identity differs from its bytes")
    binding = publication.NativePublicationBinding(
        operation_id, lane_id, "refs/heads/main", accepted_tip_oid,
        conversion.plan.snapshot.receipt.root_digest,
    )
    witness = publication.check_legacy_conversion_candidate(
        repo, candidate_oid=candidate, accepted_baseline_oids=(accepted_tip_oid,),
        target_ref="refs/heads/main", binding=binding,
        expected_legacy_blob_oid=expected_legacy_blob_oid,
        conversion_transaction_id=transaction_id, limits=limits,
    )
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    qualifier = AcceptedPrefixQualification(
        accepted_tip_oid=accepted_tip_oid, accepted_ref=accepted_ref,
        source_blob_oid=expected_legacy_blob_oid,
        source_logical_sha256=original.logical_digest,
        source_byte_count=original.byte_count,
    )
    return PreparedConversionCandidate(candidate, candidate_tree, accepted_ref,
                                       commit_metadata, witness, qualifier)


@dataclass(frozen=True)
class PreparedNativeOperationCandidate:
    """Immutable local objects only, NOT a durable pre-apply retention receipt."""

    candidate_oid: str
    tree_oid: str
    accepted_ref: str
    commit_metadata: CandidateCommitMetadata
    native_operation_receipt: publication.NativeOperationReceipt
    continuity: publication.PublicationContinuityWitness
    effect: str = "unreferenced_git_objects_only"


def _native_commit_bytes(tree, parent, operation_id, lane_id, metadata):
    if type(metadata) is not CandidateCommitMetadata:
        raise SnapshotIntegrityError("PUBLICATION_INPUT", "explicit fixed Git metadata is required")
    identity = metadata.git_identity()
    return (f"tree {tree}\nparent {parent}\nauthor {identity}\ncommitter {identity}\n\n"
            f"QLedger native operation candidate {operation_id} {lane_id}\n").encode("ascii")


def _commit_identity(payload: bytes, parent_oid: str) -> str:
    digest = sha1 if len(parent_oid) == 40 else sha256
    return digest(b"commit " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def read_native_operation_candidate(
    repo: Path, *, candidate_oid: str, accepted_tip_oid: str,
    operation_id: str, lane_id: str, authorized_transaction_ids: tuple[str, ...],
    commit_metadata: CandidateCommitMetadata, target_ref: str, limits: ProtocolLimits,
) -> tuple[publication.NativeOperationReceipt, publication.PublicationContinuityWitness]:
    """Read exact immutable original inputs; grant no retention or apply authority.

    Explicit operation/metadata must reproduce the original commit bytes, and
    the existing publisher verifies the complete ordered transaction suffix.
    Missing objects (including after GC) fail closed. This does not reconstruct
    a native sealed plan, durable operation location, outcome or claim clocks.
    """
    publication._profile(limits)
    publication._repo(repo)
    publication._oid(candidate_oid)
    publication._oid(accepted_tip_oid)
    publication._native_binding(publication.NativePublicationBinding(
        operation_id, lane_id, target_ref, accepted_tip_oid, "0" * 64))
    source_tree = publication._commit_tree(repo, accepted_tip_oid, limits=limits)
    tree = publication._commit_tree(repo, candidate_oid, limits=limits)
    expected = _native_commit_bytes(tree, accepted_tip_oid, operation_id, lane_id, commit_metadata)
    actual, _ = publication._git(repo, ["cat-file", "commit", candidate_oid],
                                 output_limit=min(limits.snapshot_bytes, 4096))
    if actual != expected or _commit_identity(expected, accepted_tip_oid) != candidate_oid:
        raise SnapshotIntegrityError("CONFLICT", "candidate differs from exact original operation/metadata")
    base = verify_source_snapshot(GitTreeSource(repo, tree_oid=source_tree, limits=limits), limits=limits)
    candidate = verify_source_snapshot(GitTreeSource(repo, tree_oid=tree, limits=limits), limits=limits)
    receipt = publication.NativeOperationReceipt(operation_id, lane_id, base, candidate,
                                                 authorized_transaction_ids, limits)
    witness = publication.check_native_operation_candidate(
        repo, candidate_oid=candidate_oid, accepted_baseline_oids=(accepted_tip_oid,),
        target_ref=target_ref, binding=publication.NativePublicationBinding(
            operation_id, lane_id, target_ref, accepted_tip_oid, candidate.receipt.root_digest),
        native_operation_receipt=receipt, limits=limits,
    )
    return receipt, witness


def prepare_native_operation_candidate(
    repo: Path, *, accepted_tip_oid: str, accepted_ref: str,
    native_operation_receipt: publication.NativeOperationReceipt,
    commit_metadata: CandidateCommitMetadata, target_ref: str, limits: ProtocolLimits,
) -> PreparedNativeOperationCandidate:
    """Prepare original native inputs as deterministic unreferenced Git objects.

    No ref/index/worktree/native apply/artifact/clock changes. The exact accepted
    native root must match the original base; this never retargets an uncertain
    original operation. These objects have NO GC protection or qualified result
    location. Actual pre-apply admission needs independent durable retention of
    bytes AND the explicit operation-to-object binding; this result is not it.
    """
    publication._profile(limits)
    publication._repo(repo)
    publication._oid(accepted_tip_oid)
    receipt = native_operation_receipt
    publication._receipt(receipt)
    if receipt.limits.fingerprint != limits.fingerprint:
        raise SnapshotIntegrityError("CONFLICT", "original profile differs from candidate profile")
    publication.classify_pending(receipt.original_candidate_snapshot, native_operation_receipt=receipt)
    publication._native_binding(publication.NativePublicationBinding(
        receipt.operation_id, receipt.lane_id, target_ref, accepted_tip_oid,
        receipt.original_candidate_snapshot.receipt.root_digest))
    # Validate explicit fixed metadata before writing even an immutable object.
    _native_commit_bytes("0" * len(accepted_tip_oid), accepted_tip_oid,
                         receipt.operation_id, receipt.lane_id, commit_metadata)
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    publication._complete_repository(repo)
    publication._baselines(repo, (accepted_tip_oid,), limits=limits)
    source_tree = publication._commit_tree(repo, accepted_tip_oid, limits=limits)
    accepted = verify_source_snapshot(GitTreeSource(repo, tree_oid=source_tree, limits=limits), limits=limits)
    if accepted.root_bytes != receipt.original_base_snapshot.root_bytes:
        raise SnapshotIntegrityError("SOURCE_CHANGED", "accepted native root differs from original operation base")
    members = dict(receipt.original_candidate_snapshot._members)
    members[ROOT_PATH] = receipt.original_candidate_snapshot.root_bytes
    changes = {tuple(part.encode("ascii") for part in path.split("/")):
               _write_git_object(repo, ["hash-object", "-w", "--stdin"], value)
               for path, value in members.items()}
    tree = _tree_with_members(repo, source_tree, changes, limits)
    payload = _native_commit_bytes(tree, accepted_tip_oid, receipt.operation_id,
                                   receipt.lane_id, commit_metadata)
    candidate = _write_git_object(repo, ["hash-object", "-t", "commit", "-w", "--stdin"], payload)
    if candidate != _commit_identity(payload, accepted_tip_oid):
        raise SnapshotIntegrityError("HASH_MISMATCH", "native candidate commit differs from explicit bytes")
    restored, witness = read_native_operation_candidate(
        repo, candidate_oid=candidate, accepted_tip_oid=accepted_tip_oid,
        operation_id=receipt.operation_id, lane_id=receipt.lane_id,
        authorized_transaction_ids=receipt.authorized_transaction_ids,
        commit_metadata=commit_metadata, target_ref=target_ref, limits=limits)
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    return PreparedNativeOperationCandidate(candidate, tree, accepted_ref, commit_metadata,
                                             restored, witness)


@dataclass(frozen=True)
class PreparedNativePublicationCandidate:
    """Claims-only current-tip preparation; not the full engine-output tree.

    Never replaces an immutable original result. The release owner validates
    its actual complete frozen candidate with bind_current_native_publication.
    """

    candidate_oid: str
    tree_oid: str
    accepted_ref: str
    binding: publication.NativePublicationBinding
    original_operation_receipt: publication.NativeOperationReceipt
    continuity: publication.PublicationContinuityWitness | None
    commit_metadata: CandidateCommitMetadata | None
    effect: str


def check_current_native_publication_candidate(
    repo: Path, prepared: PreparedNativePublicationCandidate, *,
    accepted_tip_oid: str, accepted_ref: str,
) -> publication.PublicationContinuityWitness:
    """Fresh incumbent validation, not permission to push a cached witness."""
    if type(prepared) is not PreparedNativePublicationCandidate:
        raise SnapshotIntegrityError("PUBLICATION_INPUT", "explicit current publication preparation required")
    binding, receipt = prepared.binding, prepared.original_operation_receipt
    publication._native_binding(binding)
    publication._receipt(receipt)
    if prepared.accepted_ref != accepted_ref or binding.accepted_tip_oid != accepted_tip_oid:
        raise SnapshotIntegrityError("SOURCE_CHANGED", "publication preparation differs from current accepted source")
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    if prepared.commit_metadata is not None:
        payload = _native_commit_bytes(prepared.tree_oid, accepted_tip_oid,
                                       receipt.operation_id, receipt.lane_id, prepared.commit_metadata)
        actual, _ = publication._git(repo, ["cat-file", "commit", prepared.candidate_oid],
                                     output_limit=min(receipt.limits.snapshot_bytes, 4096))
        if actual != payload or _commit_identity(payload, accepted_tip_oid) != prepared.candidate_oid:
            raise SnapshotIntegrityError("CONFLICT", "publication candidate differs from fixed explicit metadata")
    elif prepared.candidate_oid != accepted_tip_oid:
        raise SnapshotIntegrityError("CONFLICT", "no-op publication must name the already accepted commit")
    witness = publication.check_native_operation_candidate(
        repo, candidate_oid=prepared.candidate_oid, accepted_baseline_oids=(accepted_tip_oid,),
        target_ref=binding.target_ref, binding=binding, native_operation_receipt=receipt, limits=receipt.limits)
    if witness.publication.tree_oid != prepared.tree_oid:
        raise SnapshotIntegrityError("CONFLICT", "publication candidate differs from explicit tree")
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    return witness


def prepare_native_publication_candidate(
    repo: Path, *, accepted_tip_oid: str, accepted_ref: str,
    native_operation_receipt: publication.NativeOperationReceipt,
    commit_metadata: CandidateCommitMetadata, target_ref: str, limits: ProtocolLimits,
) -> PreparedNativePublicationCandidate:
    """Compose claims-only original intent onto the CURRENT accepted tip.

    Pending non-claims engine outputs remain untouched in their incumbent
    owner workspace; this isolated tree does not include or publish them.

    Uses the existing rebase/continuity/publication validators. Never mutates
    the original receipt, native store, checkout, index or ref, and never pushes.
    This is not re-preparation/replay of the domain write or a new write identity.
    The owner still owes actual current-tip authority and release admission.
    """
    publication._profile(limits)
    publication._repo(repo)
    publication._oid(accepted_tip_oid)
    receipt = native_operation_receipt
    publication._receipt(receipt)
    if receipt.limits.fingerprint != limits.fingerprint:
        raise SnapshotIntegrityError("CONFLICT", "original and current publication profiles differ")
    publication.classify_pending(receipt.original_candidate_snapshot, native_operation_receipt=receipt)
    _native_commit_bytes("0" * len(accepted_tip_oid), accepted_tip_oid,
                         receipt.operation_id, receipt.lane_id, commit_metadata)
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    publication._complete_repository(repo)
    publication._baselines(repo, (accepted_tip_oid,), limits=limits)
    source_tree = publication._commit_tree(repo, accepted_tip_oid, limits=limits)
    accepted = verify_source_snapshot(GitTreeSource(repo, tree_oid=source_tree, limits=limits), limits=limits)
    required = publication.rebase_native_pending(accepted, native_operation_receipt=receipt)
    binding = publication.NativePublicationBinding(receipt.operation_id, receipt.lane_id,
        target_ref, accepted_tip_oid, required.snapshot.receipt.root_digest)
    publication._native_binding(binding)
    tree, candidate, metadata, effect = source_tree, accepted_tip_oid, None, "not_attempted"
    if required.applied:
        members = {**required.snapshot._members, ROOT_PATH: required.snapshot.root_bytes}
        changes = {tuple(part.encode("ascii") for part in path.split("/")):
                   _write_git_object(repo, ["hash-object", "-w", "--stdin"], value)
                   for path, value in members.items()}
        tree = _tree_with_members(repo, source_tree, changes, limits)
        payload = _native_commit_bytes(tree, accepted_tip_oid, receipt.operation_id, receipt.lane_id, commit_metadata)
        candidate = _write_git_object(repo, ["hash-object", "-t", "commit", "-w", "--stdin"], payload)
        if candidate != _commit_identity(payload, accepted_tip_oid):
            raise SnapshotIntegrityError("HASH_MISMATCH", "current publication commit differs from explicit bytes")
        metadata, effect = commit_metadata, "unreferenced_git_objects_only"
    elif required.snapshot.root_bytes != accepted.root_bytes:
        raise SnapshotIntegrityError("CONFLICT", "no pending publication differs from accepted root")
    # No cached/original witness is forwarded as a current one.
    prepared = PreparedNativePublicationCandidate(candidate, tree, accepted_ref, binding, receipt, None, metadata, effect)
    witness = check_current_native_publication_candidate(repo, prepared,
        accepted_tip_oid=accepted_tip_oid, accepted_ref=accepted_ref)
    return PreparedNativePublicationCandidate(candidate, tree, accepted_ref, binding, receipt, witness, metadata, effect)


def bind_current_native_publication(
    repo: Path, *, candidate_oid: str, expected_tree_oid: str, accepted_tip_oid: str, accepted_ref: str,
    native_operation_receipt: publication.NativeOperationReceipt,
    target_ref: str, limits: ProtocolLimits,
) -> tuple[publication.NativePublicationBinding, publication.PublicationContinuityWitness]:
    """Validate the incumbent owner's ACTUAL complete frozen candidate.

    Unlike the claims-only isolated preparer, this never substitutes a tree or
    commit and never stages/omits other engine outputs. Existing publication
    validation checks that candidate's full introduced history and native root.
    Returned binding/witness are source checks, not release or clock authority.
    """
    publication._profile(limits)
    publication._repo(repo)
    publication._oid(accepted_tip_oid)
    publication._oid(candidate_oid)
    publication._oid(expected_tree_oid)
    if publication._commit_tree(repo, candidate_oid, limits=limits) != expected_tree_oid:
        raise SnapshotIntegrityError("CONFLICT", "actual frozen candidate differs from the owner's exact tree")
    receipt = native_operation_receipt
    publication._receipt(receipt)
    if receipt.limits.fingerprint != limits.fingerprint:
        raise SnapshotIntegrityError("CONFLICT", "original and actual publication profiles differ")
    publication.classify_pending(receipt.original_candidate_snapshot, native_operation_receipt=receipt)
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    source_tree = publication._commit_tree(repo, accepted_tip_oid, limits=limits)
    accepted = verify_source_snapshot(GitTreeSource(repo, tree_oid=source_tree, limits=limits), limits=limits)
    required = publication.rebase_native_pending(accepted, native_operation_receipt=receipt)
    binding = publication.NativePublicationBinding(receipt.operation_id, receipt.lane_id,
        target_ref, accepted_tip_oid, required.snapshot.receipt.root_digest)
    witness = publication.check_native_operation_candidate(repo,
        candidate_oid=candidate_oid, accepted_baseline_oids=(accepted_tip_oid,), target_ref=target_ref,
        binding=binding, native_operation_receipt=receipt, limits=limits)
    if witness.publication.tree_oid != expected_tree_oid:
        raise SnapshotIntegrityError("CONFLICT", "validated candidate replaced the owner's frozen tree")
    _ref_matches(repo, accepted_ref, accepted_tip_oid)
    return binding, witness
