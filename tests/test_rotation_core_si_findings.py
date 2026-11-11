"""Sector Intelligence first-pass reviewer findings, as named tests on the current (v2) engine."""
import numpy as np
import pandas as pd
import pytest
from engine import rotation_core_evaluation as rc
from engine import rotation_core_v2 as v2
from tests.rotation_core_v2_fixture import make_fixture


# ---------------- finding 1: missing interior close, deferral, no unbounded fill
def test_SI1_monday_buy_with_no_tuesday_close_defers_to_wednesday_close():
    s = pd.DatetimeIndex(["2024-01-08", "2024-01-09", "2024-01-10", "2024-01-11"])   # Mon Tue Wed Thu
    px = pd.Series([100.0, np.nan, 110.0, 121.0], index=s)          # no Tuesday close
    marks = px.ffill()
    r = marks.pct_change().fillna(0).to_frame("X")
    tgt = pd.DataFrame({"X": [1.0, np.nan, np.nan, np.nan]}, index=s)  # decided Monday close
    b = rc.simulate(tgt, r, pd.Series(0.0, index=s), {"X": 5.0}, "si1", avail=px.notna().to_frame("X"),
                    equity_cols=("X",))
    assert b.costs.iloc[1] == 0.0 and b.traded.iloc[1] == 0.0        # nothing charged Tuesday at Monday's mark
    assert b.meta["deferred_executions"] == 1
    assert b.traded.iloc[2] > 0 and b.returns.iloc[2] == pytest.approx(-0.0005 / 1.0005)   # bought at Wed close
    assert b.returns.iloc[3] == pytest.approx(0.10)                 # first move earned is Wed->Thu


def test_SI1_series_with_no_further_closes_is_not_kept_nominally_alive():
    s = pd.bdate_range("2024-01-08", periods=8)
    px = pd.Series([100.0, 101, 102, np.nan, np.nan, np.nan, np.nan, np.nan], index=s)   # last close day 3
    r = px.ffill().pct_change().fillna(0).to_frame("X")
    tgt = pd.DataFrame({"X": [1.0] + [np.nan] * 7}, index=s)
    b = rc.simulate(tgt, r, pd.Series(0.0, index=s), 0.0, "si1b", avail=px.notna().to_frame("X"), equity_cols=("X",))
    assert b.meta["days_holding_an_asset_after_its_last_close"] == 5   # counted, never silently alive
    import inspect, scripts.run_rotation_core_v1 as v1
    assert "adj.index <= px[t].index.max()" in inspect.getsource(v1.load)   # v1 panel stops filling at last close


# ---------------- finding 2: one NAV basis
def test_SI2_sell_after_plus_10pct_at_5bp_nets_9_945pct():
    # NAV 100 fully invested; asset +10% on the day; sell 100% at that close at 5 bp -> net 9.945%, not 9.950%
    from engine.rotation_core_evaluation import _fee_funded_nav
    N, paid = _fee_funded_nav(np.array([110.0]), 0.0, np.array([0.0]), np.array([0.0005]))
    assert (N - 100) / 100 == pytest.approx(0.09945) and paid == pytest.approx(0.055)
    # same in the simulator: buy decided day 0 (executes day 1), sell decided day 1 (executes day 2 after +10%)
    s = pd.bdate_range("2024-01-08", periods=4)
    r = pd.DataFrame({"X": [0.0, 0.0, 0.10, 0.0]}, index=s)
    b = rc.simulate(pd.DataFrame({"X": [1.0, 0.0, np.nan, np.nan]}, index=s), r, pd.Series(0.0, index=s),
                    {"X": 5.0}, "si2")
    assert b.returns.iloc[2] == pytest.approx(0.09945)


# ---------------- finding 3(iii): future-perturbation invariance of every v2 signal input
@pytest.fixture(scope="module")
def fx(tmp_path_factory):
    d = make_fixture(tmp_path_factory.mktemp("fx"), start="1990-01-01", end="1996-12-31", seed=3)
    vw, _ = v2.load_french_industries(d / "49_Industry_Portfolios_Daily.csv", "1996-12-31")
    mkt, _ = v2.load_french_market(d / "F-F_Research_Data_Factors_daily.csv", "1996-12-31")
    return vw, mkt


def _signals(vw, mkt):
    legs = v2.form_legs(vw, mkt)
    bd = v2.current_leg_breadth(vw, legs)
    rel = v2.relative_line(legs)
    st, log = v2.h1_states(rel, bd, 3, 25, return_log=True)
    lo = rel.rolling(126, min_periods=126).min(); near_low = rel <= 1.03 * lo
    return legs, bd, rel, st, near_low


def test_SI3_future_perturbation_leaves_every_signal_unchanged(fx):
    vw, mkt = fx
    t = vw.index[int(len(vw) * 0.7)]
    vw2, mkt2 = vw.copy(), mkt.copy()
    vw2.loc[vw2.index > t] = vw2.loc[vw2.index > t] * 3 - 0.01
    mkt2.loc[mkt2.index > t] = -mkt2.loc[mkt2.index > t]
    a, b = _signals(vw, mkt), _signals(vw2, mkt2)
    la, lb = a[0], b[0]
    for k in la.formed:                                          # beta legs formed at or before t
        if k <= t:
            assert la.formed[k] == lb.formed[k]
    pd.testing.assert_series_equal(a[2][:t], b[2][:t])           # relative line
    for key in ("br", "bmax", "wash_run_prev", "wash_from_low", "n_members"):   # breadth (i) and washout spells
        pd.testing.assert_series_equal(a[1][key][:t], b[1][key][:t])
    pd.testing.assert_series_equal(a[4][:t], b[4][:t])           # R12 near-low qualification input
    pd.testing.assert_series_equal(a[3][:t], b[3][:t])           # states
    # breadth (ii) narrowness is descriptive only and is not computed by any v2 code path (nothing to perturb)


def test_SI3_sahm_input_is_unchanged_by_future_observations():
    s = pd.bdate_range("2007-01-01", "2009-12-31")
    sahm = pd.Series(np.linspace(0, 1, 36), index=pd.date_range("2007-01-01", periods=36, freq="MS"))
    a = rc.sahm_available(sahm, s)
    t = pd.Timestamp("2008-06-30")
    sahm2 = sahm.copy(); sahm2[sahm2.index > "2008-05-01"] = 99.0   # values for months not yet published at t
    b = rc.sahm_available(sahm2, s)
    pd.testing.assert_series_equal(a[:t], b[:t])


# ---------------- finding 3(iv): bootstrap calibration under an autocorrelated null (declared tolerance)
def _ar1(n, phi, rng, sd=0.004):
    e = rng.normal(0, sd, n); x = np.empty(n); x[0] = e[0]
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def calibration(R=300, n=3000, phi=0.1, B=400, seed=11, mean=0.0):
    rng = np.random.default_rng(seed)
    rej = cover = 0
    for r in range(R):
        a = _ar1(n, phi, rng) + mean / 252
        dist = rc.bootstrap_stat([a, np.zeros(n)], rc.stat_mean_diff, B, 21, seed + r)
        obs = float(a.mean() * 252)
        p = rc.centred_p(dist, obs)
        lo, hi = rc.ci95(dist)
        rej += p < 0.05
        cover += (lo - obs) <= (mean - obs) <= (hi - obs) if False else (obs - (hi - obs) <= mean <= obs + (obs - lo))
    return rej / R, cover / R


@pytest.mark.slow
def test_SI3_bootstrap_size_and_coverage_under_ar1_null():
    size, cover = calibration()
    # declared before running: size in [0.02, 0.09], basic-interval coverage in [0.90, 0.99] (R=300, MC sd ~0.013)
    print({"measured_size": size, "measured_coverage": cover})
    assert 0.02 <= size <= 0.09 and 0.90 <= cover <= 0.99
