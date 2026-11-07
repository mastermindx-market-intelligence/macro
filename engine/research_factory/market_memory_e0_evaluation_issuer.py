"""Fixed native evaluation source-purpose owner; no evaluator/science admission.

The current native access owner selects scope/purpose. Requests contain equality
selectors only. A purpose grants a distinct custodian use, never reviewer truth.
"""
from __future__ import annotations
from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys

from . import market_memory_e0_native_issuer as legacy
from . import market_memory_e0_native_case as case
from . import market_memory_e0_native_peer as peer
from . import market_memory_e0_evaluation_contract as data
from . import market_memory_e0_evaluation_validation as wire

owner=case.owner
ROOT=Path('/opt/macro')
MODULE='engine/research_factory/market_memory_e0_evaluation_issuer.py'
SCHEMA='contracts/market_memory/e0_evaluation_source.v1.schema.json'
EXTRA=(MODULE,SCHEMA,'engine/research_factory/market_memory_e0_evaluation_contract.py',
       'engine/research_factory/market_memory_e0_evaluation_validation.py',
       'engine/research_factory/market_memory_e0_source_dispatch.py')
SOURCE_PATHS=tuple(dict.fromkeys((*legacy.FULL_SOURCE_PATHS,*EXTRA)))
PURPOSE='research_factory.market_memory_e0_evaluation_purpose.v1'
SCOPE='research_factory.market_memory_e0_evaluation_scope.v1'
ACTIONS=('read_evaluation_basis','authorize_evaluation_subject_read',
         'authorize_annotation_exposure','authorize_adjudication_exposure')
MAX_RESPONSE=262144
MAX_EVIDENCE=128*1024
_platform=lambda:sys.platform
_uid=os.geteuid

class EvaluationSourceError(ValueError):
    def __init__(self):super().__init__('evaluation_source_unavailable')

def require(value):
    if not value:raise EvaluationSourceError()

def _clock_ms():
    return int(datetime.now(timezone.utc).timestamp()*1000)

def _iso_clock():
    return datetime.fromtimestamp(_clock_ms()/1000,timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')

def _public_snapshot():
    require(_platform()=='linux' and _uid()==0 and Path(__file__).resolve()==ROOT/MODULE)
    result=subprocess.run(['/usr/bin/git','-C',str(ROOT),'rev-parse','--verify','HEAD'],
        check=True,capture_output=True,timeout=10,env=legacy._git_environment())
    require(not result.stderr)
    commit=result.stdout.decode('ascii').strip()
    _verify_source(commit)
    return commit

def _verify_source(commit):
    owner._verify_source(ROOT,commit,paths=SOURCE_PATHS)
    for relative in SOURCE_PATHS:
        if not relative.endswith('.py') or relative.startswith('scripts/'):continue
        name=relative[:-3].replace('/','.')
        if name.endswith('.__init__'):name=name[:-9]
        module=sys.modules.get(name)
        if module is not None:require(Path(module.__file__).resolve()==ROOT/relative)

def _record(value,kind,schema_documents):
    schema=json.loads(schema_documents[0])
    schema.pop('oneOf',None);schema['$ref']='#/$defs/'+kind
    require(next(owner.control._INTEGER_VALIDATOR(schema).iter_errors(value),None) is None)
    if kind=='scope':
        require(value['expires_at_ms']>value['not_before_ms'] and
            value['expires_at_ms']-value['not_before_ms']<=14400000)
    if kind=='purpose':
        bound=value['delegation_binding'];require(type(bound['enabled']) is bool and bound['enabled'] is True)
        require(bound['expires_at_ms']>bound['not_before_ms'] and bound['expires_at_ms']-bound['not_before_ms']<=14400000)
        require(bound['guide_ref']['sha256']==data.GUIDE_SHA)
        require(value['required_criteria']==sorted(set(value['required_criteria'])))
        require([v['role'] for v in value['slots']]==list(data.ROLES))
        data.audience(bound['source_audience'])

def _raw(fd,ref,limit=64*1024):
    owner.control._domain_reference(ref);require(ref['bytes']<=limit)
    body=owner._read(fd,ref['sha256']+'.json',limit)
    require(len(body)==ref['bytes'] and sha256(body).hexdigest()==ref['sha256'])
    return body

def _windows(purpose,scope,installation):
    bound=purpose['delegation_binding']
    lo=max(bound['not_before_ms'],scope['not_before_ms'],
        int(owner.control._clock(installation['installed_at']).timestamp()*1000))
    hi=min(bound['expires_at_ms'],scope['expires_at_ms'],
        int(owner.control._clock(installation['expires_at']).timestamp()*1000))
    require(lo<=_clock_ms()<hi and 0<hi-lo<=14400000)
    return lo,hi

def _source_context(fd,selected,records,registration_bytes,purpose):
    reg=records['registration'];task_ids=purpose['task_ids']
    values=owner._prepare_task_bytes(fd,selected,records,registration_bytes,task_id=task_ids[0])
    inputs=dict(zip(owner._INPUT_NAMES,values))
    method,_=case.tasks.resolve_registered_task_inputs(**inputs)
    manifest=owner.control._domain_json(inputs['task_manifest']);tasks={r['task_id']:r for r in manifest['tasks']}
    require(set(task_ids)<=set(tasks))
    rights,digest=case._source_rights()
    require(digest==purpose['source_registration_sha256'] and
        rights['source_authority']['sha256']==purpose['source_authority_sha256'] and
        rights['store_id']==reg['corpus']['store_id'] and
        method.purge_calendar_days==rights['method']['purge_calendar_days'] and
        method.embargo_calendar_days==rights['method']['embargo_calendar_days'])
    for task_id in task_ids:
        task=tasks[task_id]
        require(task['subject_id'] in rights['allowed_subject_ids'] and task['mode'] in rights['modes'] and
            int(owner.control._clock(task['analysis_cutoff']).timestamp()*1000)<=_clock_ms())
    return values,digest

def _prepare_evaluation_request(fd,selected,records,registration_bytes,raw_request,capability,schema_documents):
    """Fixed owner preparation, never supplied as a request authority callback."""
    request=wire.parse(raw_request,16384);data.request(request)
    include_basis=request['action']=='read_evaluation_basis'
    binding=json.loads(case._peer_binding(capability));study=request['delegation']['study_id']
    access=records['access'];installation=records['installation'];reg=records['registration']
    require(access['status']=='active' and access['contamination_state']=='clean' and
        {'read_e0_registration','disclose_e0_registration','read_registered_annotations'}<=set(installation['permitted_actions']))
    # Both are selected by current native controls BEFORE any evidence body.
    scope,scope_bytes=case._read_reference(fd,access['scope_ref'],schema=SCOPE);_record(scope,'scope',schema_documents)
    purpose,purpose_bytes=case._read_reference(fd,scope['purpose_ref'],schema=PURPOSE);_record(purpose,'purpose',schema_documents)
    service,service_bytes=case._read_reference(fd,installation['admin_receipt_ref'],schema=case._SERVICE)
    service_schema=json.loads(schema_documents[1]);service_schema.pop('oneOf',None)
    service_schema['$ref']='#/$defs/service'
    from jsonschema import FormatChecker
    require(next(owner.control._INTEGER_VALIDATOR(service_schema,format_checker=FormatChecker()).iter_errors(service),None) is None)
    require(purpose['service_ref']==installation['admin_receipt_ref'] and
        purpose['installation_id']==installation['installation_id'] and
        purpose['installation_epoch']==installation['installation_epoch'])
    require(all(service[k]==installation[k] for k in ('installation_id','installation_epoch','registration_ref','publication_ref')) and
        service['source_commit']==selected['source_commit'] and
        all(service[k]==binding[k] for k in ('ssh_key_fingerprint','restriction_profile','forced_command','native_executable','journal_profile')))
    actual=purpose['delegation_binding'];supplied={k:v for k,v in request['delegation'].items() if k!='source_purpose_ref'}
    require(wire.canonical(actual)==wire.canonical(supplied) and
        request['delegation']['source_purpose_ref']==scope['purpose_ref'] and
        actual['registration_ref']==selected['control_refs']['registration'] and
        actual['study_id']==study and request['action'] in purpose['source_actions'])
    # Native explicit purpose authorizes THIS asymmetric custodian audience.
    audience=actual['source_audience'];data.audience(audience)
    require(audience['service_key_fingerprint']==binding['ssh_key_fingerprint'] and
        audience['receiver_kind']=='native_evaluation_custodian' and
        audience['control_service_label']=='com.mastermind.executive.control')
    lo,hi=_windows(purpose,scope,installation)
    require(actual['reviewer_plan_ref']==reg['reviewer_plan_ref'])
    if request['action']!='read_evaluation_basis':
        matching=[r for r in scope['commitments'] if r['action']==request['action'] and
            all(wire.canonical(r[k])==wire.canonical(request[k]) for k in ('subject','assignment','input_sha256','pair_sha256'))]
        require(len(matching)==1 and matching[0]['task_id'] in purpose['task_ids'])
    inputs,rights_digest=_source_context(fd,selected,records,registration_bytes,purpose)
    plan,plan_bytes=case._read_reference(fd,reg['reviewer_plan_ref'],schema=owner.control._REVIEWER_PLAN_SCHEMA)
    owner.control._validate_reviewer_plan_declaration(plan,plan_bytes,reg)
    require(plan['annotation_guide_sha256']==actual['guide_ref']['sha256']==data.GUIDE_SHA)
    require(set(purpose['task_ids'])<={row['task_id'] for row in plan['assignments']})
    guide=_raw(fd,actual['guide_ref'],owner.control.MAX_DOMAIN_OBJECT_BYTES)
    cached=[(access['scope_ref'],scope_bytes),(scope['purpose_ref'],purpose_bytes),
        (installation['admin_receipt_ref'],service_bytes),(reg['reviewer_plan_ref'],plan_bytes),(actual['guide_ref'],guide)]
    basis=None
    if include_basis:
        participants=[*plan['reviewers'],plan['adjudicator']];slots=[]
        # The protected custodian must bind actual registered membership,
        # not a caller participant_slot or a reference with no plan body.
        # This exact authorized plan counts within the existing budget.
        refs=[reg['reviewer_plan_ref']]
        for row,participant in zip(purpose['slots'],participants,strict=True):
            slot={**row,**{k:participant[k] for k in ('principal_ref','qualification_ref','independence_ref')}}
            slots.append(slot);refs.extend(slot[k] for k in ('principal_ref','qualification_ref','independence_ref','identity_mapping_ref'))
        # A declared global evidence object may serve several slots.
        # Retain one exact body per reference; never invent duplicate maps.
        refs=list({wire.canonical(r):r for r in refs}.values())
        require(len(refs)<=32 and sum(r['bytes'] for r in refs)<=MAX_EVIDENCE)
        mapping_keys={wire.canonical(r['identity_mapping_ref']) for r in purpose['slots']}
        evidence=[]
        for ref in refs:
            body=_raw(fd,ref);value=owner.control._domain_json(body)
            require(type(value) is dict and value.get('schema')==ref['schema'] and wire.canonical(value)==body)
            if wire.canonical(ref) in mapping_keys:
                require(ref['schema']=='mastermind.native_model_actor_mapping.v1')
                data.identity_mapping(value)
            evidence.append({'reference':ref,'body':value});cached.append((ref,body))
        basis={'schema':'research_factory.memory_evaluation_basis.v1',
            **{k:actual[k] for k in ('registration_ref','reviewer_plan_ref','guide_ref')},
            'source_purpose_ref':scope['purpose_ref'],'required_criteria':purpose['required_criteria'],
            'independence_rules':purpose['independence_rules'],'slots':slots,'evidence':evidence}
        data.basis(basis,request['delegation'])
    # Real native FD rereads, then fresh native source rights and clock.
    for ref,body in cached:require(_raw(fd,ref,max(64*1024,len(body)))==body)
    require(case._source_rights()[1]==rights_digest)
    lo,hi=_windows(purpose,scope,installation)
    peer.require_current_broker_service(capability)
    state={'purpose':purpose,'scope':scope,'service':service,'plan':plan,'guide_sha256':sha256(guide).hexdigest(),
        'input_digests':[sha256(x).hexdigest() for x in inputs],'rights_digest':rights_digest,
        'installation':installation,'peer_binding':binding,'source_commit':selected['source_commit'],'window':[lo,hi]}
    # Internal immutable body snapshots only. These are never request fields or
    # a reusable authorization object; the fixed owner consumes them immediately.
    reg_refs=(selected['control_refs']['registration'],reg['implementation']['method_ref'],
        reg['tasks_ref'],reg['corpus']['membership_ref'])
    for ref,raw in zip(reg_refs,inputs,strict=True):cached.append((ref,raw))
    return (wire.canonical(state),None if basis is None else wire.canonical(basis),
        tuple((wire.canonical(ref),raw) for ref,raw in cached))


def _finish_evaluation_request(fd,prepared,capability):
    """Terminal native requalification AFTER the last blocking source verifier.

    Reopen every exact role/plan/guide/evidence byte read during preparation,
    then obtain current rights and the actual peer again. The installed owner
    follows this with final selected-control/history/time checks. No schema or
    Git read occurs here or afterwards; source rights and peer reads are fresh.
    """
    state_bytes,basis_bytes,snapshots=prepared
    state=wire.parse(state_bytes,owner.MAX_ACCESS_HISTORY_BYTES)
    for ref_bytes,body in snapshots:
        ref=wire.parse(ref_bytes,4096)
        require(_raw(fd,ref,max(64*1024,len(body)))==body)
    require(case._source_rights()[1]==state['rights_digest'])
    require(case._peer_binding(capability)==wire.canonical(state['peer_binding']))
    _windows(state['purpose'],state['scope'],state['installation'])
    return state_bytes,None if basis_bytes is None else wire.parse(basis_bytes,MAX_RESPONSE)


def _resolve(request,capability,*,include_basis):
    study=request['delegation']['study_id']
    directory=case._CONTROL_ROOT/sha256(study.encode()).hexdigest()
    (state,basis),selected=owner._load_selected_evaluation_request(
        directory,study,wire.canonical(request),capability)
    return state,selected,basis

def exchange(raw):
    """One fixed evaluation action. Raises an input-free refusal, no success DTO."""
    try:
        started=_clock_ms()
        request=wire.parse(raw,16384);data.request(request)
        before_source=_public_snapshot();capability=peer.observe_current_broker_service()
        first,selection,basis=_resolve(request,capability,include_basis=request['action']=='read_evaluation_basis')
        require(_public_snapshot()==before_source)
        # Reopen every disclosed native evidence body, not just its unchanged
        # reference. Public blocking reads precede this final native boundary.
        final,selected,final_basis=_resolve(request,capability,include_basis=request['action']=='read_evaluation_basis')
        require(first==final and selection==selected and wire.canonical(basis)==wire.canonical(final_basis))
        state=json.loads(final);purpose=state['purpose'];scope=state['scope'];installation=state['installation']
        lo,hi=_windows(purpose,scope,installation)
        # All values come from fresh native records/peer, never caller echo.
        response={'schema':data.RESPONSE,'state':'CURRENT','request_sha256':data.digest(request),
            'source_purpose_ref':scope['purpose_ref'],'source_owner':{'installation_id':installation['installation_id'],
                'installation_epoch':installation['installation_epoch'],'service_key_fingerprint':state['peer_binding']['ssh_key_fingerprint']},
            'generation':purpose['delegation_binding']['generation'],'not_before_ms':lo,'expires_at_ms':hi,
            'basis':basis,'verification':dict(wire.FLAGS),'scientific_admission':False}
        data.response(response,request);encoded=wire.canonical(response)
        finished=_clock_ms()
        require(len(encoded)<=MAX_RESPONSE and started<=finished and lo<=finished<hi)
        return encoded
    except Exception:raise EvaluationSourceError() from None
