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


def _yahoo_tr(t):
    d = pd.read_parquet(YAHOO / f"{t}.parquet")
    x = d["Adj Close"].astype(float); x.index = pd.to_datetime(d.index).normalize()
    x = x[(x.index >= WARMUP_FROM) & (x.index <= SEL_END)]
    return x.pct_change(fill_method=None)


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

    def book_and_stats(st, tag, fee=10.0, cash_def=False, seed=0):
        bk = v2.simulate_states(st, legs, rf, SEL_START, SEL_END, cash_for_defend=cash_def, fee_bp=fee, name=tag)
        idx = bk.returns.index
        mm = pd.Series(True, index=idx)
        mc = v2.matched_contrast(bk, legs.returns, rf, mm, B=10_000, seed=20261111 + seed)
        r = bk.returns
        W = bk.holdings[["OFF", "DEF", "BASE"]]
        wbar = W.mean(); cashbar = 1 - wbar.sum()
        mix = (legs.returns.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0) * wbar).sum(axis=1) + cashbar * rf.reindex(idx).fillna(0)
        yrs = len(r) / 252
        defw = (st.reindex(idx) == v2.DEFEND).astype(float)
        weight = (1 - defw)          # risk-off = DEFEND state held after the close
        pv = rc.pivot_table(weight, r, mkt.reindex(idx).fillna(0), level.reindex(idx), eps)
        return bk, {
            "vs_matched_mix": mc,
            "vs_SPY": _diff_stat(r.values, spy.reindex(idx).fillna(0).values, 20261111 + 100 + seed),
            "vs_RSP_or_stated_EW_proxy_before_2003_05": _diff_stat(r.values, rsp_line.reindex(idx).fillna(0).values, 20261111 + 200 + seed),
            "vs_BASE_equal_weight_industries": _diff_stat(r.values, base.reindex(idx).fillna(0).values, 20261111 + 300 + seed),
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
        bk1, s1 = book_and_stats(st1, "H1", seed=10 * i)
        bk0, s0 = book_and_stats(st0, "H1_price_only", seed=10 * i + 1)
        _, s1x = book_and_stats(st1, "H1_2x", fee=20.0, seed=10 * i + 2)
        bkc, sc = book_and_stats(st1, "H1_cash_ablation", cash_def=True, seed=10 * i + 3)
        idx = bk1.returns.index
        h2 = _diff_stat(bk1.returns.values, bk0.returns.reindex(idx).fillna(0).values, 20261111 + 500 + i)
        res["settings"][f"h{h}_b{b}"] = {"H1": s1, "H1_at_2x_costs": {"vs_matched_mix": s1x["vs_matched_mix"],
                                          "costs_per_year": s1x["costs_per_year"]},
                                          "price_only_control": s0, "H2_paired_H1_minus_price_only": h2,
                                          "cash_ablation": sc}
    st3 = v2.h3_states(legs)
    _, s3 = book_and_stats(st3, "H3", seed=99)
    res["H3"] = s3
    obs = {k: v["H1"]["vs_matched_mix"]["observed"] for k, v in res["settings"].items()}
    order = {"h3_b25.0": (3, -25.0), "h3_b37.5": (3, -37.5), "h5_b25.0": (5, -25.0), "h5_b37.5": (5, -37.5)}
    best = max(obs.values())
    ties = [k for k, v in obs.items() if abs(v - best) < 1e-9]
    sel = sorted(ties, key=lambda k: order[k])[0]
    res["selection"] = {"rule": "highest H1 excess over its matched mix; exact tie -> smaller h, then larger b",
                        "observed_by_setting": obs, "selected": sel,
                        "inherit": "H2's price-only control and the cash ablation use the selected setting"}
    return res


STAGE1_OUT_J = ROOT / "research/rotation_core/results_v2_stage1_pre1998.json"
STAGE1_OUT_M = ROOT / "research/rotation_core/RESULTS_V2_STAGE1_PRE1998.md"
SELECTED = (3, 25.0)                     # selection 1ca5228b3c (h3_b25), inherited by H2 control and ablation
ERAS = {"E1_1928_1945": ("1928-01-01", "1945-12-31"), "E2_1946_1997": ("1946-01-01", "1997-12-31")}


def run_stage1(ind_path=IND_D, fact_path=FACT, B_=10_000):
    """Stage 1 of R13: pre-1998 only. Reads nothing dated after 1997-12-31."""
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
    h, b = SELECTED
    st1 = v2.h1_states(rel, bd, h, b); st0 = v2.h1_states(rel, bd, h, b, use_breadth=False); st3 = v2.h3_states(legs)
    start = max([pd.Timestamp("1928-01-02")] + [x.first_valid_index() for x in (st1, st0, st3)])
    s = vw.index
    ew_proxy = ew.where(vw.notna().cumsum() >= 252).mean(axis=1)
    level = (1 + mkt.reindex(s).fillna(0)).cumprod()
    eps = {}
    for name, (a, b2, c) in v1.LPEAK.items():
        ep = rc.find_episode(level[(s >= start) & (s <= end)], a, b2, c)
        if ep:
            eps[name] = ep

    def stats(st, tag, fee=10.0, cash_def=False, seed=0):
        bk = v2.simulate_states(st, legs, rf, start, end, cash_for_defend=cash_def, fee_bp=fee, name=tag)
        idx = bk.returns.index; r = bk.returns
        full = pd.Series(True, index=idx)
        out = {"vs_matched_mix": v2.matched_contrast(bk, legs.returns, rf, full, B=B_, seed=20261113 + seed), "eras": {}}
        for e, (a, z) in ERAS.items():
            em = pd.Series((idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z)), index=idx)
            out["eras"][e] = v2.matched_contrast(bk, legs.returns, rf, em, B=B_, seed=20261113 + seed + 50)
        W = bk.holdings[["OFF", "DEF", "BASE"]]; wbar = W.mean(); cashbar = 1 - wbar.sum()
        mix = (legs.returns.loc[idx, ["OFF", "DEF", "BASE"]].fillna(0) * wbar).sum(axis=1) + cashbar * rf.reindex(idx).fillna(0)
        yrs = len(r) / 252
        for nm, ref in (("vs_French_market_(SPY_yardstick)", mkt), ("vs_EW_proxy_(RSP_yardstick)", ew_proxy),
                        ("vs_BASE_equal_weight_industries", legs.returns["BASE"])):
            out[nm] = _diff_stat(r.values, ref.reindex(idx).fillna(0).values, 20261113 + 300 + seed, B_)
        pv = rc.pivot_table((1 - (st.reindex(idx) == v2.DEFEND).astype(float)), r, mkt.reindex(idx).fillna(0),
                            level.reindex(idx), eps)
        out.update({"CAGR": _ann(r), "CAGR_matched_mix": _ann(mix), "max_drawdown": _mdd(r), "max_drawdown_matched_mix": _mdd(mix),
                    "matched_mix_weights": {**{k: round(float(v), 4) for k, v in wbar.items()}, "cash": round(float(cashbar), 4)},
                    "turnover_one_way_per_year": float(bk.traded.sum() / yrs / 2), "costs_per_year": float(bk.costs.sum() / yrs),
                    "deferred_executions": bk.meta["deferred_executions"],
                    "false_DEFEND_calls_per_calm_year": pv["false_pivots_per_calm_year"],
                    "share": {k: round(float((st.reindex(idx) == v).mean()), 3) for k, v in (("NEUTRAL", 0), ("DEFEND", 1), ("ATTACK", 2))}})
        return bk, out

    bk1, s1 = stats(st1, "H1", seed=1)
    bk0, s0 = stats(st0, "H1_price_only", seed=2)
    _, s1x = stats(st1, "H1_2x", fee=20.0, seed=3)
    _, s3x = stats(st3, "H3_2x", fee=20.0, seed=4)
    _, sc = stats(st1, "H1_cash_ablation", cash_def=True, seed=5)
    _, s3 = stats(st3, "H3", seed=6)
    idx = bk1.returns.index
    h2 = {"full": _diff_stat(bk1.returns.values, bk0.returns.reindex(idx).fillna(0).values, 20261113 + 700, B_)}
    for e, (a, z) in ERAS.items():
        m = (idx >= pd.Timestamp(a)) & (idx <= pd.Timestamp(z))
        h2[e] = _diff_stat(bk1.returns.values[m], bk0.returns.reindex(idx).fillna(0).values[m], 20261113 + 710, B_)
    eras = {"H1": {e: s1["eras"][e]["observed"] for e in ERAS}, "H3": {e: s3["eras"][e]["observed"] for e in ERAS},
            "H2": {e: h2[e]["ann"] for e in ERAS}}
    return {"label": "STAGE 1 of R13: pre-1998 confirmation window (previously examined by Pro run B; not clean). "
                     "No pooled Holm p at this stage.",
            "header_sha256": v2.FROZEN_V2_SHA256, "selected_setting": "h3_b25.0", "window": [str(start.date()), str(end.date())],
            "dropped_industry_days": legs.dropped_industry_days,
            "episodes": {k: {"peak": str(v["peak"].date()), "trough": str(v["trough"].date())} for k, v in eps.items()},
            "H1": s1, "H1_at_2x_costs": s1x, "price_only_control": s0, "H2_paired_H1_minus_price_only": h2,
            "H3": s3, "H3_at_2x_costs": s3x, "cash_ablation": sc, "eras": eras,
            "opening_condition_H1_or_H3_positive_in_both_eras": {
                h_: all(eras[h_][e] > 0 for e in ERAS) for h_ in ("H1", "H3")}}


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
        res = run_stage1(fx / "49_Industry_Portfolios_Daily.csv", fx / "F-F_Research_Data_Factors_daily.csv", B_=50)
        print({"window": res["window"], "keys": sorted(res), "eras_present": sorted(res["eras"]["H1"]),
               "dropped_industry_days": res["dropped_industry_days"], "episodes": len(res["episodes"])})
        print("stage-1 fixture dry run OK (synthetic data; no real pre-1998 statistic computed or written)")
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
        import json
        v2.stage1_release()
        if STAGE1_OUT_J.exists():
            raise SystemExit("refused: stage 1 already run (results_v2_stage1_pre1998.json exists); run once")
        res = run_stage1()
        STAGE1_OUT_J.write_text(json.dumps(res, indent=1, default=float) + "\n")
        from scripts.rotation_core_v2_report import write_stage1_md
        write_stage1_md(res, STAGE1_OUT_M)
        print("wrote", STAGE1_OUT_J, STAGE1_OUT_M, "opening condition:", res["opening_condition_H1_or_H3_positive_in_both_eras"])
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
