"""Research composition with separate information and artifact clocks.

This additive version leaves supplied-snapshot v1/v2 untouched. It can replay
an earlier information cut from an artifact materialized later, but cannot prove
that an owner state was historically qualified or an assessment was delivered
before a trading decision. No source acquisition, admission or publication occurs.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

from engine.news_impact.thesis import (
    ThesisError, parse_fact_log, project as project_news_theses,
)
from engine.prophet_entry_availability import validate_entry_availability
from engine.prophet_strategy_definition import build_early_leadership_sector_rotation_definition

from .assessment_v2 import _FOCAL_FIELDS, _index, _instant, _peers
from .peer_context import AUTHORITY, ContextError, canonical, closed, digest, text

INPUT_SCHEMA = "catalyst.stock_research_inputs.v3"
OUTPUT_SCHEMA = "catalyst.stock_research_assessment.v3"
ENVELOPE_SCHEMA = "catalyst.supplied_owner_time_envelope.v1"
_ENVELOPE_FIELDS = {
    "schema", "owner", "information_cutoff_at", "materialized_at", "received_at",
    "source_ref", "source_revision", "payload_digest", "payload",
}
QUALIFICATION = "SUPPLIED_OWNER_STATE_NOT_INDEPENDENTLY_ADMITTED"


def _metadata(envelope):
    if envelope is None:
        return None
    return {k: v for k, v in envelope.items() if k != "payload"}


def _envelope(value, owner, cutoff, composed, label):
    if value is None:
        return None
    row = closed(value, _ENVELOPE_FIELDS, label)
    if row["schema"] != ENVELOPE_SCHEMA or row["owner"] != owner:
        raise ContextError(f"{label}: unexpected envelope schema or owner")
    information = _instant(row["information_cutoff_at"], label + ".information_cutoff_at")
    materialized = _instant(row["materialized_at"], label + ".materialized_at")
    received = _instant(row["received_at"], label + ".received_at")
    if information != cutoff:
        raise ContextError(f"{label}: envelope differs from requested information cutoff")
    if not information <= materialized <= received <= composed:
        raise ContextError(f"{label}: information/materialization/receipt/composition ordering invalid")
    for key in ("source_ref", "source_revision"):
        text(row[key], label + "." + key)
    if not isinstance(row["payload"], Mapping):
        raise ContextError(f"{label}: owner payload is not an object")
    if digest(row["payload"]) != row["payload_digest"]:
        raise ContextError(f"{label}: payload digest mismatch")
    if owner == "news_impact":
        _instant(row["payload"].get("decision_cut"), label + ".payload.decision_cut")
        # Preserve literal owner evidence and its digest; never relabel a cut.
        if row["payload"]["decision_cut"] != row["information_cutoff_at"]:
            raise ContextError(f"{label}: explicit owner decision_cut differs from information cutoff")
    return row


def _project(log, envelope, company_id, prior=None):
    at = envelope["information_cutoff_at"]
    kwargs = {"decision_cut": at}
    if prior is not None:
        kwargs.update(prior_as_of_utc=prior["information_cutoff_at"],
                      prior_owners=prior["payload"])
    try:
        # Artifact clocks must never advance the fact owner's visibility cut.
        views = project_news_theses(log, envelope["payload"], at, **kwargs)
    except ThesisError as exc:
        raise ContextError("NewsImpact owner refused the research inputs") from exc
    return _index(views, company_id)


def _news(value, company_id, cutoff_at, composed):
    cutoff = _instant(cutoff_at, "information_cutoff_at")
    current = {
        "state": "UNAVAILABLE", "reason_code": "NEWS_INPUT_NOT_SUPPLIED",
        "information_cutoff_at": cutoff_at, "views": None, "source_envelope": None,
    }
    comparison = {
        "state": "NOT_REQUESTED", "reason_code": "COMPARISON_NOT_REQUESTED",
        "information_cutoff_at": None, "prior_views": None, "pairs": None,
        "source_envelopes": {"prior": None, "current": None},
    }
    result = {
        "current": current, "comparison": comparison,
        "owner_state_qualification": QUALIFICATION,
        "semantics": "UNCHANGED_NEWS_IMPACT_THESIS_AND_MATERIAL_DELTA_TRIGGERS",
        "interpretation": "EMPTY_TRIGGERS_ARE_NOT_PROOF_OF_NO_ECONOMIC_CHANGE",
    }
    if value is None:
        return result
    inp = closed(value, {"fact_log", "current_owners", "comparison"}, "news v3")
    current_cut = _envelope(inp["current_owners"], "news_impact", cutoff, composed,
                            "current_owners")
    prior_cut = None
    if inp["comparison"] is not None:
        comp = closed(inp["comparison"], {"information_cutoff_at", "prior_owners"},
                      "news comparison")
        since = _instant(comp["information_cutoff_at"], "comparison.information_cutoff_at")
        if since >= cutoff:
            raise ContextError("news comparison must precede information cutoff")
        prior_cut = _envelope(comp["prior_owners"], "news_impact", since, composed,
                              "prior_owners")
        comparison.update(state="UNAVAILABLE", reason_code="CURRENT_OWNER_INPUT_NOT_SUPPLIED",
                          information_cutoff_at=comp["information_cutoff_at"])
    comparison["source_envelopes"] = {
        "prior": _metadata(prior_cut), "current": _metadata(current_cut),
    }
    # Malformed supplied data must not disappear behind a missing optional facet.
    try:
        log = parse_fact_log(inp["fact_log"])
    except ThesisError as exc:
        raise ContextError("NewsImpact owner refused the research fact log") from exc
    current["source_envelope"] = _metadata(current_cut)
    if current_cut is None:
        current["reason_code"] = "CURRENT_OWNER_INPUT_NOT_SUPPLIED"
        return result
    current["information_cutoff_at"] = current_cut["information_cutoff_at"]
    current_index = _project(log, current_cut, company_id)
    current.update(state="PROJECTED_RESEARCH", reason_code=None,
                   views=[current_index[k] for k in sorted(current_index)])
    if inp["comparison"] is None:
        return result
    if prior_cut is None:
        comparison["reason_code"] = "PRIOR_OWNER_INPUT_NOT_SUPPLIED"
        return result
    prior_index = _project(log, prior_cut, company_id)
    compared_index = _project(log, current_cut, company_id, prior=prior_cut)
    if set(compared_index) != set(current_index):
        raise ContextError("NewsImpact current/comparison proposition keys differ")
    for key in current_index:
        plain = {k: v for k, v in current_index[key].items() if k != "material_delta_triggers"}
        compared = {k: v for k, v in compared_index[key].items() if k != "material_delta_triggers"}
        if canonical(plain) != canonical(compared):
            raise ContextError("NewsImpact current/comparison owner views disagree")
        triggers = compared_index[key].get("material_delta_triggers")
        if not isinstance(triggers, list) or any(not isinstance(t, str) for t in triggers):
            raise ContextError("NewsImpact comparison triggers are invalid")
    pairs = []
    for key in sorted(set(prior_index) | set(current_index)):
        presence = ("BOTH_CUTS" if key in prior_index and key in current_index else
                    "CURRENT_ONLY" if key in current_index else "PRIOR_ONLY")
        pairs.append({
            "view_key": {"company_id": key[0], "original_proposition_fact_id": key[1]},
            "presence": presence,
            "material_delta_triggers": (
                compared_index[key]["material_delta_triggers"] if key in current_index else None
            ),
        })
    comparison.update(state="PROJECTED_RESEARCH", reason_code=None,
                      prior_views=[prior_index[k] for k in sorted(prior_index)], pairs=pairs)
    return result


def _entry(value, focal, cutoff_at, composed):
    base = {
        "state": "OWNER_INPUT_UNAVAILABLE", "owner_projection": None, "source_envelope": None,
        "owner_state_qualification": QUALIFICATION,
        "decision_availability_established": False,
    }
    envelope = _envelope(value, "prophet_b4", _instant(cutoff_at, "information_cutoff_at"),
                         composed, "entry")
    if envelope is None:
        return base
    base["source_envelope"] = _metadata(envelope)
    payload = envelope["payload"]
    evaluated = _instant(payload.get("evaluated_at"), "entry.evaluated_at")
    quote = _instant(payload.get("quote_asof"), "entry.quote_asof")
    validate_entry_availability(payload)
    if payload["security_id"] != focal["security_id"] or payload["identity_epoch"] != focal["identity_epoch"]:
        raise ContextError("entry identity differs from focal identity")
    if quote > evaluated:
        raise ContextError("entry contains a future quote")
    if evaluated != _instant(envelope["information_cutoff_at"], "entry.information_cutoff_at"):
        base["state"] = "DIFFERENT_INFORMATION_CUT"
        return base
    strategy = build_early_leadership_sector_rotation_definition()
    base.update(
        state="OWNER_RESEARCH_CONTEXT_ATTACHED", owner_projection=dict(payload),
        strategy_scientific_status=strategy["scientific_status"],
        strategy_authority_tier=strategy["authority_tier"],
        scope="EXISTING_STRATEGY_AND_HORIZON_ONLY",
        interpretation="RECONSTRUCTED_CONTEXT_IS_NOT_CURRENT_ENTRY_AVAILABILITY",
    )
    return base


def build_stock_assessment_v3(request: Mapping[str, Any]) -> dict[str, Any]:
    """Replay supplied owner states without backdating their artifact clocks."""
    req = closed(request, {"schema", "focal", "information_cutoff_at", "composed_at",
                           "peer_inputs", "entry", "news"}, "stock request v3")
    if req["schema"] != INPUT_SCHEMA:
        raise ContextError("stock v3 input schema mismatch")
    req = json.loads(canonical(req))
    focal = closed(req["focal"], _FOCAL_FIELDS, "focal")
    for key in _FOCAL_FIELDS:
        text(focal[key], "focal." + key)
    cutoff = _instant(req["information_cutoff_at"], "information_cutoff_at")
    composed = _instant(req["composed_at"], "composed_at")
    if composed < cutoff:
        raise ContextError("composition precedes information cutoff")
    packet = {
        "schema": OUTPUT_SCHEMA,
        "qualification": "NONACTIVATED_RESEARCH_CONSUMER",
        "source_admission_established": False,
        "decision_availability_established": False,
        "owner_state_qualification": QUALIFICATION,
        "authority": dict(AUTHORITY),
        "information_cutoff_at": req["information_cutoff_at"], "composed_at": req["composed_at"],
        "timing_semantics": "SUPPLIED_RECONSTRUCTION_NOT_PROOF_OF_ACTUAL_DECISION_AVAILABILITY",
        "focal": dict(focal),
        "peer_context": _peers(req["peer_inputs"], focal, cutoff),
        "entry_context": _entry(req["entry"], focal, req["information_cutoff_at"], composed),
        "news_context": _news(req["news"], focal["company_id"],
                              req["information_cutoff_at"], composed),
        "advanced_estimates": {
            "best_entry_policy": {"state": "NOT_QUALIFIED", "value": None},
            "fundamental_value_priced_in": {"state": "NOT_ESTIMABLE", "value": None},
            "causal_theme_spillover": {"state": "NOT_ESTIMABLE", "value": None},
            "predictive_lead_lag": {"state": "NOT_QUALIFIED", "value": None},
            "clinical_outcome_probability": {"state": "NOT_QUALIFIED", "value": None},
        },
        "input_digest": digest(req),
        "composition_rule": "SEPARATE_OWNER_FACETS_NO_FUSION_SCORE_OR_GATE_OVERRIDE",
    }
    packet["assessment_id"] = digest(packet)
    return json.loads(canonical(packet))
