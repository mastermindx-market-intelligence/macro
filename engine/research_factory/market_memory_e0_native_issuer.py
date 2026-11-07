"""Fixed v3 native issuer composition; no enrolment or study admission.

The only external input is closed canonical framed JSON on the fixed script's
stdin. Source/peer/current native grants are fresh on every exchange. Original
storage callbacks below are fixed same-process owner closures, never requests.
Peer provenance remains a separately held source dependency; fixtures prove no
actual native authentication, protected M2 receiver or scientific admission.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys

from . import market_memory_e0_native_case as case
from . import market_memory_e0_native_peer as peer
from . import market_memory_e0_installed_control as owner
from .market_memory_e0_reserved_read import _run_reserved_read, E0ReservedReadError
from .market_memory_e0_original_case import _read_original_case

ROOT=Path('/opt/macro')
_MODULE='engine/research_factory/market_memory_e0_native_issuer.py'
_SCRIPT='scripts/market_memory_e0_native_issuer.py'
_SCHEMA='contracts/market_memory/e0_native_issuer.v3.schema.json'
FULL_SOURCE_PATHS=tuple(dict.fromkeys((*case._SOURCE_PATHS,_MODULE,_SCRIPT,_SCHEMA,
    'engine/research_factory/market_memory_e0_reserved_read.py',
    'engine/research_factory/market_memory_e0_original_case.py',
    # The fixed helper dispatches both source purposes: qualify its complete
    # shared runtime closure under the selected commit on either route.
    'engine/research_factory/market_memory_e0_evaluation_issuer.py',
    'engine/research_factory/market_memory_e0_evaluation_contract.py',
    'engine/research_factory/market_memory_e0_evaluation_validation.py',
    'engine/research_factory/market_memory_e0_source_dispatch.py',
    'contracts/market_memory/e0_evaluation_source.v1.schema.json')))
REQUEST='research_factory.market_memory_e0_native_issuer_request.v3'
RESPONSE='research_factory.market_memory_e0_native_issuer_response.v3'
ENVELOPE='research_factory.market_memory_e0_native_original_envelope.v3'
PROTOCOL='memory.e0.native_issuer.v3'
MAX_REQUEST=16384
MAX_RESPONSE=262144
MAX_ENVELOPE=1024*1024
FALSE_FLAGS={'authenticated':False,'qualification_verified':False,'independence_verified':False,
             'exposure_verified':False,'operational_admission':False}
ACTIONS=frozenset(('qualify_current_case','prepare_case','current_input',
                  'authorize_result_disclosure','read_original_case'))
REASONS=frozenset(('wire_invalid','wire_bound','broker_service_not_enrolled',
    'broker_authentication_unqualified','broker_confinement_unqualified',
    'installed_issuer_source_unqualified','native_recipient_grant_unavailable',
    'native_intent_mismatch','current_control_unqualified','current_source_rights_unqualified',
    'selected_case_unqualified','source_or_selection_changed','original_operation_unavailable',
    'original_operation_intent_mismatch','original_input_unqualified','result_reference_mismatch',
    'case_input_size_bound','adjudicator_stage_unavailable'))
_platform=lambda:sys.platform
_uid=os.geteuid


class NativeIssuerError(ValueError):
    pass


def require(value,reason):
    if not value:raise NativeIssuerError(reason)


def canonical(value):
    owner.control._bounded_tree(value,domain=True)
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def decode(body,limit):
    require(type(body) is bytes and 0<len(body)<=limit,'wire_bound')
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'wire_invalid');result[key]=value
        return result
    try:
        value=json.loads(body.decode('utf-8'),object_pairs_hook=pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(NativeIssuerError('wire_invalid')))
        require(type(value) is dict and canonical(value)==body,'wire_invalid')
        return value
    except (UnicodeError,ValueError,RecursionError) as exc:
        raise NativeIssuerError('wire_invalid') from exc


def identifier(value):
    require(type(value) is str and owner.control._ID.fullmatch(value),'wire_invalid');return value


def digest(value):
    require(type(value) is str and re.fullmatch(r'[a-f0-9]{64}',value),'wire_invalid');return value


def integer(value,maximum):
    require(type(value) is int and 1<=value<=maximum,'wire_bound');return value


def locator(value):
    require(type(value) is dict and set(value)=={'case_id','installation_id','installation_epoch',
        'original_selection_sha256','original_intent_sha256','input_sha256','input_bytes'},'wire_invalid')
    for key,item in value.items():
        if key=='input_bytes':integer(item,65536)
        elif key.endswith('sha256'):digest(item)
        else:identifier(item)
    return value


def request(body):
    value=decode(body,MAX_REQUEST);common={'schema','action','operation_id','intent'}
    action=value.get('action');require(type(action) is str and action in ACTIONS,'wire_invalid')
    expected=common|({'locator'} if action in ('current_input','authorize_result_disclosure') else set())
    if action=='authorize_result_disclosure':expected|={'result_ref'}
    require(set(value)==expected and value['schema']==REQUEST,'wire_invalid')
    case._validate_request(value['operation_id'],value['intent'])
    if 'locator' in value:locator(value['locator'])
    if 'result_ref' in value:
        ref=value['result_ref'];require(type(ref) is dict and set(ref)=={
            'attempt_id','input_sha256','result_sha256','result_bytes'},'wire_invalid')
        identifier(ref['attempt_id']);digest(ref['input_sha256']);digest(ref['result_sha256']);integer(ref['result_bytes'],65536)
    return value


def _git_environment():
    return {**{k:v for k,v in os.environ.items() if not k.startswith('GIT_')},
        'GIT_NO_LAZY_FETCH':'1','GIT_NO_REPLACE_OBJECTS':'1','GIT_OPTIONAL_LOCKS':'0',
        'GIT_TERMINAL_PROMPT':'0','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,'GIT_ALLOW_PROTOCOL':''}


def _source_snapshot():
    """Public installed code qualification BEFORE any selected private data."""
    require(_platform()=='linux' and _uid()==0 and Path(__file__).resolve()==ROOT/_MODULE,
            'installed_issuer_source_unqualified')
    try:
        result=subprocess.run(['/usr/bin/git','-C',str(ROOT),'rev-parse','--verify','HEAD'],
            capture_output=True,check=True,timeout=10,env=_git_environment())
        require(not result.stderr,'installed_issuer_source_unqualified')
        commit=result.stdout.decode('ascii').strip()
        owner._verify_source(ROOT,commit,paths=FULL_SOURCE_PATHS)
        rows=[]
        for relative in FULL_SOURCE_PATHS:
            path=ROOT/relative
            with owner._directory(path.parent,private=False) as fd:
                body=owner._read(fd,path.name,512*1024,private=False)
            rows.append({'path':relative,'sha256':sha256(body).hexdigest(),'bytes':len(body)})
        owner._verify_source(ROOT,commit,paths=FULL_SOURCE_PATHS)
        return commit,sha256(canonical(rows)).hexdigest()
    except (OSError,subprocess.SubprocessError,UnicodeError,owner.E0InstalledControlError) as exc:
        raise NativeIssuerError('installed_issuer_source_unqualified') from exc


def _current(context):
    case._check_context(context)
    data=json.loads(context._body)
    owner._verify_source(ROOT,data['source_commit'],paths=FULL_SOURCE_PATHS)
    return data


def _issuer_metadata(context,closure_digest):
    binding=case._current_case_binding(context)
    return {'issuer_id':'MACRO_LINUX_NATIVE_E0_ISSUER','protocol':PROTOCOL,
        'source_commit':binding['source_commit'],'source_closure_sha256':closure_digest,
        'installation_id':binding['installation_id'],'installation_epoch':binding['installation_epoch'],
        'registration_ref':binding['registration_ref'],'publication_ref':binding['publication_ref'],
        'current_selection_sha256':binding['current_selection_sha256'],
        'current_access_ref':binding['current_access_ref'],'recipient_grant_ref':binding['recipient_grant_ref'],
        'broker_service_fingerprint':binding['broker_service_fingerprint'],
        'authority':'current_recipient_scoped_source_view_only'}


def _wire_schema(value,role):
    with owner._directory((ROOT/_SCHEMA).parent,private=False) as fd:
        schema=json.loads(owner._read(fd,Path(_SCHEMA).name,512*1024,private=False))
    schema.pop('oneOf',None);schema['$ref']='#/$defs/'+role
    validator=owner.control._INTEGER_VALIDATOR(schema)
    require(next(validator.iter_errors(value),None) is None,'wire_invalid')


def _pending(context,capability,source_before):
    _current(context);peer.require_current_broker_service(capability)
    require(_source_snapshot()==source_before,'source_or_selection_changed')
    result=_refusal('original_operation_pending_no_replay',True)
    _wire_schema(result,'response')
    return canonical(result)


def _input(body):
    return {'encoding':'base64','bytes':len(body),'sha256':sha256(body).hexdigest(),
            'body':base64.b64encode(body).decode('ascii')}


def _decode_input(value):
    require(type(value) is dict and set(value)=={'encoding','bytes','sha256','body'} and
        value['encoding']=='base64' and type(value['body']) is str,'original_input_unqualified')
    integer(value['bytes'],65536);digest(value['sha256'])
    try:body=base64.b64decode(value['body'],validate=True)
    except (ValueError,UnicodeError) as exc:raise NativeIssuerError('original_input_unqualified') from exc
    require(base64.b64encode(body).decode()==value['body'] and len(body)==value['bytes'] and
        sha256(body).hexdigest()==value['sha256'],'original_input_unqualified')
    case.packet.extract_selected_citations(body,input_sha256=value['sha256'])
    return body


def _original_selection(context,body):
    """Original source/epoch/refs and actual current access-chain ancestry."""
    original=decode(body,16384);data=_current(context)
    require(set(original)=={'schema','study_id','source_commit','control_refs'} and
        original['schema']==owner.SELECTED_SCHEMA and original['study_id']==data['intent']['study_id'] and
        original['source_commit']==data['source_commit'],'original_input_unqualified')
    fresh=case._resolve_current_case(context._peer,operation_id=data['operation_id'],intent=data['intent'])
    require(fresh._body==context._body and fresh._inputs==context._inputs,'source_or_selection_changed')
    current=decode(fresh._selection,16384);refs=original['control_refs'];head=current['control_refs']
    require(type(refs) is dict and set(refs)==set(head)==set(owner._CONTROL_KEYS),'original_input_unqualified')
    require(all(canonical(refs[k])==canonical(head[k]) for k in head if k!='access'),'original_input_unqualified')
    directory=case._CONTROL_ROOT/sha256(data['intent']['study_id'].encode()).hexdigest()
    def read(fd,ref,kind,identity):
        owner.control._domain_reference(ref)
        body=owner._read(fd,ref['sha256']+'.json',owner.control.MAX_CONTROL_BYTES)
        require(len(body)==ref['bytes'] and sha256(body).hexdigest()==ref['sha256'],'original_input_unqualified')
        value=owner.control.parse_e0_control_record(body,kind=kind)
        require(value[identity]==ref['object_id'] and value['schema']==ref['schema'],'original_input_unqualified')
        return value,body
    with owner._directory(directory,private=True) as fd:
        installed,_=read(fd,head['installation'],'installed_binding','installation_id')
        ref=head['access'];history=[];seen=set();found=False
        while ref is not None:
            require(ref['sha256'] not in seen and len(history)<owner.MAX_ACCESS_RECORDS,'original_input_unqualified')
            seen.add(ref['sha256']);state,raw=read(fd,ref,'access_state','access_state_id')
            history.append(raw);found|=canonical(ref)==canonical(refs['access']);ref=state['previous_state_ref']
        require(found,'original_input_unqualified')
        owner.validate_access_history(installation=installed,history=list(reversed(history)),as_of=case._clock())
        require(owner._read(fd,'SELECTED.json',16384)==fresh._selection,'source_or_selection_changed')
    _current(context)


def _envelope(context,packet_bytes,intent):
    data=_current(context)
    audience=case._original_recipient_fact(context,original_intent=intent)
    result={'schema':ENVELOPE,'operation_id':data['operation_id'],'intent':data['intent'],
        'original_intent':intent,'selection_b64':base64.b64encode(context._selection).decode('ascii'),
        'selection_sha256':sha256(context._selection).hexdigest(),
        'input':_input(packet_bytes),'original_recipient':audience}
    _wire_schema(result,'envelope')
    body=canonical(result);require(0<len(body)<=MAX_ENVELOPE,'case_input_size_bound');return body


def _qualify_envelope(context,body,operation_id,intent):
    value=decode(body,MAX_ENVELOPE);_wire_schema(value,'envelope');data=_current(context)
    require(set(value)=={'schema','operation_id','intent','original_intent','selection_b64',
        'selection_sha256','input','original_recipient'} and value['schema']==ENVELOPE and
        value['operation_id']==operation_id==data['operation_id'] and
        canonical(value['intent'])==canonical(data['intent']) and
        canonical(value['original_intent'])==canonical(intent)==canonical(case._original_case_intent(context)),
        'original_operation_intent_mismatch')
    require(type(value['selection_b64']) is str,'original_input_unqualified')
    try:selection=base64.b64decode(value['selection_b64'],validate=True)
    except (ValueError,UnicodeError) as exc:raise NativeIssuerError('original_input_unqualified') from exc
    require(base64.b64encode(selection).decode()==value['selection_b64'] and
        sha256(selection).hexdigest()==value['selection_sha256'],'original_input_unqualified')
    _original_selection(context,selection);_decode_input(value['input'])
    expected=case._original_recipient_fact(context,original_intent=value['original_intent'])
    require(canonical(value['original_recipient'])==canonical(expected),'original_input_unqualified')
    _current(context)
    return value


def _locator(value):
    original=value['original_intent'];binding=original['binding'];source=value['input']
    result={'case_id':'mme0case_'+sha256(canonical(original)).hexdigest(),
        'installation_id':binding['installation_id'],'installation_epoch':binding['installation_epoch'],
        'original_selection_sha256':value['selection_sha256'],
        'original_intent_sha256':sha256(canonical(original)).hexdigest(),
        'input_sha256':source['sha256'],'input_bytes':source['bytes']}
    locator(result);return result


def _refusal(reason,pending=False):
    if reason not in REASONS and reason!='original_operation_pending_no_replay':reason='current_control_unqualified'
    return {'schema':RESPONSE,'status':'ORIGINAL_OPERATION_PENDING' if pending else 'REFUSED',
        'reason':reason,'retry_authorized':False,'verification':dict(FALSE_FLAGS),'scientific_admission':False}


def exchange(request_bytes):
    """One fixed native action; no successful caller runtime or packet input."""
    try:
        req=request(request_bytes)
        source_before=_source_snapshot()
        capability=peer.observe_current_broker_service()
        context=case._resolve_current_case(capability,operation_id=req['operation_id'],intent=req['intent'])
        _current(context)
        result={'schema':RESPONSE,'status':'CURRENT_CASE_QUALIFIED','action':req['action'],
            'operation_id':req['operation_id'],'intent':req['intent'],
            'issuer':_issuer_metadata(context,source_before[1]),'verification':dict(FALSE_FLAGS),
            'scientific_admission':False,'retry_authorized':False}
        if req['action']!='qualify_current_case':
            store=case._reservation_store(context);intent=case._original_case_intent(context)
            def authorize(phase,operation,original):
                require(operation==req['operation_id'] and canonical(original)==canonical(intent),
                        'original_operation_intent_mismatch');_current(context)
            def qualify(body,operation,original):
                _qualify_envelope(context,body,operation,original)
            if req['action']=='prepare_case':
                def load():
                    # Only incumbent NEW callback may acquire genuine sources.
                    return _envelope(context,case._build_case_input(context),intent)
                body=_run_reserved_read(store,req['operation_id'],intent,
                    authorize=authorize,load=load,qualify=qualify)
                value=_qualify_envelope(context,body,req['operation_id'],intent)
                result.update(status='CASE_PREPARED',locator=_locator(value),input=value['input'])
            else:
                state,body=_read_original_case(store,req['operation_id'],intent,
                    authorize=authorize,qualify=qualify)
                if req['action']=='read_original_case':
                    result.update(status='ORIGINAL_CASE_STATE',operation_state=state)
                    if state=='COMPLETE':
                        value=_qualify_envelope(context,body,req['operation_id'],intent)
                        result.update(locator=_locator(value),input=value['input'])
                else:
                    if state=='PENDING':return _pending(context,capability,source_before)
                    require(state=='COMPLETE','original_operation_unavailable')
                    value=_qualify_envelope(context,body,req['operation_id'],intent)
                    original_locator=_locator(value)
                    require(canonical(req['locator'])==canonical(original_locator),'original_input_unqualified')
                    result.update(locator=original_locator)
                    if req['action']=='current_input':result.update(status='INPUT_CURRENT',input=value['input'])
                    else:
                        ref=req['result_ref'];require(ref['input_sha256']==value['input']['sha256'],'result_reference_mismatch')
                        result.update(status='RESULT_DISCLOSURE_CURRENT',result_ref=ref,
                            authorization={'purpose':'disclose_exact_original_untrusted_child_result',
                                'input_sha256':ref['input_sha256'],'result_sha256':ref['result_sha256'],
                                'result_bytes':ref['result_bytes'],'original_recipient':value['original_recipient']})
        # Original snapshot is not authorization cache. Fresh metadata and full
        # source/peer qualification bracket the final response on every path.
        _current(context);peer.require_current_broker_service(capability)
        result['issuer']=_issuer_metadata(context,source_before[1])
        require(_source_snapshot()==source_before,'source_or_selection_changed')
        _wire_schema(result,'response')
        encoded=canonical(result);require(len(encoded)<=MAX_RESPONSE,'case_input_size_bound')
        return encoded
    except E0ReservedReadError as exc:
        if str(exc)=='original_operation_pending_no_replay':
            try:return _pending(context,capability,source_before)
            except Exception:return canonical(_refusal('current_control_unqualified'))
        return canonical(_refusal('original_operation_unavailable'))
    except NativeIssuerError as exc:
        return canonical(_refusal(str(exc)))
    except peer.NativePeerError:
        return canonical(_refusal('broker_authentication_unqualified'))
    except case.NativeCaseError:
        return canonical(_refusal('native_recipient_grant_unavailable'))
    except Exception:
        # No source paths, payload, key/config, exception body or traceback in
        # public responses. UNKNOWN transport remains original carrier state.
        return canonical(_refusal('current_control_unqualified'))


def serve(input_stream,output_stream):
    """Fixed CLI one-frame exchange. No request controls streams or paths."""
    try:
        header=input_stream.read(4);require(type(header) is bytes and len(header)==4,'wire_invalid')
        length=struct.unpack('>I',header)[0];require(0<length<=MAX_REQUEST,'wire_bound')
        body=input_stream.read(length);require(len(body)==length and input_stream.read(1)==b'','wire_invalid')
        result=exchange(body)
    except Exception:
        result=canonical(_refusal('wire_invalid'))
    output_stream.write(struct.pack('>I',len(result))+result);output_stream.flush()
