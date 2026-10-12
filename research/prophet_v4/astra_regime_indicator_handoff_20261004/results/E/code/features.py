"""Lane E — family feature construction (pure functions, testable).

Six pre-declared family features at signal-date close t (sessions = name's own
sessions; a feature needing more history than the name has at t is NaN and the
event is dropped from that family's table only):

    trend          = close_t / SMA200_t − 1
    momentum       = close_{t−21} / close_{t−252} − 1            (12-1 momentum)
    compression    = (std of log returns over the last 20 sessions) /
                     (std over the last 120 sessions)            (low = compressed)
    participation  = share of ALL universe names whose close_t > their own
                     SMA50_t on the SPY session date t           (date-level)
    rs             = (close_t / close_{t−63}) / (SPY_t / SPY_{t−63}) − 1
    structure      = close_t / max(close over the last 252 sessions) − 1
                                                            (0 = at the 52-week high)
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd


FAMILIES = ["trend", "momentum", "compression", "participation", "rs", "structure"]


def _log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(1))


def _sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n, min_periods=n).mean()


# ───────────────────────────────────────────────────────────────── #
# Per-name rolling computations (pure; depend only on close series)
# ───────────────────────────────────────────────────────────────── #
def per_name_rolling(close: pd.Series) -> pd.DataFrame:
    """Compute the per-name rolling quantities once for fast event-level lookup.

    Returns a DataFrame indexed by the name's own session dates with columns:
        close, sma200, sma50, log_ret, std20_log_ret, std120_log_ret,
        close_lag21, close_lag63, close_lag252, max252
    """
    s = close.sort_index().astype(float)
    out = pd.DataFrame(index=s.index)
    out["close"] = s
    out["sma200"] = _sma(s, 200)
    out["sma50"] = _sma(s, 50)
    lr = _log_returns(s)
    out["log_ret"] = lr
    out["std20_log_ret"] = lr.rolling(20, min_periods=20).std()
    out["std120_log_ret"] = lr.rolling(120, min_periods=120).std()
    out["close_lag21"] = s.shift(21)
    out["close_lag63"] = s.shift(63)
    out["close_lag252"] = s.shift(252)
    out["max252"] = s.rolling(252, min_periods=252).max()
    return out


def feat_trend(rolling: pd.DataFrame) -> pd.Series:
    out = rolling["close"] / rolling["sma200"] - 1.0
    out.name = "trend"
    return out


def feat_momentum(rolling: pd.DataFrame) -> pd.Series:
    out = rolling["close_lag21"] / rolling["close_lag252"] - 1.0
    out.name = "momentum"
    return out


def feat_compression(rolling: pd.DataFrame) -> pd.Series:
    out = rolling["std20_log_ret"] / rolling["std120_log_ret"]
    out.name = "compression"
    return out


def feat_structure(rolling: pd.DataFrame) -> pd.Series:
    out = rolling["close"] / rolling["max252"] - 1.0
    out.name = "structure"
    return out


def feat_rs(rolling: pd.DataFrame, spy_close: pd.Series) -> pd.Series:
    c = rolling["close"]
    c63 = rolling["close_lag63"]
    spy = spy_close.reindex(rolling.index, method="ffill")
    spy63 = spy.shift(63)
    rs_ratio = (c / c63) / (spy / spy63) - 1.0
    rs_ratio.name = "rs"
    return rs_ratio


# ───────────────────────────────────────────────────────────────── #
# Participation: date-level (single value per session date)
# ───────────────────────────────────────────────────────────────── #
def participation_series(
    name_rolling_dict: dict[str, pd.DataFrame],
    *,
    min_names_with_sma50: int = 50,
) -> pd.Series:
    """Universe-wide participation share per date.

    For each date d:
      participation(d) = share of names whose close[d] > SMA50[d]
    The denominator is the count of names that have a *valid* SMA50 on d
    (NaN SMA50 / missing close is excluded from both numerator and
    denominator — names still in the SMA50 warm-up do not count as "not
    above"). Survivorship caveat: a name with no row on d is also excluded;
    the universe is current-membership only.

    Returns a Series indexed by the union of name dates.
    """
    panels = []
    for name, roll in name_rolling_dict.items():
        valid = roll["sma50"].notna() & roll["close"].notna()
        cond = (roll["close"] > roll["sma50"]).where(valid).rename(name)
        panels.append(cond)
    if not panels:
        return pd.Series(dtype=float, name="participation")
    wide = pd.concat(panels, axis=1).sort_index()
    denom = wide.notna().sum(axis=1)
    numer = (wide == True).sum(axis=1)  # noqa: E712
    out = (numer / denom).where(denom >= min_names_with_sma50)
    out.name = "participation"
    return out


# ───────────────────────────────────────────────────────────────── #
# Event-level feature lookup (vectorized over many events)
# ───────────────────────────────────────────────────────────────── #
def lookup_per_name_feature(
    rolling_dict: dict[str, pd.DataFrame],
    events: pd.DataFrame,
    feature_fn: Callable[[pd.DataFrame], pd.Series],
) -> pd.Series:
    """Look up feature_fn(rolling) at each event's signal_date for that name.

    Aligns to events.index. NaN where the name or date is missing. Uses
    positional writes so a non-RangeIndex is safe.
    """
    n = len(events)
    out = np.full(n, np.nan)
    if n == 0:
        return pd.Series(out, index=events.index)
    tmp = pd.DataFrame({
        "name": events["name"].to_numpy(),
        "signal_date": pd.to_datetime(events["signal_date"]).to_numpy(),
        "pos": np.arange(n),
    })
    for name, sub in tmp.groupby("name", sort=False):
        if name not in rolling_dict:
            continue
        feat = feature_fn(rolling_dict[name])
        d = pd.DatetimeIndex(sub["signal_date"]).normalize()
        out[sub["pos"].to_numpy()] = feat.reindex(d).to_numpy()
    return pd.Series(out, index=events.index)


def lookup_participation(
    part_series: pd.Series,
    events: pd.DataFrame,
) -> pd.Series:
    """Look up participation share per event signal_date (exact date, no ffill)."""
    dates = pd.DatetimeIndex(pd.to_datetime(events["signal_date"])).normalize()
    vals = part_series.reindex(dates)
    return pd.Series(vals.to_numpy(), index=events.index)


# ───────────────────────────────────────────────────────────────── #
# Tercile binning on the PRIMARY event set over the whole sample
# ───────────────────────────────────────────────────────────────── #
def fixed_tercile_cuts(values: pd.Series) -> tuple[float, float]:
    """Tercile cuts (1/3, 2/3 quantiles) on the PRIMARY event set."""
    v = values.dropna()
    if len(v) < 30:
        return float("nan"), float("nan")
    return float(v.quantile(1.0 / 3)), float(v.quantile(2.0 / 3))


def assign_terciles(values: pd.Series, lo: float, hi: float) -> pd.Series:
    """Bin into T1 (low), T2 (mid), T3 (high) using the pre-declared cuts."""
    out = pd.Series(index=values.index, dtype=object)
    if np.isnan(lo) or np.isnan(hi):
        return out
    out[values < lo] = "T1"
    out[(values >= lo) & (values <= hi)] = "T2"
    out[values > hi] = "T3"
    return out
