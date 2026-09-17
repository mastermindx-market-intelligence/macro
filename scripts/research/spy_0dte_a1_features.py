#!/usr/bin/env python3
"""Pure pre-entry A1 features for the SPY 0DTE credit-spread prereg.

Research only. This module has no network, outcome, gamma, sizing, signal, order,
or trade authority. Inputs must already be point-in-time source observations.
The option payload is the dedicated ThetaData implied-volatility response, not an
omnibus Greeks response; gamma-bearing rows fail closed.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Any, Mapping

DECISION_CLOCKS = ("09:35:00.000", "09:45:00.000", "10:00:00.000")
HORIZONS_MINUTES = (5, 15, 30)
OPEN_CLOCK = "09:30:00.000"
UNDERLYING_TOLERANCE = 1e-9
# Frozen before economic-label unblind from the 928-session 2026-09-16 source audit.
# Exact-ATM quote-side abs(iv_error) p99 was <= 0.000849 at every decision clock;
# 0.001 is the preregistered solver-quality fence, not a performance-tuned threshold.
IV_ERROR_MAX = 0.001
EVENT_TYPES = ("CPI", "PPI", "NFP", "FOMC")


class FeatureError(ValueError):
    pass


def _finite_positive(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) and out > 0 else None


def _response(payload: Any) -> list[Any]:
    if isinstance(payload, Mapping) and set(payload) == {"response"}:
        payload = payload["response"]
    if not isinstance(payload, list):
        raise FeatureError("Theta IV payload must be a list or exact response wrapper")
    return payload


def _reject_forbidden_source_fields(row: Mapping[str, Any]) -> None:
    if any("gamma" in str(key).lower() or "gex" in str(key).lower() for key in row):
        raise FeatureError("A1 source row contains forbidden gamma/GEX fields")


def _clock_at(session_date: str, minutes_after_open: int) -> str:
    start = datetime.fromisoformat(session_date + "T09:30:00")
    return (start + timedelta(minutes=minutes_after_open)).strftime("%H:%M:%S.000")


def collapse_underlying_prices(payload: Any, session_date: str) -> dict[str, float]:
    """Collapse repeated option-contract underlying prices to one causal minute series."""
    by_clock: dict[str, list[float]] = {}
    for group in _response(payload):
        if not isinstance(group, Mapping) or set(group) != {"contract", "data"}:
            raise FeatureError("IV contract group fields are not exact")
        contract, data = group["contract"], group["data"]
        if not isinstance(contract, Mapping) or not isinstance(data, list):
            raise FeatureError("IV contract group is malformed")
        if str(contract.get("symbol", "")).upper() != "SPY" or str(contract.get("expiration")) != session_date:
            raise FeatureError("IV payload contains a different root/expiration")
        for row in data:
            if not isinstance(row, Mapping):
                raise FeatureError("IV row is malformed")
            _reject_forbidden_source_fields(row)
            timestamp = str(row.get("timestamp", ""))
            underlying_timestamp = str(row.get("underlying_timestamp", ""))
            if "T" not in timestamp or "T" not in underlying_timestamp:
                raise FeatureError("IV timestamps are malformed")
            try:
                observed = datetime.fromisoformat(timestamp)
                underlying_observed = datetime.fromisoformat(underlying_timestamp)
            except ValueError as exc:
                raise FeatureError("IV timestamps are malformed") from exc
            if timestamp[:10] != session_date or underlying_timestamp[:10] != session_date:
                raise FeatureError("IV timestamps cross the session")
            if underlying_observed > observed:
                raise FeatureError("underlying price is future relative to the IV row")
            price = _finite_positive(row.get("underlying_price"))
            if price is None:
                # Source-present invalid price is an unknown observation, not a
                # day-wide failure. Never impute it; downstream minute-dependent
                # features remain null when no valid peer row exists for the minute.
                continue
            by_clock.setdefault(timestamp.split("T", 1)[1], []).append(price)
    collapsed: dict[str, float] = {}
    for clock, values in by_clock.items():
        if max(values) - min(values) > UNDERLYING_TOLERANCE:
            raise FeatureError("contracts disagree on underlying price at one minute")
        collapsed[clock] = values[0]
    return collapsed


def price_features(prices: Mapping[str, float], decision_clock: str) -> dict[str, float | None]:
    """Frozen causal opening-price features for one decision clock."""
    if decision_clock not in DECISION_CLOCKS:
        raise FeatureError("decision clock is not frozen")
    decision_minutes = {"09:35:00.000": 5, "09:45:00.000": 15, "10:00:00.000": 30}[decision_clock]
    p0 = _finite_positive(prices.get(OPEN_CLOCK))
    if p0 is None:
        raise FeatureError("09:30 underlying price is unavailable")
    out: dict[str, float | None] = {}
    for horizon in HORIZONS_MINUTES:
        key = f"first_{horizon}m_return"
        if horizon > decision_minutes:
            out[key] = None
            continue
        ph = _finite_positive(prices.get(_clock_at("2000-01-01", horizon)))
        out[key] = None if ph is None else ph / p0 - 1.0
    minute_prices: list[float] = []
    for minute in range(decision_minutes + 1):
        price = _finite_positive(prices.get(_clock_at("2000-01-01", minute)))
        if price is None:
            out["realized_vol_open_to_decision"] = None
            break
        minute_prices.append(price)
    else:
        log_returns = [math.log(b / a) for a, b in zip(minute_prices, minute_prices[1:])]
        out["realized_vol_open_to_decision"] = math.sqrt(sum(r * r for r in log_returns))
    out["decision_minutes_from_open"] = float(decision_minutes)
    return out


def _valid_iv(value: Any, error: Any, bid: Any, ask: Any) -> float | None:
    iv = _finite_positive(value)
    bid_px = _finite_positive(bid)
    ask_px = _finite_positive(ask)
    try:
        iv_error = float(error)
    except (TypeError, ValueError):
        return None
    if (
        iv is None
        or bid_px is None
        or ask_px is None
        or ask_px < bid_px
        or not math.isfinite(iv_error)
        or abs(iv_error) > IV_ERROR_MAX + 1e-12
    ):
        return None
    return iv


def _atm_iv_at_clock(
    payload: Any, session_date: str, clock: str, underlying_price: float
) -> float | None:
    all_strikes: set[float] = set()
    valid_by_strike: dict[float, dict[str, float]] = {}
    for group in _response(payload):
        contract, data = group.get("contract"), group.get("data")
        if not isinstance(contract, Mapping) or not isinstance(data, list):
            raise FeatureError("IV contract group is malformed")
        if str(contract.get("symbol", "")).upper() != "SPY" or str(contract.get("expiration")) != session_date:
            continue
        right = str(contract.get("right", "")).upper()[:1]
        if right not in {"C", "P"}:
            continue
        try:
            strike = round(float(contract.get("strike")), 3)
        except (TypeError, ValueError):
            continue
        all_strikes.add(strike)
        for row in data:
            if not isinstance(row, Mapping):
                continue
            _reject_forbidden_source_fields(row)
            if str(row.get("timestamp", "")) != session_date + "T" + clock:
                continue
            iv = _valid_iv(
                row.get("implied_vol"),
                row.get("iv_error"),
                row.get("bid"),
                row.get("ask"),
            )
            if iv is None:
                continue
            prior = valid_by_strike.setdefault(strike, {}).get(right)
            if prior is not None and abs(prior - iv) > 1e-12:
                raise FeatureError("conflicting IV rows for one contract/clock")
            valid_by_strike[strike][right] = iv
    if not all_strikes:
        return None
    chosen = min(all_strikes, key=lambda strike: (abs(strike - underlying_price), strike))
    sides = valid_by_strike.get(chosen, {})
    if set(sides) != {"C", "P"}:
        return None
    return (sides["C"] + sides["P"]) / 2.0


def atm_iv_features(
    payload: Any, session_date: str, *, decision_clock: str, prices: Mapping[str, float]
) -> dict[str, float | None]:
    """Frozen PIT same-day ATM IV level and change from first valid post-open IV.

    At each minute the chosen strike is nearest to contemporaneous spot; ties prefer
    the lower strike. Both valid call and put IVs are required and averaged. The change
    anchor is the first valid minute strictly after 09:30 through the decision clock.
    """
    if decision_clock not in DECISION_CLOCKS:
        raise FeatureError("decision clock is not frozen")
    decision_minutes = {"09:35:00.000": 5, "09:45:00.000": 15, "10:00:00.000": 30}[decision_clock]
    observations: list[tuple[int, float]] = []
    for minute in range(1, decision_minutes + 1):
        clock = _clock_at("2000-01-01", minute)
        spot = _finite_positive(prices.get(clock))
        if spot is None:
            continue
        iv = _atm_iv_at_clock(payload, session_date, clock, spot)
        if iv is not None:
            observations.append((minute, iv))
    level = next((iv for minute, iv in observations if minute == decision_minutes), None)
    if not observations or level is None:
        return {
            "atm_iv_level": level,
            "atm_iv_change_from_first_valid": None,
            "atm_iv_anchor_minutes_from_open": None,
        }
    anchor_minute, anchor_iv = observations[0]
    return {
        "atm_iv_level": level,
        "atm_iv_change_from_first_valid": level - anchor_iv,
        "atm_iv_anchor_minutes_from_open": float(anchor_minute),
    }


def gap_features(prior_close: Any, opening_price: Any) -> dict[str, float | int | None]:
    """Overnight gap from exact previous-session raw close to the 09:30 PIT midpoint."""
    if prior_close is None:
        return {"gap_return": None, "gap_direction": None}
    close = _finite_positive(prior_close)
    opening = _finite_positive(opening_price)
    if close is None:
        raise FeatureError("prior close is not finite/positive")
    if opening is None:
        raise FeatureError("09:30 opening price is not finite/positive")
    gap = opening / close - 1.0
    return {
        "gap_return": gap,
        "gap_direction": 1 if gap > 0 else -1 if gap < 0 else 0,
    }


def event_features(session_date: str, fixture: Mapping[str, Any]) -> dict[str, int]:
    events = fixture.get("events")
    if not isinstance(events, Mapping):
        raise FeatureError("event fixture lacks events")
    year = session_date[:4]
    year_map = events.get(year, {})
    if not isinstance(year_map, Mapping):
        year_map = {}
    out = {
        f"event_{event.lower()}": int(session_date in set(year_map.get(event, []) or []))
        for event in EVENT_TYPES
    }
    out["event_high_impact_any"] = int(any(out.values()))
    return out


def build_a1_features(
    *,
    session_date: str,
    decision_clock: str,
    iv_payload: Any,
    event_fixture: Mapping[str, Any],
    prior_close: Any = None,
) -> dict[str, Any]:
    prices = collapse_underlying_prices(iv_payload, session_date)
    opening_price = prices.get(OPEN_CLOCK)
    result: dict[str, Any] = {
        "session_date": session_date,
        "decision_clock": decision_clock,
        **price_features(prices, decision_clock),
        **atm_iv_features(
            iv_payload,
            session_date,
            decision_clock=decision_clock,
            prices=prices,
        ),
        **gap_features(prior_close, opening_price),
        **event_features(session_date, event_fixture),
    }
    forbidden = ("gamma", "gex", "pnl", "profit", "stop", "take_profit", "outcome", "label")
    if any(any(token in key.lower() for token in forbidden) for key in result):
        raise FeatureError("A1 object contains a forbidden outcome/gamma field")
    return result
