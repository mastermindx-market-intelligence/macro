"""v2 rev 4 signals-only table, 1998-2019. States and counts only: no return, mean or point estimate."""
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
yrs = D.sum() / 252

def spells(x, v):
    runs, n = [], 0
    for a in x:
        if a == v: n += 1
        elif n: runs.append(n); n = 0
    if n: runs.append(n)
    return runs

out = {"D_sessions": int(D.sum()), "D_years": round(yrs, 2),
       "breadth_step_pp": {"from_1970": round(100 / 16, 2), "before_1970_approx": "7-8 (13-14 offence members)",
                           "n_offence_members_D_min_max": [int(bd["n_members"][D].min()), int(bd["n_members"][D].max())]},
       "grid": {}}
for h, b in v2.GRID:
    for ub, tag in ((True, "H1"), (False, "price_only")):
        st, log = v2.h1_states(rel, bd, h, b, use_breadth=ub, return_log=True)
        armed_nomem = pd.Series(log["armed"], index=rel.index)
        x = st[D].dropna().astype(int).values
        ent = lambda v: int(((x[1:] == v) & (x[:-1] != v)).sum() + (x[0] == v))
        row = {"armed_share_no_memory": round(float(armed_nomem[D].mean()), 4),
               "armed_share_with_21_memory": round(float((armed_nomem.astype(float).rolling(22, min_periods=1).max() > 0)[D].mean()), 4),
               "DEFEND_entries_per_year": round(ent(1) / yrs, 2), "ATTACK_entries_per_year": round(ent(2) / yrs, 2),
               "share": {k: round(float((x == v).mean()), 3) for k, v in (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))},
               "spell_median_longest": {k: ([int(np.median(spells(x, v))), int(max(spells(x, v)))] if spells(x, v) else None)
                                        for k, v in (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))}}
        row["washout_fired_all_years"] = log["wash_fired"]; row["washout_expired_all_years"] = log["wash_expired"]
        row["same_day_conflicts_all_years"] = log["conflicts"]
        out["grid"][f"{tag} h{h} b{b}"] = row
# item (d): washout spells ending (recovering) inside 1998-2019, on current-leg breadth (identical for all grid points
# and both arms: breadth and legs do not depend on h, b or the arming key)
rl, fl = bd["wash_run_prev"][D], bd["wash_from_low"][D]
rec = rl.notna() & (rl > 0)
L, F = rl[rec].astype(int), fl[rec].astype(int)
out["washout_spells_1998_2019"] = {"spells": int(rec.sum()), "length_median": int(L.median()), "length_longest": int(L.max()),
    "length_over_20": int((L > 20).sum()), "sessions_low_to_recovery_median": int(F.median()),
    "sessions_low_to_recovery_longest": int(F.max()), "fire_attack_confirm": int((F <= 20).sum()),
    "do_not_fire": int((F > 20).sum())}
first = rel.index[D][0]
for h, b in v2.GRID:
    for ub, tag in ((True, "H1"), (False, "price_only")):
        _, log = v2.h1_states(rel, bd, h, b, use_breadth=ub, return_log=True)
        _, log0 = v2.h1_states(rel[rel.index < first], {k: x[x.index < first] for k, x in bd.items()}, h, b,
                               use_breadth=ub, return_log=True)
        r = out["grid"][f"{tag} h{h} b{b}"]
        r["same_day_conflicts_D"] = log["conflicts"] - log0["conflicts"]
        for k in ("washout_fired_all_years", "washout_expired_all_years", "same_day_conflicts_all_years"):
            r.pop(k, None)
print(json.dumps(out, indent=1))
