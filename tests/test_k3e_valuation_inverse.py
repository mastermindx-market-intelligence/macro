from __future__ import annotations

import math

import pytest

from engine.valuation_scenario_qualified import (
    QUALIFIED_ASSUMPTION_BOUNDS,
    QUALIFIED_INPUT_SCHEMA,
    QUALIFIED_OWNER_PRESETS,
    compatible_multiple_interval,
    evaluate_qualified_scenario,
    required_earnings_multiple,
)


def _receipt(**overrides):
    receipt = {
        "schema": QUALIFIED_INPUT_SCHEMA,
        "receipt_id": "input-aapl-fy2025-20260130",
        "ticker": "AAPL",
        "security_ref": "security:aapl-common",
        "price_security_ref": "security:aapl-common",
        "financial_receipt_id": "financial:aapl-fy2025-v1",
        "price_receipt_id": "price:aapl-20260130-close-v1",
        "net_income": 100.0,
        "revenue": 1000.0,
        "shares": 10.0,
        "share_identity": "outstanding",
        "financial_currency": "USD",
        "price": 300.0,
        "price_currency": "USD",
        "fiscal_period": "FY2025",
        "accounting_basis": "US_GAAP",
        "financial_available_at": "2026-01-29T22:00:00Z",
        "price_available_at": "2026-01-30T21:00:00Z",
        "decision_cutoff": "2026-01-30T21:00:00Z",
        "price_basis": "qualified_per_share_close",
        "research_use_permitted": True,
        "derived_use_permitted": True,
        "price_tolerance": 0.01,
    }
    receipt.update(overrides)
    return receipt


def test_qualified_forward_preserves_owner_operation_order_and_display_policy():
    receipt = _receipt()
    out = evaluate_qualified_scenario(
        receipt,
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
        earnings_multiple=18.0,
    )

    owner_raw = (
        receipt["net_income"]
        * (1 + 3.0 / 100.0)
        * (1 + (0.0 / 100.0) / (receipt["net_income"] / receipt["revenue"]))
        * 18.0
        / receipt["shares"]
    )
    assert out["valid"] is True
    assert out["refusal_reasons"] == []
    assert out["unrounded_per_share"] == owner_raw
    assert out["display_per_share"] == round(owner_raw, 2)
    assert out["model_family"] == "f07_earnings_multiple"
    assert out["authority"] == "research_display_only"
    assert out["input_receipt_id"] == receipt["receipt_id"]
    assert out["security_ref"] == receipt["security_ref"]
    assert out["currency"] == "USD"
    assert out["share_identity"] == "outstanding"
    assert out["accounting_basis"] == "US_GAAP"
    assert out["fiscal_period"] == "FY2025"


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"ticker": "MSFT"}, "unsupported_ticker"),
        ({"security_ref": ""}, "identity_unqualified"),
        ({"accounting_basis": ""}, "accounting_basis_unqualified"),
        ({"accounting_basis": "IFRS"}, "unsupported_accounting_basis"),
        ({"fiscal_period": ""}, "fiscal_period_unqualified"),
        ({"fiscal_period": "Q1-2025"}, "unsupported_fiscal_period"),
        ({"price_security_ref": "security:msft-common"}, "price_identity_mismatch"),
        ({"financial_currency": "EUR"}, "currency_mismatch"),
        ({"share_identity": "diluted"}, "unsupported_share_identity"),
        ({"research_use_permitted": False}, "rights_not_permitted"),
        ({"derived_use_permitted": False}, "rights_not_permitted"),
        ({"financial_available_at": "2026-01-31T00:00:00Z"}, "cutoff_violation"),
        ({"price_available_at": "2026-01-31T00:00:00Z"}, "cutoff_violation"),
    ],
)
def test_qualified_forward_refuses_unqualified_receipts(overrides, reason):
    out = evaluate_qualified_scenario(
        _receipt(**overrides),
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
        earnings_multiple=18.0,
    )
    assert out["valid"] is False
    assert reason in out["refusal_reasons"]
    assert out["unrounded_per_share"] is None
    assert out["display_per_share"] is None


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("net_income", True, "nonfinite_or_boolean_input"),
        ("revenue", math.inf, "nonfinite_or_boolean_input"),
        ("shares", math.nan, "nonfinite_or_boolean_input"),
        ("net_income", 0.0, "nonpositive_net_income"),
        ("revenue", 0.0, "nonpositive_revenue"),
        ("shares", 0.0, "nonpositive_shares"),
    ],
)
def test_qualified_forward_refuses_nonfinite_boolean_and_nonpositive_inputs(field, value, reason):
    out = evaluate_qualified_scenario(
        _receipt(**{field: value}),
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
        earnings_multiple=18.0,
    )
    assert out["valid"] is False
    assert reason in out["refusal_reasons"]


@pytest.mark.parametrize(
    ("g", "d", "k", "reason"),
    [
        (-10.0001, 0.0, 18.0, "growth_out_of_bounds"),
        (20.0001, 0.0, 18.0, "growth_out_of_bounds"),
        (3.0, -3.0001, 18.0, "margin_out_of_bounds"),
        (3.0, 3.0001, 18.0, "margin_out_of_bounds"),
        (3.0, 0.0, 7.9999, "multiple_out_of_bounds"),
        (3.0, 0.0, 35.0001, "multiple_out_of_bounds"),
    ],
)
def test_qualified_forward_enforces_existing_owner_bounds(g, d, k, reason):
    out = evaluate_qualified_scenario(
        _receipt(),
        sales_growth_pct=g,
        margin_delta_pp=d,
        earnings_multiple=k,
    )
    assert out["valid"] is False
    assert reason in out["refusal_reasons"]


def test_qualified_forward_preserves_margin_floor_and_adjusted_margin_guards():
    too_thin = evaluate_qualified_scenario(
        _receipt(net_income=5.0, revenue=1000.0),
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
        earnings_multiple=18.0,
    )
    assert too_thin["valid"] is False
    assert "margin_base_too_thin" in too_thin["refusal_reasons"]

    adjusted_nonpositive = evaluate_qualified_scenario(
        _receipt(net_income=20.0, revenue=1000.0),
        sales_growth_pct=3.0,
        margin_delta_pp=-2.0,
        earnings_multiple=18.0,
    )
    assert adjusted_nonpositive["valid"] is False
    assert "adjusted_margin_nonpositive" in adjusted_nonpositive["refusal_reasons"]


def test_conditional_inverse_recovers_required_multiple_and_forward_substitutes():
    receipt = _receipt(price=185.4, price_tolerance=1e-10)
    out = required_earnings_multiple(
        receipt,
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
    )

    assert out["valid"] is True
    assert out["conditional_on"] == {
        "sales_growth_pct": 3.0,
        "margin_delta_pp": 0.0,
    }
    assert out["required_earnings_multiple"] == pytest.approx(18.0)
    assert out["forward_unrounded_per_share"] == pytest.approx(receipt["price"])
    assert abs(out["forward_residual"]) <= receipt["price_tolerance"]
    assert out["within_tolerance"] is True
    assert out["jacobian"]["rank"] == 1
    assert out["jacobian"]["nullspace_dimension"] == 2
    assert len(out["null_directions"]) == 2
    assert out["compatibility_mass"] is None
    assert out["compatibility_mass_status"] == "independent_joint_reference_not_qualified"


def test_conditional_inverse_refuses_price_domain_bounds_and_zero_scale():
    nonpositive_price = required_earnings_multiple(
        _receipt(price=0.0),
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
    )
    assert nonpositive_price["valid"] is False
    assert "price_nonpositive" in nonpositive_price["refusal_reasons"]

    out_of_bounds = required_earnings_multiple(
        _receipt(price=400.0),
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
    )
    assert out_of_bounds["valid"] is False
    assert "inverse_out_of_bounds" in out_of_bounds["refusal_reasons"]
    assert out_of_bounds["required_earnings_multiple"] is None

    zero_scale = required_earnings_multiple(
        _receipt(net_income=1e-308, revenue=1e-306, shares=1e308, price=1.0),
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
    )
    assert zero_scale["valid"] is False
    assert {"margin_base_too_thin", "zero_or_nonfinite_scale"} & set(zero_scale["refusal_reasons"])


def test_price_band_returns_jointly_feasible_multiple_interval_without_probability():
    receipt = _receipt(price=185.4)
    out = compatible_multiple_interval(
        receipt,
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
        price_lower=184.0,
        price_upper=186.0,
    )

    assert out["valid"] is True
    lo, hi = out["earnings_multiple_interval"]
    assert QUALIFIED_ASSUMPTION_BOUNDS["earnings_multiple"][0] <= lo <= hi
    assert hi <= QUALIFIED_ASSUMPTION_BOUNDS["earnings_multiple"][1]
    assert lo == pytest.approx(184.0 / 10.3)
    assert hi == pytest.approx(186.0 / 10.3)
    assert out["compatibility_mass"] is None
    assert out["compatibility_mass_status"] == "independent_joint_reference_not_qualified"


def test_price_band_refuses_empty_intersection_instead_of_clamping():
    out = compatible_multiple_interval(
        _receipt(),
        sales_growth_pct=3.0,
        margin_delta_pp=0.0,
        price_lower=400.0,
        price_upper=401.0,
    )
    assert out["valid"] is False
    assert "empty_feasible_set" in out["refusal_reasons"]
    assert out["earnings_multiple_interval"] is None


def test_qualified_contract_stays_bound_to_existing_f07_owner_controls_and_presets():
    from engine.valuation_assumptions import CONTROLS
    from engine.valuation_scenario import SCENARIOS

    control_bounds = {
        item["key"]: (float(item["min"]), float(item["max"]))
        for item in CONTROLS
    }
    assert QUALIFIED_ASSUMPTION_BOUNDS == control_bounds
    assert QUALIFIED_OWNER_PRESETS is SCENARIOS
