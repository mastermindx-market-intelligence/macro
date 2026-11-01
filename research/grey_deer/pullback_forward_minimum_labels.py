"""Research-only, horizon-matured labels for *future minima*, never a forecast.

This derives outcomes to score prospective models. It does not estimate or
publish a present-day probability, create an episode ledger, infer a recovery,
or grant a capital action. The caller supplies an owning exchange calendar
and one coherent, versioned daily price basis. Revised-vintage historical
labels are NOT evidence of what an investor knew at the original session.
"""
from __future__ import annotations

from datetime import date, timedelta
from math import isfinite
from numbers import Real
from typing import Callable, Iterable

SCHEMA = "pullback_future_minimum_label.v1"


def _origin_day(origin: str) -> date:
    if not isinstance(origin, str) or len(origin) != 10:
        raise ValueError("origin must be a YYYY-MM-DD session label")
    try:
        day = date.fromisoformat(origin)
    except ValueError as exc:
        raise ValueError("invalid origin session") from exc
    if day.isoformat() != origin:
        raise ValueError("origin must use canonical YYYY-MM-DD")
    return day


def _target_days(origin: date, horizon: int,
                 is_session: Callable[[date], bool]) -> list[date]:
    days: list[date] = []
    probe = origin
    # The market-owning calendar decides sessions; never count weekends/holidays.
    # This bounded scan refuses impossible calendars instead of looping forever.
    for _ in range(4 * horizon + 40):
        probe += timedelta(days=1)
        if is_session(probe):
            days.append(probe)
            if len(days) == horizon:
                return days
    raise ValueError("calendar could not supply the requested session horizon")


def label_forward_minimum(
    rows: Iterable[tuple[str, float]],
    *, origin: str, horizon_sessions: int,
    is_session: Callable[[date], bool],
) -> dict:
    """Retrospective A_h = 1 - min(P_t,...,P_(t+h)) / P_t.

    Returns a maturity-aware, null-preserving label, not a predictor.
    The entire horizon must be observed to be a complete label. Missing
    expected sessions are never forward-filled or treated as confirmations.
    """
    day = _origin_day(origin)
    if (isinstance(horizon_sessions, bool)
            or not isinstance(horizon_sessions, int)
            or not 1 <= horizon_sessions <= 252):
        raise ValueError("horizon_sessions must be an integer 1..252")
    if not is_session(day):
        raise ValueError("origin is not an exchange trading session")
    future_days = _target_days(day, horizon_sessions, is_session)
    target_end = future_days[-1]
    result = {
        "schema": SCHEMA,
        "origin": origin,
        "horizon_sessions": horizon_sessions,
        "target_end": target_end.isoformat(),
        "matured": False,
        "reason": None,
        "origin_close": None,
        "minimum_close": None,
        "additional_loss_fraction": None,
    }

    def unavailable(reason: str) -> dict:
        return {**result, "reason": reason}

    records: dict[date, float] = {}
    try:
        for stamp, value in rows:
            if not isinstance(stamp, str) or len(stamp) != 10:
                return unavailable("ambiguous_session")
            session = date.fromisoformat(stamp)
            if session.isoformat() != stamp or not is_session(session):
                return unavailable("ambiguous_session")
            if session > target_end:
                continue  # outcome after this horizon cannot influence this label
            if isinstance(value, bool) or not isinstance(value, Real):
                return unavailable("invalid_price")
            price = float(value)
            if not isfinite(price) or price <= 0:
                return unavailable("invalid_price")
            if session in records and records[session] != price:
                return unavailable("ambiguous_session")
            records[session] = price
    except (TypeError, ValueError, OverflowError):
        return unavailable("ambiguous_session")
    if day not in records:
        return unavailable("missing_origin")
    if not records or max(records) < target_end:
        return unavailable("label_not_mature")
    if any(d not in records for d in future_days):
        return unavailable("missing_session")
    origin_close = records[day]
    low = min([origin_close] + [records[d] for d in future_days])
    return {
        **result, "matured": True, "reason": "mature",
        "origin_close": origin_close,
        "minimum_close": low,
        "additional_loss_fraction": max(0.0, 1.0 - low / origin_close),
    }
