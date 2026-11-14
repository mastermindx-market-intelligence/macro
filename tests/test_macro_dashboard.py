"""Native display and read boundary: source truth, privacy and actual artifact reads."""
import copy
import json
from pathlib import Path

import pytest

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
    from app import macro_dashboard as endpoint
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
