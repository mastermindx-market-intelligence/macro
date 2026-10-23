"""Certified-comparison enrollment: stated end + fiscal label beside the quote (W10-A).

``enroll_certified_comparison`` joins two owners without editing either:
``enroll_stated_period`` supplies the stated cell ends and the shared fiscal
label, and ``derive_result_cash`` supplies the quoted derivation dict.  The
synthetic ``same_number_two_headers`` case carries ``FY2026 Q2`` and a 3 July
cell end; enrollment must show both next to the derivation's ``status`` /
``value`` without snapping 3 July to 30 June and without ``_ready_result``
growing a ``period`` key.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from engine.company_intelligence.industrials_certified_enrollment import (
    enroll_certified_comparison,
)
from engine.company_intelligence.industrials_source_facts import extract_case_cells
from tests.industrials_result_cash_helpers import case, comparison


def test_stated_end_not_snapped_on_certified_enrollment() -> None:
    """The certified record carries the cell's stated 3 July, not 30 June."""
    loaded = case("same_number_two_headers")
    enrolled = enroll_certified_comparison(
        loaded,
        formula="margin_pct",
        comparison_receipt=comparison("same_period", extract_case_cells(loaded)),
        tolerance_days=3,
    )
    assert enrolled["stated_ends"] == (date(2026, 7, 3), date(2026, 7, 3))
    assert all(end != date(2026, 6, 30) for end in enrolled["stated_ends"])


def test_fiscal_label_reaches_certified_record() -> None:
    """The shared cell label reaches the record AND every enrolled document.

    ``same_number_two_headers.json`` has no ``documents`` block at HEAD, so the
    cells are placed in a one-release synthetic case (the W8-A convention in
    ``test_presented_fiscal_label_reaches_payload``) and the payload assertion
    is load-bearing rather than vacuous.
    """
    loaded = _one_release(cells=deepcopy(case("same_number_two_headers")["cells"]))
    enrolled = enroll_certified_comparison(
        loaded,
        formula="margin_pct",
        comparison_receipt=comparison("same_period", extract_case_cells(loaded)),
        tolerance_days=3,
    )
    assert enrolled["presented_fiscal_label"] == "FY2026 Q2"
    assert enrolled["hold"] is None
    assert len(enrolled["documents"]) == 1
    assert all(
        document.to_payload()["presented_fiscal_label"] == "FY2026 Q2"
        for document in enrolled["documents"]
    )


def test_refused_denominator_is_quoted_not_recomputed() -> None:
    """A W8-C swapped denominator: the refusal is quoted verbatim, value None,
    and the stated ends and shared label still enroll."""
    loaded = case("same_number_two_headers")
    for candidate in loaded["cells"]:
        dimensions = candidate.get("business_dimensions") or {}
        if dimensions.get("segment") == "engineering":
            dimensions["denominator"] = "group_revenue"
    enrolled = enroll_certified_comparison(
        loaded,
        formula="margin_pct",
        comparison_receipt=comparison("same_period", extract_case_cells(loaded)),
        tolerance_days=3,
    )
    derivation = enrolled["derivation"]
    assert derivation["status"] == "refused"
    assert "mislabeled_denominator" in derivation["limitations"]
    assert derivation["value"] is None
    assert enrolled["stated_ends"] == (date(2026, 7, 3), date(2026, 7, 3))
    assert enrolled["presented_fiscal_label"] == "FY2026 Q2"
    assert enrolled["hold"] is None


def test_disagreed_labels_leave_certified_label_null() -> None:
    """FY2026 Q2 beside FY2026 Q3: the certified label is null and names the
    ``fiscal_label_disagreement`` hold; no document carries a label."""
    loaded = _one_release(cells=[deepcopy(c) for c in case("same_number_two_headers")["cells"]])
    first, second = loaded["cells"]
    second["period"] = dict(second["period"])
    second["period"]["fiscal_label"] = "FY2026 Q3"
    assert first["period"]["fiscal_label"] == "FY2026 Q2"
    enrolled = enroll_certified_comparison(
        loaded,
        formula="margin_pct",
        comparison_receipt=comparison("same_period", extract_case_cells(loaded)),
        tolerance_days=3,
    )
    assert enrolled["presented_fiscal_label"] is None
    assert enrolled["hold"] == "fiscal_label_disagreement"
    assert enrolled["stated_ends"] == (date(2026, 7, 3), date(2026, 7, 3))
    assert all(
        document.to_payload()["presented_fiscal_label"] is None
        for document in enrolled["documents"]
    )


def test_negative_tolerance_propagates_to_enroll_stated_period() -> None:
    """``tolerance_days`` must reach ``enroll_stated_period`` verbatim.

    ``enroll_stated_period`` runs ``check_tolerance_days`` first (engine/
    company_intelligence/industrials_period_enrollment.py:55; the ValueError
    is raised at engine/company_intelligence/industrials_fiscal.py:24), so
    ``enroll_certified_comparison`` must surface ``tolerance_days=-1`` before
    any record is built. Hard-coding the tolerance inside this join would
    silently swallow it (mutant mE1).
    """
    loaded = case("same_number_two_headers")
    with pytest.raises(ValueError, match="tolerance_days must be >= 0"):
        enroll_certified_comparison(
            loaded,
            formula="margin_pct",
            comparison_receipt=comparison("same_period", extract_case_cells(loaded)),
            tolerance_days=-1,
        )

def _one_release(*, cells: list[dict]) -> dict:
    """One synthetic example.invalid release plus the cells under test."""
    return {
        "synthetic": True,
        "issuer": {"company_id": "synthetic:northgate"},
        "sources": [
            {
                "source_id": "northgate-certified",
                "url": "https://example.invalid/certified-enrollment.json",
                "mode": "release",
                "rights_state": "public_primary",
                "recorded_at": "2026-07-10T12:00:00Z",
            }
        ],
        "documents": [
            {
                "document_ref": "synthetic:document:certified-enrollment",
                "source_id": "northgate-certified",
                "source_at": "2026-07-10T12:00:00Z",
                "recorded_at": "2026-07-10T12:01:00Z",
            }
        ],
        "cells": cells,
    }
