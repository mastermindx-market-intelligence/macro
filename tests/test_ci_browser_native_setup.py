"""Explicit owner composition tests. All acquisition/root calls are synthetic."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import ci_browser_native_setup as SETUP
from scripts.ci_apt_native_plan import QUALIFIED_DRIVER
from scripts.ci_apt_cold_acquisition import AcquisitionResult


def sources():
    return {name: hashlib.sha256((Path(SETUP.__file__).parent/name).read_bytes()).hexdigest() for name in SETUP.BOUND_FILES}


def observed(outcome='passed', settlement=None):
    return SimpleNamespace(outcome=outcome, returncode=0 if outcome=='passed' else None,
                           timeout_settlement=settlement, failure_signature=None, detail='browser original outcome')


def runtime(monkeypatch):
    monkeypatch.setattr(SETUP.time, 'monotonic', lambda:100)
    monkeypatch.setattr(SETUP.shutil, 'which', lambda *_a, **_k:'/isolated/bin/python')
    monkeypatch.setattr(SETUP.platform, 'freedesktop_os_release', lambda:{'ID':'ubuntu','VERSION_ID':'24.04'})
    monkeypatch.setattr(SETUP.platform, 'machine', lambda:'x86_64')
    source = {'observed_version':'1.64.1','driver_version':'1.64.0-beta-1791568591000',
              'input_sha256':{'driver_bundle':QUALIFIED_DRIVER}}
    monkeypatch.setattr(SETUP, 'observe_command', lambda argv, **kwargs:(0,b'CI_BROWSER_DEPENDENCY_INPUTS='+json.dumps(source).encode()+b'\n'))
    events=[]
    monkeypatch.setattr(SETUP, 'bootstrap_root', lambda packet, env, deadline:events.append(('bootstrap',deadline,env)) or '/tmp/ci-apt-fixture')
    class Backend:
        def __init__(self, root, env, plan): self.root=root; self.plan=plan;self.handles={};self.records={}
        def stage(self, mode, deadline):
            events.append((mode,deadline))
            return {'outcome':'passed','settlement':'settled','archives':[]}
    monkeypatch.setattr(SETUP, 'NativeAptBackend', Backend)
    def acquire(plan, backend, *, deadline):
        events.append(('acquire',deadline,plan.transaction));return AcquisitionResult('passed','settled',(),(),'passed','NATIVE_TRANSACTION_COMPLETE')
    monkeypatch.setattr(SETUP,'acquire_and_install',acquire)
    return events


def test_bound_source_packet_is_exact_and_root_bootstrap_is_statically_closed():
    expected=sources(); packet=json.loads(SETUP.source_packet(expected))
    assert set(packet['files']) == set(SETUP.ROOT_FILES)
    assert packet['expected'] == {name:expected[name] for name in SETUP.ROOT_FILES}
    tree=ast.parse(SETUP.BOOTSTRAP); compile(tree,'bound-bootstrap','exec')
    constants=[node.value for node in ast.walk(tree) if isinstance(node,ast.Constant) and isinstance(node.value,str)]
    assert '#!/bin/sh\nexec /usr/bin/python3 -I ' in constants
    assert 'os.O_EXCL|os.O_NOFOLLOW' in SETUP.BOOTSTRAP
    assert '0o444' in SETUP.BOOTSTRAP and '0o555' in SETUP.BOOTSTRAP
    changed={**expected,SETUP.ROOT_FILES[0]:'0'*64}
    with pytest.raises(ValueError, match='HELPER_SOURCE_CHANGED'):SETUP.source_packet(changed)
    with pytest.raises(ValueError, match='HELPER_SOURCE_BINDING_ABSENT'):SETUP.source_packet({})


@pytest.mark.parametrize('deadline',[float('nan'),float('inf'),-1,100])
def test_invalid_or_elapsed_original_deadline_never_launches_even_bootstrap(monkeypatch,deadline):
    monkeypatch.setattr(SETUP.time,'monotonic',lambda:100)
    monkeypatch.setattr(SETUP.subprocess,'Popen',lambda *a,**k:pytest.fail('must not launch'))
    result=SETUP.run_native_setup(deadline=deadline,command_env={},expected_sources=sources(),browser_stream=None)
    assert result['outcome']=='failed' and result['timeout_settlement'] is None


def test_native_apply_then_exact_vendor_browser_uses_same_env_and_remaining_original_total(monkeypatch):
    events=runtime(monkeypatch);env={'PATH':'/isolated/bin','ORIGINAL':'same'};calls=[]
    def browser(command,**kwargs):calls.append((command,kwargs));return observed()
    result=SETUP.run_native_setup(deadline=600,command_env=env,expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed' and result['timeout_settlement'] is None
    assert calls==[('python -m playwright install chromium',{'env':env,'timeout_seconds':500})]
    assert [e[0] for e in events]==['bootstrap','update','resolve','acquire','cleanup']
    assert all(e[1]==600 for e in events)


@pytest.mark.parametrize('fault',['unqualified-source','update-unknown','resolve-unknown','download-unknown','install-unknown','browser-unknown','cleanup-unknown'])
def test_unknown_never_falls_back_retries_installs_or_cleans_beyond_original_boundary(monkeypatch,fault):
    events=runtime(monkeypatch);calls=[]
    backend=SETUP.NativeAptBackend;original=backend.stage
    if fault=='unqualified-source':
        monkeypatch.setattr(SETUP,'observe_command',lambda *a,**k:(0,b'CI_BROWSER_DEPENDENCY_INPUTS={}\n'))
    if fault in {'update-unknown','resolve-unknown','cleanup-unknown'}:
        mode=fault.split('-')[0]
        def stage(self,selected,deadline):
            if selected==mode:events.append((selected,deadline));raise SETUP.NativeUnknown('original retained native operation',4242,'timed_out')
            return original(self,selected,deadline)
        monkeypatch.setattr(backend,'stage',stage)
    if fault in {'download-unknown','install-unknown'}:
        monkeypatch.setattr(SETUP,'acquire_and_install',lambda *a,**k:AcquisitionResult('timed_out','unknown',(),(0,),
                            'unknown' if fault=='install-unknown' else 'never_started','CHILD_SETTLEMENT_UNKNOWN'))
    def browser(command,**kwargs):calls.append(command);return observed('timed_out','unknown') if fault=='browser-unknown' else observed()
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']!='passed' and result['timeout_settlement']=='unknown'
    assert len(calls)==(1 if fault in {'browser-unknown','cleanup-unknown'} else 0)
    if fault=='cleanup-unknown':assert 'installation=passed' in result['detail'] and 'browser=passed' in result['detail']
    else:assert 'cleanup' not in [e[0] for e in events]
    assert len([e for e in events if e[0]=='bootstrap'])<=1


@pytest.mark.parametrize('raw,code',[(b'',0),(b'CI_APT_NATIVE_RESULT={}\n',0),
 (b'CI_APT_NATIVE_RESULT={"mode":"download","index":1,"outcome":"passed","settlement":"settled"}\n',0),
 (b'CI_APT_NATIVE_RESULT={"mode":"download","index":0,"outcome":"passed","settlement":"settled"}\n',73)])
def test_response_loss_partial_foreign_identity_and_exit_contradiction_cannot_admit_archive(raw,code):
    with pytest.raises(SETUP.NativeUnknown):SETUP.parsed_result(code,raw,mode='download',index=0)


def test_finite_mapping_has_no_current_source_or_missing_file_fallback(monkeypatch):
    runtime(monkeypatch)
    monkeypatch.setattr(SETUP.subprocess,'Popen',lambda *a,**k:pytest.fail('source refusal before effects'))
    expected=sources();expected[SETUP.ROOT_FILES[0]]='0'*64
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=expected,browser_stream=None)
    assert result['outcome']=='failed' and 'HELPER_SOURCE_CHANGED' in result['detail']


def test_bootstrap_deadline_after_launch_preserves_handle_without_cleanup(monkeypatch):
    readfd,writefd=os.pipe();out=os.fdopen(readfd,'rb',buffering=0)
    inread,inwrite=os.pipe();input_stream=os.fdopen(inwrite,'wb',buffering=0)
    process=SimpleNamespace(pid=4242,stdin=input_stream,stdout=out,poll=lambda:None)
    monkeypatch.setattr(SETUP.subprocess,'Popen',lambda *a,**k:process)
    ticks=iter([599,601]);monkeypatch.setattr(SETUP.time,'monotonic',lambda:next(ticks))
    try:
        with pytest.raises(SETUP.NativeUnknown) as caught:SETUP.bootstrap_root(b'{}',{},600)
        assert caught.value.child_pid==4242 and caught.value.outcome=='timed_out'
    finally:
        input_stream.close();out.close();os.close(inread);os.close(writefd)


def test_platform_override_cannot_silently_change_the_qualified_native_dependency_closure(monkeypatch):
    monkeypatch.setattr(SETUP.time,"monotonic",lambda:0)
    monkeypatch.setattr(SETUP.subprocess,"Popen",lambda *a,**k:pytest.fail("platform refusal before effects"))
    result=SETUP.run_native_setup(deadline=600,command_env={"PLAYWRIGHT_HOST_PLATFORM_OVERRIDE":"foreign"},expected_sources=sources(),browser_stream=None)
    assert result["outcome"]=="failed" and "DEPENDENCY_PLATFORM_OVERRIDE_UNQUALIFIED" in result["detail"]


def test_failed_native_download_code_and_fixed_errors_reach_existing_owner_detail(monkeypatch):
    events=runtime(monkeypatch)
    def acquire(plan,backend,*,deadline):
        backend.records[4]={'mode':'download','index':4,'outcome':'failed','settlement':'settled','returncode':100,
                            'reported_errors':['PERMISSION','FETCH'],'raw':'SECRET:credential','child_pid':'SECRET pid'}
        return AcquisitionResult('failed','settled',(),(),'never_started','NATIVE_DOWNLOAD_FAILED')
    monkeypatch.setattr(SETUP,'acquire_and_install',acquire)
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=lambda *a,**k:pytest.fail('no browser after failed download'))
    assert result['outcome']=='failed' and result['returncode']==1 and result['timeout_settlement'] is None
    assert 'downloads[index,returncode,reported_errors]=[[4,100,["PERMISSION","FETCH"]]]' in result['detail']
    assert 'SECRET' not in result['detail'] and 'credential' not in result['detail']
    assert 'installation=never_started' in result['detail']
    assert 'cleanup' not in [event[0] for event in events]


@pytest.mark.parametrize('code,reported,expected_code,expected_reported', [
    (100,['AUTH','FETCH'],100,['AUTH','FETCH']),
    (-9,['UNCLASSIFIED'],-9,['UNCLASSIFIED']),
    ('SECRET',['SECRET'],None,['UNCLASSIFIED']),
    (True,{'raw':'SECRET'},None,['UNCLASSIFIED']),
    (0,['AUTH','AUTH'],None,['UNCLASSIFIED']),
    (100000,['UNCLASSIFIED','AUTH'],None,['UNCLASSIFIED']),
])
def test_owner_sanitizes_native_diagnostics_without_changing_original_failed_status(code,reported,expected_code,expected_reported):
    native={'mode':'download','index':0,'outcome':'failed','settlement':'settled','returncode':code,
            'reported_errors':reported,'raw':'SECRET password https://private.invalid'}
    parsed=SETUP.parsed_result(1,SETUP.RESULT_PREFIX+json.dumps(native).encode()+b'\n',mode='download',index=0)
    assert parsed['outcome']=='failed' and parsed['settlement']=='settled'
    assert SETUP.failed_download_summaries({0:parsed}) == [[0,expected_code,expected_reported]]
    assert 'SECRET' not in json.dumps(SETUP.failed_download_summaries({0:parsed}))


def test_owner_summary_is_bounded_and_cannot_expose_foreign_index_or_unsettled_returncode():
    failed={'mode':'download','outcome':'failed','settlement':'settled','returncode':100,
            'reported_errors':['FETCH'],'raw':'SECRET'}
    records={i:copy.deepcopy(failed) for i in range(1000)}
    assert SETUP.failed_download_summaries(records)==[[i,100,['FETCH']] for i in range(4)]
    assert SETUP.failed_download_summaries({'SECRET':failed,-1:failed,128:failed})==[]
    records={0:{**failed,'settlement':'unknown'},1:{**failed,'outcome':'passed'}}
    assert SETUP.failed_download_summaries(records)==[]


@pytest.mark.parametrize('maximal', [False, True])
@pytest.mark.parametrize('job_id', ['ontology-explorer', 'unrun-brain-gateway'])
def test_fixed_download_summary_reaches_bounded_semantic_infrastructure_without_raw_body(monkeypatch,maximal,job_id):
    from scripts import run_ci_pack as PACK
    events=runtime(monkeypatch)
    reported = list(SETUP.sanitize_reported_errors(['PERMISSION','SELECTION','AUTH','MIRROR_LIST','HASH','FETCH','METHOD'])) if maximal else ['PERMISSION','FETCH']
    indices = range(124,128) if maximal else [4]
    def acquire(plan,backend,*,deadline):
        for index in indices:
            backend.records[index]={'mode':'download','outcome':'failed','settlement':'settled','returncode':100,
                                    'reported_errors':reported,'raw':'SECRET http://private.invalid','child_pid':'SECRET'}
        return AcquisitionResult('failed','settled',(),(),'never_started','NATIVE_DOWNLOAD_FAILED')
    monkeypatch.setattr(SETUP,'acquire_and_install',acquire)
    retained=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=None)
    monkeypatch.setattr(SETUP,'run_native_setup',lambda **kwargs:retained)
    monkeypatch.setattr(PACK,'_restore_workspace',lambda *a:None)
    monkeypatch.setattr(PACK,'_prepare_provided_actions',lambda *a,**k:None)
    monkeypatch.setattr(PACK,'_browser_dependency_diagnostic_commands',lambda:())
    monkeypatch.setattr(PACK,'_stream_command',lambda *a,**k:pytest.fail('no semantic assertion after dependency failure'))
    # Both explicitly admitted owners preserve the same bounded failure evidence.
    job=PACK.LegacyJob(job_id,{'if':PACK.DISABLED_IF,'runs-on':'ubuntu-latest','timeout-minutes':15 if job_id=='unrun-brain-gateway' else 10,'steps':[
        {'name':'browser','phase':'browser_setup','acquisition':'native_parallel','timeout-minutes':10,'run':'python -m playwright install --with-deps chromium'},
        {'name':'assertion','run':'must not execute'}]},0,1)
    result=PACK._run_job(job,base_ref='main',head_ref='',command_env={})
    assert result.infrastructure['outcome']=='dependency_failed'
    assert result.timeout_settlement is None and result.steps[0]['outcome']=='infrastructure_blocked'
    raw=result.infrastructure['detail'];assert len(raw.encode())<=1024
    inner=json.loads(raw)
    assert inner['outcome']=='failed' and inner['returncode']==1
    expected=json.dumps([[index,100,reported] for index in indices],separators=(',',':'))
    assert 'downloads[index,returncode,reported_errors]='+expected in inner['detail']
    assert 'SECRET' not in raw and 'private.invalid' not in raw
    assert 'cleanup' not in [event[0] for event in events]


def actual_completion_backend(monkeypatch, *, diagnostic=None):
    from scripts.ci_apt_cold_acquisition import ChildResult,AcquisitionResult
    backend=SETUP.NativeAptBackend('/tmp/ci-apt-fixture',{},SimpleNamespace(transaction=('bound',)))
    backend.records={0:{'mode':'download','index':0,'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':diagnostic or ['FETCH']}}
    attempt=AcquisitionResult('failed','settled',(),(),'never_started','NATIVE_DOWNLOAD_FAILED',((0,'failed','settled'),))
    monkeypatch.setattr(SETUP.time,'monotonic',lambda:100)
    return backend,attempt


def test_native_owner_completion_uses_original_bound_attempt_same_deadline_and_keeps_staging(monkeypatch):
    backend,attempt=actual_completion_backend(monkeypatch);calls=[]
    monkeypatch.setattr(backend,'stage',lambda mode,deadline:calls.append((mode,deadline)) or {'outcome':'passed','settlement':'settled'})
    result=backend.complete_native_transaction(('bound',),attempt,600)
    assert result.outcome=='passed' and result.settlement=='settled' and calls==[('complete',600)]
    assert backend.records[0]['outcome']=='failed'
    backend.cleanup_success();assert calls==[('complete',600)]


@pytest.mark.parametrize('fault',['AUTH','HASH','PERMISSION','METHOD','MIRROR_LIST','UNCLASSIFIED','mixed','wrong-plan','unknown','pending','installed','deadline'])
def test_native_owner_cannot_promote_diagnostics_or_unknown_into_completion(monkeypatch,fault):
    from dataclasses import replace
    backend,attempt=actual_completion_backend(monkeypatch)
    if fault in {'AUTH','HASH','PERMISSION','METHOD','MIRROR_LIST','UNCLASSIFIED'}:backend.records[0]['reported_errors']=[fault]
    if fault=='mixed':backend.records[0]['reported_errors']=['FETCH','AUTH']
    if fault=='unknown':attempt=replace(attempt,settlement='unknown')
    if fault=='pending':attempt=replace(attempt,pending=(0,))
    if fault=='installed':attempt=replace(attempt,installation='passed')
    if fault=='deadline':monkeypatch.setattr(SETUP.time,'monotonic',lambda:600)
    monkeypatch.setattr(backend,'stage',lambda *a:pytest.fail('no continuation'))
    assert backend.complete_native_transaction(('wrong',) if fault=='wrong-plan' else ('bound',),attempt,600) is None


def test_successful_browser_after_native_completion_retains_original_failure_in_owner_result(monkeypatch):
    from scripts.ci_apt_cold_acquisition import ChildResult
    events=runtime(monkeypatch)
    def acquire(plan,backend,*,deadline):
        backend.records[0]={'mode':'download','index':0,'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['FETCH']}
        return AcquisitionResult('passed','settled',(0,),(),'passed','NATIVE_TRANSACTION_COMPLETE',((0,'failed','settled'),),'NATIVE_DOWNLOAD_FAILED',ChildResult('passed','settled'))
    monkeypatch.setattr(SETUP,'acquire_and_install',acquire)
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=lambda *a,**k:observed())
    assert result['outcome']=='passed'
    assert 'initial_download_failure=NATIVE_DOWNLOAD_FAILED' in result['detail'] and 'completion=passed/settled' in result['detail']
    assert 'original_downloads=[[0,100,["FETCH"]]]' in result['detail'] and 'retained /tmp/ci-apt-fixture' in result['detail']
    assert 'cleanup' not in [e[0] for e in events]


def test_post_completion_browser_exception_preserves_applied_state_and_original_attempt(monkeypatch):
    from scripts.ci_apt_cold_acquisition import ChildResult
    events=runtime(monkeypatch)
    def acquire(plan,backend,*,deadline):
        backend.records[0]={'mode':'download','index':0,'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['FETCH']}
        return AcquisitionResult('passed','settled',(0,),(),'passed','NATIVE_TRANSACTION_COMPLETE',((0,'failed','settled'),),'NATIVE_DOWNLOAD_FAILED',ChildResult('passed','settled'))
    monkeypatch.setattr(SETUP,'acquire_and_install',acquire)
    def browser(*a,**k):raise OSError('unknown browser response')
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['timeout_settlement']=='unknown'
    assert 'installation=passed' in result['detail'] and 'initial_download_failure=NATIVE_DOWNLOAD_FAILED' in result['detail']
    assert 'completion=passed/settled' in result['detail'] and 'original_downloads=[[0,100,["FETCH"]]]' in result['detail']
    assert 'cleanup' not in [e[0] for e in events]
