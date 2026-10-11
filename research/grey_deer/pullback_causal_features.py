"""Research-only causal pullback feature construction, no market feed or authority.

Consumes an already-qualified, same-price-basis settled observation from the
EXISTING pullback observer. Accepts only caller-supplied daily closes and its
owning market calendar. Reuses engine.vol_forecast.realized_vol for the trailing
volatility calculation; this creates no second volatility engine, episode
state, predictor, publisher, capital policy or retrieval path.

This is an inert research read model: it neither establishes data rights nor
authorizes any numerical forward-depth forecast. Historical replay labels
remain separate under pullback_forward_minimum_labels.py.
"""
from __future__ import annotations

from datetime import date, timedelta
from math import isfinite, sqrt
from numbers import Real
from typing import Callable, Iterable, Mapping


SCHEMA = "pullback_causal_features.research.v1"
_PRICE_BASIS = "split_adjusted_dividend_unadjusted_close"
_ACTIVE = frozenset(("underway", "stabilizing", "recovering"))
_ROLLING_RETURNS = 20


def _unavailable(reason: str, market: str, asof: str) -> dict:
    return {
        "schema": SCHEMA,
        "available": False,
        "quality": reason,
        "asof": asof,
        "market": market,
        "features": None,
        "publication_authorized": False,
    }


def _price(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    try:
        x = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return x if isfinite(x) and x > 0 else None


def _required_sessions(day: date, is_session: Callable[[date], bool]) -> list[date]:
    """Owner-calendar session labels ending with day (includes current close)."""
    days = []
    d = day
    for _ in range(_ROLLING_RETURNS * 4 + 35):
        if is_session(d):
            days.append(d)
            if len(days) == _ROLLING_RETURNS + 1:
                return list(reversed(days))
        d -= timedelta(days=1)
    raise ValueError("owning calendar cannot provide a complete feature window")


def extract_causal_features(
    rows: Iterable[tuple[str, float]],
    *,
    asof: str,
    observation: Mapping,
    is_session: Callable[[date], bool],
    market: str,
    price_basis: str,
) -> dict:
    """Return 5/10-session velocity and trailing realized volatility at *asof*.

    The target is future MINIMUM additional loss, but features use nothing
    beyond the supplied settled origin. Future rows are excluded before close
    validation, just as the original observer does. A no-data condition
    abstains; it never converts missing/invalid to zero-volatility or calm.
    """
    if not isinstance(asof, str) or len(asof) != 10:
        return _unavailable("invalid_asof", market, str(asof))
    try:
        day = date.fromisoformat(asof)
    except ValueError:
        return _unavailable("invalid_asof", market, asof)
    if day.isoformat() != asof or not is_session(day):
        return _unavailable("invalid_asof", market, asof)
    if not isinstance(observation, Mapping):
        return _unavailable("observation_unavailable", market, asof)
    if (
        observation.get("schema") != "pullback_observation.v1"
        or observation.get("market") != market
        or observation.get("price_basis") != price_basis
        or price_basis != _PRICE_BASIS
        or observation.get("available") is not True
        or observation.get("quality") != "current"
        or observation.get("clock") != "settled_close"
        or observation.get("asof") != asof
        or observation.get("expected_session") != asof
        or observation.get("phase") not in _ACTIVE
        or observation.get("active") is not True
        or not isinstance(observation.get("source_digest"), str)
        or len(observation["source_digest"]) != 64
    ):
        return _unavailable("observation_unavailable", market, asof)
    age = observation.get("observed_closes_since_onset")
    if isinstance(age, bool) or not isinstance(age, int) or age < 1:
        return _unavailable("episode_age_unavailable", market, asof)
    p = _price(observation.get("close"))
    high = _price(observation.get("peak_close"))
    low = _price(observation.get("low_close"))
    if p is None or high is None or low is None or not (0 < low <= p <= high):
        return _unavailable("observation_price_invalid", market, asof)

    observed: dict[date, float] = {}
    try:
        for stamp, value in rows:
            if not isinstance(stamp, str) or len(stamp) != 10:
                return _unavailable("invalid_session_label", market, asof)
            date_value = date.fromisoformat(stamp)
            if date_value > day:
                continue   # prevent future-origin feature leakage
            if date_value.isoformat() != stamp or not is_session(date_value):
                return _unavailable("invalid_session_label", market, asof)
            close = _price(value)
            if close is None:
                return _unavailable("invalid_price", market, asof)
            if date_value in observed and observed[date_value] != close:
                return _unavailable("conflicting_duplicate", market, asof)
            observed[date_value] = close
    except (TypeError, ValueError, OverflowError):
        return _unavailable("invalid_session_label", market, asof)

    if day not in observed:
        return _unavailable("missing_origin", market, asof)
    if abs(observed[day] / p - 1) > 1e-9:
        return _unavailable("observation_price_mismatch", market, asof)
    if len(observed) < _ROLLING_RETURNS + 1:
        return _unavailable("insufficient_history", market, asof)
    expected_days = _required_sessions(day, is_session)
    if any(d not in observed for d in expected_days):
        return _unavailable("missing_session", market, asof)

    # Reuse existing research/engine trailing-volatility contract; not a copy
    # of another model or a forward volatility label.
    import pandas as pd
    from engine.vol_forecast import realized_vol

    data = [observed[d] for d in expected_days]
    series = pd.Series(data, index=pd.to_datetime(expected_days), dtype=float)
    vol_daily = realized_vol(series, _ROLLING_RETURNS).iloc[-1]
    vol_ann = float(vol_daily) * sqrt(252.0)
    if not isfinite(vol_ann) or vol_ann < 0:
        return _unavailable("volatility_unavailable", market, asof)
    return {
        "schema": SCHEMA,
        "available": True,
        "quality": "current",
        "publication_authorized": False,
        "asof": asof,
        "market": market,
        "benchmark": observation.get("benchmark"),
        "price_basis": price_basis,
        "source_digest": observation["source_digest"],
        "features": {
            "depth_fraction": 1.0 - p / high,
            "worst_depth_fraction": 1.0 - low / high,
            "rebound_fraction": p / low - 1.0,
            "decline_5_fraction": 1.0 - p / data[-6],
            "decline_10_fraction": 1.0 - p / data[-11],
            "realized_vol_20_ann": vol_ann,
            "observed_closes_since_onset": age,
        },
    }
