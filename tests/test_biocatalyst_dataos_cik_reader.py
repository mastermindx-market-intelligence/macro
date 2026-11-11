from __future__ import annotations

import pytest

from lib.dataos.identity import IdentityError, IssuerMaster


def _row(security: str, issuer: str, cik: str | None, *, state: str | None = None):
    code = security.rsplit('-', 1)[-1]
    return {
        "security_id": security,
        "issuer_id": issuer,
        "issuer_state": "RESOLVED",
        "issuer_cik": cik,
        "listing_key": security.removeprefix("SEC:"),
        "security_state": state,
        "superseded_by": None,
    }


def test_issuers_for_cik_returns_sorted_distinct_active_existing_issuers() -> None:
    master = IssuerMaster.from_records([
        _row("SEC:US-XNAS-GOOG", "ISS:US-XNAS-GOOG", "1652044"),
        _row("SEC:US-XNAS-GOOGL", "ISS:US-XNAS-GOOG", "0001652044"),
        _row("SEC:US-XNYS-ALT", "ISS:US-XNYS-ALT", "1652044"),
    ])
    assert master.issuers_for_cik("1652044") == (
        "ISS:US-XNAS-GOOG",
        "ISS:US-XNYS-ALT",
    )


def test_issuers_for_cik_excludes_superseded_security_rows() -> None:
    master = IssuerMaster.from_records([
        _row(
            "SEC:US-XNYS-OLD",
            "ISS:US-XNYS-OLD",
            "320193",
            state="SUPERSEDED_DUPLICATE_MINT",
        ),
        _row("SEC:US-XNAS-AAPL", "ISS:US-XNAS-AAPL", "320193"),
    ])
    assert master.issuers_for_cik("0000320193") == ("ISS:US-XNAS-AAPL",)


def test_issuers_for_cik_refuses_conflict_on_a_matching_issuer() -> None:
    master = IssuerMaster.from_records([
        _row("SEC:US-XNAS-ONE", "ISS:US-XNAS-ONE", "320193"),
        _row("SEC:US-XNAS-TWO", "ISS:US-XNAS-ONE", "789019"),
    ])
    with pytest.raises(IdentityError, match="conflicting current issuer CIK"):
        master.issuers_for_cik("320193")


def test_unrelated_conflicting_issuer_does_not_poison_query() -> None:
    master = IssuerMaster.from_records([
        _row("SEC:US-XNAS-AAPL", "ISS:US-XNAS-AAPL", "320193"),
        _row("SEC:US-XNAS-X1", "ISS:US-XNAS-X", "789019"),
        _row("SEC:US-XNAS-X2", "ISS:US-XNAS-X", "1652044"),
    ])
    assert master.issuers_for_cik("320193") == ("ISS:US-XNAS-AAPL",)


def test_issuers_for_cik_preserves_nullable_and_strict_cik_normalization() -> None:
    master = IssuerMaster()
    assert master.issuers_for_cik(None) == ()
    assert master.issuers_for_cik("0000320193") == ()
    with pytest.raises(IdentityError, match="issuer CIK"):
        master.issuers_for_cik("CIK-320193")
