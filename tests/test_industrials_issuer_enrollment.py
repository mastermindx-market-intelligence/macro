"""T02 — native Industrials issuer enrollment over the incumbent identity owner.

These anchors implement recovered original requirements IND-D04, IND-D05 and
IND-R210. They prove identity admission rather than ticker syntax: unknown
labels/ticker-like strings fail closed, and every admitted listing has an
evidence-bounded validity start instead of the identity owner's 1970 default.
"""
from __future__ import annotations

from datetime import date, timedelta

from engine.company_intelligence.identity import ALIAS_EPOCH, IssuerRegistry
from engine.company_intelligence.issuer_profiles import (
    issuer_for_ticker,
    profile_for_ticker,
)
from tests.industrials_result_cash_helpers import case


def _required_issuers():
    expo = issuer_for_ticker("EXPO")
    pnr = issuer_for_ticker("PNR")
    assert expo is not None, (
        "EXPO must be natively admitted; ticker syntax is not identity proof"
    )
    assert pnr is not None, (
        "PNR must be natively admitted; ticker syntax is not identity proof"
    )
    return expo, pnr

def test_ind_d04() -> None:
    """Absent fiscal-event cases need native identity admission, never fallback."""
    expo, pnr = _required_issuers()
    assert expo.company_id == "cik:0000851520"
    assert expo.external_ids == {"cik": "0000851520"}
    assert pnr.company_id == "cik:0000077360"
    assert pnr.external_ids == {"cik": "0000077360"}

    # Positive enrollment must not widen the lookup into syntax acceptance.
    for probe in ("EXPO1", "PNRA", "EXPO.US", "UNKNOWN"):
        assert issuer_for_ticker(probe) is None
        assert profile_for_ticker(probe) is None


def test_ind_d05() -> None:
    """A source-only company label cannot become an issuer/security join."""
    expo, pnr = _required_issuers()
    assert profile_for_ticker("EXPO") is not None
    assert profile_for_ticker("PNR") is not None
    assert expo.primary_listing_at(date(2026, 7, 3)) is not None
    assert pnr.primary_listing_at(date(2026, 6, 30)) is not None

    source_only = case("source_only")
    label = source_only["issuer"]["display_name"]
    assert label == "Northgate Testing Services"
    assert issuer_for_ticker(label) is None
    assert profile_for_ticker(label) is None
    assert issuer_for_ticker(source_only["issuer"]["company_id"]) is None

def test_ind_r210() -> None:
    """No default alias epoch or legacy symbol automatically proves history."""
    expo, pnr = _required_issuers()
    expected = {
        "EXPO": (expo, date(2026, 2, 27), "xnas:EXPO"),
        "PNR": (pnr, date(2026, 2, 24), "xnys:PNR"),
    }
    registry = IssuerRegistry([expo, pnr])

    for ticker, (issuer, valid_from, security_id) in expected.items():
        assert len(issuer.listings) == 1
        listing = issuer.listings[0]
        assert listing.valid_from == valid_from
        assert listing.valid_from != ALIAS_EPOCH
        assert registry.resolve_ticker(
            ticker, asof=valid_from - timedelta(days=1)
        ) is None
        resolved = registry.resolve_ticker(ticker, asof=valid_from)
        assert resolved is not None
        assert resolved.company_id == issuer.company_id
        assert resolved.security_id == security_id
