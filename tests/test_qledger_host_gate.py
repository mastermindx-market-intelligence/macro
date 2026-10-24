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
