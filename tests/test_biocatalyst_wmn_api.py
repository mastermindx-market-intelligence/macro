from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import app.biocatalyst as api
from engine.company_intelligence.contracts import canonical_json_sha256
from engine.company_intelligence.events import project_catalyst_event
from tests.test_biocatalyst_wmn_publication import CIK, COMPANY, CUTOFF, _wmn_inputs

NOW = datetime(2026, 8, 1, 15, 0, 4, tzinfo=timezone.utc)
GENERATION = "ctgov_run_abcdef1234567890"


def _projection(inputs, generation_id: str = GENERATION):
    generation = SimpleNamespace(generation_id=generation_id, schema_version="1.9.0")
    return SimpleNamespace(generation=generation, what_matters_next_inputs=inputs)


def _two_event_inputs() -> dict:
    inputs = _wmn_inputs()
    first = inputs["events"][0]
    second = project_catalyst_event(
        company_id=COMPANY,
        issuer_cik=CIK,
        source_namespace="issuer_disclosure",
        native_event_key="doc_2026_08_01#claim/readout_second",
        event_family="issuer_readout_guidance",
        revision_ref="doc_2026_08_01:r1-second",
        revision_is_current=True,
        occurrence="uncorroborated",
        timing=deepcopy(first["timing"]),
        source_available_at="2026-08-01T14:00:00Z",
        observed_at="2026-08-01T14:00:02Z",
        document_refs=["doc_2026_08_01:r1-second"],
        public_evidence=[],
        asset_mentions=[],
        relationship_claims=[],
        generation_cutoff=CUTOFF,
    )
    inputs["events"].append(second)
    inputs["identity_projection"][second["event_id"]] = deepcopy(
        inputs["identity_projection"][first["event_id"]]
    )
    inputs["input_cut"]["members"].append({
        "contract_id": "company_catalyst_event.v1",
        "ref": second["event_id"],
        "sha256": canonical_json_sha256(second),
        "observed_at": second["observed_at"],
        "accepted_at": second["observed_at"],
        "availability": "available",
    })
    inputs["coverage"]["family_states"]["issuer_readout_guidance"]["observed_count"] = 2
    return inputs


@contextmanager
def _app(read_bundle, *, auth=None):
    application = FastAPI()
    application.include_router(api.router)
    application.dependency_overrides[api.require_site_full_user] = auth or (lambda: {"id": "paid"})
    original = api._read_bundle
    api._read_bundle = read_bundle
    try:
        with TestClient(application) as client:
            yield client
    finally:
        api._read_bundle = original


def _private(response) -> None:
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def test_wmn_auth_denies_before_generation_read(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    def deny():
        raise HTTPException(401, "missing credentials", headers=api._PRIVATE_HEADERS)
    def forbidden_read():
        raise AssertionError("generation read must not occur")
    with _app(forbidden_read, auth=deny) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next")
    assert response.status_code == 401
    _private(response)


def test_wmn_old_generation_returns_owner_input_unavailable_without_breaking_trial_projection(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(None), {}
    with _app(read) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next")
    assert calls == 1
    assert response.status_code == 503
    assert response.json() == {"detail": "OWNER_INPUT_UNAVAILABLE"}
    _private(response)


def test_wmn_ready_request_reads_once_and_returns_closed_generation_bound_page(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    calls = 0
    inputs = _wmn_inputs()
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    with _app(read) as client:
        response = client.get("/api/biocatalyst/v1/what-matters-next?q=AMLX&horizon_days=90&limit=50")
    assert calls == 1
    assert response.status_code == 200
    _private(response)
    payload = response.json()
    assert payload["contract_id"] == "biocatalyst_what_matters_next.v1"
    assert payload["generation_id"] == GENERATION
    assert payload["evaluation_cutoff"] == "2026-08-01T15:00:04Z"
    assert payload["anchor_date"] == "2026-08-01"
    assert payload["query"] == {
        "view": "upcoming", "horizon_days": 90, "q": "amlx",
        "event_family": None, "lane": None, "limit": 50,
    }
    assert payload["pagination"] == {"limit": 50, "total": 1, "next_cursor": None}
    assert len(payload["rows"]) == 1
    assert payload["rows"][0]["links"]["stock_research"][0]["href"] == "stock.html?ticker=AMLX"


def test_wmn_invalid_filter_and_malformed_or_foreign_cursor_fail_before_data_io(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    def forbidden_read():
        raise AssertionError("invalid request must not read generation")
    with _app(forbidden_read) as client:
        invalid = client.get("/api/biocatalyst/v1/what-matters-next?view=bogus")
        malformed = client.get("/api/biocatalyst/v1/what-matters-next?cursor=not-a-real-cursor")
        foreign = api._encode_wmn_cursor(
            generation_id=GENERATION,
            query={"view": "upcoming", "horizon_days": 90, "q": None, "event_family": None, "lane": None, "limit": 50},
            evaluation_cutoff="2026-08-01T15:00:04Z",
            anchor_date="2026-08-01",
            last_key={"lane": "ACT_NOW", "upper_date": "2026-09-01", "lower_date": "2026-09-01", "last_material_revision_known_at": None, "event_fact_ref": "evt", "row_key": {"event_fact_ref": "evt", "issuer_id": None}},
            purpose="trial_milestones.v1",
        )
        foreign_response = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={foreign}")
    for response in (invalid, malformed, foreign_response):
        assert response.status_code == 400
        assert response.json() == {"detail": "INVALID_REQUEST"}
        _private(response)


def test_wmn_query_change_and_midnight_rollover_require_reload_before_data_io(monkeypatch) -> None:
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    query = {"view": "upcoming", "horizon_days": 90, "q": None, "event_family": None, "lane": None, "limit": 50}
    cursor = api._encode_wmn_cursor(
        generation_id=GENERATION,
        query=query,
        evaluation_cutoff="2026-08-01T15:00:04Z",
        anchor_date="2026-08-01",
        last_key={"lane": "ACT_NOW", "upper_date": "2026-09-01", "lower_date": "2026-09-01", "last_material_revision_known_at": None, "event_fact_ref": "evt", "row_key": {"event_fact_ref": "evt", "issuer_id": None}},
    )
    def forbidden_read():
        raise AssertionError("reload decision must not read generation")
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    with _app(forbidden_read) as client:
        changed = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={cursor}&q=changed")
    assert changed.status_code == 409
    assert changed.json() == {"detail": "RELOAD_REQUIRED"}

    monkeypatch.setattr(api, "_wmn_now", lambda: datetime(2026, 8, 2, 0, 0, 1, tzinfo=timezone.utc))
    with _app(forbidden_read) as client:
        midnight = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={cursor}")
    assert midnight.status_code == 409
    assert midnight.json() == {"detail": "RELOAD_REQUIRED"}


def test_wmn_generation_change_requires_reload_after_one_pointer_bound_read(monkeypatch) -> None:
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    query = {"view": "upcoming", "horizon_days": 90, "q": None, "event_family": None, "lane": None, "limit": 50}
    cursor = api._encode_wmn_cursor(
        generation_id="ctgov_run_old",
        query=query,
        evaluation_cutoff="2026-08-01T15:00:04Z",
        anchor_date="2026-08-01",
        last_key={"lane": "ACT_NOW", "upper_date": "2026-09-01", "lower_date": "2026-09-01", "last_material_revision_known_at": None, "event_fact_ref": "evt", "row_key": {"event_fact_ref": "evt", "issuer_id": None}},
    )
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(_wmn_inputs(), generation_id=GENERATION), {}
    with _app(read) as client:
        response = client.get(f"/api/biocatalyst/v1/what-matters-next?cursor={cursor}")
    assert calls == 1
    assert response.status_code == 409
    assert response.json() == {"detail": "RELOAD_REQUIRED"}


def test_wmn_cursor_paginates_by_last_complete_stable_key_not_offset(monkeypatch) -> None:
    monkeypatch.setattr(api, "_WMN_CURSOR_PROCESS_KEY", b"k" * 32)
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _two_event_inputs()
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    with _app(read) as client:
        first = client.get("/api/biocatalyst/v1/what-matters-next?limit=1")
        assert first.status_code == 200
        p1 = first.json()
        assert len(p1["rows"]) == 1 and p1["pagination"]["total"] == 2
        assert p1["pagination"]["next_cursor"]
        decoded = api._decode_wmn_cursor(p1["pagination"]["next_cursor"])
        assert "offset" not in decoded
        assert set(decoded["last_key"]) == {"lane", "upper_date", "lower_date", "last_material_revision_known_at", "event_fact_ref", "row_key"}
        second = client.get(f"/api/biocatalyst/v1/what-matters-next?limit=1&cursor={p1['pagination']['next_cursor']}")
        assert second.status_code == 200
        p2 = second.json()
    assert calls == 2
    assert len(p2["rows"]) == 1
    assert p2["pagination"] == {"limit": 1, "total": 2, "next_cursor": None}
    assert p1["rows"][0]["event_fact_ref"] != p2["rows"][0]["event_fact_ref"]


def test_wmn_detail_returns_same_generation_company_event_and_related_rows(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _two_event_inputs()
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    event_id = inputs["events"][0]["event_id"]
    with _app(read) as client:
        response = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": GENERATION, "event_fact_ref": event_id},
        )
    assert calls == 1
    assert response.status_code == 200
    _private(response)
    payload = response.json()
    assert payload["contract_id"] == "biocatalyst_wmn_detail.v1"
    assert payload["generation_id"] == GENERATION
    assert payload["event"]["event_fact_ref"] == event_id
    assert payload["trial"] is None
    assert payload["reason_codes"] == ["non_registry_event"]
    assert len(payload["related_events"]) == 1
    assert payload["related_events"][0]["event_fact_ref"] != event_id


def test_wmn_detail_generation_race_and_absent_event_are_typed(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _wmn_inputs()
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        return _projection(inputs), {}
    with _app(read) as client:
        race = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": "ctgov_run_old", "event_fact_ref": inputs["events"][0]["event_id"]},
        )
        missing = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": GENERATION, "event_fact_ref": "evt_source_" + "f" * 64},
        )
    assert calls == 2
    assert race.status_code == 409 and race.json() == {"detail": "RELOAD_REQUIRED"}
    assert missing.status_code == 404 and missing.json() == {"detail": "EVENT_NOT_IN_GENERATION"}
    _private(race); _private(missing)


def test_wmn_detail_invalid_request_and_auth_fail_before_generation_read(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    def forbidden_read():
        raise AssertionError("must not read generation")
    with _app(forbidden_read) as client:
        invalid = client.get("/api/biocatalyst/v1/what-matters-next/detail")
    assert invalid.status_code == 400
    assert invalid.json() == {"detail": "INVALID_REQUEST"}

    def deny():
        raise HTTPException(401, "missing credentials", headers=api._PRIVATE_HEADERS)
    with _app(forbidden_read, auth=deny) as client:
        denied = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={"generation_id": GENERATION, "event_fact_ref": "evt_source_" + "a" * 64},
        )
    assert denied.status_code == 401
    _private(denied)


def _registry_projection(inputs):
    fixture = Path(__file__).resolve().parents[1] / "data/biocatalyst/fixtures/clinicaltrials/trial_snapshot.v1.valid.json"
    snapshot = json.loads(fixture.read_text(encoding="utf-8"))
    generation = SimpleNamespace(generation_id=GENERATION, schema_version="1.9.0")
    return SimpleNamespace(
        generation=generation,
        what_matters_next_inputs=inputs,
        trials=(snapshot,),
        history_models_by_nct={},
        change_tapes_by_nct={},
    )


def test_wmn_registry_milestone_is_same_generation_reconcile_row_and_detail(monkeypatch) -> None:
    monkeypatch.setattr(api, "_wmn_now", lambda: NOW)
    inputs = _wmn_inputs()
    calls = 0

    def read():
        nonlocal calls
        calls += 1
        return _registry_projection(inputs), {}

    with _app(read) as client:
        page = client.get(
            "/api/biocatalyst/v1/what-matters-next",
            params={"view": "reconcile", "event_family": "registry_primary_completion"},
        )
        assert page.status_code == 200
        payload = page.json()
        registry_rows = [
            row for row in payload["rows"]
            if row["event_family"] == "registry_primary_completion"
        ]
        assert len(registry_rows) == 1
        row = registry_rows[0]
        assert row["event_fact_ref"] == "nct:NCT00000001:primary_completion"
        assert row["event_revision_ref"] == "trial_snapshot_NCT00000001_after"
        assert row["occurrence"] == "uncorroborated"
        assert row["timing"]["source_class"] == "registry_schedule"
        assert row["issuer"]["state"] == "unresolved"
        assert row["links"]["stock_research"] == []
        assert row["research_priority"]["lane"] == "RECONCILE"
        assert payload["coverage"]["family_states"]["registry_primary_completion"]["state"] == "supported"

        detail = client.get(
            "/api/biocatalyst/v1/what-matters-next/detail",
            params={
                "generation_id": GENERATION,
                "event_fact_ref": row["event_fact_ref"],
            },
        )
    assert calls == 2
    assert detail.status_code == 200
    _private(page)
    _private(detail)
    dossier = detail.json()
    assert dossier["event"]["event_fact_ref"] == row["event_fact_ref"]
    assert dossier["trial"]["nct_id"] == "NCT00000001"
    assert dossier["trial"]["brief_title"] == "Synthetic Phase 2 Study"
    assert dossier["reason_codes"] == []
