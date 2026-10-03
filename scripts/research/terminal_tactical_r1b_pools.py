"""Frozen v4 matched-control pools and control measurement for the R1-B study.

Implements the pre-outcome analysis rulings 1-8, 15-17 and 29.  Pools are built
from candidate-time facts only and nothing here selects on outcomes.  A control
is measured from its OWN session (its anchor row and that session's
normalization); the selected event's fields are never copied onto a control.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from typing import Any, Iterable, Mapping, MutableMapping

import pandas as pd

from engine.entry_radar import tactical_exhaustion as te
from engine.session_digest import session_window_et

POOL_SCHEMA = "mastermind.tti.r1b.pool.v4"
ROW_SCHEMA = "mastermind.tti.r1b.event_cell.v4"
_SIGNS = (-1, 0, 1)
_MATCH_FIELDS = ("candidate_at", "confirmation_delay_bars", "displacement_atr")


def _sign_ok(value: object) -> bool:
    return not isinstance(value, bool) and value in _SIGNS


def split_census(rows: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Census rows with a usable QQQ sign, and the count rejected for a null sign."""
    usable: list[dict[str, Any]] = []
    rejected = 0
    for row in rows:
        if _sign_ok(row.get("qqq_open_to_decision_sign")):
            usable.append(dict(row))
        else:
            rejected += 1
    return usable, rejected


def build_pool(event: Mapping[str, Any], *, census: list[dict[str, Any]],
               config_bytes: bytes) -> dict[str, Any]:
    """Matched-control pool for one selected event.  No outcome is read."""
    base = {
        "schema": POOL_SCHEMA,
        "selector": event["selector"], "anchor_id": event["anchor_id"],
        "symbol": event["symbol"], "session": event["session"],
        "candidate_at": event["candidate_at"],
        "confirmation_delay_bars": event["confirmation_delay_bars"],
        "market_outcomes_computed": False, "fallback_used": False,
    }
    sign = event.get("qqq_open_to_decision_sign")
    if not _sign_ok(sign):
        return {**base, "availability": "NO_CONTROL", "reason": "qqq_sign_unavailable",
                "matched_count": 0, "matched_controls": [], "excluded_counts": {}}
    matched = te.match_controls(
        {key: event[key] for key in _MATCH_FIELDS},
        selected_symbol=event["symbol"], selected_session=event["session"],
        selected_qqq_sign=sign, control_census=census, config_bytes=config_bytes)
    return {**base, "availability": matched["availability"], "reason": matched["reason"],
            "matched_count": matched["matched_count"],
            "matched_controls": matched["matched_controls"],
            "excluded_counts": matched["excluded_counts"]}


def build_pools(events: Iterable[Mapping[str, Any]], census: list[dict[str, Any]], *,
                config_bytes: bytes) -> list[dict[str, Any]]:
    """Every selected event's pool, in one deterministic order."""
    ordered = sorted(events, key=lambda e: (e["selector"], e["symbol"], e["session"], e["anchor_id"]))
    return [build_pool(event, census=census, config_bytes=config_bytes) for event in ordered]


def pools_digest(pools: Iterable[Mapping[str, Any]]) -> str:
    payload = json.dumps(list(pools), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def overlap(pools: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per selector: selected anchors that also serve as controls, and pool membership counts."""
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for pool in pools:
        grouped.setdefault(pool["selector"], []).append(pool)
    out: dict[str, dict[str, Any]] = {}
    for selector in sorted(grouped):
        group = grouped[selector]
        selected = {pool["anchor_id"] for pool in group}
        membership = Counter(c["anchor_id"] for pool in group for c in pool["matched_controls"])
        distribution = Counter(membership.values())
        out[selector] = {
            "selected_events": len(group),
            "distinct_controls": len(membership),
            "selected_anchors_also_controls": len(selected & set(membership)),
            "pools_per_control": {str(k): v for k, v in sorted(distribution.items())},
        }
    return out


def day_beta(day: Mapping[str, Any]) -> float | None:
    normalization = day["normalization"]
    return float(normalization["beta"]) if normalization.get("beta_available") else None


def control_event(control: Mapping[str, Any], *, day: Mapping[str, Any],
                  config_bytes: bytes) -> dict[str, Any]:
    """Measurement event for one matched control, from the control's OWN session."""
    cfg = json.loads(config_bytes)
    anchor = day["anchors"][control["anchor_id"]]
    normalization = day["normalization"]
    candidate_at = pd.Timestamp(control["candidate_at"])
    decision_at = candidate_at + pd.Timedelta(minutes=5 * int(control["confirmation_delay_bars"]))
    entry_at = decision_at + pd.Timedelta(minutes=int(cfg["execution_latency_minutes"]))
    if entry_at != pd.Timestamp(control["entry_reference_at"]):
        raise ValueError("control_entry_clock_mismatch")
    return {
        "selector": "BASE_FRESH_LOW", "anchor_id": control["anchor_id"],
        "candidate_at": candidate_at.isoformat(), "decision_at": decision_at.isoformat(),
        "entry_reference_at": entry_at.isoformat(),
        "prior_atr": float(normalization["prior_atr"]),
        "previous_regular_close": float(normalization["prior_close"]),
        "candidate_low": float(anchor["candidate_low"]),
        "episode_low": float(anchor["candidate_low"]),
        "role": "matched_control",
    }


def shift_bars_valid(control: Mapping[str, Any], *, day: Mapping[str, Any]) -> bool:
    """Reading B: each of the control's d shift bars exists once with valid OHLC and positive volume."""
    delay = int(control["confirmation_delay_bars"])
    if delay == 0:
        return True
    start, _close = session_window_et(date.fromisoformat(control["session"]))
    candidate_at = pd.Timestamp(control["candidate_at"]).tz_convert(start.tzinfo)
    state, _values = te._exact_positive_path(
        day["stock_frame"], candidate_at, candidate_at + pd.Timedelta(minutes=5 * delay))
    return state == "ok"


def measure_rows(event: Mapping[str, Any], pool: Mapping[str, Any],
                 days: Mapping[tuple[str, str], Mapping[str, Any]], *,
                 config_bytes: bytes, cache: MutableMapping[tuple, float | None]) -> list[dict[str, Any]]:
    """The 12 event-cell rows (4 horizons x 3 costs) for one selected event and its pool."""
    if (pool["selector"], pool["anchor_id"]) != (event["selector"], event["anchor_id"]):
        raise ValueError("pool_event_identity_mismatch")
    cfg = json.loads(config_bytes)
    session_day = date.fromisoformat(event["session"])
    own = days[(event["symbol"], event["session"])]
    start, _close = session_window_et(session_day)
    width = int(cfg["clock_bin_minutes"])

    def clock_bin(value: object) -> int:
        local = pd.Timestamp(value).tz_convert(start.tzinfo)
        return (local.hour * 60 + local.minute) // width

    beta = event.get("beta")
    beta = float(beta) if isinstance(beta, (int, float)) and not isinstance(beta, bool) else None
    controls = pool["matched_controls"] if pool["availability"] == "AVAILABLE" else []
    prepared = []
    for control in controls:
        cday = days[(control["symbol"], control["session"])]
        prepared.append((control, cday,
                         control_event(control, day=cday, config_bytes=config_bytes),
                         shift_bars_valid(control, day=cday)))
    rows: list[dict[str, Any]] = []
    for horizon in cfg["horizons"]:
        for cost in cfg["round_trip_cost_bps"]:
            selected = te.measure_event_outcome(
                own["stock_frame"], own["benchmark_frame"], event=dict(event),
                session=session_day, horizon=str(horizon), beta=beta,
                cost_bps=int(cost), config_bytes=config_bytes)
            returns_a: list[float] = []
            returns_b: list[float] = []
            for control, cday, cevent, shift_ok in prepared:
                key = (control["anchor_id"], int(control["confirmation_delay_bars"]), str(horizon), int(cost))
                if key not in cache:
                    measured = te.measure_event_outcome(
                        cday["stock_frame"], cday["benchmark_frame"], event=dict(cevent),
                        session=date.fromisoformat(control["session"]), horizon=str(horizon),
                        beta=day_beta(cday), cost_bps=int(cost), config_bytes=config_bytes)
                    cache[key] = measured["net_beta_residual"]
                value = cache[key]
                if value is None:
                    continue
                returns_a.append(value)
                if shift_ok:
                    returns_b.append(value)
            rows.append({
                "schema": ROW_SCHEMA,
                "selector": event["selector"], "anchor_id": event["anchor_id"],
                "horizon": str(horizon), "cost_bps": int(cost),
                "symbol": event["symbol"], "date": event["session"],
                "candidate_bin": clock_bin(event["candidate_at"]),
                "decision_bin": clock_bin(event["decision_at"]),
                "selected_status": selected["status"], "selected_reason": selected["reason"],
                "selected_return": selected["net_beta_residual"],
                "selected_touch": selected["touch"],
                "pool_availability": pool["availability"], "pool_reason": pool["reason"],
                "matched_count": pool["matched_count"],
                "control_returns_a": returns_a, "control_returns_b": returns_b,
            })
    return rows
