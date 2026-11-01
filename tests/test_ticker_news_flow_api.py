"""Wave B2 API tests: rights-gated news flow on the first ticker-news page.

The frozen fake below (contract section 6) replaces NewsStore.news_flow on the
real store class; every other store path stays real.  Lane B1's real method has
merged, and test_flow_counts_match_visible_rows_under_rights now runs it through
a delegating spy; every other test keeps the fake.
"""
from __future__ import annotations

import asyncio
import dataclasses
from datetime import datetime, timedelta, timezone
import itertools
import json
import logging
import re
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import normalize_news

UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
FLOW_NOW = datetime(2026, 10, 5, 21, 0, tzinfo=UTC)

BANNED_EN = (
    "unusual", "spike", "alert", "score", "signal", "validated", "rank",
    "ranking", "confidence", "sentiment", "buy", "sell", "bullish", "bearish",
    "positive", "negative", "beat", "miss", "upgrade", "downgrade", "hot",
    "momentum", "impact",
)
BANNED_ZH = (
    "异常", "激增", "飙升", "警报", "预警", "评分", "分数", "信号", "验证",
    "排名", "置信", "情绪", "买", "卖", "利好", "利空", "看涨", "看跌",
    "超预期", "不及预期", "热度", "影响",
)
PROVENANCE_KEYS = {
    "velocity_schema", "sources_counted", "status_counted", "distinct_by",
    "story_grouping", "cluster_policy_version", "windows", "calculation",
    "time_basis_counts_24h",
}

# --- Wave B frozen fake: wb_news_flow_contract.md section 6 (ORCH-WB, 2026-10-12). Do not edit. ---
import copy
from datetime import timedelta, timezone

from engine import qbus_news_store as store_mod

FLOW_SCHEMA = "ticker_news.flow.v1"
FLOW_METHOD = (
    "distinct reports by source + source_item_id; active status only; "
    "rights-allowed sources only; UTC calendar days; median of 28 prior days"
)
OK_DAILY = [2, 3, 1, 4, 2, 3, 0, 5, 2, 3, 2, 3, 1, 4, 2, 3, 2, 3, 1, 3, 2, 4, 2, 3, 2, 3, 2, 3]
THIN_DAILY = [0] * 22 + [1, 0, 0, 0, 0, 0]
_NULL_KEYS = (
    "as_of", "reports_24h", "reports_7d", "stories_24h", "median_daily_28d",
    "daily_counts_28d", "history_days_observed", "comparison", "provenance",
)


def flow_unavailable(reason):
    flow = {"schema": FLOW_SCHEMA, "state": "unavailable", "reason": reason, "coverage": "complete"}
    for key in _NULL_KEYS:
        flow[key] = None
    return flow


def flow_provenance(as_of, sources, published_at, received_at):
    day = as_of.astimezone(timezone.utc).date()
    return {
        "velocity_schema": "qbus.news_velocity.v1",
        "sources_counted": sorted(sources),
        "status_counted": "active",
        "distinct_by": "source + source_item_id",
        "story_grouping": "news_cluster_members.cluster_id; a report in no cluster is its own story",
        "cluster_policy_version": "qbus_news_cluster.v2",
        "windows": {
            "reports_24h": "rolling, closed at both ends: [as_of - 24h, as_of]",
            "reports_7d": "rolling, closed at both ends: [as_of - 7d, as_of]",
            "daily_28d": {
                "start_date": (day - timedelta(days=28)).isoformat(),
                "end_date": (day - timedelta(days=1)).isoformat(),
                "unit": "UTC calendar day",
                "excludes": "the current UTC day",
                "order": "oldest first",
            },
        },
        "calculation": {"method": FLOW_METHOD, "comparison_rule": "flow_compare.v1"},
        "time_basis_counts_24h": {"published_at": published_at, "received_at": received_at},
    }


def flow_fixture(kind, *, now, sources=("benzinga",)):
    """kind: ok | partial | insufficient_history | thin_partial | no_accessible_sources | unavailable."""
    if kind == "no_accessible_sources":
        return flow_unavailable("no_accessible_sources")
    if kind == "unavailable":
        return flow_unavailable("calculation_failed")
    as_of = now.astimezone(timezone.utc).replace(microsecond=0)
    base = {"schema": FLOW_SCHEMA, "reason": None, "coverage": "complete",
            "as_of": as_of.strftime("%Y-%m-%dT%H:%M:%SZ")}
    if kind in ("ok", "partial"):
        flow = dict(base, state="ok", reports_24h=7, reports_7d=21, stories_24h=4,
                    median_daily_28d=2.5, daily_counts_28d=list(OK_DAILY),
                    history_days_observed=28, comparison="busier",
                    provenance=flow_provenance(as_of, sources, 6, 1))
    elif kind in ("insufficient_history", "thin_partial"):
        flow = dict(base, state="thin_history", reports_24h=2, reports_7d=3, stories_24h=2,
                    median_daily_28d=None, daily_counts_28d=list(THIN_DAILY),
                    history_days_observed=6, comparison="insufficient_history",
                    provenance=flow_provenance(as_of, sources, 2, 0))
    else:
        raise ValueError(kind)
    if kind in ("partial", "thin_partial"):
        flow["coverage"] = "partial"
        flow["comparison"] = None
    order = ("schema", "state", "reason", "coverage") + _NULL_KEYS
    return {key: copy.deepcopy(flow[key]) for key in order}


def install_fake_flow(monkeypatch, mode="ok"):
    """Install a fake NewsStore.news_flow; return the list of recorded calls.

    mode: ok | thin | raise | parse_garbage | malformed | from_rows.
    from_rows is a reference that reads the REAL snapshot under the same rights. It is valid only
    for a seed whose every report is published inside [now - 24h, now] on now's UTC date:
    reports = sum(row.item_count), stories = len(rows), history 0 (thin_history).
    """
    calls = []

    def news_flow(self, security_id, *, now, rights):
        calls.append({"security_id": security_id, "now": now, "rights": rights})
        if not rights.allowed_sources:
            return flow_unavailable("no_accessible_sources")
        if mode == "ok":
            return flow_fixture("ok", now=now, sources=rights.allowed_sources)
        if mode == "thin":
            return flow_fixture("insufficient_history", now=now, sources=rights.allowed_sources)
        if mode == "raise":
            raise RuntimeError("fake flow failure")
        if mode == "parse_garbage":
            raise ValueError("Invalid isoformat string: 'not-a-time'")
        if mode == "malformed":
            bad = flow_fixture("ok", now=now, sources=rights.allowed_sources)
            bad["reports_24h"] = bad["reports_7d"] + 1          # breaks reports_24h <= reports_7d
            return bad
        if mode == "from_rows":
            snap = self.snapshot(security_id, limit=500, cursor=None, rights=rights)
            reports = sum(row.item_count for row in snap.rows)
            flow = flow_fixture("insufficient_history", now=now, sources=rights.allowed_sources)
            flow.update(reports_24h=reports, reports_7d=reports, stories_24h=len(snap.rows),
                        daily_counts_28d=[0] * 28, history_days_observed=0)
            flow["provenance"]["time_basis_counts_24h"] = {"published_at": reports, "received_at": 0}
            return flow
        raise AssertionError(f"unknown fake flow mode {mode!r}")

    monkeypatch.setattr(store_mod.NewsStore, "news_flow", news_flow, raising=False)
    return calls
# --- end frozen fake ---


_DB_SEQ = itertools.count()


def _routed(item_id=1, title="Nvidia launches accelerator", minute=0):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": f"teaser:{title}",
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
    db = tmp_path / f"q{next(_DB_SEQ)}.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="c1")
    return db


def _app(monkeypatch, tmp_path, *, rights=True, health_state="live", db=None):
    """The tests/test_ticker_news_api.py:50 idiom, plus a pinned flow clock."""
    from app import ticker_news

    if db is None:
        db = _make_db(tmp_path)
    if rights is True:
        resolved = store_mod.NewsReadRights.all_internal()
    elif rights is False or rights is None:
        resolved = None
    else:
        resolved = rights
    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(ticker_news, "_flow_now", lambda: FLOW_NOW, raising=False)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: (
            "SEC:US-XNAS-NVDA" if ticker.upper() == "NVDA" else None
        ),
    )
    monkeypatch.setattr(ticker_news, "_rights_for_user", lambda user: resolved)
    monkeypatch.setattr(
        ticker_news,
        "_source_health",
        lambda: {
            "state": health_state,
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


def _spy_snapshot(monkeypatch):
    """Record the rights object each real snapshot call receives."""
    seen = []
    original = store_mod.NewsStore.snapshot

    def wrapped(self, security_id, *, limit, cursor, rights):
        seen.append(rights)
        return original(
            self,
            security_id,
            limit=limit,
            cursor=cursor,
            rights=rights,
        )

    monkeypatch.setattr(store_mod.NewsStore, "snapshot", wrapped)
    return seen


def _find_key(obj, name):
    if isinstance(obj, dict):
        if name in obj:
            return True
        return any(_find_key(value, name) for value in obj.values())
    if isinstance(obj, list):
        return any(_find_key(value, name) for value in obj)
    return False


def _assert_no_banned_words(flow):
    assert _find_key(flow, "label") is False
    text = json.dumps(flow, ensure_ascii=False)
    for word in BANNED_EN:
        assert re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE) is None, word
    for word in BANNED_ZH:
        assert word not in text


def _assert_no_empty_values(value):
    if value is None:
        return False
    if isinstance(value, str):
        return value != ""
    if isinstance(value, dict):
        return len(value) > 0 and all(
            _assert_no_empty_values(item) for item in value.values()
        )
    if isinstance(value, (list, tuple)):
        return len(value) > 0 and all(
            _assert_no_empty_values(item) for item in value
        )
    return True


def test_first_page_carries_flow(monkeypatch, tmp_path):
    ticker_news, app, _db = _app(monkeypatch, tmp_path)
    calls = install_fake_flow(monkeypatch, "ok")
    seen_rights = _spy_snapshot(monkeypatch)
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    body = response.json()
    expected_sources = store_mod.NewsReadRights.all_internal().allowed_sources
    assert body["flow"] == flow_fixture("ok", now=FLOW_NOW, sources=expected_sources)
    assert list(body)[-1] == "flow"
    assert len(calls) == 1
    assert calls[0]["security_id"] == "SEC:US-XNAS-NVDA"
    assert seen_rights and calls[0]["rights"] is seen_rights[0]
    assert calls[0]["now"].tzinfo is not None
    assert calls[0]["now"].utcoffset() == timedelta(0)
    assert ticker_news._flow_payload_valid(body["flow"]) is True


def test_cursor_page_omits_flow(monkeypatch, tmp_path):
    _ticker_news, app, db = _app(monkeypatch, tmp_path)
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(
                    item_id=2,
                    title="Nvidia opens Portland research lab",
                    minute=5,
                ),
                _routed(
                    item_id=3,
                    title="Nvidia reports quarterly results",
                    minute=10,
                ),
            ],
            expected_cursor="c1",
            next_cursor="c2",
        )
    calls = install_fake_flow(monkeypatch, "ok")
    client = TestClient(app)

    first = client.get("/api/ticker-news/NVDA?limit=1")
    assert first.status_code == 200
    assert "flow" in first.json()
    assert len(calls) == 1

    cursor = first.json()["next_cursor"]
    assert cursor is not None
    second = client.get(f"/api/ticker-news/NVDA?limit=1&cursor={cursor}")
    assert second.status_code == 200
    body = second.json()
    assert "flow" not in body
    assert body["rows"]
    assert len(calls) == 1


def test_changes_story_and_sse_never_carry_flow(monkeypatch, tmp_path):
    ticker_news, app, _db = _app(monkeypatch, tmp_path)
    calls = install_fake_flow(monkeypatch, "ok")
    client = TestClient(app)
    first = client.get("/api/ticker-news/NVDA")
    assert first.status_code == 200
    story_id = first.json()["rows"][0]["story_id"]
    baseline = len(calls)
    assert baseline == 1

    changes = client.get("/api/ticker-news/NVDA/changes")
    story = client.get(f"/api/ticker-news/stories/{story_id}")
    assert changes.status_code == 200
    assert story.status_code == 200

    async def collect():
        out = []
        async for chunk in ticker_news._sse_events(
            ticker="NVDA",
            user={"id": "user-1"},
            after_sequence=0,
            poll_seconds=0,
            max_cycles=1,
        ):
            out.append(chunk)
        return out

    chunks = asyncio.run(collect())

    assert _find_key(changes.json(), "flow") is False
    assert _find_key(story.json(), "flow") is False
    sse_payloads = []
    for chunk in chunks:
        for line in chunk.splitlines():
            if line.startswith("data: "):
                sse_payloads.append(json.loads(line[len("data: "):]))
    assert sse_payloads
    for payload in sse_payloads:
        assert _find_key(payload, "flow") is False
    assert len(calls) == baseline


def _assert_flow_failure_degrades(monkeypatch, tmp_path, caplog, mode):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    ok_calls = install_fake_flow(monkeypatch, "ok")
    client = TestClient(app)
    ok_body = client.get("/api/ticker-news/NVDA").json()
    assert len(ok_calls) == 1
    assert "flow" in ok_body

    install_fake_flow(monkeypatch, mode)
    with caplog.at_level(logging.ERROR, logger="app.ticker_news"):
        response = client.get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    body = response.json()
    assert body["flow"] == flow_unavailable("calculation_failed")
    assert {k: v for k, v in body.items() if k != "flow"} == {
        k: v for k, v in ok_body.items() if k != "flow"
    }
    assert json.dumps(body["rows"]) == json.dumps(ok_body["rows"])
    assert any(
        record.getMessage() == "ticker_news flow calculation failed"
        for record in caplog.records
    )


def test_flow_failure_degrades_rows_still_200(monkeypatch, tmp_path, caplog):
    _assert_flow_failure_degrades(monkeypatch, tmp_path, caplog, "raise")


def test_flow_parse_instant_garbage_degrades(monkeypatch, tmp_path, caplog):
    _assert_flow_failure_degrades(monkeypatch, tmp_path, caplog, "parse_garbage")


def test_flow_no_accessible_sources(monkeypatch, tmp_path):
    ticker_news, app, db = _app(monkeypatch, tmp_path)
    calls = install_fake_flow(monkeypatch, "ok")

    with store_mod.NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        result = ticker_news._compute_flow(
            store,
            "SEC:US-XNAS-NVDA",
            rights=store_mod.NewsReadRights(allowed_sources=frozenset()),
        )
    assert result == flow_unavailable("no_accessible_sources")
    assert calls == []

    monkeypatch.setattr(ticker_news, "_rights_for_user", lambda user: None)
    response = TestClient(app).get("/api/ticker-news/NVDA")
    assert response.status_code == 503
    assert calls == []


@pytest.mark.parametrize(
    "mode,complete_kind,partial_kind",
    [
        ("ok", "ok", "partial"),
        ("thin", "insufficient_history", "thin_partial"),
    ],
)
@pytest.mark.parametrize(
    "health_state",
    ["catching_up", "degraded", "unheard_of_state"],
)
def test_flow_partial_when_catching_up_or_degraded(
    monkeypatch, tmp_path, health_state, mode, complete_kind, partial_kind
):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path, health_state=health_state)
    calls = install_fake_flow(monkeypatch, mode)
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    flow = response.json()["flow"]
    assert flow["coverage"] == "partial"
    assert flow["comparison"] is None
    sources = frozenset({"benzinga"})
    complete = flow_fixture(complete_kind, now=FLOW_NOW, sources=sources)
    for key, value in complete.items():
        if key in ("coverage", "comparison"):
            continue
        assert flow[key] == value, key
    assert flow == flow_fixture(partial_kind, now=FLOW_NOW, sources=sources)
    assert len(calls) == 1


def test_flow_coverage_stays_complete_when_live(monkeypatch, tmp_path):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path, health_state="live")
    install_fake_flow(monkeypatch, "ok")
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    flow = response.json()["flow"]
    assert flow["coverage"] == "complete"
    assert flow == flow_fixture("ok", now=FLOW_NOW, sources=frozenset({"benzinga"}))


def test_flow_unavailable_untouched_by_partial_states(monkeypatch, tmp_path):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path, health_state="degraded")
    install_fake_flow(monkeypatch, "raise")
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    assert response.json()["flow"] == flow_unavailable("calculation_failed")


def test_flow_provenance_complete_when_ok(monkeypatch, tmp_path):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    install_fake_flow(monkeypatch, "ok")
    body = TestClient(app).get("/api/ticker-news/NVDA").json()

    flow = body["flow"]
    provenance = flow["provenance"]
    assert set(provenance) == PROVENANCE_KEYS
    assert set(provenance["windows"]) == {"reports_24h", "reports_7d", "daily_28d"}
    assert set(provenance["windows"]["daily_28d"]) == {
        "start_date",
        "end_date",
        "unit",
        "excludes",
        "order",
    }
    assert set(provenance["calculation"]) == {"method", "comparison_rule"}
    assert _assert_no_empty_values(provenance) is True
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", flow["as_of"])


def test_flow_has_no_engine_label_and_no_banned_words(monkeypatch, tmp_path):
    fixtures = {
        kind: flow_fixture(kind, now=FLOW_NOW)
        for kind in (
            "ok",
            "partial",
            "insufficient_history",
            "thin_partial",
            "no_accessible_sources",
            "unavailable",
        )
    }
    served = {}
    for mode in ("ok", "thin", "raise"):
        _ticker_news, app, _db = _app(
            monkeypatch, tmp_path, health_state="degraded"
        )
        install_fake_flow(monkeypatch, mode)
        response = TestClient(app).get("/api/ticker-news/NVDA")
        assert response.status_code == 200
        served[f"degraded/{mode}"] = response.json()["flow"]

    for name, flow in {**fixtures, **served}.items():
        assert flow, name
        _assert_no_banned_words(flow)


def test_no_multi_security_or_sorted_flow_route():
    from app import ticker_news

    paths = {route.path for route in ticker_news.router.routes}
    assert paths == {
        "/api/ticker-news/stories/{story_id}",
        "/api/ticker-news/{ticker}/changes",
        "/api/ticker-news/{ticker}",
        "/api/ticker-news/{ticker}/stream",
        # W11 D1: the private catch-all, registered last (see
        # tests/test_ticker_news_private_errors.py route-order census).
        # W12: the private bare root (GET + non-GET), registered after the real routes.
        "/api/ticker-news",
        "/api/ticker-news/{rest:path}",
    }
    assert all("flow" not in path for path in paths)

    forbidden = {
        "sort", "order", "rank", "ranking", "tickers",
        "securities", "symbols", "ids",
    }
    for route in ticker_news.router.routes:
        names = {param.name for param in route.dependant.query_params}
        names |= {param.name for param in route.dependant.path_params}
        assert not names & forbidden, route.path
        if route.path == "/api/ticker-news/{ticker}":
            assert {param.name for param in route.dependant.query_params} == {
                "limit",
                "cursor",
                "view",
                "view_revision",
            }


_SOURCE_TABLES = (
    "news_revisions",
    "news_states",
    "news_state_projection",
    "news_security_index",
    "news_cluster_members",
    "news_changes",
)


def _seed_restricted_report(db, *, item_id, title, minute, expected_cursor):
    """Commit one report whose source the request rights do not carry.

    dataclasses.replace is attempted first; the store's identity check refuses
    a hand-edited source (recomputed revision_id mismatch), so the sanctioned
    fallback rewrites the source column for that one item across every news_*
    table holding it, in this tmp DB only.
    """
    routed = _routed(item_id=item_id, title=title, minute=minute)
    try:
        replaced = dataclasses.replace(routed.revision, source="restricted_wire")
        with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
            store.commit(
                [
                    store_mod.RoutedRevision(
                        revision=replaced,
                        security_ids=routed.security_ids,
                        universe_revision=routed.universe_revision,
                    )
                ],
                expected_cursor=expected_cursor,
                next_cursor=f"{expected_cursor}-rw",
            )
        return "dataclasses.replace"
    except store_mod.NewsStoreError:
        pass
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [routed],
            expected_cursor=expected_cursor,
            next_cursor=f"{expected_cursor}-rw",
        )
    conn = sqlite3.connect(db)
    try:
        for table in _SOURCE_TABLES:
            conn.execute(
                f"UPDATE {table} SET source='restricted_wire' "
                "WHERE source='benzinga' AND source_item_id=?",
                (str(item_id),),
            )
        conn.commit()
    finally:
        conn.close()
    return "sql_update"


def test_flow_counts_match_visible_rows_under_rights(monkeypatch, tmp_path):
    rights = store_mod.NewsReadRights(allowed_sources=frozenset({"benzinga"}))
    _ticker_news, app, db = _app(monkeypatch, tmp_path, rights=rights)
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(
                    item_id=2,
                    title="Nvidia wins data-center design deal",
                    minute=10,
                ),
                _routed(
                    item_id=3,
                    title="Nvidia expands Tokyo partnership office",
                    minute=20,
                ),
            ],
            expected_cursor="c1",
            next_cursor="c2",
        )
    approach = _seed_restricted_report(
        db,
        item_id=4,
        title="Wire desk exclusive on Nvidia supply chain",
        minute=15,
        expected_cursor="c2",
    )
    assert approach in {"dataclasses.replace", "sql_update"}

    conn = sqlite3.connect(db)
    try:
        restricted_rows = conn.execute(
            "SELECT COUNT(*) FROM news_security_index "
            "WHERE security_id=? AND source='restricted_wire'",
            ("SEC:US-XNAS-NVDA",),
        ).fetchone()[0]
    finally:
        conn.close()
    assert restricted_rows == 1

    # B1-MERGED swap: a delegating spy records each call, then runs the real
    # NewsStore.news_flow unchanged against the same seed and rights.
    assert "news_flow" in store_mod.NewsStore.__dict__
    real_news_flow = store_mod.NewsStore.news_flow
    calls = []

    def spy(self, security_id, *, now, rights):
        calls.append({"security_id": security_id, "now": now, "rights": rights})
        return real_news_flow(self, security_id, now=now, rights=rights)

    monkeypatch.setattr(store_mod.NewsStore, "news_flow", spy)
    response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    body = response.json()
    rows = body["rows"]
    assert rows
    assert all(row["source"] != "restricted_wire" for row in rows)
    flow = body["flow"]
    assert flow["reports_24h"] == sum(row["item_count"] for row in rows)
    assert flow["stories_24h"] == len(rows)
    assert flow["reports_7d"] == flow["reports_24h"]
    assert flow["provenance"]["sources_counted"] == ["benzinga"]
    assert _ticker_news._flow_payload_valid(flow) is True
    assert len(calls) == 1
    assert calls[0]["rights"] is rights


def test_old_terminal_parser_shape_unaffected(monkeypatch, tmp_path):
    ticker_news, _app_obj, db = _app(monkeypatch, tmp_path)
    with store_mod.NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        snapshot = store.snapshot(
            "SEC:US-XNAS-NVDA",
            limit=20,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        )
    health = {
        "state": "live",
        "last_successful_catchup": "2026-10-05T20:00:00+00:00",
    }
    first = ticker_news._snapshot_payload(
        ticker="NVDA",
        security_id="SEC:US-XNAS-NVDA",
        snapshot=snapshot,
        health=health,
        permitted=False,
    )
    second = ticker_news._snapshot_payload(
        ticker="NVDA",
        security_id="SEC:US-XNAS-NVDA",
        snapshot=snapshot,
        health=health,
        permitted=False,
        flow=flow_fixture("ok", now=FLOW_NOW),
    )

    expected_keys = [
        "schema", "editorial_policy", "ticker", "security_id", "state", "rows",
        # Additive atomic delivery watermark; older consumers ignore this key.
        "change_sequence", "next_cursor", "has_more", "source_health", "annotations",
        # W11-07 additive provenance keys (tests/test_ticker_news_snapshot_provenance.py).
        "universe_known_at", "rights_basis",
    ]
    assert list(first) == expected_keys
    assert list(second) == expected_keys + ["flow"]
    assert {k: v for k, v in second.items() if k != "flow"} == first
    assert json.dumps(first["rows"]) == json.dumps(second["rows"])


def test_flow_invariant_violation_degrades(monkeypatch, tmp_path, caplog):
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    install_fake_flow(monkeypatch, "malformed")
    with caplog.at_level(logging.ERROR, logger="app.ticker_news"):
        response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    body = response.json()
    assert body["rows"]
    assert body["flow"] == flow_unavailable("calculation_failed")
    assert any(
        record.getMessage() == "ticker_news flow payload failed validation"
        for record in caplog.records
    )


def test_compute_flow_returns_deep_copy(monkeypatch, tmp_path):
    """The served flow never aliases the store's result object (extra test)."""
    ticker_news, _app_obj, db = _app(monkeypatch, tmp_path)
    shared = flow_fixture("ok", now=FLOW_NOW)

    def stub_news_flow(self, security_id, *, now, rights):
        return shared

    monkeypatch.setattr(
        store_mod.NewsStore, "news_flow", stub_news_flow, raising=False
    )
    resolved = store_mod.NewsReadRights.all_internal()
    with store_mod.NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        first = ticker_news._compute_flow(
            store, "SEC:US-XNAS-NVDA", rights=resolved
        )
        first["reports_24h"] = 999
        first["provenance"]["sources_counted"].append("tampered")
        second = ticker_news._compute_flow(
            store, "SEC:US-XNAS-NVDA", rights=resolved
        )

    assert second["reports_24h"] == 7
    assert second["provenance"]["sources_counted"] == ["benzinga"]
    assert shared["reports_24h"] == 7
    assert shared["provenance"]["sources_counted"] == ["benzinga"]


def _negative_count_case(case_id):
    """The canonical ok fixture with ONE rule broken: a negative count (R1 a-f).

    Every other section-4 rule still holds, so the negative value is the only
    reason the validator may reject the payload.
    """
    flow = flow_fixture("ok", now=FLOW_NOW)
    if case_id == "daily_all_negative":
        flow["daily_counts_28d"] = [-1] * 28
    elif case_id == "counts_trio_negative":
        flow.update(reports_24h=-2, reports_7d=-1, stories_24h=-3)
        flow["provenance"]["time_basis_counts_24h"] = {
            "published_at": -1,
            "received_at": -1,
        }
    elif case_id == "reports_negative_sevenday_zero":
        flow.update(reports_24h=-1, reports_7d=0, stories_24h=-1)
        flow["provenance"]["time_basis_counts_24h"] = {
            "published_at": -1,
            "received_at": 0,
        }
    elif case_id == "basis_negative_sum_ok":
        flow["provenance"]["time_basis_counts_24h"] = {
            "published_at": 8,
            "received_at": -1,
        }
    elif case_id == "stories_negative_only":
        flow["stories_24h"] = -1
    elif case_id == "one_daily_negative":
        daily = list(flow["daily_counts_28d"])
        daily[13] = -1
        flow["daily_counts_28d"] = daily
    else:
        raise AssertionError(f"unknown negative case {case_id!r}")
    return flow


_NEGATIVE_COUNT_CASES = (
    "daily_all_negative",
    "counts_trio_negative",
    "reports_negative_sevenday_zero",
    "basis_negative_sum_ok",
    "stories_negative_only",
    "one_daily_negative",
)


@pytest.mark.parametrize("case_id", _NEGATIVE_COUNT_CASES, ids=_NEGATIVE_COUNT_CASES)
def test_flow_validator_rejects_negative_counts(case_id):
    """Contract section 4: every count is an int >= 0, not merely an int (R1)."""
    from app import ticker_news

    # Control row: the untouched canonical fixture validates, so the False
    # below comes from this case's negative value, not a broken fixture.
    assert ticker_news._flow_payload_valid(flow_fixture("ok", now=FLOW_NOW)) is True
    assert ticker_news._flow_payload_valid(_negative_count_case(case_id)) is False


def test_flow_negative_count_served_as_calculation_failed(monkeypatch, tmp_path, caplog):
    """A negative count served by the store degrades the flow, not the rows (G3)."""
    _ticker_news, app, _db = _app(monkeypatch, tmp_path)
    ok_calls = install_fake_flow(monkeypatch, "ok")
    client = TestClient(app)
    ok_body = client.get("/api/ticker-news/NVDA").json()
    assert len(ok_calls) == 1
    assert "flow" in ok_body

    def negative_news_flow(self, security_id, *, now, rights):
        return _negative_count_case("stories_negative_only")

    monkeypatch.setattr(
        store_mod.NewsStore, "news_flow", negative_news_flow, raising=False
    )
    with caplog.at_level(logging.ERROR, logger="app.ticker_news"):
        response = client.get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    body = response.json()
    assert body["flow"] == flow_unavailable("calculation_failed")
    assert json.dumps(body["rows"]) == json.dumps(ok_body["rows"])
    assert {k: v for k, v in body.items() if k != "flow"} == {
        k: v for k, v in ok_body.items() if k != "flow"
    }
    assert any(
        record.getMessage() == "ticker_news flow payload failed validation"
        for record in caplog.records
    )


@pytest.mark.parametrize("none_case", ["status_counted", "daily_28d_unit"])
def test_flow_validator_rejects_none_in_provenance(none_case):
    """Contract section 3: no None inside provenance when state is not unavailable (R2)."""
    from app import ticker_news

    flow = flow_fixture("ok", now=FLOW_NOW)
    if none_case == "status_counted":
        flow["provenance"]["status_counted"] = None
    else:
        flow["provenance"]["windows"]["daily_28d"]["unit"] = None

    # Control: the unavailable flow's TOP-LEVEL provenance None follows a
    # different rule, checked before no_empty_strings ever applies.
    assert (
        ticker_news._flow_payload_valid(flow_unavailable("calculation_failed")) is True
    )
    assert ticker_news._flow_payload_valid(flow) is False


def test_compute_flow_never_raises_on_uncopyable_payload(monkeypatch, tmp_path, caplog):
    """A payload that passes validation but cannot be deep-copied degrades (R3, G3)."""
    ticker_news, app, _db = _app(monkeypatch, tmp_path)

    def uncopyable_news_flow(self, security_id, *, now, rights):
        bad = flow_fixture("ok", now=now, sources=rights.allowed_sources)
        # An extra provenance key is contract-legal (section 4 subset check);
        # the generator it holds is what copy.deepcopy cannot pickle.
        bad["provenance"] = dict(bad["provenance"], engine_cursor=(x for x in ()))
        return bad

    precondition = uncopyable_news_flow(
        None,
        "SEC:US-XNAS-NVDA",
        now=FLOW_NOW,
        rights=store_mod.NewsReadRights.all_internal(),
    )
    assert ticker_news._flow_payload_valid(precondition) is True

    monkeypatch.setattr(
        store_mod.NewsStore, "news_flow", uncopyable_news_flow, raising=False
    )
    with caplog.at_level(logging.ERROR, logger="app.ticker_news"):
        response = TestClient(app).get("/api/ticker-news/NVDA")

    assert response.status_code == 200
    body = response.json()
    assert body["rows"]
    assert body["flow"] == flow_unavailable("calculation_failed")
    assert any(
        record.getMessage() == "ticker_news flow calculation failed"
        for record in caplog.records
    )
