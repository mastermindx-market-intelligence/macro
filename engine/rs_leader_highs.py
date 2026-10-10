"""Completed-session relative-strength new-high observations for Leader Radar.

Read-only projection of SPY-relative close ratios. No scorer, event owner, store,
order signal, or trade authority. Weekly highs use the last completed NYSE week;
a midweek partial candle can never be described as a confirmed weekly high.
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from lib.nyse_calendar import is_session, last_session_on_or_before, sessions_between

SCHEMA = "leader_rs_highs.v1"
DAILY_SESSIONS = 126
WEEKLY_WEEKS = 26


def _dated_close(series: pd.Series) -> pd.Series:
    """Map one daily bar per NY date without forward filling or deduping.

    Caller controls source adjustment basis. Ambiguous multiple bars per market
    session are rejected instead of silently choosing the last.
    """
    idx = pd.DatetimeIndex(pd.to_datetime(series.index))
    if idx.tz is not None:
        idx = idx.tz_convert("America/New_York").tz_localize(None)
    days = [stamp.date() for stamp in idx]
    if len(set(days)) != len(days):
        raise ValueError("duplicate_market_session")
    return pd.Series(series.to_numpy(dtype=float), index=pd.Index(days)).sort_index()


def _high(close: pd.Series, bench: pd.Series, sessions: list[date]) -> dict:
    """Strict new high against prior observed, *completed* closes only."""
    end = sessions[-1] if sessions else None
    result = {"as_of": end.isoformat() if end else None,
              "new_high": None, "price_new_high": None,
              "rs_leads_price": None, "reason": None}
    if len(sessions) < 2:
        result["reason"] = "insufficient_history"
        return result
    c = close.reindex(sessions).to_numpy(dtype=float)
    b = bench.reindex(sessions).to_numpy(dtype=float)
    if (not np.isfinite(c).all() or not np.isfinite(b).all()
            or (c <= 0).any() or (b <= 0).any()):
        result["reason"] = "source_gap_or_nonpositive_close"
        return result
    ratio = c / b
    new_high = bool(ratio[-1] > np.max(ratio[:-1]))
    price_high = bool(c[-1] > np.max(c[:-1]))
    result.update(new_high=new_high, price_new_high=price_high,
                  rs_leads_price=new_high and not price_high, reason=None)
    return result


def observe_rs_highs(
    close: pd.Series,
    benchmark_close: pd.Series,
    *,
    as_of: date,
) -> dict:
    """RS-line 126-session high and 26-*completed*-week high, both vs SPY.

    Missing data are UNKNOWN, never FALSE. A completed weekly observation is
    anchored to the actual last NYSE session of that week, including short
    holiday weeks. Input values after ``as_of`` never affect either result.
    """
    if not isinstance(as_of, date):
        raise ValueError("as_of_must_be_date")
    output = {
        "schema": SCHEMA, "benchmark": "SPY", "basis": "source_daily_close_ratio",
        "as_of": as_of.isoformat(),
        "daily": {"as_of": None, "lookback_sessions": DAILY_SESSIONS,
                  "new_high": None, "price_new_high": None,
                  "rs_leads_price": None, "reason": "unavailable"},
        "weekly": {"as_of": None, "lookback_completed_weeks": WEEKLY_WEEKS,
                   "new_high": None, "price_new_high": None,
                   "rs_leads_price": None, "reason": "unavailable"},
    }
    if not is_session(as_of):
        output["daily"]["reason"] = "not_nyse_session"
        output["weekly"]["reason"] = "not_nyse_session"
        return output
    try:
        c = _dated_close(close)
        b = _dated_close(benchmark_close)
    except (TypeError, ValueError, OverflowError):
        output["daily"]["reason"] = "invalid_daily_source_index"
        output["weekly"]["reason"] = "invalid_daily_source_index"
        return output

    sessions = sessions_between(as_of - timedelta(days=450), as_of)
    if len(sessions) >= DAILY_SESSIONS + 1:
        d = _high(c, b, sessions[-(DAILY_SESSIONS + 1):])
        output["daily"].update(d)
    else:
        output["daily"]["reason"] = "insufficient_history"

    # Select the last 27 completed Friday-anchored trading weeks. Do NOT use
    # resample('W-FRI').last() on partial/missing bars: that silently substitutes
    # Thursday for a missing Friday even when Friday was an open NYSE session.
    end_friday = as_of + timedelta(days=4 - as_of.weekday())
    candidate_fridays = [end_friday - timedelta(weeks=i)
                         for i in range(WEEKLY_WEEKS + 2)]
    week_last_sessions = []
    for friday in reversed(candidate_fridays):
        final = last_session_on_or_before(friday)
        if final <= as_of:
            week_last_sessions.append(final)
    if len(week_last_sessions) >= WEEKLY_WEEKS + 1:
        w = _high(c, b, week_last_sessions[-(WEEKLY_WEEKS + 1):])
        output["weekly"].update(w)
    else:
        output["weekly"]["reason"] = "insufficient_completed_weeks"
    return output
