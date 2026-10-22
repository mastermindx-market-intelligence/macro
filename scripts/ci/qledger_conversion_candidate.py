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

from engine.qledger_store_conversion import plan_legacy_conversion
from engine.qledger_store_protocol import ProtocolLimits, SnapshotIntegrityError
from engine.qledger_store_sources import read_legacy_claims_blob
from scripts.ci import qledger_publication as publication


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
class PreparedConversionCandidate:
    candidate_oid: str
    tree_oid: str
    accepted_ref: str
    commit_metadata: CandidateCommitMetadata
    continuity: publication.PublicationContinuityWitness
    effect: str = "unreferenced_git_objects_only"


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
    return PreparedConversionCandidate(candidate, candidate_tree, accepted_ref,
                                       commit_metadata, witness)
