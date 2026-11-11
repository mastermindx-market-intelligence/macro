"""v2 draft power line for H1, from D-sample contrast variance ONLY. Prints SE/MDE, never the point estimate."""
import sys, math
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")
import scripts.run_rotation_core_v1 as run
from engine import rotation_core_evaluation as rc

d = run.load(rc.D_END)
s, cash = d["sessions"], d["cash"]
T = rc.trend_broken(d["gspc_full"]).reindex(s)
el = rc.eligible(d["adj"][rc.SECTORS])
cols = rc.SECTORS
start = run.J2_FIRST
me = set(rc.month_end_sessions(s))
tgt = pd.DataFrame(np.nan, index=s, columns=cols)
prev = None
for t in s[s >= start]:
    st = T[t]
    if np.isnan(st):
        continue
    if st != prev or t in me:
        e = [x for x in cols if bool(el.at[t, x])]
        w = {x: 1 / 3 for x in rc.DEFENSIVE_TRIO} if st == 1 else {x: 1 / len(e) for x in e}
        tgt.loc[t] = [w.get(x, 0.0) for x in cols]
    prev = st
book = rc.simulate(tgt, d["rets"][cols], cash, 5.0, "H1", start=start, equity_cols=cols, always_rebalance=True)
r = d["rets"][cols]
on = r.where(el).mean(axis=1)            # equal-weight eligible sectors
df = r[rc.DEFENSIVE_TRIO].mean(axis=1)
idx = book.returns.index
mask = (idx > start) & (idx <= rc.D_END)
held = book.holdings[cols].reindex(idx)
riskon_w = 1.0 - held[rc.DEFENSIVE_TRIO].sum(axis=1).where(held.sum(axis=1) > 0)   # 0 when in defensive leg
st_on = (held[rc.DEFENSIVE_TRIO].sum(axis=1) < 0.99).astype(float)
wbar = float(st_on[mask].mean())
ref = (wbar * on + (1 - wbar) * df).reindex(idx)
a, b = book.returns[mask].values, ref[mask].fillna(0).values
dist = rc.bootstrap_stat([a, b], rc.stat_mean_diff, 10000, 21, 20261110)
se = float(np.std(dist, ddof=1))
nD = int(mask.sum())
te = float((a - b).std(ddof=1) * math.sqrt(252))
print({"stat": "H1 D-sample SE of annualised contrast (point estimate deliberately not printed)", "se": se,
       "tracking_error": te, "n_D_sessions": nD, "riskon_share_D": wbar})
