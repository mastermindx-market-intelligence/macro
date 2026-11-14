from copy import deepcopy
import json
from pathlib import Path

import pytest
pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import app.prophet_lab as api
from engine.industry_expectations import compose_with_k3e

URL = "/api/prophet/industry-research/v1"


def _snapshot():
    return {"schema": "prophet.industry_research_snapshot.v1", "as_of": "2002-12-31T00:00:00+00:00",
            "financial_influence": False, "authority": "research_only", "evidence_mode": "RECONSTRUCTED_DISCOVERY",
            "source_refs": ["source-hash"], "forecasts": [{
                "schema": "prophet.industry_transition.v1", "industry": "Meals", "decision_date": "2002-12-31",
                "state": "reversal_attempt", "authority": "research_only", "financial_influence": False,
                "evidence_mode": "RECONSTRUCTED_DISCOVERY", "probabilities": {"upside_first": .4, "downside_first": .2, "timeout": .4},
                "p_bad_loss": .25, "expected_excess_net": .01, "outside_support_share": .1,
                "model": {"calibration_label_end": "2002-12-30", "prediction_start": "2002-12-31",
                          "label_contract": {"horizon": 63, "entry_delay": 1, "target": .1, "loss": .1, "cost": .002}}}]}


def _app(paid=False):
    app = FastAPI(); app.include_router(api.router)
    if paid: app.dependency_overrides[api.require_site_full_user] = lambda: {"id": "test-paid"}
    return app


def _private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_route_has_original_auth_dependency():
    route = next(r for r in api.router.routes if r.path == URL)
    assert any(d.call is api.require_site_full_user for d in route.dependant.dependencies)


def test_paid_actual_file_consumer(tmp_path, monkeypatch):
    p = tmp_path / "latest.json"; p.write_text(json.dumps(_snapshot()))
    monkeypatch.setattr(api, "_INDUSTRY_RESEARCH_SNAPSHOT_PATH", p)
    with TestClient(_app(True)) as client:
        response = client.get(URL + "?path=/etc/passwd")
    assert response.status_code == 200
    assert response.json()["state"] == "HISTORICAL_RESEARCH"
    assert response.json()["live_signal"] is False
    assert len(response.json()["snapshot"]["forecasts"]) == 1
    _private(response)


def test_missing_and_corrupt_are_private_unavailable(tmp_path, monkeypatch):
    p = tmp_path / "latest.json"
    monkeypatch.setattr(api, "_INDUSTRY_RESEARCH_SNAPSHOT_PATH", p)
    with TestClient(_app(True)) as client:
        response = client.get(URL)
        assert response.status_code == 503; _private(response)
        p.write_text("not json")
        response = client.get(URL)
        assert response.status_code == 503; _private(response)
        assert str(tmp_path) not in response.text


def test_existing_kill_switch_stops_reader(monkeypatch):
    monkeypatch.setenv("PROPHET_LAB_DISABLED", "1")
    import engine.prophet_lab.industry_transition_context as reader
    monkeypatch.setattr(reader, "read_industry_context", lambda _: (_ for _ in ()).throw(AssertionError("must not read")))
    with TestClient(_app(True)) as client: response = client.get(URL)
    assert response.status_code == 503
    assert response.json()["error"] == "prophet_lab_disabled"
    _private(response)


@pytest.mark.parametrize("status", [401, 403])
def test_real_auth_wrapper_preserves_denial_and_private_headers(status, monkeypatch):
    import app.main as main
    import app.paywall as paywall
    if status == 401:
        monkeypatch.setattr(main, "require_user", lambda _: (_ for _ in ()).throw(HTTPException(401, "no token")))
    else:
        monkeypatch.setattr(main, "require_user", lambda _: {"id": "free-user"})
        def deny(user, *, always):
            assert always is True
            raise HTTPException(403, "paid entitlement required")
        monkeypatch.setattr(paywall, "enforce_site_full", deny)
    with TestClient(_app()) as client: response = client.get(URL)
    assert response.status_code == status; _private(response)


def _expectation(asof="2002-12-31T00:00:00Z"):
    return {"semantic_payload": {"schema": "k3e.declared_capture_inspection.v1",
        "query": {"ticker_compat": "AAA", "metric": "EPS", "as_of": asof},
        "normalized_baseline": {"value": None, "status": "UNESTIMABLE", "rights_state": "UNKNOWN"},
        "latest_captured_snapshot": {"status": "AVAILABLE"}, "period_continuity": "SAME_NATIVE_PERIOD"}}


def _binding():
    return {"ticker": "AAA", "industry": "Meals", "valid_from": "2000-01-01T00:00:00Z", "known_at": "2000-01-01T00:00:00Z"}


def test_actual_k3e_owner_is_composed_without_modifying_prediction():
    forecast = _snapshot()["forecasts"][0]; before = deepcopy(forecast)
    out = compose_with_k3e(forecast, expectation_inspection=_expectation(), member_binding=_binding())
    assert out["k3e"]["schema"] == "k3e.descriptive_coupling.v1"
    assert out["k3e"]["state"] == "EXPECTATION_ONLY"
    assert out["k3e"]["expectation"]["ticker"] == "AAA"
    assert out["probabilities"] == before["probabilities"]
    assert forecast == before and out["context_changes_forecast"] is False


def test_future_or_wrong_member_k3e_cannot_attach():
    forecast = _snapshot()["forecasts"][0]
    with pytest.raises(ValueError, match="membership"):
        compose_with_k3e(forecast, expectation_inspection=_expectation())
    with pytest.raises(ValueError, match="after forecast"):
        compose_with_k3e(forecast, expectation_inspection=_expectation("2003-01-01T00:00:00Z"), member_binding=_binding())
    wrong = _binding(); wrong["industry"] = "Chips"
    with pytest.raises(ValueError, match="membership"):
        compose_with_k3e(forecast, expectation_inspection=_expectation(), member_binding=wrong)


def test_owner_refusal_not_overridden():
    exp = _expectation(); exp["semantic_payload"]["normalized_baseline"]["value"] = 123
    out = compose_with_k3e(_snapshot()["forecasts"][0], expectation_inspection=exp)
    assert out["k3e"]["state"] == "REFUSED"
    assert "UNQUALIFIED_NORMALIZED_VALUE_PRESENT" in out["k3e"]["refusals"]
    assert not out["financial_influence"]
