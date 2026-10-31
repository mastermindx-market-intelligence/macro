"""Pure current supplier binding into the existing K3 compiler.

Inputs are outputs of the qualified native disclosure reader and one immutable
bundle supplied by the current Data OS owner. Shape is never source admission:
HTTP callers must not provide these inputs or choose the bundle/cutoff. The
host retains auth, same-request owner/current-pointer rechecks and actual clocks.
No owner read, graph edge, source body, event, mechanism or identity is created.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json

from engine.company_intelligence.current_company_context import IdentityBundle, resolve_current_company
from lib.economic_propagation import EconomicPropagationError, native_supplier_binding_valid
from lib.economic_propagation_v2 import compose_hypothesis_v2, _v2_snapshot

SCHEMA = "economic_propagation.native_supplier_composition/v1"
CONTEXT_SCHEMA = "theme_graph.native_economic_context/v1"


def _require(value, reason):
    if not value:
        raise EconomicPropagationError(reason)


def _instant(value):
    try:
        _require(type(value) is str and "T" in value, "NATIVE_SUPPLIER_CLOCK_INVALID")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        _require(parsed.tzinfo is not None, "NATIVE_SUPPLIER_CLOCK_INVALID")
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        raise EconomicPropagationError("NATIVE_SUPPLIER_CLOCK_INVALID") from None


def bind_current_supplier(context, *, identity_bundle: IdentityBundle, subject_symbol: str,
                          object_symbol: str, identity_observed_at: str,
                          asof: str, compiled_at: str) -> dict:
    """Bind one qualified current role to native customer/supplier securities.

    The bundle is owner-qualified, not caller-assembled. Both native resolutions
    run over the same object. Receipt provenance is current only; disclosure
    acceptance and adoption do not backdate these security/issuer bindings.
    """
    view = _v2_snapshot(context)
    _require(type(identity_bundle) is IdentityBundle, "NATIVE_SUPPLIER_IDENTITY_REQUIRED")
    _require(type(view) is dict and view.get("schema") == CONTEXT_SCHEMA and view.get("status") == "available"
             and view.get("reason") is None and view.get("authority") == "context_only",
             "NATIVE_SUPPLIER_CONTEXT_REQUIRED")
    c = view.get("context", {})
    _require(type(c) is dict, "NATIVE_SUPPLIER_CONTEXT_REQUIRED")
    r, p, t, m = (c.get(k, {}) for k in ("relationship", "provenance", "timing", "mapping"))
    _require(all(type(part) is dict for part in (r, p, t, m)), "NATIVE_SUPPLIER_CONTEXT_REQUIRED")
    _require(c.get("usage") == {"purpose": "private_company_intelligence_context",
             "audience": "company_intelligence_entitled"}, "NATIVE_SUPPLIER_PURPOSE_REQUIRED")
    _require(r.get("kind") == "disclosed_supplier" and r.get("lifecycle") == "reported_use"
             and r.get("direction") == "object_supplies_subject"
             and r.get("amount") is None and r.get("economic_share") is None
             and r.get("subject_id") != r.get("object_id"), "NATIVE_SUPPLIER_ROLE_REQUIRED")
    _require(t.get("identity_mode") == "current" and t.get("query_mode") == "current"
             and t.get("query_as_of") is None, "NATIVE_SUPPLIER_CURRENT_ONLY")
    _require(m.get("state") == "qualified_disclosed_role_input"
             and m.get("legacy_theme_graph_edge") is None and m.get("propagation_hypothesis") is None
             and m.get("reason") is None, "NATIVE_SUPPLIER_CONTEXT_REQUIRED")
    _require(c.get("authority") == dict.fromkeys(("rank", "gate", "size", "trade", "prediction"), False),
             "NATIVE_SUPPLIER_AUTHORITY_INVALID")
    try:
        cutoff = date.fromisoformat(asof)
        observed, compiled = _instant(identity_observed_at), _instant(compiled_at)
        _require(observed.date() == compiled.date() == cutoff and observed <= compiled,
                 "NATIVE_SUPPLIER_CURRENT_ONLY")
        # Preserve native order; none of these are inferred onset or historical availability.
        clocks = [_instant(t[k]) for k in ("sec_accepted_at", "retained_retrieved_at",
            "retained_recorded_at", "pinned_snapshot_at")]
        _require(clocks == sorted(clocks) and clocks[-1] <= _instant(t["edition_known_at"])
                 <= _instant(t["fact_known_at"]) <= compiled
                 and _instant(t["identity_observed_at"]) <= _instant(t["fact_known_at"])
                 and t["native_fact_adopted_at"] == t["fact_known_at"], "NATIVE_SUPPLIER_CLOCK_INVALID")
        _require(p["reference"]["schema"] == "company_intelligence.disclosed_supplier_fact/v1"
                 and p["edition"]["schema"] == "company_intelligence.sec_disclosure_edition/v1",
                 "NATIVE_SUPPLIER_CONTEXT_REQUIRED")
        fact, edition = p["reference"]["sha256"], p["edition"]["sha256"]
        expected = {"leg_id": "sec_supplier:" + fact, "graph": "graph_1",
            "construct": "disclosed_customer_supplier", "role": "supplier",
            "role_evidence_class": "disclosed_role_specific", "claim_strength": "disclosed",
            "owner_ref": {"owner_program": "gmi-theme-graph", "artifact": "native_disclosure:" + fact,
                          "artifact_schema": CONTEXT_SCHEMA},
            "evidence_refs": ["native_fact:sha256:" + fact, "native_edition:sha256:" + edition],
            "asof": asof, "known_at": t["fact_known_at"], "usability_state": "usable"}
        _require(m["k3_input"] == expected, "NATIVE_SUPPLIER_CARRIER_MISMATCH")
        identities = [resolve_current_company(identity_bundle, symbol, today=cutoff)
                      for symbol in (subject_symbol, object_symbol)]
        _require(p.get("current_identity_sha256s") == {
            party: identity["issuer_binding"]["identity_snapshot_reference"]["sha256"]
            for party, identity in zip(("subject", "object"), identities, strict=True)},
            "NATIVE_SUPPLIER_IDENTITY_CHANGED")
        parties = [{"issuer_id": identity["issuer_binding"]["issuer_id"],
                    "security_id": identity["security_id"], "identity_receipt": identity["identity_receipt"]}
                   for identity in identities]
        _require([party["issuer_id"] for party in parties] == [r["subject_id"], r["object_id"]],
                 "NATIVE_SUPPLIER_DIRECTION_MISMATCH")
    except EconomicPropagationError:
        raise
    except Exception:
        raise EconomicPropagationError("NATIVE_SUPPLIER_BINDING_UNAVAILABLE") from None
    binding = {"schema": "economic_propagation.native_supplier_binding/v1", "kind": "disclosed_supplier",
        "lifecycle": "reported_use", "direction": "object_supplies_subject", "identity_mode": "current",
        "current_identity_observed_at": identity_observed_at, "subject": parties[0], "object": parties[1]}
    _require(native_supplier_binding_valid(binding, asof=asof, compiled_at=compiled_at),
             "NATIVE_SUPPLIER_IDENTITY_MISMATCH")
    expected["native_disclosure_binding"] = binding
    admission = {k: deepcopy(expected[k]) for k in ("graph", "construct", "owner_ref", "evidence_refs",
                 "asof", "known_at", "native_disclosure_binding")}
    admission.update(generator_id="gen_disclosed_customer_supplier", coverage_state="partial")
    def resolution(party):
        raw = json.dumps(party["identity_receipt"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        return {"resolution_state": "RESOLVED", "issuer_id": party["issuer_id"],
                "security_id": party["security_id"], "resolution_asof": asof,
                "owner_ref": {"owner_program": "stock-identity", "artifact": "sha256:" + hashlib.sha256(raw).hexdigest(),
                              "artifact_schema": "company_intelligence.current_issuer_identity/v1"}}
    return {"relationship_paths": [expected], "generator_admissions": [admission],
            "source_identity": resolution(parties[0]),
            "target": {"requested_key": object_symbol, "resolution": resolution(parties[1])}}


def compose_current_supplier(context, *, identity_bundle: IdentityBundle, subject_symbol: str,
                             object_symbol: str, identity_observed_at: str, asof: str,
                             compiled_at: str, source_event: dict | None = None,
                             review_by: str, alternative_classes=("sector_factor",)) -> dict:
    """Compose a real supplied owner event, or retain the qualified role only.

    No mechanism is inferred from the supplier disclosure. Callers needing a
    separately qualified conditional mechanism use the incumbent K3 compiler;
    this path cannot turn an observed filing into a demand/supply shock.
    """
    inputs = bind_current_supplier(context, identity_bundle=identity_bundle, subject_symbol=subject_symbol,
        object_symbol=object_symbol, identity_observed_at=identity_observed_at, asof=asof, compiled_at=compiled_at)
    if source_event is None:
        return {"schema": SCHEMA, "status": "context_only", "reason": "SOURCE_EVENT_REQUIRED",
                "hypothesis": None, "inputs": inputs}
    event = _v2_snapshot(source_event)
    _require(type(event) is dict and event.get("source_identity") == inputs["source_identity"],
             "NATIVE_SUPPLIER_EVENT_IDENTITY_MISMATCH")
    record = compose_hypothesis_v2(source_event=event, target=inputs["target"], asof=asof,
        compiled_at=compiled_at, generator_admissions=inputs["generator_admissions"],
        relationship_paths=inputs["relationship_paths"], mechanism_spec=None,
        alternative_classes=alternative_classes, review_by=review_by)
    return {"schema": SCHEMA, "status": "abstained", "reason": "NO_MECHANISM_HYPOTHESIZED",
            "hypothesis": record, "inputs": inputs}


def bind_h20_supplier_context(context, *, identity_bundle: IdentityBundle,
                              identity_observed_at: str, asof: str, compiled_at: str) -> dict:
    """Pure pre-source admission for the one fixed H20 supplier profile.

    No source store, qualifier, event or mechanism is opened here. The host
    calls this before retained-event I/O; the composer repeats it afterward.
    This checks current owner inputs, not historical commercial applicability.
    """
    from engine.company_intelligence import h20_reported_event as reported
    context = _v2_snapshot(context)
    inputs=bind_current_supplier(context,identity_bundle=identity_bundle,subject_symbol='NVDA',object_symbol='TSM',
        identity_observed_at=identity_observed_at,asof=asof,compiled_at=compiled_at)
    c=context['context'];p=c['provenance'];leg=inputs['relationship_paths'][0]
    _require(p['reference']['sha256']=='24185935320d4ff8fe852584b1497f16f000f4af4cb5e9f195f61c7a2ff9948b'
             and p['edition']['sha256']=='49cbd4aac98292e5889e0af7b6f868b337223dd2b3a8ae5c367cabde2b4c678c'
             and c['source_attribution']=={'source':'SEC public issuer filing','archive_url':reported.URL,
                 'accession':reported.ACCESSION,'document_id':reported.DOCUMENT_ID},
             'H20_SUPPLIER_LINEAGE_MISMATCH')
    parties=leg['native_disclosure_binding']
    _require(parties['subject']['issuer_id']=='ISS:US-XNAS-NVDA'
             and parties['subject']['identity_receipt']['evidenced_cik']==reported.CIK
             and parties['object']['issuer_id']=='ISS:US-XNYS-TSM'
             and parties['object']['identity_receipt']['evidenced_cik']=='0001046179',
             'H20_SUPPLIER_IDENTITY_MISMATCH')
    return inputs


def compose_qualified_h20_supplier(context, qualified_event, *, identity_bundle: IdentityBundle,
                                    identity_observed_at: str, asof: str, compiled_at: str,
                                    review_by: str) -> dict:
    """One fixed reported event + supplier pair, explicitly conditional/untested.

    Only the native qualifier's non-serializable result can select this typed
    mechanism. No HTTP mechanism, source body, clock or fact blob is accepted.
    The host owns entitlement, fixed-record reads, and current owner rechecks.
    """
    from engine.company_intelligence import h20_reported_event as reported
    authority = dict.fromkeys(('rank','gate','size','trade','prediction'),False)
    result = {'schema':'economic_propagation.current_supplier_research/v1','status':'unavailable',
        'reason':'H20_SUPPLIER_COMPOSITION_UNAVAILABLE','candidate':None,'contextual_refusal':None,
        'source_event':None,'event_evidence':None,'lineage':None,'limitations':[], 'authority':authority}
    try:
        _require(type(qualified_event) is reported.QualifiedReportedEvent, 'H20_QUALIFICATION_REQUIRED')
        evidence=qualified_event.evidence()
        _require(_instant(evidence['clocks']['verified_at']) <= _instant(compiled_at)
                 and _instant(evidence['clocks']['adopted_at']) <= _instant(compiled_at),
                 'H20_EVENT_AFTER_COMPOSITION')
        inputs=bind_h20_supplier_context(context,identity_bundle=identity_bundle,
            identity_observed_at=identity_observed_at,asof=asof,compiled_at=compiled_at)
        p=context['context']['provenance']
        source_event={'event_id':evidence['fact']['fact_id'],
            'owner_ref':{'owner_program':'earnings-intelligence','artifact':'sha256:'+hashlib.sha256(
                json.dumps(evidence['fact'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
                'artifact_schema':'event_fact.v1'},
            'event_class':'other_owner_event','source_identity':inputs['source_identity'],
            # This is the reporting observation, never the economic occurrence instant.
            'event_time':evidence['clocks']['reporting_at'],'known_at':evidence['clocks']['adopted_at']}
        spec={'mechanism_class':'demand_transfer','mechanism_polarity':'away_from_target',
              'predicted_operating_direction':'deteriorates','operating_metric_class':'volume'}
        candidate=compose_hypothesis_v2(source_event=source_event,target=inputs['target'],asof=asof,compiled_at=compiled_at,
            generator_admissions=inputs['generator_admissions'],relationship_paths=inputs['relationship_paths'],
            mechanism_spec=spec,alternative_classes=['sector_factor','coincident_timing'],review_by=review_by)
        result.update(status='available',reason=None,candidate=candidate,source_event=source_event,event_evidence=evidence,
            contextual_refusal={'status':'refused','reason':'CO_DOCUMENT_CONTEXT_IS_NOT_GRAPH1',
                'basis':'same_retained_public_filing','document_id':reported.DOCUMENT_ID,
                'source_event_fact_id':evidence['fact']['fact_id'],'relationship_input_used':False,
                'hypothesis':None,'authority':deepcopy(authority)},
            lineage={'same_document':True,'independent_corroboration':False,'raw_sha256':reported.RAW_SHA256,
                'document_id':reported.DOCUMENT_ID,'supplier_fact':deepcopy(p['reference']),
                'supplier_edition':deepcopy(p['edition']),'reported_event_fact':source_event['owner_ref']['artifact']},
            limitations=['conditional_uncalibrated_research_only','h20_to_tsm_wafer_procurement_applicability_unestablished',
                'target_antecedent_occurrence_unestablished','current_identity_not_historical_identity',
                'relationship_current_status_and_historical_applicability_unestablished',
                'same_document_not_independent_corroboration','no_registered_empirical_test_or_observed_outcome',
                'no_magnitude_confidence_lag_ranking_gating_sizing_or_trade_authority'])
        return result
    except (EconomicPropagationError, reported.ReportedEventError) as exc:
        import re
        token=str(exc)
        if re.fullmatch(r'[A-Z][A-Z0-9_]{0,95}',token):
            result['reason']=token
        return result
    except Exception:
        return result
