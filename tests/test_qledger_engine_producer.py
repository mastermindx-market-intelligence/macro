"""Future same-process engine composition; all evidence/providers are test-owned."""
from contextlib import contextmanager
from types import SimpleNamespace
import os
import subprocess
import sys

import pytest

from tests.test_qledger_conversion_candidate import fixture, native_fixture, prepare_native, git  # noqa: F401
from tests.test_qledger_original_result import original, thematic_owner  # noqa: F401
from tests.test_qledger_causal_originals import causal, append  # noqa: F401
from engine import qledger_store_protocol as p
from scripts.ci import qledger_engine_publication as engine
from scripts.ci.qledger_owner_invocation import ConversionInvocation

pytestmark = pytest.mark.parametrize('fixture', [{'raw': b'{"claim_id":"x","status":"open"}\n', 'part_bytes':256}], indirect=True)


class FixtureGate:
    """No runtime admission: this object exists only in these tests."""
    def __init__(self):
        self.calls, self.held, self.leased = [], False, False
    @contextmanager
    def lease(self):
        self.leased = True
        try:
            yield
        finally:
            self.leased = False
    def assert_valid(self, **context):
        assert self.leased
        if git(context['repo'], 'rev-parse', 'HEAD').decode() != context['commit_oid']:
            raise p.SnapshotIntegrityError('FIXTURE', 'running checkout version differs')
        self.calls.append(context['phase'])
    def hold(self, **context):
        assert self.leased
        self.held = True
    def begin_install(self, **context): raise AssertionError('no install')
    def confirm_install(self, **context): raise AssertionError('no install')


def invoke(binding, callback, gate):
    # Test-only owner shape; all storage/native/continuity verification is real.
    tip = next(iter(binding.original_result_targets.values())).accepted_tip_oid
    owner = SimpleNamespace(repo=binding.repo_root, limits=binding.limits,
        intent=SimpleNamespace(operation_id='fixture-conversion'),
        target=SimpleNamespace(budget_id='fixture-conversion-budget', retention_id='fixture-conversion-retention'))
    call = ConversionInvocation.__new__(ConversionInvocation)
    call.owner = owner
    with gate.lease():
        return call.invoke_producer(binding, gate=gate, installed_commit_oid=tip,
            budget_id='fixture-original-budget', retention_id='fixture-original-retention', producer=callback)


def context(binding):
    return SimpleNamespace(repo=binding.repo_root)


def full_tree(callback, binding):
    """Actual complete unreferenced final Git tree, not a claims-only stand-in."""
    writes = tuple(w for w, _ in binding.prepared_original_results)
    original = binding.read_original_write_chain(writes)
    tip = original.accepted_tip_oid
    native = binding.prepare_publication_candidate(writes[-1], accepted_tip_oid=tip,
        accepted_ref='refs/remotes/origin/main', commit_metadata=original.commit_metadata)
    members = {}
    for path, payload in ((b'engine-data', b'complete engine output\n'), (b'engine-page', b'final render-sync\n')):
        members[(path,)] = git(binding.repo_root, 'hash-object', '-w', '--stdin', input=payload).decode()
    tree = engine.candidate._tree_with_members(binding.repo_root, native.tree_oid, members, binding.limits)
    broad = git(binding.repo_root, 'commit-tree', tree, '-p', tip, input=b'full engine source\n').decode()
    final = git(binding.repo_root, 'commit-tree', tree, '-p', broad, input=b'actual final render\n').decode()
    return callback(source_candidate_oid=final, expected_tree_oid=tree,
        accepted_tip_oid=tip, accepted_ref='refs/remotes/origin/main')


def build(binding, intents, finalizer):
    # The inherited storage fixture creates the accepted conversion object but
    # does not install its ref. Model that already-installed fixture before the
    # future original starts; no product checkout/admission is performed.
    git(binding.repo_root, 'update-ref', 'HEAD',
        next(iter(binding.original_result_targets.values())).accepted_tip_oid)
    return engine.build_native_engine_producer(context(binding), owner_binding=binding,
        regions=tuple(intents), native_intents=intents, finalizer=finalizer, call=object())


def test_live_owner_runs_real_thematic_once_and_checks_full_final_tree(original, monkeypatch):
    from scripts import build_allocation as allocation
    _, _, _, binding, intent, _, prepared, clocks, _ = thematic_owner(original, monkeypatch)
    monkeypatch.setattr(allocation.config, 'ROOT', binding.repo_root)
    builds = []
    monkeypatch.setattr(allocation, 'main', lambda regions, **kw: builds.append((tuple(regions), kw)) or False)
    gate = FixtureGate()
    def finalize(callback):
        assert gate.leased
        return full_tree(callback, binding)
    actual, callback = build(binding, {'us':intent}, finalize)
    assert actual is binding
    value = invoke(binding, callback, gate)
    assert value.publication.tree_oid == git(binding.repo_root, 'rev-parse', value.publication.candidate_oid+'^{tree}').decode()
    assert git(binding.repo_root, 'show', value.publication.candidate_oid+':engine-data') == b'complete engine output'
    assert git(binding.repo_root, 'show', value.publication.candidate_oid+':engine-page') == b'final render-sync'
    assert value.original_writes == tuple(w for w, _ in binding.prepared_original_results)
    assert value.regions['us'].family_clock_status == 'readback_verified'
    assert builds == [(('us',), {'run_ai':False})]
    assert prepared == ['domain'] and clocks == ['attempted'] and not gate.held
    assert 'engine-final-candidate' in gate.calls
    assert value.publication.eligible_for_cutover is False
    with pytest.raises(p.SnapshotIntegrityError, match='already entered'):
        invoke(binding, callback, gate)
    assert prepared == ['domain']


def test_multiple_originals_are_complete_and_actual_final_source_is_preserved(causal, monkeypatch):
    from scripts import build_allocation as allocation
    _, binding, intents, _ = causal
    monkeypatch.setattr(allocation.config, 'ROOT', binding.repo_root)
    monkeypatch.setattr(allocation, 'main', lambda *a, **k: False)
    def producers(*a, **k):
        append(causal, 0); append(causal, 1)
        return {'us': 'fixture-one', 'china': 'fixture-two'}
    monkeypatch.setattr(allocation, 'run_native_thematic_owner', producers)
    _, callback = build(binding, dict(zip(('us','china'), intents[:2])), lambda checked: full_tree(checked, binding))
    result = invoke(binding, callback, FixtureGate())
    assert len(result.original_writes) == 2
    assert git(binding.repo_root, 'rev-parse', result.publication.source_candidate_oid+'^{tree}').decode() == result.publication.tree_oid
    assert binding.read_original_write_chain(result.original_writes).native_operation_receipt.authorized_transaction_ids == tuple(x.transaction_id for x in intents[:2])


@pytest.mark.parametrize('fault', ['no-live-owner', 'no-finalizer', 'foreign-process'])
def test_missing_or_inherited_live_owner_refuses_before_any_domain_effect(causal, monkeypatch, fault):
    from scripts import build_allocation as allocation
    _, binding, intents, _ = causal
    monkeypatch.setattr(allocation.config, 'ROOT', binding.repo_root)
    monkeypatch.setattr(allocation, 'main', lambda *a, **k: pytest.fail('unproven owner reached deterministic build'))
    if fault == 'no-finalizer':
        with pytest.raises(p.SnapshotIntegrityError): build(binding, {'us':intents[0]}, None)
        return
    _, callback = build(binding, {'us':intents[0]}, lambda x: pytest.fail('unproven owner finalized'))
    if fault == 'no-live-owner':
        with pytest.raises(p.SnapshotIntegrityError, match='live producer invocation'): callback()
    else:
        read, write = os.pipe()
        pid = os.fork()
        if not pid:
            os.close(read)
            try: invoke(binding, callback, FixtureGate())
            except p.SnapshotIntegrityError: os.write(write, b'REFUSED')
            except BaseException as exc: os.write(write, ('WRONG '+str(exc)).encode())
            else: os.write(write, b'WRONG accepted')
            os._exit(0)
        os.close(write)
        message = os.read(read,4096)
        os.close(read); os.waitpid(pid,0)
        assert message == b'REFUSED', message
    assert not binding.attempts


@pytest.mark.parametrize('fault', ['lost-response', 'swallowed-boundary', 'changed-root', 'missing-original', 'changed-head'])
def test_finalization_failures_hold_without_replaying_the_original(causal, monkeypatch, fault):
    from scripts import build_allocation as allocation
    _, binding, intents, root = causal
    monkeypatch.setattr(allocation.config, 'ROOT', binding.repo_root)
    monkeypatch.setattr(allocation, 'main', lambda *a, **k: False)
    calls=[]
    def producers(*a, **k):
        calls.append('once'); append(causal,0)
        return {'us':'fixture'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',producers)
    def finalize(checked):
        prepared = full_tree(checked,binding)
        if fault=='lost-response': raise OSError('fixture response lost after candidate verification')
        if fault=='swallowed-boundary':
            try: checked(source_candidate_oid=prepared.source_candidate_oid, expected_tree_oid='0'*40,
                         accepted_tip_oid=prepared.accepted_tip_oid, accepted_ref=prepared.accepted_ref)
            except p.SnapshotIntegrityError: pass
        elif fault=='changed-root':
            (binding.repo_root / p.ROOT_PATH).write_bytes(b'unknown-root')
        elif fault=='changed-head':
            git(binding.repo_root, 'update-ref', 'HEAD', prepared.source_candidate_oid)
        else: (root/'one'/'manifest.json').unlink()
        return prepared
    _, callback = build(binding,{'us':intents[0]},finalize)
    gate=FixtureGate()
    with pytest.raises((p.SnapshotIntegrityError,OSError)): invoke(binding,callback,gate)
    assert gate.held and calls==['once']
    with pytest.raises(p.SnapshotIntegrityError): invoke(binding,callback,gate)
    assert calls==['once']


def test_no_write_is_a_producer_success_without_manufactured_publication(causal, monkeypatch):
    from scripts import build_allocation as allocation
    _, binding, intents, _ = causal
    monkeypatch.setattr(allocation.config, 'ROOT', binding.repo_root)
    monkeypatch.setattr(allocation, 'main', lambda *a, **k: False)
    monkeypatch.setattr(allocation, 'run_native_thematic_owner', lambda *a, **k: {'us':'fixture-skipped'})
    _, callback = build(binding, {'us':intents[0]}, lambda *a: pytest.fail('no original must not manufacture candidate'))
    gate=FixtureGate()
    value=invoke(binding, callback, gate)
    assert value.status=='no_native_write' and value.publication is None and not value.original_writes
    assert not gate.held and not binding.attempts


def test_live_scope_does_not_exist_in_fresh_python_process(fixture):
    child=subprocess.run([sys.executable,'-c', '''
from scripts.ci.qledger_owner_invocation import require_live_producer
from engine.qledger_store_protocol import SnapshotIntegrityError
try: require_live_producer(None)
except SnapshotIntegrityError: print('REFUSED fresh process')
else: raise AssertionError('fresh process adopted native owner')
'''],capture_output=True,text=True,check=True)
    assert child.stdout.strip()=='REFUSED fresh process'


def test_escaped_callback_is_closed_after_return_and_unproven_resources_refuse_before_production(causal, monkeypatch):
    from scripts import build_allocation as allocation
    _, binding, intents, _ = causal
    monkeypatch.setattr(allocation.config,'ROOT',binding.repo_root)
    calls=[]
    monkeypatch.setattr(allocation,'main',lambda *a,**k: calls.append('allocation') or False)
    def produce(*a,**k):
        append(causal,0)
        return {'us':'fixture'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    escaped=[]
    def finalize(checked):
        escaped.append(checked)
        return full_tree(checked,binding)
    _, callback=build(binding,{'us':intents[0]},finalize)
    class MissingResources(FixtureGate):
        def assert_valid(self,**context):
            super().assert_valid(**context)
            if context['phase']=='engine-owner-entry':
                raise p.SnapshotIntegrityError('FIXTURE','original producer resources unavailable')
    missing=MissingResources()
    with pytest.raises(p.SnapshotIntegrityError,match='resources unavailable'):
        invoke(binding,callback,missing)
    assert not calls and not binding.attempts and missing.held
    # No domain effect started in the refused entry; actual authority is still
    # exclusively this temporary fixture, never an enrollment receipt.
    value=invoke(binding,callback,FixtureGate())
    with pytest.raises(p.SnapshotIntegrityError,match='closed'):
        escaped[0].check_push(value.publication,push_args=('origin',value.publication.candidate_oid+':refs/heads/main'))


def test_constructor_refuses_earlier_settled_original_instead_of_borrowing_it(causal):
    _, binding, intents, _=causal
    append(causal,0)
    with pytest.raises(p.SnapshotIntegrityError,match='cannot borrow earlier'):
        build(binding,{'us':intents[0]},lambda *a: pytest.fail('borrowed original finalized'))


def test_finalizer_return_without_a_checked_candidate_is_not_success(causal, monkeypatch):
    from scripts import build_allocation as allocation
    _,binding,intents,_=causal
    monkeypatch.setattr(allocation.config,'ROOT',binding.repo_root)
    monkeypatch.setattr(allocation,'main',lambda *a,**k: False)
    def produce(*a,**k):
        append(causal,0)
        return {'us':'fixture'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    _,callback=build(binding,{'us':intents[0]},lambda checked: None)
    gate=FixtureGate()
    with pytest.raises(p.SnapshotIntegrityError,match='actual checked final candidate'):
        invoke(binding,callback,gate)
    assert gate.held and len(binding.prepared_original_results)==1


def test_callback_admission_rejects_original_created_after_construction(causal, monkeypatch):
    from scripts import build_allocation as allocation
    _,binding,intents,_=causal
    monkeypatch.setattr(allocation.config,'ROOT',binding.repo_root)
    effects=[]
    monkeypatch.setattr(allocation,'main',lambda *a,**k: effects.append('allocation') or False)
    monkeypatch.setattr(allocation,'run_native_thematic_owner',lambda *a,**k: {'us':'borrowed'})
    _,callback=build(binding,{'us':intents[0]},lambda checked:full_tree(checked,binding))
    outside=append(causal,0)  # exact original, after construction/before callback
    before=(binding.repo_root/p.ROOT_PATH).read_bytes()
    gate=FixtureGate()
    with pytest.raises(p.SnapshotIntegrityError,match='fresh original invocation'):
        invoke(binding,callback,gate)
    assert gate.held and not effects
    assert binding.prepared_original_results[0][0] is outside
    assert (binding.repo_root/p.ROOT_PATH).read_bytes()==before


@pytest.mark.parametrize('contender',['direct-writer','other-callback','copied-context-writer'])
def test_binding_excludes_concurrent_producer_before_effect_and_keeps_original_owner(causal,monkeypatch,contender):
    from scripts import build_allocation as allocation
    from threading import Thread
    _,binding,intents,_=causal
    monkeypatch.setattr(allocation.config,'ROOT',binding.repo_root)
    _,second=build(binding,{'us':intents[0]},lambda checked:full_tree(checked,binding))
    observations=[]
    def deterministic(*a,**k):
        before=(binding.repo_root/p.ROOT_PATH).read_bytes()
        def competing():
            try:
                if contender in ('direct-writer','copied-context-writer'): append(causal,0)
                else: invoke(binding,second,FixtureGate())
            except p.SnapshotIntegrityError: observations.append('REFUSED')
            except BaseException as exc: observations.append('WRONG '+str(exc))
            else: observations.append('WRONG borrowed concurrent producer')
        if contender=='copied-context-writer':
            from contextvars import copy_context
            copied=copy_context()
            thread=Thread(target=lambda: copied.run(competing))
        else:
            thread=Thread(target=competing)
        thread.start();thread.join(10)
        assert not thread.is_alive()
        assert observations==['REFUSED'],observations
        assert (binding.repo_root/p.ROOT_PATH).read_bytes()==before
        return False
    monkeypatch.setattr(allocation,'main',deterministic)
    def produce(*a,**k):
        append(causal,0)
        return {'us':'owner'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    _,callback=build(binding,{'us':intents[0]},lambda checked:full_tree(checked,binding))
    gate=FixtureGate()
    result=invoke(binding,callback,gate)
    assert result.status=='candidate_verified' and len(result.original_writes)==1
    assert not gate.held and observations==['REFUSED']


def test_callback_admission_sees_prior_original_from_another_context(causal,monkeypatch):
    from scripts import build_allocation as allocation
    from threading import Thread
    _,binding,intents,root=causal
    monkeypatch.setattr(allocation.config,'ROOT',binding.repo_root)
    monkeypatch.setattr(allocation,'main',lambda *a,**k: pytest.fail('foreign earlier original reached domain work'))
    _,callback=build(binding,{'us':intents[0]},lambda checked: pytest.fail('foreign earlier original finalized'))
    errors=[]
    def earlier():
        try: append(causal,0)
        except BaseException as exc: errors.append(exc)
    thread=Thread(target=earlier)
    thread.start();thread.join(10)
    assert not thread.is_alive() and not errors
    assert (root/'one'/'manifest.json').exists()
    assert not binding.attempts and not binding.prepared_original_results  # separate ContextVar view
    gate=FixtureGate()
    with pytest.raises(p.SnapshotIntegrityError,match='fresh original invocation'):
        invoke(binding,callback,gate)
    assert gate.held
