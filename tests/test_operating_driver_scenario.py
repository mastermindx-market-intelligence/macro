"""C19 WP15 pins (ruling R-W6-3): N2 beta is not a driver coefficient, N4 margin is not markup."""

import json

import pytest

from engine.operating_driver_scenario import (
    KIND,
    REFUSED_COEFFICIENT_BASES,
    DriverScenarioError,
    compute,
)


def _inputs(**overrides):
    kw = dict(
        volume={"value": 10.0, "unit": "barrel", "period": "2026Q2", "provenance": "FACT"},
        realized_price={"value": 10.0, "unit": "USD_per_barrel", "period": "2026Q2", "provenance": "FACT"},
        profitability={"value": 0.25, "basis": "markup", "provenance": "FACT"},
    )
    kw.update(overrides)
    return kw


def _driver(basis, value=0.5, applies_to="volume"):
    return {
        "name": "industry_demand",
        "change_pct": 10.0,
        "applies_to": applies_to,
        "coefficient": {"value": value, "basis": basis, "provenance": "STATISTICAL_ESTIMATE"},
    }


# --------------------------------------------------------------------------- #
# N4: margin is not markup
# --------------------------------------------------------------------------- #
def test_markup_is_converted_to_margin_before_it_touches_revenue():
    out = compute(**_inputs())
    assert out["base"]["revenue"] == 100.0
    assert out["base"]["margin"] == pytest.approx(0.2)
    assert out["base"]["profit"] == pytest.approx(20.0)  # not 25.0
    assert out["margin_from_markup"] is True


def test_margin_is_applied_directly():
    out = compute(**_inputs(profitability={"value": 0.25, "basis": "margin", "provenance": "FACT"}))
    assert out["base"]["profit"] == pytest.approx(25.0)
    assert out["margin_from_markup"] is False


@pytest.mark.parametrize("basis", [None, "", "gross", "Markup"])
def test_unlabelled_ratio_is_refused(basis):
    with pytest.raises(DriverScenarioError, match="N4"):
        compute(**_inputs(profitability={"value": 0.25, "basis": basis, "provenance": "FACT"}))


def test_a_margin_of_100_percent_or_more_is_refused_as_a_mislabelled_markup():
    with pytest.raises(DriverScenarioError, match="N4"):
        compute(**_inputs(profitability={"value": 1.5, "basis": "margin", "provenance": "FACT"}))
    out = compute(**_inputs(profitability={"value": 1.5, "basis": "markup", "provenance": "FACT"}))
    assert out["base"]["margin"] == pytest.approx(0.6)


# --------------------------------------------------------------------------- #
# N2: a market-price statistic is not a driver coefficient
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("basis", sorted(REFUSED_COEFFICIENT_BASES))
def test_market_price_statistic_is_refused_as_a_driver_coefficient(basis):
    with pytest.raises(DriverScenarioError, match="N2"):
        compute(**_inputs(), driver=_driver(basis))


@pytest.mark.parametrize("basis", [None, "", "beta", "unknown"])
def test_unlabelled_coefficient_basis_is_refused(basis):
    with pytest.raises(DriverScenarioError):
        compute(**_inputs(), driver=_driver(basis))


def test_operating_sensitivity_moves_only_its_target():
    out = compute(**_inputs(), driver=_driver("issuer_disclosed_sensitivity", applies_to="volume"))
    assert out["scenario"]["volume"] == pytest.approx(10.5)
    assert out["scenario"]["realized_price"] == 10.0
    assert out["scenario"]["revenue"] == pytest.approx(105.0)
    assert out["scenario"]["profit"] == pytest.approx(21.0)
    assert out["provenance"]["driver_coefficient"] == "STATISTICAL_ESTIMATE"
    priced = compute(**_inputs(), driver=_driver("scenario_assumption", applies_to="realized_price"))
    assert priced["scenario"]["volume"] == 10.0
    assert priced["scenario"]["realized_price"] == pytest.approx(10.5)


# --------------------------------------------------------------------------- #
# N3 units/period, provenance, and no valuation authority
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "price",
    [
        {"value": 10.0, "unit": "USD_per_tonne", "period": "2026Q2", "provenance": "FACT"},
        {"value": 10.0, "unit": "_per_barrel", "period": "2026Q2", "provenance": "FACT"},
        {"value": 10.0, "unit": "USD_per_barrel", "period": "2026Q1", "provenance": "FACT"},
    ],
)
def test_inconsistent_units_or_period_are_refused(price):
    with pytest.raises(DriverScenarioError, match="N3"):
        compute(**_inputs(realized_price=price))


def test_missing_provenance_is_refused():
    with pytest.raises(DriverScenarioError, match="provenance"):
        compute(**_inputs(volume={"value": 10.0, "unit": "barrel", "period": "2026Q2"}))


def test_output_carries_no_valuation_authority():
    out = compute(**_inputs(), driver=_driver("operating_data_estimate"))
    assert out["kind"] == KIND
    assert out["not_causal_attribution"] is True
    blob = json.dumps(out, sort_keys=True)
    assert "schema" not in out
    assert "valuation_scenario" not in blob
    for word in ("price_target", "target_price", "weight", "selected_share", "probability", "calibrated"):
        assert word not in blob
