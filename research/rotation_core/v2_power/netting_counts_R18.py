"""R18.1: size of the leg-level vs netted re-formation charge on the matched mix, 1998-2019, signals only.

No return is computed or printed. Mix weights are the book's time shares of its target legs (held from the session
after each decision); traded weight per formation = leg-level sum_k wbar_k * 2 * replaced_k (as charged) vs the
industry-level netted sum_i |w_new_i - w_old_i| with w_i = sum_k wbar_k * 1[i in k] / |k|.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
from engine import rotation_core_v2 as v2  # noqa: E402

FR = "/home/ubuntu2/tmp/rotation-core/data/french"
vw, _ = v2.load_french_industries(f"{FR}/le2019/49_Industry_Portfolios_Daily_le20191231.csv", "2019-12-31")
mkt, rf = v2.load_french_market(f"{FR}/x/F-F_Research_Data_Factors_daily.csv", "2019-12-31")
k = vw.index >= "1996-01-02"; vw, mkt = vw[k], mkt[mkt.index >= "1996-01-02"]
legs = v2.form_legs(vw, mkt); bd = v2.current_leg_breadth(vw, legs); rel = v2.relative_line(legs)
S, E = pd.Timestamp("1998-01-02"), pd.Timestamp("2019-12-31")
keys = [t for t in sorted(legs.formed) if S - pd.offsets.MonthEnd(1) <= t <= E]
years = ((vw.index >= S) & (vw.index <= E)).sum() / 252
h, b = v2.SELECTED_REF
books = {"H1_h3_b25": v2.h1_states(rel, bd, h, b), "price_only_h3_b25": v2.h1_states(rel, bd, h, b, use_breadth=False),
         "H3": v2.h3_states(legs)}
print(f"formations in window: {len(keys)}; years: {years:.2f}")
for name, st in books.items():
    T = v2.targets_from_states(st).shift(1).loc[S:E].fillna(0)
    wbar = T.mean()
    n_more = n_less = 0; d_sum = 0.0; leg_sum = 0.0; net_sum = 0.0; moved_between = 0; base_changed = 0
    for j in range(1, len(keys)):
        old, new = legs.formed[keys[j - 1]], legs.formed[keys[j]]
        if new[2] != old[2] and set(new[2]) != set(old[2]):
            base_changed += 1
        if (set(new[0]) & set(old[1])) or (set(new[1]) & set(old[0])):
            moved_between += 1
        leg = sum(wbar[c] * 2 * len(set(n_) - set(o_)) / len(n_) for c, n_, o_ in zip(["OFF", "DEF", "BASE"], new, old))
        def wi(f):
            w = {}
            for c, mem in zip(["OFF", "DEF", "BASE"], f):
                for i in mem:
                    w[i] = w.get(i, 0.0) + wbar[c] / len(mem)
            return w
        wo, wn = wi(old), wi(new)
        net = sum(abs(wn.get(i, 0) - wo.get(i, 0)) for i in set(wo) | set(wn))
        leg_sum += leg; net_sum += net; d_sum += leg - net
        n_more += leg - net > 1e-12; n_less += net - leg > 1e-12
    print(f"{name}: wbar OFF/DEF/BASE {wbar['OFF']:.3f}/{wbar['DEF']:.3f}/{wbar['BASE']:.3f}; "
          f"months leg-level > netted: {n_more}; months leg-level < netted: {n_less}; "
          f"months with a member moving OFF<->DEF: {moved_between}; months with base membership change: {base_changed}; "
          f"traded weight/yr leg-level {leg_sum / years:.4f}, netted {net_sum / years:.4f}, difference {d_sum / years:.4f}")
