"""Pure research helpers for point-in-time event microstructure studies.

Production-inert by contract. This module consumes caller-supplied, owner-produced
observations and returns deterministic measurements. It creates no source store,
event registry, alert, rank, gate, size, execution, or trade intent.
"""
from __future__ import annotations

import math
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping, Sequence

SCHEMA = "research.event_microstructure_study.v1"
AUTHORITY = {
    "tier": "research",
    "context_only": True,
    "may_rank": False,
    "may_gate": False,
    "may_size": False,
    "may_escalate": False,
    "may_alert": False,
    "may_execute": False,
    "may_trade": False,
    "may_write_market_memory": False,
}
MODES = frozenset({"operational_pit", "public_reconstruction"})
SOURCE_CLASSES = frozenset({"official", "wire", "social", "other"})
AUTHORITATIVE_SOURCE_CLASSES = frozenset({"official", "wire"})
DEFAULT_HORIZONS_MINUTES = (5, 15, 30, 60)


class StudyContractError(ValueError):
    """Raised when inputs make the study temporally ambiguous."""


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise StudyContractError(f"{field} must be a non-empty ISO-8601 string")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise StudyContractError(f"{field} is not valid ISO-8601") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise StudyContractError(f"{field} must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _positive(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise StudyContractError(f"{field} must be a positive finite number")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise StudyContractError(f"{field} must be a positive finite number") from exc
    if not math.isfinite(out) or out <= 0:
        raise StudyContractError(f"{field} must be a positive finite number")
    return out


def knowledge_time(event: Mapping[str, Any], *, mode: str) -> datetime:
    """Return the earliest decision-eligible clock for an event."""
    if mode not in MODES:
        raise StudyContractError(f"unsupported mode: {mode}")
    event_time = _utc(event.get("event_time"), "event.event_time")
    available_at = _utc(event.get("available_at"), "event.available_at")
    observed_at = _utc(event.get("observed_at"), "event.observed_at")
    if event_time > available_at:
        raise StudyContractError("event_time cannot be after available_at")
    if available_at > observed_at:
        raise StudyContractError("available_at cannot be after observed_at")
    return available_at if mode == "public_reconstruction" else observed_at


def _points(rows: Sequence[Mapping[str, Any]]) -> list[tuple[datetime, float]]:
    by_ts: dict[datetime, float] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise StudyContractError(f"points[{idx}] must be an object")
        ts = _utc(row.get("ts"), f"points[{idx}].ts")
        price = _positive(row.get("price"), f"points[{idx}].price")
        prior = by_ts.get(ts)
        if prior is not None and not math.isclose(prior, price, abs_tol=1e-12, rel_tol=0):
            raise StudyContractError(f"conflicting prices at {_iso(ts)}")
        by_ts[ts] = price
    return sorted(by_ts.items())


def _return_bps(start: float, end: float) -> float:
    return (end / start - 1.0) * 10_000.0


def first_threshold_cross(
    rows: Sequence[Mapping[str, Any]],
    *,
    anchor: str | datetime,
    direction: int,
    threshold_bps: float,
    horizon_minutes: int,
    max_baseline_age_minutes: int = 5,
) -> dict[str, Any]:
    """Measure the first signed threshold cross after anchor."""
    if direction not in (-1, 1):
        raise StudyContractError("direction must be -1 or 1")
    threshold = _positive(threshold_bps, "threshold_bps")
    if horizon_minutes <= 0 or max_baseline_age_minutes <= 0:
        raise StudyContractError("horizon and baseline age must be positive")
    anchor_dt = _utc(anchor, "anchor") if isinstance(anchor, str) else anchor.astimezone(timezone.utc)
    points = _points(rows)
    baselines = [row for row in points if row[0] <= anchor_dt]
    if not baselines:
        return {"status": "data_gap", "crossed_at": None, "signed_move_bps": None}
    base_ts, base_price = baselines[-1]
    if anchor_dt - base_ts > timedelta(minutes=max_baseline_age_minutes):
        return {"status": "data_gap", "crossed_at": None, "signed_move_bps": None}
    end = anchor_dt + timedelta(minutes=horizon_minutes)
    for ts, price in points:
        if ts < anchor_dt:
            continue
        if ts > end:
            break
        raw = _return_bps(base_price, price)
        signed = raw * direction
        if signed >= threshold:
            return {
                "status": "crossed",
                "baseline": {"ts": _iso(base_ts), "price": base_price},
                "crossed_at": _iso(ts),
                "raw_move_bps": round(raw, 6),
                "signed_move_bps": round(signed, 6),
            }
    return {
        "status": "not_crossed",
        "baseline": {"ts": _iso(base_ts), "price": base_price},
        "crossed_at": None,
        "signed_move_bps": None,
    }


def forward_return_bps(
    rows: Sequence[Mapping[str, Any]],
    *,
    anchor: str | datetime,
    horizon_minutes: int,
    start_tolerance_minutes: int = 1,
    end_tolerance_minutes: int = 2,
) -> float | None:
    """Return a post-anchor forward return, or None when bars are missing."""
    if horizon_minutes <= 0:
        raise StudyContractError("horizon_minutes must be positive")
    anchor_dt = _utc(anchor, "anchor") if isinstance(anchor, str) else anchor.astimezone(timezone.utc)
    points = _points(rows)
    starts = [
        row for row in points
        if anchor_dt <= row[0] <= anchor_dt + timedelta(minutes=start_tolerance_minutes)
    ]
    if not starts:
        return None
    start_ts, start_price = starts[0]
    target = anchor_dt + timedelta(minutes=horizon_minutes)
    ends = [
        row for row in points
        if target - timedelta(minutes=end_tolerance_minutes) <= row[0] <= target
    ]
    if not ends or ends[-1][0] <= start_ts:
        return None
    return round(_return_bps(start_price, ends[-1][1]), 6)


def _last_at_or_before(
    points: Sequence[tuple[datetime, float]],
    target: datetime,
    *,
    tolerance_minutes: int,
) -> tuple[datetime, float] | None:
    if tolerance_minutes < 0:
        raise StudyContractError("tolerance_minutes cannot be negative")
    eligible = [row for row in points if row[0] <= target]
    if not eligible:
        return None
    row = eligible[-1]
    if target - row[0] > timedelta(minutes=tolerance_minutes):
        return None
    return row


def _first_at_or_after(
    points: Sequence[tuple[datetime, float]],
    target: datetime,
    *,
    tolerance_minutes: int,
) -> tuple[datetime, float] | None:
    if tolerance_minutes < 0:
        raise StudyContractError("tolerance_minutes cannot be negative")
    for row in points:
        if row[0] >= target:
            if row[0] - target <= timedelta(minutes=tolerance_minutes):
                return row
            return None
    return None


def repricing_first_pass(
    *,
    known_at: str | datetime,
    causal_points: Sequence[Mapping[str, Any]],
    response_points: Sequence[Mapping[str, Any]],
    benchmark_points: Sequence[Mapping[str, Any]],
    causal_direction: int,
    pre_windows_minutes: Sequence[int] = (60, 240),
    impulse_minutes: int = 5,
    response_horizons_minutes: Sequence[int] = (15, 30, 60),
    pre_tolerance_minutes: int = 5,
    post_tolerance_minutes: int = 2,
) -> dict[str, Any]:
    """Measure the frozen V2 descriptive first-pass windows.

    The function is intentionally source- and calendar-agnostic: callers supply
    already-admitted PIT observations. Pre-event features use only observations
    at or before their target clocks. Post-event features use the first
    observation at or after each target clock within a bounded tolerance.

    This is measurement, not threshold selection or signal admission.
    """
    if causal_direction not in (-1, 1):
        raise StudyContractError("causal_direction must be -1 or 1")
    if impulse_minutes <= 0:
        raise StudyContractError("impulse_minutes must be positive")
    if any(int(v) <= 0 for v in pre_windows_minutes):
        raise StudyContractError("pre_windows_minutes entries must be positive")
    if any(int(v) <= 0 for v in response_horizons_minutes):
        raise StudyContractError(
            "response_horizons_minutes entries must be positive"
        )

    anchor = (
        _utc(known_at, "known_at")
        if isinstance(known_at, str)
        else known_at.astimezone(timezone.utc)
    )
    causal = _points(causal_points)
    response = _points(response_points)
    benchmark = _points(benchmark_points)

    event_causal = _last_at_or_before(
        causal,
        anchor,
        tolerance_minutes=pre_tolerance_minutes,
    )
    causal_at_impulse_end = _first_at_or_after(
        causal,
        anchor + timedelta(minutes=impulse_minutes),
        tolerance_minutes=post_tolerance_minutes,
    )
    response_event = _last_at_or_before(
        response,
        anchor,
        tolerance_minutes=pre_tolerance_minutes,
    )
    benchmark_event = _last_at_or_before(
        benchmark,
        anchor,
        tolerance_minutes=pre_tolerance_minutes,
    )
    response_start = _first_at_or_after(
        response,
        anchor + timedelta(minutes=impulse_minutes),
        tolerance_minutes=post_tolerance_minutes,
    )
    benchmark_start = _first_at_or_after(
        benchmark,
        anchor + timedelta(minutes=impulse_minutes),
        tolerance_minutes=post_tolerance_minutes,
    )

    pre: dict[str, dict[str, float | str | None]] = {}
    for window in pre_windows_minutes:
        target = anchor - timedelta(minutes=int(window))
        start = _last_at_or_before(
            causal,
            target,
            tolerance_minutes=pre_tolerance_minutes,
        )
        raw = None
        if start is not None and event_causal is not None:
            raw = round(_return_bps(start[1], event_causal[1]), 6)
        pre[f"{int(window)}m"] = {
            "start_known_at": None if start is None else _iso(start[0]),
            "raw_return_bps": raw,
            "signed_expected_direction_bps": (
                None if raw is None else round(raw * causal_direction, 6)
            ),
        }

    impulse_raw = None
    if event_causal is not None and causal_at_impulse_end is not None:
        impulse_raw = round(
            _return_bps(event_causal[1], causal_at_impulse_end[1]),
            6,
        )

    first_response = first_benchmark = first_residual = None
    if response_event is not None and response_start is not None:
        first_response = round(
            _return_bps(response_event[1], response_start[1]),
            6,
        )
    if benchmark_event is not None and benchmark_start is not None:
        first_benchmark = round(
            _return_bps(benchmark_event[1], benchmark_start[1]),
            6,
        )
    if first_response is not None and first_benchmark is not None:
        first_residual = round(first_response - first_benchmark, 6)

    response_windows: dict[str, dict[str, float | str | None]] = {}
    for horizon in response_horizons_minutes:
        target = anchor + timedelta(
            minutes=impulse_minutes + int(horizon)
        )
        response_end = _first_at_or_after(
            response,
            target,
            tolerance_minutes=post_tolerance_minutes,
        )
        benchmark_end = _first_at_or_after(
            benchmark,
            target,
            tolerance_minutes=post_tolerance_minutes,
        )
        response_ret = benchmark_ret = residual = None
        if response_start is not None and response_end is not None:
            response_ret = round(
                _return_bps(response_start[1], response_end[1]),
                6,
            )
        if benchmark_start is not None and benchmark_end is not None:
            benchmark_ret = round(
                _return_bps(benchmark_start[1], benchmark_end[1]),
                6,
            )
        if response_ret is not None and benchmark_ret is not None:
            residual = round(response_ret - benchmark_ret, 6)
        response_windows[f"{int(horizon)}m"] = {
            "end_known_at": (
                None if response_end is None else _iso(response_end[0])
            ),
            "response_return_bps": response_ret,
            "benchmark_return_bps": benchmark_ret,
            "residual_return_bps": residual,
        }

    required = (
        event_causal,
        causal_at_impulse_end,
        response_event,
        benchmark_event,
        response_start,
        benchmark_start,
    )
    return {
        "schema": "research.narrative_repricing_first_pass.v1",
        "authority": dict(AUTHORITY),
        "known_at": _iso(anchor),
        "status": (
            "measured"
            if all(value is not None for value in required)
            else "data_gap"
        ),
        "causal_event_point": (
            None if event_causal is None else {
                "known_at": _iso(event_causal[0]),
                "price": event_causal[1],
            }
        ),
        "causal_impulse": {
            "end_target": _iso(
                anchor + timedelta(minutes=impulse_minutes)
            ),
            "end_known_at": (
                None
                if causal_at_impulse_end is None
                else _iso(causal_at_impulse_end[0])
            ),
            "raw_return_bps": impulse_raw,
            "signed_expected_direction_bps": (
                None
                if impulse_raw is None
                else round(impulse_raw * causal_direction, 6)
            ),
        },
        "pre_event_causal": pre,
        "first_impulse": {
            "end_target": _iso(
                anchor + timedelta(minutes=impulse_minutes)
            ),
            "response_return_bps": first_response,
            "benchmark_return_bps": first_benchmark,
            "residual_return_bps": first_residual,
        },
        "response_from_impulse_end": response_windows,
        "interpretation": (
            "descriptive_only; thresholds and first-impulse rules remain owned "
            "by the frozen preregistration/evaluation split"
        ),
    }


EVIDENCE_STATES = frozenset(
    {
        "NARRATIVE_DETECTED",
        "SOURCE_QUALITY_UNRESOLVED",
        "SOURCE_QUALITY_RESOLVED",
        "CAUSAL_REJECTED",
        "CAUSAL_CONFIRMED",
        "FIRST_IMPULSE_OBSERVED",
        "CONTINUATION_OBSERVED",
        "NO_CONTINUATION",
        "CROSS_SESSION_ASSIMILATION_OBSERVED",
        "CROSS_SESSION_NO_ASSIMILATION",
        "CONFLICTED",
        "DATA_GAP",
    }
)


def classify_evidence_state(
    *,
    source_quality_resolved: bool,
    causal_confirmed: bool | None = None,
    first_impulse_observed: bool = False,
    continuation_observed: bool | None = None,
    cross_session_assimilated: bool | None = None,
    source_confounded: bool = False,
    data_gap: bool = False,
) -> dict[str, Any]:
    """Return a deterministic read-only evidence state.

    This function deliberately does not infer any of its booleans from prices,
    headlines, thresholds, or model output. Callers must supply states produced by
    their frozen source/measurement contracts. The helper only prevents later
    layers from collapsing distinct evidence conditions into a generic
    "headline worked" label.

    cross_session_assimilated is an optional, separately measured regional
    handoff fact. It does not require same-session continuation because a target
    region may have been closed at the event clock.
    """
    bool_fields = {
        "source_quality_resolved": source_quality_resolved,
        "first_impulse_observed": first_impulse_observed,
        "source_confounded": source_confounded,
        "data_gap": data_gap,
    }
    for field, value in bool_fields.items():
        if not isinstance(value, bool):
            raise StudyContractError(f"{field} must be boolean")
    for field, value in {
        "causal_confirmed": causal_confirmed,
        "continuation_observed": continuation_observed,
        "cross_session_assimilated": cross_session_assimilated,
    }.items():
        if value is not None and not isinstance(value, bool):
            raise StudyContractError(f"{field} must be boolean or None")

    if not source_quality_resolved and any(
        value is not None
        for value in (
            causal_confirmed,
            continuation_observed,
            cross_session_assimilated,
        )
    ):
        raise StudyContractError(
            "downstream evidence cannot be promoted before source quality resolves"
        )
    if first_impulse_observed and causal_confirmed is not True:
        raise StudyContractError(
            "first impulse cannot be promoted without causal confirmation"
        )
    if continuation_observed is not None and not first_impulse_observed:
        raise StudyContractError(
            "continuation state requires an observed first impulse"
        )

    flags = {
        "source_quality_resolved": source_quality_resolved,
        "causal_confirmed": causal_confirmed,
        "first_impulse_observed": first_impulse_observed,
        "continuation_observed": continuation_observed,
        "cross_session_assimilated": cross_session_assimilated,
        "source_confounded": source_confounded,
        "data_gap": data_gap,
    }

    if data_gap:
        state = "DATA_GAP"
    elif source_confounded:
        state = "CONFLICTED"
    elif not source_quality_resolved:
        state = "SOURCE_QUALITY_UNRESOLVED"
    elif causal_confirmed is False:
        state = "CAUSAL_REJECTED"
    elif cross_session_assimilated is False:
        state = "CROSS_SESSION_NO_ASSIMILATION"
    elif cross_session_assimilated is True:
        state = "CROSS_SESSION_ASSIMILATION_OBSERVED"
    elif causal_confirmed is None:
        state = "SOURCE_QUALITY_RESOLVED"
    elif not first_impulse_observed:
        state = "CAUSAL_CONFIRMED"
    elif continuation_observed is False:
        state = "NO_CONTINUATION"
    elif continuation_observed is True:
        state = "CONTINUATION_OBSERVED"
    else:
        state = "FIRST_IMPULSE_OBSERVED"

    return {
        "schema": "research.narrative_evidence_state.v1",
        "authority": dict(AUTHORITY),
        "state": state,
        "flags": flags,
        "interpretation": (
            "evidence_state_only; no score, rank, alert, trade, sizing, "
            "portfolio, or execution authority"
        ),
    }


def publication_ladder(
    claims: Sequence[Mapping[str, Any]],
    *,
    mode: str,
) -> dict[str, Any]:
    """Measure social lead time without upgrading social source authority."""
    rows: list[tuple[datetime, str, str]] = []
    for idx, claim in enumerate(claims):
        source_class = str(claim.get("source_class") or "").strip().lower()
        if source_class not in SOURCE_CLASSES:
            raise StudyContractError(f"claims[{idx}].source_class is unsupported")
        claim_id = str(claim.get("claim_id") or f"claim-{idx}")
        rows.append((knowledge_time(claim, mode=mode), source_class, claim_id))
    rows.sort()
    first_social = next((r for r in rows if r[1] == "social"), None)
    first_authoritative = next(
        (r for r in rows if r[1] in AUTHORITATIVE_SOURCE_CLASSES),
        None,
    )
    lead = None
    if first_social and first_authoritative:
        lead = (first_authoritative[0] - first_social[0]).total_seconds()
    return {
        "mode": mode,
        "first_social": None if not first_social else {
            "known_at": _iso(first_social[0]),
            "claim_id": first_social[2],
        },
        "first_authoritative": None if not first_authoritative else {
            "known_at": _iso(first_authoritative[0]),
            "source_class": first_authoritative[1],
            "claim_id": first_authoritative[2],
        },
        "social_lead_seconds": lead,
        "social_led_authoritative": bool(lead is not None and lead > 0),
    }


def analyze_event(
    *,
    event: Mapping[str, Any],
    causal_points: Sequence[Mapping[str, Any]],
    response_points: Sequence[Mapping[str, Any]],
    mode: str,
    causal_direction: int,
    response_direction: int,
    causal_threshold_bps: float = 25.0,
    response_threshold_bps: float = 25.0,
    causal_confirmation_minutes: int = 10,
    response_window_minutes: int = 30,
    benchmark_points: Sequence[Mapping[str, Any]] | None = None,
    horizons_minutes: Sequence[int] = DEFAULT_HORIZONS_MINUTES,
) -> dict[str, Any]:
    """Measure one narrative event from causal confirmation into response."""
    event_id = str(event.get("event_id") or "").strip()
    if not event_id:
        raise StudyContractError("event_id is required")
    known_at = knowledge_time(event, mode=mode)
    causal = first_threshold_cross(
        causal_points,
        anchor=known_at,
        direction=causal_direction,
        threshold_bps=causal_threshold_bps,
        horizon_minutes=causal_confirmation_minutes,
    )
    response = first_threshold_cross(
        response_points,
        anchor=known_at,
        direction=response_direction,
        threshold_bps=response_threshold_bps,
        horizon_minutes=response_window_minutes,
    )
    causal_dt = _utc(causal["crossed_at"], "causal.crossed_at") if causal.get("crossed_at") else None
    response_dt = _utc(response["crossed_at"], "response.crossed_at") if response.get("crossed_at") else None
    lag_seconds = (
        (response_dt - causal_dt).total_seconds()
        if causal_dt is not None and response_dt is not None
        else None
    )
    confirmed = causal.get("status") == "crossed"
    propagated = bool(
        confirmed
        and response.get("status") == "crossed"
        and lag_seconds is not None
        and 0 <= lag_seconds <= response_window_minutes * 60
    )
    forward: dict[str, dict[str, float | None]] = {}
    for horizon in horizons_minutes:
        if horizon <= 0:
            raise StudyContractError("all forward horizons must be positive")
        response_ret = benchmark_ret = residual = None
        if causal_dt is not None:
            response_ret = forward_return_bps(
                response_points,
                anchor=causal_dt,
                horizon_minutes=int(horizon),
            )
            if benchmark_points is not None:
                benchmark_ret = forward_return_bps(
                    benchmark_points,
                    anchor=causal_dt,
                    horizon_minutes=int(horizon),
                )
                if response_ret is not None and benchmark_ret is not None:
                    residual = round(response_ret - benchmark_ret, 6)
        forward[f"{int(horizon)}m"] = {
            "response_return_bps": response_ret,
            "benchmark_return_bps": benchmark_ret,
            "residual_return_bps": residual,
        }
    return {
        "schema": SCHEMA,
        "authority": dict(AUTHORITY),
        "event_id": event_id,
        "mode": mode,
        "known_at": _iso(known_at),
        "causal": causal,
        "response": response,
        "lag_seconds": lag_seconds,
        "causal_confirmed": confirmed,
        "ordered_propagation": propagated,
        "forward_from_causal_confirmation": forward,
        "interpretation": (
            "measurement_only: ordered propagation is a prerequisite for the "
            "hypothesis, not proof of causality or a trading recommendation"
        ),
    }


def summarize_sample(values: Iterable[float | None]) -> dict[str, Any]:
    clean: list[float] = []
    missing = 0
    for value in values:
        if value is None:
            missing += 1
            continue
        number = float(value)
        if not math.isfinite(number):
            raise StudyContractError("sample contains a non-finite value")
        clean.append(number)
    if not clean:
        return {"n": 0, "missing": missing, "mean": None, "median": None, "positive_rate": None}
    return {
        "n": len(clean),
        "missing": missing,
        "mean": round(statistics.fmean(clean), 6),
        "median": round(statistics.median(clean), 6),
        "positive_rate": round(sum(v > 0 for v in clean) / len(clean), 6),
    }


def compare_to_controls(
    event_values: Iterable[float | None],
    control_values: Iterable[float | None],
) -> dict[str, Any]:
    """Return descriptive event-versus-control deltas without a significance claim."""
    events = summarize_sample(event_values)
    controls = summarize_sample(control_values)
    return {
        "events": events,
        "controls": controls,
        "delta_mean": None if events["mean"] is None or controls["mean"] is None else round(events["mean"] - controls["mean"], 6),
        "delta_median": None if events["median"] is None or controls["median"] is None else round(events["median"] - controls["median"], 6),
        "inference": (
            "descriptive_only; use event-clustered chronological inference "
            "before any promotion"
        ),
    }
