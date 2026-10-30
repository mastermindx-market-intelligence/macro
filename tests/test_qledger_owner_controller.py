"""Actual finite bootstrap composition in temporary, test-owned controller domains.

The authority below ships ONLY inside attested temporary owner bundles. It proves
its own fixture lock/FD/job domain; it is not production enrollment or evidence.
"""
from hashlib import sha256
from pathlib import Path
import json
import os
import subprocess
import sys
import time

import pytest
import yaml

from tests.test_qledger_daily_entry import entry_fixture, bundle_files, ALLOCATION
from tests.test_qledger_daily_normalizer import alias_kind  # noqa:F401
from tests.test_qledger_conversion_candidate import conversion_invocation,git  # noqa:F401
from tests.test_qledger_runner_bootstrap import SOURCE,canonical,put
from tests.test_qledger_native_publication import https_origin  # noqa:F401


OPAQUE_FORWARD=b'{"test_owned":"forward-ledger"}\nopaque original tail\n\xff\n'


@pytest.fixture(name='fixture')
def renderer_fixture(tmp_path,request,alias_kind):
    repo,_,blob,raw,limits=entry_fixture.__wrapped__(tmp_path,request,alias_kind)
    target=repo/'data/risk_radar/forward_log.jsonl'  # ci-trigger-closure: data — temporary fixture destination
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(OPAQUE_FORWARD)
    git(repo,'add','.');git(repo,'commit','-qm','test-owned opaque forward ledger')
    tip=git(repo,'rev-parse','HEAD').decode();git(repo,'update-ref','refs/remotes/origin/main',tip)
    return repo,tip,blob,raw,limits


OWNER_ENTRY=r'''
from pathlib import Path
from hashlib import sha256
import fcntl,json,os,stat,subprocess,time
from scripts.ci.qledger_daily_entry import build_producer
from scripts.ci.qledger_owner_controller import OwnerEntryEvidence
from scripts.ci.qledger_host_gate import GateRefusal

class TestDomainAuthority:
    def __init__(self,context):
        self.context=context;self.pid=os.getpid();self.children=[];self.fd={};self.stamps={}
        # Every fixture entry/controller acquires these actual exclusive leases.
        # No test claims these files establish coverage outside this fixture.
        role=os.environ['QL_TEST_ROLE'];self.role='reader' if role=='reader' else 'producer'
        self.fault=os.environ.get('QL_TEST_FAULT','positive')
        for name in ('entry-barrier',self.role+'.resource',self.role+'.retention'):
            fd=os.open(context.owner_root/name,os.O_RDWR|os.O_NOFOLLOW)
            try:fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:raise GateRefusal('test-owned retention lease unavailable')
            self.fd[name]=fd;self.stamps[name]=self.stamp(os.fstat(fd))
        self.budget=json.loads(os.pread(self.fd[self.role+'.resource'],4096,0))
        self.ordinal=2 if role=='second' else 1
        self.old_fd=int(os.environ.get('QL_TEST_OLD_FD','-1'))
        self.git_children=[]
    def stamp(self,s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    def check(self,**ctx):
        globals()['__loader__'].check()
        assert os.getpid()==self.pid==ctx['bootstrap_pid']
        assert ctx['original_deadline_monotonic_ns']==self.context.original_deadline_monotonic_ns==self.budget['endpoint']
        assert time.monotonic_ns()<self.budget['endpoint']
        assert ctx['repo']==self.context.repo and ctx['commit_oid']==self.context.candidate_oid
        for name,fd in self.fd.items():
            assert self.stamp(os.fstat(fd))==self.stamps[name]==self.stamp(os.stat(self.context.owner_root/name,follow_symlinks=False))
            assert os.fstat(fd).st_uid==os.geteuid() and stat.S_IMODE(os.fstat(fd).st_mode)==0o600
    def assert_bootstrap_exclusion(self,**ctx):
        self.check(**ctx)
        if self.old_fd>=0:
            os.fstat(self.old_fd)
            raise GateRefusal('test-owned preopen legacy FD is not settled')
        if self.fault=='exclusion-refusal':raise GateRefusal('test-owned writer exclusion unavailable')
        if self.fault=='settlement-refusal' and ctx.get('lane_id') is not None:
            raise GateRefusal('test-owned original descendants unsettled')
    def assert_launcher_coverage(self,**ctx):
        self.check(**ctx)
        assert 'entry-barrier' in self.fd
    def assert_resources(self,**ctx):
        self.check(**ctx)
        if self.fault in ('resource-refusal','caught-resource') and ctx.get('lane_id') is not None:raise GateRefusal('test-owned resource lease unavailable')
        if ctx.get('lane_id') is not None:
            assert (ctx['operation_id'],ctx['lane_id'],ctx['budget_id'],ctx['retention_id'])==tuple(self.budget['binding'])
        else:
            assert (ctx['operation_id'],None,ctx['budget_id'],ctx['retention_id'])==tuple(self.budget['conversion'])
        if self.fault=='boolean-authority':return True
        if 'original_attempt' in ctx:
            assert (ctx['original_attempt'],ctx['original_max_attempts'],ctx['original_alarm_seconds'])==(self.ordinal,20,420)
    def assert_process_version(self,**ctx):
        self.check(**ctx)
        assert type(ctx['gate']).__module__=='scripts.ci.qledger_host_gate'
        for key in ('native_reader','native_anchor'):
            call=ctx.get(key)
            if call is not None:assert call.pid==self.pid
        path=ctx.get('git_executable')
        if path is not None:
            assert str(Path(path).resolve())==self.budget['git']
            assert sha256(Path(path).read_bytes()).hexdigest()==self.budget['git_sha256']
    def assert_publication_readback(self,**ctx):
        self.check(**ctx)  # Actual complete Git proof is supplied by the adapter.
    def assert_descendants_settled(self,**ctx):
        self.check(**ctx)
        if self.fault=='caught-settlement' and ctx.get('lane_id') is not None:
            raise GateRefusal('test-owned process settlement unavailable')
        attempts=[ctx.get(k) for k in ('native_attempt','native_anchor_attempt','native_reader_attempt')]
        for attempt in attempts:
            if attempt is not None:
                attempt.carrier.check()
                os.fstat(attempt.carrier.config_fd)
                children=getattr(attempt,'processes',None) or [attempt.process]
                for child in children:
                    assert child is not None and child.poll()==0
                    # Read/anchor children own sessions; no descendant may remain
                    # in their exact known group after the original wait.
                    if hasattr(attempt,'processes'):
                        try:os.killpg(child.pid,0)
                        except ProcessLookupError:pass
                        else:raise GateRefusal('test-owned query descendants remain')
        for child in self.children:assert child.poll()==0
        # Each test driver owns its session. Observe ONLY that known job group,
        # not a host process inventory. ps itself is the one known query child.
        assert os.getpgrp()==os.getsid(0)==self.pid
        observer=subprocess.Popen(['ps','-o','pid=','-g',str(os.getpgrp())],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        raw,error=observer.communicate(timeout=max(.01,(self.budget['endpoint']-time.monotonic_ns())/1e9))
        assert observer.returncode==0 and not error
        members=list(map(int,raw.split()))
        assert self.pid in members and len(members)==len(set(members))
        assert set(members)<={self.pid,observer.pid} and observer.poll()==0
    def close(self):
        for fd in self.fd.values():os.close(fd)
        self.fd.clear()

def build_evidence(context):
    authority=TestDomainAuthority(context)
    fault=os.environ.get('QL_TEST_FAULT','positive')
    if fault=='missing-authority':authority=None
    if fault=='boolean-provider':authority=True
    if fault=='foreign-authority':authority=Path(context.owner_root)
    evidence=OwnerEntryEvidence(context,authority,conversion_origin_binding_sha256=INITIAL_ORIGIN)
    if fault=='caught-settlement':
        checked=evidence.assert_descendants_settled
        def caught(**ctx):
            try:return checked(**ctx)
            except GateRefusal:return None
        evidence.assert_descendants_settled=caught
    if fault=='caught-resource':
        checked=evidence.assert_resources
        def caught(**ctx):
            try:return checked(**ctx)
            except GateRefusal:return None
        evidence.assert_resources=caught
    return evidence

def reader(context):
    from engine import qledger_store as store,qledger_store_protocol as p
    current=store._read_claims_binding(context.repo/'data/qledger/claims.jsonl')
    with p.open_logical_bytes(current.read_snapshot()) as raw:return raw.read()

def selection(context,packet):
    from engine import qledger_original_result as r,qledger_store_protocol as p,qledger_store_native as n
    prefix=()
    for entry in packet['originals']:
        value=r.read_original_result(owner_root=Path(entry['owner_root']),result_path=Path(entry['result_path']),
            expected_result_id=entry['result_id'],expected_manifest_digest=entry['manifest_digest'],
            expected_claims_path=context.repo/'data/qledger/claims.jsonl',expected_intent=n.NativeClaimsIntent(**entry['intent']),
            limits=p.ProtocolLimits(**packet['limits']),predecessors=prefix)
        prefix=(*prefix,value)
    return (*packet['selection'],value,packet['publication'])

def original(loaded,previous,number):
    from engine.qledger_original_result import OriginalResultClaimsBinding,OriginalResultTarget
    from engine.qledger_store_native import NativeClaimsIntent
    from scripts.ci.qledger_conversion_candidate import CandidateCommitMetadata
    from scripts.ci.qledger_engine_publisher import CheckoutHTTPSCarrier,NativePublicationFinalizer
    ctx=loaded.context;authority=loaded.gate.evidence.provider.authority
    fault=os.environ.get('QL_TEST_FAULT','positive')
    if previous is None:
        ref=loaded.gate.owner.target.accepted_ref
        accepted=loaded.gate.owner.target.accepted_tip_oid
        def actual_tip():
            return subprocess.check_output(['git','-C',str(ctx.repo),'rev-parse','--verify',ref+'^{commit}']).strip().decode()
        assert actual_tip()==accepted
        def checkout_and_seed(oid):
            # Preflight has completed and the real install HOLD is owned. A
            # named-origin push deliberately updates its tracking ref here;
            # setup must not rely on URL-push behavior across Git versions.
            assert loaded.gate._mode=='install' and loaded.gate._hold_identity is not None
            assert (ctx.owner_root/loaded.gate.HOLD).is_file() and actual_tip()==accepted
            child_git(authority,ctx.repo,'checkout','--quiet','-B','main',oid)
            child_git(authority,ctx.repo,'push','--quiet','origin',oid+':refs/heads/main')
            assert actual_tip()==oid
            child_git(authority,ctx.repo,'push','--quiet',TEST_REMOTE,oid+':refs/heads/main')
            assert actual_tip()==oid
        loaded.gate.initial_checkout(checkout_and_seed)
        assert actual_tip()==ctx.candidate_oid
        child_git(authority,ctx.repo,'remote','set-url','origin',HTTPS_URL)
        # Only test-owned credentials are provisioned, never real secrets.
        child_git(authority,ctx.repo,'config',HTTPS_KEY,TEST_HEADER)
    intent=NativeClaimsIntent('producer-original','producer-lane','write-'+str(number))
    root=ctx.owner_root/'producer-evidence';tip=ctx.candidate_oid if previous is None else previous[0]
    target=OriginalResultTarget(root,root/intent.transaction_id,intent.transaction_id,tip,
        'refs/remotes/origin/main','refs/heads/main',CandidateCommitMetadata('Test original','fixture@example.invalid',1700000099+number))
    binding=OriginalResultClaimsBinding(ctx.repo/'data/qledger/claims.jsonl',operation_id=intent.operation_id,
        lane_id=intent.lane_id,limits=loaded.gate.owner.limits,original_result_targets={intent:target})
    anchor=CheckoutHTTPSCarrier(ctx.repo,HTTPS_URL,tls_ca_file=Path(TEST_CA))
    publish=CheckoutHTTPSCarrier(ctx.repo,HTTPS_URL,tls_ca_file=Path(TEST_CA))
    if fault=='shared-carrier':anchor=publish
    if fault=='shared-fd':os.close(anchor.config_fd);anchor.config_fd=publish.config_fd
    if fault=='used-carrier':anchor._attempt=object()
    if fault=='foreign-carrier':anchor.repo=ctx.owner_root
    publication=NativePublicationFinalizer(origin_binding_sha256=NATIVE_ORIGIN,original_origin_inode=None,
        original_attempt=number,original_max_attempts=20,original_alarm_seconds=420,https_carrier=publish)
    provider=loaded.gate.evidence.provider
    provider._bind_native_original(loaded,binding,publication,anchor_carrier=anchor)
    if fault=='wrong-binding':binding.operation_id='foreign-operation'
    if fault=='changed-attempt':publication.original['original_attempt']=19
    # The ordinary public entry still refuses even this fully bound controller.
    # No source guard is patched; only the explicitly commissioned attested
    # owner entry exercises the private composition with its actual authority.
    public_refusal(loaded,binding,intent,publication)
    assert not binding.attempts and anchor._attempt is None and publish._attempt is None
    event(b'B')
    value=loaded._native_cycle(owner_binding=binding,regions=('us',),native_intents={'us':intent},
        publication=publication,current_generation=previous,call=object())
    before=(tuple(binding.attempts),anchor._attempt,publish._attempt)
    event(b'A')
    public_refusal(loaded,binding,intent,publication)
    assert before==(tuple(binding.attempts),anchor._attempt,publish._attempt)
    event(b'C')
    assert value.status=='publication_confirmed'
    assert publication.original['original_attempt']==number
    assert number==1 or provider.native._native_anchor_attempt.confirmed
    retained=binding.read_original_write_chain(value.original_writes)
    attempt=publication.generation._attempt
    assert attempt.confirmed and not attempt.uncertain
    return value,retained,dict(origin=NATIVE_ORIGIN,transport='checkout_https',layout=None)

def child_git(authority,repo,*args):
    child=subprocess.Popen(['git','-C',str(repo),*args],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    authority.children.append(child)
    assert child.wait()==0

def public_refusal(loaded,binding,intent,publication):
    try:loaded.native_producer(owner_binding=binding,regions=('us',),native_intents={'us':intent},publication=publication)
    except Exception as exc:
        assert type(exc).__name__=='BootstrapRefusal'
        assert 'native HTTPS installed-reader join is not qualified' in str(exc)
    else:raise AssertionError('public HTTPS route became permissive')

def event(value):
    assert os.write(int(os.environ['QL_TEST_EVENT_FD']),value)==1
    assert os.read(int(os.environ['QL_TEST_ACK_FD']),1)==b'!'
'''

DRIVER=r'''
import importlib.util,json,os,subprocess,sys
from pathlib import Path
boot,config,digest,role,dependency_path=sys.argv[1:]
sys.path.append(dependency_path)
spec=importlib.util.spec_from_file_location('test_owner_bootstrap',boot)
b=importlib.util.module_from_spec(spec);sys.modules[spec.name]=b;spec.loader.exec_module(b)
doc=json.loads(Path(config).read_text());owner=Path(doc['owner_root']);repo=Path(doc['repo'])
fault=os.environ.get('QL_TEST_FAULT','positive');packet=json.loads(sys.stdin.read() or 'null')
result=None;loaded=None
try:
 with b.trusted_bootstrap(owner_root=owner,repo=repo,config_path=Path(config),config_digest=digest) as loaded:
    entry=loaded.entry;provider=loaded.gate.evidence.provider
    if role in ('first','second'):
        previous=None if packet is None else entry.selection(loaded.context,packet)
        value,retained,pin=loaded.bundle.callable(entry.original)(loaded,previous,1 if role=='first' else 2)
        from engine import qledger_original_result as r
        from dataclasses import asdict
        result=dict(selection=[value.publication.candidate_oid,value.publication.tree_oid,value.publication.source_candidate_oid],
            originals=[r._descriptor(x) for x in (*retained.predecessors,retained)],limits=asdict(retained.limits),publication=pin)
    else:
        from scripts.ci.qledger_engine_publisher import CheckoutHTTPSCarrier
        carrier=CheckoutHTTPSCarrier(repo,entry.HTTPS_URL,tls_ca_file=Path(entry.TEST_CA))
        provider._bind_native_reader(loaded,carrier=carrier,operation_id='reader-original',lane_id='reader-lane',
            budget_id='reader-budget',retention_id='reader-retention',origin_binding_sha256=entry.NATIVE_ORIGIN)
        payload=loaded.native_reader(entry.selection(loaded.context,packet),operation_id='reader-original',lane_id='reader-lane',
            budget_id='reader-budget',retention_id='reader-retention')
        assert payload.count(b'fresh_fixture_original')==2
        assert provider.native._native_reader_attempt.confirmed and carrier._closed
        result={'fresh_reader':True,'pid':os.getpid(),'endpoint':loaded.context.original_deadline_monotonic_ns}
    assert loaded.gate._mode is None and not (owner/loaded.gate.HOLD).exists()
    provider.authority.close()
except BaseException as exc:
 if fault=='positive':raise
 reasons={'missing-authority':'actual external controller authority required','boolean-provider':'actual external controller authority required','foreign-authority':'qualified bundle',
    'boolean-authority':'admission flag','shared-carrier':'distinct typed original HTTPS carriers',
    'used-carrier':'foreign, transferred or used','foreign-carrier':'foreign, transferred or used',
    'preopen-fd':'preopen legacy FD','resource-refusal':'resource lease unavailable',
    'exclusion-refusal':'writer exclusion unavailable','settlement-refusal':'original descendants unsettled',
    'wrong-binding':'actual bound owner original','changed-attempt':'actual bound owner original',
    'shared-fd':'shared original credential descriptor','retention-refusal':'retention lease unavailable',
    'caught-resource':'resource lease unavailable',
    'caught-settlement':'unresolved'}
 if fault!='caught-settlement':assert reasons[fault] in str(exc),(fault,str(exc))
 if loaded is not None:
    binding=getattr(loaded.gate.evidence.provider,'original',None)
    if binding is not None:
        assert not binding[0].attempts or (owner/loaded.gate.HOLD).exists()
    if fault in ('preopen-fd','resource-refusal','caught-resource','exclusion-refusal','settlement-refusal','caught-settlement','boolean-authority'):
        assert (owner/loaded.gate.HOLD).exists()
    if fault=='caught-settlement':
        attempt=loaded.gate.evidence.provider.native._native_readback_attempt
        assert attempt.uncertain and attempt.checked.failure is not None and not attempt.confirmed
        assert str(attempt.checked.failure)=='test-owned process settlement unavailable'
        os.fstat(attempt.carrier.config_fd)
    if fault=='caught-resource':
        provider=loaded.gate.evidence.provider;first=provider.failure
        assert str(first)=='test-owned resource lease unavailable'
        binding,publication=provider.original[:2]
        assert not binding.attempts and provider.native._native_readback_attempt is None
        # Pure binding/private-cycle admission checks cannot reset the failure
        # by changing phase or trying to turn this producer into a reader.
        for check in (lambda:provider._require_native_original(loaded,binding,publication),
                      lambda:provider._bind_native_reader(loaded,carrier=provider.original[3],
                        operation_id='reader-original',lane_id='reader-lane',budget_id='reader-budget',
                        retention_id='reader-retention',origin_binding_sha256=provider.native.origin_digest)):
            try:check()
            except BaseException as again:assert again is first
            else:raise AssertionError('caught early refusal was reset')
 print('TEST_REFUSAL '+fault)
else:
 assert fault=='positive'
 print('TEST_RESULT '+json.dumps(result,sort_keys=True))
'''


@pytest.fixture
def controller_case(conversion_invocation,tmp_path,https_origin):
    invocation,prepared=conversion_invocation;owner=invocation.owner.target.owner_root;repo=invocation.owner.repo
    owner.chmod(0o700);(owner/'producer-evidence').mkdir(mode=0o700)
    remote,url,cert,header,network=https_origin
    initial=owner/'initial-published.git';git(repo,'init','--bare','--quiet',str(initial));git(repo,'remote','add','origin',str(initial))
    assert git(repo,'rev-parse','--verify',invocation.owner.target.accepted_ref+'^{commit}').decode()==invocation.owner.target.accepted_tip_oid
    bundle=owner/'bundle';files=set(bundle_files())|{'scripts/ci/qledger_owner_controller.py','scripts/ci/qledger_owner_evidence.py','scripts/ci/qledger_engine_publisher.py'}
    pins={name:put(bundle/name,(SOURCE/name).read_bytes()) for name in files}
    pins['scripts/build_allocation.py']=put(bundle/'scripts/build_allocation.py',ALLOCATION.encode())
    from urllib.parse import urlsplit
    entry=OWNER_ENTRY+f'\nINITIAL_ORIGIN={sha256(str(initial).encode()).hexdigest()!r}\nNATIVE_ORIGIN={sha256(url.encode()).hexdigest()!r}\nHTTPS_URL={url!r}\nHTTPS_KEY={"http.https://"+urlsplit(url).netloc+"/.extraheader"!r}\nTEST_HEADER={"authorization: "+header!r}\nTEST_CA={str(cert)!r}\nTEST_REMOTE={str(remote)!r}\n'
    pins['owner_entry.py']=put(bundle/'owner_entry.py',entry.encode())
    for name in ('templates/shared_shell_bridge.js','templates/shared_shell.css'):pins[name]=put(bundle/name,(SOURCE/name).read_bytes())
    assert len(pins)<=128
    bootstrap=owner/'bootstrap.py';bootstrap_sha=put(bootstrap,(SOURCE/'scripts/ci/qledger_runner_bootstrap.py').read_bytes())
    endpoint=time.monotonic_ns()+300_000_000_000
    producer=dict(operation_id='producer-original',lane_id='producer-lane',budget_id='original-producer-budget',retention_id='original-producer-retention')
    reader=dict(operation_id='reader-original',lane_id='reader-lane',budget_id='reader-budget',retention_id='reader-retention')
    executable=Path(subprocess.check_output(['which','git']).decode().strip()).resolve()
    put(owner/'entry-barrier',b'test-owned all-entry controller lease\n')
    for role,binding in (('producer',producer),('reader',reader)):
        put(owner/(role+'.resource'),canonical(dict(endpoint=endpoint,binding=list(binding.values()),
            conversion=[invocation.owner.intent.operation_id,None,invocation.owner.target.budget_id,invocation.owner.target.retention_id],
            git=str(executable),git_sha256=sha256(executable.read_bytes()).hexdigest())))
        put(owner/(role+'.retention'),b'test-owned retained-original capacity for this fixture only\n')
    runtime={str(repo/'scripts/ci'/name):sha256((repo/'scripts/ci'/name).read_bytes()).hexdigest() for name in
        ('daily_engine_commit_outputs.sh','push_retry.sh','strip_conflict_markers.sh','options_signal_nightly.sh')}
    runtime[str(repo/'config.yml')]=sha256((repo/'config.yml').read_bytes()).hexdigest()
    cfg=dict(schema=1,repo=str(repo),owner_root=str(owner),bundle_root=str(bundle),result_path=str(invocation.owner.target.result_path),
        manifest_digest=prepared.manifest_digest,bootstrap_sha256=bootstrap_sha,original_deadline_monotonic_ns=endpoint,
        bundle_files=pins,entry_module='owner_entry',producer_context=producer,
        gate=dict(candidate_oid=prepared.candidate.candidate_oid,tree_oid=prepared.candidate.tree_oid,accepted_tip_oid=invocation.owner.target.accepted_tip_oid,
            runtime_code=runtime,workflow_oids=[prepared.candidate.candidate_oid],producers=[producer,reader],runner_name='test-owned-controller',repository='fixture/macro',agent_id=28))
    config=owner/'bootstrap.json';digest=put(config,canonical(cfg));driver=tmp_path/'driver.py';driver.write_text(DRIVER)
    def run(role,packet=None,fault='positive'):
        import fcntl,threading
        event_r,event_w=os.pipe();ack_r,ack_w=os.pipe()
        env={**os.environ,'QL_TEST_ROLE':role,'QL_TEST_FAULT':fault,
             'QL_TEST_EVENT_FD':str(event_w),'QL_TEST_ACK_FD':str(ack_r)};fds=[event_w,ack_r]
        if fault=='retention-refusal':
            held=os.open(owner/'producer.retention',os.O_RDWR);fcntl.flock(held,fcntl.LOCK_EX|fcntl.LOCK_NB)
        else:held=None
        if fault=='preopen-fd':
            fd=os.open(repo/'data/qledger/claims.jsonl',os.O_RDONLY);fds.append(fd);env['QL_TEST_OLD_FD']=str(fd)
        counts=(network['received'],network['requests']);events=[];errors=[]
        child=subprocess.Popen([sys.executable,'-I',str(driver),str(bootstrap),str(config),digest,role,str(Path(yaml.__file__).parent.parent)],
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=owner,env=env,pass_fds=tuple(fds),start_new_session=True)
        for fd in fds:os.close(fd)
        def monitor():
            expected=counts
            try:
                while True:
                    value=os.read(event_r,1)
                    if not value:break
                    events.append(value)
                    actual=(network['received'],network['requests'])
                    if value in (b'B',b'C'):assert actual==expected
                    else:assert value==b'A';expected=actual
                    assert os.write(ack_w,b'!')==1
            except BaseException as exc:errors.append(exc)
            finally:os.close(event_r);os.close(ack_w)
        thread=threading.Thread(target=monitor);thread.start()
        stdout,stderr=child.communicate(json.dumps(packet),timeout=180);thread.join(timeout=5)
        if held is not None:os.close(held)
        assert not thread.is_alive() and not errors,errors
        assert child.returncode==0,stdout+stderr
        if fault!='positive':assert 'TEST_REFUSAL '+fault in stdout;return
        if role!='reader':assert events==[b'B',b'A',b'C']
        return json.loads(next(x.removeprefix('TEST_RESULT ') for x in stdout.splitlines() if x.startswith('TEST_RESULT ')))
    return run,repo,owner,network


def test_trusted_owner_two_https_originals_and_fresh_reader(controller_case):
    run,repo,owner,network=controller_case
    first=run('first');initial=(owner/'producer-evidence/write-1/manifest.json').read_bytes()
    second=run('second',first)
    assert (owner/'producer-evidence/write-1/manifest.json').read_bytes()==initial
    assert git(repo,'rev-list','--parents','-n','1',second['selection'][0]).decode().split()[1]==first['selection'][0]
    for value in (first,second):
        assert git(repo,'show',value['selection'][0]+':data/risk_radar/forward_log.jsonl')==OPAQUE_FORWARD.rstrip(b'\n')  # ci-trigger-closure: data — synthetic Git fixture read
    assert (repo/'data/risk_radar/forward_log.jsonl').read_bytes()==OPAQUE_FORWARD  # ci-trigger-closure: data — temporary fixture read
    reader=run('reader',second)
    assert reader['fresh_reader'] and network['received']==2
    assert not (owner/'qledger-install.hold').exists()


@pytest.mark.parametrize('fault',['missing-authority','foreign-authority','boolean-authority','shared-carrier','used-carrier',
    'foreign-carrier','preopen-fd','resource-refusal','exclusion-refusal','settlement-refusal','wrong-binding','changed-attempt','caught-settlement','shared-fd','retention-refusal','caught-resource','boolean-provider'])
def test_trusted_owner_composition_refuses_without_actual_inputs(controller_case,fault):
    run,repo,owner,network=controller_case
    run('first',fault=fault)
    assert network['received']==(1 if fault=='caught-settlement' else 0)
    assert (owner/'producer-evidence/write-1/manifest.json').exists()==(fault=='caught-settlement')
