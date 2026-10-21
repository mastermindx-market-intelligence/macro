"""Exact fitted-distance arithmetic for Market Memory v2 coordinate vectors."""

import re
from fractions import Fraction

ARITHMETIC_ID = "q18_coordinates_exact_fraction_equal_weight_L1_final_q18_half_even.v2"

Q18_SCALE = 10 ** 18
MAX_INTEGER_DIGITS = 400

_MAX_NUMERIC_LENGTH = 1 + MAX_INTEGER_DIGITS + 1 + 18  # sign + integer digits + dot + 18 fraction digits

_CANONICAL_Q18_RE = re.compile(r"-?(?:0|[1-9][0-9]{0,399})\.[0-9]{18}")

_QUAD_VALUES = frozenset({"Q1", "Q2", "Q3", "Q4"})
_LIQUIDITY_VALUES = frozenset({"expanding", "neutral", "contracting"})
_CYCLE_VALUES = frozenset({"early", "mid", "late"})

ERR_VECTOR = (
    "coordinates must be an exact list or tuple of exactly 5 components: "
    "growth, inflation, quad, liquidity overlay, cycle tag"
)
ERR_NUMERIC_TYPE = "growth and inflation components must be exact str instances"
ERR_NUMERIC_BOUND = (
    "growth and inflation components exceed the maximum coordinate length: "
    "at most 400 integer digits, one dot and exactly 18 fraction digits"
)
ERR_NUMERIC_FORM = (
    "growth and inflation components must be canonical signed fixed18 decimal "
    "strings: optional minus, no leading zeros, no exponent, and exactly 18 "
    "fraction digits"
)
ERR_NEGATIVE_ZERO = "growth and inflation components must not be negative zero"
ERR_CATEGORY = (
    "quad, liquidity overlay and cycle tag components must use exactly one of "
    "their allowed category values"
)


class FittedDistanceError(ValueError):
    """Raised for any malformed coordinate vector."""


def _parse_numeric_units(value):
    """Return the exact count of 1e-18 units in one canonical q18 string.

    The cheap length/integer-digit bound runs before the regex and before any
    int/Fraction conversion, so oversize input is refused without expensive
    parsing.
    """
    if type(value) is not str:
        raise FittedDistanceError(ERR_NUMERIC_TYPE)
    body = value[1:] if value[:1] == "-" else value
    dot = body.find(".")
    integer_digits = dot if dot >= 0 else len(body)
    if integer_digits > MAX_INTEGER_DIGITS or len(value) > _MAX_NUMERIC_LENGTH:
        raise FittedDistanceError(ERR_NUMERIC_BOUND)
    if _CANONICAL_Q18_RE.fullmatch(value) is None:
        raise FittedDistanceError(ERR_NUMERIC_FORM)
    sign = -1 if value[0] == "-" else 1
    digits = value[1:] if sign < 0 else value
    dot = digits.index(".")
    units = int(digits[:dot]) * Q18_SCALE + int(digits[dot + 1:])
    units *= sign
    if sign < 0 and units == 0:
        raise FittedDistanceError(ERR_NEGATIVE_ZERO)
    return units


def _validated_components(coordinates):
    if type(coordinates) is not list and type(coordinates) is not tuple:
        raise FittedDistanceError(ERR_VECTOR)
    if len(coordinates) != 5:
        raise FittedDistanceError(ERR_VECTOR)
    growth = _parse_numeric_units(coordinates[0])
    inflation = _parse_numeric_units(coordinates[1])
    if type(coordinates[2]) is not str or coordinates[2] not in _QUAD_VALUES:
        raise FittedDistanceError(ERR_CATEGORY)
    if type(coordinates[3]) is not str or coordinates[3] not in _LIQUIDITY_VALUES:
        raise FittedDistanceError(ERR_CATEGORY)
    if type(coordinates[4]) is not str or coordinates[4] not in _CYCLE_VALUES:
        raise FittedDistanceError(ERR_CATEGORY)
    return (growth, inflation, coordinates[2], coordinates[3], coordinates[4])


def _q18_half_even(value):
    """Quantize one nonnegative Fraction exactly once to canonical fixed18 text."""
    units, remainder = divmod(value.numerator * Q18_SCALE, value.denominator)
    doubled = remainder * 2
    if doubled > value.denominator or (doubled == value.denominator and units % 2 == 1):
        units += 1
    return "%d.%018d" % divmod(units, Q18_SCALE)


def _component_dict(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def compare_coordinates(left, right):
    """Compare two Market Memory v2 coordinate vectors with exact arithmetic.

    Raw coordinates are unauthenticated values: they do not authenticate their
    sources and carry no permission, so callers must wrap this function in the
    existing native source consumer, which owns typed capabilities, source
    identity and eligibility.

    Each vector is exactly 5 components: a canonical signed fixed18 decimal
    string for normalized growth, one for normalized inflation, then the quad
    (Q1/Q2/Q3/Q4), liquidity overlay (expanding/neutral/contracting) and cycle
    tag (early/mid/late) categories.  Returns a dict holding the canonical
    nonnegative q18 distance (equal-weight L1 across the five components,
    rounded half-even exactly once at the end) plus the exact rational
    per-component distances as reduced numerator/denominator decimal strings.
    Distances may legitimately exceed 1; inputs are never mutated.
    """
    left_growth, left_inflation, left_quad, left_liquidity, left_cycle = _validated_components(left)
    right_growth, right_inflation, right_quad, right_liquidity, right_cycle = _validated_components(right)
    components = {
        "growth_score": Fraction(abs(left_growth - right_growth), Q18_SCALE),
        "inflation_score": Fraction(abs(left_inflation - right_inflation), Q18_SCALE),
        "quad": Fraction(0 if left_quad == right_quad else 1),
        "liquidity_overlay": Fraction(0 if left_liquidity == right_liquidity else 1),
        "cycle_tag": Fraction(0 if left_cycle == right_cycle else 1),
    }
    distance = sum(components.values(), Fraction(0)) / 5
    return {
        "distance_q18": _q18_half_even(distance),
        "components": {name: _component_dict(value) for name, value in components.items()},
        "arithmetic": ARITHMETIC_ID,
    }
