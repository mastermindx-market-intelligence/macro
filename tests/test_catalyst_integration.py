"""Session 00 security and anonymous-value integration: synthetic fixtures are not live producer receipts."""
import copy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app import catalyst_integration as ci

NOW = datetime(2026, 10, 9, 3, 30, tzinfo=timezone.utc)


def packet():
    return {
        "schema": "catalyst.scan/v1", "schema_version": 1,
        "requested_tickers": ["NVDA", "ZZZZ"], "event_id": "fixture-earnings-20261008",
        "generation": 2, "as_of_utc": "2026-10-09T02:00:00Z",
        "publication_state": "PARTIAL", "coverage_note": "Test-only fixture, not a market-data read",
        "private_body": "DO NOT EXPOSE", "email": "secret@example.org",
        "results": [{
            "ticker": "NVDA", "status": "SUPPORTED", "relationship": "DIRECT", "public_safe": True,
            "relationship_evidence_ids": ["sec-1"], "headline_evidence_ids": ["sec-1"],
            "headline": "Test fixture: filed results available",
            "as_of_utc": "2026-10-09T02:00:00Z", "correction_state": "CORRECTED",
            "what_changed": [{"text": "The fixture records a revised result.", "evidence_ids": ["sec-1"]}],
            "scenarios": [{"case": "BASE", "trigger": "Watch the next company update", "evidence_ids": ["sec-1"]}],
            "invalidators": [{"text": "Another correction invalidates this fixture", "evidence_ids": ["sec-1"]}],
            "sources": [{"source_id": "sec-1", "url": "https://www.sec.gov/edgar/search/",
                         "title": "SEC search (fixture only)", "rights_receipt_id": "test-source-rights-receipt",
                         "display_rights": "ALLOWED", "published_at_utc": "2026-09-30T10:00:00Z"}],
            "dossier_path": "/stocks/NVDA/", "coverage_note": "Example fixture only",
            "internal_score": 0.91, "private_news_body": "DO NOT EXPOSE",
        }, {"ticker": "ZZZZ", "status": "NOT_COVERED", "coverage_note": "Not in the qualified public set",
            "headline": "HIDDEN PRIVATE TEXT", "sources": [{"body": "SECRET"}], "email": "secret@example.org"}],
    }


def reader(tickers, *, event_id=None, now_utc=None):
    assert tickers == ["NVDA", "ZZZZ"]
    return packet()


def test_real_shape_first_value_and_fail_closed_private_fields():
    scan = ci.scan_with_reader(["nvda", "zzzz"], reader=reader, now_utc=NOW)
    assert scan["requested_tickers"] == ["NVDA", "ZZZZ"]
    assert scan["results"][0]["what_changed"][0]["evidence_ids"] == ["sec-1"]
    assert scan["results"][1]["what_changed"] == []
    assert "secret" not in str(scan).lower()
    assert "private" not in str(scan).lower()
    assert "internal_score" not in str(scan)
    assert "Not in the qualified public set" not in str(scan)
    assert "Test-only fixture, not a market-data read" not in str(scan)
    assert scan["generation"] == 2


@pytest.mark.parametrize("mutation", [
    lambda p: p["results"][0]["sources"][0].update(display_rights="UNKNOWN"),
    lambda p: p["results"][0]["sources"][0].pop("rights_receipt_id"),
    lambda p: p["results"][0].update(headline_evidence_ids=["invented-source"]),
    lambda p: p["results"][0]["what_changed"][0].update(evidence_ids=["hallucinated"]),
    lambda p: p["results"][0].update(correction_state="RETRACTED"),
    lambda p: p["results"][0].update(relationship="EVIDENCED_INDIRECT", relationship_evidence_ids=[]),
    lambda p: p["results"][0].update(dossier_path="https://evil.example/steal"),
    lambda p: p.update(as_of_utc="2026-09-01T02:00:00Z"),
    lambda p: p.update(requested_tickers=["NVDA", "AAPL"]),
    lambda p: p["results"][0]["sources"][0].update(url="http://127.0.0.1/private"),
])
def test_claims_rights_clock_and_identity_negative(mutation):
    p = packet()
    mutation(p)
    with pytest.raises(HTTPException) as exc:
        ci.scan_with_reader(["NVDA", "ZZZZ"], reader=lambda *a, **k: p, now_utc=NOW)
    assert exc.value.status_code == 503
    assert "secret" not in str(exc.value.detail).lower()


def test_prevalidate_abuse_and_dedupe_without_calling_producer():
    calls = []
    with pytest.raises(HTTPException) as exc:
        ci.scan_with_reader(["AAPL"] * 11, reader=lambda *a, **k: calls.append(1))
    assert exc.value.status_code == 400 and calls == []
    assert ci.normalize_tickers(["nvda", "NVDA", "brk.b"]) == ["NVDA", "BRK.B"]
    for bad in (["../../root"], ["aapl", "ZZ@X"], [], ["ZZZZZZZZZZZ"]):
        with pytest.raises(HTTPException):
            ci.normalize_tickers(bad)


def test_explicit_optin_and_opaque_attribution_only():
    owner_calls = []
    good = {"email": "reader@example.org", "event_id": "fixture-earnings-20261008", "tickers": ["nvda"],
            "consent": True, "scope": "catalyst_event_updates/v1",
            "attribution": {"utm_source": "newsletter", "utm_medium": "partner_7",
                            "utm_campaign": "earnings", "utm_content": "post-002"}}
    owner = lambda body: (owner_calls.append(body) or {"status": "VERIFICATION_REQUIRED", "public_ref": "opaque_testref_1234"})
    assert ci.optin_with_owner(good, owner=owner) == {"status": "VERIFICATION_REQUIRED", "public_ref": "opaque_testref_1234"}
    assert owner_calls[0]["tickers"] == ["NVDA"]
    assert owner_calls[0]["attribution"]["utm_content"] == "post-002"
    for bad in ({**good, "consent": False}, {**good, "scope": "daily_campaigns"},
                {**good, "attribution": {"utm_content": "https://bad"}}):
        with pytest.raises(HTTPException) as exc:
            ci.optin_with_owner(bad, owner=owner)
        assert exc.value.status_code == 400
    assert len(owner_calls) == 1
    for bad_owner in (lambda x: {"status": "VERIFIED", "public_ref": "opaque_testref_1234"},
                      lambda x: {"status": "VERIFICATION_REQUIRED", "public_ref": "reader@example.org"}):
        with pytest.raises(HTTPException) as exc:
            ci.optin_with_owner(good, owner=bad_owner)
        assert exc.value.status_code == 503


def test_public_http_uses_explicit_switch_and_no_signup(monkeypatch):
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    assert client.get("/api/catalyst").status_code == 503
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setattr(ci, "import_module", lambda path: SimpleNamespace(scan_tickers=reader))
    # Pin time to the test fixture, no fake real-time claim.
    monkeypatch.setattr(ci, "scan_with_reader", lambda tickers, event_id=None: ci.sanitize_public_scan(packet(), ["NVDA", "ZZZZ"], NOW))
    page = client.get("/api/catalyst?tickers=NVDA,ZZZZ")
    assert page.status_code == 200
    assert "The fixture records a revised result" in page.text
    assert "This ticker is not covered" in page.text
    assert "<form" in page.text and "name='email'" not in page.text.lower() and "reader@example.org" not in page.text
    assert "frame-ancestors 'none'" in page.headers["Content-Security-Policy"]
    assert page.headers["Cache-Control"] == "private, no-store"
    assert client.post("/api/catalyst/optin", json={"email": "x@y.com"}).status_code == 503


def test_optin_http_owner_down_never_reports_verified(monkeypatch):
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("CATALYST_OPTIN_ENABLED", "1")
    payload = {"email": "reader@example.org", "tickers": ["NVDA"], "event_id": "fixture-earnings-20261008",
               "consent": True, "scope": "catalyst_event_updates/v1"}
    assert client.post("/api/catalyst/optin", json=payload).status_code == 503
    assert client.post("/api/catalyst/optin", json={**payload, "consent": False}).status_code == 400


def test_anon_rate_limits_and_distinct_lanes():
    ci._reset_rate_limits_for_tests()
    request = SimpleNamespace(headers={"eo-connecting-ip": "198.51.100.42"})
    for t in range(30):
        assert ci._allow_request(request, "scan", now=t / 10)
    assert not ci._allow_request(request, "scan", now=4)
    for t in range(5):
        assert ci._allow_request(request, "optin", now=t)
    assert not ci._allow_request(request, "optin", now=5)
    assert ci._allow_request(request, "scan", now=61)
    assert ci._allow_request(request, "optin", now=3602)
    ci._reset_rate_limits_for_tests()


def test_anon_http_body_caps_and_json_prevalidation(monkeypatch):
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("CATALYST_OPTIN_ENABLED", "1")
    ci._reset_rate_limits_for_tests()
    # The oversized body must be rejected before any producer/consent owner.
    assert client.post("/api/catalyst/scan", json={"tickers": ["NVDA"], "padding": "x" * 9000}).status_code == 413
    assert client.post("/api/catalyst/optin", json={"email": "reader@example.org", "x": "x" * 5000}).status_code == 413
    assert client.post("/api/catalyst/scan", content="{bad", headers={"Content-Type": "application/json"}).status_code == 400
    assert client.post("/api/catalyst/scan", json={"tickers": ["AAPL"] * 11}).status_code == 400
    ci._reset_rate_limits_for_tests()


def test_optin_http_ack_only_verification_required(monkeypatch):
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    monkeypatch.setenv("CATALYST_OPTIN_ENABLED", "1")
    ci._reset_rate_limits_for_tests()
    monkeypatch.setattr(ci, "import_module", lambda name: SimpleNamespace(
        request_optin=lambda body: {"status": "VERIFICATION_REQUIRED", "public_ref": "opaque_123456789"}
    ))
    payload = {"email": "reader@example.org", "tickers": ["NVDA"],
               "event_id": "fixture-earnings-20261008", "scope": "catalyst_event_updates/v1",
               "consent": True, "attribution": {"utm_content": "post-002"}}
    res = client.post("/api/catalyst/optin", json=payload)
    assert res.status_code == 202
    assert res.json() == {"status": "VERIFICATION_REQUIRED", "public_ref": "opaque_123456789"}
    assert "reader@" not in res.text
    ci._reset_rate_limits_for_tests()


def test_trusted_peer_limits_spoofed_ip_rotation(monkeypatch):
    ci._reset_rate_limits_for_tests()
    monkeypatch.setitem(ci._PEER_LIMITS, "scan", 3)
    for count in range(3):
        request = SimpleNamespace(headers={
            "eo-connecting-ip": f"203.0.113.{count + 10}",
            "x-mm-peer": "198.51.100.99",
        })
        assert ci._allow_request(request, "scan", now=count)
    another_ip_same_peer = SimpleNamespace(headers={
        "eo-connecting-ip": "203.0.113.40",
        "x-mm-peer": "198.51.100.99",
    })
    assert not ci._allow_request(another_ip_same_peer, "scan", now=4)
    ci._reset_rate_limits_for_tests()
