from __future__ import annotations

"""Hermetic tests for the Q02 research reference (engine/options_american_exercise.py).

Every test is named after the requirement it proves (req1..req6, PREREG.md section 8) plus
the module's own no-silent-activation contract. Synthetic inputs only: no network, no repo
data, no wall clock, no calendar dates (time is integer minute indexes from an arbitrary
origin). Tolerances are the frozen PREREG.md section 7 / section 8 constants.
"""

import dataclasses
import importlib.util
import inspect
import math
import sys
import types

import numpy as np
import pytest

import engine.options_american_exercise as mod

# Frozen scenario constants (PREREG.md section 7).
S0, K0, T0, SIG0, R0, Q0 = 100.0, 100.0, 0.5, 0.25, 0.03, 0.01
STRIKES = (80.0, 100.0, 120.0)
SHORT_T = 0.1
FINE = 400


# ---------------------------------------------------------------------------------------
# Incumbent formula, inlined verbatim from engine/greeks.py (base d252f919, sha256
# d471f5ed...ba8d9c). Inlined because CI hygiene forbids importing other repo modules.
# RE-PIN REQUIRED: CI hygiene also forbids opening repository files, so this suite cannot
# see drift in engine/greeks.py. If that file's sha256 ever differs from d471f5ed...ba8d9c,
# this copy must be re-inlined by hand (evaluate.py's inventory refuses on the mismatch).
# ---------------------------------------------------------------------------------------

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)


def _inc_ncdf(x):
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def _inc_npdf(x):
    return math.exp(-0.5 * x * x) / _SQRT2PI


def _incumbent_bs_greeks(S, K, T, sigma, is_call, r=0.0, q=0.0):
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0 or not math.isfinite(sigma):
        return (float("nan"),) * 4
    sqrtT = math.sqrt(T)
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma * sigma) * T) / (sigma * sqrtT)
    d2 = d1 - sigma * sqrtT
    eqT = math.exp(-q * T)
    pdf = _inc_npdf(d1)
    gamma = eqT * pdf / (S * sigma * sqrtT)
    vanna = -eqT * pdf * d2 / sigma
    common = eqT * pdf * (2.0 * (r - q) * T - d2 * sigma * sqrtT) / (2.0 * T * sigma * sqrtT)
    if is_call:
        delta = eqT * _inc_ncdf(d1)
        charm = q * eqT * _inc_ncdf(d1) - common
    else:
        delta = eqT * (_inc_ncdf(d1) - 1.0)
        charm = -q * eqT * _inc_ncdf(-d1) - common
    return delta, gamma, vanna, charm


# ---------------------------------------------------------------------------------------
# Selector fixtures (integer minute indexes; arbitrary origin; 365-day year)
# ---------------------------------------------------------------------------------------

DAY = 1440
EXPIRY_DAY = 200 * DAY
VALUATION = EXPIRY_DAY - 60 * DAY
CLOCK = mod.SessionClock(open_offset_minutes=570, close_offset_minutes=960,
                         minutes_per_year=365.0 * DAY)
PM_EXPIRY = EXPIRY_DAY + 960


def _terms(**kw):
    base = dict(underlying="XYZ", occ_root="XYZ", exercise_style=mod.AMERICAN,
                deliverable_kind=mod.SHARES, deliverable_shares=100.0, multiplier=100.0,
                settlement=mod.PM_CLOSE, expiry_day_start=EXPIRY_DAY, strike=100.0,
                is_call=False)
    base.update(kw)
    return mod.ContractTerms(**base)


def _schedule(*records, complete_through=PM_EXPIRY + DAY, asserted_at=VALUATION - 30 * DAY):
    return mod.DividendSchedule(records=tuple(records),
                                completeness=((asserted_at, complete_through),))


def _market(dividends=None, rate=0.03, cutoff=VALUATION, **kw):
    base = dict(spot=100.0, sigma=0.25, rate=rate, continuous_yield=None, valuation=VALUATION,
                cutoff=cutoff, dividends=dividends)
    base.update(kw)
    return mod.MarketInputs(**base)


def _rec(rid, known_at, ex_offset_days, amount, status=mod.DECLARED):
    return mod.DividendRecord(record_id=rid, known_at=known_at,
                              ex_time=VALUATION + ex_offset_days * DAY, amount=amount,
                              status=status)


def _price_levels(valuation):
    return valuation.per_share["price"].levels


# =======================================================================================
# req1 — European controls converge to the existing shared formula (T1a-T1g)
# =======================================================================================

@pytest.mark.parametrize("is_call", [True, False])
@pytest.mark.parametrize("K", STRIKES)
@pytest.mark.parametrize("T", [T0, SHORT_T])
def test_req1_t1a_t1d_european_fd_matches_shared_formula_at_finest_grid(is_call, K, T):
    qual = mod.qualify_fd(S0, K, T, SIG0, R0, Q0, is_call, american=False)
    price = qual.quantities["price"].levels[2]
    delta = qual.quantities["delta"].levels[2]
    gamma = qual.quantities["gamma"].levels[2]
    vanna = qual.quantities["vanna"].levels[2]
    charm = qual.quantities["charm"].levels[2]
    d, g, v, c = _incumbent_bs_greeks(S0, K, T, SIG0, is_call, R0, Q0)
    assert abs(price - mod.bs_price(S0, K, T, SIG0, is_call, R0, Q0)) <= 5e-3      # T1a
    assert abs(delta - d) <= 2e-3                                                  # T1b
    assert abs(gamma - g) <= 5e-4                                                  # T1c
    assert abs(vanna - v) <= 5e-3 + 5e-2 * abs(v)                                  # T1d
    assert abs(charm - c) <= 5e-3 + 5e-2 * abs(c)                                  # T1d
    assert qual.levels == (100, 200, 400)


@pytest.mark.parametrize("is_call", [True, False])
@pytest.mark.parametrize("S,K,T,sigma,r,q", [
    (100.0, 100.0, 0.5, 0.25, 0.03, 0.01),
    (100.0, 80.0, 0.5, 0.25, 0.03, 0.01),
    (100.0, 120.0, 0.1, 0.25, 0.03, 0.01),
    (4500.0, 4300.0, 0.02, 0.18, 0.043, 0.0),
    (37.5, 40.0, 1.7, 0.6, -0.005, 0.02),
])
def test_req1_t1e_module_analytic_greeks_equal_greeks_py_formula(is_call, S, K, T, sigma, r, q):
    ours = mod.bs_greeks(S, K, T, sigma, is_call, r, q)
    ref = _incumbent_bs_greeks(S, K, T, sigma, is_call, r, q)
    for a, b in zip(ours, ref):
        assert abs(a - b) <= 1e-12
    # Degenerate inputs return NaN like the incumbent rather than raising.
    assert all(math.isnan(x) for x in mod.bs_greeks(S, K, 0.0, sigma, is_call, r, q))


@pytest.mark.parametrize("is_call", [True, False])
def test_req1_t1f_refinement_reduces_european_atm_error(is_call):
    d, g, _, _ = _incumbent_bs_greeks(S0, K0, T0, SIG0, is_call, R0, Q0)
    p = mod.bs_price(S0, K0, T0, SIG0, is_call, R0, Q0)
    coarse = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, M=100)
    fine = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, M=FINE)
    assert abs(fine.price - p) < abs(coarse.price - p)
    assert abs(fine.delta - d) < abs(coarse.delta - d)
    assert abs(fine.gamma - g) < abs(coarse.gamma - g)


@pytest.mark.parametrize("is_call", [True, False])
def test_req1_t1g_one_cash_dividend_european_fd_matches_quadrature(is_call):
    fd = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, dividends=[(0.25, 2.0)], M=FINE)
    ref = mod.european_one_dividend_quadrature(S0, K0, T0, SIG0, R0, Q0, is_call, 0.25, 2.0)
    assert abs(fd.price - ref) <= 1e-2
    # The dividend matters: the no-dividend price is far outside the tolerance.
    assert abs(mod.bs_price(S0, K0, T0, SIG0, is_call, R0, Q0) - ref) > 0.5


# =======================================================================================
# req2 — American bounds and the American-versus-European comparison (T2a-T2f)
# =======================================================================================

@pytest.mark.parametrize("K", STRIKES)
def test_req2_t2a_american_put_at_or_above_intrinsic_at_every_node(K):
    res = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, False, True, M=FINE)
    intrinsic = np.maximum(K - res.s_nodes, 0.0)
    assert float(np.min(res.values - intrinsic)) >= -1e-10


@pytest.mark.parametrize("is_call", [True, False])
@pytest.mark.parametrize("divs", [(), ((0.25, 2.0),)])
def test_req2_t2b_american_at_or_above_european_on_same_grid(is_call, divs):
    grid = mod.build_grid(S0, K0, T0, SIG0, FINE, sum(d for _, d in divs))
    am = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, True, dividends=divs, grid=grid)
    eu = mod.fd_solve(S0, K0, T0, SIG0, R0, Q0, is_call, False, dividends=divs, grid=grid)
    assert float(np.min(am.values - eu.values)) >= -1e-10
    assert am.price - eu.price >= -1e-10


@pytest.mark.parametrize("K", STRIKES)
def test_req2_t2c_american_put_below_strike_and_call_below_spot(K):
    put = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, False, True, M=FINE)
    call = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, True, True, M=FINE)
    assert put.price < K
    assert call.price < S0
    assert float(np.max(put.values)) <= K


def test_req2_t2d_american_call_without_dividends_equals_european():
    am = mod.fd_solve(S0, K0, T0, SIG0, R0, 0.0, True, True, M=FINE)
    assert abs(am.price - mod.bs_price(S0, K0, T0, SIG0, True, R0, 0.0)) <= 5e-3


@pytest.mark.parametrize("K", STRIKES)
def test_req2_t2e_american_put_fd_matches_independent_crr_lattice(K):
    fd = mod.fd_solve(S0, K, T0, SIG0, R0, Q0, False, True, M=FINE)
    crr = mod.crr_price(S0, K, T0, SIG0, R0, Q0, False, True, steps=2000)
    assert abs(fd.price - crr) <= 2e-2
    # Discriminating: the European put is not within the same tolerance at K = 120.
    if K == 120.0:
        assert crr - mod.bs_price(S0, K, T0, SIG0, False, R0, Q0) > 0.1


def test_req2_t2f_deep_itm_dividend_call_matches_crr_vn_and_shows_premium():
    args = (100.0, 80.0, 0.5, 0.2, 0.03, 0.0, True)
    divs = [(0.25, 5.0)]
    grid = mod.build_grid(100.0, 80.0, 0.5, 0.2, FINE, 5.0)
    am = mod.fd_solve(*args, True, dividends=divs, grid=grid)
    eu = mod.fd_solve(*args, False, dividends=divs, grid=grid)
    crr = mod.crr_price(*args, True, dividends=divs, steps=2000)
    assert abs(am.price - crr) <= 5e-2
    assert am.price - eu.price >= 0.5


# =======================================================================================
# req3 — dividends and expiry use only information available at the cutoff
# =======================================================================================

def test_req3_post_cutoff_record_leaves_price_bit_identical_to_no_dividend_price():
    empty = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule()))
    late = _rec("d1", known_at=VALUATION + 1, ex_offset_days=20, amount=1.5)
    with_late = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule(late)))
    assert with_late.decision.model == mod.MODEL_AMERICAN_FD
    assert with_late.decision.dividends == ()
    assert _price_levels(with_late) == _price_levels(empty)


def test_req3_pre_cutoff_revision_changes_the_price_and_later_revision_does_not():
    first = _rec("d1", known_at=VALUATION - 20 * DAY, ex_offset_days=20, amount=0.5)
    revised = _rec("d1", known_at=VALUATION - 1, ex_offset_days=20, amount=1.5)
    too_late = _rec("d1", known_at=VALUATION + 1, ex_offset_days=20, amount=3.0)
    p_first = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule(first)))
    p_rev = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule(first, revised)))
    p_late = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule(first, too_late)))
    assert _price_levels(p_rev) != _price_levels(p_first)
    assert p_rev.per_share["price"].levels[2] > p_first.per_share["price"].levels[2]
    assert _price_levels(p_late) == _price_levels(p_first)


def test_req3_out_of_window_and_cancelled_records_change_nothing():
    empty = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule()))
    before_valuation = _rec("a", known_at=VALUATION - 40 * DAY, ex_offset_days=-5, amount=2.0)
    at_valuation = _rec("b", known_at=VALUATION - 40 * DAY, ex_offset_days=0, amount=2.0)
    after_expiry = mod.DividendRecord("c", VALUATION - 40 * DAY, PM_EXPIRY + 1, 2.0, mod.DECLARED)
    declared = _rec("d", known_at=VALUATION - 40 * DAY, ex_offset_days=20, amount=2.0)
    cancelled = _rec("d", known_at=VALUATION - 10 * DAY, ex_offset_days=20, amount=2.0,
                     status=mod.CANCELLED)
    out = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule(
        before_valuation, at_valuation, after_expiry, declared, cancelled)))
    assert _price_levels(out) == _price_levels(empty)


def test_req3_look_ahead_cutoff_raises():
    with pytest.raises(ValueError):
        mod.point_in_time_dividends(_schedule(), cutoff=VALUATION + 1, valuation=VALUATION,
                                    expiry=PM_EXPIRY)
    with pytest.raises(ValueError):
        mod.select_model(_terms(), CLOCK, _market(dividends=_schedule(), cutoff=VALUATION + 1))


def test_req3_am_open_versus_pm_close_changes_time_and_price():
    am = mod.price_contract(_terms(settlement=mod.AM_OPEN), CLOCK, _market(dividends=_schedule()))
    pm = mod.price_contract(_terms(settlement=mod.PM_CLOSE), CLOCK, _market(dividends=_schedule()))
    assert pm.decision.t_years - am.decision.t_years == pytest.approx(390.0 / (365.0 * DAY))
    assert pm.per_share["price"].levels[2] > am.per_share["price"].levels[2]


def test_req3_unknown_settlement_clock_is_unavailable():
    for terms, clock in ((_terms(settlement=None), CLOCK), (_terms(), None),
                         (_terms(expiry_day_start=None), CLOCK)):
        out = mod.price_contract(terms, clock, _market(dividends=_schedule()))
        assert out.decision.model == mod.MODEL_UNAVAILABLE
        assert "settlement_clock_unknown" in out.decision.reasons
        assert all(v.status == mod.UNAVAILABLE for v in out.per_share.values())


# =======================================================================================
# req4 — refinement exposes nonconvergence; near-boundary higher derivatives are not precise
# =======================================================================================

def test_req4_smooth_european_case_is_converged_for_every_quantity():
    qual = mod.qualify_fd(S0, 80.0, T0, SIG0, R0, Q0, True, american=False)
    for name in mod.QUANTITIES:
        res = qual.quantities[name]
        assert res.status == mod.CONVERGED, name
        assert res.value == res.levels[2]
        assert res.interval is None


def test_req4_synthetic_nonconvergent_sequence_is_interval_without_point_value():
    res = mod.classify_refinement(1.0, 1.3, 0.9, atol=1e-3, rtol=1e-4)
    assert res.status == mod.INTERVAL
    assert res.value is None
    lo, hi = res.interval
    assert lo <= 0.9 - 0.4 + 1e-12 and hi >= 1.3 + 0.4 - 1e-12
    # A last difference inside tolerance is not enough when the first is outside it and
    # the sequence is not contracting by the frozen factor 0.75.
    slow = mod.classify_refinement(1.0, 1.0011, 1.0020, atol=1e-3, rtol=0.0)
    assert slow.status == mod.INTERVAL
    # Contracting differences inside tolerance are CONVERGED with an observed order.
    fast = mod.classify_refinement(1.0, 1.0008, 1.0010, atol=1e-3, rtol=0.0)
    assert fast.status == mod.CONVERGED and fast.value == 1.0010
    assert fast.order == pytest.approx(2.0, abs=1e-6)


def test_req4_non_finite_sequence_is_unavailable():
    for seq in ((1.0, float("nan"), 1.0), (float("inf"), 1.0, 1.0), (1.0, 1.0, float("-inf"))):
        res = mod.classify_refinement(*seq, atol=1e-3, rtol=1e-4)
        assert res.status == mod.UNAVAILABLE
        assert res.value is None and res.interval is None


def test_req4_european_atm_price_interval_brackets_the_analytic_value():
    qual = mod.qualify_fd(S0, K0, T0, SIG0, R0, Q0, True, american=False)
    res = qual.quantities["price"]
    exact = mod.bs_price(S0, K0, T0, SIG0, True, R0, Q0)
    if res.status == mod.CONVERGED:
        assert abs(res.value - exact) <= 5e-3
    else:
        assert res.status == mod.INTERVAL
        lo, hi = res.interval
        assert lo <= exact <= hi


def test_req4_near_boundary_american_put_never_reports_converged_higher_derivatives():
    qual = mod.qualify_fd(92.0, 120.0, T0, SIG0, R0, Q0, False, american=True)
    assert qual.boundary is not None
    assert qual.near_boundary is True
    for name in ("gamma", "vanna", "charm"):
        res = qual.quantities[name]
        assert res.status != mod.CONVERGED, name
        assert res.value is None
        if res.status == mod.INTERVAL:
            assert res.reason == "near_exercise_boundary"
    assert qual.quantities["price"].status in (mod.CONVERGED, mod.INTERVAL)


def test_req4_charm_stencil_straddling_an_ex_date_is_unavailable():
    t_div = 0.5 * T0 / FINE
    qual = mod.qualify_fd(S0, K0, T0, SIG0, R0, Q0, True, american=True,
                          dividends=[(t_div, 1.0)])
    assert qual.quantities["charm"].status == mod.UNAVAILABLE
    assert qual.quantities["charm"].reason == "ex_dividend_within_charm_stencil"
    far = mod.qualify_fd(S0, K0, T0, SIG0, R0, Q0, True, american=True, dividends=[(0.25, 1.0)])
    assert far.quantities["charm"].reason != "ex_dividend_within_charm_stencil"


@pytest.mark.parametrize("american", [True, False])
@pytest.mark.parametrize("sigma", [0.015, 4.995])
def test_req4_vol_bump_leaving_sigma_bounds_makes_vanna_unavailable_not_an_error(sigma, american):
    # Independent-audit finding M1: an in-bounds sigma whose frozen +/-0.01 vanna bump would
    # leave SIGMA_BOUNDS must not raise and must not shrink the bump; vanna fails closed.
    assert mod.SIGMA_BOUNDS[0] <= sigma <= mod.SIGMA_BOUNDS[1]
    qual = mod.qualify_fd(S0, K0, T0, sigma, R0, Q0, False, american=american)
    vanna = qual.quantities["vanna"]
    assert vanna.status == mod.UNAVAILABLE
    assert vanna.reason == "vol_bump_out_of_bounds"
    assert vanna.value is None and vanna.interval is None
    assert qual.vol_bump == mod.VOL_BUMP == 0.01
    for name in ("price", "delta", "gamma", "charm"):
        res = qual.quantities[name]
        assert res.reason != "vol_bump_out_of_bounds", name
        assert res.status in (mod.CONVERGED, mod.INTERVAL, mod.UNAVAILABLE), name


@pytest.mark.parametrize("sigma", [0.02, 4.99])
def test_req4_vol_bump_touching_sigma_bounds_still_reports_vanna(sigma):
    qual = mod.qualify_fd(S0, K0, T0, sigma, R0, Q0, False, american=True)
    assert qual.quantities["vanna"].reason != "vol_bump_out_of_bounds"
    assert qual.quantities["vanna"].status in (mod.CONVERGED, mod.INTERVAL)
    assert qual.vol_bump == 0.01


# =======================================================================================
# req5 — discriminating unit tests
# =======================================================================================

def test_req5_per_share_to_per_contract_needs_an_explicit_multiplier():
    assert mod.convert_size(2.5, "per_share", "per_contract", multiplier=100.0) == 250.0
    assert mod.convert_size(2.5, "per_share", "per_contract", multiplier=10.0) == 25.0
    assert mod.convert_size(250.0, "per_contract", "per_share", multiplier=100.0) == 2.5
    with pytest.raises(TypeError):
        mod.convert_size(2.5, "per_share", "per_contract")  # no default multiplier
    for bad in (0.0, -1.0, float("nan"), True):
        with pytest.raises(ValueError):
            mod.convert_size(2.5, "per_share", "per_contract", multiplier=bad)
    # A 10-share adjusted deliverable values differently from a 100-share contract.
    std = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule()))
    adj = mod.price_contract(_terms(occ_root="XYZ1", deliverable_shares=10.0), CLOCK,
                             _market(dividends=_schedule()))
    assert adj.decision.strike_per_share == pytest.approx(1000.0)
    assert std.decision.strike_per_share == pytest.approx(100.0)
    assert adj.price_per_contract.levels != std.price_per_contract.levels
    assert adj.price_per_contract.levels[2] == pytest.approx(
        10.0 * adj.per_share["price"].levels[2])


def test_req5_decimal_vol_points_and_vega_units_are_distinct():
    assert mod.convert_vol(0.25, "decimal", "vol_point") == pytest.approx(25.0)
    assert mod.convert_vol(25.0, "vol_point", "decimal") == pytest.approx(0.25)
    vega = mod.bs_vega(S0, K0, T0, SIG0, R0, Q0)
    per_pt = mod.convert_vega(vega, "per_unit_vol", "per_vol_point")
    assert per_pt == pytest.approx(vega / 100.0)
    bumped = mod.bs_price(S0, K0, T0, SIG0 + 0.01, True, R0, Q0) - mod.bs_price(
        S0, K0, T0, SIG0, True, R0, Q0)
    assert abs(bumped - per_pt) < 0.01 * abs(per_pt)
    with pytest.raises(ValueError):
        mod.convert_vol(0.25, "decimal", "percent")
    with pytest.raises(ValueError):
        mod.convert_vega(vega, "per_unit_vol", "per_pct")


def test_req5_annual_to_daily_charm_needs_a_declared_basis():
    _, _, _, charm_year = mod.bs_greeks(S0, K0, T0, SIG0, True, R0, Q0)
    d365 = mod.convert_charm(charm_year, "per_year", "per_day", days_per_year=365)
    d252 = mod.convert_charm(charm_year, "per_year", "per_day", days_per_year=252)
    assert d365 == pytest.approx(charm_year / 365.0)
    assert d252 == pytest.approx(charm_year / 252.0)
    assert d365 != d252
    assert mod.convert_charm(d252, "per_day", "per_year", days_per_year=252) == pytest.approx(
        charm_year)
    with pytest.raises(TypeError):
        mod.convert_charm(charm_year, "per_year", "per_day")
    for bad in (360, 0, True):
        with pytest.raises(ValueError):
            mod.convert_charm(charm_year, "per_year", "per_day", days_per_year=bad)
    with pytest.raises(ValueError):
        mod.convert_charm(charm_year, "per_year", "per_week", days_per_year=365)
    with pytest.raises(ValueError):
        mod.convert_size(1.0, "per_lot", "per_share", multiplier=100.0)


# =======================================================================================
# req6 — unknown adjusted deliverables and missing dividend metadata fail closed
# =======================================================================================

_FAILURES = [
    ("exercise_style_unknown", dict(exercise_style=None), {}),
    ("exercise_style_unknown", dict(exercise_style="BERMUDAN"), {}),
    ("deliverable_unknown", dict(deliverable_kind=None), {}),
    ("deliverable_unknown", dict(deliverable_shares=None), {}),
    ("adjusted_deliverable_unknown", dict(occ_root="XYZ1", deliverable_shares=None), {}),
    ("adjusted_deliverable_unknown", dict(occ_root="XYZB", deliverable_shares=None), {}),
    ("non_share_deliverable_not_modelled", dict(deliverable_kind="SHARES_PLUS_CASH"), {}),
    ("multiplier_unknown", dict(multiplier=None), {}),
    ("settlement_clock_unknown", dict(settlement=None), {}),
    ("dividend_metadata_missing", {}, dict(dividends=None)),
    ("rates_missing", {}, dict(rate=None)),
]


@pytest.mark.parametrize("reason,term_kw,market_kw", _FAILURES)
def test_req6_each_missing_term_fails_closed_with_a_named_reason(reason, term_kw, market_kw):
    mk = dict(dividends=_schedule())
    mk.update(market_kw)
    out = mod.price_contract(_terms(**term_kw), CLOCK, _market(**mk))
    assert out.decision.model == mod.MODEL_UNAVAILABLE
    assert reason in out.decision.reasons
    assert out.price_per_contract is None
    assert out.decision.multiplier is None and out.decision.shares_per_contract is None
    assert all(v.status == mod.UNAVAILABLE and v.value is None for v in out.per_share.values())


def test_req6_estimated_or_incomplete_dividend_schedule_fails_closed():
    est = _rec("e", known_at=VALUATION - 5 * DAY, ex_offset_days=20, amount=0.5,
               status=mod.ESTIMATED)
    d = mod.select_model(_terms(), CLOCK, _market(dividends=_schedule(est)))
    assert d.model == mod.MODEL_UNAVAILABLE
    assert "dividend_estimated_not_declared" in d.reasons
    short = mod.select_model(_terms(), CLOCK,
                             _market(dividends=_schedule(complete_through=PM_EXPIRY - 1)))
    assert "dividend_schedule_not_complete_through_expiry" in short.reasons
    late_assertion = mod.select_model(_terms(), CLOCK, _market(
        dividends=_schedule(asserted_at=VALUATION + 1)))
    assert "dividend_schedule_not_complete_through_expiry" in late_assertion.reasons
    # Missing (None) differs from a declared-complete empty schedule.
    missing = mod.select_model(_terms(), CLOCK, _market(dividends=None))
    empty = mod.select_model(_terms(), CLOCK, _market(dividends=_schedule()))
    assert missing.model == mod.MODEL_UNAVAILABLE
    assert "dividend_metadata_missing" in missing.reasons
    assert empty.model == mod.MODEL_AMERICAN_FD and empty.reasons == ()


def test_req6_all_failing_reasons_are_reported_together_and_no_100_is_assumed():
    terms = _terms(exercise_style=None, deliverable_shares=None, multiplier=None,
                   occ_root="XYZ2", settlement=None)
    d = mod.select_model(terms, None, _market(dividends=None, rate=None))
    for reason in ("exercise_style_unknown", "adjusted_deliverable_unknown",
                   "multiplier_unknown", "settlement_clock_unknown", "rates_missing",
                   "dividend_metadata_missing"):
        assert reason in d.reasons
    assert d.shares_per_contract is None and d.multiplier is None
    assert d.strike_per_share is None
    # No dataclass field or converter carries a default multiplier/deliverable.
    for cls in (mod.ContractTerms, mod.SessionClock, mod.MarketInputs):
        for f in dataclasses.fields(cls):
            assert f.default is dataclasses.MISSING, (cls.__name__, f.name)
    assert inspect.signature(mod.convert_size).parameters["multiplier"].default is \
        inspect.Parameter.empty
    assert inspect.signature(mod.convert_charm).parameters["days_per_year"].default is \
        inspect.Parameter.empty


def test_req6_selector_model_choice_follows_declared_terms_only():
    sched = _schedule()
    div = _schedule(_rec("d", known_at=VALUATION - 5 * DAY, ex_offset_days=20, amount=0.5))
    assert mod.select_model(_terms(is_call=True), CLOCK, _market(dividends=sched)).model == \
        mod.MODEL_EUROPEAN_BS_EQUIVALENT
    assert mod.select_model(_terms(is_call=True), CLOCK, _market(dividends=div)).model == \
        mod.MODEL_AMERICAN_FD
    assert mod.select_model(_terms(exercise_style=mod.EUROPEAN), CLOCK,
                            _market(dividends=div)).model == mod.MODEL_EUROPEAN_FD_DISCRETE_DIVIDEND
    idx = _terms(underlying="IDX", occ_root="IDXW", exercise_style=mod.EUROPEAN,
                 deliverable_kind=mod.CASH_INDEX, deliverable_shares=None, multiplier=100.0,
                 settlement=mod.AM_OPEN)
    no_q = mod.select_model(idx, CLOCK, _market(dividends=None))
    assert no_q.model == mod.MODEL_UNAVAILABLE and "dividend_metadata_missing" in no_q.reasons
    with_q = mod.select_model(idx, CLOCK, _market(dividends=None, continuous_yield=0.015))
    assert with_q.model == mod.MODEL_EUROPEAN_BS_CONTINUOUS_YIELD
    assert with_q.q == 0.015 and with_q.shares_per_contract == 100.0


@pytest.mark.parametrize("sigma", [0.015, 4.995])
def test_req6_edge_volatility_contract_prices_without_raising_and_vanna_fails_closed(sigma):
    out = mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule(), sigma=sigma))
    assert out.decision.model == mod.MODEL_AMERICAN_FD
    assert out.per_share["vanna"].status == mod.UNAVAILABLE
    assert out.per_share["vanna"].reason == "vol_bump_out_of_bounds"
    assert out.per_share["vanna"].value is None


# =======================================================================================
# Module contract — no silent activation
# =======================================================================================

_ALLOWED_ROOTS = {"math", "dataclasses", "typing", "numpy", "scipy", "builtins", "abc",
                  "collections", "functools", "enum"}


def _root(name):
    return (name or "").split(".")[0]


def test_no_silent_activation_research_only_and_registers_nothing():
    assert mod.RESEARCH_ONLY is True
    assert mod.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    assert "VERDICT: " + mod.VERDICT in mod.__doc__
    for name in dir(mod):
        low = name.lower()
        for word in ("register", "activate", "wire", "schedule_", "promote", "publish", "emit"):
            assert word not in low, name
    for name, val in vars(mod).items():
        if isinstance(val, types.ModuleType):
            assert _root(val.__name__) in _ALLOWED_ROOTS, name
            assert _root(val.__name__) not in ("time", "datetime", "os", "io", "socket")
        elif callable(val) and getattr(val, "__module__", None) not in (None, mod.__name__):
            assert _root(val.__module__) in _ALLOWED_ROOTS, (name, val.__module__)


def test_no_silent_activation_calls_leave_globals_and_imports_unchanged():
    before_globals = {k: id(v) for k, v in vars(mod).items()}
    before_modules = set(sys.modules)
    mod.qualify_fd(S0, K0, SHORT_T, SIG0, R0, Q0, False, american=True, levels=(20, 40, 80))
    mod.crr_price(S0, K0, SHORT_T, SIG0, R0, Q0, False, True, steps=50)
    mod.european_one_dividend_quadrature(S0, K0, T0, SIG0, R0, Q0, True, 0.25, 1.0, n_nodes=40)
    mod.price_contract(_terms(), CLOCK, _market(dividends=_schedule()), levels=(20, 40, 80))
    mod.price_contract(_terms(multiplier=None), CLOCK, _market(dividends=None))
    assert {k: id(v) for k, v in vars(mod).items()} == before_globals
    new = set(sys.modules) - before_modules
    assert all(_root(n) in ("numpy", "scipy") for n in new), sorted(new)


def test_no_silent_activation_fresh_import_has_no_side_effects(monkeypatch):
    import builtins

    def _refuse(*_a, **_k):
        raise AssertionError("module performed file I/O at import")

    monkeypatch.setattr(builtins, "open", _refuse)
    spec = importlib.util.find_spec("engine.options_american_exercise")
    before_modules = set(sys.modules)
    registered = sys.modules["engine.options_american_exercise"]
    fresh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fresh)
    assert fresh.RESEARCH_ONLY is True
    assert sys.modules["engine.options_american_exercise"] is registered
    new = set(sys.modules) - before_modules
    assert all(_root(n) in ("numpy", "scipy") for n in new), sorted(new)
