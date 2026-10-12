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
    VerifiedSnapshot, rebase_verified_pending, validate_publication,
)
from engine.qledger_store_sources import GitTreeSource, verify_source_snapshot  # noqa: E402

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
    return tuple(out)


def _ancestor(repo: Path, ancestor: str, descendant: str) -> None:
    _raw, code = _git(repo, ["merge-base", "--is-ancestor", _oid(ancestor), _oid(descendant)],
                     output_limit=4096, allowed_codes=(0, 1))
    if code:
        _fail("CONFLICT", "the accepted target tip is not an ancestor of the candidate")


def _introduced(
    repo: Path, roots: tuple[str, ...], baselines: tuple[str, ...], *, limits: ProtocolLimits,
) -> tuple[BlobInfo, ...]:
    raw, _ = _git(repo, ["rev-list", "--objects", "--no-object-names", "--missing=print",
                         *roots, "--not", *baselines],
                  output_limit=limits.publication_objects * 66)
    if raw and not raw.endswith(b"\n"):
        _fail("INCOMPLETE", "truncated newly reachable object inventory")
    objects: list[str] = []
    seen: set[str] = set()
    for line in raw.splitlines():
        if len(objects) >= limits.publication_objects:
            _fail("NONRETRYABLE_CAPACITY", "introduced-object count exceeds the budget")
        try:
            oid = line.decode("ascii")
        except UnicodeError as exc:
            raise SnapshotIntegrityError("GIT_READ", "invalid introduced-object identity") from exc
        if oid.startswith("?"):
            _fail("INCOMPLETE", "a reachable object is missing locally")
        _oid(oid)
        if oid in seen:
            _fail("INCOMPLETE", "duplicate introduced-object inventory row")
        seen.add(oid)
        objects.append(oid)
    if not objects:
        return ()
    supplied = ("\n".join(objects) + "\n").encode("ascii")
    raw, _ = _git(repo, ["cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)"],
                  input_bytes=supplied, output_limit=len(objects) * 100)
    if not raw.endswith(b"\n"):
        _fail("INCOMPLETE", "truncated introduced-object metadata")
    rows = raw.splitlines()
    if len(rows) != len(objects):
        _fail("INCOMPLETE", "introduced-object metadata is incomplete")
    blobs: list[BlobInfo] = []
    for wanted, row in zip(objects, rows):
        fields = row.split(b" ")
        if len(fields) != 3 or fields[0] != wanted.encode() or not re.fullmatch(rb"[0-9]+", fields[2]):
            _fail("INCOMPLETE", "missing or malformed introduced-object metadata")
        if fields[1] not in (b"commit", b"tree", b"blob", b"tag"):
            _fail("INCOMPLETE", "unknown introduced object type")
        if fields[1] == b"blob":
            size = int(fields[2])
            if size > limits.git_blob_bytes:
                _fail("NONRETRYABLE_OVERSIZE", "a newly reachable blob exceeds the publication bound")
            blobs.append(BlobInfo(wanted, size))
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
    args = parser.parse_args(argv)
    try:
        from engine.qledger_store import LegacyClaimsBinding, _production_claims_binding
        repo = _repo(args.repo)
        binding = _production_claims_binding(repo / BASE_PATH)
        if type(binding) is not LegacyClaimsBinding:
            _fail("PUBLICATION_INPUT", "native publication needs a separately admitted explicit owner binding")
        # No path discovery, candidate inspection, filesystem change or Git
        # command is performed by the current production format selection.
        print(json.dumps({"status": "LEGACY_SELECTED", "boundary": args.boundary,
                          "effect": "not_attempted"}, sort_keys=True))
        return 0
    except SnapshotIntegrityError as exc:
        print(json.dumps({"status": "REJECTED", "code": exc.code,
                          "effect": "not_attempted"}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
