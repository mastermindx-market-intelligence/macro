#!/usr/bin/env python3
"""Run the frozen Prophet beta-first evaluation and write ``site/prophet/beta_evaluation.json``.

Usage:
    python scripts/run_prophet_beta_evaluation.py [--prices-dir DIR] [--out PATH] [--bootstrap B]

Refuses to run unless ``research/prophet_v4/beta_first_evaluation/protocol_header_v1.json``
hashes to ``engine.prophet_beta_evaluation.FROZEN_HEADER_SHA256``.

Prices: per-ticker ``<TICKER>.parquet`` files with an adjusted ``close`` and raw
``close_price`` column (the repo's ``data/yahoo`` layout). ``--prices-dir`` defaults to the
repo's ``data/yahoo`` when present, else ``$PROPHET_EVAL_PRICES``. Raw vendor bytes are read,
never written into the repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import prophet_beta_evaluation as ev  # noqa: E402

LABELS = {
    "C1_passive_market": "Passive market (SPY)",
    "C2_simple_participation": "Simple participation (SPY above 200-day average, else cash)",
    "C3_sector_allocation_only": "Sector allocation only (top-3 sector ETFs)",
    "C4_member_selection_only": "Member selection only (sector-neutral S&P 1500 names)",
    "C5_joint_sector_and_name": "Joint sector + member (top-3 sectors x top names)",
    "C6_exact_incumbent_prophet": "Incumbent Prophet book, as built",
    "C7_independent_emergence": "Prophet plans outside leading sectors",
    "C6A_context_aligned_prophet": "Prophet plans inside leading sectors (diagnostic)",
    "X6_exposure_matched_reference": "SPY/cash at Prophet's own invested weight (reference)",
}


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(*args) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load_jsonl(p: Path) -> tuple[list[dict], int]:
    rows, bad = [], 0
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1
    return rows, bad


def load_prices(tickers, prices_dir: Path, cal: pd.DatetimeIndex):
    adj, raw, missing = {}, {}, []
    digest = hashlib.sha256()
    for t in sorted(set(tickers)):
        f = prices_dir / f"{t}.parquet"
        if not f.exists():
            missing.append(t)
            continue
        b = f.read_bytes()
        digest.update(t.encode() + b"\0" + hashlib.sha256(b).digest())
        d = pd.read_parquet(f)
        d.index = pd.to_datetime(d.index)
        d = d[~d.index.duplicated(keep="last")].sort_index()
        adj[t] = d["close"].reindex(cal)
        raw[t] = (d["close_price"] if "close_price" in d.columns else d["close"]).reindex(cal)
    return pd.DataFrame(adj), pd.DataFrame(raw), missing, digest.hexdigest()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", default=None)
    ap.add_argument("--out", default=str(ROOT / "site/prophet/beta_evaluation.json"))
    ap.add_argument("--bootstrap", type=int, default=None)
    args = ap.parse_args(argv)

    header = ev.verify_header(ROOT / ev.HEADER_REL_PATH)          # refuses on mismatch
    st = header["statistics"]
    B = args.bootstrap or 10000
    seed = 20261110
    block, block_alt = 10, int(st["block_length_sensitivity"])
    win0 = pd.Timestamp(header["window"]["first_return_close"])
    win1 = pd.Timestamp(header["window"]["last_close"])
    warm = pd.Timestamp(header["window"]["warmup_from"])
    first_decision = pd.Timestamp("2026-08-07")
    sector_map = header["sector_map"]
    deviations: list[dict] = []

    prices_dir = Path(args.prices_dir or (ROOT / "data/yahoo" if (ROOT / "data/yahoo/SPY.parquet").exists()
                                          else os.environ.get("PROPHET_EVAL_PRICES", "")))
    spy = pd.read_parquet(prices_dir / "SPY.parquet")
    spy.index = pd.to_datetime(spy.index)
    cal = spy.index[(spy.index >= warm) & (spy.index <= win1)]
    dates = list(cal[(cal >= win0) & (cal <= win1)])
    assert len(dates) == header["window"]["sessions_inclusive"], len(dates)

    # inputs
    idx_path, led_path = ROOT / "site/prophet/index.json", ROOT / "data/prophet/ledger.jsonl"
    index = json.loads(idx_path.read_text())
    plans = index["plans"]
    led_rows, led_bad = load_jsonl(led_path)
    ledger = {r["id"]: dict(r) for r in led_rows}
    corr_rows, _ = load_jsonl(ROOT / "data/prophet/ledger_corrections.jsonl")
    applied_corr = 0
    for c in corr_rows:
        if c.get("field") == "close_date" and c.get("corrects_id") in ledger:
            ledger[c["corrects_id"]]["close_date"] = c.get("new_value")
            applied_corr += 1
    quarantine = {q["id"] for q in json.loads((ROOT / "data/prophet/ledger_quarantine.json").read_text())["quarantined"]}
    for q in quarantine:
        ledger.pop(q, None)
    plan_corr_rows, _ = load_jsonl(ROOT / "data/prophet/plan_corrections.jsonl")
    corrected_ids = frozenset(r.get("corrects_id") for r in plan_corr_rows if r.get("corrects_id"))
    pit = pd.read_parquet(ROOT / "data/breadth/sp1500_pit_membership.parquet")
    pits = pd.read_parquet(ROOT / "data/breadth/sp1500_pit_sectors.parquet")
    pit_label = {}
    for tk, g in pits.sort_values("membership_start").groupby("ticker"):
        lab = next((s for s in g["sector"] if isinstance(s, str) and s), None)
        if lab:
            pit_label[tk] = lab
    sector_of_ticker = {tk: sector_map.get(lab) for tk, lab in pit_label.items() if sector_map.get(lab)}

    era = [p for p in plans if p.get("selection_era") == ev.INCUMBENT_ERA]
    plan_etf, disagreements, unmapped = {}, 0, 0
    for p in era:
        br = ((p.get("board_read") or {}).get("fields") or {}).get("sector") or {}
        br_lab = br.get("value") if br.get("state") == "available" else None
        pl = pit_label.get(p["asset"])
        if pl and br_lab and sector_map.get(pl) != sector_map.get(br_lab):
            disagreements += 1
        lab = pl or br_lab
        plan_etf[p["id"]] = sector_map.get(lab) if lab else None
        unmapped += plan_etf[p["id"]] is None

    act = pit[(pit["start_date"] <= win1) & (pit["end_date"].isna() | (pit["end_date"] >= first_decision))]
    tickers = set(ev.SECTOR_ETFS) | {ev.BENCH, ev.CASH} | {p["asset"] for p in era} | set(act["ticker"])
    closes, raw, missing, price_digest = load_prices(tickers, prices_dir, cal)
    rets = closes.pct_change(fill_method=None)
    tradable = closes.notna()
    cash_r = rets[ev.CASH].fillna(0.0)

    def bps(mult):
        etfs = set(ev.SECTOR_ETFS) | {ev.BENCH, ev.CASH}
        return lambda a: (header["execution"]["cost_bps_per_side"]["etf"] if a in etfs
                          else header["execution"]["cost_bps_per_side"]["stock"]) * mult

    # rule targets
    sched = ev.rule_schedule(cal, first_decision, win1, 21)
    t1 = ev.targets_c1(sched)
    t2 = ev.targets_c2(closes, cal, first_decision, win1)
    t3, c3_picks = ev.targets_c3(closes, cal, first_decision, win1)
    pre = cal[cal <= first_decision][-253:]
    sw = ev.style_weights(rets.loc[pre[1:], ev.BENCH], rets.loc[pre[1:], list(ev.SECTOR_ETFS)])
    t4, t5, uni_audit = ev.targets_c4_c5(closes, raw, cal, first_decision, win1, act, sector_of_ticker, sw)

    # Prophet positions
    positions, excl, extra = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1)
    pos_nc, excl_nc, _ = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                            excluded_ids=corrected_ids)
    subsets = {
        "C6_exact_incumbent_prophet": positions,
        "C7_independent_emergence": [p for p in positions if p.aligned is False],
        "C6A_context_aligned_prophet": [p for p in positions if p.aligned is True],
    }
    for cls in ("patience", "confirmation", "early_turn_starter"):
        subsets[f"S_{cls}"] = [p for p in positions if p.admission_class == cls]
    subsets["S6_drop_corrected"] = pos_nc

    targets = {"C1_passive_market": t1, "C2_simple_participation": t2,
               "C3_sector_allocation_only": t3, "C4_member_selection_only": t4,
               "C5_joint_sector_and_name": t5}
    for k, ps in subsets.items():
        targets[k] = ev.prophet_targets(ps, dates)

    books = {k: ev.simulate_book(dates, rets, cash_r, t, tradable, bps(1.0)) for k, t in targets.items()}
    books2 = {k: ev.simulate_book(dates, rets, cash_r, t, tradable, bps(2.0)) for k, t in targets.items()}

    rdates = pd.DatetimeIndex(dates[1:])
    rm = rets.loc[rdates, ev.BENCH].to_numpy()
    rc = cash_r.loc[rdates].to_numpy()
    inv6 = books["C6_exact_incumbent_prophet"].invested.to_numpy()
    rx6 = inv6 * rm + (1 - inv6) * rc
    inv3 = books["C3_sector_allocation_only"].invested.to_numpy()
    rx3 = inv3 * rm + (1 - inv3) * rc
    series = {k: b.net.to_numpy() for k, b in books.items()}
    series["X6_exposure_matched_reference"] = rx6
    series2 = {k: b.net.to_numpy() for k, b in books2.items()}
    series2["X6_exposure_matched_reference"] = rx6
    n = len(rm)
    idx10 = ev.stationary_bootstrap_indices(n, B, block, seed)
    idx21 = ev.stationary_bootstrap_indices(n, B, block_alt, seed)

    # comparator rows
    comp_rows = []
    order = list(ev.COMPARATOR_IDS) + ["C6A_context_aligned_prophet", "X6_exposure_matched_reference"]
    for cid in order:
        r = series[cid]
        pm = ev.point_metrics(r, rm, rc)
        vs = ev.bootstrap_vs(r, rm, rm, rc, idx10)
        b = books.get(cid)
        row = {"id": cid, "label": LABELS[cid], "status": "evaluated", "reason": None,
               "definition": header["comparators"][cid], **pm,
               "vs_passive_market": {k: vs[k] for k in ("ann_diff", "ann_diff_ci95", "total_diff",
                                                        "total_diff_ci95", "p_one_sided")},
               "beta_ci95": vs["beta_ci95"], "upside_capture_ci95": vs["upside_capture_ci95"],
               "downside_capture_ci95": vs["downside_capture_ci95"],
               "window": {"first_return_close": str(win0.date()), "last_close": str(win1.date()),
                          "daily_returns": n}}
        if b is not None:
            traded = b.traded.to_numpy()
            row.update({"mean_invested": float(b.invested.mean()),
                        "time_in_market": float((b.invested > 1e-9).mean()),
                        "annual_turnover": float(traded.sum() / 2 * ev.TRADING_DAYS / n),
                        "costs_paid_total": float(-b.cost.sum()),
                        "no_fill_signals": int(b.no_fill), "stale_asset_days": int(b.stale_asset_days),
                        "no_entry_periods": int((b.invested <= 1e-9).sum())})
            row["at_2x_costs"] = {"total_net_return": ev.compound(series2[cid]),
                                  "ann_excess_vs_spy": float(np.mean(series2[cid] - rm) * ev.TRADING_DAYS)}
        else:
            row.update({"mean_invested": float(inv6.mean()), "time_in_market": float((inv6 > 0).mean()),
                        "annual_turnover": None, "costs_paid_total": 0.0, "no_fill_signals": 0,
                        "no_entry_periods": int((inv6 <= 1e-9).sum()),
                        "note": "reference series, no costs charged"})
        if cid in subsets:
            ps = subsets[cid]
            row["sample"] = {"positions": len(ps), "distinct_assets": len({p.asset for p in ps}),
                             "censored_open_at_window_end": sum(p.censored for p in ps),
                             "resolved": sum(not p.censored for p in ps)}
            row["hit_rate_vs_spy"] = ev.position_hits(ps, closes)
        comp_rows.append(row)

    # halves (descriptive)
    half = n // 2 + 1  # 32 returns in the first half per header
    halves = {}
    for cid in order:
        r = series[cid]
        halves[cid] = {"first": ev.point_metrics(r[:half], rm[:half], rc[:half]),
                       "second": ev.point_metrics(r[half:], rm[half:], rc[half:])}

    # contrasts
    fam = header["statistics"]["confirmatory_family_holm_alpha_0.05"]
    pairs = {"K1": ("C6_exact_incumbent_prophet", "C1_passive_market"),
             "K2": ("C6_exact_incumbent_prophet", "X6_exposure_matched_reference"),
             "K3": ("C3_sector_allocation_only", "C1_passive_market"),
             "K4": ("C4_member_selection_only", "C1_passive_market"),
             "K5": ("C5_joint_sector_and_name", "C4_member_selection_only"),
             "K6": ("C5_joint_sector_and_name", "C3_sector_allocation_only"),
             "K7": ("C6A_context_aligned_prophet", "C7_independent_emergence"),
             "K8": ("C2_simple_participation", "C1_passive_market")}

    def run_contrasts(ser, idx):
        out = {}
        for k, (a, b_) in pairs.items():
            out[k] = ev.bootstrap_vs(ser[a], ser[b_], rm, rc, idx)
        return out

    con = run_contrasts(series, idx10)
    hol = ev.holm({k: v["p_one_sided"] for k, v in con.items()})
    con21 = run_contrasts(series, idx21)
    hol21 = ev.holm({k: v["p_one_sided"] for k, v in con21.items()})
    con2 = run_contrasts(series2, idx10)
    contrasts = {}
    for k, (a, b_) in pairs.items():
        c = con[k]
        contrasts[k] = {"id": k, "a": a, "b": b_, "header_definition": fam[k],
                        "ann_diff": c["ann_diff"], "ann_diff_ci95": c["ann_diff_ci95"],
                        "total_diff": c["total_diff"], "total_diff_ci95": c["total_diff_ci95"],
                        **hol[k],
                        "block21": {"ann_diff_ci95": con21[k]["ann_diff_ci95"], **hol21[k]},
                        "at_2x_costs": {"ann_diff": con2[k]["ann_diff"],
                                        "ann_diff_ci95": con2[k]["ann_diff_ci95"]}}
    sec_pairs = {f"S_{c}": c for c in ("patience", "confirmation", "early_turn_starter")}
    sec_con = {k: ev.bootstrap_vs(series[k], rm, rm, rc, idx10) for k in sec_pairs}
    sec_hol = ev.holm({k: v["p_one_sided"] for k, v in sec_con.items()})
    secondary = {k: {"stratum": c, "positions": len(subsets[k]), "ann_diff_vs_spy": sec_con[k]["ann_diff"],
                     "ann_diff_ci95": sec_con[k]["ann_diff_ci95"], "beta_vs_market":
                     ev.point_metrics(series[k], rm, rc)["beta_vs_market"],
                     "mean_invested": float(books[k].invested.mean()), **sec_hol[k]}
                 for k, c in sec_pairs.items()}
    k3x = ev.bootstrap_vs(series["C3_sector_allocation_only"], rx3, rm, rc, idx10)

    # attribution
    attribution = {}
    for cid in ("C6_exact_incumbent_prophet", "C7_independent_emergence", "C6A_context_aligned_prophet"):
        attribution[cid] = ev.attribution_bridge(books[cid], rets, cash_r, ev.asset_sector_map(subsets[cid]))
        attribution[cid]["unit"] = "fraction (0.01 = 1 percentage point)"

    # event study (policy-free, all era plans published in-window)
    pub = extra["pub_sessions"]
    es = ev.event_study(pub, {p["id"]: p["asset"] for p in era}, plan_etf, closes, cal, win1, B, seed)

    # coverage
    entered_seen = len(positions) + sum(v for k, v in excl.items()
                                        if k in ("no_fill_no_close_at_entry",))
    classified = len(positions) + sum(excl.values())
    spy_mdd = ev.max_drawdown(rm)
    l0_checks = {"classified_share": classified / max(extra["era_plans"], 1),
                 "priced_share": len(positions) / max(entered_seen, 1)}
    c6row = next(r for r in comp_rows if r["id"] == "C6_exact_incumbent_prophet")
    c6vs = ev.bootstrap_vs(series["C6_exact_incumbent_prophet"], rm, rm, rc, idx10)
    rel = ev.release_assessment(
        header, window_sessions=len(dates), spy_mdd=spy_mdd,
        resolved_positions=c6row["sample"]["resolved"], c6=c6row, c6_vs_c1=c6vs,
        c6_stress={"ann_diff": c6row["at_2x_costs"]["ann_excess_vs_spy"]},
        contrasts={k: {"p_holm": v["p_holm"], "ann_diff": v["ann_diff"]} for k, v in contrasts.items()},
        stress_contrasts={k: {"ann_diff": v["at_2x_costs"]["ann_diff"]} for k, v in contrasts.items()},
        k3_vs_exposure=k3x, l0_checks=l0_checks)

    c3_failed = 0
    c3_total = 0
    keys = sorted(c3_picks)
    for i, x in enumerate(keys):
        end = keys[i + 1] if i + 1 < len(keys) else win1
        for s in c3_picks[x]:
            c3_total += 1
            if closes.at[end, s] / closes.at[x, s] < closes.at[end, ev.BENCH] / closes.at[x, ev.BENCH]:
                c3_failed += 1

    code_commit = git("rev-parse", "HEAD")
    dirty = git("status", "--porcelain", "--", "engine/prophet_beta_evaluation.py",
                "scripts/run_prophet_beta_evaluation.py")
    artifact = {
        "schema": ev.SCHEMA,
        "view": "STRATEGY_EVALUATION_VIEW",
        "protocol_ref": ev.HEADER_REL_PATH,
        "protocol": {"id": header["protocol_id"], "header_sha256": ev.FROZEN_HEADER_SHA256,
                     "header_commit": ev.HEADER_COMMIT, "frozen_on": header["frozen_on"]},
        "code": {"commit": code_commit, "harness_dirty": bool(dirty),
                 "module": "engine/prophet_beta_evaluation.py",
                 "runner": "scripts/run_prophet_beta_evaluation.py",
                 "bootstrap": {"B": B, "seed": seed, "mean_block": block, "sensitivity_block": block_alt}},
        "data_clocks": {
            "macro_data_commit": header["data_pin"]["macro_commit"],
            "plans_index": {"path": "site/prophet/index.json", "sha256": sha_file(idx_path),
                            "asof": index.get("asof"), "source_asof": index.get("source_asof"),
                            "computed_at": index.get("computed_at")},
            "ledger": {"path": "data/prophet/ledger.jsonl", "sha256": sha_file(led_path),
                       "rows": len(led_rows), "malformed_lines_skipped": led_bad,
                       "max_asof": max(r.get("asof", "") for r in led_rows),
                       "close_date_corrections_applied": applied_corr,
                       "quarantined_ids_removed": len(quarantine)},
            "pit_membership": {"path": "data/breadth/sp1500_pit_membership.parquet",
                               "sha256": sha_file(ROOT / "data/breadth/sp1500_pit_membership.parquet"),
                               "last_recorded_change": str(max(pit["start_date"].max(), pit["end_date"].max()).date())},
            "prices": {"source": "data/yahoo per-ticker parquet (adjusted close)", "tickers_loaded": closes.shape[1],
                       "digest_sha256": price_digest, "missing_files": len(missing),
                       "last_close_used": str(win1.date())},
        },
        "market": "US", "benchmark": ev.BENCH, "currency": "USD",
        "return_basis": "total_return_adjusted_close", "cash_instrument": ev.CASH,
        "costs_bp_per_side": header["execution"]["cost_bps_per_side"],
        "window": {"first_return_close": str(win0.date()), "last_close": str(win1.date()),
                   "sessions": len(dates), "daily_returns": n,
                   "spy_total_return": ev.compound(rm), "spy_max_drawdown": spy_mdd},
        "release": rel,
        "comparators": comp_rows,
        "contrasts": {"family": "confirmatory K1-K8, Holm alpha 0.05, one-sided (a beats b)",
                      "rows": list(contrasts.values())},
        "secondary_contrasts": {"family": "admission_class strata vs SPY, Holm alpha 0.05", "rows": secondary},
        "exposure_matched_reference": {"definition": header["comparators"]["X6_exposure_matched_reference"],
                                       "invested_fraction": float(inv6.mean()),
                                       "c6_minus_reference": contrasts["K2"],
                                       "c3_minus_reference": {k: k3x[k] for k in ("ann_diff", "ann_diff_ci95", "p_one_sided")}},
        "attribution": attribution,
        "event_study": {"ruler": "engine.grading.forward_metrics next-bar fill; fixed horizons in sessions; policy-free",
                        "population": "all incumbent-era plans with a publication session in the window (entered or not)",
                        "plans": len(pub), "horizons": es},
        "stability_halves": halves,
        "failed_leaders": {"c3_sector_picks": c3_total, "lagged_spy_over_hold": c3_failed},
        "rebounds": {"status": "not_evaluable",
                     "reason": "window holds no SPY drawdown deep enough for a rebound test (see window.spy_max_drawdown)"
                     if spy_mdd > -0.08 else "see stability_halves"},
        "coverage": {
            "era_plans": extra["era_plans"],
            "evaluated_positions": len(positions),
            "excluded": excl,
            "entry_shifted_to_publication": extra["entry_shifted_to_publication"],
            "exit_basis": {"ledger_close_date": extra["exit_ledger"], "mechanical_published_levels":
                           extra["exit_mechanical"], "censored_open_at_window_end": extra["censored"]},
            "classified_share": l0_checks["classified_share"],
            "priced_share": l0_checks["priced_share"],
            "sector": {"unmapped_plans": unmapped, "label_source_disagreements": disagreements,
                       "labels_basis": "current-basis GICS (not era-correct)"},
            "c7_c6a_split": {"outside_leading": len(subsets["C7_independent_emergence"]),
                             "inside_leading": len(subsets["C6A_context_aligned_prophet"]),
                             "unmapped": sum(p.aligned is None for p in positions)},
            "member_universe_by_rebalance": uni_audit,
            "member_universe_missing_price_files": sorted(t for t in missing if t in set(act["ticker"])),
            "c4_sector_weights": {k: float(v) for k, v in sw.items()},
            "issuer_excluded_peers": {"status": "unavailable",
                                      "reason": "listing-ticker identity only; no issuer master join in this harness, so issuer-excluded peer counts are not supportable"},
            "drop_corrected_sensitivity": {"positions": len(pos_nc), "excluded": excl_nc},
        },
        "claims": {
            "observed_relative_performance": {"status": "descriptive",
                                              "basis": "realised window returns with bootstrap CIs; L0 only"},
            "estimated_exposure_residual": {"status": "descriptive",
                                            "basis": "OLS beta/intercept on 63 daily returns; not a validated factor model"},
            "participation_attribution": {"status": "model_book_accounting",
                                          "basis": "equal-weight model book of published plans; not actual holdings or user portfolios"},
            "incremental_selection_value": {"status": "not_established",
                                            "basis": "sample below the predeclared L1 minimum"},
        },
        "limitations": [],
        "deviations": deviations,
        **ev.AUTHORITY,
    }
    artifact = ev.json_safe(artifact)
    bad = ev.assert_no_forbidden_keys(artifact)
    if bad:
        raise SystemExit(f"forbidden key names: {bad}")
    Path(args.out).write_text(json.dumps(artifact, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
