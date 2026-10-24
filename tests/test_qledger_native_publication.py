"""Actual local bare-origin effects; every authority/budget is test-owned."""
from hashlib import sha256
from pathlib import Path
import os
import pickle

import pytest

from tests.test_qledger_conversion_candidate import fixture,native_fixture,prepare_native,git  # noqa:F401
from tests.test_qledger_original_result import original  # noqa:F401
from tests.test_qledger_causal_originals import causal  # noqa:F401
from tests.test_qledger_engine_finalizer import setup,stage
from tests.test_qledger_engine_producer import FixtureGate,invoke
from engine import qledger_store as store,qledger_store_protocol as p

pytestmark=pytest.mark.parametrize('fixture',[{'raw':b'{"claim_id":"x","status":"open"}\n','part_bytes':256}],indirect=True)


class Authority:
    """Fixture-only assertions; never an installed authority or receipt."""
    def __init__(self,origin):self.inode=(origin.stat().st_dev,origin.stat().st_ino);self.missing=False;self.boolean=False;self.calls=[]
    def assert_resources(self,**ctx):
        self.calls.append(ctx['phase'])
        assert ctx['original_attempt']==1 and ctx['original_max_attempts']==20 and ctx['original_alarm_seconds']==420
        assert ctx['original_origin_inode']==self.inode
        if self.missing:raise RuntimeError('test-owned original resource unavailable')
        if self.boolean:return True
    def assert_process_version(self,**ctx):assert ctx['git_executable']
    def assert_publication_readback(self,**ctx):assert ctx['git_pid']>0
    def assert_descendants_settled(self,**ctx):assert ctx['git_pid']>0


def prepare_case(causal,monkeypatch,tmp_path,body):
    binding,callback,gate=setup(causal,monkeypatch,body)
    repo=binding.repo_root;tip=next(iter(binding.original_result_targets.values())).accepted_tip_oid
    origin=tmp_path/'actual-original.git';git(repo,'init','--bare','-q',str(origin));git(repo,'remote','add','origin',str(origin));git(repo,'push','-q','origin',tip+':refs/heads/main')
    gate.evidence=Authority(origin)
    args=dict(origin_binding_sha256=sha256(str(origin).encode()).hexdigest(),original_origin_inode=gate.evidence.inode,
              original_attempt=1,original_max_attempts=20,original_alarm_seconds=420)
    return binding,callback,gate,origin,args


def test_real_native_fullcandidate_push_readback_and_reader_preserve_source(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine
    state={}
    def reader(generation):
        assert type(generation) is store.NativeGitClaimsBinding
        with p.open_logical_bytes(generation.read_snapshot()) as raw:
            assert raw.read().endswith(b'{"future":"0"}\n')
        with pytest.raises(p.SnapshotIntegrityError,match='read-only|read binding|READ_ONLY'):
            with generation.mutation(native_intent=causal[2][0]):pass
        return 'actual immutable reader'
    def final(checked):
        stage(binding);state['refs']=git(binding.repo_root,'show-ref');state['index']=(binding.repo_root/'.git/index').read_bytes()
        prepared=checked.prepare_engine_tree('test-owned full native publication')
        generation=engine.publish_native_engine(checked,prepared,reader=reader,**args)
        assert generation.candidate_oid==prepared.candidate_oid
        assert generation.reader_result=='actual immutable reader'
        with pytest.raises(TypeError):pickle.dumps(generation)
        pid=os.fork()
        if pid==0:
            try:generation.invoke_reader(reader)
            except p.SnapshotIntegrityError:os._exit(0)
            os._exit(4)
        assert os.waitpid(pid,0)[1]==0
        state['generation']=generation;state['prepared']=prepared
        return prepared
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    result=invoke(binding,callback,gate)
    prepared=state['prepared']
    assert result.status=='publication_confirmed' and not gate.held
    assert git(origin,'rev-parse','refs/heads/main').decode()==prepared.candidate_oid
    assert git(origin,'show',prepared.candidate_oid+':site/render.html')==b'actual final normalized render'
    assert git(origin,'show',prepared.candidate_oid+':data/engine.txt')==b'complete broad engine data'
    assert git(binding.repo_root,'show-ref')==state['refs'] and (binding.repo_root/'.git/index').read_bytes()==state['index']
    assert not (binding.repo_root/'.git/index.lock').exists()
    with pytest.raises(p.SnapshotIntegrityError):state['generation'].invoke_reader(reader)
    assert not store.uses_native_claims(binding.claims_path)


@pytest.mark.parametrize('fault',['origin','tree','resource','boolean'])
def test_native_publication_refuses_before_git_effect(causal,monkeypatch,tmp_path,fault):
    from dataclasses import replace
    from scripts.ci import qledger_engine_publication as engine
    state={}
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('refuse before original effect');state['root']=(binding.repo_root/p.ROOT_PATH).read_bytes()
        if fault=='origin':args['origin_binding_sha256']='0'*64
        if fault=='tree':prepared=replace(prepared,tree_oid='0'*40)
        if fault=='resource':gate.evidence.missing=True
        if fault=='boolean':gate.evidence.boolean=True
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    before=git(origin,'rev-parse','refs/heads/main')
    with pytest.raises((p.SnapshotIntegrityError,RuntimeError)):invoke(binding,callback,gate)
    assert gate.held and git(origin,'rev-parse','refs/heads/main')==before
    assert (binding.repo_root/p.ROOT_PATH).read_bytes()==state['root']


def test_lost_object_ingestion_response_retains_original_without_retry(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    real=publisher._OriginalPublicationAttempt.wait_output
    def lost(attempt,child):
        value=real(attempt,child)
        if child is attempt.push_process:raise RuntimeError('test-owned lost original ingestion response')
        return value
    monkeypatch.setattr(publisher._OriginalPublicationAttempt,'wait_output',lost)
    state={}
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('one actual original, lost response');state['prepared']=prepared
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    before_refs=git(binding.repo_root,'show-ref');before_origin=git(origin,'rev-parse','refs/heads/main')
    with pytest.raises(RuntimeError,match='lost original ingestion response'):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and attempt.effect_started and attempt.uncertain and not attempt.confirmed
    assert attempt.push_process.returncode==0
    assert git(origin,'rev-parse','refs/heads/main')==before_origin
    assert not attempt.origin_ref_installed
    assert (origin/'refs/heads/main.lock').is_file()
    assert git(binding.repo_root,'show-ref')==before_refs
    assert attempt.control.exists() and os.fstat(attempt.control_fd)
    assert (binding.repo_root/'.git/index.lock').exists()
    with pytest.raises(p.SnapshotIntegrityError):attempt.checked._check()


def test_mutable_origin_and_insteadof_aba_cannot_redirect_actual_effect(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    alternate=tmp_path/'foreign-original.git'
    real=publisher._OriginalPublicationAttempt.run_git
    state={}
    def aba(attempt,command,*,effect=False):
        if not effect:return real(attempt,command,effect=False)
        git(binding.repo_root,'config','url.'+str(alternate)+'.insteadOf',str(origin))
        assert git(binding.repo_root,'remote','get-url','origin')==str(alternate).encode()
        try:return real(attempt,command,effect=True)
        finally:git(binding.repo_root,'config','--remove-section','url.'+str(alternate))
    monkeypatch.setattr(publisher._OriginalPublicationAttempt,'run_git',aba)
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('actual FD origin, not mutable redirect');state['prepared']=prepared
        engine.publish_native_engine(checked,prepared,**args)
        return prepared
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    git(binding.repo_root,'init','--bare','-q',str(alternate))
    result=invoke(binding,callback,gate)
    assert result.status=='publication_confirmed' and not gate.held
    assert git(origin,'rev-parse','refs/heads/main').decode()==state['prepared'].candidate_oid
    assert not git(alternate,'for-each-ref')


@pytest.mark.parametrize('fault',['control-path','control-config','origin-path','origin-fd','tracking-ref','network'])
def test_path_descriptor_tracking_and_transport_refusal_preserves_custody(causal,monkeypatch,tmp_path,fault):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    state={};real=publisher._OriginalPublicationAttempt.run_git
    def replaced(attempt,command,*,effect=False):
        if not state.get('changed'):
            state['changed']=True;state['attempt']=attempt
            if fault in ('control-path','origin-path'):
                path=attempt.control if fault=='control-path' else origin
                displaced=path.with_name(path.name+'-retained-original');path.rename(displaced);path.mkdir()
                (path/'foreign-evidence').write_bytes(b'never cleanup')
                state['displaced']=displaced
            elif fault=='control-config':
                (attempt.control/'config').write_bytes(b'[core]\n hooksPath=/test-owned-foreign\n')
            elif fault=='origin-fd':
                replacement=tmp_path/'replacement';replacement.mkdir()
                fd=os.open(replacement,os.O_RDONLY)
                try:os.dup2(fd,attempt.origin_fd)
                finally:os.close(fd)
        return real(attempt,command,effect=effect)
    if fault in ('control-path','control-config','origin-path','origin-fd'):
        monkeypatch.setattr(publisher._OriginalPublicationAttempt,'run_git',replaced)
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('refuse unqualified original destination')
        state['root']=(binding.repo_root/p.ROOT_PATH).read_bytes()
        if fault=='tracking-ref':
            git(binding.repo_root,'update-ref','refs/remotes/origin/main',prepared.source_candidate_oid)
            state['changed_ref']=git(binding.repo_root,'rev-parse','refs/remotes/origin/main')
        if fault=='network':
            url='https://example.invalid/test-owned-no-auth.git'
            git(binding.repo_root,'remote','set-url','origin',url)
            args['origin_binding_sha256']=sha256(url.encode()).hexdigest()
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    before=git(origin,'rev-parse','refs/heads/main')
    with pytest.raises(p.SnapshotIntegrityError):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and (attempt is None or not attempt.effect_started)
    assert (binding.repo_root/p.ROOT_PATH).read_bytes()==state['root']
    actual=state['displaced'] if fault=='origin-path' else origin
    assert git(actual,'rev-parse','refs/heads/main')==before
    if fault=='tracking-ref':assert git(binding.repo_root,'rev-parse','refs/remotes/origin/main')==state['changed_ref']
    if fault in ('control-path','origin-path'):
        path=attempt.control if fault=='control-path' else origin
        assert (path/'foreign-evidence').read_bytes()==b'never cleanup'
    if fault=='control-path':
        assert state['displaced'].is_dir() and attempt.uncertain
        assert (binding.repo_root/'.git/index.lock').exists()



def test_caught_reader_failure_cannot_confirm_original_publication(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine
    state={}
    def reader(binding):
        raise RuntimeError('test-owned lost reader response')
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('readback cannot settle a lost reader');state['prepared']=prepared
        try:engine.publish_native_engine(checked,prepared,reader=reader,**args)
        except RuntimeError as exc:
            assert 'lost reader response' in str(exc)
        return prepared
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    with pytest.raises(p.SnapshotIntegrityError,match='closed or unresolved'):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and attempt.remote_confirmed and attempt.uncertain and not attempt.confirmed
    assert git(origin,'rev-parse','refs/heads/main').decode()==state['prepared'].candidate_oid
    assert attempt.control.exists() and (binding.repo_root/'.git/index.lock').exists()


def test_two_originals_publish_last_native_root_and_complete_nonql_tree(causal,monkeypatch,tmp_path):
    import time
    from types import SimpleNamespace
    from scripts import build_allocation as allocation
    from scripts.ci import qledger_engine_publication as engine
    from tests.test_qledger_causal_originals import append
    state={}
    def reader(generation):
        with p.open_logical_bytes(generation.read_snapshot()) as raw:
            value=raw.read()
        assert value.endswith(b'{"future":"0"}\n{"future":"1"}\n')
        return 'both exact originals'
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('both exact original outcomes, full tree');state['prepared']=prepared
        generation=engine.publish_native_engine(checked,prepared,reader=reader,**args)
        assert generation.reader_result=='both exact originals'
        return prepared
    binding,_,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    def produce(*a,**kw):
        append(causal,0);append(causal,1)
        return {'us':'test-owned first','china':'test-owned second'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    _,callback=engine.build_native_engine_producer(SimpleNamespace(repo=binding.repo_root,
        original_deadline_monotonic_ns=time.monotonic_ns()+90_000_000_000),owner_binding=binding,
        regions=('us','china'),native_intents=dict(zip(('us','china'),causal[2])),finalizer=final,call=object())
    before=git(binding.repo_root,'show-ref')
    result=invoke(binding,callback,gate)
    assert result.status=='publication_confirmed' and len(result.original_writes)==2 and not gate.held
    assert git(origin,'rev-parse','refs/heads/main').decode()==state['prepared'].candidate_oid
    assert git(origin,'show',state['prepared'].candidate_oid+':data/engine.txt')==b'complete broad engine data'
    assert git(binding.repo_root,'show-ref')==before
    assert all(binding.original_result_targets[intent].result_path.joinpath('manifest.json').is_file()
               for intent in causal[2][:2])
    assert not binding.original_result_targets[causal[2][2]].result_path.exists()


@pytest.mark.parametrize('redirect',['commondir','nested-git'])
def test_origin_metadata_cannot_redirect_actual_ref_cas_or_readback(causal,monkeypatch,tmp_path,redirect):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    real=publisher._OriginalPublicationAttempt.run_git
    state={}
    def changed(attempt,command,*,effect=False):
        if effect:
            if redirect=='commondir':(origin/'commondir').write_text(str(foreign)+'\n')
            else:(origin/'.git').symlink_to(foreign,target_is_directory=True)
        try:return real(attempt,command,effect=effect)
        finally:
            if not effect and attempt.effect_started:
                (origin/('commondir' if redirect=='commondir' else '.git')).unlink(missing_ok=True)
    monkeypatch.setattr(publisher._OriginalPublicationAttempt,'run_git',changed)
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('actual original repository, never metadata redirect');state['prepared']=prepared
        engine.publish_native_engine(checked,prepared,**args)
        return prepared
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    foreign=tmp_path/'foreign.git';git(binding.repo_root,'clone','--bare','-q',str(origin),str(foreign))
    before=git(origin,'rev-parse','refs/heads/main')
    result=invoke(binding,callback,gate)
    assert result.status=='publication_confirmed' and not gate.held
    assert git(origin,'rev-parse','refs/heads/main').decode()==state['prepared'].candidate_oid
    assert git(foreign,'rev-parse','refs/heads/main')==before


def test_local_ref_cas_refuses_to_bypass_receive_hook_policy(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('hooked local origin requires admitted transport')
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    hook=origin/'hooks/pre-receive';hook.write_text('#!/bin/sh\nexit 0\n');hook.chmod(0o700)
    before=git(origin,'rev-parse','refs/heads/main')
    with pytest.raises(p.SnapshotIntegrityError,match='original Git completion unproven'):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and attempt.uncertain and not attempt.confirmed
    assert b'receive-hook policy requires admitted transport' in attempt.last_response[1]
    assert git(origin,'rev-parse','refs/heads/main')==before
    assert (binding.repo_root/'.git/index.lock').exists()



def test_lost_actual_ref_commit_response_retains_original_without_retry(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    real=publisher._OriginalPublicationAttempt.commit_original_ref
    def lost(attempt):
        real(attempt)
        raise RuntimeError('test-owned lost original ref commit response')
    monkeypatch.setattr(publisher._OriginalPublicationAttempt,'commit_original_ref',lost)
    state={}
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('one original ref effect, lost response');state['prepared']=prepared
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    mode=(origin/'refs/heads/main').stat().st_mode
    with pytest.raises(RuntimeError,match='lost original ref commit response'):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and attempt.origin_ref_installed and attempt.uncertain and not attempt.confirmed
    assert git(origin,'rev-parse','refs/heads/main').decode()==state['prepared'].candidate_oid
    assert (origin/'refs/heads/main').stat().st_mode==mode
    assert attempt.control.exists() and os.fstat(attempt.origin_lock_fd)
    assert (binding.repo_root/'.git/index.lock').exists()


@pytest.mark.parametrize('fault',['foreign-lock','packed-ref','symbolic-ref'])
def test_local_ref_transaction_refuses_unsupported_or_foreign_state(causal,monkeypatch,tmp_path,fault):
    from scripts.ci import qledger_engine_publication as engine
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('never replace foreign or unsupported ref state')
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    before=git(origin,'rev-parse','refs/heads/main')
    if fault=='foreign-lock':(origin/'refs/heads/main.lock').write_bytes(b'test-owned foreign lock')
    if fault=='packed-ref':git(origin,'pack-refs','--all','--prune')
    if fault=='symbolic-ref':
        git(origin,'update-ref','refs/heads/other',before.decode())
        git(origin,'symbolic-ref','refs/heads/main','refs/heads/other')
    with pytest.raises((p.SnapshotIntegrityError,FileExistsError)):invoke(binding,callback,gate)
    assert gate.held and git(origin,'rev-parse','refs/heads/main')==before
    if fault=='foreign-lock':assert (origin/'refs/heads/main.lock').read_bytes()==b'test-owned foreign lock'
    if fault=='packed-ref':assert not (origin/'refs/heads/main').exists()
    if fault=='symbolic-ref':assert git(origin,'symbolic-ref','refs/heads/main')==b'refs/heads/other'


@pytest.mark.parametrize('when',['before-ingestion','during-ingestion'])
def test_transient_destination_alternate_cannot_grant_primary_custody(causal,monkeypatch,tmp_path,when):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    real=publisher._OriginalPublicationAttempt.run_git;join=publisher.shlex.join;state={}
    def borrow(args):
        args=list(args)
        if when=='during-ingestion' and '-c' in args and 'upload-pack' in args[args.index('-c')+1]:
            i=args.index('-c')+1
            args[i]='from pathlib import Path;Path('+repr(str(origin/'objects/info/alternates'))+').write_text('+repr(state['source']+'\n')+');'+args[i]
        return join(args)
    monkeypatch.setattr(publisher.shlex,'join',borrow)
    def transient(attempt,command,*,effect=False):
        if effect:
            state['source']=str(attempt.objects_path)
            if when=='before-ingestion':(origin/'objects/info/alternates').write_text(state['source']+'\n')
        try:return real(attempt,command,effect=effect)
        finally:
            if effect:(origin/'objects/info/alternates').unlink(missing_ok=True)
    monkeypatch.setattr(publisher._OriginalPublicationAttempt,'run_git',transient)
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('primary origin custody cannot borrow alternates')
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    before=git(origin,'rev-parse','refs/heads/main')
    with pytest.raises(p.SnapshotIntegrityError):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and attempt.uncertain and not attempt.origin_ref_installed and not attempt.confirmed
    assert git(origin,'rev-parse','refs/heads/main')==before
    assert (origin/'refs/heads/main.lock').exists() and (binding.repo_root/'.git/index.lock').exists()
    if when=='during-ingestion':
        assert attempt.push_process.returncode==0 and attempt.verification_process is not None
        assert attempt.verification_process.returncode!=0


def test_primary_custody_accepts_real_destination_pack_without_alternate(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine
    state={}
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('primary packed objects, exact candidate');state['prepared']=prepared
        engine.publish_native_engine(checked,prepared,**args)
        return prepared
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    git(origin,'config','fetch.unpackLimit','1')
    result=invoke(binding,callback,gate)
    assert result.status=='publication_confirmed' and not gate.held
    assert list((origin/'objects/pack').glob('*.pack'))
    assert git(origin,'rev-parse','refs/heads/main').decode()==state['prepared'].candidate_oid
    git(origin,'fsck','--connectivity-only','--no-reflogs',state['prepared'].candidate_oid)


def test_lost_primary_verification_response_never_commits_ref(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    real=publisher._OriginalPublicationAttempt.wait_output
    def lost(attempt,child):
        value=real(attempt,child)
        if child is attempt.verification_process:raise RuntimeError('test-owned lost primary verification response')
        return value
    monkeypatch.setattr(publisher._OriginalPublicationAttempt,'wait_output',lost)
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('verification response belongs to this original')
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    before=git(origin,'rev-parse','refs/heads/main')
    with pytest.raises(RuntimeError,match='lost primary verification response'):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and attempt.verification_process.returncode==0 and attempt.uncertain
    assert not attempt.origin_ref_installed and not attempt.confirmed
    assert git(origin,'rev-parse','refs/heads/main')==before
    assert (origin/'refs/heads/main.lock').exists() and (binding.repo_root/'.git/index.lock').exists()



def test_primary_verifier_rejects_wrong_physical_loose_object(fixture,tmp_path):
    import shutil,subprocess,sys,zlib
    from hashlib import sha1
    from scripts.ci.qledger_engine_publisher import _PRIMARY_CUSTODY
    # Fresh test-owned invalid file; never alter a protected Git object or its
    # permissions. A correct-looking pathname cannot substitute for byte proof.
    primary=tmp_path/'test-owned-primary';primary.mkdir()
    (primary/'info').mkdir();(primary/'pack').mkdir()
    wanted=sha1(b'blob 5\0right').hexdigest();(primary/wanted[:2]).mkdir()
    (primary/wanted[:2]/wanted[2:]).write_bytes(zlib.compress(b'blob 5\0wrong'))
    descriptor=os.open(primary,os.O_RDONLY|os.O_DIRECTORY)
    try:
        result=subprocess.run([sys.executable,'-I','-c',_PRIMARY_CUSTODY,str(descriptor),shutil.which('git'),
            str(tmp_path),'1','5','5'],input=(wanted+'\n').encode(),capture_output=True,pass_fds=(descriptor,))
    finally:os.close(descriptor)
    assert result.returncode!=0 and b'primary object does not match exact original inventory' in result.stderr





@pytest.mark.parametrize('alias',['loose','fanout','pack','index'])
def test_primary_verifier_refuses_external_physical_object_paths(fixture,tmp_path,alias):
    import shutil,subprocess,sys
    from scripts.ci.qledger_engine_publisher import _PRIMARY_CUSTODY
    external=tmp_path/'test-owned-external.git';git(tmp_path,'init','--bare','-q',str(external))
    raw=b'test-owned primary custody';oid=git(external,'hash-object','-w','--stdin',input=raw).decode()
    primary=tmp_path/'test-owned-primary';primary.mkdir();(primary/'info').mkdir();(primary/'pack').mkdir()
    if alias=='fanout':(primary/oid[:2]).symlink_to(external/'objects'/oid[:2],target_is_directory=True)
    elif alias=='loose':
        (primary/oid[:2]).mkdir();(primary/oid[:2]/oid[2:]).symlink_to(external/'objects'/oid[:2]/oid[2:])
    else:
        pack_hash=git(external,'pack-objects',str(tmp_path/'test-owned-pack'),input=(oid+'\n').encode()).decode()
        for suffix in ('idx','pack'):
            source=tmp_path/('test-owned-pack-'+pack_hash+'.'+suffix)
            target=primary/'pack'/('pack-'+pack_hash+'.'+suffix)
            if (alias=='pack' and suffix=='pack') or (alias=='index' and suffix=='idx'):target.symlink_to(source)
            else:os.link(source,target)
    descriptor=os.open(primary,os.O_RDONLY|os.O_DIRECTORY)
    try:
        result=subprocess.run([sys.executable,'-I','-c',_PRIMARY_CUSTODY,str(descriptor),shutil.which('git'),
            str(tmp_path),'1',str(len(raw)),str(len(raw))],input=(oid+'\n').encode(),capture_output=True,pass_fds=(descriptor,))
    finally:os.close(descriptor)
    assert result.returncode!=0 and b'primary-custody-ready' not in result.stdout
    assert any(path.is_symlink() for path in primary.rglob('*'))


def test_actual_publication_cannot_replace_missing_primary_object_with_external_link(causal,monkeypatch,tmp_path):
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    real=publisher._OriginalPublicationAttempt.run_git;join=publisher.shlex.join;state={}
    def borrow(args):
        args=list(args)
        if '-c' in args and 'upload-pack' in args[args.index('-c')+1]:
            i=args.index('-c')+1
            args[i]='from pathlib import Path;Path('+repr(str(origin/'objects/info/alternates'))+').write_text('+repr(state['source']+'\n')+');'+args[i]
        return join(args)
    monkeypatch.setattr(publisher.shlex,'join',borrow)
    def external_link(attempt,command,*,effect=False):
        if effect:state['source']=str(attempt.objects_path)
        value=real(attempt,command,effect=effect)
        if effect:
            (origin/'objects/info/alternates').unlink()
            oid=attempt.prepared.candidate_oid
            target=origin/'objects'/oid[:2]/oid[2:]
            assert not target.exists()  # Never alter a Git-protected object.
            target.parent.mkdir(exist_ok=True)
            target.symlink_to(attempt.objects_path/oid[:2]/oid[2:]);state['link']=target
        return value
    monkeypatch.setattr(publisher._OriginalPublicationAttempt,'run_git',external_link)
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('linked source bytes are not destination custody')
        return engine.publish_native_engine(checked,prepared,**args)
    binding,callback,gate,origin,args=prepare_case(causal,monkeypatch,tmp_path,final)
    before=git(origin,'rev-parse','refs/heads/main')
    with pytest.raises(p.SnapshotIntegrityError,match='primary destination unproven'):invoke(binding,callback,gate)
    attempt=callback.finalization.publication_attempt
    assert gate.held and attempt.uncertain and not attempt.origin_ref_installed and not attempt.confirmed
    assert state['link'].is_symlink() and git(origin,'rev-parse','refs/heads/main')==before
    assert (origin/'refs/heads/main.lock').exists() and (binding.repo_root/'.git/index.lock').exists()
