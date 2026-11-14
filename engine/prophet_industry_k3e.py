"""Industry-level K3E/Prophet research composition, not a replacement owner.

Uses existing source-dated revisions and K3E descriptive coupling independently.
Reconstructed inputs are useful research evidence, never invented historical
availability. No live score, timer, ranking, position or order is changed.
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
from lib.nyse_calendar import sessions_between

SCHEMA = "prophet.industry_k3e_research.v1"
MEMBERSHIP_BASES = {"dated_membership", "reconstructed_static_membership", "synthetic_fixture"}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return float(value) if math.isfinite(value) else None
    except (OverflowError, ValueError):
        return None


def _day(value: Any) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("ISO date required")
    return date.fromisoformat(value)


def _reading(snapshot: dict, name: str) -> float | None:
    readings = snapshot.get("readings", {})
    item = readings.get(name, {}) if isinstance(readings, dict) else {}
    return _number(item.get("value")) if isinstance(item, dict) else None


def _native_component(native: Any, ticker: str, as_of: str) -> dict:
    """Do not gate independent K3E evidence on legacy revision availability."""
    if native is None:
        return {"state": "NOT_REQUESTED"}
    if not isinstance(native, dict):
        return {"state": "INVALID_COMPONENT_ENVELOPE"}
    expectation, market = native.get("expectation"), native.get("market")
    if expectation is not None:
        if not isinstance(expectation, dict) or not isinstance(expectation.get("semantic_payload"), dict):
            return {"state": "INVALID_COMPONENT_ENVELOPE"}
        query = expectation["semantic_payload"].get("query", {})
        if not isinstance(query, dict) or query.get("ticker_compat") != ticker or str(query.get("as_of", ""))[:10] != as_of:
            return {"state": "SUBJECT_OR_CUTOFF_MISMATCH"}
    if market is not None:
        if not isinstance(market, dict) or market.get("ticker") != ticker:
            return {"state": "SUBJECT_OR_CUTOFF_MISMATCH"}
        # An input without an explicit session end is not joined by inference.
        window = market.get("window", {})
        endpoint = window.get("end_session") if isinstance(window, dict) else None
        if endpoint != as_of:
            return {"state": "MARKET_CUTOFF_UNQUALIFIED"}
    coupling = compose_descriptive_coupling(expectation, market)
    return {"state": coupling["state"], "refusals": coupling.get("refusals", []),
            "query_identity": coupling.get("expectation", {}).get("query_identity"),
            "coupling_status": coupling.get("coupling", {}).get("status"),
            "financial_influence": False}


def aggregate_industry_expectations(membership: dict, snapshots: dict[str, dict], *, as_of: str,
                                   max_age_sessions: int = 10, minimum_coverage: float = .5,
                                   k3e_inputs: dict[str, dict] | None = None) -> dict:
    """Equal-issuer context; explicit coverage, independent evidence and missingness.

    Missing issuer identity is a disclosed ticker proxy. Ambiguous share classes
    need one explicit primary; never count duplicates as independent companies.
    Source EPS drift remains a legacy observation, not normalized K3E economics.
    """
    cutoff = _day(as_of)
    if not isinstance(membership, dict) or membership.get("basis") not in MEMBERSHIP_BASES:
        raise ValueError("explicit membership basis required")
    if membership.get("as_of") != as_of or not membership.get("source_ref"):
        raise ValueError("membership date and source reference must bind request")
    if not isinstance(snapshots, dict) or (k3e_inputs is not None and not isinstance(k3e_inputs, dict)):
        raise ValueError("source mappings required")
    if not isinstance(max_age_sessions, int) or isinstance(max_age_sessions, bool) or max_age_sessions < 0:
        raise ValueError("invalid freshness window")
    if _number(minimum_coverage) is None or not 0 < minimum_coverage <= 1:
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
        if (industry, ticker) in seen:
            raise ValueError("duplicate industry/ticker membership")
        seen.add((industry, ticker))
        issuer = member.get("issuer_id")
        if issuer is not None and (not isinstance(issuer, str) or not issuer.strip()):
            raise ValueError("invalid issuer identity")
        grouped[industry][issuer or "ticker_proxy:" + ticker].append(member)
    groups = {}
    for industry, issuers in sorted(grouped.items()):
        diagnostics, accepted, components = [], [], []
        coupling_states = Counter()
        for issuer, classes in sorted(issuers.items()):
            chosen = classes if len(classes) == 1 else [x for x in classes if x.get("primary") is True]
            if len(chosen) != 1:
                diagnostics.append({"issuer": issuer, "status": "AMBIGUOUS_SHARE_CLASS"})
                continue
            ticker = chosen[0]["ticker"]
            component = _native_component((k3e_inputs or {}).get(ticker), ticker, as_of)
            coupling_states[component["state"]] += 1
            if component["state"] != "NOT_REQUESTED":
                components.append({"issuer": issuer, "ticker": ticker, **component})
            snap, reason = snapshots.get(ticker), None
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
                    source_day, age = _day(snap.get("source_date")), snap.get("source_age_sessions")
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
            accepted.append({"issuer": issuer, "ticker": ticker,
                "eps_change_pct": _reading(snap, "eps_estimate_change_30d"),
                "revision_breadth": _reading(snap, "coverage_normalized_net_revisions"),
                "source_date": snap["source_date"],
                "first_seen_qualified": snap.get("first_seen_qualified") is True})
            diagnostics.append({"issuer": issuer, "ticker": ticker, "status": "OBSERVED_CONTEXT"})
        drift = [x["eps_change_pct"] for x in accepted if x["eps_change_pct"] is not None]
        breadth = [x["revision_breadth"] for x in accepted if x["revision_breadth"] is not None]
        coverage = len(drift) / len(issuers) if issuers else 0.0
        groups[industry] = {
            "industry": industry, "issuer_count": len(issuers), "snapshot_count": len(accepted),
            "eps_drift_count": len(drift), "eps_drift_coverage": coverage,
            "status": "OBSERVED_RESEARCH_CONTEXT" if coverage >= minimum_coverage else "SPARSE_CONTEXT",
            "median_eps_change_30d_pct": median(drift) if drift else None,
            "eps_positive_share": sum(x > 0 for x in drift) / len(drift) if drift else None,
            "eps_negative_share": sum(x < 0 for x in drift) / len(drift) if drift else None,
            "median_coverage_normalized_revisions": median(breadth) if breadth else None,
            "coverage_breadth_count": len(breadth),
            "issuer_identity_qualified": not any(x.startswith("ticker_proxy:") for x in issuers),
            "all_first_seen_qualified": bool(accepted) and all(x["first_seen_qualified"] for x in accepted),
            "fiscal_comparability": "LEGACY_ROLLING_DRIFT_NOT_QUALIFIED_NORMALIZATION",
            "k3e_component_states": dict(coupling_states), "k3e_components": components,
            "normalized_k3e_revision": None, "members": accepted, "diagnostics": diagnostics,
        }
    return {"schema": SCHEMA, "as_of": as_of, "membership_basis": membership["basis"],
            "membership_source_ref": membership["source_ref"], "groups": groups,
            "authority": "research_context_only", "financial_influence": False,
            "k3e_normalized_baseline_modified": False,
            "disclosure": "Equal-issuer source-dated observations; no causal incorporation or calibrated trading probability."}


def from_revision_frame(membership: dict, revisions: pd.DataFrame, *, as_of: str,
                        sessions: list[date], k3e_inputs: dict[str, dict] | None = None) -> dict:
    """Use the incumbent parser with a checked, complete native session calendar."""
    cutoff = _day(as_of)
    if (not isinstance(sessions, list) or not sessions or any(type(x) is not date for x in sessions)
            or sessions != sessions_between(sessions[0], cutoff)):
        raise ValueError("complete unique native session calendar through cutoff required")
    tickers = sorted({x["ticker"] for x in membership.get("members", [])})
    snapshots = {ticker: project_expectations(ticker, revisions, as_of=cutoff, sessions=sessions)
                 for ticker in tickers}
    for snapshot in snapshots.values():
        source = snapshot.get("source_date")
        if source is not None and _day(source) < sessions[0]:
            snapshot["source_age_sessions"] = None
    return aggregate_industry_expectations(membership, snapshots, as_of=as_of, k3e_inputs=k3e_inputs)


def compare_same_issuers(previous: dict, current: dict, industry: str) -> dict:
    """Composition-controlled observed change, not subtracting moving populations."""
    for item in (previous, current):
        if item.get("schema") != SCHEMA or item.get("financial_influence") is not False:
            raise ValueError("unsupported expectations envelope")
    if _day(previous["as_of"]) >= _day(current["as_of"]):
        raise ValueError("previous observation must precede current")
    old = {x["issuer"]: x for x in previous.get("groups", {}).get(industry, {}).get("members", [])}
    new = {x["issuer"]: x for x in current.get("groups", {}).get(industry, {}).get("members", [])}
    common = sorted(set(old) & set(new))
    pairs = [(old[k]["eps_change_pct"], new[k]["eps_change_pct"]) for k in common
             if old[k]["eps_change_pct"] is not None and new[k]["eps_change_pct"] is not None
             and old[k]["source_date"] < new[k]["source_date"]]
    return {"industry": industry, "previous_as_of": previous["as_of"], "as_of": current["as_of"],
            "common_issuers": len(common), "new_capture_pairs": len(pairs),
            "matched_change_in_reported_30d_drift_pp": median([y - x for x, y in pairs]) if pairs else None,
            "interpretation": "Reported rolling drift change, not normalized revision acceleration; fiscal-roll and overlap remain possible.",
            "financial_influence": False}


def compose_industry_context(price_rows: list[dict], expectations: dict, *, as_of: str,
                             model_rows: list[dict] | None = None, model_ref: str | None = None) -> dict:
    """Join observations and research estimates; missing families are never votes."""
    _day(as_of)
    if expectations.get("schema") != SCHEMA or expectations.get("as_of") != as_of:
        raise ValueError("expectation envelope or cutoff mismatch")
    if expectations.get("financial_influence") is not False:
        raise ValueError("research-only expectation envelope required")
    if model_rows and not model_ref:
        raise ValueError("forecast provenance required")
    estimates = {}
    for row in model_rows or []:
        key = row.get("industry")
        if not isinstance(key, str) or not key or key in estimates or str(row.get("as_of"))[:10] != as_of:
            raise ValueError("duplicate/misaligned forecast")
        probs = [_number(row.get("p_" + name)) for name in ("upside_first", "downside_first", "unresolved")]
        if any(x is None or not 0 <= x <= 1 for x in probs) or abs(sum(probs) - 1) > 1e-8:
            raise ValueError("invalid competing-outcome probabilities")
        if (row.get("probability_status") != "UNCALIBRATED_RESEARCH_ESTIMATE"
                or _number(row.get("p_bad10")) is None or not 0 <= row["p_bad10"] <= 1
                or any(_number(row.get(k)) is None for k in ("expected_net63", "expected_excess63"))):
            raise ValueError("unqualified forecast status or values")
        estimates[key] = deepcopy(row)
    groups = {}
    for row in price_rows:
        industry = row.get("industry")
        if not isinstance(industry, str) or not industry or industry in groups:
            raise ValueError("unique price group identity required")
        if str(row.get("as_of"))[:10] != as_of:
            raise ValueError("price cutoff mismatch")
        if industry in estimates and row.get("basis") != estimates[industry].get("basis"):
            raise ValueError("forecast/measurement evidence basis mismatch")
        context = expectations["groups"].get(industry)
        groups[industry] = {"industry": industry, "price_state": deepcopy(row),
            "expectations": deepcopy(context) if context else {"status": "UNAVAILABLE", "reason": "NO_MATCHING_INDUSTRY"},
            "forecast": estimates.get(industry),
            "next_question": ("Test continuation versus exhaustion" if row.get("state") == "leading" else
                              "Test recovery versus failed rebound" if row.get("state") == "improving" else
                              "Investigate persistence of weakness")}
    if set(estimates) - set(groups):
        raise ValueError("forecast has no matching measurement")
    return {"schema": "prophet.industry_context_composition.v1", "as_of": as_of,
            "authority": "research_context_only", "financial_influence": False,
            "model_ref": model_ref, "groups": groups,
            "probability_status": "UNCALIBRATED_RESEARCH_ESTIMATE" if estimates else "NOT_ESTIMATED"}


def attach_to_candidates(candidates: list[dict], context: dict, *, as_of: str) -> list[dict]:
    """Namespaced read only; preserve existing timer, rank, state and score fields."""
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
        row["industry_research_context"] = {"schema": context["schema"], "as_of": as_of,
            "financial_influence": False, "status": "AVAILABLE" if industry in context["groups"] else "UNAVAILABLE",
            "context": deepcopy(context["groups"].get(industry))}
        output.append(row)
    return output
