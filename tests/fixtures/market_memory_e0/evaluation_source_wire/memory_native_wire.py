"""Closed native issuer framing DATA. Validation never authenticates an issuer."""
from __future__ import annotations
import base64
import hashlib
import json
import re

SUFFIX = b'\n\nReturn a bounded final response of at most 12000 characters. Do not delegate further.\n'
FLAGS = {k: False for k in ('authenticated', 'qualification_verified', 'independence_verified', 'exposure_verified', 'operational_admission')}
ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)
SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)
REASONS = frozenset('wire_invalid wire_bound broker_service_not_enrolled broker_authentication_unqualified broker_confinement_unqualified installed_issuer_source_unqualified native_recipient_grant_unavailable native_intent_mismatch current_control_unqualified current_source_rights_unqualified selected_case_unqualified source_or_selection_changed original_operation_unavailable original_operation_intent_mismatch original_input_unqualified result_reference_mismatch case_input_size_bound adjudicator_stage_unavailable'.split())

class WireRefused(ValueError):
    def __init__(self): super().__init__('memory_issuer_wire_refused')

def fail(): raise WireRefused()

def canonical(value):
    try: return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError): raise WireRefused() from None

def exact(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()): fail()

def token(value):
    if type(value) is not str or not ID.fullmatch(value): fail()

def digest(value):
    if type(value) is not str or not SHA.fullmatch(value): fail()

def integer(value, upper):
    if type(value) is not int or not 1 <= value <= upper: fail()

def _tree(value, depth=0, budget=None):
    if budget is None: budget = [8192]
    budget[0] -= 1
    if budget[0] < 0 or depth > 16: fail()
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str: fail()
            _tree(item, depth+1, budget)
    elif type(value) is list:
        for item in value: _tree(item, depth+1, budget)
    elif type(value) not in (str, int, bool, type(None)): fail()

def parse(raw, maximum):
    if type(raw) is not bytes or not 1 <= len(raw) <= maximum: fail()
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: fail()
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: fail())
        _tree(value)
        if canonical(value) != raw: fail()
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError): raise WireRefused() from None

def _unframe(raw, maximum):
    if type(raw) is not bytes or not 5 <= len(raw) <= maximum+4: fail()
    if int.from_bytes(raw[:4], 'big') != len(raw)-4: fail()
    return parse(raw[4:], maximum)

def _intent(value):
    exact(value, 'study_id root_id operator_run_id child_run_id participant_binding_sha256')
    for key in ('study_id', 'root_id', 'operator_run_id', 'child_run_id'): token(value[key])
    digest(value['participant_binding_sha256'])

def locator(value):
    exact(value, 'case_id installation_id installation_epoch original_selection_sha256 original_intent_sha256 input_sha256 input_bytes')
    for key in ('case_id', 'installation_id', 'installation_epoch'): token(value[key])
    for key in ('original_selection_sha256', 'original_intent_sha256', 'input_sha256'): digest(value[key])
    integer(value['input_bytes'], 65536)

def result_ref(value):
    exact(value, 'attempt_id input_sha256 result_sha256 result_bytes')
    token(value['attempt_id']); digest(value['input_sha256']); digest(value['result_sha256']); integer(value['result_bytes'], 65536)

def validate_request(value):
    _tree(value)
    if type(value) is not dict: fail()
    schema = value.get('schema')
    if type(schema) is not str or schema not in ('research_factory.market_memory_e0_native_issuer_request.v1', 'research_factory.market_memory_e0_native_issuer_request.v2', 'research_factory.market_memory_e0_native_issuer_request.v3'): fail()
    version = schema[-2:]
    action = value.get('action')
    actions={'prepare_case','current_input','authorize_result_disclosure'}
    if version in ('v2','v3'):actions.add('read_original_case')
    if version=='v3':actions.add('qualify_current_case')
    if type(action) is not str or action not in actions: fail()
    extra = '' if action in ('prepare_case', 'read_original_case','qualify_current_case') else ' locator'
    if action == 'authorize_result_disclosure': extra += ' result_ref'
    exact(value, 'schema action operation_id intent'+extra)
    token(value['operation_id']); _intent(value['intent'])
    if 'locator' in value: locator(value['locator'])
    if 'result_ref' in value:
        result_ref(value['result_ref'])
        if value['result_ref']['input_sha256'] != value['locator']['input_sha256']: fail()
    if len(canonical(value)) > 16384: fail()
    return parse(canonical(value), 16384)

def _reference(value):
    exact(value, 'schema object_id sha256 bytes')
    token(value['schema']); token(value['object_id']); digest(value['sha256']); integer(value['bytes'], 4194304)

def fingerprint(value):
    if type(value) is not str or not value.startswith('SHA256:'):fail()
    try:
        raw=base64.b64decode(value[7:]+'=',validate=True)
        if len(raw)!=32 or base64.b64encode(raw).decode().rstrip('=')!=value[7:]:fail()
    except (ValueError,TypeError):raise WireRefused() from None

def original_recipient(value,*,request=None,issuer=None):
    exact(value,'schema recipient_kind principal_ref ssh_key_fingerprint original_operation_id pre_input_intent_sha256')
    if (value['schema']!='research_factory.market_memory_e0_original_recipient.v3'
            or value['recipient_kind']!='native_broker_service'):fail()
    _reference(value['principal_ref']);fingerprint(value['ssh_key_fingerprint'])
    token(value['original_operation_id']);digest(value['pre_input_intent_sha256'])
    if request is not None and (value['original_operation_id']!=request['operation_id']
            or value['pre_input_intent_sha256']!=hashlib.sha256(canonical(request['intent'])).hexdigest()):fail()
    if issuer is not None and value['ssh_key_fingerprint']!=issuer['broker_service_fingerprint']:fail()
    return parse(canonical(value),16384)

def _issuer(value, version):
    exact(value, 'issuer_id protocol source_commit source_closure_sha256 installation_id installation_epoch registration_ref publication_ref current_selection_sha256 current_access_ref recipient_grant_ref broker_service_fingerprint authority')
    if (value['issuer_id'] != 'MACRO_LINUX_NATIVE_E0_ISSUER' or value['protocol'] != 'memory.e0.native_issuer.'+version
            or value['authority'] != 'current_recipient_scoped_source_view_only'): fail()
    if type(value['source_commit']) is not str or re.fullmatch(r'(?:[a-f0-9]{40}|[a-f0-9]{64})', value['source_commit']) is None: fail()
    for key in ('source_closure_sha256', 'current_selection_sha256'): digest(value[key])
    for key in ('installation_id', 'installation_epoch'): token(value[key])
    for key in ('registration_ref', 'publication_ref', 'current_access_ref', 'recipient_grant_ref'): _reference(value[key])
    fingerprint(value['broker_service_fingerprint'])

def packet(value, loc):
    exact(value, 'encoding bytes sha256 body')
    if value['encoding'] != 'base64' or type(value['body']) is not str: fail()
    integer(value['bytes'], 65536); digest(value['sha256'])
    try:
        raw = base64.b64decode(value['body'], validate=True)
        raw.decode('utf-8')
        if (base64.b64encode(raw).decode() != value['body'] or b'\0' in raw
                or len(raw) != value['bytes'] or hashlib.sha256(raw).hexdigest() != value['sha256']
                or len(raw) != loc['input_bytes'] or value['sha256'] != loc['input_sha256']
                or not raw.endswith(SUFFIX) or raw.count(SUFFIX) != 1): fail()
        return raw
    except (ValueError, TypeError, UnicodeError): raise WireRefused() from None

def validate_response(value, *, request):
    req = validate_request(request); _tree(value)
    if type(value) is not dict: fail()
    version = req['schema'][-2:]
    if value.get('schema') != 'research_factory.market_memory_e0_native_issuer_response.'+version: fail()
    if (type(value.get('verification')) is not dict or set(value['verification']) != set(FLAGS)
            or any(value['verification'][k] is not False for k in FLAGS)
            or value.get('scientific_admission') is not False or value.get('retry_authorized') is not False): fail()
    status = value.get('status')
    if status in ('REFUSED', 'ORIGINAL_OPERATION_PENDING'):
        exact(value, 'schema status reason retry_authorized verification scientific_admission')
        if status == 'ORIGINAL_OPERATION_PENDING':
            if value['reason'] != 'original_operation_pending_no_replay': fail()
        elif type(value['reason']) is not str or value['reason'] not in REASONS: fail()
        return parse(canonical(value), 262144)
    action = req['action']
    expected = {'prepare_case': 'CASE_PREPARED', 'current_input': 'INPUT_CURRENT',
        'authorize_result_disclosure': 'RESULT_DISCLOSURE_CURRENT', 'read_original_case': 'ORIGINAL_CASE_STATE',
        'qualify_current_case':'CURRENT_CASE_QUALIFIED'}[action]
    if status != expected or value.get('action') != action or value.get('operation_id') != req['operation_id'] or value.get('intent') != req['intent']: fail()
    common = 'schema status action operation_id intent issuer verification scientific_admission retry_authorized'
    if action == 'read_original_case':
        state = value.get('operation_state')
        if type(state) is not str or state not in {'ABSENT', 'PENDING', 'COMPLETE'}: fail()
        exact(value, common+' operation_state'+(' locator input' if state == 'COMPLETE' else ''))
    elif action=='qualify_current_case':exact(value,common)
    elif action in ('prepare_case', 'current_input'): exact(value, common+' locator input')
    else: exact(value, common+' locator result_ref authorization')
    _issuer(value['issuer'], version)
    if 'locator' in value:
        loc = value['locator']; locator(loc)
        if loc['installation_id'] != value['issuer']['installation_id'] or loc['installation_epoch'] != value['issuer']['installation_epoch']: fail()
        if 'locator' in req and loc != req['locator']: fail()
        if 'input' in value: packet(value['input'], loc)
    if action == 'authorize_result_disclosure':
        if value['result_ref'] != req['result_ref']: fail()
        auth = value['authorization']; exact(auth, 'purpose input_sha256 result_sha256 result_bytes'+(' original_recipient' if version=='v3' else ''))
        expected_auth=dict(purpose='disclose_exact_original_untrusted_child_result', **{k:req['result_ref'][k] for k in ('input_sha256','result_sha256','result_bytes')})
        if version=='v3':expected_auth['original_recipient']=original_recipient(auth['original_recipient'],request=req,issuer=value['issuer'])
        if auth != expected_auth: fail()
    return parse(canonical(value), 262144)

def encode_request(value):
    raw = canonical(validate_request(value)); return len(raw).to_bytes(4, 'big')+raw

def decode_request(raw): return validate_request(_unframe(raw, 16384))
def decode_response(raw, *, request): return validate_response(_unframe(raw, 262144), request=request)
