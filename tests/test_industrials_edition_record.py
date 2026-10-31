"""Hold the dossier source-edition section until a selector ruling (W8-B).

The six block codes are the holes that keep the T05 strict xfails in place.
This file does not define ``select_editions`` or ``assess_dossier_comparison``.
"""
from __future__ import annotations

from engine.company_intelligence import financial_dossier
from engine.company_intelligence.documents import DOCUMENT_KINDS, SourceDocument
from engine.company_intelligence.industrials_edition_record import edition_hold
from engine.company_intelligence.industrials_source_facts import edition_documents
from tests.industrials_result_cash_helpers import case


# Pinned. A later change that adds select_editions drops a code and turns this red.
_XFAIL_BLOCKS = frozenset(
    {
        "statement_mode_unstored",
        "selector_signature_unruled",
        "cutoff_exclusion_unselected",
        "same_day_grain_unstored",
        "acquisition_outside_document",
        "comparison_unbound",
    }
)


def test_edition_hold_names_the_blocks_that_keep_xfails() -> None:
    loaded = case("preliminary_final")
    held = edition_hold(loaded)
    assert held["status"] == "held"
    assert isinstance(held["blocks"], frozenset)
    assert held["blocks"] == _XFAIL_BLOCKS
    documents = held["documents"]
    assert documents == edition_documents(loaded)
    assert len(documents) == 2
    assert all(isinstance(document, SourceDocument) for document in documents)
    assert documents[0].event_id == documents[1].event_id


def test_three_documents_share_one_event() -> None:
    loaded = _three_edition_case()
    documents = edition_documents(loaded)
    assert len(documents) == 3
    assert len({document.event_id for document in documents}) == 1
    assert len({document.document_id for document in documents}) == 3
    assert all(document.document_kind in DOCUMENT_KINDS for document in documents)
    filings = [document for document in documents if document.document_kind == "filing"]
    releases = [
        document for document in documents if document.document_kind == "release"
    ]
    assert len(filings) == 1
    assert len(releases) == 2
    assert filings[0].is_amendment is False
    held = edition_hold(loaded)
    assert held["status"] == "held"
    assert held["blocks"] == _XFAIL_BLOCKS


def test_hold_does_not_define_select_editions() -> None:
    assert getattr(financial_dossier, "select_editions", None) is None
    assert getattr(financial_dossier, "assess_dossier_comparison", None) is None


def _three_edition_case() -> dict:
    """Two releases and one filing, three example.invalid sources, one company."""
    return {
        "synthetic": True,
        "issuer": {"company_id": "synthetic:halcyon"},
        "sources": [
            {
                "source_id": "halcyon-release-a",
                "url": "https://example.invalid/release-a.json",
                "mode": "release",
                "rights_state": "public_primary",
                "recorded_at": "2026-07-09T12:00:00Z",
            },
            {
                "source_id": "halcyon-release-b",
                "url": "https://example.invalid/release-b.json",
                "mode": "release",
                "rights_state": "public_primary",
                "recorded_at": "2026-07-20T12:00:00Z",
            },
            {
                "source_id": "halcyon-filing",
                "url": "https://example.invalid/filing.json",
                "mode": "filing",
                "rights_state": "public_primary",
                "recorded_at": "2026-08-01T12:00:00Z",
            },
        ],
        "documents": [
            {
                "document_ref": "synthetic:document:release-a",
                "source_id": "halcyon-release-a",
                "source_at": "2026-07-09T12:00:00Z",
            },
            {
                "document_ref": "synthetic:document:release-b",
                "source_id": "halcyon-release-b",
                "source_at": "2026-07-20T12:00:00Z",
            },
            {
                "document_ref": "synthetic:document:filing",
                "source_id": "halcyon-filing",
                "source_at": "2026-08-01T12:00:00Z",
            },
        ],
        "cells": [],
    }
