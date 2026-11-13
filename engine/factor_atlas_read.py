"""Read-only Factor Atlas Session 1 measurement candidate.

This is an invocation-scoped projection, not a catalog, identity/membership store,
price collector, rights service or ThemeState. Inputs come from incumbent owners;
Data OS owns identifier, clock and price-basis meanings. The function has no I/O.

Scope: USD, regular consolidated closes, equal target weights at the initial
close and subsequent month ends, drifting constituent-total-return units between
rebalances. Dividends are already included in admitted TRADJ observations; do not
add them again. Returns are gross fractions, not a financed/investable strategy.

Reference checks below are necessary conditions, NOT authentication of an owner's
receipt or entitlement. All outputs remain CANDIDATE_NOT_ADMITTED; neither a
caller-provided reference nor passing synthetic tests authorizes publication.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
import math
import re
from statistics import stdev
from typing import Any

from engine.price_ladder import _basis_for_selected
from lib.dataos.identity import parse_id
from lib.dataos.price import AdjustmentBasis, Session, VenueScope
from lib.dataos.temporal import utc
from lib.market_session import _windows, calendar_verified
from lib.us_cash_calendar import ET, sessions_between

SCHEMA = "factor_atlas_read.v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_REQUEST_KEYS = {"basket_id", "history_mode", "start", "end", "measurement_cutoff",
                 "purpose", "weighting", "rebalance"}


def canonical_bytes(value: Any) -> bytes:
    """Stable strict JSON; NaN/Infinity are errors, never null or numeric zero."""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _ref(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 2048


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    try:
        value = float(value)
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) and value > 0 else None


def _clock(value: Any):
    try:
        return utc(value)
    except (TypeError, ValueError):
        return None


def _day(value: Any) -> str | None:
    try:
        return value if isinstance(value, str) and date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def _effective(on: str, start: Any, end: Any) -> bool:
    if start is not None and (_day(start) is None or on < start):
        return False
    if end is not None and (_day(end) is None or on >= end):
        return False
    return not (start is not None and end is not None and start >= end)


def _mapping(value: Any, name: str) -> dict:
    if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{name} must be a string-keyed mapping")
    return dict(value)


def _normalise(owner_inputs: Mapping[str, Any]) -> dict:
    data = deepcopy(_mapping(owner_inputs, "owner_inputs"))
    for key in ("calendar", "prices", "identity", "pit_rosters", "decision_cutoffs", "rights", "identity_by_date", "construction"):
        data[key] = _mapping(data.get(key, {}), key)
    for key, value in data["identity"].items():
        _mapping(value, f"identity.{key}")
    for on, entries in data["identity_by_date"].items():
        for sid, entry in _mapping(entries, "identity_by_date").items():
            _mapping(entry, f"identity_by_date.{on}.{sid}")
    for key, value in data["prices"].items():
        value = _mapping(value, f"prices.{key}")
        _mapping(value.get("evidence", {}), "price evidence")
        _mapping(value.get("values", {}), "price values")
    for value in [data.get("current_roster")] + list(data["pit_rosters"].values()):
        if value is not None:
            _mapping(value, "roster")
    # Membership order is not a weight or identity. Preserve duplicates for refusal.
    rosters = [data.get("current_roster")] + list((data.get("pit_rosters") or {}).values())
    for roster in rosters:
        if isinstance(roster, dict) and isinstance(roster.get("members"), list):
            if not all(isinstance(sid, str) for sid in roster["members"]):
                raise ValueError("membership identifiers must be strings")
            roster["members"] = sorted(roster["members"])
    try:
        canonical_bytes(data)
    except (TypeError, ValueError) as exc:
        raise ValueError("owner inputs must be finite JSON values") from exc
    return data


def _validate_request(request: Mapping[str, Any], data: dict):
    if set(request) != _REQUEST_KEYS:
        raise ValueError("request has missing or unsupported fields")
    allowed = {"history_mode": {"CURRENT_ROSTER", "PIT_AS_KNOWN"},
               "purpose": {"internal_research"}, "weighting": {"equal"}, "rebalance": {"monthly"}}
    for key, values in allowed.items():
        if request[key] not in values:
            raise ValueError(f"unsupported {key}: {request[key]!r}")
    if not _ref(request["basket_id"]):
        raise ValueError("basket_id must reference the incumbent basket owner")
    cutoff = utc(request["measurement_cutoff"])
    cal = data.get("calendar") or {}
    sessions = cal.get("sessions")
    if not _ref(cal.get("ref")) or not isinstance(sessions, list) or not 2 <= len(sessions) <= 1262:
        raise ValueError("a bounded owner calendar with an anchor and return sessions is required")
    days, clocks = [], {}
    for row in sessions:
        row = _mapping(row, "calendar session")
        day = row.get("date")
        if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
            raise ValueError("invalid calendar session date")
        if date.fromisoformat(day).weekday() >= 5:
            raise ValueError("unsupported weekend in modern US regular-session calendar")
        clock = utc(row["close_at"])
        if clock.date().isoformat() != day or clock > cutoff:
            raise ValueError("calendar session close is outside its date or measurement cutoff")
        days.append(day)
        clocks[day] = clock
    if days != sorted(set(days)):
        raise ValueError("duplicate or unordered calendar sessions")
    first, last = date.fromisoformat(days[0]), date.fromisoformat(days[-1])
    if (last - first).days > 1850:
        raise ValueError("calendar window exceeds the bounded pilot")
    expected_days = [day.isoformat() for day in sessions_between(first, last)]
    if days != expected_days:
        raise ValueError("calendar must contain every incumbent US cash session")
    for day in days:
        parsed = date.fromisoformat(day)
        expected_close = datetime.combine(parsed, _windows("US", parsed)[-1][1], tzinfo=ET).astimezone(timezone.utc)
        if clocks[day] != expected_close:
            raise ValueError("calendar close disagrees with the incumbent session owner")
    if any(clocks[b] <= clocks[a] for a, b in zip(days, days[1:])):
        raise ValueError("calendar close instants are not increasing")
    construction = data["construction"]
    if not _ref(construction.get("owner_ref")):
        raise ValueError("construction owner reference is required")
    if construction.get("inception") != days[0]:
        raise ValueError("complete calendar must start at the fixed construction inception")
    if request["start"] not in days or request["end"] != days[-1] or request["start"] >= request["end"]:
        raise ValueError("requested window needs an observed anchor and at least one return interval")
    expected = [days[0]] + [a for a, b in zip(days, days[1:]) if a[:7] != b[:7]]
    rebalances = cal.get("rebalance_dates")
    if not isinstance(rebalances, list) or sorted(rebalances) != sorted(set(expected)):
        raise ValueError("rebalance dates must match initial close and calendar month boundaries")
    decisions = data.get("decision_cutoffs") or {}
    for day in rebalances:
        decision = utc(decisions.get(day))
        if decision > clocks[day]:
            raise ValueError("rebalance decision follows execution close")
    if data.get("evidence_kind") not in {"SYNTHETIC_FIXTURE", "RETAINED_OWNER_INPUT"}:
        raise ValueError("unsupported evidence kind")
    if not _ref(data.get("code_ref")) or not _ref(data.get("input_revision")):
        raise ValueError("code and input revisions are required")
    if data.get("correction_of") is not None and not _sha(data["correction_of"]):
        raise ValueError("correction_of must identify the earlier result digest")
    return days, clocks, set(rebalances), cutoff


def _cohort(request: Mapping[str, Any], data: dict, day: str, cutoff):
    pit = request["history_mode"] == "PIT_AS_KNOWN"
    raw = (data.get("pit_rosters") or {}).get(day) if pit else data.get("current_roster")
    if not isinstance(raw, dict):
        return [], ["PIT_COVERAGE_UNAVAILABLE" if pit else "CURRENT_ROSTER_UNAVAILABLE"], None
    members = raw.get("members")
    if not isinstance(members, list) or len(members) > 512:
        raise ValueError("bounded explicit membership list required")
    if len(members) != len(set(members)):
        raise ValueError("duplicate security identity in cohort")
    reasons = []
    for sid in members:
        try:
            kind, _ = parse_id(sid)
            if kind != "security":
                raise ValueError("not a security")
        except ValueError:
            reasons.append("SECURITY_IDENTITY_UNAVAILABLE")
    if raw.get("basket_id") != request["basket_id"]:
        reasons.append("COHORT_ID_MISMATCH")
    if not members:
        reasons.append("COHORT_RETIRED" if raw.get("collection_state") == "RETIRED" else "COHORT_EMPTY")
    elif len(members) < 3:
        reasons.append("COHORT_TOO_SMALL")
    if raw.get("collection_state") != "COMPLETE":
        reasons.append("COLLECTION_NOT_COMPLETE")
    if raw.get("source_shape") != "membership":
        reasons.append("MEMBERSHIP_POPULATION_MISMATCH")
    if not _sha(raw.get("source_sha256")) or not _ref(raw.get("snapshot_ref")):
        reasons.append("MEMBERSHIP_RECEIPT_UNAVAILABLE")
    if pit and (raw.get("pit") is not True or raw.get("basis") != "pit_snapshot"):
        reasons.append("CURRENT_ROSTER_FALLBACK")
    query_day = _day(raw.get("asof"))
    snapshot_day = _day(raw.get("snapshot_date"))
    if query_day is None or (pit and query_day != day) or (not pit and query_day > cutoff.date().isoformat()):
        reasons.append("MEMBERSHIP_QUERY_MISMATCH")
    if snapshot_day is None:
        reasons.append("MEMBERSHIP_SNAPSHOT_UNAVAILABLE")
    elif query_day is not None and snapshot_day > query_day:
        reasons.append("MEMBERSHIP_FUTURE_SNAPSHOT")
    if "effective_from" not in raw or "effective_to" not in raw:
        reasons.append("MEMBERSHIP_INTERVAL_UNAVAILABLE")
    elif query_day is not None and not _effective(query_day, raw["effective_from"], raw["effective_to"]):
        reasons.append("MEMBERSHIP_NOT_EFFECTIVE")
    known = _clock(raw.get("known_at"))
    selection_cutoff = utc(data["decision_cutoffs"][day]) if pit else cutoff
    if known is None:
        reasons.append("MEMBERSHIP_CLOCK_UNAVAILABLE")
    elif known > selection_cutoff:
        reasons.append("MEMBERSHIP_NOT_KNOWN_AT_DECISION" if pit else "MEMBERSHIP_NOT_KNOWN_AT_MEASUREMENT")
    identity = (data.get("identity_by_date") or {}).get(day, data.get("identity") or {}) if pit else data.get("identity") or {}
    for sid in members:
        entry = identity.get(sid) or {}
        if "valid_from" not in entry or "valid_to" not in entry:
            reasons.append("IDENTITY_INTERVAL_UNAVAILABLE")
        elif query_day is not None and not _effective(query_day, entry["valid_from"], entry["valid_to"]):
            reasons.append("IDENTITY_NOT_EFFECTIVE")
        identity_known = _clock(entry.get("known_at"))
        if not _ref(entry.get("owner_ref")) or identity_known is None:
            reasons.append("IDENTITY_RECEIPT_UNAVAILABLE")
        elif identity_known > selection_cutoff:
            reasons.append("IDENTITY_NOT_KNOWN_AT_DECISION" if pit else "IDENTITY_NOT_KNOWN_AT_MEASUREMENT")
    return members, sorted(set(reasons)), raw.get("snapshot_ref")


def _price_gate(price: dict, cutoff, outcome_at):
    evidence = price.get("evidence") or {}
    reasons = []
    if (evidence.get("basis") != AdjustmentBasis.TRADJ.value
            or _basis_for_selected(evidence.get("source"), evidence.get("column")) != AdjustmentBasis.TRADJ.value):
        reasons.append("PRICE_BASIS_UNQUALIFIED")
    if (evidence.get("receipt_state") != "EXACT_ENCODED_OBJECT"
            or not _sha(evidence.get("content_sha256"))
            or not _ref(evidence.get("source_path"))
            or _number(evidence.get("content_bytes")) is None):
        reasons.append("PRICE_RECEIPT_UNAVAILABLE")
    vintage = _clock(evidence.get("adjustment_asof"))
    if vintage is None:
        reasons.append("ADJUSTMENT_VINTAGE_UNAVAILABLE")
    elif vintage > cutoff or vintage < outcome_at:
        reasons.append("ADJUSTMENT_VINTAGE_OUTSIDE_MEASUREMENT")
    observed = _clock(evidence.get("observed_at"))
    if observed is None:
        reasons.append("PRICE_OBSERVATION_CLOCK_UNAVAILABLE")
    elif observed > cutoff:
        reasons.append("PRICE_NOT_KNOWN_AT_MEASUREMENT")
    elif observed < outcome_at:
        reasons.append("PRICE_OBSERVATION_PRECEDES_OUTCOME")
    if evidence.get("session") != Session.REGULAR.value:
        reasons.append("SESSION_UNAVAILABLE_OR_MISMATCHED")
    if evidence.get("venue_scope") != VenueScope.CONSOLIDATED.value:
        reasons.append("VENUE_UNAVAILABLE_OR_MISMATCHED")
    if price.get("currency") != "USD":
        reasons.append("CURRENCY_MISMATCH")
    if not _ref(price.get("corporate_action_ref")):
        reasons.append("CORPORATE_ACTION_BASIS_UNAVAILABLE")
    return reasons, vintage.isoformat() if vintage else None


def _concentration(weights: dict[str, float]) -> dict:
    hhi = math.fsum(weight * weight for weight in weights.values())
    return {"hhi": hhi, "effective_n": 1 / hhi, "largest_weight": max(weights.values()),
            "top5_weight": math.fsum(sorted(weights.values(), reverse=True)[:5]),
            "basis": "end_of_interval_security_weights", "security_count": len(weights)}


def _compound(values: list) -> float | None:
    if not values or any(value is None for value in values):
        return None
    return math.prod(1 + value for value in values) - 1


def _analytics(points: list[dict], *, anchor: float | None) -> dict:
    values = [point["return"] for point in points]
    out = {f"return_{n}": _compound(values[-n:]) if len(values) >= n else None for n in (1, 5, 10, 20, 60)}
    out["window_return"] = _compound(values)
    levels = [anchor] + [point["index_level"] for point in points]
    out["max_drawdown"] = None
    if all(level is not None for level in levels):
        peak, drawdown = anchor, 0.0
        for level in levels:
            peak = max(peak, level)
            drawdown = min(drawdown, level / peak - 1)
        out["max_drawdown"] = drawdown
    tail = values[-20:]
    qualified = len(tail) == 20 and all(value is not None for value in tail)
    out["realized_volatility_20"] = stdev(tail) * math.sqrt(252) if qualified else None
    out["downside_volatility_20"] = math.sqrt(math.fsum(min(value, 0) ** 2 for value in tail) / 20 * 252) if qualified else None
    out["annualization_sessions"] = 252
    out["volatility_definition"] = "sample_sd; downside=root_mean_square_negative_returns"
    return out


def build_factor_read(request: Mapping[str, Any], *, owner_inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Compose explicitly supplied owner projections without reading or writing stores.

    Invalid requests/shapes raise ValueError. Unavailable evidence or valuations
    yield explicit nulls/reasons, never a fallback source, renormalized basket or
    stitched NAV. Local returns can resume only at an admitted rebalance after a
    broken valuation chain; the full-window index never silently reconnects.
    """
    request = _mapping(request, "request")
    data = _normalise(owner_inputs)
    days, clocks, rebalances, cutoff = _validate_request(request, data)
    rights = data.get("rights") or {}
    global_reasons = []
    if (rights.get("status") != "QUALIFIED" or rights.get("purpose") != request["purpose"]
            or not _ref(rights.get("owner_ref"))):
        global_reasons.append("RIGHTS_UNAVAILABLE")
    if data["evidence_kind"] == "RETAINED_OWNER_INPUT" and not all(calendar_verified("US", date.fromisoformat(day).year) for day in days):
        global_reasons.append("CALENDAR_NOT_OWNER_VERIFIED")
    price_map = data.get("prices") or {}
    points, cohort_history = [], []
    weights, members, cohort_reasons, cohort_ref = None, [], [], None
    index_level = 100.0
    index_by_date = {days[0]: index_level}
    segment = 0
    all_reasons = set(global_reasons)
    for previous, day in zip(days, days[1:]):
        if previous in rebalances:
            members, cohort_reasons, cohort_ref = _cohort(request, data, previous, cutoff)
            cohort_history.append({"effective_close": previous, "members": members, "snapshot_ref": cohort_ref})
            if weights is None and points:
                segment += 1
            weights = {sid: 1 / len(members) for sid in members} if members and not cohort_reasons else None
        reasons = list(global_reasons) + list(cohort_reasons)
        per_member, vintages = {}, set()
        for sid in members:
            price = price_map.get(sid) or {}
            failures, vintage = _price_gate(price, cutoff, clocks[day])
            if vintage is not None:
                vintages.add(vintage)
            values = price.get("values") or {}
            start, end = _number(values.get(previous)), _number(values.get(day))
            if start is None or end is None:
                failures.append("MISSING_OR_INVALID_HELD_PRICE")
            value = None if failures else end / start - 1
            if value is not None and not math.isfinite(value):
                failures.append("NONFINITE_CONSTITUENT_RETURN")
                value = None
            per_member[sid] = value
            reasons.extend(failures)
        if len(vintages) > 1:
            reasons.append("MIXED_ADJUSTMENT_VINTAGES")
            per_member = {sid: None for sid in members}
        evaluated = bool(members) and not cohort_reasons and not global_reasons
        valid = [sid for sid in members if per_member[sid] is not None] if evaluated else []
        count_coverage = len(valid) / len(members) if evaluated else None
        weight_coverage = math.fsum(weights[sid] for sid in valid) if evaluated and weights is not None else None
        breadth_ready = (evaluated and len(members) >= 3 and count_coverage >= 0.8
                         and weight_coverage is not None and weight_coverage >= 0.8)
        breadth = {"advance_fraction": (sum(per_member[sid] > 0 for sid in valid) / len(valid)) if breadth_ready else None,
                   "eligible_count": len(members) if evaluated else None,
                   "valid_count": len(valid) if evaluated else None,
                   "status": "READY" if breadth_ready and len(valid) == len(members) else "PARTIAL" if breadth_ready else "UNAVAILABLE"}
        contributions = {sid: (weights[sid] * per_member[sid]
                              if weights is not None and per_member[sid] is not None and evaluated else None)
                         for sid in members}
        measured = evaluated and weights is not None and len(valid) == len(members) and not reasons
        value, concentration = None, None
        if measured:
            value = math.fsum(contributions.values())
            gross = 1 + value
            if gross <= 0 or not math.isfinite(gross):
                raise ValueError("portfolio gross return must remain finite and positive")
            weights = {sid: weights[sid] * (1 + per_member[sid]) / gross for sid in members}
            if not math.isclose(math.fsum(weights.values()), 1.0, rel_tol=0, abs_tol=1e-12):
                raise ValueError("weight conservation failed")
            concentration = _concentration(weights)
            index_level = index_level * gross if index_level is not None else None
        else:
            if weights is None and not cohort_reasons:
                reasons.append("VALUATION_CHAIN_UNAVAILABLE")
            weights, index_level = None, None
        index_by_date[day] = index_level
        all_reasons.update(reasons)
        points.append({"date": day, "interval_start": clocks[previous].isoformat(),
                       "interval_end": clocks[day].isoformat(), "return": value,
                       "index_level": index_level, "segment_id": segment, "cohort_ref": cohort_ref,
                       "coverage": {"eligible_count": len(members) if evaluated else None,
                                    "valid_count": len(valid) if evaluated else None,
                                    "count": count_coverage, "weight": weight_coverage,
                                    "weight_basis": "declared_start_weights"},
                       "breadth": breadth, "concentration": concentration,
                       "contributions": contributions, "reasons": sorted(set(reasons))})
    points = [point for point in points if point["date"] > request["start"]]
    anchor = index_by_date[request["start"]]
    valid_points = sum(point["return"] is not None for point in points)
    result = {
        "schema": SCHEMA, "release_state": "CANDIDATE_NOT_ADMITTED",
        "input_admission": "REFERENCE_CHECKS_ONLY_NOT_RECEIPT_AUTHENTICATION",
        "evidence_kind": data["evidence_kind"], "basket_id": request["basket_id"],
        "history_mode": request["history_mode"], "as_of": days[-1], "request": request,
        "anchor": {"date": request["start"], "index_level": anchor},
        "method": {"weighting": "equal", "rebalance": "monthly", "between_rebalances": "drift",
                   "return_basis": AdjustmentBasis.TRADJ.value, "currency": "USD",
                   "session": Session.REGULAR.value, "venue_scope": VenueScope.CONSOLIDATED.value,
                   "dividends": "constituent_total_return_reinvestment", "costs": "gross_zero_cost",
                   "base_index": 100.0, "minimum_held_weight_coverage": 1.0,
                   "series_inception": data["construction"]["inception"], "window_semantics": "DISPLAY_WINDOW_NOT_RECONSTRUCTION"},
        "status": "READY" if valid_points == len(points) and anchor is not None and all(p["index_level"] is not None for p in points) else "PARTIAL" if valid_points else "UNAVAILABLE",
        "reasons": sorted(all_reasons), "points": points, "analytics": _analytics(points, anchor=anchor),
        "units": {"returns": "fraction", "volatility": "annualized_fraction", "coverage": "fraction"},
        "cohort_digest": _digest(cohort_history),
        "input_digest": _digest({"request": request, "owner_inputs": data}),
        "input_revision": data["input_revision"], "correction_of": data.get("correction_of"),
        "source_refs": {"code": data["code_ref"], "construction": data["construction"]["owner_ref"], "calendar": data["calendar"]["ref"],
                        "rights": rights.get("owner_ref"), "cohorts": cohort_history,
                        "identity": data["identity"], "identity_by_date": data["identity_by_date"],
                        "prices": {sid: price_map.get(sid, {}).get("evidence")
                                   for sid in sorted({sid for row in cohort_history for sid in row["members"]})}},
        "authority": {"may_rank": False, "may_gate": False, "may_size": False,
                      "may_trade": False, "may_publish": False, "may_escalate": False},
    }
    result["result_digest"] = _digest(result)
    return result
