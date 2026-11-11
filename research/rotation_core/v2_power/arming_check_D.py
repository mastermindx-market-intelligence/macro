"""v2 point G: fraction of 1998-2019 sessions in the ARMED state, per declared grid point. Signals only:
no strategy, leg-vs-leg or matched-mix return statistic is computed or printed. Inputs truncated at 2019-12-31."""
import numpy as np, pandas as pd, json
P = "/home/ubuntu2/tmp/rotation-core/data/french/le2019/49_Industry_Portfolios_Daily_le20191231.csv"
F = "/home/ubuntu2/tmp/rotation-core/data/french/x/F-F_Research_Data_Factors_daily.csv"
GRID = {"near_high_pct": [3, 5], "breadth_drop_pp_i": [25, 37.5], "narrow_drop_ii": ["bottom 20% of own 6m range"]}

def section(name):
    L = open(P).read().splitlines(); out, cols, on = [], None, False
    for ln in L:
        if name in ln: on = True; continue
        if on and cols is None and ln.startswith(","): cols = [c.strip() for c in ln.split(",")[1:]]; continue
        k = ln.split(",", 1)[0].strip()
        if on and cols and len(k) == 8 and k.isdigit(): out.append(ln.split(","))
        elif on and cols and out and not k: break
    df = pd.DataFrame([r[1:] for r in out], index=pd.to_datetime([r[0] for r in out], format="%Y%m%d"), columns=cols).astype(float)
    return df.where(df > -99.0) / 100.0

vw = section("Average Value Weighted Returns -- Daily"); ew = section("Average Equal Weighted Returns -- Daily")
ff = []
for ln in open(F):
    p = [x.strip() for x in ln.split(",")]
    if len(p[0]) == 8 and p[0].isdigit() and p[0] <= "20191231": ff.append(p)
mkt = pd.Series([float(r[1]) + float(r[4]) for r in ff], index=pd.to_datetime([r[0] for r in ff], format="%Y%m%d")) / 100
vw = vw[vw.index <= "2019-12-31"]; ew = ew[ew.index <= "2019-12-31"]; mkt = mkt.reindex(vw.index)
valid = vw.notna()
nvalid = valid.cumsum()
dropped_days = int((~valid & (nvalid > 0)).sum().sum())
s = vw.index
me = pd.Series(s, index=s).groupby([s.year, s.month]).max().values
# beta on trailing 252 sessions ending t-1, formed at each month-end, using only valid pairs (>= 200)
legs = {}
for t in me:
    if t < pd.Timestamp("1996-06-01"): continue
    i = s.get_loc(t); w = slice(s[max(0, i - 252)], s[i - 1])
    y = vw.loc[w]; x = mkt.loc[w]
    b = {}
    for c in vw.columns:
        ok = y[c].notna() & x.notna()
        if ok.sum() >= 200 and nvalid[c].iloc[i - 1] >= 252:
            b[c] = np.cov(y[c][ok], x[ok])[0, 1] / np.var(x[ok], ddof=1)
    b = pd.Series(b).sort_values()
    k = len(b) // 3
    legs[t] = (list(b.index[-k:]), list(b.index[:k]))
ms = pd.Series(pd.DatetimeIndex(sorted(legs)))
def leg_on(d):
    j = ms.searchsorted(d, side="left") - 1      # legs formed at a month-end strictly before d
    return legs[ms.iloc[j]] if j >= 0 else (None, None)
days = s[(s >= "1997-01-02")]
lvl = (1 + vw.fillna(0)).cumprod()                   # per-industry level; a missing day contributes no move
sma50 = lvl.rolling(50, min_periods=50).mean()
off_r, def_r, br_i, nar = [], [], [], []
ew60 = (1 + ew.fillna(0)).rolling(60).apply(np.prod, raw=True) - 1
vw60 = (1 + vw.fillna(0)).rolling(60).apply(np.prod, raw=True) - 1
for d in days:
    o, df_ = leg_on(d)
    if o is None: off_r.append(np.nan); def_r.append(np.nan); br_i.append(np.nan); nar.append(np.nan); continue
    vo = [c for c in o if valid.at[d, c]]; vd = [c for c in df_ if valid.at[d, c]]
    off_r.append(vw.loc[d, vo].mean()); def_r.append(vw.loc[d, vd].mean())
    br_i.append(float((lvl.loc[d, vo] > sma50.loc[d, vo]).mean()))
    nar.append(float((ew60.loc[d, vo] - vw60.loc[d, vo]).mean()))
X = pd.DataFrame({"o": off_r, "d": def_r, "bi": br_i, "nar": nar}, index=days)
rel = ((1 + X.o).cumprod() / (1 + X.d).cumprod())
Dm = (X.index >= "1998-01-02") & (X.index <= "2019-12-31")
hi = rel.rolling(126).max(); bmax = X.bi.rolling(126).max()
nlo, nhi = X.nar.rolling(126).min(), X.nar.rolling(126).max()
out = {"dropped_industry_days_le2019": dropped_days, "leg_size_example": {str(pd.Timestamp(k).date()): [len(v[0]), len(v[1])] for k, v in list(legs.items())[::60]},
       "breadth_i_granularity": "1/n_offence_members (about 1/16 = 6.25 pp); grid steps are multiples: 25 pp = 4 steps, 37.5 pp = 6 steps"}
for nh in GRID["near_high_pct"]:
    near = rel >= (1 - nh / 100) * hi
    for bd in GRID["breadth_drop_pp_i"]:
        armed = near & (X.bi <= bmax - bd / 100 + 1e-9)
        out[f"armed_frac_D near{nh}% breadth_i_drop{bd}pp"] = round(float(armed[Dm].mean()), 4)
    armed2 = near & (X.nar <= nlo + 0.2 * (nhi - nlo))
    out[f"armed_frac_D near{nh}% narrow_ii_bottom20%"] = round(float(armed2[Dm].mean()), 4)
    out[f"near_high_alone_frac_D near{nh}%"] = round(float(near[Dm].mean()), 4)
print(json.dumps(out, indent=1))
