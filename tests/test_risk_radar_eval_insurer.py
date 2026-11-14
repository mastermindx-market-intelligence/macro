"""Insurer-profile secondary read (synthetic; no store access)."""
import numpy as np
import pandas as pd
import pytest

from engine.risk_radar_eval import insurer as N


def _px():
    v = np.concatenate([np.linspace(100, 110, 30), np.linspace(110, 96.8, 10)[1:],
                        np.linspace(96.8, 111, 20)[1:], np.linspace(111, 115, 30)])
    return pd.Series(v, index=pd.bdate_range("2019-01-02", periods=len(v)))


def test_out_during_decline_cuts_drawdown_and_keeps_gains():
    px = _px(); idx = px.index
    spy = px.pct_change().fillna(0.0); bills = pd.Series(0.0, index=idx)
    alert = pd.Series(False, index=idx); alert.iloc[29:38] = True     # out onset..trough
    sl = N.sleeve_returns(alert, spy, bills, exec_lag=0)
    a = N.profile(sl, spy_ret=spy, bill_ret=bills, px=px, outcomes_through=idx[-1], depths=(0.10,))
    b = N.profile(spy, spy_ret=spy, bill_ret=bills, px=px, outcomes_through=idx[-1], depths=(0.10,))
    assert a["max_drawdown"] > b["max_drawdown"]
    d = a["by_depth"]["dd10"]
    assert d["drawdown_avoided_pooled"] > 0.8
    assert d["gains_kept_outside_declines"] == pytest.approx(1.0, abs=1e-6)
    assert b["by_depth"]["dd10"]["drawdown_avoided_pooled"] == pytest.approx(0.0, abs=1e-9)


def test_alert_acts_next_session():
    idx = pd.bdate_range("2020-01-01", periods=4)
    spy = pd.Series([0.01, -0.05, 0.02, 0.0], index=idx); bills = pd.Series(0.0, index=idx)
    alert = pd.Series([True, False, False, False], index=idx)
    assert N.sleeve_returns(alert, spy, bills, exec_lag=0).tolist() == [0.01, 0.0, 0.02, 0.0]
    # default: one-session execution lag (seen at d close, executed at d+1 close)
    assert N.sleeve_returns(alert, spy, bills).tolist() == [0.01, -0.05, 0.0, 0.0]


def test_hy_lag_shifts_credit_leg_only():
    from engine.risk_radar_eval import inputs as I
    idx = pd.bdate_range("2020-01-01", periods=4)
    s = pd.DataFrame({"credit_oas_roc": [0.1, 0.2, 0.3, 0.4], "bubble_ext": [1, 2, 3, 4.0]}, index=idx)
    o = I.lag_for_availability(s)
    assert np.isnan(o["credit_oas_roc"].iloc[0]) and o["credit_oas_roc"].iloc[1] == 0.1
    assert o["bubble_ext"].tolist() == [1, 2, 3, 4.0]


def test_peak_starts_from_opening_capital():
    # #11137 review: a loss in session 1 must count (peak = opening capital 1.0)
    idx = pd.bdate_range("2021-01-04", periods=6)
    ret = pd.Series([-0.10, 0, 0, 0, 0, 0], index=idx, dtype=float)
    px = (1 + ret).cumprod() * 100
    r = N.profile(ret, spy_ret=ret, bill_ret=pd.Series(0.0, index=idx), px=px,
                  outcomes_through=idx[-1], depths=(0.10,))
    assert r["max_drawdown"] == pytest.approx(-0.10, abs=1e-4)
    assert r["longest_under_water_sessions"] == 6
    assert r["share_sessions_under_water"] == pytest.approx(1.0)
