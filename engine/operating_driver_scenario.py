"""Operating-driver scenario arithmetic (Commission 19 WP15, ruling R-W6-3).

A scenario is ``revenue = volume x realized_price`` and
``profit = revenue x margin``. Every input carries a provenance tag
(FACT / STATISTICAL_ESTIMATE / SCENARIO_ASSUMPTION), a unit and a period,
and the arithmetic refuses rather than guesses:

N2  a driver coefficient may not be a market-price statistic (a stock beta,
    a price correlation, a return regression). Co-movement of share prices
    is not an operating sensitivity, so those bases raise.
N3  volume and realized price must share a period, and the price unit must
    be ``<currency>_per_<volume unit>``.
N4  margin is not markup. A ratio must say which it is; a markup m becomes
    the margin m / (1 + m) before it touches revenue, and a "margin" of 100%
    or more (a markup mislabelled as a margin) raises.

The output is display-tier scenario arithmetic only. It carries no
valuation authority: no price target, share, weight or probability. It is
not a valuation_scenario contract and does not extend one.
"""

from __future__ import annotations

import math

KIND = "OPERATING_DRIVER_SCENARIO"
PROVENANCES = frozenset({"FACT", "STATISTICAL_ESTIMATE", "SCENARIO_ASSUMPTION"})
ALLOWED_COEFFICIENT_BASES = frozenset(
    {"issuer_disclosed_sensitivity", "operating_data_estimate", "scenario_assumption"}
)
REFUSED_COEFFICIENT_BASES = frozenset({"market_beta", "price_correlation", "return_regression"})
RATIO_BASES = frozenset({"margin", "markup"})
DRIVER_TARGETS = frozenset({"volume", "realized_price"})


class DriverScenarioError(ValueError):
    """An input the scenario arithmetic refuses rather than guesses about."""


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise DriverScenarioError(f"{name}: value must be a finite number, got {value!r}")
    return float(value)


def _provenance(name, spec):
    tag = spec.get("provenance")
    if tag not in PROVENANCES:
        raise DriverScenarioError(f"{name}: provenance must be one of {sorted(PROVENANCES)}, got {tag!r}")
    return tag


def _margin(profitability):
    basis = profitability.get("basis")
    if basis not in RATIO_BASES:
        raise DriverScenarioError(
            f"profitability: basis must be 'margin' or 'markup' (N4: margin is not markup), got {basis!r}"
        )
    ratio = _number("profitability", profitability.get("value"))
    if basis == "markup":
        if ratio <= -1.0:
            raise DriverScenarioError(f"profitability: a markup must exceed -1, got {ratio!r}")
        return ratio / (1.0 + ratio), True
    if ratio >= 1.0:
        raise DriverScenarioError(
            f"profitability: a margin of {ratio!r} is 100% or more of revenue (N4: is this a markup?)"
        )
    return ratio, False


def _coefficient(driver):
    coefficient = driver.get("coefficient") or {}
    basis = coefficient.get("basis")
    if basis in REFUSED_COEFFICIENT_BASES:
        raise DriverScenarioError(
            f"driver coefficient basis {basis!r} is a market-price statistic, "
            "not an operating sensitivity (N2)"
        )
    if basis not in ALLOWED_COEFFICIENT_BASES:
        raise DriverScenarioError(
            f"driver coefficient basis must be one of {sorted(ALLOWED_COEFFICIENT_BASES)}, got {basis!r}"
        )
    return _number("driver coefficient", coefficient.get("value")), _provenance("driver coefficient", coefficient)


def _leg(volume, price, margin):
    revenue = volume * price
    return {
        "volume": volume,
        "realized_price": price,
        "revenue": revenue,
        "margin": margin,
        "profit": revenue * margin,
    }


def compute(*, volume, realized_price, profitability, driver=None):
    """Return the base leg and, when ``driver`` is given, the shocked leg.

    ``volume``          {"value", "unit", "period", "provenance"}
    ``realized_price``  {"value", "unit" = "<currency>_per_<volume unit>", "period", "provenance"}
    ``profitability``   {"value", "basis" in RATIO_BASES, "provenance"}
    ``driver``          {"name", "change_pct", "applies_to" in DRIVER_TARGETS,
                         "coefficient": {"value", "basis", "provenance"}}
    A driver moves its target by ``coefficient * change_pct`` percent.
    """
    v = _number("volume", volume.get("value"))
    p = _number("realized_price", realized_price.get("value"))
    provenance = {
        "volume": _provenance("volume", volume),
        "realized_price": _provenance("realized_price", realized_price),
        "profitability": _provenance("profitability", profitability),
    }
    volume_unit = volume.get("unit")
    price_unit = realized_price.get("unit")
    if not volume_unit or not isinstance(price_unit, str) or not price_unit.endswith(f"_per_{volume_unit}"):
        raise DriverScenarioError(
            f"units: realized_price unit {price_unit!r} must be '<currency>_per_{volume_unit}' (N3)"
        )
    currency = price_unit[: -len(f"_per_{volume_unit}")]
    if not currency:
        raise DriverScenarioError(f"units: realized_price unit {price_unit!r} names no currency (N3)")
    period = volume.get("period")
    if not period or realized_price.get("period") != period:
        raise DriverScenarioError(
            f"period: volume period {period!r} and realized_price period "
            f"{realized_price.get('period')!r} must match (N3)"
        )
    margin, from_markup = _margin(profitability)

    out = {
        "kind": KIND,
        "period": period,
        "volume_unit": volume_unit,
        "currency": currency,
        "margin_from_markup": from_markup,
        "not_causal_attribution": True,
        "provenance": provenance,
        "base": _leg(v, p, margin),
        "scenario": None,
    }
    if driver is not None:
        target = driver.get("applies_to")
        if target not in DRIVER_TARGETS:
            raise DriverScenarioError(f"driver: applies_to must be one of {sorted(DRIVER_TARGETS)}, got {target!r}")
        k, k_provenance = _coefficient(driver)
        move = k * _number("driver change_pct", driver.get("change_pct")) / 100.0
        provenance["driver_coefficient"] = k_provenance
        shocked_v = v * (1.0 + move) if target == "volume" else v
        shocked_p = p * (1.0 + move) if target == "realized_price" else p
        out["scenario"] = dict(_leg(shocked_v, shocked_p, margin), driver=driver.get("name"), applies_to=target)
    return out
