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
