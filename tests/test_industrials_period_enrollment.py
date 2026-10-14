"""Enroll the stated fiscal label onto the native edition record (W8-A).

The synthetic cell already carries ``FY2026 Q2`` and period end 3 July.
Enrollment copies that label onto ``presented_fiscal_label`` and must not
let a three-day tolerance rewrite the cell end to 30 June.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

from engine.company_intelligence.industrials_period_enrollment import (
    enroll_stated_period,
)
from engine.company_intelligence.industrials_source_facts import edition_documents
from tests.industrials_result_cash_helpers import case


def test_stated_end_not_snapped_on_enrolled_cell() -> None:
    result = enroll_stated_period(case("same_number_two_headers"), tolerance_days=3)
    assert result.stated_ends
    assert set(result.stated_ends) == {date(2026, 7, 3)}
    assert all(end != date(2026, 6, 30) for end in result.stated_ends)
    assert len(result.cells) == 2
    assert [cell["period"]["end"] for cell in result.cells] == [
        "2026-07-03",
        "2026-07-03",
    ]


def test_presented_fiscal_label_reaches_payload() -> None:
    loaded = case("same_number_two_headers")
    cell = deepcopy(loaded["cells"][0])
    enrolled = enroll_stated_period(
        _one_release(cells=[cell]),
        tolerance_days=3,
    )
    assert len(enrolled.documents) == 1
    document = enrolled.documents[0]
    assert document.to_payload()["presented_fiscal_label"] == "FY2026 Q2"
    assert document.rights_profile == "rp_unknown_v1"
    assert cell["quality"]["rights_profile"] == "rp_public_primary_v1"
    assert enrolled.label == "FY2026 Q2"
    assert enrolled.hold is None


def test_disagreed_labels_leave_payload_null() -> None:
    loaded = case("same_number_two_headers")
    first = deepcopy(loaded["cells"][0])
    second = deepcopy(loaded["cells"][1])
    second["period"] = dict(second["period"])
    second["period"]["fiscal_label"] = "FY2026 Q3"
    enrolled = enroll_stated_period(
        _one_release(cells=[first, second]),
        tolerance_days=3,
    )
    assert enrolled.label is None
    assert enrolled.hold == "fiscal_label_disagreement"
    assert enrolled.documents
    assert all(
        document.presented_fiscal_label is None for document in enrolled.documents
    )
    assert all(
        document.to_payload()["presented_fiscal_label"] is None
        for document in enrolled.documents
    )


def test_preliminary_final_has_no_cell_label() -> None:
    loaded = case("preliminary_final")
    enrolled = enroll_stated_period(loaded, tolerance_days=3)
    assert enrolled.label is None
    assert enrolled.hold == "no_cell_fiscal_label"
    assert enrolled.cells == ()
    assert enrolled.stated_ends == ()
    assert enrolled.documents == edition_documents(loaded)
    assert len(enrolled.documents) == 2


def _one_release(*, cells: list[dict]) -> dict:
    """One synthetic example.invalid release plus the cells under test."""
    return {
        "synthetic": True,
        "issuer": {"company_id": "synthetic:northgate"},
        "sources": [
            {
                "source_id": "northgate-stated",
                "url": "https://example.invalid/stated-period.json",
                "mode": "release",
                "rights_state": "public_primary",
                "recorded_at": "2026-07-10T12:00:00Z",
            }
        ],
        "documents": [
            {
                "document_ref": "synthetic:document:stated-period",
                "source_id": "northgate-stated",
                "source_at": "2026-07-10T12:00:00Z",
                "recorded_at": "2026-07-10T12:01:00Z",
            }
        ],
        "cells": cells,
    }
