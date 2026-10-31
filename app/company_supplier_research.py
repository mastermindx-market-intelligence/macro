"""Authenticated host composition over incumbent native owners and K3.

The router authenticates before entry. No caller controls source, identity,
mechanism, date, purpose or storage. This module writes nothing and never
acquires a document; it reads the already retained exact public filing through
the incumbent pinned-source authority. Evidence prose stays server-side.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os

from engine.company_intelligence import issuer_disclosures as native
from engine.company_intelligence import issuer_disclosure_selection as selection
from engine.company_intelligence.current_context_runtime import CommittedCompanyContextOwner
from engine.theme_graph import economic_context

SCHEMA = 'company_intelligence.private_supplier_research/v1'
_AUTHORITY = dict.fromkeys(('rank', 'gate', 'size', 'trade', 'prediction'), False)


def _protected_records(identity_owner):
    from engine.company_intelligence import h20_reported_event as event
    native._require(type(identity_owner) is CommittedCompanyContextOwner,
                    'CURRENT_IDENTITY_OWNER_REQUIRED')
    head = identity_owner._head()
    identity_owner._git('merge-base', '--is-ancestor', head, 'refs/remotes/origin/main')
    raw = identity_owner._read(identity_owner._objects(head, event.SOURCE_PATHS))
    native._require(sha256(raw[event.DECISION_PATH]).hexdigest() == event.DECISION_SHA256
                    and sha256(raw[event.POLICY_PATH]).hexdigest() == event.POLICY_SHA256,
                    'H20_PROTECTED_RECORD_MISMATCH')
    # Enforce the live rights family before even opening the retained source.
    import yaml
    family = yaml.safe_load(raw['config/theme_sources.yml'])['families'].get('sec_public_filing_facts')
    native._require(type(family) is dict and family.get('rights_class') == 'derived_display_ok'
                    and family.get('auth_class') == 'keyless_public', 'H20_PURPOSE_NOT_ADMITTED')
    native._require(identity_owner._head() == head, 'SOURCE_GENERATION_CHANGED')
    return head, raw


def _retained_event(raw):
    from engine.company_intelligence import h20_reported_event as event
    from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority
    from engine.research_vault import r2_store
    # Same native factory as publish_company_disclosure._pinned_supplier_source.
    # No local fallback, copied archive, second store or new credential path.
    native._require(not os.environ.get('RESEARCH_LOCAL_STORE'), 'SEC_LOCAL_SOURCE_OVERRIDE_REFUSED')
    store = r2_store.build_store()
    native._require(type(store) is r2_store.R2Store and store.available,
                    'SEC_NATIVE_SOURCE_STORE_UNAVAILABLE')
    authority = PinnedSourceAuthority(store=store, snapshot_id=event.SNAPSHOT_ID)
    return event.qualify_retained_h20_event(authority, decision_raw=raw[event.DECISION_PATH],
        policy_raw=raw[event.POLICY_PATH], theme_sources_raw=raw['config/theme_sources.yml'])


def _project(result):
    """Closed browser projection after native compiler validation, never a grant."""
    from lib.economic_propagation_v2 import validate_hypothesis_v2
    native._require(type(result) is dict and result.get('status') == 'available'
                    and result.get('reason') is None and result.get('authority') == _AUTHORITY,
                    'RESEARCH_COMPOSITION_UNAVAILABLE')
    record = result['candidate']
    native._require(not validate_hypothesis_v2(record), 'RESEARCH_COMPOSITION_INVALID')
    event = result['event_evidence']; source = event['source_ref']; clocks = event['clocks']
    native._require(result['lineage']['same_document'] is True
                    and result['lineage']['independent_corroboration'] is False
                    and result['contextual_refusal']['reason'] == 'CO_DOCUMENT_CONTEXT_IS_NOT_GRAPH1'
                    and result['contextual_refusal']['hypothesis'] is None
                    and result['contextual_refusal']['relationship_input_used'] is False,
                    'RESEARCH_LINEAGE_INVALID')
    return {
        'record_id': record['record_id'], 'content_sha256': record['content_sha256'],
        'compiled_at': record['compiled_at'], 'review_by': record['expiry']['review_by'],
        'target': {'issuer_id': record['target']['resolution']['issuer_id'],
                   'security_id': record['target']['resolution']['security_id'],
                   'symbol': record['target']['requested_key']},
        'observed': {
            'event_fact_id': event['fact']['fact_id'], 'kind': event['fact']['metric'],
            'source_report_period': event['source_report_period'],
            'occurrence_period': event['reported_occurrence_period'], 'occurrence_at': event['occurrence_at'],
            **{k: clocks[k] for k in ('reporting_at', 'retrieved_at', 'adopted_at', 'verified_at')},
            **{k: source[k] for k in ('document_id', 'raw_sha256', 'span_sha256',
                'span_start_byte', 'span_end_byte', 'accession', 'archive_url')},
            **{k: event['purpose'][k] for k in ('policy_sha256', 'decision_sha256')},
        },
        'mechanism': deepcopy(record['mechanism']),
        'alternatives': deepcopy(record['alternatives']), 'falsifiers': deepcopy(record['falsifiers']),
        'applicability_conditions': deepcopy(record['applicability_conditions']),
        'evaluation_requirements': deepcopy(record['evaluation_requirements']),
        'contextual_refusal': {'reason': 'CO_DOCUMENT_CONTEXT_IS_NOT_GRAPH1',
                              'hypothesis': None, 'relationship_input_used': False},
        'lineage': {'same_document': True, 'independent_corroboration': False},
        'empirical_evaluation': 'not_performed', 'authority': deepcopy(_AUTHORITY),
    }


def read_supplier_research(reader, identity_owner, fact_id, *, purpose, audience):
    """One native fact/selection/identity/source transaction; no partial return."""
    request = native.Request(fact_id, purpose, audience)
    admission = native.preflight(reader.authority, request)
    native._require(type(admission.subject_binding) is native.SubjectIdentityBinding
                    and reader.selection_owner is not None, 'SUBJECT_IDENTITY_REQUIRED')
    bundle = selection.read_issuer_disclosure_bundle(reader.selection_owner, reader.authority,
        reader.store_factory, admission.subject_binding.issuer_id, purpose=purpose, audience=audience,
        required_fields=economic_context.REQUIRED_FIELDS)
    matches = [item for item in bundle.disclosures if item.request.fact_id == fact_id]
    native._require(len(matches) == 1 and matches[0].admission == admission,
                    'RESEARCH_SELECTION_CHANGED')
    item = matches[0]; fact = item.payload
    response = {'schema': SCHEMA, 'status': 'context_only', 'reason': 'NO_QUALIFIED_SUPPLIER_ROLE',
                'disclosure': fact, 'candidate': None}
    binding = None; protected_head = None
    if admission.reference.schema == native.SUPPLIER_FACT_SCHEMA:
        from engine.theme_graph.native_disclosure_propagation import (
            bind_h20_supplier_context, compose_qualified_h20_supplier,
        )
        protected_head, records = _protected_records(identity_owner)
        binding = identity_owner.current_identity_bundle(purpose, audience)
        observed_at = datetime.now(timezone.utc).isoformat()
        view = economic_context._project_selected(item.admission, item.request, item.payload)
        bind_h20_supplier_context(view, identity_bundle=binding, identity_observed_at=observed_at,
            asof=observed_at[:10], compiled_at=observed_at)
        qualified_event = _retained_event(records)
        compiled = datetime.now(timezone.utc)
        # Review tomorrow is a maintenance boundary, never an estimated impact lag.
        result = compose_qualified_h20_supplier(view, qualified_event, identity_bundle=binding,
            identity_observed_at=observed_at, asof=compiled.date().isoformat(),
            compiled_at=compiled.isoformat(), review_by=(compiled.date()+timedelta(days=1)).isoformat())
        response.update(status='available', reason=None, candidate=_project(result))
    # All checks follow the potentially slower source read, before serialization.
    native._require(selection._resolve(reader.selection_owner, bundle.selection.issuer_id,
        purpose, audience) == bundle.selection, 'SELECTION_CHANGED')
    for selected in bundle.disclosures:
        native._require(native.preflight(reader.authority, selected.request) == selected.admission,
                        'SELECTION_ADMISSION_CHANGED')
    if binding is not None:
        native._require(identity_owner.current_identity_bundle(purpose, audience) == binding
                        and identity_owner._head() == protected_head, 'SOURCE_GENERATION_CHANGED')
    return response
