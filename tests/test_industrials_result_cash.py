"""Pure signed exact-decimal result-to-cash derivation tests (T04).

These tests cover ``engine.fundamental_forensics.industrials_result_cash``:
the pure, versioned, signed derivation module that exposes
``qualify_operands`` and ``derive_result_cash`` and the production
comparison-receipt constructor ``build_comparison_receipt``.  Every fixture
is synthetic; all numbers are invented under fictional issuers with
``example.invalid`` sources and ``synthetic: true``.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

import pytest

from engine.fundamental_forensics.industrials_result_cash import (
    ALLOWED_FORMULAS,
    FORMULA_VERSION,
    build_comparison_receipt,
    derive_result_cash,
    qualify_operands,
)

from tests.industrials_result_cash_helpers import cell, comparison, typed_absence


# ---------------------------------------------------------------------------
# C0 / R1 / R2 — module constants, versioned exports, receipt compatibility
# ---------------------------------------------------------------------------


def test_formula_version_is_v1() -> None:
    assert FORMULA_VERSION == "v1"
    assert "growth_pct" in ALLOWED_FORMULAS
    assert "margin_pct" in ALLOWED_FORMULAS
    assert "paired_remeasurement" in ALLOWED_FORMULAS
    assert "cash_after_capital_payments" in ALLOWED_FORMULAS
    assert "cash_rollforward" in ALLOWED_FORMULAS
    assert "segment_change_bridge" in ALLOWED_FORMULAS
    assert "final_vs_preview" in ALLOWED_FORMULAS
    assert len(ALLOWED_FORMULAS) == 7


def test_receipt_helper_round_trip_matches_comparison_helper() -> None:
    """T01 ``comparison(...)`` and T04 ``build_comparison_receipt(...)``
    must produce byte-compatible closed shapes for the same cells."""
    cells = [
        cell("1", owner_ref="synthetic:cell:a"),
        cell("2", owner_ref="synthetic:cell:b"),
    ]
    t01_receipt = comparison("same_period", cells)
    t04_receipt = build_comparison_receipt("same_period", cells, checked=t01_receipt["checked"])
    # Same closed shape — every key the T01 helper emits, T04 reproduces.
    assert set(t04_receipt) >= {"receipt_id", "purpose", "operand_refs", "checked", "unknowns", "transformations"}
    assert t04_receipt["purpose"] == t01_receipt["purpose"]
    assert t04_receipt["operand_refs"] == t01_receipt["operand_refs"]
    assert t04_receipt["checked"] == t01_receipt["checked"]
    assert t04_receipt["unknowns"] == []
    assert t04_receipt["transformations"] == []


def test_build_receipt_records_transformations_with_decimal_text_factor() -> None:
    cells = [cell("100", owner_ref="synthetic:cell:usd"), cell("92", owner_ref="synthetic:cell:eur")]
    receipt = build_comparison_receipt(
        "year_over_year",
        cells,
        checked={"currency": True},
        transformations=({"kind": "currency_convert", "factor": "0.92", "lineage": "ECB-2026Q2"},),
    )
    assert receipt["transformations"][0]["factor"] == "0.92"
    assert receipt["transformations"][0]["kind"] == "currency_convert"
    assert receipt["transformations"][0]["lineage"] == "ECB-2026Q2"


def test_receipt_operand_refs_match_input_cell_order_and_content() -> None:
    """Spec §1: receipt ``operand_refs`` is the ordered list of every
    operand's owner_ref, in cell order.  Verify exact content + order.
    """
    cells = [
        cell("100", metric="op", owner_ref="synthetic:cell:op", digest="a" * 64, revision="rev-A"),
        cell("100", metric="cap", owner_ref="synthetic:cell:cap", digest="b" * 64, revision="rev-B"),
        cell("100", metric="core", owner_ref="synthetic:cell:core", digest="c" * 64, revision="rev-C"),
    ]
    receipt = build_comparison_receipt("same_period", cells)
    assert receipt["operand_refs"] == [
        "synthetic:cell:op",
        "synthetic:cell:cap",
        "synthetic:cell:core",
    ]


def test_result_operand_refs_match_input_cell_order_and_content() -> None:
    """Spec §1: result ``operand_refs`` carries owner_ref/revision/digest
    of every operand in cell order.  Verify exact content + order on a
    derivation result, not just the length.
    """
    cells = [
        cell("-12", metric="operating_cash", owner_ref="synthetic:cell:op", digest="a" * 64, revision="rev-A"),
        cell("3", metric="cash_capital_payments", owner_ref="synthetic:cell:cap", digest="b" * 64, revision="rev-B"),
    ]
    receipt = build_comparison_receipt("same_period", cells)
    r = derive_result_cash(
        "cash_after_capital_payments",
        cells,
        comparison_receipt=receipt,
    )
    assert r["operand_refs"] == [
        {"owner_ref": "synthetic:cell:op", "revision": "rev-A", "digest": "a" * 64},
        {"owner_ref": "synthetic:cell:cap", "revision": "rev-B", "digest": "b" * 64},
    ]
    # Reversed input order MUST yield a different result operand_refs order.
    reversed_cells = list(reversed(cells))
    r_rev = derive_result_cash(
        "cash_after_capital_payments",
        reversed_cells,
        comparison_receipt=build_comparison_receipt("same_period", reversed_cells),
    )
    assert r_rev["operand_refs"] == [
        {"owner_ref": "synthetic:cell:cap", "revision": "rev-B", "digest": "b" * 64},
        {"owner_ref": "synthetic:cell:op", "revision": "rev-A", "digest": "a" * 64},
    ]


def test_build_receipt_unknowns_round_trip() -> None:
    """``unknowns`` is a field on the receipt — it must round-trip exactly."""
    cells = [cell("100", owner_ref="synthetic:cell:a"), cell("100", owner_ref="synthetic:cell:b")]
    receipt = build_comparison_receipt(
        "same_period",
        cells,
        unknowns=("basis", "currency"),
    )
    assert receipt["unknowns"] == ["basis", "currency"]


def test_receipt_id_differs_when_only_unknowns_differ() -> None:
    """Identity binds ``unknowns`` — two receipts disclosing different
    unknowns share no receipt_id (the digest covers them).
    """
    cells = [cell("100", owner_ref="synthetic:cell:a"), cell("100", owner_ref="synthetic:cell:b")]
    base = build_comparison_receipt("same_period", cells)
    with_unknowns = build_comparison_receipt(
        "same_period",
        cells,
        unknowns=("basis",),
    )
    assert base["receipt_id"] != with_unknowns["receipt_id"]


def test_receipt_id_differs_when_only_transformations_differ() -> None:
    """Identity binds ``transformations`` — a different declared conversion
    declares a different comparison was run; the digest must reflect it.
    """
    cells = [cell("100", owner_ref="synthetic:cell:a"), cell("100", owner_ref="synthetic:cell:b")]
    base = build_comparison_receipt("same_period", cells)
    with_transforms = build_comparison_receipt(
        "same_period",
        cells,
        checked={"currency": True},
        transformations=({"kind": "currency_convert", "factor": "0.92", "lineage": "ECB-2026Q2"},),
    )
    assert base["receipt_id"] != with_transforms["receipt_id"]


def test_receipt_id_differs_when_only_checked_differs() -> None:
    """Identity binds ``checked`` — a receipt declaring one gate checked and
    another declaring it NOT checked declare different comparisons.
    """
    cells = [cell("100", owner_ref="synthetic:cell:a"), cell("100", owner_ref="synthetic:cell:b")]
    checked_one = build_comparison_receipt("same_period", cells, checked={"currency": True})
    checked_other = build_comparison_receipt("same_period", cells, checked={"currency": False})
    assert checked_one["receipt_id"] != checked_other["receipt_id"]


def test_receipt_id_differs_when_only_purpose_differs() -> None:
    """Identity binds ``purpose`` — a same_period comparison is a different
    receipt than a year_over_year comparison even over the same cells.
    """
    cells = [cell("100", owner_ref="synthetic:cell:a"), cell("100", owner_ref="synthetic:cell:b")]
    same_period = build_comparison_receipt("same_period", cells)
    year_over_year = build_comparison_receipt("year_over_year", cells)
    assert same_period["receipt_id"] != year_over_year["receipt_id"]


def test_receipt_id_stable_for_identical_inputs() -> None:
    """Identity is stable — identical inputs produce identical receipt_id."""
    cells = [cell("100", owner_ref="synthetic:cell:a"), cell("100", owner_ref="synthetic:cell:b")]
    first = build_comparison_receipt(
        "same_period",
        cells,
        checked={"basis": True, "currency": True},
    )
    second = build_comparison_receipt(
        "same_period",
        cells,
        checked={"currency": True, "basis": True},  # different insertion order
    )
    assert first["receipt_id"] == second["receipt_id"]


def test_build_receipt_rejects_unknown_purpose() -> None:
    with pytest.raises(ValueError):
        build_comparison_receipt("not_a_purpose", [cell("1")])


# ---------------------------------------------------------------------------
# T04 plan verbatim — test_ind_sf01
# ---------------------------------------------------------------------------


def test_ind_sf01() -> None:
    """Plan T04 verbatim — operating cash -12, capital payments 3 -> -15."""
    cells = [
        cell("-12", metric="operating_cash"),
        cell("3", metric="cash_capital_payments"),
    ]
    r = derive_result_cash(
        "cash_after_capital_payments",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "ready"
    assert r["value"] == "-15"
    assert len(r["operand_refs"]) == 2


# ---------------------------------------------------------------------------
# cash_after_capital_payments — positive and refusal cases
# ---------------------------------------------------------------------------


def test_cash_after_capital_payments_ready_with_researcher_proxy_label() -> None:
    cells = [
        cell("100", metric="operating_cash"),
        cell("40", metric="cash_capital_payments"),
    ]
    r = derive_result_cash(
        "cash_after_capital_payments",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "ready"
    assert r["value"] == "60"
    assert r["label"] == "researcher_proxy"
    assert r["formula"] == "cash_after_capital_payments"
    assert r["formula_version"] == FORMULA_VERSION


def test_cash_after_capital_payments_company_adjusted_when_definition_supplied() -> None:
    """When the issuer's exact FCF definition is supplied AND reproduced in the
    receipt, the label switches to ``company_adjusted``."""
    cells = [
        cell("100", metric="operating_cash"),
        cell("40", metric="cash_capital_payments"),
    ]
    receipt = comparison("same_period", cells)
    # Replace unknown transformations with one that carries the issuer definition
    receipt = {
        **receipt,
        "transformations": [
            {"kind": "issuer_fcf_definition", "factor": "1", "lineage": "issuer-method-v3"}
        ],
        "checked": {**receipt["checked"], "definition": True},
    }
    r = derive_result_cash(
        "cash_after_capital_payments",
        cells,
        comparison_receipt=receipt,
    )
    assert r["status"] == "ready"
    assert r["label"] == "company_adjusted"


def test_cash_after_capital_payments_negative_loss_keeps_sign() -> None:
    cells = [
        cell("-12", metric="operating_cash"),
        cell("3", metric="cash_capital_payments"),
    ]
    r = derive_result_cash(
        "cash_after_capital_payments",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["value"] == "-15"


def test_cash_after_capital_payments_refuses_typed_absence_operand() -> None:
    # A typed-absence operand carries every native field PLUS the absence
    # reason.  Missing, nil, ambiguous and zero are four different states;
    # typed absence is never treated as 0.
    absent_cell = cell(
        "100",
        metric="cash_capital_payments",
        owner_ref="synthetic:cell:capex-absent",
    )
    absent_cell.pop("value", None)
    absent_cell["absence"] = "missing_source"

    cells = [
        cell("100", metric="operating_cash"),
        absent_cell,
    ]
    r = derive_result_cash(
        "cash_after_capital_payments",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "refused"
    assert "operand_typed_absence" in r["limitations"]


# ---------------------------------------------------------------------------
# growth_pct — positive and refusal cases
# ---------------------------------------------------------------------------


def test_growth_pct_ready_with_positive_base() -> None:
    cells = [cell("110", metric="revenue_current"), cell("100", metric="revenue_prior")]
    r = derive_result_cash(
        "growth_pct",
        cells,
        comparison_receipt=comparison("year_over_year", cells),
    )
    assert r["status"] == "ready"
    assert r["value"] == "10"
    assert r["formula_version"] == FORMULA_VERSION


def test_growth_pct_loss_keeps_sign() -> None:
    cells = [cell("-50", metric="profit_current"), cell("100", metric="profit_prior")]
    r = derive_result_cash(
        "growth_pct",
        cells,
        comparison_receipt=comparison("year_over_year", cells),
    )
    assert r["status"] == "ready"
    assert r["value"] == "-150"


def test_growth_pct_zero_base_refuses_percentage() -> None:
    cells = [cell("50", metric="revenue_current"), cell("0", metric="revenue_prior")]
    r = derive_result_cash(
        "growth_pct",
        cells,
        comparison_receipt=comparison("year_over_year", cells),
    )
    assert r["status"] == "limited"
    assert r["value"] is None
    assert r["absolute_change"] == "50"
    assert "percentage_refused_nonpositive_base" in r["limitations"]


def test_growth_pct_negative_base_refuses_percentage() -> None:
    cells = [cell("50", metric="revenue_current"), cell("-10", metric="revenue_prior")]
    r = derive_result_cash(
        "growth_pct",
        cells,
        comparison_receipt=comparison("year_over_year", cells),
    )
    assert r["status"] == "limited"
    assert r["value"] is None
    assert r["absolute_change"] == "60"
    assert "percentage_refused_nonpositive_base" in r["limitations"]


# ---------------------------------------------------------------------------
# margin_pct — positive and refusal cases
# ---------------------------------------------------------------------------


def test_margin_pct_ready_with_same_period_same_perimeter() -> None:
    cells = [
        cell("20", metric="gross_profit"),
        cell("100", metric="revenue"),
    ]
    r = derive_result_cash(
        "margin_pct",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "ready"
    assert r["value"] == "20"
    assert r["formula_version"] == FORMULA_VERSION


def test_margin_pct_refuses_nonpositive_denominator() -> None:
    cells = [cell("10", metric="gross_profit"), cell("0", metric="revenue")]
    r = derive_result_cash(
        "margin_pct",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "refused"
    assert "percentage_refused_nonpositive_base" in r["limitations"]


def test_margin_pct_refuses_mismatched_perimeter() -> None:
    cells = [
        cell("20", metric="gross_profit", business_dimensions={"perimeter": "company"}),
        cell("100", metric="revenue", business_dimensions={"perimeter": "segment:alpha"}),
    ]
    receipt = comparison("same_period", cells)
    receipt = {
        **receipt,
        "checked": {**receipt["checked"], "perimeter": False},
    }
    r = derive_result_cash(
        "margin_pct",
        cells,
        comparison_receipt=receipt,
    )
    assert r["status"] == "refused"
    assert any("perimeter_mismatch" in lim for lim in r["limitations"])


# ---------------------------------------------------------------------------
# paired_remeasurement — both legs required
# ---------------------------------------------------------------------------


def test_paired_remeasurement_ready_with_equal_legs() -> None:
    cells = [
        cell("100", metric="operating_profit"),
        cell("5", metric="matched_expense"),
        cell("20", metric="other_income"),
        cell("5", metric="matched_gain"),
    ]
    r = derive_result_cash(
        "paired_remeasurement",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "ready"
    # operating_profit + matched_expense = 105 ; other_income - matched_gain = 15
    assert r["legs"]["operating_with_expense"] == "105"
    assert r["legs"]["other_income_net"] == "15"
    # Pretax profit unchanged: (100+5) - (20-5) = 90
    assert r["pretax_after_pairing"] == "90"
    assert r["formula_version"] == FORMULA_VERSION


def test_paired_remeasurement_refuses_missing_leg() -> None:
    cells = [
        cell("100", metric="operating_profit"),
        cell("5", metric="matched_expense"),
        cell("20", metric="other_income"),
        # missing matched_gain leg
    ]
    r = derive_result_cash(
        "paired_remeasurement",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "refused"
    assert any("matched_gain" in lim for lim in r["limitations"])


# ---------------------------------------------------------------------------
# cash_rollforward — including residual disclosure
# ---------------------------------------------------------------------------


def test_cash_rollforward_ready_when_closing_matches() -> None:
    cells = [
        cell("100", metric="opening_cash"),
        cell("50", metric="operating_movement"),
        cell("-20", metric="investing_movement"),
        cell("-10", metric="financing_movement"),
        cell("-5", metric="exchange_movement"),
        cell("115", metric="closing_cash"),
    ]
    r = derive_result_cash(
        "cash_rollforward",
        cells,
        comparison_receipt=comparison("rollforward", cells),
    )
    assert r["status"] == "ready"
    assert r["value"] == "115"
    assert r["computed_total"] == "115"
    assert r["residual"] == "0"
    assert r["formula_version"] == FORMULA_VERSION


def test_cash_rollforward_discloses_residual_when_closing_differs() -> None:
    cells = [
        cell("100", metric="opening_cash"),
        cell("50", metric="operating_movement"),
        cell("-20", metric="investing_movement"),
        cell("-10", metric="financing_movement"),
        cell("-5", metric="exchange_movement"),
        cell("120", metric="closing_cash"),
    ]
    r = derive_result_cash(
        "cash_rollforward",
        cells,
        comparison_receipt=comparison("rollforward", cells),
    )
    assert r["status"] == "limited"
    assert r["residual"] == "5"
    assert "rollforward_residual" in r["limitations"]


def test_cash_rollforward_without_closing_discloses_residual_limitation() -> None:
    cells = [
        cell("100", metric="opening_cash"),
        cell("50", metric="operating_movement"),
        cell("-20", metric="investing_movement"),
        cell("-10", metric="financing_movement"),
        cell("-5", metric="exchange_movement"),
    ]
    r = derive_result_cash(
        "cash_rollforward",
        cells,
        comparison_receipt=comparison("rollforward", cells),
    )
    assert r["status"] == "limited"
    assert r["computed_total"] == "115"
    assert "rollforward_residual" in r["limitations"]


# ---------------------------------------------------------------------------
# segment_change_bridge — including residual disclosure
# ---------------------------------------------------------------------------


def test_segment_change_bridge_ready_with_explicit_residual_zero() -> None:
    cells = [
        cell("3", metric="segment_alpha_change"),
        cell("-1", metric="segment_beta_change"),
        cell("0", metric="corporate_change"),
        cell("-2", metric="eliminations"),
    ]
    r = derive_result_cash(
        "segment_change_bridge",
        cells,
        comparison_receipt=comparison("segment_bridge", cells),
    )
    assert r["status"] == "ready"
    assert r["value"] == "0"
    assert r["residual"] == "0"


def test_segment_change_bridge_discloses_unknown_refund_residual() -> None:
    cells = [
        cell("3", metric="segment_alpha_change"),
        cell("-1", metric="segment_beta_change"),
        cell("0", metric="corporate_change"),
        cell("-2", metric="eliminations"),
        cell("1", metric="unallocated_change"),  # e.g. refunds the source did not allocate
    ]
    r = derive_result_cash(
        "segment_change_bridge",
        cells,
        comparison_receipt=comparison("segment_bridge", cells),
    )
    # The unknown 1 is NOT silently allocated to a segment — it stays disclosed.
    assert r["status"] == "ready"
    assert r["value"] == "1"
    assert r["residual"] == "1"
    assert "bridge_residual_disclosed" in r["limitations"]


def test_segment_change_bridge_refuses_zero_segment_legs() -> None:
    """A bridge with no segment_*_change operands is not a bridge.

    Defends against the measured failure: corporate + eliminations alone
    used to fabricate a segment subtotal of zero, certifying a clean bridge
    over no segments.  The derivation surface refuses explicitly.
    """
    corp = cell("40", metric="corporate_change", owner_ref="synthetic:cell:corp")
    elim = cell("-10", metric="eliminations", owner_ref="synthetic:cell:elim")
    cells = [corp, elim]
    receipt = build_comparison_receipt("segment_bridge", cells, checked={})
    r = derive_result_cash(
        "segment_change_bridge",
        cells,
        comparison_receipt=receipt,
    )
    assert r["status"] == "refused"
    assert "operand_missing:segments" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_qualify_operands_refuses_segment_bridge_without_segment_legs() -> None:
    """Same gate, qualification surface entry point."""
    corp = cell("40", metric="corporate_change", owner_ref="synthetic:cell:corp")
    elim = cell("-10", metric="eliminations", owner_ref="synthetic:cell:elim")
    cells = [corp, elim]
    receipt = build_comparison_receipt("segment_bridge", cells, checked={})
    q = qualify_operands(
        "segment_bridge",
        cells,
        comparison_receipt=receipt,
        formula="segment_change_bridge",
    )
    assert q["status"] == "refused"
    assert "operand_missing:segments" in q["limitations"]
    assert q["receipt_ref"] == receipt["receipt_id"]


def test_segment_change_bridge_refuses_typed_absence_unallocated_leg() -> None:
    """A typed-absent unallocated leg must surface — refuse with the absent
    leg's metric so the caller distinguishes 'the issuer disclosed no
    unallocated amount' (no leg) from 'the issuer disclosed one we could
    not read' (typed absence).
    """
    absent = cell("1", metric="unallocated_change", owner_ref="synthetic:cell:ua")
    absent.pop("value", None)
    absent["absence"] = "missing_source"
    cells = [
        cell("3", metric="segment_alpha_change"),
        cell("-1", metric="segment_beta_change"),
        cell("0", metric="corporate_change"),
        cell("-2", metric="eliminations"),
        absent,
    ]
    receipt = build_comparison_receipt("segment_bridge", cells, checked={})
    r = derive_result_cash(
        "segment_change_bridge",
        cells,
        comparison_receipt=receipt,
    )
    assert r["status"] == "refused"
    assert "operand_missing:unallocated_change" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_segment_change_bridge_legitimate_unallocated_value_still_ready() -> None:
    """Control: a valued unallocated leg keeps the bridge ready and
    discloses the residual — the typed-absence gate above does not change
    this well-formed case.
    """
    cells = [
        cell("3", metric="segment_alpha_change"),
        cell("-1", metric="segment_beta_change"),
        cell("0", metric="corporate_change"),
        cell("-2", metric="eliminations"),
        cell("1", metric="unallocated_change"),
    ]
    receipt = build_comparison_receipt("segment_bridge", cells, checked={})
    r = derive_result_cash(
        "segment_change_bridge",
        cells,
        comparison_receipt=receipt,
    )
    assert r["status"] == "ready"
    assert r["residual"] == "1"
    assert "bridge_residual_disclosed" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


# ---------------------------------------------------------------------------
# final_vs_preview — distinct information editions required
# ---------------------------------------------------------------------------


def test_final_vs_preview_ready_with_distinct_editions() -> None:
    cells = [
        cell("100", metric="net_income", digest="a" * 64, revision="r2"),
        cell("100", metric="net_income", digest="b" * 64, revision="r1"),
    ]
    receipt = comparison("final_vs_preview", cells)
    r = derive_result_cash(
        "final_vs_preview",
        cells,
        comparison_receipt=receipt,
    )
    assert r["status"] == "ready"
    assert r["delta"] == "0"
    assert r["editions"]["current"]["revision"] == "r2"
    assert r["editions"]["prior"]["revision"] == "r1"
    assert r["formula_version"] == FORMULA_VERSION


def test_final_vs_preview_refuses_same_edition() -> None:
    cells = [
        cell("100", metric="net_income", digest="a" * 64, revision="r1"),
        cell("100", metric="net_income", digest="a" * 64, revision="r1"),
    ]
    r = derive_result_cash(
        "final_vs_preview",
        cells,
        comparison_receipt=comparison("final_vs_preview", cells),
    )
    assert r["status"] == "refused"
    assert any("distinct_edition_required" in lim for lim in r["limitations"])


# ---------------------------------------------------------------------------
# Qualification — basis/currency/scale/duration/perimeter mismatches
# ---------------------------------------------------------------------------


def test_qualify_operands_refuses_unknown_basis() -> None:
    cells = [
        cell("100", metric="revenue_current", basis={"accounting": "GAAP", "recast": "as_reported"}),
        cell("100", metric="revenue_prior", basis={"accounting": "GAAP"}),  # recast missing
    ]
    q = qualify_operands("year_over_year", cells, comparison_receipt=comparison("year_over_year", cells))
    assert q["status"] == "refused"
    assert any("required_basis_unknown" in lim for lim in q["limitations"])


def test_qualify_operands_refuses_scale_mismatch_without_conversion() -> None:
    cells = [
        cell("100", metric="revenue_current", scale=1, currency="USD"),
        cell("100", metric="revenue_prior", scale=1000, currency="USD"),
    ]
    q = qualify_operands("year_over_year", cells, comparison_receipt=comparison("year_over_year", cells))
    assert q["status"] == "refused"
    assert any("scale_mismatch" in lim for lim in q["limitations"])


def test_qualify_operands_accepts_scale_mismatch_with_exact_conversion() -> None:
    cells = [
        cell("100", metric="revenue_current", scale=1, currency="USD"),
        cell("100", metric="revenue_prior", scale=1000, currency="USD"),
    ]
    receipt = comparison("year_over_year", cells)
    receipt = {
        **receipt,
        "checked": {**receipt["checked"], "scale": True},
        "transformations": [{"kind": "scale_normalize", "factor": "0.001", "lineage": "USD-thousands->millions"}],
    }
    q = qualify_operands("year_over_year", cells, comparison_receipt=receipt)
    assert q["status"] == "ready"


def test_qualify_operands_refuses_currency_mismatch_without_conversion() -> None:
    cells = [
        cell("100", metric="revenue_current", currency="USD"),
        cell("100", metric="revenue_prior", currency="EUR"),
    ]
    q = qualify_operands("year_over_year", cells, comparison_receipt=comparison("year_over_year", cells))
    assert q["status"] == "refused"
    assert any("currency_mismatch" in lim for lim in q["limitations"])


def test_qualify_operands_refuses_duration_mismatch() -> None:
    cells = [
        cell("100", metric="revenue_h1", period={"start": "2026-01-01", "end": "2026-06-30", "fiscal_label": "FY26 H1", "duration": "half_year"}),
        cell("100", metric="revenue_q2", period={"start": "2026-04-01", "end": "2026-06-30", "fiscal_label": "FY26 Q2", "duration": "quarter"}),
    ]
    # Receipt declares duration NOT checked — the module must refuse the
    # quarter-vs-half-year subtraction.
    receipt = comparison("year_over_year", cells)
    receipt = {
        **receipt,
        "checked": {**receipt["checked"], "duration": False},
    }
    q = qualify_operands("year_over_year", cells, comparison_receipt=receipt)
    assert q["status"] == "refused"
    assert any("duration_mismatch" in lim for lim in q["limitations"])


def test_qualify_operands_refuses_equal_null_bases() -> None:
    """Equal nulls NEVER certify comparability."""
    cells = [
        cell("100", metric="revenue_current", basis={"accounting": "GAAP"}),
        cell("100", metric="revenue_prior", basis={"accounting": "GAAP"}),
    ]
    q = qualify_operands("year_over_year", cells, comparison_receipt=comparison("year_over_year", cells))
    # The recast field is missing on both sides — required_basis_unknown, not
    # magically comparable.
    assert q["status"] == "refused"


def test_qualify_operands_refuses_perimeter_mismatch() -> None:
    cells = [
        cell("100", metric="revenue_current", business_dimensions={"perimeter": "company"}),
        cell("100", metric="revenue_prior", business_dimensions={"perimeter": "segment:alpha"}),
    ]
    receipt = comparison("year_over_year", cells)
    receipt = {
        **receipt,
        "checked": {**receipt["checked"], "perimeter": False},
    }
    q = qualify_operands("year_over_year", cells, comparison_receipt=receipt)
    assert q["status"] == "refused"
    assert any("perimeter_mismatch" in lim for lim in q["limitations"])


def test_qualify_operands_refuses_receipt_with_fewer_refs_than_used() -> None:
    cells = [
        cell("100", metric="revenue_current", owner_ref="synthetic:cell:a"),
        cell("100", metric="revenue_prior", owner_ref="synthetic:cell:b"),
    ]
    receipt = comparison("year_over_year", cells[:1])  # receipt only names 'a'
    q = qualify_operands("year_over_year", cells, comparison_receipt=receipt)
    assert q["status"] == "refused"
    assert any("receipt_incomplete" in lim for lim in q["limitations"])


# ---------------------------------------------------------------------------
# Hostile inputs — NaN / Infinity / bool / malformed / float / unknown formula
# ---------------------------------------------------------------------------


def test_nan_decimal_text_refuses() -> None:
    bad = dict(cell("100"), value="NaN")
    r = derive_result_cash(
        "growth_pct",
        [bad, cell("100", metric="revenue_prior")],
        comparison_receipt=comparison("year_over_year", [bad, cell("100", metric="revenue_prior")]),
    )
    assert r["status"] == "refused"
    assert any("operand_malformed" in lim or "non_finite" in lim for lim in r["limitations"])


def test_infinity_decimal_text_refuses() -> None:
    bad = dict(cell("100"), value="Infinity")
    r = derive_result_cash(
        "growth_pct",
        [bad, cell("100", metric="revenue_prior")],
        comparison_receipt=comparison("year_over_year", [bad, cell("100", metric="revenue_prior")]),
    )
    assert r["status"] == "refused"


def test_bool_operand_refuses() -> None:
    bad = dict(cell("100"), value=True)
    r = derive_result_cash(
        "growth_pct",
        [bad, cell("100", metric="revenue_prior")],
        comparison_receipt=comparison("year_over_year", [bad, cell("100", metric="revenue_prior")]),
    )
    assert r["status"] == "refused"


def test_malformed_decimal_text_refuses() -> None:
    bad = dict(cell("100"), value="not-a-number")
    r = derive_result_cash(
        "growth_pct",
        [bad, cell("100", metric="revenue_prior")],
        comparison_receipt=comparison("year_over_year", [bad, cell("100", metric="revenue_prior")]),
    )
    assert r["status"] == "refused"


def test_float_operand_refuses() -> None:
    bad = dict(cell("100"), value=12.5)
    r = derive_result_cash(
        "growth_pct",
        [bad, cell("100", metric="revenue_prior")],
        comparison_receipt=comparison("year_over_year", [bad, cell("100", metric="revenue_prior")]),
    )
    assert r["status"] == "refused"


def test_unknown_formula_refuses() -> None:
    cells = [cell("1"), cell("2")]
    r = derive_result_cash(
        "future_valuation_score",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    assert r["status"] == "refused"
    assert any("unknown_formula" in lim for lim in r["limitations"])


def test_duplicate_operand_refs_refuses() -> None:
    cells = [
        cell("1", owner_ref="synthetic:cell:same"),
        cell("2", owner_ref="synthetic:cell:same"),
    ]
    r = derive_result_cash(
        "growth_pct",
        cells,
        comparison_receipt=comparison("year_over_year", cells),
    )
    assert r["status"] == "refused"
    assert any("duplicate_operand_ref" in lim for lim in r["limitations"])


def test_missing_operand_refuses() -> None:
    # No cells supplied.
    with pytest.raises(TypeError):
        derive_result_cash(
            "growth_pct",
            None,
            comparison_receipt={"receipt_id": "x", "purpose": "year_over_year"},
        )


def test_non_dict_argument_shape_raises_type_error() -> None:
    with pytest.raises(TypeError):
        # comparison_receipt is a non-dict shape; the module refuses the
        # call with TypeError rather than fabricating a comparison.
        derive_result_cash(
            "growth_pct",
            [cell("1"), cell("2")],
            comparison_receipt="not a dict",
        )


def test_non_list_argument_shape_raises_type_error() -> None:
    with pytest.raises(TypeError):
        # cells is a non-list shape; the module refuses the call with
        # TypeError rather than guessing at a list-like.
        derive_result_cash(
            "growth_pct",
            "not a list",
            comparison_receipt={"purpose": "year_over_year", "receipt_id": "x", "operand_refs": ["a", "b"], "checked": {}},
        )


# ---------------------------------------------------------------------------
# Formula-version present in every result + closed-dict shape
# ---------------------------------------------------------------------------


def test_every_result_has_formula_version() -> None:
    for formula in ALLOWED_FORMULAS:
        cells, receipt = _ready_pair(formula)
        r = derive_result_cash(formula, cells, comparison_receipt=receipt)
        assert r["formula_version"] == FORMULA_VERSION, formula
        assert r["formula"] == formula
        assert "operand_refs" in r
        assert "limitations" in r
        assert "status" in r
        assert "receipt_ref" in r


def test_result_is_closed_dict_no_extras() -> None:
    cells, receipt = _ready_pair("cash_after_capital_payments")
    r = derive_result_cash("cash_after_capital_payments", cells, comparison_receipt=receipt)
    expected_keys = {
        "status", "formula", "formula_version", "value", "unit",
        "scale", "currency", "operand_refs", "limitations",
        "receipt_ref", "label",
    }
    assert set(r) == expected_keys


# ---------------------------------------------------------------------------
# Exact-decimal precision
# ---------------------------------------------------------------------------


def test_exact_decimal_precision_0_1_plus_0_2() -> None:
    """Pure Decimal arithmetic — operating_cash -0.1, capital_payments -0.2 -> +0.1 (text-exact)."""
    cells = [
        cell("-0.1", metric="operating_cash"),
        cell("-0.2", metric="cash_capital_payments"),
    ]
    r = derive_result_cash(
        "cash_after_capital_payments",
        cells,
        comparison_receipt=comparison("same_period", cells),
    )
    # -0.1 - (-0.2) = 0.1  (text-exact via Decimal)
    assert r["value"] == "0.1"


def test_underlying_arithmetic_uses_decimal_string_comparison() -> None:
    """The module never reaches for float; a 0.1 + 0.2 sequence yields 0.3 exactly."""
    assert Decimal("0.1") + Decimal("0.2") == Decimal("0.3")


# ---------------------------------------------------------------------------
# B1 — production receipt fed into the derivation consumer
# ---------------------------------------------------------------------------
# For EACH of the five comparability gates, two tests assert the receipt
# round-trip:
#   (a) production build_comparison_receipt(..., checked={}) → derive refuses
#       with the gate's named limitation.
#   (b) production build_comparison_receipt(..., checked={<gate>: True})
#       [+ required transformation for scale / currency] → derive proceeds
#       with r["receipt_ref"] == receipt["receipt_id"].


def test_b1_basis_gate_refuses_with_production_receipt_checked_empty() -> None:
    cells = [
        cell("100", metric="revenue_current", basis={"accounting": "GAAP", "recast": "as_reported"}),
        cell("100", metric="revenue_prior", basis={"accounting": "GAAP"}),  # recast missing
    ]
    receipt = build_comparison_receipt("year_over_year", cells, checked={})
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "refused"
    assert "required_basis_unknown" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_basis_gate_proceeds_with_production_receipt_checked_basis() -> None:
    cells = [
        cell("110", metric="revenue_current", basis={"accounting": "GAAP", "recast": "as_reported"}),
        cell("100", metric="revenue_prior", basis={"accounting": "GAAP", "recast": "as_reported"}),
    ]
    receipt = build_comparison_receipt("year_over_year", cells, checked={"basis": True})
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "ready"
    assert r["value"] == "10"
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_perimeter_gate_refuses_with_production_receipt_checked_empty() -> None:
    cells = [
        cell("20", metric="gross_profit", business_dimensions={"perimeter": "company"}),
        cell("100", metric="revenue", business_dimensions={"perimeter": "segment:alpha"}),
    ]
    receipt = build_comparison_receipt("same_period", cells, checked={})
    r = derive_result_cash("margin_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "refused"
    assert "perimeter_mismatch" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_perimeter_gate_proceeds_with_production_receipt_checked_perimeter() -> None:
    cells = [
        cell("20", metric="gross_profit", business_dimensions={"perimeter": "company"}),
        cell("100", metric="revenue", business_dimensions={"perimeter": "segment:alpha"}),
    ]
    receipt = build_comparison_receipt("same_period", cells, checked={"perimeter": True})
    r = derive_result_cash("margin_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "ready"
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_duration_gate_refuses_with_production_receipt_checked_empty() -> None:
    cells = [
        cell(
            "100",
            metric="revenue_h1",
            period={"start": "2026-01-01", "end": "2026-06-30", "fiscal_label": "FY26 H1", "duration": "half_year"},
        ),
        cell(
            "100",
            metric="revenue_q2",
            period={"start": "2026-04-01", "end": "2026-06-30", "fiscal_label": "FY26 Q2", "duration": "quarter"},
        ),
    ]
    receipt = build_comparison_receipt("year_over_year", cells, checked={})
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "refused"
    assert "duration_mismatch" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_duration_gate_proceeds_with_production_receipt_checked_duration() -> None:
    cells = [
        cell(
            "100",
            metric="revenue_h1",
            period={"start": "2026-01-01", "end": "2026-06-30", "fiscal_label": "FY26 H1", "duration": "half_year"},
        ),
        cell(
            "100",
            metric="revenue_q2",
            period={"start": "2026-04-01", "end": "2026-06-30", "fiscal_label": "FY26 Q2", "duration": "quarter"},
        ),
    ]
    receipt = build_comparison_receipt("year_over_year", cells, checked={"duration": True})
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "ready"
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_scale_gate_refuses_with_production_receipt_checked_empty() -> None:
    cells = [
        cell("100", metric="revenue_current", scale=1, currency="USD"),
        cell("100", metric="revenue_prior", scale=1000, currency="USD"),
    ]
    receipt = build_comparison_receipt("year_over_year", cells, checked={})
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "refused"
    assert "scale_mismatch" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_scale_gate_proceeds_with_production_receipt_checked_scale_with_transform() -> None:
    cells = [
        cell("100", metric="revenue_current", scale=1, currency="USD"),
        cell("100", metric="revenue_prior", scale=1000, currency="USD"),
    ]
    receipt = build_comparison_receipt(
        "year_over_year",
        cells,
        checked={"scale": True},
        transformations=(
            {"kind": "scale_normalize", "factor": "0.001", "lineage": "USD-thousands->millions"},
        ),
    )
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "ready"
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_currency_gate_refuses_with_production_receipt_checked_empty() -> None:
    cells = [
        cell("100", metric="revenue_current", currency="USD"),
        cell("100", metric="revenue_prior", currency="EUR"),
    ]
    receipt = build_comparison_receipt("year_over_year", cells, checked={})
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "refused"
    assert "currency_mismatch" in r["limitations"]
    assert r["receipt_ref"] == receipt["receipt_id"]


def test_b1_currency_gate_proceeds_with_production_receipt_checked_currency_with_transform() -> None:
    cells = [
        cell("100", metric="revenue_current", currency="USD"),
        cell("100", metric="revenue_prior", currency="EUR"),
    ]
    receipt = build_comparison_receipt(
        "year_over_year",
        cells,
        checked={"currency": True},
        transformations=(
            {"kind": "currency_convert", "factor": "0.92", "lineage": "ECB-2026Q2"},
        ),
    )
    r = derive_result_cash("growth_pct", cells, comparison_receipt=receipt)
    assert r["status"] == "ready"
    assert r["receipt_ref"] == receipt["receipt_id"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ready_pair(formula: str) -> tuple[list[Mapping], dict]:
    """Return a (cells, receipt) pair that is ready for the named formula."""
    if formula == "cash_after_capital_payments":
        cells = [cell("100", metric="operating_cash"), cell("40", metric="cash_capital_payments")]
    elif formula == "growth_pct":
        cells = [cell("110", metric="revenue"), cell("100", metric="revenue_prior")]
    elif formula == "margin_pct":
        cells = [cell("20", metric="gross_profit"), cell("100", metric="revenue")]
    elif formula == "paired_remeasurement":
        cells = [
            cell("100", metric="operating_profit"),
            cell("5", metric="matched_expense"),
            cell("20", metric="other_income"),
            cell("5", metric="matched_gain"),
        ]
    elif formula == "cash_rollforward":
        cells = [
            cell("100", metric="opening_cash"),
            cell("50", metric="operating_movement"),
            cell("-20", metric="investing_movement"),
            cell("-10", metric="financing_movement"),
            cell("-5", metric="exchange_movement"),
            cell("115", metric="closing_cash"),
        ]
    elif formula == "segment_change_bridge":
        cells = [
            cell("3", metric="segment_alpha_change"),
            cell("-1", metric="segment_beta_change"),
            cell("0", metric="corporate_change"),
            cell("-2", metric="eliminations"),
        ]
    elif formula == "final_vs_preview":
        cells = [
            cell("100", metric="net_income", digest="a" * 64, revision="r2"),
            cell("100", metric="net_income", digest="b" * 64, revision="r1"),
        ]
    else:
        raise AssertionError(formula)
    return cells, comparison(_purpose_for(formula), cells)


def _purpose_for(formula: str) -> str:
    return {
        "cash_after_capital_payments": "same_period",
        "growth_pct": "year_over_year",
        "margin_pct": "same_period",
        "paired_remeasurement": "same_period",
        "cash_rollforward": "rollforward",
        "segment_change_bridge": "segment_bridge",
        "final_vs_preview": "final_vs_preview",
    }[formula]


def test_typed_absence_helper_returns_owner_shape() -> None:
    typed = typed_absence("missing_source")
    assert typed == {"absence": "missing_source"}