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

    def book_and_stats(st, tag, fee=10.0, cash_def=False, seed=0, base_reading="eq"):
        LR = v2.base_view(legs.returns, base_reading)
        bk = v2.simulate_states(st, legs, rf, SEL_START, SEL_END, cash_for_defend=cash_def, fee_bp=fee, name=tag,
                                base=base_reading)
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
        _, s1x = book_and_stats(st1, f"H1_2x_h{h}_b{b}", fee=20.0, seed=10 * i + 2)
        bkc, sc = book_and_stats(st1, f"H1_cash_ablation_h{h}_b{b}", cash_def=True, seed=10 * i + 3)
        idx = bk1.returns.index
        h2 = _diff_stat(bk1.returns.values, bk0.returns.reindex(idx).fillna(0).values, 20261111 + 500 + i)
        res["settings"][f"h{h}_b{b}"] = {"H1": s1, "H1_at_2x_costs": {"vs_matched_mix": s1x["vs_matched_mix"],
                                          "costs_per_year": s1x["costs_per_year"]},
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


SEEDS = {"stage1": 20261113, "stage2": 20261114, "pooled": 20261115}     # R13-h: fixed per stage before any read
B_STAGE, BLOCK, BLOCK_SENS = 10_000, 21, 63
ERAS = {"E1_1928_1945": ("1928-01-01", "1945-12-31"), "E2_1946_1997": ("1946-01-02", "1997-12-31")}


def compute_pre1998(ind_path=IND_D, fact_path=FACT, B_=B_STAGE):
    """Full stage-1 computation (pre-1998 only). Returns (results, gate, integrity). Reads nothing after 1997-12-31."""
    from engine import rotation_core_evaluation as rc
    import scripts.run_rotation_core_v1 as v1
    end = v2.PRE_END
    v2.assert_stage1_window(end)
    vw, ew = v2.load_french_industries(ind_path, end)
    mkt, rf = v2.load_french_market(fact_path, end)
    assert vw.index.max() <= end and mkt.index.max() <= end, "stage 1 read a date after 1997-12-31"
    legs = v2.form_legs(vw, mkt)
    bd = v2.current_leg_breadth(vw, legs)
    rel = v2.relative_line(legs)
    h, b = v2.selected_setting()                       # from the committed selection result (R13-g(i))
    st1 = v2.h1_states(rel, bd, h, b); st0 = v2.h1_states(rel, bd, h, b, use_breadth=False); st3 = v2.h3_states(legs)
    start = max([pd.Timestamp("1928-01-02")] + [x.first_valid_index() for x in (st1, st0, st3)])
    eras = {"E1_1928_1945": (start, pd.Timestamp("1945-12-31")), "E2_1946_1997": (pd.Timestamp("1946-01-02"), end)}
    s = vw.index
    ew_proxy = ew.where(vw.notna().cumsum() >= 252).mean(axis=1)
    level = (1 + mkt.reindex(s).fillna(0)).cumprod()
    eps = {}
    for name, (a_, b2, c) in v1.LPEAK.items():
        ep = rc.find_episode(level[(s >= start) & (s <= end)], a_, b2, c)
        if ep:
            eps[name] = ep
    seed0 = SEEDS["stage1"]
    books = {}

    def stats(st, tag, fee=10.0, cash_def=False, k=0, base_reading="eq"):
        LR = v2.base_view(legs.returns, base_reading)
        bk = v2.simulate_states(st, legs, rf, start, end, cash_for_defend=cash_def, fee_bp=fee, name=tag, base=base_reading)
        books[tag] = bk
        idx = bk.returns.index; r = bk.returns
        full = pd.Series(True, index=idx)
        out = {"base_reading": base_reading, "ann_factor_full": v2.ann_factor(idx),
               "vs_matched_mix": v2.matched_contrast(bk, LR, rf, full, B=B_, block=BLOCK, seed=seed0 + k),
               "vs_matched_mix_block63": v2.matched_contrast(bk, LR, rf, full, B=B_, block=BLOCK_SENS, seed=seed0 + k + 1),
               "eras": {}}
        for e, (a_, z) in eras.items():
            em = pd.Series((idx >= a_) & (idx <= z), index=idx)
            out["eras"][e] = v2.matched_contrast(bk, LR, rf, em, B=B_, block=BLOCK, seed=seed0 + k + 2)
            out["eras"][e]["window_excess"] = v2.window_excess(bk, LR, rf, a_, z)
            out["eras"][e]["ann_factor"] = v2.ann_factor(idx[(idx >= a_) & (idx <= z)])
        W = bk.holdings[["OFF", "DEF", "BASE"]]; wbar = W.mean(); cashbar = 1 - wbar.sum()
        mix = (LR.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0) * wbar).sum(axis=1) + cashbar * rf.reindex(idx).fillna(0)
        yrs = len(r) / v2.ann_factor(idx)
        for nm, ref in (("vs_French_market_(SPY_yardstick)", mkt), ("vs_EW_proxy_(RSP_yardstick)", ew_proxy),
                        ("vs_BASE_equal_weight_industries", LR["BASE"])):
            out[nm] = _diff_stat(r.values, ref.reindex(idx).fillna(0).values, seed0 + 300 + k, B_)
        pv = rc.pivot_table(held_risk_on(bk), r, mkt.reindex(idx).fillna(0), level.reindex(idx), eps)
        out.update({"CAGR": _ann(r), "CAGR_matched_mix": _ann(mix), "max_drawdown": _mdd(r), "max_drawdown_matched_mix": _mdd(mix),
                    "matched_mix_weights": {**{kk: round(float(v), 4) for kk, v in wbar.items()}, "cash": round(float(cashbar), 4)},
                    "turnover_one_way_per_year": float(bk.traded.sum() / yrs / 2), "costs_per_year": float(bk.costs.sum() / yrs),
                    "false_DEFEND_calls_per_calm_year": pv["false_pivots_per_calm_year"]})
        return out

    res, gate = {}, {}
    sign = lambda x: "+" if x > 0 else "-"
    for bi, br_ in enumerate(("eq", "drift")):              # R14(c): both base readings
        o = 100 * bi
        rr = {"H1": stats(st1, f"H1_{br_}", k=10 + o, base_reading=br_),
              "H1_at_2x_costs": stats(st1, f"H1_2x_{br_}", fee=20.0, k=20 + o, base_reading=br_),
              "price_only_control": stats(st0, f"H1_price_only_{br_}", k=30 + o, base_reading=br_),
              "price_only_at_2x": stats(st0, f"H1_price_only_2x_{br_}", fee=20.0, k=40 + o, base_reading=br_),
              "H3": stats(st3, f"H3_{br_}", k=50 + o, base_reading=br_),
              "H3_at_2x_costs": stats(st3, f"H3_2x_{br_}", fee=20.0, k=60 + o, base_reading=br_),
              "cash_ablation": stats(st1, f"H1_cash_ablation_{br_}", cash_def=True, k=70 + o, base_reading=br_)}
        idx = books[f"H1_{br_}"].returns.index
        d = books[f"H1_{br_}"].returns - books[f"H1_price_only_{br_}"].returns.reindex(idx).fillna(0)
        h2 = {"full": _diff_stat(d.values, np.zeros(len(d)), seed0 + 700 + o, B_)}
        for e, (a_, z) in eras.items():
            m = (idx >= a_) & (idx <= z)
            h2[e] = {"ann": float(d[m].mean() * v2.ann_factor(idx[m]))}
        rr["H2_paired_H1_minus_price_only"] = h2
        res[f"base_{br_}"] = rr
        gate[f"base_{br_}"] = {h_: {e: sign(rr[h_]["eras"][e]["window_excess"]) for e in eras} for h_ in ("H1", "H3")}
        gate[f"base_{br_}"]["H2"] = {e: sign(h2[e]["ann"]) for e in eras}
    integrity = {"window": [str(start.date()), str(end.date())],
                 "sessions_per_era": {e: int(((idx >= a_) & (idx <= z)).sum()) for e, (a_, z) in eras.items()},
                 "offence_members_min_max": [int(bd["n_members"][idx].min()), int(bd["n_members"][idx].max())],
                 "deferred_executions_total": int(sum(v.meta["deferred_executions"] for v in books.values())),
                 "days_holding_after_last_close_total": int(sum(v.meta["days_holding_an_asset_after_its_last_close"] for v in books.values())),
                 "dropped_industry_days": int(legs.dropped_industry_days),
                 "state_session_counts": {k_: {nm: int((st.reindex(idx) == v).sum()) for nm, v in (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))}
                                          for k_, st in (("H1", st1), ("price_only", st0), ("H3", st3))},
                 "episodes_found": len(eps)}
    res.update({"label": "STAGE 1 of R13 (pre-1998; previously examined by Pro run B; not clean). Sealed.",
                "header_sha256": v2.FROZEN_V2_SHA256, "selected_setting": f"h{h:g}_b{b:g}", "integrity": integrity,
                "seeds": SEEDS, "B": B_, "block": BLOCK, "block_sensitivity": BLOCK_SENS})
    return res, gate, integrity


def blind_stage1(ind_path, fact_path, sealed_path, gate_path, B_=B_STAGE, engine_commit=None):
    """Compute stage 1, write everything sealed, write the gate file, print only signs, gate and counts."""
    import json
    res, gate, integ = compute_pre1998(ind_path, fact_path, B_)
    sha = v2.write_sealed(res, sealed_path)
    gate_open = any(all(gate[b_][h_][e] == "+" for b_ in gate for e in gate[b_][h_]) for h_ in ("H1", "H3"))
    g = {"schema": "rotation_core.stage1_gate/v2", "header_sha256": v2.FROZEN_V2_SHA256, "engine_commit": engine_commit,
         "selected_setting": res["selected_setting"], "gate_signs": gate,
         "gate_rule": "open if H1 or H3 has a positive excess over its era-alone matched mix at 10 bp in both eras "
                      "under BOTH base readings (R14(c))",
         "gate_open": bool(gate_open), "integrity": integ, "sealed_path": str(sealed_path), "sealed_sha256": sha}
    Path(gate_path).write_text(json.dumps(g, indent=1) + "\n")
    print(json.dumps({"gate_signs": gate, "gate_open": gate_open, "integrity": integ, "sealed_sha256": sha}, indent=1))
    return g


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--stage", choices=["select", "pre1998", "h2020_2025", "confirm"])
    ap.add_argument("--dry-run-stage1-fixture", metavar="DIR",
                    help="run stage 1 end to end on a SYNTHETIC fixture directory (refuses real data paths); writes nothing")
    a = ap.parse_args()
    if a.dry_run_stage1_fixture:
        fx = Path(a.dry_run_stage1_fixture).resolve()
        if "rotation-core/data" in str(fx) or str(fx).startswith(str(ROOT)):
            raise SystemExit("refused: fixture dry run accepts only a synthetic fixture directory")
        v2.verify_header_v2(FROZEN)
        if not v2.SELECTION_RESULT.exists():          # before the R15 rerun exists, the dry run reads 1ca5228b3c's file
            v2.SELECTION_RESULT = ROOT / "research/rotation_core/results_v2_selection.json"
        out = fx / "dry_run_out"; out.mkdir(exist_ok=True)
        for f in out.iterdir():
            f.chmod(0o600); f.unlink()
        blind_stage1(fx / "49_Industry_Portfolios_Daily.csv", fx / "F-F_Research_Data_Factors_daily.csv",
                     out / "sealed_stage1.json", out / "gate.json", B_=50, engine_commit="fixture")
        print("stage-1 fixture dry run OK (synthetic data; blind output; no real pre-1998 statistic computed)")
        return 0
    if a.dry_run:
        out = pipeline("2019-12-31", IND_D)
        import json
        print(json.dumps(out, indent=1))
        print("dry run OK: structure only; no return, contrast or selection printed or written")
        return 0
    if not FROZEN.exists():
        raise SystemExit("refused: protocol_header_v2.json is not frozen")
    v2.verify_header_v2(FROZEN)
    if a.stage == "pre1998":
        rel1 = v2.stage1_release()
        if v2.STAGE1_GATE.exists() or v2.STAGE1_SEALED.exists():
            raise SystemExit("refused: stage 1 already run; run once")
        blind_stage1(IND_D, FACT, v2.STAGE1_SEALED, v2.STAGE1_GATE, engine_commit=rel1["engine_commit"])
        print("stage 1 done: commit research/rotation_core/results_v2_stage1_gate.json; the sealed file stays unopened")
        return 0
    if a.stage in ("h2020_2025", "confirm"):
        r2 = v2.stage2_release()          # raises unless release 2 is committed and stage-1 result satisfies it
        if (ROOT / "research/rotation_core/results_v2_stage2_2020_2025.json").exists():
            raise SystemExit("refused: stage 2 already run; run once")
        raise SystemExit(f"stage 2 released (opened by {r2['_opened_by']}); the stage-2 computation (all header "
                         "configurations incl. tradable funds and pooled Holm) is wired after the release is committed")
    if a.stage == "select":
        import json
        if OUT_J.exists():
            raise SystemExit("refused: selection already run (results_v2_selection.json exists); run once")
        res = run_selection()
        OUT_J.write_text(json.dumps(res, indent=1, default=float) + "\n")
        from scripts.rotation_core_v2_report import write_selection_md
        write_selection_md(res, OUT_M)
        print("wrote", OUT_J, OUT_M, "selected:", res["selection"]["selected"])
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
