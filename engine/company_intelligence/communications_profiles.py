"""Communications issuer identity for Alphabet's dual listing.

This module enrolls GOOGL and GOOG as one issuer on the incumbent Company
Intelligence identity/profile seam. It does not extract facts and it does not
place Alphabet into ``event_workspace.production_registry`` (that registry is
the discovery population ``scripts/refresh_event_workspaces.py`` sends to
submissions).

Grounded fields, read from this tree (no EDGAR call):

* CIK ``0001652044`` — ``data/edgar/ticker_cik_ledger.json`` maps both
  ``"GOOG"`` and ``"GOOGL"`` to ``1652044``. The same CIK is
  ``config/fundamental_forensics/coverage/five_issuer_v1.json`` ``cik`` and
  ``tests/fixtures/fundamental_forensics/five_issuer_submissions/CIK0001652044.json``.
* Legal name ``Alphabet Inc.`` — submissions ``name`` and the coverage
  record's ``legal_name``.
* Fiscal year end month ``12`` — submissions ``fiscalYearEnd`` ``1231`` and
  the coverage record's ``fiscal_year_end`` ``12-31``.
* MIC ``XNAS`` — coverage ``security_master_binding.mic``. The submissions
  ``exchanges`` array is ``Nasdaq`` for every ticker.
* Listing floor ``2023-05-09`` — coverage ``security_master_binding.effective_at``
  for the GOOGL security-master row, applied to both listings. No separate
  GOOG floor is in the tree. This is an evidence floor, not ``ALIAS_EPOCH``.
* ``share_class`` ``listing`` — the submissions object has no share-class
  field. The literal is a placeholder, not a class election.
* ``is_primary`` false on both listings. ``IssuerIdentity.primary_listing_at``
  falls back to the first covering listing when none is primary; that
  fallback is not a share-class election.
* Extractors stay empty because the coverage record's
  ``identity_binding_state`` is ``generic_path_only``.

``reporting_currency`` and ``trading_currency`` are ``USD`` because
``IssuerIdentity`` / ``ListingAlias`` require an ISO currency and every other
US listing constructed in this package uses that token. The submissions
fixture has no currency field.

GOOGM and GOOGN are in the submissions ``tickers`` array and are not enrolled.
META, TTD, and MGNI are not enrolled.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .identity import IssuerIdentity, ListingAlias, company_id_for_cik
from .issuer_profiles import IssuerProfile, _no_guidance


# data/edgar/ticker_cik_ledger.json "GOOG" / "GOOGL", and
# five_issuer_v1.json cik / CIK0001652044.json.
ALPHABET_CIK = "0001652044"

# five_issuer_v1.json security_master_binding.effective_at (GOOGL row).
# Applied to both listings: the tree has no separate GOOG floor.
ALPHABET_LISTING_VALID_FROM = date(2023, 5, 9)


def alphabet_issuer() -> IssuerIdentity:
    """One issuer for both Nasdaq listings. Neither listing is primary."""
    return IssuerIdentity(
        company_id=company_id_for_cik(ALPHABET_CIK),
        display_name="Alphabet Inc.",
        fiscal_year_end_month=12,
        reporting_currency="USD",
        listings=(
            ListingAlias(
                ticker="GOOGL",
                mic="XNAS",
                share_class="listing",
                trading_currency="USD",
                is_primary=False,
                valid_from=ALPHABET_LISTING_VALID_FROM,
            ),
            ListingAlias(
                ticker="GOOG",
                mic="XNAS",
                share_class="listing",
                trading_currency="USD",
                is_primary=False,
                valid_from=ALPHABET_LISTING_VALID_FROM,
            ),
        ),
        external_ids={"cik": ALPHABET_CIK},
    )


def _no_release_facts(**_kwargs: Any) -> list[dict[str, Any]]:
    return []


def _no_transcript_claims(**_kwargs: Any) -> list[dict[str, Any]]:
    return []


def googl_profile() -> IssuerProfile:
    """Empty extraction profile. generic_path_only owns no Alphabet facts."""
    return IssuerProfile(
        ticker="GOOGL",
        extract_release_facts=_no_release_facts,
        extract_transcript_claims=_no_transcript_claims,
        extract_guidance=_no_guidance,
    )


def goog_profile() -> IssuerProfile:
    """Empty extraction profile for the second listing of the same issuer."""
    return IssuerProfile(
        ticker="GOOG",
        extract_release_facts=_no_release_facts,
        extract_transcript_claims=_no_transcript_claims,
        extract_guidance=_no_guidance,
    )


__all__ = [
    "ALPHABET_CIK",
    "ALPHABET_LISTING_VALID_FROM",
    "alphabet_issuer",
    "googl_profile",
    "goog_profile",
]
