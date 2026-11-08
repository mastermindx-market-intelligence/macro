"""Industrials T02 issuer identities and empty extraction profiles.

This module enrolls the two first-vertical cases into the incumbent Company
Intelligence identity/profile seam. It deliberately does not implement T03
financial extraction and does not place either issuer into the #7870 discovery
population.

Listing validity starts are evidence bounds, not incorporation/history claims:
the selected SEC filings are a 10-K for CIK 0000851520 filed 2026-02-27 and a
10-K for CIK 0000077360 filed 2026-02-24. Those companyfacts rows carry form,
filed, and accession, and they do not carry a listing MIC. Those floors cite
10-K accession 0001193125-26-082508 (EXPO, filed 2026-02-27) and 10-K accession
0000077360-26-000007 (PNR, filed 2026-02-24) from companyfacts rows in
data/debt_maturity/cache/CIK0000851520.json and CIK0000077360.json. CIKs are
data/edgar/ticker_cik_ledger.json ("EXPO": 851520, "PNR": 77360). Earlier
symbol history remains unbound rather than falling back to the identity
owner's ALIAS_EPOCH default.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .identity import IssuerIdentity, ListingAlias, company_id_for_cik
from .issuer_profiles import IssuerProfile, _no_guidance


# 10-K accession 0001193125-26-082508 filed 2026-02-27 (CIK0000851520.json).
EXPO_CIK = "0000851520"
# 10-K accession 0000077360-26-000007 filed 2026-02-24 (CIK0000077360.json).
PNR_CIK = "0000077360"

# 10-K accession 0001193125-26-082508 filed 2026-02-27.
EXPO_LISTING_VALID_FROM = date(2026, 2, 27)
# 10-K accession 0000077360-26-000007 filed 2026-02-24.
PNR_LISTING_VALID_FROM = date(2026, 2, 24)


def expo_issuer() -> IssuerIdentity:
    return IssuerIdentity(
        company_id=company_id_for_cik(EXPO_CIK),
        display_name="Exponent, Inc.",
        fiscal_year_end_month=1,
        reporting_currency="USD",
        listings=(
            ListingAlias(
                ticker="EXPO",
                mic="XNAS",
                share_class="common",
                trading_currency="USD",
                is_primary=True,
                valid_from=EXPO_LISTING_VALID_FROM,
            ),
        ),
        external_ids={"cik": EXPO_CIK},
    )


def pnr_issuer() -> IssuerIdentity:
    return IssuerIdentity(
        company_id=company_id_for_cik(PNR_CIK),
        display_name="Pentair plc",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(
            ListingAlias(
                ticker="PNR",
                mic="XNYS",
                share_class="ordinary",
                trading_currency="USD",
                is_primary=True,
                valid_from=PNR_LISTING_VALID_FROM,
            ),
        ),
        external_ids={"cik": PNR_CIK},
    )


def _no_release_facts(**_kwargs: Any) -> list[dict[str, Any]]:
    return []


def _no_transcript_claims(**_kwargs: Any) -> list[dict[str, Any]]:
    return []


def expo_profile() -> IssuerProfile:
    """T02 profile shell; T03 owns all Exponent fact/claim extraction."""
    return IssuerProfile(
        ticker="EXPO",
        extract_release_facts=_no_release_facts,
        extract_transcript_claims=_no_transcript_claims,
        extract_guidance=_no_guidance,
    )


def pnr_profile() -> IssuerProfile:
    """T02 profile shell; T03 owns all Pentair fact/claim extraction."""
    return IssuerProfile(
        ticker="PNR",
        extract_release_facts=_no_release_facts,
        extract_transcript_claims=_no_transcript_claims,
        extract_guidance=_no_guidance,
    )


__all__ = [
    "EXPO_CIK",
    "PNR_CIK",
    "EXPO_LISTING_VALID_FROM",
    "PNR_LISTING_VALID_FROM",
    "expo_issuer",
    "pnr_issuer",
    "expo_profile",
    "pnr_profile",
]
