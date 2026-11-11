"""Rotation Core v2 confirmatory runner (corrected engine).

  python scripts/run_rotation_core_v2.py --dry-run     # 1998-2019 only, end to end, prints STRUCTURE only
  python scripts/run_rotation_core_v2.py --stage select   # after freeze: 1998-2019 grid selection (not before)
  python scripts/run_rotation_core_v2.py --stage confirm  # after the parent's HOLDOUT_RELEASE_v2.json only

The dry run builds legs, breadth, every H1 grid point, H2 controls, H3 and the cash ablation, simulates every book
and runs the matched-mix bootstrap machinery on a 50-draw shake-out, but prints and writes no return, contrast or
selection result. Any path under sealed_post2019/ or window end after 2019-12-31 is refused without the release.
"""
from __future__ import annotations

import argparse, hashlib, sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import rotation_core_evaluation as rc  # noqa: E402
from engine import rotation_core_v2 as v2  # noqa: E402

FR = Path("/home/ubuntu2/tmp/rotation-core/data/french")
IND_D = FR / "le2019/49_Industry_Portfolios_Daily_le20191231.csv"
IND_FULL = FR / "sealed_post2019/49_Industry_Portfolios_Daily.csv"
FACT = FR / "x/F-F_Research_Data_Factors_daily.csv"
FROZEN = ROOT / "research/rotation_core/protocol_header_v2.json"


def pipeline(end, ind_path, quiet=True, bootstrap_B=50):
    vw, ew = v2.load_french_industries(ind_path, end)
    mkt, rf = v2.load_french_market(FACT, end)
    legs = v2.form_legs(vw, mkt)
    bd = v2.current_leg_breadth(vw, legs)
    rel = v2.relative_line(legs)
    start, stop = pd.Timestamp("1998-01-02"), pd.Timestamp(end)
    books, structure = {}, {}
    for h, b in v2.GRID:
        for ub, tag in ((True, "H1"), (False, "H2ctl")):
            st = v2.h1_states(rel, bd, h, b, use_breadth=ub)
            bk = v2.simulate_states(st, legs, rf, start, stop, name=f"{tag}_h{h}_b{b}")
            books[bk.name] = bk
            sd = st.loc[start:stop]
            structure[bk.name] = {"decided_sessions": int(sd.notna().sum()),
                                  "state_share": {k: round(float((sd == v).mean()), 3) for k, v in
                                                  (("neutral", 0), ("defend", 1), ("attack", 2))},
                                  "executions": int((bk.traded > 0).sum()), "deferred": bk.meta["deferred_executions"]}
        st = v2.h1_states(rel, bd, h, b)
        bk = v2.simulate_states(st, legs, rf, start, stop, cash_for_defend=True, name=f"H1cash_h{h}_b{b}")
        books[bk.name] = bk
        structure[bk.name] = {"executions": int((bk.traded > 0).sum())}
    st3 = v2.h3_states(legs)
    books["H3"] = v2.simulate_states(st3, legs, rf, start, stop, name="H3")
    structure["H3"] = {"executions": int((books["H3"].traded > 0).sum())}
    mask = pd.Series(True, index=books["H3"].returns.index)
    for k, bk in books.items():                     # exercise the bootstrap; results are discarded unprinted
        res = v2.matched_contrast(bk, legs.returns, rf, mask, B=bootstrap_B)
        assert res["finite_draws"] == bootstrap_B and res["n"] > 5000, k
    return {"sessions": int(len(vw)), "first": str(vw.index[0].date()), "last": str(vw.index[-1].date()),
            "legs_formed": len(legs.formed), "leg_sizes_last": [len(x) for x in legs.formed[max(legs.formed)]],
            "dropped_industry_days": legs.dropped_industry_days, "books": len(books), "structure": structure}


WARMUP_FROM = pd.Timestamp("1996-01-02")      # signal warm-up only (beta 252 + look-back 126); no statistic uses it
SEL_START, SEL_END = pd.Timestamp("1998-01-02"), pd.Timestamp("2019-12-31")
YAHOO = Path("/home/ubuntu2/tmp/rotation-core/data/yahoo")
OUT_J = ROOT / "research/rotation_core/results_v2_selection.json"
OUT_M = ROOT / "research/rotation_core/RESULTS_V2_SELECTION.md"


def _yahoo_tr(t, end=None):
    x = v2.load_yahoo_tr(YAHOO / f"{t}.parquet", SEL_END if end is None else end)   # F1: filtered before any frame
    x = x[x.index >= WARMUP_FROM]
    return x.pct_change(fill_method=None)


def held_risk_on(bk) -> pd.Series:
    """F3: 1 - (defensive or cash weight HELD after each close); a DEFEND decided at t shows from the t+1 close."""
    ph = bk.post_holdings
    return 1.0 - (ph["DEF"] + (1.0 - ph[["OFF", "DEF", "BASE"]].sum(axis=1))).clip(0, 1)


def _ann(x):
    return float((1 + x).prod() ** (252 / len(x)) - 1)


def _mdd(x):
    v = (1 + x).cumprod(); return float((v / v.cummax() - 1).min())


def _diff_stat(a, b, seed, B_=10_000):
    from engine import rotation_core_evaluation as rc
    a, b = np.asarray(a), np.asarray(b)
    obs = float((a - b).mean() * 252)
    dist = rc.bootstrap_stat([a, b], rc.stat_mean_diff, B_, 21, seed)
    return {"ann": obs, "ci95": rc.ci95(dist), "p_one_sided_centred": rc.centred_p(dist, obs)}


def _superseded_2x(setting: str):
    """R18.3: the 2x rows of 1ca5228b3c (switches at 20 bp, re-formation left at 10 bp, mix on net legs), shown old
    beside new as a correction."""
    import json
    p = ROOT / "research/rotation_core/results_v2_selection.json"
    if not p.exists():
        return None
    x = json.loads(p.read_text())["settings"].get(setting, {}).get("H1_at_2x_costs")
    return None if x is None else dict(x, definition="superseded (1ca5228b3c): 20 bp on switches only; re-formation "
                                                      "at 10 bp inside the legs; mix on the same net legs")


BOOKS: dict = {}
STATES: dict = {}


def run_selection():
    from engine import rotation_core_evaluation as rc
    import scripts.run_rotation_core_v1 as v1
    vw, ew = v2.load_french_industries(IND_D, SEL_END)
    mkt, rf = v2.load_french_market(FACT, SEL_END)
    keep = vw.index >= WARMUP_FROM
    vw, ew, mkt, rf = vw[keep], ew[keep], mkt[mkt.index >= WARMUP_FROM], rf[rf.index >= WARMUP_FROM]
    legs = v2.form_legs(vw, mkt)
    bd = v2.current_leg_breadth(vw, legs)
    rel = v2.relative_line(legs)
    s = vw.index; m = (s >= SEL_START) & (s <= SEL_END)
    mask = pd.Series(m, index=s)
    spy, rsp = _yahoo_tr("SPY").reindex(s), _yahoo_tr("RSP").reindex(s)
    elig_ew = ew.where(vw.notna().cumsum() >= 252)
    ew_proxy = elig_ew.mean(axis=1)
    rsp_line = rsp.where(rsp.index >= pd.Timestamp("2003-05-02"), ew_proxy)
    base = legs.returns["BASE"]
    level = (1 + mkt.reindex(s).fillna(0)).cumprod()
    eps = {}
    for name, (a, b2, c) in v1.DPEAK.items():
        ep = rc.find_episode(level[m], a, b2, c)
        if ep:
            eps[name] = ep

    def book_and_stats(st, tag, fee=10.0, cash_def=False, seed=0, base_reading="eq", strict=False):
        # R18: strict = book at `fee` on switches and on re-formation of what it holds; mix on gross legs
        LR = v2.base_view(legs.returns, base_reading, "gross" if strict else "net")
        bk = v2.simulate_states(st, legs, rf, SEL_START, SEL_END, cash_for_defend=cash_def, fee_bp=fee, name=tag,
                                base=base_reading, strict=strict)
        BOOKS[tag] = bk
        idx = bk.returns.index
        mm = pd.Series(True, index=idx)
        mc = v2.matched_contrast(bk, LR, rf, mm, B=10_000, seed=20261111 + seed)
        r = bk.returns
        W = bk.holdings[["OFF", "DEF", "BASE"]]
        wbar = W.mean(); cashbar = 1 - wbar.sum()
        mix = (LR.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0) * wbar).sum(axis=1) + cashbar * rf.reindex(idx).fillna(0)
        yrs = len(r) / 252
        pv = rc.pivot_table(held_risk_on(bk), r, mkt.reindex(idx).fillna(0), level.reindex(idx), eps)
        return bk, {
            "vs_matched_mix": mc,
            "vs_SPY": _diff_stat(r.values, spy.reindex(idx).fillna(0).values, 20261111 + 100 + seed),
            "vs_RSP_or_stated_EW_proxy_before_2003_05": _diff_stat(r.values, rsp_line.reindex(idx).fillna(0).values, 20261111 + 200 + seed),
            "vs_BASE_equal_weight_industries": _diff_stat(r.values, LR["BASE"].reindex(idx).fillna(0).values, 20261111 + 300 + seed),
            "CAGR": _ann(r), "CAGR_matched_mix": _ann(mix), "CAGR_SPY": _ann(spy.reindex(idx).fillna(0)),
            "CAGR_BASE": _ann(base.reindex(idx).fillna(0)),
            "max_drawdown": _mdd(r), "max_drawdown_matched_mix": _mdd(mix),
            "matched_mix_weights": {**{k: round(float(v), 4) for k, v in wbar.items()}, "cash": round(float(cashbar), 4)},
            "turnover_one_way_per_year": float(bk.traded.sum() / yrs / 2), "costs_per_year": float(bk.costs.sum() / yrs),
            "deferred_executions": bk.meta["deferred_executions"],
            "false_DEFEND_calls_per_calm_year": pv["false_pivots_per_calm_year"],
            "false_DEFEND_cost_per_calm_year": pv["false_pivot_cost_per_calm_year"],
            "share": {k: round(float((st.reindex(idx) == v).mean()), 3) for k, v in (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))}}

    res = {"label": "SELECTION WINDOW 1998-01-02..2019-12-31 (previously examined; disclosed). Not evidence.",
           "header_sha256": v2.FROZEN_V2_SHA256, "warmup_note": "closes from 1996-01-02 used only as signal warm-up "
           "(252-session beta, 126-session look-backs); no statistic computed on dates before 1998-01-02",
           "episodes": {k: {"peak": str(v["peak"].date()), "trough": str(v["trough"].date())} for k, v in eps.items()},
           "dropped_industry_days": legs.dropped_industry_days, "settings": {}}
    for i, (h, b) in enumerate(v2.GRID):
        st1 = v2.h1_states(rel, bd, h, b); st0 = v2.h1_states(rel, bd, h, b, use_breadth=False)
        STATES[f"H1_h{h}_b{b}"], STATES[f"price_only_h{h}_b{b}"] = st1, st0
        bk1, s1 = book_and_stats(st1, f"H1_h{h}_b{b}", seed=10 * i)
        bk0, s0 = book_and_stats(st0, f"H1_price_only_h{h}_b{b}", seed=10 * i + 1)
        _, s1x = book_and_stats(st1, f"H1_2x_h{h}_b{b}", fee=20.0, seed=10 * i + 2, strict=True)
        bkc, sc = book_and_stats(st1, f"H1_cash_ablation_h{h}_b{b}", cash_def=True, seed=10 * i + 3)
        idx = bk1.returns.index
        h2 = _diff_stat(bk1.returns.values, bk0.returns.reindex(idx).fillna(0).values, 20261111 + 500 + i)
        prev2x = _superseded_2x(f"h{h}_b{b}")
        res["settings"][f"h{h}_b{b}"] = {"H1": s1, "H1_at_2x_costs": {"vs_matched_mix": s1x["vs_matched_mix"],
                                          "costs_per_year": s1x["costs_per_year"],
                                          "definition": "R18 strict run: 20 bp on switches and on re-formation of "
                                                        "the held leg; matched mix on gross legs (pays nothing)"},
                                          "H1_at_2x_costs_before_R18_superseded": prev2x,
                                          "price_only_control": s0, "H2_paired_H1_minus_price_only": h2,
                                          "cash_ablation": sc}
    st3 = v2.h3_states(legs)
    _, s3 = book_and_stats(st3, "H3", seed=99)
    res["H3"] = s3
    # R14(d): disclosed sensitivity, selected setting by reference to 1ca5228b3c (h3_b25) and H3, drift base
    hs, bs = v2.SELECTED_REF
    _, d1 = book_and_stats(v2.h1_states(rel, bd, hs, bs), "H1_drift_base", seed=200, base_reading="drift")
    _, d3 = book_and_stats(st3, "H3_drift_base", seed=201, base_reading="drift")
    res["R14d_drift_base_sensitivity"] = {"note": "BASE weights equal at each month-end then drifting; not a re-selection",
                                          "H1_h3_b25": d1, "H3": d3}
    obs = {k: v["H1"]["vs_matched_mix"]["observed"] for k, v in res["settings"].items()}
    order = {"h3_b25.0": (3, -25.0), "h3_b37.5": (3, -37.5), "h5_b25.0": (5, -25.0), "h5_b37.5": (5, -37.5)}
    best = max(obs.values())
    ties = [k for k, v in obs.items() if abs(v - best) < 1e-9]
    sel = sorted(ties, key=lambda k: order[k])[0]
    res["selection"] = {"rule": "highest H1 excess over its matched mix; exact tie -> smaller h, then larger b",
                        "observed_by_setting": obs, "selected": sel,
                        "inherit": "H2's price-only control and the cash ablation use the selected setting"}
    return res


# ============================================================================ confirmation (R13, R16, R17, R18)
SEEDS = {"stage1": 20261113, "stage2": 20261114, "pooled": 20261115}     # R13-h: fixed per stage before any read
B_STAGE, BLOCK, BLOCK_SENS = 10_000, 21, 63
OFF_BLOCK63 = 500_000                 # block-63 sensitivity stream: seed + 500000 + chunk
OFF_WINDOW = {"pre1998": 0, "h2020_2025": 100_000}     # pooled test: one stream per window (stratified)
PRE_START = pd.Timestamp("1928-01-02")
ERAS = {"E1_1928_1945": (PRE_START, pd.Timestamp("1945-12-31")), "E2_1946_1997": (pd.Timestamp("1946-01-02"), v2.PRE_END)}
READINGS = ("eq", "drift")            # R14 leg-weighting readings
COST_RUNS = ("base", "strict")        # R18
CONVENTIONS = ("weekday", "fixed252")  # R15.5
HYPS = ("H1", "H2", "H3")
STAGE1_PUBLISHED = ROOT / "research/rotation_core/results_v2_stage1_pre1998_published.json"
FINAL_J = ROOT / "research/rotation_core/results_v2_final.json"
FINAL_M = ROOT / "research/rotation_core/RESULTS_V2_FINAL.md"
SELECTION_RERUN_J = ROOT / "research/rotation_core/results_v2_selection_rerun.json"
SELECTION_RERUN_M = ROOT / "research/rotation_core/RESULTS_V2_SELECTION_RERUN.md"
HPEAK = {"E2020": ("2020-02-01", "2020-02-29", "2020-04-30"),      # protocol_header_v1.json named episodes in H
         "E2022": ("2021-12-15", "2022-01-31", "2022-12-31"),
         "E2025": ("2025-01-15", "2025-03-15", "2025-05-31")}
FUND_DIR = YAHOO
STAGE1_INPUTS = {"industries_le2019": IND_D, "factors": FACT}


def stage2_inputs(fund_dir=FUND_DIR) -> dict:
    d = {"industries_full": IND_FULL, "industries_le2019": IND_D, "factors": FACT}
    for t in ["SPY", "RSP"] + v2.FUNDS:
        d[f"yahoo_{t}"] = Path(fund_dir) / f"{t}.parquet"
    return d


def seeds_record() -> dict:
    """S11: every seed used by the confirmation runs, pinned by the release's engine commit."""
    return {
        "stage1_standalone_pre1998": {"block21": f"{SEEDS['stage1']} + c", "block63": f"{SEEDS['stage1']} + {OFF_BLOCK63} + c"},
        "stage2_standalone_2020_2025": {"block21": f"{SEEDS['stage2']} + c", "block63": f"{SEEDS['stage2']} + {OFF_BLOCK63} + c"},
        "pooled_pre1998": {"block21": f"{SEEDS['pooled']} + c", "block63": f"{SEEDS['pooled']} + {OFF_BLOCK63} + c"},
        "pooled_2020_2025": {"block21": f"{SEEDS['pooled']} + {OFF_WINDOW['h2020_2025']} + c",
                             "block63": f"{SEEDS['pooled']} + {OFF_WINDOW['h2020_2025']} + {OFF_BLOCK63} + c"},
        "c": "chunk number 0..19 (500 resamples per chunk, B = 10,000)",
        "shared_indices": "within one window and one block length, H1, H2 and H3 and all four reading x cost runs use "
                          "the SAME resample indices; the three Holm contrasts therefore share indices (stratified: "
                          "the two windows are resampled separately, no block spans the join)",
        "selection": "unchanged from 1ca5228b3c (20261111 + fixed offsets; adjacent books overlap, S11: left as committed)"}


def _cagr(x, ann) -> float:
    x = np.asarray(x, dtype=float)
    return float(np.prod(1 + x) ** (ann / len(x)) - 1) if len(x) else float("nan")


def build(ind_path, fact_path, end, h, b) -> dict:
    """One continuous run over all data to `end` (S1b(i): warm state; no restart at a window start)."""
    vw, ew = v2.load_french_industries(ind_path, end)
    mkt, rf = v2.load_french_market(fact_path, end)
    legs = v2.form_legs(vw, mkt)
    bd = v2.current_leg_breadth(vw, legs)
    rel = v2.relative_line(legs)                   # O1: computed once, net at 10 bp; identical in every cost run
    states = {"H1": v2.h1_states(rel, bd, h, b), "PO": v2.h1_states(rel, bd, h, b, use_breadth=False),
              "H3": v2.h3_states(legs)}
    return {"vw": vw, "ew": ew, "mkt": mkt, "rf": rf, "legs": legs, "bd": bd, "states": states}


def sim_start(legs) -> pd.Timestamp:
    return legs.returns[["OFF", "DEF", "BASE"]].dropna().index[0]


def run_books(legs, states, rf, end, reading, cost) -> tuple[dict, pd.DataFrame]:
    """Books held continuously from the first formed legs (warm holdings) and scored by slicing; R18 cost runs:
    base = book at legs.fee_bp on switches, legs net at legs.fee_bp, mix on the same net legs;
    strict = book at 2x on switches AND on the re-formation of what it holds, mix on GROSS legs (pays nothing)."""
    strict = cost == "strict"
    fee = legs.fee_bp * (2 if strict else 1)
    a = sim_start(legs)

    def mk(st, tag, cash=False):
        return v2.simulate_states(st, legs, rf, a, end, cash_for_defend=cash, fee_bp=fee, name=tag, base=reading,
                                  strict=strict)
    bks = {"H1": mk(states["H1"], "H1"), "PO": mk(states["PO"], "PO"), "H3": mk(states["H3"], "H3"),
           "CASH": mk(states["H1"], "CASH", True)}
    LR = v2.base_view(legs.returns, reading, "gross" if strict else "net", legs.fee_bp)
    return bks, LR


def window_block(bks, LR, rf, a, z, eras, yard, level=None, mkt=None, episodes=None) -> dict:
    out = {}
    for k, bk in bks.items():
        ii, r, W, L = v2.window_arrays(bk, LR, rf, a, z)
        mix = v2.mix_series(W, L)
        ann = v2.ann_factor(ii)
        yrs = len(ii) / ann
        o = {"excess": v2.window_excess(bk, LR, rf, a, z),
             "excess_fixed252": v2.window_excess(bk, LR, rf, a, z, ann=float(rc.TRADING_DAYS)),
             "eras": {e: v2.window_excess(bk, LR, rf, ea, ez) for e, (ea, ez) in eras.items()},
             "max_drawdown": v2.max_drawdown(r), "max_drawdown_matched_mix": v2.max_drawdown(mix),
             "CAGR": _cagr(r, ann), "CAGR_matched_mix": _cagr(mix, ann),
             "matched_mix_weights": dict(zip(["OFF", "DEF", "BASE", "cash"], map(float, W.mean(axis=0)))),
             "turnover_one_way_per_year": float(bk.traded.loc[ii].sum() / yrs / 2),
             "costs_per_year": float(bk.costs.loc[ii].sum() / yrs),
             "vs_yardsticks_ann_DESCRIPTIVE_not_a_pass_condition": {nm: float(np.mean(r - y.reindex(ii).fillna(0).to_numpy(dtype=float)) * ann)
                                   for nm, y in yard.items()}}
        if k == "H1":                      # descriptive state split: excess over the mix by leg held that day
            held = np.argmax(W, axis=1)
            o["state_split_DESCRIPTIVE_not_a_pass_condition"] = {nm: (float(np.mean((r - mix)[held == j]) * ann) if (held == j).any() else None)
                                            for j, nm in enumerate(["ATTACK(OFF)", "DEFEND(DEF)", "NEUTRAL(BASE)", "cash"])}
        if episodes is not None and k in ("H1", "PO", "CASH"):
            pv = rc.pivot_table(held_risk_on(bk).loc[ii], bk.returns.loc[ii], mkt.reindex(ii).fillna(0),
                                level.reindex(ii), episodes)
            o["false_DEFEND_calls_per_calm_year_DESCRIPTIVE"] = pv["false_pivots_per_calm_year"]
            o["episodes_DESCRIPTIVE_not_a_pass_condition"] = pv["episodes"]
        out[k] = o
    return out


def paired_h2(bks, a, z, eras) -> dict:
    """H2: paired daily difference H1 - price-only; annualised mean on the window and each era."""
    d = bks["H1"].returns - bks["PO"].returns.reindex(bks["H1"].returns.index)
    res = {}
    for e, (ea, ez) in {"window": (a, z), **eras}.items():
        x = d.loc[ea:ez]
        res[e] = float(x.mean() * v2.ann_factor(x.index)) if len(x) else float("nan")
        res[e + "_fixed252"] = float(x.mean() * rc.TRADING_DAYS) if len(x) else float("nan")
    res["max_drawdown_H1"] = v2.max_drawdown(bks["H1"].returns.loc[a:z])
    res["max_drawdown_price_only"] = v2.max_drawdown(bks["PO"].returns.loc[a:z])
    return res


def window_series(runs, rf, a, z) -> tuple[dict, pd.DatetimeIndex]:
    """Bootstrap inputs on one window for every reading x cost run and H1/H2/H3 (shared indices)."""
    ser, ii = {}, None
    for (reading, cost), (bks, LR) in runs.items():
        for hyp in ("H1", "H3"):
            ii, r, W, L = v2.window_arrays(bks[hyp], LR, rf, a, z)
            ser[f"{reading}|{cost}|{hyp}"] = ("mix", r, W, L)
        _, r0, _, _ = v2.window_arrays(bks["PO"], LR, rf, a, z)
        _, r1, _, _ = v2.window_arrays(bks["H1"], LR, rf, a, z)
        ser[f"{reading}|{cost}|H2"] = ("paired", r1 - r0)
    return ser, ii


def observed_raw(ser) -> dict:
    return {k: (float(s[1].mean()) if s[0] == "paired" else v2.raw_mix_excess(*s[1:])) for k, s in ser.items()}


def standalone(ser, ii, B_, seed) -> dict:
    """One window alone: observed, 95% interval, one-sided centred p (governing) and two-sided p (labelled), for
    block 21 (governs) and block 63 (sensitivity)."""
    obs = observed_raw(ser)
    ann = v2.ann_factor(ii)
    out = {}
    for blk, s0 in ((BLOCK, seed), (BLOCK_SENS, seed + OFF_BLOCK63)):
        dr = v2.bootstrap_draws(ser, B_, blk, s0)
        out[f"block{blk}"] = {k: {"observed_ann": obs[k] * ann, "ci95_ann": rc.ci95(dr[k] * ann),
                                  "p_one_sided_centred": rc.centred_p(dr[k], obs[k]),
                                  "p_two_sided_centred_LABELLED_NOT_GOVERNING": v2.two_sided_p(dr[k], obs[k]),
                                  "finite_draws": rc.finite_draws(dr[k])} for k in ser}
    return out


# ---------------------------------------------------------------------------- R19.1 Phase A: integrity only
class IntegrityAbort(Exception):
    """Phase A found a non-zero integrity count. Carries counts and booleans only."""
    def __init__(self, phase_a: dict):
        super().__init__("INTEGRITY_ABORT")
        self.phase_a = phase_a


TOL = 1e-12


def phase_a_window(runs, legs, states, rf, a, z, windows: dict) -> dict:
    """R19.1 Phase A for one data window. Counts and booleans only: no mean, sum, cumulative return, drawdown and
    no comparison of a book with its mix (a grep test pins the calls this function may make).
    nan: per book x window x reading x cost run, the inputs of every statistic that could be non-finite:
      non-finite book returns + non-finite start-of-day weights + held legs with a non-finite return that day +
      cash held on a day with a non-finite cash rate + 1 if the window has no session.
    leg_unobserved: sessions on which a held leg has no member with an observed close.
    warm: sessions in the window with no state; and whether the book was held before the window's first date."""
    nan, unobs, warm = {}, {}, {}
    valid = legs.valid[LEG_COLS_R]
    for (reading, cost), (bks, LR) in runs.items():
        for k, bk in bks.items():
            idx = bk.returns.index
            r_all = bk.returns.to_numpy(dtype=float)
            W_all = bk.holdings[LEG_COLS_R].to_numpy(dtype=float)
            L_all = LR.reindex(idx)[LEG_COLS_R].to_numpy(dtype=float)
            C_all = rf.reindex(idx).to_numpy(dtype=float)
            V_all = valid.reindex(idx).to_numpy()
            st = states[ST_OF_BOOK[k]].reindex(idx).to_numpy(dtype=float)
            for w, (wa, wz) in windows.items():
                m = (idx >= pd.Timestamp(wa)) & (idx <= pd.Timestamp(wz))
                held = W_all[m] > TOL
                cash_only = ~np.any(held, axis=1)
                key = f"{k}|{w}|{reading}|{cost}"
                nan[key] = (np.count_nonzero(~np.isfinite(r_all[m])) + np.count_nonzero(~np.isfinite(W_all[m]))
                            + np.count_nonzero(held & ~np.isfinite(L_all[m]))
                            + np.count_nonzero(cash_only & ~np.isfinite(C_all[m])) + int(np.count_nonzero(m) == 0))
                unobs[key] = int(np.count_nonzero(held & (V_all[m] == 0)))
                warm[key] = int(np.count_nonzero(~np.isfinite(st[m]))) + int(not (np.count_nonzero(m) > 0
                                                                                   and idx[0] < pd.Timestamp(wa)))
    return {"nan": {k: int(v) for k, v in nan.items()}, "leg_unobserved": unobs, "warm_failures": warm}


def phase_a_strict(runs, a, z) -> int:
    """R18 inequality, Phase A form: book against the SAME book at two cost levels, and legs against the same legs
    at two cost levels; no book is compared with a mix. strict book return <= base book return every session;
    start-of-day weights identical (so the strict mix, built on legs >= the base legs with identical weights, is
    never below the base mix); strict mix legs >= base mix legs on every session."""
    n = 0
    for reading in READINGS:
        bb, Lb = runs[(reading, "base")]; bs, Ls = runs[(reading, "strict")]
        for k in bb:
            idx = bb[k].returns.index
            m = (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z))
            rb = bb[k].returns.to_numpy(dtype=float)[m]; rs = bs[k].returns.reindex(idx).to_numpy(dtype=float)[m]
            n += int(np.count_nonzero(~(rs <= rb + TOL)))
            Wb = bb[k].holdings[LEG_COLS_R].to_numpy(dtype=float)[m]
            Ws = bs[k].holdings.reindex(idx)[LEG_COLS_R].to_numpy(dtype=float)[m]
            n += int(np.count_nonzero(np.abs(Ws - Wb) > 1e-9))
        ib = Lb.index
        mb = (ib >= pd.Timestamp(a)) & (ib <= pd.Timestamp(z))
        lb = Lb[LEG_COLS_R].to_numpy(dtype=float)[mb]; ls = Ls.reindex(ib)[LEG_COLS_R].to_numpy(dtype=float)[mb]
        ok = np.isfinite(lb) & np.isfinite(ls)
        n += int(np.count_nonzero(ok & ~(ls >= lb - TOL)))
    return n


def phase_a(preps: list) -> dict:
    """Phase A over every prepared window: (name, prep) with prep = {"runs", "legs", "states", "rf", "a", "z",
    "windows"}. Returns counts, booleans and `clean`."""
    out = {"windows": {}, "strict_inequality_violations": 0, "executions_identical_across_cost_runs": True}
    for name, p in preps:
        w = phase_a_window(p["runs"], p["legs"], p["states"], p["rf"], p["a"], p["z"], p["windows"])
        out["windows"][name] = w
        out["strict_inequality_violations"] += phase_a_strict(p["runs"], p["a"], p["z"])
        out["executions_identical_across_cost_runs"] &= states_identical_across_costs(p["runs"])
    nonzero = sorted(f"{name}|{kind}|{k}" for name, w in out["windows"].items() for kind, d in w.items()
                     for k, v in d.items() if v != 0)
    if out["strict_inequality_violations"]:
        nonzero.append("strict_inequality_violations")
    if not out["executions_identical_across_cost_runs"]:
        nonzero.append("executions_identical_across_cost_runs")
    out["nonzero"] = nonzero
    out["clean"] = not nonzero
    return out


PHASE_A_FUNCTIONS = ("phase_a_window", "phase_a_strict", "phase_a", "states_identical_across_costs")
LEG_COLS_R = ["OFF", "DEF", "BASE"]
ST_OF_BOOK = {"H1": "H1", "PO": "PO", "H3": "H3", "CASH": "H1"}


def phase_a_lines(A: dict, inputs_sha: dict | None, engine_commit, out) -> None:
    for k, h_ in sorted((inputs_sha or {}).items()):
        out(f"PHASE_A input_sha256 {k} {h_}")
    for k, v in sorted(v2.versions().items()):
        out(f"PHASE_A version {k} {v}")
    out(f"PHASE_A engine_commit {engine_commit} (checked against the release before this run)")
    for name, w in A["windows"].items():
        for kind, d in w.items():
            label = "NaN_count" if kind == "nan" else kind
            for k in sorted(d):
                out(f"PHASE_A {label} {name} {k.replace('|', ' ')} {d[k]}")
    out(f"PHASE_A strict_inequality_violations {A['strict_inequality_violations']}")
    out(f"PHASE_A executions_identical_across_cost_runs {str(A['executions_identical_across_cost_runs']).lower()}")
    out(f"PHASE_A {'CLEAN' if A['clean'] else 'INTEGRITY_ABORT'}")


def states_identical_across_costs(runs) -> bool:
    """O1(i): the cost run never changes a decision; executions (traded days) coincide in base and strict."""
    for reading in READINGS:
        bb, _ = runs[(reading, "base")]; bs, _ = runs[(reading, "strict")]
        for k in bb:
            if not ((bb[k].traded > 0).equals(bs[k].traded > 0)):
                return False
    return True


def strict_inequality_violations(runs, rf, a, z) -> int:
    """Kept name for the counter used in tests; the Phase A form (book vs same book, legs vs same legs)."""
    return phase_a_strict(runs, a, z)


# ---------------------------------------------------------------------------- preparation (no statistic)
def prepare_pre1998(ind_path=IND_D, fact_path=FACT) -> dict:
    """Reads nothing after 1997-12-31; builds states and simulates every book at both readings and cost runs.
    Computes no statistic."""
    end = v2.PRE_END
    v2.assert_stage1_window(end)
    h, b = v2.selected_setting()
    D = build(ind_path, fact_path, end, h, b)
    assert D["vw"].index.max() <= end and D["mkt"].index.max() <= end, "stage 1 read a date after 1997-12-31"
    runs = {(r_, c_): run_books(D["legs"], D["states"], D["rf"], end, r_, c_) for r_ in READINGS for c_ in COST_RUNS}
    return {"D": D, "runs": runs, "legs": D["legs"], "states": D["states"], "rf": D["rf"], "h": h, "b": b,
            "a": PRE_START, "z": end, "windows": dict(ERAS)}


def prepare_h2020(full_ind, fact, h, b, z) -> dict:
    D = build(full_ind, fact, z, h, b)
    runs = {(r_, c_): run_books(D["legs"], D["states"], D["rf"], z, r_, c_) for r_ in READINGS for c_ in COST_RUNS}
    return {"D": D, "runs": runs, "legs": D["legs"], "states": D["states"], "rf": D["rf"], "a": v2.H_START, "z": z,
            "windows": {"h2020_2025": (v2.H_START, z)}}


def prepare_funds(states, rf, fund_dir, a, z) -> dict:
    R_, spy = v2.load_fund_panel(fund_dir, z)
    fl = v2.form_fund_legs(R_, spy)
    named = v2.form_fund_legs(R_, spy, fixed=(v2.NAMED_OFFENCE, v2.NAMED_DEFENCE))
    rff = rf.reindex(R_.index)
    mapped = {k: v2.map_states_to_sessions(st, R_.index) for k, st in states.items()}
    runs = {(r_, c_): run_books(fl, mapped, rff, z, r_, c_) for r_ in READINGS for c_ in COST_RUNS}
    return {"runs": runs, "legs": fl, "states": mapped, "rf": rff, "a": a, "z": z, "named": named,
            "windows": {"funds_2020_2025": (a, z)}}


# ---------------------------------------------------------------------------- Phase B: statistics (after a clean A)
def pre1998_stats(prep: dict, B_=B_STAGE) -> dict:
    """Stage-1 statistics; only ever called after a clean Phase A. Magnitudes (hashed, never written at stage 1
    unless the gate closes), the sixteen gate signs, H2's signs (never printed or written at stage 1)."""
    import scripts.run_rotation_core_v1 as v1
    D, runs, end = prep["D"], prep["runs"], prep["z"]
    vw, ew, mkt, rf, legs = D["vw"], D["ew"], D["mkt"], D["rf"], D["legs"]
    s = vw.index
    ew_proxy = ew.where(vw.notna().cumsum() >= 252).mean(axis=1)
    level = (1 + mkt.reindex(s).fillna(0)).cumprod()
    eps = {}
    for name, (a_, b2, c) in v1.LPEAK.items():
        ep = rc.find_episode(level[(s >= PRE_START) & (s <= end)], a_, b2, c)
        if ep:
            eps[name] = ep
    mag, signs, h2signs = {}, {}, {}
    for (reading, cost), (bks, LR) in runs.items():
        yard = {"French_market_(SPY_yardstick)": mkt, "EW_proxy_(RSP_yardstick)": ew_proxy, "BASE_equal_weight": LR["BASE"]}
        blk = window_block(bks, LR, rf, PRE_START, end, ERAS, yard, level, mkt, eps)
        h2 = paired_h2(bks, PRE_START, end, ERAS)
        mag[f"{reading}|{cost}"] = {"books": blk, "H2_paired": h2}
        for hyp in v2.OPENING_HYPOTHESES:
            for e in ERAS:
                signs[f"{hyp}|{e}|{reading}|{cost}"] = v2.sign(blk[hyp]["eras"][e])
        for e in ERAS:
            h2signs[f"H2|{e}|{reading}|{cost}"] = v2.sign(h2[e])
    ser, ii = window_series(runs, rf, PRE_START, end)
    mag["standalone_pre1998"] = standalone(ser, ii, B_, SEEDS["stage1"])
    idx = ii
    integrity = {"sessions_per_era": {e: int(((idx >= a_) & (idx <= z)).sum()) for e, (a_, z) in ERAS.items()},
                 "offence_members_min": int(D["bd"]["n_members"][idx].min()),
                 "offence_members_max": int(D["bd"]["n_members"][idx].max()),
                 "deferred_executions_total_incl_warmup": int(sum(x.meta["deferred_executions"]
                                                                   for r_ in runs.values() for x in r_[0].values())),
                 "days_holding_after_last_close_total": int(sum(x.meta["days_holding_an_asset_after_its_last_close"]
                                                                for r_ in runs.values() for x in r_[0].values())),
                 "dropped_industry_days_unique": int(legs.dropped_industry_days),
                 "state_sessions": {k_: {nm: int((st.reindex(idx) == v).sum()) for nm, v in
                                         (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))}
                                    for k_, st in (("H1", D["states"]["H1"]), ("price_only", D["states"]["PO"]),
                                                   ("H3", D["states"]["H3"]))},
                 "episodes_found": len(eps)}
    mag.update({"label": "STAGE 1 of R13 (pre-1998; previously examined by Pro run B; not clean)",
                "header_sha256": v2.FROZEN_V2_SHA256, "selected_setting": f"h{prep['h']:g}_b{prep['b']:g}",
                "window": [str(PRE_START.date()), str(end.date())], "integrity": integrity,
                "seeds": seeds_record(), "B": B_, "block": BLOCK, "block_sensitivity": BLOCK_SENS,
                "H2_signs": h2signs})
    return {"magnitudes": mag, "signs": signs, "h2_signs": h2signs, "integrity": integrity, "window_index": ii}


def pre1998_report(ind_path=IND_D, fact_path=FACT, B_=B_STAGE) -> dict:
    """Prepare -> Phase A -> (IntegrityAbort | Phase B). Used by the final run and the tests."""
    prep = prepare_pre1998(ind_path, fact_path)
    A = phase_a([("pre1998", prep)])
    if not A["clean"]:
        raise IntegrityAbort(A)
    B = pre1998_stats(prep, B_)
    return dict(B, phase_a=A, violations=A["strict_inequality_violations"], runs=prep["runs"], rf=prep["rf"],
                prep=prep)


def _flat(d, p=""):
    for k, v in d.items():
        if isinstance(v, dict):
            yield from _flat(v, f"{p}{k}.")
        else:
            yield f"{p}{k}", v


gate_decision = v2.gate_decision          # R20.3: exactly eight signs per hypothesis, else closed


def _now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def start_entry(stage, release_sha, engine_commit, inputs_sha) -> dict:
    return {"kind": "START", "stage": stage, "release_sha256": release_sha, "engine_commit": engine_commit,
            "inputs_sha256": inputs_sha, "versions": v2.versions(), "utc": _now()}


def record_phase_a(ledger, start_index: int, A: dict) -> dict:
    """R19.1/R20.1(b)/R20.11: Phase A always leaves its entry, counts only, before any statistic exists."""
    if A["clean"]:
        return ledger.append({"kind": "PHASE_A_CLEAN", "start_index": start_index, "utc": _now()})
    counts = {f"{n}|{kind}|{k}": int(v) for n, w in A["windows"].items() for kind, d in w.items()
              for k, v in d.items() if v != 0}
    if A["strict_inequality_violations"]:
        counts["strict_inequality_violations"] = int(A["strict_inequality_violations"])
    return ledger.append({"kind": "INTEGRITY_ABORT", "start_index": start_index, "utc": _now(),
                          "nonzero_counts": counts, "magnitudes": "none computed"})


def stage1_command(ledger, release: dict, release_sha: str, engine_commit: str, ind_path, fact_path,
                   inputs_sha: dict, B_=B_STAGE, publish_path=None, out=print) -> dict:
    """R20.1 stage 1. START pushed before anything is loaded; Phase A outcome pushed before any statistic; the gate
    record pushed BEFORE any sign is printed or written elsewhere (a failed push prints nothing about signs and
    exits non-zero). Exceptions carry no value."""
    import json, warnings
    warnings.filterwarnings("ignore")
    start = start_entry("stage1", release_sha, engine_commit, inputs_sha)
    v2.start_allowed(ledger.entries(), start, release)
    s = ledger.append(start)
    try:
        prep = prepare_pre1998(ind_path, fact_path)
        A = phase_a([("pre1998", prep)])
    except v2.SealedRefusal:
        raise
    except Exception as e:
        raise SystemExit(f"stage 1 failed in preparation/Phase A: {type(e).__name__} (message withheld); "
                         "START stands with no outcome") from None
    phase_a_lines(A, inputs_sha, engine_commit, out)
    pa = record_phase_a(ledger, s["index"], A)
    if not A["clean"]:
        out(f"INTEGRITY_ABORT recorded as ledger entry {pa['index']}: no gate statistic computed, no sign; "
            "not a stage-1 gate result (R19 item 1)")
        return dict(pa, integrity_abort=True)
    try:
        R = pre1998_stats(prep, B_)
    except Exception as e:
        raise SystemExit(f"stage 1 failed in Phase B: {type(e).__name__} (message withheld); the Phase-A-clean "
                         "entry stands: only the identical rerun is permitted (R20.1)") from None
    signs = R["signs"]
    gate_open, per = gate_decision(signs)
    status = {h_: ("OPEN" if per[h_] else "FAILED") for h_ in v2.OPENING_HYPOTHESES}
    status["H2"] = "NOT SHOWN (decided at the final conjunction)" if gate_open else "FAILED (closed gate, amendment f)"
    sha = v2.magnitudes_sha(R["magnitudes"])
    rec = {"kind": "GATE", "start_index": s["index"], "utc": _now(), "selected_setting": R["magnitudes"]["selected_setting"],
           "gate_signs": signs, "integrity": R["integrity"], "hypothesis_status": status,
           "gate_rule": "open iff H1 or H3 has exactly its eight signs, all '+': positive excess over its era-alone "
                        "matched mix in both eras under both leg readings in both the base and the strict cost run",
           "gate_open": bool(gate_open), "magnitudes_sha256": sha, "seeds": seeds_record()}
    try:
        g = ledger.append(rec)
    except v2.LedgerPushFailed:
        raise SystemExit("stage 1: the gate record could not be pushed; nothing about signs is printed or written. "
                         "Only the identical rerun is permitted (R20.1)") from None
    for k in sorted(signs):
        out(f"GATE_SIGN {k.replace('|', ' ')} {signs[k]}")
    for k, v in _flat(R["integrity"]):
        out(f"count {k} {v}")
    for h_, st in status.items():
        out(f"status {h_} {st}")
    out(f"gate_open {str(gate_open).lower()}")
    out(f"ledger_index {g['index']}")
    out(f"magnitudes_sha256 {sha}")
    if not gate_open and publish_path is not None:
        pub = dict(R["magnitudes"], published_because="the gate closed; R16 S6: a closed gate publishes at once",
                   magnitudes_sha256=sha)
        Path(publish_path).write_text(json.dumps(pub, indent=1, sort_keys=True, default=float) + "\n")
        out(f"published {Path(publish_path).name}")
    return g


# ---------------------------------------------------------------------------- final conjunction (stage 2)
def conjunction_legs(hyp: str, R: dict) -> dict:
    """Every leg of the frozen pass condition under R13-g (2x covers the whole conjunction), R14(c) (both leg
    readings), R15.5 (both annualisation conventions), R18 (strict run) and S1b(v)/R19.2 (drawdown at both cost
    runs; H2: H1's drawdown no worse than the price-only control's).
    R: {"holm": {"reading|cost|conv": {hyp: {"reject_h0": bool}}},
        "point": {"reading|cost": {hyp: {"pre1998", "E1_1928_1945", "E2_1946_1997", "h2020_2025"}}},
        "drawdown": {"reading|cost": {hyp: {"pre1998": (book, ref), "h2020_2025": (book, ref)}}},
        "integrity_ok": bool}"""
    legs = {"integrity": R["integrity_ok"] is True}
    for reading in READINGS:
        for cost in COST_RUNS:
            rc_ = f"{reading}|{cost}"
            for conv in CONVENTIONS:
                legs[f"pooled_holm_block21|{rc_}|{conv}"] = R["holm"][f"{rc_}|{conv}"][hyp]["reject_h0"] is True
            for w in ("pre1998", "E1_1928_1945", "E2_1946_1997", "h2020_2025"):
                legs[f"sign|{w}|{rc_}"] = v2.sign(R["point"][rc_][hyp][w]) == "+"
            for w in ("pre1998", "h2020_2025"):
                bk_, ref = R["drawdown"][rc_][hyp][w]
                legs[f"drawdown|{w}|{rc_}"] = bool(np.isfinite(bk_) and np.isfinite(ref) and bk_ >= ref)
    return legs


def fund_veto(estimates: dict) -> bool:
    return v2.tradable_veto(estimates)


def fund_stats(Fp: dict) -> dict:
    """F4 + R18 + R19.3, Phase B: point estimates on 2020-2025 alone, both readings, base and strict; H2 = paired
    difference of the fund-executed H1 and price-only books. Named mapping descriptive (hindsight)."""
    a, z, rff = Fp["a"], Fp["z"], Fp["rf"]
    est = {}
    for (reading, cost), (bks, LR) in Fp["runs"].items():
        est[f"{reading}|{cost}"] = {"H1": v2.window_excess(bks["H1"], LR, rff, a, z),
                                    "H3": v2.window_excess(bks["H3"], LR, rff, a, z),
                                    "H2": paired_h2(bks, a, z, {})["window"]}
    nb, nLR = run_books(Fp["named"], Fp["states"], rff, z, "eq", "base")
    return {"estimates": est,
            "named_mapping_DESCRIPTIVE_hindsight_not_a_pass_condition":
                {"H1_excess_eq_base": v2.window_excess(nb["H1"], nLR, rff, a, z)},
            "fund_drawdown_reported_not_binding": {k: v2.max_drawdown(b_["H1"].returns.loc[a:z])
                                                   for k, (b_, _) in ((f"{r}|{c}", v) for (r, c), v in Fp["runs"].items())},
            "veto": {h_: fund_veto({k: est[k][h_] for k in est}) for h_ in HYPS}}


def final_evaluation(pre_ind, full_ind, fact, fund_dir, expected_sha: str, expected_signs: dict, ledger,
                     start_index: int, B_=B_STAGE, h_end=v2.H_END, out=print, inputs_sha=None, engine_commit=None) -> dict:
    """S1 + R19.1 + R20: prepare pre-1998, 2020-2025 and the fund tier (books simulated, no statistic); Phase A over
    all three, its outcome pushed to the ledger; IntegrityAbort before any 2020-2025 number if not clean. Then Phase
    B: pre-1998 recomputed, its magnitudes hash REQUIRED to reproduce (R20.6), the gate re-derived from the
    reproduced numbers and required open with signs equal to the recorded ones (R20.3); then 2020-2025, the pooled
    stratified test, Holm, the conjunction, the fund veto and the verdicts."""
    import re as _re
    if not (isinstance(expected_sha, str) and _re.fullmatch(r"[0-9a-f]{64}", expected_sha)):
        raise v2.SealedRefusal("refused: the reproduction hash is required (R20.6)")
    if not isinstance(expected_signs, dict) or not v2.gate_decision(expected_signs)[0]:
        raise v2.SealedRefusal("refused: the recorded gate signs are required and must be open (R20.3)")
    Pp = prepare_pre1998(pre_ind, fact)
    h, b = Pp["h"], Pp["b"]
    a, z = v2.H_START, pd.Timestamp(h_end)
    Hp = prepare_h2020(full_ind, fact, h, b, z)
    Fp = prepare_funds(Hp["states"], Hp["rf"], fund_dir, a, z)
    A = phase_a([("pre1998", Pp), ("h2020_2025", Hp), ("funds", Fp)])
    phase_a_lines(A, inputs_sha, engine_commit, out)
    record_phase_a(ledger, start_index, A)
    if not A["clean"]:
        raise IntegrityAbort(A)
    # ---- Phase B
    import scripts.run_rotation_core_v1 as v1  # noqa: F401
    P = pre1998_stats(Pp, B_)
    v2.verify_reproduction(P["magnitudes"], expected_sha)
    reopen, _ = v2.gate_decision(P["signs"])                  # R20.3: nothing recorded is trusted
    if not reopen or P["signs"] != expected_signs:
        raise v2.SealedRefusal("refused: the gate re-derived from the reproduced numbers is not open or its signs "
                               "differ from the recorded ones")
    D, runs = Hp["D"], Hp["runs"]
    rf, mkt = D["rf"], D["mkt"]
    s = D["vw"].index
    level = (1 + mkt.reindex(s).fillna(0)).cumprod()
    eps = {}
    for name, (p0, p1, tb) in HPEAK.items():
        ep = rc.find_episode(level[(s >= a) & (s <= z)], p0, p1, tb)
        if ep:
            eps[name] = ep
    spy, rsp = (v2.load_yahoo_tr(Path(fund_dir) / f"{t}.parquet", z).pct_change(fill_method=None) for t in ("SPY", "RSP"))
    blocks = {}
    for (reading, cost), (bks, LR) in runs.items():
        yard = {"SPY": spy, "RSP": rsp, "BASE_equal_weight": LR["BASE"], "French_market": mkt}
        blocks[f"{reading}|{cost}"] = {"books": window_block(bks, LR, rf, a, z, {}, yard, level, mkt, eps),
                                       "H2_paired": paired_h2(bks, a, z, {})}
    ser_h, ii_h = window_series(runs, rf, a, z)
    ser_p, ii_p = window_series(Pp["runs"], Pp["rf"], PRE_START, v2.PRE_END)
    stand = standalone(ser_h, ii_h, B_, SEEDS["stage2"])
    obs_p, obs_h = observed_raw(ser_p), observed_raw(ser_h)
    pooled, holm = {}, {}
    for blk, extra in ((BLOCK, 0), (BLOCK_SENS, OFF_BLOCK63)):
        dp = v2.bootstrap_draws(ser_p, B_, blk, SEEDS["pooled"] + OFF_WINDOW["pre1998"] + extra)
        dh = v2.bootstrap_draws(ser_h, B_, blk, SEEDS["pooled"] + OFF_WINDOW["h2020_2025"] + extra)
        for conv in CONVENTIONS:
            c = v2.pooled_weights([ii_p, ii_h], conv)
            for reading in READINGS:
                for cost in COST_RUNS:
                    key = f"{reading}|{cost}|{conv}"
                    ps = {}
                    for hyp in HYPS:
                        k = f"{reading}|{cost}|{hyp}"
                        o = c[0] * obs_p[k] + c[1] * obs_h[k]
                        d = c[0] * dp[k] + c[1] * dh[k]
                        pooled.setdefault(f"block{blk}", {}).setdefault(key, {})[hyp] = {
                            "observed_ann_CONDITIONAL_ON_GATE": o, "ci95_ann": rc.ci95(d),
                            "p_one_sided_centred": rc.centred_p(d, o),
                            "p_two_sided_centred_LABELLED_NOT_GOVERNING": v2.two_sided_p(d, o)}
                        ps[hyp] = rc.centred_p(d, o)
                    holm.setdefault(f"block{blk}", {})[key] = rc.holm(ps)
    funds = fund_stats(Fp)
    point, dd = {}, {}
    for reading in READINGS:
        for cost in COST_RUNS:
            rc_ = f"{reading}|{cost}"
            pm, hm = P["magnitudes"][rc_], blocks[rc_]
            point[rc_], dd[rc_] = {}, {}
            for hyp in ("H1", "H3"):
                point[rc_][hyp] = {"pre1998": pm["books"][hyp]["excess"], **pm["books"][hyp]["eras"],
                                   "h2020_2025": hm["books"][hyp]["excess"]}
                dd[rc_][hyp] = {w: (x["books"][hyp]["max_drawdown"], x["books"][hyp]["max_drawdown_matched_mix"])
                                for w, x in (("pre1998", pm), ("h2020_2025", hm))}
            point[rc_]["H2"] = {"pre1998": pm["H2_paired"]["window"], **{e: pm["H2_paired"][e] for e in ERAS},
                                "h2020_2025": hm["H2_paired"]["window"]}
            dd[rc_]["H2"] = {w: (x["H2_paired"]["max_drawdown_H1"], x["H2_paired"]["max_drawdown_price_only"])
                             for w, x in (("pre1998", pm), ("h2020_2025", hm))}
    Rc = {"holm": holm[f"block{BLOCK}"], "point": point, "drawdown": dd, "integrity_ok": A["clean"]}
    verdicts = {}
    for hyp in HYPS:
        lg = conjunction_legs(hyp, Rc)
        passed_industry = all(lg.values())
        verdicts[hyp] = {"verdict": v2.verdict(lg, funds["veto"][hyp] if passed_industry else None),
                         "failed_legs": sorted(k for k, v in lg.items() if not v), "legs_total": len(lg),
                         "fund_veto_fired": funds["veto"][hyp]}
    return {"label": "FINAL CONJUNCTION v2 (historical tier). Best attainable label: 'survives falsification on "
                     "history'. Pooled figures are conditional on the pre-1998 gate, not an unbiased effect size; the "
                     "2020-2025 standalone estimate is the out-of-sample effect size.",
            "header_sha256": v2.FROZEN_V2_SHA256, "selected_setting": f"h{h:g}_b{b:g}",
            "phase_a": {"clean": A["clean"], "nonzero": A["nonzero"],
                        "strict_inequality_violations": A["strict_inequality_violations"]},
            "pre1998_magnitudes_sha256_reproduced": v2.magnitudes_sha(P["magnitudes"]),
            "pre1998": P["magnitudes"], "h2020_2025": blocks, "standalone_2020_2025_OUT_OF_SAMPLE_EFFECT_SIZE": stand,
            "pooled_CONDITIONAL_ON_GATE": pooled, "holm_m3": holm, "governing": "block 21, one-sided centred p",
            "funds": funds, "strict_inequality_violations": A["strict_inequality_violations"],
            "verdicts": verdicts, "seeds": seeds_record(), "conjunction_inputs": Rc,
            "descriptive_only": "Yardsticks (vs_yardsticks), named episodes, false-DEFEND counts, the state split and "
                                "the named fund mapping are descriptive only; none enters any pass condition (R19.5).",
            "reporting_rule_i": "Significance comes from the examined pre-1998 window; the unexamined 2020-2025 window "
                                "supplied a sign check, which a rule with no edge passes about half the time.",
            "independence": "Industries or sectors agreeing are not that many independent confirmations: 49 industries "
                            "at typical pairwise correlation are roughly 2 to 2.5 independent bets by the "
                            "equal-correlation formula (8 to 12 by eigenvalue count); breadth is a share of members, "
                            "not a count of confirmations."}


def confirm_command(ledger, r2: dict, release_sha: str, engine_commit: str, pre_ind, full_ind, fact, fund_dir,
                    inputs_sha: dict, B_=B_STAGE, out=print) -> dict:
    """R20.1 stage 2: START pushed before anything is loaded; Phase A outcome pushed; the FINAL record (verdicts and
    the results hash) pushed before any result is printed or written."""
    start = start_entry("stage2", release_sha, engine_commit, inputs_sha)
    v2.start_allowed(ledger.entries(), start, r2)
    s = ledger.append(start)
    g = r2["_gate_latest"]
    try:
        res = final_evaluation(pre_ind, full_ind, fact, fund_dir, g["magnitudes_sha256"], g["gate_signs"], ledger,
                               s["index"], B_=B_, out=out, inputs_sha=inputs_sha, engine_commit=engine_commit)
    except IntegrityAbort:
        out("INTEGRITY_ABORT: no 2020-2025 number computed; recorded in the ledger")
        return {"integrity_abort": True}
    rec = {"kind": "FINAL", "start_index": s["index"], "utc": _now(),
           "verdicts": {h_: v["verdict"] for h_, v in res["verdicts"].items()},
           "results_sha256": v2.magnitudes_sha(res)}
    try:
        ledger.append(rec)
    except v2.LedgerPushFailed:
        raise SystemExit("stage 2: the FINAL record could not be pushed; nothing is printed or written") from None
    return res


# ---------------------------------------------------------------------------- R20.4 fixture dry run (no path)
FIXTURE_SEED = 7


def fixture_dry_run(out=print, B_=50) -> dict:
    """Stage 1 end to end on inputs built IN MEMORY by the committed seeded generator; takes no path; writes to an
    in-memory ledger only. Every printed line is stamped FIXTURE."""
    import io
    from tests.rotation_core_v2_fixture import fixture_texts
    ind, fac = fixture_texts(seed=FIXTURE_SEED)
    I, F = io.StringIO(ind), io.StringIO(fac)
    stamp = lambda s: out(f"FIXTURE {s}")
    return stage1_command(v2.MemoryLedger(), {}, "fixture-release", "fixture",
                          I, F, {"industries": v2.sha256_file(I), "factors": v2.sha256_file(F)}, B_=B_, out=stamp)


def run_once_guard(path: Path, what: str) -> None:
    """O8: the guard state is the committed file on the just-fetched remote (R20.5), not a local marker."""
    sha = v2.fetch_remote()
    rel = str(Path(path).resolve().relative_to(ROOT))
    if Path(path).exists() or v2._git("cat-file", "-e", f"{sha}:{rel}", check=False).returncode == 0:
        raise SystemExit(f"refused: {what} already run ({Path(path).name} exists locally or on the remote); run once")


def verified_ledger() -> tuple:
    """R20.1/R20.2/R20.5: fetch (fails closed), local == remote, every release version mapped, every ledger version a
    prefix, the whole ledger replayed under the state rules."""
    led = v2.GitLedger()
    sha = led.fetch()
    led.require_local_equals_remote()
    entries = led.entries()
    docs = v2.check_release_history({p.name: v2.file_versions(str(p.relative_to(ROOT)), sha)
                                     for p in (v2.RELEASE, v2.RELEASE2)}, entries)
    v2.validate_ledger(entries, led.version_entries(), docs)
    return led, sha, entries


def main() -> int:
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stage", choices=["select", "pre1998", "confirm"])
    ap.add_argument("--manifest", choices=["stage1", "stage2"], help="print input sha256 and library versions only")
    ap.add_argument("--dry-run-stage1-fixture", action="store_true",
                    help="stage 1 end to end on in-memory synthetic inputs from the committed generator (no path)")
    a = ap.parse_args()
    if a.manifest:
        ins = STAGE1_INPUTS if a.manifest == "stage1" else stage2_inputs()
        man = {}
        for k, p in ins.items():
            try:
                man[k] = v2.sha256_file(p)
            except OSError:
                man[k] = "SEALED (hashed by the runner inside the verified stage-2 run; recorded hash in v2_power)"
        print(json.dumps({"inputs_sha256": man, "versions": v2.versions()}, indent=1))
        return 0
    if a.dry_run_stage1_fixture:
        v2.verify_header_v2(FROZEN)
        if not v2.SELECTION_RESULT.exists():          # before the R15 rerun exists, the dry run reads 1ca5228b3c's file
            v2.SELECTION_RESULT = ROOT / "research/rotation_core/results_v2_selection.json"
        fixture_dry_run(out=print)
        print("FIXTURE stage-1 fixture dry run OK (in-memory synthetic data; in-memory ledger; no real statistic)")
        return 0
    if a.dry_run:
        out = pipeline("2019-12-31", IND_D)
        print(json.dumps(out, indent=1))
        print("dry run OK: structure only; no return, contrast or selection printed or written")
        return 0
    if not FROZEN.exists():
        raise SystemExit("refused: protocol_header_v2.json is not frozen")
    v2.verify_header_v2(FROZEN)
    if a.stage == "pre1998":
        led, sha, entries = verified_ledger()
        rel1 = v2.stage1_release(inputs=STAGE1_INPUTS, remote_sha=sha)
        ins_sha = {k: v2.sha256_file(p) for k, p in STAGE1_INPUTS.items()}
        e = stage1_command(led, rel1, v2.sha256_file(v2.RELEASE), rel1["engine_commit"], IND_D, FACT, ins_sha,
                           publish_path=STAGE1_PUBLISHED)
        return 3 if e.get("integrity_abort") else 0
    if a.stage == "confirm":
        led, sha, entries = verified_ledger()                       # R20.7: the release is verified first
        r = v2._load_release(v2.RELEASE2)
        v2.on_remote(v2.RELEASE2, sha)
        r2 = v2.verify_release2(r, entries)
        v2.check_engine_commit(r2["engine_commit"])
        ins = stage2_inputs()
        with v2.stage2_opened([IND_FULL]):                          # unseal, check recorded hash, re-seal on exit
            ins_sha = v2.check_manifest(r2, ins)
            res = confirm_command(led, r2, v2.sha256_file(v2.RELEASE2), r2["engine_commit"], IND_D, IND_FULL, FACT,
                                  FUND_DIR, ins_sha)
        if res.get("integrity_abort"):
            return 3
        FINAL_J.write_text(json.dumps(res, indent=1, sort_keys=True, default=float) + "\n")
        from scripts.rotation_core_v2_report import write_final_md
        write_final_md(res, FINAL_M)
        print(json.dumps({h_: v["verdict"] for h_, v in res["verdicts"].items()}, indent=1))
        print("wrote", FINAL_J, FINAL_M)
        return 0
    if a.stage == "select":
        run_once_guard(SELECTION_RERUN_J, "the R15 selection rerun")
        res = run_selection()
        SELECTION_RERUN_J.write_text(json.dumps(res, indent=1, default=float) + "\n")
        from scripts.rotation_core_v2_report import write_selection_md
        write_selection_md(res, SELECTION_RERUN_M)
        print("wrote", SELECTION_RERUN_J, SELECTION_RERUN_M, "selected:", res["selection"]["selected"])
        if res["selection"]["selected"] != "h3_b25.0":
            print("STOP: the rerun's selected setting is not h=3, b=25 (R16): tell the CEO")
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
