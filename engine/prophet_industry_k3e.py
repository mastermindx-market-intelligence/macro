"""Industry-level K3E/Prophet research composition, not a replacement owner.

Uses existing source-dated revision projection and K3E descriptive coupling.
Allows explicitly reconstructed membership for discovery. It never rebrands a
current snapshot as a past estimate, overwrites a score, or invents probability.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
import math
from statistics import median
from typing import Any

import pandas as pd

from engine.k3e_coupling import compose_descriptive_coupling
from engine.leader_recovery_expectations import project_expectations

SCHEMA = "prophet.industry_k3e_research.v1"
MEMBERSHIP_BASES = {"dated_membership", "reconstructed_static_membership", "synthetic_fixture"}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _day(value: Any) -> date:
    if not isinstance(value, str):
        raise ValueError("ISO date required")
    return date.fromisoformat(value)


def _reading(snapshot: dict, name: str) -> float | None:
    item = snapshot.get("readings", {}).get(name, {})
    return _number(item.get("value")) if isinstance(item, dict) else None


def aggregate_industry_expectations(
    membership: dict, snapshots: dict[str, dict], *, as_of: str,
    max_age_sessions: int = 10, minimum_coverage: float = .5,
    k3e_inputs: dict[str, dict] | None = None,
) -> dict:
    """Equal-issuer observed context with explicit coverage and duplicate handling.

    membership = {as_of, basis, source_ref, members: [{industry,ticker,issuer_id?}]}.
    Missing issuer identity uses a disclosed ticker proxy, not fake qualification.
    Multiple share classes for one issuer need an explicit primary=True member;
    otherwise that issuer is excluded, not counted twice or chosen by outcome.
    """
    cutoff = _day(as_of)
    if not isinstance(membership, dict) or membership.get("basis") not in MEMBERSHIP_BASES:
        raise ValueError("explicit membership basis required")
    if membership.get("as_of") != as_of or not membership.get("source_ref"):
        raise ValueError("membership date and source reference must bind the request")
    if not isinstance(max_age_sessions, int) or isinstance(max_age_sessions, bool) or max_age_sessions < 0:
        raise ValueError("invalid freshness window")
    if not 0 < minimum_coverage <= 1:
        raise ValueError("coverage must be in (0,1]")
    members = membership.get("members")
    if not isinstance(members, list):
        raise ValueError("membership rows required")
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    seen = set()
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("invalid member")
        industry, ticker = member.get("industry"), member.get("ticker")
        if not all(isinstance(x, str) and x.strip() for x in (industry, ticker)):
            raise ValueError("industry and ticker identity required")
        key = (industry, ticker)
        if key in seen:
            raise ValueError("duplicate industry/ticker membership")
        seen.add(key)
        issuer = member.get("issuer_id")
        if issuer is not None and (not isinstance(issuer, str) or not issuer.strip()):
            raise ValueError("invalid issuer identity")
        grouped[industry][issuer or "ticker_proxy:" + ticker].append(member)
    groups = {}
    for industry, issuers in sorted(grouped.items()):
        diagnostics, accepted, coupling_states = [], [], Counter()
        for issuer, classes in sorted(issuers.items()):
            chosen = classes if len(classes) == 1 else [x for x in classes if x.get("primary") is True]
            if len(chosen) != 1:
                diagnostics.append({"issuer": issuer, "status": "AMBIGUOUS_SHARE_CLASS"})
                continue
            ticker = chosen[0]["ticker"]
            snap = snapshots.get(ticker)
            reason = None
            if not isinstance(snap, dict) or snap.get("schema") != "leader_recovery_expectations.v1":
                reason = "MISSING_OWNER_SNAPSHOT"
            elif snap.get("ticker") != ticker or snap.get("as_of") != as_of:
                reason = "SNAPSHOT_IDENTITY_OR_CUTOFF_MISMATCH"
            elif snap.get("availability") != "SOURCE_DATED_OBSERVATIONS":
                reason = "OWNER_NUMERICS_UNAVAILABLE"
            elif snap.get("quality_flags"):
                reason = "OWNER_QUALITY_FLAGS"
            else:
                try:
                    source_day = _day(snap.get("source_date"))
                    age = snap.get("source_age_sessions")
                    if source_day > cutoff:
                        reason = "SOURCE_AFTER_CUTOFF"
                    elif not isinstance(age, int) or isinstance(age, bool) or age < 0:
                        reason = "SOURCE_AGE_UNQUALIFIED"
                    elif age > max_age_sessions:
                        reason = "STALE_SNAPSHOT"
                except (TypeError, ValueError):
                    reason = "SOURCE_DATE_UNAVAILABLE"
            if reason:
                diagnostics.append({"issuer": issuer, "ticker": ticker, "status": reason})
                continue
            drift = _reading(snap, "eps_estimate_change_30d")
            breadth = _reading(snap, "coverage_normalized_net_revisions")
            accepted.append({"issuer": issuer, "ticker": ticker, "eps_change_pct": drift,
                             "revision_breadth": breadth, "source_date": snap["source_date"],
                             "first_seen_qualified": snap.get("first_seen_qualified") is True})
            diagnostics.append({"issuer": issuer, "ticker": ticker, "status": "OBSERVED_CONTEXT"})
            native = (k3e_inputs or {}).get(ticker, {})
            expectation, market = native.get("expectation"), native.get("market")
            if expectation is not None:
                query = expectation.get("semantic_payload", {}).get("query", {}) if isinstance(expectation, dict) else {}
                native_date = str(query.get("as_of", ""))[:10]
                if query.get("ticker_compat") != ticker or native_date != as_of:
                    coupling_states["SUBJECT_OR_CUTOFF_MISMATCH"] += 1
                    continue
            coupling = compose_descriptive_coupling(expectation, market)
            coupling_states[coupling["state"]] += 1
        valid_drift = [x["eps_change_pct"] for x in accepted if x["eps_change_pct"] is not None]
        valid_breadth = [x["revision_breadth"] for x in accepted if x["revision_breadth"] is not None]
        denominator = len(issuers)
        coverage = len(valid_drift) / denominator if denominator else 0.0
        groups[industry] = {
            "industry": industry, "issuer_count": denominator,
            "snapshot_count": len(accepted), "eps_drift_count": len(valid_drift),
            "eps_drift_coverage": coverage,
            "status": "OBSERVED_RESEARCH_CONTEXT" if coverage >= minimum_coverage else "SPARSE_CONTEXT",
            "median_eps_change_30d_pct": median(valid_drift) if valid_drift else None,
            "eps_positive_share": sum(x > 0 for x in valid_drift) / len(valid_drift) if valid_drift else None,
            "eps_negative_share": sum(x < 0 for x in valid_drift) / len(valid_drift) if valid_drift else None,
            "median_coverage_normalized_revisions": median(valid_breadth) if valid_breadth else None,
            "coverage_breadth_count": len(valid_breadth),
            "issuer_identity_qualified": not any(x.startswith("ticker_proxy:") for x in issuers),
            "all_first_seen_qualified": bool(accepted) and all(x["first_seen_qualified"] for x in accepted),
            "k3e_component_states": dict(coupling_states),
            "normalized_k3e_revision": None,
            "members": accepted, "diagnostics": diagnostics,
        }
    return {"schema": SCHEMA, "as_of": as_of, "membership_basis": membership["basis"],
            "membership_source_ref": membership["source_ref"], "groups": groups,
            "authority": "research_context_only", "financial_influence": False,
            "k3e_normalized_baseline_modified": False,
            "disclosure": "Equal-issuer source-dated observations; no causal incorporation or calibrated trading probability."}


def from_revision_frame(membership: dict, revisions: pd.DataFrame, *, as_of: str,
                        sessions: list[date], k3e_inputs: dict[str, dict] | None = None) -> dict:
    """Actual adapter to the incumbent source owner; does not duplicate its parser."""
    cutoff = _day(as_of)
    if sessions != sorted(set(sessions)) or any(not isinstance(x, date) for x in sessions):
        raise ValueError("explicit unique ordered session calendar required")
    tickers = sorted({x["ticker"] for x in membership.get("members", [])})
    snapshots = {ticker: project_expectations(ticker, revisions, as_of=cutoff, sessions=sessions)
                 for ticker in tickers}
    return aggregate_industry_expectations(membership, snapshots, as_of=as_of, k3e_inputs=k3e_inputs)


def compare_same_issuers(previous: dict, current: dict, industry: str) -> dict:
    """Composition-controlled change; never subtract changing-population averages."""
    for item in (previous, current):
        if item.get("schema") != SCHEMA or item.get("financial_influence") is not False:
            raise ValueError("unsupported expectations envelope")
    if _day(previous["as_of"]) >= _day(current["as_of"]):
        raise ValueError("previous observation must precede current")
    a = previous.get("groups", {}).get(industry, {})
    b = current.get("groups", {}).get(industry, {})
    old = {x["issuer"]: x for x in a.get("members", [])}
    new = {x["issuer"]: x for x in b.get("members", [])}
    common = sorted(set(old) & set(new))
    pairs = [(old[k]["eps_change_pct"], new[k]["eps_change_pct"]) for k in common
             if old[k]["eps_change_pct"] is not None and new[k]["eps_change_pct"] is not None
             and old[k]["source_date"] < new[k]["source_date"]]
    return {"industry": industry, "previous_as_of": previous["as_of"], "as_of": current["as_of"],
            "common_issuers": len(common), "new_capture_pairs": len(pairs),
            "matched_change_in_reported_30d_drift_pp": median([y - x for x, y in pairs]) if pairs else None,
            "interpretation": "Change in reported rolling drift, not normalized revision acceleration; overlap and fiscal-roll effects remain possible.",
            "financial_influence": False}


def compose_industry_context(price_rows: list[dict], expectations: dict, *, as_of: str,
                             model_rows: list[dict] | None = None, model_ref: str | None = None) -> dict:
    """Join measurements and forecasts without turning missing families into votes."""
    if expectations.get("schema") != SCHEMA or expectations.get("as_of") != as_of:
        raise ValueError("expectation envelope or cutoff mismatch")
    if expectations.get("financial_influence") is not False:
        raise ValueError("research-only expectation envelope required")
    if model_rows and not model_ref:
        raise ValueError("forecast provenance required")
    estimates = {}
    for row in model_rows or []:
        key = row.get("industry")
        if key in estimates or str(row.get("as_of"))[:10] != as_of:
            raise ValueError("duplicate/misaligned forecast")
        probs = [_number(row.get("p_" + name)) for name in ("upside_first", "downside_first", "unresolved")]
        if any(x is None or not 0 <= x <= 1 for x in probs) or abs(sum(probs) - 1) > 1e-8:
            raise ValueError("invalid competing-outcome probabilities")
        if row.get("probability_status") != "UNCALIBRATED_RESEARCH_ESTIMATE":
            raise ValueError("unqualified forecast status")
        estimates[key] = deepcopy(row)
    groups = {}
    for row in price_rows:
        industry = row.get("industry")
        if not isinstance(industry, str) or not industry or industry in groups:
            raise ValueError("unique price group identity required")
        if str(row.get("as_of"))[:10] != as_of:
            raise ValueError("price cutoff mismatch")
        context = expectations["groups"].get(industry)
        groups[industry] = {
            "industry": industry, "price_state": deepcopy(row),
            "expectations": deepcopy(context) if context else {"status": "UNAVAILABLE", "reason": "NO_MATCHING_INDUSTRY"},
            "forecast": estimates.get(industry),
            "next_question": ("Test continuation versus exhaustion" if row.get("state") == "leading" else
                              "Test recovery versus failed rebound" if row.get("state") == "improving" else
                              "Investigate persistence of weakness"),
        }
    return {"schema": "prophet.industry_context_composition.v1", "as_of": as_of,
            "authority": "research_context_only", "financial_influence": False,
            "model_ref": model_ref, "groups": groups,
            "probability_status": "UNCALIBRATED_RESEARCH_ESTIMATE" if estimates else "NOT_ESTIMATED"}


def attach_to_candidates(candidates: list[dict], context: dict, *, as_of: str) -> list[dict]:
    """Add a namespaced read only; preserve all existing timer/rank/score fields."""
    if (context.get("schema") != "prophet.industry_context_composition.v1"
            or context.get("as_of") != as_of or context.get("financial_influence") is not False):
        raise ValueError("unsupported context envelope")
    output = []
    for original in candidates:
        row = deepcopy(original)
        if "industry_research_context" in row:
            raise ValueError("refuse overwrite of existing context")
        if row.get("as_of") != as_of:
            raise ValueError("candidate cutoff mismatch")
        industry = row.get("industry")
        row["industry_research_context"] = {
            "schema": context["schema"], "as_of": as_of, "financial_influence": False,
            "status": "AVAILABLE" if industry in context["groups"] else "UNAVAILABLE",
            "context": deepcopy(context["groups"].get(industry)),
        }
        output.append(row)
    return output
