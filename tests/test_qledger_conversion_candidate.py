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
def fixture(tmp_path, request):
    repo = tmp_path.resolve() / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Synthetic fixture")
    git(repo, "config", "user.email", "fixture@example.invalid")
    claims = repo / "data/qledger/claims.jsonl"
    claims.parent.mkdir(parents=True)
    specimen = getattr(request, "param", {})
    raw = specimen.get("raw", b'{"duplicate":1}\n' * 4 + b"bad-json\n\n\xff\n")
    claims.write_bytes(raw)
    (repo / "unrelated").write_bytes(b"accepted\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "accepted")
    tip = git(repo, "rev-parse", "HEAD").decode()
    git(repo, "update-ref", "refs/remotes/origin/main", tip)
    blob = git(repo, "rev-parse", "HEAD:data/qledger/claims.jsonl").decode()
    limits = ProtocolLimits(base_bytes=16, part_bytes=specimen.get("part_bytes", 32), page_bytes=4096,
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


def test_preparation_refuses_missing_excluded_accepted_history(fixture):
    repo, _, _, raw, _ = fixture
    historical_file = repo / "retired-source"
    historical_file.write_bytes(b"accepted historical bytes\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "accepted historical source")
    historical_blob = git(repo, "rev-parse", "HEAD:retired-source").decode()
    git(repo, "rm", "-q", "retired-source")
    git(repo, "commit", "-qm", "accepted source no longer in tip")
    tip = git(repo, "rev-parse", "HEAD").decode()
    git(repo, "update-ref", "refs/remotes/origin/main", tip)
    missing = repo / ".git/objects" / historical_blob[:2] / historical_blob[2:]
    missing.unlink()
    refs_before = git(repo, "show-ref")
    index_before = (repo / ".git/index").read_bytes()
    with pytest.raises(SnapshotIntegrityError, match="INCOMPLETE|GIT_READ"):
        prepare(fixture, accepted_tip_oid=tip)
    assert not missing.exists()
    assert git(repo, "show-ref") == refs_before
    assert (repo / ".git/index").read_bytes() == index_before
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == raw


@pytest.fixture
def native_fixture(fixture):
    from engine import qledger_store_protocol as protocol
    from scripts.ci.qledger_publication import NativeOperationReceipt
    repo, _, _, raw, limits = fixture
    converted = prepare(fixture)
    git(repo, "update-ref", "refs/remotes/origin/main", converted.candidate_oid)
    base = verify_source_snapshot(GitTreeSource(repo, tree_oid=converted.tree_oid, limits=limits), limits=limits)
    one = protocol.plan_append(base, transaction_id="native:one", serialized_rows=[b'{"original":1}\n'], limits=limits)
    two = protocol.plan_append(one.snapshot, transaction_id="native:two", serialized_rows=[b'raw-duplicate\n', b'raw-duplicate\n'], limits=limits)
    receipt = NativeOperationReceipt("operation:native", "lane:native", base, two.snapshot,
                                     ("native:one", "native:two"), limits)
    return repo, converted.candidate_oid, raw, limits, receipt


def prepare_native(native_fixture, **overrides):
    repo, tip, _, limits, receipt = native_fixture
    kwargs = dict(accepted_tip_oid=tip, accepted_ref="refs/remotes/origin/main",
                  native_operation_receipt=receipt, target_ref="refs/heads/main", limits=limits,
                  commit_metadata=candidate.CandidateCommitMetadata("Native fixture", "fixture@example.invalid", 1700000100))
    kwargs.update(overrides)
    return candidate.prepare_native_operation_candidate(repo, **kwargs)


def read_native(native_fixture, prepared, **overrides):
    repo, tip, _, limits, receipt = native_fixture
    kwargs = dict(candidate_oid=prepared.candidate_oid, accepted_tip_oid=tip,
        operation_id=receipt.operation_id, lane_id=receipt.lane_id,
        authorized_transaction_ids=receipt.authorized_transaction_ids,
        commit_metadata=prepared.commit_metadata, target_ref="refs/heads/main", limits=limits)
    kwargs.update(overrides)
    return candidate.read_native_operation_candidate(repo, **kwargs)


def test_native_candidate_and_readback_preserve_original_bytes_and_live_state(native_fixture):
    repo, tip, raw, limits, receipt = native_fixture
    (repo / "data/qledger/claims.jsonl").write_bytes(raw + b"LIVE-PENDING\n")
    before = (git(repo, "status", "--porcelain"), git(repo, "show-ref"), (repo / ".git/index").read_bytes())
    result = prepare_native(native_fixture)
    restored, witness = read_native(native_fixture, result)
    assert witness.status == "NATIVE_OPERATION_VERIFIED" and not witness.eligible_for_cutover
    assert restored.authorized_transaction_ids == ("native:one", "native:two")
    assert restored.original_base_snapshot.root_bytes == receipt.original_base_snapshot.root_bytes
    assert restored.original_candidate_snapshot.root_bytes == receipt.original_candidate_snapshot.root_bytes
    with open_logical_bytes(restored.original_candidate_snapshot) as stream:
        assert stream.read() == raw + b'{"original":1}\nraw-duplicate\nraw-duplicate\n'
    assert git(repo, "rev-list", "--parents", "-n", "1", result.candidate_oid).decode() == result.candidate_oid + " " + tip
    assert before == (git(repo, "status", "--porcelain"), git(repo, "show-ref"), (repo / ".git/index").read_bytes())
    assert (repo / "data/qledger/claims.jsonl").read_bytes() == raw + b"LIVE-PENDING\n"
    assert result.effect == "unreferenced_git_objects_only"


@pytest.mark.parametrize("changes", [
    {"operation_id": "other"}, {"lane_id": "other"},
    {"authorized_transaction_ids": ("native:two", "native:one")},
    {"authorized_transaction_ids": ("native:one",)},
    {"commit_metadata": candidate.CandidateCommitMetadata("Other", "fixture@example.invalid", 1700000100)},
])
def test_native_readback_refuses_changed_operation_or_original_inputs(native_fixture, changes):
    result = prepare_native(native_fixture)
    with pytest.raises(SnapshotIntegrityError):
        read_native(native_fixture, result, **changes)


def test_native_bad_receipt_or_stale_ref_refuses_before_object_writes(native_fixture, monkeypatch):
    receipt = native_fixture[-1]
    monkeypatch.setattr(candidate, "_write_git_object", lambda *a: pytest.fail("invalid original inputs wrote objects"))
    with pytest.raises(SnapshotIntegrityError):
        prepare_native(native_fixture, native_operation_receipt=replace(receipt, authorized_transaction_ids=("native:one",)))
    with pytest.raises(SnapshotIntegrityError):
        prepare_native(native_fixture, accepted_ref="refs/remotes/origin/missing")


def test_native_commit_response_loss_repeats_same_immutable_candidate(native_fixture, monkeypatch):
    write = candidate._write_git_object
    commits = []
    def response_lost(repo, args, payload):
        oid = write(repo, args, payload)
        if args == ["hash-object", "-t", "commit", "-w", "--stdin"]:
            commits.append(oid)
            raise RuntimeError("fixture response loss after native commit")
        return oid
    monkeypatch.setattr(candidate, "_write_git_object", response_lost)
    with pytest.raises(RuntimeError, match="response loss"):
        prepare_native(native_fixture)
    monkeypatch.setattr(candidate, "_write_git_object", write)
    monkeypatch.setenv("GIT_AUTHOR_DATE", "1800000000 +0000")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "1800000001 +0000")
    result = prepare_native(native_fixture)
    assert commits == [result.candidate_oid]
    assert read_native(native_fixture, result)[1].status == "NATIVE_OPERATION_VERIFIED"


def test_native_git_readback_refuses_missing_retained_member(native_fixture):
    repo, _, _, _, receipt = native_fixture
    result = prepare_native(native_fixture)
    path = next(path for path, payload in receipt.original_candidate_snapshot._members.items()
                if payload == b'{"original":1}\n')
    oid = git(repo, "rev-parse", result.candidate_oid + ":" + path).decode()
    (repo / ".git/objects" / oid[:2] / oid[2:]).unlink()
    with pytest.raises(SnapshotIntegrityError):
        read_native(native_fixture, result)


def test_native_preparation_never_retargets_original_to_advanced_accepted_root(native_fixture, monkeypatch):
    repo = native_fixture[0]
    original = prepare_native(native_fixture)
    git(repo, "update-ref", "refs/remotes/origin/main", original.candidate_oid)
    monkeypatch.setattr(candidate, "_write_git_object", lambda *a: pytest.fail("advanced source wrote objects"))
    with pytest.raises(SnapshotIntegrityError, match="original operation base"):
        prepare_native(native_fixture, accepted_tip_oid=original.candidate_oid)


def test_current_native_publication_uses_current_parent_not_cached_original(native_fixture):
    from scripts.ci import qledger_publication as publication
    from engine import qledger_store_protocol as protocol
    repo, tip, raw, limits, original = native_fixture
    old = prepare_native(native_fixture)
    remote = protocol.plan_append(original.original_base_snapshot, transaction_id='remote:accepted',
                                  serialized_rows=[b'{"remote":1}\n'], limits=limits)
    remote_candidate = candidate.prepare_native_operation_candidate(repo, accepted_tip_oid=tip,
        accepted_ref='refs/remotes/origin/main', native_operation_receipt=publication.NativeOperationReceipt(
            'operation:remote', 'lane:remote', remote._before, remote.snapshot, ('remote:accepted',), limits),
        commit_metadata=candidate.CandidateCommitMetadata('Remote fixture', 'fixture@example.invalid', 1700000200),
        target_ref='refs/heads/main', limits=limits)
    git(repo, 'update-ref', 'refs/remotes/origin/main', remote_candidate.candidate_oid)
    current = candidate.prepare_native_publication_candidate(repo,
        accepted_tip_oid=remote_candidate.candidate_oid, accepted_ref='refs/remotes/origin/main',
        native_operation_receipt=original, commit_metadata=candidate.CandidateCommitMetadata(
            'Publication fixture', 'fixture@example.invalid', 1700000300), target_ref='refs/heads/main', limits=limits)
    assert current.candidate_oid != old.candidate_oid
    assert current.binding.accepted_tip_oid == remote_candidate.candidate_oid
    assert current.original_operation_receipt is original
    assert git(repo, 'rev-list', '--parents', '-n', '1', current.candidate_oid).decode() == (
        current.candidate_oid+' '+remote_candidate.candidate_oid)
    checked = candidate.check_current_native_publication_candidate(repo, current,
        accepted_tip_oid=remote_candidate.candidate_oid, accepted_ref='refs/remotes/origin/main')
    assert checked.status == 'NATIVE_OPERATION_VERIFIED'
    snapshot = verify_source_snapshot(GitTreeSource(repo, tree_oid=current.tree_oid, limits=limits), limits=limits)
    with open_logical_bytes(snapshot) as stream:
        assert stream.read() == raw+b'{"remote":1}\n'+b'{"original":1}\nraw-duplicate\nraw-duplicate\n'
    with pytest.raises(SnapshotIntegrityError):
        candidate.check_current_native_publication_candidate(repo, old,
            accepted_tip_oid=remote_candidate.candidate_oid, accepted_ref='refs/remotes/origin/main')
    git(repo, 'update-ref', 'refs/remotes/origin/main', tip)
    with pytest.raises(SnapshotIntegrityError, match='accepted ref'):
        candidate.check_current_native_publication_candidate(repo, current,
            accepted_tip_oid=remote_candidate.candidate_oid, accepted_ref='refs/remotes/origin/main')


def test_current_native_publication_already_accepted_creates_no_empty_commit(native_fixture, monkeypatch):
    repo, _, _, limits, original = native_fixture
    accepted = prepare_native(native_fixture)
    git(repo, 'update-ref', 'refs/remotes/origin/main', accepted.candidate_oid)
    monkeypatch.setattr(candidate, '_write_git_object', lambda *a, **k: pytest.fail('already accepted operation created another object/commit'))
    current = candidate.prepare_native_publication_candidate(repo,
        accepted_tip_oid=accepted.candidate_oid, accepted_ref='refs/remotes/origin/main', native_operation_receipt=original,
        commit_metadata=candidate.CandidateCommitMetadata('Explicit no-op', 'fixture@example.invalid', 1700000400),
        target_ref='refs/heads/main', limits=limits)
    assert current.candidate_oid == accepted.candidate_oid and current.effect == 'not_attempted'
    assert current.commit_metadata is None and current.continuity.planned_transaction_ids == ()
    assert current.continuity.already_present_transaction_ids == original.authorized_transaction_ids


def test_current_native_publication_refuses_unknown_order_before_objects(native_fixture, monkeypatch):
    from dataclasses import replace
    repo, tip, _, limits, original = native_fixture
    monkeypatch.setattr(candidate, '_write_git_object', lambda *a, **k: pytest.fail('unknown original wrote Git objects'))
    with pytest.raises(SnapshotIntegrityError):
        candidate.prepare_native_publication_candidate(repo,
            accepted_tip_oid=tip, accepted_ref='refs/remotes/origin/main',
            native_operation_receipt=replace(original, authorized_transaction_ids=tuple(reversed(original.authorized_transaction_ids))),
            commit_metadata=candidate.CandidateCommitMetadata('Unknown', 'fixture@example.invalid', 1700000400),
            target_ref='refs/heads/main', limits=limits)


def test_current_native_publication_ref_movement_never_returns_witness_or_restores_ref(native_fixture, monkeypatch):
    repo, tip, _, limits, original = native_fixture
    other = prepare_native(native_fixture)
    write = candidate._write_git_object
    def moved(repo, args, payload):
        oid = write(repo, args, payload)
        if args[:3] == ['hash-object', '-t', 'commit']:
            git(repo, 'update-ref', 'refs/remotes/origin/main', other.candidate_oid)
        return oid
    monkeypatch.setattr(candidate, '_write_git_object', moved)
    with pytest.raises(SnapshotIntegrityError, match='accepted ref'):
        candidate.prepare_native_publication_candidate(repo,
            accepted_tip_oid=tip, accepted_ref='refs/remotes/origin/main', native_operation_receipt=original,
            commit_metadata=candidate.CandidateCommitMetadata('Moving', 'fixture@example.invalid', 1700000500),
            target_ref='refs/heads/main', limits=limits)
    assert git(repo, 'rev-parse', 'refs/remotes/origin/main').decode() == other.candidate_oid


def test_actual_owner_frozen_candidate_keeps_broad_outputs_and_requires_fresh_binding(native_fixture):
    repo, tip, _, limits, original = native_fixture
    native = prepare_native(native_fixture)
    output = git(repo, "hash-object", "-w", "--stdin", input=b"complete engine output\n").decode()
    tree = candidate._tree_with_members(repo, native.tree_oid, {(b"engine-output",): output}, limits)
    actual = git(repo, "commit-tree", tree, "-p", tip, input=b"incumbent complete output commit\n").decode()
    before = (git(repo, "show-ref"), (repo / ".git/index").read_bytes(), git(repo, "status", "--porcelain"))
    binding, witness = candidate.bind_current_native_publication(repo, candidate_oid=actual, expected_tree_oid=tree,
        accepted_tip_oid=tip, accepted_ref="refs/remotes/origin/main", native_operation_receipt=original,
        target_ref="refs/heads/main", limits=limits)
    assert binding.accepted_tip_oid == tip and witness.publication.candidate_oid == actual
    assert witness.publication.tree_oid == tree and actual != native.candidate_oid
    assert git(repo, "show", actual+":engine-output") == b"complete engine output"
    assert (git(repo, "show-ref"), (repo / ".git/index").read_bytes(), git(repo, "status", "--porcelain")) == before
    with pytest.raises(SnapshotIntegrityError, match="exact tree"):
        # A claims-only candidate cannot substitute for the owner's full tree.
        candidate.bind_current_native_publication(repo, candidate_oid=native.candidate_oid, expected_tree_oid=tree,
            accepted_tip_oid=tip, accepted_ref="refs/remotes/origin/main", native_operation_receipt=original,
            target_ref="refs/heads/main", limits=limits)
    accepted_tree = git(repo, "rev-parse", tip+"^{tree}").decode()
    with pytest.raises(SnapshotIntegrityError):
        candidate.bind_current_native_publication(repo, candidate_oid=tip, expected_tree_oid=accepted_tree,
            accepted_tip_oid=tip, accepted_ref="refs/remotes/origin/main", native_operation_receipt=original,
            target_ref="refs/heads/main", limits=limits)
    git(repo, "update-ref", "refs/remotes/origin/main", native.candidate_oid)
    with pytest.raises(SnapshotIntegrityError):
        # Fresh accepted input still rejects an actual commit with the old parent.
        candidate.bind_current_native_publication(repo, candidate_oid=actual, expected_tree_oid=tree,
            accepted_tip_oid=native.candidate_oid, accepted_ref="refs/remotes/origin/main", native_operation_receipt=original,
            target_ref="refs/heads/main", limits=limits)
    with pytest.raises(SnapshotIntegrityError, match="accepted ref"):
        candidate.bind_current_native_publication(repo, candidate_oid=actual, expected_tree_oid=tree,
            accepted_tip_oid=tip, accepted_ref="refs/remotes/origin/main", native_operation_receipt=original,
            target_ref="refs/heads/main", limits=limits)
