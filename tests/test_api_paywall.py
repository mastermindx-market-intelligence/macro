"""Premium /api surfaces enforce the same site_full authority as static files."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from app import paywall
from app.main import app, require_user

client = TestClient(app)
UID = "11111111-1111-1111-1111-111111111111"


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.delenv("PAYWALL_ENABLED", raising=False)
    paywall._ENT_CACHE.clear()
    app.dependency_overrides[require_user] = lambda: {"id": UID, "email": "u@example.test"}
    yield
    app.dependency_overrides.clear()
    paywall._ENT_CACHE.clear()


def test_gmi_bea_route_requires_real_existing_session_authentication():
    app.dependency_overrides.pop(require_user, None)
    r = client.get("/api/gmi/bea/industry/5241X")
    assert r.status_code == 401
    assert r.headers.get("cache-control") == "private, no-store"


def test_gmi_bea_route_respects_existing_paid_site_gate(monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    monkeypatch.setattr(
        paywall, "_store_entitlement",
        lambda uid: ({"tier": "free", "status": "none", "features": []}, True),
    )
    r = client.get("/api/gmi/bea/industry/5241X")
    assert r.status_code == 403
    assert r.json()["detail"]["required_feature"] == "site_full"
    assert r.headers.get("cache-control") == "private, no-store"


def test_gmi_bea_route_always_returns_source_unavailable_not_unadmitted_rows():
    from engine.market_ontology.bea_gvc_current import candidate_packet_bytes
    r = client.get("/api/gmi/bea/industry/5241X")
    assert r.status_code == 503
    assert r.headers.get("cache-control") == "private, no-store"
    assert r.headers.get("content-type", "").startswith("application/json")
    packet = r.json()
    assert packet["status"] == "UNAVAILABLE"
    assert packet["reason"] in {"SOURCE_UNREGISTERED", "SOURCE_NOT_PRODUCED"}
    assert packet["annual_descriptive"] == []
    assert packet["source_generation_id"] is None
    assert packet["may_publish"] is False
    assert r.content == candidate_packet_bytes(packet)


def test_gmi_bea_route_rejects_unsafe_source_token_before_any_source_read():
    r = client.get("/api/gmi/bea/industry/5241X%3Cbad%3E")
    assert r.status_code == 422
    assert r.headers.get("cache-control") == "private, no-store"


def test_gmi_bea_unsafe_code_refuses_before_canonical_registry_read(monkeypatch):
    def forbidden_source_read():
        raise AssertionError("unsafe code attempted to read the registry")
    monkeypatch.setattr("lib.dataos.registry.load_registry", forbidden_source_read)
    r = client.get("/api/gmi/bea/industry/5241X%3Cbad%3E")
    assert r.status_code == 422
    assert r.headers.get("cache-control") == "private, no-store"


def test_gmi_bea_claimed_produced_metadata_does_not_enable_unbound_rows(monkeypatch):
    from engine.market_ontology import bea_gvc_current as gmi
    # Only for the fixture: imagine a source contract has passed. No owner
    # original bytes or authenticated generation is provided to the handler.
    monkeypatch.setattr(gmi, "_source_gate", lambda registry: None)
    r = client.get("/api/gmi/bea/industry/5241X")
    assert r.status_code == 503
    body = r.json()
    assert body["reason"] == "OWNER_VIEW_BYTES_MISSING_OR_OVERSIZED"
    assert body["may_publish"] is False
    assert body["annual_descriptive"] == []


def test_gmi_bea_registry_exception_coarsens_private_path(monkeypatch):
    def unavailable_registry():
        raise OSError("secret-data-root/on-private-disk")
    monkeypatch.setattr("lib.dataos.registry.load_registry", unavailable_registry)
    r = client.get("/api/gmi/bea/industry/5241X")
    assert r.status_code == 503
    assert r.json()["detail"] == {"error": "BEA_SOURCE_REGISTRY_UNAVAILABLE"}
    assert "secret-data-root" not in r.text
    assert r.headers.get("cache-control") == "private, no-store"


def test_ask_keeps_registered_behavior_while_paid_switch_off(monkeypatch):
    monkeypatch.setattr(
        "engine.neuralweb.ask_brain.ask",
        lambda **kwargs: {"ok": True, "mode": "test"},
    )
    r = client.post("/api/ask", json={"question": "What is the current regime?"})
    assert r.status_code == 200
    assert r.json()["mode"] == "test"


def test_ask_refuses_user_without_site_full_when_armed(monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    monkeypatch.setattr(
        paywall,
        "_store_entitlement",
        lambda uid: ({"tier": "free", "status": "none", "features": []}, True),
    )
    r = client.post("/api/ask", json={"question": "Show the neural web state"})
    assert r.status_code == 403
    assert r.json()["detail"]["locked"] is True
    assert r.json()["detail"]["required_feature"] == "site_full"


def test_ask_allows_active_site_full_when_armed(monkeypatch):
    monkeypatch.setenv("PAYWALL_ENABLED", "1")
    monkeypatch.setattr(
        paywall,
        "_store_entitlement",
        lambda uid: ({"tier": "essential", "status": "active", "features": ["site_full"]}, True),
    )
    monkeypatch.setattr(
        "engine.neuralweb.ask_brain.ask",
        lambda **kwargs: {"ok": True, "mode": "test"},
    )
    r = client.post("/api/ask", json={"question": "Show the neural web state"})
    assert r.status_code == 200
    assert r.json()["ok"] is True
