"""Tests for engine/global_liquidity_accounting.py (lane B2, task T04).

All pinned numeric expectations below come from the package oracle
``glt_fable_20261013/SYNTHETIC_ARITHMETIC.json``
(``evidence_type: SYNTHETIC_ARITHMETIC_ONLY_NOT_MARKET_RESULTS``): every value
asserted here is exact algebra on synthetic inputs, not a market measurement.
"""

from __future__ import annotations

import dataclasses
import random
from decimal import Decimal
from fractions import Fraction

import pandas as pd
import pytest

import engine.global_liquidity_accounting as gla
from engine.global_liquidity_accounting import (
    AccountingReconciliationError,
    ConceptAmount,
    FxDecomposition,
    MagnitudePair,
    RawMagnitude,
    ReserveIdentity,
    StandardizedMagnitude,
    assert_reconciles,
    assert_reserve_identity,
    decompose_fx_change,
    fx_rate_to_usd,
    incomplete_net_liquidity_proxy,
    raw_magnitudes,
    reserves_from_balance_sheet,
    reserve_change,
    standardized_magnitudes,
    sum_same_concept,
)
from engine.global_liquidity_transmission import causal_expanding_z


ORACLE = "glt_fable_20261013/SYNTHETIC_ARITHMETIC.json"


# --------------------------------------------------------------------------
# C07 / fx decomposition — exact synthetic cases
# --------------------------------------------------------------------------


def test_synthetic_fx_translation_only_exact():
    d = decompose_fx_change(
        Decimal("100"), Decimal("100"), Decimal("1"), Decimal("1.1")
    )
    assert d.is_null is False
    assert d.null_reason is None
    assert d.usd_prev == Decimal("100.0")
    assert d.usd_curr == Decimal("110.0")
    assert d.usd_change == Decimal("10.0")
    assert d.domestic_at_prior_fx == 0
    assert d.fx_translation == Decimal("10.0")
    assert d.interaction == Decimal("0.0")
    assert d.parts_sum() == d.usd_change
    assert_reconciles(d)


def test_synthetic_fx_quantity_and_fx_exact():
    d = decompose_fx_change(
        Decimal("100"), Decimal("120"), Decimal("1"), Decimal("1.1")
    )
    assert d.usd_change == Decimal("32.0")
    assert d.domestic_at_prior_fx == Decimal("20")
    assert d.fx_translation == Decimal("10.0")
    assert d.interaction == Decimal("2.0")
    assert d.parts_sum() == Decimal("32.0")
    assert_reconciles(d)


def test_synthetic_fx_cases_float_within_stated_tolerance():
    d1 = decompose_fx_change(100.0, 100.0, 1.0, 1.1)
    assert abs(d1.usd_change - 10.0) <= 1e-9
    assert abs(d1.domestic_at_prior_fx - 0.0) <= 1e-9
    assert abs(d1.fx_translation - 10.0) <= 1e-9
    assert abs(d1.interaction - 0.0) <= 1e-9
    assert_reconciles(d1)

    d2 = decompose_fx_change(100.0, 120.0, 1.0, 1.1)
    assert abs(d2.usd_change - 32.0) <= 1e-9
    assert abs(d2.domestic_at_prior_fx - 20.0) <= 1e-9
    assert abs(d2.fx_translation - 10.0) <= 1e-9
    assert abs(d2.interaction - 2.0) <= 1e-9
    assert_reconciles(d2)


def test_c07_constant_local_assets_rising_fx_has_zero_domestic_term():
    q_path = [Fraction("0.0068"), Fraction("0.0070"), Fraction("0.0075")]
    for q_prev, q_curr in zip(q_path, q_path[1:]):
        d = decompose_fx_change(
            Fraction(5_000_000), Fraction(5_000_000), q_prev, q_curr
        )
        assert d.domestic_at_prior_fx == 0
        assert d.interaction == 0
        assert d.usd_change == d.fx_translation
        assert d.usd_change > 0
        assert_reconciles(d)

    # control (C07's definitional anchor): with non-constant local assets the
    # domestic term is defined at the PRIOR fx, not the current fx
    l_prev, l_curr = Fraction(5_000_000), Fraction(5_100_000)
    d = decompose_fx_change(l_prev, l_curr, q_path[0], q_path[1])
    d_l = l_curr - l_prev
    assert d.domestic_at_prior_fx == q_path[0] * d_l
    assert d.domestic_at_prior_fx != q_path[1] * d_l  # fx rises, prior != curr
    assert (
        d.usd_change
        == d.domestic_at_prior_fx + d.fx_translation + d.interaction
    )


def test_sign_flip_rising_local_assets_falling_fx_is_negative_in_usd():
    d = decompose_fx_change(
        Decimal("100"), Decimal("110"), Decimal("1.0"), Decimal("0.8")
    )
    assert d.domestic_at_prior_fx == Decimal("10")
    assert d.fx_translation == Decimal("-20.0")
    assert d.interaction == Decimal("-2.0")
    assert d.usd_change == Decimal("-12.0")
    assert d.domestic_at_prior_fx > 0
    assert d.fx_translation < 0
    assert d.usd_change < 0
    assert_reconciles(d)


def test_currency_inversion_usdjpy_quote():
    usdjpy = fx_rate_to_usd(Decimal("150"), invert=True)
    assert usdjpy == Decimal(1) / Decimal(150)
    direct = fx_rate_to_usd(Decimal("1.1"), invert=False)
    assert direct == Decimal("1.1")
    assert fx_rate_to_usd(Decimal("0"), invert=True) is None
    assert fx_rate_to_usd(Decimal("-1.5"), invert=False) is None
    assert fx_rate_to_usd(None, invert=True) is None
    assert fx_rate_to_usd(float("nan"), invert=False) is None
    assert fx_rate_to_usd(float("inf"), invert=True) is None
    assert fx_rate_to_usd(Fraction(150), invert=True) == Fraction(1, 150)
    assert fx_rate_to_usd(150, invert=True) == Fraction(1, 150)


def test_missing_input_returns_null_with_reason():
    d = decompose_fx_change(Decimal("100"), None, Decimal("1"), Decimal("1.1"))
    assert d.is_null is True
    assert d.null_reason is not None and "local_curr" in d.null_reason
    assert d.usd_prev is None
    assert d.usd_curr is None
    assert d.usd_change is None
    assert d.domestic_at_prior_fx is None
    assert d.fx_translation is None
    assert d.interaction is None
    assert d.parts_sum() is None

    d2 = decompose_fx_change(100.0, 110.0, float("nan"), 1.1)
    assert d2.is_null and "usd_per_local_prev" in d2.null_reason
    with pytest.raises(ValueError):
        assert_reconciles(d2)

    d3 = decompose_fx_change(
        100.0, 110.0, 1.0, None
    )
    assert d3.is_null and "usd_per_local_curr" in d3.null_reason


def test_non_positive_fx_is_null_not_zero():
    d = decompose_fx_change(100.0, 110.0, 1.0, 0.0)
    assert d.is_null and "non-positive fx" in d.null_reason
    assert "usd_per_local_curr" in d.null_reason
    assert d.usd_change is None
    assert d.parts_sum() is None

    d2 = decompose_fx_change(100.0, 110.0, -0.5, 1.1)
    assert d2.is_null and "usd_per_local_prev" in d2.null_reason
    d3 = decompose_fx_change(
        Decimal("100"), Decimal("110"), Decimal("0"), Decimal("1.1")
    )
    assert d3.is_null


def test_bool_and_mixed_decimal_float_are_refused():
    with pytest.raises(TypeError):
        decompose_fx_change(True, 100.0, 1.0, 1.1)
    with pytest.raises(TypeError):
        decompose_fx_change(100.0, True, 1.0, 1.1)
    with pytest.raises(TypeError):
        fx_rate_to_usd(False, invert=True)
    with pytest.raises(TypeError):
        decompose_fx_change(Decimal("100"), 120.0, Decimal("1"), Decimal("1.1"))
    with pytest.raises(TypeError):
        reserves_from_balance_sheet(
            assets=Decimal("1000"),
            treasury_cash=100.0,
            reverse_repo=200,
            other_nonreserve_liabilities_and_capital=100,
        )


def test_randomized_property_parts_reconcile_seeded():
    rng = random.Random(20261013)
    cases = []
    for _ in range(500):
        l_prev = rng.uniform(1e3, 1e13)
        l_curr = rng.uniform(1e3, 1e13)
        q_prev = rng.uniform(1e-4, 2.0)
        q_curr = rng.uniform(1e-4, 2.0)
        cases.append((l_prev, l_curr, q_prev, q_curr))

    for l_prev, l_curr, q_prev, q_curr in cases:
        d = decompose_fx_change(l_prev, l_curr, q_prev, q_curr)
        assert not d.is_null
        assert_reconciles(d)

    for l_prev, l_curr, q_prev, q_curr in cases:
        d = decompose_fx_change(
            Fraction(l_prev), Fraction(l_curr), Fraction(q_prev), Fraction(q_curr)
        )
        assert d.parts_sum() - d.usd_change == 0
        assert d.usd_change - (d.usd_curr - d.usd_prev) == 0
        assert_reconciles(d)


def test_assert_reconciles_detects_a_broken_decomposition():
    d = decompose_fx_change(
        Decimal("100"), Decimal("120"), Decimal("1"), Decimal("1.1")
    )
    broken = dataclasses.replace(d, interaction=d.interaction + 1)
    assert broken.parts_sum() != broken.usd_change
    with pytest.raises(AccountingReconciliationError):
        assert_reconciles(broken)
    assert_reconciles(d)  # the untouched decomposition still reconciles


# --------------------------------------------------------------------------
# US reserves identity (R = A - N) and the incomplete proxy
# --------------------------------------------------------------------------


def _reserve_ri(assets, tga, rrp, other):
    return reserves_from_balance_sheet(
        assets=assets,
        treasury_cash=tga,
        reverse_repo=rrp,
        other_nonreserve_liabilities_and_capital=other,
    )


def test_synthetic_reserve_identity_change_is_minus_10_and_proxy_is_plus_10():
    # Oracle reserve_identity inputs verbatim, ONE balance sheet per date:
    # the proxy and the identity read the same assets/TGA/RRP, so the sign
    # disagreement is a property of the proxy, not of different inputs.
    prev = _reserve_ri(1000, 120, 80, 200)
    curr = _reserve_ri(1010, 150, 50, 220)
    assert prev.reserves == 600
    assert curr.reserves == 590
    assert reserve_change(prev, curr) == -10
    assert_reserve_identity(prev)
    assert_reserve_identity(curr)

    proxy_prev = incomplete_net_liquidity_proxy(assets=1000, treasury_cash=120, reverse_repo=80)
    proxy_curr = incomplete_net_liquidity_proxy(assets=1010, treasury_cash=150, reverse_repo=50)
    assert proxy_prev.value == 800
    assert proxy_curr.value == 810
    assert (proxy_curr.value - proxy_prev.value) == 10
    assert (proxy_curr.value - proxy_prev.value) == -reserve_change(prev, curr)


def test_reserve_identity_null_component_propagates_not_zero():
    prev = _reserve_ri(1000, 100, 200, 100)
    null_ri = _reserve_ri(1000, 100, 200, None)
    assert null_ri.reserves is None
    assert null_ri.missing == ("other_nonreserve_liabilities_and_capital",)
    assert null_ri.null_reason is not None
    assert "other_nonreserve_liabilities_and_capital" in null_ri.null_reason
    assert reserve_change(null_ri, prev) is None
    assert reserve_change(prev, null_ri) is None
    with pytest.raises(ValueError):
        assert_reserve_identity(null_ri)

    proxy = incomplete_net_liquidity_proxy(assets=1100, treasury_cash=200, reverse_repo=None)
    assert proxy.value is None
    assert proxy.null_reason is not None
    assert "reverse_repo" in proxy.null_reason

    multi = _reserve_ri(None, 100, None, 300)
    assert multi.reserves is None
    assert multi.missing == ("assets", "reverse_repo")


def test_assert_reserve_identity_detects_inconsistent_components():
    ri = _reserve_ri(1000, 100, 200, 100)
    assert_reserve_identity(ri)
    broken = dataclasses.replace(ri, reserves=ri.reserves + 1)
    with pytest.raises(AccountingReconciliationError):
        assert_reserve_identity(broken)


# --------------------------------------------------------------------------
# C08 — raw vs standardized magnitudes are distinct, non-substitutable types
# --------------------------------------------------------------------------


def test_c08_magnitude_types_are_not_substitutable():
    raw = RawMagnitude(1.0, "u")
    std = StandardizedMagnitude(1.0, "u", min_periods=2)
    assert raw != std

    with pytest.raises(TypeError):
        MagnitudePair(
            magnitude=StandardizedMagnitude(1.0, "u", min_periods=2),
            magnitude_z=StandardizedMagnitude(1.0, "u", min_periods=2),
        )
    with pytest.raises(TypeError):
        MagnitudePair(magnitude=RawMagnitude(1.0, "u"), magnitude_z=RawMagnitude(2.0, "u"))
    pair = MagnitudePair(magnitude=raw, magnitude_z=std)
    assert pair.magnitude is raw and pair.magnitude_z is std

    with pytest.raises(TypeError):
        standardized_magnitudes([1.0, 2.0], min_periods=2)
    with pytest.raises(TypeError):
        standardized_magnitudes([std], min_periods=2)
    with pytest.raises(TypeError):
        raw_magnitudes([RawMagnitude(1, "u")], unit="u")
    with pytest.raises(ValueError):
        standardized_magnitudes(
            [RawMagnitude(1.0, "u"), RawMagnitude(2.0, "v")], min_periods=2
        )


def test_standardized_magnitudes_are_prior_only_and_prefix_causal():
    rng = random.Random(20261013)
    levels = [100.0]
    for _ in range(29):
        levels.append(levels[-1] + rng.uniform(-5.0, 5.0))
    assert len(levels) == 30

    unit = "usd_bn"
    full = standardized_magnitudes(raw_magnitudes(levels, unit=unit), min_periods=3)
    assert len(full) == 30
    assert full[0].value is None  # raw magnitude at t=0 is null
    assert full[1].value is None  # 0 prior observations < min_periods
    assert full[2].value is None  # 1 prior value < min_periods
    assert full[3].value is None  # 2 prior values < min_periods
    assert full[4].value is not None  # 3 prior values >= min_periods
    for m in full:
        assert m.method == "prior_only_expanding_z"
        assert m.min_periods == 3
        assert m.unit == "prior_only_expanding_z_of_" + unit

    for k in (10, 20, 30):
        prefix = standardized_magnitudes(raw_magnitudes(levels[:k], unit=unit), min_periods=3)
        assert prefix == full[:k]

    perturbed = levels[:-1] + [levels[-1] + 1000.0]
    perturbed_z = standardized_magnitudes(raw_magnitudes(perturbed, unit=unit), min_periods=3)
    assert perturbed_z[:29] == full[:29]
    assert perturbed_z[29].value != full[29].value


def test_standardized_magnitudes_match_incumbent_causal_expanding_z():
    """Mapping to the incumbent: ``causal_expanding_z(series, min_periods=m)``

    defines index i when at least ``m`` observations strictly before i exist
    (``expanding(min_periods=m)...shift(1)``). Here raw magnitude at position t
    is series index t-1, and ``standardized_magnitudes`` defines it when at
    least ``m`` non-null prior raws exist. So the same ``min_periods`` value
    means "at least m prior observations" in both, and my position t compares
    to incumbent index t-1.
    """
    rng = random.Random(20261013)
    levels = [50.0]
    for _ in range(39):
        levels.append(levels[-1] + rng.uniform(-2.0, 2.0))
    raw_values = [levels[i + 1] - levels[i] for i in range(len(levels) - 1)]
    assert all(pd.notna(v) for v in raw_values)

    min_periods = 4
    mine = standardized_magnitudes(
        raw_magnitudes(levels, unit="usd_bn"), min_periods=min_periods
    )
    incumbent = causal_expanding_z(pd.Series(raw_values, dtype=float), min_periods)

    compared = 0
    for t in range(len(mine)):
        series_index = t - 1
        if series_index < 0:
            assert mine[t].value is None
            continue
        expected = incumbent.iloc[series_index]
        if pd.isna(expected):
            assert mine[t].value is None
            continue
        assert mine[t].value is not None
        assert abs(mine[t].value - float(expected)) <= 1e-12
        compared += 1
    assert compared >= 30


# --------------------------------------------------------------------------
# C05 — concept guard
# --------------------------------------------------------------------------


def test_sum_same_concept_refuses_pooling_and_propagates_null():
    total = sum_same_concept(
        [
            ConceptAmount("central_bank_assets", 1, "usd_bn"),
            ConceptAmount("central_bank_assets", 2, "usd_bn"),
        ]
    )
    assert total.concept == "central_bank_assets"
    assert total.value == 3
    assert total.unit == "usd_bn"

    with pytest.raises(ValueError) as exc:
        sum_same_concept(
            [
                ConceptAmount("central_bank_assets", 1, "usd_bn"),
                ConceptAmount("reserves", 2, "usd_bn"),
            ]
        )
    assert "C05" in str(exc.value)

    with_null = sum_same_concept(
        [
            ConceptAmount("private_credit", 1, "usd_bn"),
            ConceptAmount("private_credit", None, "usd_bn"),
            ConceptAmount("private_credit", 3, "usd_bn"),
        ]
    )
    assert with_null.value is None
    assert with_null.concept == "private_credit"

    with pytest.raises(ValueError):
        sum_same_concept(
            [
                ConceptAmount("broad_money", 1, "usd_bn"),
                ConceptAmount("broad_money", 2, "cny_tn"),
            ]
        )

    with pytest.raises(ValueError):
        sum_same_concept([])

    with pytest.raises(ValueError):
        ConceptAmount("not_a_concept", 1, "usd_bn")


# --------------------------------------------------------------------------
# T18 repricing distinction — arithmetic pin only (T18 owns the consumer)
# --------------------------------------------------------------------------


def test_synthetic_repricing_distinction_arithmetic_only_t18_owns_consumer():
    """T18 owns the consumer proof; this test only pins the arithmetic so every
    SYNTHETIC_ARITHMETIC case maps to a named test."""
    reference_path_discrepancy = Decimal("0.04") - Decimal("0.01")
    naive_old_full_minus_realized = Decimal("0.08") - Decimal("0.01")
    hypothetical_updated_remaining_expectation = Decimal("-0.02")

    assert reference_path_discrepancy == Decimal("0.03")
    assert naive_old_full_minus_realized == Decimal("0.07")
    assert reference_path_discrepancy != hypothetical_updated_remaining_expectation
    assert reference_path_discrepancy != naive_old_full_minus_realized
    assert naive_old_full_minus_realized != hypothetical_updated_remaining_expectation


# --------------------------------------------------------------------------
# Purity / display-tier markers
# --------------------------------------------------------------------------


def test_module_is_display_tier_and_pure():
    assert gla.VALIDATED is False
    assert gla.CLAIM_LEVEL == "synthetic_arithmetic_identity"
    source = open(gla.__file__, "r", encoding="utf-8").read()
    assert "datetime.now" not in source
    assert "import pandas" not in source
    assert "import numpy" not in source


# --------------------------------------------------------------------------
# B4 adversarial-review regressions (non-finite values fail closed)
# --------------------------------------------------------------------------


def test_overflowing_float_decomposition_is_null_with_reason_never_reconciles():
    # Finite inputs whose float products overflow to inf (and inf - inf to NaN)
    # are a null decomposition with a reason, never a garbage "reconciled" one.
    d = decompose_fx_change(1e308, 1e308, 10.0, 10.0)
    assert d.is_null
    assert d.null_reason.startswith("non-finite result (overflow)")
    assert d.usd_change is None and d.parts_sum() is None
    with pytest.raises(ValueError):
        assert_reconciles(d)


def test_assert_reconciles_fails_closed_on_non_finite_fields():
    # A hand-built decomposition carrying NaN must not pass because
    # ``abs(nan) > limit`` is False.
    d = decompose_fx_change(100.0, 120.0, 1.0, 1.1)
    poisoned = dataclasses.replace(d, interaction=float("nan"))
    with pytest.raises(AccountingReconciliationError):
        assert_reconciles(poisoned)
    inf_scale = dataclasses.replace(
        d, usd_prev=float("inf"), usd_curr=float("inf"), usd_change=float("nan")
    )
    with pytest.raises(AccountingReconciliationError):
        assert_reconciles(inf_scale)


def test_exact_int_decomposition_beyond_float_range_reconciles_exactly():
    # An exact decomposition too large for a float reconciles exactly (no
    # OverflowError); a broken one of the same size fails closed.
    d = decompose_fx_change(10**400, 10**400 + 5, Fraction(1, 3), Fraction(1, 2))
    assert not d.is_null
    assert d.parts_sum() == d.usd_change
    assert_reconciles(d)
    broken = dataclasses.replace(d, interaction=d.interaction + 1)
    with pytest.raises(AccountingReconciliationError):
        assert_reconciles(broken)


def test_standardized_magnitude_non_finite_raw_is_null_never_nan():
    raws = [
        RawMagnitude(Decimal(v), "usd") for v in ("1", "2", "3", "1e400", "4")
    ]
    values = [m.value for m in standardized_magnitudes(raws, min_periods=2)]
    assert values[3] is None  # the non-finite raw is null, not NaN
    assert values[4] == 2.0  # and it never entered the prior sample [1, 2, 3]
    assert all(v is None or v == v for v in values)  # no NaN anywhere


def test_reserve_change_non_finite_side_is_null_never_nan():
    prev = _reserve_ri(1000, 120, 80, 200)
    curr = _reserve_ri(1010, 150, 50, 220)
    assert reserve_change(prev, curr) == -10
    assert reserve_change(prev, dataclasses.replace(curr, reserves=float("inf"))) is None
    assert reserve_change(dataclasses.replace(prev, reserves=float("nan")), curr) is None


def test_standardized_magnitude_overflowing_prior_variance_is_null_never_raises():
    # B5 NF1: all-finite raws whose squared prior deviations exceed float
    # range used to raise OverflowError; the z is null instead.
    raws = [RawMagnitude(v, "usd") for v in (1e200, -1e200, 1e200, 5e199)]
    values = [m.value for m in standardized_magnitudes(raws, min_periods=2)]
    assert values == [None, None, None, None]


def test_standardized_magnitude_non_finite_z_is_null_never_inf():
    # B5 NF2: a finite raw over a tiny-but-nonzero prior std gives a z that
    # overflows to inf; the z guard makes it null.
    raws = [RawMagnitude(v, "usd") for v in (0.0, 1e-150, 0.0, 1e308)]
    values = [m.value for m in standardized_magnitudes(raws, min_periods=2)]
    assert values[2] is not None and abs(values[2]) < float("inf")
    assert values[3] is None


def test_standardized_magnitude_silently_infinite_variance_is_null_never_zero():
    # B5 NF2: priors whose squared deviations are each finite but whose sum
    # overflows to inf silently; the std guard makes the head null, not 0.0.
    priors = [5e153 if i % 2 == 0 else -5e153 for i in range(20)]
    raws = [RawMagnitude(v, "usd") for v in priors + [1.0]]
    values = [m.value for m in standardized_magnitudes(raws, min_periods=2)]
    assert values[-1] is None
