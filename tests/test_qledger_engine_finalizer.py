"""Offline OIP prepare-only/native callback composition, never daily execution."""
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import os
import time

import pytest

from tests.test_qledger_conversion_candidate import fixture,native_fixture,prepare_native,git  # noqa:F401
from tests.test_qledger_original_result import original  # noqa:F401
from tests.test_qledger_causal_originals import causal,append  # noqa:F401
from tests.test_qledger_engine_producer import FixtureGate,invoke
from scripts.ci import qledger_engine_publication as engine
from scripts.ci.qledger_host_gate import CodePin
from engine import qledger_store_protocol as p, qledger_store_sources as sources

pytestmark=pytest.mark.parametrize('fixture',[{'raw':b'{"claim_id":"x","status":"open"}\n','part_bytes':256}],indirect=True)
SOURCE=Path(__file__).resolve().parents[1]


def setup(causal,monkeypatch,finalize,gate=None):
    from scripts import build_allocation as allocation
    _,binding,intents,_=causal
    tip=binding.original_result_targets[intents[0]].accepted_tip_oid
    git(binding.repo_root,'symbolic-ref','HEAD','refs/heads/main')
    git(binding.repo_root,'update-ref','HEAD',tip)
    monkeypatch.setattr(allocation.config,'ROOT',binding.repo_root)
    monkeypatch.setattr(allocation,'main',lambda *a,**k:False)
    def produce(*a,**k):
        append(causal,0)
        return {'us':'test-owned original'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    gate=gate or FixtureGate()
    gate.owner_code=tuple(CodePin(SOURCE/name,sha256((SOURCE/name).read_bytes()).hexdigest()) for name in
        ('scripts/ci/options_signal_nightly.sh','scripts/ci/options_index_lock_identity.py'))
    gate.runtime_code=()
    context=SimpleNamespace(repo=binding.repo_root,original_deadline_monotonic_ns=time.monotonic_ns()+90_000_000_000)
    _,callback=engine.build_native_engine_producer(context,owner_binding=binding,regions=('us',),
        native_intents={'us':intents[0]},finalizer=finalize,call=object())
    return binding,callback,gate


def stage(binding):
    repo=binding.repo_root
    (repo/'site').mkdir(exist_ok=True)
    (repo/'data/engine.txt').write_bytes(b'complete broad engine data\n')
    (repo/'site/render.html').write_bytes(b'actual final normalized render\n')
    git(repo,'add','-A','data','site')
    (repo/'data/engine.txt').write_bytes(b'complete broad engine data\nunstaged suffix\n')
    (repo/'untracked-owner.txt').write_bytes(b'original untracked input\n')


def observed(binding):
    repo=binding.repo_root
    return (git(repo,'show-ref'),(repo/'.git/index').read_bytes(),
            (repo/'data/engine.txt').read_bytes(),(repo/'untracked-owner.txt').read_bytes())


def test_prepare_full_final_tree_keeps_original_index_and_anchor_locked_through_finish(causal,monkeypatch):
    state={};events=[]
    real_lock=sources.claims_lock
    def claims_lock(path,**kw):
        assert not (state['binding'].repo_root/'.git/index.lock').exists(), 'claims reacquisition under index lock'
        events.append('claims-first')
        return real_lock(path,**kw)
    monkeypatch.setattr(sources,'claims_lock',claims_lock)
    class Gate(FixtureGate):
        def assert_valid(self,**kw):
            super().assert_valid(**kw)
            if kw['phase']=='engine-final-candidate' and (kw['repo']/'.git/index.lock').exists():
                events.append('checked-with-index-lock')
                assert observed(state['binding'])==state['before']
    def finalize(checked):
        stage(binding);state['before']=observed(binding)
        prepared=checked.prepare_engine_tree('test-owned complete final engine')
        assert (binding.repo_root/'.git/index.lock').exists()
        late=__import__('subprocess').run(['git','add','data/engine.txt'],cwd=binding.repo_root,capture_output=True)
        assert late.returncode!=0
        state['checks_at_return']=events.count('checked-with-index-lock')
        return prepared
    binding,callback,gate=setup(causal,monkeypatch,finalize,Gate());state['binding']=binding
    result=invoke(binding,callback,gate)
    assert result.status=='candidate_verified' and not gate.held
    assert observed(binding)==state['before']
    assert not (binding.repo_root/'.git/index.lock').exists()
    assert events.count('checked-with-index-lock')>state['checks_at_return']
    assert git(binding.repo_root,'show',result.publication.candidate_oid+':site/render.html')==b'actual final normalized render'
    assert git(binding.repo_root,'show',result.publication.candidate_oid+':data/engine.txt')==b'complete broad engine data'


@pytest.mark.parametrize('fault',['foreign-scope','narrow-scope','accepted-anchor'])
def test_prepare_refuses_scope_or_anchor_changes_without_install_or_parent_restore(causal,monkeypatch,fault):
    state={}
    def finalize(checked):
        stage(binding)
        repo=binding.repo_root
        if fault in ('foreign-scope','narrow-scope'):
            path=repo/('config/foreign.txt' if fault=='foreign-scope' else 'data/options_signal_episode/foreign.txt')
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text('do not publish')
            git(repo,'add',str(path))
        state['before']=observed(binding)
        prepared=checked.prepare_engine_tree('must not install')
        if fault=='accepted-anchor':
            git(repo,'update-ref','refs/remotes/origin/main',prepared.source_candidate_oid)
            state['before']=(git(repo,'show-ref'),*state['before'][1:])
        return prepared
    binding,callback,gate=setup(causal,monkeypatch,finalize)
    reason={'foreign-scope':'scope escape','narrow-scope':'narrow-path escape','accepted-anchor':'accepted ref changed'}[fault]
    with pytest.raises(p.SnapshotIntegrityError,match=reason):invoke(binding,callback,gate)
    assert gate.held and observed(binding)==state['before']
    assert not (binding.repo_root/'.git/index.lock').exists()


@pytest.mark.parametrize('fault',['different-inode','dirty','symlink','hardlink','fifo'])
def test_final_check_and_cleanup_preserve_foreign_or_dirty_index_lock(causal,monkeypatch,fault):
    state={}
    def finalize(checked):
        stage(binding);state['before']=observed(binding)
        prepared=checked.prepare_engine_tree('test-owned lock replacement')
        lock=binding.repo_root/'.git/index.lock'
        if fault=='dirty':lock.write_bytes(b'foreign dirty bytes')
        else:
            lock.rename(lock.with_name('original-index.lock'))
            if fault=='different-inode':lock.write_bytes(b'')
            elif fault=='symlink':lock.symlink_to('original-index.lock')
            elif fault=='hardlink':os.link(lock.with_name('original-index.lock'),lock)
            else:os.mkfifo(lock)
        state['inode']=lock.lstat().st_ino
        return prepared
    binding,callback,gate=setup(causal,monkeypatch,finalize)
    with pytest.raises(p.SnapshotIntegrityError):invoke(binding,callback,gate)
    lock=binding.repo_root/'.git/index.lock'
    assert gate.held and lock.lstat().st_ino==state['inode']
    assert observed(binding)==state['before']
    if fault=='dirty':assert lock.read_bytes()==b'foreign dirty bytes'


def test_lost_prepare_response_retains_original_lock_without_guessed_cleanup(causal,monkeypatch):
    real=engine._LiveFinalCandidate._run_prepare
    state={}
    def lost(final,program,args):
        real(final,program,args)
        raise OSError('test-owned response lost after object preparation')
    monkeypatch.setattr(engine._LiveFinalCandidate,'_run_prepare',lost)
    def finalize(checked):
        stage(binding);state['before']=observed(binding)
        return checked.prepare_engine_tree('test-owned lost response')
    binding,callback,gate=setup(causal,monkeypatch,finalize)
    with pytest.raises(OSError,match='response lost'):invoke(binding,callback,gate)
    assert gate.held and observed(binding)==state['before']
    lock=binding.repo_root/'.git/index.lock'
    assert lock.is_file() and lock.read_bytes()==b''
    assert callback.finalization._prepare_uncertain is True
    # Released claims lease is not a statement about runtime descendants or
    # bootstrap exclusion; the unknown index marker is intentionally retained.
    with sources.claims_lock(binding.repo_root/sources.LOCK_RELATIVE_PATH,mode='exclusive',timeout=0):pass


@pytest.mark.parametrize('fault',['existing-lock','expired-original','missing-code-pin'])
def test_unavailable_actual_preparation_inputs_refuse_without_install(causal,monkeypatch,fault):
    state={}
    def finalize(checked):
        stage(binding);state['before']=observed(binding)
        if fault=='existing-lock':(binding.repo_root/'.git/index.lock').write_bytes(b'foreign owner')
        if fault=='missing-code-pin':gate.owner_code=()
        return checked.prepare_engine_tree('must refuse absent original input')
    binding,callback,gate=setup(causal,monkeypatch,finalize)
    if fault=='expired-original':callback.original_deadline=time.monotonic_ns()-1
    with pytest.raises((OSError,p.SnapshotIntegrityError)):invoke(binding,callback,gate)
    assert gate.held and observed(binding)==state['before']
    lock=binding.repo_root/'.git/index.lock'
    if fault=='existing-lock':assert lock.read_bytes()==b'foreign owner'
    else:assert not lock.exists()


def test_preparation_executes_frozen_program_bytes_not_a_mutable_path(causal,monkeypatch):
    original_source=(SOURCE/'scripts/ci/options_signal_nightly.sh').read_bytes()
    script=causal[3].parent/'qualified-owner-program'/'options_signal_nightly.sh'
    script.parent.mkdir(mode=0o700);script.write_bytes(original_source)
    real=engine._LiveFinalCandidate._run_prepare
    def swap(final,program,args):
        script.write_bytes(b'echo WRONG_MUTABLE_PROGRAM; exit 91\n')
        try:return real(final,program,args)
        finally:script.write_bytes(original_source)
    monkeypatch.setattr(engine._LiveFinalCandidate,'_run_prepare',swap)
    def finalize(checked):
        stage(binding)
        return checked.prepare_engine_tree('actual frozen program bytes')
    binding,callback,gate=setup(causal,monkeypatch,finalize)
    gate.owner_code=(CodePin(script,sha256(original_source).hexdigest()),gate.owner_code[1])
    value=invoke(binding,callback,gate)
    assert value.status=='candidate_verified' and not gate.held
    assert not (binding.repo_root/'.git/index.lock').exists()
    assert script.read_bytes()==original_source


@pytest.mark.parametrize('fault',['source-construction','index-bytes'])
def test_partial_resource_acquisition_and_index_tamper_fail_closed(causal,monkeypatch,fault):
    state={}
    real_source=sources.LockedLocalSource
    def refused(*a,**k):raise p.SnapshotIntegrityError('FIXTURE','preheld source construction refused')
    def finalize(checked):
        stage(binding);state['before']=observed(binding)
        if fault=='source-construction':monkeypatch.setattr(sources,'LockedLocalSource',refused)
        prepared=checked.prepare_engine_tree('resource cleanup negative')
        (binding.repo_root/'.git/index').write_bytes(b'foreign authoritative index bytes')
        state['before']=(state['before'][0],b'foreign authoritative index bytes',*state['before'][2:])
        return prepared
    binding,callback,gate=setup(causal,monkeypatch,finalize)
    with pytest.raises(p.SnapshotIntegrityError):invoke(binding,callback,gate)
    assert gate.held and observed(binding)==state['before']
    assert not (binding.repo_root/'.git/index.lock').exists()
    monkeypatch.setattr(sources,'LockedLocalSource',real_source)
    with sources.claims_lock(binding.repo_root/sources.LOCK_RELATIVE_PATH,mode='exclusive',timeout=0):pass
