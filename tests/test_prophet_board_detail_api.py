"""Authenticated-router boundary tests; data is explicitly synthetic.

Tests overriding the entitlement dependency prove routing/ordering, not the
production entitlement implementation. The separate assembled tests exercise
the real shared authentication chain and the app's existing mount.
"""
import hashlib
import importlib
import json
from contextlib import nullcontext
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

URL = "/api/prophet/board-detail/v1"


def source():
    return json.dumps({"as_of": "2026-11-12", "buy": [{"ticker": "TEST", "price": 0,
        "entry_signal": {"status": "watch", "buy_zone": {"low": 10, "high": 10}, "stop": 10},
        "signal": {"provisional": False, "tier_observation_provisional": True}}]}).encode()


def query(raw=None):
    return {"ticker": "TEST", "source_sha256": "sha256:" + hashlib.sha256(raw or source()).hexdigest()}


def private(response):
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


@pytest.fixture
def owner(monkeypatch, tmp_path):
    owner = importlib.import_module("app.prophet_daily_brief")
    monkeypatch.setattr(owner, "_REPO_ROOT", tmp_path)
    target = tmp_path / owner._CANDIDATE_SOURCE_PATH
    target.parent.mkdir(parents=True); target.write_bytes(source())
    return owner


@pytest.fixture
def client(owner):
    app = FastAPI(); app.include_router(owner.router)
    app.dependency_overrides[owner.require_site_full_user] = lambda: {"id": "test-entitled"}
    with TestClient(app) as client: yield client


def test_detail_is_reachable_and_keeps_the_exact_source_receipt(client, owner):
    response = client.get(URL, params=query()); private(response)
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "mastermind.prophet_board_detail_read.v1"
    assert payload["display_only"] is True and payload["market"] == "US"
    assert payload["source"] == {"path": owner._CANDIDATE_SOURCE_PATH, "sha256": query()["source_sha256"], "bytes": len(source())}
    assert payload["row"]["price"] == 0 and payload["row"]["price_as_of"] is None
    assert payload["row"]["signal"]["provisional"] is False
    assert payload["row"]["signal"]["tier_observation_provisional"] is True


@pytest.mark.parametrize("changes", [{"ticker": "test"}, {"ticker": "../TEST"}, {"ticker": ""},
    {"source_sha256": "a" * 64}, {"source_sha256": "sha256:" + "A" * 64}, {"root": "/private"}, {"market": "US"}])
def test_invalid_query_never_reads_source(client, owner, monkeypatch, changes):
    monkeypatch.setattr(owner, "_read_candidate_source", lambda: pytest.fail("query reached source"))
    response = client.get(URL, params={**query(), **changes})
    assert response.status_code == 400; private(response)


@pytest.mark.parametrize("params", [[], [("ticker", "TEST")], [("ticker", "TEST"), ("ticker", "TEST"), ("source_sha256", query()["source_sha256"])]])
def test_missing_or_duplicate_query_is_invalid(client, params):
    response = client.get(URL, params=params)
    assert response.status_code == 400; private(response)


def test_hash_mismatch_is_a_conflict_and_does_not_rebind(client):
    response = client.get(URL, params={**query(), "source_sha256": "sha256:" + "0" * 64})
    assert response.status_code == 409 and response.json() == {"error": "SOURCE_BINDING_MISMATCH"}; private(response)


def test_valid_absence_is_not_a_source_failure(client):
    response = client.get(URL, params={**query(), "ticker": "OFFLIST"})
    assert response.status_code == 200
    assert response.json()["status"] == "not_on_main_list" and response.json()["row"] is None


@pytest.mark.parametrize("raw", [b'{"as_of":"2026-11-12","buy":[],"buy":[]}',
    b'{"as_of":"2026-11-12","buy":null}', b'{"buy":[NaN]}', b'{"buy":[1e999]}', b'not-json'])
def test_corrupt_source_is_private_unavailable(client, owner, monkeypatch, raw):
    monkeypatch.setattr(owner, "_read_candidate_source", lambda: raw)
    response = client.get(URL, params=query(raw))
    assert response.status_code == 503 and response.json() == {"error": "BOARD_DETAIL_UNAVAILABLE"}; private(response)


def test_final_source_race_withdraws_the_serialized_detail(client, owner, monkeypatch):
    reads = iter([source(), source() + b" "])
    monkeypatch.setattr(owner, "_read_candidate_source", lambda: next(reads))
    response = client.get(URL, params=query())
    assert response.status_code == 503 and "row" not in response.json(); private(response)


def test_detail_candidates_and_daily_brief_share_nonqueuing_admission(client, owner, monkeypatch):
    monkeypatch.setattr(owner, "_read_candidate_source", lambda: pytest.fail("busy route read source"))
    daily = {"source_sha256": query()["source_sha256"], "pair_id": "b" * 32, "selection_receipt": "sha256:" + "c" * 64}
    with owner._READ_ADMISSION:
        for path, params in [(URL, query()), ("/api/prophet/candidates/v1", {}), ("/api/prophet/daily-brief/v1", daily)]:
            response = client.get(path, params=params)
            assert response.status_code == 503; private(response)


def test_auth_dependency_denial_precedes_query_and_source(owner, monkeypatch):
    app = FastAPI(); app.include_router(owner.router)
    def deny(): raise HTTPException(401, "test denial", headers=owner._PRIVATE_HEADERS)
    app.dependency_overrides[owner.require_site_full_user] = deny
    monkeypatch.setattr(owner, "_read_candidate_source", lambda: pytest.fail("denied route read source"))
    with owner._READ_ADMISSION, TestClient(app) as client:
        response = client.get(URL + "?root=/private")
    assert response.status_code == 401; private(response)


@pytest.mark.parametrize("point", ["final_read", "projection", "serialization"])
def test_child_failures_are_sanitized_and_release_the_permit(client, owner, monkeypatch, point):
    import app.prophet_board_detail as child
    import engine.us_prophet_board_view as projection
    with monkeypatch.context() as patch:
        def fail(*_args, **_kwargs): raise OSError("PRIVATE_TEST_DETAIL")
        if point == "final_read":
            count = 0
            def read():
                nonlocal count
                count += 1
                return source() if count == 1 else fail()
            patch.setattr(owner, "_read_candidate_source", read)
        elif point == "projection":
            patch.setattr(projection, "project_board_detail", fail)
        else:
            original = child.JSONResponse
            def serialize(content, **kwargs):
                if "schema" in content: fail()
                return original(content, **kwargs)
            patch.setattr(child, "JSONResponse", serialize)
        response = client.get(URL, params=query())
        assert response.status_code == 503 and response.json() == {"error": "BOARD_DETAIL_UNAVAILABLE"}
        assert "PRIVATE_TEST_DETAIL" not in response.text; private(response)
    assert client.get(URL, params=query()).status_code == 200


def test_child_holds_shared_permit_through_its_final_read(client, owner, monkeypatch):
    reached_final, release = Event(), Event()
    calls = 0
    def read():
        nonlocal calls
        calls += 1
        if calls == 2:
            reached_final.set()
            assert release.wait(5), "test release timed out"
        return source()
    monkeypatch.setattr(owner, "_read_candidate_source", read)
    daily = {"source_sha256": query()["source_sha256"], "pair_id": "b" * 32, "selection_receipt": "sha256:" + "c" * 64}
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.get, URL, params=query())
        try:
            assert reached_final.wait(5)
            for path, params in [(URL, query()), ("/api/prophet/candidates/v1", {}), ("/api/prophet/daily-brief/v1", daily)]:
                busy = client.get(path, params=params)
                assert busy.status_code == 503; private(busy)
        finally:
            release.set()
        assert pending.result(timeout=5).status_code == 200
    assert client.get(URL, params=query()).status_code == 200


@pytest.mark.parametrize("denial,busy", [(401, False), (401, True), (403, False), (403, True)])
def test_assembled_auth_chain_precedes_query_and_busy_response(owner, monkeypatch, denial, busy):
    import app.main as main
    import app.paywall as paywall
    calls = []
    def authenticate(_authorization):
        calls.append("auth")
        if denial == 401: raise HTTPException(401, "test anonymous")
        return {"id": "test-free"}
    def entitle(_user, *, always=False):
        assert always is True; calls.append("entitle"); raise HTTPException(403, "test entitlement")
    monkeypatch.setattr(main, "require_user", authenticate)
    monkeypatch.setattr(paywall, "enforce_site_full", entitle)
    monkeypatch.setattr(owner, "_read_candidate_source", lambda: pytest.fail("denied route read source"))
    app = FastAPI(); app.include_router(owner.router)
    with owner._READ_ADMISSION if busy else nullcontext():
        with TestClient(app) as client: response = client.get(URL + "?root=/private")
    assert response.status_code == denial; private(response)
    assert calls == (["auth"] if denial == 401 else ["auth", "entitle"])


def test_assembled_app_exposes_the_child_on_the_original_router(owner, monkeypatch):
    import app.main as main
    import app.paywall as paywall
    calls = []
    def authenticate(_authorization):
        calls.append("auth"); return {"id": "test-detail-entitled"}
    def entitle(user, *, always=False):
        assert always is True; calls.append("entitle"); return user
    monkeypatch.setattr(main, "require_user", authenticate)
    monkeypatch.setattr(paywall, "enforce_site_full", entitle)
    assert main.prophet_daily_brief_router is owner.router
    response = TestClient(main.app).get(URL, params=query())
    assert response.status_code == 200 and response.json()["row"]["ticker"] == "TEST"
    assert calls == ["auth", "entitle"]; private(response)
