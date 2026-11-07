"""Fixed selected native E0 service/recipient to original source evidence.

Internal issuer composition only. Peer authentication belongs to the separate
native peer owner; protocol/reservation sequencing belongs to the fixed issuer.
No caller path, policy, source rows or successful runtime is accepted. These
functions do not install grants, enroll services, initialize stores or admit a
study. Current native records and incumbent house source rights gate every use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import weakref

from . import market_memory_e0_installed_control as owner
from . import market_memory_e0_selected_condition as selected_condition
from . import market_memory_e0_task_evidence as tasks
from . import market_memory_e0_baselines as baselines
from . import market_memory_e0_participant_packet as packet
from .market_memory_e0_reservations import ReservationStore
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_trusted as trusted

_INSTALLED_ROOT = Path('/opt/macro')
_CONTROL_ROOT = _INSTALLED_ROOT / 'data/research_factory/market_memory_e0'
_SOURCE_ROOT = Path('/var/lib/macro-market-memory/public/trusted-v1')
_MODULE = 'engine/research_factory/market_memory_e0_native_case.py'
_SCHEMA = 'contracts/market_memory/e0_native_bindings.v3.schema.json'
_SERVICE = 'research_factory.market_memory_e0_native_service.v3'
_RECIPIENT = 'research_factory.market_memory_e0_native_recipient.v3'
_ACTIONS = frozenset(('prepare_case','current_input','authorize_result_disclosure','read_original_case','qualify_current_case'))
_EXTRA_SOURCES = (_MODULE, _SCHEMA,
    'engine/research_factory/market_memory_e0_native_peer.py',
    'engine/research_factory/market_memory_e0_participant_packet.py',
    'engine/neuralweb/market_memory_retained_use.py',
    'engine/neuralweb/market_memory_identity.py',
    use.AUTHORITY_RECORD)
_SOURCE_PATHS = tuple(dict.fromkeys((*selected_condition._SOURCES, *_EXTRA_SOURCES)))
_TOKEN = object()
_ISSUED = weakref.WeakKeyDictionary()


class NativeCaseError(ValueError):
    """Stable source refusal, with no private source/grant body."""


def _require(value, reason):
    if not value:
        raise NativeCaseError(reason)


def _canonical(value):
    owner.control._bounded_tree(value,domain=True)
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _clock():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')


def _peer_owner():
    # Fixed import, never selected by a request or supplied callback.
    from . import market_memory_e0_native_peer
    return market_memory_e0_native_peer


def _peer_binding(capability):
    peer = _peer_owner()
    _require(type(capability) is peer.NativeBrokerServiceCapability,
             'native_broker_service_capability_required')
    _require(peer.require_current_broker_service(capability) is None, 'native_peer_contract')
    binding = peer.broker_service_binding(capability)
    _require(type(binding) is dict and set(binding) == {
        'ssh_key_fingerprint','restriction_profile','forced_command','native_observation_sha256',
        'native_executable','journal_profile'},
        'native_peer_binding_required')
    _require(type(binding['native_observation_sha256']) is str and
             re.fullmatch(r'[a-f0-9]{64}',binding['native_observation_sha256']),
             'native_peer_binding_required')
    return _canonical(binding)


def _verify_source(commit):
    owner._verify_source(_INSTALLED_ROOT, commit, paths=_SOURCE_PATHS)
    # The frozen allocator has its own exact original source pin.
    relative = 'engine/research_factory/market_memory_e0_allocation.py'
    with owner._directory((_INSTALLED_ROOT / relative).parent, private=False) as fd:
        body = owner._read(fd, Path(relative).name,
                           selected_condition.binding.ALLOCATOR_SOURCE_BYTES, private=False)
    _require(len(body) == selected_condition.binding.ALLOCATOR_SOURCE_BYTES and
             sha256(body).hexdigest() == selected_condition.binding.ALLOCATOR_SOURCE_SHA256,
             'installed_allocator_bytes_mismatch')
    # Imported owner code must be the installed code whose bytes were checked.
    for relative in _SOURCE_PATHS:
        if not relative.endswith('.py') or relative.startswith('scripts/'):
            continue
        name = relative[:-3].replace('/','.')
        if name.endswith('.__init__'):
            name = name[:-9]
        module = sys.modules.get(name)
        if module is not None:
            _require(Path(module.__file__).resolve() == _INSTALLED_ROOT / relative,
                     'native_case_import_origin_mismatch')


def _source_rights():
    """Incumbent purpose parser, bracketed by native fixed-file custody."""
    def read(relative):
        path=_INSTALLED_ROOT/relative
        with owner._directory(path.parent,private=False) as fd:
            return owner._read(fd,path.name,64*1024,private=False)
    before=tuple(read(relative) for relative in (use.REGISTRATION,use.AUTHORITY_RECORD))
    registration,digest=use.load_registration(_INSTALLED_ROOT)
    _require(sha256(before[0]).hexdigest()==digest and
             sha256(before[1]).hexdigest()==registration['source_authority']['sha256'] and
             before==tuple(read(relative) for relative in (use.REGISTRATION,use.AUTHORITY_RECORD)),
             'native_source_rights_changed')
    return registration,digest


def _read_reference(fd, reference, *, schema=None):
    ref = owner.control._domain_reference(reference)
    if schema is not None:
        _require(ref['schema'] == schema, 'native_binding_reference_kind_required')
    body = owner._read(fd, ref['sha256']+'.json', owner.control.MAX_DOMAIN_OBJECT_BYTES)
    _require(len(body) == ref['bytes'] and sha256(body).hexdigest() == ref['sha256'],
             'native_binding_reference_bytes_mismatch')
    value = owner.control._domain_json(body)
    _require(type(value) is dict and value.get('schema') == ref['schema'] and
             value.get('object_id') == ref['object_id'] and _canonical(value) == body,
             'native_binding_reference_identity_mismatch')
    return value, body


def _binding_record(value, role):
    # Schema itself is in the selected source-byte closure before it is read.
    from jsonschema import FormatChecker
    with owner._directory((_INSTALLED_ROOT/_SCHEMA).parent, private=False) as fd:
        schema = json.loads(owner._read(fd, Path(_SCHEMA).name, 128*1024, private=False))
    schema['$ref'] = '#/$defs/'+role
    schema.pop('oneOf', None)
    validator = owner.control._INTEGER_VALIDATOR(schema, format_checker=FormatChecker())
    _require(next(validator.iter_errors(value), None) is None, 'closed_native_binding_required')


def _validate_request(operation_id, intent):
    _require(type(operation_id) is str and owner.control._ID.fullmatch(operation_id),
             'original_operation_required')
    _require(type(intent) is dict and set(intent) == {
        'study_id','root_id','operator_run_id','child_run_id','participant_binding_sha256'},
        'native_original_intent_required')
    for key, value in intent.items():
        pattern = r'[a-f0-9]{64}' if key == 'participant_binding_sha256' else owner.control._ID
        _require(type(value) is str and re.fullmatch(pattern,value), 'native_original_intent_required')
    return _canonical(intent)


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False, init=False, repr=False)
class NativeE0CaseContext:
    _body: bytes
    _digest: str
    _inputs: tuple
    _peer: object
    _peer_binding: bytes
    _selection: bytes
    _seal: object

    def __init__(self, *args, **kwargs):
        raise NativeCaseError('owner_native_case_factory_required')

    def __copy__(self):
        raise NativeCaseError('native_case_not_serializable')

    def __deepcopy__(self, memo):
        raise NativeCaseError('native_case_not_serializable')

    def __reduce__(self):
        raise NativeCaseError('native_case_not_serializable')


def _resolve_current_case(capability, *, operation_id, intent):
    """Internal fixed owner resolution; JSON intent is an equality constraint."""
    intent_bytes = _validate_request(operation_id,intent)
    binding = _peer_binding(capability)
    study_id = intent['study_id']
    directory = _CONTROL_ROOT / sha256(study_id.encode()).hexdigest()

    def prepare(fd, selected, records, registration_bytes):
        access, installed, reg = records['access'],records['installation'],records['registration']
        _require(access['status'] == 'active' and access['contamination_state'] == 'clean' and
            {'read_e0_registration','disclose_e0_registration','read_registered_condition_outputs'}
            <= set(installed['permitted_actions']), 'current_native_case_access_required')
        service,service_bytes = _read_reference(fd,installed['admin_receipt_ref'],schema=_SERVICE)
        recipient,recipient_bytes = _read_reference(fd,access['scope_ref'],schema=_RECIPIENT)
        _binding_record(service,'service');_binding_record(recipient,'recipient')
        for name in ('installation_id','installation_epoch','registration_ref','publication_ref'):
            _require(_canonical(service[name]) == _canonical(installed[name]) and
                     _canonical(recipient[name]) == _canonical(installed[name]),
                     'native_service_installation_binding_mismatch')
        _require(service['source_commit'] == selected['source_commit'] and
            recipient['service_ref'] == installed['admin_receipt_ref'] and
            recipient['owner_principal_ref'] == installed['owner_principal_ref'] and
            recipient['operation_id'] == operation_id and _canonical(recipient['intent']) == intent_bytes,
            'native_recipient_intent_mismatch')
        actual_peer = json.loads(binding)
        _require(all(service[key] == actual_peer[key] for key in
                ('ssh_key_fingerprint','restriction_profile','forced_command','native_executable','journal_profile')),
                'native_service_peer_mismatch')
        _require(recipient['protected_mode'] == service['protected_mode'] == 'PROTECTED_MEMORY_EXECUTION'
            and set(recipient['actions']) == _ACTIONS,
            'native_protected_recipient_required')
        original_recipient=recipient['original_recipient']
        _require(original_recipient['recipient_kind']=='native_broker_service' and
            original_recipient['principal_ref']==installed['admin_receipt_ref'] and
            original_recipient['ssh_key_fingerprint']==actual_peer['ssh_key_fingerprint'] and
            set(recipient['recipient_permissions'])=={
                'delegate_original_child_input','read_original_child_result'},
            'native_original_service_recipient_required')
        # Protected owner/admission refs are native administrative bindings, NOT
        # claimed observations of an M2 process or a key/ThreadID-derived mode.
        for name in ('protected_owner_ref','control_admission_ref'):
            owner.control._domain_reference(recipient[name])
        plan,plan_bytes = _read_reference(fd,reg['reviewer_plan_ref'],
                                          schema=owner.control._REVIEWER_PLAN_SCHEMA)
        owner.control._validate_reviewer_plan_declaration(plan,plan_bytes,reg)
        reviewer = recipient['reviewer_principal_ref']
        _require(any(row['principal_ref'] == reviewer for row in plan['reviewers']),
                 'original_reviewer_recipient_required')
        assignments = [row for row in plan['assignments'] if row['task_id'] == recipient['task_id']]
        _require(len(assignments) == 1 and reviewer['object_id'] in assignments[0]['reviewer_principal_ids'],
                 'original_reviewer_task_assignment_required')
        inputs,assignment,condition = selected_condition._prepare_condition_bytes(fd,selected,records,
            registration_bytes,task_id=recipient['task_id'],slot=recipient['slot'])
        bodies = dict(zip(owner._INPUT_NAMES,inputs))
        method,_ = tasks.resolve_registered_task_inputs(**bodies)
        task_manifest = owner.control._domain_json(bodies['task_manifest'])
        task = next(row for row in task_manifest['tasks'] if row['task_id'] == recipient['task_id'])
        scope = recipient['source_use']
        registration,source_registration_sha = _source_rights()
        expected_corpus = {key:reg['corpus'][key] for key in
                           ('profile','store_id','generation_id','generation_sha256')}
        _require(_canonical(scope['corpus']) == _canonical(expected_corpus) and
            scope['source_registration_sha256'] == source_registration_sha and
            scope['source_authority_sha256'] == registration['source_authority']['sha256'] and
            all(scope[key] == task[field] for key,field in
                (('subject_id','subject_id'),('query_cutoff','analysis_cutoff'),('mode','mode'),('k','k'))) and
            _canonical(scope['method_spec']) == _canonical(method.disclosure()) and
            method.purge_calendar_days == registration['method']['purge_calendar_days'] and
            method.embargo_calendar_days == registration['method']['embargo_calendar_days'] and
            scope['maximum_looks'] == access['budget']['maximum_looks'],
            'native_source_scope_or_method_mismatch')
        _require(scope['subject_id'] in registration['allowed_subject_ids'] and
            scope['corpus']['store_id'] == registration['store_id'] and
            scope['mode'] in registration['modes'], 'current_house_source_scope_required')
        # Additional payloads are not in _load_selected_control's cached five
        # controls, therefore explicitly bracket their exact named bytes too.
        for ref,original in ((installed['admin_receipt_ref'],service_bytes),
                             (access['scope_ref'],recipient_bytes),
                             (reg['reviewer_plan_ref'],plan_bytes)):
            _require(owner._read(fd,ref['sha256']+'.json',owner.control.MAX_DOMAIN_OBJECT_BYTES)==original,
                     'native_binding_changed_during_resolution')
        data = {'operation_id':operation_id,'intent':json.loads(intent_bytes),
            'service_ref':installed['admin_receipt_ref'],'recipient_ref':access['scope_ref'],
            'service':service,'recipient':recipient,'source_commit':selected['source_commit'],
            'registration_ref':selected['control_refs']['registration'],
            'publication_ref':selected['control_refs']['publication'],
            'installation_id':installed['installation_id'],'installation_epoch':installed['installation_epoch'],
            'owner_principal_ref':installed['owner_principal_ref'],'reviewer_plan_ref':reg['reviewer_plan_ref'],
            'task':task,'condition':condition,'assignment_sha256':sha256(assignment).hexdigest(),
            'source_registration_sha256':source_registration_sha}
        return _canonical(data),tuple(inputs)

    (body,inputs),selection = owner._load_selected_control(directory,study_id,_verify_source,
                                                        clock=_clock,prepare=prepare)
    _require(_peer_binding(capability) == binding, 'native_peer_changed_during_resolution')
    # Only this actual native resolver can issue an instance. The registry
    # retains immutable original integrity, never current permission.
    result=object.__new__(NativeE0CaseContext)
    values=(body,sha256(body).hexdigest(),inputs,capability,binding,selection,_TOKEN)
    for name,value in zip(('_body','_digest','_inputs','_peer','_peer_binding','_selection','_seal'),values,strict=True):
        object.__setattr__(result,name,value)
    _ISSUED[result]=values
    return result


def _context_snapshot(context):
    _require(type(context) is NativeE0CaseContext, 'owner_native_case_required')
    issued=_ISSUED.get(context)
    _require(issued is not None, 'owner_native_case_factory_required')
    try:
        values=(context._body,context._digest,context._inputs,context._peer,
                context._peer_binding,context._selection,context._seal)
    except AttributeError as exc:
        raise NativeCaseError('owner_native_case_required') from exc
    _require(values==issued and values[2] is issued[2] and values[3] is issued[3]
             and values[6] is issued[6], 'native_case_issued_state_changed')
    body,digest,inputs,peer,binding,selection,seal=values
    _require(seal is _TOKEN and type(body) is bytes and
             0 < len(body) <= owner.control.MAX_DOMAIN_TOTAL_BYTES and
             type(digest) is str and sha256(body).hexdigest()==digest and
             type(binding) is bytes and 0 < len(binding) <= 16384 and
             type(selection) is bytes and 0 < len(selection) <= 16384 and
             type(inputs) is tuple and len(inputs)==4 and
             all(type(x) is bytes and 0 < len(x) <= owner.control.MAX_DOMAIN_OBJECT_BYTES
                 for x in inputs), 'owner_native_case_required')
    return values


def _check_context(context):
    before=_context_snapshot(context)
    data=json.loads(before[0])
    current=_resolve_current_case(before[3],operation_id=data['operation_id'],intent=data['intent'])
    after=_context_snapshot(context)
    _require(current._body == before[0] and current._inputs == before[2] and
             current._peer_binding == before[4] and
             after == before and after[2] is before[2] and after[3] is before[3]
             and after[6] is before[6], 'native_case_binding_changed')
    return data


class _NativeE0SourcePolicy(use.RetainedHouseUsePolicy):
    """Existing source-right checks under the actual fixed E0 native principal."""
    def __init__(self, context, *, _key=None):
        _require(_key is _TOKEN,'owner_native_case_required')
        self._context=context
        self.root=_INSTALLED_ROOT
        data=_check_context(context);scope=data['recipient']['source_use']
        self._bind_source_scope(**{key:scope['corpus'][key] for key in
                ('store_id','generation_id','generation_sha256')},
            subject_id=scope['subject_id'],query_cutoff=scope['query_cutoff'],mode=scope['mode'])
        self.policy_id='market_memory.native_e0.v3:'+self.registration_sha256+':'+data['recipient_ref']['sha256']

    def _enforce_current_principal(self):
        _check_context(self._context)


def _build_case_input(context):
    """Genuine registered native sources -> shipped packet, no storage effects."""
    before=_context_snapshot(context)
    data=_check_context(context);scope=data['recipient']['source_use'];task=data['task']
    policy=_NativeE0SourcePolicy(context,_key=_TOKEN)
    reader=trusted.TrustedFileAsKnownAtReader(_SOURCE_ROOT,mode='operational_pit')
    generation=reader.read_pinned_generation(generation_id=scope['corpus']['generation_id'],
                                            maximum_capture_count=256)
    _require(all(getattr(generation,key)==scope['corpus'][key] for key in
        ('profile','store_id','generation_id','generation_sha256')), 'native_original_generation_required')
    population=cohort.read_retained_context_cohort(reader,generation,
            subject_id=task['subject_id'],query_cutoff=task['analysis_cutoff'],policy=policy)
    query=features.read_episode_feature_capability(reader,generation,
            query_id=task['query_id'],subject_id=task['subject_id'],
            query_cutoff=task['analysis_cutoff'],policy=policy)
    method,_=tasks.resolve_registered_task_inputs(**dict(zip(owner._INPUT_NAMES,context._inputs)))
    selection=baselines.build_condition_selections(population,query,policy=policy,k=task['k'],method=method)
    evidence=tasks.build_registered_task_condition_evidence(selection,reader,generation,
        **dict(zip(owner._INPUT_NAMES,context._inputs)),task_id=task['task_id'],policy=policy)
    result=packet.build_task_condition_packet(evidence,condition=data['condition'],policy=policy)
    _check_context(context)
    after=_context_snapshot(context)
    _require(before==after and before[2] is after[2] and before[3] is after[3]
             and before[6] is after[6], 'native_case_changed_during_source_read')
    return result


def _current_case_binding(context):
    """Fresh internal issuer metadata; never public task/condition disclosure."""
    before=_context_snapshot(context)
    data=_check_context(context)
    current=_resolve_current_case(before[3],operation_id=data['operation_id'],intent=data['intent'])
    selected=json.loads(current._selection)
    after=_context_snapshot(context)
    _require(current._body==before[0] and current._inputs==before[2]
             and current._peer_binding==before[4] and before==after
             and before[3] is after[3] and before[6] is after[6],
             'native_case_changed_during_binding')
    return {'source_commit':data['source_commit'],
            'installation_id':data['installation_id'],'installation_epoch':data['installation_epoch'],
            'registration_ref':data['registration_ref'],'publication_ref':data['publication_ref'],
            'service_ref':data['service_ref'],'recipient_grant_ref':data['recipient_ref'],
            'current_selection_sha256':sha256(current._selection).hexdigest(),
            'current_access_ref':selected['control_refs']['access'],
            'broker_service_fingerprint':json.loads(current._peer_binding)['ssh_key_fingerprint']}


def _original_case_intent(context):
    """Immutable original binding; excludes future input and changing access."""
    data=_check_context(context)
    return {'schema':'research_factory.market_memory_e0_native_case_intent.v3',
            'packet_schema':packet.SCHEMA,'binding':json.loads(context._body)}


def _original_recipient_fact(context, *, original_intent):
    """Expected exact service audience after original store/envelope custody.

    The fixed protocol must already authenticate its retained original using
    ReservationStore/recovery. A supplied matching dict is only an equality
    constraint, not proof that an original reservation exists or is complete.
    No response caller field constructs the returned native-admin fact.
    """
    expected=_original_case_intent(context)
    _require(type(original_intent) is dict and _canonical(original_intent)==_canonical(expected),
             'original_native_case_intent_mismatch')
    data=_check_context(context)
    recipient=data['recipient']['original_recipient']
    return {'schema':'research_factory.market_memory_e0_original_recipient.v3',
            'recipient_kind':recipient['recipient_kind'],'principal_ref':recipient['principal_ref'],
            'ssh_key_fingerprint':recipient['ssh_key_fingerprint'],
            'original_operation_id':data['operation_id'],
            'pre_input_intent_sha256':sha256(_canonical(data['intent'])).hexdigest()}


def _reservation_store(context):
    """Fixed original existing store; no initialization/reservation is performed."""
    data=_check_context(context)
    directory=_CONTROL_ROOT/sha256(data['intent']['study_id'].encode()).hexdigest()/'reservations'
    binding={'study_id':data['intent']['study_id'],'installation_id':data['installation_id'],
             'installation_epoch':data['installation_epoch'],
             'registration_sha256':data['registration_ref']['sha256'],
             'publication_sha256':data['publication_ref']['sha256']}
    with owner._directory(directory,private=True):
        store=ReservationStore(directory,binding);snapshot=store.snapshot()
    _require(snapshot['maximum_looks']==data['recipient']['source_use']['maximum_looks'],
             'native_original_look_limit_mismatch')
    _check_context(context)
    return store
