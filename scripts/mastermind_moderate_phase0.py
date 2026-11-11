"""Historical diagnostics for the native Mastermind GTAA Moderate engine.

Recompute net-of-cost scorecards, historical halves, fixed folds and crisis
omissions after an allocator change. This reads the existing Trial Ledger family;
it does not search parameters, register new trials or promote a Signal Lab tier.
The macro frame contains revised history. Next-bar execution is preserved, but
a two-day lag is not a release-vintage reconstruction or prospective validation.
The separate TSMOM overlay is outside this harness.

Run: python -m scripts.mastermind_moderate_phase0
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
warnings.filterwarnings("ignore")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import masterminds as mm  # noqa: E402
from engine import active_alloc as aa  # noqa: E402
from engine.trial_ledger import TrialLedger  # noqa: E402
from engine.validation import (  # noqa: E402
    ret_moments, deflated_sharpe, dsr_verdict, block_bootstrap_ci,
    purged_folds, _sharpe, _maxdd,
)

ANN = 252
# independent SPY/cross-asset crises spanning 2007-05 (engine _START) → now.
CRISES = [("2008 GFC", "2008-09-01", "2009-03-31"),
          ("2011 EZ/US-dgrade", "2011-07-01", "2011-10-31"),
          ("2015-16 China/oil", "2015-08-01", "2016-02-29"),
          ("2018Q4", "2018-10-01", "2018-12-31"),
          ("2020 COVID", "2020-02-19", "2020-03-31"),
          ("2022 bear", "2022-01-01", "2022-10-31")]
FAMILY = "mastermind_moderate_phase0"


def _trial_ledger() -> TrialLedger:
    ledger = TrialLedger(Path(__file__).resolve().parents[1] / "data" / "trial_ledger.jsonl")
    if FAMILY not in ledger.families():
        raise RuntimeError("GTAA historical diagnostics require the existing trial family")
    return ledger


def m_from_net(net: pd.Series) -> dict:
    net = net.dropna()
    eq = (1 + net).cumprod()
    yrs = (net.index[-1] - net.index[0]).days / 365.25
    cagr = float(eq.iloc[-1]) ** (1 / yrs) - 1 if yrs > 0 else np.nan
    return {"cagr": cagr * 100, "sharpe": _sharpe(net.to_numpy(), ANN),
            "maxdd": _maxdd(net.to_numpy()) * 100, "n": len(net)}


def fmt(label, m, w=26):
    return (f"  {label:<{w}} CAGR={m['cagr']:+6.2f}%  Sharpe={m['sharpe']:+5.2f}  "
            f"MaxDD={m['maxdd']:+7.1f}%  n={m['n']}")


def main() -> dict:
    print("=" * 100)
    print("MASTERMIND GTAA (MODERATE) — historical native-engine diagnostics (READ-ONLY)")
    print("=" * 100)

    P = mm._prices()
    r = mm.backtest("moderate", P=P)
    sc = r["scorecard"]
    net = sc["net"].dropna()                     # realized, net-of-cost, levered book
    bill = mm.ea.bill_yield()

    print(f"  span {sc['years']}y  ({net.index[0].date()}..{net.index[-1].date()})  "
          f"avg_lev {sc['avg_leverage']}  max_lev {sc['max_leverage']}  "
          f"turnover/yr {sc['turnover_annual']}")

    # ---- baselines on the SAME window --------------------------------------
    spy_ret = P["SPY"].pct_change().reindex(net.index).fillna(0.0)
    spy_bh = aa.backtest_portfolio(pd.DataFrame({"SPY": 1.0}, index=P.index),
                                   P[["SPY"]], bill, cost_bps=1.0)["net"].reindex(net.index).dropna()
    w64 = pd.DataFrame({"SPY": 0.6, "IEF": 0.4}, index=P.index)
    b6040 = aa.backtest_portfolio(w64, P[["SPY", "IEF"]], bill, cost_bps=1.0)["net"].reindex(net.index).dropna()

    print("\n### HEADLINE — moderate book vs the DUMB baselines (same window)")
    print(fmt("Mastermind Moderate", m_from_net(net)))
    print(fmt("SPY buy&hold (dumb)", m_from_net(spy_bh)))
    print(fmt("60/40 SPY/IEF (dumb)", m_from_net(b6040)))

    mm_m, spy_m, b64_m = m_from_net(net), m_from_net(spy_bh), m_from_net(b6040)
    beats_spy_sharpe = mm_m["sharpe"] > spy_m["sharpe"]
    beats_64_sharpe = mm_m["sharpe"] > b64_m["sharpe"]
    beats_spy_dd = mm_m["maxdd"] > spy_m["maxdd"]      # less negative = shallower
    beats_64_dd = mm_m["maxdd"] > b64_m["maxdd"]
    print(f"  beats SPY  on Sharpe? {beats_spy_sharpe}   on MaxDD? {beats_spy_dd}")
    print(f"  beats 60/40 on Sharpe? {beats_64_sharpe}   on MaxDD? {beats_64_dd}")

    # Existing family includes the historical search budget; never silently use N=1.
    ledger = _trial_ledger()
    n_trials = ledger.effective_n(FAMILY)
    print(f"\n### DEFLATED SHARPE — existing ledger family {FAMILY}, effective N={n_trials}")
    sr_d, sk, ku, n = ret_moments(net)
    d = deflated_sharpe(sr_d, sk, ku, n, ledger=ledger, family=FAMILY, trading_year=ANN)
    print(f"  SR(annual)={d['sr_annual']:+.2f}  SR0(annual,haircut)={d['sr0_annual']:+.2f}  "
          f"skew={d['skew']:+.2f}  kurt={d['kurt']:.1f}  T={d['T']}")
    print(f"  DSR = {d['dsr']:.4f}  -> {dsr_verdict(d['dsr'])} (statistic only; no tier promotion)")

    # ---- bootstrap CI ------------------------------------------------------
    ci = block_bootstrap_ci(net, block=21, B=5000, ann=ANN)
    if ci:
        print(f"\n### BLOCK-BOOTSTRAP 95% CI (block=21, B=5000)")
        print(f"  Sharpe 95% CI {ci['sharpe_ci']}   MaxDD% 95% CI {ci['maxdd_ci_pct']}   "
              f"P(Sharpe>0)={ci['sharpe_gt0_prob']}")

    # ---- split-half (sign + magnitude) ------------------------------------
    print("\n### HISTORICAL SPLIT — Sharpe / MaxDD comparisons vs SPY")
    nh = len(net)
    h1, h2 = net.iloc[: nh // 2], net.iloc[nh // 2:]
    s1y, s2y = m_from_net(h1), m_from_net(h2)
    spy1, spy2 = m_from_net(spy_bh.iloc[: nh // 2]), m_from_net(spy_bh.iloc[nh // 2:])
    print(fmt("  H1 Mastermind", s1y, 24));  print(fmt("  H1 SPY", spy1, 24))
    print(fmt("  H2 Mastermind", s2y, 24));  print(fmt("  H2 SPY", spy2, 24))
    same_sharpe = np.sign(s1y["sharpe"]) == np.sign(s2y["sharpe"])
    h1_beats = s1y["sharpe"] > spy1["sharpe"] and s1y["maxdd"] > spy1["maxdd"]
    h2_beats = s2y["sharpe"] > spy2["sharpe"] and s2y["maxdd"] > spy2["maxdd"]
    print(f"  Sharpe same-sign across halves: {same_sharpe}")
    print(f"  H1 beats SPY (Sharpe&DD): {h1_beats}    H2 beats SPY (Sharpe&DD): {h2_beats}")
    print(f"  (engine split_half_oos CAGR-robust flag: {r['oos'].get('robust')} — "
          f"this flag measures only whether CAGR beats in both historical halves)")

    # ---- purged CV ---------------------------------------------------------
    print("\n### FIXED PURGED 5-FOLD COMPARISON (embargo=63d) — historical Sharpe differences vs SPY")
    flips = 0
    folds = []
    for k_, idx_ in purged_folds(net.index, k=5, embargo=63).items():
        s = net.reindex(idx_).dropna()
        sp = spy_bh.reindex(idx_).dropna()
        sh, shp = _sharpe(s.to_numpy(), ANN), _sharpe(sp.to_numpy(), ANN)
        edge = sh - shp
        folds.append({"fold": k_, "strategy_sharpe": sh, "spy_sharpe": shp, "delta_sharpe": edge, "n": len(s)})
        if edge <= 0:
            flips += 1
        print(f"  {k_}: MM Sharpe={sh:+.2f}  SPY Sharpe={shp:+.2f}  edge={edge:+.2f}  "
              f"(n={len(s)})")
    print(f"  folds where MM does NOT beat SPY: {flips}/5")

    # ---- leave-one-crisis-out ---------------------------------------------
    print("\n### LEAVE-ONE-CRISIS-OUT — does the Sharpe/MaxDD edge vs SPY survive dropping each?")
    holds = 0
    omissions = []
    full_edge_sharpe = mm_m["sharpe"] - spy_m["sharpe"]
    full_edge_dd = mm_m["maxdd"] - spy_m["maxdd"]
    print(f"  full-sample edge: dSharpe={full_edge_sharpe:+.2f}  dMaxDD={full_edge_dd:+.1f}pp")
    for nm, a, b in CRISES:
        keep = ~((net.index >= a) & (net.index <= b))
        mmk = m_from_net(net[keep]); spk = m_from_net(spy_bh.reindex(net.index)[keep])
        ds, dd = mmk["sharpe"] - spk["sharpe"], mmk["maxdd"] - spk["maxdd"]
        ok = ds > 0 and dd > 0
        holds += ok
        omissions.append({"crisis": nm, "delta_sharpe": ds, "delta_maxdd_pp": dd, "both_positive": bool(ok)})
        print(f"  drop {nm:<18}: dSharpe={ds:+.2f}  dMaxDD={dd:+6.1f}pp  -> "
              f"{'holds' if ok else 'WEAK'}")
    print(f"  crises where edge holds: {holds}/{len(CRISES)}")

    # ---- crisis convexity (absolute) --------------------------------------
    print("\n### CRISIS CONVEXITY — cumulative net return through each window")
    print(f"  {'window':<20}{'Mastermind':>12}{'60/40':>10}{'SPY':>10}")
    def cum(rr, a, b):
        wnd = rr.loc[a:b].dropna()
        return (np.prod(1 + wnd.to_numpy()) - 1) * 100 if len(wnd) else float("nan")
    for nm, a, b in CRISES:
        print(f"  {nm:<20}{cum(net, a, b):>11.1f}%{cum(b6040, a, b):>9.1f}%{cum(spy_bh, a, b):>9.1f}%")

    # ---- robustness: kill the regime layer (the only revised-macro-data leg) ----
    print("\n### SENSITIVITY — macro REGIME layer DISABLED (not a release-vintage test)")
    M = mm
    orig = M._conviction

    def _conv_no_regime(P):
        from engine.cross_asset_trend import tsmom_alloc
        cal, cols = P.index, [a for a in M.ASSETS if a in P.columns]
        trend = pd.DataFrame({a: tsmom_alloc(P[a]) for a in cols}, index=cal)
        carry = pd.DataFrame(0.0, index=cal, columns=cols)
        y10 = M._zscore(M._fred("DGS10")).reindex(cal).ffill()
        oas = M._zscore(M._fred("BAMLH0A0HYM2")).reindex(cal).ffill()
        realy = M._zscore(M._fred("DFII10")).reindex(cal).ffill()
        for a in (set(M.DUR) & set(cols)):
            carry[a] = y10
        for a in (set(M.CRED) & set(cols)):
            carry[a] = (0.5 * y10 + 0.5 * oas).clip(-1, 1)
        if "GC=F" in cols:
            carry["GC=F"] = (-realy).clip(-1, 1)
        xrank = P.pct_change(126).rank(axis=1, pct=True)
        xmom = (2 * xrank - 1).fillna(0.0)
        conv = (0.45 * trend + 0.20 * carry.fillna(0) + 0.15 * xmom) / 0.80   # renorm
        return conv.clip(-1, 1).clip(lower=0.0)

    try:
        M._conviction = _conv_no_regime
        sc2 = M.backtest("moderate", P=P)["scorecard"]
        print(f"  no-regime : Sharpe={sc2['sharpe']}  MaxDD={sc2['maxdd']}  CAGR={sc2['cagr']}  "
              f"(vs full {sc['sharpe']}/{sc['maxdd']}/{sc['cagr']})")
        print(f"  measured no-regime differences vs SPY: Sharpe={sc2['sharpe'] - spy_m['sharpe']:+.2f}, "
              f"MaxDD={sc2['maxdd'] - spy_m['maxdd']:+.1f}pp; not a point-in-time certification")
    finally:
        M._conviction = orig

    # Fixed adversarial control from the existing incrementality question: same
    # universe, warm-up, inverse vol, final limits, cadence, costs and financing;
    # only the four-factor conviction is replaced by one. No parameter search.
    try:
        M._conviction = lambda prices: pd.DataFrame(1.0, index=prices.index, columns=prices.columns)
        control = M.backtest("moderate", P=P)["scorecard"]["net"].reindex(net.index)
    finally:
        M._conviction = orig
    control_m = m_from_net(control)
    control_folds = []
    for fold, dates in purged_folds(net.index, k=5, embargo=63).items():
        control_folds.append({"fold": fold,
            "delta_sharpe": _sharpe(net.reindex(dates).to_numpy(), ANN) - _sharpe(control.reindex(dates).to_numpy(), ANN)})
    control_omissions = []
    for name, start, end in CRISES:
        keep = ~((net.index >= start) & (net.index <= end))
        actual_m, omitted_m = m_from_net(net[keep]), m_from_net(control[keep])
        control_omissions.append({"crisis": name,
            "delta_sharpe": actual_m["sharpe"] - omitted_m["sharpe"],
            "delta_maxdd_pp": actual_m["maxdd"] - omitted_m["maxdd"]})
    incrementality = {"control": control_m,
        "delta_sharpe": mm_m["sharpe"] - control_m["sharpe"],
        "delta_maxdd_pp": mm_m["maxdd"] - control_m["maxdd"],
        "folds": control_folds, "crisis_omissions": control_omissions}
    print("\n### SAME-CHASSIS CONTROL — conviction=1, corrected final caps")
    print(fmt("No-signal chassis", control_m))
    print(f"  conviction increment: Sharpe={incrementality['delta_sharpe']:+.3f}, "
          f"MaxDD={incrementality['delta_maxdd_pp']:+.2f}pp; no tier promotion")

    print("\n" + "=" * 100)
    print("Historical diagnostics only. The separate TSMOM overlay and Signal Lab tiers are unchanged.")
    print("=" * 100)
    return {"family": FAMILY, "effective_n": n_trials, "profile": "moderate",
            "span": [str(net.index[0].date()), str(net.index[-1].date())],
            "strategy": mm_m, "spy": spy_m, "6040": b64_m, "dsr": d,
            "bootstrap": ci, "halves": {"first": s1y, "second": s2y, "spy_first": spy1, "spy_second": spy2},
            "cagr_both_halves": bool(r["oos"].get("robust")), "folds": folds,
            "crisis_omissions": omissions, "incrementality": incrementality,
            "no_regime": {k: sc2[k] for k in ("cagr", "sharpe", "maxdd")},
            "qualification": "Revised macro history; descriptive diagnostics, no prospective validation or tier promotion."}



if __name__ == "__main__":
    main()
