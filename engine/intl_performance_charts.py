"""Raw selected-period numerical series over accepted International return records.

This projection emits timestamped owner levels inside an already-selected
return window. Observation provenance describes owner calculation context, not
freshness, rights or ranking eligibility. Return math stays in the owner;
request validation and exact endpoints stay in the accepted records adapter.
"""
from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
import math

import pandas as pd

from engine import intl_performance as owner
from engine.intl_performance_records import build_return_records

_DEFAULT_HORIZONS = {"1m": 21, "3m": 63, "6m": 126, "12m": 252}
_ALLOWED_BASIS = {"local", "usd"}
_SAMPLING_POLICY = "all_supplied_timestamps_no_downsampling"
_NORMALIZATION = {
    "status": "unavailable",
    "reason": "qualification_policy_not_supplied",
}


def _contributor(observations: pd.Series | None, timestamp: pd.Timestamp) -> str | None:
    if observations is None or observations.empty:
        return None
    position = int(observations.index.searchsorted(timestamp, side="right")) - 1
    return observations.index[position].isoformat() if position >= 0 else None


def _inclusive_index(index: pd.DatetimeIndex, window: dict) -> pd.DatetimeIndex:
    start_iso, end_iso = window["start"], window["end"]
    isos = [timestamp.isoformat() for timestamp in index]
    if start_iso in isos and end_iso in isos:
        left = isos.index(start_iso)
        right = len(isos) - 1 - isos[::-1].index(end_iso)
        if left <= right:
            return index[left:right + 1]
    start, end = pd.Timestamp(start_iso), pd.Timestamp(end_iso)
    return index[(index >= start) & (index <= end)]


def _paired_levels(cc: str, closes: pd.DataFrame) -> tuple[pd.Series | None, pd.Series | None]:
    usd = owner.usd_series(cc, closes=closes)
    if usd is None:
        return None, None
    local = owner._local_aligned(cc, usd, closes)
    if local is None:
        return None, None
    # Proven exact shared suffix only; never fill a missing joint history.
    if local.index.equals(usd.index[-len(local):]):
        return local, usd.loc[local.index]
    return None, None


def _finite_positive_level(value) -> float | None:
    try:
        if value is None or pd.isna(value):
            return None
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number > 0 else None


def _missing_cell(series: pd.Series | None, timestamp: pd.Timestamp) -> bool:
    if series is None or timestamp not in series.index:
        return True
    try:
        return bool(pd.isna(series.loc[timestamp]))
    except (TypeError, ValueError):
        return True


def _points(
    timestamps: pd.DatetimeIndex,
    *,
    derived: pd.Series | None,
    price: pd.Series | None,
    fx: pd.Series | None,
    require_fx: bool,
) -> list[dict]:
    levels = derived.reindex(timestamps) if derived is not None else None
    price_obs = None if price is None else price.dropna()
    fx_obs = None if (not require_fx or fx is None) else fx.dropna()
    points = []
    for timestamp in timestamps:
        price_missing = _missing_cell(price, timestamp)
        fx_missing = _missing_cell(fx, timestamp) if require_fx else False
        if require_fx and price_missing and fx_missing:
            value, reason = None, "missing_price_and_fx"
        elif price_missing:
            value, reason = None, "missing_price"
        elif fx_missing:
            value, reason = None, "missing_fx"
        else:
            raw = None if levels is None else levels.loc[timestamp]
            value = _finite_positive_level(raw)
            reason = None if value is not None else "invalid_calculation"
        points.append({
            "timestamp": timestamp.isoformat(),
            "value": value,
            "reason": reason,
            "source_observations": {
                "price": _contributor(price_obs, timestamp),
                "fx": _contributor(fx_obs, timestamp) if require_fx else None,
            },
        })
    return points


def _status_from_points(points: list[dict]) -> tuple[str, str | None]:
    finite = [point["value"] is not None for point in points]
    if finite and all(finite):
        return "available", None
    if any(finite):
        return "partial", "partial_numerical_coverage"
    return "unavailable", "no_numerical_coverage"


def _derived_levels(cc: str, closes: pd.DataFrame, *, basis: str, policy: str,
                    index_id: str) -> pd.Series | None:
    if basis == "local" and policy == "observed_local_prices":
        return closes[index_id] if index_id in closes.columns else None
    local, usd = _paired_levels(cc, closes)
    return local if basis == "local" else usd


def _chart_record(return_record: dict, closes: pd.DataFrame, *,
                  horizon: str, basis: str) -> dict:
    selected = return_record[basis]
    window = deepcopy(selected["window"])
    record = {
        "market_id": return_record["market_id"],
        "index_id": return_record["index_id"],
        "index_label": return_record["index_label"],
        "fx_id": return_record["fx_id"],
        "fx_quote_orientation": return_record["fx_quote_orientation"],
        "horizon": horizon,
        "basis": basis,
        "return_basis": "price",
        "currency_basis": basis,
        "currency_code": "USD" if basis == "usd" else None,
        "currency_code_reason": None if basis == "usd" else "owner_not_exposed",
        "qualification": "not_evaluated",
        "window": window,
        "sampling_policy": _SAMPLING_POLICY,
        "normalization": deepcopy(_NORMALIZATION),
    }
    if selected["numerical_status"] != "available":
        record["numerical_status"] = "unavailable"
        record["reason"] = selected["reason"]
        record["points"] = []
        return record

    policy = window["calendar_policy"] if window is not None else ""
    derived = _derived_levels(
        return_record["market_id"], closes, basis=basis, policy=policy,
        index_id=return_record["index_id"],
    )
    timestamps = _inclusive_index(closes.index, window)
    price = closes[return_record["index_id"]] if return_record["index_id"] in closes.columns else None
    fx = closes[return_record["fx_id"]] if return_record["fx_id"] in closes.columns else None
    points = _points(
        timestamps, derived=derived, price=price, fx=fx, require_fx=(basis == "usd"),
    )
    status, reason = _status_from_points(points)
    record["numerical_status"] = status
    record["reason"] = reason
    record["points"] = points
    return record


def _envelope(records: list[dict], source_reference: str | None,
              reason: str | None = None) -> dict:
    statuses = [record["numerical_status"] for record in records]
    if records and all(status == "available" for status in statuses):
        status = "available"
        reason = None
    elif any(status in ("available", "partial") for status in statuses):
        status = "partial"
        if reason is None:
            reason = "partial_numerical_coverage"
    else:
        status = "unavailable"
        if reason is None:
            reason = "no_numerical_coverage"
    return {
        "source_reference": source_reference,
        "source_reference_reason": None if source_reference is not None else "unknown",
        "numerical_status": status,
        "reason": reason,
        "records": records,
    }


def build_chart_records(
    closes: pd.DataFrame,
    *,
    market_ids: Sequence[str] | None = None,
    horizon: str = "1m",
    basis: str = "usd",
    source_reference: str | None = None,
) -> dict:
    """Project supplied prices into raw selected-period numerical series.

    Request, source and geometry validation are the accepted records adapter's.
    An unavailable selected metric emits no points and keeps that metric's
    reason and window. A malformed request raises ValueError.
    """
    envelope = build_return_records(
        closes, market_ids=market_ids, source_reference=source_reference,
    )
    if not isinstance(basis, str) or basis not in _ALLOWED_BASIS:
        raise ValueError("invalid_request:basis")
    horizons = owner._pcfg().get("horizons_d", _DEFAULT_HORIZONS)
    if not isinstance(horizon, str) or not horizon or (
        horizon != "ytd" and (not isinstance(horizons, dict) or horizon not in horizons)
    ):
        raise ValueError("invalid_request:horizon")
    if envelope["reason"] in ("no_markets", "invalid_geometry"):
        return _envelope([], envelope["source_reference"], envelope["reason"])
    records = [
        _chart_record(return_record, closes, horizon=horizon, basis=basis)
        for return_record in envelope["records"]
        if return_record["horizon"] == horizon
    ]
    return _envelope(records, envelope["source_reference"])
