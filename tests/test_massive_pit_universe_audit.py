"""Read-only Massive PIT universe identity audit tests.

Network-free.  These tests pin the two important boundaries:
* provider PIT rows are evidence, never canonical identity by themselves;
* current CIK agreement is diagnostic only and ticker reuse conflicts fail closed.
"""

from __future__ import annotations

from datetime import date

import pytest

from scripts import audit_massive_pit_universe as audit


ASOF = date(2006, 1, 3)


def _source(
    ticker: str,
    *,
    cik: str | None,
    mic: str = "XNYS",
    figi: str | None = "BBG000TEST",
) -> dict:
    return {
        "ticker": ticker,
        "cik": cik,
        "primary_exchange": mic,
        "composite_figi": figi,
        "share_class_figi": None,
        "type": "CS",
        "active": True,
    }


def _master(
    ticker: str,
    *,
    cik: str | None,
    mic: str = "XNYS",
    security_id: str | None = None,
    state: str | None = None,
) -> dict:
    sid = security_id or f"SEC:US-{mic}-{ticker}"
    return {
        "security_id": sid,
        "issuer_id": f"ISS:US-{mic}-{ticker}",
        "issuer_cik": cik,
        "mic": mic,
        "inception_code": ticker,
        "security_state": state,
    }


def _alias(
    ticker: str,
    *,
    security_id: str,
    vendor: str = "massive",
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> dict:
    return {
        "vendor": vendor,
        "vendor_symbol": ticker,
        "security_id": security_id,
        "valid_from": valid_from,
        "valid_to": valid_to,
    }


def test_dated_canonical_alias_plus_matching_identity_is_resolved():
    source = [_source("ABC", cik="1234")]
    master = [_master("ABC", cik="0000001234")]
    aliases = [_alias("ABC", security_id=master[0]["security_id"])]

    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=aliases,
        master_records=master,
    )

    assert receipt["counts"][audit.STATUS_RESOLVED] == 1
    assert receipt["canonical_identity_ready"] is True
    assert receipt["resolved_fraction"] == 1.0


def test_current_cik_match_without_dated_alias_is_diagnostic_not_authority():
    source = [_source("ABC", cik="1234")]
    master = [_master("ABC", cik="0000001234")]

    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=[],
        master_records=master,
    )

    assert receipt["counts"][audit.STATUS_CURRENT_CIK_MATCH_ONLY] == 1
    assert receipt["counts"][audit.STATUS_RESOLVED] == 0
    assert receipt["canonical_identity_ready"] is False
    assert receipt["current_cik_match_only_is_authority"] is False


def test_reused_ticker_with_historical_cik_different_from_current_master_conflicts():
    # The production proof uses real ticker L: Liberty Media in 2006 vs Loews later.
    source = [_source("L", cik="0001082114")]
    current_master = [_master("L", cik="0000060086")]

    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=[],
        master_records=current_master,
    )

    assert receipt["counts"][audit.STATUS_IDENTITY_CONFLICT] == 1
    example = receipt["examples"][audit.STATUS_IDENTITY_CONFLICT][0]
    assert example["source_cik"] == "0001082114"
    assert example["canonical_current_cik"] == "0000060086"
    assert receipt["canonical_identity_ready"] is False


def test_a_dated_alias_cannot_override_a_stable_id_conflict():
    source = [_source("L", cik="0001082114")]
    master = [_master("L", cik="0000060086")]
    aliases = [_alias("L", security_id=master[0]["security_id"])]

    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=aliases,
        master_records=master,
    )

    assert receipt["counts"][audit.STATUS_IDENTITY_CONFLICT] == 1
    assert receipt["counts"][audit.STATUS_RESOLVED] == 0


def test_missing_massive_namespace_remains_an_explicit_owner_gap():
    source = [_source("XYZ", cik="9999")]
    master = []

    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=[
            _alias(
                "XYZ",
                vendor="membership",
                security_id="SEC:US-XNYS-XYZ",
            )
        ],
        master_records=master,
    )

    assert receipt["canonical_vendor_rows_total"] == 0
    assert receipt["counts"][audit.STATUS_MISSING_CANONICAL_ALIAS] == 1
    assert receipt["canonical_identity_ready"] is False


def test_missing_source_stable_identifier_is_not_promoted_from_ticker_only():
    source = [_source("AAA", cik=None, figi=None)]
    master = [_master("AAA", cik=None)]

    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=[],
        master_records=master,
    )

    assert receipt["counts"][audit.STATUS_SOURCE_ID_INCOMPLETE] == 1
    assert receipt["canonical_identity_ready"] is False


def test_unsupported_mic_is_counted_never_guessed():
    source = [_source("XYZ", cik="1234", mic="ARCX")]
    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=[],
        master_records=[],
    )
    assert receipt["counts"][audit.STATUS_UNSUPPORTED_MIC] == 1


def test_duplicate_source_ticker_mic_key_refuses_both_rows():
    source = [
        _source("ABC", cik="1"),
        _source("ABC", cik="2"),
    ]
    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=[],
        master_records=[],
    )
    assert receipt["counts"][audit.STATUS_SOURCE_DUPLICATE] == 2


def test_superseded_master_row_is_not_a_current_identity_candidate():
    source = [_source("ABC", cik="1234")]
    master = [
        _master(
            "ABC",
            cik="0000001234",
            state="SUPERSEDED_DUPLICATE_MINT",
        )
    ]
    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=[],
        master_records=master,
    )
    assert receipt["counts"][audit.STATUS_MISSING_CANONICAL_ALIAS] == 1
    assert receipt["counts"][audit.STATUS_CURRENT_CIK_MATCH_ONLY] == 0


def test_broken_alias_target_is_visible():
    source = [_source("ABC", cik="1234")]
    aliases = [_alias("ABC", security_id="SEC:US-XNYS-MISSING")]
    receipt = audit.audit_identity_rows(
        source,
        on=ASOF,
        alias_records=aliases,
        master_records=[],
    )
    assert receipt["counts"][audit.STATUS_BROKEN_CANONICAL_ALIAS] == 1


def test_alias_validity_is_half_open_through_existing_data_os_reader():
    master = [_master("NEW", cik="0000001234", security_id="SEC:US-XNYS-OLD")]
    aliases = [
        _alias(
            "OLD",
            security_id=master[0]["security_id"],
            valid_from="2000-01-01",
            valid_to="2006-01-03",
        ),
        _alias(
            "NEW",
            security_id=master[0]["security_id"],
            valid_from="2006-01-03",
            valid_to=None,
        ),
    ]

    old = audit.audit_identity_rows(
        [_source("OLD", cik="1234")],
        on=date(2006, 1, 2),
        alias_records=aliases,
        master_records=master,
    )
    new = audit.audit_identity_rows(
        [_source("NEW", cik="1234")],
        on=date(2006, 1, 3),
        alias_records=aliases,
        master_records=master,
    )

    assert old["counts"][audit.STATUS_RESOLVED] == 1
    assert new["counts"][audit.STATUS_RESOLVED] == 1


def test_pagination_follows_only_safe_next_url_and_reports_complete():
    calls = []

    def fetcher(path, params):
        calls.append((path, dict(params or {})))
        if len(calls) == 1:
            return {
                "status": "OK",
                "results": [_source("A", cik="1")],
                "next_url": (
                    "https://api.massive.com/v3/reference/tickers?"
                    "cursor=opaque123&limit=1000"
                ),
            }
        return {
            "status": "OK",
            "results": [_source("B", cik="2")],
        }

    rows, receipt = audit.fetch_pit_common_stock_rows(
        fetcher,
        on=ASOF,
        max_pages=2,
    )

    assert [r["ticker"] for r in rows] == ["A", "B"]
    assert receipt["pages_fetched"] == 2
    assert receipt["row_count"] == 2
    assert receipt["complete"] is True
    assert calls[1] == (
        "/v3/reference/tickers",
        {"cursor": "opaque123", "limit": "1000"},
    )


def test_page_ceiling_marks_population_incomplete_not_complete():
    def fetcher(path, params):
        return {
            "status": "OK",
            "results": [_source("A", cik="1")],
            "next_url": "https://api.massive.com/v3/reference/tickers?cursor=more",
        }

    _, receipt = audit.fetch_pit_common_stock_rows(
        fetcher,
        on=ASOF,
        max_pages=1,
    )

    assert receipt["complete"] is False
    assert receipt["truncated_by_max_pages"] is True


@pytest.mark.parametrize(
    "url",
    [
        "http://api.massive.com/v3/reference/tickers?cursor=x",
        "https://evil.example/v3/reference/tickers?cursor=x",
        "https://api.massive.com/v3/reference/tickers?apiKey=SECRET",
        "https://api.massive.com/v3/reference/tickers?token=SECRET",
    ],
)
def test_pagination_refuses_untrusted_or_credential_bearing_urls(url):
    with pytest.raises(audit.AuditError):
        audit._next_request(url)


def test_receipt_never_calls_current_cik_match_canonical_identity():
    source = [_source("ABC", cik="1234")]
    master = [_master("ABC", cik="1234")]
    receipt = audit.build_receipt(
        on=ASOF,
        source_rows=source,
        source_receipt={
            "pages_fetched": 1,
            "row_count": 1,
            "complete": True,
            "truncated_by_max_pages": False,
        },
        alias_records=[],
        master_records=master,
        canonical_vendor="massive",
    )

    assert receipt["source"]["complete"] is True
    assert receipt["identity"]["canonical_identity_ready"] is False
    assert receipt["authority"]["source_population_canonical"] is True
    assert receipt["authority"]["canonical_identity_ready"] is False
    assert all(
        receipt["authority"][key] is False
        for key in ("may_write_identity", "may_train", "may_rank", "may_size", "may_trade")
    )


def test_receipt_is_json_serializable_and_examples_are_bounded():
    rows = [_source(f"A{i}", cik=str(i + 1)) for i in range(20)]
    receipt = audit.build_receipt(
        on=ASOF,
        source_rows=rows,
        source_receipt={"complete": True, "row_count": len(rows)},
        alias_records=[],
        master_records=[],
        canonical_vendor="massive",
    )
    blob = json_dumps(receipt)
    assert "market_experience.massive_pit_universe_audit.v1" in blob
    assert (
        len(
            receipt["identity"]["examples"][
                audit.STATUS_MISSING_CANONICAL_ALIAS
            ]
        )
        == audit.MAX_EXAMPLES_PER_STATUS
    )


def json_dumps(value) -> str:
    # Local wrapper keeps the test explicit about serialization without importing
    # production helpers that could hide a non-JSON type.
    import json

    return json.dumps(value, sort_keys=True)
