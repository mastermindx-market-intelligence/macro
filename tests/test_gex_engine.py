"""Finite-difference-verified greeks + GEX engine sanity.

The greeks (gamma/vanna/charm) are checked against numerical derivatives of delta —
the only honest way to pin the sign+scaling conventions the whole magnets layer
rests on. Engine tests assert the economic behaviour (call-heavy -> +GEX, magnets
at the max dollar-gamma strikes, fragility tiering).
"""
import math
import warnings

import numpy as np
import pandas as pd
import pytest

from engine.greeks import bs_greeks
from engine.gex_engine import (DEFAULTS, REGIME_EPS, _gamma_flip, _window,
                               compute_gex, gamma_profile)

R, Q = 0.03, 0.01


def _delta(S, K, T, sig, call):
    return bs_greeks(S, K, T, sig, call, R, Q)[0]


@pytest.mark.parametrize("call", [True, False])
def test_gamma_is_dDelta_dS(call):
    S, K, T, sig = 100.0, 105.0, 0.5, 0.2
    _, gamma, _, _ = bs_greeks(S, K, T, sig, call, R, Q)
    h = 1e-3 * S
    fd = (_delta(S + h, K, T, sig, call) - _delta(S - h, K, T, sig, call)) / (2 * h)
    assert abs(gamma - fd) < 1e-4, (gamma, fd)


@pytest.mark.parametrize("call", [True, False])
def test_vanna_is_dDelta_dSigma(call):
    S, K, T, sig = 100.0, 105.0, 0.5, 0.2
    _, _, vanna, _ = bs_greeks(S, K, T, sig, call, R, Q)
    h = 1e-4
    fd = (_delta(S, K, T, sig + h, call) - _delta(S, K, T, sig - h, call)) / (2 * h)
    assert abs(vanna - fd) < 5e-4, (vanna, fd)


@pytest.mark.parametrize("call", [True, False])
def test_charm_is_dDelta_dt(call):
    S, K, T, sig = 100.0, 105.0, 0.5, 0.2
    _, _, _, charm = bs_greeks(S, K, T, sig, call, R, Q)
    h = 1e-4
    # charm = d delta / d calendar-time = - d delta / dT
    fd = -(_delta(S, K, T + h, sig, call) - _delta(S, K, T - h, sig, call)) / (2 * h)
    assert abs(charm - fd) < 5e-4, (charm, fd)


def test_degenerate_nan():
    assert all(math.isnan(x) for x in bs_greeks(100, 100, 0.0, 0.2, True))
    assert all(math.isnan(x) for x in bs_greeks(100, 100, 0.5, 0.0, False))


def _chain(call_oi, put_oi, S=100.0, iv=0.25, T=0.08):
    rows = []
    for k in range(80, 121, 2):
        rows.append(dict(K=float(k), T=T, iv=iv, oi=call_oi, is_call=True))
        rows.append(dict(K=float(k), T=T, iv=iv, oi=put_oi, is_call=False))
    return pd.DataFrame(rows)


def test_call_heavy_pos_gex_put_heavy_neg():
    S = 100.0
    assert compute_gex(_chain(1000, 10, S), S)["net_gex_bn"] > 0
    assert compute_gex(_chain(10, 1000, S), S)["net_gex_bn"] < 0


def test_magnets_at_max_dollar_gamma_strike():
    S, rows = 100.0, []
    for k in range(80, 121, 2):
        oi = 8000 if k in (94, 110) else 100
        rows.append(dict(K=float(k), T=0.08, iv=0.25, oi=oi, is_call=True))
        rows.append(dict(K=float(k), T=0.08, iv=0.25, oi=oi, is_call=False))
    g = compute_gex(pd.DataFrame(rows), S)
    assert g["magnet_down"] == 94.0
    assert g["magnet_up"] == 110.0


def test_summary_keys_and_tiers():
    S = 100.0
    g = compute_gex(_chain(1000, 1000, S), S)
    for k in ("net_gex_bn", "net_vex", "net_cex", "gamma_regime", "magnet_up",
              "magnet_down", "charm_anchor", "iv30", "put_call_oi_ratio", "max_pain", "tier"):
        assert k in g
    assert g["tier"] in ("full", "thin_chain")
    assert compute_gex(pd.DataFrame([]), S)["tier"] == "no_options"
    few = [dict(K=100.0, T=0.08, iv=0.25, oi=100, is_call=True),
           dict(K=105.0, T=0.08, iv=0.25, oi=100, is_call=False)]
    assert compute_gex(pd.DataFrame(few), S)["tier"] == "no_options"   # <6 strikes


def test_gamma_regime_passport_single_name_vs_index():
    """Audit #29: every gamma_regime carries an assumption-basis passport. Single names are
    flagged structurally-constant (product attribute, not a time-varying signal); indices are
    not, but are still assumption-signed."""
    S = 100.0
    single = compute_gex(_chain(1000, 1000, S), S, symbol="AAPL")["regime_passport"]
    assert single["basis"] == "assumption"
    assert single["structurally_constant"] is True
    assert single["is_index_product"] is False
    assert single["verdict"] == "display-only"

    index = compute_gex(_chain(1000, 1000, S), S, symbol="SPX")["regime_passport"]
    assert index["basis"] == "assumption"
    assert index["structurally_constant"] is False   # market-wide read, not a name attribute
    assert index["is_index_product"] is True

    # no symbol -> still assumption-basis, but constancy is unknown (None)
    anon = compute_gex(_chain(1000, 1000, S), S)["regime_passport"]
    assert anon["basis"] == "assumption" and anon["structurally_constant"] is None


# ── gamma_profile — the ±25% spot-grid exposure curve (masterplan §4.2) ──────────────
# One definition: _gamma_flip is a thin wrapper over gamma_profile, so the published
# curve and the published crossing can never disagree.

def test_gamma_profile_shape_and_center():
    from engine.gex_engine import DEFAULTS, _window, gamma_profile
    S = 100.0
    cfg = dict(DEFAULTS)
    c = _window(_chain(1000, 10, S), S, cfg)
    grid, net, flips = gamma_profile(c, S, cfg)
    assert grid is not None and len(grid) == 101 and len(net) == 101
    # centre grid point IS the current spot (linspace 0.75..1.25 × S, index 50)
    assert grid[50] == pytest.approx(S)
    # grid strictly increasing
    assert all(grid[i] < grid[i + 1] for i in range(100))


def test_gamma_profile_sign_at_spot_matches_book():
    from engine.gex_engine import DEFAULTS, _window, gamma_profile
    S = 100.0
    cfg = dict(DEFAULTS)
    call_heavy = gamma_profile(_window(_chain(1000, 10, S), S, cfg), S, cfg)
    put_heavy = gamma_profile(_window(_chain(10, 1000, S), S, cfg), S, cfg)
    assert call_heavy[1][50] > 0   # dealers long-call heavy → positive gamma at spot
    assert put_heavy[1][50] < 0    # dealers short-put heavy → negative gamma at spot


def test_gamma_flip_is_nearest_profile_crossing():
    from engine.gex_engine import DEFAULTS, _gamma_flip, _window, gamma_profile
    S = 100.0
    cfg = dict(DEFAULTS)
    # A mixed book whose sign changes across the grid: heavy puts below spot,
    # heavy calls above — the classic index shape with a flip near spot.
    rows = []
    for k in range(80, 121, 2):
        rows.append(dict(K=float(k), T=0.08, iv=0.25, oi=3000 if k >= 100 else 50, is_call=True))
        rows.append(dict(K=float(k), T=0.08, iv=0.25, oi=3000 if k < 100 else 50, is_call=False))
    c = _window(pd.DataFrame(rows), S, cfg)
    grid, net, flips = gamma_profile(c, S, cfg)
    flip, dist, regime = _gamma_flip(c, S, cfg)
    if flip is None:
        assert not flips
    else:
        assert flips, "wrapper found a flip the profile did not"
        assert flip == pytest.approx(min(flips, key=lambda f: abs(f - S)))
        # the crossing really is a sign change of the published curve
        i = int(np.searchsorted(grid, flip))
        assert 0 < i < 101
        assert (net[i - 1] < 0) != (net[i] < 0) or net[i - 1] == 0.0


def test_gamma_profile_thin_chain_declines():
    from engine.gex_engine import DEFAULTS, gamma_profile
    S = 100.0
    few = pd.DataFrame([
        dict(K=100.0, T=0.08, iv=0.25, oi=100, is_call=True),
        dict(K=105.0, T=0.08, iv=0.25, oi=100, is_call=False),
    ])
    grid, net, flips = gamma_profile(few, S, dict(DEFAULTS))
    assert grid is None and net is None and flips == []


# ── gamma REGIME provenance: regime from the repriced curve AT S ────────────────────
# Defect (options-mechanics-witness.py, macro capsule): ``_gamma_flip`` derived the
# regime from the current spot's LOCATION relative to the nearest zero-crossing
# ("S >= flip"), which is correct only for an ascending curve. On a "descending" book
# (call-heavy lower strikes / put-heavy upper strikes) the sign of the curve at S is
# the OPPOSITE of that location test, so the published regime contradicted the
# published curve. The regime is now read from the repriced curve AT the actual spot S
# — never from flip location — with an absolute near-zero band of REGIME_EPS dollars
# per ``pct_move`` mapping to gamma_regime None (indeterminate).
#
# Witness recipe (immutable research): lower strikes 95.00+0.01j, upper 105.00+0.01j,
# T=30/365, iv=0.2, oi=100, multiplier=100; "descending" = lower calls + upper puts.

WITNESS_T = 30.0 / 365.0


def _witness_chain(orientation):
    low_call = orientation == "descending"
    rows = [dict(K=95.0 + j * 0.01, T=WITNESS_T, iv=0.2, oi=100.0, is_call=low_call)
            for j in range(10)]
    rows += [dict(K=105.0 + j * 0.01, T=WITNESS_T, iv=0.2, oi=100.0, is_call=not low_call)
             for j in range(10)]
    if orientation == "all_calls":
        for r in rows:
            r["is_call"] = True
    elif orientation == "all_puts":
        for r in rows:
            r["is_call"] = False
    return pd.DataFrame(rows)


def _direct_net_gamma_at(c, S, cfg):
    """Independent same-state direct gamma: bs_greeks at spot S (not the profile
    grid), dealer sign call +1 / put -1, in dollars per ``pct_move``."""
    mult, pm = cfg["contract_multiplier"], cfg["pct_move"]
    total = 0.0
    for r in c.itertuples():
        g = bs_greeks(S, r.K, r.T, r.iv, bool(r.is_call), cfg["r"], cfg["q"])[1]
        total += (1.0 if r.is_call else -1.0) * g * r.oi * mult * S * S * pm
    return total


def test_regime_descending_uses_own_curve_sign_not_nearest_flip():
    """The witness counterexample: a descending book is POSITIVE at S=98 and NEGATIVE
    at S=101, the opposite of "S vs nearest flip". The old orientation logic returned
    short/long here — this test fails against it."""
    cfg = dict(DEFAULTS)
    c = _witness_chain("descending")

    flip, dist, regime = _gamma_flip(c, 98.0, cfg)
    assert flip == pytest.approx(99.75550734870933, abs=1e-6)
    assert dist == pytest.approx(-1.79, abs=0.01)
    assert regime == "long", "own curve at S=98 is positive — flip location is the bug"
    assert _direct_net_gamma_at(c, 98.0, cfg) > 0

    flip, dist, regime = _gamma_flip(c, 101.0, cfg)
    assert flip == pytest.approx(99.75550988739006, abs=1e-6)
    assert dist == pytest.approx(1.23, abs=0.01)
    assert regime == "short", "own curve at S=101 is negative"
    assert _direct_net_gamma_at(c, 101.0, cfg) < 0


def test_regime_ascending_matches_own_curve_sign():
    cfg = dict(DEFAULTS)
    c = _witness_chain("ascending")
    for spot, expected in [(98.0, "short"), (101.0, "long")]:
        _, _, regime = _gamma_flip(c, spot, cfg)
        assert regime == expected
        assert (regime == "long") == (_direct_net_gamma_at(c, spot, cfg) > 0)


def test_regime_no_crossing_all_call_all_put():
    cfg = dict(DEFAULTS)
    calls = _witness_chain("all_calls")
    flip, dist, regime = _gamma_flip(calls, 101.0, cfg)
    assert flip is None and dist is None
    assert regime == "long" and _direct_net_gamma_at(calls, 101.0, cfg) > 0

    puts = _witness_chain("all_puts")
    flip, dist, regime = _gamma_flip(puts, 101.0, cfg)
    assert flip is None and dist is None
    assert regime == "short" and _direct_net_gamma_at(puts, 101.0, cfg) < 0


def test_regime_multiple_roots_nearest_crossing_and_own_sign():
    """Several zero-crossings: the reported flip is the NEAREST, while the regime at S
    still comes from the curve at S (not from S's side of the nearest crossing)."""
    cfg = dict(DEFAULTS)
    rows = []
    for j in range(10):
        rows.append(dict(K=80.0 + j * 0.01, T=WITNESS_T, iv=0.2, oi=5000.0, is_call=True))
    for j in range(10):
        rows.append(dict(K=100.0 + j * 0.01, T=WITNESS_T, iv=0.2, oi=5000.0, is_call=False))
    for j in range(10):
        rows.append(dict(K=120.0 + j * 0.01, T=WITNESS_T, iv=0.2, oi=5000.0, is_call=True))
    c = pd.DataFrame(rows)
    spot = 95.0
    _, _, flips = gamma_profile(c, spot, cfg)
    assert len(flips) >= 2, "fixture must carry multiple zero-crossings"
    flip, dist, regime = _gamma_flip(c, spot, cfg)
    assert flip == pytest.approx(min(flips, key=lambda f: abs(f - spot)))
    assert dist == pytest.approx(round(100.0 * (spot - flip) / spot, 2))
    assert regime == "short"
    assert _direct_net_gamma_at(c, spot, cfg) < 0


def test_regime_near_zero_band_is_none_indeterminate():
    cfg = dict(DEFAULTS)
    assert REGIME_EPS == 1e-8
    rows = []
    for _ in range(10):
        rows.append(dict(K=100.0, T=WITNESS_T, iv=0.25, oi=1.0, is_call=True))
        rows.append(dict(K=100.0, T=WITNESS_T, iv=0.25, oi=1.0, is_call=False))
    c = pd.DataFrame(rows)
    assert abs(_direct_net_gamma_at(c, 100.0, cfg)) <= REGIME_EPS
    _, _, regime = _gamma_flip(c, 100.0, cfg)
    assert regime is None, "inside the near-zero band the regime is indeterminate"


@pytest.mark.parametrize("bad_spot", [0.0, -1.0, float("nan"), float("inf"),
                                      float("-inf"), None, True])
def test_regime_rejects_invalid_spot(bad_spot):
    cfg = dict(DEFAULTS)
    assert _gamma_flip(_witness_chain("descending"), bad_spot, cfg) == (None, None, None)


def test_regime_declines_malformed_and_thin_input():
    cfg = dict(DEFAULTS)
    S = 100.0
    empty = pd.DataFrame(columns=["K", "T", "iv", "oi", "is_call"])
    assert _gamma_flip(empty, S, cfg) == (None, None, None)
    assert gamma_profile(empty, S, cfg) == (None, None, [])
    nan_rows = pd.DataFrame([dict(K=float("nan"), T=WITNESS_T, iv=0.2, oi=100.0,
                                  is_call=True) for _ in range(20)])
    assert _gamma_flip(nan_rows, S, cfg) == (None, None, None)
    thin = pd.DataFrame([dict(K=100.0 + j * 0.01, T=WITNESS_T, iv=0.2, oi=100.0,
                              is_call=(j % 2 == 0)) for j in range(19)])
    assert _gamma_flip(thin, S, cfg) == (None, None, None)
    ok = pd.DataFrame([dict(K=100.0 + j * 0.01, T=WITNESS_T, iv=0.2, oi=100.0,
                            is_call=(j % 2 == 0)) for j in range(20)])
    assert _gamma_flip(ok, S, cfg)[2] in ("long", "short")


@pytest.mark.parametrize("bad_row", [
    dict(T=WITNESS_T, iv=0.0, oi=100.0),   # zero vol -> nonfinite gamma
    dict(T=0.0, iv=0.2, oi=100.0),         # zero tenor -> nonfinite gamma
])
def test_regime_nonfinite_repricing_is_unavailable(bad_row):
    cfg = dict(DEFAULTS)
    rows = [dict(K=100.0 + j * 0.01, is_call=(j % 2 == 0), **bad_row) for j in range(20)]
    c = pd.DataFrame(rows)
    with np.errstate(all="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        flip, dist, regime = _gamma_flip(c, 100.0, cfg)
    assert regime is None, "failed repricing must not synthesize a sign"


def test_regime_input_order_permutation_is_invariant():
    cfg = dict(DEFAULTS)
    c = _witness_chain("descending")
    baseline = _gamma_flip(c, 98.0, cfg)
    shuffled = _gamma_flip(c.iloc[::-1].reset_index(drop=True), 98.0, cfg)
    assert shuffled[2] == baseline[2]
    assert shuffled[0] == pytest.approx(baseline[0])


def test_regime_matches_direct_gamma_across_spot_grid():
    """Same chosen rows: the profile-repriced regime and an independent bs_greeks
    evaluation at S agree wherever |gamma| exceeds REGIME_EPS."""
    cfg = dict(DEFAULTS)
    rows = []
    for k in range(80, 121, 2):
        rows.append(dict(K=float(k), T=0.08, iv=0.25, oi=3000.0 if k >= 100 else 50.0,
                         is_call=True))
        rows.append(dict(K=float(k), T=0.08, iv=0.25, oi=3000.0 if k < 100 else 50.0,
                         is_call=False))
    c = pd.DataFrame(rows)
    for spot in (90.0, 95.0, 98.0, 100.0, 102.0, 108.0):
        direct = _direct_net_gamma_at(c, spot, cfg)
        _, _, regime = _gamma_flip(c, spot, cfg)
        if abs(direct) <= REGIME_EPS:
            assert regime is None
        else:
            assert (regime == "long") == (direct > 0)


def test_compute_gex_regime_agrees_with_its_own_net_gex():
    """Integration: the published regime must share the sign of the same-state net GEX
    the summary already reports (both repriced at the actual spot)."""
    c = _witness_chain("descending")
    for spot, expected in [(98.0, "long"), (101.0, "short")]:
        out = compute_gex(c, spot)
        assert out["gamma_regime"] == expected
        assert (out["gamma_regime"] == "long") == (out["net_gex_bn"] > 0)
