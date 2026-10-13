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


def test_ind_t02_factory_keys_and_identity_attributes() -> None:
    """A third factory key, or a drifted name/year-end/class, fails enrollment."""
    from engine.company_intelligence.issuer_profiles import (
        _INDUSTRIALS_ISSUER_FACTORIES,
        _INDUSTRIALS_PROFILE_FACTORIES,
    )

    assert set(_INDUSTRIALS_ISSUER_FACTORIES) == set(_INDUSTRIALS_PROFILE_FACTORIES) == {
        "EXPO",
        "PNR",
    }
    expo, pnr = _required_issuers()
    assert expo.display_name == "Exponent, Inc."
    assert expo.fiscal_year_end_month == 1
    assert expo.listings[0].share_class == "common"
    assert pnr.display_name == "Pentair plc"
    assert pnr.fiscal_year_end_month == 12
    assert pnr.listings[0].share_class == "ordinary"


def test_issuer_for_ticker_doc_names_expo_and_pnr() -> None:
    """The lookup docstring must name the Industrials issuers it now resolves."""
    doc = issuer_for_ticker.__doc__ or ""
    assert "EXPO" in doc
    assert "PNR" in doc
    assert "four homebuilders" not in doc


def test_ind_listing_floors_cite_sec_accessions() -> None:
    """Each CIK and listing floor names the 10-K accession whose filed date it uses."""
    import inspect

    from engine.company_intelligence import industrials_profiles as profiles

    text = inspect.getsource(profiles)

    def window(needle: str) -> str:
        index = text.index(needle)
        return text[max(0, index - 180) : index + 160]

    expo_cik = window("EXPO_CIK")
    pnr_cik = window("PNR_CIK")
    expo_from = window("EXPO_LISTING_VALID_FROM")
    pnr_from = window("PNR_LISTING_VALID_FROM")
    assert "0001193125-26-082508" in expo_cik
    assert "2026-02-27" in expo_cik
    assert "0000077360-26-000007" in pnr_cik
    assert "2026-02-24" in pnr_cik
    assert "0001193125-26-082508" in expo_from
    assert "2026-02-27" in expo_from or "2026, 2, 27" in expo_from
    assert "0000077360-26-000007" in pnr_from
    assert "2026-02-24" in pnr_from or "2026, 2, 24" in pnr_from
