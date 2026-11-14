"""Extends defect_mass_published: the any-session side of the pivot placebo table, and its HY row on
the HY input in force when that table was generated (inputs.py before bb856951), proven by
reproducing the published HY figures first. Placement mass only; no outcome joined.
Usage: defect_mass_published_v2.py <pre_bb856951_inputs.py> <pre_repair_pivots.py> <unlagged_states.parquet>"""
import sys, json, importlib.util
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE)]
sys.argv, args = sys.argv[:1] + ["/dev/null", "/dev/null"], sys.argv[1:]
from engine.risk_radar_eval import labels as L, pivots as P
src = (HERE / "defect_mass_published.py").read_text().split("px = L.spy_total_return()")[0]
ns = {"__file__": str(HERE / "defect_mass_published.py")}; exec(src, ns); old_mass = ns["old_mass"]

def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s)
    sys.modules[name] = m; s.loader.exec_module(m); return m
I_old = load("inputs_pre_bb856951", args[0]); P_old = load("pivots_pre_repair", args[1])
px = L.spy_total_return(); CUT = pd.Timestamp("2026-11-10"); LOUD = {"elevated", "risk-off"}
idx = px.index[(px.index >= pd.Timestamp("2020-01-02")) & (px.index <= CUT)]
fl_old = I_old.baseline_flags(I_old.baseline_scores()).reindex(idx).fillna(False)
st0 = pd.read_parquet(args[2])["state"].reindex(idx).ffill()
e5 = [e for e in L.drawdown_episodes(px.loc[:CUT], 0.05, outcomes_through=CUT) if e.peak >= idx[0]]
pub = json.loads((ROOT / "research/risk_radar/walkforward/PIVOT_PLACEBO_INSAMPLE_v2.json").read_text())
hy = fl_old["hy_oas_chg21_top_decile"].astype(bool)
repro = {}
for near in (None, "high", "low"):
    r = P_old.placebo(hy, px=px, turns=P.turns_from_episodes(e5), episodes=e5, outcomes_through=CUT,
                      near=near, n_draws=300, seen_history_ok=True)
    k = f"hy_oas_top_decile|{near}"
    repro[k] = all(r[s].get(q) == pub[k][s].get(q) for s in ("top", "bottom")
                   for q in ("placebo_mean", "placebo_p90") if pub[k][s].get(q) is not None)
out = {"hy_pre_bb856951_reproduces_published": repro}
ser = {"pivot radar_loud": st0.isin(LOUD), "pivot hy (pre-bb856951 input)": hy,
       "pivot vix_ge_20": fl_old["vix_ge_20"].astype(bool), "pivot spy_below_200": fl_old["spy_below_200"].astype(bool)}
for k, a in ser.items():
    for near in ([None, "high", "low"] if "hy" in k else [None]):
        out[f"{k}|{near}"] = old_mass(a, px, near, 300)
print(json.dumps(out, indent=1))
