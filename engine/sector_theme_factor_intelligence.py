"""Read-only sector/theme factor projection over already-owned observation inputs.

This module is NOT a collector, identity/rights authority, membership writer, entry
engine, score publisher, alert source or predictor. In particular, caller-provided
clocks are validated for coherence but NOT authenticated as original observation
receipts. An owner adapter must qualify them before customer use.

Returns are fractions. Breadth uses the incumbent logical identification bounds,
not confidence intervals; missing observations are never treated as negative.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
import math
from typing import Any

from engine.leadership_rotation_context import (
    Breadth, Unmeasured, breadth, breadth_change, is_measured, relative_wealth,
)

SCHEMA = "sector_theme_factor_frame/v1"
HORIZONS = frozenset((
    "1m", "5m", "15m", "60m", "rth", "1d", "5d", "20d",
    "63d", "126d", "252d", "756d", "1260d",
))
MEMBERSHIP_MODES = frozenset(("CURRENT_ROSTER", "PIT_AS_KNOWN"))
MA_BASES = frozenset(("daily_sessions", "1m_bars", "5m_bars", "15m_bars",
                      "60m_bars", "rth_bars"))
EVIDENCE_MODES = frozenset((
    "original_retained", "reconstructed_price_history", "corrected",
    "synthetic_fixture", "prospective_estimate",
))


def _timestamp(value: object) -> datetime | None:
    """Only timezone-aware timestamps are comparable; naive clocks are unknown."""
    try:
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError, TypeError):
        return None


def _required_clock(value: object, label: str) -> datetime:
    result = _timestamp(value)
    if result is None:
        raise ValueError(f"{label} requires an aware timestamp")
    return result


def _members(ids: Sequence[str], label: str) -> tuple[str, ...]:
    if isinstance(ids, (str, bytes)) or not isinstance(ids, Sequence):
        raise ValueError(f"{label} must be a sequence of canonical IDs")
    result = tuple(ids)
    if any(not isinstance(item, str) or not item or item != item.strip()
           for item in result):
        raise ValueError(f"{label} contains an invalid canonical ID")
    if len(set(result)) != len(result):
        raise ValueError(f"{label} contains duplicate canonical IDs")
    return tuple(sorted(result))


def _number(value: object) -> float | None:
    if not is_measured(value):
        return None
    try:
        val = float(value)
        return val if math.isfinite(val) else None
    except (OverflowError, TypeError, ValueError):
        return None


def _ret(value: object) -> float | None:
    val = _number(value)
    return val if val is not None and val >= -1.0 else None


def _measurement(value: object, reason: str = "missing_input") -> dict:
    if isinstance(value, Unmeasured):
        return value.to_dict()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        val = _number(value)
        if val is not None:
            return {"status": "measured", "value": val, "unit": "fraction"}
    return {"status": "unmeasured", "reason": reason}


def _clock_gate(
    row: object, *, period_end: datetime, decision_at: datetime, horizon: str,
) -> str | None:
    if not isinstance(row, Mapping):
        return "missing_observation"
    if row.get("horizon") != horizon:
        return "horizon_mismatch"
    row_end = _timestamp(row.get("period_end"))
    observed = _timestamp(row.get("observed_at"))
    available = _timestamp(row.get("available_at"))
    if row_end is None or observed is None or available is None:
        return "missing_or_naive_clock"
    if row_end != period_end:
        return "period_end_mismatch"
    if observed < period_end:
        # A derived observation may be calculated after its input period,
        # but cannot claim to have observed that future period in advance.
        return "observation_predates_period_end"
    if available < observed:
        return "availability_predates_observation"
    if observed > decision_at or available > decision_at:
        return "future_known"
    return None


def _positive_above(row: Mapping[str, Any], ma_key: str) -> bool | None:
    close, line = _number(row.get("close")), _number(row.get(ma_key))
    if close is None or line is None or close <= 0 or line <= 0:
        return None
    return close > line


def _trend(row: Mapping[str, Any]) -> str | None:
    keys = ("close", "ma20", "ma50", "ma200", "previous_ma50")
    vals = [_number(row.get(key)) for key in keys]
    if any(v is None or v <= 0 for v in vals):
        return None
    close, ma20, ma50, ma200, prev_ma50 = vals
    if close > ma20 > ma50 > ma200 and ma50 > prev_ma50:
        return "up"
    if close < ma20 < ma50 < ma200 and ma50 < prev_ma50:
        return "down"
    return "mixed"


def _read_member(
    raw: object, *, period_end: datetime, decision_at: datetime,
    horizon: str, benchmark_return: object, parent_return: object,
    ma_basis: str,
) -> dict:
    reason = _clock_gate(raw, period_end=period_end,
                         decision_at=decision_at, horizon=horizon)
    if reason is not None:
        return {
            "eligible_for_projection": False, "unmeasured_reason": reason,
            "return_frac": _measurement(None, reason),
            "rs_market": _measurement(None, reason),
            "rs_parent": _measurement(None, reason),
            "above_ma50": None, "above_ma200": None, "trend": None,
            "ma_basis": None, "technical_basis_reason": reason,
        }
    row = raw  # clock_gate proved this is a Mapping
    basis_usable = row.get("ma_basis") == ma_basis
    member_return = _ret(row.get("return_frac"))
    if member_return is None:
        ret_field = _measurement(None, "missing_or_invalid_return")
    else:
        ret_field = _measurement(member_return)
    return {
        "eligible_for_projection": True,
        "unmeasured_reason": None,
        "return_frac": ret_field,
        "rs_market": _measurement(relative_wealth(member_return, benchmark_return)),
        "rs_parent": _measurement(relative_wealth(member_return, parent_return)),
        "above_ma50": _positive_above(row, "ma50") if basis_usable else None,
        "above_ma200": _positive_above(row, "ma200") if basis_usable else None,
        "trend": _trend(row) if basis_usable else None,
        "ma_basis": ma_basis if basis_usable else None,
        "technical_basis_reason": None if basis_usable else "missing_or_mismatched_ma_basis",
    }


def _bool_breadth(members: tuple[str, ...], states: Mapping[str, dict],
                  key: str, target: object = True) -> dict:
    observed = [states[sym][key] for sym in members
                if states[sym].get(key) is not None]
    positives = sum(value == target for value in observed)
    return breadth(positives, len(observed), len(members)).to_dict()


def _rs_breadth(members: tuple[str, ...], states: Mapping[str, dict],
                key: str) -> dict:
    observed = [states[sym][key]["value"] for sym in members
                if states[sym][key].get("status") == "measured"]
    return breadth(sum(v > 0.0 for v in observed),
                   len(observed), len(members)).to_dict()


def _weighted_return(
    members: tuple[str, ...], states: Mapping[str, dict],
    lagged_weights: Mapping[str, float] | None,
) -> dict:
    if lagged_weights is None:
        return _measurement(None, "weights_unavailable")
    if not isinstance(lagged_weights, Mapping) or set(lagged_weights) != set(members):
        return _measurement(None, "weights_incomplete_or_extra")
    weights = {sym: _number(lagged_weights[sym]) for sym in members}
    if any(v is None or v < 0.0 for v in weights.values()):
        return _measurement(None, "weights_invalid")
    try:
        denom = math.fsum(weights.values())
    except OverflowError:
        return _measurement(None, "weights_invalid")
    if denom <= 0.0 or not math.isfinite(denom):
        return _measurement(None, "weights_invalid")
    if any(states[sym]["return_frac"]["status"] != "measured" for sym in members):
        return _measurement(None, "returns_incomplete")
    try:
        value = math.fsum((weights[sym] / denom) *
                          states[sym]["return_frac"]["value"] for sym in members)
    except OverflowError:
        return _measurement(None, "non_finite_result")
    return _measurement(value, "non_finite_result")


def _serialize_change(changes: Mapping[str, Any]) -> dict:
    return {key: (value.to_dict() if isinstance(value, Breadth) else value)
            for key, value in changes.items()}


def project_factor_frame(
    *, group_id: str, cohort_id: str, member_ids: Sequence[str],
    measurements: Mapping[str, Mapping[str, object]], horizon: str,
    period_end: datetime | str, decision_at: datetime | str,
    membership_revision: str, membership_known_at: datetime | str,
    benchmark_return: object, parent_return: object = None,
    membership_mode: str = "PIT_AS_KNOWN",
    evidence_mode: str = "reconstructed_price_history",
    ma_basis: str = "daily_sessions",
    lagged_weights: Mapping[str, float] | None = None,
    previous_member_ids: Sequence[str] | None = None,
    previous_measurements: Mapping[str, Mapping[str, object]] | None = None,
    previous_period_end: datetime | str | None = None,
    previous_decision_at: datetime | str | None = None,
    previous_membership_known_at: datetime | str | None = None,
) -> dict:
    """Project one same-horizon, same-clock group frame with explicit unknowns.

    Does not read a source or authenticate membership, rights, data basis, weight
    vintage, historical availability, benchmark return or customer entitlements.
    A consumer must obtain those guarantees from incumbent owners (P2).
    """
    for label, val in (("group_id", group_id), ("cohort_id", cohort_id),
                       ("membership_revision", membership_revision)):
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"{label} must be nonempty")
    if horizon not in HORIZONS:
        raise ValueError("unknown horizon")
    if membership_mode not in MEMBERSHIP_MODES:
        raise ValueError("unknown membership mode")
    if evidence_mode not in EVIDENCE_MODES:
        raise ValueError("unknown evidence mode")
    if ma_basis not in MA_BASES:
        raise ValueError("unknown moving-average basis")
    members = _members(member_ids, "member_ids")
    if not isinstance(measurements, Mapping):
        raise ValueError("measurements must be a mapping")
    end = _required_clock(period_end, "period_end")
    decision = _required_clock(decision_at, "decision_at")
    known = _required_clock(membership_known_at, "membership_known_at")
    if end > decision or known > decision:
        raise ValueError("future market endpoint or membership knowledge")
    if membership_mode == "PIT_AS_KNOWN" and known > end:
        raise ValueError("PIT membership knowledge postdates measured endpoint")
    benchmark = _ret(benchmark_return)
    parent = _ret(parent_return)
    states = {
        sym: _read_member(measurements.get(sym), period_end=end,
                          decision_at=decision, horizon=horizon,
                          benchmark_return=benchmark, parent_return=parent,
                          ma_basis=ma_basis)
        for sym in members
    }
    valid_returns = [states[sym]["return_frac"]["value"] for sym in members
                     if states[sym]["return_frac"]["status"] == "measured"]
    try:
        sample_mean = math.fsum(valid_returns) / len(valid_returns) if valid_returns else None
    except OverflowError:
        sample_mean = None
    sample_ew = _measurement(sample_mean,
                             "non_finite_group_aggregate" if valid_returns else "no_measured_members")
    full_ew = (sample_ew if len(valid_returns) == len(members) and members
               else _measurement(None, "incomplete_full_cohort"))
    # A group return based on partial sample cannot masquerade as its full-group RS.
    group_return = full_ew.get("value") if full_ew["status"] == "measured" else None
    missing_reasons = Counter(
        states[sym]["unmeasured_reason"] for sym in members
        if not states[sym]["eligible_for_projection"]
    )
    missing_reasons.update(
        {"missing_or_invalid_return": sum(
            1 for sym in members
            if states[sym]["eligible_for_projection"]
            and states[sym]["return_frac"]["status"] != "measured"
        )}
    )
    missing_reasons = {k: v for k, v in sorted(missing_reasons.items()) if v}
    result = {
        "schema": SCHEMA,
        "group": {
            "group_id": group_id, "cohort_id": cohort_id,
            "membership_revision": membership_revision,
            "membership_mode": membership_mode,
            "overlap_policy": "membership_is_not_a_disjoint_partition",
        },
        "clock": {
            "period_end": end.isoformat(), "decision_at": decision.isoformat(),
            "membership_known_at": known.isoformat(), "horizon": horizon,
            "moving_average_basis": ma_basis,
        },
        "evidence": {
            "mode": evidence_mode,
            "source_use_qualification": "not_performed_by_pure_projection",
            "source_rights_verified": False,
            "original_known_at_receipts_verified": False,
        },
        "universe": {
            "expected_n": len(members),
            "measured_return_n": len(valid_returns),
            "missing_by_reason": missing_reasons,
            "member_ids": list(members),
        },
        "constituents": states,
        "measures": {
            "equal_weight_observed_sample_return": sample_ew,
            "equal_weight_full_cohort_return": full_ew,
            "lagged_weight_full_cohort_return":
                _weighted_return(members, states, lagged_weights),
            "group_rs_market": _measurement(relative_wealth(group_return, benchmark)),
            "group_rs_parent": _measurement(relative_wealth(group_return, parent)),
            "positive_return_breadth": _bool_breadth(
                members, {sym: {**states[sym],
                                "positive": states[sym]["return_frac"]["value"] > 0.0
                                if states[sym]["return_frac"]["status"] == "measured"
                                else None} for sym in members}, "positive",
            ),
            "positive_rs_market_breadth": _rs_breadth(members, states, "rs_market"),
            "positive_rs_parent_breadth": _rs_breadth(members, states, "rs_parent"),
            "above_ma50_breadth": _bool_breadth(members, states, "above_ma50"),
            "above_ma200_breadth": _bool_breadth(members, states, "above_ma200"),
            "uptrend_breadth": _bool_breadth(members, states, "trend", "up"),
            "downtrend_breadth": _bool_breadth(members, states, "trend", "down"),
        },
        "transitions": {
            "status": "unmeasured",
            "reason": "no_qualified_previous_endpoint",
        },
        "authority": {
            "display_only": True, "predictive_promoted": False,
            "eligible_for_customer_publication": False,
            "entry_or_sizing_authority": False,
            "alert_authority": False,
            "ranking_authority": False,
        },
    }
    prior_args = (previous_member_ids, previous_measurements,
                  previous_period_end, previous_decision_at,
                  previous_membership_known_at)
    if all(arg is not None for arg in prior_args):
        prev_members = _members(previous_member_ids, "previous_member_ids")
        prev_end = _required_clock(previous_period_end, "previous_period_end")
        prev_decision = _required_clock(previous_decision_at, "previous_decision_at")
        prev_known = _required_clock(previous_membership_known_at,
                                     "previous_membership_known_at")
        if (not isinstance(previous_measurements, Mapping) or
                prev_end > prev_decision or prev_known > prev_decision or
                prev_decision > decision or prev_end >= end or
                (membership_mode == "PIT_AS_KNOWN" and prev_known > prev_end)):
            raise ValueError("invalid previous endpoint or membership/clock ordering")
        prev_states = {
            sym: _read_member(previous_measurements.get(sym),
                              period_end=prev_end, decision_at=prev_decision,
                              horizon=horizon, benchmark_return=None,
                              parent_return=None, ma_basis=ma_basis)
            for sym in prev_members
        }
        before = {sym: (prev_states[sym]["trend"] == "up"
                         if prev_states[sym]["trend"] is not None else None)
                  for sym in prev_members}
        after = {sym: (states[sym]["trend"] == "up"
                        if states[sym]["trend"] is not None else None)
                 for sym in members}
        result["transitions"] = {
            "status": "measured_with_endpoint_coverage",
            "metric": "uptrend",
            "previous_period_end": prev_end.isoformat(),
            "previous_decision_at": prev_decision.isoformat(),
            "previous_membership_known_at": prev_known.isoformat(),
            "change": _serialize_change(breadth_change(before, after)),
        }
    return result
