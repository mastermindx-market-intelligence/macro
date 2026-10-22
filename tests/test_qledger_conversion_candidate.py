"""Isolated real-Git preparation; no live claims or remote publication."""
from dataclasses import replace
import subprocess

import pytest

from engine.qledger_store_protocol import ProtocolLimits, SnapshotIntegrityError
from engine.qledger_store_sources import GitTreeSource, verify_source_snapshot
from engine.qledger_store_protocol import open_logical_bytes
from scripts.ci import qledger_conversion_candidate as candidate


def git(repo, *args, input=None):
    return subprocess.check_output(["git", "-C", str(repo), *args], input=input).strip()


@pytest.fixture
def fixture(tmp_path):
    repo = tmp_path.resolve() / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Synthetic fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    claims = repo / "data/qledger/claims.jsonl"
    claims.parent.mkdir(parents=True)
    raw = b'{"duplicate":1}\n' * 4 + b"bad-json\n\n\xff\n"
    claims.write_bytes(raw)
    (repo / "unrelated").write_bytes(b"accepted\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "accepted")
    tip = git(repo, "rev-parse", "HEAD").decode()
    git(repo, "update-ref", "refs/remotes/origin/main", tip)
    blob = git(repo, "rev-parse", "HEAD:data/qledger/claims.jsonl").decode()
    limits = ProtocolLimits(base_bytes=16, part_bytes=32, page_bytes=4096,
                            logical_bytes=16384, snapshot_bytes=1048576,
                            git_blob_bytes=16384)
    return repo, tip, blob, raw, limits


def prepare(fixture, **overrides):
    repo, tip, blob, _, limits = fixture
    args = dict(accepted_tip_oid=tip, accepted_ref="refs/remotes/origin/main",
                expected_legacy_blob_oid=blob, transaction_id="convert:one",
                operation_id="operation:one", lane_id="lane:one", limits=limits,
                commit_metadata=candidate.CandidateCommitMetadata(
                    "Synthetic preparation", "fixture@example.invalid", 1700000000))
    args.update(overrides)
    return candidate.prepare_legacy_conversion_candidate(repo, **args)


def test_candidate_is_direct_parent_lossless_and_changes_no_live_state(fixture):
    repo, tip, blob, raw, limits = fixture
    pending = raw + b"unpublished-pending\n"
    (repo / "data/qledger/claims.jsonl").write_bytes(pending)
    (repo / "unrelated").write_bytes(b"unstaged\n")
    (repo / "untracked").write_bytes(b"keep\n")
    # Preserve a nonempty staged delta too; preparation never borrows the index.
    (repo / "staged").write_bytes(b"staged\n")
    git(repo, "add", "staged")
    index_before = (repo / ".git/index").read_bytes()
    status_before = git(repo, "status", "--porcelain")
    refs_before = git(repo, "show-ref")
    result = prepare(fixture)
    assert git(repo, "rev-list", "--parents", "-n", "1", result.candidate_oid).decode() == (
        result.candidate_oid + " " + tip)
    assert result.continuity.source_blob_oid == blob
    assert result.continuity.eligible_for_cutover is False
    assert result.accepted_ref == "refs/remotes/origin/main"
    snapshot = verify_source_snapshot(GitTreeSource(repo, tree_oid=result.tree_oid,
                                                   limits=limits), limits=limits)
    with open_logical_bytes(snapshot) as stream:
        assert stream.read() == raw
    assert git(repo, "show", result.candidate_oid + ":unrelated") == b"accepted"
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == pending
    assert (repo / ".git/index").read_bytes() == index_before
    assert git(repo, "status", "--porcelain") == status_before
    assert git(repo, "show-ref") == refs_before


@pytest.mark.parametrize("overrides", [
    {"accepted_tip_oid": "0" * 40},
    {"expected_legacy_blob_oid": "0" * 40},
    {"accepted_ref": "HEAD"},
    {"accepted_ref": "refs/remotes/origin/other"},
    {"operation_id": "bad operation"},
    {"commit_metadata": None},
    {"commit_metadata": candidate.CandidateCommitMetadata("bad\nname", "a@b", 1)},
    {"commit_metadata": candidate.CandidateCommitMetadata("A", "bad email", 1)},
    {"commit_metadata": candidate.CandidateCommitMetadata("A", "a@b", True)},
])
def test_stale_or_invalid_source_refuses_before_writing_objects(fixture, overrides, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("source refusal must precede object writes")
    monkeypatch.setattr(candidate, "_write_git_object", forbidden)
    with pytest.raises(SnapshotIntegrityError):
        prepare(fixture, **overrides)


def test_ref_changed_during_preparation_refuses_without_restoring_it(fixture, monkeypatch):
    repo, tip, _, raw, _ = fixture
    other = git(repo, "commit-tree", tip + "^{tree}", "-p", tip,
                input=b"other accepted work\n").decode()
    write = candidate._write_git_object
    changed = False
    def move(*args, **kwargs):
        nonlocal changed
        result = write(*args, **kwargs)
        if not changed:
            git(repo, "update-ref", "refs/remotes/origin/main", other, tip)
            changed = True
        return result
    monkeypatch.setattr(candidate, "_write_git_object", move)
    with pytest.raises(SnapshotIntegrityError, match="accepted ref changed"):
        prepare(fixture)
    assert git(repo, "rev-parse", "refs/remotes/origin/main").decode() == other
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == raw


def test_oversized_or_incomplete_source_does_not_create_a_candidate(fixture, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid source must precede object writes")
    monkeypatch.setattr(candidate, "_write_git_object", forbidden)
    with pytest.raises(SnapshotIntegrityError):
        prepare(fixture, limits=replace(fixture[-1], logical_bytes=8))


@pytest.mark.parametrize("raw,native", [(b"missing final LF", False), (b"original\n", True)])
def test_bad_legacy_shape_precedes_object_writes(fixture, monkeypatch, raw, native):
    repo, _, _, _, _ = fixture
    (repo / "data/qledger/claims.jsonl").write_bytes(raw)
    if native:
        (repo / "data/qledger/claims.root.json").write_bytes(b"unexpected native namespace")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "changed accepted source")
    tip = git(repo, "rev-parse", "HEAD").decode()
    blob = git(repo, "rev-parse", "HEAD:data/qledger/claims.jsonl").decode()
    git(repo, "update-ref", "refs/remotes/origin/main", tip)
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid source must precede object writes")
    monkeypatch.setattr(candidate, "_write_git_object", forbidden)
    with pytest.raises(SnapshotIntegrityError):
        prepare(fixture, accepted_tip_oid=tip, expected_legacy_blob_oid=blob)


def test_corrupt_candidate_member_is_rejected_by_existing_verifier(fixture, monkeypatch):
    repo, _, _, raw, _ = fixture
    refs_before = git(repo, "show-ref")
    write = candidate._write_git_object
    corrupted = False
    def corrupt(repo, args, payload):
        nonlocal corrupted
        if args[0] == "hash-object" and payload.startswith(b'{"duplicate":1}'):
            payload = b"X" + payload[1:]
            corrupted = True
        return write(repo, args, payload)
    monkeypatch.setattr(candidate, "_write_git_object", corrupt)
    with pytest.raises(SnapshotIntegrityError):
        prepare(fixture)
    assert corrupted
    assert git(repo, "show-ref") == refs_before
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == raw


def test_failed_object_write_never_moves_a_ref_or_live_file(fixture, monkeypatch):
    repo, _, _, raw, _ = fixture
    refs_before = git(repo, "show-ref")
    index_before = (repo / ".git/index").read_bytes()
    def fail(*args, **kwargs):
        raise SnapshotIntegrityError("GIT_READ", "synthetic object write failure")
    monkeypatch.setattr(candidate, "_write_git_object", fail)
    with pytest.raises(SnapshotIntegrityError, match="synthetic object write failure"):
        prepare(fixture)
    assert git(repo, "show-ref") == refs_before
    assert (repo / ".git/index").read_bytes() == index_before
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == raw


def test_post_commit_failure_reconciles_same_fixed_inputs_without_live_changes(fixture, monkeypatch):
    repo, _, _, raw, _ = fixture
    refs_before = git(repo, "show-ref")
    index_before = (repo / ".git/index").read_bytes()
    created = []
    def fail_after_commit(*args, **kwargs):
        created.append(kwargs["candidate_oid"])
        assert git(repo, "cat-file", "-t", created[-1]) == b"commit"
        raise SnapshotIntegrityError("GIT_READ", "synthetic post-commit response loss")
    with monkeypatch.context() as fault:
        fault.setattr(candidate.publication, "check_legacy_conversion_candidate", fail_after_commit)
        with pytest.raises(SnapshotIntegrityError, match="post-commit response loss"):
            prepare(fixture)
    assert git(repo, "show-ref") == refs_before
    assert (repo / ".git/index").read_bytes() == index_before
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == raw
    # Host Git identity/date overrides cannot change these explicit commit bytes.
    monkeypatch.setenv("GIT_AUTHOR_DATE", "1800000000 +0000")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "1900000000 +0000")
    result = prepare(fixture)
    assert result.candidate_oid == created[0]
    assert result.commit_metadata.timestamp == 1700000000
    commit = git(repo, "cat-file", "commit", result.candidate_oid)
    assert b"fixture@example.invalid> 1700000000 +0000" in commit
    assert git(repo, "show-ref") == refs_before
    assert (repo / ".git/index").read_bytes() == index_before
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == raw
