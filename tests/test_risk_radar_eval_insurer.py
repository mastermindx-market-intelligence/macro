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
    sl = N.sleeve_returns(alert, spy, bills)
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
    assert N.sleeve_returns(alert, spy, bills).tolist() == [0.01, 0.0, 0.02, 0.0]
