"""Private Macro API tests for the live ticker-news read plane."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import normalize_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)


def _routed(item_id=1, title="Nvidia launches accelerator", minute=0, *, teaser=None):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": f"teaser:{title}" if teaser is None else teaser,
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=t + timedelta(seconds=2),
    )
    return store_mod.RoutedRevision(
        revision=revision,
        security_ids=("SEC:US-XNAS-NVDA",),
        universe_revision="sp500-r1",
    )


def _make_db(tmp_path):
    db = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="c1")
    return db


def _app(monkeypatch, tmp_path, *, rights=True):
    from app import ticker_news

    db = _make_db(tmp_path)
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: (
            "SEC:US-XNAS-NVDA" if ticker.upper() == "NVDA" else None
        ),
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: (
            store_mod.NewsReadRights.all_internal() if rights else None
        ),
    )
    monkeypatch.setattr(
        ticker_news,
        "_source_health",
        lambda: {
            "state": "live",
            "last_successful_catchup": "2026-10-05T20:00:00+00:00",
        },
    )
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
        "id": "user-1",
        "email": "user@example.test",
    }
    return ticker_news, app, db


def test_snapshot_is_authenticated_private_and_returns_cluster_rows(monkeypatch, tmp_path):
    ticker_news, app, _db = _app(monkeypatch, tmp_path)
    response = TestClient(app).get("/api/ticker-news/NVDA?limit=20")

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "ticker_news.snapshot.v1"
    assert body["ticker"] == "NVDA"
    assert body["security_id"] == "SEC:US-XNAS-NVDA"
    assert body["state"] == "live"
    assert len(body["rows"]) == 1
    assert isinstance(body["rows"][0]["story_id"], str)
    assert body["rows"][0]["story_id"]
    assert body["rows"][0]["title"] == "Nvidia launches accelerator"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["vary"] == "Authorization"
    assert response.headers["x-robots-tag"] == "noindex, noarchive"


def test_auth_denial_happens_before_store_open(monkeypatch, tmp_path):
    from app import ticker_news

    opened = []
    monkeypatch.setattr(
        ticker_news,
        "_open_store",
        lambda: opened.append(True),
    )
    app = FastAPI()
    app.include_router(ticker_news.router)

    def deny():
        raise HTTPException(status_code=401, detail="authentication required")

    app.dependency_overrides[ticker_news.require_site_full_user] = deny
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 401
    assert opened == []


def test_unknown_source_rights_fail_closed_before_store_open(monkeypatch, tmp_path):
    from app import ticker_news

    opened = []
    monkeypatch.setattr(ticker_news, "_rights_for_user", lambda user: None)
    monkeypatch.setattr(ticker_news, "_open_store", lambda: opened.append(True))
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "u"}

    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 503
    assert response.json()["detail"] == "ticker news rights unavailable"
    assert opened == []


def test_unknown_ticker_is_404_without_guessing_security_id(monkeypatch, tmp_path):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    response = TestClient(app).get("/api/ticker-news/ZZZZ")

    assert response.status_code == 404
    assert response.json()["detail"] == "ticker not in qualified news universe"


def test_changes_are_ticker_scoped_and_resume_after_sequence(monkeypatch, tmp_path):
    ticker_news, app, db = _app(monkeypatch, tmp_path)
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [_routed(item_id=2, title="Nvidia second story", minute=2)],
            expected_cursor="c1",
            next_cursor="c2",
        )

    response = TestClient(app).get(
        "/api/ticker-news/NVDA/changes?after_sequence=1&limit=20"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schema"] == "ticker_news.changes.v1"
    assert body["ticker"] == "NVDA"
    assert [row["source_item_id"] for row in body["rows"]] == ["2"]
    assert body["next_sequence"] == body["rows"][-1]["sequence"]


def test_story_detail_respects_store_rights_and_missing_story_is_404(monkeypatch, tmp_path):
    ticker_news, app, db = _app(monkeypatch, tmp_path)
    with store_mod.NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        story_id = store.snapshot(
            "SEC:US-XNAS-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows[0].story_id

    ok = TestClient(app).get(f"/api/ticker-news/stories/{story_id}")
    missing = TestClient(app).get("/api/ticker-news/stories/cluster_missing")

    assert ok.status_code == 200
    assert ok.json()["schema"] == "ticker_news.story.v1"
    assert ok.json()["story_id"] == story_id
    assert ok.json()["item_count"] == 1
    assert missing.status_code == 404


def test_store_unavailable_is_503_not_empty_200(monkeypatch, tmp_path):
    from app import ticker_news

    monkeypatch.setattr(
        ticker_news,
        "_news_db_path",
        lambda: tmp_path / "missing.sqlite3",
    )
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "u"}

    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 503
    assert response.json()["detail"] == "ticker news temporarily unavailable"


def test_sse_cycle_rechecks_rights_and_emits_removal_before_stopping(monkeypatch, tmp_path):
    from app import ticker_news

    db = _make_db(tmp_path)
    current_rights = [store_mod.NewsReadRights.all_internal()]
    monkeypatch.setattr(
        ticker_news,
        "_news_db_path",
        lambda: db,
    )
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: current_rights[0],
    )

    async def collect():
        out = []
        async for chunk in ticker_news._sse_events(
            ticker="NVDA",
            user={"id": "u"},
            after_sequence=0,
            poll_seconds=0,
            max_cycles=2,
        ):
            out.append(chunk)
            if chunk.startswith("event: upsert"):
                current_rights[0] = None
        return out

    chunks = asyncio.run(collect())
    joined = "".join(chunks)

    assert "event: upsert" in joined
    assert "Nvidia launches accelerator" in joined
    assert "event: restricted" in joined
    assert "ticker news rights" in joined


def test_rate_limit_is_bounded_per_authenticated_user(monkeypatch, tmp_path):
    ticker_news, app, _db = _app(monkeypatch, tmp_path)
    monkeypatch.setattr(ticker_news, "_RATE_LIMIT_REQUESTS", 2)
    client = TestClient(app)

    assert client.get("/api/ticker-news/NVDA").status_code == 200
    assert client.get("/api/ticker-news/NVDA").status_code == 200
    third = client.get("/api/ticker-news/NVDA")

    assert third.status_code == 429
    assert third.headers["retry-after"] == "60"


def test_live_source_with_no_ticker_rows_reports_quiet(monkeypatch, tmp_path):
    from app import ticker_news

    db = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest"):
        pass
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )
    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )
    monkeypatch.setattr(ticker_news, "_source_health", lambda: {"state": "live"})
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {"id": "u"}

    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    assert response.json()["state"] == "quiet"


def test_production_app_mounts_all_private_ticker_news_routes() -> None:
    import app.main as main_mod

    paths = main_mod.app.openapi().get("paths", {})
    expected = {
        "/api/ticker-news/{ticker}",
        "/api/ticker-news/{ticker}/changes",
        "/api/ticker-news/{ticker}/stream",
        "/api/ticker-news/stories/{story_id}",
    }
    assert expected <= set(paths)

    client = TestClient(main_mod.app, raise_server_exceptions=False)
    # Every paid news route must hit authentication, never fall through to a 404.
    assert client.get("/api/ticker-news/NVDA").status_code == 401
    assert client.get("/api/ticker-news/NVDA/changes").status_code == 401
    assert client.get("/api/ticker-news/NVDA/stream").status_code == 401
    assert client.get("/api/ticker-news/stories/ev2_missing").status_code == 401


def test_snapshot_default_initial_page_is_twenty(monkeypatch, tmp_path):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    seen = []
    original = store_mod.NewsStore.snapshot

    def wrapped(self, security_id, *, limit, cursor, rights):
        seen.append(limit)
        return original(
            self,
            security_id,
            limit=limit,
            cursor=cursor,
            rights=rights,
        )

    monkeypatch.setattr(store_mod.NewsStore, "snapshot", wrapped)
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    assert seen == [20]


def test_quiet_sse_heartbeats_keep_margin_before_edge_idle_timeout(monkeypatch, tmp_path):
    """A quiet connection must emit bytes well before the edge's 15s idle limit."""
    from types import SimpleNamespace
    from app import ticker_news

    now = [100.0]
    pauses = []
    reads = []
    scope_checks = []
    rights = store_mod.NewsReadRights.all_internal()

    class ImmediateScopeReader:
        async def read(self, reader):
            return reader()

    class QuietChangeReader:
        async def read(self, key, reader):
            reads.append(key[2])
            return SimpleNamespace(rows=(), next_sequence=7, has_more=False)

    def current_scope(user):
        scope_checks.append(now[0])
        return rights, False

    async def advance(seconds):
        pauses.append(seconds)
        now[0] = round(now[0] + seconds, 6)

    monkeypatch.setattr(ticker_news, "time", SimpleNamespace(monotonic=lambda: now[0]))
    monkeypatch.setattr(ticker_news, "asyncio", SimpleNamespace(sleep=advance))
    monkeypatch.setattr(ticker_news, "_STREAM_BLOCKING_READER", ImmediateScopeReader())
    monkeypatch.setattr(ticker_news, "_STREAM_CHANGE_READER", QuietChangeReader())
    monkeypatch.setattr(ticker_news, "_stream_scope", current_scope)
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: tmp_path / "unused.sqlite3")
    monkeypatch.setattr(
        ticker_news, "_security_or_404",
        lambda ticker, now: ("NVDA", "SEC:US-XNAS-NVDA"),
    )

    async def collect():
        return [
            (now[0], chunk)
            async for chunk in ticker_news._sse_events(
                ticker="NVDA", user={"id": "fixture"}, after_sequence=7,
                poll_seconds=0.1, max_cycles=201,
            )
        ]

    frames = asyncio.run(collect())
    times = [at for at, _chunk in frames]
    assert times[0] == 100.0  # Flush a quiet connection immediately.
    assert len(times) >= 5
    assert max(later - earlier for earlier, later in zip(times, times[1:])) <= 5.1
    assert all(chunk == ": heartbeat\n\n" for _at, chunk in frames)
    # The heartbeat only emits a comment; it must not add polling, move a cursor,
    # or replace the existing fresh permission check on each read cycle.
    assert reads == [7] * 201
    assert len(scope_checks) == 201
    assert pauses == [0.1] * 201
    assert not (tmp_path / "unused.sqlite3").exists()


def test_sse_revalidates_access_after_cached_read_before_delivery(monkeypatch, tmp_path):
    from app import ticker_news
    db = _make_db(tmp_path)
    current_rights = [store_mod.NewsReadRights.all_internal()]
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(ticker_news, "_security_for_ticker", lambda ticker, now: "SEC:US-XNAS-NVDA")
    monkeypatch.setattr(ticker_news, "_rights_for_user", lambda user: current_rights[0])
    class DelayedRead:
        async def read(self, key, read):
            page = read()
            current_rights[0] = None  # policy expires while the read was in flight
            return page
    monkeypatch.setattr(ticker_news, "_STREAM_CHANGE_READER", DelayedRead())
    async def collect():
        return [chunk async for chunk in ticker_news._sse_events(
            ticker="NVDA", user={"id": "fixture"}, after_sequence=0, poll_seconds=0, max_cycles=1)]
    output = "".join(asyncio.run(collect()))
    assert "event: restricted" in output
    assert "event: upsert" not in output
    assert "Nvidia launches accelerator" not in output


# Explicit editorial views use the actual qualified-universe seam. Legacy requests
# remain compatible; these cases exercise acknowledgement and continuation fences.
def _editorial_app(monkeypatch, tmp_path):
    import json
    from app import ticker_news

    resolver = ticker_news._security_for_ticker
    ticker_news, app, db = _app(monkeypatch, tmp_path)
    monkeypatch.setattr(ticker_news, "_security_for_ticker", resolver)
    now = datetime.now(UTC)
    universe = {
        "owner": "fixture.security_reference", "revision": "fixture-r1",
        "complete": True, "truncated": False,
        "effective_at": (now - timedelta(days=1)).isoformat(),
        "known_at": (now - timedelta(minutes=1)).isoformat(),
        "fresh_until": (now + timedelta(days=1)).isoformat(),
        "securities": [{
            "security_id": "SEC:US-XNAS-NVDA", "ticker": "NVDA", "aliases": ["NVDA"],
            "valid_from": (now - timedelta(days=100)).isoformat(), "valid_to": None,
            "known_at": (now - timedelta(minutes=1)).isoformat(),
        }],
    }
    path = tmp_path / "universe.json"
    path.write_text(json.dumps(universe))
    monkeypatch.setattr(ticker_news, "_universe_path", lambda: path)
    names = [["Nvidia"]]
    monkeypatch.setattr(ticker_news, "company_reference_names", lambda ticker: tuple(names[0]))
    monkeypatch.setattr(ticker_news, "_derivative_permitted_after_rights", lambda: True)
    monkeypatch.setattr(ticker_news, "_flow_now", lambda: T0 + timedelta(hours=1))
    with store_mod.NewsStore(db, source_key="benzinga-rest") as writer:
        writer.commit([
            _routed(2, "Benzinga Bulls And Bears: Nvidia, Apple", 2),
            _routed(3, "Astera opens a manufacturing facility", 3),
        ], expected_cursor="c1", next_cursor="c2")
    return ticker_news, TestClient(app), db, names


def test_editorial_views_filter_rows_groups_details_changes_and_flow(monkeypatch, tmp_path):
    ticker_news, client, _db, _names = _editorial_app(monkeypatch, tmp_path)
    bodies = {}
    for mode, count in (("all", 3), ("news", 2), ("company", 1)):
        response = client.get(f"/api/ticker-news/NVDA?view={mode}")
        assert response.status_code == 200, response.text
        body = bodies[mode] = response.json()
        assert len(body["rows"]) == count
        assert body["editorial_view"]["mode"] == mode
        assert body["editorial_view"]["rules"] == "ticker_news.editorial_rules.v2"
        assert body["editorial_view"]["name_coverage"] == "names_and_symbols"
        assert body["flow"]["reports_24h"] == count
        assert body["flow"]["provenance"]["editorial_view"] == body["editorial_view"]
        assert all(row["editorial_view"] == body["editorial_view"] for row in body["rows"])
        changes = client.get(f"/api/ticker-news/NVDA/changes?view={mode}").json()
        visible = [row for row in changes["rows"] if row["kind"] == "upsert"]
        assert len(visible) == count
        for row in body["rows"]:
            detail = client.get(
                f"/api/ticker-news/stories/{row['story_id']}?ticker=NVDA&view={mode}"
                f"&view_revision={body['editorial_view']['revision']}"
            )
            assert detail.status_code == 200, detail.text
            assert detail.json()["item_count"] == row["item_count"]
            assert detail.json()["editorial_view"] == body["editorial_view"]
    assert {row["source_item_id"] for row in bodies["company"]["rows"]} == {"1"}
    row = bodies["company"]["rows"][0]
    assert row["editorial"]["company_reference"] == "headline"
    assert row["editorial"]["format"] == "unclassified"
    assert "editorial_view" not in client.get("/api/ticker-news/NVDA").json()
    omitted = next(row for row in bodies["all"]["rows"] if row["source_item_id"] == "3")
    assert client.get(
        f"/api/ticker-news/stories/{omitted['story_id']}?ticker=NVDA&view=company"
    ).status_code == 404


def test_editorial_continuations_require_matching_context(monkeypatch, tmp_path):
    _api, client, _db, names = _editorial_app(monkeypatch, tmp_path)
    first = client.get("/api/ticker-news/NVDA?view=news&limit=1").json()
    revision = first["editorial_view"]["revision"]
    cursor = first["next_cursor"]
    assert cursor is not None
    assert client.get(f"/api/ticker-news/NVDA?view=news&cursor={cursor}").status_code == 422
    assert client.get(
        f"/api/ticker-news/NVDA?view=news&cursor={cursor}&view_revision={revision}"
    ).status_code == 200
    for path in (
        f"/api/ticker-news/NVDA?view=company&cursor={cursor}",
        "/api/ticker-news/NVDA/changes?view=company&after_sequence=1",
        f"/api/ticker-news/stories/{first['rows'][0]['story_id']}?ticker=NVDA&view=company",
    ):
        response = client.get(path + "&view_revision=" + revision)
        assert response.status_code == 409
        assert response.headers["cache-control"] == "private, no-store"
    names[0] = ["Nvidia", "NVIDIA Corporation"]
    assert client.get(
        f"/api/ticker-news/NVDA?view=news&cursor={cursor}&view_revision={revision}"
    ).status_code == 409
    assert client.get("/api/ticker-news/NVDA?view=unknown").status_code == 422
    assert client.get(
        f"/api/ticker-news/stories/{first['rows'][0]['story_id']}?view=news"
    ).status_code == 422


def test_editorial_revision_binds_current_display_and_derivative_rights(monkeypatch, tmp_path):
    api, client, _db, _names = _editorial_app(monkeypatch, tmp_path)
    initial = client.get("/api/ticker-news/NVDA?view=company").json()["editorial_view"]["revision"]
    rights = store_mod.NewsReadRights(allowed_sources=frozenset({"benzinga"}), allow_teaser=False)
    monkeypatch.setattr(api, "_rights_for_user", lambda user: rights)
    denied = client.get("/api/ticker-news/NVDA?view=company").json()["editorial_view"]["revision"]
    assert initial != denied
    monkeypatch.setattr(api, "_derivative_permitted_after_rights", lambda: False)
    response = client.get("/api/ticker-news/NVDA?view=company").json()
    assert denied != response["editorial_view"]["revision"]
    assert all(row["editorial"] is None for row in response["rows"])
    assert client.get(
        f"/api/ticker-news/NVDA/changes?view=company&after_sequence=1&view_revision={initial}"
    ).status_code == 409

    async def collect():
        return [chunk async for chunk in api._sse_events(
            ticker="NVDA", user={"id": "u"}, after_sequence=1,
            view="company", view_revision=initial, poll_seconds=0, max_cycles=1,
        )]
    chunks = asyncio.run(collect())
    assert len(chunks) == 1 and chunks[0].startswith("event: reset")
    assert "Nvidia launches" not in chunks[0]


def test_editorial_sse_revalidates_context_before_batch_and_separates_cache(monkeypatch, tmp_path):
    api, client, _db, names = _editorial_app(monkeypatch, tmp_path)
    revisions = {
        mode: client.get(f"/api/ticker-news/NVDA?view={mode}").json()["editorial_view"]["revision"]
        for mode in ("news", "company")
    }
    keys = []

    class ObservedReader:
        async def read(self, key, reader):
            keys.append(key)
            page = reader()
            if len(keys) == 2:
                names[0] = ["Alternate issuer"]
            return page

    monkeypatch.setattr(api, "_STREAM_CHANGE_READER", ObservedReader())

    async def collect(mode):
        return [chunk async for chunk in api._sse_events(
            ticker="NVDA", user={"id": "u"}, after_sequence=0,
            view=mode, view_revision=revisions[mode], poll_seconds=0, max_cycles=1,
        )]
    news = asyncio.run(collect("news"))
    company = asyncio.run(collect("company"))
    assert any(chunk.startswith("event: upsert") for chunk in news)
    assert len(company) == 1 and company[0].startswith("event: reset")
    assert keys[0][-1] == revisions["news"]
    assert keys[1][-1] == revisions["company"]
    assert keys[0] != keys[1]


def test_editorial_sse_resets_quiet_feed_when_name_context_changes(monkeypatch, tmp_path):
    from types import SimpleNamespace
    api, client, _db, names = _editorial_app(monkeypatch, tmp_path)
    revision = client.get("/api/ticker-news/NVDA?view=company").json()["editorial_view"]["revision"]
    clock = [100.0]

    class QuietReader:
        async def read(self, key, reader):
            names[0] = ["Alternate issuer"]
            clock[0] = 106.0
            return SimpleNamespace(rows=(), next_sequence=3, has_more=False)

    monkeypatch.setattr(api, "_STREAM_CHANGE_READER", QuietReader())
    monkeypatch.setattr(api, "time", SimpleNamespace(monotonic=lambda: clock[0]))

    async def collect():
        return [chunk async for chunk in api._sse_events(
            ticker="NVDA", user={"id": "u"}, after_sequence=3,
            view="company", view_revision=revision, poll_seconds=0, max_cycles=1,
        )]
    chunks = asyncio.run(collect())
    assert len(chunks) == 1 and chunks[0].startswith("event: reset")


@pytest.mark.parametrize("stored_title,visible_in_news,display_title", [
    ("Benzinga Bulls &amp; Bears: Nvidia, Apple", False, "Benzinga Bulls & Bears: Nvidia, Apple"),
    ("Benzinga Bulls &amp;amp; Bears: Nvidia, Apple", True, "Benzinga Bulls &amp; Bears: Nvidia, Apple"),
])
def test_editorial_admission_and_detail_use_once_decoded_headline(
    monkeypatch, tmp_path, stored_title, visible_in_news, display_title,
):
    _api, client, db, _names = _editorial_app(monkeypatch, tmp_path)
    with store_mod.NewsStore(db, source_key="benzinga-rest") as writer:
        writer.commit([_routed(4, stored_title, 4)], expected_cursor="c2", next_cursor="c3")
    all_rows = client.get("/api/ticker-news/NVDA?view=all").json()["rows"]
    story = next(row for row in all_rows if row["source_item_id"] == "4")
    news = client.get("/api/ticker-news/NVDA?view=news").json()
    visible = [row for row in news["rows"] if row["source_item_id"] == "4"]
    assert bool(visible) is visible_in_news
    detail = client.get(
        f"/api/ticker-news/stories/{story['story_id']}?ticker=NVDA&view=news"
        f"&view_revision={news['editorial_view']['revision']}"
    )
    if visible_in_news:
        assert detail.status_code == 200, detail.text
        assert visible[0]["title"] == display_title
        assert visible[0]["editorial"]["eligible"] is True
        assert visible[0]["editorial"]["format"] == "unclassified"
        member = next(row for row in detail.json()["members"] if row["source_item_id"] == "4")
        assert member["title"] == display_title
        assert member["editorial"] == visible[0]["editorial"]
    else:
        assert detail.status_code == 404


@pytest.mark.parametrize("stored_teaser,observed", [
    ("N&#118;idia is the customer.", True),
    ("N&amp;#118;idia is the customer.", False),
    ("&#36;NVDA is the customer.", True),
    ("&amp;#36;NVDA is the customer.", False),
])
def test_editorial_admission_and_detail_use_once_decoded_permitted_summary(
    monkeypatch, tmp_path, stored_teaser, observed,
):
    _api, client, db, _names = _editorial_app(monkeypatch, tmp_path)
    with store_mod.NewsStore(db, source_key="benzinga-rest") as writer:
        writer.commit([
            _routed(4, "Supplier signs a manufacturing agreement", 4, teaser=stored_teaser),
        ], expected_cursor="c2", next_cursor="c3")
    news = client.get("/api/ticker-news/NVDA?view=news").json()
    row = next(row for row in news["rows"] if row["source_item_id"] == "4")
    assert row["editorial"]["company_reference"] == ("summary" if observed else "not_observed")
    assert row["editorial"]["eligible"] is True
    detail = client.get(
        f"/api/ticker-news/stories/{row['story_id']}?ticker=NVDA&view=news"
        f"&view_revision={news['editorial_view']['revision']}"
    )
    assert detail.status_code == 200, detail.text
    member = next(member for member in detail.json()["members"] if member["source_item_id"] == "4")
    assert member["editorial"] == row["editorial"]
    company = client.get("/api/ticker-news/NVDA?view=company").json()
    admitted = [member for member in company["rows"] if member["source_item_id"] == "4"]
    assert bool(admitted) is observed
    company_detail = client.get(
        f"/api/ticker-news/stories/{row['story_id']}?ticker=NVDA&view=company"
        f"&view_revision={company['editorial_view']['revision']}"
    )
    assert company_detail.status_code == (200 if observed else 404)
    if admitted:
        assert admitted[0]["editorial"]["eligible"] is True
        assert admitted[0]["editorial"]["company_reference"] == "summary"


def test_editorial_rule_version_change_rejects_old_continuations_and_resets_stream(monkeypatch, tmp_path):
    from engine import qbus_news_editorial as editorial
    monkeypatch.setattr(editorial, "EDITORIAL_RULES_VERSION", "ticker_news.editorial_rules.v1")
    api, client, _db, _names = _editorial_app(monkeypatch, tmp_path)
    first = client.get("/api/ticker-news/NVDA?view=news&limit=1").json()
    old_revision = first["editorial_view"]["revision"]
    cursor = first["next_cursor"]
    assert cursor is not None
    monkeypatch.setattr(editorial, "EDITORIAL_RULES_VERSION", "ticker_news.editorial_rules.v2")
    current = client.get("/api/ticker-news/NVDA?view=news&limit=1").json()
    assert current["editorial_view"]["rules"] == "ticker_news.editorial_rules.v2"
    assert current["editorial_view"]["revision"] != old_revision
    for path in (
        f"/api/ticker-news/NVDA?view=news&cursor={cursor}",
        "/api/ticker-news/NVDA/changes?view=news&after_sequence=1",
        f"/api/ticker-news/stories/{first['rows'][0]['story_id']}?ticker=NVDA&view=news",
    ):
        response = client.get(path + "&view_revision=" + old_revision)
        assert response.status_code == 409
        assert response.headers["cache-control"] == "private, no-store"

    async def collect():
        return [chunk async for chunk in api._sse_events(
            ticker="NVDA", user={"id": "u"}, after_sequence=1,
            view="news", view_revision=old_revision, poll_seconds=0, max_cycles=1,
        )]
    chunks = asyncio.run(collect())
    assert len(chunks) == 1 and chunks[0].startswith("event: reset")
    assert "Nvidia launches" not in chunks[0]
