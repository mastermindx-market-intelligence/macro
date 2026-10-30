"""V4-A2 read-only settlement observations through the incumbent sentinel.

These tests enforce that a fresh public publication stamp cannot override a
stale/mismatched user-served Prophet index and that the public staleness file
contains no private plans or unreviewed evidence fields. They introduce no
new alert, publisher, source store or settlement authority.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from scripts import freshness_sentinel as fs


NOW = datetime(2026, 10, 30, 23, 0, 0, tzinfo=timezone.utc)


def _served(asof: str, *, mixed: bool = False, include_computed: bool = True):
    doc = {
        "schema": "prophet.index/v1",
        "source_asof": asof,
        "source_delayed": False,
        "source_unknown": False,
        "source_mixed_vintage": mixed,
        "source_basis": "panel_majority",
        "source_board_sha256": "b" * 64,
        "plans": [{"id": "PAID-PRIVATE-PLAN", "ticker": "PAID-TICKER"}],
    }
    if include_computed:
        doc["computed_at"] = "2026-10-30T22:45:00Z"
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _health(raw: bytes, *, asof: str, stamp="2026-10-30T22:50:00Z", digest=None):
    return fs.FetchResult(
        status=200,
        body=json.dumps({
            "schema": "prophet.public_health/v1",
            "source_asof": asof,
            "published_at": stamp,
            "checkpoint": "a" * 40,
            "index_sha256": digest or hashlib.sha256(raw).hexdigest(),
        }),
    )


def _measure(raw: bytes | None, *, health: fs.FetchResult | None):
    return fs.project_prophet_settlement_from_reads(
        NOW,
        fs.FetchResult(status=200, body=raw.decode("utf-8")) if raw else None,
        health,
    )


def test_fresh_publication_cannot_settle_frozen_source():
    raw = _served("2026-10-23")
    report = _measure(raw, health=_health(raw, asof="2026-10-23"))
    assert report["schema"] == "prophet.settlement_manifest/v1"
    assert report["status"] != "SETTLED"
    assert report["source_asof"] in ("2026-10-23", None)
    assert "PAID-TICKER" not in json.dumps(report)


def test_no_actual_served_read_can_never_settle_even_with_public_receipt():
    raw = _served("2026-10-30")
    report = _measure(None, health=_health(raw, asof="2026-10-30"))
    assert report["status"] != "SETTLED"
    assert "PAID-PRIVATE-PLAN" not in json.dumps(report)


def test_mismatched_served_bytes_cannot_settle_even_with_matching_source_dates():
    raw = _served("2026-10-30")
    report = _measure(raw, health=_health(raw, asof="2026-10-30", digest="0" * 64))
    assert report["status"] != "SETTLED"


def test_invalid_health_body_and_mixed_source_cannot_settle():
    raw = _served("2026-10-30")
    assert _measure(raw, health=fs.FetchResult(status=200, body="<html>oops</html>"))["status"] != "SETTLED"
    mixed = _served("2026-10-30", mixed=True)
    assert _measure(mixed, health=_health(mixed, asof="2026-10-30"))["status"] != "SETTLED"


def test_missing_computed_clock_withholds_settlement():
    raw = _served("2026-10-30", include_computed=False)
    assert _measure(raw, health=_health(raw, asof="2026-10-30"))["status"] != "SETTLED"


def test_public_report_projects_only_allowlisted_health_metadata():
    private = {
        "generated_at": NOW.isoformat(),
        "surfaces": {"prophet_us": {"status": "stale", "facts": {"ticker": "PRIVATE"}}},
        "prophet_settlement": {
            "schema": "prophet.settlement_manifest/v1",
            "status": "UNAVAILABLE_DATA",
            "source_asof": "2026-10-23",
            "owed_session": "2026-10-30",
            "failures": ["SOURCE_STALE", "/etc/secret", "x" * 900],
            "plans": [{"ticker": "PRIVATE"}],
            "artifact_hashes": {"customer": "secret-hash"},
            "private": "SECRET",
        },
    }
    public = fs.public_report(private)
    assert set(public["prophet_settlement"]) == {
        "schema", "status", "source_asof", "owed_session", "failures"
    }
    assert public["prophet_settlement"]["failures"] == ["SOURCE_STALE"]
    assert public["surfaces"]["prophet_us"] == {"status": "stale"}
    assert "PRIVATE" not in json.dumps(public)
    assert "SECRET" not in json.dumps(public)
    assert "SECRET" in json.dumps(private)


def test_untrusted_public_settlement_status_fails_closed():
    public = fs.public_report({
        "surfaces": {},
        "prophet_settlement": {"status": ["SETTLED"], "failures": "oops"},
    })
    assert public["prophet_settlement"]["status"] == "UNAVAILABLE_DATA"
    assert public["prophet_settlement"]["failures"] == []
