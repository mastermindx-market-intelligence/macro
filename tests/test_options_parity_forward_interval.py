from __future__ import annotations

# Hermetic tests for the Q12 research reference (synthetic data, integer clocks).

import dataclasses
import math

import numpy as np
import pytest

from engine import options_parity_forward_interval as m

D = 0.98
K = 100.0
WITNESS = (100.83673469387755, 101.16326530612245)


def leg(right, bid, ask, *, strike=K, idx=10, exercise="european", settlement="cash_pm",
        deliverable="100 IDX", multiplier=100.0, expiry="E1", underlying="IDX",
        standard=True):
    return m.OptionQuote(right=right, underlying=underlying, expiry=expiry, strike=strike,
                         deliverable=deliverable, multiplier=multiplier,
                         settlement=settlement, exercise=exercise, bid=bid, ask=ask,
                         quote_index=idx, deliverable_standard=standard)


def witness_pair(**kw):
    # True F = 101 at D = 0.98: C_mid - P_mid = (F - K) * D = 0.98.
    return leg("C", 5.00, 5.16, **kw), leg("P", 4.02, 4.18, **kw)


def priced_pair(strike, f_true=101.0, d=D, half=0.08, **kw):
    x = (f_true - strike) * d
    p_mid = 4.0 + max(0.0, strike - f_true)
    c_mid = p_mid + x
    return (leg("C", c_mid - half, c_mid + half, strike=strike, **kw),
            leg("P", p_mid - half, p_mid + half, strike=strike, **kw))


ARGS = dict(now_index=10, max_quote_age=2, max_async=1)


# req1 — pair identity includes deliverable / settlement / exercise / multiplier
@pytest.mark.parametrize("field,value", [
    ("deliverable", "100 IDX + 12.50 USD"), ("settlement", "cash_am"),
    ("exercise", "american"), ("multiplier", 10.0), ("expiry", "E2"), ("strike", 105.0),
])
def test_req1_pair_identity_includes_deliverable_and_settlement(field, value):
    c, p = witness_pair()
    p2 = dataclasses.replace(p, **{field: value})
    chk = m.check_pair(c, p2, **ARGS)
    assert not chk.eligible
    assert f"identity_mismatch:{field}" in chk.reasons
    assert "deliverable" in m.IDENTITY_FIELDS and "settlement" in m.IDENTITY_FIELDS
    # end to end, mismatched legs never form a pair
    est, diag = m.estimate_forward([c, p2], d_band=(D, D), **ARGS)
    assert est.status == "unavailable" and est.lo is None


def test_req1_nonstandard_deliverable_is_unavailable():
    c, p = witness_pair(standard=False, deliverable="100 IDX + 12.50 USD")
    est, _ = m.estimate_forward([c, p], d_band=(D, D), **ARGS)
    assert est.status == "unavailable"
    assert any("nonstandard_deliverable" in r for r in est.reasons)


# req2 — European synthetic control recovers the known interval
def test_req2_european_synthetic_control_recovers_interval():
    c, p = witness_pair()
    lo, hi = m.pair_forward_interval(c, p, (D, D))
    assert lo == pytest.approx(WITNESS[0], abs=1e-12)
    assert hi == pytest.approx(WITNESS[1], abs=1e-12)
    assert lo < 101.0 < hi
    est, _ = m.estimate_forward([c, p], d_band=(D, D), **ARGS)
    assert est.status == "consistent"
    assert (est.lo, est.hi) == pytest.approx(WITNESS, abs=1e-12)


def test_req2_multi_strike_intersection_contains_truth_and_discount_band_widens():
    legs = []
    for k in (90.0, 95.0, 100.0, 105.0, 110.0):
        legs.extend(priced_pair(k))
    est, _ = m.estimate_forward(legs, d_band=(D, D), **ARGS)
    assert est.status == "consistent" and est.n_pairs == 5
    assert est.lo <= 101.0 <= est.hi
    wide, _ = m.estimate_forward(legs, d_band=(0.97, 0.99), **ARGS)
    assert wide.status == "consistent"
    assert wide.lo <= est.lo and wide.hi >= est.hi


# req3 — crossed / stale / asynchronous quotes cannot manufacture precision
def test_req3_crossed_quote_rejected():
    c, p = witness_pair()
    crossed = dataclasses.replace(c, bid=5.20, ask=5.10)  # would shrink/invert interval
    chk = m.check_pair(crossed, p, **ARGS)
    assert not chk.eligible and "crossed_call" in chk.reasons
    est, _ = m.estimate_forward([crossed, p], d_band=(D, D), **ARGS)
    assert est.status == "unavailable" and est.lo is None and est.hi is None


def test_req3_locked_stale_async_future_rejected():
    c, p = witness_pair()
    assert "locked_put" in m.check_pair(c, dataclasses.replace(p, bid=4.10, ask=4.10),
                                        **ARGS).reasons
    assert "stale_call" in m.check_pair(dataclasses.replace(c, quote_index=5), p,
                                        **ARGS).reasons
    assert "asynchronous_legs" in m.check_pair(c, dataclasses.replace(p, quote_index=8),
                                               **ARGS).reasons
    assert "future_quote_put" in m.check_pair(c, dataclasses.replace(p, quote_index=11),
                                              **ARGS).reasons


def _bad_variant(kind):
    # a very tight pair at another strike that WOULD shrink the intersection if admitted
    c, p = priced_pair(95.0, half=0.001)
    if kind == "stale":
        return dataclasses.replace(c, quote_index=3), dataclasses.replace(p, quote_index=3)
    if kind == "future":
        return dataclasses.replace(c, quote_index=12), dataclasses.replace(p, quote_index=12)
    if kind == "async":
        return c, dataclasses.replace(p, quote_index=8)
    if kind == "crossed":
        return dataclasses.replace(c, bid=c.ask + 0.0005, ask=c.ask), p
    if kind == "locked":
        return c, dataclasses.replace(p, bid=p.ask)
    raise AssertionError(kind)


@pytest.mark.parametrize("kind,reason", [
    ("stale", "stale_call"), ("future", "future_quote_call"),
    ("async", "asynchronous_legs"), ("crossed", "crossed_call"), ("locked", "locked_put"),
])
def test_req3_bad_pair_cannot_narrow_a_good_estimate(kind, reason):
    good = list(priced_pair(100.0)) + list(priced_pair(105.0))
    base, _ = m.estimate_forward(good, d_band=(D, D), **ARGS)
    c, p = _bad_variant(kind)
    est, diag = m.estimate_forward(good + [c, p], d_band=(D, D), **ARGS)
    assert (est.status, est.lo, est.hi, est.n_pairs) == (base.status, base.lo, base.hi, 2)
    assert any(reason in r for _, r in diag["rejected"])


# D band — pairs must hold at ONE common discount factor (exact, not an outer bound)
def test_dband_pairs_need_a_common_discount_factor():
    # At any single D in [0.9, 1.0] the K=83.5 lower bound (83.5 + 18/D) exceeds the
    # K=82 upper bound (82 + 19/D); widening each pair over the band first would wrongly
    # report the overlap [101.5, 103.11].
    legs = []
    for k in (82.0, 83.5):
        legs += [leg("C", 19.5, 20.0, strike=k), leg("P", 1.0, 1.5, strike=k)]
    est, _ = m.estimate_forward(legs, d_band=(0.9, 1.0), **ARGS)
    assert est.status == "incompatible" and est.lo is None and est.hi is None
    assert "no_common_discount_factor_in_band" in est.reasons
    assert len(est.conflicts) >= 1
    ivs = [m.pair_forward_interval(legs[i], legs[i + 1], (0.9, 1.0)) for i in (0, 2)]
    assert max(iv[0] for iv in ivs) <= min(iv[1] for iv in ivs)  # outer bound overlaps


def _grid_union(pairs, d_lo, d_hi, n=20001):
    u = np.linspace(1.0 / d_hi, 1.0 / d_lo, n)
    lo = np.max([k + xl * u for k, xl, _ in pairs], axis=0)
    hi = np.min([k + xh * u for k, _, xh in pairs], axis=0)
    ok = lo <= hi
    if not ok.any():
        return None
    return float(lo[ok].min()), float(hi[ok].max())


@pytest.mark.parametrize("seed", range(24))
def test_dband_exact_matches_brute_force_grid(seed):
    rng = np.random.default_rng(seed)
    d_lo, d_hi = 0.85, 1.0
    d_true = rng.uniform(d_lo, d_hi)
    f_true = 100.0 + rng.normal(0, 2)
    legs, pairs = [], []
    for k in np.linspace(70.0, 130.0, int(rng.integers(2, 15))):
        x = (f_true - k) * d_true + rng.normal(0, 0.25)
        p_mid = 3.0 + max(0.0, k - f_true)
        half_c, half_p = rng.uniform(0.02, 0.3, size=2)
        c = leg("C", p_mid + x - half_c, p_mid + x + half_c, strike=float(k))
        p = leg("P", p_mid - half_p, p_mid + half_p, strike=float(k))
        legs += [c, p]
        pairs.append((float(k), c.bid - p.ask, c.ask - p.bid))
    est, _ = m.estimate_forward(legs, d_band=(d_lo, d_hi), **ARGS)
    grid = _grid_union(pairs, d_lo, d_hi)
    du = (1.0 / d_lo - 1.0 / d_hi) / 20000
    tol = 4 * du * max(abs(v) for _, a, b in pairs for v in (a, b)) + 1e-9
    if grid is None:
        assert est.status == "incompatible"
    else:
        assert est.status == "consistent"
        assert est.lo <= grid[0] + 1e-9 and est.hi >= grid[1] - 1e-9
        assert est.lo >= grid[0] - tol and est.hi <= grid[1] + tol
        # never wider than the band-widened outer bound
        widened = [m.pair_forward_interval(legs[i], legs[i + 1], (d_lo, d_hi))
                   for i in range(0, len(legs), 2)]
        assert est.lo >= max(w[0] for w in widened) - 1e-9
        assert est.hi <= min(w[1] for w in widened) + 1e-9


def test_dband_point_band_equals_plain_intersection():
    legs = []
    for k in (90.0, 95.0, 100.0, 105.0, 110.0):
        legs.extend(priced_pair(k))
    est, _ = m.estimate_forward(legs, d_band=(D, D), **ARGS)
    ivs = [m.pair_forward_interval(legs[i], legs[i + 1], (D, D)) for i in range(0, 10, 2)]
    assert (est.lo, est.hi) == (max(v[0] for v in ivs), min(v[1] for v in ivs))


# req4 — incompatible intervals are reported, not averaged
def test_req4_incompatible_intervals_reported_not_averaged():
    a = priced_pair(100.0, f_true=101.0)
    b = priced_pair(105.0, f_true=102.0)  # disjoint at these spreads
    est, _ = m.estimate_forward(list(a) + list(b), d_band=(D, D), **ARGS)
    assert est.status == "incompatible"
    assert est.lo is None and est.hi is None
    assert len(est.conflicts) >= 1
    assert est.max_overlap_count == 1


def test_req4_mixed_groups_are_not_combined():
    ivs = [m.PairInterval(100.0, 100.8, 101.2, ("A",)),
           m.PairInterval(100.0, 100.9, 101.1, ("B",))]
    est = m.combine_intervals(ivs)
    assert est.status == "unavailable"
    assert "mixed_identity_groups_not_combined" in est.reasons


# req5 — American applicability and dividend/borrow limits explicit
def test_req5_american_has_no_parity_forward():
    c, p = witness_pair(exercise="american", settlement="physical")
    est, _ = m.estimate_forward([c, p], d_band=(D, D), **ARGS)
    assert est.status == "unavailable"
    assert any("american" in r and "q02" in r for r in est.reasons)


def test_req5_american_bounds_need_dividend_and_borrow():
    c, p = witness_pair(exercise="american", settlement="physical")
    st, lo, hi = m.american_spot_bounds(c, p, discount_factor=D, dividend_pv_upper=None,
                                        borrow_negligible=True)
    assert st.startswith("unavailable") and lo is None
    st, lo, hi = m.american_spot_bounds(c, p, discount_factor=D, dividend_pv_upper=0.5,
                                        borrow_negligible=False)
    assert st.startswith("unavailable") and hi is None
    st, lo, hi = m.american_spot_bounds(c, p, discount_factor=D, dividend_pv_upper=0.5,
                                        borrow_negligible=True)
    assert st == "bounds_only" and lo < hi
    assert lo == pytest.approx((5.00 - 4.18) + K * D)
    assert hi == pytest.approx((5.16 - 4.02) + K + 0.5)


def test_req5_carry_is_joint_only():
    b_lo, b_hi = m.implied_net_carry_interval(100.8, 101.2, 99.9, 100.1, 0.25)
    assert b_lo < b_hi
    assert b_lo == pytest.approx(math.log(100.8 / 100.1) / 0.25)
    assert "joint" in m.CARRY_IDENTIFICATION and "not separately" in m.CARRY_IDENTIFICATION


# req6 — never relabelled as arbitrage or spot prediction
def test_req6_no_relabel_as_arbitrage_or_spot_prediction():
    c, p = witness_pair()
    est, _ = m.estimate_forward([c, p], d_band=(D, D), **ARGS)
    assert est.not_executable_arbitrage is True and est.not_spot_forecast is True
    assert est.label == m.MEASUREMENT_LABEL
    with pytest.raises(dataclasses.FrozenInstanceError):
        est.label = "arbitrage opportunity"  # type: ignore[misc]
    with pytest.raises(TypeError):
        m.ForwardEstimate("consistent", 1.0, 2.0, 1, not_spot_forecast=False)  # type: ignore[call-arg]
    names = {f.name for f in dataclasses.fields(m.ForwardEstimate)}
    assert not any(w in n for n in names for w in ("profit", "signal", "predict", "target"))


# bounded inputs
def test_bounded_inputs():
    c, p = witness_pair()
    with pytest.raises(ValueError):
        m.pair_forward_interval(c, p, (0.0, 0.98))
    with pytest.raises(ValueError):
        m.pair_forward_interval(c, p, (0.99, 0.98))
    with pytest.raises(ValueError):
        m.estimate_forward([c] * (m.MAX_LEGS + 1), d_band=(D, D), **ARGS)
    assert "non_finite_call" in m.check_pair(dataclasses.replace(c, bid=float("nan")), p,
                                             **ARGS).reasons


# no silent activation
def test_no_silent_activation():
    assert m.RESEARCH_ONLY is True
    assert m.VERDICT == "INSUFFICIENT_DATA"
    assert m.__doc__.startswith("RESEARCH REFERENCE — NOT WIRED")
    assert "INSUFFICIENT_DATA" in m.__doc__
    public = [n for n in dir(m) if not n.startswith("_")]
    for banned in ("register", "schedule", "publish", "write", "main", "run", "activate"):
        assert banned not in public
    # the module defines exactly this public callable surface and nothing else
    own_callables = {n for n in public if callable(getattr(m, n))
                     and getattr(getattr(m, n), "__module__", None) == m.__name__}
    assert own_callables == {
        "OptionQuote", "PairCheck", "PairInterval", "ForwardEstimate", "pair_identity",
        "group_identity", "check_pair", "applicability", "pair_forward_interval",
        "combine_intervals", "estimate_forward", "american_spot_bounds",
        "implied_net_carry_interval",
    }
    # the module itself binds no I/O, network or subprocess stack
    for mod in ("os", "io", "pathlib", "subprocess", "socket", "requests", "urllib"):
        assert mod not in vars(m)
