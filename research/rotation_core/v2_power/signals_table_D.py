"""v2 signals-only table under R12 (trough clock + relative-line-near-low qualification), 1998-2019.
States and counts only: no return, mean or point estimate. Run once."""
import sys, json
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")
from engine import rotation_core_v2 as v2
FR = "/home/ubuntu2/tmp/rotation-core/data/french"
vw, ew = v2.load_french_industries(f"{FR}/le2019/49_Industry_Portfolios_Daily_le20191231.csv", "2019-12-31")
mkt, rf = v2.load_french_market(f"{FR}/x/F-F_Research_Data_Factors_daily.csv", "2019-12-31")
legs = v2.form_legs(vw, mkt)
bd = v2.current_leg_breadth(vw, legs)
rel = v2.relative_line(legs)
D = (rel.index >= "1998-01-02") & (rel.index <= "2019-12-31")
first = rel.index[D][0]
yrs = D.sum() / 252

def spells(x, v):
    runs, n = [], 0
    for a in x:
        if a == v: n += 1
        elif n: runs.append(n); n = 0
    if n: runs.append(n)
    return runs

rl, fl = bd["wash_run_prev"][D], bd["wash_from_low"][D]
rec = rl.notna() & (rl > 0)
L, F = rl[rec].astype(int), fl[rec].astype(int)
out = {"D_sessions": int(D.sum()), "D_years": round(yrs, 2),
       "washout_spells_1998_2019": {"spells": int(rec.sum()), "length_median": int(L.median()), "length_longest": int(L.max()),
                                    "length_over_20": int((L > 20).sum()), "low_to_recovery_median": int(F.median()),
                                    "low_to_recovery_longest": int(F.max()), "within_20_of_low": int((F <= 20).sum())},
       "grid": {}}
pre_rel = rel[rel.index < first]; pre_bd = {k: x[x.index < first] for k, x in bd.items()}
for h, b in v2.GRID:
    for ub, tag in ((True, "H1"), (False, "price_only")):
        st, log = v2.h1_states(rel, bd, h, b, use_breadth=ub, return_log=True)
        _, log0 = v2.h1_states(pre_rel, pre_bd, h, b, use_breadth=ub, return_log=True)
        armed = pd.Series(log["armed"], index=rel.index)
        x = st[D].dropna().astype(int).values
        ent = lambda v: int(((x[1:] == v) & (x[:-1] != v)).sum() + (x[0] == v))
        dlt = lambda k: log[k] - log0[k]
        row = {"armed_share_no_memory": round(float(armed[D].mean()), 4),
               "armed_share_with_21_memory": round(float((armed.astype(float).rolling(22, min_periods=1).max() > 0)[D].mean()), 4),
               "DEFEND_entries_per_year": round(ent(1) / yrs, 2), "ATTACK_entries_per_year": round(ent(2) / yrs, 2),
               "share": {k: round(float((x == v).mean()), 3) for k, v in (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))},
               "spell_median_longest": {k: ([int(np.median(spells(x, v))), int(max(spells(x, v)))] if spells(x, v) else None)
                                        for k, v in (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))},
               "washout_spells": dlt("wash_spells"), "spells_qualifying": dlt("wash_qualified"),
               "attack_confirms": dlt("wash_fired"), "attack_confirms_per_year": round(dlt("wash_fired") / yrs, 2),
               "same_day_conflicts": dlt("conflicts"),
               "exit_reasons": {k: log["exit"][k] - log0["exit"][k] for k in log["exit"]}}
        out["grid"][f"{tag} h{h} b{b}"] = row
print(json.dumps(out, indent=1))
