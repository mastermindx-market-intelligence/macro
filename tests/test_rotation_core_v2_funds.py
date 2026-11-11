"""F4 tradable fund tier: synthetic fixtures and hand examples only (no real fund data)."""
import numpy as np
import pandas as pd
import pytest
from engine import rotation_core_evaluation as rc
from engine import rotation_core_v2 as v2


def _panel(n=900, start="1998-12-22", late=None, seed=4):
    s = pd.bdate_range(start, periods=n)
    rng = np.random.default_rng(seed)
    spy = pd.Series(rng.normal(0.0004, 0.01, n), index=s)
    betas = dict(zip(v2.FUNDS[:9], np.linspace(0.4, 1.6, 9)))
    R = pd.DataFrame({f: betas[f] * spy + rng.normal(0, 0.004, n) for f in betas}, index=s)
    for f, k in (late or {}).items():
        R[f] = 1.0 * spy + rng.normal(0, 0.004, n); R.iloc[:k, R.columns.get_loc(f)] = np.nan
    return R, spy


def test_F4_legs_with_nine_funds_are_three_highest_and_three_lowest_beta():
    R, spy = _panel()
    legs = v2.form_fund_legs(R, spy)
    t = sorted(legs.formed)[-1]
    off, dfn, base = legs.formed[t]
    assert set(off) == {"XLU", "XLV", "XLY"}
    assert set(dfn) == {"XLB", "XLE", "XLF"} and len(base) == 9


def test_F4_late_fund_enters_only_after_252_observed_sessions():
    R, spy = _panel(late={"XLRE": 400})
    legs = v2.form_fund_legs(R, spy)
    first_obs = R["XLRE"].first_valid_index()
    n_obs = R["XLRE"].notna().cumsum()
    for t, (_, _, base) in sorted(legs.formed.items()):
        i = R.index.get_loc(t)
        assert ("XLRE" in base) == (n_obs.iloc[i - 1] >= 252)
    assert any("XLRE" in b for _, _, b in legs.formed.values())


def test_F4_fee_5bp_on_one_nav_basis_via_the_shared_simulator():
    s = pd.bdate_range("2005-01-03", periods=4)
    R = pd.DataFrame(0.0, index=s, columns=["OFF", "DEF", "BASE"])
    tgt = pd.DataFrame({"OFF": [0, 0, np.nan, np.nan], "DEF": [0, 1, np.nan, np.nan], "BASE": [1, 0, np.nan, np.nan]}, index=s)
    bk = rc.simulate(tgt, R, pd.Series(0.0, index=s), v2.FEE_FUND_BP, "f4", equity_cols=("OFF", "DEF", "BASE"))
    fee = 0.0005
    n1 = 1 / (1 + fee)                                   # initial buy into BASE
    N = n1 * (1 - fee) / (1 + fee)                       # switch BASE -> DEF: N + fee(N + n1) = n1
    assert (1 + bk.returns).prod() == pytest.approx(N)
    assert bk.costs.iloc[2] * n1 == pytest.approx(fee * (N + n1))


def test_F4_future_perturbation_leaves_fund_legs_and_mapped_states_unchanged():
    R, spy = _panel()
    t = R.index[600]
    R2, spy2 = R.copy(), spy.copy()
    R2.loc[R2.index > t] *= -3; spy2.loc[spy2.index > t] *= -3
    a, b = v2.form_fund_legs(R, spy), v2.form_fund_legs(R2, spy2)
    assert {k: v for k, v in a.formed.items() if k <= t} == {k: v for k, v in b.formed.items() if k <= t}
    pd.testing.assert_frame_equal(a.returns[:t], b.returns[:t])
    st = pd.Series(np.r_[np.zeros(400), np.ones(500)], index=R.index)
    st2 = st.copy(); st2[st2.index > t] = 2
    pd.testing.assert_series_equal(v2.map_states_to_sessions(st, R.index)[:t], v2.map_states_to_sessions(st2, R.index)[:t])


def test_F4_states_map_from_last_industry_date_on_or_before_each_fund_session():
    ind = pd.DatetimeIndex(["1999-01-04", "1999-01-05", "1999-01-07"])
    st = pd.Series([0.0, 1.0, 2.0], index=ind)
    fs = pd.DatetimeIndex(["1999-01-04", "1999-01-05", "1999-01-06", "1999-01-07", "1999-01-08"])
    assert v2.map_states_to_sessions(st, fs).tolist() == [0, 1, 1, 2, 2]


def test_F4_veto_is_a_pure_negative_check():
    assert v2.tradable_veto({"eq_5bp": 0.01, "drift_5bp": -0.0001}) is True
    assert v2.tradable_veto({"eq_5bp": 0.01, "drift_5bp": 0.0}) is False


def test_F4_fund_row_after_2019_cannot_enter_without_stage2_release(tmp_path):
    s = pd.bdate_range("2019-12-20", "2020-01-10")
    df = pd.DataFrame({"Adj Close": np.arange(len(s), dtype=float) + 1}, index=pd.DatetimeIndex(s, name="Date"))
    for t in v2.FUNDS + ["SPY"]:
        df.to_parquet(tmp_path / f"{t}.parquet")
    R, spy = v2.load_fund_panel(tmp_path, "2019-12-31")
    assert R.index.max() <= pd.Timestamp("2019-12-31")
    with pytest.raises(v2.SealedRefusal):
        v2.load_fund_panel(tmp_path, "2020-01-06")
