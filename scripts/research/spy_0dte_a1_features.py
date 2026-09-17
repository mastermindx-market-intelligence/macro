#!/usr/bin/env python3
"""Pure pre-entry A1 features for the SPY 0DTE credit-spread prereg.

Research only. This module has no network, outcome, gamma, sizing, signal, order,
or trade authority. Inputs must already be point-in-time source observations.
The option payload is the dedicated ThetaData implied-volatility response, not an
omnibus Greeks response; gamma-bearing rows fail closed. Opening price/range/VWAP
state comes from the separate consolidated ThetaData 1-minute stock OHLCV source.
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
BAR_FIELDS = frozenset({"timestamp", "open", "high", "low", "close", "volume", "count", "vwap"})
SESSION_MINUTES = 390
CALENDAR_MINUTES_PER_YEAR = 365.0 * 24.0 * 60.0


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


def collapse_underlying_prices(
    payload: Any, session_date: str, *, through_clock: str | None = None
) -> dict[str, float]:
    """Collapse option-repeated underlying prices through a causal clock only."""
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
            timestamp = str(row.get("timestamp", ""))
            if "T" not in timestamp:
                raise FeatureError("IV timestamp is malformed")
            try:
                observed = datetime.fromisoformat(timestamp)
            except ValueError as exc:
                raise FeatureError("IV timestamp is malformed") from exc
            if timestamp[:10] != session_date:
                raise FeatureError("IV timestamp crosses the session")
            clock = observed.strftime("%H:%M:%S.000")
            if through_clock is not None and clock > through_clock:
                # Future rows are outside the decision information set. Their
                # values/schema extensions cannot poison an earlier decision.
                continue
            _reject_forbidden_source_fields(row)
            underlying_timestamp = str(row.get("underlying_timestamp", ""))
            if "T" not in underlying_timestamp:
                raise FeatureError("IV underlying timestamp is malformed")
            try:
                underlying_observed = datetime.fromisoformat(underlying_timestamp)
            except ValueError as exc:
                raise FeatureError("IV underlying timestamp is malformed") from exc
            if underlying_timestamp[:10] != session_date:
                raise FeatureError("IV underlying timestamp crosses the session")
            if underlying_observed > observed:
                raise FeatureError("underlying price is future relative to the IV row")
            price = _finite_positive(row.get("underlying_price"))
            if price is None:
                # Source-present invalid price is an unknown observation, not a
                # day-wide failure. Never impute it; downstream minute-dependent
                # features remain null when no valid peer row exists for the minute.
                continue
            by_clock.setdefault(clock, []).append(price)
    collapsed: dict[str, float] = {}
    for clock, values in by_clock.items():
        if max(values) - min(values) > UNDERLYING_TOLERANCE:
            raise FeatureError("contracts disagree on underlying price at one minute")
        collapsed[clock] = values[0]
    return collapsed


def _stock_response(payload: Any) -> list[Any]:
    if isinstance(payload, Mapping) and set(payload) == {"response"}:
        payload = payload["response"]
    if not isinstance(payload, list):
        raise FeatureError("Theta stock OHLC payload must be a list or exact response wrapper")
    return payload


def parse_underlying_bars(
    payload: Any, session_date: str, *, before_clock: str | None = None
) -> dict[str, dict[str, float | int]]:
    """Parse causal one-minute UTP/CTA OHLCV+VWAP bars without imputation."""
    out: dict[str, dict[str, float | int]] = {}
    for row in _stock_response(payload):
        if not isinstance(row, Mapping):
            raise FeatureError("stock OHLC row is malformed")
        timestamp = str(row.get("timestamp", ""))
        if "T" not in timestamp or timestamp[:10] != session_date:
            raise FeatureError("stock OHLC timestamp is malformed/cross-session")
        try:
            observed = datetime.fromisoformat(timestamp)
        except ValueError as exc:
            raise FeatureError("stock OHLC timestamp is malformed") from exc
        if observed.second != 0 or observed.microsecond != 0:
            raise FeatureError("stock OHLC bar is not minute-aligned")
        clock = observed.strftime("%H:%M:%S.000")
        if before_clock is not None and clock >= before_clock:
            # Bars opening at/after the exact decision are unknowable then. Do
            # not let future value/schema corruption change an earlier row.
            continue
        if set(row) != BAR_FIELDS:
            raise FeatureError("stock OHLC row fields are not exact")
        values = {key: _finite_positive(row.get(key)) for key in ("open", "high", "low", "close", "vwap")}
        if any(value is None for value in values.values()):
            continue
        integers: dict[str, int] = {}
        for key in ("volume", "count"):
            try:
                raw = float(row[key])
            except (TypeError, ValueError) as exc:
                raise FeatureError("stock OHLC volume/count is malformed") from exc
            if not math.isfinite(raw) or raw < 0 or not raw.is_integer():
                raise FeatureError("stock OHLC volume/count is malformed")
            integers[key] = int(raw)
        volume = integers["volume"]; count = integers["count"]
        low = float(values["low"]); high = float(values["high"])
        if low > min(float(values["open"]), float(values["close"]), high) + 1e-9:
            raise FeatureError("stock OHLC low is inconsistent")
        if high + 1e-9 < max(float(values["open"]), float(values["close"]), low):
            raise FeatureError("stock OHLC high is inconsistent")
        vwap = float(values["vwap"])
        parsed = {**{key: float(value) for key, value in values.items()}, "volume": volume, "count": count}
        previous = out.get(clock)
        if previous is not None and previous != parsed:
            raise FeatureError("conflicting stock OHLC rows for one minute")
        out[clock] = parsed
    # Theta's OHLC `vwap` is session-to-date cumulative VWAP. It may lie outside
    # the current minute's high/low, but never outside the cumulative traded range.
    running_low = math.inf; running_high = -math.inf
    for clock in sorted(out):
        row = out[clock]
        running_low = min(running_low, float(row["low"]))
        running_high = max(running_high, float(row["high"]))
        vwap = float(row["vwap"])
        if vwap < running_low - 1e-9 or vwap > running_high + 1e-9:
            raise FeatureError("stock OHLC cumulative VWAP is outside cumulative range")
    return out


def _normalized_slope(values: list[float]) -> float | None:
    if len(values) < 2 or not all(math.isfinite(v) and v > 0 for v in values):
        return None
    n = len(values); mean_x = (n - 1) / 2.0; mean_y = sum(values) / n
    denom = sum((i - mean_x) ** 2 for i in range(n))
    if denom <= 0 or mean_y <= 0:
        return None
    slope = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values)) / denom
    return slope / mean_y


def opening_bar_features(
    payload: Any, session_date: str, decision_clock: str
) -> dict[str, float | None]:
    """Frozen causal opening-state features from completed 1m consolidated bars."""
    if decision_clock not in DECISION_CLOCKS:
        raise FeatureError("decision clock is not frozen")
    decision_minutes = {"09:35:00.000": 5, "09:45:00.000": 15, "10:00:00.000": 30}[decision_clock]
    bars = parse_underlying_bars(payload, session_date, before_clock=decision_clock)
    open_bar = bars.get(OPEN_CLOCK)
    if open_bar is None:
        raise FeatureError("09:30 stock OHLC bar is unavailable")
    opening = float(open_bar["open"])
    out: dict[str, float | None] = {"opening_price": opening}
    for horizon in HORIZONS_MINUTES:
        key = f"first_{horizon}m_return"
        if horizon > decision_minutes:
            out[key] = None
            continue
        final = bars.get(_clock_at("2000-01-01", horizon - 1))
        out[key] = None if final is None else float(final["close"]) / opening - 1.0

    completed: list[Mapping[str, float | int]] = []
    missing = False
    for minute in range(decision_minutes):
        bar = bars.get(_clock_at("2000-01-01", minute))
        if bar is None:
            missing = True
            break
        completed.append(bar)
    last = bars.get(_clock_at("2000-01-01", decision_minutes - 1))
    decision_price = None if last is None else float(last["close"])
    out["decision_price"] = decision_price
    out["decision_minutes_from_open"] = float(decision_minutes)
    if missing or not completed or decision_price is None:
        out.update({
            "realized_vol_open_to_decision": None,
            "opening_range_high": None, "opening_range_low": None,
            "opening_range_width_frac": None, "opening_range_location": None,
            "session_vwap_to_decision": None, "vwap_distance_frac": None,
            "vwap_slope_5m_frac_per_min": None, "range_expansion_vs_first_5m": None,
            "opening_range_5m_high": None, "opening_range_5m_low": None,
            "opening_range_5m_width_frac": None, "opening_range_5m_location": None,
            "opening_range_15m_high": None, "opening_range_15m_low": None,
            "opening_range_15m_width_frac": None, "opening_range_15m_location": None,
        })
        return out

    closes = [opening] + [float(bar["close"]) for bar in completed]
    log_returns = [math.log(b / a) for a, b in zip(closes, closes[1:])]
    out["realized_vol_open_to_decision"] = math.sqrt(sum(r * r for r in log_returns))
    high = max(float(bar["high"]) for bar in completed); low = min(float(bar["low"]) for bar in completed)
    width = high - low
    out["opening_range_high"] = high; out["opening_range_low"] = low
    out["opening_range_width_frac"] = width / opening
    out["opening_range_location"] = None if width <= 0 else (decision_price - low) / width
    # Theta's row VWAP is already session-to-date cumulative VWAP; never re-weight
    # cumulative values a second time. The last completed bar is the causal value.
    session_vwap = float(completed[-1]["vwap"])
    out["session_vwap_to_decision"] = session_vwap
    out["vwap_distance_frac"] = decision_price / session_vwap - 1.0
    vwap_tail = [float(bar["vwap"]) for bar in completed[-5:]]
    out["vwap_slope_5m_frac_per_min"] = _normalized_slope(vwap_tail)

    for horizon in (5, 15):
        prefix = f"opening_range_{horizon}m"
        if decision_minutes < horizon:
            out.update({
                prefix + "_high": None, prefix + "_low": None,
                prefix + "_width_frac": None, prefix + "_location": None,
            })
            continue
        window = completed[:horizon]
        w_high = max(float(bar["high"]) for bar in window)
        w_low = min(float(bar["low"]) for bar in window)
        w_width = w_high - w_low
        out[prefix + "_high"] = w_high; out[prefix + "_low"] = w_low
        out[prefix + "_width_frac"] = w_width / opening
        out[prefix + "_location"] = None if w_width <= 0 else (decision_price - w_low) / w_width

    first5_width = float(out["opening_range_5m_high"]) - float(out["opening_range_5m_low"])
    out["range_expansion_vs_first_5m"] = None if first5_width <= 0 else width / first5_width
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
            if str(row.get("timestamp", "")) != session_date + "T" + clock:
                continue
            _reject_forbidden_source_fields(row)
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


def gap_features(
    prior_close: Any, opening_price: Any, *,
    prior_realized_vol: Any = None, prior_implied_move: Any = None,
) -> dict[str, float | int | None]:
    """Overnight gap from prior raw close to consolidated 09:30 opening trade.

    Optional normalizers are positive fractional scales known before the session;
    unavailable scales remain null rather than being reconstructed from future data.
    """
    empty = {
        "gap_return": None, "gap_direction": None,
        "gap_vs_prior_realized_vol": None, "gap_vs_prior_implied_move": None,
    }
    if prior_close is None:
        return empty
    close = _finite_positive(prior_close); opening = _finite_positive(opening_price)
    if close is None:
        raise FeatureError("prior close is not finite/positive")
    if opening is None:
        raise FeatureError("09:30 opening price is not finite/positive")
    gap = opening / close - 1.0
    realized = _finite_positive(prior_realized_vol)
    implied = _finite_positive(prior_implied_move)
    if prior_realized_vol is not None and realized is None:
        raise FeatureError("prior realized volatility is not finite/positive")
    if prior_implied_move is not None and implied is None:
        raise FeatureError("prior implied move is not finite/positive")
    return {
        "gap_return": gap,
        "gap_direction": 1 if gap > 0 else -1 if gap < 0 else 0,
        "gap_vs_prior_realized_vol": None if realized is None else gap / realized,
        "gap_vs_prior_implied_move": None if implied is None else gap / implied,
    }


def opening_direction_features(
    gap_direction: Any, opening_range_location: Any
) -> dict[str, float | int | None]:
    try:
        gap = int(gap_direction) if gap_direction is not None else None
        location = float(opening_range_location) if opening_range_location is not None else None
    except (TypeError, ValueError):
        return {"gap_reversal_score": None, "reversal_from_gap_extreme_flag": None, "continuation_in_gap_direction_flag": None}
    if gap not in {-1, 1} or location is None or not math.isfinite(location):
        return {"gap_reversal_score": None, "reversal_from_gap_extreme_flag": None, "continuation_in_gap_direction_flag": None}
    reversal_score = 1.0 - location if gap > 0 else location
    reversal = int((gap > 0 and location < 0.5) or (gap < 0 and location > 0.5))
    continuation = int((gap > 0 and location > 0.5) or (gap < 0 and location < 0.5))
    return {"gap_reversal_score": reversal_score, "reversal_from_gap_extreme_flag": reversal, "continuation_in_gap_direction_flag": continuation}


def expected_move_features(
    decision_price: Any, atm_iv_level: Any, decision_clock: str
) -> dict[str, float | None]:
    if decision_clock not in DECISION_CLOCKS:
        raise FeatureError("decision clock is not frozen")
    elapsed = {"09:35:00.000": 5, "09:45:00.000": 15, "10:00:00.000": 30}[decision_clock]
    remaining = float(SESSION_MINUTES - elapsed)
    price = _finite_positive(decision_price); iv = _finite_positive(atm_iv_level)
    out: dict[str, float | None] = {"expected_move_remaining_minutes": remaining}
    if price is None or iv is None:
        out.update({"expected_move_1sigma_frac": None, "expected_move_1sigma_abs": None, "expected_move_lower": None, "expected_move_upper": None})
        return out
    frac = iv * math.sqrt(remaining / CALENDAR_MINUTES_PER_YEAR); move = price * frac
    out.update({"expected_move_1sigma_frac": frac, "expected_move_1sigma_abs": move, "expected_move_lower": max(0.0, price - move), "expected_move_upper": price + move})
    return out


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
    bar_payload: Any,
    event_fixture: Mapping[str, Any],
    prior_close: Any = None,
    prior_realized_vol: Any = None,
    prior_implied_move: Any = None,
) -> dict[str, Any]:
    iv_prices = collapse_underlying_prices(
        iv_payload, session_date, through_clock=decision_clock
    )
    bar_state = opening_bar_features(bar_payload, session_date, decision_clock)
    opening_price = bar_state.get("opening_price")
    iv_state = atm_iv_features(
        iv_payload, session_date, decision_clock=decision_clock, prices=iv_prices
    )
    gap_state = gap_features(
        prior_close, opening_price,
        prior_realized_vol=prior_realized_vol, prior_implied_move=prior_implied_move,
    )
    result: dict[str, Any] = {
        "session_date": session_date,
        "decision_clock": decision_clock,
        **bar_state,
        **iv_state,
        **gap_state,
        **opening_direction_features(
            gap_state.get("gap_direction"), bar_state.get("opening_range_location")
        ),
        **expected_move_features(
            bar_state.get("decision_price"), iv_state.get("atm_iv_level"), decision_clock
        ),
        **event_features(session_date, event_fixture),
    }
    forbidden = ("gamma", "gex", "pnl", "profit", "stop", "take_profit", "outcome", "label")
    if any(any(token in key.lower() for token in forbidden) for key in result):
        raise FeatureError("A1 object contains a forbidden outcome/gamma field")
    return result
