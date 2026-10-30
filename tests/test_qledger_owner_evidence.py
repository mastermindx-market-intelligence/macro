"""Local bare-Git publication through the existing factory/gate; no host admission."""
from hashlib import sha256
from pathlib import Path
import subprocess
import os

import pytest

from tests.test_qledger_runner_bootstrap import bootstrap, put  # noqa: F401
from tests.test_qledger_conversion_candidate import fixture, conversion_invocation  # noqa: F401

SOURCE=Path(__file__).resolve().parents[1]


def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE).strip()


@pytest.fixture
def publication(bootstrap):
    run,config,owner,repo=bootstrap
    remote=owner.parent/'published.git'
    subprocess.run(['git','init','--bare','--quiet',str(remote)],check=True,capture_output=True)
    git(repo,'remote','add','origin',str(remote))
    # This is the original identity captured before this fresh fixture push,
    # using the same convention as the incumbent normal-push observation.
    origin=sha256(git(repo,'remote','get-url','--push','origin')).hexdigest()
    name='scripts/ci/qledger_owner_evidence.py'
    config['bundle_files'][name]=put(owner/'bundle'/name,(SOURCE/name).read_bytes())
    entry=owner/'bundle/owner_entry.py'
    prefix=entry.read_bytes()
    driver=owner.parent/'driver.py'
    original_driver=driver.read_text()
    def configure(*, publish=False, mode='readback', tamper='', origin_pin=origin):
        extension=f'''
from scripts.ci.qledger_owner_evidence import build_evidence as production_evidence
class PublicationFixtureEvidence(FixtureEvidence):
    # All other evidence here is exclusively the accepted offline fixture.
    def __init__(self, context):
        super().__init__(context)
        self.real = production_evidence(context, origin_binding_sha256={origin_pin!r})
    def assert_publication_readback(self, **context):
        {tamper or 'pass'}
        return self.real.assert_publication_readback(**context)
'''
        if mode=='resources':
            extension+='''
    def assert_resources(self, **context):
        return self.real.assert_resources(**context)
'''
        extension+='''
def build_evidence(context):
    return PublicationFixtureEvidence(context)
'''
        if mode=='production':
            extension+=f'''
def build_evidence(context):
    return production_evidence(context, origin_binding_sha256={origin_pin!r})
'''
        config['bundle_files']['owner_entry.py']=put(entry,prefix+extension.encode())
        text=original_driver
        if publish:
            # Normal Git push is performed inside the fixture's already-held
            # install barrier, after preflight/checkout and before confirm. No
            # production shell budget is minted or claimed by these tests.
            helper='''
def fixture_checkout_and_publish(oid):
    subprocess.check_call(['git','-C',str(repo),'checkout','--quiet','--detach',oid])
    subprocess.check_call(['git','-C',str(repo),'push','--quiet','origin',oid+':refs/heads/main'])
'''
            text=text.replace('operational=False',helper+'\noperational=False')
            text=text.replace("lambda oid: subprocess.check_call(\n                ['git','-C',str(repo),'checkout','--quiet','--detach',oid])",'fixture_checkout_and_publish')
        # Mark install refusals as operational: every one must retain HOLD.
        text=text.replace('            loaded.gate.initial_checkout(', '            operational=True\n            loaded.gate.initial_checkout(')
        driver.write_text(text)
    return run,config,owner,repo,remote,configure


def test_normal_publication_readback_releases_only_test_owned_installation(publication):
    run,config,owner,repo,remote,configure=publication
    configure(publish=True)
    assert 'OFFLINE_FIXTURE_SUCCESS' in run('reader')
    assert git(remote,'rev-parse','refs/heads/main').decode()==config['gate']['candidate_oid']
    assert (owner/'qledger-installed.json').is_file()
    assert not (owner/'qledger-install.hold').exists()


def test_local_candidate_and_tracking_ref_do_not_prove_remote_publication(publication):
    run,config,owner,repo,_,configure=publication
    configure()
    # Local objects already contain the complete candidate. An invented local
    # tracking ref cannot make the actual remote contain it.
    git(repo,'update-ref','refs/remotes/fake/main',config['gate']['candidate_oid'])
    run('reader','normal publication ref readback is unavailable')
    assert not (owner/'qledger-installed.json').exists()


def test_wrong_remote_generation_stays_held_without_fetch_or_replay(publication):
    run,config,owner,repo,_,configure=publication
    old=config['gate']['accepted_tip_oid']
    git(repo,'push','--quiet','origin',old+':refs/heads/main')
    configure()
    run('reader','exact full candidate is not confirmed')
    assert (owner/'qledger-install.hold').is_file()


def test_changed_original_origin_is_not_recaptured(publication):
    run,_,_,repo,_,configure=publication
    configure()
    git(repo,'remote','set-url','origin',str(repo.parent/'different-origin.git'))
    run('reader','original normal-push origin changed')


@pytest.mark.parametrize('tamper', [
    "context['bootstrap_pid'] += 1",
    "context['conversion_manifest_digest'] = '0'*64",
    "context['budget_id'] = 'different-original-budget'",
    "context['gate'].tree_oid = '0'*40",
])
def test_readback_binds_original_process_result_budget_and_complete_tree(publication,tamper):
    run,_,_,_,_,configure=publication
    configure(publish=True,tamper=tamper)
    expected='complete publication tree differs' if 'tree_oid' in tamper else 'original publication invocation binding differs'
    run('reader',expected)


def test_no_original_origin_pin_is_an_explicit_refusal(publication):
    run,_,_,_,_,configure=publication
    configure(origin_pin=None)
    run('reader','original normal-push origin binding required')


def test_actual_resource_contract_cannot_be_replaced_by_manifest_labels(publication):
    run,_,_,_,_,configure=publication
    configure(mode='resources')
    run('reader','original ordinary push budget/process anchor and actual root retention/capacity policy unavailable')


def test_partial_production_factory_never_issues_runtime_admission(publication):
    run,_,owner,_,_,configure=publication
    configure(publish=True,mode='production')
    run('reader','held complete new-entry/launcher exclusion authority unavailable')
    assert not (owner/'qledger-installed.json').exists()


@pytest.mark.parametrize('tamper', [
    "self.real._pid += 1",
    "self.real.context = __import__('dataclasses').replace(self.real.context, original_deadline_monotonic_ns=1)",
])
def test_readback_does_not_reanchor_expired_or_different_process_inputs(publication,tamper):
    run,_,_,_,_,configure=publication
    configure(publish=True,tamper=tamper)
    run('reader','readback process changed or original endpoint is unavailable/expired')


@pytest.mark.parametrize('redirect', ['origin', 'insteadOf'])
def test_remote_query_cannot_follow_mutable_origin_aba(publication, redirect):
    run,config,owner,repo,remote,configure=publication
    alternate=owner.parent/'alternate.git'
    subprocess.run(['git','init','--bare','--quiet',str(alternate)],check=True,capture_output=True)
    git(repo,'push','--quiet',str(alternate),config['gate']['candidate_oid']+':refs/heads/main')
    # Interleave exactly at the actual Git read: original has no candidate,
    # alternate does. Restore configuration before the final identity check.
    change = (['remote','set-url','origin',str(alternate)] if redirect=='origin' else
              ['config','url.'+str(alternate)+'.insteadOf',str(remote)])
    restore = (['remote','set-url','origin',str(remote)] if redirect=='origin' else
               ['config','--unset-all','url.'+str(alternate)+'.insteadOf'])
    lines=[
        'read_git = self.real._git',
        'def interleave(args, *extra, **kwargs):',
        "    if args[0] != 'ls-remote': return read_git(args, *extra, **kwargs)",
        "    command = ['git', '-C', str(self.real.context.repo)]",
        f"    __import__('subprocess').check_call(command + {change!r})",
        '    try:',
        '        return read_git(args, *extra, **kwargs)',
        '    finally:',
        f"        __import__('subprocess').check_call(command + {restore!r})",
        'self.real._git = interleave',
    ]
    configure(tamper='\n        '.join(lines))
    run('reader','normal publication ref readback is unavailable')
    assert not (owner/'qledger-installed.json').exists()
    assert (owner/'qledger-install.hold').is_file()
    assert git(repo,'remote','get-url','origin')==str(remote).encode()
    assert git(alternate,'rev-parse','refs/heads/main').decode()==config['gate']['candidate_oid']
    assert git(remote,'for-each-ref','--format=%(objectname)','refs/heads/main')==b''

# Native fixtures are future, test-owned original operations. This provider
# branch test supplies the typed caller context explicitly; production caller
# registration remains separate while publisher bytes are under review.
from tests.test_qledger_conversion_candidate import native_fixture,prepare_native  # noqa:F401
from tests.test_qledger_original_result import original  # noqa:F401
from tests.test_qledger_causal_originals import causal,append  # noqa:F401
from tests.test_qledger_native_publication import https_origin  # noqa:F401


@pytest.mark.parametrize('fault',['positive','creator','lease','order','tree','root','lost-response','readback','manifest','missing-context','caught-lost-response','https-positive','caught-missing-context','caught-invalid-context','caught-provider-check','caught-legacy-route'])
def test_native_readback_evidence_requires_actual_live_original(causal,fixture,monkeypatch,tmp_path,request,fault):
    from dataclasses import replace
    from types import SimpleNamespace
    import os,time
    from engine import qledger_original_conversion as conversion
    from engine import qledger_store_protocol as protocol
    from scripts.ci import qledger_engine_publication as engine,qledger_engine_publisher as publisher
    from scripts.ci.qledger_owner_evidence import build_evidence,EvidenceUnavailable
    from scripts.ci.qledger_owner_invocation import load_conversion
    from tests.test_qledger_native_publication import prepare_case,Authority
    from tests.test_qledger_engine_finalizer import stage
    from scripts import build_allocation as allocation
    state={}
    def final(checked):
        stage(binding);prepared=checked.prepare_engine_tree('test-owned real native evidence');state.update(checked=checked,prepared=prepared)
        engine.publish_native_engine(checked,prepared,**args)
        return prepared
    binding,_,gate,remote,args=prepare_case(causal,monkeypatch,tmp_path,final)
    repo,legacy_tip,blob,_,limits=fixture;tip=next(iter(binding.original_result_targets.values())).accepted_tip_oid
    if fault=='https-positive':
        remote,url,cert,header,network=request.getfixturevalue('https_origin')
        subprocess.check_call(['git','-C',str(repo),'push','--quiet',str(remote),tip+':refs/heads/main'])
        subprocess.check_call(['git','-C',str(repo),'remote','set-url','origin',url])
        subprocess.check_call(['git','-C',str(repo),'config','http.'+url.rsplit('/owner/',1)[0]+'/.extraheader','AUTHORIZATION: '+header])
        carrier=publisher.CheckoutHTTPSCarrier(repo,url,tls_ca_file=cert)
        args.update(origin_binding_sha256=sha256(url.encode()).hexdigest(),original_origin_inode=None,https_carrier=carrier)
    # Retain the same accepted conversion using its actual deterministic inputs.
    # A separate named original ref preserves the native producer's accepted ref.
    subprocess.check_call(['git','-C',str(repo),'update-ref','refs/remotes/fixture/legacy',legacy_tip])
    owner_root=tmp_path/'retained-initial';owner_root.mkdir(mode=0o700)
    target=conversion.ConversionOwnerTarget(owner_root,owner_root/'original','original',legacy_tip,
        'refs/remotes/fixture/legacy',blob,
        engine.candidate.CandidateCommitMetadata('Synthetic preparation','fixture@example.invalid',1700000000),
        'test-conversion-budget','test-conversion-retention')
    owner=conversion.OriginalConversionOwner(repo,intent=conversion.OriginalConversionIntent('operation:one','lane:one','convert:one'),target=target,limits=limits)
    prepared_conversion=owner.prepare();owner.retain(prepared_conversion)
    assert prepared_conversion.candidate.candidate_oid==tip
    loaded=load_conversion(repo,result_path=target.result_path,manifest_digest=prepared_conversion.manifest_digest)
    context=SimpleNamespace(repo=repo,owner_root=owner_root,result_path=target.result_path,
        manifest_digest=prepared_conversion.manifest_digest,original_deadline_monotonic_ns=time.monotonic_ns()+90_000_000_000,
        candidate_oid=tip,operation_id=owner.intent.operation_id,budget_id=target.budget_id,retention_id=target.retention_id)
    real=build_evidence(context,origin_binding_sha256=args['origin_binding_sha256'])
    gate.repo,gate.owner,gate.invocation,gate.candidate_oid=repo,loaded.owner,loaded,tip
    gate.producers={(binding.operation_id,binding.lane_id):('fixture-original-budget','fixture-original-retention')}
    class NativeFixtureAuthority(Authority):
        def assert_resources(self,**ctx):
            if fault=='https-positive':
                assert ctx['publication_transport']=='checkout_https' and ctx['original_origin_inode'] is None
                assert (ctx['original_attempt'],ctx['original_max_attempts'],ctx['original_alarm_seconds'])==(1,20,420)
            else:super().assert_resources(**ctx)
        def assert_publication_readback(self,**ctx):
            checked=state['checked'];attempt=checked.publication_attempt
            assert ctx['native_checked'] is checked and ctx['native_prepared'] is state['prepared']
            assert ctx['native_attempt'] is attempt
            ctx.update(bootstrap_pid=os.getpid(),original_deadline_monotonic_ns=context.original_deadline_monotonic_ns,
                conversion_result_path=context.result_path,conversion_manifest_digest=context.manifest_digest)
            if fault=='creator':
                child=os.fork()
                if child==0:
                    try:real.assert_publication_readback(**ctx)
                    except EvidenceUnavailable:os._exit(0)
                    os._exit(4)
                assert os.waitpid(child,0)[1]==0
                raise EvidenceUnavailable('test-owned child cannot credit original creator')
            if fault=='lease':checked.live.active=False
            if fault=='order':checked.invocation.writes=(checked.invocation.writes[-1],)
            if fault=='tree':ctx['native_prepared']=replace(state['prepared'],tree_oid='0'*40)
            if fault=='root':(repo/protocol.ROOT_PATH).write_bytes(b'test-owned corrupt current root')
            old_response=attempt.push_response
            if fault in ('lost-response','caught-lost-response'):attempt.push_response=None
            if fault=='readback':subprocess.check_call(['git','-C',str(remote),'update-ref','refs/heads/main',tip])
            if fault=='manifest':ctx['original_manifest_digest']='0'*64
            if fault in ('missing-context','caught-missing-context'):ctx.pop('native_attempt')
            if fault=='caught-invalid-context':ctx['native_checked']=None
            if fault=='caught-provider-check':real._failed=True
            if fault=='caught-legacy-route':
                for key in ('native_checked','native_prepared','native_attempt'):ctx.pop(key)
                ctx['phase']='fixture-wrong-conversion-route'
            try:return real.assert_publication_readback(**ctx)
            except EvidenceUnavailable as exc:
                if fault in ('caught-missing-context','caught-invalid-context','caught-provider-check','caught-legacy-route'):
                    return None  # Intentionally swallow an EARLY refusal before provider binding.
                if fault in ('lost-response','caught-lost-response'):
                    assert checked.failure is exc and attempt.uncertain
                    if fault=='caught-lost-response':
                        attempt.push_response=old_response
                        return None  # Buggy fixture wrapper; the caller must retain original failure.
                if fault=='lost-response':
                    attempt.push_response=old_response
                    with pytest.raises(EvidenceUnavailable,match='already entered'):
                        real.assert_publication_readback(**ctx)
                raise
    gate.evidence=NativeFixtureAuthority(remote)
    def produce(*a,**kw):
        append(causal,0);append(causal,1)
        return {'us':'test-owned two originals'}
    monkeypatch.setattr(allocation,'run_native_thematic_owner',produce)
    intents=causal[2]
    _,callback=engine.build_native_engine_producer(context,owner_binding=binding,regions=('us','ca'),
        native_intents={'us':intents[0],'ca':intents[1]},finalizer=final,call=object())
    def run():
        with gate.lease():
            return loaded.invoke_producer(binding,gate=gate,installed_commit_oid=tip,budget_id='fixture-original-budget',
                retention_id='fixture-original-retention',producer=callback)
    if fault in ('positive','https-positive'):
        assert run().status=='publication_confirmed' and not gate.held
        assert len(binding.attempts)==2
        if fault=='https-positive':assert network['received']==1 and carrier._closed
    else:
        messages={'creator':'child cannot credit original','lease':'same-process live producer',
            'order':'missing, duplicate, reordered','tree':'live installed owner/candidate',
            'lost-response':'actual original successful Git response','readback':'full candidate not confirmed',
            'manifest':'resources, chain, full tree','missing-context':'actual typed live native',
            'caught-lost-response':'final-candidate callback closed or unresolved',
            **{key:'final-candidate callback closed or unresolved' for key in
               ('caught-missing-context','caught-invalid-context','caught-provider-check','caught-legacy-route')}}
        with pytest.raises((EvidenceUnavailable,protocol.SnapshotIntegrityError),match=messages.get(fault)):run()
        assert gate.held and not callback.finalization.publication_attempt.confirmed
        if fault in ('caught-lost-response','caught-missing-context','caught-invalid-context','caught-provider-check','caught-legacy-route'):
            attempt=callback.finalization.publication_attempt
            assert attempt.uncertain and not attempt.remote_confirmed and attempt.control.exists()
            assert attempt.push_process.returncode==0 and os.fstat(attempt.origin_heads_fd)
            assert isinstance(callback.finalization.failure,EvidenceUnavailable)
            if fault=='caught-lost-response':assert 'successful Git response unavailable' in str(callback.finalization.failure)
    # This concrete partial provider still issues no host/resource admission.
    with pytest.raises(EvidenceUnavailable):real.assert_resources()


@pytest.fixture
def fresh_https_reader(tmp_path, https_origin):
    """Fast read-transport fixture; host admission is exclusively test-owned."""
    import time
    from types import SimpleNamespace
    from scripts.ci import qledger_owner_evidence as evidence, qledger_engine_publisher as publisher
    from scripts.ci.qledger_owner_invocation import NativeReaderInvocation, reader_assertion_scope
    remote,url,cert,header,network=https_origin
    repo=tmp_path/'reader-repo';repo.mkdir();git(repo,'init','-q')
    git(repo,'config','user.name','fixture');git(repo,'config','user.email','fixture@example.invalid')
    (repo/'retained').write_bytes(b'test-owned immutable input\n');git(repo,'add','retained');git(repo,'commit','-qm','fixture')
    oid=git(repo,'rev-parse','HEAD').decode();git(repo,'push','-q',str(remote),oid+':refs/heads/main')
    git(repo,'remote','add','origin',url)
    git(repo,'config','http.'+url.rsplit('/owner/',1)[0]+'/.extraheader','AUTHORIZATION: '+header)
    owner=tmp_path/'reader-owner';owner.mkdir(mode=0o700)
    context=SimpleNamespace(repo=repo,owner_root=owner,original_deadline_monotonic_ns=time.monotonic_ns()+30_000_000_000)
    proof=evidence.OrdinaryPublicationEvidence.__new__(evidence.OrdinaryPublicationEvidence)
    proof.context=context;proof.origin_digest=sha256(url.encode()).hexdigest()
    proof._pid=os.getpid();proof._last=time.monotonic_ns();proof._failed=False;proof._native_reader_attempt=None
    proof.native_reader_carrier=publisher.CheckoutHTTPSCarrier(repo,url,tls_ca_file=cert)
    class TestGate:
        def __init__(self):self._native_reader_call=None;self.calls=[];self.refuse=None
        def _check(self):pass
        def _assert(self,method,**ctx):
            self.calls.append((method,ctx))
            if self.refuse==method:raise evidence.EvidenceUnavailable('test-owned missing '+method)
            if method=='assert_descendants_settled':
                attempt=ctx['native_reader_attempt']
                assert attempt.process.poll()==0 and attempt.process.stdout.closed
                assert attempt.call is self._native_reader_call and attempt.carrier.pid==os.getpid()
    gate=TestGate();record={'candidate':oid,'publication':{'origin':proof.origin_digest,'transport':'checkout_https','layout':None}}
    call=NativeReaderInvocation(gate,None,record,{'operation_id':'test-reader','lane_id':'test-lane','budget_id':'reader-budget','retention_id':'reader-retention'},context.original_deadline_monotonic_ns,time.monotonic_ns())
    gate._native_reader_call=call
    def run():
        with reader_assertion_scope(call):
            try:return proof._native_origin_readback(record,call.check,reader_call=call)
            except BaseException as exc:
                # Match the public evidence entry's sticky-refusal wrapper.
                from scripts.ci.qledger_owner_invocation import record_publication_assertion_refusal
                record_publication_assertion_refusal(exc);raise
    state=SimpleNamespace(proof=proof,gate=gate,call=call,run=run,network=network,repo=repo,remote=remote,url=url,cert=cert,oid=oid)
    yield state
    # Test-owned cleanup only, after assertions about retained uncertain state.
    attempt=proof._native_reader_attempt
    if attempt and attempt.process and attempt.process.poll() is None:
        import signal
        os.killpg(attempt.process.pid,signal.SIGKILL);attempt.process.wait()
    if attempt and attempt.process and attempt.process.stdout:attempt.process.stdout.close()
    carrier=proof.native_reader_carrier
    if not carrier._closed:
        for fd in (carrier.git_dir,carrier.config_fd,carrier.ca_fd):
            if fd is not None:
                try:os.close(fd)
                except OSError:pass
    if attempt and not attempt.confirmed:
        for fd in [attempt.control_fd,*attempt.directories.values(),*(item[0] for item in attempt.files.values())]:
            if fd is not None:
                try:os.close(fd)
                except OSError:pass


@pytest.mark.parametrize('fault',['positive','origin','config-replaced','borrowed-writer','foreign-pid','resources','settlement','wrong-ref','redirect','missing-header','ambient-config'])
def test_fresh_https_reader_uses_own_bound_readonly_carrier(fresh_https_reader,monkeypatch,fault):
    from scripts.ci.qledger_owner_evidence import EvidenceUnavailable
    from engine.qledger_store_protocol import SnapshotIntegrityError
    s=fresh_https_reader;c=s.proof.native_reader_carrier
    before=git(s.remote,'rev-parse','refs/heads/main');config=(s.repo/'.git/config')
    if fault=='origin':s.proof.origin_digest='0'*64
    if fault=='config-replaced':
        payload=config.read_bytes();config.rename(config.with_name('original-config'));config.write_bytes(payload)
    if fault=='borrowed-writer':c._attempt=object()
    if fault=='foreign-pid':c.pid+=1
    if fault=='resources':s.gate.refuse='assert_resources'
    if fault=='settlement':s.gate.refuse='assert_descendants_settled'
    if fault=='wrong-ref':s.call.record['candidate']='a'*40
    if fault=='redirect':s.network['redirect']=True
    if fault=='missing-header':
        # A newly opened original FD with no qualified header cannot authenticate.
        for fd in (c.git_dir,c.config_fd,c.ca_fd):
            if fd is not None:os.close(fd)
        c._closed=True
        git(s.repo,'config','--unset-all',c.key)
        from scripts.ci.qledger_engine_publisher import CheckoutHTTPSCarrier
        c=s.proof.native_reader_carrier=CheckoutHTTPSCarrier(s.repo,s.url,tls_ca_file=s.cert)
    if fault=='ambient-config':
        monkeypatch.setenv('GIT_CONFIG_COUNT','1');monkeypatch.setenv('GIT_CONFIG_KEY_0','url.https://localhost:1/.insteadOf');monkeypatch.setenv('GIT_CONFIG_VALUE_0',s.url)
        monkeypatch.setenv('https_proxy','https://localhost:1')
    if fault in ('positive','ambient-config'):
        s.run();attempt=s.proof._native_reader_attempt
        assert attempt.confirmed and not attempt.uncertain and c._closed and not attempt.control.exists()
        assert attempt.response==((s.oid+'\trefs/heads/main\n').encode(),0)
        assert {method for method,_ in s.gate.calls}=={'assert_resources','assert_process_version','assert_descendants_settled'}
    else:
        with pytest.raises((EvidenceUnavailable,SnapshotIntegrityError)):s.run()
        assert s.call.failure is not None and s.call.uncertain
        attempt=s.proof._native_reader_attempt
        if attempt:
            assert not attempt.confirmed and attempt.uncertain and not c._closed
            with pytest.raises((EvidenceUnavailable,SnapshotIntegrityError)):s.run()
    assert s.network['received']==0 and git(s.remote,'rev-parse','refs/heads/main')==before
    assert all('receive-pack' not in path for _,path,_,_ in s.network.get('protocol',[]))
    if fault in ('origin','config-replaced','borrowed-writer','foreign-pid','resources','missing-header'):
        assert s.network['requests']==0


@pytest.mark.parametrize('fault',['partial','error','oversized','timeout','caught-settlement'])
def test_fresh_https_reader_uncertain_completion_is_not_retried(fresh_https_reader,monkeypatch,fault):
    import time,sys
    from scripts.ci import qledger_engine_publisher as publisher
    from scripts.ci.qledger_owner_evidence import EvidenceUnavailable
    from engine.qledger_store_protocol import SnapshotIntegrityError
    s=fresh_https_reader;original=subprocess.Popen;dispatches=[]
    if fault=='caught-settlement':
        original_assert=s.gate._assert
        def caught(method,**context):
            if method=='assert_descendants_settled':
                from scripts.ci.qledger_owner_invocation import record_publication_assertion_refusal
                try:raise EvidenceUnavailable('test-owned caught settlement failure')
                except EvidenceUnavailable as exc:record_publication_assertion_refusal(exc)
                return None
            return original_assert(method,**context)
        monkeypatch.setattr(s.gate,'_assert',caught)
    else:
        expected=(s.oid+'\trefs/heads/main\n').encode()
        payload=expected[:-1] if fault=='partial' else (b'x'*4097 if fault=='oversized' else expected)
        program='import sys,time\n'
        if fault=='timeout':
            endpoint=time.monotonic_ns()+2_000_000_000
            s.call.deadline=s.proof.context.original_deadline_monotonic_ns=endpoint
            program+='time.sleep(20)\n'
        else:program+=f'sys.stdout.buffer.write({payload!r});sys.stdout.flush();sys.exit({2 if fault=="error" else 0})\n'
        def child(command,**kwargs):
            if publisher._HTTPS_EXEC in command:
                dispatches.append(command)
                assert command[-6:]==['ls-remote','--refs','--exit-code','--',s.url,'refs/heads/main']
                assert 'push' not in command and kwargs['start_new_session'] is True
                return original([sys.executable,'-I','-c',program],**kwargs)
            return original(command,**kwargs)
        monkeypatch.setattr(subprocess,'Popen',child)
    with pytest.raises((EvidenceUnavailable,SnapshotIntegrityError)):s.run()
    attempt=s.proof._native_reader_attempt
    assert attempt.uncertain and not attempt.confirmed and s.call.failure is not None
    assert not attempt.carrier._closed and attempt.control.exists()
    with pytest.raises((EvidenceUnavailable,SnapshotIntegrityError)):s.run()
    if fault!='caught-settlement':assert len(dispatches)==1
    assert s.network['received']==0
