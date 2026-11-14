"""Mean placed mass under the pre-repair placement loop on the exact published placebo inputs (no outcome)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
from engine.risk_radar_eval import inputs as I, labels as L, pivots as P

def elig(p, near, tol=0.01):
    n = len(p); hi = np.maximum.accumulate(np.where(np.isnan(p), -np.inf, p))
    if near is None: return np.ones(n, bool)
    if near == "high": return p >= hi * (1 - tol)
    lo = np.empty(n)
    for i in range(n):
        lo[i] = p[i] if (i == 0 or hi[i] != hi[i-1] or p[i] >= hi[i]) else min(lo[i-1], p[i])
    return p <= lo * (1 + tol)

def old_mass(alert, px, near, n_draws, seed=0):   # verbatim pre-repair placement loop
    idx = alert.index; p = px.reindex(idx).ffill().to_numpy(float); n = len(idx)
    starts = np.flatnonzero(elig(p, near)); runs = [e-s+1 for s, e in P._run_bounds(alert.to_numpy(bool))]
    rng = np.random.default_rng(seed); m = []; short = 0
    for _ in range(n_draws):
        a = np.zeros(n, bool)
        for ln in rng.permutation(runs):
            for _t in range(50):
                s = int(rng.choice(starts)) if len(starts) else 0
                e = min(n, s + int(ln)); lo_, hi_ = max(0, s-1), min(n, e+1)
                if not a[lo_:hi_].any(): a[s:e] = True; break
        m.append(int(a.sum())); short += a.sum() < sum(runs)
    return {"mass": int(sum(runs)), "mean_placed": round(float(np.mean(m)), 1), "draws_short": int(short), "n_draws": n_draws}

px = L.spy_total_return(); CUT = pd.Timestamp("2026-11-10"); LOUD = {"elevated", "risk-off"}
out = {}
s = pd.read_csv(ROOT/"data/risk_radar/walkforward_alert_series.csv", comment="#", parse_dates=["date"]).set_index("date")["loud"].astype(bool)
for near in ("high", "low"):
    out[f"OOS §3 walkforward_loud 2022-26|{near}"] = old_mass(s, px, near, 2000)
    out[f"2022-23 subset|{near}"] = old_mass(s.loc[:"2023-12-29"], px, near, 2000)
idx = px.index[(px.index >= pd.Timestamp("2020-01-02")) & (px.index <= CUT)]
fl = I.baseline_flags(I.baseline_scores()).reindex(idx).fillna(False)
st1 = pd.read_parquet(sys.argv[1])["state"].reindex(idx).ffill()
st0 = pd.read_parquet(sys.argv[2])["state"].reindex(idx).ffill()
for k, a in {"§6 radar_loud": st1.isin(LOUD), "§6 hy": fl["hy_oas_chg21_top_decile"].astype(bool),
             "§6 mech_near_high": fl["mech_near_high_1pct"].astype(bool),
             "pivot radar_loud": st0.isin(LOUD), "pivot vix_ge_20": fl["vix_ge_20"].astype(bool),
             "pivot spy_below_200": fl["spy_below_200"].astype(bool)}.items():
    for near in ("high", "low"):
        out[f"{k}|{near}"] = old_mass(a, px, near, 300)
print(json.dumps(out, indent=1))
