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


# --- P12.T11.S14 diagnostic phase-attribution cases (adapter-owned sink only) ---

class TimingSink:
    """Test-owned diagnostic sink: records writes or fails on demand."""
    def __init__(self, fail=False): self.lines=[]; self.fail=fail
    def write(self, text):
        if self.fail: raise RuntimeError('sink unavailable')
        self.lines.append(text); return len(text)
    def flush(self):
        if self.fail: raise RuntimeError('sink unavailable')
    def records(self):
        return [json.loads(line[len(SETUP.TIMING_PREFIX):]) for line in self.lines if line.startswith(SETUP.TIMING_PREFIX)]
    def evidence_records(self):
        prefix = 'CI_NATIVE_ACQUISITION_EVIDENCE='
        return [json.loads(line[len(prefix):]) for line in self.lines if line.startswith(prefix)]

VALID_ROW = {'package':'libx11-6','version':'2:1.8.7-1build1','package_architecture':'amd64',
             'archive_architecture':'amd64','filename':'libx11-6_2%3a1.8.7-1build1_amd64.deb',
             'size':262144,'sha256':'a'*64,
             'uri':'https://archive.ubuntu.com/ubuntu/pool/main/libx/libx11/libx11-6_2%3a1.8.7-1build1_amd64.deb'}

def timing_runtime(monkeypatch, *, sink=None, archive_rows=(), resolve_result=None, raise_mode=None):
    """Mocked runtime driving the REAL NativeAptBackend.stage diagnostic path.

    The fake nanosecond clock only advances inside original operation seams, so
    each emitted phase duration is exact; original deadline math stays on
    SETUP.time.monotonic and is mocked independently.
    """
    monkeypatch.setattr(SETUP.time,'monotonic',lambda:100)
    monkeypatch.setattr(SETUP.shutil,'which',lambda *_a,**_k:'/isolated/bin/python')
    monkeypatch.setattr(SETUP.platform,'freedesktop_os_release',lambda:{'ID':'ubuntu','VERSION_ID':'24.04'})
    monkeypatch.setattr(SETUP.platform,'machine',lambda:'x86_64')
    source = {'observed_version':'1.64.1','driver_version':'1.64.0-beta-1791568591000',
              'input_sha256':{'driver_bundle':QUALIFIED_DRIVER}}
    events=[]; holder={'ns':1000000000}
    monkeypatch.setattr(SETUP,'_diag_now',lambda:holder['ns'])
    def observe(argv, **kwargs):
        if argv[0]=='sudo':
            mode=argv[-2]; events.append((mode,kwargs['deadline']))
            holder['ns'] += {'update':50,'resolve':60,'install':70,'cleanup':20}.get(mode,10)*1000000
            if mode==raise_mode:
                raise SETUP.NativeUnknown('original retained native operation',4242,'timed_out')
            if mode=='resolve' and resolve_result is not None:
                return resolve_result
            body={'mode':mode,'outcome':'passed','settlement':'settled'}
            if mode=='resolve': body['archives']=list(archive_rows)
            return 0, SETUP.RESULT_PREFIX+json.dumps(body).encode()+b'\n'
        events.append(('capture-observe',kwargs['deadline']))
        holder['ns'] += 100000000
        return 0, b'CI_BROWSER_DEPENDENCY_INPUTS='+json.dumps(source).encode()+b'\n'
    monkeypatch.setattr(SETUP,'observe_command',observe)
    def bootstrap(packet, env, deadline):
        events.append(('bootstrap',deadline,env)); holder['ns'] += 200000000
        return '/tmp/ci-apt-fixture'
    monkeypatch.setattr(SETUP,'bootstrap_root',bootstrap)
    def acquire(plan, backend, *, deadline):
        from scripts.ci_apt_cold_acquisition import ChildResult
        events.append(('acquire',deadline,plan.transaction)); holder['ns'] += 10000000
        install=backend.install_frozen(plan.transaction, deadline)
        assert isinstance(install,ChildResult) and install.outcome=='passed' and install.settlement=='settled'
        return AcquisitionResult('passed','settled',(),(),'passed','NATIVE_TRANSACTION_COMPLETE')
    monkeypatch.setattr(SETUP,'acquire_and_install',acquire)
    sink = sink if sink is not None else TimingSink()
    monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    def browser(command, **kwargs):
        events.append(('browser',command,kwargs)); holder['ns'] += 300000000
        return observed()
    return events, holder, sink, browser

def phase_lines(records):
    return [r for r in records if 'elapsed_ms' in r]

def test_fake_nanosecond_clock_gives_exact_phase_durations_without_changing_original_calls(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch)
    env={'PATH':'/isolated/bin'}
    result=SETUP.run_native_setup(deadline=600,command_env=env,expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed' and result['timeout_settlement'] is None
    assert [e[0] for e in events]==['capture-observe','bootstrap','update','resolve','acquire','install','browser','cleanup']
    assert events[-2]==('browser','python -m playwright install chromium',{'env':env,'timeout_seconds':500})
    assert [e[1] for e in events if e[0] in {'update','resolve','install','cleanup'}]==[600]*4
    assert [e[1] for e in events if e[0] in {'capture-observe','bootstrap'}]==[600,600]
    assert events[4][2]==()
    durations={'capture':100,'bootstrap':200,'update':50,'resolve':60,'install':70,'cleanup':20,'browser':300}
    lines=phase_lines(sink.records())
    assert [r['phase'] for r in lines]==['capture','bootstrap','update','resolve','install','browser','cleanup']
    for line in lines:
        assert line['elapsed_ms']==durations[line['phase']]
        assert line['observation']=='returned'
    assert sink.records()[4]=={'phase':'inventory','archive_count':0,'archive_bytes':0}
    assert all(r['outcome']=='passed' for r in lines)
    assert all(r['settlement']=='settled' for r in lines if r['phase'] in {'update','resolve','install','cleanup'})

def test_validated_inventory_emits_exact_count_and_bytes_with_no_payload_sentinels(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch,archive_rows=[VALID_ROW])
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed'
    inventory=[r for r in sink.records() if r['phase']=='inventory']
    assert inventory==[{'phase':'inventory','archive_count':1,'archive_bytes':262144}]
    text=''.join(line for line in sink.lines if line.startswith(SETUP.TIMING_PREFIX))
    for sentinel in ('archive.ubuntu.com','libx11','%3a','.deb','a'*64,'sudo','/tmp/ci-apt','SECRET','https','ubuntu','playwright','chromium'):
        assert sentinel not in text
    assert {r['phase'] for r in sink.records()} <= set(SETUP.TIMING_PHASES)|{'inventory'}
    assert all(type(r['archive_index']) is int for r in phase_lines(sink.records()) if r['phase']=='download')

def test_failed_resolution_settles_without_inventory_or_downstream_phases(monkeypatch):
    failed=(1,SETUP.RESULT_PREFIX+json.dumps({'mode':'resolve','outcome':'failed','settlement':'settled'}).encode()+b'\n')
    events,holder,sink,browser=timing_runtime(monkeypatch,resolve_result=failed)
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='failed' and result['timeout_settlement']=='unknown'
    assert result['detail'].startswith('native cold acquisition unproven') and 'child_pid=None' in result['detail']
    records=sink.records()
    assert [r['phase'] for r in records]==['capture','bootstrap','update','resolve']
    assert records[-1]['observation']=='returned' and records[-1]['outcome']=='failed'
    assert records[-1]['settlement']=='settled'
    assert all(r['phase']!='inventory' for r in records)

def test_malformed_archive_resolution_never_claims_inventory(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch,archive_rows=[{**VALID_ROW,'sha256':'short'}])
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='failed' and 'ARCHIVE_HASH' in result['detail']
    assert [r['phase'] for r in sink.records()]==['capture','bootstrap','update','resolve']

def _fake_download_child(monkeypatch, pipes, launched):
    def fake_popen(argv, **kwargs):
        index=int(argv[-1]); launched.append(index)
        readfd,writefd=os.pipe()
        pipes[index]={'write':writefd,
                      'payload':SETUP.RESULT_PREFIX+json.dumps({'mode':'download','index':index,'outcome':'passed','settlement':'settled'}).encode()+b'\n'}
        return SimpleNamespace(pid=7000+index, stdout=os.fdopen(readfd,'rb',buffering=0),
                               poll=lambda:0, wait=lambda timeout=None:0)
    monkeypatch.setattr(SETUP.subprocess,'Popen',fake_popen)

def test_two_concurrent_downloads_in_separate_collects_emit_unique_index_observations(monkeypatch):
    sink=TimingSink(); monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    holder={'ns':5000000000}; monkeypatch.setattr(SETUP,'_diag_now',lambda:holder['ns'])
    from scripts.ci_apt_cold_acquisition import DownloadPlan, make_download_plan
    second={**VALID_ROW,'package':'libxcb1','version':'1:1.15.2-2build1','filename':'libxcb1_1%3a1.15.2-2build1_amd64.deb',
            'sha256':'b'*64,'uri':'https://archive.ubuntu.com/ubuntu/pool/main/libx/libxcb/libxcb1_1%3a1.15.2-2build1_amd64.deb'}
    plan=make_download_plan((SETUP.Archive(**VALID_ROW),SETUP.Archive(**second)))
    assert DownloadPlan.__dataclass_fields__['concurrency'].default==4 and plan.concurrency==4
    backend=SETUP.NativeAptBackend('/tmp/ci-apt-fixture',{},plan)
    monkeypatch.setattr(SETUP.time,'monotonic',lambda:100)  # launch pre-deadline check only
    pipes={}; launched=[]
    _fake_download_child(monkeypatch,pipes,launched)
    pending0=backend.launch(0,('argv',),10000)
    holder['ns']+=250000000  # launch-to-observation wall time for index 0
    pending1=backend.launch(1,('argv',),10000)
    os.write(pipes[0]['write'],pipes[0]['payload']); os.close(pipes[0]['write'])
    first=backend.collect({0:pending0,1:pending1},10000)
    assert set(first)=={0} and first[0].outcome=='passed' and first[0].settlement=='settled'
    holder['ns']+=350000000  # second launch-to-observation window for index 1
    os.write(pipes[1]['write'],pipes[1]['payload']); os.close(pipes[1]['write'])
    second_observation=backend.collect({1:pending1},10000)
    assert set(second_observation)=={1} and second_observation[1].outcome=='passed'
    assert launched==[0,1]  # no duplicate or dependent relaunch
    downloads=[r for r in sink.records() if r['phase']=='download']
    assert [r['archive_index'] for r in downloads]==[0,1]
    assert [r['elapsed_ms'] for r in downloads]==[250,350]
    assert all(r['observation']=='returned' and r['outcome']=='passed' and r['settlement']=='settled' for r in downloads)
    assert type(backend.records[0]['index']) is int and backend.records[1]['index']==1

def test_deadline_exhaustion_reports_unobserved_downloads_without_extra_wait(monkeypatch):
    sink=TimingSink(); monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    monkeypatch.setattr(SETUP.time,'monotonic',lambda:600)
    holder={'ns':5400000000}; monkeypatch.setattr(SETUP,'_diag_now',lambda:holder['ns'])
    selects=[]
    class FakeSelector:
        def __enter__(self):return self
        def __exit__(self,*a):return False
        def register(self,*a,**k):selects.append(('register',a))
        def unregister(self,*a):pass
        def select(self,*a,**k):selects.append(('select',a));return []
        def close(self):pass
    monkeypatch.setattr(SETUP.selectors,'DefaultSelector',FakeSelector)
    backend=SETUP.NativeAptBackend('/tmp/ci-apt-fixture',{},None)
    backend.download_timing[3]={'started_ns':5000000000,'emitted':False}
    child=SETUP.Pending(SimpleNamespace(pid=1,stdout=SimpleNamespace(close=lambda:None),poll=lambda:None,
                                        wait=lambda *a,**k:pytest.fail('no extra wait')),bytearray())
    results=backend.collect({3:child},599)
    assert results[3].outcome=='timed_out' and results[3].settlement=='unknown'
    assert not any(call[0]=='select' for call in selects)  # no timing grace or added wait
    line=[r for r in sink.records() if r['phase']=='download'][0]
    assert line['archive_index']==3 and line['observation']=='unobserved'
    assert line['outcome']=='timed_out' and line['settlement']=='unknown' and line['elapsed_ms']==400

def test_native_unknown_preserves_result_and_marks_raised_phase(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch,raise_mode='update')
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='timed_out' and result['timeout_settlement']=='unknown'
    assert 'child_pid=4242' in result['detail'] and "handles={'update': 4242}" in result['detail']
    records=sink.records()
    assert [r['phase'] for r in records]==['capture','bootstrap','update']
    assert records[-1]['observation']=='raised' and records[-1]['outcome']=='timed_out'
    assert records[-1]['settlement'] is None and records[-1]['elapsed_ms'] is not None

def test_browser_exception_preserves_unknown_and_emits_raised_browser_phase(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch)
    def broken(command,**kwargs):raise OSError('unknown browser response')
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=broken)
    assert result['outcome']=='failed' and result['timeout_settlement']=='unknown'
    records=sink.records()
    assert records[-1]['phase']=='browser' and records[-1]['observation']=='raised'
    assert records[-1]['outcome'] is None and records[-1]['settlement'] is None
    assert all(r['phase']!='cleanup' for r in records)

def test_early_refusal_or_elapsed_deadline_emits_no_diagnostics_and_no_launch(monkeypatch):
    sink=TimingSink(); monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    monkeypatch.setattr(SETUP.time,'monotonic',lambda:100)
    monkeypatch.setattr(SETUP.subprocess,'Popen',lambda *a,**k:pytest.fail('refusal before effects'))
    result=SETUP.run_native_setup(deadline=600,command_env={'PLAYWRIGHT_HOST_PLATFORM_OVERRIDE':'foreign'},
                                  expected_sources=sources(),browser_stream=None)
    assert result['outcome']=='failed' and 'DEPENDENCY_PLATFORM_OVERRIDE_UNQUALIFIED' in result['detail']
    result=SETUP.run_native_setup(deadline=100,command_env={},expected_sources=sources(),browser_stream=None)
    assert result['outcome']=='failed' and result['timeout_settlement'] is None
    assert sink.lines==[]

def test_diagnostic_sink_failure_cannot_mask_original_result_or_call_order(monkeypatch):
    failing=TimingSink(fail=True)
    events,holder,sink,browser=timing_runtime(monkeypatch,sink=failing)
    env={'PATH':'/isolated/bin'}
    result=SETUP.run_native_setup(deadline=600,command_env=env,expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed' and result['timeout_settlement'] is None
    assert failing.lines==[]
    assert [e[0] for e in events]==['capture-observe','bootstrap','update','resolve','acquire','install','browser','cleanup']
    assert events[-2][2]=={'env':env,'timeout_seconds':500}

def test_invalid_diagnostic_clock_yields_null_elapsed_without_changing_results(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch)
    monkeypatch.setattr(SETUP,'_diag_now',lambda:'bogus')
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed'
    assert all(r['elapsed_ms'] is None for r in phase_lines(sink.records()))
    def broken_clock():raise RuntimeError('clock unavailable')
    monkeypatch.setattr(SETUP,'_diag_now',broken_clock)
    before=len(sink.lines)
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed'
    assert all(r['elapsed_ms'] is None for r in phase_lines(sink.records())[before:] if 'elapsed_ms' in r)

def test_phase_timing_wrapper_propagates_original_exception_identity(monkeypatch):
    sink=TimingSink(); monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    original=ValueError('unique-original-identity')
    with pytest.raises(ValueError) as caught:
        with SETUP._phase_timing('update'):
            raise original
    assert caught.value is original
    line=sink.records()[0]
    assert line['phase']=='update' and line['observation']=='raised'
    assert line['outcome'] is None and line['settlement'] is None

def test_child_result_channel_stays_exact_single_prefixed_line(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch)
    valid=SETUP.RESULT_PREFIX+json.dumps({'mode':'update','outcome':'passed','settlement':'settled'}).encode()+b'\n'
    assert valid.count(SETUP.RESULT_PREFIX)==1
    assert SETUP.parsed_result(0,valid,mode='update')['outcome']=='passed'
    with pytest.raises(SETUP.NativeUnknown):SETUP.parsed_result(0,valid+SETUP.RESULT_PREFIX+b'{}\n',mode='update')
    with pytest.raises(SETUP.NativeUnknown):SETUP.parsed_result(0,SETUP.TIMING_PREFIX.encode()+b'{"phase":"update"}\\n',mode='update')
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed'
    assert all(line.startswith((SETUP.TIMING_PREFIX, SETUP.EVIDENCE_PREFIX)) and 'CI_APT_NATIVE_RESULT' not in line for line in sink.lines)
    assert all(record['phase'] in set(SETUP.TIMING_PHASES)|{'inventory'} for record in sink.records())
    assert all(record['kind'] in {'inventory', 'download'} for record in sink.evidence_records())
    with pytest.raises(SETUP.NativeUnknown):
        SETUP.parsed_result(0, SETUP.EVIDENCE_PREFIX.encode()+b'{}\n', mode='update')

def test_source_binding_caps_and_dynamic_adapter_digest_binding_unchanged():
    expected=sources()
    assert SETUP.ROOT_FILES==('ci_apt_cold_acquisition.py','ci_apt_native_plan.py','ci_apt_native_stage.py','ci_apt_transaction_contract.py')
    assert SETUP.BOUND_FILES==(*SETUP.ROOT_FILES,'ci_browser_native_setup.py','ci_browser_dependency_capture.py','ci_browser_dependency_inputs.py')
    packet=json.loads(SETUP.source_packet(expected))
    assert set(packet['files'])==set(SETUP.ROOT_FILES)
    changed={**expected,'ci_browser_native_setup.py':'0'*64}
    with pytest.raises(ValueError,match='HELPER_SOURCE_CHANGED'):SETUP.source_packet(changed)
    from scripts.ci_apt_cold_acquisition import DownloadPlan
    from scripts.ci_apt_native_stage import LIMIT as STAGE_LIMIT
    assert DownloadPlan.__dataclass_fields__['concurrency'].default==4
    assert STAGE_LIMIT==1024*1024


def test_diagnostic_metadata_failure_preserves_original_exception_identity(monkeypatch):
    class OriginalError(Exception):
        @property
        def outcome(self):
            raise RuntimeError('diagnostic metadata unavailable')
    original = OriginalError('original operation failure')
    with pytest.raises(OriginalError) as caught:
        with SETUP._phase_timing('update'):
            raise original
    assert caught.value is original


def test_download_timing_includes_original_process_launch_overhead(monkeypatch):
    sink = TimingSink()
    monkeypatch.setattr(SETUP, '_timing_sink', lambda: sink)
    ticks = {'ns': 1_000_000_000}
    monkeypatch.setattr(SETUP, '_diag_now', lambda: ticks['ns'])
    monkeypatch.setattr(SETUP.time, 'monotonic', lambda: 100)
    def launch(*args, **kwargs):
        ticks['ns'] += 125_000_000
        return SimpleNamespace(pid=1234)
    monkeypatch.setattr(SETUP.subprocess, 'Popen', launch)
    backend = SETUP.NativeAptBackend('/tmp/ci-apt-fixture', {},
                                    SETUP.make_download_plan((SETUP.Archive(**VALID_ROW),)))
    child = backend.launch(0, ('unchanged',), 600)
    assert child.process.pid == 1234
    ticks['ns'] += 75_000_000
    backend._finish_download(0, observation='returned', outcome='passed', settlement='settled')
    assert sink.records()[0]['elapsed_ms'] == 200


def test_timing_schema_never_emits_foreign_phase_or_unbounded_archive_index(monkeypatch):
    sink = TimingSink()
    monkeypatch.setattr(SETUP, '_timing_sink', lambda: sink)
    SETUP._emit_phase('SECRET https://private.invalid')
    for index in (-1, 128, True, 'SECRET'):
        SETUP._emit_phase('download', archive_index=index)
    assert sink.records() == []
    SETUP._emit_phase('update', observation='returned', outcome='passed', settlement='settled')
    assert sink.records() == [{'phase':'update', 'observation':'returned', 'outcome':'passed',
                               'settlement':'settled', 'elapsed_ms':None}]


@pytest.mark.parametrize('start,end,expected', [
    (2_000_000, 1_000_000, None), (None, 1_000_000, None),
    (True, 1_000_000, None), ('invalid', 1_000_000, None),
    (1_000_000, 2_500_000, 1),
])
def test_diagnostic_elapsed_refuses_backward_or_invalid_clock(start, end, expected):
    assert SETUP._diag_elapsed_ms(start, end) == expected


def test_raised_exception_metadata_cannot_claim_success(monkeypatch):
    sink = TimingSink()
    monkeypatch.setattr(SETUP, '_timing_sink', lambda: sink)
    original = RuntimeError('original failed operation')
    original.outcome = 'passed'
    with pytest.raises(RuntimeError) as caught:
        with SETUP._phase_timing('update'):
            raise original
    assert caught.value is original
    line = sink.records()[0]
    assert line['observation'] == 'raised'
    assert line['outcome'] is None and line['settlement'] is None


# Safe original-input evidence is a separate outer diagnostic, never child state.
def evidence_plan(count=9):
    rows = []
    for index in range(count):
        name = f'font-fixture-{index}'
        rows.append(SETUP.Archive(name, '1.0', 'amd64', 'all', f'{name}_1.0_all.deb',
                                 index+1, hashlib.sha256(str(index).encode()).hexdigest(),
                                 f'https://archive.ubuntu.com/ubuntu/pool/main/f/{name}_1.0_all.deb'))
    return SETUP.make_download_plan(tuple(rows))


def test_complete_evidence_inventory_preserves_all_original_indices_and_exact_source_binding(monkeypatch):
    sink = TimingSink(); monkeypatch.setattr(SETUP, '_timing_sink', lambda:sink)
    plan = evidence_plan(); expected = sources()
    assert plan.schedule != tuple(range(9))
    digest = SETUP._emit_inventory_evidence(plan, expected)
    [record] = sink.evidence_records()
    assert record['kind'] == 'inventory' and record['helper_source_sha256'] == expected
    assert [r['index'] for r in record['archives']] == list(range(9))
    for index, row in enumerate(record['archives']):
        source = plan.transaction[index]
        assert row == {'index':index,'package':source.package,'version':source.version,
                       'package_architecture':source.package_architecture,'archive_architecture':source.archive_architecture,
                       'size':source.size,'sha256':source.sha256}
    assert digest == record['inventory_sha256'] == hashlib.sha256(json.dumps(record['archives'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    raw = ''.join(sink.lines)
    assert not any(value in raw for value in ('https:', 'archive.ubuntu.com', '.deb', 'uri', 'filename', 'sudo'))


@pytest.mark.parametrize('fault', ['hash','name','version','uri-secret','size','count','source-name','source-hash','source-extra','source-value'])
def test_invalid_or_secret_bearing_inventory_metadata_emits_nothing(monkeypatch, fault):
    from dataclasses import replace
    sink=TimingSink(); monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    plan=evidence_plan(); expected=sources()
    changes={'hash':{'sha256':'SECRET'},'name':{'package':'SECRET:credential'},
             'version':{'version':'1.0\nSECRET'},'uri-secret':{'uri':'https://SECRET:credential@private.invalid/a.deb'},
             'size':{'size':True}}
    if fault in changes:
        rows=(replace(plan.transaction[0],**changes[fault]),*plan.transaction[1:])
        plan=replace(plan,transaction=rows)
    elif fault=='count':plan=replace(plan,transaction=plan.transaction*15)
    elif fault=='source-name':expected={'SECRET': 'a'*64}
    elif fault=='source-hash':expected[SETUP.BOUND_FILES[0]]='SECRET https://private.invalid'
    elif fault=='source-extra':expected['SECRET']='a'*64
    else:expected[SETUP.BOUND_FILES[0]]={'raw':'SECRET:credential'}
    assert SETUP._emit_inventory_evidence(plan,expected) is None
    assert sink.lines == []


@pytest.mark.parametrize('code,errors,expected_code,expected_errors', [
    (100,['PERMISSION','FETCH'],100,['PERMISSION','FETCH']),
    (100,['FETCH'],100,['FETCH']),
    ('SECRET',['SECRET'],None,['UNCLASSIFIED']),
    (True,{'secret':'credential'},None,['UNCLASSIFIED']),
    (0,['AUTH','AUTH'],None,['UNCLASSIFIED']),
    (100000,['UNCLASSIFIED','AUTH'],None,['UNCLASSIFIED']),
])
def test_download_evidence_only_retains_observed_finite_fields_not_raw_or_http_guesses(monkeypatch,code,errors,expected_code,expected_errors):
    sink=TimingSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    row={'mode':'download','index':3,'outcome':'failed','settlement':'settled','returncode':code,
         'reported_errors':errors,'http_status':403,'raw':'SECRET https://private.invalid user:credential',
         'child_pid':'SECRET','argv':['sudo','SECRET'],'uri':'https://SECRET:credential@private.invalid'}
    SETUP._emit_download_evidence(3,{3:row},'a'*64,evidence_plan())
    assert sink.evidence_records()==[{'kind':'download','inventory_sha256':'a'*64,'index':3,'outcome':'failed',
                                      'settlement':'settled','returncode':expected_code,'reported_errors':expected_errors,'http_status':'unknown'}]
    raw=''.join(sink.lines)
    assert not any(value in raw for value in ('SECRET','credential','private.invalid','sudo','403'))


@pytest.mark.parametrize('changes', [{'index':True},{'index':4},{'mode':'SECRET'},{'outcome':'SECRET'},{'settlement':'SECRET'}])
def test_unqualified_download_records_cannot_claim_an_observed_result(monkeypatch,changes):
    sink=TimingSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    row={'mode':'download','index':3,'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['FETCH']}
    SETUP._emit_download_evidence(3,{3:{**row,**changes}},'a'*64,evidence_plan())
    assert sink.lines==[]


def test_unknown_native_result_does_not_invent_returncode_error_category_or_http_status(monkeypatch):
    sink=TimingSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    row={'mode':'download','index':0,'outcome':'timed_out','settlement':'unknown','child_pid':4242}
    SETUP._emit_download_evidence(0,{0:row},'a'*64,evidence_plan())
    [record]=sink.evidence_records()
    assert record['outcome']=='timed_out' and record['settlement']=='unknown'
    assert record['returncode'] is None and record['reported_errors'] is None and record['http_status']=='unknown'
    assert 'child_pid' not in record


def test_interrupted_later_child_preserves_original_inventory_and_prior_return_without_false_settlement(monkeypatch):
    sink=TimingSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    monkeypatch.setattr(SETUP.time,'monotonic',lambda:100)
    plan=evidence_plan(2);backend=SETUP.NativeAptBackend('/tmp/ci-apt-fixture',{},plan)
    backend.evidence_inventory_sha256=SETUP._emit_inventory_evidence(plan,sources())
    pipes={};launched=[];_fake_download_child(monkeypatch,pipes,launched)
    first=backend.launch(0,('original',),600);second=backend.launch(1,('original',),600)
    os.write(pipes[0]['write'],pipes[0]['payload']);os.close(pipes[0]['write'])
    assert backend.collect({0:first,1:second},600)[0].settlement=='settled'
    retained=list(sink.evidence_records())
    assert [r['kind'] for r in retained]==['inventory','download'] and retained[1]['index']==0
    os.write(pipes[1]['write'],b'PARTIAL SECRET https://private.invalid\n');os.close(pipes[1]['write'])
    with pytest.raises(SETUP.NativeUnknown):backend.collect({1:second},600)
    assert sink.evidence_records()==retained
    assert backend.records[0]['settlement']=='settled' and 1 not in backend.records
    assert launched==[0,1] and 'SECRET' not in ''.join(sink.lines)


def test_safe_evidence_sink_failure_and_clock_failure_do_not_change_original_flow(monkeypatch):
    events,holder,sink,browser=timing_runtime(monkeypatch,sink=TimingSink(fail=True),archive_rows=[VALID_ROW])
    monkeypatch.setattr(SETUP,'_diag_now',lambda:(_ for _ in ()).throw(RuntimeError('SECRET clock failure')))
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=sources(),browser_stream=browser)
    assert result['outcome']=='passed' and result['timeout_settlement'] is None
    assert [e[0] for e in events]==['capture-observe','bootstrap','update','resolve','acquire','install','browser','cleanup']
    assert all(e[1]==600 for e in events if e[0] in {'update','resolve','install','cleanup'})
    assert sink.lines==[]


@pytest.mark.parametrize('native_digest', ['b'*64,None,True,{'raw':'SECRET'},'SECRET https://private.invalid'])
def test_native_frozen_transaction_digest_is_observed_only_when_valid_and_never_reconstructed(monkeypatch,native_digest):
    sink=TimingSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    SETUP._emit_inventory_evidence(evidence_plan(),sources(),native_digest)
    [record]=sink.evidence_records()
    assert record['native_transaction_sha256']==('b'*64 if native_digest=='b'*64 else None)
    assert 'SECRET' not in ''.join(sink.lines)


def test_actual_setup_boundary_retains_full_inventory_and_original_failed_result_under_same_deadline(monkeypatch):
    plan=evidence_plan();expected=sources()
    events,holder,sink,browser=timing_runtime(monkeypatch,archive_rows=[row.__dict__ for row in plan.transaction])
    def acquire(original,backend,*,deadline):
        assert deadline==600 and original==plan
        backend.records[3]={'mode':'download','index':3,'outcome':'failed','settlement':'settled',
                            'returncode':100,'reported_errors':['PERMISSION','FETCH'],'raw':'SECRET'}
        backend.download_timing[3]={'started_ns':holder['ns'],'emitted':False}
        backend._finish_download(3,observation='returned',outcome='failed',settlement='settled')
        return AcquisitionResult('failed','settled',(),(),'never_started','NATIVE_DOWNLOAD_FAILED')
    monkeypatch.setattr(SETUP,'acquire_and_install',acquire)
    result=SETUP.run_native_setup(deadline=600,command_env={},expected_sources=expected,browser_stream=lambda *a,**k:pytest.fail('original failure cannot start browser'))
    assert result['outcome']=='failed' and result['timeout_settlement'] is None
    records=sink.evidence_records()
    assert len(records)==2, 'original full inventory and observed failed download must be retained'
    inventory,download=records
    assert len(inventory['archives'])==9 and inventory['helper_source_sha256']==expected
    assert inventory['native_transaction_sha256'] is None
    assert download['index']==3 and download['inventory_sha256']==inventory['inventory_sha256']
    assert download['reported_errors']==['PERMISSION','FETCH'] and download['http_status']=='unknown'
    assert [e[0] for e in events]==['capture-observe','bootstrap','update','resolve']
    assert all(e[1]==600 for e in events) and 'SECRET' not in ''.join(sink.lines)


@pytest.mark.parametrize('field', ['package','version','outcome','settlement'])
def test_evidence_disclosure_rejects_string_subclasses_with_forged_enum_comparison(monkeypatch,field):
    from dataclasses import replace
    class Forged(str):
        def __eq__(self,other):return True
        __hash__=str.__hash__
    sink=TimingSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    plan=evidence_plan()
    if field in {'package','version'}:
        plan=replace(plan,transaction=(replace(plan.transaction[0],**{field:Forged('SECRET')}),*plan.transaction[1:]))
        assert SETUP._emit_inventory_evidence(plan,sources()) is None
    else:
        row={'mode':'download','index':0,'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['FETCH']}
        SETUP._emit_download_evidence(0,{0:{**row,field:Forged('SECRET')}},'a'*64,plan)
    assert sink.lines==[]


def test_download_evidence_cannot_bind_a_foreign_index_to_a_smaller_original_inventory(monkeypatch):
    sink=TimingSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    row={'mode':'download','index':3,'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['FETCH']}
    SETUP._emit_download_evidence(3,{3:row},'a'*64,evidence_plan(2))
    assert sink.lines==[]


def test_interrupted_metadata_write_does_not_remove_prior_complete_evidence_or_change_result(monkeypatch):
    class InterruptedSink(TimingSink):
        def write(self,text):
            if self.lines:
                self.lines.append(text[:20])
                raise OSError('SECRET interrupted output')
            return super().write(text)
    sink=InterruptedSink();monkeypatch.setattr(SETUP,'_timing_sink',lambda:sink)
    plan=evidence_plan();digest=SETUP._emit_inventory_evidence(plan,sources())
    complete=sink.lines[0]
    row={'mode':'download','index':0,'outcome':'failed','settlement':'settled','returncode':100,'reported_errors':['FETCH']}
    assert SETUP._emit_download_evidence(0,{0:row},digest,plan) is None
    assert sink.lines[0]==complete and len(sink.lines)==2
    assert json.loads(complete[len(SETUP.EVIDENCE_PREFIX):])['kind']=='inventory'
    assert 'SECRET' not in ''.join(sink.lines)
    with pytest.raises(json.JSONDecodeError):json.loads(sink.lines[1])
