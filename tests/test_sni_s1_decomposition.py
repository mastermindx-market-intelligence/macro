"""test_sni_s1_decomposition.py — a synthetic known beta is recovered;
resid = r - common; z = resid/(sigma*sqrt(h)); M0 behaviour; endpoint rule."""
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"))

from s1_decomposition import (daily_log_returns, decompose_unit,  # noqa: E402
                              factors_for, spec_hash, window_log_ret)
from s1_synth import sessions_us  # noqa: E402


def _panel(n: int = 400, beta: float = 1.3, seed: int = 5):
    dates = sessions_us(n)
    rng = np.random.default_rng(seed)
    f = rng.normal(0.0, 0.01, size=n)
    eps = rng.normal(0.0, 0.002, size=n)
    r = 0.0002 + beta * f + eps
    factor, subject = {}, {}
    p_f, p_s = 50.0, 100.0
    for i, d in enumerate(dates):
        factor[d] = float(p_f)
        p_f *= math.exp(f[i])
        subject[d] = float(p_s)
        p_s *= math.exp(r[i])
    return dates, subject, factor, beta


def test_known_beta_is_recovered():
    dates, subject, factor, beta = _panel()
    d_s = dates[-20]
    row = decompose_unit(
        "M1", "US", 5, dates[-10], d_s, dates[-10], dates[-5],
        subject, dates, {"SPY": factor}, {"SPY": dates})
    assert row["abstention"] == "OK"
    assert abs(row["beta_SPY__dc"] - beta) < 0.05
    assert row["n_obs__dc"] >= 200


def test_resid_equals_r_minus_common_and_z_scales():
    dates, subject, factor, _ = _panel()
    fill, coverage = dates[-10], dates[-5]
    row = decompose_unit("M1", "US", 5, dates[-2], dates[-20], fill, coverage,
                         subject, dates, {"SPY": factor}, {"SPY": dates})
    assert row["abstention"] == "OK"
    assert abs(row["resid__oc"] - (row["r__oc"] - row["common__oc"])) < 1e-12
    assert abs(row["common__oc"] - row["beta_SPY__dc"] * row["F_SPY__oc"]) < 1e-12
    assert abs(row["z__oc"] - row["resid__oc"] /
               (row["sigma_hat__dc"] * math.sqrt(5))) < 1e-12


def test_m0_common_is_zero_and_sigma_is_subject_vol():
    dates, subject, factor, _ = _panel()
    row = decompose_unit("M0", "US", 5, dates[-2], dates[-20], dates[-10], dates[-5],
                         subject, dates, {"SPY": factor}, {"SPY": dates})
    assert row["abstention"] == "OK"
    assert row["common__oc"] == 0.0
    assert abs(row["resid__oc"] - row["r__oc"]) < 1e-12
    rets = daily_log_returns(subject, dates)
    d_s = dates[-20]
    win_dates = [d for d in dates if d <= d_s][-252:]     # the beta window, by hand
    win = [rets[d] for d in win_dates]
    assert len(win) == 252
    assert abs(row["sigma_hat__dc"] - float(np.std(win, ddof=1))) < 1e-12


def test_missing_endpoint_abstains_never_graded_short():
    dates, subject, factor, _ = _panel()
    broken = dict(factor)
    del broken[dates[-5]]
    row = decompose_unit("M1", "US", 5, dates[-2], dates[-20], dates[-10], dates[-5],
                         subject, dates, {"SPY": broken}, {"SPY": dates})
    assert row["abstention"] == "ABSTAIN_MISSING_ENDPOINT"
    assert window_log_ret(broken, dates[-10], dates[-5]) is None


def test_insufficient_history_abstains():
    dates, subject, factor, _ = _panel(n=120)
    row = decompose_unit("M1", "US", 5, dates[-2], dates[-20], dates[-10], dates[-5],
                         subject, dates, {"SPY": factor}, {"SPY": dates})
    assert row["abstention"] == "ABSTAIN_INSUFFICIENT_HISTORY"


def test_spec_hash_is_canonical_and_stable():
    a = spec_hash("M1", "SEC:US-XNYS-BABA", ["SPY"], 21)
    b = spec_hash("M1", "SEC:US-XNYS-BABA", ["SPY"], 21)
    c = spec_hash("M2", "SEC:US-XNYS-BABA", ["SPY", "KWEB"], 21)
    assert a == b and a != c and len(a) == 64
    assert factors_for("M2", "HK") == ["2800.HK", "3033.HK"]
    assert factors_for("M1", "US") == ["SPY"]
    assert factors_for("M0", "US") == []
