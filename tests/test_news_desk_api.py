"""Behavioral tests for private aggregate-news snapshot recovery."""
from __future__ import annotations

import asyncio
import copy
from datetime import datetime, timezone
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


@pytest.mark.parametrize("route", ["/api/news-desk/snapshot", "/api/news-desk/stream", "/api/news-desk/coverage", "/api/news-desk/history"])
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


@pytest.mark.parametrize("route", ["/api/news-desk/snapshot", "/api/news-desk/stream", "/api/news-desk/coverage", "/api/news-desk/history"])
@pytest.mark.parametrize("switch,entitled,expected_read", [
    (None, False, True), ("0", False, True), ("1", False, False), ("1", True, True),
])
def test_every_desk_route_uses_the_real_launch_switch_entitlement_owner(
    monkeypatch, route, switch, entitled, expected_read,
):
    # Only identity and the remote entitlement lookup are hermetic substitutes.
    # The actual canonical enforce_site_full policy decides before artifact I/O.
    import importlib
    paywall = importlib.import_module("app.paywall")
    identity = types.ModuleType("app.main")
    identity.require_user = lambda authorization, request: {"id": "fixture-registered"}
    monkeypatch.setitem(sys.modules, "app.main", identity)
    if switch is None:
        monkeypatch.delenv("PAYWALL_ENABLED", raising=False)
    else:
        monkeypatch.setenv("PAYWALL_ENABLED", switch)
    checked, reads = [], []
    def lookup(user_id, feature):
        checked.append((user_id, feature))
        return entitled, "pro" if entitled else "free"
    monkeypatch.setattr(paywall, "_entitled", lookup)
    def unavailable():
        reads.append(True)
        raise HTTPException(503, "fixture artifact deliberately absent")
    monkeypatch.setattr(desk, "_read_snapshot", unavailable)
    with client(monkeypatch) as c:
        response = c.get(route)
    assert response.status_code == (503 if expected_read else 403)
    assert bool(reads) is expected_read
    assert bool(checked) is (switch == "1")
    assert response.headers["cache-control"] == "private, no-store"
    if not expected_read:
        assert response.json()["detail"]["required_feature"] == "site_full"


@pytest.mark.parametrize("route", ["/api/news-desk/snapshot", "/api/news-desk/coverage", "/api/news-desk/history"])
def test_missing_artifact_is_private_503_after_auth(monkeypatch, tmp_path, route):
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(tmp_path / "absent.json"))
    with client(monkeypatch, lambda: {"id": "registered"}) as c:
        response = c.get(route)
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


def test_coverage_revision_observes_the_cached_pair_under_its_owner_lock(monkeypatch):
    payload = packet()
    expected = desk._revision(payload)
    class ObservedLock:
        depth = 0
        def __enter__(self):
            self.depth += 1
            return self
        def __exit__(self, *exc):
            self.depth -= 1
    lock = ObservedLock()
    class GuardedRevision(str):
        def __bool__(self):
            assert lock.depth > 0, "cached payload/revision pair must be read under the owner lock"
            return True
    monkeypatch.setattr(desk, "_cache_lock", lock)
    monkeypatch.setattr(desk, "_cache_payload", payload)
    monkeypatch.setattr(desk, "_cache_revision", GuardedRevision(expected))
    coverage = desk._build_coverage(payload, now=datetime(2026, 10, 18, 12, tzinfo=timezone.utc))
    assert coverage["artifact_revision"] == expected
    assert lock.depth == 0


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
            initial = (await anext(events)).decode("utf-8")
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
        event = (await anext(events)).decode("utf-8")
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


COVERAGE_NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def test_coverage_is_private_derived_metadata_and_does_not_mutate_live_snapshot(monkeypatch):
    payload = packet()
    payload["stories"][0].update(brief="private article body sentinel", drafts=["draft sentinel"])
    original = copy.deepcopy(payload)
    revision = desk._revision(payload)
    monkeypatch.setattr(desk, "_read_snapshot", lambda: payload)
    with client(monkeypatch, lambda: {"id": "registered"}) as c:
        response = c.get("/api/news-desk/coverage")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    assert {part.strip() for part in response.headers["vary"].split(",")} == {"Cookie", "Authorization"}
    data = response.json()
    assert data["schema"] == "intelligence.coverage/v1"
    assert data["artifact_revision"] == revision
    assert data["scope"]["collection"] == "current_aggregate_projection"
    assert data["scope"]["history_complete"] is False
    assert data["scope"]["publisher_to_screen_latency_measured"] is False
    assert "private article body sentinel" not in response.text
    assert "draft sentinel" not in response.text
    assert payload == original and desk._revision(payload) == revision


def test_coverage_separates_loaded_publisher_labels_from_feed_health_and_declared_regions():
    payload = {"schema": desk.SCHEMA, "updated_at": "2026-10-19T10:00:00Z", "stories": [
        {"id": "official", "feed_id": "fed", "source_name": "Federal Reserve", "language": "en",
         "category": "central_banks", "coverage_regions": ["global", "americas", "global"],
         "publisher_country": "US", "evidence": [{"name": "Federal Reserve"}, {"name": "Federal Reserve"}]},
        {"id": "discovery", "feed_id": "gdelt", "source_name": "Outlet", "language": "ja",
         "category": "economy", "coverage_regions": ["global"], "publisher_country": "Japan"},
        {"id": "legacy", "evidence": [{"name": "Federal Reserve"}]}],
        "source_health": [
            {"id": "fed", "publisher": "Federal Reserve", "enabled": True, "status": "observed",
             "last_attempt_at": "2026-10-19T10:00:00Z", "last_fetch_success_at": "2026-10-19T10:00:00Z"},
            {"id": "gdelt", "enabled": True, "status": "degraded", "last_error": "TimeoutError"},
            {"id": "held", "enabled": False, "status": "held"}],
    }
    result = desk._build_coverage(payload, now=COVERAGE_NOW)
    loaded = result["loaded_coverage"]
    publishers = {row["value"]: row["stories"] for row in loaded["publisher_labels"]["values"]}
    assert publishers == {"Federal Reserve": 2, "Outlet": 1}
    assert loaded["stories"] == 3
    assert loaded["feed_ids"]["missing_stories"] == 1
    assert loaded["declared_regions"]["values"][0] == {"value": "global", "stories": 2}
    assert result["scope"]["geographic_completeness_measured"] is False
    assert result["scope"]["publisher_independence_measured"] is False
    sources = {row["id"]: row for row in result["source_observations"]["rows"]}
    assert sources["fed"]["loaded_stories"] == 1
    assert sources["fed"]["observation_state"] == "checked"
    assert sources["fed"]["clocks"]["last_attempt_at"]["age_seconds"] == 7200
    assert sources["gdelt"]["observation_state"] == "degraded"
    assert sources["held"]["observation_state"] == "held"
    assert result["source_observations"]["stories_without_observed_feed"] == 1
    assert result["artifact_export_clock"]["age_seconds"] == 7200


def test_a_successful_check_without_outcome_counters_is_not_invented_as_empty():
    payload = packet()
    payload["stories"] = []
    payload["source_health"] = [{
        "id": "quiet", "enabled": True, "status": "observed",
        "last_attempt_at": "2026-10-19T11:00:00Z",
        "last_fetch_success_at": "2026-10-19T11:00:00Z",
    }]
    row = desk._build_coverage(payload, now=COVERAGE_NOW)["source_observations"]["rows"][0]
    assert row["loaded_stories"] == 0
    assert row["observation_state"] == "checked"
    assert row["last_outcome"] == "unknown"
    assert row["last_http_status"] is None
    assert all(row[key] is None for key in desk._SOURCE_COUNTS)
    assert row["last_attempt_duration_ms"] is None


@pytest.mark.parametrize("outcome,observed,eligible,filtered,status", [
    ("empty", 0, 0, 0, 200), ("filtered", 12, 0, 12, 200),
    ("unchanged", 0, 0, 0, 304), ("accepted", 12, 8, 3, 200),
])
def test_published_source_outcomes_retain_distinct_count_and_attempt_clock_meanings(
    outcome, observed, eligible, filtered, status,
):
    payload = packet()
    payload["source_health"] = [{
        "id": "feed", "enabled": True, "status": "observed",
        "last_attempt_at": "2026-10-19T11:00:00Z",
        "last_fetch_success_at": "2026-10-19T11:00:00Z",
        "last_attempt_started_at": "2026-10-19T11:00:01Z",
        "last_attempt_completed_at": "2026-10-19T11:00:03.5Z",
        "last_attempt_duration_ms": 2500, "last_outcome": outcome,
        "last_http_status": status, "last_observed_item_count": observed,
        "last_eligible_item_count": eligible, "last_filtered_item_count": filtered,
        "last_duplicate_item_count": 1 if outcome == "accepted" else 0,
        "last_changed_item_count": 8 if outcome == "accepted" else 0,
    }]
    row = desk._build_coverage(payload, now=COVERAGE_NOW)["source_observations"]["rows"][0]
    assert row["last_outcome"] == outcome
    assert row["last_observed_item_count"] == observed
    assert row["last_eligible_item_count"] == eligible
    assert row["last_filtered_item_count"] == filtered
    assert row["last_http_status"] == status
    assert row["last_attempt_duration_ms"] == 2500
    assert row["clocks"]["last_attempt_completed_at"]["at"] == "2026-10-19T11:00:03.500000Z"
    assert row["clocks"]["last_attempt_at"]["at"] == "2026-10-19T11:00:00Z"


def test_recorded_clock_differences_do_not_alias_indexing_to_publication_or_hide_bad_clocks():
    payload = packet()
    payload["stories"] = [
        {"id": "valid", "published_at": "2026-10-19T11:59:00Z", "first_seen": "2026-10-19T11:59:30Z",
         "source_updated_at": "2026-10-19T11:59:10Z", "provider_indexed_at": "2026-10-19T11:59:20Z",
         "accepted_revision_at": "2026-10-19T11:59:45Z"},
        {"id": "reverse", "published_at": "2026-10-19T11:59:55Z", "first_seen": "2026-10-19T11:59:50Z"},
        {"id": "future", "published_at": "2026-10-19T12:00:01Z", "first_seen": "2026-10-19T11:59:50Z"},
        {"id": "naive", "published_at": "2026-10-19T11:59:00", "first_seen": "2026-10-19T11:59:50Z"},
        {"id": "indexed_only", "provider_indexed_at": "2026-10-19T11:59:30Z",
         "accepted_revision_at": "2026-10-19T11:59:45Z"},
    ]
    result = desk._build_coverage(payload, now=COVERAGE_NOW)
    timing = result["recorded_timing"]
    assert timing["acceptance_and_export_clock_basis"] == "collector_tick"
    assert timing["completion_latency_measured"] is False
    publication, amendment, indexing = timing["differences"]
    assert publication["sample_count"] == 1 and publication["p95"] == 30
    assert publication["excluded"] == {
        "reverse_clock_order": 1, "start_future": 1, "start_invalid": 1, "start_missing": 1,
    }
    assert amendment["sample_count"] == 1 and amendment["p95"] == 35
    assert indexing["sample_count"] == 2 and indexing["max"] == 25
    assert timing["clocks"]["published_at"] == {
        "valid": 2, "missing": 1, "invalid": 1, "future": 1, "latest_at": "2026-10-19T11:59:55Z",
    }


def test_missing_or_future_clocks_do_not_report_zero_latency_or_freshness():
    payload = packet()
    payload["updated_at"] = "2027-01-01T00:00:00Z"
    payload["source_health"] = [{
        "id": "future", "enabled": True, "status": "observed",
        "last_attempt_at": "2027-01-01T00:00:00Z", "last_fetch_success_at": "2027-01-01T00:00:00Z",
    }]
    result = desk._build_coverage(payload, now=COVERAGE_NOW)
    assert result["artifact_export_clock"]["state"] == "future"
    assert result["artifact_export_clock"]["age_seconds"] is None
    row = result["source_observations"]["rows"][0]
    assert row["observation_state"] == "unknown"
    assert row["clocks"]["last_fetch_success_at"]["age_seconds"] is None
    for metric in result["recorded_timing"]["differences"]:
        assert metric["sample_count"] == 0
        assert metric["p50"] is None and metric["p95"] is None and metric["p99"] is None


def test_conflicting_health_identity_is_unobserved_and_arbitrary_error_text_is_not_exposed():
    payload = packet()
    payload["stories"][0]["feed_id"] = "collision"
    payload["source_health"] = [
        {"id": "collision", "enabled": True, "status": "observed"},
        {"id": "collision", "enabled": True, "status": "degraded"}, None,
        {"id": "invalid", "enabled": "yes", "status": {}, "last_outcome": {"bad": True},
         "last_error": "secret path sentinel", "last_error_code": "secret path sentinel",
         "last_http_status": True, "last_observed_item_count": 10**500,
         "last_eligible_item_count": False, "last_attempt_duration_ms": -5},
    ]
    result = desk._build_coverage(payload, now=COVERAGE_NOW)
    sources = result["source_observations"]
    assert sources["duplicate_source_ids"] == 1 and sources["invalid_rows"] == 1
    assert sources["stories_without_observed_feed"] == 1
    assert sources["source_count"] == 1
    row = sources["rows"][0]
    assert row["id"] == "invalid" and row["enabled"] is None
    assert row["last_outcome"] == "unknown"
    assert row["last_http_status"] is None and row["last_observed_item_count"] is None
    assert row["last_eligible_item_count"] is None and row["last_attempt_duration_ms"] is None
    assert "secret path sentinel" not in json.dumps(result)


def test_coverage_counts_all_admitted_labels_and_discloses_response_truncation():
    payload = packet()
    payload["stories"] = [{"id": "many", "coverage_regions": ["region" + str(i) for i in range(103)],
                           "evidence": [{"name": "publisher" + str(i)} for i in range(75)]}]
    result = desk._build_coverage(payload, now=COVERAGE_NOW)["loaded_coverage"]
    assert result["publisher_labels"]["distinct_labels"] == 75
    assert result["declared_regions"]["distinct_labels"] == 103
    assert len(result["declared_regions"]["values"]) == 100
    assert result["declared_regions"]["omitted_labels"] == 3
    assert result["declared_regions"]["omitted_story_memberships"] == 3


def _history_pair(monkeypatch, tmp_path, *, as_of=None):
    as_of = as_of or datetime.now(timezone.utc).replace(microsecond=0)
    stamp = as_of.isoformat().replace("+00:00", "Z")
    health = [{"id": "official", "enabled": True, "status": "observed", "content_use": "attributed_feed_excerpt"}]
    rows = [{"schema": desk.retained.PACKET_SCHEMA, "id": sid, "purpose": "research", "stage": "reported",
             "headline": "Policy report " + sid, "brief": "Attributed excerpt", "feed_id": "official",
             "source_name": "Official Source", "content_use": "attributed_feed_excerpt",
             "published_at": stamp, "first_seen": stamp, "accepted_revision_at": stamp,
             "url": "https://example.gov/" + sid} for sid in ("a", "b", "c")]
    projection = desk.retained.build_projection(rows, source_health=health, as_of=as_of,
                                              retention_hours=72, max_stories=1500)
    aggregate = {"schema": desk.SCHEMA, "updated_at": projection["as_of"], "source_health": health,
                 "stories": projection["stories"][:1], "retained_history": desk.retained.descriptor(projection)}
    main, private = tmp_path / "desk.json", tmp_path / "private-history.json"
    main.write_text(json.dumps(aggregate))
    desk.retained.atomic_write(private, projection)
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(main))
    monkeypatch.setenv("MM_NEWS_DESK_HISTORY_SNAPSHOT", str(private))
    return aggregate, projection, main, private


def test_history_route_returns_private_bounded_pages_without_touching_files_or_sqlite(monkeypatch, tmp_path):
    import sqlite3
    aggregate, projection, main, private = _history_pair(monkeypatch, tmp_path)
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (main, private)}
    def forbidden(*args, **kwargs):
        raise AssertionError("the read API may not open a database")
    monkeypatch.setattr(sqlite3, "connect", forbidden)
    with client(monkeypatch, lambda: {"id": "registered"}) as c:
        response = c.get("/api/news-desk/history", params={"limit": 1})
        assert response.status_code == 200
        first = response.json()
        following = c.get("/api/news-desk/history", params={"limit": 1, "cursor": first["next_cursor"]})
    assert first["schema"] == "intelligence.history_page/v1"
    assert first["revision"] == aggregate["retained_history"]["revision"]
    assert first["collection"] == "retained_current_packets"
    assert first["matched_count"] == 3 and first["returned_count"] == 1
    assert first["query"] == {"q": "", "source": "", "feed_id": "", "category": "", "language": "",
                              "from_at": None, "to_at": None, "limit": 1}
    assert first["stories"][0]["id"] == "a" and following.json()["stories"][0]["id"] == "b"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Cookie, Authorization"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"
    assert before == {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in (main, private)}


def test_history_cursor_after_correction_is_a_private_deliberate_restart(monkeypatch, tmp_path):
    aggregate, projection, main, private = _history_pair(monkeypatch, tmp_path)
    with client(monkeypatch, lambda: {"id": "registered"}) as c:
        first = c.get("/api/news-desk/history", params={"limit": 1}).json()
        projection["stories"][0]["headline"] = "Correction replaces the previous report"
        desk.retained.atomic_write(private, projection)
        aggregate["retained_history"] = desk.retained.descriptor(projection)
        main.write_text(json.dumps(aggregate))
        response = c.get("/api/news-desk/history", params={"limit": 1, "cursor": first["next_cursor"]})
    assert response.status_code == 409
    assert response.json() == {"detail": {"code": "history_revision_changed", "restart_required": True}}
    assert response.headers["cache-control"] == "private, no-store"


def test_history_mismatched_publications_and_rights_never_serve_an_old_page(monkeypatch, tmp_path):
    aggregate, projection, main, private = _history_pair(monkeypatch, tmp_path)
    now = datetime.now(timezone.utc)
    assert desk._read_current_history(now=now) == projection
    projection["stories"][0]["headline"] = "New private generation awaiting main publication"
    desk.retained.atomic_write(private, projection)
    with pytest.raises(HTTPException) as exc:
        desk._read_current_history(now=now)
    assert exc.value.status_code == 503
    aggregate["retained_history"] = desk.retained.descriptor(projection)
    aggregate["source_health"][0]["enabled"] = False
    main.write_text(json.dumps(aggregate))
    with pytest.raises(HTTPException) as exc:
        desk._read_current_history(now=now)
    assert exc.value.status_code == 503
    aggregate["retained_history"] = desk.retained.unavailable("publish_failed")
    main.write_text(json.dumps(aggregate))
    with pytest.raises(HTTPException):
        desk._read_current_history(now=now)


def test_history_checks_current_descriptor_again_after_private_read(monkeypatch, tmp_path):
    aggregate, projection, main, private = _history_pair(monkeypatch, tmp_path)
    changed = copy.deepcopy(aggregate)
    changed["retained_history"] = desk.retained.unavailable("publish_failed")
    snapshots = iter([aggregate, changed])
    monkeypatch.setattr(desk, "_read_snapshot", lambda: next(snapshots))
    with pytest.raises(HTTPException) as exc:
        desk._read_current_history()
    assert exc.value.status_code == 503


@pytest.mark.parametrize("private_offset,main_offset", [(-301, -301), (-301, 0), (1, 1), (0, 1), (0, -1)])
def test_history_expired_future_or_reversed_export_clocks_are_unavailable(monkeypatch, tmp_path, private_offset, main_offset):
    from datetime import timedelta
    aggregate, projection, main, private = _history_pair(monkeypatch, tmp_path, as_of=COVERAGE_NOW + timedelta(seconds=private_offset))
    aggregate["updated_at"] = (COVERAGE_NOW + timedelta(seconds=main_offset)).isoformat().replace("+00:00", "Z")
    main.write_text(json.dumps(aggregate))
    with pytest.raises(HTTPException) as exc:
        desk._read_current_history(now=COVERAGE_NOW)
    assert exc.value.status_code == 503


@pytest.mark.parametrize("replacement", ["delete", "malformed", "symlink", "oversized"])
def test_history_invalid_replacement_cannot_reuse_previously_good_cache(monkeypatch, tmp_path, replacement):
    aggregate, projection, main, private = _history_pair(monkeypatch, tmp_path)
    assert desk._read_current_history() == projection
    if replacement == "delete":
        private.unlink()
    elif replacement == "malformed":
        private.write_bytes(b'{"schema":')
    elif replacement == "symlink":
        other = tmp_path / "other.json"
        private.rename(other)
        private.symlink_to(other)
    else:
        monkeypatch.setattr(desk.retained, "MAX_BYTES", private.stat().st_size - 1)
    with pytest.raises(HTTPException) as exc:
        desk._read_current_history()
    assert exc.value.status_code == 503


@pytest.mark.parametrize("params,code,detail", [
    ({"from_at": "2026-10-19T12:00:00"}, 400, {"code": "invalid_history_query"}),
    ({"cursor": "!"}, 400, {"code": "invalid_history_cursor"}),
    ({"q": "x" * 257}, 422, None),
    ({"limit": 101}, 422, None),
])
def test_history_query_and_cursor_errors_are_private(monkeypatch, tmp_path, params, code, detail):
    _history_pair(monkeypatch, tmp_path)
    with client(monkeypatch, lambda: {"id": "registered"}) as c:
        response = c.get("/api/news-desk/history", params=params)
    assert response.status_code == code
    assert response.headers["cache-control"] == "private, no-store"
    if detail is not None:
        assert response.json() == {"detail": detail}


def test_history_every_page_reenters_canonical_access_before_read(monkeypatch, tmp_path):
    _history_pair(monkeypatch, tmp_path)
    permitted = True
    reads = []
    original = desk._read_history_file
    def observe():
        reads.append(True)
        return original()
    def authorize():
        if not permitted:
            raise HTTPException(403, "access changed")
        return {"id": "registered"}
    monkeypatch.setattr(desk, "_read_history_file", observe)
    with client(monkeypatch, authorize) as c:
        first = c.get("/api/news-desk/history", params={"limit": 1})
        assert first.status_code == 200
        permitted = False
        response = c.get("/api/news-desk/history", params={"limit": 1, "cursor": first.json()["next_cursor"]})
    assert response.status_code == 403 and len(reads) == 1
    assert response.headers["cache-control"] == "private, no-store"


def test_snapshot_delivery_reuses_encoded_frames_but_never_an_old_export_clock(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path = tmp_path / "desk.json"
    payload = packet()
    path.write_text(json.dumps(payload))
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(path))
    event = desk._event
    encoded = []
    def observe(name, data, revision=None):
        encoded.append(name)
        return event(name, data, revision)
    monkeypatch.setattr(desk, "_event", observe)
    with ThreadPoolExecutor(max_workers=8) as pool:
        frames = list(pool.map(lambda _: desk._read_snapshot_delivery(), range(32)))
    assert encoded == ["snapshot"]
    assert all(row[1] is frames[0][1] and row[2] is frames[0][2] for row in frames)
    assert frames[0][1].startswith(b"retry: 1500\nid: ")
    previous = frames[0]
    payload["updated_at"] = "2026-10-18T12:01:15Z"
    replacement = tmp_path / "replacement.json"
    replacement.write_text(json.dumps(payload))
    replacement.replace(path)
    current = desk._read_snapshot_delivery()
    assert current[0] == previous[0] and current[2] != previous[2]
    assert b"2026-10-18T12:01:15Z" in current[2]
    assert encoded == ["snapshot", "snapshot"]
    path.write_bytes(b"invalid replacement")
    with pytest.raises(HTTPException) as exc:
        desk._read_snapshot_delivery()
    assert exc.value.status_code == 503


def test_private_history_read_lock_cannot_block_aggregate_delivery(monkeypatch, tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    path = tmp_path / "desk.json"
    path.write_text(json.dumps(packet()))
    monkeypatch.setenv("MM_NEWS_DESK_SNAPSHOT", str(path))
    with ThreadPoolExecutor(max_workers=1) as pool:
        with desk._history_cache_lock:
            delivery = pool.submit(desk._read_snapshot_delivery).result(timeout=2)
    assert b"event: snapshot" in delivery[2]
