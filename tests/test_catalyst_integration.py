"""Session 00 security and anonymous-value integration: synthetic fixtures are not live producer receipts."""
import copy
import json
from pathlib import Path
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
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/search?email=visitor%40example.org"),
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/search?ref=visitor%40example.org&doc=10k"),
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/Archives/visitor%2540example.org/filing"),
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/search?q=filing#visitor@example.org"),
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/Archives/filing?signature=not-public"),
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/Archives/filing#token=hidden-value"),
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/Archives/filing?ref=ok%26token%3Dsecret"),
    lambda p: p["results"][0]["sources"][0].update(url="https://www.sec.gov/Archives/filing?ref=ok%250Aevil"),
    lambda p: p["results"][0]["sources"].append(copy.deepcopy(p["results"][0]["sources"][0])),
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
    assert client.post("/api/catalyst/optin", json={"email": "x@y.com"}).status_code == 404



def test_public_source_query_without_identity_remains_citable():
    p = packet()
    safe_url = "https://www.sec.gov/Archives/edgar/data/123/10-K?ref=0001&lang=en"
    p["results"][0]["sources"][0]["url"] = safe_url
    public = ci.sanitize_public_scan(p, ["NVDA", "ZZZZ"], now_utc=NOW)
    assert public["results"][0]["sources"][0]["url"] == safe_url


def test_first_value_html_shows_public_evidence_clocks_and_falsifiers():
    data = ci.sanitize_public_scan(packet(), ["NVDA", "ZZZZ"], now_utc=NOW)
    page = ci.render_first_value(data, "NVDA,ZZZZ")
    assert "<h4>What changed</h4>" in page
    assert "The fixture records a revised result" in page
    assert "Conditional scenarios, not predictions" in page
    assert "BASE: Watch the next company update" in page
    assert "What could invalidate this reading" in page
    assert "Another correction invalidates this fixture" in page
    assert 'datetime="2026-10-09T02:00:00Z"' in page
    assert 'datetime="2026-09-30T10:00:00Z"' in page
    assert "Correction state: CORRECTED" in page
    assert "Relationship: DIRECT" in page
    assert "This ticker is not covered" in page
    assert "No account required" in page
    assert "name='email'" not in page.lower()


def test_first_value_html_escapes_untrusted_headline_claims_and_source_title():
    p = packet()
    p["results"][0]["headline"] = '<script>alert("source")</script>'
    p["results"][0]["what_changed"][0]["text"] = '<img src=x onerror=alert(1)>'
    p["results"][0]["sources"][0]["title"] = '<svg onload="alert(1)">'
    data = ci.sanitize_public_scan(p, ["NVDA", "ZZZZ"], now_utc=NOW)
    page = ci.render_first_value(data)
    assert '<script>alert("source")</script>' not in page
    assert '<img src=x onerror=alert(1)>' not in page
    assert '<svg onload="alert(1)">' not in page
    assert "&lt;script&gt;" in page
    assert "&lt;img" in page
    assert "&lt;svg" in page



def test_anon_rate_limits():
    ci._reset_rate_limits_for_tests()
    request = SimpleNamespace(headers={"eo-connecting-ip": "198.51.100.42"})
    for t in range(30):
        assert ci._allow_request(request, "scan", now=t / 10)
    assert not ci._allow_request(request, "scan", now=4)
    assert ci._allow_request(request, "scan", now=61)
    ci._reset_rate_limits_for_tests()


def test_anon_http_body_caps_and_json_prevalidation(monkeypatch):
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    ci._reset_rate_limits_for_tests()
    # The oversized body must be rejected before any producer/consent owner.
    assert client.post("/api/catalyst/scan", json={"tickers": ["NVDA"], "padding": "x" * 9000}).status_code == 413
    # Insecure legacy direct submission was removed in favor of Session 02 OTP.
    assert client.post("/api/catalyst/optin", json={"email": "reader@example.org"}).status_code == 404
    assert client.post("/api/catalyst/scan", content="{bad", headers={"Content-Type": "application/json"}).status_code == 400
    assert client.post("/api/catalyst/scan", json={"tickers": ["AAPL"] * 11}).status_code == 400
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


def test_frozen_json_contract_fixture():
    """Sibling producers can target this exact on-disk schema, never real prices."""
    fixture_path = Path(__file__).parent / "fixtures" / "catalyst_scan_contract_v1.json"
    fixture = json.loads(fixture_path.read_text())
    assert fixture["_fixture_warning"].startswith("SYNTHETIC")
    result = ci.sanitize_public_scan(fixture, ["NVDA", "ZZZZ"], now_utc=NOW)
    assert result["event_id"] == "fixture-earnings-20261008"
    assert result["generation"] == 2
    assert result["results"][0]["headline_evidence_ids"] == ["fixture-source-1"]
    assert result["results"][1]["status"] == "NOT_COVERED"
    assert result["coverage_note"] != fixture["coverage_note"]
    assert "_fixture_warning" not in result


def test_public_json_issues_scan_proof_only_after_qualified_result(monkeypatch):
    """Contract bridge gives first value even without a receipt key."""
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    ci._reset_rate_limits_for_tests()
    monkeypatch.setenv("CATALYST_PUBLIC_ENABLED", "1")
    current = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def current_fixture(tickers, event_id=None):
        tickers = ci.normalize_tickers(tickers)
        p = packet()
        p["as_of_utc"] = current
        p["results"][0]["as_of_utc"] = current
        p["requested_tickers"] = list(tickers)
        p["results"] = [row for row in p["results"] if row["ticker"] in tickers]
        return ci.sanitize_public_scan(p, list(tickers))

    monkeypatch.setattr(ci, "scan_with_reader", current_fixture)
    monkeypatch.delenv("CATALYST_SCAN_RECEIPT_SECRET", raising=False)
    no_secret = client.get("/api/catalyst/scan?tickers=NVDA,ZZZZ")
    assert no_secret.status_code == 200
    assert "scan_receipt" not in no_secret.json()
    assert no_secret.json()["results"][0]["status"] == "SUPPORTED"

    monkeypatch.setenv("CATALYST_SCAN_RECEIPT_SECRET", "t" * 40)
    eligible = client.post("/api/catalyst/scan", json={"tickers": ["NVDA", "ZZZZ"]})
    assert eligible.status_code == 200
    assert eligible.json()["scan_receipt"].count(".") == 1
    assert eligible.json()["results"][1]["status"] == "NOT_COVERED"
    assert "email" not in eligible.text.lower()
    ci._reset_rate_limits_for_tests()

def test_public_dossier_deep_link_rewrites_legacy_one_ticker_path():
    """Macro's actual site builder publishes /stocks/TICKER.html, not /TICKER/."""
    p = packet()
    legacy = ci.sanitize_public_scan(p, ["NVDA", "ZZZZ"], now_utc=NOW)
    assert legacy["results"][0]["dossier_path"] == "/stocks/NVDA.html"
    html_page = ci.render_first_value(legacy, "NVDA,ZZZZ")
    assert 'href="/stocks/NVDA.html"' in html_page
    assert 'href="/stocks/NVDA/"' not in html_page

    p["results"][0]["dossier_path"] = "/stocks/NVDA.html"
    canonical = ci.sanitize_public_scan(p, ["NVDA", "ZZZZ"], now_utc=NOW)
    assert canonical["results"][0]["dossier_path"] == "/stocks/NVDA.html"


@pytest.mark.parametrize("bad", [
    "/stocks/NVDA/index.html", "/stocks/nvda.html",
    "/stocks/AMD.html", "/stocks/NVDA/../AMD.html",
    "//evil.example/stocks/NVDA.html",
    "https://evil.example/stocks/NVDA.html", "/stocks/NVDA.html?token=secret",
])
def test_public_dossier_denies_untrusted_paths(bad):
    p = packet()
    p["results"][0]["dossier_path"] = bad
    with pytest.raises(HTTPException) as err:
        ci.scan_with_reader(["NVDA", "ZZZZ"], reader=lambda *args, **kwargs: p, now_utc=NOW)
    assert err.value.status_code == 503


def test_obsolete_unsafe_optin_path_not_mounted():
    app = FastAPI()
    app.include_router(ci.router)
    client = TestClient(app)
    assert client.post("/api/catalyst/optin", json={"email": "reader@example.com"}).status_code == 404
