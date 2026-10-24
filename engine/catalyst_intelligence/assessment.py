"""A nonactivated research consumer of peer arithmetic, NewsImpact and Prophet.

NewsImpact owns its fact/revision fold and change triggers; Prophet B4 owns its
strategy-specific availability state. This module owns only the derived packet.
Caller-supplied source cuts are checked for consistency, not authenticated or
admitted. Runtime acquisition, GMI/identity/rights qualification and authenticated
publication remain with the existing owners.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
from typing import Any

from engine.news_impact.thesis import ThesisError, project as project_news_theses
from engine.prophet_entry_availability import validate_entry_availability
from engine.prophet_strategy_definition import build_early_leadership_sector_rotation_definition

from .peer_context import (
    AUTHORITY, ContextError, build_peer_context, canonical, clock, closed, digest, text,
)

INPUT_SCHEMA = "catalyst.stock_research_inputs.v1"
OUTPUT_SCHEMA = "catalyst.stock_research_assessment.v1"


def _cut(value, owner, label):
    row = closed(value, {"owner", "as_of", "known_at", "source_ref", "payload_digest", "payload"}, label)
    if row["owner"] != owner:
        raise ContextError(f"{label}: unexpected source owner")
    a, k = clock(row["as_of"], label + ".as_of"), clock(row["known_at"], label + ".known_at")
    if a > k:
        raise ContextError(f"{label}: as_of follows known_at")
    text(row["source_ref"], label + ".source_ref")
    if digest(row["payload"]) != row["payload_digest"]:
        raise ContextError(f"{label}: payload digest mismatch")
    return row


def _entry(value, focal, decision_at):
    if value is None:
        return {"state": "OWNER_INPUT_UNAVAILABLE", "owner_projection": None, "source_cut": None}
    cut = _cut(value, "prophet_b4", "entry")
    decision = clock(decision_at, "decision_at")
    if clock(cut["known_at"], "entry.known_at") > decision:
        return {"state": "NOT_KNOWN_AT_DECISION", "owner_projection": None,
                "source_cut": {k: cut[k] for k in cut if k != "payload"}}
    payload = cut["payload"]
    if not isinstance(payload, Mapping):
        raise ContextError("entry payload is not an object")
    validate_entry_availability(payload)
    if payload["security_id"] != focal["security_id"] or payload["identity_epoch"] != focal["identity_epoch"]:
        raise ContextError("entry identity differs from focal identity")
    if clock(payload["evaluated_at"], "entry.evaluated_at") != clock(cut["as_of"], "entry.as_of"):
        raise ContextError("entry owner clock differs from source cut")
    if clock(payload["quote_asof"], "entry.quote_asof") > clock(payload["evaluated_at"], "entry.evaluated_at"):
        raise ContextError("entry contains a future quote")
    if clock(payload["evaluated_at"], "entry.evaluated_at") != decision:
        return {"state": "DIFFERENT_DECISION_CUT", "owner_projection": None,
                "source_cut": {k: cut[k] for k in cut if k != "payload"}}
    strategy = build_early_leadership_sector_rotation_definition()
    return {"state": "OWNER_PROJECTION_ATTACHED", "owner_projection": dict(payload),
            "source_cut": {k: cut[k] for k in cut if k != "payload"},
            "strategy_scientific_status": strategy["scientific_status"],
            "strategy_authority_tier": strategy["authority_tier"],
            "scope": "EXISTING_STRATEGY_AND_HORIZON_ONLY"}


def _news(value, company_id, decision_at):
    if value is None:
        return {"state": "OWNER_INPUT_UNAVAILABLE", "views": [], "source_cuts": []}
    inp = closed(value, {"fact_log", "current_owners", "prior_owners", "since_at"}, "news")
    since, decision = clock(inp["since_at"], "since_at"), clock(decision_at, "decision_at")
    if since >= decision:
        raise ContextError("news comparison must precede decision")
    # Never accept project's default of replaying current owner state as prior.
    # Missing historical owner evidence is an unavailable comparison, not zero change.
    if inp["current_owners"] is None or inp["prior_owners"] is None:
        return {"state": "OWNER_COMPARISON_CUT_UNAVAILABLE", "views": [], "source_cuts": []}
    current = _cut(inp["current_owners"], "news_impact", "current_owners")
    prior = _cut(inp["prior_owners"], "news_impact", "prior_owners")
    for cut, requested in ((current, decision), (prior, since)):
        if clock(cut["as_of"], "news.as_of") != requested:
            raise ContextError("news owner snapshot does not match requested comparison cut")
        if clock(cut["known_at"], "news.known_at") > requested:
            return {"state": "OWNER_SNAPSHOT_NOT_KNOWN_AT_CUT", "views": [],
                    "source_cuts": [{k: c[k] for k in c if k != "payload"} for c in (prior, current)]}
        if not isinstance(cut["payload"], Mapping) or cut["payload"].get("decision_cut") != cut["as_of"]:
            raise ContextError("explicit NewsImpact decision_cut is required in both snapshots")
    try:
        views = project_news_theses(
            inp["fact_log"], current["payload"], decision_at,
            prior_as_of_utc=inp["since_at"], prior_owners=prior["payload"], decision_cut=decision_at,
        )
    except ThesisError as exc:
        raise ContextError("NewsImpact owner refused the research inputs") from exc
    return {"state": "OWNER_PROJECTION_ATTACHED", "since_at": inp["since_at"],
            "views": [v for v in views if v["company_id"] == company_id],
            "source_cuts": [{k: c[k] for k in c if k != "payload"} for c in (prior, current)],
            "semantics": "UNCHANGED_NEWS_IMPACT_THESIS_AND_MATERIAL_DELTA_TRIGGERS"}


def build_stock_assessment(request: Mapping[str, Any]) -> dict[str, Any]:
    """Run actual owner code and compose an immutable, non-trading research view."""
    req = closed(request, {"schema", "peer_inputs", "entry", "news"}, "stock request")
    if req["schema"] != INPUT_SCHEMA:
        raise ContextError("stock input schema mismatch")
    # Freeze caller-owned mappings before invoking any downstream projection.
    req = json.loads(canonical(req))
    peer = build_peer_context(req["peer_inputs"])
    focal, decision_at = peer["focal"], peer["decision_at"]
    entry = _entry(req["entry"], focal, decision_at)
    news = _news(req["news"], focal["company_id"], decision_at)
    packet = {
        "schema": OUTPUT_SCHEMA, "qualification": "NONACTIVATED_RESEARCH_CONSUMER",
        "source_admission_established": False, "authority": dict(AUTHORITY),
        "decision_at": decision_at, "focal": focal,
        "peer_context": peer, "entry_context": entry, "news_changes": news,
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
