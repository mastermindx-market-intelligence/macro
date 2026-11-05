"""Unrounded numerical records over the existing International performance owner.

This adapter accepts supplied closes only. Observation provenance describes the
owner's calculation inputs, not freshness, access rights or ranking eligibility.
The legacy owner retains all return and currency-conversion formulas.
"""
from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
import math
from numbers import Real

import pandas as pd

from engine import intl_inputs, intl_performance as owner


def _observed(closes: pd.DataFrame, column: str) -> tuple[pd.Series | None, str | None]:
    if column not in closes.columns:
        return None, "missing_observations"
    series = closes[column].dropna()
    if series.empty:
        return None, "missing_observations"
    try:
        valid = all(
            isinstance(value, Real) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0
            for value in series
        )
    except (TypeError, ValueError, OverflowError):
        valid = False
    return (series, None) if valid else (None, "invalid_observation")


def _finite_positive(series: pd.Series | None) -> bool:
    if series is None or series.empty:
        return False
    try:
        return all(math.isfinite(value) and value > 0 for value in series)
    except (TypeError, ValueError, OverflowError):
        return False


def _endpoint_positions(series: pd.Series, observations: int | None) -> tuple[int, int] | None:
    if series.empty:
        return None
    if observations is not None:
        return (len(series) - 1 - observations, len(series) - 1) if len(series) > observations else None
    # This is endpoint selection, not a second return formula. The owner's YTD
    # formula uses the last observation before the final observation's local year.
    previous = [i for i, year in enumerate(series.index.year) if year < series.index[-1].year]
    return (previous[-1], len(series) - 1) if previous else None


def _observation_at(series: pd.Series | None, endpoint: pd.Timestamp) -> str | None:
    if series is None:
        return None
    position = int(series.index.searchsorted(endpoint, side="right")) - 1
    return series.index[position].isoformat() if position >= 0 else None


def _window(series: pd.Series, positions: tuple[int, int], price: pd.Series,
            fx: pd.Series | None, policy: str) -> dict:
    start, end = (series.index[position] for position in positions)
    return {
        "start": start.isoformat(), "end": end.isoformat(),
        "calendar_policy": policy,
        "endpoint_observations": {
            "price_start": _observation_at(price, start),
            "price_end": _observation_at(price, end),
            "fx_start": _observation_at(fx, start),
            "fx_end": _observation_at(fx, end),
        },
    }


def _metric(value: float | None = None, *, reason: str | None = None,
            window: dict | None = None, unit: str = "percent") -> dict:
    return {
        "value": value, "unit": unit,
        "numerical_status": "available" if value is not None else "unavailable",
        "reason": reason, "window": deepcopy(window),
    }


def _return_metric(series: pd.Series, observations: int | None,
                   price: pd.Series, fx: pd.Series | None, policy: str) -> dict:
    positions = _endpoint_positions(series, observations)
    if positions is None:
        return _metric(reason="insufficient_history")
    window = _window(series, positions, price, fx, policy)
    try:
        if observations is None:
            # The owner compares with a naive Jan 1 timestamp. This view retains
            # local wall-clock years and positions; output dates remain original.
            view = series.copy(deep=False)
            if view.index.tz is not None:
                view.index = view.index.tz_localize(None)
            value = owner._ytd_ret(view)
        else:
            value = owner._ret(series, observations)
        if value is None or not math.isfinite(value):
            return _metric(reason="invalid_calculation", window=window)
        return _metric(float(value), window=window)
    except (ArithmeticError, TypeError, ValueError):
        return _metric(reason="invalid_calculation", window=window)


def _envelope(records: list[dict], source_reference: str | None,
              reason: str | None = None) -> dict:
    states = [record[leg]["value"] is not None
              for record in records for leg in ("local", "usd", "fx_contribution")]
    status = "available" if states and all(states) else "partial" if any(states) else "unavailable"
    if reason is None and status != "available":
        reason = "partial_numerical_coverage" if any(states) else "no_numerical_coverage"
    return {
        "source_reference": source_reference,
        "source_reference_reason": None if source_reference is not None else "unknown",
        "numerical_status": status, "reason": reason, "records": records,
    }


def build_return_records(closes: pd.DataFrame, *,
                         market_ids: Sequence[str] | None = None,
                         source_reference: str | None = None) -> dict:
    """Project supplied prices into numerical records without collecting or storing.

    A malformed request raises ValueError. Invalid frame geometry returns an
    unavailable envelope; absent/invalid observations withhold the affected legs.
    Paired legs require the real owner's identical cleaned grids. If that owner
    cannot align them, a separately named observed-local calculation can survive.
    No output is qualified for a current ranking by this function.
    """
    if not isinstance(closes, pd.DataFrame):
        raise ValueError("invalid_request:closes")
    if source_reference is not None and (
        not isinstance(source_reference, str) or not source_reference.strip()
    ):
        raise ValueError("invalid_request:source_reference")
    countries = deepcopy(intl_inputs.countries())
    # The default is the incumbent usd_leaderboard default, used only when its
    # optional configuration is absent. Ordinary calls use the configured order.
    horizons = deepcopy(owner._pcfg().get("horizons_d", {
        "1m": 21, "3m": 63, "6m": 126, "12m": 252,
    }))
    if not isinstance(horizons, dict) or any(
        not isinstance(key, str) or not key or key == "ytd"
        or isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for key, value in horizons.items()
    ):
        raise ValueError("invalid_configuration:horizons_d")
    if market_ids is None:
        selected = list(countries)
    elif isinstance(market_ids, Sequence) and not isinstance(market_ids, (str, bytes)):
        selected = list(market_ids)
    else:
        raise ValueError("invalid_request:market_ids")
    if any(not isinstance(cc, str) or cc not in countries for cc in selected):
        raise ValueError("invalid_request:market_ids")
    if len(set(selected)) != len(selected):
        raise ValueError("invalid_request:duplicate_market_ids")
    if not selected:
        return _envelope([], source_reference, "no_markets")
    index = closes.index
    if (not isinstance(index, pd.DatetimeIndex) or index.hasnans
            or not index.is_unique or not index.is_monotonic_increasing
            or not closes.columns.is_unique):
        return _envelope([], source_reference, "invalid_geometry")

    records = []
    for cc in selected:
        country = countries[cc]
        price, price_error = _observed(closes, country["index"])
        fx, fx_error = _observed(closes, country["fx"])
        local = usd = None
        pair_error = price_error or fx_error
        if price is not None and fx is not None:
            try:
                usd = owner.usd_series(cc, closes=closes)
                local = owner._local_aligned(cc, usd, closes) if usd is not None else None
                if not _finite_positive(usd) or not _finite_positive(local):
                    pair_error = "invalid_calculation"
                else:
                    # The owner may drop a leading local null after constructing
                    # the USD grid. Keep only its actual shared suffix. For every
                    # available n-step window the original endpoints are unchanged;
                    # missing shared history remains insufficient, never filled.
                    if local.index.equals(usd.index[-len(local):]):
                        usd = usd.loc[local.index]
                        pair_error = None
                    else:
                        pair_error = "unaligned_owner_grid"
            except (ArithmeticError, TypeError, ValueError):
                pair_error = "invalid_calculation"

        for horizon, observations in [*horizons.items(), ("ytd", None)]:
            record = {
                "market_id": cc, "index_id": country["index"],
                "index_label": (country.get("indices") or {}).get(country["index"], country["index"]),
                "fx_id": country["fx"],
                "fx_quote_orientation": "local_per_USD" if country.get("fx_invert") else "USD_per_local",
                "horizon": horizon, "requested_observations": observations,
                "return_basis": "price", "qualification": "not_evaluated",
            }
            if pair_error is None:
                record["local"] = _return_metric(local, observations, price, fx, "owner_union_forward_fill")
                record["usd"] = _return_metric(usd, observations, price, fx, "owner_union_forward_fill")
                left, right = record["local"]["value"], record["usd"]["value"]
                if left is not None and right is not None:
                    contribution = right - left
                    record["fx_contribution"] = _metric(
                        contribution if math.isfinite(contribution) else None,
                        reason=None if math.isfinite(contribution) else "invalid_calculation",
                        window=record["usd"]["window"], unit="percentage_points",
                    )
                else:
                    record["fx_contribution"] = _metric(
                        reason=record["local"]["reason"] or record["usd"]["reason"],
                        window=record["usd"]["window"], unit="percentage_points",
                    )
            else:
                record["local"] = (
                    _return_metric(price, observations, price, None, "observed_local_prices")
                    if price is not None else _metric(reason=price_error)
                )
                record["usd"] = _metric(reason=pair_error)
                record["fx_contribution"] = _metric(reason=pair_error, unit="percentage_points")
            records.append(record)
    return _envelope(records, source_reference)
