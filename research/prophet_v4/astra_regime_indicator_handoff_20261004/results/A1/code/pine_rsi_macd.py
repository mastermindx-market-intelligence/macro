"""Independent Pine-formula RSI-MACD. Does not import engine.canon.

Formulas (lane A1 spec + R4):
  gain/loss from close diffs
  RMA: ta.sma seed over the first n finite values, then (src + (n-1)*prev)/n
  RSI = 100 - 100/(1 + RMA(gain)/RMA(loss))
  EMA alpha=2/(span+1), seed = first finite value, recursive, adjust=False
  macd = EMA(RSI, 14) - EMA(RSI, 60)
  signal = EMA(macd, 5)
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def pine_rma(series: pd.Series, n: int) -> pd.Series:
    """Pine ``ta.rma``: SMA of the first n finite src values, then Wilder step.

    Pine writes the recursive step as ``(src + (n-1)*prev)/n``, which is the
    same algebra as ``alpha=1/n`` but is not the SMA-window / NaN-carry loop
    in ``engine.canon.rma``. Interior NaN after the seed leaves that bar NaN
    and does not update ``prev`` (Pine ``na``).
    """
    s = pd.to_numeric(series, errors="coerce").astype(float)
    src = s.to_numpy(dtype=float)
    n_obs = int(src.shape[0])
    out = np.full(n_obs, np.nan, dtype=float)
    seed_buf = np.empty(n, dtype=float)
    filled = 0
    seed_i = None
    for i, v in enumerate(src):
        if not np.isfinite(v):
            continue
        if filled < n:
            seed_buf[filled] = v
            filled += 1
            if filled == n:
                seed_i = i
            continue
        break
    if seed_i is None:
        return pd.Series(out, index=s.index)
    prev = float(seed_buf.sum() / n)
    out[seed_i] = prev
    nm1 = float(n - 1)
    for i in range(seed_i + 1, n_obs):
        v = src[i]
        if not np.isfinite(v):
            continue
        prev = (v + nm1 * prev) / n
        out[i] = prev
    return pd.Series(out, index=s.index)


def pine_ema(series: pd.Series, span: int) -> pd.Series:
    """Recursive EMA, alpha=2/(span+1), seeded with the first finite value.

    Unlike engine.canon.ema this does NOT apply min_periods=span: values are
    emitted from the seed bar onward.
    """
    s = pd.to_numeric(series, errors="coerce").astype(float)
    vals = s.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    alpha = 2.0 / (span + 1.0)
    prev = np.nan
    started = False
    for i, v in enumerate(vals):
        if not np.isfinite(v):
            if started:
                out[i] = prev
            continue
        if not started:
            prev = float(v)
            out[i] = prev
            started = True
            continue
        prev = alpha * float(v) + (1.0 - alpha) * prev
        out[i] = prev
    return pd.Series(out, index=s.index)


def pine_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    s = pd.to_numeric(close, errors="coerce").astype(float)
    d = s.diff()
    up = pine_rma(d.clip(lower=0), n)
    dn = pine_rma((-d).clip(lower=0), n)
    rs = up / dn.replace(0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


def pine_rsi_macd(close: pd.Series):
    """Return (macd, signal) with Pine lengths 14/60/5 on RSI-14."""
    r = pine_rsi(close, 14)
    macd = pine_ema(r, 14) - pine_ema(r, 60)
    signal = pine_ema(macd, 5)
    return macd, signal


def bullish_cross_dates(macd: pd.Series, signal: pd.Series) -> pd.DatetimeIndex:
    """Dates where macd crosses above signal (strict, prior bar <=)."""
    a = pd.to_numeric(macd, errors="coerce")
    b = pd.to_numeric(signal, errors="coerce")
    cross = (a > b) & (a.shift(1) <= b.shift(1))
    return pd.DatetimeIndex(cross[cross.fillna(False)].index)
