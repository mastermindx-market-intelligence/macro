"""Phase-0 VERIFY: Mastermind GTAA (Moderate) — Track-A live-engine validation. READ-ONLY.

Historical diagnostics for the signal_lab CONFIRMER; these do not automatically promote
the strategy or establish incremental timing alpha. The diagnostics include:
  * DSR >= 0.90 (>= 0.95 'survives') on the realized, net-of-cost, levered book
  * same-sign split-half (already in engine via active_alloc.split_half_oos)
  * leave-one-crisis-out: the Sharpe/MaxDD edge over the DUMB baseline survives dropping
    EACH independent crisis (honest-N constraint)
  * beats a DUMB baseline (here: SPY buy&hold AND 60/40 SPY/IEF — the relevant dumb
    cross-asset book)
  * honest-N adequate (count independent crises, not rows)

This re-runs the native engine (engine/masterminds.py) — no re-implementation — and layers
the gates engine.backtest() does not itself compute (DSR, leave-one-crisis-out, baseline
deltas). The separately reported 60/40 + 30% TSMOM overlay study is not rerun here and
its DSR is not evidence for this GTAA book.

The backtest applies targets next bar via shift(1). Revised macro history, including
carry inputs, still limits point-in-time interpretation; lags and ablations do not
establish that all data were available in their present form at each historical date.

Run:  ./.venv/bin/python scripts/mastermind_moderate_phase0.py
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
# Consume the existing ledger family; validation never registers or appends trials.
TRIAL_FAMILY = "mastermind_moderate_phase0"


def _trial_context(path: Path | None = None) -> tuple[TrialLedger, int]:
    path = path if path is not None else Path(__file__).resolve().parent.parent / "data" / "trial_ledger.jsonl"
    ledger = TrialLedger(path=path)
    if ledger.load_error or ledger.corrupt_lines:
        raise RuntimeError("GTAA trial ledger could not be read completely")
    if not (ledger.declared_budget(TRIAL_FAMILY) or ledger.literal_n(TRIAL_FAMILY)):
        raise RuntimeError("GTAA trial budget is missing; qualification cannot infer a count")
    count = ledger.effective_n(TRIAL_FAMILY)
    if count < len(mm.PROFILES):
        raise RuntimeError("GTAA trial budget is smaller than the exposed profile count")
    return ledger, count


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


def main() -> None:
    print("=" * 100)
    print("MASTERMIND GTAA (MODERATE) — Track-A Phase-0 VERIFY (native engine, READ-ONLY)")
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

    # ---- DSR on the realized levered book, using the existing trial budget ----
    ledger, n_trials = _trial_context()
    print(f"\n### DEFLATED SHARPE — realized moderate net returns, n_trials={n_trials} (existing trial ledger)")
    print(f"  family={TRIAL_FAMILY}; itemized={ledger.literal_n(TRIAL_FAMILY)}; "
          f"declared={ledger.declared_budget(TRIAL_FAMILY)}")
    mom = ret_moments(net)
    sr_d, sk, ku, n = mom
    d = deflated_sharpe(sr_d, sk, ku, n, ledger=ledger, family=TRIAL_FAMILY, trading_year=ANN)
    print(f"  SR(annual)={d['sr_annual']:+.2f}  SR0(annual,haircut)={d['sr0_annual']:+.2f}  "
          f"skew={d['skew']:+.2f}  kurt={d['kurt']:.1f}  T={d['T']}")
    print(f"  DSR = {d['dsr']:.4f}  -> {dsr_verdict(d['dsr'])}")
    # also report DSR with a heavier haircut (treat the whole knob-grid as trials)
    for nt in (8, 16):
        if nt <= n_trials:
            continue
        dd = deflated_sharpe(sr_d, sk, ku, n, n_trials=nt, trading_year=ANN)
        print(f"  (sensitivity: n_trials={nt:2d} -> DSR={dd['dsr']:.4f})")

    # ---- bootstrap CI ------------------------------------------------------
    ci = block_bootstrap_ci(net, block=21, B=5000, ann=ANN)
    if ci:
        print(f"\n### BLOCK-BOOTSTRAP 95% CI (block=21, B=5000)")
        print(f"  Sharpe 95% CI {ci['sharpe_ci']}   MaxDD% 95% CI {ci['maxdd_ci_pct']}   "
              f"P(Sharpe>0)={ci['sharpe_gt0_prob']}")

    # ---- split-half (sign + magnitude) ------------------------------------
    print("\n### SPLIT-HALF (OOS) — Sharpe / MaxDD sign consistency vs SPY")
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
    half_result = ("wins both CAGR halves" if r['oos'].get('robust') else
                   "does not win both CAGR halves" if 'robust' in r['oos'] else
                   "split-half CAGR result unavailable")
    print(f"  engine split_half_oos CAGR-robust flag: {r['oos'].get('robust')} — {half_result}")

    # ---- purged CV ---------------------------------------------------------
    print("\n### PURGED 5-FOLD CV (embargo=63d) — no fold should flip the Sharpe edge vs SPY")
    flips = 0
    for k_, idx_ in purged_folds(net.index, k=5, embargo=63).items():
        s = net.reindex(idx_).dropna()
        sp = spy_bh.reindex(idx_).dropna()
        sh, shp = _sharpe(s.to_numpy(), ANN), _sharpe(sp.to_numpy(), ANN)
        edge = sh - shp
        if edge <= 0:
            flips += 1
        print(f"  {k_}: MM Sharpe={sh:+.2f}  SPY Sharpe={shp:+.2f}  edge={edge:+.2f}  "
              f"(n={len(s)})")
    print(f"  folds where MM does NOT beat SPY: {flips}/5")

    # ---- leave-one-crisis-out ---------------------------------------------
    print("\n### LEAVE-ONE-CRISIS-OUT — does the Sharpe/MaxDD edge vs SPY survive dropping each?")
    holds = 0
    full_edge_sharpe = mm_m["sharpe"] - spy_m["sharpe"]
    full_edge_dd = mm_m["maxdd"] - spy_m["maxdd"]
    print(f"  full-sample edge: dSharpe={full_edge_sharpe:+.2f}  dMaxDD={full_edge_dd:+.1f}pp")
    for nm, a, b in CRISES:
        keep = ~((net.index >= a) & (net.index <= b))
        mmk = m_from_net(net[keep]); spk = m_from_net(spy_bh.reindex(net.index)[keep])
        ds, dd = mmk["sharpe"] - spk["sharpe"], mmk["maxdd"] - spk["maxdd"]
        ok = ds > 0 and dd > 0
        holds += ok
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

    # ---- ablation: remove regime, retaining the unchanged revised-data carry leg ----
    print("\n### ABLATION — macro REGIME layer DISABLED; revised-data carry retained")
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
        no_regime = m_from_net(sc2['net'])
        print(f"  no-regime beats SPY on Sharpe? {no_regime['sharpe'] > spy_m['sharpe']} "
              f"on MaxDD? {no_regime['maxdd'] > spy_m['maxdd']}")
        print(f"  no-regime beats 60/40 on Sharpe? {no_regime['sharpe'] > b64_m['sharpe']} "
              f"on MaxDD? {no_regime['maxdd'] > b64_m['maxdd']}")
        print("  Revised-data carry remains. This ablation does not establish point-in-time correctness.")
    finally:
        M._conviction = orig

    print("\n" + "=" * 100)
    print("SEPARATE HISTORICAL STUDY: 60/40+30% TSMOM overlay DSR 0.9952; not rerun here or attributed to GTAA.")
    print("=" * 100)


if __name__ == "__main__":
    main()
