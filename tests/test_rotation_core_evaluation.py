"""Synthetic red->green tests for engine/rotation_core_evaluation.py (no market data)."""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import rotation_core_evaluation as rc

ROOT = Path(__file__).resolve().parents[1]


def _sessions(n=600, start="2000-01-03"):
    return pd.bdate_range(start, periods=n)


def _prices(n=600, seed=1, cols=("SPY",)):
    rng = np.random.default_rng(seed)
    s = _sessions(n)
    return pd.DataFrame({c: 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, n)) for c in cols}, index=s)


# ------------------------------------------------------------------ header guard
def test_header_hash_matches_frozen_file():
    h = rc.verify_header(ROOT / "research/rotation_core/protocol_header_v1.json")
    assert h["protocol_id"] == "rotation-core-historical-v1"


def test_header_mismatch_refuses(tmp_path):
    p = tmp_path / "h.json"
    p.write_text("{}")
    with pytest.raises(rc.HeaderMismatch):
        rc.verify_header(p)


# ------------------------------------------------------------------ execution timing and costs
def test_decision_executes_next_close_and_earns_from_following_day():
    s = _sessions(6)
    rets = pd.DataFrame({"SPY": [0.0, 0.10, 0.20, 0.30, 0.40, 0.50]}, index=s)
    cash = pd.Series(0.0, index=s)
    tgt = pd.DataFrame({"SPY": [np.nan, 1.0, np.nan, np.nan, np.nan, np.nan]}, index=s)  # decided at close of day 1
    b = rc.simulate(tgt, rets, cash, 0.0, "t")
    # executed at close of day 2 -> day-2 return NOT earned, day-3 return earned
    assert b.returns.iloc[2] == pytest.approx(0.0)
    assert b.returns.iloc[3] == pytest.approx(0.30)
    assert b.risky_weight.iloc[2] == 0.0 and b.risky_weight.iloc[3] == pytest.approx(1.0)


def test_cost_charged_on_execution_day_per_side():
    s = _sessions(5)
    rets = pd.DataFrame({"SPY": [0.0] * 5}, index=s)
    cash = pd.Series(0.0, index=s)
    tgt = pd.DataFrame({"SPY": [1.0, 0.0, np.nan, np.nan, np.nan]}, index=s)
    b = rc.simulate(tgt, rets, cash, 10.0, "t")
    assert b.costs.iloc[1] == pytest.approx(0.001)   # buy 1.0 at 10 bp
    assert b.costs.iloc[2] == pytest.approx(0.001)   # sell 1.0 at 10 bp
    assert b.traded.sum() == pytest.approx(2.0)


def test_daily_rule_trades_only_on_change():
    s = _sessions(10)
    rets = pd.DataFrame({"SPY": np.linspace(0.01, -0.01, 10)}, index=s)
    cash = pd.Series(0.0001, index=s)
    tgt = pd.DataFrame({"SPY": [1.0] * 10}, index=s)
    b = rc.simulate(tgt, rets, cash, 5.0, "t")
    assert int((b.traded > 0).sum()) == 1


def test_threshold_rule_rebalances_only_beyond_band():
    s = _sessions(4)
    rets = pd.DataFrame({"SPY": [0.0] * 4}, index=s)
    cash = pd.Series(0.0, index=s)
    tgt = pd.DataFrame({"SPY": [0.5, 0.55, 0.70, 0.70]}, index=s)
    b = rc.simulate(tgt, rets, cash, 0.0, "t", threshold=0.10)
    assert list((b.traded > 0).astype(int)) == [0, 1, 0, 1]


def test_cash_accrues_lagged_yield():
    s = _sessions(3)
    y = pd.Series([5.0, 10.0, 20.0], index=s)
    c = rc.cash_returns(y, s)
    assert c.iloc[0] == 0.0
    assert c.iloc[1] == pytest.approx(1.05 ** (1 / 252) - 1)
    assert c.iloc[2] == pytest.approx(1.10 ** (1 / 252) - 1)


# ------------------------------------------------------------------ no look-ahead in signals
@pytest.mark.parametrize("fn", [
    lambda p: rc.trend_broken(p["SPY"]),
    lambda p: rc.mtf(p["SPY"]),
    lambda p: rc.mtf(p[["SPY", "XLK"]]),
    lambda p: rc.total_return(p, 252, 21),
])
def test_price_signals_do_not_use_future_data(fn):
    p = _prices(700, cols=("SPY", "XLK"))
    cut = 450
    q = p.copy()
    q.iloc[cut + 1:] = q.iloc[cut + 1:] * 3.7   # perturb the future
    a, b = fn(p), fn(q)
    pd.testing.assert_frame_equal(pd.DataFrame(a).iloc[: cut + 1], pd.DataFrame(b).iloc[: cut + 1])


def test_credit_flag_uses_only_observations_before_t():
    s = _sessions(400)
    spread = pd.Series(np.r_[np.full(300, 3.0), np.full(100, 9.0)], index=s)
    c = rc.credit_flag(spread, s, window=252)
    # first high observation is at index 300; flag may only turn on at session 301
    assert c.iloc[300] == 0.0
    assert c.iloc[301] == 1.0
    q = spread.copy(); q.iloc[350:] = 0.1
    c2 = rc.credit_flag(q, s, window=252)
    pd.testing.assert_series_equal(c.iloc[:351], c2.iloc[:351])


def test_sahm_available_after_tenth_business_day_of_next_month():
    s = pd.bdate_range("2008-01-01", "2008-04-30")
    sahm = pd.Series([0.2, 0.6, 0.6], index=pd.to_datetime(["2008-01-01", "2008-02-01", "2008-03-01"]))
    m = rc.sahm_available(sahm, s)
    # Feb 2008 value (0.6) usable from the first session after the 10th business day of March 2008 (2008-03-14)
    assert m.loc["2008-03-14"] == 0.0
    assert m.loc["2008-03-17"] == 1.0


def test_eligibility_counts_priced_sessions():
    p = _prices(300, cols=("SPY", "XLRE"))
    p.loc[p.index[:100], "XLRE"] = np.nan
    el = rc.eligible(p, 150)
    assert not el["XLRE"].iloc[248] and el["XLRE"].iloc[249]


# ------------------------------------------------------------------ statistics
def test_holm_step_down():
    h = rc.holm({"a": 0.001, "b": 0.03, "c": 0.04})
    assert h["a"]["reject_h0"] and not h["b"]["reject_h0"] and not h["c"]["reject_h0"]
    assert h["b"]["p_holm"] == pytest.approx(0.06)


def test_centred_p_is_small_for_strong_positive_and_large_for_zero():
    rng = np.random.default_rng(0)
    a = rng.normal(0.002, 0.01, 2000); b = rng.normal(0.0, 0.01, 2000)
    dist = rc.bootstrap_stat([a, b], rc.stat_mean_diff, 500, 21, 1)
    obs = float((a - b).mean() * 252)
    assert rc.centred_p(dist, obs) < 0.01
    d0 = rc.bootstrap_stat([b, b], rc.stat_mean_diff, 200, 21, 1)
    assert rc.centred_p(d0, 0.0) == 1.0


def test_power_line_sentence():
    pl = rc.power_line(0.02, 10, 0.01, "per year")
    assert "could not" in pl["sentence"] and pl["mde80_holm"] > 0.05
    assert "could have" in rc.power_line(0.001, 10, 0.01, "per year")["sentence"]


# ------------------------------------------------------------------ pivots
def test_pivot_table_exit_and_reentry():
    s = _sessions(400)
    lvl = pd.Series(np.r_[np.linspace(100, 120, 200), np.linspace(120, 80, 100), np.linspace(80, 130, 100)], index=s)
    r = lvl.pct_change().fillna(0.0)
    w = pd.Series(1.0, index=s)
    w.iloc[210:310] = 0.0          # out 10 sessions after the peak (index 199), back 10 after the trough (299)
    ep = rc.find_episode(lvl, s[150], s[220], s[350])
    assert ep["peak"] == s[199] and ep["trough"] == s[299]
    pv = rc.pivot_table(w, r * w.shift(1).fillna(1.0), r, lvl, {"E": ep})
    row = pv["episodes"]["E"]
    assert row["exit_lead_sessions"] == 199 - 210
    assert row["reentry_lag_sessions"] == 310 - 299
    assert row["missed_after_trough"] > 0
    assert pv["false_pivots"] == 0


def test_algorithmic_drawdowns():
    s = _sessions(300)
    lvl = pd.Series(np.r_[np.linspace(100, 100, 50), np.linspace(100, 70, 50), np.linspace(70, 110, 200)], index=s)
    dd = rc.algorithmic_drawdowns(lvl, 0.15)
    assert len(dd) == 1 and dd[0]["drawdown"] == pytest.approx(-0.30)


# ------------------------------------------------------------------ stage guard
def test_stage_h_refused_without_parent_release(monkeypatch):
    import scripts.run_rotation_core_v1 as run
    monkeypatch.setattr(run, "committed_clean", lambda p: p == run.STAGE_D_JSON)
    with pytest.raises(SystemExit) as e:
        run.stage_guard("H")
    assert "HOLDOUT_RELEASE_v1.json" in str(e.value)
    monkeypatch.setattr(run, "committed_clean", lambda p: False)
    with pytest.raises(SystemExit) as e2:
        run.stage_guard("H")
    assert "results_stage_D.json" in str(e2.value)


def test_stage_d_window_ends_before_holdout():
    assert rc.D_END < rc.H_START


# ------------------------------------------------------------------ review-driven tests
def test_always_rebalance_resets_drift_each_decision():
    s = _sessions(6)
    rets = pd.DataFrame({"A": [0.0, 0.5, 0.0, 0.5, 0.0, 0.0], "B": [0.0] * 6}, index=s)
    cash = pd.Series(0.0, index=s)
    tgt = pd.DataFrame({"A": [0.5, np.nan, 0.5, np.nan, np.nan, np.nan], "B": [0.5, np.nan, 0.5, np.nan, np.nan, np.nan]}, index=s)
    b = rc.simulate(tgt, rets, cash, 0.0, "t", always_rebalance=True, equity_cols=("A", "B"))
    assert b.holdings["A"].iloc[4] == pytest.approx(0.5)            # day-3 close reset drift back to target
    assert int((b.traded > 0).sum()) == 2
    nb = rc.simulate(tgt, rets, cash, 0.0, "t", equity_cols=("A", "B"))
    assert int((nb.traded > 0).sum()) == 1                          # change-only rule does not reset
    assert nb.holdings["A"].iloc[4] == pytest.approx(0.75 / 1.25)   # drifted weight kept


def test_pivot_excludes_startup_and_sealed_tail_spells():
    s = _sessions(400)
    lvl = pd.Series(np.linspace(100, 140, 400), index=s)
    r = lvl.pct_change().fillna(0.0)
    w = pd.Series(1.0, index=s)
    w.iloc[0] = 0.0                     # start-up: nothing held before first execution
    w.iloc[380:] = 0.0                  # spell starting in the last 63 sessions
    pv = rc.pivot_table(w, r * w.shift(1).fillna(0.0), r, lvl, {}, first_exec=s[1], sealed_tail=63)
    assert pv["false_pivots"] == 0 and pv["spells_undetermined_sealed"] == 1
    pv2 = rc.pivot_table(w, r, r, lvl, {})
    assert pv2["false_pivots"] == 2


def test_xref_rebuilt_per_era(monkeypatch):
    import scripts.run_rotation_core_v1 as run
    monkeypatch.setattr(run, "B", 50)
    s = pd.bdate_range("2008-01-01", "2011-12-30")
    rng = np.random.default_rng(3)
    spy = pd.Series(rng.normal(0.0004, 0.01, len(s)), index=s)
    cash = pd.Series(0.0001, index=s)
    w = pd.Series(np.where(s <= rc.ERA_SPLIT, 0.2, 1.0), index=s)
    book = rc.Book("c", w * spy + (1 - w) * cash, w, w, pd.DataFrame({"SPY": w}), w * 0, w * 0)
    mask = pd.Series(True, index=s)
    res = run.contrast("x", book.returns, run.XRef(book, spy, cash), cash, "mean", mask, 10, 0.01, "y", 1)
    assert res["x_mean_weight_eras"]["E1"] == pytest.approx(0.2)
    assert res["x_mean_weight_eras"]["E2"] == pytest.approx(1.0)
    assert abs(res["eras"]["E1"]) < 1e-9 and abs(res["eras"]["E2"]) < 1e-9


def test_run_j4_formation_unchanged_by_future_prices():
    from engine import rotation_core_j4 as j4
    rng = np.random.default_rng(7)
    s = pd.bdate_range("2004-01-01", periods=700)
    etf = pd.DataFrame({e: 100 * np.cumprod(1 + rng.normal(0.0003, 0.01, len(s))) for e in ["XLK", "XLF", "XLE", "XLV"]}, index=s)
    spy = etf.mean(axis=1)
    names = {}
    for e in etf.columns:
        er = etf[e].pct_change().fillna(0).values
        for k in range(6):
            names[f"{e}{k}"] = 50 * np.cumprod(1 + er + rng.normal(0, 0.006, len(s)))
    prices = pd.DataFrame(names, index=s)
    pit = pd.DataFrame({"ticker": list(names), "start_date": pd.Timestamp("2000-01-01"), "end_date": pd.NaT, "src": "sp500"})
    me = rc.month_end_sessions(s)
    forms = list(me[(me > s[300]) & (me < s[650])])
    el = rc.eligible(etf)
    a = j4.run_j4(prices, etf, spy, pit, forms, s, el)["records"]
    t0 = forms[2]
    p2 = prices.copy()
    p2.loc[p2.index > t0] *= 1.0 + np.linspace(0, 2, int((p2.index > t0).sum()))[:, None]
    b = j4.run_j4(p2, etf, spy, pit, forms, s, el)["records"]
    for col in ("leading", "lagging", "assigned", "priced"):
        assert a.loc[t0, col] == b.loc[t0, col]


def test_build_artifact_and_markdown_on_stub(tmp_path):
    from scripts.rotation_core_report import build_artifact, write_markdown
    fam = {"J1-A:P1": {"contrast": "J1-A:P1", "kind": "mean", "observed": 0.0, "ci95": [-0.01, 0.01],
                       "p_one_sided_centred": 0.5, "eras": {"E1": 0.0, "E2": 0.0},
                       "power": {"se": 0.01, "mde80_holm": 0.03, "reference_effect": 0.01, "sentence": "x"},
                       "holm": {"p_holm": 1.0, "reject_h0": False}}}
    m = {"ann_return": 0.05, "ann_vol": 0.1, "sharpe": 0.4, "max_drawdown": -0.2, "up_capture_monthly": 1.0,
         "down_capture_monthly": 1.0, "beta_vs_spy": 1.0, "mean_risky_weight": 1.0, "traded_notional_per_year": 0.1,
         "costs_paid_per_year": 0.0, "dsr": {"dsr": 0.5}}
    g = {"J1-A": {"criteria": [{"criterion": "G1 x", "met": False}], "clears_G1_G2_G3_G5_on_D": False}}
    job = {"window_D": ["a", "b"], "metrics": {"B1": m}, "gates": g, "pivots": {}, "selection": {"J1_star": "B3", "p1_observed_D": {}, "J2_star": "B5"},
           "episode_holdings_D": {}}
    res = {"jobs": {"J1": {**job, "family_F1": fam}, "J2": {**job, "family_F2": fam}, "J3": {**job, "family_F3": fam},
                    "J4": {"status": "unavailable", "reason": "stub"},
                    "J5": {"J1_star": "B3", "J2_star": "B5", "point_differences_D": {}, "metrics": {"J5-A": m}}},
           "incumbents": {"family_FI": {}, "J1": {}, "J2-I1": "x"}, "long_history": {"tiers": {}},
           "data_quality": {}, "dsr_trial_count": {}, "deviations": [{"kind": "k", "text": "t"}]}
    hdr = {"protocol_id": "p", "frozen_on_utc": "d"}
    art = build_artifact(res, hdr, {}, "pin", 10, 1)
    assert art["may_trade"] is False and art["schema"] == "rotation_core.evaluation/v1"
    write_markdown(art, tmp_path / "r.md")
    assert "Deviations" in (tmp_path / "r.md").read_text()
