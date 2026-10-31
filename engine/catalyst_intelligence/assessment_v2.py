"""Versioned company-first research composition; no source admission or activation.

V1 stays in assessment.py. V2 makes focal identity and the decision instant
independent of peer availability and separates current news from a historical
comparison. Owner projections remain unchanged; this consumer never fills absent
history with current state or infers a trading conclusion from combined facets.
"""
from __future__ import annotations

from collections.abc import Mapping
import json
import re
from typing import Any

from engine.news_impact.thesis import (
    ThesisError, parse_fact_log, project as project_news_theses,
)

from .assessment import _cut, _entry
from .peer_context import (
    AUTHORITY, ContextError, build_peer_context, canonical, clock, closed, digest, text,
)

INPUT_SCHEMA = "catalyst.stock_research_inputs.v2"
OUTPUT_SCHEMA = "catalyst.stock_research_assessment.v2"
_FOCAL_FIELDS = {"security_id", "company_id", "identity_epoch", "identity_source_ref"}
_UTC = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$")


def _instant(value, label):
    # Reject precision Python datetime would otherwise silently discard.
    if not isinstance(value, str) or not _UTC.fullmatch(value):
        raise ContextError(f"{label}: expected complete UTC clock with at most six fractional digits")
    return clock(value, label)


def _metadata(cut):
    return {k: cut[k] for k in cut if k != "payload"} if cut is not None else None


def _snapshot(value, requested, label):
    if value is None:
        return None
    cut = _cut(value, "news_impact", label)
    as_of = _instant(cut["as_of"], label + ".as_of")
    _instant(cut["known_at"], label + ".known_at")
    if as_of != requested:
        raise ContextError(f"{label}: snapshot differs from requested cut")
    payload = cut["payload"]
    if not isinstance(payload, Mapping):
        raise ContextError(f"{label}: owner payload is not an object")
    _instant(payload.get("decision_cut"), label + ".payload.decision_cut")
    # Evidence spelling stays literal; do not rewrite a digested owner snapshot.
    if payload["decision_cut"] != cut["as_of"]:
        raise ContextError(f"{label}: explicit decision_cut differs from source as_of")
    return cut


def _index(views, company_id):
    indexed = {}
    for view in views:
        if not isinstance(view, Mapping):
            raise ContextError("NewsImpact returned a non-object view")
        key = (text(view.get("company_id"), "news.company_id"),
               text(view.get("original_proposition_fact_id"), "news.original_proposition_fact_id"))
        if key[0] != company_id:
            continue
        if key in indexed:
            raise ContextError("NewsImpact returned duplicate proposition keys")
        indexed[key] = dict(view)
    return indexed


def _project(log, cut, company_id, prior=None):
    kwargs = {"decision_cut": cut["as_of"]}
    if prior is not None:
        kwargs.update(prior_as_of_utc=prior["as_of"], prior_owners=prior["payload"])
    try:
        views = project_news_theses(log, cut["payload"], cut["as_of"], **kwargs)
    except ThesisError as exc:
        raise ContextError("NewsImpact owner refused the research inputs") from exc
    return _index(views, company_id)


def _news_context(value, company_id, decision_at):
    decision = _instant(decision_at, "decision_at")
    current = {
        "state": "UNAVAILABLE", "reason_code": "NEWS_INPUT_NOT_SUPPLIED",
        "as_of": decision_at, "views": None, "source_cut": None,
    }
    comparison = {
        "state": "NOT_REQUESTED", "reason_code": "COMPARISON_NOT_REQUESTED",
        "since_at": None, "prior_views": None, "pairs": None,
        "source_cuts": {"prior": None, "current": None},
    }
    result = {
        "current": current, "comparison": comparison,
        "semantics": "UNCHANGED_NEWS_IMPACT_THESIS_AND_MATERIAL_DELTA_TRIGGERS",
        "interpretation": "EMPTY_TRIGGERS_ARE_NOT_PROOF_OF_NO_ECONOMIC_CHANGE",
    }
    if value is None:
        return result
    inp = closed(value, {"fact_log", "current_owners", "comparison"}, "news v2")
    current_cut = _snapshot(inp["current_owners"], decision, "current_owners")
    prior_cut = None
    since = None
    if inp["comparison"] is not None:
        comp = closed(inp["comparison"], {"since_at", "prior_owners"}, "news comparison")
        since = _instant(comp["since_at"], "since_at")
        if since >= decision:
            raise ContextError("news comparison must precede decision")
        prior_cut = _snapshot(comp["prior_owners"], since, "prior_owners")
        comparison.update(state="UNAVAILABLE", reason_code="CURRENT_OWNER_INPUT_NOT_SUPPLIED",
                          since_at=comp["since_at"])
    comparison["source_cuts"] = {
        "prior": _metadata(prior_cut), "current": _metadata(current_cut),
    }
    # Validate the supplied log even when a snapshot is intentionally absent.
    # Every projection uses this same frozen owner-parsed log.
    try:
        log = parse_fact_log(inp["fact_log"])
    except ThesisError as exc:
        raise ContextError("NewsImpact owner refused the research fact log") from exc
    current["source_cut"] = _metadata(current_cut)
    if current_cut is None:
        current["reason_code"] = "CURRENT_OWNER_INPUT_NOT_SUPPLIED"
        return result
    current["as_of"] = current_cut["as_of"]
    if _instant(current_cut["known_at"], "current_owners.known_at") > decision:
        current["reason_code"] = "CURRENT_OWNER_NOT_KNOWN_AT_CUT"
        if inp["comparison"] is not None:
            comparison["reason_code"] = "CURRENT_OWNER_NOT_KNOWN_AT_CUT"
        return result
    current_index = _project(log, current_cut, company_id)
    current.update(state="PROJECTED", reason_code=None,
                   views=[current_index[k] for k in sorted(current_index)])
    if inp["comparison"] is None:
        return result
    if prior_cut is None:
        comparison["reason_code"] = "PRIOR_OWNER_INPUT_NOT_SUPPLIED"
        return result
    if _instant(prior_cut["known_at"], "prior_owners.known_at") > since:
        comparison["reason_code"] = "PRIOR_OWNER_NOT_KNOWN_AT_CUT"
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
    comparison.update(state="PROJECTED", reason_code=None,
                      prior_views=[prior_index[k] for k in sorted(prior_index)], pairs=pairs)
    return result


def _peers(value, focal, decision):
    if value is None:
        return {"state": "UNAVAILABLE", "reason_code": "PEER_INPUT_NOT_SUPPLIED", "context": None}
    if not isinstance(value, Mapping):
        raise ContextError("peer input is not an object")
    other_focal = closed(value.get("focal"), _FOCAL_FIELDS, "peer focal")
    if dict(other_focal) != dict(focal):
        raise ContextError("peer focal differs from explicit assessment identity")
    if _instant(value.get("decision_at"), "peer.decision_at") != decision:
        raise ContextError("peer decision differs from explicit assessment cut")
    return {"state": "PROJECTED", "reason_code": None, "context": build_peer_context(value)}


def _entry_context(value, focal, decision_at):
    if value is not None:
        if not isinstance(value, Mapping):
            raise ContextError("entry cut is not an object")
        for key in ("as_of", "known_at"):
            _instant(value.get(key), "entry." + key)
        payload = value.get("payload")
        if isinstance(payload, Mapping):
            for key in ("evaluated_at", "quote_asof"):
                _instant(payload.get(key), "entry." + key)
    return _entry(value, focal, decision_at)


def build_stock_assessment_v2(request: Mapping[str, Any]) -> dict[str, Any]:
    """Compose a supplied company case with independently available owner facets."""
    req = closed(request, {"schema", "focal", "decision_at", "peer_inputs", "entry", "news"},
                 "stock request v2")
    if req["schema"] != INPUT_SCHEMA:
        raise ContextError("stock v2 input schema mismatch")
    req = json.loads(canonical(req))
    focal = closed(req["focal"], _FOCAL_FIELDS, "focal")
    for key in _FOCAL_FIELDS:
        text(focal[key], "focal." + key)
    decision = _instant(req["decision_at"], "decision_at")
    packet = {
        "schema": OUTPUT_SCHEMA,
        "qualification": "NONACTIVATED_RESEARCH_CONSUMER",
        "source_admission_established": False,
        "authority": dict(AUTHORITY),
        "decision_at": req["decision_at"], "focal": dict(focal),
        "peer_context": _peers(req["peer_inputs"], focal, decision),
        "entry_context": _entry_context(req["entry"], focal, req["decision_at"]),
        "news_context": _news_context(req["news"], focal["company_id"], req["decision_at"]),
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
