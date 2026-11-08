"""Synthetic intraday label conformance under the existing Entry Radar replay.

This is NOT W5 daily outcome attachment, a registered trial, source admission,
or an executable trade simulator. It reuses the native input and minute owners.
Observed-market input is refused until a separate real enrollment contract exists.
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta
from typing import Any, Mapping

from engine.entry_radar.contracts import AUTHORITY_BLOCK
from engine.entry_radar.replay import rs_pullback_launch_data as inputs

LABEL_SCHEMA = "mastermind.rs_pullback_launch.synthetic_labels.v1"
SCALE_KIND = "true_range_wilder_atr14_30m"
HORIZON_MINUTES = 120


_CLOCK_FIELDS = {"decision_at", "evaluation_at", "known_at", "origin_at", "asof_end",
                 "event_anchor_at", "valid_until", "start", "end", "open", "close"}


def _require_lossless_owner_clocks(value: Any, key: str = "") -> None:
    """Native Phase1 is microsecond-based; this candidate refuses lost precision.

    This is an input-format guard, not a new timestamp parser or source selector.
    A malformed/out-of-domain clock anywhere in the synthetic bundle rejects it,
    including unsupported future revisions. Valid future payloads stay invisible.
    """
    if isinstance(value, Mapping):
        for child_key, child in value.items():
            _require_lossless_owner_clocks(child, str(child_key))
    elif isinstance(value, (list, tuple)):
        for child in value:
            _require_lossless_owner_clocks(child, key)
    elif key in _CLOCK_FIELDS and isinstance(value, str):
        try:
            inputs._clock(value)
        except inputs.InputContractError:
            # Malformed/non-clock payloads remain with the original input owner.
            return
        # fromisoformat accepts space/lowercase/basic/comma spellings and
        # fractional UTC offsets too; checking only a literal T misses them.
        for fraction in re.finditer(r"[.,]([0-9]+)", value):
            if any(d != "0" for d in fraction.group(1)[6:]):
                raise inputs.InputContractError("submicrosecond clock unsupported by native Phase1")


def _base(frame: Mapping[str, Any], cutoff: datetime) -> dict[str, Any]:
    return {
        "candidate_id": frame["candidate_id"], "decision_at": frame["decision_at"],
        "evaluation_at": inputs._iso(cutoff),
        "input_snapshot_sha256": frame["snapshot_sha256"],
        "path_state": "INPUT_UNAVAILABLE", "primary_eligible": False,
        "label_scope": "NOT_EVALUABLE", "entry_start": None, "entry_price": None,
        "entry_kind": "NEXT_MINUTE_REPORTED_OPEN_NOT_EXECUTABLE_FILL",
        "label_end": None, "expected_minutes": 0, "observed_minutes": 0,
        "launch": None, "low_in": None, "mae_atr": None, "mfe_atr": None,
        "first_event_interval_start": None, "first_event_interval_end": None,
        "first_event_known_at": None, "first_event_order_basis": None,
        "scale_snapshot_sha256": None, "path_snapshot_sha256": None,
        "refusals": list(frame["refusals"]), "authority": dict(AUTHORITY_BLOCK),
    }


def _scale_value(scale: Any, meta: Mapping[str, Any], opening: datetime,
                 issue: datetime) -> float | None:
    """Check the frozen unit's consistency, not its source authenticity."""
    if not isinstance(scale, Mapping):
        return None
    v = scale.get("value")
    if (isinstance(v, bool) or not isinstance(v, (int, float))
            or not math.isfinite(v) or v <= 0
            or scale.get("kind") != SCALE_KIND
            or scale.get("basis_id") != meta.get("basis", {}).get("basis_id")
            or not inputs._has_receipt(scale)):
        return None
    try:
        origin = inputs._clock(scale["origin_at"])
        known = inputs._clock(scale["known_at"])
        end = inputs._clock(scale["asof_end"])
    except (KeyError, inputs.InputContractError):
        return None
    if not opening <= origin <= issue or not end < origin or not end <= known <= origin:
        return None
    return float(v)


def _event(bar: Mapping[str, Any], upper: float, lower: float) -> tuple[str | None, str | None]:
    """Reported open precedes the other reported prices; H/L order is unknown."""
    v = bar["ohlcv"]
    if v["open"] >= upper:
        return "UPPER_FIRST", "REPORTED_OPEN"
    if v["open"] <= lower:
        return "LOWER_FIRST", "REPORTED_OPEN"
    u, d = v["high"] >= upper, v["low"] <= lower
    if u and d:
        return "ORDER_AMBIGUOUS", "BOTH_BARRIERS_WITH_OPEN_INSIDE"
    if u:
        return "UPPER_FIRST", "SINGLE_BARRIER_IN_MINUTE"
    if d:
        return "LOWER_FIRST", "SINGLE_BARRIER_IN_MINUTE"
    return None, None


def _attach(result: dict[str, Any], bars: list[dict[str, Any]], a0: float) -> None:
    """Attach path interpretation; a complete first-event prefix is necessary."""
    readable = [bar for bar in bars if bar["availability"] == "available"]
    result["observed_minutes"] = len(readable)
    result["path_snapshot_sha256"] = inputs.digest(bars)
    result["refusals"] = sorted({reason for bar in bars for reason in bar["refusals"]})
    if not bars or bars[0]["availability"] != "available":
        result["path_state"] = "ENTRY_UNAVAILABLE"
        return
    entry = float(bars[0]["ohlcv"]["open"])
    upper, lower = entry + a0, entry - .5 * a0
    if not math.isfinite(upper) or lower <= 0:
        result["path_state"] = "SCALE_UNAVAILABLE"
        result["refusals"].append("NONPOSITIVE_OR_NONFINITE_PRICE_BARRIER")
        return
    result["entry_price"] = entry
    state = None
    prefix_known = None
    prefix_broken = False
    for bar in bars:
        if bar["availability"] != "available":
            prefix_broken = True
            continue
        if state is not None or prefix_broken:
            continue
        known = inputs._clock(bar["known_at"])
        prefix_known = max(prefix_known, known) if prefix_known is not None else known
        state, order = _event(bar, upper, lower)
        if state is not None:
            result.update(first_event_interval_start=bar["start"],
                          first_event_interval_end=bar["end"],
                          first_event_known_at=inputs._iso(prefix_known),
                          first_event_order_basis=order)
    complete = len(readable) == len(bars)
    result["path_state"] = state or ("NEITHER_BY_HORIZON" if complete else "PATH_UNKNOWN")
    # MFE/MAE/low-in always use the full requested path, not the stopping prefix.
    violation = any(bar["ohlcv"]["low"] < entry - .25 * a0 for bar in readable)
    if result["primary_eligible"]:
        if result["path_state"] == "UPPER_FIRST":
            result["launch"] = True
        elif result["path_state"] in {"LOWER_FIRST", "NEITHER_BY_HORIZON"}:
            result["launch"] = False
        result["low_in"] = False if violation else (True if complete else None)
    if complete:
        result["mae_atr"] = max(0., (entry - min(bar["ohlcv"]["low"] for bar in bars)) / a0)
        result["mfe_atr"] = max(0., (max(bar["ohlcv"]["high"] for bar in bars) - entry) / a0)


def build_label_panel(bundle: Mapping[str, Any], scales: Mapping[str, Any],
                      evaluation_at: str) -> dict[str, Any]:
    """Retain every candidate and label only synthetic, owner-valid inputs.

    `scales` is keyed by the existing candidate IDs; each value freezes a positive
    true-range30m ATR14 unit before the declared episode origin. It is not an ATR
    estimator or an enrollment/identity receipt. The calendar and input context
    are bound at original issue time; future observations at evaluation_at.

    A returned trade-price label is neither a PnL nor an execution probability.
    No price lookup, source publication, side effect or statistical grade exists.
    """
    if bundle.get("input_kind") != "SYNTHETIC_CONFORMANCE":
        raise inputs.InputContractError("observed-market outcome read is not enrolled")
    if not isinstance(scales, Mapping):
        raise inputs.InputContractError("scales must be keyed by candidate identity")
    _require_lossless_owner_clocks(bundle)
    _require_lossless_owner_clocks(scales)
    _require_lossless_owner_clocks(evaluation_at, "evaluation_at")
    cutoff = inputs._clock(evaluation_at)
    panel = inputs.build_input_panel(bundle)
    candidates = {c["candidate_id"]: c for c in bundle["candidates"]}
    if set(scales) - set(candidates):
        raise inputs.InputContractError("scale references an undeclared candidate")
    results = []
    for frame in panel["frames"]:
        result = _base(frame, cutoff)
        results.append(result)
        issue = inputs._clock(frame["decision_at"])
        if cutoff < issue:
            result["path_state"] = "EVALUATION_BEFORE_DECISION"
            continue
        if frame["availability"] != "available":
            continue
        if frame["eligible"] is not True:
            result["path_state"] = "NOT_ELIGIBLE"
            continue
        candidate = candidates[frame["candidate_id"]]
        calendar = bundle["calendar"]
        if calendar.get("schema") == inputs.CALENDAR_INPUT_SCHEMA:
            calendar = inputs._calendar_at(calendar, issue)
        law = calendar["sessions"][candidate["session"]]
        opening, closing = inputs._clock(law["open"]), inputs._clock(law["close"])
        stream = candidate["streams"]["stock"]
        meta = bundle["streams"][stream]
        scale = scales.get(frame["candidate_id"])
        a0 = _scale_value(scale, meta, opening, issue)
        if a0 is None:
            result["path_state"] = "SCALE_UNAVAILABLE"
            result["refusals"].append("FROZEN_TRUE_RANGE_UNIT_NOT_BOUND")
            continue
        result["scale_snapshot_sha256"] = inputs.digest(scale)
        # A clock exactly at a minute boundary still needs the NEXT boundary.
        start = issue.replace(second=0, microsecond=0) + timedelta(minutes=1)
        primary_end = start + timedelta(minutes=HORIZON_MINUTES)
        result["entry_start"] = inputs._iso(start)
        if start >= closing:
            result["path_state"] = "NO_SESSION_ENTRY"
            continue
        end = min(primary_end, closing)
        n = int((end - start).total_seconds() // 60)
        primary = primary_end <= closing
        result.update(label_end=inputs._iso(end), expected_minutes=n,
                      primary_eligible=primary,
                      label_scope="PRIMARY_120M" if primary else "SESSION_REMAINDER_ONLY")
        bars = [inputs._aggregate(bundle.get("minutes", []), stream, meta,
                                  start + timedelta(minutes=i),
                                  start + timedelta(minutes=i + 1), cutoff)
                for i in range(n)]
        _attach(result, bars, a0)
    for result in results:
        result["snapshot_sha256"] = inputs.digest(result)
    return {"schema": LABEL_SCHEMA, "status": "SYNTHETIC_LABEL_CONFORMANCE_ONLY",
            "population_count": panel["population_count"], "retained_count": len(results),
            "input_bundle_sha256": panel["input_bundle_sha256"], "frames": results,
            "market_experiment_enrolled": False, "authority": dict(AUTHORITY_BLOCK)}
