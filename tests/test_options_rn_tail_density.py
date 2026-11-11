"""Hermetic tests for engine.options_rn_tail_density (Q13, research reference).

Every test is named after the brief's acceptance requirement it proves:

- req1: nonnegative density and probability accounting;
- req2: reintegrated option prices match source-compatible intervals;
- req3: forward/moment constraints use the same discount and forward basis;
- req4: tail truncation and extrapolation mass are reported;
- req5: quote perturbations change uncertainty instead of generating false
  exact crash odds;
- req6: risk-neutral and physical probabilities remain explicitly different.

Synthetic surfaces only: no network, no repository data, no dates, no repo scan.
"""
from __future__ import annotations

import builtins
import importlib
import importlib.util
import logging
import math
import os
import sys

import numpy as np
import pytest

from engine import options_rn_tail_density as rn


# ---------------------------------------------------------------------------
# Synthetic fixtures (relative/integer indexes only; no calendar dates)
# ---------------------------------------------------------------------------


def _basis():
    return rn.make_forward_basis(100.0, 0.04, 30.0 / 365.0)


def _mild_iv(k):
    return 0.18 - 0.2 * k + 0.3 * k * k


def _quotes(basis, lo=70.0, hi=125.0, n=45):
    K = np.linspace(lo, hi, n)
    k = np.log(K / basis.forward)
    return K, k, _mild_iv(k), K >= basis.forward


def _dense_basis():
    return rn.from_forward(100.0, 0.99, 0.25)


def _dense_iv(k):
    return 0.20 - 0.25 * k + 0.4 * k * k


def _dense_quotes(basis):
    K = np.arange(70.0, 130.01, 0.5)
    k = np.log(K / basis.forward)
    return K, k, _dense_iv(k), K >= basis.forward


def _aligned_flat_quotes(basis, n_nodes=801):
    """A compatible fine-grid control, not an empirical validation surface."""
    grid = rn.default_grid(basis, rn.flat_smile(0.2, basis.T), n_nodes)
    K = grid[(grid >= 70) & (grid <= 130)]
    return K, np.log(K / basis.forward), np.full(K.size, 0.2), K >= basis.forward


def _walk_keys(obj):
    if isinstance(obj, dict):
        for key, val in obj.items():
            yield str(key)
            yield from _walk_keys(val)
    elif isinstance(obj, (list, tuple)):
        for val in obj:
            yield from _walk_keys(val)


# ---------------------------------------------------------------------------
# req1 — nonnegative density and probability accounting
# ---------------------------------------------------------------------------


def test_req1_butterfly_witness_is_detected_and_repaired_to_nonnegative_density():
    basis = rn.from_forward(100.0, 1.0, 0.1)
    K = np.array([90.0, 100.0, 110.0])
    bad = rn.static_arbitrage_report(K, [15.0, 9.0, 2.0], basis)
    assert bad["n_butterfly_violations"] == 1
    assert bad["negative_atom_mass"] == pytest.approx(0.1, abs=1e-12)
    assert bad["arbitrage_free"] is False
    good = rn.static_arbitrage_report(K, [15.0, 8.0, 2.0], basis)
    assert good["arbitrage_free"] is True

    rep = rn.repair_call_prices(K, [15.0, 9.0, 2.0], basis)
    after = rn.static_arbitrage_report(K, rep["C"], basis)
    assert after["arbitrage_free"] is True
    dens = rn.density_from_call_grid(K, [15.0, 9.0, 2.0], basis)
    assert dens.raw_negative_mass == pytest.approx(0.1, abs=1e-12)
    assert dens.negative_mass <= 1e-12
    assert dens.left_mass >= 0.0 and dens.right_mass >= 0.0
    assert np.all(dens.atom_masses >= -1e-12)
    assert dens.total_mass == pytest.approx(1.0, abs=1e-12)


def test_req1_noisy_quotes_repair_removes_all_negative_mass_and_keeps_accounting():
    basis = _dense_basis()
    K = np.linspace(60.0, 140.0, 81)
    rng = np.random.default_rng(1)
    C = rn.black76_price(basis, K, np.full(K.shape, 0.2), True) + rng.normal(0.0, 0.02, K.size)
    raw = rn.static_arbitrage_report(K, C, basis)
    assert raw["n_butterfly_violations"] > 0
    dens = rn.density_from_call_grid(K, C, basis)
    assert dens.raw_negative_mass > 0.0
    assert dens.negative_mass <= 1e-12
    assert dens.total_mass == pytest.approx(1.0, abs=1e-12)
    repaired = rn.static_arbitrage_report(K, dens.calls, basis)
    assert repaired["n_butterfly_violations"] == 0
    assert repaired["n_monotonicity_violations"] == 0
    assert repaired["n_slope_floor_violations"] == 0


def test_req1_smile_density_is_nonnegative_sums_to_one_and_has_monotone_cdf():
    basis = _basis()
    _, k, iv, _ = _quotes(basis)
    smile = rn.fit_smile(k, iv, basis.T, lam=0.0, m=5)
    dens = rn.density_from_smile(smile, basis, n_nodes=801)
    assert dens.total_mass == pytest.approx(1.0, abs=1e-12)
    assert dens.negative_mass <= 1e-12
    assert dens.raw_negative_mass < rn.NEG_MASS_TOL
    assert np.all(dens.atom_masses >= -1e-12)
    cdf = dens.cdf(np.linspace(dens.grid[0], dens.grid[-1], 300, endpoint=False))
    assert np.all(np.diff(cdf) >= -1e-12)
    assert cdf.min() >= 0.0 and cdf.max() <= 1.0
    with pytest.raises(rn.ProbabilityUnavailableError, match="unidentified_right_tail"):
        dens.cdf([dens.grid[-1]])


def test_req1_arbitrage_free_black76_grid_is_left_unchanged_by_repair():
    basis = _dense_basis()
    K = np.linspace(20.0, 300.0, 2001)
    C = rn.black76_price(basis, K, np.full(K.shape, 0.2), True)
    dens = rn.density_from_call_grid(K, C, basis)
    assert dens.max_repair_change < 1e-9
    assert dens.level_shift < 1e-9
    assert dens.raw_report["arbitrage_free"] is True
    assert dens.total_mass == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# req2 — reintegrated prices match source-compatible intervals
# ---------------------------------------------------------------------------


def test_req2_reintegrated_prices_fall_inside_declared_quote_bands_at_quoted_strikes():
    basis = _basis()
    K, k, iv, calls = _quotes(basis)
    smile = rn.fit_smile(k, iv, basis.T, lam=0.0, m=5)
    dens = rn.density_from_smile(smile, basis)
    _, lo, hi = rn.call_equivalent_bands(basis, K, iv, calls, rn.iv_half_width(k))
    chk = rn.reintegration_check(dens, K, lo, hi)
    assert chk["n"] == K.size
    assert chk["within"] is True
    assert chk["n_outside"] == 0


def test_req2_reintegration_flags_prices_outside_bands_and_refuses_outside_grid():
    basis = _basis()
    K, k, iv, calls = _quotes(basis)
    smile = rn.fit_smile(k, iv, basis.T, lam=0.0, m=5)
    dens = rn.density_from_smile(smile, basis)
    _, lo, hi = rn.call_equivalent_bands(basis, K, iv, calls, rn.iv_half_width(k))
    chk = rn.reintegration_check(dens, K, lo + 1.0, hi + 1.0)
    assert chk["within"] is False
    assert chk["n_outside"] == K.size
    with pytest.raises(ValueError):
        rn.reintegrate_call_prices(dens, [dens.grid[-1] + 1.0])
    with pytest.raises(ValueError):
        rn.reintegrate_call_prices(dens, [dens.grid[0] - 1.0])


# ---------------------------------------------------------------------------
# req3 — one forward/discount basis for pricing, parity and the moment check
# ---------------------------------------------------------------------------


def test_req3_forward_check_passes_when_prices_and_density_share_one_basis():
    basis = _basis()
    _, k, iv, _ = _quotes(basis)
    dens = rn.density_from_smile(rn.fit_smile(k, iv, basis.T, lam=0.0, m=5), basis)
    lo, hi = dens.forward_interval
    assert lo - 1e-3 * basis.forward <= basis.forward <= hi + 1e-3 * basis.forward
    assert dens.forward_ok_raw is True
    assert dens.forward_ok_repaired is True
    assert dens.forward_ok is True


@pytest.mark.parametrize("which,mult", [("D", 0.99), ("D", 1.01), ("F", 0.99), ("F", 1.01)])
def test_req3_forward_check_fails_on_discount_or_forward_mismatch(which, mult):
    basis = _basis()
    _, k, iv, _ = _quotes(basis)
    smile = rn.fit_smile(k, iv, basis.T, lam=0.0, m=5)
    grid = rn.density_from_smile(smile, basis).grid
    prices = rn.black76_price(basis, grid, smile(np.log(grid / basis.forward)), True)
    if which == "D":
        wrong = rn.from_forward(basis.forward, basis.discount * mult, basis.T)
    else:
        wrong = rn.from_forward(basis.forward * mult, basis.discount, basis.T)
    dens = rn.density_from_call_grid(grid, prices, wrong)
    assert dens.forward_ok is False


def test_req3_put_call_parity_and_put_bands_use_the_same_basis():
    basis = _basis()
    K = np.array([80.0, 90.0, 95.0])
    vol = np.array([0.25, 0.21, 0.19])
    put = rn.black76_price(basis, K, vol, False)
    call = rn.black76_price(basis, K, vol, True)
    assert np.allclose(rn.put_to_call(basis, K, put), call, atol=1e-10)
    mid, lo, hi = rn.call_equivalent_bands(basis, K, vol, [False, False, False], np.full(3, 0.01))
    assert np.allclose(mid, call, atol=1e-10)
    assert np.all(lo <= mid) and np.all(mid <= hi)
    rt = rn.implied_vol_black76(basis, K, put, False)
    assert np.allclose(rt, vol, atol=1e-6)


# ---------------------------------------------------------------------------
# req4 — truncation and extrapolation mass are reported
# ---------------------------------------------------------------------------


def test_req4_narrow_grid_reports_positive_truncation_and_extrapolation_mass():
    basis = _dense_basis()
    K = np.linspace(90.0, 110.0, 41)
    C = rn.black76_price(basis, K, np.full(K.shape, 0.2), True)
    dens = rn.density_from_call_grid(K, C, basis)
    assert dens.left_mass > 0.05 and dens.right_mass > 0.05
    assert dens.total_mass == pytest.approx(1.0, abs=1e-12)
    ex = rn.extrapolation_mass(dens, 97.0, 103.0)
    assert ex["mass_below_quoted"] > 0.0 and ex["mass_above_quoted"] > 0.0
    assert ex["extrapolated_mass"] == pytest.approx(ex["mass_below_quoted"] + ex["mass_above_quoted"])
    assert ex["grid_truncation_mass"] == pytest.approx(dens.left_mass + dens.right_mass)
    assert ex["left_truncation_mass"] == pytest.approx(dens.left_mass)
    assert ex["right_truncation_mass"] == pytest.approx(dens.right_mass)


def test_req4_wide_grid_truncation_mass_is_negligible():
    basis = _dense_basis()
    K = np.linspace(20.0, 300.0, 2001)
    C = rn.black76_price(basis, K, np.full(K.shape, 0.2), True)
    dens = rn.density_from_call_grid(K, C, basis)
    assert dens.left_mass < 1e-6
    assert dens.right_mass < 1e-6


def test_req4_report_exposes_extrapolation_fields_and_flags_extrapolated_strike():
    basis = _basis()
    K, k, iv, calls = _quotes(basis)
    sel = (K / basis.forward >= 0.95) & (K / basis.forward <= 1.10)
    rep = rn.rn_tail_report(basis, K[sel], iv[sel], calls[sel], n_draws=5, n_nodes=401)
    dens = rep["density"]
    for key in ("mass_below_quoted", "mass_above_quoted", "extrapolated_mass", "grid_truncation_mass",
                "left_truncation_mass", "right_truncation_mass"):
        assert key in dens and math.isfinite(dens[key])
    assert dens["mass_below_quoted"] > 0.0
    assert rep["smile"]["k_star_extrapolated"] is True


def test_req4_smile_wings_are_explicit_and_lee_capped():
    smile = rn.fit_smile([-0.1, -0.05, 0.0, 0.05, 0.1], [0.30, 0.25, 0.20, 0.18, 0.17], 0.25, lam=0.0, m=3)
    far = np.array([-3.0, -1.0, 1.0, 3.0])
    assert np.all(smile.extrapolated(far))
    assert not np.any(smile.extrapolated([-0.05, 0.0, 0.05]))
    assert np.all(smile(far) <= np.maximum(np.sqrt(2.0 * np.abs(far) / 0.25), rn.IV_FLOOR) + 1e-12)
    assert np.all(smile(far) >= rn.IV_FLOOR)


# ---------------------------------------------------------------------------
# req5 — quote perturbations change uncertainty, not false exact odds
# ---------------------------------------------------------------------------


def test_req5_perturbation_interval_widens_with_quote_uncertainty():
    basis = _dense_basis()
    _, k, iv, _ = _aligned_flat_quotes(basis)

    def fitter(kk, vv):
        return rn.flat_smile(float(np.mean(vv)), basis.T)

    widths = []
    for scale in (0.0, 0.5, 2.0):
        pi = rn.perturbation_interval(basis, k, iv, rn.iv_half_width(k, scale), 90.0, fitter,
                                      n_draws=12, seed=7, n_nodes=801)
        assert pi["measure"] == "Q"
        assert pi["available"] and pi["n_qualified"] == pi["n_draws"] == 12
        widths.append(pi["width"])
    assert widths[0] == 0.0
    assert widths[1] > 0.0
    assert widths[2] > widths[1]


def test_req5_identified_bounds_widen_with_band_and_contain_the_true_q_probability():
    basis = _dense_basis()
    K, k, iv, calls = _dense_quotes(basis)
    k_star = 90.0
    h = 1e-3
    kk = np.array([k_star - h, k_star + h])
    c = rn.black76_price(basis, kk, _dense_iv(np.log(kk / basis.forward)), True)
    q_true = 1.0 + (c[1] - c[0]) / (2.0 * h) / basis.discount
    widths = []
    for scale in (0.0, 0.5, 1.0, 2.0):
        _, lo, hi = rn.call_equivalent_bands(basis, K, iv, calls, rn.iv_half_width(k, scale))
        b = rn.tail_probability_bounds(K, lo, hi, basis, k_star)
        assert b["consistent"] is True
        assert b["L"] - 1e-9 <= q_true <= b["U"] + 1e-9
        widths.append(b["width"])
    assert all(w1 > w0 for w0, w1 in zip(widths, widths[1:]))


def test_req5_weak_wing_support_restricts_output_to_price_bounds_only():
    basis = _basis()
    K, k, iv, calls = _quotes(basis)
    sel = (K / basis.forward >= 0.95) & (K / basis.forward <= 1.10)
    rep = rn.rn_tail_report(basis, K[sel], iv[sel], calls[sel], n_draws=5, n_nodes=401)
    assert rep["identification"] == rn.IDENT_BOUNDS
    assert "weak_wing_support" in rep["identification_reasons"]
    assert "k_star_extrapolated" in rep["identification_reasons"]
    assert rep["point_estimate"] is None
    assert rep["perturbation_interval"] is None
    b = rep["identified_bounds"]
    assert 0.0 <= b["L"] <= b["U"] <= 1.0


@pytest.mark.parametrize("n_nodes", [401, 801])
def test_req5_full_density_only_when_identified_and_point_sits_inside_bounds(n_nodes):
    basis = _dense_basis()
    K, k, iv, calls = _aligned_flat_quotes(basis, n_nodes)
    rep = rn.rn_tail_report(basis, K, iv, calls, band_scale=0, lam=0.0, n_draws=8, n_nodes=n_nodes)
    assert rep["identification"] == rn.IDENT_FULL
    b = rep["identified_bounds"]
    assert b["L"] <= rep["point_estimate"] <= b["U"]
    pi = rep["perturbation_interval"]
    assert pi is not None and pi["width"] == 0.0
    assert pi["n_qualified"] == pi["n_draws"] == 8
    assert rep["numerical_validity"] == {"qualified": True, "reasons": []}
    smile = rn.fit_smile(k, iv, basis.T, 0, 5)
    assert rep["point_estimate"] == rn.q_tail_probability(smile, basis, 90, n_nodes=n_nodes)
    assert rep["point_estimate"] == rn.density_from_smile(smile, basis, n_nodes).cdf([90])[0]
    K, _, iv, calls = _dense_quotes(basis)
    wide = rn.rn_tail_report(basis, K, iv, calls, band_scale=2.0, lam=0.0, n_draws=8, n_nodes=801)
    assert wide["identification"] == rn.IDENT_BOUNDS
    assert "identified_interval_too_wide" in wide["identification_reasons"]
    assert wide["point_estimate"] is None


def test_req5_classifier_rules_are_the_frozen_thresholds():
    ok = {"consistent": True, "relative_width": 0.2}
    assert rn.classify_identification(5, False, 0.0, ok) == (rn.IDENT_FULL, [])
    mode, why = rn.classify_identification(1, False, 0.0, ok)
    assert mode == rn.IDENT_BOUNDS and why == ["weak_wing_support"]
    mode, why = rn.classify_identification(5, False, 0.02, ok)
    assert mode == rn.IDENT_BOUNDS and why == ["unstable_curvature"]
    mode, why = rn.classify_identification(5, False, float("nan"), ok)
    assert "unstable_curvature" in why
    mode, why = rn.classify_identification(5, False, 0.0, {"consistent": False, "relative_width": float("inf")})
    assert why == ["identified_interval_inconsistent"]
    mode, why = rn.classify_identification(5, False, 0.0, {"consistent": True, "relative_width": 0.51})
    assert why == ["identified_interval_too_wide"]
    mode, why = rn.classify_identification(5, True, 0.0, None)
    assert why == ["k_star_extrapolated", "no_identified_interval"]


def test_req5_perturbation_is_deterministic_for_a_fixed_seed():
    basis = _dense_basis()
    _, k, iv, _ = _dense_quotes(basis)

    def fitter(kk, vv):
        return rn.fit_smile(kk, vv, basis.T, 0.0, 5)

    hw = rn.iv_half_width(k, 0.5)
    a = rn.perturbation_interval(basis, k, iv, hw, 90.0, fitter, n_draws=6, seed=3, n_nodes=301)
    b = rn.perturbation_interval(basis, k, iv, hw, 90.0, fitter, n_draws=6, seed=3, n_nodes=301)
    assert a == b


# ---------------------------------------------------------------------------
# req6 — risk-neutral (Q) and physical (P) stay explicitly different
# ---------------------------------------------------------------------------


_P_TERMS = ("physical", "real_world", "realworld", "p_measure", "objective", "crash", "forecast", "p_prob")


def test_req6_report_is_labeled_risk_neutral_and_carries_no_physical_keys():
    basis = _dense_basis()
    K, _, iv, calls = _aligned_flat_quotes(basis)
    rep = rn.rn_tail_report(basis, K, iv, calls, band_scale=0, lam=0.0, n_draws=4, n_nodes=801)
    assert rep["measure"] == "Q"
    assert "not a physical probability" in rep["measure_label"]
    assert rep["perturbation_interval"]["measure"] == "Q"
    for key in _walk_keys(rep):
        low = key.lower()
        assert not any(term in low for term in _P_TERMS), key
    dens = rn.density_from_smile(rn.flat_smile(0.2, basis.T), basis, n_nodes=201)
    assert dens.measure == "Q"
    _, lo, hi = rn.call_equivalent_bands(basis, K, iv, calls, rn.iv_half_width(np.log(K / basis.forward)))
    assert rn.tail_probability_bounds(K, lo, hi, basis, 90.0)["measure"] == "Q"


def test_req6_conversion_to_physical_probability_is_refused():
    with pytest.raises(rn.MeasureError):
        rn.to_physical(0.05)
    with pytest.raises(rn.MeasureError):
        rn.to_physical(q=0.05, kernel=None)


def test_req6_report_is_unadmitted_proxy_with_insufficient_data_verdict():
    basis = _basis()
    K, _, iv, calls = _quotes(basis)
    rep = rn.rn_tail_report(basis, K, iv, calls, n_draws=4, n_nodes=401)
    assert rep["admitted"] is False
    assert rep["research_only"] is True
    assert rep["admission_status"] == "DIAGNOSTIC_UNADMITTED"
    assert rep["label"] == rn.PROXY_LABEL == "PROXY — not admitted surface"
    assert rep["verdict"] == "INSUFFICIENT_DATA"
    assert [m.split(":")[0] for m in rep["missing_inputs"]] == ["M1", "M2", "M3", "M4"]


# ---------------------------------------------------------------------------
# Bounded inputs (reject rather than silently truncate)
# ---------------------------------------------------------------------------


def test_contract_bounded_inputs_are_rejected_not_truncated():
    basis = _basis()
    with pytest.raises(ValueError):
        rn.call_equivalent_bands(basis, np.linspace(50, 150, rn.MAX_QUOTES + 1),
                                 np.full(rn.MAX_QUOTES + 1, 0.2), True, 0.01)
    with pytest.raises(ValueError):
        rn.tail_probability_bounds([90.0, float("nan")], [1.0, 1.0], [2.0, 2.0], basis, 90.0)
    with pytest.raises(ValueError):
        rn.from_forward(100.0, 0.0, 0.25)
    with pytest.raises(ValueError):
        rn.from_forward(-1.0, 0.99, 0.25)
    with pytest.raises(ValueError):
        rn.make_forward_basis(100.0, 4.0, 0.25)
    with pytest.raises(ValueError):
        rn.density_from_call_grid([100.0, 90.0, 110.0], [5.0, 10.0, 2.0], basis)
    with pytest.raises(ValueError):
        rn.fit_smile([0.0, 0.0, 0.1], [0.2, 0.2, 0.2], 0.25)
    with pytest.raises(ValueError):
        rn.perturbation_interval(basis, [0.0, 0.1], [0.2, 0.2], 0.01, 90.0,
                                 lambda a, b: rn.flat_smile(0.2, 0.25), n_draws=rn.MAX_DRAWS + 1)


# ---------------------------------------------------------------------------
# No silent activation (the module's own contract; no repository scan)
# ---------------------------------------------------------------------------


def test_no_silent_activation_module_contract():
    assert rn.RESEARCH_ONLY is True
    assert rn.VERDICT == "INSUFFICIENT_DATA"
    assert rn.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    banned = ("register", "schedule", "promote", "activate", "wire", "publish", "emit", "main")
    public = [name for name in vars(rn) if not name.startswith("_")]
    assert not [name for name in public if any(b in name.lower() for b in banned)]

    env_before = dict(os.environ)
    handlers_before = list(logging.getLogger().handlers)
    modules_before = set(sys.modules)

    def _no_open(*_a, **_kw):
        raise AssertionError("module import must not open files")

    # Execute a FRESH copy of the module rather than importlib.reload(rn): a
    # reload rebinds the shared module object's classes (MeasureError,
    # ForwardBasis, ...) and makes class identity in other tests order-dependent.
    # The fresh copy is never inserted into sys.modules.
    shared_measure_error = rn.MeasureError
    fresh = importlib.util.module_from_spec(rn.__spec__)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(builtins, "open", _no_open)
        rn.__spec__.loader.exec_module(fresh)

    assert fresh.RESEARCH_ONLY is True
    assert fresh is not rn
    assert sys.modules["engine.options_rn_tail_density"] is rn
    assert rn.MeasureError is shared_measure_error
    assert dict(os.environ) == env_before
    assert list(logging.getLogger().handlers) == handlers_before
    new_modules = set(sys.modules) - modules_before
    assert not [m for m in new_modules if not m.startswith(("numpy", "scipy"))]


# ---------------------------------------------------------------------------
# research-v2 — one probability object and explicit numerical availability
# These are development fixtures under NUMERICAL_CONSISTENCY_REVISION.md.
# ---------------------------------------------------------------------------


def _atomic_density(grid, strikes=(80.0, 100.0, 120.0), masses=(0.25, 0.50, 0.25), repair=True):
    grid = np.asarray(grid, dtype=float)
    strikes, masses = np.asarray(strikes), np.asarray(masses)
    basis = rn.from_forward(float(strikes @ masses), 1.0, 0.25)
    calls = np.maximum(strikes[None, :] - grid[:, None], 0.0) @ masses
    return rn.density_from_call_grid(grid, calls, basis, repair=repair)


@pytest.mark.parametrize("repair", [False, True])
@pytest.mark.parametrize("grid", [[60, 80, 100, 120, 140], [80, 100, 120]])
def test_v2_atom_cdf_limits_interval_mass_and_reintegration_share_one_law(repair, grid):
    dens = _atomic_density(grid, repair=repair)
    query = [-1, 0, 70, 79, 80, 99, 100, 101, 119, 120, 121, 200]
    expected = [0, 0, 0, 0, 0.25, 0.25, 0.75, 0.75, 0.75, 1, 1, 1]
    assert np.allclose(dens.cdf(query), expected, atol=1e-14, rtol=0)
    assert np.allclose(dens.cdf_left([80, 100, 120]), [0, 0.25, 0.75], atol=1e-14, rtol=0)
    assert dens.left_tail_probability(100) == pytest.approx(0.75)
    assert np.diff(dens.cdf([99, 101]))[0] == pytest.approx(0.50)
    assert np.diff(dens.cdf([70, 79]))[0] == 0
    assert np.allclose(rn.reintegrate_call_prices(dens, grid), dens.calls, atol=1e-14, rtol=0)
    outside = rn.extrapolation_mass(dens, 80, 120)
    assert outside["mass_below_quoted"] == 0
    assert outside["mass_above_quoted"] == 0
    assert outside["extrapolated_mass"] == 0
    assert outside["extrapolated_mass_available"] is True
    assert outside["mass_strictly_outside_grid"] == 0
    # Endpoint components are still reported even though their atoms are in-grid.
    if len(grid) == 3:
        assert outside["grid_truncation_mass"] == 0.50


def test_v2_redundant_collinear_knots_leave_probabilities_and_prices_unchanged():
    coarse = _atomic_density([60, 80, 100, 120, 140])
    fine = _atomic_density([60, 70, 80, 90, 100, 110, 120, 130, 140])
    x = np.arange(50.0, 151.0)
    assert np.array_equal(coarse.cdf(x), fine.cdf(x))
    assert np.array_equal(coarse.cdf_left(x), fine.cdf_left(x))
    assert np.allclose(rn.reintegrate_call_prices(coarse, x[10:-10]),
                       rn.reintegrate_call_prices(fine, x[10:-10]), atol=1e-14, rtol=0)


def test_v2_tail_means_do_not_locate_atoms_or_identify_boundary_probabilities():
    first = _atomic_density([80, 100, 120], (60, 140), (0.5, 0.5))
    second = _atomic_density([80, 100, 120], (40, 80, 120, 160), (0.25,) * 4)
    assert np.array_equal(first.calls, second.calls)
    assert first.basis == second.basis
    for dens in (first, second):
        assert np.array_equal(dens.cdf([80, 100, 119]), [0.5, 0.5, 0.5])
        assert dens.cdf_left([120])[0] == 0.5
        for x, side in ((60, "left"), (120, "right"), (140, "right")):
            with pytest.raises(rn.ProbabilityUnavailableError, match=f"unidentified_{side}_tail"):
                dens.cdf([x])
        with pytest.raises(rn.ProbabilityUnavailableError, match="unidentified_left_tail"):
            dens.cdf_left([80])
        with pytest.raises(rn.ProbabilityUnavailableError):
            dens.cdf([100, 140])
        outside = rn.extrapolation_mass(dens, 80, 120)
        assert outside["mass_below_quoted"] is None
        assert outside["mass_above_quoted"] is None
        assert outside["extrapolated_mass"] is None
        assert outside["extrapolated_mass_available"] is False
        assert outside["mass_strictly_outside_grid"] is None


@pytest.mark.parametrize("side", ["left", "right"])
def test_v2_small_positive_unresolved_tails_are_never_discarded(side):
    eps = 5e-13
    masses = (eps, 0.75 - eps, 0.25) if side == "left" else (0.25, 0.75 - eps, eps)
    dens = _atomic_density([80, 100, 120], (60, 100, 140), masses, repair=False)
    assert 0 < getattr(dens, f"{side}_mass") < 1e-12
    with pytest.raises(rn.ProbabilityUnavailableError, match=f"unidentified_{side}_tail"):
        dens.cdf([60 if side == "left" else 120])


@pytest.mark.parametrize("forward,query,left_limit", [(70 + 1e-13, 0, False), (110 - 1e-13, 80, True)])
def test_v2_near_endpoint_moments_do_not_force_endpoint_atoms(forward, query, left_limit):
    dens = rn.density_from_call_grid([80, 100, 120], [30, 20, 10],
                                     rn.from_forward(forward, 1, 0.25), repair=False)
    assert dens.forward_ok
    with pytest.raises(rn.ProbabilityUnavailableError, match="unidentified_left_tail"):
        (dens.cdf_left if left_limit else dens.cdf)([query])


def test_v2_rounded_product_cannot_certify_a_left_endpoint():
    dens = rn.density_from_call_grid([1, 10, 20], [6.3, 0, 0],
                                     rn.from_forward(7, 1, 0.25), repair=False)
    assert 10 * dens.atom_masses[0] == 7
    # The exact product of the canonical binary floats is smaller than 7.
    # Two possible left-tail placements therefore differ at zero.
    with pytest.raises(rn.ProbabilityUnavailableError, match="unidentified_left_tail"):
        dens.cdf([0])


def test_v2_rounded_right_mean_does_not_certify_an_endpoint():
    last = float(2 ** 52)
    dens = rn.density_from_call_grid([last - 2, last - 1, last], [1.125, 0.375, 0.125],
                                     rn.from_forward(last - 1, 1, 0.25), repair=False)
    assert dens.right_mass == 0.25 and dens.calls[-1] > 0
    assert dens.right_mean == last  # The positive excess mean rounds away.
    with pytest.raises(rn.ProbabilityUnavailableError, match="unidentified_right_tail"):
        dens.cdf([last])


@pytest.mark.parametrize("grid,calls,forward,reason", [
    ([80, 100, 120], [25, 15, 0], 100, "negative_probability_mass"),
    ([80, 100, 120], [30, 20, 10], 110.01, "infeasible_forward_moment"),
    ([80, 100, 120], [21, 1, 1], 100, "right_tail_without_mass"),
    ([-20, 0, 20], [110, 90, 70], 90, "negative_support"),
])
def test_v2_invalid_measures_cannot_be_hidden_by_clipping(grid, calls, forward, reason):
    dens = rn.density_from_call_grid(grid, calls, rn.from_forward(forward, 1, 0.25), repair=False)
    with pytest.raises(rn.ProbabilityUnavailableError, match=reason):
        dens.cdf([100])
    # Raw diagnostics remain accessible for an unavailable probability object.
    assert isinstance(dens.raw_report, dict)


def test_v2_repaired_atoms_use_the_repaired_monotone_slopes_without_redifferencing():
    basis = _dense_basis()
    grid = np.linspace(60, 140, 81)
    calls = rn.black76_price(basis, grid, 0.2, True) + np.random.default_rng(1).normal(0, 0.02, grid.size)
    dens = rn.density_from_call_grid(grid, calls, basis)
    assert np.array_equal(dens.atom_masses, np.diff(dens.slopes) / basis.discount)
    assert np.all(dens.atom_masses >= 0)
    assert dens.negative_mass == 0


@pytest.mark.parametrize("n_nodes", [3, 5, 11, 21, 51, 101])
def test_v2_incompatible_coarse_grid_reports_withhold_point_and_interval(n_nodes):
    basis = _dense_basis()
    K, _, iv, calls = _dense_quotes(basis)
    report = rn.rn_tail_report(basis, K, iv, calls, band_scale=0.1, lam=0, n_draws=2, n_nodes=n_nodes)
    assert report["schema"] == "options.rn_tail_density/research-v2"
    assert report["identification"] == rn.IDENT_BOUNDS
    assert report["point_estimate"] is None and report["perturbation_interval"] is None
    assert report["numerical_validity"]["qualified"] is False
    assert report["numerical_validity"]["reasons"]


def test_v2_partial_quote_coverage_cannot_qualify_a_full_surface():
    basis = rn.from_forward(100, 1, 0.01)
    strikes = np.array([20, 70, 80, 85, 90, 95, 100, 105, 110, 150, 200], dtype=float)
    report = rn.rn_tail_report(basis, strikes, np.full(strikes.size, 0.2), strikes >= 100,
                               k_star_ratio=0.99, band_scale=0.1, lam=0, n_draws=2, n_nodes=801)
    coverage = report["reintegration"]
    assert coverage["n_supplied"] == strikes.size
    assert coverage["n_unchecked"] > 0
    assert coverage["n_checked"] + coverage["n_unchecked"] == strikes.size
    assert coverage["complete_coverage"] is False
    assert "incomplete_quote_coverage" in report["identification_reasons"]
    assert report["point_estimate"] is None and report["perturbation_interval"] is None


@pytest.mark.parametrize("n_nodes", [401, 801])
def test_v2_retained_smooth_fixture_withholds_incompatible_uncertainty(n_nodes):
    basis = _dense_basis()
    K, _, iv, calls = _dense_quotes(basis)
    report = rn.rn_tail_report(basis, K, iv, calls, band_scale=0.1, lam=0, n_draws=8, n_nodes=n_nodes)
    assert report["reintegration"]["within"] is True
    assert report["reintegration"]["complete_coverage"] is True
    assert report["identification"] == rn.IDENT_BOUNDS
    assert "uncertainty_draws_unavailable" in report["identification_reasons"]
    assert report["point_estimate"] is None and report["perturbation_interval"] is None
    diagnostics = report["perturbation_diagnostics"]
    assert diagnostics["n_draws"] == diagnostics["n_finite"] == 8
    assert diagnostics["n_qualified"] + diagnostics["n_unavailable"] == 8
    assert diagnostics["unavailable_reasons"]["reintegration_outside_source_bands"] > 0


def test_v2_uncertainty_never_reports_survivor_quantiles(monkeypatch):
    basis = _dense_basis()
    _, k, iv, _ = _aligned_flat_quotes(basis)
    draw_count = 0
    original = rn.density_from_smile

    def unavailable_second_draw(*args, **kwargs):
        nonlocal draw_count
        draw_count += 1
        if draw_count == 2:
            raise rn.ProbabilityUnavailableError("synthetic_unavailable_draw")
        return original(*args, **kwargs)

    monkeypatch.setattr(rn, "density_from_smile", unavailable_second_draw)
    result = rn.perturbation_interval(basis, k, iv, 0, 90,
                                      lambda kk, vv: rn.flat_smile(float(np.mean(vv)), basis.T),
                                      n_draws=3, seed=7, n_nodes=801)
    assert draw_count == result["n_draws"] == 3
    assert result["n_unavailable"] == 1 and result["n_qualified"] == result["n_finite"] == 2
    assert result["n_qualified"] + result["n_unavailable"] == 3
    assert result["unavailable_reasons"]["synthetic_unavailable_draw"] == 1
    assert result["available"] is False
    assert all(result[key] is None for key in ("lo", "hi", "p05", "p95", "width"))


def test_v2_finite_incompatible_draws_are_not_silently_dropped():
    basis = _dense_basis()
    _, k, iv, _ = _aligned_flat_quotes(basis)
    vols = iter([0.2, 0.3, 0.2])
    result = rn.perturbation_interval(basis, k, iv, 0, 90,
                                      lambda kk, vv: rn.flat_smile(next(vols), basis.T),
                                      n_draws=3, seed=7, n_nodes=801)
    assert result["n_draws"] == result["n_finite"] == 3
    assert result["n_qualified"] == 2 and result["n_unavailable"] == 1
    assert result["unavailable_reasons"]["reintegration_outside_source_bands"] == 1
    assert result["available"] is False
    assert all(result[key] is None for key in ("lo", "hi", "p05", "p95", "width"))


def test_v2_uncertainty_input_errors_are_not_downgraded_to_unavailability():
    basis = _dense_basis()
    def broken_fitter(_k, _iv):
        raise ValueError("caller fitter error")
    with pytest.raises(ValueError, match="caller fitter error"):
        rn.perturbation_interval(basis, [-0.1, 0.1], [0.2, 0.2], 0.01, 90, broken_fitter, n_draws=1)
