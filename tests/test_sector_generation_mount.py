"""Actual app mount + incumbent private reader; no live service or account."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app import main as macro_main
from app.sector_generation_reader import SectorGenerationReader, configure_sector_generation_reader
from scripts import vps_live_orchestrator as publisher
from tests.test_sector_generation_reader import bundle, gates, _publish, PUBLISHED, SOURCE


def test_unconfigured_actual_app_keeps_route_and_gates_before_unavailable(monkeypatch):
    monkeypatch.setattr(macro_main.app.state, "sector_generation_reader", None, raising=False)
    client = TestClient(macro_main.app)
    denied = client.get("/api/sector-generation")
    assert denied.status_code == 401
    response = client.get("/api/sector-generation", cookies={"sb-fixture-auth-token": "fixture"})
    assert response.status_code == 503
    assert response.json()["code"] == "SECTOR_GENERATION_UNAVAILABLE"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Cookie"


@pytest.mark.parametrize("audience", ["preview", "entitled"])
def test_actual_app_serves_one_verified_capture_through_incumbent_gates(tmp_path, monkeypatch, bundle, audience):
    _, published, root = _publish(tmp_path, bundle)
    assert published.status == "published", published.detail
    calls = []
    def captured(**kwargs):
        calls.append(kwargs)
        return publisher.read_selected_generation(**kwargs)
    reader = SectorGenerationReader(generations_root=root, clock=lambda: PUBLISHED, snapshot_reader=captured)
    monkeypatch.setattr(macro_main.app.state, "sector_generation_reader", reader, raising=False)
    response = TestClient(macro_main.app).get("/api/sector-generation?audience=" + audience,
        cookies={"sb-fixture-auth-token": "fixture"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(calls) == 1
    assert body["source_session"] == SOURCE
    assert body["published_at"] == published.published_at
    assert body["qualification"] == "accepted"
    assert body["projection"]["receipt"]["generation_id"] == "g1"
    assert body["projection"]["data"]["audience"] == audience
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Cookie"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "PRIVATE_SOURCE_VALUE" not in response.text


def test_binding_is_explicit_and_does_not_acquire_or_create_a_store(tmp_path, monkeypatch):
    app = FastAPI()
    root = tmp_path / "private-generations"
    def forbidden(*args, **kwargs):
        raise AssertionError("Configuration attempted storage acquisition")
    with monkeypatch.context() as scoped:
        for name in ("read_bytes", "read_text", "mkdir", "resolve"):
            scoped.setattr(Path, name, forbidden)
        assert configure_sector_generation_reader(app, generations_root=None) is False
        assert app.state.sector_generation_reader is None
        assert configure_sector_generation_reader(app, generations_root=str(root)) is True
        assert isinstance(app.state.sector_generation_reader, SectorGenerationReader)
        assert app.state.sector_generation_reader._root == root
    assert not root.exists()


@pytest.mark.parametrize("root", ["", "relative", "/", " /private/state", "/private/state ", "/private/../site", "/bad\x00root"])
def test_invalid_configuration_clears_capability_without_any_fallback(root):
    app = FastAPI()
    app.state.sector_generation_reader = object()
    with pytest.raises(ValueError, match="invalid_sector_generation_root"):
        configure_sector_generation_reader(app, generations_root=root)
    assert app.state.sector_generation_reader is None


def test_actual_app_denial_never_resolves_the_store(tmp_path, monkeypatch):
    calls = []
    reader = SectorGenerationReader(generations_root=tmp_path / "absent",
        snapshot_reader=lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(macro_main.app.state, "sector_generation_reader", reader, raising=False)
    response = TestClient(macro_main.app).get("/api/sector-generation?audience=entitled")
    assert response.status_code == 401
    assert calls == []
    assert not (tmp_path / "absent").exists()
