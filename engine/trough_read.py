"""Description-only Prophet trough state; no scoring/ranking consumer.

Event definition: RD causal_fires, revision 1.2. The replay implementation is
imported unchanged. Calendar bars deliberately retain its trailing-bucket lag.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine import canon
from engine.stock_identity.replay import grey_dot as gd
from engine.stock_identity.replay.grid import macro_grid

ENGINE_REF = "e999086d"
TIMEFRAMES = ("1D", "3D", "1W", "2W")


def causal_fires(c: pd.Series) -> pd.DatetimeIndex:
    """Port of the desk's eight-line causal availability filter, unchanged."""
    mask, d, grid = gd._terminal_dot_mask(c)
    known = pd.DatetimeIndex(grid.known)
    two = gd._period_last_session(c, "2B")
    if len(two) < canon.BASE_LEN + canon.SIG_LEN:
        return pd.DatetimeIndex([])
    m, s = canon.rsi_macd(pd.Series(two.close.to_numpy()))
    h = m - s
    rise = (h > h.shift()).fillna(False).to_numpy()
    first = c.resample("2B").apply(lambda z: z.index[0] if len(z) else pd.NaT).dropna()
    avail = pd.DatetimeIndex(first.iloc[1:len(two) + 1])
    ix = avail.searchsorted(known, side="right") - 1
    good = ix >= 0
    out = np.zeros(len(mask), bool)
    out[good] = rise[ix[good]]
    out &= ix + 1 >= canon.BASE_LEN + canon.SIG_LEN
    return known[mask & out]


def washed_out(d: pd.Series) -> pd.Series:
    """Exactly the replay's from_os rule, including a full eight-bar window."""
    return (d.rolling(canon.CONF_W).min() < canon.OS).fillna(False)


def completed_bars(c: pd.Series, tf: str) -> tuple[pd.Series, pd.DatetimeIndex]:
    if tf == "1D":
        return pd.Series(c.to_numpy()), pd.DatetimeIndex(c.index)
    if tf == "3D":
        grid = macro_grid(c, 3)
        complete = grid.completed_mask()
        return (pd.Series(grid.close.to_numpy()[complete]),
                pd.DatetimeIndex(grid.known.to_numpy()[complete]))
    if tf not in ("1W", "2W"):
        raise ValueError("unknown timeframe")
    bars = gd._period_last_session(c, "W-FRI" if tf == "1W" else "2W-FRI")
    return pd.Series(bars.close.to_numpy()), pd.DatetimeIndex(bars.known)


def _float(value) -> float | None:
    return float(value) if pd.notna(value) and np.isfinite(value) else None


def _comparison(a: pd.Series, b: pd.Series) -> bool | None:
    if a.empty or b.empty or pd.isna(a.iloc[-1]) or pd.isna(b.iloc[-1]):
        return None
    return bool(a.iloc[-1] > b.iloc[-1])


def timeframe_state(c: pd.Series, tf: str, fires: pd.DatetimeIndex) -> dict:
    bars, known = completed_bars(c, tf)
    empty = {"tf": tf, "bar_end": None, "available": False,
             "washed_out": None, "d": None, "turned_up": None,
             "components": dict.fromkeys(("K_gt_D", "K_rising", "D_rising", "hist_rising"))}
    if bars.empty:
        return empty
    empty["bar_end"] = str(known[-1].date())
    # A finite D alone is insufficient: the washout predicate needs eight D's.
    k, d = canon.stoch_rsi_kd(bars)
    if len(d) < canon.CONF_W or d.iloc[-canon.CONF_W:].isna().any():
        return empty
    m, signal = canon.rsi_macd(bars)
    hist = m - signal
    return {"tf": tf, "bar_end": str(known[-1].date()), "available": True,
            "washed_out": bool(washed_out(d).iloc[-1]), "d": _float(d.iloc[-1]),
            "turned_up": bool(known[-1] in fires) if tf == "3D" else None,
            "components": {"K_gt_D": _comparison(k, d),
                           "K_rising": _comparison(k, k.shift()),
                           "D_rising": _comparison(d, d.shift()),
                           "hist_rising": _comparison(hist, hist.shift())}}


def own_history(c: pd.Series, fires: pd.DatetimeIndex) -> dict | None:
    atr = c.diff().abs().rolling(14).mean()
    depth = (c.rolling(252).max() - c) / atr.replace(0, np.nan)
    prior = depth.reindex(fires[fires < c.index[-1]]).replace([np.inf, -np.inf], np.nan).dropna()
    current = _float(depth.iloc[-1])
    if len(prior) < 3 or current is None:
        return None
    return {"tf": "3D", "depth_atrc": current,
            "own_history_pct": float((prior <= current).mean()), "n_prior": len(prior),
            "past": [{"date": str(date.date()), "depth_atrc": float(value)}
                     for date, value in prior.items()]}


def stock_read(c: pd.Series, *, group_id: str | None, group_name: str) -> dict:
    """Caller must truncate the daily input to completed sessions BEFORE calling."""
    c = pd.to_numeric(c, errors="coerce").dropna().sort_index()
    c = c[np.isfinite(c) & (c > 0)]
    if c.empty or not c.index.is_unique or c.index.tz is not None:
        raise ValueError("unique timezone-naive daily prices required")
    fires = causal_fires(c)
    return {"as_of": str(c.index[-1].date()),
            "known_ts": fires[-1].tz_localize("UTC").isoformat() if len(fires) else None,
            "timeframes": [timeframe_state(c, tf, fires) for tf in TIMEFRAMES],
            "kind": None, "own_history": own_history(c, fires),
            "group": {"group_id": group_id, "name": group_name, "state": None, "fields": None},
            "provenance": None}
