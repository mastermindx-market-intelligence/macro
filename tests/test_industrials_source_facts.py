"""Native Industrials edition records from the synthetic fixtures (W6-B).

These tests build ``SourceDocument`` values. They do not call
``select_editions`` or ``assess_dossier_comparison``, and they do not
assert ``statement_mode``.
"""
from __future__ import annotations

from datetime import datetime, timezone

from engine.company_intelligence.documents import (
    DOCUMENT_KINDS,
    DocumentRevisionChain,
    SourceDocument,
)
from engine.company_intelligence.industrials_source_facts import (
    edition_chain,
    edition_documents,
    extract_case_cells,
)
from tests.industrials_result_cash_helpers import case


def test_ind_r205() -> None:
    """Same digits under two headers stay two cells (IND-R205)."""
    cells = extract_case_cells(case("same_number_two_headers"))
    assert len(cells) == 2
    assert cells[0]["value"] == "68"
    assert cells[1]["value"] == "68"
    assert cells[0]["semantic_selector"] != cells[1]["semantic_selector"]
    assert cells[0]["business_dimensions"]["denominator"] == "group_revenue"
    assert cells[1]["business_dimensions"]["denominator"] == "engineering_revenue"


def test_preliminary_and_final_share_one_event() -> None:
    loaded = case("preliminary_final")
    documents = edition_documents(loaded)
    assert len(documents) == 2
    assert all(isinstance(document, SourceDocument) for document in documents)
    assert documents[0].event_id == documents[1].event_id
    assert documents[0].content_sha256 != documents[1].content_sha256
    assert all(document.document_kind in DOCUMENT_KINDS for document in documents)
    chain = edition_chain(loaded)
    assert isinstance(chain, DocumentRevisionChain)
    assert len(chain.revisions) == 2
    assert chain.event_id == documents[0].event_id
    assert chain.revisions[0].superseded_by_document_id == chain.revisions[1].document_id
    assert chain.revisions[1].supersedes_document_id == chain.revisions[0].document_id
    assert chain.revisions[1].is_amendment is False
    by_published = sorted(documents, key=lambda document: document.published_at)
    assert by_published[0].published_at == datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    assert by_published[0].available_at == datetime(2026, 7, 9, 12, 1, tzinfo=timezone.utc)
    assert by_published[1].published_at == datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    assert by_published[1].available_at == datetime(2026, 8, 1, 12, 1, tzinfo=timezone.utc)
    assert all(document.rights_state == "public_primary" for document in documents)
    assert all(document.rights_profile == "rp_unknown_v1" for document in documents)


def test_date_only_publication_stays_unknown() -> None:
    """A date-only clock is not midnight UTC (IND-D20 / ruling R3)."""
    documents = edition_documents(
        {
            "synthetic": True,
            "issuer": {"company_id": "synthetic:halcyon"},
            "sources": [
                {
                    "source_id": "halcyon-date-only",
                    "url": "https://example.invalid/date-only.json",
                    "mode": "release",
                    "rights_state": "unknown",
                }
            ],
            "documents": [
                {
                    "document_ref": "synthetic:document:date-only",
                    "source_id": "halcyon-date-only",
                    "source_at": "2026-07-30",
                }
            ],
        }
    )
    assert len(documents) == 1
    published = documents[0].published_at
    assert published is None
    assert published != datetime(2026, 7, 30, 0, 0, 0, tzinfo=timezone.utc)
    assert documents[0].available_at is None
    assert documents[0].fetched_at is None


def test_filing_enrichment_is_not_an_amendment() -> None:
    """Filing enrichment is not a correction (IND-R204)."""
    documents = edition_documents(case("filing_later"))
    assert [document.document_kind for document in documents] == ["release", "filing"]
    filing = documents[1]
    assert filing.is_amendment is False
    assert documents[0].event_id == filing.event_id
    assert documents[0].is_amendment is False
    assert all(document.published_at is None for document in documents)
    assert documents[0].available_at == datetime(2026, 7, 10, 12, 0, tzinfo=timezone.utc)
    assert documents[1].available_at == datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    assert documents[0].rights_state == "public_primary"
    assert filing.rights_state == "unknown"
    assert all(document.rights_profile == "rp_unknown_v1" for document in documents)
