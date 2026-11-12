"""Shared inputs: the incumbent's causal leg panel and the simple baselines.

Research-only. The incumbent panel is exactly ``engine.risk_radar.leading_signals()`` (the live
owner), so a challenger scored with this module sees the same inputs the Radar sees. Baselines
are causal daily scores/flags on the same calendar.
"""
from __future__ import annotations

import pandas as pd

from engine.indicators import pct_rank_window

PCT_WIN = 504  # same trailing causal percentile window as the engine (engine/risk_radar.py:52)


def incumbent_signals() -> pd.DataFrame:
    """Causal 0-1 leg percentiles, one column per leg (live owner, unchanged)."""
    from engine import risk_radar as rr
    return rr.leading_signals()


def gate_components(index: pd.DatetimeIndex | None = None) -> pd.DataFrame:
    """Inputs of the context gate, as in engine/risk_radar.context_gate_series:
    spy_below_200 (SPY < 200-session MA, min 120) and breadth_pct (504-session causal percentile
    of % members above their 200dma, forward-filled onto the SPY calendar)."""
    from lib import store
    spy = store.read("yahoo", "SPY")["close"]
    spy.index = pd.to_datetime(spy.index)
    below = spy < spy.rolling(200, min_periods=120).mean()
    out = pd.DataFrame({"spy_below_200": below})
    b = store.read("breadth", "breadth")
    if b is not None and "pct_above_200" in b.columns:
        bp = pct_rank_window(b["pct_above_200"].astype(float), PCT_WIN)
        bp.index = pd.to_datetime(bp.index)
        out["breadth_pct"] = bp.reindex(out.index).ffill()
    else:
        out["breadth_pct"] = float("nan")
    if index is not None:
        out = out.reindex(index)
        out["spy_below_200"] = out["spy_below_200"].fillna(False).astype(bool)
        out["breadth_pct"] = out["breadth_pct"].ffill()
    return out


def gate_series(components: pd.DataFrame, breadth_pct_thr: float) -> pd.Series:
    """Context gate with a given breadth threshold (0.40 reproduces the shipped gate)."""
    return (components["spy_below_200"].astype(bool)
            & (components["breadth_pct"] <= breadth_pct_thr)).fillna(False).astype(bool)


def baseline_scores() -> pd.DataFrame:
    """Causal baseline series on the SPY calendar.

    - ``spy_below_200``: bool, SPY total-return close below its 200-session average (min 200).
    - ``vix``: VIX close level (flags at the convention levels 20 and 25 via ``baseline_flags``).
    - ``hy_oas_chg21_pct``: 504-session causal percentile of the 21-session change in HY OAS.
    """
    from lib import store
    spy = store.read("yahoo", "SPY")["close"]
    spy.index = pd.to_datetime(spy.index)
    out = pd.DataFrame(index=spy.index)
    out["spy_below_200"] = spy < spy.rolling(200, min_periods=200).mean()
    vix = store.read("yahoo", "_VIX")
    if vix is not None:
        v = vix["close"]
        v.index = pd.to_datetime(v.index)
        out["vix"] = v.reindex(out.index).ffill(limit=3)
    hy = store.read("fred", "BAMLH0A0HYM2")
    if hy is not None:
        h = hy["hy_oas"].astype(float)
        h.index = pd.to_datetime(h.index)
        h = h.reindex(out.index).ffill(limit=3)
        out["hy_oas_chg21_pct"] = pct_rank_window(h.diff(21), PCT_WIN)
    return out


def baseline_flags(scores: pd.DataFrame) -> pd.DataFrame:
    """Fixed-rule baseline alerts (convention thresholds, never fitted)."""
    f = pd.DataFrame(index=scores.index)
    f["spy_below_200"] = scores["spy_below_200"].astype(bool)
    if "vix" in scores:
        f["vix_ge_20"] = scores["vix"] >= 20
        f["vix_ge_25"] = scores["vix"] >= 25
    if "hy_oas_chg21_pct" in scores:
        f["hy_oas_chg21_top_decile"] = scores["hy_oas_chg21_pct"] >= 0.90
    return f.fillna(False).astype(bool)
