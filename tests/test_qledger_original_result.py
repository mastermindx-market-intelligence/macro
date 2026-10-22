"""Synthetic original-result retention; no real producer, root or publication."""
from dataclasses import replace
from hashlib import sha256
import os
from pathlib import Path

import pytest

from tests.test_qledger_conversion_candidate import fixture, native_fixture, prepare_native
from engine import qledger_store_protocol as p, qledger_store_native as n
from engine.qledger_store import NativeClaimsWrite
from scripts.ci.qledger_publication import NativeOperationReceipt
from engine import qledger_original_result as result


@pytest.fixture
def original(tmp_path, native_fixture):
    repo, _, _, limits, receipt = native_fixture
    plan = p.plan_append(receipt.original_base_snapshot, transaction_id="native:original",
                         serialized_rows=[b'{"original":"fixed-clock"}\n'], limits=limits)
    intent = n.NativeClaimsIntent(receipt.operation_id, receipt.lane_id, "native:original")
    write = NativeClaimsWrite(intent, plan, repo / p.BASE_PATH)
    candidate = prepare_native(native_fixture, native_operation_receipt=NativeOperationReceipt(
        intent.operation_id, intent.lane_id, plan._before, plan.snapshot, (intent.transaction_id,), limits))
    prepared = result.prepare_original_result(write, candidate=candidate, result_id="fixture-original", limits=limits)
    root = tmp_path / "owner-evidence"
    root.mkdir(mode=0o700)
    return write, prepared, root, root / "fixture-original", limits, candidate


def read(original, **changes):
    write, prepared, root, path, limits, _ = original
    kwargs = dict(owner_root=root, result_path=path, expected_result_id=prepared.result_id,
        expected_manifest_digest=prepared.manifest_digest, expected_claims_path=write.claims_path,
        expected_intent=write.intent, limits=limits)
    kwargs.update(changes)
    return result.read_original_result(**kwargs)


def test_retained_result_survives_process_inputs_and_git_object_loss(original):
    write, prepared, root, path, limits, candidate = original
    retained = result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert retained.manifest_digest == prepared.manifest_digest
    # Git is deliberately unavailable afterwards: the result contains original
    # native bytes, roots, transactions and the explicit operation/object binding.
    oid = candidate.candidate_oid
    (write.claims_path.parents[2] / ".git/objects" / oid[:2] / oid[2:]).unlink()
    restored = read(original)
    assert restored.write.intent == write.intent and restored.write.claims_path == write.claims_path
    assert restored.write.plan._before.root_bytes == write.plan._before.root_bytes
    assert restored.write.plan.snapshot.root_bytes == write.plan.snapshot.root_bytes
    with p.open_logical_bytes(restored.write.plan.snapshot) as stream:
        actual = stream.read()
    with p.open_logical_bytes(write.plan.snapshot) as stream:
        assert actual == stream.read()
    assert restored.candidate_oid == candidate.candidate_oid
    assert restored.native_operation_receipt.authorized_transaction_ids == (write.intent.transaction_id,)
    assert result.require_retained_original(write, restored).manifest_digest == prepared.manifest_digest


def test_missing_or_boolean_retention_never_calls_native_apply(original):
    write, _, _, _, _, _ = original
    class Session:
        def apply_prepared(self, plan):
            pytest.fail("unretained input reached native apply")
    for missing in (None, True, object()):
        with pytest.raises(p.SnapshotIntegrityError):
            result.apply_retained_original(Session(), write, missing)


def test_manifest_loss_blocks_apply_even_with_previous_readback(original):
    write, prepared, root, path, _, _ = original
    retained = result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    (path / "manifest.json").unlink()
    class Session:
        def apply_prepared(self, plan):
            pytest.fail("lost manifest reached apply")
    with pytest.raises(p.SnapshotIntegrityError):
        result.apply_retained_original(Session(), write, retained)


def test_partial_install_keeps_evidence_and_never_overwrites(original, monkeypatch):
    _, prepared, root, path, _, _ = original
    monkeypatch.setattr(result, "_sync_file", lambda fd: (_ for _ in ()).throw(OSError("fixture durability failure")))
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert path.exists() and not (path / "manifest.json").exists()
    before = {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert before == {str(p.relative_to(path)): p.read_bytes() for p in path.rglob("*") if p.is_file()}
    with pytest.raises(p.SnapshotIntegrityError):
        read(original)


def test_complete_manifest_response_loss_reconciles_same_explicit_path(original, monkeypatch):
    _, prepared, root, path, _, _ = original
    sync = result._sync_dir
    def response_lost(fd):
        sync(fd)
        if (path / "manifest.json").exists() and os.fstat(fd).st_ino == root.stat().st_ino:
            raise OSError("fixture final retention return lost")
    monkeypatch.setattr(result, "_sync_dir", response_lost)
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    manifest = (path / "manifest.json").read_bytes()
    monkeypatch.setattr(result, "_sync_dir", sync)
    restored = read(original)
    assert restored.manifest_digest == sha256(manifest).hexdigest()
    assert restored.result_path == path and (path / "manifest.json").read_bytes() == manifest


@pytest.mark.parametrize("field", ["target", "intent", "digest", "identity", "profile"])
def test_foreign_binding_refuses(original, field):
    write, prepared, root, path, limits, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    changes = {
        "target": {"expected_claims_path": root / p.BASE_PATH},
        "intent": {"expected_intent": replace(write.intent, operation_id="foreign")},
        "digest": {"expected_manifest_digest": "0" * 64},
        "identity": {"expected_result_id": "other-result"},
        "profile": {"limits": replace(limits, input_rows=limits.input_rows - 1)},
    }[field]
    with pytest.raises(p.SnapshotIntegrityError):
        read(original, **changes)


def test_root_must_exist_be_explicit_and_not_symlinked(original):
    _, prepared, root, path, _, _ = original
    missing = root / "missing"
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=missing, result_path=missing / prepared.result_id, prepared=prepared)
    assert not missing.exists()
    alias = root.parent / "alias"
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=alias, result_path=alias / prepared.result_id, prepared=prepared)
    assert not path.exists()


def test_verified_retention_precedes_explicit_native_apply(original):
    write, prepared, root, path, limits, _ = original
    # Install ONLY a synthetic native base in this fixture's disposable checkout.
    for relative, payload in {**write.plan._before._members, p.ROOT_PATH: write.plan._before.root_bytes}.items():
        target = write.claims_path.parents[2] / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    retained = result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    with n.NativeClaimsSession(write.claims_path.parents[2], intent=write.intent, limits=limits) as session:
        outcome = result.apply_retained_original(session, write, retained)
    assert outcome.status == "materialized" and outcome.clock_status == "not_attempted"
    assert read(original).write.plan.root_bytes == write.plan.root_bytes


@pytest.mark.parametrize("level", ["root", "result", "members"])
def test_readback_rejects_directory_symlink_substitution(original, monkeypatch, level):
    _, prepared, root, path, _, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    read_file = result._read
    substituted = []
    def replace_path(parent, name, maximum, identities):
        value = read_file(parent, name, maximum, identities)
        if name == "manifest.json" and not substituted:
            target = root if level == "root" else (path if level == "result" else path / "members")
            moved = target.with_name(target.name + "-moved")
            target.rename(moved)
            target.symlink_to(moved, target_is_directory=True)
            substituted.append(moved)
        return value
    monkeypatch.setattr(result, "_read", replace_path)
    with pytest.raises(p.SnapshotIntegrityError):
        read(original)
    assert substituted


@pytest.mark.parametrize("kind", ["oversize", "hash", "extra", "writable"])
def test_readback_enforces_exact_bounded_inventory(original, kind):
    _, prepared, root, path, limits, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    member = next((path / "members").iterdir())
    if kind == "oversize":
        with member.open("r+b") as handle:
            handle.truncate(limits.snapshot_bytes + 1)
    elif kind == "hash":
        member.write_bytes(b"wrong-original-bytes")
    elif kind == "extra":
        (path / "members" / ("0" * 64)).write_bytes(b"foreign")
    else:
        (path / "members").chmod(0o777)
    with pytest.raises(p.SnapshotIntegrityError):
        read(original)


def test_non_overwriting_completed_result_and_tampered_object_binding(original):
    import json
    _, prepared, root, path, _, _ = original
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    before = (path / "manifest.json").read_bytes()
    with pytest.raises(p.SnapshotIntegrityError):
        result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    assert (path / "manifest.json").read_bytes() == before
    manifest = json.loads(before)
    manifest["git"]["candidate_oid"] = "0" * 40
    changed = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    (path / "manifest.json").write_bytes(changed)
    # Even a caller's altered hash cannot make a contradictory operation/object
    # binding pass the canonical commit identity check.
    with pytest.raises(p.SnapshotIntegrityError):
        read(original, expected_manifest_digest=sha256(changed).hexdigest())


@pytest.mark.parametrize("kind", ["append", "replace"])
def test_restore_original_plan_preserves_raw_single_transaction_and_refuses_extra_history(kind):
    limits = p.ProtocolLimits(base_bytes=64, part_bytes=64, snapshot_bytes=1048576)
    raw = b"malformed\n"
    root = p.RootRecord(p.MemberRef(p.BASE_PATH, sha256(raw).hexdigest(), len(raw)),
                        None, 0, len(raw), sha256(raw).hexdigest(), limits.fingerprint)
    base = p.verify_snapshot(p.InMemorySource({p.BASE_PATH: raw}, snapshot_id="fixture:original"), root, limits=limits)
    if kind == "append":
        original = p.plan_append(base, transaction_id="original", serialized_rows=[b"duplicate\n", b"duplicate\n"], limits=limits)
    else:
        original = p.plan_replace_view(base, transaction_id="original", expected_view_digest=base.root.logical_digest,
                                       replacement_rows=[b"raw-replacement\n"], limits=limits)
    restored = p.restore_original_plan(base, original.snapshot, transaction_id="original", limits=limits)
    assert restored.root_bytes == original.root_bytes and restored.transaction == original.transaction
    assert restored.members == original.members
    with pytest.raises(p.SnapshotIntegrityError):
        p.restore_original_plan(base, original.snapshot, transaction_id="foreign", limits=limits)
    later = p.plan_append(original.snapshot, transaction_id="later", serialized_rows=[b"later\n"], limits=limits)
    with pytest.raises(p.SnapshotIntegrityError):
        p.restore_original_plan(base, later.snapshot, transaction_id="original", limits=limits)


def test_member_growth_after_census_cannot_exceed_actual_read_budget(fixture, tmp_path, monkeypatch):
    from tests.test_qledger_conversion_candidate import prepare
    from engine.qledger_store_sources import GitTreeSource, verify_source_snapshot
    from tests.test_qledger_conversion_candidate import git
    repo, _, _, raw, limits = fixture
    # A valid small fixture with a supported large per-part ceiling exposes the
    # distinct aggregate allocation boundary; no large real claims are read.
    limits = replace(limits, part_bytes=4 * 1024 * 1024)
    converted = prepare(fixture, limits=limits)
    git(repo, "update-ref", "refs/remotes/origin/main", converted.candidate_oid)
    base = verify_source_snapshot(GitTreeSource(repo, tree_oid=converted.tree_oid, limits=limits), limits=limits)
    plan = p.plan_append(base, transaction_id="original", serialized_rows=[b"new-original\n"], limits=limits)
    intent = n.NativeClaimsIntent("operation:native", "lane:native", "original")
    write = NativeClaimsWrite(intent, plan, repo / p.BASE_PATH)
    receipt = NativeOperationReceipt(intent.operation_id, intent.lane_id, base, plan.snapshot, ("original",), limits)
    candidate = prepare_native((repo, converted.candidate_oid, raw, limits, receipt), native_operation_receipt=receipt)
    prepared = result.prepare_original_result(write, candidate=candidate, result_id="growth-original", limits=limits)
    root = tmp_path / "growth-evidence"
    root.mkdir(mode=0o700)
    path = root / prepared.result_id
    result.retain_original_result(owner_root=root, result_path=path, prepared=prepared)
    native_part = next(payload for relative, payload in base._members.items() if relative.startswith(p.PART_PREFIX))
    target_digest = sha256(native_part).hexdigest()
    read_file = result._read
    consumed, grew = [], []
    def grow_then_read(parent, name, maximum, identities):
        if name == target_digest and not grew:
            # Census already happened. The now-stable file is individually
            # within part_bytes, but exceeds the remaining total by one byte.
            size = limits.snapshot_bytes - sum(consumed) + 1
            (path / "members" / name).write_bytes(b"x" * size)
            grew.append(size)
        payload = read_file(parent, name, maximum, identities)
        consumed.append(len(payload))
        assert sum(consumed) <= limits.snapshot_bytes, "reader allocated past aggregate budget"
        return payload
    monkeypatch.setattr(result, "_read", grow_then_read)
    with pytest.raises(p.SnapshotIntegrityError):
        result.read_original_result(owner_root=root, result_path=path,
            expected_result_id=prepared.result_id, expected_manifest_digest=prepared.manifest_digest,
            expected_claims_path=write.claims_path, expected_intent=write.intent, limits=limits)
    assert grew and sum(consumed) <= limits.snapshot_bytes


def test_growth_during_read_never_allocates_an_extra_probe_byte(tmp_path, monkeypatch):
    target = tmp_path / "original"
    target.write_bytes(b"a")
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    real_read = result.os.read
    observed = []
    def grow(fd, count):
        if not observed:
            with target.open("ab") as handle:
                handle.write(b"b")
        block = real_read(fd, count)
        observed.append(len(block))
        assert sum(observed) <= 1, "read exceeded exact remaining byte budget"
        return block
    monkeypatch.setattr(result.os, "read", grow)
    try:
        with pytest.raises(p.SnapshotIntegrityError):
            result._read(fd, "original", 1, [])
    finally:
        os.close(fd)
    assert sum(observed) <= 1


def owner_bridge(original, monkeypatch, *, intents=("bridge",)):
    from engine import qledger as q, qledger_store as store
    write, _, root, _, limits, candidate = original
    repo = write.claims_path.parents[2]
    for relative, payload in {**write.plan._before._members, p.ROOT_PATH: write.plan._before.root_bytes}.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    monkeypatch.setattr(q, "_prepare_claim", lambda claim: dict(claim))
    clocks = []
    monkeypatch.setattr(q, "_start_control_clocks_for", lambda rows, root, today=None: clocks.append(list(rows)))
    identities = [n.NativeClaimsIntent(write.intent.operation_id, write.intent.lane_id, tag) for tag in intents]
    targets = {intent: result.OriginalResultTarget(root, root / tag, tag,
        candidate.continuity.accepted_tip_oid, candidate.accepted_ref, "refs/heads/main", candidate.commit_metadata)
        for intent, tag in zip(identities, intents)}
    binding = result.OriginalResultClaimsBinding(write.claims_path,
        operation_id=write.intent.operation_id, lane_id=write.intent.lane_id, limits=limits,
        original_result_targets=targets)
    return q, store, binding, identities, root, clocks


def test_owner_bridge_requires_retention_before_registrar_native_apply(original, monkeypatch):
    q, store, binding, identities, root, clocks = owner_bridge(original, monkeypatch)
    intent = identities[0]
    apply = n.NativeClaimsSession.apply_prepared
    seen = []
    def only_after_retention(session, plan):
        assert (root / "bridge" / "manifest.json").exists()
        assert binding.prepared_original_results
        seen.append(plan.transaction.transaction_id)
        return apply(session, plan)
    monkeypatch.setattr(n.NativeClaimsSession, "apply_prepared", only_after_retention)
    with store._synthetic_claims_binding(binding.claims_path, binding):
        assert q.register({"claim_id": "new"}, binding.repo_root, dedupe=False, native_intent=intent) == {"claim_id": "new"}
    assert seen == [intent.transaction_id] and clocks == [[{"claim_id": "new"}]]
    assert binding.last_outcome.status == "materialized"
    assert len(binding.prepared_original_results) == 1


def test_owner_bridge_has_no_result_target_or_identity_factory(original, monkeypatch):
    q, store, binding, identities, root, clocks = owner_bridge(original, monkeypatch)
    before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    unknown = replace(identities[0], transaction_id="not-predeclared")
    with store._synthetic_claims_binding(binding.claims_path, binding):
        with pytest.raises(p.SnapshotIntegrityError, match="predeclared"):
            q.register({"claim_id": "new"}, binding.repo_root, dedupe=False, native_intent=unknown)
    assert not binding.attempts and not list(root.iterdir()) and not clocks
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == before


def test_owner_bridge_refuses_stale_later_mapping_without_retarget(original, monkeypatch):
    q, store, binding, identities, root, clocks = owner_bridge(original, monkeypatch, intents=("one", "two"))
    with store._synthetic_claims_binding(binding.claims_path, binding):
        q.register({"claim_id": "one"}, binding.repo_root, dedupe=False, native_intent=identities[0])
        after_one = (binding.repo_root / p.ROOT_PATH).read_bytes()
        with pytest.raises(p.SnapshotIntegrityError, match="original operation base"):
            q.register({"claim_id": "two"}, binding.repo_root, dedupe=False, native_intent=identities[1])
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == after_one
    assert (root / "one" / "manifest.json").exists() and not (root / "two").exists()
    assert clocks == [[{"claim_id": "one"}]]


@pytest.mark.parametrize("complete", [False, True])
def test_owner_bridge_retention_failure_never_applies_or_replaces_original(original, monkeypatch, complete):
    q, store, binding, identities, root, clocks = owner_bridge(original, monkeypatch)
    native_before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    sync_file, sync_dir = result._sync_file, result._sync_dir
    if complete:
        def lost(fd):
            sync_dir(fd)
            if (root / "bridge" / "manifest.json").exists() and os.fstat(fd).st_ino == root.stat().st_ino:
                raise OSError("fixture original-result return lost")
        monkeypatch.setattr(result, "_sync_dir", lost)
    else:
        monkeypatch.setattr(result, "_sync_file", lambda fd: (_ for _ in ()).throw(OSError("fixture retention barrier failed")))
    with store._synthetic_claims_binding(binding.claims_path, binding):
        with pytest.raises(p.SnapshotIntegrityError):
            q.register({"claim_id": "new"}, binding.repo_root, dedupe=False, native_intent=identities[0])
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == native_before and not clocks
    original_attempt = binding.attempts[0]
    assert original_attempt.outcome is None
    monkeypatch.setattr(result, "_sync_file", sync_file)
    monkeypatch.setattr(result, "_sync_dir", sync_dir)
    monkeypatch.setattr(q, "_prepare_claim", lambda *a: pytest.fail("recovery re-prepared claims"))
    monkeypatch.setattr(result.git_candidate, "prepare_native_operation_candidate", lambda *a, **k: pytest.fail("recovery created replacement Git candidate"))
    if complete:
        assert binding.reconcile_original_write(original_attempt.write).status == "materialized"
    else:
        with pytest.raises(p.SnapshotIntegrityError):
            binding.reconcile_original_write(original_attempt.write)
        assert (binding.repo_root / p.ROOT_PATH).read_bytes() == native_before
    assert list(root.iterdir()) == [root / "bridge"] and not clocks
    assert binding.attempts[0] == original_attempt


def test_owner_bridge_reconciles_uncertain_native_effect_from_retained_original_after_git_loss(original, monkeypatch):
    import json
    q, store, binding, identities, root, clocks = owner_bridge(original, monkeypatch)
    real_replace = n.os.replace
    def uncertain(source, target, *args, **kwargs):
        value = real_replace(source, target, *args, **kwargs)
        if str(target) == Path(p.ROOT_PATH).name:
            raise OSError("fixture native root return lost")
        return value
    monkeypatch.setattr(n.os, "replace", uncertain)
    with store._synthetic_claims_binding(binding.claims_path, binding):
        with pytest.raises(n.ClaimsStorageError) as caught:
            q.register({"claim_id": "new"}, binding.repo_root, dedupe=False, native_intent=identities[0])
    assert caught.value.outcome.status == "root_effect_uncertain" and not clocks
    original_attempt = binding.attempts[0]
    candidate_oid = json.loads((root / "bridge" / "manifest.json").read_bytes())["git"]["candidate_oid"]
    (binding.repo_root / ".git/objects" / candidate_oid[:2] / candidate_oid[2:]).unlink()
    monkeypatch.setattr(n.os, "replace", real_replace)
    monkeypatch.setattr(q, "_prepare_claim", lambda *a: pytest.fail("recovery re-prepared claims"))
    monkeypatch.setattr(result.git_candidate, "prepare_native_operation_candidate", lambda *a, **k: pytest.fail("recovery created replacement candidate"))
    # A restored sealed plan has artifact provenance instead of pretending to
    # be the original locked-local source; exact raw inputs still reconcile.
    _, prepared = binding.prepared_original_results[0]
    restored = result.read_original_result(owner_root=root, result_path=root / "bridge",
        expected_result_id="bridge", expected_manifest_digest=prepared.manifest_digest,
        expected_claims_path=binding.claims_path, expected_intent=identities[0], limits=binding.limits)
    outcome = binding.reconcile_original_write(restored.write, retained_original=restored)
    assert outcome.status == "already_applied" and outcome.clock_status == "uncertain"
    assert binding.attempts[0] == original_attempt and not clocks


def test_owner_bridge_constructor_rejects_factories_duplicate_targets_and_foreign_identity(original, monkeypatch):
    _, _, binding, identities, _, _ = owner_bridge(original, monkeypatch)
    intent = identities[0]
    target = binding.original_result_targets[intent]
    base = dict(explicit_claims_path=binding.claims_path, operation_id=binding.operation_id,
                lane_id=binding.lane_id, limits=binding.limits)
    invalid = [lambda intent: target, {intent: True},
        {intent: target, replace(intent, transaction_id="other"): target},
        {replace(intent, operation_id="foreign"): target},
        {intent: replace(target, owner_root=binding.repo_root, result_path=binding.repo_root / target.result_id)}]
    for values in invalid:
        with pytest.raises(p.SnapshotIntegrityError):
            result.OriginalResultClaimsBinding(**base, original_result_targets=values)
    with pytest.raises(p.SnapshotIntegrityError):
        result.OriginalResultClaimsBinding(**{**base, "limits": replace(binding.limits, history_operations=1)},
            original_result_targets={intent: target, replace(intent, transaction_id="other"):
                replace(target, result_path=target.owner_root / "other", result_id="other")})


def test_owner_bridge_rejects_foreign_retained_location_even_for_identical_original(original, monkeypatch):
    q, store, binding, identities, root, _ = owner_bridge(original, monkeypatch)
    with store._synthetic_claims_binding(binding.claims_path, binding):
        q.register({"claim_id": "new"}, binding.repo_root, dedupe=False, native_intent=identities[0])
    write, prepared = binding.prepared_original_results[0]
    foreign_root = root.parent / "foreign-evidence"
    foreign_root.mkdir(mode=0o700)
    foreign = result.retain_original_result(owner_root=foreign_root,
        result_path=foreign_root / "bridge", prepared=prepared)
    before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    with pytest.raises(p.SnapshotIntegrityError, match="predeclared owner target"):
        binding.reconcile_original_write(write, retained_original=foreign)
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == before and len(binding.attempts) == 1
