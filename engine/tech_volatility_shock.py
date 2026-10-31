"""Deterministic SPY/QQQ EOD volatility-shock read for the Macro Dashboard.

Display-only. Reads the existing Massive raw daily OHLCV store; never mixes
Yahoo adjusted closes with raw opens. Prices represent XNYS regular sessions;
vendor daily volume includes broader market-day activity (see
DSC-SPY-DAILY-AGG-IS-RTH-PRICE-FULLDAY-ACTIVITY).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

import pandas as pd

from lib import nyse_calendar, store

log = logging.getLogger(__name__)
Z_WINDOW = 60
VOLUME_WINDOW = 20


def _missing(reason: str, *, asof: str | None = None) -> dict:
    return {
        "status": "unavailable", "reason": reason, "asof": asof,
        "lag_sessions": None, "indices": [], "relative_pp": None,
        "relative_z60": None, "session_read": None,
        "volume_scope": "full_market_day", "price_scope": "xnys_regular_session",
    }


def _number(value: object) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return v if math.isfinite(v) else None


def _clean(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    if not {"open", "close"}.issubset(frame.columns):
        return None
    try:
        idx = pd.DatetimeIndex(frame.index)
        if idx.hasnans:
            return None
        if idx.tz is not None:
            idx = idx.tz_convert("UTC").tz_localize(None)
        if not idx.equals(idx.normalize()) or not idx.is_unique:
            return None
        out = frame[["open", "close"]].copy()
        out.index = idx
        out = out.sort_index()
        for col in ("open", "close"):
            out[col] = pd.to_numeric(out[col], errors="coerce")
            out.loc[~(out[col] > 0) | ~out[col].apply(math.isfinite), col] = float("nan")
        if "volume" in frame.columns:
            out["volume"] = pd.to_numeric(frame["volume"].set_axis(idx), errors="coerce")
            out.loc[~(out["volume"] > 0) | ~out["volume"].apply(math.isfinite), "volume"] = float("nan")
        else:
            out["volume"] = float("nan")
        return out
    except (TypeError, ValueError, OverflowError, KeyError):
        return None


def _returns(bars: pd.DataFrame) -> pd.Series:
    """Close-to-close returns, null across missing exchange sessions."""
    close = bars["close"]
    raw = close.pct_change(fill_method=None)
    for i in range(1, len(bars)):
        d0, d1 = bars.index[i - 1].date(), bars.index[i].date()
        if nyse_calendar.sessions_strictly_between(d0, d1):
            raw.iat[i] = float("nan")
    return raw


def _z_prior(returns: pd.Series, date: pd.Timestamp, value: float | None) -> float | None:
    """Causal reference: exactly the previous 60 rows, never includes today."""
    if value is None:
        return None
    hist = returns.loc[returns.index < date].tail(Z_WINDOW)
    if len(hist) != Z_WINDOW or hist.isna().any():
        return None
    stdev = float(hist.std(ddof=1))
    if not math.isfinite(stdev) or stdev <= 0:
        return None
    return round((value - float(hist.mean())) / stdev, 2)


def _volume_multiple(bars: pd.DataFrame, date: pd.Timestamp) -> float | None:
    today = _number(bars.at[date, "volume"])
    prior = bars.loc[bars.index < date, "volume"].tail(VOLUME_WINDOW)
    if today is None or today <= 0 or len(prior) != VOLUME_WINDOW or prior.isna().any():
        return None
    mean = float(prior.mean())
    return round(today / mean, 2) if mean > 0 and math.isfinite(mean) else None


def _rank(returns: pd.Series, date: pd.Timestamp) -> tuple[int | None, int]:
    """Observed calendar-year rank, 1=worst; ties share a rank."""
    series = returns.loc[(returns.index.year == date.year) & (returns.index <= date)]
    eligible = series.dropna()
    if date not in eligible.index:
        return None, len(eligible)
    val = float(eligible.loc[date])
    return 1 + int((eligible < val).sum()), len(eligible)


def _pct(v: float | None) -> float | None:
    return round(v * 100, 2) if v is not None and math.isfinite(v) else None


def snapshot_from_bars(
    spy_raw: pd.DataFrame | None,
    qqq_raw: pd.DataFrame | None,
    *,
    now: datetime | None = None,
) -> dict:
    """Pure presentation model. No network, no writes, and no futures."""
    spy, qqq = _clean(spy_raw), _clean(qqq_raw)
    if spy is None or qqq is None:
        return _missing("Regular-session raw OHLC not available for both ETFs.")
    date = spy.index[-1]
    if qqq.index[-1] != date:
        return _missing("SPY and QQQ daily bars have different as-of sessions.")
    asof = date.date().isoformat()
    if not nyse_calendar.is_session(date.date()):
        return _missing("Latest price date is not an exchange session.", asof=asof)
    now = now or datetime.now(timezone.utc)
    expected = nyse_calendar.expected_last_session(now)
    if date.date() > expected:
        return _missing("The latest bar has not passed the session-completion cutoff.", asof=asof)
    lag = nyse_calendar.sessions_behind(date.date(), now=now)
    prev_date = nyse_calendar.last_session_on_or_before(date.date() - timedelta(days=1))
    prev = pd.Timestamp(prev_date)
    if prev not in spy.index or prev not in qqq.index:
        return _missing("Previous regular-session close missing for one or both ETFs.", asof=asof)
    spy_r, qqq_r = _returns(spy), _returns(qqq)
    idx_rows = []
    raw_current = {}
    legs = {}
    for symbol, bars, returns in (("SPY", spy, spy_r), ("QQQ", qqq, qqq_r)):
        op = _number(bars.at[date, "open"])
        cl = _number(bars.at[date, "close"])
        pc = _number(bars.at[prev, "close"])
        if not op or not cl or not pc:
            return _missing(f"{symbol} current/previous regular-session price invalid.", asof=asof)
        net = cl / pc - 1.0
        overnight = op / pc - 1.0
        intraday = cl / op - 1.0
        # Invariant: legs compound to the exact price return, not simply sum.
        if not math.isclose((1 + overnight) * (1 + intraday) - 1, net, abs_tol=1e-10):
            return _missing(f"{symbol} price decomposition failed.", asof=asof)
        raw_current[symbol] = net
        legs[symbol] = (overnight, intraday)
        rank, n_ytd = _rank(returns, date)
        z = _z_prior(returns, date, net)
        idx_rows.append({
            "symbol": symbol, "return_pct": _pct(net), "z60": z,
            "volume_multiple": _volume_multiple(bars, date),
            "rank_ytd": rank, "n_ytd": n_ytd, "year": date.year,
            "overnight_pct": _pct(overnight), "intraday_pct": _pct(intraday),
            "overnight_share": round(abs(overnight) / (abs(overnight) + abs(intraday)) * 100, 1)
                if overnight < 0 and intraday < 0 else None,
        })
    paired = pd.concat([spy_r.rename("SPY"), qqq_r.rename("QQQ")], axis=1, join="inner")
    differential = (paired["QQQ"] - paired["SPY"]).where(paired.notna().all(axis=1))
    relative = raw_current["QQQ"] - raw_current["SPY"]
    relative_z = _z_prior(differential, date, relative)
    # All negative legs and a majority pre-open loss for BOTH symbols is required
    # before a shared "most damage before the open" statement is justified.
    if all(legs[s][0] < 0 and legs[s][1] < 0 for s in ("SPY", "QQQ")):
        if all(abs(legs[s][0]) > abs(legs[s][1]) for s in ("SPY", "QQQ")):
            read = "overnight_dominant"
        elif all(abs(legs[s][0]) < abs(legs[s][1]) for s in ("SPY", "QQQ")):
            read = "intraday_dominant"
        else:
            read = "mixed"
    else:
        read = "mixed"
    incomplete = (relative_z is None or any(
        v["z60"] is None or v["volume_multiple"] is None for v in idx_rows
    ))
    return {
        "status": "stale" if lag > 0 else "partial" if incomplete else "ok",
        "reason": ("Daily OHLC is behind the exchange calendar." if lag > 0 else
                   "Some historical statistics or volume baselines unavailable." if incomplete else None),
        "asof": asof, "lag_sessions": lag, "indices": idx_rows,
        "relative_pp": _pct(relative), "relative_z60": relative_z,
        "session_read": read,
        "volume_scope": "full_market_day", "price_scope": "xnys_regular_session",
    }


def build_snapshot(*, now: datetime | None = None) -> dict:
    """Read the existing R2-restored price store; fail visibly, never fabricate."""
    try:
        return snapshot_from_bars(
            store.read("massive_stock_day", "SPY"),
            store.read("massive_stock_day", "QQQ"),
            now=now,
        )
    except Exception as exc:  # noqa: BLE001 — a broken optional data lane is a null
        log.warning("tech volatility shock source unavailable: %s", exc)
        return _missing("Raw daily market-data store could not be read.")
