"""SBIR source generation -> committed twins -> entitled consumer boundary."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app import government_revenue as api
from engine.government_revenue.sbir_progression import (
    build_sbir_progression_payload,
    is_valid_sbir_progression_payload,
    sbir_progression_content_id,
)
from scripts import build_government_revenue as builder
from engine.government_revenue.workspace import build_procurement_workspace
from tests.test_sbir_awards import OBSERVED, _bundle, _phase_pair


def _payload():
    return {
        "schema_version": "company_government_revenue.v1",
        "as_of": "2026-08-01", "known_at": "2026-08-01T08:00:00Z",
        "authority": {"tier": "display", "can_rank": False},
        "coverage": {"entities_mapped": 1}, "market": {},
        "procurement_workspace": build_procurement_workspace(
            {"freshness": {"status": "ok"}}, [], as_of="2026-08-01",
            known_at="2026-08-01T08:00:00Z", award_freshness={"status": "ok"},
            award_event_freshness={"status": "unavailable"},
        ),
        "companies": [{"ticker": "LMT", "name": "Lockheed Martin", "metrics": {}}],
    }


@pytest.fixture
def build_root(tmp_path, monkeypatch):
    templates = tmp_path / "templates"
    templates.mkdir()
    canonical = Path(__file__).resolve().parents[1] / "templates"
    for name in ("government-revenue-page.js.j2", "theme.css", "product-nav-icons.css",
                 "government-revenue-sbir.css", "government-revenue-investor.css",
                 "government-revenue-theme-context.css", "government-revenue-parity.css"):
        shutil.copyfile(canonical / name, templates / name)
    shutil.copytree(canonical / "fonts", templates / "fonts")
    (templates / "government_revenue.html.j2").write_text("<title>Government Revenue</title>")
    monkeypatch.setattr(builder, "build_payload", lambda **_kwargs: _payload())
    return tmp_path


def _twins(root):
    return (root / "data/government_revenue/sbir_progression.json",
            root / "site/government-revenue-data/sbir-progression.json")


def test_live_builder_publishes_unavailable_instead_of_false_zero(build_root):
    builder.build(build_root)
    canonical, twin = _twins(build_root)
    assert canonical.read_bytes() == twin.read_bytes()
    payload = json.loads(canonical.read_bytes())
    assert is_valid_sbir_progression_payload(payload)
    assert payload["availability"]["state"] == "unavailable"
    assert payload["availability"]["reason"] == "sbir_observation_bundle_absent"
    assert payload["as_of"] == "2026-08-01T08:00:00+00:00"


def test_real_bundle_reaches_builder_and_http_without_recollection(build_root, monkeypatch):
    _bundle(build_root, _phase_pair())
    builder.build(build_root, as_of=OBSERVED)
    canonical, twin = _twins(build_root)
    assert canonical.read_bytes() == twin.read_bytes()
    monkeypatch.setattr(api, "_SBIR_PROGRESSION_PATHS", (canonical, twin))
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"site_full": True}
    response = TestClient(app).get("/api/government-revenue/sbir-progression")
    assert response.status_code == 200
    payload = response.json()
    assert payload == json.loads(canonical.read_bytes())
    assert payload["availability"]["state"] == "ready"
    assert len(payload["progression_evidence"]) == 1
    assert payload["forward_events"] == []
    assert payload["progression_evidence"][0]["is_production_conversion"] is False


def test_earlier_cutoff_is_valid_empty_source_not_missing_source(tmp_path):
    _bundle(tmp_path, _phase_pair())
    payload = build_sbir_progression_payload(root=tmp_path, as_of="2026-08-07T00:00:00Z")
    assert payload["availability"]["state"] == "ready"
    assert payload["known_at"] is None
    assert payload["progression_evidence"] == []
    assert is_valid_sbir_progression_payload(payload)


def test_torn_input_refuses_before_replacing_last_good(build_root):
    builder.build(build_root)
    canonical, twin = _twins(build_root)
    before = (canonical.read_bytes(), twin.read_bytes())
    (canonical.parent / "sbir_projection_state.json").write_text("{}")
    with pytest.raises(ValueError, match="partial"):
        builder.build(build_root)
    assert (canonical.read_bytes(), twin.read_bytes()) == before


def test_site_only_mirrors_committed_generation_without_recomputation(build_root, monkeypatch):
    builder.build(build_root)
    canonical, twin = _twins(build_root)
    before = canonical.read_bytes()
    twin.unlink()
    def forbidden(**_kwargs):
        raise AssertionError("renderer recomputed mutable source")
    monkeypatch.setattr(builder, "build_sbir_progression_payload", forbidden)
    builder.build_site_only(build_root)
    assert canonical.read_bytes() == twin.read_bytes() == before


@pytest.mark.parametrize("failure", ["missing", "mismatch", "hash", "false_ready", "private_field", "nested_private_field"])
def test_reader_refuses_broken_or_falsely_promoted_generation(build_root, monkeypatch, failure):
    builder.build(build_root)
    canonical, twin = _twins(build_root)
    monkeypatch.setattr(api, "_SBIR_PROGRESSION_PATHS", (canonical, twin))
    if failure == "missing":
        canonical.unlink()
    elif failure == "mismatch":
        twin.write_text("{}")
    else:
        payload = json.loads(canonical.read_bytes())
        if failure == "hash":
            payload["content_id"] = "grsp1-" + "0" * 24
        elif failure == "false_ready":
            payload["availability"] = {"state": "ready", "reason": "sbir_observation_bundle_ready"}
            payload["content_id"] = sbir_progression_content_id(payload)
        else:
            target = payload if failure == "private_field" else payload["source"]
            target["poc_email"] = "synthetic@example.invalid"
            payload["content_id"] = sbir_progression_content_id(payload)
        for path in (canonical, twin):
            path.write_text(json.dumps(payload))
    with pytest.raises(HTTPException) as error:
        api.sbir_progression()
    assert error.value.status_code == 503


@pytest.mark.parametrize("mutation", ["generation", "receipt", "future_known", "count", "future_leg", "early_pair", "phase_order"])
def test_ready_validator_checks_semantics_even_after_rehash(tmp_path, mutation):
    _bundle(tmp_path, _phase_pair())
    payload = copy.deepcopy(build_sbir_progression_payload(root=tmp_path, as_of=OBSERVED))
    if mutation == "generation":
        payload.pop("generation")
    elif mutation == "receipt":
        payload["source"].pop("receipt_ledger")
    elif mutation == "future_known":
        payload["known_at"] = "2030-01-01T00:00:00Z"
    elif mutation == "count":
        payload["coverage"]["progression_pairs"] += 1
    elif mutation == "future_leg":
        payload["progression_evidence"][0]["phase_ii"]["known_at"] = "2030-01-01T00:00:00Z"
    elif mutation == "early_pair":
        payload["progression_evidence"][0]["known_at"] = "2026-08-07T00:00:00Z"
    else:
        payload["progression_evidence"][0]["phase_ii"]["effective_at"] = "1900-01-01"
    payload["content_id"] = sbir_progression_content_id(payload)
    assert not is_valid_sbir_progression_payload(payload)


def test_denied_entitlement_precedes_source_read(monkeypatch):
    class Unreadable:
        def read_bytes(self):
            raise AssertionError("private source opened before entitlement")
    monkeypatch.setattr(api, "_SBIR_PROGRESSION_PATHS", (Unreadable(), Unreadable()))
    def denied():
        raise HTTPException(status_code=403, detail="site_full required")
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = denied
    assert TestClient(app).get("/api/government-revenue/sbir-progression").status_code == 403


@pytest.mark.parametrize("field", ["pi_name", "address1", "address2", "city", "zip"])
def test_nested_source_private_fields_remain_forbidden_after_rehash(tmp_path, field):
    payload = build_sbir_progression_payload(root=tmp_path, as_of=OBSERVED)
    payload["source"][field] = "synthetic-private-value"
    payload["content_id"] = sbir_progression_content_id(payload)
    assert not is_valid_sbir_progression_payload(payload)
