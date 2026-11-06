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
    # The BEA endpoint is permanently paid-gated, even with the global
    # PAYWALL_ENABLED staged off. Keep all tests hermetic with a paid fixture;
    # individual negative tests override this to a free account.
    monkeypatch.setattr(
        paywall, "_store_entitlement",
        lambda uid: ({"tier": "essential", "status": "active",
                      "features": ["site_full"]}, True),
    )
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


def test_gmi_bea_paid_gate_is_always_enforced_even_when_global_wall_off(monkeypatch):
    monkeypatch.delenv("PAYWALL_ENABLED", raising=False)
    monkeypatch.setattr(
        paywall, "_store_entitlement",
        lambda uid: ({"tier": "free", "status": "none", "features": []}, True),
    )
    paywall._ENT_CACHE.clear()
    response = client.get("/api/gmi/bea/industry/5241X")
    assert response.status_code == 403
    assert response.json()["detail"]["required_feature"] == "site_full"
    assert response.headers.get("cache-control") == "private, no-store"
    assert "SOURCE_UNREGISTERED" not in response.text


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


def test_gmi_bea_registry_exception_coarsens_private_path(monkeypatch, caplog):
    def unavailable_registry():
        raise OSError("secret-data-root/on-private-disk")
    monkeypatch.setattr("lib.dataos.registry.load_registry", unavailable_registry)
    r = client.get("/api/gmi/bea/industry/5241X")
    assert r.status_code == 503
    assert r.json()["detail"] == {"error": "BEA_SOURCE_REGISTRY_UNAVAILABLE"}
    assert "secret-data-root" not in r.text
    assert r.headers.get("cache-control") == "private, no-store"
    # Operators receive a bounded cause *type*, never private original path.
    assert "gmi BEA native source refusal" in caplog.text
    assert "OSError" in caplog.text
    assert "secret-data-root" not in caplog.text


def test_gmi_bea_current_route_rejects_historical_or_unknown_queries_before_registry(monkeypatch):
    def forbidden_source_read():
        raise AssertionError("historical/unsupported query accessed Data OS registry")
    monkeypatch.setattr("lib.dataos.registry.load_registry", forbidden_source_read)
    for query in (
        "?known_at=2018-01-01", "?as_of=2019-09-01",
        "?year=2021", "?edition=2026-05-21", "?format=csv",
        "?asof=2020-01-01&known_at=2020-01-02",
        "?unexpected_private_key=1",
    ):
        response = client.get("/api/gmi/bea/industry/5241X" + query)
        assert response.status_code == 422, (query, response.status_code, response.text)
        assert response.headers.get("cache-control") == "private, no-store"
        assert "source_generation_id" not in response.text


def test_gmi_bea_internal_packet_refusal_is_not_misreported_as_client_422(monkeypatch):
    from lib.dataos.registry import Registry
    from engine.market_ontology import bea_gvc_current as gmi

    def refused_packet(_packet):
        raise gmi.BEADescriptiveRefused("private-source-invalid")

    monkeypatch.setattr("lib.dataos.registry.load_registry", lambda: Registry(()))
    monkeypatch.setattr(gmi, "candidate_packet_bytes", refused_packet)
    response = client.get("/api/gmi/bea/industry/5241X")
    assert response.status_code == 503
    assert response.json()["detail"] == {"error": "BEA_SOURCE_REGISTRY_UNAVAILABLE"}
    assert "private-source-invalid" not in response.text
    assert response.headers.get("cache-control") == "private, no-store"


def test_gmi_bea_paid_human_view_uses_same_source_api_and_no_cache():
    response = client.get("/api/gmi/bea/industry/5241X/view")
    assert response.status_code == 200
    assert response.headers.get("cache-control") == "private, no-store"
    assert response.headers.get("content-type", "").startswith("text/html")
    assert "default-src 'none'" in response.headers.get("content-security-policy", "")
    assert '<script src="/api/gmi/bea/assets/view.js"></script>' in response.text
    assert 'id="bea-gvc-root"' in response.text
    assert 'id="bea-year-name"' in response.text
    assert "Source status not checked" in response.text
    assert "2026" in response.text
    assert "observed company" in response.text


def test_gmi_bea_human_view_refuses_unauthorized_or_invalid_requests(monkeypatch):
    app.dependency_overrides.pop(require_user, None)
    assert client.get("/api/gmi/bea/industry/5241X/view").status_code == 401
    app.dependency_overrides[require_user] = lambda: {"id": UID, "email": "u@example.test"}
    monkeypatch.setattr(
        paywall, "_store_entitlement",
        lambda uid: ({"tier": "free", "status": "none", "features": []}, True),
    )
    paywall._ENT_CACHE.clear()
    assert client.get("/api/gmi/bea/industry/5241X/view").status_code == 403
    monkeypatch.setattr(
        paywall, "_store_entitlement",
        lambda uid: ({"tier": "essential", "status": "active",
                      "features": ["site_full"]}, True),
    )
    paywall._ENT_CACHE.clear()
    assert client.get("/api/gmi/bea/industry/5241X%3Cscript%3E/view").status_code == 422
    assert client.get(
        "/api/gmi/bea/industry/5241X/view?known_at=2019-01-01"
    ).status_code == 422


def test_gmi_bea_human_view_script_is_existing_auth_gated_and_private():
    response = client.get("/api/gmi/bea/assets/view.js")
    assert response.status_code == 200
    assert response.headers.get("cache-control") == "private, no-store"
    assert response.headers.get("content-type", "").startswith("application/javascript")
    assert "encodeURIComponent" in response.text
    assert "innerHTML" not in response.text
    assert "PUBLISHED_CURRENT_DESCRIPTIVE" not in response.text
    assert "CANDIDATE_NOT_PUBLISHED" in response.text
    app.dependency_overrides.pop(require_user, None)
    assert client.get("/api/gmi/bea/assets/view.js").status_code == 401


def test_gmi_bea_human_shell_never_reads_native_registry_or_original_files(monkeypatch):
    def prohibited_registry():
        raise AssertionError("human UI shell must not access native BEA source")
    monkeypatch.setattr("lib.dataos.registry.load_registry", prohibited_registry)
    response = client.get("/api/gmi/bea/industry/5241X/view")
    assert response.status_code == 200
    assert response.headers.get("cache-control") == "private, no-store"
    assert "source_generation_id" not in response.text
    assert "world_import_million_USD" not in response.text


def test_gmi_bea_human_view_missing_asset_fails_closed_without_leaking_path(monkeypatch):
    from pathlib import Path
    def unavailable_static(_path):
        raise OSError("secret-mount/originals/hidden.json")
    monkeypatch.setattr(Path, "read_bytes", unavailable_static)
    response = client.get("/api/gmi/bea/industry/5241X/view")
    assert response.status_code == 503
    assert response.json()["detail"] == {"error": "BEA_HUMAN_VIEW_UNAVAILABLE"}
    assert "secret-mount" not in response.text
    assert response.headers.get("cache-control") == "private, no-store"


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
