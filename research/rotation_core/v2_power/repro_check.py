"""R15.3 / R18.5 reproduction check on 1998-2019: states and daily returns, old engine (1ca5228b3c) vs current."""
import sys, importlib, json
import numpy as np, pandas as pd
def load(root):
    for m in [k for k in list(sys.modules) if k.startswith(("engine", "scripts", "lib"))]:
        del sys.modules[m]
    sys.path.insert(0, root)
    v2 = importlib.import_module("engine.rotation_core_v2")
    sys.path.pop(0)
    return v2
FR = "/home/ubuntu2/tmp/rotation-core/data/french"
out = {}
res = {}
for tag, root in (("old", "/home/ubuntu2/tmp/rotation-core/repro_1ca5228b3c"), ("new", "/home/ubuntu2/.t3/worktrees/Macro/rotation-core")):
    v2 = load(root)
    vw, ew = v2.load_french_industries(f"{FR}/le2019/49_Industry_Portfolios_Daily_le20191231.csv", "2019-12-31")
    mkt, rf = v2.load_french_market(f"{FR}/x/F-F_Research_Data_Factors_daily.csv", "2019-12-31")
    k = vw.index >= "1996-01-02"; vw, mkt, rf = vw[k], mkt[mkt.index >= "1996-01-02"], rf[rf.index >= "1996-01-02"]
    legs = v2.form_legs(vw, mkt); bd = v2.current_leg_breadth(vw, legs); rel = v2.relative_line(legs)
    S, E = pd.Timestamp("1998-01-02"), pd.Timestamp("2019-12-31")
    books = {}
    for h, b in v2.GRID:
        st1 = v2.h1_states(rel, bd, h, b); st0 = v2.h1_states(rel, bd, h, b, use_breadth=False)
        for nm, st, kw in ((f"H1_{h}_{b}", st1, {}), (f"PO_{h}_{b}", st0, {}), (f"H1x2_{h}_{b}", st1, {"fee_bp": 20.0}),
                           (f"CASH_{h}_{b}", st1, {"cash_for_defend": True})):
            books[nm] = (st, v2.simulate_states(st, legs, rf, S, E, **kw).returns)
    st3 = v2.h3_states(legs); books["H3"] = (st3, v2.simulate_states(st3, legs, rf, S, E).returns)
    res[tag] = books
maxd, sc_eq, wu = 0.0, True, {}
for nm in res["old"]:
    so, ro = res["old"][nm]; sn, rn = res["new"][nm]
    sc = so.index >= S                                         # scored sessions: 1998-01-02 onward
    sc_eq &= so[sc].equals(sn[so.index[sc]])
    w = so.index[~sc]
    diff = w[(so[w].fillna(-1) != sn[w].fillna(-1)).values]
    if len(diff):
        new_vals = set(sn[diff].fillna(-1))
        assert new_vals <= ({-1} if nm == "H3" else {0}), "a warm-up difference other than S2's"
        wu[nm] = diff
    maxd = max(maxd, float((ro - rn.reindex(ro.index)).abs().max()))
print(json.dumps({"books": len(res["old"]), "scored_sessions_1998_2019_states_identical": bool(sc_eq),
                  "max_abs_daily_return_diff": maxd}))
def span(keys):
    d = sorted(set().union(*[wu[k] for k in keys])) if keys else []
    return {"books": len(keys), "sessions_max_per_book": max((len(wu[k]) for k in keys), default=0),
            "first": str(d[0].date()) if d else None, "last": str(d[-1].date()) if d else None}
print(json.dumps({"warmup_sessions_before_1998_changed_by_S2": {
    "H1_family_now_NEUTRAL": span([k for k in wu if k != "H3"]),
    "H3_now_no_state": span([k for k in wu if k == "H3"])}}))
