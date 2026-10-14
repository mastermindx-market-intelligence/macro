"""Hold the dossier source-edition section dict (W10-C).

``chronology_section`` publishes the section the dossier renders while
``select_editions`` and ``assess_dossier_comparison`` remain unbound. It does
not define either name. The dict carries the six block codes W8-B pins, the
enrolled label and stated ends, and ``SourceDocument.to_payload()`` for each
document. When a later ruling makes ``financial_dossier.select_editions``
callable, the W8-B frozenset pin turns red and this section's ``blocks`` pin
turns red in the same change.

No theme state, no ``guidance_history``, no ``document_kind`` field.
"""

from __future__ import annotations

from copy import deepcopy

from engine.company_intelligence import financial_dossier
from engine.company_intelligence.industrials_chronology_section import (
    chronology_section,
)
from tests.industrials_result_cash_helpers import case
from tests.test_industrials_edition_record import _XFAIL_BLOCKS


def test_chronology_stays_held_with_the_six_blocks() -> None:
    held = chronology_section(case("preliminary_final"), tolerance_days=3)
    assert held["status"] == "held"
    assert isinstance(held["blocks"], frozenset)
    assert held["blocks"] == _XFAIL_BLOCKS
    documents = held["documents"]
    assert len(documents) == 2
    assert all(isinstance(payload, dict) for payload in documents)
    assert documents[0]["event_id"] == documents[1]["event_id"]
    assert held["presented_fiscal_label"] is None
    assert held["hold"] == "no_cell_fiscal_label"
    assert held["stated_ends"] == ()


def test_labeled_case_puts_fy2026_q2_on_payloads() -> None:
    loaded = case("same_number_two_headers")
    cell = deepcopy(loaded["cells"][0])
    wrapped = _one_release(cells=[cell])
    section = chronology_section(wrapped, tolerance_days=3)
    assert section["status"] == "held"
    assert section["blocks"] == _XFAIL_BLOCKS
    documents = section["documents"]
    assert len(documents) == 1
    payload = documents[0]
    assert payload["presented_fiscal_label"] == "FY2026 Q2"
    assert section["presented_fiscal_label"] == "FY2026 Q2"
    assert section["hold"] is None
    stated_ends = section["stated_ends"]
    assert len(stated_ends) == 1


def test_chronology_does_not_define_select_editions() -> None:
    assert getattr(financial_dossier, "select_editions", None) is None
    assert getattr(financial_dossier, "assess_dossier_comparison", None) is None


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
