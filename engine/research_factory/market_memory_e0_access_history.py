"""Bounded access-history semantics used by the installed E0 owner.

This validates supplied metadata, not its origin or current selection. Only the
installed owner may load the current private selected chain and supply its own
clock. A hash-linked list from a caller cannot grant access, reset reservations,
prove reviewer independence, or establish that no later revocation exists.
ReservationStore remains the authority for actual consumed/reserved looks;
these records describe policy history, not a second reservation ledger.
"""
from __future__ import annotations

import hashlib

from . import market_memory_contextual_registration as control
from .market_memory_e0_reservations import MAX_LOOKS

MAX_ACCESS_RECORDS = 1025
MAX_ACCESS_HISTORY_BYTES = 8 * 1024 * 1024
_BOUND_FIELDS = (
    "study_id", "installation_id", "installation_epoch", "access_state_id",
    "registration_ref", "publication_ref", "owner_principal_ref", "scope_ref",
)


class E0AccessHistoryError(ValueError):
    """Stable reason only; no caller values or private record bodies."""


def _require(ok: bool, reason: str) -> None:
    if not ok:
        raise E0AccessHistoryError(reason)


def validate_access_history(*, installation: object, history: object, as_of: str) -> dict:
    """Validate one complete chronological chain against its installation.

    Exact canonical bytes preserve every predecessor reference. Time is an
    explicit diagnostic input here; production must use current owner time.
    Revocation, exhaustion and contamination cannot be undone within an epoch.
    Incomplete/malformed history refuses instead of treating its newest row as
    evidence of current permission. The returned summary grants no actions.
    """
    bound = control.validate_e0_control_record(installation, kind="installed_binding")
    now = control._clock(as_of)
    _require(control._clock(bound["installed_at"]) <= now < control._clock(bound["expires_at"]),
             "installation_clock_or_expiry")
    _require(type(history) is list and 1 <= len(history) <= MAX_ACCESS_RECORDS,
             "bounded_access_history_required")
    _require(all(type(body) is bytes and 0 < len(body) <= control.MAX_CONTROL_BYTES
                 for body in history), "bounded_access_record_bytes_required")
    _require(sum(map(len, history)) <= MAX_ACCESS_HISTORY_BYTES, "access_history_byte_limit")
    previous = None
    previous_ref = None
    initial = None
    latest_ref = None
    for index, body in enumerate(history):
        state = control.parse_e0_control_record(body, kind="access_state")
        _require(state["sequence"] == index, "access_sequence_gap")
        _require(state["previous_state_ref"] == previous_ref, "access_predecessor_mismatch")
        _require(all(state[key] == bound[key] for key in _BOUND_FIELDS if key != "scope_ref"),
                 "access_installation_binding_mismatch")
        recorded = control._clock(state["recorded_at"])
        _require(control._clock(bound["installed_at"]) <= recorded <= now,
                 "access_clock_order")
        budget = state["budget"]
        used = budget["consumed_looks"] + budget["reserved_looks"]
        _require(budget["maximum_looks"] <= MAX_LOOKS, "unsupported_owner_look_budget")
        if previous is None:
            _require(used == 0, "initial_access_budget_not_empty")
            initial = state
        else:
            _require(all(state[key] == initial[key] for key in _BOUND_FIELDS),
                     "access_epoch_binding_changed")
            _require(recorded >= control._clock(previous["recorded_at"]), "access_clock_order")
            old_budget = previous["budget"]
            _require(budget["maximum_looks"] == old_budget["maximum_looks"],
                     "access_budget_limit_changed")
            _require(budget["consumed_looks"] >= old_budget["consumed_looks"]
                     and used >= old_budget["consumed_looks"] + old_budget["reserved_looks"],
                     "access_look_refund")
            # Revoking an already exhausted epoch tightens its policy. Neither
            # terminal state can return to active, and revocation is final.
            rank = {"active": 0, "exhausted": 1, "revoked": 2}
            _require(rank[state["status"]] >= rank[previous["status"]],
                     "terminal_access_state_changed")
            _require(previous["contamination_state"] != "contaminated"
                     or state["contamination_state"] == "contaminated",
                     "contamination_state_reversed")
        latest_ref = {"schema": control.SCHEMAS["access_state"],
                      "object_id": state["access_state_id"],
                      "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        previous, previous_ref = state, latest_ref
    return {"schema": "research_factory.market_memory_e0_access_history_consistency.v1",
            "authority": "display_only", "study_id": bound["study_id"],
            "installation_id": bound["installation_id"],
            "installation_epoch": bound["installation_epoch"],
            "records": len(history), "selected_state_ref": latest_ref,
            "status": previous["status"], "contamination_state": previous["contamination_state"],
            "declared_budget": dict(previous["budget"]),
            "metadata_consistent": True, "current_selection_authenticated": False,
            "actual_reservation_accounting_verified": False, "operational_admission": False}


def _evaluation_scope_documents(*, installation, history, scope_objects,
        purpose_body, service_body, source_commit, as_of, schema_documents=None):
    """Versioned scope DATA grammar, hashes and stable-purpose joins only."""
    import json
    from pathlib import Path
    from . import market_memory_e0_evaluation_contract as data
    from . import market_memory_e0_evaluation_validation as wire
    _require(type(history) is list and 1<=len(history)<=MAX_ACCESS_RECORDS,
             'bounded_access_history_required')
    _require(type(scope_objects) is dict and 1<=len(scope_objects)<=MAX_ACCESS_RECORDS,
             'bounded_evaluation_scope_objects_required')
    if schema_documents is None:
        # Standalone DATA diagnostics may read public schemas. The fixed native
        # owner supplies its preloaded bytes to avoid I/O after terminal checks.
        schema_root=Path(__file__).resolve().parents[2]/'contracts/market_memory'
        schema_documents=((schema_root/'e0_evaluation_source.v1.schema.json').read_bytes(),
            (schema_root/'e0_native_bindings.v3.schema.json').read_bytes())
    _require(type(schema_documents) is tuple and len(schema_documents)==2
        and all(type(body) is bytes for body in schema_documents),'evaluation_schema_bytes')
    schema,service_schema=(json.loads(body) for body in schema_documents)
    def native_json(body,kind):
        _require(type(body) is bytes and 0<len(body)<=control.MAX_CONTROL_BYTES,
                 'bounded_evaluation_metadata_required')
        value=control._domain_json(body)
        _require(control._domain_snapshot(value)[1]==body,'canonical_evaluation_metadata_required')
        check=dict(service_schema if kind=='service' else schema)
        check.pop('oneOf',None);check['$ref']='#/$defs/'+kind
        _require(next(control._INTEGER_VALIDATOR(check).iter_errors(value),None) is None,
                 'evaluation_metadata_schema')
        return value
    bound=control.validate_e0_control_record(installation,kind='installed_binding')
    purpose=native_json(purpose_body,'purpose');service=native_json(service_body,'service')
    stable_ref=None;used=set();scopes=[];total=len(purpose_body)+len(service_body)
    for raw in history:
        state=control.parse_e0_control_record(raw,kind='access_state')
        ref=control._domain_reference(state['scope_ref'])
        _require(ref['schema']=='research_factory.market_memory_e0_evaluation_scope.v1',
                 'evaluation_scope_profile_required')
        digest=ref['sha256'];_require(digest in scope_objects,'evaluation_scope_missing')
        body=scope_objects[digest];_require(type(body) is bytes and len(body)==ref['bytes']
            and hashlib.sha256(body).hexdigest()==digest,'evaluation_scope_reference_bytes')
        scope=native_json(body,'scope');_require(scope['object_id']==ref['object_id'],'evaluation_scope_identity')
        _require(0<scope['expires_at_ms']-scope['not_before_ms']<=14400000,'evaluation_scope_window')
        _require(stable_ref is None or scope['purpose_ref']==stable_ref,'evaluation_purpose_changed')
        stable_ref=scope['purpose_ref'];used.add(digest);scopes.append(scope)
    _require(set(scope_objects)==used,'unexpected_evaluation_scope_objects')
    total+=sum(len(scope_objects[k]) for k in used)+sum(len(v) for v in history)
    _require(total<=MAX_ACCESS_HISTORY_BYTES,'evaluation_history_byte_limit')
    purpose_ref=control._domain_reference(stable_ref)
    _require(purpose_ref['schema']==purpose['schema'] and purpose_ref['object_id']==purpose['object_id']
        and purpose_ref['bytes']==len(purpose_body) and purpose_ref['sha256']==hashlib.sha256(purpose_body).hexdigest(),
        'evaluation_purpose_reference_bytes')
    service_ref=control._domain_reference(bound['admin_receipt_ref'])
    _require(service_ref['schema']==service['schema'] and service_ref['object_id']==service['object_id']
        and service_ref['bytes']==len(service_body) and service_ref['sha256']==hashlib.sha256(service_body).hexdigest(),
        'evaluation_service_reference_bytes')
    _require(purpose['service_ref']==service_ref and purpose['installation_id']==bound['installation_id']
        and purpose['installation_epoch']==bound['installation_epoch'],'evaluation_service_binding')
    _require(all(service[k]==bound[k] for k in ('installation_id','installation_epoch','registration_ref','publication_ref'))
        and service['source_commit']==source_commit,'evaluation_service_installation')
    delegation=purpose['delegation_binding'];data.delegation({**delegation,'source_purpose_ref':purpose_ref})
    _require(delegation['enabled'] is True and delegation['study_id']==bound['study_id']
        and delegation['registration_ref']==bound['registration_ref'],'evaluation_delegation_binding')
    audience=delegation['source_audience'];data.audience(audience)
    _require(audience['service_key_fingerprint']==service['ssh_key_fingerprint'],'evaluation_custodian_service')
    _require(purpose['required_criteria']==sorted(set(purpose['required_criteria']))
        and [s['role'] for s in purpose['slots']]==list(data.ROLES),'evaluation_basis_declaration')
    for value in (*purpose['task_ids'],*purpose['required_criteria']):wire.token(value)
    for slot in purpose['slots']:
        wire.token(slot['execution_profile_id']);wire._reference(slot['identity_mapping_ref'])
    for scope in scopes:
        _require(all(row['task_id'] in purpose['task_ids'] for row in scope['commitments']),
                 'evaluation_scope_task_outside_purpose')
    latest=scopes[-1];now_ms=int(control._clock(as_of).timestamp()*1000)
    lo=max(delegation['not_before_ms'],latest['not_before_ms'],int(control._clock(bound['installed_at']).timestamp()*1000))
    hi=min(delegation['expires_at_ms'],latest['expires_at_ms'],int(control._clock(bound['expires_at']).timestamp()*1000))
    _require(lo<=now_ms<hi,'evaluation_current_window')


def validate_evaluation_access_history(*, installation: object, history: object,
        as_of: str, scope_objects: object, purpose_body: bytes, service_body: bytes,
        source_commit: str, schema_documents=None) -> dict:
    """Validate one complete chronological chain against its installation.

    Exact canonical bytes preserve every predecessor reference. Time is an
    explicit diagnostic input here; production must use current owner time.
    Revocation, exhaustion and contamination cannot be undone within an epoch.
    Incomplete/malformed history refuses instead of treating its newest row as
    evidence of current permission. The returned summary grants no actions.
    """
    # Pure DATA validation only. The fixed installed owner loads every exact
    # scope/purpose/service body through its protected reference loader; a
    # caller-owned map here grants no authority or current selection.
    _evaluation_scope_documents(installation=installation, history=history,
        scope_objects=scope_objects,purpose_body=purpose_body,
        service_body=service_body,source_commit=source_commit,as_of=as_of,schema_documents=schema_documents)
    bound = control.validate_e0_control_record(installation, kind="installed_binding")
    now = control._clock(as_of)
    _require(control._clock(bound["installed_at"]) <= now < control._clock(bound["expires_at"]),
             "installation_clock_or_expiry")
    _require(type(history) is list and 1 <= len(history) <= MAX_ACCESS_RECORDS,
             "bounded_access_history_required")
    _require(all(type(body) is bytes and 0 < len(body) <= control.MAX_CONTROL_BYTES
                 for body in history), "bounded_access_record_bytes_required")
    _require(sum(map(len, history)) <= MAX_ACCESS_HISTORY_BYTES, "access_history_byte_limit")
    previous = None
    previous_ref = None
    initial = None
    latest_ref = None
    for index, body in enumerate(history):
        state = control.parse_e0_control_record(body, kind="access_state")
        _require(state["sequence"] == index, "access_sequence_gap")
        _require(state["previous_state_ref"] == previous_ref, "access_predecessor_mismatch")
        _require(all(state[key] == bound[key] for key in _BOUND_FIELDS if key != "scope_ref"),
                 "access_installation_binding_mismatch")
        recorded = control._clock(state["recorded_at"])
        _require(control._clock(bound["installed_at"]) <= recorded <= now,
                 "access_clock_order")
        budget = state["budget"]
        used = budget["consumed_looks"] + budget["reserved_looks"]
        _require(budget["maximum_looks"] <= MAX_LOOKS, "unsupported_owner_look_budget")
        if previous is None:
            _require(used == 0, "initial_access_budget_not_empty")
            initial = state
        else:
            _require(all(state[key] == initial[key] for key in _BOUND_FIELDS if key != "scope_ref"),
                     "access_epoch_binding_changed")
            _require(recorded >= control._clock(previous["recorded_at"]), "access_clock_order")
            old_budget = previous["budget"]
            _require(budget["maximum_looks"] == old_budget["maximum_looks"],
                     "access_budget_limit_changed")
            _require(budget["consumed_looks"] >= old_budget["consumed_looks"]
                     and used >= old_budget["consumed_looks"] + old_budget["reserved_looks"],
                     "access_look_refund")
            # Revoking an already exhausted epoch tightens its policy. Neither
            # terminal state can return to active, and revocation is final.
            rank = {"active": 0, "exhausted": 1, "revoked": 2}
            _require(rank[state["status"]] >= rank[previous["status"]],
                     "terminal_access_state_changed")
            _require(previous["contamination_state"] != "contaminated"
                     or state["contamination_state"] == "contaminated",
                     "contamination_state_reversed")
        latest_ref = {"schema": control.SCHEMAS["access_state"],
                      "object_id": state["access_state_id"],
                      "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}
        previous, previous_ref = state, latest_ref
    return {"schema": "research_factory.market_memory_e0_evaluation_access_history_consistency.v1",
            "authority": "display_only", "study_id": bound["study_id"],
            "installation_id": bound["installation_id"],
            "installation_epoch": bound["installation_epoch"],
            "records": len(history), "selected_state_ref": latest_ref,
            "status": previous["status"], "contamination_state": previous["contamination_state"],
            "declared_budget": dict(previous["budget"]),
            "metadata_consistent": True, "current_selection_authenticated": False,
            "actual_reservation_accounting_verified": False, "operational_admission": False}
