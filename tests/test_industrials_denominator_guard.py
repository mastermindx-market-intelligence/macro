"""IND-R206: refuse a company-revenue share presented as segment mix.

The two agreed pairs are the synthetic fixture's own
``(segment, denominator)`` values under ``business_dimensions``. Any other
pair, or a missing key, is ``mislabeled_denominator``. The guard does not
apply to any other metric and does not call ``derive_result_cash``.

requirement_index.md reserves IND-R206's anchor test for T03's
``tests/test_industrials_source_facts.py``. This suite uses a behaviour
name and is not that anchor.
"""

from __future__ import annotations

import copy

from engine.fundamental_forensics.industrials_denominator_guard import denominator_refusal
from tests.industrials_result_cash_helpers import case


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
    swapped["business_dimensions"]["segment"] = "engineering"
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
