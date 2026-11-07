"""Native source-purpose composition under honest isolated install primitives.

Synthetic native grant/evidence/subject commitments are NOT actual reviewer,
M2 Control, study or two-host authority. No top-level issuer is mocked. Public
M2 DATA validators execute in a separate copied temporary Python package/process.
"""
import base64
import copy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import pytest

from engine.research_factory import market_memory_e0_evaluation_issuer as evaluation
from engine.research_factory import market_memory_e0_source_dispatch as dispatch
from engine.research_factory import market_memory_e0_native_case as case
from engine.research_factory import market_memory_e0_native_issuer as legacy
from tests.market_memory_native_peer_fixtures import native_peer_primitives,native_peer_capability
from tests.test_market_memory_e0_native_case import (native_world,records,SOURCE_ROOT,INTENT,
    write,retain,reference,canonical,publish,inventory,source_guard_snapshot)


def request(world,action):
    value={'schema':evaluation.data.REQUEST,'action':action,'delegation':copy.deepcopy(world['delegation']),
        'subject':None,'assignment':None,'input_sha256':None,'pair_sha256':None}
    if action!=evaluation.ACTIONS[0]:
        row=next(r for r in world['scope']['commitments'] if r['action']==action)
        value.update({k:copy.deepcopy(row[k]) for k in ('subject','assignment','input_sha256','pair_sha256')})
    return value


def framed(value):
    raw=canonical(value);return struct.pack('>I',len(raw))+raw


def actual(value):
    output=io.BytesIO();dispatch.serve(io.BytesIO(framed(value)),output)
    raw=output.getvalue();assert struct.unpack('>I',raw[:4])[0]==len(raw)-4
    result=json.loads(raw[4:]);assert canonical(result)==raw[4:]
    return result,raw


def select(world):
    world['selected']['control_refs']={k:retain(world['directory'],world['records'][k],identity)
        for k,(_kind,identity) in case.owner._CONTROL_KEYS.items()}
    write(world['directory']/'SELECTED.json',canonical(world['selected']))


@pytest.fixture
def evaluation_world(monkeypatch,request,tmp_path):
    monkeypatch.setattr(case,'_SOURCE_PATHS',evaluation.SOURCE_PATHS)
    world=request.getfixturevalue('native_world');installed=world['installed_root']
    for module in (evaluation,legacy):
        monkeypatch.setattr(module,'ROOT',installed);monkeypatch.setattr(module,'_platform',lambda:'linux');monkeypatch.setattr(module,'_uid',lambda:0)
    # The original V3 path remains callable under its original selected grant.
    old={'schema':legacy.REQUEST,'action':'qualify_current_case','operation_id':'original-operation','intent':INTENT}
    before=inventory(world['store'].directory)
    original,_=actual(old);assert original['status']=='CURRENT_CASE_QUALIFIED'
    assert inventory(world['store'].directory)==before
    world['legacy_scope_ref']=copy.deepcopy(world['records']['access']['scope_ref'])
    plan_ref=world['records']['registration']['reviewer_plan_ref']
    plan=json.loads((world['directory']/(plan_ref['sha256']+'.json')).read_bytes())
    mappings=[];evidence_refs=[]
    ids=['fixture-evaluator-'+str(i+1) for i in range(3)]
    metadata_schema=json.loads((SOURCE_ROOT/'contracts/market_memory/e0_review_metadata.v2.schema.json').read_bytes())
    from jsonschema import Draft202012Validator
    metadata_validator=Draft202012Validator(metadata_schema)
    for index,participant in enumerate([*plan['reviewers'],plan['adjudicator']]):
        for field in ('principal_ref','qualification_ref','independence_ref'):
            role=field.removesuffix('_ref');who=ids[index]
            body={'schema':'research_factory.market_memory_e0_reviewer_'+role+'_metadata.v2',
                'object_id':who if role=='principal' else who+':'+field,'authority':'display_only',
                'study_id':INTENT['study_id'],'participant_id':who,'verification':dict(evaluation.wire.FLAGS)}
            if role=='principal':body['execution_identity']=None
            elif role=='qualification':body['declared_competencies']=['source_support','contradiction_detection','material_omissions','market_context']
            else:body.update(declared_distinct_from=[value for value in ids if value!=who],
                prior_exposure_status='not_established',peer_ratings_visibility='not_established')
            assert metadata_validator.is_valid(body) # unchanged accepted DATA, never reviewer authority
            participant[field]=retain(world['directory'],body);evidence_refs.append(participant[field])
        mapping={'schema':'mastermind.native_model_actor_mapping.v1','actor_kind':'NATIVE_MODEL',
            'canonical_actor_ref':participant['principal_ref'],
            'credential_bindings':[{'credential_binding_ref':participant['principal_ref'],'credential_document_sha256':'a'*64}],
            'assessment_basis':'Explicit synthetic assessor metadata, not actual served identity',
            'limitations':list(evaluation.data.LIMITS)}
        raw=canonical(mapping);ref=reference(raw,mapping['schema'],'fixture-actor-mapping-'+str(index));write(world['directory']/(ref['sha256']+'.json'),raw)
        mappings.append(ref);evidence_refs.append(ref)
    for assignment_row in plan['assignments']:
        assignment_row['reviewer_principal_ids']=[r['principal_ref']['object_id'] for r in plan['reviewers']]
        assignment_row['adjudicator_principal_id']=plan['adjudicator']['principal_ref']['object_id']
    world['records']['registration']['reviewer_plan_ref']=retain(world['directory'],plan)
    rr,pr=publish(tmp_path,world['records'])
    service=copy.deepcopy(world['service']);service.update(registration_ref=rr,publication_ref=pr)
    service_ref=retain(world['directory'],service);world['records']['installation']['admin_receipt_ref']=service_ref
    world['records']['installation']['permitted_actions'].append('read_registered_annotations')
    guide=(SOURCE_ROOT/'tests/fixtures/market_memory_e0/E0_ANNOTATION_GUIDE_PRELABEL_V1.md').read_bytes()
    assert sha256(guide).hexdigest()==evaluation.data.GUIDE_SHA
    guide_ref=reference(guide,'text.markdown.v1','frozen-original-guide');write(world['directory']/(guide_ref['sha256']+'.json'),guide)
    now=evaluation._clock_ms()
    binding={'schema':evaluation.data.DELEGATION,'enabled':True,'generation':'native-evaluation-generation',
        'study_root':INTENT['root_id'],'study_id':INTENT['study_id'],'root_job_id':'fixture-root-job',
        'registration_ref':rr,'reviewer_plan_ref':world['records']['registration']['reviewer_plan_ref'],
        'guide_ref':guide_ref,'source_audience':{'receiver_kind':'native_evaluation_custodian',
            'service_key_fingerprint':service['ssh_key_fingerprint'],'control_service_label':'com.mastermind.executive.control'},
        'decision_ref':plan['reviewers'][0]['qualification_ref'],'principal_binding_digest':'a'*64,
        'actions':list(evaluation.data.ACTIONS),'evidence_profile':evaluation.data.PROFILE,
        'not_before_ms':now-2000,'expires_at_ms':now+3600000}
    purpose={'schema':evaluation.PURPOSE,'object_id':'fixture-evaluation-purpose','installation_id':service['installation_id'],
        'installation_epoch':service['installation_epoch'],'service_ref':service_ref,'delegation_binding':binding,
        'source_actions':list(evaluation.ACTIONS),'source_registration_sha256':world['recipient']['source_use']['source_registration_sha256'],
        'source_authority_sha256':world['recipient']['source_use']['source_authority_sha256'],
        'task_ids':[world['task']['task_id']],'required_criteria':['retained_conflicts','retained_qualification'],
        'independence_rules':['distinct_canonical_actor','assessed_conflicts'],
        'slots':[{'role':role,'identity_mapping_ref':ref,'execution_profile_id':'synthetic-fixed-model-profile'}
            for role,ref in zip(evaluation.data.ROLES,mappings,strict=True)]}
    purpose_ref=retain(world['directory'],purpose)
    # These are explicit native SOURCE-GRANT metadata commitments, not a fake
    # M2 original-result/actor capability. M2 independently owns actual custody.
    subject={'operation_id':'original-operation','attempt_id':'retained-subject-attempt',
        'input_sha256':sha256(b'synthetic retained subject input').hexdigest(),'input_bytes':32,
        'result_sha256':sha256(b'synthetic retained subject result').hexdigest(),'result_bytes':33}
    assignment=sha256(b'synthetic existing native assignment').hexdigest()
    rows=[]
    for action in evaluation.ACTIONS[1:]:
        rows.append({'action':action,'task_id':world['task']['task_id'],'subject':copy.deepcopy(subject),
            'assignment':assignment,'input_sha256':None if action==evaluation.ACTIONS[1] else sha256(action.encode()).hexdigest(),
            'pair_sha256':sha256(b'synthetic immutable pair').hexdigest() if action==evaluation.ACTIONS[3] else None})
    scope={'schema':evaluation.SCOPE,'object_id':'fixture-native-evaluation-scope','purpose_ref':purpose_ref,
        'not_before_ms':now-1000,'expires_at_ms':now+1800000,'commitments':rows}
    world['records']['access']['scope_ref']=retain(world['directory'],scope);select(world)
    world.update(purpose=purpose,scope=scope,purpose_ref=purpose_ref,delegation={**binding,'source_purpose_ref':purpose_ref},
        evidence_refs=evidence_refs,guide_ref=guide_ref,native_service=service,plan=plan,
        plan_ref=copy.deepcopy(world['records']['registration']['reviewer_plan_ref']),plan_bytes=canonical(plan))
    return world


def public_validate(tmp_path,req,response,request_frame,response_frame):
    root=tmp_path/'isolated-public-validator';root.mkdir(exist_ok=True)
    common=root/'common';common.mkdir(exist_ok=True);(common/'__init__.py').write_text('')
    fixtures=SOURCE_ROOT/'tests/fixtures/market_memory_e0/evaluation_source_wire'
    for name in ('memory_evaluation_contract.py','memory_native_wire.py'):(common/name).write_bytes((fixtures/name).read_bytes())
    code="""import base64,json,sys
from common import memory_evaluation_contract as c
from common import memory_native_wire as w
x=json.loads(sys.stdin.buffer.read());r=w._unframe(base64.b64decode(x['request_frame']),16384);v=w._unframe(base64.b64decode(x['response_frame']),262144)
assert r==x['request'] and v==x['response'];c.request(r);c.response(v,r)
print('PUBLIC_FROZEN_CONTRACT_PASS')
"""
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')};env.update(PYTHONPATH=str(root),PYTHONDONTWRITEBYTECODE='1')
    result=subprocess.run([sys.executable,'-B','-c',code],cwd=root,env=env,input=canonical({'request':req,'response':response,
        'request_frame':base64.b64encode(request_frame).decode(),'response_frame':base64.b64encode(response_frame).decode()}),capture_output=True,timeout=20)
    assert result.returncode==0,result.stderr.decode();assert result.stdout.strip()==b'PUBLIC_FROZEN_CONTRACT_PASS'


def test_all_four_native_actions_actual_framed_frozen_m2_contract(evaluation_world,tmp_path,monkeypatch):
    world=evaluation_world;before=inventory(world['store'].directory);guard=source_guard_snapshot()
    def forbidden(*a,**k):pytest.fail('evaluation source authorization touched cohort/card/reservation/provider')
    monkeypatch.setattr(case,'_build_case_input',forbidden)
    for name in ('snapshot','reserve','finish','read_completed','_locked','_load'):monkeypatch.setattr(case.ReservationStore,name,forbidden)
    for action in evaluation.ACTIONS:
        req=request(world,action);result,frame=actual(req)
        public_validate(tmp_path,req,result,framed(req),frame)
        assert result['source_owner']=={'installation_id':world['native_service']['installation_id'],
            'installation_epoch':world['native_service']['installation_epoch'],
            'service_key_fingerprint':world['native_service']['ssh_key_fingerprint']}
        assert result['not_before_ms']==world['scope']['not_before_ms'] and result['expires_at_ms']==world['scope']['expires_at_ms']
        assert result['verification']==evaluation.wire.FLAGS and result['scientific_admission'] is False
        if action==evaluation.ACTIONS[0]:
            assert len(result['basis']['evidence'])==13
            plan_rows=[row for row in result['basis']['evidence'] if row['reference']==world['plan_ref']]
            assert len(plan_rows)==1 and canonical(plan_rows[0]['body'])==world['plan_bytes']
            assert plan_rows[0]['body']==world['plan']
            for actual_slot,participant,native_slot in zip(result['basis']['slots'],[*world['plan']['reviewers'],world['plan']['adjudicator']],world['purpose']['slots'],strict=True):
                assert all(actual_slot[k]==participant[k] for k in ('principal_ref','qualification_ref','independence_ref'))
                assert all(actual_slot[k]==native_slot[k] for k in ('role','identity_mapping_ref','execution_profile_id'))
        else:assert result['basis'] is None
    assert inventory(world['store'].directory)==before and source_guard_snapshot()==guard


@pytest.mark.parametrize('defect',['purpose','role','key','study','plan','subject','assignment','input','pair','nullability','extra'])
def test_closed_or_scope_mismatch_refuses(evaluation_world,defect):
    world=evaluation_world;req=request(world,evaluation.ACTIONS[3])
    if defect=='purpose':req['delegation']['source_purpose_ref']['sha256']='f'*64
    elif defect=='role':req['delegation']['source_audience']['receiver_kind']='native_broker_service'
    elif defect=='key':req['delegation']['source_audience']['service_key_fingerprint']='SHA256:'+base64.b64encode(b'x'*32).decode().rstrip('=')
    elif defect=='study':req['delegation']['study_id']='other-study'
    elif defect=='plan':req['delegation']['reviewer_plan_ref']['sha256']='f'*64
    elif defect=='subject':req['subject']['result_sha256']='f'*64
    elif defect=='assignment':req['assignment']='f'*64
    elif defect=='input':req['input_sha256']='f'*64
    elif defect=='pair':req['pair_sha256']='f'*64
    elif defect=='nullability':req['input_sha256']=None
    else:req['caller_authorized']=True
    output=io.BytesIO()
    with pytest.raises(SystemExit) as error:dispatch.serve(io.BytesIO(framed(req)),output)
    assert error.value.code==77 and output.getvalue()==b''


def test_old_service_scope_cannot_authorize_evaluation(evaluation_world):
    world=evaluation_world;world['records']['access']['scope_ref']=world['legacy_scope_ref'];select(world)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


def test_revoked_current_access_before_evidence(evaluation_world,monkeypatch):
    world=evaluation_world;world['records']['access']['status']='revoked';select(world)
    original=case.owner._read;evidence={r['sha256']+'.json' for r in world['evidence_refs']}
    def read(fd,name,*a,**k):
        assert name not in evidence,'revoked access read participant evidence'
        return original(fd,name,*a,**k)
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


def test_mid_read_revocation_withholds(evaluation_world,monkeypatch):
    world=evaluation_world;original=case.owner._read;fired=[];target=world['evidence_refs'][0]['sha256']+'.json'
    def read(fd,name,*a,**k):
        body=original(fd,name,*a,**k)
        if name==target and not fired:
            fired.append(True);world['records']['access']['status']='revoked';select(world)
        return body
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))
    assert fired


def test_expiry_during_guide_read_withholds(evaluation_world,monkeypatch):
    world=evaluation_world;original=case.owner._read;now=evaluation._clock_ms();clock=[now];fired=[]
    monkeypatch.setattr(evaluation,'_clock_ms',lambda:clock[0])
    def read(fd,name,*a,**k):
        body=original(fd,name,*a,**k)
        if name==world['guide_ref']['sha256']+'.json':clock[0]=world['scope']['expires_at_ms'];fired.append(True)
        return body
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))
    assert fired


def test_changed_source_rights_withholds(evaluation_world):
    world=evaluation_world;path=world['source_config'];original=path.read_bytes()
    value=json.loads(original);value['allowed_subject_ids']=[];write(path,canonical(value),False)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


def test_dispatch_legacy_malformed_frame_parity():
    for raw in (b'',b'\0\0\0',struct.pack('>I',16385),struct.pack('>I',2)+b'{}x'):
        before=io.BytesIO();after=io.BytesIO();legacy.serve(io.BytesIO(raw),before);dispatch.serve(io.BytesIO(raw),after)
        assert before.getvalue()==after.getvalue()


def test_native_current_resolution_returns_only_selected_basis(evaluation_world):
    world=evaluation_world;req=request(world,evaluation.ACTIONS[0])
    evaluation.data.request(req)
    evaluation._public_snapshot()
    cap=evaluation.peer.observe_current_broker_service()
    state,selection,basis=evaluation._resolve(req,cap,include_basis=True)
    assert json.loads(state)['purpose']==world['purpose']
    assert basis['source_purpose_ref']==world['purpose_ref']
    assert selection==(world['directory']/'SELECTED.json').read_bytes()


@pytest.mark.parametrize('target_kind',['principal','plan'])
def test_cached_evidence_corruption_between_native_resolutions_withholds(evaluation_world,monkeypatch,target_kind):
    world=evaluation_world;original=case.owner._read;reads=[];fired=[]
    ref=world['evidence_refs'][0] if target_kind=='principal' else world['plan_ref']
    target=world['directory']/(ref['sha256']+'.json')
    before=target.read_bytes()
    def read(fd,name,*a,**k):
        body=original(fd,name,*a,**k)
        if name=='SELECTED.json':
            reads.append(True)
            # AFTER first native resolution's body rereads and BEFORE its
            # final return; second actual resolution must reread evidence.
            if len(reads)==2:
                write(target,before[:-1]+bytes([before[-1]^1]));fired.append(True)
        return body
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):
        evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))
    assert fired


def advance_native_scope(world,scope):
    access=copy.deepcopy(world['records']['access'])
    access['sequence']+=1
    access['previous_state_ref']=world['selected']['control_refs']['access']
    access['recorded_at']=evaluation._iso_clock()
    access['scope_ref']=retain(world['directory'],scope)
    world['records']['access']=access;world['scope']=scope;select(world)


def test_static_purpose_and_genuine_access_history_advance_without_digest_cycle(evaluation_world):
    world=evaluation_world;purpose_ref=copy.deepcopy(world['purpose_ref'])
    source_rows=copy.deepcopy(world['scope']['commitments'])
    scope=copy.deepcopy(world['scope']);scope['commitments']=[];advance_native_scope(world,scope)
    basis,_=actual(request(world,evaluation.ACTIONS[0]))
    assert basis['basis']['source_purpose_ref']==purpose_ref
    # Native subject-read permission is established before a compiled input
    # exists. No subject body or future digest is part of the static purpose.
    scope=copy.deepcopy(scope);scope['commitments']=[source_rows[0]];advance_native_scope(world,scope)
    subject_request={'schema':evaluation.data.REQUEST,'action':evaluation.ACTIONS[1],
        'delegation':copy.deepcopy(world['delegation']),**{k:copy.deepcopy(source_rows[0][k]) for k in ('subject','assignment','input_sha256','pair_sha256')}}
    permitted,_=actual(subject_request);assert permitted['basis'] is None
    compiled=canonical({'schema':'synthetic.compiled.annotation.v1','source_purpose_ref':purpose_ref,
        'subject':source_rows[0]['subject'],'assignment':source_rows[0]['assignment']})
    annotation=copy.deepcopy(source_rows[1]);annotation['input_sha256']=sha256(compiled).hexdigest()
    exposure={'schema':evaluation.data.REQUEST,'action':evaluation.ACTIONS[2],
        'delegation':copy.deepcopy(world['delegation']),**{k:annotation[k] for k in ('subject','assignment','input_sha256','pair_sha256')}}
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(exposure))
    # Existing native access owner publishes the actual compiled commitment.
    scope=copy.deepcopy(scope);scope['commitments'].append(annotation);advance_native_scope(world,scope)
    authorized,_=actual(exposure)
    assert authorized['source_purpose_ref']==purpose_ref==world['purpose_ref']
    assert world['records']['access']['sequence']==3


def test_native_grant_wrong_key_cannot_be_echoed_as_source_owner(evaluation_world,monkeypatch):
    world=evaluation_world;purpose=copy.deepcopy(world['purpose'])
    purpose['delegation_binding']['source_audience']['service_key_fingerprint']='SHA256:'+base64.b64encode(b'z'*32).decode().rstrip('=')
    world['purpose']=purpose;world['purpose_ref']=retain(world['directory'],purpose)
    world['delegation']={**purpose['delegation_binding'],'source_purpose_ref':world['purpose_ref']}
    scope=copy.deepcopy(world['scope']);scope['purpose_ref']=world['purpose_ref']
    world['scope']=scope;world['records']['access']['scope_ref']=retain(world['directory'],scope);select(world)
    evidence={r['sha256']+'.json' for r in world['evidence_refs']};original=case.owner._read
    def read(fd,name,*a,**k):
        assert name not in evidence,'mismatched native grant key disclosed evidence'
        return original(fd,name,*a,**k)
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


def test_expanded_public_closure_rejects_dispatcher_drift_before_private_metadata(evaluation_world,monkeypatch):
    world=evaluation_world;path=world['installed_root']/'engine/research_factory/market_memory_e0_source_dispatch.py'
    write(path,path.read_bytes()+b'\n# explicit temporary source-byte drift\n',False)
    original=case.owner._directory
    def directory(path,*,private):
        assert not private,'source drift reached private metadata'
        return original(path,private=private)
    monkeypatch.setattr(case.owner,'_directory',directory)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))
    legacy_request={'schema':legacy.REQUEST,'action':'qualify_current_case','operation_id':'original-operation','intent':INTENT}
    # The original V3 route also qualifies every new dispatcher dependency.
    response,_=actual(legacy_request)
    assert response['status']=='REFUSED' and response['reason']=='installed_issuer_source_unqualified'


def test_future_registered_cutoff_refuses_current_native_purpose(evaluation_world):
    world=evaluation_world;reg=world['records']['registration'];directory=world['directory']
    task_ref=reg['tasks_ref'];manifest=json.loads((directory/(task_ref['sha256']+'.json')).read_bytes())
    from datetime import datetime,timedelta,timezone
    manifest['tasks'][0]['analysis_cutoff']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat(timespec='microseconds').replace('+00:00','Z')
    reg['tasks_ref']=retain(directory,manifest)
    method_ref=reg['implementation']['method_ref'];method=json.loads((directory/(method_ref['sha256']+'.json')).read_bytes())
    method['tasks_ref']=reg['tasks_ref'];reg['implementation']['method_ref']=retain(directory,method)
    world['plan']['tasks_ref']=reg['tasks_ref'];reg['reviewer_plan_ref']=retain(directory,world['plan'])
    rr,pr=publish(world['temporary_root'],world['records'])
    service=copy.deepcopy(world['native_service']);service.update(registration_ref=rr,publication_ref=pr)
    service_ref=retain(directory,service);world['records']['installation']['admin_receipt_ref']=service_ref
    purpose=copy.deepcopy(world['purpose']);purpose['service_ref']=service_ref
    purpose['delegation_binding'].update(registration_ref=rr,reviewer_plan_ref=reg['reviewer_plan_ref'])
    purpose_ref=retain(directory,purpose);world['purpose']=purpose;world['purpose_ref']=purpose_ref
    world['delegation']={**purpose['delegation_binding'],'source_purpose_ref':purpose_ref}
    scope=copy.deepcopy(world['scope']);scope['purpose_ref']=purpose_ref
    world['records']['access']['scope_ref']=retain(directory,scope);select(world)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


def test_legacy_history_and_v3_keep_rejecting_scope_advance(evaluation_world):
    world=evaluation_world;scope=copy.deepcopy(world['scope']);scope['commitments']=scope['commitments'][:1]
    advance_native_scope(world,scope)
    # Fixed new entry validates a real native scope evolution, with DATA-only
    # diagnostics. The unchanged legacy API continues to reject it.
    summary=case.owner._load_selected_evaluation_control(world['directory'],INTENT['study_id'],evaluation._verify_source,clock=evaluation._iso_clock)
    assert summary['authority']=='display_only' and summary['current_selection_authenticated'] is False
    assert summary['access_history']['current_selection_authenticated'] is False
    assert summary['evaluation_scope_metadata_read'] is True
    with pytest.raises(Exception,match='access_epoch_binding_changed'):
        case.owner._load_selected_control(world['directory'],INTENT['study_id'],evaluation._verify_source,clock=evaluation._iso_clock)
    old={'schema':legacy.REQUEST,'action':'qualify_current_case','operation_id':'original-operation','intent':INTENT}
    result,_=actual(old);assert result['status']=='REFUSED'


@pytest.mark.parametrize('defect',['purpose_change','mixed_legacy','scope_bytes','service_change','refund','budget_raise','revocation_reversal','contamination_reversal'])
def test_native_evaluation_history_rejects_invalid_evolution(evaluation_world,monkeypatch,defect):
    world=evaluation_world;scope=copy.deepcopy(world['scope'])
    if defect=='purpose_change':
        other=copy.deepcopy(world['purpose']);other['object_id']='other-native-purpose'
        scope['purpose_ref']=retain(world['directory'],other)
        advance_native_scope(world,scope)
    elif defect=='mixed_legacy':
        advance_native_scope(world,scope)
        world['records']['access']['scope_ref']=world['legacy_scope_ref'];select(world)
    elif defect=='scope_bytes':
        scope['object_id']='next-native-scope';advance_native_scope(world,scope)
        target=world['directory']/(world['records']['access']['scope_ref']['sha256']+'.json')
        raw=target.read_bytes();write(target,raw[:-1]+bytes([raw[-1]^1]))
    elif defect=='service_change':
        advance_native_scope(world,scope)
        service=copy.deepcopy(world['native_service']);service['object_id']='different-service-binding'
        world['records']['installation']['admin_receipt_ref']=retain(world['directory'],service);select(world)
    else:
        access=world['records']['access']
        if defect=='refund':access['budget']['consumed_looks']=1
        elif defect=='budget_raise':pass
        elif defect=='revocation_reversal':access['status']='revoked'
        else:access['contamination_state']='contaminated'
        advance_native_scope(world,scope)
        # Restore the originally retained initial state (it was copied by
        # advance); the next authentic record expresses the invalid reversal.
        initial_ref=world['records']['access']['previous_state_ref']
        # Existing fixture state mutation above would alter no retained bytes.
        if defect=='refund':world['records']['access']['budget']['consumed_looks']=0
        elif defect=='budget_raise':world['records']['access']['budget']['maximum_looks']=4
        elif defect=='revocation_reversal':world['records']['access']['status']='active'
        else:world['records']['access']['contamination_state']='clean'
        advance_native_scope(world,scope)
    original=case.owner._read;evidence={r['sha256']+'.json' for r in world['evidence_refs']}
    def read(fd,name,*a,**k):
        assert name not in evidence,'invalid native history disclosed evaluator evidence'
        return original(fd,name,*a,**k)
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


def test_native_service_and_purpose_key_must_match_actual_peer(evaluation_world,monkeypatch):
    world=evaluation_world;key='SHA256:'+base64.b64encode(b'k'*32).decode().rstrip('=')
    service=copy.deepcopy(world['native_service']);service['ssh_key_fingerprint']=key
    service_ref=retain(world['directory'],service);world['records']['installation']['admin_receipt_ref']=service_ref
    purpose=copy.deepcopy(world['purpose']);purpose['service_ref']=service_ref
    purpose['delegation_binding']['source_audience']['service_key_fingerprint']=key
    purpose_ref=retain(world['directory'],purpose)
    world['purpose']=purpose;world['purpose_ref']=purpose_ref
    world['delegation']={**purpose['delegation_binding'],'source_purpose_ref':purpose_ref}
    scope=copy.deepcopy(world['scope']);scope['purpose_ref']=purpose_ref
    world['scope']=scope;world['records']['access']['scope_ref']=retain(world['directory'],scope);select(world)
    original=case.owner._read;evidence={r['sha256']+'.json' for r in world['evidence_refs']}
    def read(fd,name,*a,**k):
        assert name not in evidence,'wrong actual peer reached evaluator evidence'
        return original(fd,name,*a,**k)
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


@pytest.mark.parametrize('defect',['criterion_newline','profile_newline'])
def test_invalid_native_identifier_cannot_authorize_exposure(evaluation_world,defect):
    world=evaluation_world;purpose=copy.deepcopy(world['purpose'])
    if defect=='criterion_newline':purpose['required_criteria'][0]+='\n'
    else:purpose['slots'][0]['execution_profile_id']+='\n'
    purpose_ref=retain(world['directory'],purpose);world['purpose']=purpose;world['purpose_ref']=purpose_ref
    world['delegation']={**purpose['delegation_binding'],'source_purpose_ref':purpose_ref}
    scope=copy.deepcopy(world['scope']);scope['purpose_ref']=purpose_ref
    world['scope']=scope;world['records']['access']['scope_ref']=retain(world['directory'],scope);select(world)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[2])))


def test_plan_evidence_budget_refuses_without_truncating_or_reading_role_bodies(evaluation_world,monkeypatch):
    world=evaluation_world
    # Tightening the source resource cap to exactly the old12-object budget
    # proves the additional plan is counted; it cannot create authorization.
    old_role_bytes=sum(ref['bytes'] for ref in world['evidence_refs'])
    assert old_role_bytes<old_role_bytes+world['plan_ref']['bytes']
    monkeypatch.setattr(evaluation,'MAX_EVIDENCE',old_role_bytes)
    original=case.owner._read;role_names={ref['sha256']+'.json' for ref in world['evidence_refs']}
    def read(fd,name,*a,**k):
        assert name not in role_names,'over-budget basis opened evaluator body'
        return original(fd,name,*a,**k)
    monkeypatch.setattr(case.owner,'_read',read)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[0])))


def test_purpose_task_must_be_assigned_in_exact_registered_plan(evaluation_world):
    world=evaluation_world;plan=copy.deepcopy(world['plan']);plan['assignments'][0]['task_id']='other-unassigned-task'
    reg=world['records']['registration'];reg['reviewer_plan_ref']=retain(world['directory'],plan)
    rr,pr=publish(world['temporary_root'],world['records'])
    service=copy.deepcopy(world['native_service']);service.update(registration_ref=rr,publication_ref=pr)
    service_ref=retain(world['directory'],service);world['records']['installation']['admin_receipt_ref']=service_ref
    purpose=copy.deepcopy(world['purpose']);purpose['service_ref']=service_ref
    purpose['delegation_binding'].update(registration_ref=rr,reviewer_plan_ref=reg['reviewer_plan_ref'])
    purpose_ref=retain(world['directory'],purpose);world['purpose']=purpose;world['purpose_ref']=purpose_ref
    world['delegation']={**purpose['delegation_binding'],'source_purpose_ref':purpose_ref}
    scope=copy.deepcopy(world['scope']);scope['purpose_ref']=purpose_ref;world['scope']=scope
    world['records']['access']['scope_ref']=retain(world['directory'],scope);select(world)
    with pytest.raises(evaluation.EvaluationSourceError):evaluation.exchange(canonical(request(world,evaluation.ACTIONS[1])))


@pytest.mark.parametrize('defect',['rights','principal','plan','guide','peer','selection'])
def test_second_post_prepare_public_verification_revocation_withholds(evaluation_world,monkeypatch,native_peer_primitives,defect):
    import inspect
    world=evaluation_world;original=evaluation._verify_source;posts=[];fired=[]
    def verify(commit):
        result=original(commit) # real Git/public-source I/O remains intact
        caller=inspect.currentframe().f_back
        # The real final verifier in each native resolution. Both rejected and
        # repaired source retain this invocation and the initial prepared value.
        if caller.f_code.co_name=='_load_selected_control_records' and 'prepared' in caller.f_locals:
            posts.append(True)
            if len(posts)==2:
                if defect=='rights':
                    policy=json.loads(world['source_config'].read_bytes());policy['allowed_subject_ids']=[]
                    write(world['source_config'],canonical(policy),False)
                elif defect in ('principal','plan','guide'):
                    ref=(world['evidence_refs'][0] if defect=='principal' else world['plan_ref'] if defect=='plan' else world['guide_ref'])
                    path=world['directory']/(ref['sha256']+'.json');body=path.read_bytes()
                    # Same-size custody corruption cannot be hidden by a stable ref.
                    altered=bytes([body[0]^1])+body[1:];write(path,altered)
                elif defect=='peer':
                    native_peer_primitives['rows'][-1]['MESSAGE']='Starting session: not the fixed key-option command'
                else:
                    world['records']['access']['status']='revoked';select(world)
                fired.append(True)
        return result
    monkeypatch.setattr(evaluation,'_verify_source',verify)
    output=io.BytesIO();failure=None
    try:dispatch.serve(io.BytesIO(framed(request(world,evaluation.ACTIONS[0]))),output)
    except SystemExit as error:failure=error
    # Assert trigger BEFORE refusal so an earlier setup/qualification failure
    # cannot masquerade as a discriminating successful negative.
    assert fired and len(posts)==2,'actual second post-prepare verifier did not inject mutation'
    print(json.dumps({'f01_defect':defect,'injection_fired':bool(fired),'post_prepare_verifier_hits':len(posts),
        'refused':failure is not None,'output_bytes':len(output.getvalue())},sort_keys=True))
    assert failure is not None and failure.code==77 and output.getvalue()==b''


def test_terminal_native_boundary_has_no_later_public_io(evaluation_world,monkeypatch):
    finishes=[];public=[];active=[True];original_finish=evaluation._finish_evaluation_request
    original_read=case.owner._read;original_open=Path.open;original_run=subprocess.run
    def finish(*a,**k):
        result=original_finish(*a,**k);finishes.append(True);return result
    def read(fd,name,*a,**k):
        if active[0] and len(finishes)==2 and k.get('private',True) is False:
            public.append(name);pytest.fail('public native read after terminal currentness')
        return original_read(fd,name,*a,**k)
    def opened(path,*a,**k):
        if active[0] and len(finishes)==2:
            public.append(str(path));pytest.fail('public/schema file open after terminal currentness')
        return original_open(path,*a,**k)
    def run(*a,**k):
        if active[0] and len(finishes)==2:public.append('subprocess');pytest.fail('blocking command after terminal currentness')
        return original_run(*a,**k)
    monkeypatch.setattr(evaluation,'_finish_evaluation_request',finish)
    monkeypatch.setattr(case.owner,'_read',read);monkeypatch.setattr(Path,'open',opened)
    monkeypatch.setattr(subprocess,'run',run)
    try:response,_=actual(request(evaluation_world,evaluation.ACTIONS[0]))
    finally:active[0]=False # fixture teardown is outside the framed action
    assert response['state']=='CURRENT' and len(finishes)==2 and public==[]
    print(json.dumps({'terminal_native_boundaries':len(finishes),'later_public_io':len(public)},sort_keys=True))
