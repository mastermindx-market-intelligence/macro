"""Behavioral tests for private aggregate-news snapshot recovery."""
from __future__ import annotations

import asyncio
import copy
import json
import sys
import types

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from app import news_desk as desk


def packet():
    return {"schema": desk.SCHEMA, "updated_at": "2026-10-18T12:00:00Z",
            "health": {"state": "quiet"},
            "stories": [{"id": "one", "headline": "Original report",
                         "evidence": [{"name": "Source", "url": "https://example.com/report"}]}]}


def client(monkeypatch, auth=None):
    app = FastAPI()
    app.include_router(desk.router)
    if auth is not None:
        app.dependency_overrides[desk.require_desk_user] = auth
    return TestClient(app)


@pytest.mark.parametrize("route", ["/api/news-desk/snapshot", "/api/news-desk/stream"])
def test_auth_precedes_any_artifact_read(monkeypatch, route):
    reads = []
    monkeypatch.setattr(desk, "_read_snapshot", lambda: reads.append(True))
    def deny():
        raise HTTPException(401, "sign in")
    with client(monkeypatch, deny) as c:
        response = c.get(route)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "private, no-store"
    assert "Cookie" in response.headers["vary"]
    assert not reads


def test_cookie_request_is_passed_to_canonical_identity(monkeypatch):
    identity = types.ModuleType("app.main")
    paywall = types.ModuleType("app.paywall")
    seen = {}
    def require_user(authorization, request):
        seen.update(authorization=authorization, cookie=request.headers.get("cookie"))
        return {"id": "registered"}
    def enforce(user):
        seen["enforced"] = user["id"]
        return user
    identity.require_user = require_user
    paywall.enforce_site_full = enforce
    monkeypatch.setitem(sys.modules, "app.main", identity)
    monkeypatch.setitem(sys.modules, "app.paywall", paywall)
    monkeypatch.setattr(desk, "_read_snapshot", packet)
    with client(monkeypatch) as c:
        response = c.get("/api/news-desk/snapshot", headers={"cookie": "incumbent=session"})
    assert response.status_code == 200
    assert seen == {"authorization": None, "cookie": "incumbent=session", "enforced": "registered"}


def test_missing_artifact_is_private_503_after_auth(monkeypatch, tmp_path):
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(tmp_path / "absent.json"))
    with client(monkeypatch, lambda: {"id": "registered"}) as c:
        response = c.get("/api/news-desk/snapshot")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "private, no-store"
    assert response.json() == {"detail": "news desk temporarily unavailable"}


@pytest.mark.parametrize("payload", [
    {}, {"schema": desk.SCHEMA, "stories": {}},
    {"schema": desk.SCHEMA, "stories": [{"id": ""}]},
    {"schema": desk.SCHEMA, "stories": [{"id": "a"}, {"id": "a"}]},
    {"schema": desk.SCHEMA, "stories": [None]},
    {"schema": desk.SCHEMA, "stories": [{"id": "a", "value": float("nan")}]},
    {"schema": desk.SCHEMA, "stories": [{"id": str(i)} for i in range(1001)]},
])
def test_malformed_artifact_fails_closed(monkeypatch, tmp_path, payload):
    path = tmp_path / "desk.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(path))
    with pytest.raises(HTTPException) as exc:
        desk._read_snapshot()
    assert exc.value.status_code == 503


def test_read_size_is_bounded(monkeypatch, tmp_path):
    path = tmp_path / "desk.json"
    path.write_bytes(b" " * (desk.MAX_BYTES + 1))
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(path))
    with pytest.raises(HTTPException):
        desk._read_snapshot()


def test_export_clock_does_not_invent_a_news_revision():
    old = packet()
    new = copy.deepcopy(old)
    new["updated_at"] = "2026-10-18T12:01:15Z"
    assert desk._revision(new) == desk._revision(old)
    new["stories"][0]["headline"] = "Corrected report"
    assert desk._revision(new) != desk._revision(old)


class Connection:
    async def is_disconnected(self):
        return False


def test_every_reconnect_starts_with_the_complete_snapshot():
    async def check():
        for _ in range(2):
            events = desk._events(Connection(), packet(), connection_seconds=0)
            initial = await anext(events)
            assert "event: snapshot" in initial
            assert "Original report" in initial
            assert "id: " in initial
            assert "event: reconnect" in await anext(events)
            with pytest.raises(StopAsyncIteration):
                await anext(events)
    asyncio.run(check())


@pytest.mark.parametrize("change", ["correction", "removal"])
def test_replacement_delivers_corrections_and_removals(monkeypatch, change):
    old = packet()
    new = copy.deepcopy(old)
    if change == "correction":
        new["stories"][0]["headline"] = "Corrected report"
    else:
        new["stories"] = []
    monkeypatch.setattr(desk, "_read_snapshot", lambda: new)
    async def check():
        events = desk._events(Connection(), old, poll_seconds=0)
        await anext(events)
        event = await anext(events)
        data = json.loads(event.split("data: ", 1)[1])
        assert data == new
        await events.aclose()
    asyncio.run(check())


def test_artifact_failure_terminates_with_unavailable(monkeypatch):
    def failed():
        raise desk._unavailable()
    monkeypatch.setattr(desk, "_read_snapshot", failed)
    async def check():
        events = desk._events(Connection(), packet(), poll_seconds=0)
        await anext(events)
        assert "event: unavailable" in await anext(events)
        with pytest.raises(StopAsyncIteration):
            await anext(events)
    asyncio.run(check())


def test_disconnected_reader_stops_without_more_disk_reads(monkeypatch):
    reads = []
    monkeypatch.setattr(desk, "_read_snapshot", lambda: reads.append(True))
    class Disconnected:
        async def is_disconnected(self):
            return True
    async def check():
        events = desk._events(Disconnected(), packet(), poll_seconds=0)
        await anext(events)
        with pytest.raises(StopAsyncIteration):
            await anext(events)
    asyncio.run(check())
    assert not reads


def test_read_cache_shares_validated_bytes_but_replacement_and_deletion_invalidate(monkeypatch, tmp_path):
    path = tmp_path / "desk.json"
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(path))
    path.write_text(json.dumps(packet()))
    loader = desk._load_snapshot_file
    reads = []
    def load(p):
        reads.append(p)
        return loader(p)
    monkeypatch.setattr(desk, "_load_snapshot_file", load)
    original = desk._read_snapshot()
    for _ in range(25):
        assert desk._read_snapshot() is original
    assert len(reads) == 1
    revised = packet()
    revised["stories"] = []
    replacement = tmp_path / "replacement.json"
    replacement.write_text(json.dumps(revised))
    replacement.replace(path)
    current = desk._read_snapshot()
    assert current["stories"] == [] and current is not original
    assert len(reads) == 2
    path.write_text("broken")
    with pytest.raises(HTTPException):
        desk._read_snapshot()
    path.unlink()
    with pytest.raises(HTTPException):
        desk._read_snapshot()


def test_atomic_replace_during_read_never_caches_old_bytes_under_new_identity(monkeypatch, tmp_path):
    path = tmp_path / "desk.json"
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(path))
    path.write_text(json.dumps(packet()))
    loader = desk._load_snapshot_file
    def replace_after_read(p):
        old = loader(p)
        replacement = tmp_path / "next.json"
        revised = packet()
        revised["stories"] = []
        replacement.write_text(json.dumps(revised))
        replacement.replace(path)
        monkeypatch.setattr(desk, "_load_snapshot_file", loader)
        return old
    monkeypatch.setattr(desk, "_load_snapshot_file", replace_after_read)
    assert desk._read_snapshot()["stories"]
    assert desk._read_snapshot()["stories"] == []

