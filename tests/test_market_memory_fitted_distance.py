"""Focused tests for the Market Memory v2 fitted exact-distance module."""

import copy
import decimal
import re
from fractions import Fraction

import pytest

from engine.neuralweb.market_memory_fitted_distance import (
    ARITHMETIC_ID,
    ERR_CATEGORY,
    ERR_NEGATIVE_ZERO,
    ERR_NUMERIC_BOUND,
    ERR_NUMERIC_FORM,
    ERR_NUMERIC_TYPE,
    ERR_VECTOR,
    FittedDistanceError,
    MAX_INTEGER_DIGITS,
    compare_coordinates,
)

ZERO = "0." + "0" * 18
UNIT = "0." + "0" * 17 + "1"


def q18(frac):
    """Independent reference quantizer: half-even to 18 fraction digits, once."""
    units, remainder = divmod(frac.numerator * 10 ** 18, frac.denominator)
    if 2 * remainder > frac.denominator or (
        2 * remainder == frac.denominator and units % 2 == 1
    ):
        units += 1
    return "%d.%018d" % divmod(units, 10 ** 18)


def vec(growth=ZERO, inflation=ZERO, quad="Q1", liquidity="neutral", cycle="mid"):
    return [growth, inflation, quad, liquidity, cycle]


def as_fraction(component):
    return Fraction(int(component["numerator"]), int(component["denominator"]))


def test_identical_vector_gives_exact_zero():
    result = compare_coordinates(vec(), vec())
    assert result["arithmetic"] == ARITHMETIC_ID
    assert result["arithmetic"] == (
        "q18_coordinates_exact_fraction_equal_weight_L1_final_q18_half_even.v2"
    )
    assert result["distance_q18"] == "0.000000000000000000"
    for name in ("growth_score", "inflation_score", "quad", "liquidity_overlay", "cycle_tag"):
        assert result["components"][name] == {"numerator": "0", "denominator": "1"}
    assert compare_coordinates(tuple(vec()), tuple(vec())) == result


def test_numeric_difference_exact_fraction():
    left = vec(growth="0.100000000000000000")
    right = vec(growth="0.400000000000000000")
    result = compare_coordinates(left, right)
    assert result["components"]["growth_score"] == {"numerator": "3", "denominator": "10"}
    assert result["components"]["inflation_score"] == {"numerator": "0", "denominator": "1"}
    assert result["components"]["quad"]["numerator"] == "0"
    # hand-checked: (3/10) / 5 = 3/50
    assert result["distance_q18"] == "0.060000000000000000"
    assert Fraction(result["distance_q18"]) == Fraction(3, 50)


def test_categorical_mismatch_is_exactly_one():
    result = compare_coordinates(vec(quad="Q1"), vec(quad="Q3"))
    assert result["components"]["quad"] == {"numerator": "1", "denominator": "1"}
    assert result["distance_q18"] == "0.200000000000000000"
    assert Fraction(result["distance_q18"]) == Fraction(1, 5)

    result = compare_coordinates(vec(liquidity="expanding"), vec(liquidity="contracting"))
    assert result["components"]["liquidity_overlay"] == {"numerator": "1", "denominator": "1"}

    result = compare_coordinates(vec(cycle="early"), vec(cycle="late"))
    assert result["components"]["cycle_tag"] == {"numerator": "1", "denominator": "1"}


def test_combined_components_sum_exact():
    left = vec(growth=ZERO, quad="Q2", cycle="late")
    right = vec(growth="0.500000000000000000", quad="Q4", cycle="late")
    result = compare_coordinates(left, right)
    assert as_fraction(result["components"]["growth_score"]) == Fraction(1, 2)
    assert as_fraction(result["components"]["quad"]) == 1
    assert as_fraction(result["components"]["cycle_tag"]) == 0
    # hand-checked: (1/2 + 1) / 5 = 3/10
    assert result["distance_q18"] == "0.300000000000000000"
    assert Fraction(result["distance_q18"]) == Fraction(3, 10)


def test_distance_may_legitimately_exceed_one():
    big = "9" * 40 + "." + "0" * 18
    left = vec(growth=big, quad="Q1", liquidity="expanding", cycle="early")
    right = vec(quad="Q2", liquidity="contracting", cycle="late")
    result = compare_coordinates(left, right)
    expected_growth = Fraction(10 ** 40 - 1)  # 9999...9.0 is exactly this integer
    assert as_fraction(result["components"]["growth_score"]) == expected_growth
    exact = (expected_growth + 3) / 5
    assert exact > 1
    assert Fraction(result["distance_q18"]) > 1
    assert result["distance_q18"] == q18(exact)


def test_negative_values_use_absolute_difference():
    result = compare_coordinates(
        vec(growth="-1.500000000000000000"), vec(growth="1.500000000000000000")
    )
    assert result["components"]["growth_score"] == {"numerator": "3", "denominator": "1"}
    assert result["distance_q18"] == "0.600000000000000000"

    result = compare_coordinates(vec(growth="-" + UNIT), vec())
    assert as_fraction(result["components"]["growth_score"]) == Fraction(1, 10 ** 18)


def test_no_clipping_and_no_range_assumption():
    result = compare_coordinates(
        vec(growth="2.500000000000000000"), vec(growth="1000.000000000000000000")
    )
    # hand-checked: |1000 - 2.5| = 1995/2, distance = (1995/2)/5 = 199.5
    assert result["components"]["growth_score"] == {"numerator": "1995", "denominator": "2"}
    assert result["distance_q18"] == "199.500000000000000000"


def test_final_rounding_on_reachable_steps_only():
    # Distances built from q18 components divided by 5 are exact multiples of
    # 0.2e-18, so true half-way ties (2.5e-18, 3.5e-18) are unreachable.  The
    # reachable 0.2e-18 steps around the half point pin the single final
    # half-even quantization instead; every case below needs rounding, and the
    # per-component rationals stay exact, so rounding demonstrably happens
    # only once, at the end.
    cases = {
        1: "0.000000000000000000",  # 0.2e-18 rounds down
        2: "0.000000000000000000",  # 0.4e-18 rounds down
        3: "0.000000000000000001",  # 0.6e-18 rounds up
        4: "0.000000000000000001",  # 0.8e-18 rounds up
        7: "0.000000000000000001",  # 1.4e-18 rounds down after carry
        13: "0.000000000000000003",  # 2.6e-18 rounds up after carry
    }
    for units, expected in cases.items():
        growth = "%d.%018d" % divmod(units, 10 ** 18)
        result = compare_coordinates(vec(growth=growth), vec())
        exact = Fraction(units, 5 * 10 ** 18)
        assert exact % 1 == exact and exact != Fraction(expected)  # rounding really occurred
        assert result["distance_q18"] == expected
        assert result["distance_q18"] == q18(exact)
        assert as_fraction(result["components"]["growth_score"]) == Fraction(units, 10 ** 18)


def test_rounding_carries_across_the_dot():
    growth = "%d.%018d" % divmod(5 * 10 ** 18 - 2, 10 ** 18)  # 4.999999999999999998
    result = compare_coordinates(vec(growth=growth), vec())
    exact = Fraction(5 * 10 ** 18 - 2, 5 * 10 ** 18)  # 0.9999999999999999996
    assert result["distance_q18"] == "1.000000000000000000"
    assert result["distance_q18"] == q18(exact)


def test_single_final_rounding_across_components():
    result = compare_coordinates(vec(growth=UNIT, inflation=UNIT), vec())
    exact = Fraction(2, 5 * 10 ** 18)  # 0.4e-18
    assert result["distance_q18"] == "0.000000000000000000"
    assert result["distance_q18"] == q18(exact)
    assert Fraction(result["distance_q18"]) != exact  # exact rational preserved, rounding once

    result = compare_coordinates(vec(growth=UNIT, inflation=UNIT, quad="Q1"), vec(quad="Q2"))
    exact = (Fraction(2, 10 ** 18) + 1) / 5  # 0.2 + 0.4e-18
    assert result["distance_q18"] == "0.200000000000000000"
    assert result["distance_q18"] == q18(exact)


def test_maximum_integer_digits_are_accepted():
    big = "9" * MAX_INTEGER_DIGITS + "." + "0" * 17 + "1"
    result = compare_coordinates(vec(growth=big), vec())
    # 999...9.000000000000000001 -> (10^400 - 1) * 10^18 + 1 units of 1e-18,
    # coprime to 10^18, so the reduced rational keeps the full q18 denominator.
    expected = Fraction((10 ** MAX_INTEGER_DIGITS - 1) * 10 ** 18 + 1, 10 ** 18)
    assert as_fraction(result["components"]["growth_score"]) == expected
    assert result["distance_q18"] == q18(expected / 5)
    assert re.fullmatch(r"\d+\.\d{18}", result["distance_q18"])


def test_oversize_is_refused_by_the_length_bound_before_expensive_parsing():
    # ERR_NUMERIC_BOUND is emitted only by the cheap length guard, which runs
    # before the canonical-form regex and before any int/Fraction conversion.
    # Receiving it -- and not ERR_NUMERIC_FORM, whose only producer sits after
    # the guard -- is the tripwire proving oversize is rejected early, with no
    # timing or implementation mocks involved.
    too_long = "1" * (MAX_INTEGER_DIGITS + 1) + "." + "0" * 18
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(growth=too_long), vec())
    assert str(excinfo.value) == ERR_NUMERIC_BOUND
    assert str(excinfo.value) != ERR_NUMERIC_FORM

    huge = "9" * 1_000_000  # no dot, far past the bound
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(growth=huge), vec())
    assert str(excinfo.value) == ERR_NUMERIC_BOUND

    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(), vec(inflation="-9" * (MAX_INTEGER_DIGITS + 1) + "." + "0" * 18))
    assert str(excinfo.value) == ERR_NUMERIC_BOUND


@pytest.mark.parametrize(
    "bad",
    [
        None,
        {},
        {"growth": ZERO},
        ZERO,
        b"1.000000000000000000",
        123,
        1.5,
        True,
        [ZERO, ZERO, "Q1", "neutral", "mid", "extra"],
        [ZERO, ZERO, "Q1", "neutral"],
        [ZERO, ZERO, "Q1"],
        [],
        (ZERO, ZERO, "Q1", "neutral"),
    ],
)
def test_vector_type_and_length_rejected(bad):
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(bad, vec())
    assert isinstance(excinfo.value, ValueError)


def test_subclasses_are_rejected():
    class VectorSub(list):
        pass

    class TupleSub(tuple):
        pass

    class StrSub(str):
        def __int__(self):  # pragma: no cover - reached only if the type check is skipped
            raise AssertionError("conversion attempted on a str subclass")

        def __index__(self):  # pragma: no cover
            raise AssertionError("conversion attempted on a str subclass")

    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(VectorSub(vec()), vec())
    assert str(excinfo.value) == ERR_VECTOR

    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(TupleSub(vec()), vec())
    assert str(excinfo.value) == ERR_VECTOR

    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(growth=StrSub("1.000000000000000000")), vec())
    assert str(excinfo.value) == ERR_NUMERIC_TYPE


BAD_NUMERIC_FORMS = [
    "NaN",
    "nan",
    "Infinity",
    "-Infinity",
    "+Infinity",
    "1e0",
    "1E18",
    "1.000000000000000000e0",
    "-1.000000000000000000E0",
    "+1.000000000000000000",
    "+0.000000000000000000",
    "01.000000000000000000",
    "00.000000000000000000",
    "000.000000000000000000",
    "-01.000000000000000000",
    "1.0000000000000000",
    "1.00000000000000000000",
    "1.0",
    "1.",
    ".500000000000000000",
    "1",
    "0",
    "-0",
    "",
    ".",
    "-",
    "--1.000000000000000000",
    " 1.000000000000000000",
    "1.000000000000000000 ",
    "1 000.000000000000000000",
    "1_0.000000000000000000",
    "0x1.000000000000000000",
]


@pytest.mark.parametrize("bad", BAD_NUMERIC_FORMS)
def test_malformed_numeric_strings_rejected_as_malformed(bad):
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(growth=bad), vec())
    assert str(excinfo.value) == ERR_NUMERIC_FORM
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(inflation=bad), vec())
    assert str(excinfo.value) == ERR_NUMERIC_FORM


def test_negative_zero_rejected_but_positive_zero_allowed():
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(growth="-0.000000000000000000"), vec())
    assert str(excinfo.value) == ERR_NEGATIVE_ZERO

    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(), vec(inflation="-0.000000000000000000"))
    assert str(excinfo.value) == ERR_NEGATIVE_ZERO

    result = compare_coordinates(vec(growth=ZERO), vec(inflation=ZERO))
    assert result["distance_q18"] == "0.000000000000000000"


@pytest.mark.parametrize(
    "bad",
    [None, 1, 1.0, True, False, b"1.000000000000000000", [UNIT], {"v": 1}],
)
def test_non_string_numeric_components_rejected(bad):
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(growth=bad), vec())
    assert str(excinfo.value) == ERR_NUMERIC_TYPE


@pytest.mark.parametrize(
    "field,bad",
    [
        ("quad", "Q5"),
        ("quad", "q1"),
        ("quad", "Q01"),
        ("quad", ""),
        ("quad", " Q1"),
        ("quad", 1),
        ("quad", None),
        ("quad", True),
        ("liquidity", "Expanding"),
        ("liquidity", "stable"),
        ("liquidity", ""),
        ("liquidity", 0),
        ("cycle", "MID"),
        ("cycle", "middle"),
        ("cycle", ""),
        ("cycle", None),
    ],
)
def test_invalid_categories_rejected(field, bad):
    with pytest.raises(FittedDistanceError) as excinfo:
        compare_coordinates(vec(**{field: bad}), vec())
    assert str(excinfo.value) == ERR_CATEGORY


def test_error_is_valueerror_subclass():
    assert issubclass(FittedDistanceError, ValueError)
    with pytest.raises(ValueError):
        compare_coordinates(None, vec())


def test_result_shape_is_plain_exact_data():
    result = compare_coordinates(vec(growth="0.100000000000000000"), vec())
    assert set(result) == {"distance_q18", "components", "arithmetic"}
    assert set(result["components"]) == {
        "growth_score",
        "inflation_score",
        "quad",
        "liquidity_overlay",
        "cycle_tag",
    }
    assert type(result["distance_q18"]) is str
    for component in result["components"].values():
        assert set(component) == {"numerator", "denominator"}
        assert type(component["numerator"]) is str
        assert type(component["denominator"]) is str
        assert int(component["denominator"]) > 0

    def walk(node):
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
        else:
            assert not isinstance(node, float)

    walk(result)  # no float ever leaks into the exact result


def test_inputs_are_preserved_and_calls_deterministic():
    left = ["0.100000000000000000", "-2.500000000000000000", "Q2", "expanding", "late"]
    right = ("7.000000000000000000", "0.000000000000000001", "Q3", "contracting", "early")
    left_snapshot = copy.deepcopy(left)
    right_snapshot = copy.deepcopy(right)
    first = compare_coordinates(left, right)
    second = compare_coordinates(left, right)
    assert left == left_snapshot
    assert right == right_snapshot
    assert first == second


def test_hostile_decimal_context_cannot_change_results_and_is_preserved():
    left = vec(growth="4.999999999999999998")  # exact distance needs final rounding
    baseline = compare_coordinates(left, vec())
    zero_baseline = compare_coordinates(vec(), vec())

    context = decimal.getcontext()
    saved = context.copy()
    try:
        context.prec = 1
        context.rounding = decimal.ROUND_DOWN
        context.traps[decimal.Inexact] = True
        context.traps[decimal.Rounded] = True
        context.traps[decimal.FloatOperation] = True
        context.traps[decimal.DivisionByZero] = True
        assert decimal.getcontext().prec == 1  # the hostile context really is active
        hostile = compare_coordinates(left, vec())
        hostile_zero = compare_coordinates(vec(), vec())
    finally:
        decimal.setcontext(saved)

    assert decimal.getcontext() == saved  # the call left the ambient context unchanged
    assert hostile == baseline
    assert hostile_zero == zero_baseline
