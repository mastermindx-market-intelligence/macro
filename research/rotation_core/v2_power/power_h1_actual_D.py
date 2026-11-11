"""SE of H1's matched-mix contrast per grid point on 1998-2019 from the bootstrap SPREAD only (dispersion of the
resampled statistic about its own mean). The point estimate is never computed into a printed or stored value."""
import sys, json, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.path.insert(0, "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")
from engine import rotation_core_evaluation as rc
from engine import rotation_core_v2 as v2
FR = "/home/ubuntu2/tmp/rotation-core/data/french"
vw, ew = v2.load_french_industries(f"{FR}/le2019/49_Industry_Portfolios_Daily_le20191231.csv", "2019-12-31")
mkt, rf = v2.load_french_market(f"{FR}/x/F-F_Research_Data_Factors_daily.csv", "2019-12-31")
legs = v2.form_legs(vw, mkt); bd = v2.current_leg_breadth(vw, legs); rel = v2.relative_line(legs)
start, end = pd.Timestamp("1998-01-02"), pd.Timestamp("2019-12-31")
k3 = NormalDist().inv_cdf(1 - 0.05 / 3) + NormalDist().inv_cdf(0.8)
out = {}
for h, b in v2.GRID:
    st = v2.h1_states(rel, bd, h, b)
    bk = v2.simulate_states(st, legs, rf, start, end)
    idx = bk.returns.index
    r = bk.returns.values
    W = bk.holdings[["OFF", "DEF", "BASE"]].values; W = np.concatenate([W, 1 - W.sum(1, keepdims=True)], 1)
    L = np.concatenate([legs.returns.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0).values, rf.reindex(idx).fillna(0).values[:, None]], 1)
    dist = []
    for c in range(0, 4000, 1000):
        ii = rc.stationary_bootstrap_indices(len(r), 1000, 21, 20261111 + c)
        dist.append(v2.matched_mix_stat(r[ii], W[ii], L[ii]))
    se = float(np.std(np.concatenate(dist), ddof=1)); yrs = len(r) / 252
    tilt = float(1 - W[:, 2].mean())
    m = lambda y: round(k3 * se * math.sqrt(yrs / y), 4)
    out[f"h{h} b{b}"] = {"time_in_tilt": round(tilt, 3), "D_se_annual": round(se, 4),
                         "mde80_holm_m3": {"pre1998_plus_2020_25": m(76), "2020_25": m(6), "forward_5y": m(5), "forward_10y": m(10)}}
print(json.dumps(out, indent=1))
