"""Restated in-sample reads with availability lag (FRED legs +1 session) and execution lag (1).

IN-SAMPLE 2020-01-02 -> 2026-11-10; 2024+ is seen history. Writes
research/risk_radar/walkforward/INSAMPLE_READS_LAG1_v2.json. States from
/tmp/rr_insample_states_lag1.parquet (or recomputed with inputs.incumbent_signals()).
"""
import json, sys
from pathlib import Path
import pandas as pd
from engine.risk_radar_eval import inputs as I, labels as L, pivots as P, scorecard as S, insurer as N

def states(path="/tmp/rr_insample_states_lag1.parquet"):
    if Path(path).exists():
        return pd.read_parquet(path)["state"]
    from engine import risk_radar as rr, risk_radar_backtest as bt
    c = rr._calib(); g = I.incumbent_signals()
    return bt.state_series(rr.subscore_series(g, c), c, g)

px = L.spy_total_return(); st = states()
cut = pd.Timestamp("2026-11-10"); idx = px.index[(px.index >= pd.Timestamp("2020-01-02")) & (px.index <= cut)]
st = st.reindex(idx).ffill()
fl = I.baseline_flags(I.baseline_scores()).reindex(idx).fillna(False)
series = {"radar_loud": st.isin({"elevated", "risk-off"}), "radar_riskoff": st.eq("risk-off"),
          **{f"base_{c}": fl[c].astype(bool) for c in fl.columns}}
out = {"label": "IN-SAMPLE, availability lag FRED legs +1, execution lag 1", "scorecard": {},
       "pivot": {}, "placebo": {}, "insurer": {}}
eps = {d: [e for e in L.drawdown_episodes(px.loc[:cut], d, outcomes_through=cut) if e.peak >= idx[0]]
       for d in (0.10, 0.07, 0.05)}
for k, a in series.items():
    out["scorecard"][k] = S.score(a, px=px, outcomes_through=cut, seen_history_ok=True, name=k)
    for d, e in eps.items():
        out["pivot"][f"dd{int(d*100)}|{k}"] = P.score_pivots(a, turns=P.turns_from_episodes(e), episodes=e,
            outcomes_through=cut, post=10, seen_history_ok=True, name=k)
    if k in ("radar_loud", "radar_riskoff", "base_hy_oas_chg21_top_decile", "base_mech_near_high_1pct"):
        for near in ("high", "low"):
            out["placebo"][f"{k}|{near}"] = P.placebo(a, px=px, turns=P.turns_from_episodes(eps[0.05]),
                episodes=eps[0.05], outcomes_through=cut, near=near, n_draws=300, seen_history_ok=True)
spy = px.pct_change().reindex(idx); bills = N.bill_returns(idx)
rets = {k: N.sleeve_returns(a, spy, bills) for k, a in series.items()}
for k, r in {**rets, **N.comparators(idx, spy_ret=spy, bill_ret=bills, match_vol_of=rets["radar_loud"])}.items():
    out["insurer"][k] = N.profile(r, spy_ret=spy, bill_ret=bills, px=px, outcomes_through=cut, name=k)
Path("research/risk_radar/walkforward/INSAMPLE_READS_LAG1_v2.json").write_text(json.dumps(out, indent=1, default=str))
