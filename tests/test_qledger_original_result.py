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
    original_clock_hook = q._start_control_clocks_for
    def observed_clock_hook(rows, root, today=None):
        clocks.append(list(rows))
        return original_clock_hook(rows, root, today=today)
    monkeypatch.setattr(q, "_start_control_clocks_for", observed_clock_hook)
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


thematic_source = pytest.mark.parametrize("fixture", [{"raw": b'{"claim_id":"x","status":"open"}\n', "part_bytes": 256}], indirect=True)


def thematic_owner(original, monkeypatch):
    from engine import thematic_desk as td, qledger_desk_adapter as adapter, qledger_evidence_clock as clock
    from scripts import build_allocation as allocation
    q, store, binding, identities, root, clocks = owner_bridge(original, monkeypatch)
    intent = identities[0]
    prepared = []
    monkeypatch.setattr(td, 'gather_thematic_state', lambda *a: {'fixture': True})
    def synthesize(*a):
        prepared.append('domain')
        return {'theses': [{'fixture': True}]}
    monkeypatch.setattr(td, 'synthesize', synthesize)
    monkeypatch.setattr(td, '_append_ledger', lambda *a, **k: [{'market': 'us', 'lean': 'overweight'}])
    monkeypatch.setattr(td, 'score_ledger', lambda: pytest.fail('native owner invocation launched unowned grading'))
    monkeypatch.setattr(adapter, 'translate_row', lambda *a, **k: {'claim_id': 'thematic-new', 'status': 'open', 'horizon_d': 5})
    monkeypatch.setattr(adapter, 'outcome_not_yet_determined', lambda *a: (True, ''))
    monkeypatch.setattr(clock, 'git_sha', lambda root: 'fixture-provenance')
    family_clocks = []
    original_family_clock = clock.record_start
    def observed_family_clock(*args, **kwargs):
        family_clocks.append('attempted')
        return original_family_clock(*args, **kwargs)
    monkeypatch.setattr(clock, 'record_start', observed_family_clock)
    def invoke():
        return allocation.run_native_thematic_owner(['us'], native_intents={'us': intent},
            root=binding.repo_root, owner_binding=binding, call=object())
    return td, adapter, clock, binding, intent, root, prepared, family_clocks, invoke


@thematic_source
def test_thematic_owner_success_returns_actual_original_write_and_result(original, monkeypatch):
    td, _, _, binding, intent, root, prepared, clocks, invoke = thematic_owner(original, monkeypatch)
    value = invoke()['us']
    assert isinstance(value, td.NativeThematicResult)
    assert value.intent == intent and value.claims_status == 'materialized' and value.status == 'returned'
    assert value.attempts == binding.attempts and len(value.attempts) == 1
    assert value.original_results == binding.prepared_original_results
    assert value.written_rows == ({"market": "us", "lean": "overweight"},)
    assert value.thematic_ledger_status == "returned"
    assert value.family_clock_status == 'readback_verified' and clocks == ['attempted']
    assert (root / 'bridge' / 'manifest.json').exists() and prepared == ['domain']
    with pytest.raises(td.NativeThematicFailure) as failure:
        invoke()
    assert failure.value.result.attempts == value.attempts
    assert prepared == ['domain']  # no domain replay or replacement result


@pytest.mark.parametrize('uncertain', [False, True])
@thematic_source
def test_thematic_owner_propagates_retention_refusal_and_uncertain_root(original, monkeypatch, uncertain):
    td, adapter, _, binding, intent, root, prepared, clocks, invoke = thematic_owner(original, monkeypatch)
    before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    if uncertain:
        real_replace = n.os.replace
        def lost(source, target, *args, **kwargs):
            value = real_replace(source, target, *args, **kwargs)
            if str(target) == Path(p.ROOT_PATH).name:
                raise OSError('fixture native ROOT response lost')
            return value
        monkeypatch.setattr(n.os, 'replace', lost)
    else:
        monkeypatch.setattr(result, '_sync_file', lambda fd: (_ for _ in ()).throw(OSError('fixture original retention refused')))
    with pytest.raises(td.NativeThematicFailure) as failure:
        invoke()
    value = failure.value.result
    assert isinstance(failure.value.__cause__, adapter.NativeProspectiveFailure)
    assert value.attempts == binding.attempts and len(value.attempts) == 1
    assert value.original_results == binding.prepared_original_results
    assert value.family_clock_status == 'not_attempted' and not clocks
    assert value.claims_status == ('root_effect_uncertain' if uncertain else 'unproven')
    if not uncertain:
        assert (binding.repo_root / p.ROOT_PATH).read_bytes() == before
    assert prepared == ['domain']


@thematic_source
def test_thematic_owner_clock_failure_keeps_applied_claims_and_uncertain_clock(original, monkeypatch):
    td, adapter, clock, binding, _, root, prepared, clocks, invoke = thematic_owner(original, monkeypatch)
    def lost(*a, **k):
        clocks.append('attempted')
        raise OSError('fixture clock response lost')
    monkeypatch.setattr(clock, 'record_start', lost)
    with pytest.raises(td.NativeThematicFailure) as failure:
        invoke()
    value = failure.value.result
    assert value.claims_status == 'materialized' and value.family_clock_status == 'uncertain'
    assert value.attempts == binding.attempts and value.original_results == binding.prepared_original_results
    assert clocks == ['attempted'] and (root / 'bridge' / 'manifest.json').exists()
    with pytest.raises(td.NativeThematicFailure):
        invoke()
    assert prepared == ['domain'] and clocks == ['attempted']


@thematic_source
def test_thematic_owner_dedupe_is_verified_no_write_not_accepted_count(original, monkeypatch):
    td, adapter, _, binding, _, root, _, clocks, invoke = thematic_owner(original, monkeypatch)
    with p.open_logical_bytes(original[0].plan._before) as raw:
        import json
        row = json.loads(raw.readline())
    assert row.get('claim_id')
    monkeypatch.setattr(adapter, 'translate_row', lambda *a, **k: row)
    value = invoke()['us']
    assert value.registration['n_accepted'] == 1
    assert value.claims_status == 'no_write' and value.attempts == () and value.original_results == ()
    assert value.family_clock_status == 'not_attempted' and not clocks
    assert not (root / 'bridge').exists()


@thematic_source
def test_thematic_native_skipped_is_explicit_and_legacy_failure_remains_optional(original, monkeypatch):
    td, _, _, binding, _, _, prepared, _, invoke = thematic_owner(original, monkeypatch)
    monkeypatch.setattr(td, 'gather_thematic_state', lambda *a: None)
    value = invoke()['us']
    assert value.claims_status == 'not_attempted' and value.status == 'skipped'
    assert not value.attempts and not prepared
    monkeypatch.setattr(td, 'gather_thematic_state', lambda *a: (_ for _ in ()).throw(OSError('fixture unavailable')))
    assert td.run('us', root=binding.repo_root, call=object()) is None
    with pytest.raises(td.NativeThematicFailure):
        invoke()


@thematic_source
def test_thematic_owner_real_clock_swallowed_failure_is_not_success(original, monkeypatch):
    from engine import qledger_evidence_clock as clock
    actual_record_start = clock.record_start
    td, _, _, binding, _, root, _, _, invoke = thematic_owner(original, monkeypatch)
    monkeypatch.setattr(clock, "record_start", actual_record_start)
    actual_link = clock.os.link
    def refused(source, destination, *a, **k):
        if Path(destination) == clock._clock_path("thematic_desk", binding.repo_root):
            raise OSError("fixture clock persistence refused")
        return actual_link(source, destination, *a, **k)
    monkeypatch.setattr(clock.os, "link", refused)
    with pytest.raises(td.NativeThematicFailure) as failure:
        invoke()
    assert failure.value.result.claims_status == "materialized"
    assert failure.value.result.family_clock_status == "uncertain"
    assert failure.value.result.attempts == binding.attempts
    assert (root / "bridge" / "manifest.json").exists()
    assert clock.read_start("thematic_desk", binding.repo_root) is None


@thematic_source
def test_thematic_owner_claim_preparation_error_is_not_empty_success(original, monkeypatch):
    from engine import qledger as q
    td, _, _, binding, _, root, _, clocks, invoke = thematic_owner(original, monkeypatch)
    monkeypatch.setattr(q, "_prepare_claim", lambda *a: (_ for _ in ()).throw(ValueError("fixture invalid claim preparation")))
    with pytest.raises(td.NativeThematicFailure) as failure:
        invoke()
    assert failure.value.result.status == "failed"
    assert failure.value.result.claims_status == "no_write"
    assert not failure.value.result.attempts and not clocks
    assert not (root / "bridge").exists()


@thematic_source
def test_thematic_owner_partial_desk_append_is_unknown_not_no_rows(original, monkeypatch):
    td, _, _, binding, _, root, _, clocks, invoke = thematic_owner(original, monkeypatch)
    def lost(*a, **k):
        raise OSError("fixture desk-ledger response lost")
    monkeypatch.setattr(td, "_append_ledger", lost)
    with pytest.raises(td.NativeThematicFailure) as failure:
        invoke()
    assert failure.value.result.thematic_ledger_status == "uncertain"
    assert failure.value.result.written_rows == ()
    assert failure.value.result.claims_status == "not_attempted"
    assert not binding.attempts and not clocks and not (root / "bridge").exists()


@thematic_source
def test_thematic_owner_old_open_plus_new_rejected_does_not_start_clock(original, monkeypatch):
    td, adapter, _, binding, _, _, _, clocks, invoke = thematic_owner(original, monkeypatch)
    rows = [{'market': 'us', 'lean': 'overweight', 'id': 'old'},
            {'market': 'us', 'lean': 'overweight', 'id': 'new'}]
    monkeypatch.setattr(td, '_append_ledger', lambda *a, **k: rows)
    monkeypatch.setattr(adapter, 'translate_row', lambda row, **k:
        {'claim_id': 'x' if row['id'] == 'old' else 'new-rejected',
         'status': 'open' if row['id'] == 'old' else 'rejected', 'horizon_d': 5})
    value = invoke()['us']
    assert value.claims_status == 'materialized'
    assert value.registration['n_accepted'] == 1 and value.registration['n_rejected'] == 1
    assert value.family_clock_status == 'not_attempted' and not clocks


@thematic_source
def test_explicit_immutable_git_scope_reads_native_despite_empty_checkout(original, monkeypatch):
    from engine import qledger_store as store
    write, _, _, _, limits, candidate = original
    repo = write.claims_path.parents[2]
    commit = candidate.continuity.accepted_tip_oid
    binding = store.NativeGitClaimsBinding(repo, commit_oid=commit,
        expected_root_digest=write.plan._before.receipt.root_digest, limits=limits)
    write.claims_path.write_bytes(b'')
    (repo / p.ROOT_PATH).write_bytes(b'partially checked out root')
    monkeypatch.setattr(store, '_synthetic_claims_binding', lambda *a, **k: pytest.fail('production owner used fixture hook'))
    with store.ClaimsBindingScope(binding):
        with store.ClaimsReadScope(repo):
            value = store.read_raw_lines(write.claims_path, encoding='latin1')
            text, source = store.read_tracked_claims_text(repo, Path(p.BASE_PATH),
                legacy_reader=lambda *a: pytest.fail('native immutable read fell through to empty legacy base'))
    with p.open_logical_bytes(write.plan._before) as raw:
        expected = raw.read()
    assert value == expected.decode('latin1').splitlines()
    assert text == expected.decode('utf-8') and source.startswith('qledger-native:')


def test_unbound_native_root_refuses_legacy_reads_writes_and_cli(original, monkeypatch, capsys):
    from engine import qledger_store as store, qledger as q
    from scripts.ci import qledger_publication as publication
    repo = original[0].claims_path.parents[2]
    path = original[0].claims_path
    path.write_bytes(b'')
    (repo / p.ROOT_PATH).write_bytes(b'unknown native ROOT')
    monkeypatch.setattr(q, '_prepare_claim', lambda *a: pytest.fail('unowned native write prepared claims'))
    for read in (lambda: store.read_raw_lines(path), lambda: q.load_claims(repo),
                 lambda: store.read_tracked_claims_text(repo, Path(p.BASE_PATH), legacy_reader=lambda *a: pytest.fail('legacy fallback')),
                 lambda: q.register({'fixture': True}, repo)):
        with pytest.raises(p.SnapshotIntegrityError, match='NATIVE_BINDING_REQUIRED'):
            read()
    with pytest.raises(p.SnapshotIntegrityError, match='NATIVE_BINDING_REQUIRED'):
        with store.open_raw_lines(path):
            pytest.fail('unbound native stream opened')
    assert publication.main(['--repo', str(repo), '--boundary', 'publish-candidate']) == 1
    assert 'NATIVE_BINDING_REQUIRED' in capsys.readouterr().out
    assert path.read_bytes() == b'' and (repo / p.ROOT_PATH).read_bytes() == b'unknown native ROOT'


@thematic_source
def test_public_binding_scope_refuses_readonly_write_and_conflicting_generation(original, monkeypatch):
    from engine import qledger_store as store, qledger as q
    write, _, _, _, limits, candidate = original
    repo = write.claims_path.parents[2]
    binding = store.NativeGitClaimsBinding(repo, commit_oid=candidate.continuity.accepted_tip_oid,
        expected_root_digest=write.plan._before.receipt.root_digest, limits=limits)
    other = store.NativeGitClaimsBinding(repo, commit_oid=candidate.candidate_oid,
        expected_root_digest=write.plan.snapshot.receipt.root_digest, limits=limits)
    with pytest.raises(p.SnapshotIntegrityError, match='explicit root'):
        store.NativeGitClaimsBinding(repo, commit_oid=candidate.candidate_oid,
            expected_root_digest='0'*64, limits=limits)
    monkeypatch.setattr(q, '_prepare_claim', lambda *a: pytest.fail('read-only source prepared mutation'))
    with pytest.raises(RuntimeError, match='fixture consumer failed'):
        with store.ClaimsBindingScope(binding):
            with store.ClaimsBindingScope(binding):
                assert store._selected_claims_binding(write.claims_path) is binding
            with store.ClaimsReadScope(repo):
                first = store.read_raw_lines(write.claims_path)
                from tests.test_qledger_conversion_candidate import git
                git(repo, 'update-ref', 'refs/remotes/origin/main', candidate.candidate_oid)
                with pytest.raises(p.SnapshotIntegrityError, match='another explicit binding'):
                    with store.ClaimsBindingScope(other):
                        pass
                with pytest.raises(p.SnapshotIntegrityError, match='READ_ONLY'):
                    q.register({'fixture': True}, repo, native_intent=write.intent)
                assert store.read_raw_lines(write.claims_path) == first
            raise RuntimeError('fixture consumer failed')
    assert isinstance(store._selected_claims_binding(write.claims_path), store.LegacyClaimsBinding)
    with store.ClaimsBindingScope(other):
        assert store.read_raw_lines(write.claims_path) != first
    with pytest.raises(p.SnapshotIntegrityError, match='explicit claims owner'):
        with store.ClaimsBindingScope(object()):
            pass


@thematic_source
def test_public_binding_does_not_shadow_existing_read_scope_or_use_fixture_hook(original, monkeypatch):
    from engine import qledger_store as store
    write, _, _, _, limits, candidate = original
    repo = write.claims_path.parents[2]
    binding = store.NativeGitClaimsBinding(repo, commit_oid=candidate.continuity.accepted_tip_oid,
        expected_root_digest=write.plan._before.receipt.root_digest, limits=limits)
    with store.ClaimsReadScope(repo):
        with pytest.raises(p.SnapshotIntegrityError, match='active read scope'):
            with store.ClaimsBindingScope(binding):
                pass
    monkeypatch.setattr(store, '_synthetic_claims_binding', lambda *a, **k: pytest.fail('fixture hook'))
    with store.ClaimsBindingScope(binding):
        with store.ClaimsReadScope(repo):
            assert store.read_raw_lines(write.claims_path)
    assert isinstance(store._selected_claims_binding(write.claims_path), store.LegacyClaimsBinding)


@thematic_source
def test_explicit_owner_invocation_rejects_missing_foreign_root_and_intent_before_producer(original, monkeypatch):
    from scripts import build_allocation as allocation
    td, _, _, binding, intent, _, prepared, _, _ = thematic_owner(original, monkeypatch)
    calls = []
    monkeypatch.setattr(td, 'run', lambda *a, **k: calls.append((a, k)) or pytest.fail('unqualified owner invoked producer'))
    for owner, root, identity in [(None, binding.repo_root, intent),
                                 (binding, binding.repo_root.parent, intent),
                                 (binding, binding.repo_root, replace(intent, lane_id='foreign'))]:
        with pytest.raises((ValueError, p.SnapshotIntegrityError)):
            allocation.run_native_thematic_owner(['us'], native_intents={'us': identity}, root=root, owner_binding=owner)
    assert not prepared and not calls and not binding.attempts


@thematic_source
def test_owner_publication_reads_retained_original_and_builds_current_binding(original, monkeypatch):
    from tests.test_qledger_conversion_candidate import git
    q, store, binding, identities, root, _ = owner_bridge(original, monkeypatch)
    with store.ClaimsBindingScope(binding):
        q.register({'claim_id': 'owned'}, binding.repo_root, dedupe=False, native_intent=identities[0])
    write, prepared = binding.prepared_original_results[0]
    checked = binding.read_original_write_result(write)
    old_oid = checked.candidate_oid
    original_manifest = (root / 'bridge' / 'manifest.json').read_bytes()
    # A separately accepted commit with unchanged claims still invalidates the
    # original candidate's parent. Fixture-only commit/ref changes, no publisher.
    tree = git(binding.repo_root, 'rev-parse', checked.accepted_tip_oid+'^{tree}').decode()
    current_tip = git(binding.repo_root, 'commit-tree', tree, '-p', checked.accepted_tip_oid,
                      input=b'fixture accepted source integration\n').decode()
    git(binding.repo_root, 'update-ref', 'refs/remotes/origin/main', current_tip)
    (binding.repo_root / '.git/objects' / old_oid[:2] / old_oid[2:]).unlink()
    before = ((binding.repo_root / p.ROOT_PATH).read_bytes(), (binding.repo_root / '.git/index').read_bytes(),
              git(binding.repo_root, 'show-ref'))
    current = binding.prepare_publication_candidate(write, accepted_tip_oid=current_tip,
        accepted_ref='refs/remotes/origin/main', commit_metadata=result.git_candidate.CandidateCommitMetadata(
            'Current owner publication', 'fixture@example.invalid', 1700000600))
    assert current.binding.accepted_tip_oid == current_tip and current.candidate_oid != old_oid
    assert current.original_operation_receipt.original_base_snapshot.root_bytes == write.plan._before.root_bytes
    output = git(binding.repo_root, 'hash-object', '-w', '--stdin', input=b'actual engine output\n').decode()
    actual_tree = result.git_candidate._tree_with_members(binding.repo_root, current.tree_oid, {(b'engine-output',): output}, binding.limits)
    actual = git(binding.repo_root, 'commit-tree', actual_tree, '-p', current_tip, input=b'actual owner output commit\n').decode()
    bound, witness = binding.check_publication_candidate(write, candidate_oid=actual, expected_tree_oid=actual_tree,
        accepted_tip_oid=current_tip, accepted_ref='refs/remotes/origin/main')
    assert bound.accepted_tip_oid == current_tip and witness.publication.candidate_oid == actual
    assert git(binding.repo_root, 'show', actual+':engine-output') == b'actual engine output'
    assert (root / 'bridge' / 'manifest.json').read_bytes() == original_manifest
    assert ((binding.repo_root / p.ROOT_PATH).read_bytes(), (binding.repo_root / '.git/index').read_bytes(),
            git(binding.repo_root, 'show-ref')) == before
    assert not (binding.repo_root / '.git/objects' / old_oid[:2] / old_oid[2:]).exists()
    (root / 'bridge' / 'manifest.json').unlink()
    monkeypatch.setattr(result.git_candidate, 'prepare_native_publication_candidate',
        lambda *a, **k: pytest.fail('missing retained original reached publication preparation'))
    with pytest.raises(p.SnapshotIntegrityError):
        binding.prepare_publication_candidate(write, accepted_tip_oid=current_tip,
            accepted_ref='refs/remotes/origin/main', commit_metadata=current.commit_metadata)
    with pytest.raises(p.SnapshotIntegrityError):
        binding.check_publication_candidate(write, candidate_oid=actual, expected_tree_oid=actual_tree,
            accepted_tip_oid=current_tip, accepted_ref='refs/remotes/origin/main')
