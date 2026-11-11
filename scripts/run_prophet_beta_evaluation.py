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
    "X6_exposure_matched_reference": "Exposure-weight arithmetic reference only (SPY/BIL at the book's invested weight)",
}


def sha_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write_artifact_atomic(out: Path, text: str) -> None:
    """Write the artifact via temp file + rename so readers never see a partial.

    A crash or timeout mid-write leaves at most a ``.beta_evaluation.tmp.*``
    sibling behind; the previous committed artifact stays intact until the
    rename. The nightly step removes stale temp siblings before each run.
    """
    tmp = out.with_name(f".beta_evaluation.tmp.{os.getpid()}")
    try:
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, out)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def git(*args) -> str:
    try:
        return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load_jsonl(p: Path) -> tuple[list[dict], int]:
    """Parse JSONL, skipping blank lines and ``#`` documentation comments.

    The malformed-row counter is reserved for actual bad data rows; schema comment
    headers are not data defects (review NOTE).
    """
    rows, bad = [], 0
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
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


def _pp(x: float | None, signed: bool = True) -> str:
    if x is None:
        return "n/a"
    return f"{x * 100:+.1f} pp" if signed else f"{x * 100:.1f}%"


def _pct(x: float | None) -> str:
    """A standalone return is a percentage, not a percentage-point difference."""
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def _ci_pp(c) -> str:
    return "n/a" if not c else f"[{c[0] * 100:+.1f}, {c[1] * 100:+.1f}] pp"


def plain_words(a: dict) -> tuple[list[str], list[str]]:
    """Plain-language headline and limitations computed from the artifact's own numbers."""
    c = {r["id"]: r for r in a["comparators"]}
    k = {r["id"]: r for r in a["contrasts"]["rows"]}
    c6, w = c["C6_exact_incumbent_prophet"], a["window"]
    d6 = a["post_hoc_diagnostics"]["C6_exact_incumbent_prophet"]
    es = a["event_study"]["horizons"]
    pop = a["population"]["excluded_cohort"]
    head = [
        f"Release level: descriptive only (L0). The window is {w['sessions']} sessions; the predeclared "
        f"minimum for any accepted historical claim is 252 sessions including an 8% market drawdown.",
        f"Market over the window: SPY {_pct(w['spy_total_return'])} total return, deepest drawdown {_pct(w['spy_max_drawdown'])}.",
        f"Population: live-published plans only. {pop['era_plans_excluded']} outage-reconstructed plans that no user "
        f"could see on their nominal publication dates are excluded from every headline number (deviation D5); "
        f"the superseded as-run numbers are retained under sensitivity.superseded_as_run.",
        f"Incumbent Prophet book (as built, {c6['sample']['positions']} positions): {_pct(c6['total_net_return'])} net, "
        f"{_pp(c6['vs_passive_market']['total_diff'])} versus SPY, 95% CI {_ci_pp(c6['vs_passive_market']['total_diff_ci95'])}. "
        f"The interval includes zero: this is not evidence of outperformance, and the sample is far too short.",
        f"Beta capture: beta {c6['beta_vs_market']:.2f} (95% CI {c6['beta_ci95'][0]:.2f} to {c6['beta_ci95'][1]:.2f}), "
        f"mean invested weight {c6['mean_invested'] * 100:.0f}%; upside capture {c6['upside_capture']:.2f}, "
        f"downside capture {c6['downside_capture']:.2f}.",
        f"Without its largest single contributor ({d6['without_top_contributor']['dropped_asset']}) the book is "
        f"{_pp(d6['without_top_contributor']['excess_total_vs_spy'])} versus SPY "
        f"(CI {_ci_pp(d6['without_top_contributor']['excess_total_ci95'])}).",
        f"Live-published plans held for a fixed 21 sessions without Prophet's exits differed from SPY by "
        f"{_pp(es['21']['excess_vs_spy']['mean'])} on average (date-cluster CI {_ci_pp(es['21']['excess_vs_spy']['ci95_date_cluster'])}); "
        + ("most of that gap was the stock versus its own sector ETF, not the sector choice."
         if abs(es["21"]["stock_minus_sector_etf"]["mean"]) > abs(es["21"]["sector_etf_minus_spy"]["mean"])
         else "most of that gap came from the sector choice, not the stock versus its sector."),
        "Sector rotation alone, sector-neutral member selection alone and their combination did not beat SPY on this "
        f"window (K3 {_pp(k['K3']['ann_diff'])}/yr, K4 {_pp(k['K4']['ann_diff'])}/yr, K5 {_pp(k['K5']['ann_diff'])}/yr "
        "annualised; none significant after Holm). Insignificant results mean value is not shown, not that there is none.",
        "The exposure-matched reference (X6) is an exposure-weight arithmetic reference only: it matches risky weight "
        "alone, and because the book is essentially fully invested, K2 nearly repeats the SPY comparison (K1) and "
        "cannot identify member-selection value.",
        "Prophet plans inside leading sectors did better than plans outside them in this window "
        f"(K7 {_pp(k['K7']['ann_diff'])}/yr annualised, Holm p {k['K7']['p_holm']:.2f}); this is not significant"
        + (" and its largest contributor is the same single name." if
           a["post_hoc_diagnostics"]["C6A_context_aligned_prophet"]["without_top_contributor"]["dropped_asset"]
           == d6["without_top_contributor"]["dropped_asset"] else "."),
        "Nothing here shows that sector context or member selection adds value beyond market participation.",
    ]
    lim = [
        f"Short sample: one {a['window']['sessions']}-session window (SPY {_pp(a['window']['spy_total_return'])}); "
        "no rebound or crash regime was observed.",
        "Annualised differentials from 63 daily returns are very noisy; read total-window differences and their intervals.",
        f"Population (deviation D5): {pop['era_plans_excluded']} outage-reconstructed plans "
        f"({pop['of_which_replayed_receipted_bake']} receipted replays, "
        f"{pop['of_which_synthetic_board_reconstructions']} synthetic-board reconstructions) are excluded because "
        "their earliest auditable availability is after their nominal publication session; the correction was made "
        "after outcomes were seen, follows a rule that predates the evaluation, and lowers the headline.",
        "X6 is an exposure-weight arithmetic reference, not a selection-matched comparator: it matches only risky "
        "weight, so K2 nearly repeats K1. A comparator matched on eligible cohort, concentration, sector/factor "
        "exposure, timing and costs requires a new pre-declared protocol; X6 is not replaced retrospectively.",
        a["population"]["mrna"]["price_authentication"] + "; it affects any population that admits the replayed plans.",
        "S&P 1500 point-in-time membership has no recorded change after 2026-06-02; "
        f"{len(a['coverage']['member_universe_missing_price_files'])} point-in-time members had no price file and were excluded.",
        "Sector labels are current-basis GICS, not the classification in force at each date.",
        "Prophet plans are read from the 2026-11-09 plan snapshot, not each plan's as-published bytes; entries use the "
        "publication clock and close-only fills, so results differ from the plan record's own same-bar outcomes.",
        "Model book: equal weight across open positions (per position, not per distinct ticker; no same-ticker "
        "overlaps occur in this sample, so the two coincide here). It is not user holdings, a portfolio "
        "recommendation or sizing advice.",
        "The event-study date-cluster intervals treat publication dates as independent although nearby dates share "
        "overlapping market paths, so those intervals are likely too narrow.",
        "Issuer-excluded peer counts are unavailable: identity is the listing ticker only.",
        "The eight catalog sleeves cannot be evaluated: plans carry no sleeve link. admission_class strata are reported instead.",
    ]
    return head, lim


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
    deviations: list[dict] = [
        {"id": "D1", "kind": "naming", "when": "before outcome access",
         "what": "reason/key names derived from 'ledger' renamed to 'recorded_*' / 'resolution_log'",
         "why": "lane-8 validator forbids key substrings incl. 'edge' (contained in 'ledger'); no method change"},
        {"id": "D2", "kind": "added_diagnostic", "when": "after outcome access",
         "what": "post_hoc_diagnostics: per-asset contribution concentration, concurrent position counts, Prophet books re-run without their single largest contributor",
         "why": "the C6 book's result was visibly driven by one name; disclosed as descriptive only, cannot change any release level or threshold"},
        {"id": "D3", "kind": "implementation_note", "when": "after outcome access",
         "what": "the last scheduled rule rebalance (decision 2026-11-05) executes at the final close 2026-11-06; its trading cost has no following return day and is not charged",
         "why": "header schedule executes while t+1 <= last close; omitted cost is at most one rebalance (< 0.1 pp for C3-C5)"},
        {"id": "D4", "kind": "presentation", "when": "after outcome access",
         "what": "event-study horizons with fewer than 5 distinct publication dates are marked status=too_few_dates",
         "why": "H=63 matured for a single publication date; a one-cluster bootstrap interval is degenerate and must not be displayed as uncertainty"},
        {"id": "D5", "kind": "population_correction", "when": "after outcome access (2026-11-10)",
         "what": None,   # filled in below, once the before/after numbers are computed
         "why": "the runner had treated backfilled plans as if historically published although their earliest auditable "
                "availability is their backfill receipt, after their nominal publication session (e.g. MRNA-BULL-20260616 "
                "entered at the 2026-08-10 close although instantiated 2026-08-11T05:32Z). research/PROPHET_OUTAGE_BACKFILL_2026_08.md "
                "forbids presenting reconstructed picks as live historical calls; that rule predates this evaluation. "
                "Correction made after outcomes were seen and it lowers the headline. Source: independent review "
                "REVIEW_beta_evaluation.md (sha256 6296bf4cb77d09e47f1311dbd46cd915a794e050ce7460a228ad821e7b13541a), "
                "BLOCKER finding, accepted by the programme CEO."},
    ]

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

    # ── origination cohorts, detected from the data (deviation D5) ────────────────
    # Non-live (outage-backfilled) plans may not be presented as live historical
    # calls (research/PROPHET_OUTAGE_BACKFILL_2026_08.md). The stamped
    # origination_mode set must equal the disclosure artifact's minted set in BOTH
    # directions; a mismatch is a data defect, not a judgment call.
    bf_disc = json.loads((ROOT / "data/prophet/backfill_disclosures.json").read_text())
    window_kind = {w["id"]: w.get("kind") for w in bf_disc["windows"]}
    minted: dict[str, str] = {}      # plan_id -> window kind (replay | reconstruction)
    for w in bf_disc["backfills"]:
        for m in w["minted"]:
            minted[m["plan_id"]] = window_kind.get(w["id"], w.get("kind"))
    stamped = {p["id"] for p in plans if ev.is_backfilled(p)}
    if stamped != set(minted):
        raise SystemExit(f"origination receipts disagree with stamped plans: "
                         f"stamped-not-minted={sorted(stamped - set(minted))} "
                         f"minted-not-stamped={sorted(set(minted) - stamped)}")
    # every stamped plan must carry its backfill execution receipt
    missing_receipt = [p["id"] for p in plans if ev.is_backfilled(p) and not p.get("backfill_executed_at")]
    if missing_receipt:
        raise SystemExit(f"backfilled plans without backfill_executed_at receipt: {missing_receipt}")
    era_ids = {p["id"] for p in era}
    not_live = frozenset(stamped & era_ids)                     # primary-population exclusions
    replay_ids = {pid for pid, kind in minted.items() if kind == "replay"}
    recon_ids = {pid for pid, kind in minted.items() if kind != "replay"}
    replay_avail = {p["id"]: ev.auditable_first_availability(p) for p in era
                    if p["id"] in replay_ids}
    by_mode: dict[str, int] = {}
    for p in era:
        if ev.is_backfilled(p):
            m = str(p.get("origination_mode"))
            by_mode[m] = by_mode.get(m, 0) + 1

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

    # Prophet positions — primary population is LIVE-PUBLISHED plans only (deviation D5):
    # the 16 outage-reconstructed era plans are excluded with reason not_live_origination.
    positions, excl, extra = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                                not_live_ids=not_live)
    pos_nc, excl_nc, _ = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                            excluded_ids=corrected_ids, not_live_ids=not_live)
    # sensitivity (a): the 13 receipted replays admitted from the first session at/after
    # their actual backfill_executed_at; the 3 synthetic-board reconstructions never admitted.
    pos_s1, excl_s1, _ = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1,
                                            not_live_ids=frozenset(recon_ids & era_ids),
                                            avail_floor=replay_avail)
    # superseded as-run population (the v1 population, retained verbatim; never the headline)
    pos_asrun, _, extra_asrun = ev.build_positions(era, ledger, cal, closes, raw, plan_etf, win0, win1)
    backfilled_entered_asrun = sorted({p.plan_id for p in pos_asrun} & not_live)
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

    # post-hoc descriptive diagnostics (deviation D2: added after outcome access; no threshold change)
    diagnostics = {"label": "POST_HOC_DESCRIPTIVE_DIAGNOSTIC (not in the frozen header; cannot change any release level)"}
    for cid in ("C6_exact_incumbent_prophet", "C7_independent_emergence", "C6A_context_aligned_prophet"):
        contrib = ev.asset_contributions(books[cid], rets)
        pos_sum = float(contrib[contrib > 0].sum())
        top = contrib.index[-1] if len(contrib) else None
        drop = [p for p in subsets[cid] if p.asset != top]
        bk = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(drop, dates), tradable, bps(1.0))
        r_drop = bk.net.to_numpy()
        vs_drop = ev.bootstrap_vs(r_drop, rm, rm, rc, idx10)
        diagnostics[cid] = {
            "concurrent_positions": ev.concurrency(subsets[cid], dates),
            "top_contributors": [{"asset": a, "gross_contribution": float(v)} for a, v in contrib.iloc[::-1][:5].items()],
            "bottom_contributors": [{"asset": a, "gross_contribution": float(v)} for a, v in contrib.iloc[:5].items()],
            "top5_share_of_positive_contribution": (float(contrib.iloc[-5:].sum()) / pos_sum) if pos_sum > 0 else None,
            "without_top_contributor": {"dropped_asset": top, "total_net_return": ev.compound(r_drop),
                                        "excess_total_vs_spy": vs_drop["total_diff"],
                                        "excess_total_ci95": vs_drop["total_diff_ci95"],
                                        "ann_excess_vs_spy": vs_drop["ann_diff"],
                                        "ann_excess_ci95": vs_drop["ann_diff_ci95"],
                                        "beta_vs_market": ev.point_metrics(r_drop, rm, rc)["beta_vs_market"]},
        }

    # event study (policy-free, LIVE-PUBLISHED era plans published in-window; D5)
    pub = extra["pub_sessions"]
    es = ev.event_study(pub, {p["id"]: p["asset"] for p in era}, plan_etf, closes, cal, win1, B, seed)
    for h, v in es.items():
        if v.get("n_dates", 0) and v["n_dates"] < 5:
            v["status"] = "too_few_dates"
    # as-run event study retained for the superseded block (same seed -> v1 numbers)
    es_asrun = ev.event_study(extra_asrun["pub_sessions"], {p["id"]: p["asset"] for p in era},
                              plan_etf, closes, cal, win1, B, seed)
    for h, v in es_asrun.items():
        if v.get("n_dates", 0) and v["n_dates"] < 5:
            v["status"] = "too_few_dates"

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

    # ── deviation D5 blocks: origination population, sensitivity, superseded as-run ──
    # sensitivity (a): replays admitted from their auditable availability (never the headline)
    book_s1 = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(pos_s1, dates), tradable, bps(1.0))
    r_s1 = book_s1.net.to_numpy()
    vs_s1 = ev.bootstrap_vs(r_s1, rm, rm, rc, idx10)
    mrna_s1 = next((p for p in pos_s1 if p.plan_id == "MRNA-BULL-20260616"), None)
    mrna_asrun = next((p for p in pos_asrun if p.plan_id == "MRNA-BULL-20260616"), None)

    # superseded as-run books: the v1 population, recomputed with the same pinned engine,
    # seed, prices and costs so nothing is hidden and the numbers can be compared directly.
    asrun_subsets = {
        "C6_exact_incumbent_prophet": pos_asrun,
        "C7_independent_emergence": [p for p in pos_asrun if p.aligned is False],
        "C6A_context_aligned_prophet": [p for p in pos_asrun if p.aligned is True],
    }
    asrun_rows, asrun_books = {}, {}
    for cid, ps in asrun_subsets.items():
        b = ev.simulate_book(dates, rets, cash_r, ev.prophet_targets(ps, dates), tradable, bps(1.0))
        asrun_books[cid] = b
        r = b.net.to_numpy()
        vs = ev.bootstrap_vs(r, rm, rm, rc, idx10)
        asrun_rows[cid] = {
            "positions": len(ps),
            "total_net_return": ev.compound(r),
            "excess_total_vs_spy": vs["total_diff"], "excess_total_ci95": vs["total_diff_ci95"],
            "ann_excess_vs_spy": vs["ann_diff"], "ann_excess_ci95": vs["ann_diff_ci95"],
            "beta_vs_market": ev.point_metrics(r, rm, rc)["beta_vs_market"],
            "hit_rate_vs_spy": ev.position_hits(ps, closes),
        }
    inv6_asrun = asrun_books["C6_exact_incumbent_prophet"].invested.to_numpy()
    rx6_asrun = inv6_asrun * rm + (1 - inv6_asrun) * rc
    k1_asrun = ev.bootstrap_vs(asrun_books["C6_exact_incumbent_prophet"].net.to_numpy(),
                               series["C1_passive_market"], rm, rc, idx10)
    k2_asrun = ev.bootstrap_vs(asrun_books["C6_exact_incumbent_prophet"].net.to_numpy(), rx6_asrun, rm, rc, idx10)
    k7_asrun = ev.bootstrap_vs(asrun_books["C6A_context_aligned_prophet"].net.to_numpy(),
                               asrun_books["C7_independent_emergence"].net.to_numpy(), rm, rc, idx10)
    exec_by_kind: dict[str, set] = {}
    for p in era:
        if ev.is_backfilled(p):
            exec_by_kind.setdefault(minted[p["id"]], set()).add(str(p["backfill_executed_at"]))

    population = {
        "primary": "live-published incumbent-era plans only (deviation D5): every C6/C7/C6A position, "
                   "event-study plan, attribution leg, coverage count and contrast in this artifact uses this population",
        "excluded_cohort": {
            "reason": ev.NOT_LIVE_EXCLUSION_REASON + ": outage-reconstructed plans are not live historical "
                      "publications and may never be presented as live historical calls "
                      "(research/PROPHET_OUTAGE_BACKFILL_2026_08.md)",
            "detection": "plan rows' origination_mode startswith outage_backfill, each carrying a "
                         "backfill_executed_at receipt, cross-checked in both directions against the minted "
                         "sets in data/prophet/backfill_disclosures.json; the run refuses on any disagreement; "
                         "no hard-coded id list",
            "era_plans_excluded": len(not_live),
            "of_which_replayed_receipted_bake": len(replay_ids & era_ids),
            "of_which_synthetic_board_reconstructions": len(recon_ids & era_ids),
            "origination_mode_counts": by_mode,
            "backfill_executed_at_by_kind": {k: sorted(v) for k, v in exec_by_kind.items()},
            "plan_ids": sorted(not_live),
            "would_have_entered_positions_as_run": len(backfilled_entered_asrun),
            "would_have_entered_ids_as_run": backfilled_entered_asrun,
        },
        "mrna": {
            "note": "MRNA-BULL-20260616 (origination_mode outage_backfill_2026_08_09, instantiated "
                    "2026-08-11T05:32:28Z) is NOT in the primary book: as run it entered at the 2026-08-10 "
                    "close, a session before it existed for any user.",
            "as_run_entry": str(mrna_asrun.entry.date()) if mrna_asrun else None,
            "in_sensitivity_a": mrna_s1 is not None,
            "sensitivity_a_entry": str(mrna_s1.entry.date()) if mrna_s1 else None,
            "price_authentication": "the 2026-08-19 one-day close move of +177% (62.96 -> 174.38; raw and "
                                    "adjusted closes agree; volume 199,252,300) is present only in the single "
                                    "price cache used by this runner and is not authenticated by any second source",
        },
        "review": {"file": "REVIEW_beta_evaluation.md (independent scientific review, 2026-11-10)",
                   "sha256": "6296bf4cb77d09e47f1311dbd46cd915a794e050ce7460a228ad821e7b13541a"},
    }

    sensitivity = {
        "label": "SENSITIVITY — separately labelled, never the headline; descriptive only (L0)",
        "backfill_replays_admitted_after_availability": {
            "definition": f"the {len(replay_ids & era_ids)} receipted replays of the 2026-08-09 bake admitted "
                          f"from the first session at/after their actual backfill_executed_at "
                          f"({sorted(exec_by_kind.get('replay', set()))[0] if exec_by_kind.get('replay') else 'n/a'}); "
                          f"the {len(recon_ids & era_ids)} synthetic-board reconstructions "
                          f"({', '.join(sorted(recon_ids & era_ids))}) never admitted",
            "excluded_from_this_variant": excl_s1,
            "positions": len(pos_s1),
            "total_net_return": ev.compound(r_s1),
            "excess_total_vs_spy": vs_s1["total_diff"], "excess_total_ci95": vs_s1["total_diff_ci95"],
            "ann_excess_vs_spy": vs_s1["ann_diff"], "ann_excess_ci95": vs_s1["ann_diff_ci95"],
            "beta_vs_market": ev.point_metrics(r_s1, rm, rc)["beta_vs_market"],
            "mean_invested": float(book_s1.invested.mean()),
            "hit_rate_vs_spy": ev.position_hits(pos_s1, closes),
        },
        "superseded_as_run": {
            "reason": "v1 as-run population included the 16 outage-reconstructed plans as if historically "
                      "published; superseded by the deviation-D5 primary correction, which lowers the headline. "
                      "Retained verbatim so nothing is hidden; never render as the current result.",
            "same_engine_seed_prices_costs": True,
            "C6_exact_incumbent_prophet": asrun_rows["C6_exact_incumbent_prophet"],
            "C7_independent_emergence": asrun_rows["C7_independent_emergence"],
            "C6A_context_aligned_prophet": asrun_rows["C6A_context_aligned_prophet"],
            "contrasts": {
                "K1_C6_minus_C1": k1_asrun, "K2_C6_minus_X6": k2_asrun, "K7_C6A_minus_C7": k7_asrun,
            },
            "attribution_C6": ev.attribution_bridge(asrun_books["C6_exact_incumbent_prophet"], rets, cash_r,
                                                    ev.asset_sector_map(asrun_subsets["C6_exact_incumbent_prophet"])),
            "event_study_h21": es_asrun["21"],
            "event_study_h42": es_asrun["42"],
        },
    }

    # fill D5's what with the concrete before -> after numbers
    d5 = next(d for d in deviations if d["id"] == "D5")
    c6_now = next(r for r in comp_rows if r["id"] == "C6_exact_incumbent_prophet")
    a6_old = asrun_rows["C6_exact_incumbent_prophet"]

    def _p4(x):
        return f"{x * 100:+.4f}%"

    def _p4pp(x):
        return f"{x * 100:+.4f} pp"

    def _ci4(c):
        return f"[{c[0] * 100:+.3f}, {c[1] * 100:+.3f}]"

    d5["what"] = (
        f"primary population corrected to live-published plans only: {len(not_live)} outage-reconstructed "
        f"incumbent-era plans ({len(replay_ids & era_ids)} receipted replays of the 2026-08-09 bake instantiated "
        f"2026-08-11T05:32:28Z; {len(recon_ids & era_ids)} synthetic-board reconstructions of the never-published "
        f"2026-08-11 board executed 2026-08-13T13:31:33Z) excluded from C6/C7/C6A, the all-published-plans event "
        f"study, attribution, coverage counts and every contrast using them (reason "
        f"{ev.NOT_LIVE_EXCLUSION_REASON}, detected from origination_mode/backfill_executed_at and the disclosure "
        f"receipts, never a hard-coded id list). Before -> after: C6 total {_p4(a6_old['total_net_return'])} -> "
        f"{_p4(c6_now['total_net_return'])}; C6 vs SPY {_p4pp(a6_old['excess_total_vs_spy'])} -> "
        f"{_p4pp(c6_now['vs_passive_market']['total_diff'])} (CI {_ci4(a6_old['excess_total_ci95'])} -> "
        f"{_ci4(c6_now['vs_passive_market']['total_diff_ci95'])} pp); C6 positions {a6_old['positions']} -> "
        f"{c6_now['sample']['positions']}; K1 {_p4pp(k1_asrun['ann_diff'])} -> "
        f"{_p4pp(contrasts['K1']['ann_diff'])}/yr; K2 {_p4pp(k2_asrun['ann_diff'])} -> "
        f"{_p4pp(contrasts['K2']['ann_diff'])}/yr; K7 {_p4pp(k7_asrun['ann_diff'])} -> "
        f"{_p4pp(contrasts['K7']['ann_diff'])}/yr; event study H=21 "
        f"{_p4pp(es_asrun['21']['excess_vs_spy']['mean'])} -> {_p4pp(es['21']['excess_vs_spy']['mean'])} "
        f"(n {es_asrun['21']['excess_vs_spy']['n']} -> {es['21']['excess_vs_spy']['n']}, dates "
        f"{es_asrun['21']['n_dates']} -> {es['21']['n_dates']}). The superseded population is retained verbatim "
        f"under sensitivity.superseded_as_run; sensitivity (a) admits the {len(replay_ids & era_ids)} replays only "
        f"from their auditable availability and admits the synthetic-board reconstructions never."
    )

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
            "resolution_log": {"path": "data/prophet/ledger.jsonl", "sha256": sha_file(led_path),
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
                        "population": "all LIVE-PUBLISHED incumbent-era plans with a publication session in the window "
                                      "(entered or not); outage-reconstructed plans excluded (deviation D5)",
                        "plans": len(pub), "excluded_backfilled_plans": len(not_live), "horizons": es},
        "stability_halves": halves,
        "post_hoc_diagnostics": diagnostics,
        "population": population,
        "sensitivity": sensitivity,
        "failed_leaders": {"c3_sector_picks": c3_total, "lagged_spy_over_hold": c3_failed},
        "rebounds": {"status": "not_evaluable",
                     "reason": "window holds no SPY drawdown deep enough for a rebound test (see window.spy_max_drawdown)"
                     if spy_mdd > -0.08 else "see stability_halves"},
        "coverage": {
            "era_plans": extra["era_plans"],
            "evaluated_positions": len(positions),
            "excluded": excl,
            "entry_shifted_to_publication": extra["entry_shifted_to_publication"],
            "exit_basis": {"recorded_close_date": extra["exit_ledger"], "mechanical_published_levels":
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
    artifact["headline"], artifact["limitations"] = plain_words(artifact)
    artifact["release"]["overall_level"] = min(
        (j["level"] for j in artifact["release"]["jobs"].values()),
        key=lambda lv: artifact["release"]["levels_defined"].index(lv)
        if lv in artifact["release"]["levels_defined"] else -1)
    artifact = ev.json_safe(artifact)
    bad = ev.assert_no_forbidden_keys(artifact)
    if bad:
        raise SystemExit(f"forbidden key names: {bad}")
    write_artifact_atomic(Path(args.out),
                          json.dumps(artifact, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
