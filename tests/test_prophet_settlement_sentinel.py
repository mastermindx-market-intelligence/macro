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


def test_green_read_without_bundle_evidence_stays_pending_typed():
    """MUTATION PIN (the reproduced false green, at the read model).  A fully
    green read — owed session fresh, receipt digest bound to the exact served
    bytes, qualified reader and compute clocks, clean vintage flags — used to
    read SETTLED with ``artifact_hashes`` null, because the read model binds
    no §18.2 full-bundle evidence.  Fail closed: the verdict is PENDING and
    the typed missing-evidence codes name exactly what the acceptance side
    (source-issued accepted bundle reference + reader served identity) must
    inject before SETTLED is reachable.  Nothing here is production proof."""
    raw = _served("2026-10-30")
    report = _measure(raw, health=_health(raw, asof="2026-10-30"))
    assert report["status"] == "PENDING"
    assert "artifact_hashes_missing" in report["failures"]
    assert "accepted_bundle_missing" in report["failures"]
    assert "reader_proof_missing" in report["failures"]
    assert report["artifact_hashes"] is None
    assert "PAID-PRIVATE-PLAN" not in json.dumps(report)


def test_public_report_projects_only_allowlisted_health_metadata():
    private = {
        "generated_at": NOW.isoformat(),
        "surfaces": {"prophet_us": {"status": "stale", "facts": {"ticker": "PRIVATE"}}},
        "prophet_settlement": {
            "schema": "prophet.settlement_manifest/v1",
            "status": "UNAVAILABLE_DATA",
            "source_asof": "2026-10-23",
            "owed_session": "2026-10-30",
            "failures": ["source_asof_stale", "/etc/secret", "x" * 900],
            "plans": [{"ticker": "PRIVATE"}],
            "artifact_hashes": {"customer": "secret-hash"},
            "private": "SECRET",
        },
    }
    public = fs.public_report(private)
    assert set(public["prophet_settlement"]) == {
        "schema", "status", "source_asof", "owed_session", "failures"
    }
    assert public["prophet_settlement"]["failures"] == ["source_asof_stale"]
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


def test_public_report_never_erases_settled_failures_into_false_green():
    """The public allowlist must not turn malformed or future failure codes
    into an empty list while preserving a supplied SETTLED claim.

    The normal pure manifest emits a closed failures list; this mutation
    pins the public boundary against missing, mixed or future-shaped
    internal evidence without treating synthetic fixtures as production.
    """
    failures_cases = (
        None,
        "source_asof_stale",
        {"reason": "source_asof_stale"},
        ["source_asof_stale"],
        ["SOURCE_FUTURE_UNKNOWN_SECRET"],
        ["source_asof_stale", "SOURCE_FUTURE_UNKNOWN_SECRET"],
        [None],
        [42],
    )
    for failures in failures_cases:
        private = {
            "surfaces": {},
            "prophet_settlement": {
                "status": "SETTLED",
                "owed_session": "2026-10-30",
                "source_asof": "2026-10-30",
                "failures": failures,
                "private_plan": "PAID_SECRET_PLAN",
            },
        }
        public = fs.public_report(private)
        block = public["prophet_settlement"]
        assert block["schema"] == "prophet.settlement_manifest/v1"
        assert block["status"] == "UNAVAILABLE_DATA"
        assert set(block) == {
            "schema", "status", "owed_session", "source_asof", "failures"
        }
        assert "PAID_SECRET_PLAN" not in json.dumps(public)
        assert "SOURCE_FUTURE_UNKNOWN_SECRET" not in json.dumps(public)

    omitted = fs.public_report({
        "surfaces": {},
        "prophet_settlement": {
            "status": "SETTLED",
            "owed_session": "2026-10-30",
            "source_asof": "2026-10-30",
        },
    })
    assert omitted["prophet_settlement"]["status"] == "UNAVAILABLE_DATA"


def _complete_settled_fixture():
    """Full synthetic internal projection shape; never a real issuer receipt."""
    return {
        "schema": "prophet.settlement_manifest/v1",
        "status": "SETTLED",
        "owed_session": "2026-10-30",
        "source_asof": "2026-10-30",
        "reader_visible_asof": "2026-10-30",
        "computed_at": "2026-10-30T21:58:41Z",
        "published_at": "2026-10-30T22:05:00Z",
        "checked_at": "2026-10-30T22:11:03Z",
        "checkpoint": "a" * 40,
        "artifact_hashes": {
            "board": "a" * 64,
            "candidate_store": "b" * 64,
            "index": "c" * 64,
            "theme_state": "d" * 64,
        },
        "failures": [],
    }


def test_public_report_retains_only_valid_empty_failures_settled_claim():
    """Only a complete, closed synthetic internal claim retains SETTLED."""
    raw = _complete_settled_fixture()
    public = fs.public_report({"surfaces": {}, "prophet_settlement": raw})
    block = public["prophet_settlement"]
    assert block == {
        "schema": "prophet.settlement_manifest/v1",
        "status": "SETTLED",
        "owed_session": "2026-10-30",
        "source_asof": "2026-10-30",
        "failures": [],
    }
    assert "a" * 64 not in json.dumps(public)
    assert "b" * 64 not in json.dumps(public)


def test_public_boundary_rejects_non_dict_and_unknown_top_level_secrets():
    """Public status is default-deny even for synthetic malformed top-level
    and settlement values; no plan, token or path may leak."""
    for raw in (
        [{"plan": "PAID_PRIVATE_PLAN", "path": "/etc/secret"}],
        "PRIVATE_TOKEN",
        None,
        42,
    ):
        doc = fs.public_report({
            "generated_at": NOW.isoformat(),
            "surfaces": {},
            "secret_top_level": "PAID_TOP_SECRET",
            "prophet_settlement": raw,
        })
        assert doc["prophet_settlement"] == {
            "schema": "prophet.settlement_manifest/v1",
            "status": "UNAVAILABLE_DATA",
            "owed_session": None, "source_asof": None, "failures": [],
        }
        blob = json.dumps(doc)
        for bait in ("PAID_PRIVATE_PLAN", "/etc/secret", "PRIVATE_TOKEN", "PAID_TOP_SECRET"):
            assert bait not in blob
    assert "prophet_settlement" not in fs.public_report({"surfaces": {}})


def test_public_boundary_rejects_false_settled_schema_dates_clocks_and_extensions():
    valid = _complete_settled_fixture()
    changed = (
        {"schema": "prophet.settlement_manifest/v2"},
        {"schema": None},
        {"source_asof": "2026-10-30_PRIVATE_TOKEN"},
        {"owed_session": "2026-10-30_PRIVATE_TOKEN"},
        {"computed_at": None},
        {"computed_at": "2099-01-01T00:00:00Z"},
        {"published_at": "2026-09-01T22:05:00Z"},
        {"checked_at": "2026-10-29T21:00:00Z"},
        {"reader_visible_asof": "2099-01-01"},
        {"source_delayed": True},
        {"source_unknown": True},
        {"source_mixed_vintage": True},
        {"private_plan": "PAID_PRIVATE_PLAN"},
        {"artifact_hashes": {"index": "c" * 64}},
    )
    for mutation in changed:
        doc = fs.public_report({
            "surfaces": {},
            "prophet_settlement": dict(valid, **mutation),
            "unknown_top_level": "PAID_TOP_SECRET",
        })
        assert doc["prophet_settlement"]["status"] == "UNAVAILABLE_DATA", mutation
        assert "PAID_PRIVATE_PLAN" not in json.dumps(doc), mutation
        assert "PAID_TOP_SECRET" not in json.dumps(doc), mutation
        assert "_PRIVATE_TOKEN" not in json.dumps(doc), mutation


def test_public_boundary_rejects_fake_empty_failure_list_equality():
    """A list-like comparison or custom equality is not exact [] evidence."""
    from collections import UserList

    class AlwaysEmpty:
        def __eq__(self, other):
            return other == []

    valid = _complete_settled_fixture()
    for bogus in (UserList([]), AlwaysEmpty()):
        doc = fs.public_report({
            "surfaces": {},
            "prophet_settlement": dict(valid, failures=bogus),
        })
        assert doc["prophet_settlement"]["status"] == "UNAVAILABLE_DATA"
        assert doc["prophet_settlement"]["failures"] == []


def test_public_boundary_preserves_incumbent_health_keys_only():
    raw = {
        "generated_at": NOW.isoformat(),
        "ok": True,
        "surfaces": {"prophet_us": {"status": "ok", "facts": {"secret": "PAID_PLAN"}}},
        "heartbeat": {"last_pass_utc": NOW.isoformat()},
        "unknown_private_owner": "PAID_OWNER_SECRET",
    }
    out = fs.public_report(raw)
    assert out["generated_at"] == raw["generated_at"]
    assert out["ok"] is True
    assert out["heartbeat"] == raw["heartbeat"]
    assert out["surfaces"] == {"prophet_us": {"status": "ok"}}
    assert "unknown_private_owner" not in out
