"""Synthetic local Git checks; no source checkout, live push or financial reads."""

from __future__ import annotations

import hashlib
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from engine import qledger_store_protocol as p
from engine.qledger_store import LegacyClaimsBinding
from scripts.ci import qledger_publication as q


@pytest.fixture
def limits():
    return p.ProtocolLimits(
        base_bytes=4096, part_bytes=1024, page_bytes=16384, root_bytes=2048,
        descriptor_bytes=2048, leaf_entries=4, fanout=4, index_levels=3,
        history_operations=32, reference_visits=4096, snapshot_members=256,
        snapshot_bytes=1048576, logical_bytes=65536, input_rows=512,
        publication_objects=1024, git_blob_bytes=131072,
    )


def git(root, *args):
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1"}
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE"):
        env.pop(key, None)
    result = subprocess.run(["git", "-C", str(root), *args], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return result.stdout.decode().strip()


def write_members(root, values):
    for path, payload in values.items():
        dest = root / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)


def initial(raw, limits):
    digest = hashlib.sha256(raw).hexdigest()
    record = p.RootRecord(p.MemberRef(p.BASE_PATH, digest, len(raw)), None,
                          0, len(raw), digest, limits.fingerprint)
    values = {p.BASE_PATH: raw, p.ROOT_PATH: p.encode_root(record, limits=limits)}
    source = p.InMemorySource(values, snapshot_id="synthetic:publication-base")
    return values, p.verify_snapshot(source, record, limits=limits)


def fixture_repo(tmp_path, limits):
    root = tmp_path / "synthetic-repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.name", "Synthetic QLedger Test")
    git(root, "config", "user.email", "synthetic@example.invalid")
    git(root, "config", "commit.gpgsign", "false")
    values, base = initial(b"{\"claim_id\":\"base\"}\n", limits)
    write_members(root, values)
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic baseline")
    baseline = git(root, "rev-parse", "HEAD")
    return root, baseline, values, base


def appended(root, values, base, limits, *, tx="local", rows=(b'{"claim_id":"repeat"}\n',)):
    plan = p.plan_append(base, transaction_id=tx, serialized_rows=rows, limits=limits)
    values = {**values, **plan.members, p.ROOT_PATH: plan.root_bytes}
    write_members(root, values)
    git(root, "add", ".")
    git(root, "commit", "-qm", "synthetic append")
    return git(root, "rev-parse", "HEAD"), values, plan.snapshot


def binding(baseline, snapshot):
    return q.NativePublicationBinding("synthetic-operation", "synthetic-lane",
                                      "refs/heads/main", baseline, snapshot.receipt.root_digest)


def checked(root, candidate, baseline, snapshot, limits, **changes):
    args = dict(candidate_oid=candidate, accepted_baseline_oids=(baseline,),
                target_ref="refs/heads/main", binding=binding(baseline, snapshot), limits=limits)
    args.update(changes)
    return q.check_publish_candidate(root, **args)


def physical_state(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob("*")
            if path.is_file() and ".git" not in path.relative_to(root).parts}


def test_named_candidate_is_checked_even_when_head_and_worktree_are_older(tmp_path, limits):
    root, baseline, values, base = fixture_repo(tmp_path, limits)
    candidate, _, snapshot = appended(root, values, base, limits)
    tree = git(root, "rev-parse", candidate + "^{tree}")
    git(root, "checkout", "--detach", "-q", baseline)
    before = physical_state(root)
    index = (root / ".git/index").read_bytes()
    result = checked(root, candidate, baseline, snapshot, limits)
    assert result.status == "NATIVE_VERIFIED" and result.candidate_oid == candidate
    assert result.tree_oid == tree and result.root_digest == snapshot.receipt.root_digest
    assert result.effect == "not_attempted" and result.introduced_blobs > 0
    assert git(root, "rev-parse", "HEAD") == baseline
    assert physical_state(root) == before and (root / ".git/index").read_bytes() == index


def test_frozen_tree_validation_does_not_install_ref_or_change_staging(tmp_path, limits):
    root, baseline, values, base = fixture_repo(tmp_path, limits)
    plan = p.plan_append(base, transaction_id="staged", serialized_rows=[b"staged\n"], limits=limits)
    write_members(root, {**values, **plan.members, p.ROOT_PATH: plan.root_bytes})
    git(root, "add", ".")
    tree = git(root, "write-tree")
    index = (root / ".git/index").read_bytes()
    before = physical_state(root)
    result = q.check_frozen_tree(root, tree_oid=tree, parent_commit_oid=baseline,
                                accepted_baseline_oids=(baseline,),
                                binding=binding(baseline, plan.snapshot), limits=limits)
    assert result.status == "NATIVE_VERIFIED" and result.tree_oid == tree
    assert result.candidate_oid is None and result.parent_commit_oid == baseline
    assert git(root, "rev-parse", "HEAD") == baseline
    assert physical_state(root) == before and (root / ".git/index").read_bytes() == index


@pytest.mark.parametrize("boundary", ["candidate", "frozen"])
def test_oversized_deleted_ancestor_blob_is_still_rejected(boundary, tmp_path, limits):
    limited = replace(limits, git_blob_bytes=2048)
    root, baseline, values, base = fixture_repo(tmp_path, limited)
    large = root / "unrelated-intermediate.bin"
    large.write_bytes(b"x" * 4096)
    git(root, "add", ".")
    git(root, "commit", "-qm", "oversized intermediate")
    parent = git(root, "rev-parse", "HEAD")
    git(root, "rm", "-q", str(large))
    tree = git(root, "write-tree")
    if boundary == "frozen":
        action = lambda: q.check_frozen_tree(root, tree_oid=tree, parent_commit_oid=parent,
                                             accepted_baseline_oids=(baseline,),
                                             binding=binding(baseline, base), limits=limited)
    else:
        git(root, "commit", "-qm", "delete oversized final-tree file")
        candidate = git(root, "rev-parse", "HEAD")
        action = lambda: checked(root, candidate, baseline, base, limited)
    before = physical_state(root)
    index = (root / ".git/index").read_bytes()
    with pytest.raises(p.SnapshotIntegrityError, match="NONRETRYABLE_OVERSIZE"):
        action()
    assert physical_state(root) == before and (root / ".git/index").read_bytes() == index


def test_accepted_baseline_blob_does_not_become_new_again(tmp_path, limits):
    limited = replace(limits, git_blob_bytes=2048)
    root, _, values, base = fixture_repo(tmp_path, limited)
    (root / "previously-accepted.bin").write_bytes(b"a" * 4096)
    git(root, "add", ".")
    git(root, "commit", "-qm", "explicit accepted baseline fixture")
    baseline = git(root, "rev-parse", "HEAD")
    candidate, _, snapshot = appended(root, values, base, limited)
    assert checked(root, candidate, baseline, snapshot, limited).status == "NATIVE_VERIFIED"


def test_missing_newly_reachable_object_is_not_a_complete_inventory(tmp_path, limits):
    root, baseline, _, base = fixture_repo(tmp_path, limits)
    (root / "missing.bin").write_bytes(b"temporary fixture object")
    git(root, "add", ".")
    git(root, "commit", "-qm", "temporary object")
    candidate = git(root, "rev-parse", "HEAD")
    blob = git(root, "rev-parse", candidate + ":missing.bin")
    (root / ".git/objects" / blob[:2] / blob[2:]).unlink()
    with pytest.raises(p.SnapshotIntegrityError):
        checked(root, candidate, baseline, base, limits)


def test_shallow_history_is_refused_without_fetching(tmp_path, limits, monkeypatch):
    root, baseline, _, base = fixture_repo(tmp_path, limits)
    (root / ".git/shallow").write_text(baseline + "\n")
    with pytest.raises(p.SnapshotIntegrityError, match="shallow"):
        checked(root, baseline, baseline, base, limits)


@pytest.mark.parametrize("bad", [None, "HEAD", "a" * 39, "a" * 41, True, 3.0, "A" * 40])
def test_candidate_requires_an_exact_full_object_identity(bad, tmp_path, limits):
    root, baseline, _, base = fixture_repo(tmp_path, limits)
    with pytest.raises(p.SnapshotIntegrityError):
        checked(root, bad, baseline, base, limits)


@pytest.mark.parametrize("case", ["empty", "text", "duplicate", "missing", "wrong-type"])
def test_baseline_set_must_be_explicit_complete_and_unambiguous(case, tmp_path, limits):
    root, baseline, _, base = fixture_repo(tmp_path, limits)
    cases = {"empty": (), "text": baseline, "duplicate": (baseline, baseline),
             "missing": ("f" * 40,), "wrong-type": (git(root, "rev-parse", "HEAD^{tree}"),)}
    with pytest.raises(p.SnapshotIntegrityError):
        checked(root, baseline, baseline, base, limits, accepted_baseline_oids=cases[case])


@pytest.mark.parametrize("target", ["main", "refs/heads/", "refs/heads/main/", "refs/heads/a..b", "refs/heads/x.lock", "refs/tags/main"])
def test_target_binding_requires_a_supported_exact_branch_ref(target, tmp_path, limits):
    root, baseline, _, base = fixture_repo(tmp_path, limits)
    with pytest.raises(p.SnapshotIntegrityError):
        checked(root, baseline, baseline, base, limits,
                target_ref=target, binding=replace(binding(baseline, base), target_ref=target))


@pytest.mark.parametrize("case", ["root", "target", "tip", "binding"])
def test_candidate_must_match_explicit_owner_binding(case, tmp_path, limits):
    root, baseline, _, base = fixture_repo(tmp_path, limits)
    changes = {"root": {"binding": replace(binding(baseline, base), expected_root_digest="0" * 64)},
               "target": {"target_ref": "refs/heads/other"},
               "tip": {"binding": replace(binding(baseline, base), accepted_tip_oid="f" * 40)},
               "binding": {"binding": None}}
    with pytest.raises(p.SnapshotIntegrityError):
        checked(root, baseline, baseline, base, limits, **changes[case])


def test_introduced_inventory_count_is_bounded_before_returning_success(tmp_path, limits):
    limited = replace(limits, publication_objects=1)
    root, baseline, values, base = fixture_repo(tmp_path, limited)
    candidate, _, snapshot = appended(root, values, base, limited)
    with pytest.raises(p.SnapshotIntegrityError, match="NONRETRYABLE_CAPACITY"):
        checked(root, candidate, baseline, snapshot, limited)


@pytest.mark.parametrize("boundary", ["frozen-tree", "publish-candidate", "pre-rebase"])
def test_current_production_cli_is_hard_legacy_without_any_source_or_git_read(boundary, tmp_path, monkeypatch, capsys):
    missing = tmp_path / "does-not-exist"
    monkeypatch.setattr(q, "_git", lambda *a, **k: pytest.fail("legacy selection invoked Git"))
    monkeypatch.setattr(q, "GitTreeSource", lambda *a, **k: pytest.fail("legacy selection discovered a native source"))
    assert q.main(["--repo", str(missing), "--boundary", boundary]) == 0
    assert '"status": "LEGACY_SELECTED"' in capsys.readouterr().out
    assert not missing.exists()


def test_public_check_legacy_selection_does_not_inspect_invalid_candidate(tmp_path, limits, monkeypatch):
    monkeypatch.setattr(q, "_git", lambda *a, **k: pytest.fail("legacy check invoked Git"))
    legacy = LegacyClaimsBinding(tmp_path / p.BASE_PATH)
    result = q.check_publish_candidate(tmp_path, candidate_oid="not-a-candidate",
                                       accepted_baseline_oids=(), target_ref="not-a-ref",
                                       binding=legacy, limits=limits)
    assert result.status == "LEGACY_SELECTED" and result.effect == "not_attempted"


def pending(limits):
    values, base = initial(b"unterminated", limits)
    plan = p.plan_append(base, transaction_id="local", serialized_rows=[b"same\n", b"same\n"], limits=limits)
    receipt = q.NativeOperationReceipt("native-op", "lane", base, plan.snapshot, ("local",), limits)
    return base, plan.snapshot, receipt


def test_native_pending_classification_is_exact_and_does_not_infer_claim_ids(limits):
    base, candidate, receipt = pending(limits)
    result = q.classify_pending(candidate, native_operation_receipt=receipt)
    assert result["status"] == "KNOWN_NATIVE_PENDING"
    assert result["transaction_ids"] == ("local",) and result["effect"] == "not_attempted"
    noop = replace(receipt, original_candidate_snapshot=base, authorized_transaction_ids=())
    assert q.classify_pending(base, native_operation_receipt=noop)["status"] == "NATIVE_NO_PENDING"


@pytest.mark.parametrize("case", ["none", "missing-id", "wrong-id", "mutable-ids", "different-candidate", "bad-tag"])
def test_unknown_or_mismatched_native_pending_work_is_refused(case, limits):
    base, candidate, receipt = pending(limits)
    if case == "none":
        receipt = None
    elif case == "missing-id":
        receipt = replace(receipt, authorized_transaction_ids=())
    elif case == "wrong-id":
        receipt = replace(receipt, authorized_transaction_ids=("claim_id",))
    elif case == "mutable-ids":
        receipt = replace(receipt, authorized_transaction_ids=["local"])
    elif case == "different-candidate":
        candidate = p.plan_append(base, transaction_id="local", serialized_rows=[b"other\n"], limits=limits).snapshot
    else:
        receipt = replace(receipt, operation_id="invalid operation tag")
    with pytest.raises(p.SnapshotIntegrityError):
        q.classify_pending(candidate, native_operation_receipt=receipt)


def test_native_restart_preserves_remote_prefix_then_pending_occurrences(limits):
    base, candidate, receipt = pending(limits)
    remote = p.plan_append(base, transaction_id="remote", serialized_rows=[b"remote\n"], limits=limits).snapshot
    result = q.rebase_native_pending(remote, native_operation_receipt=receipt)
    with p.open_logical_bytes(result.snapshot) as handle:
        assert handle.read() == b"unterminatedremote\nsame\nsame\n"
    assert result.applied == ("local",)
    retried = q.rebase_native_pending(result.snapshot, native_operation_receipt=receipt)
    assert retried.snapshot is result.snapshot and retried.already_applied == ("local",)


def test_native_restart_refuses_stale_full_view_replacement(limits):
    base, _, receipt = pending(limits)
    replaced = p.plan_replace_view(base, transaction_id="replace", expected_view_digest=base.root.logical_digest,
                                   replacement_rows=[b"replacement\n"], limits=limits).snapshot
    remote = p.plan_append(base, transaction_id="remote", serialized_rows=[b"remote\n"], limits=limits).snapshot
    receipt = replace(receipt, original_candidate_snapshot=replaced, authorized_transaction_ids=("replace",))
    with pytest.raises(p.SnapshotIntegrityError, match="CONFLICT"):
        q.rebase_native_pending(remote, native_operation_receipt=receipt)


@pytest.mark.parametrize("graft_location", ["local", "environment"])
def test_grafts_cannot_hide_an_oversized_deleted_ancestor(
    graft_location, tmp_path, limits, monkeypatch
):
    limited = replace(limits, git_blob_bytes=2048)
    root, baseline, _, base = fixture_repo(tmp_path, limited)
    git(root, "config", "advice.graftFileDeprecated", "false")
    large = root / "grafted-intermediate.bin"
    large.write_bytes(b"x" * 4096)
    git(root, "add", ".")
    git(root, "commit", "-qm", "oversized intermediate before graft")
    git(root, "rm", "-q", str(large))
    git(root, "commit", "-qm", "delete oversized final-tree file")
    candidate = git(root, "rev-parse", "HEAD")
    with pytest.raises(p.SnapshotIntegrityError, match="NONRETRYABLE_OVERSIZE"):
        checked(root, candidate, baseline, base, limited)
    graft = f"{candidate} {baseline}" + chr(10)
    graft_path = root / ".git/info/grafts" if graft_location == "local" else tmp_path / "external-grafts"
    graft_path.write_text(graft)
    if graft_location == "environment":
        monkeypatch.setenv("GIT_GRAFT_FILE", str(graft_path))
    before = physical_state(root)
    index = (root / ".git/index").read_bytes()
    with pytest.raises(p.SnapshotIntegrityError, match="NONRETRYABLE_OVERSIZE"):
        checked(root, candidate, baseline, base, limited)
    assert graft_path.read_text() == graft
    assert git(root, "rev-parse", "HEAD") == candidate
    assert physical_state(root) == before
    assert (root / ".git/index").read_bytes() == index


def test_caller_shallow_override_cannot_hide_repository_shallow_marker(
    tmp_path, limits, monkeypatch
):
    root, baseline, _, base = fixture_repo(tmp_path, limits)
    marker = root / ".git/shallow"
    marker.write_text(baseline + chr(10))
    external = tmp_path / "empty-shallow"
    external.write_bytes(b"")
    monkeypatch.setenv("GIT_SHALLOW_FILE", str(external))
    index = (root / ".git/index").read_bytes()
    with pytest.raises(p.SnapshotIntegrityError, match="shallow"):
        checked(root, baseline, baseline, base, limits)
    assert marker.read_text() == baseline + chr(10)
    assert external.read_bytes() == b""
    assert (root / ".git/index").read_bytes() == index
