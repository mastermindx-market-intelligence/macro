"""v2 draft power (revision 1): SE of the beta-matched H1 contrast on D only. Point estimate NOT printed."""
import sys, math
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")
import scripts.run_rotation_core_v1 as run
from engine import rotation_core_evaluation as rc

d = run.load(rc.D_END)
s, cash, r = d["sessions"], d["cash"], d["rets"][rc.SECTORS]
T = rc.trend_broken(d["gspc_full"]).reindex(s)
el = rc.eligible(d["adj"][rc.SECTORS])
on = r.where(el).mean(axis=1)
de = r[rc.DEFENSIVE_TRIO].mean(axis=1)
state = T.shift(1)                       # state held on day t was decided at close t-1 (execution lag ignored for SE)
cov = de.rolling(252, min_periods=200).cov(on).shift(1)
var = on.rolling(252, min_periods=200).var().shift(1)
beta = (cov / var).clip(0, 1.5)
ref_off = beta * on + (1 - beta) * cash
diff = (de - ref_off).where(state == 1, 0.0)     # risk-on days: both hold the risk-on leg
mask = (s > run.J2_FIRST) & (s <= rc.D_END) & diff.notna().values
x = diff[mask].values
dist = rc.bootstrap_stat([x, np.zeros_like(x)], rc.stat_mean_diff, 10000, 21, 20261111)
yrs = mask.sum() / 252
print({"stat": "beta-matched H1 contrast, D-only SE (annualised x252); point estimate not printed",
       "se": float(np.std(dist, ddof=1)), "n_sessions": int(mask.sum()), "years": round(yrs, 2),
       "share_riskoff": float((state[mask] == 1).mean())})
