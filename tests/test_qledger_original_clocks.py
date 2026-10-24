"""Fresh test-owned originals only; clock facts never grant runtime admission."""
from dataclasses import replace
from datetime import date
import os

import pytest

from tests.test_qledger_conversion_candidate import fixture, native_fixture, prepare_native, git  # noqa: F401
from tests.test_qledger_original_result import original, owner_bridge  # noqa: F401
from engine import qledger as q, qledger_evidence_clock as clocks, qledger_store_native as native
from engine import qledger_store_protocol as protocol
from scripts.ci.qledger_engine_publication import EnginePublicationInvocation

pytestmark = pytest.mark.parametrize('fixture', [{'raw': b'{"claim_id":"accepted"}\n', 'part_bytes': 1024}], indirect=True)


@pytest.fixture
def owned(original, monkeypatch):
    real_hook = q._start_control_clocks_for
    _, store, binding, intents, root, _ = owner_bridge(original, monkeypatch)
    monkeypatch.setattr(q, '_start_control_clocks_for', real_hook)
    return store, binding, intents[0], root


def row(family='thematic_desk', **changes):
    value = dict(claim_id='new-original', status='open', desk=family, claim_family=family,
        direction=1, timestamp='2026-10-24T00:00:00+00:00', asof='2026-10-24', horizon_d=5,
        horizon_unit='trading_days', control='XLK', bench='SPY', scope={'type':'ticker','key':'AAPL'})
    value.update(changes)
    return value


def register(owned, *, family=True, rows=None):
    store, binding, intent, _ = owned
    with store.ClaimsBindingScope(binding):
        if family:
            with binding.prospective_clock_scope(intent, family='thematic_desk', horizon_d=5,
                    horizon_unit='trading_days', git_sha='test-source') as scope:
                result = q.register_batch(rows or [row()], root=binding.repo_root,
                    today=date(2026,10,24), native_intent=intent)
            return result, scope
        result = q.register_batch(rows or [row('stock_desk')], root=binding.repo_root,
            today=date(2026,10,24), native_intent=intent)
        return result, None


def test_no_control_required_plus_family_sequence_completes_exact_original(owned, monkeypatch):
    _, binding, _, _ = owned
    assert q.family_control_policy('thematic_desk')[0] == q.CONTROL_POLICY_BENCHMARK_ONLY
    apply = native.NativeClaimsSession.apply_prepared
    seen = []
    def prebound(session, plan):
        owner = binding._registration_family.get()
        assert owner.sequence is not None and owner.sequence.write.plan is plan
        assert owner.sequence.family_plan is not None
        assert not owner.sequence.control and not owner.sequence.done
        seen.append(plan.transaction.transaction_id)
        return apply(session, plan)
    monkeypatch.setattr(native.NativeClaimsSession, 'apply_prepared', prebound)
    result, scope = register(owned)
    assert result[0]['claim_id'] == 'new-original' and seen
    assert binding.last_outcome.clock_status == 'confirmed'
    assert scope.record == clocks.read_start('thematic_desk', binding.repo_root)
    assert not q._control_clock_path('thematic_desk', binding.repo_root).exists()
    write = binding.attempts[-1].write
    assert EnginePublicationInvocation(binding, write).manifest_digest


def test_required_control_clock_completes_with_triggering_original_timestamp(owned):
    _, binding, _, _ = owned
    register(owned, family=False)
    assert binding.last_outcome.clock_status == 'confirmed'
    assert q.read_control_clock_start('stock_desk', binding.repo_root)['first_controlled_prospective_registration_utc'] == row()['timestamp']
    assert tuple(q.read_control_clock_start('stock_desk', binding.repo_root)) == (
        'claim_family', 'first_controlled_prospective_registration_utc',
        'declared_horizon_d', 'horizon_unit', 'control', 'git_sha')


@pytest.mark.parametrize('fault', ['dir-fsync', 'lost-response', 'intended-return'])
def test_visible_or_returned_family_clock_cannot_settle_failed_sequence(owned, monkeypatch, fault):
    _, binding, _, _ = owned
    actual = clocks.record_start
    if fault == 'dir-fsync':
        real_sync = native._sync_dir
        def failed(fd):
            if clocks._clock_path('thematic_desk', binding.repo_root).exists():
                raise OSError('test directory durability unknown')
            return real_sync(fd)
        monkeypatch.setattr(native, '_sync_dir', failed)
    else:
        def incomplete(*args, **kwargs):
            if fault == 'lost-response':
                actual(*args, **kwargs)
                raise OSError('test original response lost')
            return {'first_prospective_registration_utc':'intended-only'}
        monkeypatch.setattr(clocks, 'record_start', incomplete)
    with pytest.raises((OSError, ValueError)):
        register(owned)
    assert binding.last_outcome.status == 'materialized' and binding.last_outcome.clock_status == 'uncertain'
    if fault != 'intended-return':
        assert clocks._clock_path('thematic_desk', binding.repo_root).exists()
    write = binding.attempts[-1].write
    with pytest.raises(protocol.SnapshotIntegrityError):
        EnginePublicationInvocation(binding, write)
    # Reconciliation may read the exact claims effect; it must never repeat the
    # clock or turn a visible/already-applied claim into settled old authority.
    monkeypatch.setattr(clocks, 'record_start', lambda *a, **k: pytest.fail('clock replay'))
    observed = binding.reconcile_original_write(write)
    assert observed.status == 'already_applied' and observed.clock_status == 'uncertain'
    with pytest.raises(protocol.SnapshotIntegrityError):
        EnginePublicationInvocation(binding, write)


def test_preexisting_family_clock_preserves_original_bytes(owned):
    _, binding, _, _ = owned
    path = clocks._clock_path('thematic_desk', binding.repo_root)
    clocks.record_start('thematic_desk', horizon_d=21, horizon_unit='trading_days', root=binding.repo_root,
                        now='2025-01-01T00:00:00+00:00', strict=True)
    before = path.read_bytes()
    _, scope = register(owned)
    assert binding.last_outcome.clock_status == 'confirmed'
    assert path.read_bytes() == before and scope.record['declared_horizon_d'] == 21


def test_caught_late_failure_does_not_allow_publication(owned, monkeypatch):
    _, binding, _, _ = owned
    actual = clocks.record_start
    def lost(*a, **k):
        actual(*a, **k)
        raise OSError('late P3 response lost')
    monkeypatch.setattr(clocks, 'record_start', lost)
    try:
        register(owned)
    except (OSError, ValueError):
        pass  # Optional producer catches the failed annotation and returns.
    assert binding.last_outcome.clock_status == 'uncertain'
    with pytest.raises(protocol.SnapshotIntegrityError):
        EnginePublicationInvocation(binding, binding.attempts[-1].write)


def test_fork_after_prebinding_cannot_complete_parent_original(owned, monkeypatch):
    _, binding, _, _ = owned
    actual = q._NativeRegistrationClocks.run
    def forced(sequence):
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            try:
                actual(sequence)
            except ValueError as exc:
                message = ('REFUSED '+str(exc)).encode()
            else:
                message = b'WRONG inherited clocks completed'
            os.write(write_fd, message); os.close(write_fd); os._exit(0)
        os.close(write_fd)
        message = os.read(read_fd,4096).decode(); os.close(read_fd)
        _, status = os.waitpid(pid,0)
        assert os.waitstatus_to_exitcode(status) == 0 and message.startswith('REFUSED '), message
        raise OSError('test parent consumed inherited-clock refusal')
    monkeypatch.setattr(q._NativeRegistrationClocks, 'run', forced)
    with pytest.raises(ValueError):
        register(owned)
    assert binding.last_outcome.clock_status == 'uncertain'
    assert not clocks._clock_path('thematic_desk', binding.repo_root).exists()


def test_actual_prospective_adapter_prebinds_family_and_completes(owned, monkeypatch):
    from engine import qledger_desk_adapter as adapter
    store, binding, intent, _ = owned
    monkeypatch.setattr(adapter, 'translate_row', lambda *a, **k: row())
    monkeypatch.setattr(adapter, 'outcome_not_yet_determined', lambda *a: (True, ''))
    with store.ClaimsBindingScope(binding):
        stats = adapter.register_prospective([{'market':'us','lean':'overweight'}],
            family='thematic_desk', root=binding.repo_root, today=date(2026,10,24), native_intent=intent)
    assert stats['native_write_status'] == 'materialized'
    assert stats['family_clock_status'] == 'readback_verified'
    assert binding.last_outcome.clock_status == 'confirmed'


def test_no_write_declares_no_clock_effect_without_fake_completion(owned, monkeypatch):
    _, binding, _, root = owned
    monkeypatch.setattr(clocks, 'record_start', lambda *a, **k: pytest.fail('dedupe clock effect'))
    result, scope = register(owned, rows=[row(claim_id='accepted')])
    assert result[0]['claim_id'] == 'accepted' and scope.record is None
    assert not binding.attempts and not list(root.iterdir())


def test_wrong_prebound_rows_refuse_before_native_apply(owned, monkeypatch):
    store, binding, intent, root = owned
    before = (binding.repo_root / protocol.ROOT_PATH).read_bytes()
    monkeypatch.setattr(native.NativeClaimsSession, 'apply_prepared', lambda *a, **k: pytest.fail('foreign clock input applied'))
    with store.ClaimsBindingScope(binding):
        with store._claims_mutation(binding.claims_path, native_intent=intent) as writer:
            writer.bind_registration_clocks([row()], today=date(2026,10,24))
            with pytest.raises(protocol.SnapshotIntegrityError, match='exact original native write'):
                writer.append_serialized_rows([b'{"foreign":"rows"}\n'])
    assert not binding.attempts and not list(root.iterdir())
    assert (binding.repo_root / protocol.ROOT_PATH).read_bytes() == before


def test_fresh_python_readback_does_not_recover_lost_clock_settlement(owned, monkeypatch):
    import json
    import subprocess
    import sys
    from pathlib import Path
    _, binding, _, _ = owned
    actual = clocks.record_start
    def lost(*a, **k):
        actual(*a, **k)
        raise OSError('original response lost')
    monkeypatch.setattr(clocks, 'record_start', lost)
    with pytest.raises(ValueError):
        register(owned)
    write = binding.attempts[-1].write
    retained = binding.read_original_write_result(write)
    inputs = dict(repo=str(binding.repo_root), root=str(retained.owner_root), path=str(retained.result_path),
        result_id=retained.result_id, manifest=retained.manifest_digest,
        limits=__import__('dataclasses').asdict(binding.limits), intent=__import__('dataclasses').asdict(write.intent))
    code = '''
import json,sys
from pathlib import Path
from engine import qledger_original_result as r, qledger_store_native as n, qledger_store_protocol as p
from scripts.ci.qledger_engine_publication import EnginePublicationInvocation
x=json.load(sys.stdin); intent=n.NativeClaimsIntent(**x['intent']); limits=p.ProtocolLimits(**x['limits'])
a=r.read_original_result(owner_root=Path(x['root']),result_path=Path(x['path']),expected_result_id=x['result_id'],expected_manifest_digest=x['manifest'],expected_claims_path=Path(x['repo'])/p.BASE_PATH,expected_intent=intent,limits=limits)
t=r.OriginalResultTarget(a.owner_root,a.result_path,a.result_id,a.accepted_tip_oid,'refs/remotes/origin/main',a.target_ref,a.commit_metadata)
b=r.OriginalResultClaimsBinding(a.write.claims_path,operation_id=intent.operation_id,lane_id=intent.lane_id,limits=limits,original_result_targets={intent:t})
assert b.reconcile_original_write(a.write,retained_original=a).clock_status=='uncertain'
try: EnginePublicationInvocation(b,a.write,retained_original=a)
except p.SnapshotIntegrityError: print('REFUSED_OLD_CLOCK_SETTLEMENT')
else: raise AssertionError('fresh process accepted old clock authority')
'''
    child = subprocess.run([sys.executable, '-c', code], input=json.dumps(inputs), text=True,
        cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=30)
    assert child.returncode == 0, child.stderr
    assert child.stdout.strip() == 'REFUSED_OLD_CLOCK_SETTLEMENT'
    assert binding.last_outcome.clock_status == 'uncertain'


def test_identical_clock_bytes_at_replaced_inode_do_not_settle_original(owned, monkeypatch):
    _, binding, _, _ = owned
    actual = clocks.record_start
    def replaced(*args, **kwargs):
        returned = actual(*args, **kwargs)
        path = clocks._clock_path('thematic_desk', binding.repo_root)
        replacement = path.with_name('test-identical-replacement')
        replacement.write_bytes(path.read_bytes())
        os.replace(replacement, path)
        return returned
    monkeypatch.setattr(clocks, 'record_start', replaced)
    with pytest.raises(ValueError):
        register(owned)
    assert clocks.read_start('thematic_desk', binding.repo_root)
    assert binding.last_outcome.clock_status == 'uncertain'


def test_two_pending_prospective_originals_complete_whole_sequences(owned, original, monkeypatch):
    from engine import qledger_desk_adapter as adapter, qledger_original_result as results
    store, old, _, root = owned
    first = next(iter(old.original_result_targets))
    second = replace(first, transaction_id='second-original')
    target = old.original_result_targets[first]
    targets = {first: target, second: replace(target, result_path=root/'second-original',
        result_id='second-original', predecessor_intents=(first,))}
    binding = results.OriginalResultClaimsBinding(old.claims_path, operation_id=old.operation_id,
        lane_id=old.lane_id, limits=old.limits, original_result_targets=targets)
    monkeypatch.setattr(adapter, 'translate_row', lambda value, **kwargs: row(claim_id=value['id']))
    monkeypatch.setattr(adapter, 'outcome_not_yet_determined', lambda *a: (True,''))
    refs = git(binding.repo_root,'show-ref')
    with store.ClaimsBindingScope(binding):
        for index, intent in enumerate((first, second)):
            stats = adapter.register_prospective([{'market':'us','lean':'overweight','id':f'new-{index}'}],
                family='thematic_desk', root=binding.repo_root, today=date(2026,10,24), native_intent=intent)
            assert stats['native_write_status']=='materialized' and stats['family_clock_status']=='readback_verified'
            assert binding.last_outcome.clock_status=='confirmed'
    writes = tuple(a.write for a in binding.attempts)
    assert len(writes)==2
    assert EnginePublicationInvocation(binding,writes[-1],original_writes=writes).manifest_digest
    assert git(binding.repo_root,'show-ref')==refs


@pytest.mark.parametrize('fault', ['foreign-family', 'malformed-timestamp', 'symlink'])
def test_unproven_preexisting_clock_refuses_before_native_apply(owned, monkeypatch, fault):
    import json
    _, binding, _, root = owned
    path = clocks._clock_path('thematic_desk', binding.repo_root)
    path.parent.mkdir(parents=True)
    record = dict(claim_family='thematic_desk', first_prospective_registration_utc='2025-01-01T00:00:00+00:00')
    if fault == 'foreign-family':
        record['claim_family'] = 'different-original-family'
    elif fault == 'malformed-timestamp':
        record['first_prospective_registration_utc'] = 'not-an-original-time'
    payload = json.dumps(record).encode()
    if fault == 'symlink':
        target = root/'original-clock'; target.write_bytes(payload); path.symlink_to(target)
    else:
        path.write_bytes(payload)
    before = (binding.repo_root/protocol.ROOT_PATH).read_bytes()
    monkeypatch.setattr(native.NativeClaimsSession, 'apply_prepared', lambda *a, **k: pytest.fail('unproven clock reached apply'))
    with pytest.raises((ValueError, OSError)):
        register(owned)
    assert (binding.repo_root/protocol.ROOT_PATH).read_bytes()==before
    assert not binding.attempts and not (root/'bridge').exists() and path.read_bytes()==payload


@pytest.mark.parametrize('api', ['single', 'batch'])
def test_postapply_preclock_interruption_keeps_original_unresolved(owned, api):
    import inspect
    import sys
    store, binding, intent, _ = owned
    registrar = q.register if api == 'single' else q.register_batch
    lines, start = inspect.getsourcelines(registrar)
    interrupt_at = start + next(index for index, line in enumerate(lines)
        if 'if storage is None or outcome.status == "materialized":' in line)
    class OriginalInterrupted(RuntimeError):
        pass
    def interrupt(frame, event, arg):
        if event == 'line' and frame.f_code is registrar.__code__ and frame.f_lineno == interrupt_at:
            raise OriginalInterrupted('test interrupted after native apply, before clock entry')
        return interrupt
    previous = sys.gettrace()
    with store.ClaimsBindingScope(binding):
        try:
            sys.settrace(interrupt)
            with pytest.raises(OriginalInterrupted):
                registrar(row('stock_desk') if api == 'single' else [row('stock_desk')],
                    root=binding.repo_root, today=date(2026,10,24), native_intent=intent)
        finally:
            sys.settrace(previous)
    assert len(binding.attempts) == 1 and binding.last_outcome.status == 'materialized'
    assert binding.pre_attempt_failure is None
    assert not q._control_clock_path('stock_desk', binding.repo_root).exists()
    # A caught interruption must not look like a settled no-clock direct write.
    with pytest.raises(protocol.SnapshotIntegrityError):
        EnginePublicationInvocation(binding, binding.attempts[0].write)
    assert binding.last_outcome.clock_status == 'uncertain'


def test_direct_write_without_registrar_clock_obligation_stays_distinct(owned):
    store, binding, intent, _ = owned
    with store.ClaimsBindingScope(binding):
        with store._claims_mutation(binding.claims_path, native_intent=intent) as writer:
            writer.append_serialized_rows([b'{"direct":"no registrar hooks"}\n'])
    assert binding.last_outcome.clock_status == 'not_attempted'
    assert EnginePublicationInvocation(binding, binding.attempts[0].write).manifest_digest


def test_materialized_transport_error_before_clock_entry_stays_unresolved(owned, monkeypatch):
    _, binding, _, _ = owned
    apply = native.NativeClaimsSession.apply_prepared
    def returned_error(session, plan):
        outcome = apply(session, plan)
        assert outcome.status == 'materialized' and outcome.clock_status == 'not_attempted'
        raise native.ClaimsStorageError(outcome)
    monkeypatch.setattr(native.NativeClaimsSession, 'apply_prepared', returned_error)
    with pytest.raises(native.ClaimsStorageError) as error:
        register(owned, family=False)
    assert error.value.outcome.clock_status == 'uncertain'
    assert binding.last_outcome.clock_status == 'uncertain'
    assert not q._control_clock_path('stock_desk', binding.repo_root).exists()
    with pytest.raises(protocol.SnapshotIntegrityError):
        EnginePublicationInvocation(binding, binding.attempts[0].write)
