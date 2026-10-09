from __future__ import annotations

from datetime import date, datetime

import pytest

from engine.research_vault import subjects
from lib.dataos.identity import AliasRow, VendorAliasTable


def test_source_ticker_is_candidate_not_exact_identity():
    artifact = subjects.discover_candidates(
        report_id="r1",
        source_tickers=["NVDA"],
        title="",
        summary_points=[],
    )
    assert artifact["schema"] == subjects.CANDIDATE_SCHEMA
    assert artifact["authority"] == "candidate_context_only"
    assert artifact["candidates"] == [{
        "symbol": "NVDA",
        "confidence": 1.0,
        "methods": ["source_sidecar"],
        "source_fields": ["source_sidecar"],
    }]
    assert "security_id" not in artifact["candidates"][0]


def test_candidate_discovery_combines_existing_context_resolver_without_copying_text(
        monkeypatch):
    from engine import entity_resolver

    monkeypatch.setattr(
        entity_resolver,
        "resolve_us",
        lambda text: (
            [{"ticker": "NVDA", "confidence": 0.90, "method": "us_alias"}]
            if "NVIDIA" in text else []
        ),
    )
    monkeypatch.setattr(
        entity_resolver,
        "resolve_cn",
        lambda text: (
            [{"ticker": "600519.SS", "confidence": 0.99, "method": "cn_code"}]
            if "600519" in text else []
        ),
    )

    title = "NVIDIA optical networking update"
    summary = ["Demand broadens; 600519 appears only as a fixture."]
    artifact = subjects.discover_candidates(
        report_id="r2",
        source_tickers=["nvda"],
        title=title,
        summary_points=summary,
    )

    assert artifact["candidate_count"] == 2
    nvda = next(row for row in artifact["candidates"] if row["symbol"] == "NVDA")
    assert nvda["confidence"] == 1.0
    assert nvda["methods"] == ["source_sidecar", "entity_resolver:us_alias"]
    assert nvda["source_fields"] == ["source_sidecar", "title"]

    encoded = repr(artifact)
    assert title not in encoded
    assert summary[0] not in encoded


def test_body_scan_is_explicit_opt_in(monkeypatch):
    from engine import entity_resolver

    monkeypatch.setattr(
        entity_resolver,
        "resolve_us",
        lambda text: (
            [{"ticker": "COHR", "confidence": 0.80, "method": "us_token"}]
            if "COHR" in text else []
        ),
    )
    monkeypatch.setattr(entity_resolver, "resolve_cn", lambda _text: [])

    body = "Licensed publisher text mentions COHR deep in the report."
    without = subjects.discover_candidates(
        report_id="r3",
        body=body,
        include_body=False,
    )
    with_body = subjects.discover_candidates(
        report_id="r3",
        body=body,
        include_body=True,
    )

    assert without["candidate_count"] == 0
    assert without["body_scanned"] is False
    assert with_body["candidate_count"] == 1
    assert with_body["body_scanned"] is True
    assert with_body["candidates"][0]["source_fields"] == ["body"]
    assert body not in repr(with_body)


def test_exact_resolution_requires_explicit_dataos_alias_vendor_and_date():
    table = VendorAliasTable([
        AliasRow(
            "membership",
            "MMC",
            "SEC:US-XNYS-MMC",
            None,
            date(2026, 1, 14),
        ),
        AliasRow(
            "membership",
            "MRSH",
            "SEC:US-XNYS-MMC",
            date(2026, 1, 14),
            None,
        ),
    ])
    candidate = subjects.discover_candidates(
        report_id="rename-report",
        source_tickers=["MMC"],
    )

    old = subjects.resolve_candidates(
        candidate,
        aliases=table,
        alias_vendor="membership",
        published_at="2025-12-31T18:00:00Z",
    )
    assert old["resolved_count"] == 1
    assert old["subjects"][0]["security_id"] == "SEC:US-XNYS-MMC"
    assert old["subjects"][0]["resolution_date"] == "2025-12-31"

    new = subjects.resolve_candidates(
        candidate,
        aliases=table,
        alias_vendor="membership",
        published_at="2026-02-01",
    )
    assert new["resolved_count"] == 0
    assert new["subjects"][0]["resolution_state"] == subjects.UNMAPPED
    assert new["subjects"][0]["security_id"] is None


def test_resolution_never_falls_back_to_another_vendor_namespace():
    table = VendorAliasTable([
        AliasRow("store", "NVDA", "SEC:US-XNAS-NVDA"),
    ])
    candidate = subjects.discover_candidates(
        report_id="vendor-bound",
        source_tickers=["NVDA"],
    )

    unresolved = subjects.resolve_candidates(
        candidate,
        aliases=table,
        alias_vendor="membership",
        published_at="2026-10-05",
    )
    assert unresolved["unmapped_count"] == 1
    assert unresolved["subjects"][0]["security_id"] is None

    resolved = subjects.resolve_candidates(
        candidate,
        aliases=table,
        alias_vendor="store",
        published_at="2026-10-05",
    )
    assert resolved["resolved_count"] == 1
    assert resolved["subjects"][0]["security_id"] == "SEC:US-XNAS-NVDA"


def test_resolution_preserves_unmapped_candidates_instead_of_dropping():
    table = VendorAliasTable([])
    candidate = subjects.discover_candidates(
        report_id="unknown",
        source_tickers=["ZZZZ"],
    )
    result = subjects.resolve_candidates(
        candidate,
        aliases=table,
        alias_vendor="membership",
        published_at="2026-10-05",
    )

    assert result["resolved_count"] == 0
    assert result["unmapped_count"] == 1
    assert result["subjects"][0] == {
        "symbol": "ZZZZ",
        "resolution_state": "UNMAPPED",
        "security_id": None,
        "alias_vendor": "membership",
        "resolution_date": "2026-10-05",
        "confidence": 1.0,
        "methods": ["source_sidecar"],
        "source_fields": ["source_sidecar"],
    }


@pytest.mark.parametrize("published_at", ["", "20261005", "not-a-date"])
def test_resolution_refuses_unusable_publication_clock(published_at):
    candidate = subjects.discover_candidates(
        report_id="bad-clock",
        source_tickers=["NVDA"],
    )
    with pytest.raises(ValueError):
        subjects.resolve_candidates(
            candidate,
            aliases=VendorAliasTable([]),
            alias_vendor="membership",
            published_at=published_at,
        )


@pytest.mark.parametrize(
    "published_at",
    [
        "2026-01-14Tnot-a-time",
        "2026-01-14T",
        "2026-01-14T25:00",
        "2026-01-14T10:61",
        "2026-01-14T10:00:61",
        "2026-01-14T10:00:00+24:00",
        "2026-01-14T10:00:00Zjunk",
        "2026-01-14T10:00:00 2026-01-15T10:00:00",
        "2026-01-14T10:00:00+5",
        "2026-01-14T2026-01-14",
    ],
)
def test_resolution_refuses_malformed_publication_timestamp(published_at):
    candidate = subjects.discover_candidates(
        report_id="bad-timestamp",
        source_tickers=["NVDA"],
    )
    with pytest.raises(ValueError):
        subjects.resolve_candidates(
            candidate,
            aliases=VendorAliasTable([]),
            alias_vendor="membership",
            published_at=published_at,
        )


def test_malformed_clock_never_reaches_exact_alias_resolution():
    table = VendorAliasTable([
        AliasRow(
            "membership",
            "MMC",
            "SEC:US-XNYS-MMC",
            None,
            date(2026, 1, 14),
        ),
        AliasRow(
            "membership",
            "MRSH",
            "SEC:US-XNYS-MMC",
            date(2026, 1, 14),
            None,
        ),
    ])
    candidate = subjects.discover_candidates(
        report_id="rename-report",
        source_tickers=["MMC"],
    )
    with pytest.raises(ValueError):
        subjects.resolve_candidates(
            candidate,
            aliases=table,
            alias_vendor="membership",
            published_at="2026-01-14Tnot-a-time",
        )


@pytest.mark.parametrize(
    ("published_at", "expected"),
    [
        ("2026-01-14", date(2026, 1, 14)),
        ("2026-01-14T10", date(2026, 1, 14)),
        ("2026-01-14T10:00:00", date(2026, 1, 14)),
        ("2026-01-14T10:00:00Z", date(2026, 1, 14)),
        ("2026-01-14T10:00:00+05:00", date(2026, 1, 14)),
        ("2026-01-14T10:00:00.123456-05:00", date(2026, 1, 14)),
        ("2026-01-14T23:30:00+14:00", date(2026, 1, 14)),
        ("2026-01-13T23:30:00-12:00", date(2026, 1, 13)),
        (date(2026, 1, 14), date(2026, 1, 14)),
        (datetime(2026, 1, 14, 23, 0), date(2026, 1, 14)),
    ],
)
def test_publication_date_keeps_the_written_date(published_at, expected):
    assert subjects._publication_date(published_at) == expected


def test_publication_date_refuses_basic_form_timestamp():
    with pytest.raises(ValueError):
        subjects._publication_date("20260114T10:00:00")


def test_resolution_refuses_implicit_vendor_choice():
    candidate = subjects.discover_candidates(
        report_id="no-vendor",
        source_tickers=["NVDA"],
    )
    with pytest.raises(ValueError, match="alias_vendor"):
        subjects.resolve_candidates(
            candidate,
            aliases=VendorAliasTable([]),
            alias_vendor="",
            published_at="2026-10-05",
        )


def test_candidate_rows_reject_malformed_shape_before_identity_resolution():
    bad = {
        "schema": subjects.CANDIDATE_SCHEMA,
        "report_id": "r",
        "candidates": [{
            "symbol": "NVDA",
            "confidence": 0.9,
            "methods": ["source_sidecar"],
            "source_fields": ["invented_field"],
        }],
    }
    with pytest.raises(ValueError, match="source_fields"):
        subjects.resolve_candidates(
            bad,
            aliases=VendorAliasTable([]),
            alias_vendor="membership",
            published_at="2026-10-05",
        )


def test_discovery_rejects_string_ticker_iterable():
    with pytest.raises(TypeError, match="source_tickers"):
        subjects.discover_candidates(
            report_id="string-tickers",
            source_tickers="NVDA",
        )


def test_resolution_rejects_forged_blank_report_id():
    candidate = subjects.discover_candidates(
        report_id="real-report",
        source_tickers=["NVDA"],
    )
    candidate["report_id"] = "   "
    with pytest.raises(ValueError, match="report_id"):
        subjects.resolve_candidates(
            candidate,
            aliases=VendorAliasTable([]),
            alias_vendor="membership",
            published_at="2026-10-05",
        )


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -float("inf")])
def test_resolution_rejects_nonfinite_candidate_confidence(confidence):
    candidate = subjects.discover_candidates(
        report_id="finite-confidence",
        source_tickers=["NVDA"],
    )
    candidate["candidates"][0]["confidence"] = confidence
    with pytest.raises(ValueError, match="finite"):
        subjects.resolve_candidates(
            candidate,
            aliases=VendorAliasTable([]),
            alias_vendor="membership",
            published_at="2026-10-05",
        )


def test_resolution_refuses_malformed_dataos_alias_target():
    table = VendorAliasTable([
        AliasRow("exchange", "NVDA", "not-a-security-id"),
    ])
    candidate = subjects.discover_candidates(
        report_id="bad-dataos-target",
        source_tickers=["NVDA"],
    )
    with pytest.raises(ValueError, match="valid security id"):
        subjects.resolve_candidates(
            candidate,
            aliases=table,
            alias_vendor="exchange",
            published_at="2026-10-05",
        )


def test_resolution_refuses_non_security_dataos_alias_target():
    table = VendorAliasTable([
        AliasRow("exchange", "NVDA", "ISS:US-XNAS-NVDA"),
    ])
    candidate = subjects.discover_candidates(
        report_id="issuer-not-security",
        source_tickers=["NVDA"],
    )
    with pytest.raises(ValueError, match="not a security id"):
        subjects.resolve_candidates(
            candidate,
            aliases=table,
            alias_vendor="exchange",
            published_at="2026-10-05",
        )
