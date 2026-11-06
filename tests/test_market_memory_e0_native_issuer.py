"""Whole v3 fixed source owner path; explicit OS/install/domain fixtures only.

Peer profile2 is a composed service source candidate. No actual SSH/host/source/study,
M2 caller/admission/provider or protected receiver is observed by these tests.
"""
import base64
import copy
from hashlib import sha256
import io
import json
import os
import time
from pathlib import Path
import struct
import subprocess
import sys

import pytest

from tests.market_memory_native_peer_fixtures import native_peer_primitives, native_peer_capability

from engine.research_factory import market_memory_e0_native_issuer as issuer
from engine.research_factory import market_memory_e0_native_case as case
from tests.test_market_memory_e0_native_case import (
    native_world,records,INTENT,SOURCE_ROOT,inventory,retain,write,canonical,source_guard_snapshot,
)


@pytest.fixture
def protocol_world(monkeypatch,request):
    # Strengthened fixture install closure contains every actual entry module,
    # script/schema/dependency, not a source-verifier-success callback.
    monkeypatch.setattr(case,'_SOURCE_PATHS',issuer.FULL_SOURCE_PATHS)
    monkeypatch.setattr(issuer,'_platform',lambda:'linux')
    monkeypatch.setattr(issuer,'_uid',lambda:0)
    world=request.getfixturevalue('native_world')
    monkeypatch.setattr(issuer,'ROOT',world['installed_root'])
    return world


def request(action='qualify_current_case',**extra):
    return canonical({'schema':issuer.REQUEST,'action':action,'operation_id':'original-operation',
                      'intent':copy.deepcopy(INTENT),**extra})


def exchange(action='qualify_current_case',**extra):
    return json.loads(issuer.exchange(request(action,**extra)))


def response_schema(value):
    issuer._wire_schema(value,'response')
    assert value['verification']==issuer.FALSE_FLAGS
    assert value['retry_authorized'] is False and value['scientific_admission'] is False


def test_genuine_prepare_lost_response_original_recovery_and_result_audience(protocol_world,monkeypatch):
    world=protocol_world;before=inventory(world['store'].directory)
    source_before=source_guard_snapshot()
    assert world['installed_root']!=SOURCE_ROOT
    # Optional EXPLICIT test artifact destination; never an issuer input/path.
    sink_text=os.environ.get('MM_E0_NATIVE_VECTOR_SINK')
    sink=Path(sink_text).absolute() if sink_text else None
    if sink is not None:
        assert sink==sink.resolve() and not sink.is_relative_to(SOURCE_ROOT)
        assert not sink.exists() and sink.parent.is_dir()
        sink.mkdir(mode=0o700)
    counts={'verify_source':0,'peer_observe':0,'peer_require':0}
    def counted(function,key):
        def call(*args,**kwargs):
            counts[key]+=1
            return function(*args,**kwargs) # ORIGINAL current authority always runs.
        return call
    monkeypatch.setattr(issuer.owner,'_verify_source',counted(issuer.owner._verify_source,'verify_source'))
    monkeypatch.setattr(issuer.peer,'observe_current_broker_service',counted(issuer.peer.observe_current_broker_service,'peer_observe'))
    monkeypatch.setattr(issuer.peer,'require_current_broker_service',counted(issuer.peer.require_current_broker_service,'peer_require'))
    vectors=[]
    def actual(phase,action='qualify_current_case',**extra):
        raw_request=request(action,**extra);prior=counts.copy()
        wall=time.perf_counter();cpu=time.process_time()
        raw_response=issuer.exchange(raw_request) # Genuine production exchange.
        elapsed={'wall_seconds':time.perf_counter()-wall,'cpu_seconds':time.process_time()-cpu}
        value=json.loads(raw_response)
        assert canonical(value)==raw_response
        entry={'phase':phase,'action':action,'status':value['status'],**elapsed,
               'actual_calls':{k:counts[k]-prior[k] for k in counts},'payloads':{}}
        blobs={'request.json':raw_request,'response.json':raw_response,
               'request.frame':struct.pack('>I',len(raw_request))+raw_request,
               'response.frame':struct.pack('>I',len(raw_response))+raw_response}
        for suffix,body in blobs.items():
            name=phase+'.'+suffix
            entry['payloads'][suffix]={'path':name,'sha256':sha256(body).hexdigest(),'bytes':len(body)}
            if sink is not None:(sink/name).write_bytes(body)
        vectors.append(entry)
        return value
    with monkeypatch.context() as scoped:
        def forbidden(*a,**k):pytest.fail('qualification touched source acquisition/accounting')
        scoped.setattr(case,'_build_case_input',forbidden)
        for name in ('snapshot','reserve','finish','read_completed','_locked','_load'):
            scoped.setattr(case.ReservationStore,name,forbidden)
        qualified=actual('01-qualification');response_schema(qualified)
        assert qualified['status']=='CURRENT_CASE_QUALIFIED'
        assert not {'input','locator','operation_state','original_recipient','condition'} & qualified.keys()
    assert inventory(world['store'].directory)==before
    absent=actual('02-absent','read_original_case');response_schema(absent)
    assert absent['operation_state']=='ABSENT' and 'input' not in absent
    assert inventory(world['store'].directory)==before
    prepared=actual('03-prepare','prepare_case');response_schema(prepared)
    assert prepared['status']=='CASE_PREPARED'
    input_bytes=base64.b64decode(prepared['input']['body'],validate=True)
    assert sha256(input_bytes).hexdigest()==prepared['input']['sha256']
    assert len(case.packet.extract_selected_citations(input_bytes,
        input_sha256=prepared['input']['sha256']))==10
    assert world['store'].snapshot()['consumed_looks']==1
    # Caller discards/lost this response: same-original read is the sole recovery.
    original_input=prepared['input'];original_locator=prepared['locator'];del prepared
    after=inventory(world['store'].directory)
    with monkeypatch.context() as scoped:
        def forbidden(*a,**k):pytest.fail('COMPLETE/recovery rebuilt or reserved sources')
        scoped.setattr(case,'_build_case_input',forbidden)
        scoped.setattr(case.ReservationStore,'reserve',forbidden)
        scoped.setattr(case.ReservationStore,'finish',forbidden)
        recovered=actual('04-complete-lost-response','read_original_case');response_schema(recovered)
        assert recovered['operation_state']=='COMPLETE' and recovered['input']==original_input
        current=actual('05-current-input','current_input',locator=original_locator);response_schema(current)
        assert current['status']=='INPUT_CURRENT' and current['input']==original_input
        report=b'explicit synthetic untrusted original child result'
        result_ref={'attempt_id':'original-synthetic-attempt','input_sha256':original_input['sha256'],
            'result_sha256':sha256(report).hexdigest(),'result_bytes':len(report)}
        authorized=actual('06-result-authorization','authorize_result_disclosure',locator=original_locator,result_ref=result_ref)
        response_schema(authorized);assert authorized['status']=='RESULT_DISCLOSURE_CURRENT'
        fact=authorized['authorization']['original_recipient']
        assert fact=={'schema':'research_factory.market_memory_e0_original_recipient.v3',
            'recipient_kind':'native_broker_service','principal_ref':world['recipient']['service_ref'],
            'ssh_key_fingerprint':world['service']['ssh_key_fingerprint'],
            'original_operation_id':'original-operation','pre_input_intent_sha256':sha256(canonical(INTENT)).hexdigest()}
    assert inventory(world['store'].directory)==after
    # Legitimate current access advances, but native scope and original input do not.
    access=copy.deepcopy(world['records']['access'])
    access.update(sequence=1,previous_state_ref=world['selected']['control_refs']['access'],
        recorded_at='2026-10-14T00:05:00.000000Z',budget={'maximum_looks':3,'consumed_looks':1,'reserved_looks':0})
    world['selected']['control_refs']['access']=retain(world['directory'],access,'access_state_id')
    write(world['directory']/'SELECTED.json',canonical(world['selected']))
    continued=actual('07-current-access-advance','read_original_case');response_schema(continued)
    assert continued['operation_state']=='COMPLETE' and continued['locator']==original_locator
    assert continued['input']==original_input
    assert continued['issuer']['current_selection_sha256']!=original_locator['original_selection_sha256']
    # Exact same-size original body corruption is not recovered by reconstruction.
    target=world['store'].directory/world['store']._result_name('original-operation')
    original=target.read_bytes();write(target,original[:-1]+bytes([original[-1]^1]))
    try:
        refused=actual('08-original-custody-corruption','read_original_case');response_schema(refused)
        assert refused['status']=='REFUSED' and 'input' not in refused
    finally:write(target,original)
    assert source_guard_snapshot()==source_before
    if sink is not None:
        provenance={'schema':'market_memory.native_issuer_actual_synthetic_wire_vectors.v3',
            'complete':True,'vectors':vectors,'actual_call_totals':counts,
            'production_exchange_source_sha256':sha256((SOURCE_ROOT/issuer._MODULE).read_bytes()).hexdigest(),
            'native_peer_source_sha256':sha256((SOURCE_ROOT/'engine/research_factory/market_memory_e0_native_peer.py').read_bytes()).hexdigest(),
            'original_source_snapshot':source_before,'source_and_git_unchanged':True,
            'source_git_sentinel_present':(SOURCE_ROOT/'.git').exists(),
            'isolated_install':str(world['installed_root']),'fixture_authority_substitutions':world['fixture_record'],
            'native_runtime_claims':dict(issuer.FALSE_FLAGS),'scientific_admission':False,
            'semantic_blinding':False,'retry_authorized':False,
            'scope':'Actual unchanged production exchange outputs over genuine SYNTHETIC native owners; no actual SSH/M2 Control/provider/study effects. Per-action timing/counters are this fixture run only.'}
        (sink/'MANIFEST.json').write_bytes(canonical(provenance))


def test_pending_never_replays_or_loads_and_recovery_absent_no_auto_retry(protocol_world,monkeypatch):
    world=protocol_world;ctx=case._resolve_current_case(world['cap'],operation_id='original-operation',intent=INTENT)
    original_intent=case._original_case_intent(ctx)
    world['store'].reserve('original-operation',original_intent) # explicit TEST setup.
    before=inventory(world['store'].directory)
    def forbidden(*a,**k):pytest.fail('PENDING invoked source executor')
    monkeypatch.setattr(case,'_build_case_input',forbidden)
    pending=exchange('prepare_case');response_schema(pending)
    assert pending['status']=='ORIGINAL_OPERATION_PENDING'
    recovered=exchange('read_original_case');response_schema(recovered)
    assert recovered['operation_state']=='PENDING' and not {'input','locator'} & recovered.keys()
    assert inventory(world['store'].directory)==before


def test_qualified_then_revoked_refuses_before_source_or_store(protocol_world,monkeypatch):
    world=protocol_world;qualified=exchange();assert qualified['status']=='CURRENT_CASE_QUALIFIED'
    access=world['records']['access'];access['status']='revoked'
    world['selected']['control_refs']['access']=retain(world['directory'],access,'access_state_id')
    write(world['directory']/'SELECTED.json',canonical(world['selected']))
    before=inventory(world['store'].directory)
    def forbidden(*a,**k):pytest.fail('revoked qualification reached source/store')
    monkeypatch.setattr(case,'_build_case_input',forbidden)
    monkeypatch.setattr(case.ReservationStore,'_locked',forbidden)
    refused=exchange('prepare_case');response_schema(refused)
    assert refused['status']=='REFUSED' and inventory(world['store'].directory)==before


@pytest.mark.parametrize('defect',['extra','wrong_version','locator_on_qualification','bool_result','noncanonical','duplicate'])
def test_closed_requests_refuse_before_source_peer_or_private_io(defect,monkeypatch):
    def forbidden(*a,**k):pytest.fail('invalid wire reached installed/peer/private qualification')
    monkeypatch.setattr(issuer,'_source_snapshot',forbidden)
    value=json.loads(request())
    if defect=='extra':value['role']='reviewer'
    elif defect=='wrong_version':value['schema']=issuer.REQUEST.replace('.v3','.v2')
    elif defect=='locator_on_qualification':value['locator']={}
    elif defect=='bool_result':value={'schema':issuer.REQUEST,'action':'authorize_result_disclosure',
        'operation_id':'original-operation','intent':INTENT,'locator':{},'result_ref':{'result_bytes':True}}
    body=json.dumps(value,indent=2).encode() if defect=='noncanonical' else b'{"schema":1,"schema":2}' if defect=='duplicate' else canonical(value)
    result=json.loads(issuer.exchange(body));assert result['status']=='REFUSED' and result['reason'] in ('wire_invalid','wire_bound')


def test_one_frame_no_trailing_data_and_uninstalled_script_is_quiet(monkeypatch):
    def forbidden(*a,**k):pytest.fail('malformed frame reached exchange')
    monkeypatch.setattr(issuer,'exchange',forbidden)
    for body in (b'',b'\0\0\0',struct.pack('>I',16385),struct.pack('>I',2)+b'{}x'):
        output=io.BytesIO();issuer.serve(io.BytesIO(body),output)
        raw=output.getvalue();length=struct.unpack('>I',raw[:4])[0]
        assert len(raw)==4+length and json.loads(raw[4:])['status']=='REFUSED'
    script=SOURCE_ROOT/'scripts/market_memory_e0_native_issuer.py'
    proc=subprocess.run([sys.executable,'-I','-B',str(script)],capture_output=True,check=False)
    assert proc.returncode==77 and proc.stdout==proc.stderr==b''
