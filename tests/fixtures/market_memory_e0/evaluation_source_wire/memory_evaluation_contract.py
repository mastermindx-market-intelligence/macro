"""Prospective evaluation DATA. Nothing in this module issues authority.

This is a separate purpose, never an extension of the frozen v3 SERVICE grant.
Canonical actor mappings are reasoned assessor attestations, not provider claims.
"""
from __future__ import annotations
import hashlib
import json
from common import memory_native_wire as w

DELEGATION = 'mastermind.memory_evaluation_delegation.v1'
FRAME = 'mastermind.ceo_ingress.memory_evaluation_assessment.v1'
REQUEST = 'research_factory.market_memory_e0_evaluation_issuer_request.v1'
RESPONSE = 'research_factory.market_memory_e0_evaluation_issuer_response.v1'
PROFILE = 'native-model-custody-assessment.v1'
GUIDE_SHA = '4efc664f6c86f5af6a62ac4fd8b98ae37ae130fa18ecfa7bdf0a88b399a71696'
ROLES = ('reviewer_1', 'reviewer_2', 'adjudicator')
ACTIONS = ['admit_evaluator', 'assign_evaluation', 'retain_annotation', 'retain_resolution']
OBSERVED = ['owned_process', 'protected_credential_object', 'fixed_model_profile']
LIMITS = ['canonical_actor_mapping_is_assessor_attestation',
          'provider_served_identity_not_attested', 'model_pretraining_risk_not_removed',
          'semantic_blinding_not_established']

def fail():
    raise ValueError('memory_evaluation_unavailable')

def digest(value):
    return hashlib.sha256(w.canonical(value)).hexdigest()

def text(value, maximum=4096):
    if type(value) is not str or not value.strip() or len(value.encode()) > maximum:
        fail()
    return value

def refs(value):
    w._reference(value)
    return value

def delegation(value):
    w.exact(value, 'schema enabled generation study_root study_id root_job_id registration_ref reviewer_plan_ref guide_ref source_purpose_ref source_audience decision_ref principal_binding_digest actions evidence_profile not_before_ms expires_at_ms')
    if (value['schema'] != DELEGATION or type(value['enabled']) is not bool
            or value['actions'] != ACTIONS or value['evidence_profile'] != PROFILE):
        fail()
    for k in ('generation', 'study_root', 'study_id', 'root_job_id'):
        w.token(value[k])
    for k in ('registration_ref', 'reviewer_plan_ref', 'guide_ref', 'source_purpose_ref', 'decision_ref'):
        refs(value[k])
    w.digest(value['principal_binding_digest'])
    audience(value['source_audience'])
    if value['guide_ref']['sha256'] != GUIDE_SHA:
        fail()
    for k in ('not_before_ms', 'expires_at_ms'):
        w.integer(value[k], 100_000_000_000_000)
    if not 0 < value['expires_at_ms'] - value['not_before_ms'] <= 14_400_000:
        fail()
    return json.loads(w.canonical(value))

def audience(value):
    w.exact(value, 'receiver_kind service_key_fingerprint control_service_label')
    if (value['receiver_kind'] != 'native_evaluation_custodian'
            or value['control_service_label'] != 'com.mastermind.executive.control'): fail()
    w.fingerprint(value['service_key_fingerprint'])
    return value

def assessment(value):
    w.exact(value, 'schema command_id work_ref participant_slot decision criteria canonical_actor_ref identity_mapping_ref limitations')
    if value['schema'] != FRAME or value['participant_slot'] not in ROLES or value['decision'] not in ('ADMIT', 'REFUSE'):
        fail()
    w.token(value['command_id']); text(value['work_ref'], 256)
    for k in ('canonical_actor_ref', 'identity_mapping_ref'):
        refs(value[k])
    if value['limitations'] != LIMITS or type(value['criteria']) is not list or not 1 <= len(value['criteria']) <= 32:
        fail()
    seen = []
    for c in value['criteria']:
        w.exact(c, 'criterion_id evidence_ref finding reason')
        w.token(c['criterion_id']); refs(c['evidence_ref']); text(c['reason'])
        if c['finding'] not in ('SATISFIED', 'UNRESOLVED', 'CONFLICT'):
            fail()
        seen.append(c['criterion_id'])
    if seen != sorted(set(seen)):
        fail()
    return json.loads(w.canonical(value))

def request(value):
    w.exact(value, 'schema action delegation subject assignment input_sha256 pair_sha256')
    if value['schema'] != REQUEST or value['action'] not in ('read_evaluation_basis', 'authorize_evaluation_subject_read', 'authorize_annotation_exposure', 'authorize_adjudication_exposure'):
        fail()
    delegation(value['delegation'])
    # The source owner matches these exact retained identities to its grant.
    if value['subject'] is not None:
        w.exact(value['subject'], 'operation_id attempt_id input_sha256 input_bytes result_sha256 result_bytes')
        for k in ('operation_id', 'attempt_id'): w.token(value['subject'][k])
        for k in ('input_sha256', 'result_sha256'): w.digest(value['subject'][k])
        for k in ('input_bytes', 'result_bytes'): w.integer(value['subject'][k], 65536)
    for k in ('assignment', 'input_sha256', 'pair_sha256'):
        if value[k] is not None: w.digest(value[k])
    if value['action'] == 'read_evaluation_basis':
        if any(value[k] is not None for k in ('subject', 'assignment', 'input_sha256', 'pair_sha256')): fail()
    elif value['action'] == 'authorize_evaluation_subject_read':
        if value['subject'] is None or value['assignment'] is None or value['input_sha256'] is not None: fail()
    elif any(value[k] is None for k in ('subject', 'assignment', 'input_sha256')):
        fail()
    if (value['action'] == 'authorize_adjudication_exposure') != (value['pair_sha256'] is not None):
        fail()
    return json.loads(w.canonical(value))

def response(value, original):
    request(original)
    w.exact(value, 'schema state request_sha256 source_purpose_ref source_owner generation not_before_ms expires_at_ms basis verification scientific_admission')
    if (value['schema'] != RESPONSE or value['state'] != 'CURRENT'
            or value['request_sha256'] != digest(original)
            or value['source_purpose_ref'] != original['delegation']['source_purpose_ref']
            or value['verification'] != w.FLAGS or value['scientific_admission'] is not False):
        fail()
    w.token(value['generation'])
    source = value['source_owner']
    w.exact(source, 'installation_id installation_epoch service_key_fingerprint')
    w.token(source['installation_id']); w.token(source['installation_epoch'])
    w.fingerprint(source['service_key_fingerprint'])
    if source['service_key_fingerprint'] != original['delegation']['source_audience']['service_key_fingerprint']: fail()
    for k in ('not_before_ms', 'expires_at_ms'): w.integer(value[k], 100_000_000_000_000)
    if not 0 < value['expires_at_ms'] - value['not_before_ms'] <= 14_400_000: fail()
    if original['action'] == 'read_evaluation_basis':
        basis(value['basis'], original['delegation'])
    elif value['basis'] is not None: fail()
    return json.loads(w.canonical(value))

def basis(value, authority):
    w.exact(value, 'schema registration_ref reviewer_plan_ref guide_ref source_purpose_ref required_criteria independence_rules slots evidence')
    if value['schema'] != 'research_factory.memory_evaluation_basis.v1': fail()
    for k in ('registration_ref', 'reviewer_plan_ref', 'guide_ref', 'source_purpose_ref'):
        if value[k] != authority[k]: fail()
    if value['independence_rules'] != ['distinct_canonical_actor', 'assessed_conflicts']: fail()
    criteria = value['required_criteria']
    if type(criteria) is not list or not criteria or criteria != sorted(set(criteria)): fail()
    for k in criteria: w.token(k)
    if type(value['slots']) is not list or [s.get('role') for s in value['slots']] != list(ROLES): fail()
    for s in value['slots']:
        w.exact(s, 'role principal_ref qualification_ref independence_ref identity_mapping_ref execution_profile_id')
        for k in ('principal_ref', 'qualification_ref', 'independence_ref', 'identity_mapping_ref'): refs(s[k])
        w.token(s['execution_profile_id'])
    evidence = value['evidence']
    if type(evidence) is not list or not 1 <= len(evidence) <= 32: fail()
    ids = []
    for item in evidence:
        w.exact(item, 'reference body')
        ref = refs(item['reference']); raw = w.canonical(item['body'])
        if ref['sha256'] != hashlib.sha256(raw).hexdigest() or ref['bytes'] != len(raw): fail()
        ids.append(ref['object_id'])
    if len(ids) != len(set(ids)): fail()
    for slot in value['slots']:
        for k in ('principal_ref', 'qualification_ref', 'independence_ref', 'identity_mapping_ref'):
            evidence_body(value, slot[k])
    return json.loads(w.canonical(value))

def evidence_body(value, ref):
    rows = [i['body'] for i in value['evidence'] if i['reference'] == ref]
    if len(rows) != 1: fail()
    return json.loads(w.canonical(rows[0]))

def identity_mapping(value):
    w.exact(value, 'schema actor_kind canonical_actor_ref credential_bindings assessment_basis limitations')
    if value['schema'] != 'mastermind.native_model_actor_mapping.v1' or value['actor_kind'] != 'NATIVE_MODEL': fail()
    refs(value['canonical_actor_ref']); text(value['assessment_basis'])
    if value['limitations'] != LIMITS or type(value['credential_bindings']) is not list or not value['credential_bindings']: fail()
    seen = []
    for b in value['credential_bindings']:
        w.exact(b, 'credential_binding_ref credential_document_sha256')
        refs(b['credential_binding_ref']); w.digest(b['credential_document_sha256'])
        seen.append(digest(b))
    if len(seen) != len(set(seen)): fail()
    return value

def evaluation_intent(value):
    w.exact(value, 'schema subject_attempt_id participant_slot registration_ref reviewer_plan_ref guide_ref')
    if value['schema'] != 'mastermind.native_memory_evaluation_intent.v1' or value['participant_slot'] not in ROLES: fail()
    w.token(value['subject_attempt_id'])
    for k in ('registration_ref', 'reviewer_plan_ref', 'guide_ref'): refs(value[k])
    if value['guide_ref']['sha256'] != GUIDE_SHA: fail()
    return json.loads(w.canonical(value))
