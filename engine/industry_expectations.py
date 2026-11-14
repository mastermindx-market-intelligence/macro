"""K3E-compatible research context without changing K3E owner qualification.

Reconstructed observations are usable for discovery, not backdated claims about
what the system actually knew. This module is a stateless adapter, not a warehouse
or a replacement for SRC-A1, EXP-1, MKT-1 or K3E evaluation admission.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import math
from typing import Any, Iterable

SCHEMA = "prophet.industry_expectations_research.v1"
ALLOWED_MODES = {"AS_CAPTURED", "RECONSTRUCTED"}
KEY = ("security_ref", "metric", "period_end", "currency", "basis")


def clock(value: str) -> datetime:
    if not isinstance(value, str): raise ValueError("timestamp must be a string")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None: raise ValueError("timestamp must include a timezone")
    return t.astimezone(timezone.utc)


def _number(x: Any) -> float:
    if isinstance(x, bool): raise ValueError("boolean is not a measurement")
    v = float(x)
    if not math.isfinite(v): raise ValueError("finite measurement required")
    return v


def expectation_changes(observations: Iterable[dict], *, as_of: str,
                        mode: str, assumed_lag_days: int = 90,
                        additional_lag_days: int = 0,
                        stale_days: int = 120) -> dict:
    """Compute same-security/metric/period/basis changes with explicit clocks.

    AS_CAPTURED uses both source observation and system observation clocks.
    RECONSTRUCTED uses an explicitly supplied historical effective timestamp
    plus an assumed publication lag; the later actual capture remains visible.
    A current snapshot without a historical effective timestamp is not silently
    transformed into decades of history. Period rolls are separate groups.
    """
    if mode not in ALLOWED_MODES: raise ValueError("unsupported evidence mode")
    if any(type(v) is not int or v < 0 for v in (assumed_lag_days, additional_lag_days, stale_days)):
        raise ValueError("lag and freshness parameters must be nonnegative integer days")
    cutoff = clock(as_of); groups: dict[tuple, list] = {}; exclusions: dict[str, int] = {}
    raw_count = 0; source_ids = set(); revision_ids: dict[str, str] = {}
    def exclude(reason): exclusions[reason] = exclusions.get(reason, 0) + 1
    for original in observations:
        raw_count += 1
        if not isinstance(original, dict): exclude("INVALID_RECORD"); continue
        row = dict(original)
        if not all(isinstance(row.get(k), str) and row[k].strip() for k in KEY):
            exclude("INCOMPARABLE_IDENTITY_OR_BASIS"); continue
        if row.get("metric") not in {"eps", "revenue", "guidance_eps", "guidance_revenue"}:
            exclude("UNSUPPORTED_METRIC"); continue
        if not row.get("source_ref") or not row.get("observation_id"):
            exclude("MISSING_SOURCE_IDENTITY"); continue
        if row.get("missingness_reason") is not None:
            exclude("SOURCE_MISSING"); continue
        if row.get("rights_state") == "RIGHTS_BLOCKED":
            exclude("RIGHTS_BLOCKED"); continue
        try:
            value = _number(row.get("value")); observed = clock(row["system_observed_at"])
            if mode == "AS_CAPTURED":
                published = clock(row["source_available_at"])
                effective = max(published, observed)
                assumed = False
            else:
                effective = clock(row["historical_effective_at"]) + timedelta(days=assumed_lag_days)
                assumed = True
            effective += timedelta(days=additional_lag_days)
        except (ValueError, TypeError, KeyError, OverflowError):
            exclude("INVALID_OR_MISSING_CLOCK_VALUE"); continue
        if effective > cutoff: exclude("NOT_AVAILABLE_AT_CUTOFF"); continue
        identity = str(row["observation_id"])
        binding = sha256(json.dumps(row, sort_keys=True, allow_nan=False).encode()).hexdigest()
        if identity in revision_ids:
            if revision_ids[identity] != binding:
                raise ValueError("conflicting bytes for the same observation_id")
            exclude("DUPLICATE_IDENTICAL_OBSERVATION"); continue
        revision_ids[identity] = binding
        source_ids.add(str(row["source_ref"]))
        key = tuple(row[k] for k in KEY)
        groups.setdefault(key, []).append((effective, observed, identity, value, assumed, str(row["source_ref"])))
    nodes = []
    for key, values in sorted(groups.items()):
        # Multiple independent values at one effective timestamp are ambiguous,
        # not averaged as though their contributors were known.
        values.sort(key=lambda x: (x[0], x[1], x[2]))
        latest = values[-1]
        same_clock = [x for x in values if x[0] == latest[0]]
        ambiguous = len({x[3] for x in same_clock}) > 1
        prior = [x for x in values if x[0] < latest[0]]
        previous = prior[-1] if prior else None
        if previous is not None:
            ambiguous = ambiguous or len({x[3] for x in prior if x[0] == previous[0]}) > 1
        age = (cutoff - latest[0]).total_seconds() / 86400
        state = "AMBIGUOUS" if ambiguous else "STALE" if age > stale_days else "AVAILABLE"
        delta = latest[3] - previous[3] if previous and state == "AVAILABLE" else None
        denom = max(abs(previous[3]), abs(latest[3])) if previous else None
        scaled = delta / denom if delta is not None and denom and denom > 1e-12 else None
        node = dict(zip(KEY, key))
        node.update(state=state, latest_value=latest[3] if not ambiguous else None,
                    previous_value=previous[3] if previous else None,
                    change=delta, symmetric_relative_change=scaled,
                    latest_effective_at=latest[0].isoformat(), actual_capture_at=latest[1].isoformat(),
                    age_days=age, records=len(values), latest_observation_id=latest[2],
                    previous_observation_id=previous[2] if previous else None,
                    source_refs=sorted({x[5] for x in values}), clock_assumed=latest[4],
                    historical_knowability_proven=not latest[4],
                    change_semantics="captured_or_reconstructed_value_change_not_analyst_revision")
        nodes.append(node)
    return {"schema": SCHEMA, "as_of": cutoff.isoformat(), "mode": mode,
            "authority": "research_context_only", "financial_influence": False,
            "assumed_lag_days": assumed_lag_days if mode == "RECONSTRUCTED" else None,
            "additional_lag_days": additional_lag_days, "records_received": raw_count,
            "records_used": sum(n["records"] for n in nodes), "exclusions": exclusions,
            "source_refs": sorted(source_ids), "nodes": nodes,
            "limitations": ["Comparability relies on supplied identity/currency/basis assertions.",
                            "Reconstructed effective time is an assumption, not historical capture proof.",
                            "Changes in estimates are not a calibrated trade signal."]}


def lag_sensitivity(observations: list[dict], *, as_of: str,
                    assumed_lag_days: int = 90) -> dict:
    """Declared 0/30/60-day additional delays; no favorable-lag selection."""
    readings = {str(d): expectation_changes(observations, as_of=as_of, mode="RECONSTRUCTED",
                                           assumed_lag_days=assumed_lag_days, additional_lag_days=d)
                for d in (0, 30, 60)}
    return {"schema": "prophet.industry_expectation_lag_sensitivity.v1", "readings": readings,
            "selected_best_lag": None, "financial_influence": False}


def aggregate_industry_context(result: dict, membership: list[dict], *, as_of: str) -> dict:
    """Aggregate economic expectation changes using dated, leave-identity-aware membership.

    Metrics and fiscal periods never get blended into one scalar. One security
    contributes at most one observation to a metric/period/basis denominator.
    """
    if result.get("schema") != SCHEMA or result.get("financial_influence") is not False:
        raise ValueError("unsupported expectation context")
    cutoff = clock(as_of)
    if clock(result["as_of"]) != cutoff: raise ValueError("context cutoff mismatch")
    members = {}
    for row in membership:
        if clock(row["valid_from"]) > cutoff: continue
        if row.get("valid_to") and clock(row["valid_to"]) <= cutoff: continue
        if result["mode"] == "AS_CAPTURED" and clock(row["known_at"]) > cutoff: continue
        sec = row["security_ref"]
        if sec in members and members[sec] != row["industry"]:
            raise ValueError("ambiguous industry membership")
        members[sec] = row["industry"]
    groups = {}
    for node in result["nodes"]:
        industry = members.get(node["security_ref"])
        if not industry: continue
        key = (industry, node["metric"], node["period_end"], node["currency"], node["basis"])
        groups.setdefault(key, []).append(node)
    out = []
    for key, nodes in sorted(groups.items()):
        good = [n for n in nodes if n["state"] == "AVAILABLE" and n["change"] is not None]
        out.append(dict(zip(("industry", "metric", "period_end", "currency", "basis"), key)) |
                   {"covered_securities": len(nodes), "comparable_changes": len(good),
                    "industry_members": sum(v == key[0] for v in members.values()),
                    "revision_breadth": (sum(n["change"] > 0 for n in good) - sum(n["change"] < 0 for n in good)) / len(good) if good else None,
                    "state": "AVAILABLE" if good else "UNESTIMABLE",
                    "evidence_mode": result["mode"],
                    "change_semantics": "comparable_value_changes_not_identified_analyst_revisions"})
    return {"schema": "prophet.industry_expectation_aggregation.v1", "as_of": as_of,
            "groups": out, "financial_influence": False, "mode": result["mode"]}


def compose_with_k3e(forecast: dict, *, expectation_inspection: dict | None = None,
                    market_response: dict | None = None, research_context: dict | None = None,
                    member_binding: dict | None = None) -> dict:
    """Delegate accepted K3E semantics to its original pure composer.

    Never feed reconstruction into a qualified owner input or silently treat
    absent K3E as a favorable condition. This attachment cannot alter forecasts.
    """
    from engine.k3e_coupling import compose_descriptive_coupling
    if forecast.get("schema") != "prophet.industry_transition.v1" or forecast.get("financial_influence") is not False:
        raise ValueError("research forecast required")
    result = json.loads(json.dumps(forecast, allow_nan=False))
    result["k3e"] = compose_descriptive_coupling(expectation_inspection, market_response)
    subject = result["k3e"].get("expectation", {}).get("ticker") or result["k3e"].get("market", {}).get("ticker")
    if subject is not None:
        if not member_binding or member_binding.get("industry") != forecast["industry"] or member_binding.get("ticker") != subject:
            raise ValueError("K3E company context requires matching industry membership")
        cutoff = clock(forecast["decision_date"] + "T23:59:59+00:00")
        if clock(member_binding["valid_from"]) > cutoff or (member_binding.get("valid_to") and clock(member_binding["valid_to"]) <= cutoff):
            raise ValueError("K3E membership not effective at decision")
        if forecast["evidence_mode"] == "OBSERVED_SHADOW" and clock(member_binding["known_at"]) > cutoff:
            raise ValueError("K3E membership not known at decision")
    result["k3e_member_binding"] = member_binding
    if research_context is not None:
        if research_context.get("schema") != SCHEMA or research_context.get("financial_influence") is not False:
            raise ValueError("invalid reconstruction context")
        decision_end = clock(forecast["decision_date"] + "T23:59:59+00:00")
        if clock(research_context["as_of"]) > decision_end:
            raise ValueError("research context is after the forecast decision date")
    result["reconstructed_expectations"] = research_context
    result["context_changes_forecast"] = False
    return result
