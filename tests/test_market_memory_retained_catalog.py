"""Authenticated discovery through the actual trusted owner, API and Brain."""
from __future__ import annotations

import json
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from app import market_memory as api
from engine.neuralweb import market_memory_retained_catalog as catalog
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_trusted as trusted
from tests.test_market_memory_retained_consumer import original


def discover(original, **spec):
    return api.retained_catalog_for_user(original[0], "member", spec)


def test_catalog_pins_full_authenticated_generation_and_pages(original):
    value = discover(original, limit=2)
    assert value["schema"] == catalog.SCHEMA
    assert value["selection"]["total"] == 5
    assert len(value["entries"]) == 2
    assert value["generation"]["generation_id"] == original[2].generation_id
    assert len(value["methods"]) == 2
    next_page = api.retained_catalog_for_user(original[0], "member", value["selection"]["continuation"])
    assert next_page["generation"] == value["generation"]
    assert not {r["query_id"] for r in value["entries"]} & {r["query_id"] for r in next_page["entries"]}
    assert value["outcomes"]["status"] == "NOT_ATTACHED"


def test_supported_cutoff_is_actual_maximum_clock_then_consumes_real_refs(original):
    value = discover(original)
    query = next(row for row in value["entries"] if row["query_id"] == original[3]["query_id"])
    from engine.neuralweb.market_memory_retained_context_cohort import utc_instant
    assert utc_instant(query["earliest_supported_cutoff"]) == max(map(utc_instant, query["clocks"].values()))
    method = next(m for m in value["methods"] if m["mode"] == value["mode"])
    spec = {key: query[key] for key in ("query_id", "subject_id")}
    spec.update({key: value["generation"][key] for key in ("generation_id", "generation_sha256")})
    spec.update(query_cutoff=query["earliest_supported_cutoff"], method_spec_id=method["method_spec_id"])
    answer = api.retained_macro_for_user(original[0], "member", spec)
    assert answer["source_cards"][0]["context_id"] == query["context_id"]


@pytest.mark.parametrize("spec", [{"offset": 1}, {"limit": True}, {"limit": 21}, {"offset": "01"},
    {"user_id": "admin"}, {"subject_id": "guessed"}, {"mode": "live"}, {"generation_id": "bad"}])
def test_invalid_catalog_request_denied_before_owner(original, monkeypatch, spec):
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", lambda *a, **k: pytest.fail("opened owner"))
    with pytest.raises(HTTPException) as exc:
        discover(original, **spec)
    assert exc.value.status_code == 400


def test_source_use_denied_before_reader_construction(original, monkeypatch):
    path = original[0] / use.REGISTRATION
    value = json.loads(path.read_text()); value["enabled"] = False; path.write_text(json.dumps(value))
    monkeypatch.setattr(trusted, "TrustedFileAsKnownAtReader", lambda *a, **k: pytest.fail("opened owner"))
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 403


def test_revoked_unreturned_capture_refuses_count_and_payload(original):
    path = original[0] / use.REGISTRATION
    value = json.loads(path.read_text())
    value["revoked_capture_ids"] = [original[4][0].capture_receipt["capture_id"]]
    path.write_text(json.dumps(value))
    with pytest.raises(HTTPException) as exc:
        discover(original, limit=1)
    assert exc.value.status_code == 403
    assert "entries" not in exc.value.detail and "total" not in exc.value.detail


def test_final_source_registration_change_refuses_whole_disclosure(original, monkeypatch):
    real = use.RetainedHouseUsePolicy.disclosure
    def revoke(self):
        value = real(self)
        path = self.root / use.REGISTRATION
        data = json.loads(path.read_text()); data["enabled"] = False; path.write_text(json.dumps(data))
        return value
    monkeypatch.setattr(use.RetainedHouseUsePolicy, "disclosure", revoke)
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 403


def test_wrong_generation_hash_has_no_substitution(original):
    with pytest.raises(HTTPException) as exc:
        discover(original, generation_id=original[2].generation_id, generation_sha256="0" * 64)
    assert exc.value.status_code == 503


def test_http_headers_duplicates_and_actual_brain_dispatch(original, monkeypatch):
    monkeypatch.setattr(api, "_repo_root", lambda: original[0])
    app = FastAPI(); app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "member"}
    client = TestClient(app)
    for params, expected in (({"limit": 1}, 200), ([("limit", 1), ("limit", 2)], 400)):
        response = client.get("/api/market-memory/v1/macro/retained/catalog", params=params)
        assert response.status_code == expected
        assert response.headers["cache-control"] == "private, no-store"
        assert response.headers["vary"] == "Authorization"
    from engine.neuralweb import brain_gateway as gateway, ask_brain
    result = gateway._dispatch_brain_tool("get_retained_market_catalog", {"limit": 1},
        original[0], original[0], "", user_id="member")
    assert result["schema"] == catalog.SCHEMA and result["selection"]["returned"] == 1
    assert "get_retained_market_catalog" in ask_brain._FAST_VISIBLE_TOOL_FAMILIES["macro_rates"]
    denied = gateway._dispatch_brain_tool("get_retained_market_catalog", {}, original[0], original[0], "", user_id="")
    assert denied["http_status"] == 403 and "entries" not in denied


def test_actual_other_subject_refused_before_payload(original, monkeypatch):
    actual_read = trusted.TrustedFileAsKnownAtReader.read_pinned_capture_receipt
    def other(self, *args, **kwargs):
        receipt = actual_read(self, *args, **kwargs)
        receipt["subject"]["subject_id"] = "mmsecurity_" + "0" * 64
        return receipt
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_receipt", other)
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections",
                        lambda *a, **k: pytest.fail("denied subject loaded payload"))
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 403


def test_catalog_owner_budget_and_shared_slot_refuse_without_counts(original, monkeypatch):
    from engine.neuralweb import market_memory_pit as pit
    def exceed(*a, **k):
        raise pit.OwnerReadBudgetError("test budget")
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation", exceed)
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 503 and exc.value.detail["state"] == "OWNER_READ_BUDGET_EXCEEDED"
    assert api._playback_slots.acquire(blocking=False)
    assert api._playback_slots.acquire(blocking=False)
    try:
        with pytest.raises(HTTPException) as exc:
            discover(original)
        assert exc.value.status_code == 503 and exc.value.detail["state"] == "BUSY"
    finally:
        api._playback_slots.release(); api._playback_slots.release()


def test_comparison_components_are_exact_owner_values(original):
    from decimal import Decimal, ROUND_HALF_EVEN
    value = api.retained_macro_for_user(original[0], "member", original[3])
    assert len(value["neighbors"]) == 2
    for row in value["neighbors"]:
        assert set(row["components_exact_decimal"]) == set(use.FIELDS)
        assert row["comparison_id"].startswith("mmepisodecomparison_")
        parts = {k: Decimal(v) for k, v in row["components_exact_decimal"].items()}
        assert all(v == 0 for k, v in parts.items() if k != "growth_score")
        assert Decimal(row["distance_q18"]) == (sum(parts.values()) / 5).quantize(Decimal("1e-18"), rounding=ROUND_HALF_EVEN)


def test_registered_dependency_mismatch_is_typed_private_api_and_brain_failure(original, monkeypatch):
    from engine.neuralweb import market_memory_episode_retrieval as retrieval, brain_gateway as gateway
    def mismatch(self):
        raise retrieval.EpisodeRetrievalError("registered_dependency_source_mismatch")
    monkeypatch.setattr(retrieval.RetainedContextMethodSpec, "disclosure", mismatch)
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 503 and exc.value.detail["state"] == "EXACT_CATALOG_UNAVAILABLE"
    monkeypatch.setattr(api, "_repo_root", lambda: original[0])
    app = FastAPI(); app.include_router(api.router)
    app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "member"}
    response = TestClient(app).get("/api/market-memory/v1/macro/retained/catalog")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "private, no-store"
    assert "entries" not in response.json()
    result = gateway._dispatch_brain_tool("get_retained_market_catalog", {}, original[0], original[0], "", user_id="member")
    assert result["http_status"] == 503 and result["state"] == "EXACT_CATALOG_UNAVAILABLE"


def test_wrong_configured_store_refuses_before_ancestry_or_payload(original, monkeypatch):
    path = original[0] / use.REGISTRATION
    value = json.loads(path.read_text()); value["store_id"] = "mmstore_" + "0" * 64
    path.write_text(json.dumps(value))
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_generation",
                        lambda *a, **k: pytest.fail("wrong store opened ancestry"))
    monkeypatch.setattr(trusted.TrustedFileAsKnownAtReader, "read_pinned_capture_projections",
                        lambda *a, **k: pytest.fail("wrong store opened payload"))
    with pytest.raises(HTTPException) as exc:
        discover(original)
    assert exc.value.status_code == 503 and exc.value.detail["state"] == "EXACT_CATALOG_UNAVAILABLE"
