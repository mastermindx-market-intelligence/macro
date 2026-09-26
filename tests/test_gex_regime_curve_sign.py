"""A modeled regime must agree with modeled net gamma, not flip orientation.

Synthetic chain fixtures test arithmetic/consumer consistency only. They do not
establish observed dealer inventory, a live feed, or predictive trade authority.
"""
import numpy as np
import pandas as pd
import pytest
from engine.gex_engine import DEFAULTS, _gamma_flip, compute_gex, gamma_profile


def chain(descending=True):
    return pd.DataFrame({
        "K": np.r_[np.linspace(96, 99.6, 10), np.linspace(100.4, 104, 10)],
        "T": [0.03] * 20, "iv": [0.2] * 20, "oi": [100.0] * 20,
        "is_call": [descending] * 10 + [not descending] * 10,
    })


@pytest.mark.parametrize("spot,expected", [(99.0, "long"), (101.0, "short")])
def test_descending_crossing_uses_the_actual_local_sign(spot, expected):
    c = chain()
    grid, net, flips = gamma_profile(c, spot, DEFAULTS)
    assert len(flips) == 1
    assert (float(np.interp(spot, grid, net)) > 0) == (expected == "long")
    flip, distance, regime = _gamma_flip(c, spot, DEFAULTS)
    assert flip == min(flips, key=lambda value: abs(value - spot))
    assert distance == round(100.0 * (spot - flip) / spot, 2)
    assert regime == expected


@pytest.mark.parametrize("spot,expected", [(99.0, "long"), (101.0, "short")])
def test_real_compute_gex_payload_cannot_contradict_its_net_gamma(spot, expected):
    result = compute_gex(chain(), spot, symbol="SPY")
    assert (result["net_gex_bn"] > 0) == (expected == "long")
    assert result["gamma_regime"] == expected
    assert result["regime_passport"]["basis"] == "assumption"
    assert result["regime_passport"]["verdict"] == "display-only"


@pytest.mark.parametrize("spot,expected", [(99.0, "short"), (101.0, "long")])
def test_ascending_crossing_keeps_its_correct_regime(spot, expected):
    assert _gamma_flip(chain(False), spot, DEFAULTS)[2] == expected


@pytest.mark.parametrize("is_call,expected", [(True, "long"), (False, "short")])
def test_no_crossing_still_reports_the_curve_sign(is_call, expected):
    c = chain(); c["is_call"] = is_call
    flip, distance, regime = _gamma_flip(c, 100.0, DEFAULTS)
    assert flip is None and distance is None
    assert regime == expected


def test_thin_chain_remains_unavailable():
    assert _gamma_flip(chain().iloc[:10], 100.0, DEFAULTS) == (None, None, None)


def test_multiple_crossings_are_not_assumed_to_share_orientation():
    c = pd.DataFrame({"K": np.repeat([94.,100.,106.],10),
        "T": [0.01]*30,"iv":[0.15]*30,"oi":[100.]*30,
        "is_call":[True]*10+[False]*10+[True]*10})
    for spot in [95.,98.,100.,102.,105.]:
        grid, net, flips = gamma_profile(c, spot, DEFAULTS)
        assert len(flips) >= 2
        expected = "long" if float(np.interp(spot,grid,net)) >= 0 else "short"
        assert _gamma_flip(c,spot,DEFAULTS)[2] == expected
