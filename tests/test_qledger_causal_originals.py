"""Test-owned future originals only; no clocks, production roots or admission."""
from dataclasses import replace
import json
import os

import pytest

from tests.test_qledger_conversion_candidate import fixture, native_fixture, prepare_native, prepare, git  # noqa: F401
from tests.test_qledger_original_result import original, owner_bridge  # noqa: F401
from engine import qledger_original_result as r, qledger_store_native as n, qledger_store_protocol as p
from scripts.ci import qledger_conversion_candidate as c
from scripts.ci.qledger_engine_publication import EnginePublicationInvocation

pytestmark = pytest.mark.parametrize('fixture', [{'raw': b'{"claim_id":"accepted"}\n', 'part_bytes': 256}], indirect=True)


@pytest.fixture
def causal(original, monkeypatch):
    _, store, old, intents, root, _ = owner_bridge(original, monkeypatch, intents=('one', 'two', 'three'))
    targets = {intent: replace(old.original_result_targets[intent], predecessor_intents=tuple(intents[:index]))
               for index, intent in enumerate(intents)}
    binding = r.OriginalResultClaimsBinding(old.claims_path, operation_id=old.operation_id,
        lane_id=old.lane_id, limits=old.limits, original_result_targets=targets)
    return store, binding, intents, root


def append(causal, index):
    store, binding, intents, _ = causal
    with store.ClaimsBindingScope(binding):
        with store._claims_mutation(binding.claims_path, native_intent=intents[index]) as writer:
            writer.append_serialized_rows([b'{"future":"' + str(index).encode() + b'"}\n'])
    return binding.prepared_original_results[-1][0]


def retained_bytes(root):
    return {str(path.relative_to(root)): path.read_bytes() for path in root.rglob('*') if path.is_file()}


def read_kwargs(retained):
    return dict(owner_root=retained.owner_root, result_path=retained.result_path,
        expected_result_id=retained.result_id, expected_manifest_digest=retained.manifest_digest,
        expected_claims_path=retained.write.claims_path, expected_intent=retained.write.intent,
        limits=retained.limits, predecessors=retained.predecessors)


def test_two_pending_originals_retain_separately_before_apply_without_advancing_accepted_ref(causal, monkeypatch):
    _, binding, intents, root = causal
    tip = next(iter(binding.original_result_targets.values())).accepted_tip_oid
    refs = git(binding.repo_root, 'show-ref')
    index = (binding.repo_root / '.git/index').read_bytes()
    real_apply = n.NativeClaimsSession.apply_prepared
    applies, old = [], {}
    def after_exact_retention(session, plan):
        number = len(applies)
        target = binding.original_result_targets[intents[number]]
        write = binding.prepared_original_results[-1][0]
        checked = binding.read_original_write_result(write)
        assert checked.accepted_tip_oid == tip
        assert tuple(x.write.intent for x in checked.predecessors) == tuple(intents[:number])
        assert target.result_path.joinpath('manifest.json').exists()
        assert (binding.repo_root / p.ROOT_PATH).read_bytes() == plan._before.root_bytes
        if number:
            assert all((root / path).read_bytes() == payload for path, payload in old.items())
        else:
            old.update(retained_bytes(root))
            assert json.loads(target.result_path.joinpath('manifest.json').read_bytes())['schema'] == 'qledger-original-result/v1'
        applies.append(plan.transaction.transaction_id)
        return real_apply(session, plan)
    monkeypatch.setattr(n.NativeClaimsSession, 'apply_prepared', after_exact_retention)
    one, two = append(causal, 0), append(causal, 1)
    last = binding.read_original_write_chain((one, two))
    assert last.native_operation_receipt.authorized_transaction_ids == tuple(x.transaction_id for x in intents[:2])
    assert last.write.plan._before.root_bytes == one.plan.snapshot.root_bytes
    assert last.native_operation_receipt.original_base_snapshot.root_bytes == one.plan._before.root_bytes
    assert last.predecessors[0].write.intent == one.intent
    assert git(binding.repo_root, 'show-ref') == refs
    assert (binding.repo_root / '.git/index').read_bytes() == index
    assert applies == [one.intent.transaction_id, two.intent.transaction_id]
    # Restart readback needs the exact typed prefix, not Git objects or discovery.
    monkeypatch.setattr(c.publication, '_git', lambda *a, **k: pytest.fail('retained chain reread used Git'))
    assert r.read_original_result(**read_kwargs(last)).manifest_digest == last.manifest_digest
    assert all((root / path).read_bytes() == payload for path, payload in old.items())


@pytest.mark.parametrize('fault', ['missing-result', 'corrupt-result', 'clock', 'durability', 'visibility', 'before-root', 'foreign-tail'])
def test_predecessor_fault_refuses_next_original_before_native_apply(causal, monkeypatch, fault):
    _, binding, intents, root = causal
    first = append(causal, 0)
    first_result = binding.read_original_write_result(first)
    if fault == 'missing-result':
        (first_result.result_path / 'manifest.json').unlink()
    elif fault == 'corrupt-result':
        next((first_result.result_path / 'members').iterdir()).write_bytes(b'foreign')
    elif fault in ('clock', 'durability', 'visibility'):
        field, value = {'clock': ('clock_status', 'uncertain'), 'durability': ('durability_status', 'uncertain'),
                        'visibility': ('root_visibility', 'unknown')}[fault]
        binding._record(first, replace(binding.attempts[-1].outcome, **{field: value}))
    else:
        snapshot = first.plan._before if fault == 'before-root' else p.plan_append(first.plan.snapshot,
            transaction_id='unaccounted-tail', serialized_rows=[b'unknown\n'], limits=binding.limits).snapshot
        for path, payload in {**snapshot._members, p.ROOT_PATH: snapshot.root_bytes}.items():
            target = binding.repo_root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    evidence = retained_bytes(root)
    monkeypatch.setattr(n.NativeClaimsSession, 'apply_prepared', lambda *a, **k: pytest.fail('invalid predecessor reached apply'))
    with pytest.raises(p.SnapshotIntegrityError):
        append(causal, 1)
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == before
    assert retained_bytes(root) == evidence and not (root / 'two').exists()


def test_explicit_readback_rejects_incomplete_or_foreign_prefix(causal):
    _, binding, _, _ = causal
    writes = tuple(append(causal, i) for i in range(3))
    last = binding.read_original_write_chain(writes)
    prefix = last.predecessors
    for fault in ("missing", "duplicate", "reorder", "foreign", "path", "digest", "profile"):
        args = read_kwargs(last)
        if fault == 'missing':
            args['predecessors'] = prefix[1:]
        elif fault == 'duplicate':
            args['predecessors'] = (prefix[0], prefix[0])
        elif fault == 'reorder':
            args['predecessors'] = tuple(reversed(prefix))
        elif fault == 'foreign':
            args['expected_intent'] = replace(writes[-1].intent, operation_id='foreign')
        elif fault == 'path':
            args['expected_claims_path'] = last.owner_root / p.BASE_PATH
        elif fault == 'digest':
            args['expected_manifest_digest'] = '0' * 64
        else:
            args['limits'] = replace(last.limits, snapshot_bytes=last.limits.snapshot_bytes - 1)
        with pytest.raises(p.SnapshotIntegrityError):
            r.read_original_result(**args)


def test_aggregate_retention_budget_cannot_be_reset_per_original(fixture, tmp_path, monkeypatch):
    from engine import qledger_store as store
    from engine.qledger_store_sources import GitTreeSource, verify_source_snapshot
    repo, tip, blob, raw, original_limits = fixture
    # Create a coherent smaller TEST profile from its original conversion;
    # changing a profile after native-root creation must remain forbidden.
    limits = replace(original_limits, snapshot_members=16)
    converted = prepare((repo, tip, blob, raw, limits))
    git(repo, 'update-ref', 'refs/remotes/origin/main', converted.candidate_oid)
    snapshot = verify_source_snapshot(GitTreeSource(repo, tree_oid=converted.tree_oid, limits=limits), limits=limits)
    for path, payload in {**snapshot._members, p.ROOT_PATH: snapshot.root_bytes}.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    root = tmp_path / 'budget-owner'
    root.mkdir(mode=0o700)
    intents = tuple(n.NativeClaimsIntent('test-budget-originals', 'test-lane', tag) for tag in ('one', 'two'))
    targets = {intent: r.OriginalResultTarget(root, root / intent.transaction_id, intent.transaction_id,
        converted.candidate_oid, 'refs/remotes/origin/main', 'refs/heads/main',
        c.CandidateCommitMetadata('Test originals', 'fixture@example.invalid', 1700000100), intents[:index])
        for index, intent in enumerate(intents)}
    binding = r.OriginalResultClaimsBinding(repo / p.BASE_PATH, operation_id=intents[0].operation_id,
        lane_id=intents[0].lane_id, limits=limits, original_result_targets=targets)
    test_owned = store, binding, intents, root
    first = append(test_owned, 0)
    retained = binding.read_original_write_result(first)
    assert retained.retained_members < binding.limits.snapshot_members
    evidence = retained_bytes(root)
    before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    monkeypatch.setattr(n.NativeClaimsSession, 'apply_prepared', lambda *a, **k: pytest.fail('over-budget chain applied'))
    with pytest.raises(p.SnapshotIntegrityError, match='inventory/byte bounds'):
        append(test_owned, 1)
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == before
    assert retained_bytes(root) == evidence and not (root / 'two').exists()


def test_fork_before_next_original_refuses_inherited_binding_before_apply(causal):
    _, binding, _, root = causal
    append(causal, 0)
    before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    pipe, output = os.pipe()
    pid = os.fork()
    if pid == 0:
        os.close(pipe)
        n.NativeClaimsSession.apply_prepared = lambda *a, **k: (_ for _ in ()).throw(AssertionError('inherited apply'))
        try:
            append(causal, 1)
        except p.SnapshotIntegrityError as exc:
            message = ('REFUSED ' + str(exc)).encode()
        except BaseException as exc:
            message = ('WRONG ' + str(exc)).encode()
        else:
            message = b'WRONG inherited write admitted'
        os.write(output, message)
        os.close(output)
        os._exit(0)
    os.close(output)
    try:
        message = os.read(pipe, 4096).decode()
    finally:
        os.close(pipe)
        _, status = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status) == 0 and message.startswith('REFUSED '), message
    assert 'original process' in message
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == before and not (root / 'two').exists()


def test_complete_engine_tree_requires_all_originals_and_preserves_every_output(causal):
    _, binding, _, root = causal
    one, two = append(causal, 0), append(causal, 1)
    retained = binding.read_original_write_chain((one, two))
    tip, ref = retained.accepted_tip_oid, 'refs/remotes/origin/main'
    native = binding.prepare_publication_candidate(two, accepted_tip_oid=tip, accepted_ref=ref,
                                                  commit_metadata=retained.commit_metadata)
    repo = binding.repo_root
    blob = git(repo, 'hash-object', '-w', '--stdin', input=b'complete engine output\n').decode()
    broad_tree = c._tree_with_members(repo, native.tree_oid, {(b'engine-data',): blob}, binding.limits)
    broad = git(repo, 'commit-tree', broad_tree, '-p', tip, input=b'engine outputs\n').decode()
    page = git(repo, 'hash-object', '-w', '--stdin', input=b'final render sync\n').decode()
    full = c._tree_with_members(repo, broad_tree, {(b'engine-page',): page}, binding.limits)
    source = git(repo, 'commit-tree', full, '-p', broad, input=b'render sync\n').decode()
    before = (git(repo, 'show-ref'), (repo / '.git/index').read_bytes(), retained_bytes(root),
              (repo / p.ROOT_PATH).read_bytes())
    for missing in ((two,), (one, one, two), (two, one, two)):
        with pytest.raises(p.SnapshotIntegrityError):
            EnginePublicationInvocation(binding, two, original_writes=missing)
    owner = EnginePublicationInvocation(binding, two, original_writes=(one, two))
    prepared = owner.prepare(source_candidate_oid=source, expected_tree_oid=full,
                             accepted_tip_oid=tip, accepted_ref=ref)
    bound, witness = owner.check(prepared, push_args=('origin', prepared.candidate_oid + ':refs/heads/main'))
    assert bound.operation_id == binding.operation_id and witness.status == 'NATIVE_OPERATION_VERIFIED'
    assert git(repo, 'rev-parse', prepared.candidate_oid + '^{tree}').decode() == full
    assert git(repo, 'show', prepared.candidate_oid + ':engine-data') == b'complete engine output'
    assert git(repo, 'show', prepared.candidate_oid + ':engine-page') == b'final render sync'
    assert git(repo, 'show', prepared.candidate_oid + ':unrelated') == b'accepted'
    assert git(repo, 'show', '-s', '--format=%P', prepared.candidate_oid).decode() == tip
    assert prepared.source_candidate_oid == source and prepared.candidate_oid != source
    assert not prepared.eligible_for_cutover
    # An extra final-tree transaction cannot be erased or claimed as part of
    # the complete retained chain by making another direct-parent object.
    extra = p.plan_append(two.plan.snapshot, transaction_id='unaccounted-engine-tail',
                          serialized_rows=[b'unknown tail\n'], limits=binding.limits).snapshot
    changes = {tuple(part.encode() for part in path.split('/')):
               git(repo, 'hash-object', '-w', '--stdin', input=payload).decode()
               for path, payload in {**extra._members, p.ROOT_PATH: extra.root_bytes}.items()}
    bad_tree = c._tree_with_members(repo, full, changes, binding.limits)
    bad_source = git(repo, 'commit-tree', bad_tree, '-p', tip, input=b'unknown final tail\n').decode()
    with pytest.raises(p.SnapshotIntegrityError):
        owner.prepare(source_candidate_oid=bad_source, expected_tree_oid=bad_tree,
                      accepted_tip_oid=tip, accepted_ref=ref)
    assert before == (git(repo, 'show-ref'), (repo / '.git/index').read_bytes(), retained_bytes(root),
                      (repo / p.ROOT_PATH).read_bytes())


def test_publication_refuses_unresolved_earlier_original_even_when_last_settled(causal):
    _, binding, _, _ = causal
    one, two = append(causal, 0), append(causal, 1)
    attempts = binding.attempts
    assert attempts[-1].outcome.clock_status != 'uncertain'
    for field, value in (('clock_status', 'uncertain'), ('durability_status', 'uncertain'),
                         ('root_visibility', 'unknown')):
        bad = replace(attempts[0], outcome=replace(attempts[0].outcome, **{field: value}))
        binding._attempts.set((bad,) + attempts[1:])
        with pytest.raises(p.SnapshotIntegrityError, match='unresolved'):
            EnginePublicationInvocation(binding, two, original_writes=(one, two))
    binding._attempts.set(attempts)
    assert EnginePublicationInvocation(binding, two, original_writes=(one, two)).manifest_digest


def test_invalid_predeclared_order_and_missing_original_refuse_before_effect(causal, monkeypatch):
    _, binding, intents, root = causal
    for bad_prefix in ((intents[1],), (intents[0], intents[0]), tuple(reversed(intents[:2]))):
        targets = dict(binding.original_result_targets)
        targets[intents[2]] = replace(targets[intents[2]], predecessor_intents=bad_prefix)
        with pytest.raises(p.SnapshotIntegrityError):
            r.OriginalResultClaimsBinding(binding.claims_path, operation_id=binding.operation_id,
                lane_id=binding.lane_id, limits=binding.limits, original_result_targets=targets)
    targets = dict(binding.original_result_targets)
    targets[intents[1]] = replace(targets[intents[1]], accepted_tip_oid='0' * 40)
    with pytest.raises(p.SnapshotIntegrityError, match='accepted source'):
        r.OriginalResultClaimsBinding(binding.claims_path, operation_id=binding.operation_id,
            lane_id=binding.lane_id, limits=binding.limits, original_result_targets=targets)
    before = (binding.repo_root / p.ROOT_PATH).read_bytes()
    monkeypatch.setattr(n.NativeClaimsSession, 'apply_prepared', lambda *a, **k: pytest.fail('absent predecessor applied'))
    with pytest.raises(p.SnapshotIntegrityError, match='missing or duplicate'):
        append(causal, 1)
    assert not binding.attempts and not list(root.iterdir())
    assert (binding.repo_root / p.ROOT_PATH).read_bytes() == before
