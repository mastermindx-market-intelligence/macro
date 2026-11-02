"""API tests for rights-gated ticker-news annotation.

Serialization coverage is the four read paths: snapshot rows, story members,
changes rows, and SSE change events. Receipt fixtures follow
tests/test_ticker_news_receipt_binding.py; the app harness follows
tests/test_ticker_news_api.py.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
import pytest

from engine import qbus_news_store as store_mod
from engine.qbus_news_annotate import annotate_row
from engine.qbus_news_contract import normalize_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 20, 0, tzinfo=UTC)
_CONTRACT = "Defense contractor wins $2.4B Navy contract for destroyer program"
_UNMATCHED = "Warehouse inventory climbed 12.5% during the quiet season"
_PLAIN = "Nvidia launches accelerator"
_LEAKY_TEASER = (
    "Amazon posts Q3 earnings that beat analyst estimates and records $88.8 million"
)
_ANNOTATOR_VERSION = "qbus_news_annotate.v1"

_SNAPSHOT_KEYS = {
    "schema",
    "ticker",
    "security_id",
    "state",
    "rows",
    "next_cursor",
    "has_more",
    "source_health",
}
_STORY_ROW_KEYS = {
    "sequence",
    "source",
    "source_item_id",
    "story_id",
    "source_count",
    "item_count",
    "title",
    "url",
    "teaser",
    "published_at",
    "updated_at",
    "received_at",
    "universe_revision",
}
_CHANGES_KEYS = {
    "schema",
    "ticker",
    "security_id",
    "rows",
    "next_sequence",
    "has_more",
}
_CHANGE_ROW_KEYS = {
    "sequence",
    "kind",
    "source",
    "source_item_id",
    "story_id",
    "title",
    "url",
    "teaser",
    "security_ids",
    "universe_revision",
    "observed_at",
}
_STORY_KEYS = {
    "schema",
    "story_id",
    "source_count",
    "item_count",
    "members",
}
_SSE_FAULT_KEYS = {"schema", "ticker", "detail"}
_STANCE_KEYS = {"direction", "confidence"}


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat()


def _rights(now: datetime, **capability_overrides) -> dict:
    capabilities = {
        "internal_ingestion": True,
        "historical_retention": True,
        "headline_display": True,
        "source_link_display": True,
        "teaser_display": True,
        "body_display": False,
        "image_display": False,
        "derivative_processing": True,
    }
    capabilities.update(capability_overrides)
    return {
        "schema": "qbus.news_rights_receipt.v1",
        "receipt_id": "rights-annotation",
        "owner_ref": "source-rights/BENZINGA-A",
        "status": "approved",
        "source": "benzinga",
        "product_id": "benzinga-newsfeed-commercial",
        "audiences": ["site_full"],
        "effective_at": _iso(now - timedelta(days=1)),
        "expires_at": _iso(now + timedelta(days=30)),
        "capabilities": capabilities,
    }


def _routed(item_id=1, title=_PLAIN, teaser="color", minute=0):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": teaser,
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


def _make_db(tmp_path: Path, items: list) -> Path:
    db = tmp_path / "q.sqlite3"
    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(items, expected_cursor=None, next_cursor="c1")
    return db


def _client(monkeypatch, tmp_path: Path, db: Path, receipt_path: Path):
    from app import ticker_news

    monkeypatch.setattr(ticker_news, "_news_db_path", lambda: db)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: (
            "SEC:US-XNAS-NVDA" if str(ticker).upper() == "NVDA" else None
        ),
    )
    monkeypatch.setattr(
        ticker_news,
        "_source_health",
        lambda: {
            "schema": "qbus.news_health.v1",
            "source": "benzinga",
            "state": "live",
            "last_successful_catchup": "2026-10-05T20:00:00+00:00",
        },
    )
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(receipt_path))
    ticker_news._reset_rate_limit_for_tests()
    app = FastAPI()
    app.include_router(ticker_news.router)
    app.dependency_overrides[ticker_news.require_site_full_user] = lambda: {
        "id": "user-1",
        "email": "user@example.test",
    }
    return ticker_news, TestClient(app)


def _nested_keys(value):
    found = set()
    if isinstance(value, dict):
        found.update(value)
        for item in value.values():
            found |= _nested_keys(item)
    elif isinstance(value, list):
        for item in value:
            found |= _nested_keys(item)
    return found


def _parse_sse(chunks: list[str]) -> list[tuple[str, dict | None]]:
    parsed = []
    for chunk in chunks:
        if chunk.startswith(":"):
            parsed.append(("heartbeat", None))
            continue
        event_name = ""
        data = None
        for line in chunk.splitlines():
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
        parsed.append((event_name, data))
    return parsed


def _collect_sse(ticker_news, *, cycles: int, after: int = 0) -> list[str]:
    async def collect():
        out = []
        async for chunk in ticker_news._sse_events(
            ticker="NVDA",
            user={"id": "user-1"},
            after_sequence=after,
            poll_seconds=0,
            max_cycles=cycles,
        ):
            out.append(chunk)
        return out

    return asyncio.run(collect())


def _assert_no_stance(annotation: dict) -> None:
    assert _nested_keys(annotation).isdisjoint(_STANCE_KEYS)
    assert "usd_all" not in _nested_keys(annotation)
    assert "body" not in annotation
    assert "image" not in annotation


def _assert_closed_rows(rows: list[dict]) -> None:
    assert rows
    for row in rows:
        assert "annotation" in row
        assert row["annotation"] is None


def _assert_closed_payload(payload: dict, *, row_key: str) -> None:
    assert payload["annotations"] == {
        "state": "not_permitted",
        "annotator_version": _ANNOTATOR_VERSION,
    }
    _assert_closed_rows(payload[row_key])


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_permitted_receipt_annotates_every_serialization_path(monkeypatch, tmp_path):
    """Mutation: skip annotation on any one of snapshot, story, changes, or SSE."""
    now = datetime.now(UTC)
    receipt = _write(tmp_path / "rights.json", _rights(now))
    db = _make_db(
        tmp_path,
        [
            _routed(item_id=1, title=_CONTRACT, teaser="color", minute=0),
            _routed(item_id=2, title=_UNMATCHED, teaser="color", minute=2),
        ],
    )
    ticker_news, client = _client(monkeypatch, tmp_path, db, receipt)

    snapshot = client.get("/api/ticker-news/NVDA")
    assert snapshot.status_code == 200
    assert snapshot.headers["cache-control"] == "private, no-store"
    body = snapshot.json()
    assert body["schema"] == "ticker_news.snapshot.v1"
    assert _SNAPSHOT_KEYS <= set(body)
    assert body["annotations"] == {
        "state": "on",
        "annotator_version": _ANNOTATOR_VERSION,
    }
    by_title = {row["title"]: row for row in body["rows"]}
    assert set(by_title) == {_CONTRACT, _UNMATCHED}
    contract = by_title[_CONTRACT]
    unmatched = by_title[_UNMATCHED]
    assert _STORY_ROW_KEYS <= set(contract)
    assert "body" not in contract
    assert "image" not in contract
    assert contract["annotation"]["event_type"] == "contract_award"
    assert contract["annotation"]["basis"] == "headline+teaser"
    assert contract["annotation"]["figures"]["usd"] == pytest.approx(2_400_000_000)
    assert contract["annotation"]["derivation"] == "deterministic_pattern"
    assert unmatched["annotation"]["event_type"] is None
    assert unmatched["annotation"]["figures"]["percentages"] == [12.5]
    assert unmatched["annotation"]["event_type"] != contract["annotation"]["event_type"]
    for row in body["rows"]:
        _assert_no_stance(row["annotation"])
    _assert_no_stance(body["annotations"])

    story_id = contract["story_id"]
    story = client.get(f"/api/ticker-news/stories/{story_id}")
    assert story.status_code == 200
    story_body = story.json()
    assert story_body["schema"] == "ticker_news.story.v1"
    assert _STORY_KEYS <= set(story_body)
    assert story_body["annotations"]["state"] == "on"
    assert story_body["members"]
    assert _STORY_ROW_KEYS <= set(story_body["members"][0])
    assert story_body["members"][0]["annotation"]["event_type"] == "contract_award"
    _assert_no_stance(story_body["members"][0]["annotation"])

    changes = client.get("/api/ticker-news/NVDA/changes?after_sequence=0")
    assert changes.status_code == 200
    changes_body = changes.json()
    assert changes_body["schema"] == "ticker_news.changes.v1"
    assert _CHANGES_KEYS <= set(changes_body)
    assert changes_body["annotations"]["state"] == "on"
    assert len(changes_body["rows"]) >= 2
    assert _CHANGE_ROW_KEYS <= set(changes_body["rows"][0])
    change_titles = {row["title"]: row for row in changes_body["rows"]}
    assert change_titles[_CONTRACT]["annotation"]["event_type"] == "contract_award"
    assert change_titles[_UNMATCHED]["annotation"]["event_type"] is None
    for row in changes_body["rows"]:
        _assert_no_stance(row["annotation"])

    events = _parse_sse(_collect_sse(ticker_news, cycles=1))
    change_events = [(name, data) for name, data in events if name != "heartbeat"]
    assert change_events
    assert {name for name, _data in change_events} <= {"upsert", "remove"}
    sse_titles = {}
    for name, data in change_events:
        assert name == "upsert"
        assert data is not None
        assert _CHANGE_ROW_KEYS <= set(data)
        assert "annotation" in data
        _assert_no_stance(data["annotation"])
        sse_titles[data["title"]] = data
    assert sse_titles[_CONTRACT]["annotation"]["event_type"] == "contract_award"
    assert sse_titles[_CONTRACT]["annotation"]["schema"] == "ticker_news.annotation.v1"
    assert sse_titles[_UNMATCHED]["annotation"]["event_type"] is None


def test_teaser_stripped_by_rights_is_not_used(monkeypatch, tmp_path):
    """Mutation: annotate from the stored teaser after rights blanked it."""
    now = datetime.now(UTC)
    receipt = _write(
        tmp_path / "rights.json",
        _rights(now, teaser_display=False, derivative_processing=True),
    )
    db = _make_db(
        tmp_path,
        [_routed(item_id=1, title=_PLAIN, teaser=_LEAKY_TEASER, minute=0)],
    )
    oracle = annotate_row(_PLAIN, _LEAKY_TEASER)
    assert oracle["basis"] == "headline+teaser"
    assert oracle["event_type"] == "earnings_result"
    assert oracle["figures"]["usd"] == pytest.approx(88_800_000)

    with store_mod.NewsStore.open_readonly(db, source_key="benzinga-rest") as store:
        stored = store.snapshot(
            "SEC:US-XNAS-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights(
                allowed_sources=frozenset({"benzinga"}),
                allow_teaser=True,
            ),
        )
    assert stored.rows[0].teaser == _LEAKY_TEASER

    ticker_news, client = _client(monkeypatch, tmp_path, db, receipt)
    snapshot = client.get("/api/ticker-news/NVDA")
    assert snapshot.status_code == 200
    row = snapshot.json()["rows"][0]
    assert row["teaser"] == ""
    assert row["title"] == _PLAIN
    _assert_headline_only(row["annotation"])

    story_id = row["story_id"]
    member = client.get(f"/api/ticker-news/stories/{story_id}").json()["members"][0]
    assert member["teaser"] == ""
    _assert_headline_only(member["annotation"])

    change = client.get("/api/ticker-news/NVDA/changes").json()["rows"][0]
    assert change["teaser"] == ""
    _assert_headline_only(change["annotation"])

    events = _parse_sse(_collect_sse(ticker_news, cycles=1))
    sse_row = next(data for name, data in events if name == "upsert")
    assert sse_row is not None
    assert sse_row["teaser"] == ""
    _assert_headline_only(sse_row["annotation"])


def _assert_headline_only(annotation: dict) -> None:
    assert annotation is not None
    assert annotation["basis"] == "headline"
    assert annotation["event_type"] is None
    assert annotation["figures"]["usd"] is None
    assert "88800000" not in json.dumps(annotation)
    assert "earnings_result" not in json.dumps(annotation)
    _assert_no_stance(annotation)


def _assert_all_paths_closed(monkeypatch, tmp_path, receipt: Path) -> None:
    db = _make_db(
        tmp_path,
        [_routed(item_id=1, title=_CONTRACT, teaser="color", minute=0)],
    )
    ticker_news, client = _client(monkeypatch, tmp_path, db, receipt)
    snapshot = client.get("/api/ticker-news/NVDA")
    assert snapshot.status_code == 200
    snapshot_body = snapshot.json()
    assert snapshot_body["schema"] == "ticker_news.snapshot.v1"
    _assert_closed_payload(snapshot_body, row_key="rows")
    story_id = snapshot_body["rows"][0]["story_id"]

    story = client.get(f"/api/ticker-news/stories/{story_id}")
    assert story.status_code == 200
    assert story.json()["schema"] == "ticker_news.story.v1"
    _assert_closed_payload(story.json(), row_key="members")

    changes = client.get("/api/ticker-news/NVDA/changes")
    assert changes.status_code == 200
    assert changes.json()["schema"] == "ticker_news.changes.v1"
    _assert_closed_payload(changes.json(), row_key="rows")

    events = _parse_sse(_collect_sse(ticker_news, cycles=1))
    sse_rows = [data for name, data in events if name == "upsert"]
    assert sse_rows
    for data in sse_rows:
        assert data is not None
        assert data["annotation"] is None
        assert "annotations" not in data


def test_derivative_false_nulls_every_row(monkeypatch, tmp_path):
    """Mutation: treat a qualified receipt as permission to annotate."""
    now = datetime.now(UTC)
    receipt = _write(
        tmp_path / "rights.json",
        _rights(now, derivative_processing=False),
    )
    _assert_all_paths_closed(monkeypatch, tmp_path, receipt)


def test_derivative_missing_nulls_every_row(monkeypatch, tmp_path):
    """Mutation: default a missing derivative_processing flag to True."""
    now = datetime.now(UTC)
    payload = _rights(now)
    del payload["capabilities"]["derivative_processing"]
    receipt = _write(tmp_path / "rights.json", payload)
    _assert_all_paths_closed(monkeypatch, tmp_path, receipt)


def test_derivative_string_true_nulls_every_row(monkeypatch, tmp_path):
    """Mutation: accept the string ``\"true\"`` as the boolean True.

    A non-bool capability does not qualify (engine/qbus_news_receipts.py), so the
    unpatched route stays 503. After a qualified rights result, the same file
    still fail-closes the annotation gate.
    """
    now = datetime.now(UTC)
    receipt = _write(
        tmp_path / "rights.json",
        _rights(now, derivative_processing="true"),
    )
    db = _make_db(
        tmp_path,
        [_routed(item_id=1, title=_CONTRACT, teaser="color", minute=0)],
    )
    ticker_news_mod, client = _client(monkeypatch, tmp_path, db, receipt)
    denied = client.get("/api/ticker-news/NVDA")
    assert denied.status_code == 503
    assert denied.json()["detail"] == "ticker news rights unavailable"
    assert "annotations" not in denied.json()

    monkeypatch.setattr(
        ticker_news_mod,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )
    _assert_closed_payload(client.get("/api/ticker-news/NVDA").json(), row_key="rows")
    changes = client.get("/api/ticker-news/NVDA/changes").json()
    _assert_closed_payload(changes, row_key="rows")
    story_id = client.get("/api/ticker-news/NVDA").json()["rows"][0]["story_id"]
    _assert_closed_payload(
        client.get(f"/api/ticker-news/stories/{story_id}").json(),
        row_key="members",
    )
    events = _parse_sse(_collect_sse(ticker_news_mod, cycles=1))
    sse_rows = [data for name, data in events if name == "upsert"]
    assert sse_rows and all(row["annotation"] is None for row in sse_rows)
    assert ticker_news_mod.derivative_permitted(receipt) is False


def test_unreadable_receipt_nulls_every_row(monkeypatch, tmp_path):
    """Mutation: annotate when the receipt path cannot be read."""
    missing = tmp_path / "missing-rights.json"
    db = _make_db(
        tmp_path,
        [_routed(item_id=1, title=_CONTRACT, teaser="color", minute=0)],
    )
    ticker_news_mod, client = _client(monkeypatch, tmp_path, db, missing)
    denied = client.get("/api/ticker-news/NVDA")
    assert denied.status_code == 503
    assert denied.json()["detail"] == "ticker news rights unavailable"

    monkeypatch.setattr(
        ticker_news_mod,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )
    opened = client.get("/api/ticker-news/NVDA")
    assert opened.status_code == 200
    _assert_closed_payload(opened.json(), row_key="rows")
    story_id = opened.json()["rows"][0]["story_id"]
    _assert_closed_payload(
        client.get(f"/api/ticker-news/stories/{story_id}").json(),
        row_key="members",
    )
    _assert_closed_payload(
        client.get("/api/ticker-news/NVDA/changes").json(),
        row_key="rows",
    )
    events = _parse_sse(_collect_sse(ticker_news_mod, cycles=1))
    sse_rows = [data for name, data in events if name == "upsert"]
    assert sse_rows and all(row["annotation"] is None for row in sse_rows)


def test_receipt_unreadable_after_qualification_fail_closes(monkeypatch, tmp_path):
    """Mutation: cache the first read, or treat qualified rights as derivative.

    The file grants derivative_processing true and qualifies. The second read
    (the derivative check) raises. Annotation must be off for that request.
    """
    now = datetime.now(UTC)
    receipt = _write(tmp_path / "rights.json", _rights(now, derivative_processing=True))
    db = _make_db(
        tmp_path,
        [_routed(item_id=1, title=_CONTRACT, teaser="color", minute=0)],
    )
    _ticker_news, client = _client(monkeypatch, tmp_path, db, receipt)
    opened = client.get("/api/ticker-news/NVDA")
    assert opened.status_code == 200
    assert opened.json()["annotations"]["state"] == "on"
    assert opened.json()["rows"][0]["annotation"]["event_type"] == "contract_award"

    reads = {"n": 0}
    original = Path.read_text
    target = receipt.resolve()

    def flaky(self, *args, **kwargs):
        if Path(self).resolve() == target:
            reads["n"] += 1
            if reads["n"] > 1:
                raise OSError("unreadable")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky)
    closed = client.get("/api/ticker-news/NVDA")
    assert closed.status_code == 200
    assert reads["n"] >= 2
    _assert_closed_payload(closed.json(), row_key="rows")


def test_derivative_permission_is_read_once_per_http_projection(monkeypatch, tmp_path):
    """Bounded HTTP projections share one derivative decision across their rows."""
    now = datetime.now(UTC)
    receipt = _write(tmp_path / "rights.json", _rights(now))
    db = _make_db(
        tmp_path,
        [
            _routed(item_id=1, title=_CONTRACT, teaser="color", minute=0),
            _routed(item_id=2, title=_UNMATCHED, teaser="color", minute=3),
            _routed(item_id=3, title="Desk notes a quiet tape", teaser="color", minute=4),
        ],
    )
    ticker_news, client = _client(monkeypatch, tmp_path, db, receipt)
    calls = []
    real = ticker_news.derivative_permitted

    def spy(path):
        calls.append(str(path))
        return real(path)

    monkeypatch.setattr(ticker_news, "derivative_permitted", spy)

    changes = client.get("/api/ticker-news/NVDA/changes")
    assert changes.status_code == 200
    assert len(changes.json()["rows"]) >= 2
    assert len(calls) == 1

    calls.clear()
    snapshot = client.get("/api/ticker-news/NVDA")
    assert len(snapshot.json()["rows"]) >= 2
    assert len(calls) == 1

    calls.clear()
    story_id = snapshot.json()["rows"][0]["story_id"]
    assert client.get(f"/api/ticker-news/stories/{story_id}").status_code == 200
    assert len(calls) == 1

    # A long-lived SSE connection must requalify its scope. Idle expiry and
    # revocation during a shared read are behavioral regressions covered in
    # test_shared_news_intelligence.py; a one-read stream would fail those.


def test_derivative_gate_is_not_consulted_without_qualified_rights(monkeypatch, tmp_path):
    """Mutation: read the derivative flag before _rights_for_user qualifies."""
    from app import ticker_news

    receipt = _write(
        tmp_path / "rights.json",
        _rights(datetime.now(UTC), derivative_processing=True),
    )
    calls = []
    monkeypatch.setattr(
        ticker_news,
        "derivative_permitted",
        lambda path: calls.append(str(path)) or True,
    )
    monkeypatch.setenv("MM_TICKER_NEWS_RIGHTS", str(receipt))
    monkeypatch.setattr(ticker_news, "_rights_for_user", lambda user: None)
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )
    ticker_news._reset_rate_limit_for_tests()

    events = _parse_sse(_collect_sse(ticker_news, cycles=1))
    assert calls == []
    assert len(events) == 1
    name, data = events[0]
    assert name == "restricted"
    assert data is not None
    assert set(data) == _SSE_FAULT_KEYS
    assert data["schema"] == "ticker_news.restricted.v1"
    assert "annotation" not in data
    assert "annotations" not in data


def test_unavailable_sse_payload_is_unchanged(monkeypatch, tmp_path):
    """Mutation: add annotation to the unavailable SSE event."""
    from app import ticker_news

    monkeypatch.setattr(
        ticker_news,
        "_rights_for_user",
        lambda user: store_mod.NewsReadRights.all_internal(),
    )
    monkeypatch.setattr(
        ticker_news,
        "_security_for_ticker",
        lambda ticker, now: "SEC:US-XNAS-NVDA",
    )

    def boom():
        raise HTTPException(
            status_code=503,
            detail="ticker news temporarily unavailable",
        )

    monkeypatch.setattr(ticker_news, "_open_store", boom)
    events = _parse_sse(_collect_sse(ticker_news, cycles=1))
    assert len(events) == 1
    name, data = events[0]
    assert name == "unavailable"
    assert data is not None
    assert set(data) == _SSE_FAULT_KEYS
    assert data["schema"] == "ticker_news.unavailable.v1"
    assert "annotation" not in data


def test_closed_gate_does_not_call_annotate_row(monkeypatch, tmp_path):
    """Mutation: call annotate_row and then discard the result when not permitted."""
    now = datetime.now(UTC)
    receipt = _write(
        tmp_path / "rights.json",
        _rights(now, derivative_processing=False),
    )
    db = _make_db(
        tmp_path,
        [_routed(item_id=1, title=_CONTRACT, teaser=_LEAKY_TEASER, minute=0)],
    )
    ticker_news, client = _client(monkeypatch, tmp_path, db, receipt)
    calls = []
    real = ticker_news.annotate_row

    def spy(title, teaser):
        calls.append((title, teaser))
        return real(title, teaser)

    monkeypatch.setattr(ticker_news, "annotate_row", spy)
    response = client.get("/api/ticker-news/NVDA")
    assert response.status_code == 200
    assert response.json()["rows"][0]["annotation"] is None
    assert calls == []


def test_anonymous_ticker_news_remains_401():
    import app.main as main_mod

    client = TestClient(main_mod.app, raise_server_exceptions=False)
    for path in (
        "/api/ticker-news/NVDA",
        "/api/ticker-news/NVDA/changes",
        "/api/ticker-news/NVDA/stream",
        "/api/ticker-news/stories/ev2_missing",
    ):
        response = client.get(path)
        assert response.status_code == 401
        assert response.headers["cache-control"] == "private, no-store"
