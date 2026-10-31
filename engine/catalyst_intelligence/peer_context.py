"""Synchronized descriptive comparisons for explicitly supplied research cohorts.

This calculator does not discover peers, admit GMI memberships, resolve rights,
infer issuer identity, rank securities, or identify causal spillovers. Its input
is a frozen research fixture or an owner-supplied research snapshot. A source ref
or a self-consistent digest is provenance, never proof of source admission.

The entire focal issuer is excluded. A missing observation stays in the frozen
eligible denominator. Partial aggregates explicitly describe the observed subset;
the complete-cohort aggregate is absent until every eligible issuer is observed.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import re
from statistics import mean, median, pstdev
from typing import Any


INPUT_SCHEMA = "catalyst.supplied_peer_research_inputs.v1"
OUTPUT_SCHEMA = "catalyst.peer_research_context.v1"
MAX_ROWS = 512
AUTHORITY = {
    "may_rank": False, "may_size": False, "may_gate": False,
    "may_execute": False, "may_publish": False, "may_change_entry": False,
    "may_admit_membership": False, "may_claim_causality": False,
}


class ContextError(ValueError):
    """A bounded research input or cross-owner consistency error."""


def canonical(value: object) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError) as exc:
        raise ContextError("input is not finite JSON") from exc


def digest(value: object) -> str:
    return "sha256:" + sha256(canonical(value).encode()).hexdigest()


def closed(value: object, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ContextError(f"{label}: fields are not closed")
    return value


def text(value: object, label: str) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > 512
            or any(ord(c) < 32 for c in value)):
        raise ContextError(f"{label}: expected bounded nonempty text")
    return value


def clock(value: object, label: str) -> datetime:
    raw = text(value, label)
    if not raw.endswith("Z") or "T" not in raw:
        raise ContextError(f"{label}: expected UTC timestamp ending Z")
    try:
        dt = datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise ContextError(f"{label}: invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset().total_seconds() != 0:
        raise ContextError(f"{label}: expected UTC")
    return dt.astimezone(timezone.utc)


def number(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ContextError(f"{label}: expected finite number")
    try:
        out = float(value)
    except OverflowError as exc:
        raise ContextError(f"{label}: number out of range") from exc
    if not math.isfinite(out) or (positive and out <= 0):
        raise ContextError(f"{label}: invalid finite number")
    return out


def rows(value: object, label: str) -> list:
    if not isinstance(value, list) or len(value) > MAX_ROWS:
        raise ContextError(f"{label}: expected list of at most {MAX_ROWS} rows")
    return value


def _identity(row: Mapping[str, Any]) -> tuple[str, str, str]:
    return tuple(text(row[k], k) for k in ("security_id", "company_id", "identity_epoch"))


def _unique(items: list, key, label: str) -> list:
    """Exact repeated graph paths collapse; contradictory bindings refuse."""
    out = {}
    for row in items:
        k = key(row)
        if k in out and canonical(out[k]) != canonical(row):
            raise ContextError(f"{label}: conflicting duplicate")
        out[k] = row
    return [out[k] for k in sorted(out)]


def build_peer_context(inputs: Mapping[str, Any]) -> dict[str, Any]:
    inp = closed(inputs, {"schema", "decision_at", "focal", "cohort", "window",
                          "observations", "catalysts", "catalyst_coverage"}, "inputs")
    if inp["schema"] != INPUT_SCHEMA:
        raise ContextError("peer input schema mismatch")
    decision = clock(inp["decision_at"], "decision_at")
    focal = closed(inp["focal"], {"security_id", "company_id", "identity_epoch",
                                "identity_source_ref"}, "focal")
    focal_key = _identity(focal)
    text(focal["identity_source_ref"], "identity_source_ref")
    cohort = closed(inp["cohort"], {"subtheme_id", "definition_ref", "membership_ref",
                                   "universe_description", "formed_at", "purpose",
                                   "rights_ref", "members"}, "cohort")
    for key in ("subtheme_id", "definition_ref", "membership_ref", "universe_description", "rights_ref"):
        text(cohort[key], key)
    if cohort["purpose"] != "supplied_research_cohort":
        raise ContextError("only supplied research cohorts are supported")
    formed = clock(cohort["formed_at"], "formed_at")
    window = closed(inp["window"], {"start_at", "end_at", "currency", "return_basis",
                                   "max_age_seconds"}, "window")
    start, end = clock(window["start_at"], "start_at"), clock(window["end_at"], "end_at")
    if not formed <= start < end <= decision:
        raise ContextError("formation/window/decision ordering invalid")
    for key in ("currency", "return_basis"):
        text(window[key], key)
    age_limit = number(window["max_age_seconds"], "max_age_seconds", positive=True)

    members = rows(cohort["members"], "members")
    valid_members, excluded = [], []
    member_keys = {"security_id", "company_id", "identity_epoch", "known_at",
                   "effective_from", "effective_to", "source_ref"}
    for row in members:
        closed(row, member_keys, "member")
        _identity(row)
        text(row["source_ref"], "member.source_ref")
        known = clock(row["known_at"], "member.known_at")
        effective = clock(row["effective_from"], "member.effective_from")
        until = clock(row["effective_to"], "member.effective_to") if row["effective_to"] else None
        if until and until <= effective:
            raise ContextError("membership validity interval invalid")
        reason = ("MEMBERSHIP_NOT_KNOWN_AT_FORMATION" if known > formed else
                  "MEMBERSHIP_NOT_EFFECTIVE_AT_FORMATION" if effective > formed or (until and until <= formed)
                  else None)
        if reason:
            excluded.append({"security_id": row["security_id"], "reason": reason})
        else:
            valid_members.append(row)
    valid_members = _unique(valid_members, lambda r: r["security_id"], "members")
    focal_bound = any(_identity(r) == focal_key for r in valid_members)
    peers = [r for r in valid_members if r["company_id"] != focal["company_id"]]
    for row in valid_members:
        if row["company_id"] == focal["company_id"]:
            excluded.append({"security_id": row["security_id"], "reason": "FOCAL_ISSUER_EXCLUDED"})
    issuer_counts = Counter(r["company_id"] for r in peers)
    ambiguous = {k for k, n in issuer_counts.items() if n > 1}
    # No invented share-class selection rule. Every ambiguous issuer stays in
    # the eligible issuer denominator and gets no observed contribution.
    peer_issuers = sorted(issuer_counts)
    eligible = [r for r in peers if r["company_id"] not in ambiguous]
    for row in peers:
        if row["company_id"] in ambiguous:
            excluded.append({"security_id": row["security_id"], "reason": "AMBIGUOUS_PEER_LISTINGS"})

    obs_keys = {"security_id", "company_id", "identity_epoch", "start_at", "end_at",
                "known_at", "start_value", "end_value", "currency", "return_basis", "source_ref"}
    observations = rows(inp["observations"], "observations")
    for row in observations:
        closed(row, obs_keys, "observation")
        _identity(row)
        text(row["source_ref"], "observation.source_ref")
        a, b = clock(row["start_at"], "observation.start_at"), clock(row["end_at"], "observation.end_at")
        known = clock(row["known_at"], "observation.known_at")
        if not a < b <= known:
            raise ContextError("price observation clocks invalid")
        number(row["start_value"], "start_value", positive=True)
        number(row["end_value"], "end_value", positive=True)
        text(row["currency"], "currency")
        text(row["return_basis"], "return_basis")
    observations = _unique(observations, lambda r: r["security_id"], "observations")
    obs_by_id = {r["security_id"]: r for r in observations}

    def measure(member):
        row = obs_by_id.get(member["security_id"])
        reason = "PRICE_MISSING"
        if row:
            reason = ("PRICE_IDENTITY_MISMATCH" if _identity(row) != _identity(member) else
                      "PRICE_NOT_KNOWN_AT_DECISION" if clock(row["known_at"], "known_at") > decision else
                      "PRICE_WINDOW_MISMATCH" if clock(row["start_at"], "start_at") != start or clock(row["end_at"], "end_at") != end else
                      "PRICE_CURRENCY_MISMATCH" if row["currency"] != window["currency"] else
                      "PRICE_BASIS_MISMATCH" if row["return_basis"] != window["return_basis"] else
                      "PRICE_WINDOW_STALE" if (decision - end).total_seconds() > age_limit else None)
        if reason:
            excluded.append({"security_id": member["security_id"], "reason": reason})
            return None
        value = (number(row["end_value"], "end_value") / number(row["start_value"], "start_value") - 1) * 100
        if not math.isfinite(value):
            raise ContextError("return overflow")
        return {"security_id": member["security_id"], "company_id": member["company_id"],
                "return_pct": value, "source_ref": row["source_ref"], "known_at": row["known_at"]}

    focal_observation = measure(focal) if focal_bound else None
    measured = [m for m in (measure(row) for row in eligible) if m is not None] if focal_bound else []
    n, total = len(measured), len(peer_issuers)
    values = [r["return_pct"] for r in measured]
    all_observed = bool(total) and n == total and focal_observation is not None
    state = ("FOCAL_MEMBERSHIP_UNAVAILABLE" if not focal_bound else
             "FOCAL_PRICE_UNAVAILABLE" if focal_observation is None else
             "NO_ELIGIBLE_PEERS" if not total else "NO_OBSERVED_PEERS" if not n else
             "COMPLETE" if all_observed else "PARTIAL")
    observed_mean = mean(values) if values else None
    gap = focal_observation["return_pct"] - observed_mean if focal_observation and values else None
    catalysts = _catalysts(inp, decision, start, end, focal, valid_members)
    output = {
        "schema": OUTPUT_SCHEMA, "qualification": "SUPPLIED_RESEARCH_COHORT_ONLY",
        "source_admission_established": False, "authority": dict(AUTHORITY),
        "decision_at": inp["decision_at"], "focal": dict(focal),
        "cohort": {k: cohort[k] for k in cohort if k != "members"},
        "window": dict(window), "state": state,
        "coverage": {"eligible_peer_issuers": total, "observed_peer_issuers": n,
                     "fraction": n / total if total else None,
                     "ambiguous_peer_issuers": len(ambiguous)},
        "focal_observation": focal_observation,
        "observed_peers": sorted(measured, key=lambda r: r["security_id"]),
        "statistics": {
            "observed_subset_equal_weight_return_pct": observed_mean,
            "complete_cohort_equal_weight_return_pct": observed_mean if all_observed else None,
            "focal_minus_observed_peers_pp": gap,
            "observed_subset_median_return_pct": median(values) if values else None,
            "observed_subset_dispersion_pp": pstdev(values) if values else None,
            "advancing": sum(x > 0 for x in values), "declining": sum(x < 0 for x in values),
            "unchanged": sum(x == 0 for x in values),
            "effective_observed_issuer_count": n,
        },
        "excluded": sorted({canonical(r): r for r in excluded}.values(), key=lambda r: (r["security_id"], r["reason"])),
        "catalyst_context": catalysts,
        "interpretation_limits": ["RELATIVE_RETURN_IS_NOT_FACTOR_RESIDUAL",
                                  "PARTICIPATION_IS_NOT_CAUSAL_SPILLOVER",
                                  "NO_INTRADAY_LEAD_LAG_FROM_WINDOW_RETURNS",
                                  "COHORT_IS_NOT_ALL_SUBTHEME_SECURITIES",
                                  "NO_SOURCE_OR_DISPLAY_ADMISSION"],
    }
    output["input_digest"] = digest(inp)
    output["context_id"] = digest(output)
    return json.loads(canonical(output))


def _catalysts(inp, decision, start, end, focal, members):
    """Compare owner-assigned event keys, never headline similarity or prices."""
    keys = {"event_owner", "event_id", "revision_id", "security_id", "company_id", "identity_epoch",
            "event_type", "comparison_owner", "comparison_key", "source_available_at", "known_at",
            "status", "source_ref"}
    items = rows(inp["catalysts"], "catalysts")
    for row in items:
        closed(row, keys, "catalyst")
        _identity(row)
        for k in ("event_id", "revision_id", "event_type", "source_ref"):
            text(row[k], k)
        if not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", text(row["event_owner"], "event_owner")):
            raise ContextError("invalid event owner namespace")
        if row["comparison_key"] is not None:
            text(row["comparison_key"], "comparison_key")
            if not re.fullmatch(r"[a-z][a-z0-9_.-]{0,63}", text(row["comparison_owner"], "comparison_owner")):
                raise ContextError("invalid comparison owner namespace")
        elif row["comparison_owner"] is not None:
            raise ContextError("comparison owner without comparison key")
        if row["status"] not in {"current", "superseded", "withdrawn", "cancelled"}:
            raise ContextError("invalid catalyst status")
        if clock(row["source_available_at"], "source_available_at") > clock(row["known_at"], "known_at"):
            raise ContextError("catalyst availability follows observation")
    def event_key(row):
        return row["event_owner"] + "::" + row["event_id"]

    def comparison_key(row):
        return (row["comparison_owner"], row["comparison_key"])

    items = _unique(items, lambda r: (event_key(r), r["revision_id"], r["security_id"]), "catalysts")
    visible = [r for r in items if clock(r["known_at"], "known_at") <= decision]
    bound = {_identity(r) for r in members}
    visible_bound = [r for r in visible if _identity(r) in bound]
    # Owner must supply one finalized current revision. This calculator never
    # elects a winner from contradictory revisions or repairs a correction chain.
    groups = {}
    for row in visible_bound:
        groups.setdefault((event_key(row), row["security_id"]), []).append(row)
    for revisions in groups.values():
        current_count = sum(r["status"] == "current" for r in revisions)
        terminal = any(r["status"] in {"withdrawn", "cancelled"} for r in revisions)
        if current_count > 1 or (current_count and terminal):
            raise ContextError("conflicting catalyst revisions require owner reconciliation")
    window_observations = [r for r in visible_bound
                           if start < clock(r["source_available_at"], "available") <= end]
    current = [r for r in window_observations if r["status"] == "current"]
    focal_events = [r for r in current if _identity(r) == _identity(focal)]
    focal_ids = {event_key(r) for r in focal_events}
    comparison_keys = {comparison_key(r) for r in focal_events if r["comparison_key"] is not None}
    coverage = rows(inp["catalyst_coverage"], "catalyst_coverage")
    for row in coverage:
        closed(row, {"security_id", "company_id", "identity_epoch", "covered_from",
                     "covered_through", "known_at", "state", "source_ref"}, "catalyst_coverage")
        _identity(row)
        text(row["source_ref"], "coverage.source_ref")
        a, b, k = [clock(row[x], x) for x in ("covered_from", "covered_through", "known_at")]
        if not a <= b <= k or row["state"] not in {"covered", "unavailable"}:
            raise ContextError("invalid catalyst coverage")
    coverage = _unique(coverage, lambda r: r["security_id"], "catalyst_coverage")
    cov = {r["security_id"]: r for r in coverage}
    result = []
    for member in sorted(members, key=lambda r: r["security_id"]):
        if member["company_id"] == focal["company_id"]:
            continue
        events = [r for r in current if _identity(r) == _identity(member)]
        observed = [r for r in window_observations if _identity(r) == _identity(member)]
        same = [event_key(r) for r in events if event_key(r) in focal_ids]
        comparable = [event_key(r) for r in events if event_key(r) not in focal_ids
                      and r["comparison_key"] is not None and comparison_key(r) in comparison_keys]
        other = [event_key(r) for r in events if event_key(r) not in set(same + comparable)]
        c = cov.get(member["security_id"])
        covered = bool(c and _identity(c) == _identity(member) and c["state"] == "covered"
                       and clock(c["covered_from"], "from") <= start
                       and clock(c["covered_through"], "through") >= end
                       and clock(c["known_at"], "known_at") <= decision)
        result.append({"security_id": member["security_id"], "company_id": member["company_id"],
                       "coverage_state": "COVERED_DECLARED_SOURCES" if covered else "COVERAGE_UNKNOWN",
                       "same_underlying_event_ids": sorted(set(same)),
                       "distinct_comparable_event_ids": sorted(set(comparable)),
                       "other_observed_event_ids": sorted(set(other)),
                       "no_event_observed_in_covered_sources": covered and not observed,
                       "observed_event_revisions": [{k: r[k] for k in (
                           "event_owner", "event_id", "revision_id", "status", "known_at", "source_ref")}
                           for r in sorted(observed, key=lambda r: (event_key(r), r["revision_id"]))],
                       "evidence_refs": sorted({r["source_ref"] for r in observed})})
    return {"focal_event_ids": sorted(focal_ids), "peers": result,
            "comparison_basis": "EXPLICIT_OWNER_COMPARISON_KEYS",
            "late_observation_count": len(items) - len(visible),
            "superseded_revision_count": sum(r["status"] == "superseded" for r in visible),
            "withdrawn_or_cancelled_count": sum(r["status"] in {"withdrawn", "cancelled"} for r in visible)}
