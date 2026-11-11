"""Run PRO_RUN_A fixtures against the harness at the CURRENT checkout. Prints observed vs required per finding."""
import sys, json, math
import numpy as np, pandas as pd
ROOT = sys.argv[1]
sys.path.insert(0, ROOT)
from engine import rotation_core_evaluation as rc
from engine import rotation_core_j4 as j4
import scripts.run_rotation_core_v1 as run
out = {}
S = lambda n: pd.bdate_range("2005-01-03", periods=n)

def cell(k, observed, required, confirmed):
    out[k] = {"observed": observed, "required": required, "confirmed": bool(confirmed)}

# A01 stale-mark execution
s = S(5); px = pd.Series([100, np.nan, 120, 120, 120.], index=s)
marked = px.ffill(); r = marked.pct_change().fillna(0).to_frame("SPY")
tgt = pd.DataFrame({"SPY": [1.0, np.nan, np.nan, np.nan, np.nan]}, index=s)
kw = {}
if "avail" in rc.simulate.__code__.co_varnames:
    kw["avail"] = px.notna().to_frame("SPY")
b = rc.simulate(tgt, r, pd.Series(0.0, index=s), 0.0, "a01", **kw)
got = float(np.prod(1 + b.returns) - 1)
cell("A01", round(got, 6), 0.0, abs(got - 0.0) > 1e-9)

# A02 fee base
s = S(4); r = pd.DataFrame({"SPY": [0.0, 0.0, 0.20, 0.0]}, index=s)
tgt = pd.DataFrame({"SPY": [np.nan, np.nan, np.nan, np.nan]}, index=s)
# fully invested from start: decide buy at close0 with 0 cost then sell at close 2 with 5bp
tgt.iloc[0] = 1.0; tgt.iloc[1] = 0.0
b = rc.simulate(tgt, r, pd.Series(0.0, index=s), {"SPY": 5.0}, "a02")
# execution: buy at close1 (cost 5bp on 1.0); sell decided at close1 -> executes close2 after +20% day
day2 = float(b.returns.iloc[2])
cell("A02", round(day2, 6), round(0.20 - 0.0005 * 1.2, 6), abs(day2 - (0.20 - 0.0006)) > 1e-9)

# A12 long-only
s = S(4); r = pd.DataFrame({"SPY": [0.0, 0.0, -0.10, 0.0]}, index=s)
tgt = pd.DataFrame({"SPY": [-0.5, np.nan, np.nan, np.nan]}, index=s)
try:
    b = rc.simulate(tgt, r, pd.Series(0.0, index=s), 0.0, "a12"); cell("A12", round(float(b.returns.iloc[2]), 6), "rejected", True)
except ValueError as e:
    cell("A12", "rejected: " + str(e)[:60], "rejected", False)

# A07 eligibility on filled panel
s = S(300); raw = pd.Series(np.nan, index=s); raw.iloc[:100] = 100.0; raw.iloc[253:] = 100.0
filled_el = rc.eligible(raw.ffill().to_frame("X")).iloc[252, 0]; raw_el = rc.eligible(raw.to_frame("X")).iloc[252, 0]
src = open(f"{ROOT}/scripts/run_rotation_core_v1.py").read()
uses_raw = 'rc.eligible(d["avail"]' in src
cell("A07", {"filled_panel_eligible": bool(filled_el), "raw_eligible": bool(raw_el), "runner_uses_raw": uses_raw}, "raw mask", (not uses_raw) and filled_el != raw_el)

# A04 J4 interior gap
s = S(4); p = pd.Series([100, np.nan, 50, 50.], index=s)
rr = (j4.marked_returns(p.to_frame("X"))["X"] if hasattr(j4, "marked_returns") else p.pct_change(fill_method=None))
got, ended = j4.window_return(rr.iloc[1:])
cell("A04", round(got, 6), -0.5, abs(got + 0.5) > 1e-9)

# A05 temporary final gap read as delisting
s = S(6); p = pd.Series([100, 100, 100, np.nan, 100, 100.], index=s)
win = (j4.marked_returns(p.to_frame("X"))["X"] if hasattr(j4, "marked_returns") else p.pct_change(fill_method=None)).iloc[1:4]
res = j4.window_return(win)
ended = res[1]
if hasattr(j4, "history_ended"):
    ended = j4.history_ended(p, s[3])
cell("A05", {"ended_flag": bool(ended)}, False, bool(ended))

# A03 J4-B fee after return
fee = 0.001; gross = 0.20
old = gross - 1.0 * fee
cell("A03", {"code_formula_net": round(old, 7)}, round((1 + gross) / (1 + fee) - 1, 7),
     "gross - turn * cost_bp" in open(f"{ROOT}/engine/rotation_core_j4.py").read())

# A06 filter before B/coverage
cell("A06", {"filter_line_present": 'df = df[df["delta_i"].notna()]' in src}, "independent masks",
     'df = df[df["delta_i"].notna()]' in src and "cov = df[\"priced_share\"]" in src)

# A08 false-pivot cost endpoints
s = S(100); w = pd.Series(1.0, index=s); w.iloc[20:30] = 0.0   # out after close 20, back after close 30
m = pd.Series(0.0, index=s); m.iloc[30] = 0.20
strat = m * w.shift(1).fillna(1.0)
lvl = (1 + m).cumprod()
pv = rc.pivot_table(w, strat, m, lvl, {})
cost = pv["false_pivot_cost_per_calm_year"] * pv["calm_years"]
cell("A08", round(cost, 6), 0.20, abs(cost - 0.20) > 1e-9)

# A09 tail censoring
s = S(100); w = pd.Series(1.0, index=s); w.iloc[70:] = 0.0
pv = rc.pivot_table(w, w * 0, w * 0, pd.Series(1.0, index=s), {}, sealed_tail=20)
cell("A09", {"false": pv["false_pivots"], "undetermined": pv["spells_undetermined_sealed"]}, {"false": 0, "undetermined": 1},
     pv["false_pivots"] != 0)

# A10 final-close holdings
s = S(3); r = pd.DataFrame({"SPY": [0.0, 0, 0]}, index=s)
tgt = pd.DataFrame({"SPY": [1.0, 0.0, np.nan]}, index=s)
b = rc.simulate(tgt, r, pd.Series(0.0, index=s), 0.0, "a10")
acw = run.after_close_weight(b).tolist()
cell("A10", acw, [0, 1, 0], acw != [0, 1, 0])

# A11 L0 coverage not enforced
from scripts.rotation_core_report import build_artifact
stub = {"jobs": {k: {"gates": {}} for k in ("J1", "J2", "J3")}, "incumbents": {}, "long_history": {}, "dsr_trial_count": {},
        "deviations": [], "data_quality": {"l0_ge_99pct": False}}
stub["jobs"]["J4"] = {"gates": [], "cap": "x"}; stub["jobs"]["J5"] = {}
try:
    art = build_artifact(stub, {"protocol_id": "p", "frozen_on_utc": "d"}, {}, "pin", 1, 1)
    lvl = art["release"]["overall_level"]
except Exception as e:
    lvl = f"error {e}"
cell("A11", lvl, "not plain L0_descriptive when l0_ge_99pct is False", lvl == "L0_descriptive")

# A13 costless splice
cell("A13", {"bond_splice_uncharged": "VFITX" in src and "splice" not in open(f"{ROOT}/engine/rotation_core_evaluation.py").read()}, "charged or registered",
     not any(d for d in getattr(run, "DEVIATIONS", []) if "splice" in d.get("text", "").lower()))

# A14 cash gap -> zero
s = S(12); y = pd.Series([5.0] + [np.nan] * 11, index=s)
c = rc.cash_returns(y, s)
cell("A14", {"zero_days": int((c.iloc[7:] == 0).sum())}, "flagged unavailable", int((c.iloc[7:] == 0).sum()) > 0)

# A15 no J4-B terminal sensitivity
cell("A15", {"has_book_iii": "book_L_net_iii" in open(f"{ROOT}/engine/rotation_core_j4.py").read()}, "B under iii", "book_L_net_iii" not in open(f"{ROOT}/engine/rotation_core_j4.py").read())

# A16 stock files hashed
cell("A16", {"hashes_stock_files": "_hash_bytes(str(p1)" in src or "_hash_bytes(str(pf)" in src}, "hash every consumed file",
     not ("_hash_bytes(str(p1)" in src or "_hash_bytes(str(pf)" in src))

# A17 exclusive first date
cell("A17", {"exclusive_mask": "(s > J1_FIRST)" in src}, "inclusive", "(s > J1_FIRST)" in src)

# A18 nonfinite draws
p = rc.centred_p(np.array([0.0, 0.0, np.nan]), 1.0)
cell("A18", round(p, 4), 0.25, abs(p - 0.25) > 1e-9)

# A19 presentation contract
cell("A19", {"registered": any("presentation" in d.get("text", "") for d in getattr(run, "DEVIATIONS", []))}, "fields or registered narrowing",
     not any("presentation" in d.get("text", "") for d in getattr(run, "DEVIATIONS", [])))
print(json.dumps(out, indent=1, default=str))
