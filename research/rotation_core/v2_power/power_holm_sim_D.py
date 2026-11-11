"""Post-freeze check: power of the frozen pooled test simulated under Holm (m=3), from 1998-2019 VARIANCE and
COVARIANCE only (no mean used). Compare with the frozen header's normal-approximation / Bonferroni figures."""
import sys, json, math
import numpy as np, pandas as pd
from statistics import NormalDist
sys.path.insert(0, "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")
from engine import rotation_core_evaluation as rc
from engine import rotation_core_v2 as v2
FR = "/home/ubuntu2/tmp/rotation-core/data/french"
vw, ew = v2.load_french_industries(f"{FR}/le2019/49_Industry_Portfolios_Daily_le20191231.csv", "2019-12-31")
mkt, rf = v2.load_french_market(f"{FR}/x/F-F_Research_Data_Factors_daily.csv", "2019-12-31")
k = vw.index >= "1996-01-02"; vw, mkt, rf = vw[k], mkt[mkt.index >= "1996-01-02"], rf[rf.index >= "1996-01-02"]
legs = v2.form_legs(vw, mkt); bd = v2.current_leg_breadth(vw, legs); rel = v2.relative_line(legs)
S, E = pd.Timestamp("1998-01-02"), pd.Timestamp("2019-12-31")
def series(st, cash_def=False):
    bk = v2.simulate_states(st, legs, rf, S, E, cash_for_defend=cash_def)
    idx = bk.returns.index
    W = bk.holdings[["OFF", "DEF", "BASE"]]; wbar = W.mean(); cb = 1 - wbar.sum()
    mix = (legs.returns.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0) * wbar).sum(axis=1) + cb * rf.reindex(idx).fillna(0)
    return bk.returns, bk.returns - mix
r1, x1 = series(v2.h1_states(rel, bd, 3, 25))
r0, _ = series(v2.h1_states(rel, bd, 3, 25, use_breadth=False))
_, x3 = series(v2.h3_states(legs))
X = np.c_[x1.values, (r1 - r0.reindex(r1.index).fillna(0)).values, x3.reindex(r1.index).fillna(0).values]
X = X - X.mean(axis=0)                          # centred: only dispersion is used
idx = rc.stationary_bootstrap_indices(len(X), 4000, 21, 20261111)
M = np.stack([X[idx][:, :, j].mean(axis=1) * 252 for j in range(3)], axis=1)
C = np.cov(M.T); se = np.sqrt(np.diag(C)); corr = C / np.outer(se, se)
yrsD = len(X) / 252; Y = {"E1": 17.2, "E2": 52.0, "H": 6.0}; Yt = sum(Y.values())
rng = np.random.default_rng(5); n = 200000
def p_one(z): return 1 - np.vectorize(NormalDist().cdf)(z)
out = {"D_se_annual": dict(zip(["H1", "H2", "H3"], np.round(se, 4).tolist())), "corr": np.round(corr, 3).tolist(), "results": {}}
for eff in (0.0218, 0.02, 0.01):
    # per-window draws with the D covariance scaled by years; effect on H1 only (H2, H3 null)
    draws = {w: rng.multivariate_normal([eff, 0, 0], C * yrsD / y, n) for w, y in Y.items()}
    pooled = sum(draws[w] * Y[w] for w in Y) / Yt
    sep = se * math.sqrt(yrsD / Yt)
    z = pooled / sep
    from scipy.stats import norm
    p = norm.sf(z)
    order = np.argsort(p, axis=1); ps = np.take_along_axis(p, order, 1)
    thr = 0.05 / np.array([3, 2, 1])
    ok = ps < thr; stop = np.cumprod(ok, axis=1).astype(bool)
    rej = np.zeros_like(p, dtype=bool); np.put_along_axis(rej, order, stop, 1)
    pre = (draws["E1"] * Y["E1"] + draws["E2"] * Y["E2"]) / (Y["E1"] + Y["E2"])
    signs = (draws["E1"][:, 0] > 0) & (draws["E2"][:, 0] > 0) & (draws["H"][:, 0] > 0) & (pre[:, 0] > 0)
    bonf = norm.sf(z[:, 0]) < 0.05 / 3
    out["results"][f"H1_true_{eff}"] = {"P_H1_rejected_holm_sim": round(float(rej[:, 0].mean()), 3),
                                        "P_H1_rejected_bonferroni": round(float(bonf.mean()), 3),
                                        "P_joint_pass_holm_sim": round(float((rej[:, 0] & signs).mean()), 3),
                                        "P_joint_pass_bonferroni": round(float((bonf & signs).mean()), 3)}
print(json.dumps(out, indent=1))
