# FIF PF-3 server suite: the /api/forensics/health entity_id query parameter.
#
# Production mode answers per-issuer generation headers; the parameter is
# OPTIONAL and its absence keeps the pre-PF-3 AAPL behaviour byte for byte.
# A malformed id never reaches the store (no generation headers, same 200
# body, never a 4xx/5xx, never logged with the raw value). Golden mode never
# emits generation headers, with or without the parameter.
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.forensics as forensics_api

AAPL_ID = "ISS:US-XNAS-AAPL"
MSFT_ID = "ISS:US-XNAS-MSFT"
HEALTH_PATH = "/api/forensics/health"

_HEALTH_BODY = {
    "schema": "fundamental_forensics.health/v1",
    "status": "current",
    "reason_code": "SOURCE_CURRENT",
    "age_seconds": 1,
    "clocks": {"broad_source_at": "2026-10-11T00:00:00Z"},
}

_EXPECTED_PRIVATE_HEADERS = {
    "cache-control": "private, no-store",
    "vary": "Authorization",
    "x-content-type-options": "nosniff",
    "x-robots-tag": "noindex, noarchive",
}


def _assert_private_headers(response) -> None:
    for name, expected in _EXPECTED_PRIVATE_HEADERS.items():
        assert response.headers.get(name) == expected, f"Missing or wrong header {name!r}"


@pytest.fixture
def router_app(monkeypatch) -> FastAPI:
    monkeypatch.setattr(forensics_api, "REPO", "/nonexistent-repo")
    app = FastAPI()
    app.include_router(forensics_api.router)
    app.dependency_overrides[forensics_api.require_site_full_user] = lambda: {"id": "paid-user"}
    return app


class _StoreStub:
    """Records the issuer ids that reach latest_generation_summary's store."""


def _production_summary_stub(monkeypatch, summaries: dict[str, dict | None]):
    """Patch the production module the route imports; record every issuer id."""
    import engine.fundamental_forensics.production_datasets as pds_module

    requested: list[str] = []

    def _build(*_args, **_kwargs):
        return _StoreStub()

    def _summary(_store, issuer_id: str):
        requested.append(issuer_id)
        return summaries.get(issuer_id)

    monkeypatch.setattr(pds_module, "build_production_dataset_store", _build)
    monkeypatch.setattr(pds_module, "latest_generation_summary", _summary)
    return requested


def _msft_summary() -> dict:
    return {
        "dataset_generation_id": "ffprods_" + "1" * 64,
        "admitted_at": "2026-10-12T01:00:00.000000Z",
    }


def _aapl_summary() -> dict:
    return {
        "dataset_generation_id": "ffprods_" + "a" * 64,
        "admitted_at": "2026-10-13T02:00:00.000000Z",
    }


def _get(client: TestClient, query: str | None):
    url = HEALTH_PATH if query is None else f"{HEALTH_PATH}?{query}"
    return client.get(url)


def test_absent_parameter_keeps_the_aapl_summary_byte_for_byte(monkeypatch, router_app):
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, None)
    assert response.status_code == 200
    _assert_private_headers(response)
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert response.headers["x-fif-dataset-generation-id"] == _aapl_summary()["dataset_generation_id"]
    assert response.headers["x-fif-dataset-admitted-at"] == _aapl_summary()["admitted_at"]
    assert response.json() == _HEALTH_BODY
    # The absent parameter asks for exactly the pre-PF-3 issuer.
    assert requested == [AAPL_ID]


def test_matching_id_with_a_pointer_serves_that_issuers_generation(monkeypatch, router_app):
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    requested = _production_summary_stub(
        monkeypatch, {MSFT_ID: _msft_summary(), AAPL_ID: _aapl_summary()}
    )
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    _assert_private_headers(response)
    summary = _msft_summary()
    assert response.headers["x-fif-dataset-generation-id"] == summary["dataset_generation_id"]
    assert response.headers["x-fif-dataset-admitted-at"] == summary["admitted_at"]
    assert requested == [MSFT_ID]
    assert response.json() == _HEALTH_BODY


def test_matching_id_without_a_pointer_has_no_generation_headers(monkeypatch, router_app):
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    # AAPL has a pointer; the asked-for issuer does not.
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, f"entity_id={MSFT_ID}")
    assert response.status_code == 200
    _assert_private_headers(response)
    assert "x-fif-dataset-generation-id" not in response.headers
    assert "x-fif-dataset-admitted-at" not in response.headers
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert response.json() == _HEALTH_BODY
    # The id DID reach the store lookup (a real pointer check), just found none.
    assert requested == [MSFT_ID]


@pytest.mark.parametrize(
    "query",
    [
        "entity_id=../x",
        "entity_id=ISS%3AUS-XNAS-AAPL%2F..%2FB",
        "entity_id=",
        "entity_id=" + "A" * 200,
        "entity_id=iss%3Aus-xnas-aapl",
        "entity_id=ISS%3AUS-XNAS-aapl",
        "entity_id=ISS%3AUS-XNAS-AAPL%0A",
    ],
)
def test_malformed_ids_never_reach_the_store_and_stay_200(monkeypatch, router_app, query):
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        response = _get(client, query)
    assert response.status_code == 200, "a malformed id is never a 4xx/5xx"
    _assert_private_headers(response)
    assert "x-fif-dataset-generation-id" not in response.headers
    assert "x-fif-dataset-admitted-at" not in response.headers
    assert response.headers["x-fif-financial-dataset-mode"] == "production"
    assert response.json() == _HEALTH_BODY
    # Nothing but the private policy and the mode name ever leave the route.
    assert "../" not in response.text
    # The malformed value never reaches the store key path.
    assert requested == []


def test_golden_mode_with_the_parameter_has_no_generation_headers(monkeypatch, router_app):
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.delenv("FIF_FINANCIAL_DATASET_MODE", raising=False)
    requested = _production_summary_stub(monkeypatch, {AAPL_ID: _aapl_summary()})
    with TestClient(router_app, raise_server_exceptions=False) as client:
        absent = _get(client, None)
        present = _get(client, f"entity_id={MSFT_ID}")
    for response in (absent, present):
        assert response.status_code == 200
        _assert_private_headers(response)
        assert response.headers["x-fif-financial-dataset-mode"] == "golden"
        assert "x-fif-dataset-generation-id" not in response.headers
        assert "x-fif-dataset-admitted-at" not in response.headers
    assert absent.json() == present.json() == _HEALTH_BODY
    assert requested == []


def test_the_json_body_is_identical_across_every_case(monkeypatch, router_app):
    monkeypatch.setattr(forensics_api, "evaluate_health", lambda _root, **_kw: dict(_HEALTH_BODY))
    monkeypatch.setenv("FIF_FINANCIAL_DATASET_MODE", "production")
    _production_summary_stub(
        monkeypatch, {AAPL_ID: _aapl_summary(), MSFT_ID: _msft_summary()}
    )
    queries = [
        None,
        f"entity_id={AAPL_ID}",
        f"entity_id={MSFT_ID}",
        "entity_id=ISS%3AUS-XNAS-NOPE",
        "entity_id=../x",
        "entity_id=",
    ]
    bodies = set()
    with TestClient(router_app, raise_server_exceptions=False) as client:
        for query in queries:
            response = _get(client, query)
            assert response.status_code == 200
            bodies.add(response.text)
    assert len(bodies) == 1, "only the generation headers vary, never the body"
