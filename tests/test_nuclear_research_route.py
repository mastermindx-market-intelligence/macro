"""Production-route rights and privacy proof for the Nuclear vertical."""

from __future__ import annotations

import dataclasses

import pytest

pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.earnings as earnings_api
import app.theme_research as theme_research
from engine.market_ontology import nuclear_theme_research as nuclear
from engine.market_ontology.theme_research_registry import (
    VerticalRegistration, registration_for as real_registration_for,
)
from tests.nuclear_research_helpers import N04, X02, nuclear_bundle


def nuclear_registration():
    def load_bundle(query, *, rights_snapshot=None):
        return nuclear_bundle(N04, X02)

    return VerticalRegistration(
        anchor_theme_id=nuclear.ANCHOR_THEME_ID,
        slice_keys=nuclear.SLICES,
        schema_id=nuclear.SCHEMA_ID,
        evidence_schema_id=nuclear.EVIDENCE_SCHEMA_ID,
        definition_version=nuclear.DEFINITION_VERSION,
        compose=nuclear.compose_nuclear_research,
        select_evidence=nuclear.select_authorized_evidence,
        load_bundle=load_bundle,
        title_en="Nuclear value capture",
        title_zh="核电价值捕获",
        note_en="This module reports public evidence without entry authority.",
        note_zh="该模块报告公开证据，不提供入场授权。",
    )


def client(monkeypatch, registration=None):
    app = FastAPI()
    app.include_router(theme_research.router)
    app.dependency_overrides[earnings_api.require_site_full_user] = lambda: {
        "id": "paid-user", "tier": "essential"}

    def registration_for(anchor):
        if anchor == nuclear.ANCHOR_THEME_ID:
            return registration or nuclear_registration()
        return real_registration_for(anchor)

    monkeypatch.setattr(theme_research, "registration_for", registration_for)
    return TestClient(app, raise_server_exceptions=False)


def test_route_filters_refused_rights_families_before_composition(monkeypatch):
    with client(monkeypatch) as test_client:
        response = test_client.post("/api/themes/v1/research/query", json={
            "anchor_theme_id": "nuclear_power", "slice_key": "nuclear_components",
            "view": "economics", "time_mode": "latest", "source_cutoff": None,
            "recorded_cutoff": None, "offset": 0, "limit": 50,
            "expected_generation": None,
        })
    assert response.status_code == 200, response.text
    assert "private" in response.headers["Cache-Control"]
    assert "no-store" in response.headers["Cache-Control"]
    assert "noindex" in response.headers["X-Robots-Tag"]
    assert "noarchive" in response.headers["X-Robots-Tag"]
    payload = response.json()
    assert "rights_refused_families_hidden" in payload["limitations"]
    assert X02["curation_revision"] not in response.text
    assert N04["curation_revision"] in response.text


def test_error_responses_keep_paid_private_headers(monkeypatch):
    with client(monkeypatch) as test_client:
        response = test_client.post("/api/themes/v1/research/query", json={
            "anchor_theme_id": "nuclear_power", "slice_key": "nuclear_components",
            "view": "unknown_view", "time_mode": "latest", "source_cutoff": None,
            "recorded_cutoff": None, "offset": 0, "limit": 50,
            "expected_generation": None,
        })
    assert response.status_code == 400, response.text
    assert response.json()["detail"]["error"]["code"] == "invalid_request"
    assert "private" in response.headers["Cache-Control"]
    assert "no-store" in response.headers["Cache-Control"]
    assert "noindex" in response.headers["X-Robots-Tag"]
    assert "noarchive" in response.headers["X-Robots-Tag"]


@pytest.mark.parametrize(("reviewed_at", "served"), [("2026-09-20", True), ("", False)])
def test_a_replay_withholds_an_unreadable_review_time_instead_of_failing(
        monkeypatch, reviewed_at, served):
    block = {
        "interpretation_id": "synthetic-interpretation",
        "input_revisions": [N04["curation_revision"]], "freshness": "current",
        "reviewed_at": reviewed_at, "mechanism": "Synthetic demand mechanism.",
        "offset": None, "falsifier": "Synthetic falsifier.",
        "missing_measurement": None,
    }
    bundle = dataclasses.replace(
        nuclear_bundle(N04, X02), interpretation_blocks=(block,))
    registration = dataclasses.replace(
        nuclear_registration(),
        load_bundle=lambda query, *, rights_snapshot=None: bundle)
    with client(monkeypatch, registration) as test_client:
        response = test_client.post("/api/themes/v1/research/query", json={
            "anchor_theme_id": "nuclear_power", "slice_key": "nuclear_components",
            "view": "economics", "time_mode": "system_replay",
            "source_cutoff": "2026-12-31T00:00:00Z", "recorded_cutoff": "2026-12-31",
            "offset": 0, "limit": 50, "expected_generation": None,
        })
    assert response.status_code == 200, response.text
    assert "no-store" in response.headers["Cache-Control"]
    assert "noarchive" in response.headers["X-Robots-Tag"]
    assert ("Synthetic demand mechanism." in response.text) is served
