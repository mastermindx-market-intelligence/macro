"""v2 power from 1998-2019 VARIANCE ONLY. Prints standard errors / tracking error, never a mean or point estimate.
Proxy contrast: a switch between the beta-sorted legs (state = price-only relative-trend break, the simplest member of
the family) minus the matched static mix of the same legs; SE of its annualised mean via stationary bootstrap."""
import sys, json, math
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")
from engine import rotation_core_evaluation as rc
exec(open("/home/ubuntu2/tmp/rotation-core/v2/arming_check_D.py").read().split("rel = ((1 + X.o)")[0])
rel = ((1 + X.o).cumprod() / (1 + X.d).cumprod())
state = (rel < rel.rolling(50).mean()).astype(float).shift(1)       # 1 = defend, decided t-1
Dm = (X.index >= "1998-01-02") & (X.index <= "2019-12-31") & state.notna().values
o, d_, st = X.o[Dm].fillna(0).values, X.d[Dm].fillna(0).values, state[Dm].values
r = np.where(st == 1, d_, o)                       # rotation on the base: full tilt (upper bound on active risk)
w = st.mean()
ref = w * d_ + (1 - w) * o
def stat(a, b, s_):
    ww = s_.mean(axis=1, keepdims=True)              # matched mix rebuilt inside each resample (parent ruling A)
    return ((a - (ww * b[0] + (1 - ww) * b[1])).mean(axis=1)) * 252
B = 4000; n = len(r)
idx = rc.stationary_bootstrap_indices(n, B, 21, 20261111)
dist = stat(r[idx], (d_[idx], o[idx]), st[idx])
se = float(np.std(dist, ddof=1)); te = float((r - ref).std(ddof=1) * math.sqrt(252))
yrs = n / 252
z = lambda p: __import__("statistics").NormalDist().inv_cdf(p)
k3 = z(1 - 0.05 / 3) + z(0.8)
def mde(years): return k3 * se * math.sqrt(yrs / years)
out = {"note": "variance only; full-tilt proxy (H1 tilts away from equal weight, so its active risk is at most this)",
       "D_years": round(yrs, 2), "D_se_annual": round(se, 4), "D_tracking_error": round(te, 4),
       "mde80_holm_m3": {"D_only_seen_not_confirmatory": round(mde(yrs), 4), "pre1998_1928_1997_70y": round(mde(70.0), 4),
                         "holdout_2020_2025_6y": round(mde(6.0), 4), "pooled_pre1998_plus_2020_2025": round(mde(76.0), 4),
                         "forward_5y": round(mde(5.0), 4), "forward_10y": round(mde(10.0), 4)},
       "years_needed_for_2pp": round((k3 * se * math.sqrt(yrs) / 0.02) ** 2, 1),
       "years_needed_for_1pp": round((k3 * se * math.sqrt(yrs) / 0.01) ** 2, 1)}
print(json.dumps(out, indent=1))
