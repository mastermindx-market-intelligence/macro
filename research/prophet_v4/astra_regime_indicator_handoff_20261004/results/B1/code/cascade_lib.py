"""Cascade with memory factor k — reproduces engine.canon.rsi_macd when k=1
and transforms every smoother's alpha by alpha_k = 1 − (1 − alpha)^k when k != 1.

Memory factor semantics:

  k = 1          → alpha_k = alpha              (canonical; matches canon.rsi_macd exactly)
  k > 1          → alpha_k > alpha              (SHORTER memory; faster decay on bars;
                                                 e.g. amended 3D.K1 = k=3 → 1-session elapsed memory)
  k < 1          → alpha_k < alpha              (LONGER memory; slower decay on bars;
                                                 e.g. amended 1D.M3 = k=1/3 → 3-session elapsed memory)

The math: with alpha ∈ (0,1) and k>0, (1-alpha)^k is monotone in k.
For k>1, (1-alpha)^k < (1-alpha), so alpha_k = 1 - (1-alpha)^k > alpha.
A larger alpha means the smoother forgets old bars faster → SHORTER memory.
Conversely, k<1 gives a smaller alpha and LONGER memory.

Amended constants binding for B1:
  1D.M2 = cascade(close_1D, k=1/2)   (1D grain, 2-session elapsed memory)
  1D.M3 = cascade(close_1D, k=1/3)   (1D grain, 3-session elapsed memory)
  3D.K1 = cascade(close_3D(p=0), k=3) (3D grain, 1-session elapsed memory)

Half-life in SESSIONS (EMA60 reference):
  1D     k=1   → 20.8 sessions
  1D.M3  k=1/3 → 62.4 sessions
  3D.p0  k=1   → 62.4 sessions  (3 × 20.8)
  3D.K1  k=3   → 20.8 sessions  (3 × 6.94 bar half-lives)

Used by B1 lane (stock-panel phase and matched-memory event panel).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# --- Wilder RMA ---------------------------------------------------------------
def _rma_alpha_for(n: int, k: float) -> float:
    """alpha_k = 1 - (1 - 1/n)^k for RMA of length n."""
    base = 1.0 - 1.0 / n
    return float(1.0 - (base ** k))


def rma_cascade(series: pd.Series, n: int, k: float = 1.0) -> pd.Series:
    """Wilder RMA with memory factor k.

    For k=1: matches engine.canon.rma exactly (SMA-seed of first n finite values,
    then recursive with alpha_k = 1/n).
    For k != 1: alpha_k = 1 - (1 - 1/n)^k.
    Carry-through on NaN (Pine na-handling for RMA).
    """
    s = pd.to_numeric(series, errors="coerce").astype(float)
    vals = s.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    alpha = _rma_alpha_for(n, k)
    finite = np.isfinite(vals)
    prev = np.nan
    seeded = False
    for i in range(len(vals)):
        if not seeded:
            if i >= n - 1 and finite[i - n + 1:i + 1].all():
                prev = float(np.mean(vals[i - n + 1:i + 1]))
                out[i] = prev
                seeded = True
            continue
        v = vals[i]
        if not np.isfinite(v):
            out[i] = prev
            continue
        prev = alpha * v + (1.0 - alpha) * prev
        out[i] = prev
    return pd.Series(out, index=s.index)


# --- EMA ----------------------------------------------------------------------
def _ema_alpha_for(n: int, k: float) -> float:
    """alpha_k = 1 - (1 - 2/(n+1))^k for EMA of length n (canonical span=n, alpha=2/(n+1))."""
    base = 1.0 - 2.0 / (n + 1)
    return float(1.0 - (base ** k))


def ema_cascade(series: pd.Series, n: int, k: float = 1.0) -> pd.Series:
    """Recursive EMA with memory factor k.

    For k=1: matches engine.canon.ema (ewm(span=n, adjust=False, min_periods=n)).
    For k != 1: alpha_k = 1 - (1 - 2/(n+1))^k, applied via ewm(alpha=alpha_k,
    adjust=False, min_periods=n).
    """
    s = pd.to_numeric(series, errors="coerce").astype(float)
    alpha_k = _ema_alpha_for(n, k)
    return s.ewm(alpha=alpha_k, adjust=False, min_periods=n).mean()


# --- RSI ----------------------------------------------------------------------
def rsi_cascade(close: pd.Series, k: float = 1.0, n: int = 14) -> pd.Series:
    """Wilder RSI with memory factor k (uses rma_cascade)."""
    s = pd.to_numeric(close, errors="coerce").astype(float)
    d = s.diff()
    up = rma_cascade(d.clip(lower=0), n, k)
    dn = rma_cascade((-d).clip(lower=0), n, k)
    rs = up / dn.replace(0, np.nan)
    return 100.0 - 100.0 / (1.0 + rs)


# --- RSI-based MACD -----------------------------------------------------------
def rsi_macd_cascade(close: pd.Series, k: float = 1.0,
                     fast: int = 14, slow: int = 60, sig: int = 5,
                     rsi_len: int = 14):
    """RSI-MACD cascade. k=1 reproduces engine.canon.rsi_macd exactly."""
    r = rsi_cascade(close, k=k, n=rsi_len)
    macd = ema_cascade(r, fast, k) - ema_cascade(r, slow, k)
    sig_ = ema_cascade(macd, sig, k)
    return macd, sig_


# --- n-day bars with phase p --------------------------------------------------
def make_n_day_bars(close: pd.Series, n: int, phase: int,
                    positions: np.ndarray) -> pd.Series:
    """Build n-session bars with phase offset p (canonical, also enforces size==n).

    pos = absolute session positions (from session_anchor.session_positions).
    bucket = (pos + p) // n.
    bar close = close of the last session of the bucket.
    bar date = that session's date.
    Drop any bucket whose size != n (incomplete or internal-gap bucket).

    Output: pd.Series indexed by bar date (= last session date of the bucket),
    values = close at the last session.
    """
    s = close.dropna()
    if s.empty:
        return s
    pos_series = pd.Series(positions, index=s.index)
    buck = (pos_series + phase) // n
    df = pd.DataFrame({"v": s.to_numpy(), "d": s.index, "b": buck.to_numpy()})
    sizes = df.groupby("b").size()
    full_buckets = sizes.index[sizes == n]
    sub = df[df["b"].isin(full_buckets)]
    if sub.empty:
        return pd.Series(dtype=float, name="close")
    last = sub.groupby("b").agg(v=("v", "last"), d=("d", "last"))
    out = pd.Series(last["v"].to_numpy(), index=pd.DatetimeIndex(last["d"].to_numpy()),
                    name="close")
    out.index.name = "Date"
    return out