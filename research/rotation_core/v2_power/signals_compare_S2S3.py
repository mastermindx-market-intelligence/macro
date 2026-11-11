"""R16: signals-only comparison on 1998-01-02..2019-12-31, engine at 7dbb7647c2 vs current (S2+S3). States only;
no return is computed."""
import sys, importlib, json
import pandas as pd
def load(root):
    for m in [k for k in list(sys.modules) if k.startswith(("engine", "scripts", "lib"))]:
        del sys.modules[m]
    sys.path.insert(0, root); v2 = importlib.import_module("engine.rotation_core_v2"); sys.path.pop(0); return v2
FR = "/home/ubuntu2/tmp/rotation-core/data/french"
S, E = pd.Timestamp("1998-01-02"), pd.Timestamp("2019-12-31")
states = {}
for tag, root in (("old", "/home/ubuntu2/tmp/rotation-core/repro_7dbb7647c2"), ("new", "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")):
    v2 = load(root)
    vw, _ = v2.load_french_industries(f"{FR}/le2019/49_Industry_Portfolios_Daily_le20191231.csv", "2019-12-31")
    mkt, _ = v2.load_french_market(f"{FR}/x/F-F_Research_Data_Factors_daily.csv", "2019-12-31")
    k = vw.index >= "1996-01-02"; vw, mkt = vw[k], mkt[mkt.index >= "1996-01-02"]
    legs = v2.form_legs(vw, mkt); bd = v2.current_leg_breadth(vw, legs); rel = v2.relative_line(legs)
    d = {}
    for h, b in v2.GRID:
        st1 = v2.h1_states(rel, bd, h, b); st0 = v2.h1_states(rel, bd, h, b, use_breadth=False)
        for nm, st in ((f"H1_h{h:g}_b{b:g}", st1), (f"price_only_h{h:g}_b{b:g}", st0), (f"H1_2x_h{h:g}_b{b:g}", st1),
                       (f"cash_ablation_h{h:g}_b{b:g}", st1)):
            d[nm] = st
    d["H3"] = v2.h3_states(legs)
    states[tag] = {k_: v.loc[S:E] for k_, v in d.items()}
rows = {}
for nm in states["old"]:
    a, b = states["old"][nm], states["new"][nm]
    diff = ~((a == b) | (a.isna() & b.isna()))
    dd = a.index[diff.values]
    rows[nm] = {"sessions_differing": int(diff.sum()), "first": str(dd[0].date()) if len(dd) else None,
                "last": str(dd[-1].date()) if len(dd) else None}
print(json.dumps({"window": ["1998-01-02", "2019-12-31"], "books": 17, "rows": rows,
                  "books_with_any_difference": sum(r["sessions_differing"] > 0 for r in rows.values())}, indent=1))
