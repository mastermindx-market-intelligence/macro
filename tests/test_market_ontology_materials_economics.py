"""TDD contract tests for the pure Basic Materials economics core."""
from __future__ import annotations

try:
    from engine.market_ontology.materials_economics import compare_measures
except ImportError:
    compare_measures = None

try:
    from engine.market_ontology.materials_economics import compose_materials_economics
except ImportError:
    compose_materials_economics = None


def _basis(**overrides):
    data = {
        "domain": "signed_financial",
        "unit": "USD/product_metric_tonne",
        "currency": "USD",
        "scale_text": "1",
        "quantity_basis": "sold_product_metric_tonne",
        "period_start": "2025-04-01",
        "period_end": "2025-06-30",
        "period_kind": "quarter",
        "consolidation_basis": "synthetic_segment",
        "valuation_basis": "reported_cash",
        "inclusions": ["synthetic_product"],
        "exclusions": [],
        "source_precision": "whole_currency_unit",
    }
    data.update(overrides)
    return data


def _measure(label, value, evidence_id, **basis_overrides):
    return {
        **_basis(**basis_overrides),
        "metric_label": label,
        "value_text": value,
        "evidence_id": evidence_id,
    }


def test_same_period_spread_preserves_negative_exact_decimal():
    assert compare_measures is not None, "compare_measures must be implemented"
    price = _measure("unit_price", "7", "ev:0000000000000001")
    cost = _measure("unit_cost", "10", "ev:0000000000000002")

    result = compare_measures(price, cost, relation="same_period_spread")

    assert result["state"] == "available"
    assert result["value_text"] == "-3"
    assert result["input_refs"] == [
        "ev:0000000000000001",
        "ev:0000000000000002",
    ]



def _unit_case_assertions():
    common = {
        "subject_ref": "co:us:SYNTH",
        "analysis_kind": "unit_economics",
        "domain": "signed_financial",
        "unit": "USD/product_metric_tonne",
        "currency": "USD",
        "scale_text": "1",
        "quantity_basis": "sold_product_metric_tonne",
        "period_kind": "quarter",
        "consolidation_basis": "synthetic_segment",
        "valuation_basis": "reported_cash",
        "inclusions": ["synthetic_product"],
        "exclusions": [],
        "source_precision": "whole_currency_unit",
    }
    rows = [
        ("price_prior", "70", "2025-01-01", "2025-03-31", "ev:p0"),
        ("cost_prior", "64", "2025-01-01", "2025-03-31", "ev:c0"),
        ("price_current", "78", "2025-04-01", "2025-06-30", "ev:p1"),
        ("cost_current", "81", "2025-04-01", "2025-06-30", "ev:c1"),
    ]
    return tuple(
        {
            **common,
            "assertion_id": f"a:{label}",
            "metric_label": label,
            "value_text": value,
            "period_start": start,
            "period_end": end,
            "evidence_id": evidence_id,
        }
        for label, value, start, end, evidence_id in rows
    )


def test_unit_economics_explains_price_up_margin_down_without_company_wide_claim():
    assert compose_materials_economics is not None, "composer must be implemented"

    doc = compose_materials_economics(
        assertions=_unit_case_assertions(),
        identity_rows=(),
        source_bindings=(),
        route_receipts=(),
        source_generation="synthetic-generation",
        rights_version="synthetic-rights",
        cutoff={"effective_at": "2025-06-30", "knowledge_at": "2025-07-01"},
    )

    values = {row["key"]: row["value_text"] for row in doc["calculations"]}
    assert values == {
        "current_unit_margin": "-3",
        "prior_unit_margin": "6",
        "price_change": "8",
        "cost_change": "17",
        "margin_change": "-9",
    }
    assert doc["explanation"]["code"] == "price_up_margin_down"
    assert "Higher realization" in doc["explanation"]["lead"]
    assert "whole-company profitability" in doc["explanation"]["does_not_prove"]
    assert doc["company_link"] is None



def _cash_case_assertions():
    common = {
        "subject_ref": "co:us:SYNTH",
        "analysis_kind": "cash_reconciliation",
        "domain": "signed_financial",
        "unit": "USD_million",
        "currency": "USD",
        "scale_text": "1000000",
        "quantity_basis": "company_cash",
        "period_start": "2025-04-01",
        "period_end": "2025-06-30",
        "period_kind": "quarter",
        "consolidation_basis": "consolidated_company",
        "valuation_basis": "reported_cash",
        "inclusions": ["synthetic_company"],
        "exclusions": [],
        "source_precision": "million_currency_unit",
    }
    return (
        {**common, "assertion_id": "a:ocf", "metric_label": "operating_cash",
         "value_text": "1000", "evidence_id": "ev:ocf"},
        {**common, "assertion_id": "a:capex", "metric_label": "capital_spending",
         "value_text": "400", "evidence_id": "ev:capex"},
        {**common, "assertion_id": "a:adj", "metric_label": "issuer_adjustment",
         "value_text": "100", "evidence_id": "ev:adj"},
    )


def test_cash_reconciliation_keeps_actual_spending_visible_beside_adjusted_measure():
    doc = compose_materials_economics(
        assertions=_cash_case_assertions(),
        identity_rows=(),
        source_bindings=(),
        route_receipts=(),
        source_generation="synthetic-generation",
        rights_version="synthetic-rights",
        cutoff={"effective_at": "2025-06-30", "knowledge_at": "2025-07-01"},
    )

    values = {row["key"]: row["value_text"] for row in doc["calculations"]}
    assert values["cash_after_spending"] == "600"
    assert values["issuer_adjusted_distribution_measure"] == "700"
    assert doc["explanation"]["code"] == "cash_vs_adjusted_distribution"
    assert "spending still occurred" in doc["explanation"]["lead"]
    assert "sustainable distribution capacity" in doc["explanation"]["does_not_prove"]
