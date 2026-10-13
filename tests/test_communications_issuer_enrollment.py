"""Alphabet dual-listing enrollment on the incumbent identity/profile seam.

GOOGL and GOOG are one issuer (CIK 0001652044). The lookup is what
``scripts/refresh_event_workspaces.py`` already calls. This suite does not
call that script and does not put Alphabet on ``production_registry``.
"""
from __future__ import annotations

from datetime import date

from engine.company_intelligence.event_workspace import production_registry
from engine.company_intelligence.issuer_profiles import (
    issuer_for_ticker,
    profile_for_ticker,
)

_ALPHABET_COMPANY_ID = "cik:0001652044"
_LISTING_FLOOR = date(2023, 5, 9)
_DAY_BEFORE_FLOOR = date(2023, 5, 8)
# tests/fixtures/company_intelligence/golden_corpus_issuers.v1.json
# Alphabet listings: GOOGL share_class "A", GOOG share_class "C".
# That fixture's is_primary is not copied.
_ALPHABET_SHARE_CLASS = {"GOOGL": "A", "GOOG": "C"}


def _assert_alphabet_identity(issuer) -> None:
    assert issuer is not None
    assert issuer.company_id == _ALPHABET_COMPANY_ID
    assert issuer.display_name == "Alphabet Inc."
    assert issuer.fiscal_year_end_month == 12
    assert issuer.listings_at(_DAY_BEFORE_FLOOR) == ()
    assert tuple(listing.ticker for listing in issuer.listings) == ("GOOGL", "GOOG")
    for listing in issuer.listings:
        assert listing.mic == "XNAS"
        assert listing.is_primary is False
        assert listing.share_class == _ALPHABET_SHARE_CLASS[listing.ticker]
        assert listing.valid_from == _LISTING_FLOOR


def test_issuer_for_ticker_resolves_both_alphabet_listings() -> None:
    """Both listings are one CIK, and neither is elected primary."""
    googl = issuer_for_ticker("GOOGL")
    goog = issuer_for_ticker("GOOG")
    _assert_alphabet_identity(googl)
    _assert_alphabet_identity(goog)
    assert googl.company_id == goog.company_id
    assert issuer_for_ticker("GOOGM") is None
    assert issuer_for_ticker("GOOGN") is None


def test_profile_for_ticker_is_an_empty_extractor() -> None:
    """generic_path_only: release facts, transcript claims, and guidance stay empty."""
    for ticker in ("GOOGL", "GOOG"):
        profile = profile_for_ticker(ticker)
        assert profile is not None
        assert profile.ticker == ticker
        assert profile.extract_release_facts(
            bound=None, document_id="doc", event_id="evt", fiscal_period=None,
        ) == []
        assert profile.extract_transcript_claims(
            segments=(), document_id="doc", body_sha256="", event_id="evt",
        ) == []
        assert profile.extract_guidance(
            segments=(), document_id="doc", body_sha256="", event_id="evt",
        ) == []


def test_meta_ttd_mgni_stay_unenrolled() -> None:
    for ticker in ("META", "TTD", "MGNI"):
        assert issuer_for_ticker(ticker) is None
        assert profile_for_ticker(ticker) is None


def test_production_registry_excludes_communications_tickers() -> None:
    """GOOGL, GOOG, META, TTD, and MGNI stay off the registry.

    The four homebuilders stay. This does not freeze the rest of the ticker
    list, so a later issuer rebase can add listings without enrolling these.
    """
    registry = production_registry()
    tickers = {
        listing.ticker for issuer in registry for listing in issuer.listings
    }
    for ticker in ("GOOGL", "GOOG", "META", "TTD", "MGNI"):
        assert ticker not in tickers
    for ticker in ("DHI", "PHM", "KBH", "TOL"):
        assert ticker in tickers


def test_homebuilder_lookup_unchanged() -> None:
    dhi = issuer_for_ticker("DHI")
    assert dhi is not None
    assert dhi.company_id == "cik:0000882184"
    assert dhi.display_name == "D.R. Horton, Inc."
    profile = profile_for_ticker("DHI")
    assert profile is not None
    assert profile.ticker == "DHI"
