"""Native display and read boundary: source truth, privacy and actual artifact reads."""
import copy
import json
from pathlib import Path

import pytest

from app import macro_dashboard as endpoint
from lib.macro_dashboard_view import MAX_BYTES, build_dashboard, write_dashboard


def view():
    return {"generated_utc": "2026-11-13 14:30", "latest": {"quad_name": "Goldilocks", "private_token": "secret"},
            "market_state": {"schema": "market_state.v1", "market": "us", "asof": "2026-11-13", "score": 0,
                "raw_score": 61, "score_source": "radar_ceiling", "capped": True, "verdict": "RISK_OFF",
                "components": [{"key": "risk", "score": 0, "weight": .2, "degraded": False, "metrics": [{"k_en": "Rate", "v": float("nan")}]}]},
            "ms_history": [{"asof": "2026-11-12", "score": None}, {"asof": "2026-11-13", "score": 61}],
            "event_strip": [{"label": "Payrolls", "label_zh": "非农就业", "date": "2026-12-04", "time_et": "08:30"}],
            "market_tiles": [{"label": {"en": "S&P 500", "zh": "标普500"}, "level": "6,000.00", "chg": "0.00", "pct": "0.00%", "sym": "SPY"}],
            "alerts": [{"rule": "credit", "plain_en": "Credit widening", "tier": "watch", "severity": 2}],
            "fear_greed": {"dial": 0, "legs_included": [{"name_en": "Breadth", "pct": 0, "last_date": "2026-11-12"}]},
            "health": [{"name": "provider", "status": "error", "error": "private API key"}],
            "master_brief": {"state_asof": "2026-11-12", "summary": "Read-through", "tldr": ["One"], "zh": {"summary": "解读"}},
            "macro_news": {"headlines": [{"title": "Official release", "seendate": "2026-11-13", "url": "https://example.com"}], "leg_status": {"gdelt": {"n": 0, "degraded_reason": "unavailable"}}},
            "us_prophet_book": {"private": "never publish"}}


def test_projection_preserves_zero_gaps_caps_and_actual_producer_shapes():
    source = view(); before = copy.deepcopy(source)
    result = build_dashboard(source)
    assert result["market_state"]["score"] == 0
    assert result["market_state"]["raw_score"] == 61
    assert result["market_state"]["components"][0]["metrics"][0]["v"] is None
    assert result["history"][0]["score"] is None
    assert result["market_tiles"][0]["label"]["zh"] == "标普500"
    assert result["market_tiles"][0]["level"] == "6,000.00"
    assert result["events"][0]["label"] == "Payrolls"
    assert result["sentiment"]["dial"] == 0
    assert result["sentiment"]["legs_included"][0]["pct"] == 0
    assert result["brief"]["zh"]["summary"] == "解读"
    assert result["news"][0]["seendate"] == "2026-11-13"
    assert result["news_state"]["leg_status"]["gdelt"]["n"] == 0
    assert source["market_state"]["raw_score"] == before["market_state"]["raw_score"]
    raw = json.dumps(result, allow_nan=False)
    assert "private" not in raw and "token" not in raw and "prophet_book" not in raw


def test_empty_optional_sources_remain_absent():
    result = build_dashboard({"generated_utc": "2026-11-13 14:30"})
    assert result["market_state"] is None and result["rates"] is None
    assert result["history"] == [] and result["events"] == []
    assert result["sentiment"] is None


@pytest.fixture
def api(tmp_path, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI(); app.include_router(endpoint.router)
    app.dependency_overrides[endpoint.require_user] = lambda: {"id": "registered-test-member"}
    root = tmp_path / "served"; root.mkdir()
    live = tmp_path / "runtime-live"; live.mkdir()
    monkeypatch.setattr(endpoint, "_served_root", lambda: root)
    monkeypatch.setattr(endpoint, "_live_root", lambda: live)
    write_dashboard(view(), root / "macrodata" / "dashboard.json")
    return TestClient(app), endpoint, root, live


def test_authenticated_read_keeps_missing_current_separate_and_returns_receipt(api):
    client, _, root, _ = api
    before = (root / "macrodata" / "dashboard.json").read_bytes()
    response = client.get("/api/macro/dashboard")
    assert response.status_code == 200
    assert response.json()["current_risk"] is None
    assert response.json()["market_state"]["score"] == 0
    assert len(response.json()["publication_sha256"]) == 64
    assert "no-store" in response.headers["cache-control"]
    assert "noindex" in response.headers["x-robots-tag"]
    assert before == (root / "macrodata" / "dashboard.json").read_bytes()
    assert client.get("/api/macro/dashboard?path=/tmp/other").status_code == 400


def test_live_read_uses_runtime_only_and_preserves_expiry(api):
    client, _, root, live = api
    (root / "live").mkdir(); (root / "live" / "risk_state.json").write_text('{"schema":"risk_state.v1","score":99}')
    assert client.get("/api/macro/dashboard").json()["current_risk"] is None
    (live / "risk_state.json").write_text(json.dumps({"schema": "risk_state.v1", "live_active": True,
        "stale_after": "2026-11-13T14:00:00Z", "live": {"score": 0, "verdict": "RISK_OFF"}, "secret": "excluded"}))
    value = client.get("/api/macro/dashboard").json()["current_risk"]
    assert value["live"]["score"] == 0 and value["stale_after"] == "2026-11-13T14:00:00Z"
    assert "secret" not in value


def test_official_release_read_preserves_binding_without_recomputing_or_repo_fallback(api):
    client, _, root, live = api
    row = {"status": "published", "data_ready": True, "date": "2026-11-13", "type": "PPI",
           "source_url": "https://www.bls.gov/news.release/ppi.htm", "source_sha256": "b" * 64,
           "content_sha256": "b" * 64, "actual": {"headline_en": "Official result", "source_url": "https://www.bls.gov/news.release/ppi.htm", "internal": "exclude"}}
    (live / "release_publications.json").write_text(json.dumps({"schema": "release_publications.v2", "is_context_only": True,
        "built": "2026-11-14T00:00:00Z", "publications": [row], "private_state": "exclude"}))
    feed = client.get("/api/macro/dashboard").json()["release_feed"]
    assert feed["publications"][0]["actual"]["headline_en"] == "Official result"
    assert feed["publications"][0]["source_sha256"] == feed["publications"][0]["content_sha256"]
    assert "exclude" not in json.dumps(feed)


@pytest.mark.parametrize("failure", ["missing", "invalid", "oversized", "symlink", "future", "nonfinite"])
def test_unqualified_publication_is_typed_unavailable(api, failure):
    client, _, root, _ = api
    path = root / "macrodata" / "dashboard.json"
    if failure == "missing": path.unlink()
    elif failure == "invalid": path.write_text("[]")
    elif failure == "oversized": path.write_bytes(b" " * (MAX_BYTES + 1))
    elif failure == "symlink":
        target = root / "other.json"; path.rename(target); path.symlink_to(target)
    else:
        body = json.loads(path.read_text())
        if failure == "future": body["published_at"] = "2999-01-01T00:00:00Z"
        else: body["market_state"]["score"] = float("nan")
        path.write_text(json.dumps(body))
    response = client.get("/api/macro/dashboard")
    assert response.status_code == 503
    assert response.json() == {"error": "dashboard_unavailable"}


def test_authentication_precedes_artifact_read(api, monkeypatch):
    from fastapi import HTTPException
    client, endpoint, _, _ = api
    def denied(): raise HTTPException(status_code=401, detail="unauthorized")
    client.app.dependency_overrides[endpoint.require_user] = denied
    monkeypatch.setattr(endpoint, "_served_root", lambda: pytest.fail("read before authentication"))
    assert client.get("/api/macro/dashboard").status_code == 401


def forecast_source():
    return json.loads((Path(__file__).parent / "fixtures" / "release_forecast_full.json").read_text())


def test_forecast_uses_its_own_served_artifact_clock_receipt_and_disclosures(api):
    import hashlib
    client, _, root, _ = api
    source = forecast_source()
    source["methodology_status"] = {"accuracy_claim": "withheld_until_clean_aligned_forward_evidence", "street_consensus": "unavailable"}
    source["track_record"] = {"score_receipts": {"raw_n": 20, "canonical_n": 8, "superseded_n": 12}, "releases": []}
    source["private_key"] = "never export"
    raw = json.dumps(source).encode()
    (root / "macrodata" / "release_forecast.json").write_bytes(raw)
    body = client.get("/api/macro/dashboard").json()
    forecast = body["release_forecast"]
    assert forecast["asof"] == source["asof"] != body["published_at"]
    assert body["release_forecast_sha256"] == hashlib.sha256(raw).hexdigest()
    assert forecast["upcoming"][3]["projection"]["mode"] == "benchmark_only"
    assert forecast["upcoming"][9]["projection"]["point"] is None
    assert forecast["upcoming"][9]["components"]["private_trend"] is None
    assert forecast["methodology_status"]["street_consensus"] == "unavailable"
    assert forecast["track_record"]["score_receipts"]["canonical_n"] == 8
    assert body["release_forecast_state"] == "available"
    assert "gap_bp" not in forecast["upcoming"][0]["policy_backdrop"]
    assert "never export" not in json.dumps(forecast)


@pytest.mark.parametrize("withdrawal", [True, {}, {"verdict": "WITHDRAWN", "receipt_sha256": "a" * 64}])
def test_withdrawal_removes_shadow_forecast_numbers_and_components(withdrawal):
    from lib.macro_dashboard_view import project_release_forecast
    source = forecast_source()
    source["upcoming"][0]["shadows"]["v3_factor"] = {"display_only": True, "claim_withdrawn": withdrawal,
        "point": 777, "p10": 700, "p90": 800, "confidence": .9, "components": [{"name": "hidden", "contrib_pp": 777}]}
    shadow = project_release_forecast(source)["upcoming"][0]["shadows"]["v3_factor"]
    assert shadow["claim_withdrawn"]
    assert not {"point", "p10", "p90", "confidence", "components"}.intersection(shadow)


@pytest.mark.parametrize("failure", ["schema", "authority", "undated", "future", "nonfinite", "oversized", "symlink"])
def test_unqualified_forecast_does_not_disable_dashboard(api, failure):
    client, _, root, _ = api
    source = forecast_source()
    if failure == "schema": source["schema"] = "other"
    if failure == "authority": source["authority"]["can_trade"] = True
    if failure == "undated": source["asof"] = "2026-07-10"
    if failure == "future": source["asof"] = "2999-01-01T00:00:00Z"
    if failure == "nonfinite": source["upcoming"][0]["projection"]["point"] = float("nan")
    path = root / "macrodata" / "release_forecast.json"
    path.write_text(json.dumps(source))
    if failure == "oversized": path.write_bytes(b" " * (MAX_BYTES + 1))
    if failure == "symlink":
        other = root / "forecast-other.json"; path.rename(other); path.symlink_to(other)
    response = client.get("/api/macro/dashboard")
    assert response.status_code == 200
    assert response.json()["release_forecast"] is None
    assert response.json()["release_forecast_sha256"] is None
    assert response.json()["release_forecast_state"] == "unqualified"
    assert response.json()["market_state"]["score"] == 0


def test_optional_forecast_respects_aggregate_response_budget(api, monkeypatch):
    client, endpoint, root, _ = api
    base_size = len(client.get("/api/macro/dashboard").content)
    monkeypatch.setattr(endpoint, "MAX_RESPONSE_BYTES", base_size + 500)
    (root / "macrodata" / "release_forecast.json").write_text(json.dumps(forecast_source()))
    response = client.get("/api/macro/dashboard")
    assert response.status_code == 200
    assert len(response.content) <= base_size + 500
    assert response.json()["release_forecast"] is None
    assert response.json()["release_forecast_sha256"] is None


def test_response_trimming_never_downgrades_forecast_refusal_to_transient_failure(api, monkeypatch):
    client, endpoint, root, live = api
    base_size = len(client.get("/api/macro/dashboard").content)
    monkeypatch.setattr(endpoint, "MAX_RESPONSE_BYTES", base_size + 500)
    source = forecast_source(); source["authority"]["can_trade"] = True
    (root / "macrodata" / "release_forecast.json").write_text(json.dumps(source))
    (live / "release_publications.json").write_text(json.dumps({"schema": "release_publications.v2", "is_context_only": True,
        "publications": [{"actual": {"summary_en": "x" * 6000}}]}))
    response = client.get("/api/macro/dashboard")
    assert response.status_code == 200
    assert len(response.content) <= base_size + 500
    assert response.json()["release_forecast_state"] == "unqualified"
    assert response.json()["release_feed"] is None
