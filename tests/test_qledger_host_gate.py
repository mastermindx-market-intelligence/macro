"""Temporary real Git/FD fixtures; these authorities are NOT runtime admission."""
from hashlib import sha256
import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ci.qledger_host_gate import CodePin, GateRefusal, HostGate
from tests.test_qledger_conversion_candidate import fixture, conversion_invocation, git, _invocation_producer  # noqa: F401


class FixtureEvidence:
    def __init__(self):
        self.calls = []
        self.refuse = None
        self.boolean = False

    def _assert(self, name, **context):
        self.calls.append(name)
        if self.refuse == name:
            raise GateRefusal('fixture actual evidence absent: ' + name)
        if self.boolean:
            return True

    def assert_bootstrap_exclusion(self, **context):
        return self._assert('bootstrap', **context)

    def assert_launcher_coverage(self, **context):
        return self._assert('launchers', **context)

    def assert_resources(self, **context):
        return self._assert('resources', **context)

    def assert_publication_readback(self, **context):
        return self._assert('publication', **context)

    def assert_process_version(self, **context):
        return self._assert('process-version', **context)

    def assert_descendants_settled(self, **context):
        return self._assert('descendants', **context)


@pytest.fixture
def host_gate(conversion_invocation):
    invocation, prepared = conversion_invocation
    root = invocation.owner.target.owner_root
    root.chmod(0o700)
    hook = root / 'fixture-owner-hook.py'
    hook.write_bytes(b'# synthetic installed hook; not a production issuer\n')
    runtime = invocation.owner.repo / 'unrelated'
    evidence = FixtureEvidence()
    args = dict(candidate_oid=prepared.candidate.candidate_oid,
        tree_oid=prepared.candidate.tree_oid, accepted_tip_oid=invocation.owner.target.accepted_tip_oid,
        owner_code=(CodePin(hook, sha256(hook.read_bytes()).hexdigest()),),
        runtime_code=(CodePin(runtime, sha256(runtime.read_bytes()).hexdigest()),),
        workflow_oids=(prepared.candidate.candidate_oid,),
        producers={('producer-original', 'producer-lane'): ('original-producer-budget', 'original-producer-retention')},
        runner_name='fixture-runner', repository='fixture/macro', agent_id=28, evidence=evidence)
    gate = HostGate(invocation, **args)
    def checkout(oid):
        git(invocation.owner.repo, 'checkout', '--detach', oid)
    return gate, args, checkout


def test_install_retains_full_readback_and_explicit_reader_and_hook(host_gate):
    gate, args, checkout = host_gate
    digest = gate.initial_checkout(checkout)
    assert digest == gate.owner.readback(gate.invocation.manifest_digest).snapshot.receipt.root_digest
    assert (gate.root / gate.READY).read_bytes() == gate._ready
    assert not (gate.root / gate.HOLD).exists()
    from engine import qledger_store as store
    def read():
        assert store.uses_native_claims(gate.repo / 'data/qledger/claims.jsonl')
        return 'bound-consumer'
    assert gate.invoke_reader(read) == 'bound-consumer'
    assert not store.uses_native_claims(gate.repo / 'data/qledger/claims.jsonl')
    gate.job_started({'RUNNER_NAME': gate.runner_name, 'GITHUB_REPOSITORY': gate.repository,
           'GITHUB_WORKSPACE': str(gate.repo), 'GITHUB_SHA': gate.candidate_oid})
    assert {'bootstrap', 'resources', 'launchers', 'publication', 'descendants'} <= set(gate.evidence.calls)


@pytest.mark.parametrize('missing', ['bootstrap', 'launchers', 'resources', 'process-version', 'publication', 'descendants'])
def test_live_missing_evidence_never_releases_installation(host_gate, missing):
    gate, args, checkout = host_gate
    gate.evidence.refuse = missing
    before = git(gate.repo, 'rev-parse', 'HEAD').decode()
    with pytest.raises(GateRefusal, match='actual evidence absent'):
        gate.initial_checkout(checkout)
    assert (gate.root / gate.HOLD).exists()
    assert not (gate.root / gate.READY).exists()
    if missing in ('bootstrap', 'launchers', 'resources', 'process-version'):
        assert git(gate.repo, 'rev-parse', 'HEAD').decode() == before
    # A fresh process/object does not infer restart permission from the same ID.
    restarted = HostGate(gate.invocation, **args)
    gate.evidence.refuse = None
    with pytest.raises(GateRefusal, match='original state'):
        restarted.initial_checkout(checkout)


def test_boolean_evidence_and_unleased_or_forked_gate_refuse(host_gate, monkeypatch):
    gate, _, checkout = host_gate
    with pytest.raises(GateRefusal, match='live same-process'):
        gate.assert_valid(**gate._conversion_context('reader'))
    gate.evidence.boolean = True
    with pytest.raises(GateRefusal, match='not return an admission flag'):
        gate.initial_checkout(checkout)
    with monkeypatch.context() as patch:
        patch.setattr(os, 'getpid', lambda: gate._pid + 1)
        with pytest.raises(GateRefusal, match='same-process'):
            with gate.lease('entry'):
                pytest.fail('forked capability cannot enter')


def test_checkout_response_loss_is_sticky_same_original_not_retry(host_gate):
    gate, args, checkout = host_gate
    def lost(oid):
        checkout(oid)
        raise OSError('original checkout response lost')
    with pytest.raises(OSError, match='response lost'):
        gate.initial_checkout(lost)
    held = (gate.root / gate.HOLD).read_bytes()
    assert held == gate._held and not (gate.root / gate.READY).exists()
    restarted = HostGate(gate.invocation, **args)
    with pytest.raises(GateRefusal, match='original state'):
        restarted.initial_checkout(checkout)
    assert (gate.root / gate.HOLD).read_bytes() == held


def test_lost_confirm_ack_reinstates_hold_and_prevents_new_entry(host_gate, monkeypatch):
    gate, _, checkout = host_gate
    original = gate.confirm_install
    def lost(**context):
        original(**context)
        raise OSError('confirm response lost')
    monkeypatch.setattr(gate, 'confirm_install', lost)
    with pytest.raises(OSError, match='confirm response lost'):
        gate.initial_checkout(checkout)
    assert (gate.root / gate.READY).exists() and (gate.root / gate.HOLD).exists()
    with pytest.raises(GateRefusal, match='absent or held'):
        gate.invoke_reader(lambda: pytest.fail('held entry cannot call consumer'))


@pytest.mark.parametrize('wrong', ['workflow', 'workspace', 'runner', 'repository', 'runtime-code', 'hook-code', 'version'])
def test_actual_precheckout_and_process_version_refusals(host_gate, wrong):
    gate, _, checkout = host_gate
    gate.initial_checkout(checkout)
    env = {'RUNNER_NAME': gate.runner_name, 'GITHUB_REPOSITORY': gate.repository,
           'GITHUB_WORKSPACE': str(gate.repo), 'GITHUB_SHA': gate.candidate_oid}
    if wrong == 'workflow':
        env['GITHUB_SHA'] = '0' * 40
    elif wrong == 'workspace':
        env['GITHUB_WORKSPACE'] += '-other'
    elif wrong == 'runner':
        env['RUNNER_NAME'] = 'other-runner'
    elif wrong == 'repository':
        env['GITHUB_REPOSITORY'] = 'different/repository'
    elif wrong == 'runtime-code':
        gate.runtime_code[0].path.write_bytes(b'changed runtime\n')
    elif wrong == 'hook-code':
        gate.owner_code[0].path.write_bytes(b'changed owner hook\n')
    else:
        git(gate.repo, 'checkout', '--detach', gate.accepted_tip_oid)
    with pytest.raises(GateRefusal):
        gate.job_started(env)


def test_shared_process_lease_prevents_exclusive_install_across_processes(host_gate):
    gate, _, _ = host_gate
    with gate.lease('entry'):
        script = '''import fcntl,os,sys
fd=os.open(sys.argv[1],os.O_RDWR)
try:
 fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:
 sys.exit(0)
sys.exit(9)
'''
        result = subprocess.run([sys.executable, '-c', script, str(gate.root / gate.LOCK)], capture_output=True)
        assert result.returncode == 0, result.stderr
    # Releasing a cooperative lease does not claim that old uninstrumented FDs settled.
    assert gate.evidence.calls == []


@pytest.mark.parametrize('attack', ['lock-symlink', 'lock-hardlink', 'replaced-lock', 'hold-symlink', 'root-mode'])
def test_gate_inode_and_owner_path_fail_closed(host_gate, tmp_path, attack):
    gate, _, checkout = host_gate
    outsider = tmp_path / 'outside'
    outsider.write_bytes(b'unchanged outside\n')
    outsider.chmod(0o600)
    if attack == 'lock-symlink':
        (gate.root / gate.LOCK).symlink_to(outsider)
    elif attack == 'lock-hardlink':
        os.link(outsider, gate.root / gate.LOCK)
    elif attack == 'hold-symlink':
        (gate.root / gate.HOLD).symlink_to(outsider)
    elif attack == 'root-mode':
        gate.root.chmod(0o755)
    else:
        with gate.lease('entry'):
            (gate.root / gate.LOCK).unlink()
            (gate.root / gate.LOCK).write_bytes(b'new lock')
            (gate.root / gate.LOCK).chmod(0o600)
            with pytest.raises(GateRefusal, match='replaced'):
                gate._check()
        assert outsider.read_bytes() == b'unchanged outside\n'
        return
    with pytest.raises((GateRefusal, OSError)):
        gate.initial_checkout(checkout)
    assert outsider.read_bytes() == b'unchanged outside\n'


def test_descendant_failure_holds_after_reader_scope_exits(host_gate):
    gate, _, checkout = host_gate
    gate.initial_checkout(checkout)
    gate.evidence.refuse = 'descendants'
    with pytest.raises(GateRefusal, match='descendants'):
        gate.invoke_reader(lambda: 'callback completed but child settlement absent')
    assert (gate.root / gate.HOLD).exists()
    from engine import qledger_store as store
    assert not store.uses_native_claims(gate.repo / 'data/qledger/claims.jsonl')


def test_publication_can_advance_tracking_ref_only_after_frozen_candidate_validation(host_gate):
    gate, _, checkout = host_gate
    def publish_after_checkout(oid):
        checkout(oid)
        # Simulates the normal publisher updating its tracking ref. This fixture
        # has no remote and makes no hosted-publication acceptance claim.
        git(gate.repo, 'update-ref', gate.owner.target.accepted_ref, oid)
    gate.initial_checkout(publish_after_checkout)
    assert (gate.root / gate.READY).read_bytes() == gate._ready
    assert 'publication' in gate.evidence.calls


def test_raw_gate_confirm_cannot_skip_incumbent_data_and_site_verification(host_gate):
    gate, _, _ = host_gate
    with gate.lease('install'):
        with pytest.raises(GateRefusal, match='incumbent checkout'):
            gate.begin_install(**gate._conversion_context('initial-checkout'))
    assert not (gate.root / gate.READY).exists()


@pytest.mark.parametrize('replacement', ['lock', 'owner-root'])
def test_restart_cannot_copy_ready_receipt_to_different_barrier(host_gate, replacement):
    import shutil
    gate, args, checkout = host_gate
    gate.initial_checkout(checkout)
    if replacement == 'lock':
        # Allocate the new inode before dropping the old one, avoiding reuse.
        other = gate.root / 'new-lock'
        other.write_bytes(b'')
        other.chmod(0o600)
        os.replace(other, gate.root / gate.LOCK)
    else:
        moved = gate.root.with_name(gate.root.name + '-old')
        gate.root.rename(moved)
        shutil.copytree(moved, gate.root)
    restarted = HostGate(gate.invocation, **args)
    with pytest.raises(GateRefusal, match='absent or held'):
        restarted.invoke_reader(lambda: pytest.fail('copied receipt cannot admit a different barrier'))


@pytest.mark.parametrize('wrong_budget', [False, True])
def test_host_gate_producer_keeps_per_invocation_native_binding_and_original_budget(host_gate, tmp_path, wrong_budget):
    from engine import qledger_store as store
    gate, _, checkout = host_gate
    gate.initial_checkout(checkout)
    prepared = gate.owner.readback(gate.invocation.manifest_digest)
    # Existing accepted helper needs only the immutable candidate OID.
    from types import SimpleNamespace
    binding, intent, root, oid = _invocation_producer(gate.invocation,
        SimpleNamespace(candidate=SimpleNamespace(candidate_oid=prepared.candidate_oid)), tmp_path)
    def producer():
        assert store.uses_native_claims(binding.claims_path)
        with store._claims_mutation(binding.claims_path, native_intent=intent) as writer:
            writer.append_serialized_rows([b'{"host-gate":1}\n'])
        return 'retained-producer'
    kwargs = dict(budget_id='different-budget' if wrong_budget else 'original-producer-budget',
        retention_id='original-producer-retention', producer=producer)
    if wrong_budget:
        with pytest.raises(GateRefusal, match='original resource binding'):
            gate.invoke_producer(binding, **kwargs)
        assert not binding.attempts and not (root / 'write-one').exists()
    else:
        assert gate.invoke_producer(binding, **kwargs) == 'retained-producer'
        assert len(binding.attempts) == 1 and (root / 'write-one/manifest.json').exists()
    assert not store.uses_native_claims(binding.claims_path)


@pytest.mark.parametrize('failure', ['hold-fsync', 'ready-fsync', 'hold-unlink'])
def test_install_durability_failure_never_clears_original_hold(host_gate, monkeypatch, failure):
    gate, _, checkout = host_gate
    actual_sync, actual_unlink = os.fsync, os.unlink
    fired = []
    target = gate.HOLD if failure == 'hold-fsync' else gate.READY
    def refused_sync(fd):
        info = os.fstat(fd)
        try:
            expected = (gate.root / target).stat()
        except FileNotFoundError:
            expected = None
        if (failure != 'hold-unlink' and not fired and expected is not None
                and (info.st_dev, info.st_ino) == (expected.st_dev, expected.st_ino)):
            fired.append(failure)
            raise OSError('fixture durability acknowledgement lost')
        return actual_sync(fd)
    def refused_unlink(path, *args, **kwargs):
        if failure == 'hold-unlink' and path == gate.HOLD and not fired:
            fired.append(failure)
            raise OSError('fixture hold removal refused')
        return actual_unlink(path, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(os, 'fsync', refused_sync)
        patch.setattr(os, 'unlink', refused_unlink)
        with pytest.raises(OSError):
            gate.initial_checkout(checkout)
    assert fired == [failure]
    assert (gate.root / gate.HOLD).exists()
    with pytest.raises(GateRefusal, match='absent or held'):
        gate.invoke_reader(lambda: pytest.fail('durability failure cannot admit reader'))


def test_same_instance_concurrent_admission_cannot_erase_failing_owner_hold(host_gate, monkeypatch):
    """Force both old callers past the non-atomic _mode test, without sleeps."""
    from threading import Event, Thread, current_thread
    from scripts.ci import qledger_host_gate as module
    gate, _, checkout = host_gate
    gate.initial_checkout(checkout)
    owner_paused, competitor_boundary = Event(), Event()
    owner_inside, competitor_inside, owner_done = Event(), Event(), Event()
    results, touched, lock_fd, hold_at_release = {}, set(), [], []
    actual_directory, actual_close = module._directory, os.close
    def wait(event):
        assert event.wait(10), 'forced interleaving did not reach its boundary'
    def directory(path):
        name = current_thread().name
        if name not in touched and name in ('gate-owner', 'gate-competitor'):
            touched.add(name)
            if name == 'gate-owner':
                owner_paused.set()
                wait(competitor_boundary)
            else:
                results['competitor-passed-admission'] = True
                competitor_boundary.set()
                wait(owner_inside)
        return actual_directory(path)
    def close(fd):
        if current_thread().name == 'gate-owner' and lock_fd and fd == lock_fd[0]:
            hold_at_release.append((gate.root / gate.HOLD).exists())
        return actual_close(fd)
    def owner():
        try:
            with gate.lease('entry'):
                lock_fd.append(gate._lock_fd)
                owner_inside.set()
                if results.get('competitor-passed-admission'):
                    # Old code admits B, then A's normal cleanup erases B's
                    # live descriptors. B subsequently cannot hold its failure.
                    wait(competitor_inside)
                else:
                    assert gate._mode == 'entry' and gate._lock_fd == lock_fd[0]
                    raise OSError('admitted owner failure')
        except BaseException as exc:
            results['owner-error'] = exc
        finally:
            owner_done.set()
    def competitor():
        try:
            with gate.lease('entry'):
                competitor_inside.set()
                wait(owner_done)
                raise OSError('admitted competitor failure')
        except BaseException as exc:
            results['competitor-error'] = exc
            competitor_boundary.set()  # Repaired code rejects before directory I/O.
    with monkeypatch.context() as patch:
        patch.setattr(module, '_directory', directory)
        patch.setattr(os, 'close', close)
        a = Thread(target=owner, name='gate-owner', daemon=True)
        b = Thread(target=competitor, name='gate-competitor', daemon=True)
        a.start()
        wait(owner_paused)
        b.start()
        a.join(15)
        b.join(15)
        assert not a.is_alive() and not b.is_alive()
    assert isinstance(results.get('owner-error'), OSError), results
    assert isinstance(results.get('competitor-error'), GateRefusal), results
    assert not results.get('competitor-passed-admission'), results
    assert hold_at_release == [True]
    assert (gate.root / gate.HOLD).read_bytes() == gate._held
    with pytest.raises(GateRefusal, match='absent or held'):
        gate.invoke_reader(lambda: pytest.fail('failure must block a fresh entry'))


def test_same_instance_guard_remains_owned_until_descriptor_cleanup_finishes(host_gate, monkeypatch):
    from threading import Event, Thread, current_thread
    gate, _, _ = host_gate
    cleanup, resume, finished = Event(), Event(), Event()
    active_lock, errors = [], []
    actual_close = os.close
    def close(fd):
        if current_thread().name == 'gate-cleanup-owner' and active_lock and fd == active_lock[0]:
            # The old implementation has already cleared _mode/_lock_fd here.
            cleanup.set()
            assert resume.wait(10), 'cleanup continuation absent'
        return actual_close(fd)
    def owner():
        try:
            with gate.lease('entry'):
                active_lock.append(gate._lock_fd)
        except BaseException as exc:
            errors.append(exc)
        finally:
            finished.set()
    with monkeypatch.context() as patch:
        patch.setattr(os, 'close', close)
        thread = Thread(target=owner, name='gate-cleanup-owner', daemon=True)
        thread.start()
        try:
            assert cleanup.wait(10), 'owner did not reach descriptor cleanup'
            assert gate._mode is None
            with pytest.raises(GateRefusal, match='concurrent lease'):
                with gate.lease('entry'):
                    pytest.fail('cleared descriptor fields are not admission')
        finally:
            resume.set()
            thread.join(15)
        assert finished.is_set() and not thread.is_alive() and not errors
    # Normal completion releases the guard only after its own cleanup.
    with gate.lease('entry'):
        gate._check()
    assert not (gate.root / gate.HOLD).exists()

# Future native operations and all controller/resource assertions in this
# section belong only to temporary tests; none is a production issuer.
from tests.test_qledger_conversion_candidate import native_fixture,prepare_native  # noqa:F401
from tests.test_qledger_original_result import original  # noqa:F401
from tests.test_qledger_causal_originals import causal,append  # noqa:F401


def _native_cycle_case(causal,fixture,monkeypatch,tmp_path,*,future_producer=None,real_normalizer=False):
    import time
    from types import SimpleNamespace
    from engine import qledger_original_conversion as conversion
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    from scripts.ci.qledger_owner_invocation import load_conversion
    from scripts.ci.qledger_owner_evidence import build_evidence
    from tests.test_qledger_engine_finalizer import stage
    from scripts import build_allocation as allocation
    _,binding,intents,_=causal;repo,legacy,blob,_,limits=fixture
    tip=binding.original_result_targets[intents[0]].accepted_tip_oid
    git(repo,'update-ref','refs/remotes/fixture/legacy',legacy)
    root=tmp_path/'test-owned-controller';root.mkdir(mode=0o700)
    target=conversion.ConversionOwnerTarget(root,root/'initial','initial',legacy,'refs/remotes/fixture/legacy',blob,
        engine.candidate.CandidateCommitMetadata('Synthetic preparation','fixture@example.invalid',1700000000),
        'conversion-budget','conversion-retention')
    owner=conversion.OriginalConversionOwner(repo,intent=conversion.OriginalConversionIntent('operation:one','lane:one','convert:one'),target=target,limits=limits)
    prepared=owner.prepare();owner.retain(prepared);assert prepared.candidate.candidate_oid==tip
    invocation=load_conversion(repo,result_path=target.result_path,manifest_digest=prepared.manifest_digest)
    remote=tmp_path/'native-published.git';git(repo,'init','--bare','-q',str(remote));git(repo,'remote','add','origin',str(remote));git(repo,'push','-q','origin',tip+':refs/heads/main')
    origin=sha256(str(remote).encode()).hexdigest()
    context=SimpleNamespace(repo=repo,owner_root=root,result_path=target.result_path,manifest_digest=prepared.manifest_digest,
        original_deadline_monotonic_ns=time.monotonic_ns()+180_000_000_000,candidate_oid=tip,
        operation_id=owner.intent.operation_id,budget_id=target.budget_id,retention_id=target.retention_id)
    class ControllerFixtureEvidence(FixtureEvidence):
        def __init__(self, original_context=context):
            super().__init__()
            self.context=original_context
            self.real=build_evidence(original_context,origin_binding_sha256=origin)
        def assert_publication_readback(self,**ctx):
            context=self.context
            self._assert('publication',**ctx)
            if 'native_anchor' in ctx:
                fresh=SimpleNamespace(**{**vars(context),'original_deadline_monotonic_ns':ctx['native_anchor'].data_anchor_deadline})
                proof=build_evidence(fresh,origin_binding_sha256=origin)
            elif 'native_reader' in ctx:
                fresh=SimpleNamespace(**{**vars(context),'original_deadline_monotonic_ns':ctx['native_reader'].deadline})
                proof=build_evidence(fresh,origin_binding_sha256=origin)
            else:proof=self.real
            return proof.assert_publication_readback(**ctx,bootstrap_pid=os.getpid(),
                original_deadline_monotonic_ns=proof.context.original_deadline_monotonic_ns,
                conversion_result_path=context.result_path,conversion_manifest_digest=context.manifest_digest)
    evidence=ControllerFixtureEvidence()
    pins=[];source=Path(__file__).resolve().parents[1]
    for name in ('options_signal_nightly.sh','options_index_lock_identity.py'):
        path=root/name;path.write_bytes((source/'scripts/ci'/name).read_bytes());pins.append(CodePin(path,sha256(path.read_bytes()).hexdigest()))
    if real_normalizer:
        from lib import shared_shell
        for relative in ('scripts/ci/daily_engine_commit_outputs.sh','scripts/ci/push_retry.sh',
                'scripts/ci/strip_conflict_markers.sh','templates/shared_shell_bridge.js','templates/shared_shell.css'):
            path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes((source/relative).read_bytes());pins.append(CodePin(path,sha256(path.read_bytes()).hexdigest()))
        monkeypatch.setattr(shared_shell,'ROOT',root)
    from scripts.ci import options_index_lock_identity as index_owner
    monkeypatch.setattr(index_owner,'__file__',str(root/'options_index_lock_identity.py'))
    args=dict(candidate_oid=tip,tree_oid=prepared.candidate.tree_oid,accepted_tip_oid=legacy,owner_code=tuple(pins),
        runtime_code=(CodePin(repo/'unrelated',sha256(b'accepted\n').hexdigest()),),workflow_oids=(tip,),
        producers={(binding.operation_id,binding.lane_id):('producer-budget','producer-retention'),
                   ('reader-original','reader-lane'):('reader-budget','reader-retention')},
        runner_name='fixture-native',repository='fixture/macro',agent_id=28,evidence=evidence)
    if future_producer is not None:args['producers'][future_producer[0]]=future_producer[1]
    gate=HostGate(invocation,**args)
    # owner_bridge materializes its test-owned baseline before any original.
    # Restore only those known fixture members for the real initial checkout.
    from engine import qledger_store_protocol as protocol
    snapshot=binding.read_snapshot()
    for relative in (*snapshot._members,protocol.ROOT_PATH):
        path=repo/relative
        if path.is_file():path.unlink()
    (repo/'data/qledger/claims.jsonl').write_bytes(fixture[3])
    gate.initial_checkout(lambda oid:git(repo,'checkout','--detach',oid))
    # Engine preparation deliberately requires the original named main HEAD.
    git(repo,'symbolic-ref','HEAD','refs/heads/main');git(repo,'update-ref','HEAD',tip)
    monkeypatch.setattr(allocation.config,'ROOT',repo);monkeypatch.setattr(allocation,'main',lambda *a,**k:False)
    def produce(*a,**k):
        assert gate._mode=='install' and (root/gate.HOLD).is_file()
        append(causal,0);append(causal,1)
        return {'us':'test-owned two originals'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    state={}
    def finalize(checked):
        assert gate._mode=='install' and (root/gate.HOLD).is_file()
        stage(binding);state['index_before_freeze']=(repo/'.git/index').read_bytes()
        result=checked.prepare_engine_tree('test-owned complete native generation')
        state.update(checked=checked,prepared=result);return result
    monkeypatch.setattr(engine,'finalize_daily_engine_outputs',finalize)
    publication=publisher.NativePublicationFinalizer(origin_binding_sha256=origin,
        original_origin_inode=(remote.stat().st_dev,remote.stat().st_ino),original_attempt=1,original_max_attempts=20,original_alarm_seconds=420)
    def run():
        with gate.native_cycle(binding,budget_id='producer-budget',retention_id='producer-retention'):
            _,callback=engine.build_native_engine_producer(context,owner_binding=binding,regions=('us','ca'),
                native_intents={'us':intents[0],'ca':intents[1]},finalizer=publication,call=object())
            state['callback']=callback
            return invocation.invoke_producer(binding,gate=gate,installed_commit_oid=tip,budget_id='producer-budget',
                retention_id='producer-retention',producer=callback)
    state.update(gate=gate,args=args,context=context,binding=binding,remote=remote,publication=publication,run=run)
    return state


def test_native_ex_cycle_publishes_complete_generation_and_separate_reader(causal,fixture,monkeypatch,tmp_path):
    import time
    from engine import qledger_store as store,qledger_store_protocol as protocol
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path);gate=state['gate'];repo=gate.repo
    head=git(repo,'rev-parse','HEAD');refs=git(repo,'show-ref');old=(gate.root/gate.READY).read_bytes()
    result=state['run']()
    assert result.status=='publication_confirmed' and not (gate.root/gate.HOLD).exists()
    assert git(repo,'rev-parse','HEAD')==head and (repo/'.git/index').read_bytes()==state['index_before_freeze']
    value=__import__('json').loads((gate.root/gate.READY).read_bytes());record=value['native_generation']
    assert (gate.root/gate.READY).read_bytes()!=old and record['candidate']==result.publication.candidate_oid
    assert git(repo,'show-ref')==refs
    for relative,payload in (('data/engine.txt',b'complete broad engine data\n'),
            ('site/render.html',b'actual final normalized render\n'),('unrelated',b'accepted\n')):
        assert subprocess.check_output(['git','-C',str(repo),'show',record['candidate']+':'+relative])==payload
    # The incumbent freezes the whole authoritative staged tree. The helper's
    # deliberately later unstaged suffix is preserved, never silently absorbed.
    assert (repo/'data/engine.txt').read_bytes()==b'complete broad engine data\nunstaged suffix\n'
    assert (repo/'untracked-owner.txt').read_bytes()==b'original untracked input\n'
    assert not (gate.root/(gate.READY+'.lock')).exists() and gate._native_ready_fd is None
    checked=state['checked'];retained=checked.invocation.binding.read_original_write_result(checked.invocation.write)
    selection=(record['candidate'],record['tree'],record['source'],retained,record['publication'])
    def consumer():
        assert store.uses_native_claims(repo/'data/qledger/claims.jsonl')
        binding=store._read_claims_binding(repo/'data/qledger/claims.jsonl')
        with protocol.open_logical_bytes(binding.read_snapshot()) as raw:return raw.read()
    raw=gate.invoke_native_reader(selection,consumer,operation_id='reader-original',lane_id='reader-lane',
        budget_id='reader-budget',retention_id='reader-retention',original_deadline_monotonic_ns=time.monotonic_ns()+60_000_000_000)
    assert raw==fixture[3]+b'{"future":"0"}\n{"future":"1"}\n'
    assert not store.uses_native_claims(repo/'data/qledger/claims.jsonl')
    assert not (gate.root/gate.HOLD).exists()


def _selection(state):
    import json
    gate=state['gate'];record=json.loads((gate.root/gate.READY).read_bytes())['native_generation']
    checked=state['checked'];retained=checked.invocation.binding.read_original_write_result(checked.invocation.write)
    return (record['candidate'],record['tree'],record['source'],retained,record['publication'])


def _read_native(state,selection=None,consumer=lambda:None,**overrides):
    import time
    values=dict(operation_id='reader-original',lane_id='reader-lane',budget_id='reader-budget',
        retention_id='reader-retention',original_deadline_monotonic_ns=time.monotonic_ns()+60_000_000_000)
    values.update(overrides)
    return state['gate'].invoke_native_reader(selection or _selection(state),consumer,**values)


@pytest.mark.parametrize('fault',['resources','bootstrap','nested-entry','old-anchor'])
def test_native_cycle_refuses_before_producer(causal,fixture,monkeypatch,tmp_path,fault):
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path);gate=state['gate']
    before=(gate.repo/'data/qledger/claims.root.json').read_bytes()
    if fault in ('resources','bootstrap'):gate.evidence.refuse=fault
    if fault=='old-anchor':git(gate.repo,'update-ref','HEAD',gate.accepted_tip_oid)
    def enter():
        with gate.native_cycle(state['binding'],budget_id='producer-budget',retention_id='producer-retention'):
            pytest.fail('unqualified producer entered')
    with pytest.raises((GateRefusal,OSError)):
        if fault=='nested-entry':
            with gate.lease('entry'):enter()
        else:enter()
    assert not state['binding'].attempts and (gate.repo/'data/qledger/claims.root.json').read_bytes()==before
    assert (gate.root/gate.HOLD).exists()


@pytest.mark.parametrize('fault',['same-bytes-foreign-ready','foreign-lock','lost-ready-response','late-producer-failure','file-fsync'])
def test_native_confirmation_failure_retains_hold_and_foreign_state(causal,fixture,monkeypatch,tmp_path,fault):
    from scripts.ci import qledger_engine_publication as engine
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path);gate=state['gate']
    old=(gate.root/gate.READY).read_bytes();original=gate._replace_native_ready;foreign=None
    if fault=='file-fsync':
        sync=os.fsync;failed=[]
        def fsync(fd):
            if fd==gate._native_ready_fd and not failed:
                failed.append(fd);raise OSError('test-owned READY file fsync lost')
            return sync(fd)
        monkeypatch.setattr(os,'fsync',fsync)
    if fault=='late-producer-failure':
        monkeypatch.setattr(engine._LiveFinalCandidate,'finish',lambda *a:(_ for _ in ()).throw(OSError('test-owned late finish response lost')))
    else:
        def replace(payload):
            nonlocal foreign
            if fault=='same-bytes-foreign-ready':
                foreign=gate.root/'foreign-ready';foreign.write_bytes(old);foreign.chmod(0o600)
                os.replace(foreign,gate.root/gate.READY)
            if fault=='foreign-lock':
                foreign=gate.root/(gate.READY+'.lock');foreign.write_bytes(b'foreign-lock');foreign.chmod(0o600)
            value=original(payload)
            if fault=='lost-ready-response':raise OSError('test-owned READY response lost')
            return value
        monkeypatch.setattr(gate,'_replace_native_ready',replace)
    with pytest.raises((OSError,GateRefusal)):state['run']()
    assert (gate.root/gate.HOLD).exists()
    if fault in ('same-bytes-foreign-ready','foreign-lock','file-fsync'):assert (gate.root/gate.READY).read_bytes()==old
    if fault=='foreign-lock':assert foreign.read_bytes()==b'foreign-lock'
    if fault=='file-fsync':assert gate._native_ready_fd is not None and (gate.root/(gate.READY+'.lock')).exists()
    if fault in ('lost-ready-response','late-producer-failure'):
        assert gate._native_ready_fd is not None and (gate.root/gate.READY).read_bytes()!=old
    with pytest.raises(GateRefusal):gate.invoke_reader(lambda:pytest.fail('held generation admitted reader'))


@pytest.mark.parametrize('fault',['default-reader','expired','wrong-resources','missing-prefix','reordered-prefix','wrong-generation','caught-readback','unsupported-reader-carrier','conversion-context'])
def test_native_reader_refuses_stale_missing_or_uncertain_evidence(causal,fixture,monkeypatch,tmp_path,fault):
    import time
    from scripts.ci.qledger_owner_evidence import EvidenceUnavailable
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path);state['run']();gate=state['gate'];selection=_selection(state)
    if fault=='missing-prefix':(selection[3].predecessors[0].result_path/'manifest.json').unlink()
    if fault=='reordered-prefix':object.__setattr__(selection[3],'predecessors',(selection[3],))
    if fault=='wrong-generation':selection=(gate.candidate_oid,*selection[1:])
    if fault=='unsupported-reader-carrier':
        from scripts.ci.qledger_owner_evidence import OrdinaryPublicationEvidence
        monkeypatch.setattr(OrdinaryPublicationEvidence,'_origin',lambda self:b'https://test-owned.invalid/no-network.git')
        monkeypatch.setattr(OrdinaryPublicationEvidence,'_git',lambda *a,**k:pytest.fail('unsupported reader attempted Git transport'))
    if fault=='caught-readback':
        real=gate.evidence.assert_publication_readback
        def caught(**context):
            try:return real(**{**context,'native_reader':None})
            except EvidenceUnavailable:return None
        monkeypatch.setattr(gate.evidence,'assert_publication_readback',caught)
    with pytest.raises(Exception):
        if fault=='default-reader':gate.invoke_reader(lambda:pytest.fail('default reader borrowed native generation'))
        else:
            options={}
            if fault=='expired':options['original_deadline_monotonic_ns']=time.monotonic_ns()-1
            if fault=='wrong-resources':options['budget_id']='different-budget'
            if fault=='conversion-context':options.update(operation_id=gate.owner.intent.operation_id,lane_id=None,
                budget_id=gate.owner.target.budget_id,retention_id=gate.owner.target.retention_id)
            _read_native(state,selection,lambda:pytest.fail('unqualified read entered'),**options)
    if fault=='caught-readback':assert gate._native_reader_call.uncertain and gate._native_reader_call.failure is not None


def _fresh_native_reader(packet):
    """Executed only in a fresh test Python, with explicitly test-owned facts."""
    from types import SimpleNamespace
    from engine import qledger_original_result as result,qledger_store_protocol as protocol,qledger_store_native as native
    from scripts.ci.qledger_owner_invocation import load_conversion
    from scripts.ci.qledger_owner_evidence import build_evidence
    import time
    context=SimpleNamespace(**packet['context'])
    for name in ('repo','owner_root','result_path'):setattr(context,name,Path(getattr(context,name)))
    context.original_deadline_monotonic_ns=time.monotonic_ns()+60_000_000_000
    proof=build_evidence(context,origin_binding_sha256=packet['publication']['origin'])
    class TestOnlyEvidence(FixtureEvidence):
        def assert_publication_readback(self,**ctx):
            return proof.assert_publication_readback(**ctx,bootstrap_pid=os.getpid(),
                original_deadline_monotonic_ns=context.original_deadline_monotonic_ns,
                conversion_result_path=context.result_path,conversion_manifest_digest=context.manifest_digest)
    args=packet['args'];args['evidence']=TestOnlyEvidence()
    for key in ('owner_code','runtime_code'):args[key]=tuple(CodePin(Path(p),digest) for p,digest in args[key])
    args['producers']={(op,lane):(budget,retention) for op,lane,budget,retention in args['producers']}
    invocation=load_conversion(context.repo,result_path=context.result_path,manifest_digest=context.manifest_digest)
    gate=HostGate(invocation,**args);prefix=()
    for entry in packet['originals']:
        last=result.read_original_result(owner_root=Path(entry['owner_root']),result_path=Path(entry['result_path']),
            expected_result_id=entry['result_id'],expected_manifest_digest=entry['manifest_digest'],
            expected_claims_path=context.repo/'data/qledger/claims.jsonl',expected_intent=native.NativeClaimsIntent(**entry['intent']),
            limits=protocol.ProtocolLimits(**packet['limits']),predecessors=prefix)
        prefix=(*prefix,last)
    selection=(*packet['selection'],last,packet['publication'])
    def read():
        from engine import qledger_store as store
        current=store._read_claims_binding(context.repo/'data/qledger/claims.jsonl')
        with protocol.open_logical_bytes(current.read_snapshot()) as raw:return raw.read()
    from scripts.ci.qledger_runner_bootstrap import LoadedBootstrap
    loaded=LoadedBootstrap(gate,SimpleNamespace(reader=lambda ctx:read()),SimpleNamespace(callable=lambda value:value),
        None,context,{})
    payload=loaded.native_reader(selection,operation_id='reader-original',lane_id='reader-lane',
        budget_id='reader-budget',retention_id='reader-retention')
    assert payload.endswith(b'{"future":"1"}\n')


def test_native_generation_fresh_python_reader_and_second_producer_anchor_refusal(causal,fixture,monkeypatch,tmp_path):
    from dataclasses import asdict
    import json
    from engine import qledger_original_result as result
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path);state['run']();selection=_selection(state)
    gate=state['gate'];retained=selection[3]
    args={k:v for k,v in state['args'].items() if k!='evidence'}
    for key in ('owner_code','runtime_code'):args[key]=[(str(p.path),p.digest) for p in args[key]]
    args['producers']=[[*k,*v] for k,v in args['producers'].items()]
    packet=dict(context={k:str(v) if isinstance(v,Path) else v for k,v in vars(state['context']).items()},args=args,
        originals=[result._descriptor(r) for r in (*retained.predecessors,retained)],limits=asdict(retained.limits),
        selection=selection[:3],publication=selection[4])
    import inspect
    encoded=json.dumps(packet)
    # Standalone test-owned driver: isolated Python must not need pytest or
    # inherit the parent's user site just to load this reader fixture.
    program=('import json,sys,os\nfrom pathlib import Path\n'
        'sys.path.insert(0,sys.argv[1])\n'
        'from scripts.ci.qledger_host_gate import HostGate,CodePin,GateRefusal\n'
        +inspect.getsource(FixtureEvidence)+'\n'+inspect.getsource(_fresh_native_reader)
        +'\n_fresh_native_reader(json.loads(sys.stdin.read()))\n')
    child=subprocess.run([sys.executable,'-I','-c',program,str(Path(__file__).resolve().parents[1])],
        input=encoded,text=True,capture_output=True,timeout=90,cwd=Path(__file__).resolve().parents[1])
    assert child.returncode==0,child.stderr
    # An inherited controller object is a different fact from fresh loading.
    pid=os.fork()
    if pid==0:
        try:_read_native(state,selection)
        except GateRefusal:os._exit(0)
        except BaseException:os._exit(2)
        os._exit(1)
    _,status=os.waitpid(pid,0)
    assert os.waitstatus_to_exitcode(status)==0
    assert not (gate.root/gate.HOLD).exists()
    # This future binding still has the original code tip, not the newly
    # published data tip. Do not relax that check to imply repeatability.
    old=state['binding']
    fresh=result.OriginalResultClaimsBinding(old.claims_path,operation_id=old.operation_id,lane_id=old.lane_id,
        limits=old.limits,original_result_targets=dict(old.original_result_targets))
    with pytest.raises(GateRefusal,match='accepted data anchor'):
        with gate.native_cycle(fresh,budget_id='producer-budget',retention_id='producer-retention',current_generation=selection):
            pytest.fail('stale original accepted data tip admitted second producer')
    assert not fresh.attempts and (gate.root/gate.HOLD).exists()


def test_native_cycle_excludes_separate_gate_before_original(causal,fixture,monkeypatch,tmp_path):
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path);gate=state['gate']
    other=HostGate(gate.invocation,**state['args'])
    with pytest.raises(OSError,match='test-owned end'):
        with gate.native_cycle(state['binding'],budget_id='producer-budget',retention_id='producer-retention'):
            with pytest.raises(BlockingIOError):
                with other.lease('entry'):pytest.fail('shared entry admitted during EX')
            assert (gate.root/gate.HOLD).exists() and not state['binding'].attempts
            raise OSError('test-owned end without publication')
    assert (gate.root/gate.HOLD).exists()


@pytest.mark.parametrize('failure_phase', [None, 'anchor', 'build', 'callback'])
def test_native_bootstrap_routes_ex_and_refuses_network_gap_in_isolated_python(failure_phase):
    # Exercise the actual bootstrap-owned producer closure in its required
    # isolated interpreter. These are test-owned boundaries, not admission.
    program=r"""
import sys
sys.path.insert(0,sys.argv[1])
from contextlib import contextmanager
from types import SimpleNamespace
from scripts.ci.qledger_runner_bootstrap import LoadedBootstrap,BootstrapRefusal
from scripts.ci.qledger_engine_publisher import NativePublicationFinalizer
calls=[]
failure_phase=sys.argv[2]
failure=OSError('test-owned original boundary failure')
binding=SimpleNamespace(operation_id='test-op',lane_id='test-lane')
context=SimpleNamespace(original_deadline_monotonic_ns=123456789)
@contextmanager
def cycle(value,**ctx):
    assert value is binding
    assert ctx==dict(budget_id='test-budget',retention_id='test-retention',current_generation=None)
    calls.append('EX')
    try:yield
    finally:calls.append('release')
def anchor(**ctx):
    assert calls==['EX','invoke']
    assert ctx==dict(original_deadline_monotonic_ns=context.original_deadline_monotonic_ns)
    calls.append('anchor')
    if failure_phase=='anchor':raise failure
def callback():
    assert calls==['EX','invoke','anchor','build']
    calls.append('callback')
    if failure_phase=='callback':raise failure
    return 'test-owned result'
def build(actual_context,**inputs):
    assert actual_context is context and calls==['EX','invoke','anchor']
    assert inputs==dict(owner_binding=binding,regions=('us',),native_intents={},call=None,publication=finalizer)
    calls.append('build')
    if failure_phase=='build':raise failure
    return binding,callback
def invoke(value,**ctx):
    assert value is binding and calls==['EX']
    assert ctx['gate'] is gate and ctx['installed_commit_oid']=='a'*40
    assert ctx['budget_id']=='test-budget' and ctx['retention_id']=='test-retention'
    assert set(ctx)=={'gate','installed_commit_oid','budget_id','retention_id','producer'}
    calls.append('invoke')
    return ctx['producer']()
gate=SimpleNamespace(native_cycle=cycle,establish_native_anchor=anchor,candidate_oid='a'*40,
    invocation=SimpleNamespace(invoke_producer=invoke))
loaded=LoadedBootstrap(gate,SimpleNamespace(build_producer=build),SimpleNamespace(callable=lambda value:value),
    None,context,dict(producer_context=dict(operation_id='test-op',lane_id='test-lane',budget_id='test-budget',retention_id='test-retention')))
finalizer=NativePublicationFinalizer(origin_binding_sha256='b'*64,original_origin_inode=(1,2),original_attempt=1,original_max_attempts=20,original_alarm_seconds=420)
if failure_phase:
    try:loaded.native_producer(owner_binding=binding,regions=('us',),native_intents={},publication=finalizer)
    except OSError as exc:assert exc is failure
    else:raise AssertionError('original failure swallowed')
    ordered=['EX','invoke','anchor','build','callback']
    assert calls==ordered[:ordered.index(failure_phase)+1]+['release']
else:
    assert loaded.native_producer(owner_binding=binding,regions=('us',),native_intents={},publication=finalizer)=='test-owned result'
    assert calls==['EX','invoke','anchor','build','callback','release']
calls.clear()
finalizer.original['https_carrier']=object()
try:loaded.native_producer(owner_binding=binding,regions=('us',),native_intents={},publication=finalizer)
except BootstrapRefusal as exc:assert 'installed-reader join' in str(exc)
else:raise AssertionError('unsupported carrier admitted')
assert calls==[]
"""
    child=subprocess.run([sys.executable,'-I','-c',program,str(Path(__file__).resolve().parents[1]),failure_phase or ''],
        capture_output=True,text=True,timeout=30)
    assert child.returncode==0,child.stderr


@pytest.mark.parametrize('failure_phase',['finish','producer-complete'])
def test_caught_original_completion_failure_cannot_release_native_hold(causal,fixture,monkeypatch,tmp_path,failure_phase):
    from scripts.ci import qledger_engine_publication as engine
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path);gate=state['gate']
    failure=OSError('test-owned late original completion response lost');caught=[]
    if failure_phase=='finish':
        def finish(*args):raise failure
        monkeypatch.setattr(engine._LiveFinalCandidate,'finish',finish)
    else:
        original_assert=gate.assert_valid
        def actual_completion(**context):
            original_assert(**context)
            if context['phase']=='producer-complete':raise failure
        monkeypatch.setattr(gate,'assert_valid',actual_completion)
    original_invoke=gate.invocation.invoke_producer
    def wrapper(*args,**kwargs):
        try:return original_invoke(*args,**kwargs)
        except OSError as exc:
            caught.append(exc)
            assert (gate.root/gate.HOLD).exists()
            return None
    monkeypatch.setattr(gate.invocation,'invoke_producer',wrapper)
    with pytest.raises(GateRefusal,match='original native completion'):
        state['run']()
    assert caught==[failure] and (gate.root/gate.HOLD).exists()
    checked=state['checked']
    assert gate._native_checked is checked and checked.live.failure is failure and not checked.live.completed
    if failure_phase=='finish':
        assert checked.failure is failure and not checked._finish_completed and not checked._close_completed
        assert checked.publication_attempt.uncertain and checked.publication_attempt.control_fd is not None
        # Existing index ownership closes its FD on preserve=True, while the
        # original empty lock path/identity remains for same-owner recovery.
        from scripts.ci.options_index_lock_identity import check
        assert check(checked._index_lock.path,checked._index_lock.identity)==0
        assert gate._native_ready_fd is not None
    with pytest.raises(GateRefusal):gate.invoke_reader(lambda:pytest.fail('caught failure admitted reader'))


# These are future test-owned operations/roots only. The first operation is
# actually published locally; the second never adopts its creator outcomes.
def _second_native_case(causal,fixture,monkeypatch,tmp_path,*,real_normalizer=False):
    import time,json
    from dataclasses import replace
    from types import SimpleNamespace
    from engine import qledger_original_result as originals,qledger_store_native as native
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    from scripts import build_allocation as allocation
    from tests.test_qledger_engine_finalizer import stage
    real_finalize=engine.finalize_daily_engine_outputs
    operation,lane='operation:second','lane:second'
    state=_native_cycle_case(causal,fixture,monkeypatch,tmp_path,
        future_producer=((operation,lane),('second-budget','second-retention')),real_normalizer=real_normalizer)
    gate=state['gate'];repo=gate.repo
    risk=repo/'data/risk_radar/forward_log.jsonl'  # ci-trigger-closure: data — temporary test-owned ledger destination, not a repository data read
    risk.parent.mkdir(parents=True,exist_ok=True)
    opaque=b'{"test_owned":"forward-ledger"}\nopaque-original-tail\n\xff\n'
    risk.write_bytes(opaque)
    first_page=repo/'site/first-generation.html';first_page.parent.mkdir(exist_ok=True)
    first_page.write_bytes(b'<!doctype html><html><head></head><body>first accepted generation</body></html>')
    if real_normalizer:
        from tests.test_qledger_daily_normalizer import dirty
        def first_finalize(checked):
            dirty(repo);prepared=real_finalize(checked)
            state.update(checked=checked,prepared=prepared,index_before_freeze=(repo/'.git/index').read_bytes())
            return prepared
        monkeypatch.setattr(engine,'finalize_daily_engine_outputs',first_finalize)
    first=state['run']();selection=_selection(state)
    first_files={str(p.relative_to(causal[3])):p.read_bytes() for p in causal[3].rglob('*') if p.is_file()}
    old_binding=state['binding'];intents=tuple(native.NativeClaimsIntent(operation,lane,'gen2-'+s) for s in ('one','two'))
    template=next(iter(old_binding.original_result_targets.values()))
    targets={intent:replace(template,result_path=template.owner_root/('gen2-'+s),result_id='gen2-'+s,
        accepted_tip_oid=first.publication.candidate_oid,predecessor_intents=tuple(intents[:i]))
        for i,(intent,s) in enumerate(zip(intents,('one','two')))}
    binding=originals.OriginalResultClaimsBinding(old_binding.claims_path,operation_id=operation,lane_id=lane,
        limits=old_binding.limits,original_result_targets=targets)
    context=SimpleNamespace(**{**vars(state['context']),'original_deadline_monotonic_ns':time.monotonic_ns()+180_000_000_000})
    # Each trusted_bootstrap invocation owns a fresh gate and one-use evidence
    # provider. Keep the first original's provider intact; never reset its latch.
    from scripts.ci.qledger_owner_invocation import load_conversion
    evidence=type(state['args']['evidence'])(context)
    second_args=dict(state['args'],evidence=evidence)
    gate=HostGate(load_conversion(repo,result_path=context.result_path,
        manifest_digest=context.manifest_digest),**second_args)
    second_causal=(causal[0],binding,intents,causal[3]);second={}
    def produce(*args,**kwargs):
        assert gate.native_data_tip(binding,original_deadline_monotonic_ns=context.original_deadline_monotonic_ns)==first.publication.candidate_oid
        append(second_causal,0);append(second_causal,1)
        return {'us':'test-owned second original','ca':'test-owned causal successor'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    def finalize(checked):
        if real_normalizer:
            from tests.test_qledger_daily_normalizer import dirty
            dirty(repo)
            first_page.write_bytes(b'<<<<<<< test-owned\nnot an accepted page\n>>>>>>> test-owned\n')
            prepared=real_finalize(checked)
        else:
            stage(binding)
            prepared=checked.prepare_engine_tree('test-owned second complete generation')
        second.update(checked=checked,prepared=prepared,index_before_freeze=(repo/'.git/index').read_bytes())
        return prepared
    monkeypatch.setattr(engine,'finalize_daily_engine_outputs',finalize)
    publication=publisher.NativePublicationFinalizer(**state['publication'].original)
    def run():
        with gate.native_cycle(binding,budget_id='second-budget',retention_id='second-retention',current_generation=selection):
            def original():
                gate.establish_native_anchor(original_deadline_monotonic_ns=context.original_deadline_monotonic_ns)
                _,callback=engine.build_native_engine_producer(context,owner_binding=binding,regions=('us','ca'),
                    native_intents={'us':intents[0],'ca':intents[1]},finalizer=publication,call=object())
                second['callback']=callback
                return callback()
            return gate.invocation.invoke_producer(binding,gate=gate,installed_commit_oid=gate.candidate_oid,
                budget_id='second-budget',retention_id='second-retention',producer=original)
    second.update(gate=gate,binding=binding,context=context,run=run,publication=publication,args=second_args)
    return state,second,first,selection,first_files,opaque


def test_two_genuine_native_generations_preserve_code_originals_and_forward_ledger(causal,fixture,monkeypatch,tmp_path):
    import json,time,inspect
    from dataclasses import asdict
    from engine import qledger_original_result as originals,qledger_store_protocol as protocol
    state,second,first,selection,files,opaque=_second_native_case(causal,fixture,monkeypatch,tmp_path)
    gate=state['gate'];repo=gate.repo;code=git(repo,'rev-parse','HEAD')
    parent=first.publication.candidate_oid
    old_first=git(repo,'show',parent+':site/first-generation.html')
    value=second['run']()
    assert value.status=='publication_confirmed' and value.publication.accepted_tip_oid==parent
    assert git(repo,'rev-list','--parents','-n','1',value.publication.candidate_oid).decode()==value.publication.candidate_oid+' '+parent
    assert git(repo,'rev-parse','HEAD')==code and git(repo,'rev-parse','refs/remotes/origin/main').decode()==parent
    assert (repo/'.git/index').read_bytes()==second['index_before_freeze']
    for rel,payload in files.items():assert (causal[3]/rel).read_bytes()==payload
    for oid in (parent,value.publication.candidate_oid):
        assert subprocess.check_output(['git','-C',str(repo),'show',oid+':data/risk_radar/forward_log.jsonl'])==opaque  # ci-trigger-closure: data — test-owned Git fixture output, not a repository source read
        assert git(repo,'show',oid+':site/first-generation.html')==old_first
    assert (repo/'data/risk_radar/forward_log.jsonl').read_bytes()==opaque  # ci-trigger-closure: data — temporary fixture ledger
    selection2=_selection(second)
    with protocol.open_logical_bytes(selection2[3].write.plan.snapshot) as raw:
        assert raw.read()==fixture[3]+b'{"future":"0"}\n{"future":"1"}\n'*2
    args={k:v for k,v in second['args'].items() if k!='evidence'}
    for key in ('owner_code','runtime_code'):args[key]=[(str(p.path),p.digest) for p in args[key]]
    args['producers']=[[*k,*v] for k,v in args['producers'].items()]
    retained=selection2[3]
    packet=dict(context={k:str(v) if isinstance(v,Path) else v for k,v in vars(second['context']).items()},args=args,
        originals=[originals._descriptor(r) for r in (*retained.predecessors,retained)],limits=asdict(retained.limits),
        selection=selection2[:3],publication=selection2[4])
    program=('import json,sys,os\nfrom pathlib import Path\nsys.path.insert(0,sys.argv[1])\n'
        'from scripts.ci.qledger_host_gate import HostGate,CodePin,GateRefusal\n'+inspect.getsource(FixtureEvidence)+'\n'
        +inspect.getsource(_fresh_native_reader)+'\n_fresh_native_reader(json.loads(sys.stdin.read()))\n')
    child=subprocess.run([sys.executable,'-I','-c',program,str(Path(__file__).resolve().parents[1])],
        input=json.dumps(packet),text=True,capture_output=True,timeout=90)
    assert child.returncode==0,child.stderr
    assert not (gate.root/gate.HOLD).exists() and gate._native_anchor_handles is None
    with pytest.raises(GateRefusal):_read_native(state,selection)
    assert (gate.root/gate.HOLD).exists()  # Old and new generations cannot mix.


@pytest.mark.parametrize('layout', ['packed', 'commondir', 'symbolic', 'alias', 'gitfile'])
def test_second_generation_tracking_cas_refuses_noncanonical_layout_before_lock(host_gate, monkeypatch, tmp_path, layout):
    """Isolate the ref namespace; mocked authorities grant no runtime admission."""
    gate, _, _ = host_gate
    repo=gate.repo; control=repo/'.git'
    git(repo,'symbolic-ref','HEAD','refs/heads/main')
    git(repo,'update-ref','refs/heads/main',gate.candidate_oid)
    origin=control/'refs/remotes/origin';origin.mkdir(parents=True,exist_ok=True)
    before=(gate.candidate_oid+'\n').encode();(origin/'main').write_bytes(before)
    monkeypatch.setattr(gate,'_anchor_check',lambda live:None)
    monkeypatch.setattr(gate,'_anchor_context',lambda live:{})
    monkeypatch.setattr(gate,'_assert',lambda *a,**k:None)
    if layout=='packed':(control/'packed-refs').write_text('# packed-refs\n')
    elif layout=='commondir':(control/'commondir').write_text('../foreign\n')
    elif layout=='symbolic':(origin/'main').write_text('ref: refs/heads/main\n')
    elif layout=='alias':
        (origin/'main').unlink();(origin/'main').symlink_to(control/'refs/heads/main')
    else:
        moved=repo/'.retained-test-git';control.rename(moved)
        control.write_text('gitdir: '+str(moved)+'\n');origin=moved/'refs/remotes/origin'
    original=(origin/'main').read_bytes()
    with pytest.raises((GateRefusal,OSError)):
        gate._tracking_data_cas(object(),{'accepted_tip':gate.candidate_oid,'candidate':'a'*40})
    assert (origin/'main').read_bytes()==original and not (origin/'main.lock').exists()
    assert gate._native_anchor_handles is None


def test_second_generation_tracking_cas_lost_durability_keeps_original_handles(host_gate,monkeypatch):
    """A matching ref after an uncertain original CAS never becomes success."""
    from scripts.ci import qledger_host_gate as module
    gate,_,_=host_gate;repo=gate.repo
    git(repo,'symbolic-ref','HEAD','refs/heads/main')
    git(repo,'update-ref','refs/heads/main',gate.candidate_oid)
    origin=repo/'.git/refs/remotes/origin';origin.mkdir(parents=True,exist_ok=True)
    (origin/'main').write_text(gate.candidate_oid+'\n')
    monkeypatch.setattr(gate,'_anchor_check',lambda live:None)
    monkeypatch.setattr(gate,'_anchor_context',lambda live:{})
    readbacks=[];monkeypatch.setattr(gate,'_assert',lambda *a,**k:readbacks.append(a))
    original_fsync=module.os.fsync
    def lose_after_replace(fd):
        if gate._native_anchor_handles and gate._native_anchor_handles['replaced']:
            raise OSError('test-owned lost directory durability response')
        return original_fsync(fd)
    monkeypatch.setattr(module.os,'fsync',lose_after_replace)
    with pytest.raises(OSError,match='lost directory durability'):
        gate._tracking_data_cas(object(),{'accepted_tip':gate.candidate_oid,'candidate':'b'*40})
    assert (origin/'main').read_text()=='b'*40+'\n'
    assert gate._native_anchor_handles['entered'] and gate._native_anchor_handles['replaced']
    assert gate._native_anchor_handles['fds'] and not readbacks
    assert all(os.fstat(fd) for fd in gate._native_anchor_handles['fds'])
