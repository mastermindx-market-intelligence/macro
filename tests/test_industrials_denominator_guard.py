"""IND-R206: refuse a company-revenue share presented as segment mix.

The two agreed pairs are the synthetic fixture's own
``(segment, denominator)`` values under ``business_dimensions``. Any other
pair, or a missing key, is ``mislabeled_denominator``. The guard does not
apply to any other metric. It is now reached through
``industrials_result_cash.qualify_operands``, which calls it for every
parsed operand, so ``derive_result_cash`` refuses a mislabeled denominator
before any formula code is reached.

requirement_index.md reserves IND-R206's anchor test for T03's
``tests/test_industrials_source_facts.py``. This suite uses a behaviour
name and is not that anchor.
"""

from __future__ import annotations

import copy
from typing import Any

from engine.fundamental_forensics.industrials_denominator_guard import denominator_refusal
from engine.fundamental_forensics.industrials_result_cash import (
    derive_result_cash,
    qualify_operands,
)
from tests.industrials_result_cash_helpers import case, comparison


def test_denominator_refusal_rejects_a_company_revenue_share_labeled_as_segment_mix() -> None:
    cells = case("same_number_two_headers")["cells"]
    assert {
        (
            cell["business_dimensions"]["segment"],
            cell["business_dimensions"]["denominator"],
        )
        for cell in cells
    } == {
        ("group", "group_revenue"),
        ("engineering", "engineering_revenue"),
    }
    for cell in cells:
        assert denominator_refusal(cell) is None

    engineering = next(
        cell
        for cell in cells
        if cell["business_dimensions"]["segment"] == "engineering"
        and cell["business_dimensions"]["denominator"] == "engineering_revenue"
    )
    swapped = copy.deepcopy(engineering)
    swapped["business_dimensions"]["denominator"] = "group_revenue"
    assert swapped["metric"] == "revenue_share_pct"
    assert denominator_refusal(swapped) == "mislabeled_denominator"

    omitted = copy.deepcopy(engineering)
    del omitted["business_dimensions"]["segment"]
    assert omitted["metric"] == "revenue_share_pct"
    assert "segment" not in omitted["business_dimensions"]
    assert denominator_refusal(omitted) == "mislabeled_denominator"

    other = copy.deepcopy(swapped)
    other["metric"] = "operating_cash"
    assert denominator_refusal(other) is None


# ---------------------------------------------------------------------------
# IND-R206 wiring — the guard is reached through qualify_operands, so a
# refusal surfaces from qualify_operands and from derive_result_cash.


def _engineering_cell(cells: list[dict[str, Any]]) -> dict[str, Any]:
    return next(
        cell
        for cell in cells
        if cell["business_dimensions"].get("segment") == "engineering"
    )


def test_qualify_operands_refuses_swapped_denominator_with_clean_control() -> None:
    """The swapped pair refuses; the same receipt on the agreed pair does not.

    The two fixture cells already carry distinct ``owner_ref`` values
    (``synthetic:cell:group-share`` / ``synthetic:cell:segment-share``), so
    neither call can be refused for ``duplicate_operand_ref`` or
    ``receipt_incomplete`` — the refusal is attributable to the swap alone.
    """
    cells = case("same_number_two_headers")["cells"]
    receipt = comparison("same_period", cells)

    control = qualify_operands("same_period", cells, comparison_receipt=receipt)
    assert control["status"] == "ready"
    assert control["limitations"] == []

    swapped = case("same_number_two_headers")["cells"]
    _engineering_cell(swapped)["business_dimensions"]["denominator"] = "group_revenue"
    refused = qualify_operands("same_period", swapped, comparison_receipt=receipt)
    assert refused["status"] == "refused"
    assert "mislabeled_denominator" in refused["limitations"]


def test_full_comparison_receipt_cannot_silence_the_denominator_guard() -> None:
    """Every ``checked`` key True, a non-empty ``transformations`` list, a
    matching ``purpose`` and complete ``operand_refs`` still cannot vouch a
    mislabeled denominator into a legal operand: the guard call is not
    conditioned on any receipt field.
    """
    swapped = case("same_number_two_headers")["cells"]
    _engineering_cell(swapped)["business_dimensions"]["denominator"] = "group_revenue"
    loud_receipt = {
        "receipt_id": "synthetic:comparison:loud",
        "purpose": "same_period",
        "operand_refs": [cell["owner_ref"] for cell in swapped],
        "checked": {
            name: True
            for name in (
                "basis",
                "definition",
                "perimeter",
                "scale",
                "currency",
                "duration",
                "source_mode",
            )
        },
        "unknowns": [],
        "transformations": [
            {"kind": "unit_scaling", "factor": "1", "lineage": "synthetic:lineage:1"}
        ],
    }
    refused = qualify_operands("same_period", swapped, comparison_receipt=loud_receipt)
    assert refused["status"] == "refused"
    assert "mislabeled_denominator" in refused["limitations"]


def test_derive_result_cash_refuses_swapped_denominator_before_formula_code() -> None:
    """``derive_result_cash('margin_pct', ...)`` gates through
    ``qualify_operands`` before formula dispatch, so the swap refuses with
    ``mislabeled_denominator`` in the ``_refusal_result`` limitations.
    """
    swapped = case("same_number_two_headers")["cells"]
    _engineering_cell(swapped)["business_dimensions"]["denominator"] = "group_revenue"
    result = derive_result_cash(
        "margin_pct", swapped, comparison_receipt=comparison("same_period", swapped)
    )
    assert result["status"] == "refused"
    assert "mislabeled_denominator" in result["limitations"]
    assert result["value"] is None


def test_qualify_operands_refuses_share_cell_with_missing_segment() -> None:
    missing = case("same_number_two_headers")["cells"]
    del _engineering_cell(missing)["business_dimensions"]["segment"]
    refused = qualify_operands(
        "same_period", missing, comparison_receipt=comparison("same_period", missing)
    )
    assert refused["status"] == "refused"
    assert "mislabeled_denominator" in refused["limitations"]


def test_non_share_metric_with_mismatched_pair_is_not_refused_by_the_guard() -> None:
    """Control: the guard is metric-scoped — ``operating_cash`` carrying the
    mismatched pair must not collect ``mislabeled_denominator``.
    """
    cells = case("same_number_two_headers")["cells"]
    cell = _engineering_cell(cells)
    cell["metric"] = "operating_cash"
    cell["business_dimensions"]["denominator"] = "group_revenue"
    single = [cell]
    result = qualify_operands(
        "same_period", single, comparison_receipt=comparison("same_period", single)
    )
    assert "mislabeled_denominator" not in result["limitations"]
    assert result["status"] == "ready"
