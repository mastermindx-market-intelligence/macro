"""Insurer-profile secondary read: drawdown and risk-adjusted paper profile of an alert series.

Research-only, paper-only: never a trading rule, sizing or execution. Chairman's objective
(2026-11-12): higher risk-adjusted return and smaller drawdowns through regime awareness, not raw
S&P 500 outperformance. This is a declared SECONDARY read; the frozen prereg's primary endpoint
(the pivot read, `pivots.py`) is unchanged (PREREG_WALKFORWARD_v1_ADDENDUM_1.md).

Paper sleeve for an alert: alert seen at day d's close, executed at d+1's close -> bills for
session d+2, else SPY total return (one-session execution lag, desk H19; `exec_lag`). Bills = FRED DTB3 3-month yield, the prior session's value / 100 / 252 per session.

Metrics (per series, over its own window):
- max drawdown; longest time under water (sessions below the prior peak) and share of sessions
  under water;
- drawdowns avoided: for each SPY drawdown episode of >= depth (peak -> trough), 1 - sleeve
  return / SPY return over that span; median and pooled (sum of log declines);
- gains kept: sleeve log growth / SPY log growth on sessions outside every >= depth decline phase
  (onset..trough), and over rebound phases (trough+1..recovery) separately;
- Sharpe and Sortino of daily excess return over bills, annualised (sqrt 252);
- CAGR, reported last, never as the headline.

Comparators (`comparators`): SPY; RSP; SPY+bills at a constant weight matching the sleeve's
realized volatility (the weight uses the full window: a descriptive comparator, not a strategy
available at the time); fixed 60/40 SPY/IEF rebalanced daily; SPY-or-bills on the 200-session rule
(SPY below its 200-session average at d's close -> bills on d+1).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.risk_radar_eval import labels as L
from engine.risk_radar_eval.scorecard import _r, SESSIONS_PER_YEAR


def _tr(ticker: str) -> pd.Series:
    from lib import store
    s = store.read("yahoo", ticker)["close"].astype(float)
    s.index = pd.to_datetime(s.index)
    return s[s > 0].dropna()


def bill_returns(index: pd.DatetimeIndex) -> pd.Series:
    from lib import store
    y = store.read("fred", "DTB3")["us3m_bill"].astype(float)
    y.index = pd.to_datetime(y.index)
    y = y.reindex(index.union(y.index)).ffill().reindex(index)
    return (y.shift(1) / 100.0 / SESSIONS_PER_YEAR).fillna(0.0)


def sleeve_returns(alert: pd.Series, spy_ret: pd.Series, bill_ret: pd.Series,
                   exec_lag: int = 1) -> pd.Series:
    """Alert seen at d's close, executed at d+exec_lag's close -> bills for session d+1+exec_lag.
    Default exec_lag=1 (desk H19); exec_lag=0 reproduces the earlier same-close reading."""
    out_ = alert.astype(bool).shift(1 + exec_lag, fill_value=False).reindex(spy_ret.index).fillna(False)
    return spy_ret.where(~out_, bill_ret)


def profile(ret: pd.Series, *, spy_ret: pd.Series, bill_ret: pd.Series, px: pd.Series,
            outcomes_through, depths=(0.10, 0.07, 0.05), name: str = "") -> dict:
    ret = ret.dropna()
    idx = ret.index
    spy_ret = spy_ret.reindex(idx)
    bill_ret = bill_ret.reindex(idx).fillna(0.0)
    eq = (1 + ret).cumprod()
    # the running peak starts from opening capital 1.0, so a loss in session 1 counts
    dd = eq / eq.cummax().clip(lower=1.0) - 1
    uw = (dd < 0).to_numpy()
    longest, cur = 0, 0
    for u in uw:
        cur = cur + 1 if u else 0
        longest = max(longest, cur)
    ex = ret - bill_ret
    downside = np.sqrt(np.mean(np.minimum(ex.to_numpy(), 0.0) ** 2))
    yrs = len(idx) / SESSIONS_PER_YEAR
    lr, ls = np.log1p(ret), np.log1p(spy_ret)
    res = {"name": name, "window": [idx[0].date().isoformat(), idx[-1].date().isoformat()],
           "max_drawdown": _r(float(dd.min())),
           "longest_under_water_sessions": int(longest),
           "share_sessions_under_water": _r(float(uw.mean())),
           "sharpe_excess": _r(float(ex.mean() / ex.std() * np.sqrt(SESSIONS_PER_YEAR))) if ex.std() > 0 else None,
           "sortino_excess": _r(float(ex.mean() / downside * np.sqrt(SESSIONS_PER_YEAR))) if downside > 0 else None,
           "by_depth": {}}
    for depth in depths:
        eps = [e for e in L.drawdown_episodes(px.loc[:outcomes_through], depth,
                                              outcomes_through=outcomes_through)
               if e.onset >= idx[0] and e.trough <= idx[-1]]
        per, s_dec, p_dec = [], 0.0, 0.0
        decline = pd.Series(False, index=idx)
        rebound = pd.Series(False, index=idx)
        for e in eps:
            m = (idx >= e.onset) & (idx <= e.trough)
            decline |= m
            sd, pdx = float(ls[m].sum()), float(lr[m].sum())
            s_dec += sd
            p_dec += pdx
            per.append({"onset": e.onset.date().isoformat(), "trough": e.trough.date().isoformat(),
                        "spy": _r(float(np.expm1(sd))), "sleeve": _r(float(np.expm1(pdx))),
                        "avoided": _r(1 - pdx / sd) if sd < 0 else None})
            if e.recovery is not None:
                rebound |= (idx > e.trough) & (idx <= e.recovery)
        outside = ~decline
        g_s, g_p = float(ls[outside].sum()), float(lr[outside].sum())
        r_s, r_p = float(ls[rebound].sum()), float(lr[rebound].sum())
        av = [x["avoided"] for x in per if x["avoided"] is not None]
        res["by_depth"][f"dd{int(round(depth * 100))}"] = {
            "n_episodes": len(eps),
            "drawdown_avoided_median": _r(float(np.median(av))) if av else None,
            "drawdown_avoided_pooled": _r(1 - p_dec / s_dec) if s_dec < 0 else None,
            "gains_kept_outside_declines": _r(g_p / g_s) if g_s > 0 else None,
            "rebound_kept": _r(r_p / r_s) if r_s > 0 else None,
            "per_episode": per}
    res["cagr"] = _r(float(eq.iloc[-1] ** (1 / yrs) - 1)) if yrs > 0 else None
    return res


def comparators(index: pd.DatetimeIndex, *, spy_ret: pd.Series, bill_ret: pd.Series,
                match_vol_of: pd.Series | None = None) -> dict[str, pd.Series]:
    spy_px = _tr("SPY")
    out = {"SPY": spy_ret.reindex(index)}
    out["RSP"] = _tr("RSP").pct_change().reindex(index)
    ief = _tr("IEF").pct_change().reindex(index)
    out["60/40 SPY/IEF"] = 0.6 * out["SPY"] + 0.4 * ief
    below = (spy_px < spy_px.rolling(200, min_periods=200).mean()).reindex(index).fillna(False)
    out["SPY-or-bills 200d"] = sleeve_returns(below, out["SPY"], bill_ret.reindex(index))  # same lag
    if match_vol_of is not None:
        w = float(match_vol_of.reindex(index).std() / out["SPY"].std())
        w = min(max(w, 0.0), 1.0)
        out[f"SPY+bills vol-matched (w={w:.2f})"] = w * out["SPY"] + (1 - w) * bill_ret.reindex(index)
    return out
