"""Synthetic transport tests for the direct Benzinga live-news adapter."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json

import pytest
import requests

from collectors import benzinga_news
from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import normalize_news
from engine.qbus_news_universe import qualify_universe


UTC = timezone.utc
POLL_AT = datetime(2026, 10, 5, 14, 30, 5, tzinfo=UTC)


def _article(
    item_id: int,
    *,
    updated: str,
    ticker: str = "NVDA",
    title: str | None = None,
) -> dict:
    return {
        "id": item_id,
        "created": "Mon, 05 Oct 2026 10:29:00 -0400",
        "updated": updated,
        "title": title or f"Story {item_id}",
        "teaser": f"teaser {item_id}",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": [{"name": "News"}],
        "stocks": [{"name": ticker}],
        "tags": [{"name": "breaking"}],
    }


class FakeResponse:
    def __init__(self, payload, *, status=200, headers=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            exc = requests.HTTPError(f"HTTP {self.status_code}")
            exc.response = self
            raise exc


class FakeHttp:
    def __init__(self, routes):
        self.routes = list(routes)
        self.calls = []

    def __call__(self, url, *, params, headers, timeout):
        self.calls.append(
            {
                "url": url,
                "params": dict(params),
                "headers": dict(headers),
                "timeout": timeout,
            }
        )
        if not self.routes:
            raise AssertionError("unexpected HTTP call")
        expected_path, expected_page, response = self.routes.pop(0)
        assert url.endswith(expected_path)
        assert params["page"] == expected_page
        return response


def _universe():
    asof = POLL_AT
    return qualify_universe(
        {
            "owner": "security_reference.sp500",
            "revision": "sp500-r1",
            "complete": True,
            "truncated": False,
            "effective_at": asof - timedelta(days=1),
            "known_at": asof - timedelta(hours=1),
            "fresh_until": asof + timedelta(days=1),
            "securities": [
                {
                    "security_id": "sec-NVDA",
                    "ticker": "NVDA",
                    "aliases": ["NVDA"],
                    "valid_from": asof - timedelta(days=100),
                    "valid_to": None,
                    "known_at": asof - timedelta(days=100),
                },
                {
                    "security_id": "sec-AMD",
                    "ticker": "AMD",
                    "aliases": ["AMD"],
                    "valid_from": asof - timedelta(days=100),
                    "valid_to": None,
                    "known_at": asof - timedelta(days=100),
                },
            ],
        },
        asof=asof,
    )


def _stream_payload(item_id=1, action="created", ticker="NVDA") -> dict:
    content = _article(
        item_id,
        updated="Mon, 05 Oct 2026 10:30:01 -0400",
        ticker=ticker,
    )
    return {
        "id": f"msg-{item_id}",
        "api_version": "websocket/v1",
        "kind": "news",
        "data": {
            "action": action,
            "id": item_id,
            "timestamp": "2026-10-05T14:30:02Z",
            "content": content,
        },
    }


def test_delta_fetch_uses_updated_since_overlap_and_exhausts_news_and_removals():
    http = FakeHttp(
        [
            ("/api/v2/news", 0, FakeResponse([
                _article(1, updated="Mon, 05 Oct 2026 10:30:01 -0400"),
                _article(2, updated="Mon, 05 Oct 2026 10:30:02 -0400", ticker="AMD"),
            ])),
            ("/api/v2/news", 1, FakeResponse([])),
            ("/api/v2/news-removed", 0, FakeResponse({
                "items": [
                    {"id": 9, "updated": "Mon, 05 Oct 2026 10:30:03 -0400"},
                    {"id": 10, "updated": "Mon, 05 Oct 2026 10:30:04 -0400"},
                ]
            })),
            ("/api/v2/news-removed", 1, FakeResponse({"items": []})),
        ]
    )
    client = benzinga_news.BenzingaNewsClient(
        token="not-a-real-key",
        http_get=http,
        page_size=2,
        overlap_seconds=3,
    )

    batch = client.fetch_delta(cursor_epoch=1791201000, observed_at=POLL_AT)

    assert [r.source_item_id for r in batch.revisions] == ["1", "2", "9", "10"]
    assert batch.revisions[-1].action == "removed"
    assert batch.gap_unresolved is False
    assert batch.next_cursor_epoch == int(POLL_AT.timestamp())
    assert batch.news_pages == 2
    assert batch.removed_pages == 2
    assert all(c["params"]["updatedSince"] == 1791200997 for c in http.calls)
    assert all(c["params"]["pageSize"] == 2 for c in http.calls)
    assert http.calls[0]["params"]["sort"] == "updated:asc"
    assert http.calls[0]["params"]["displayOutput"] == "headline"
    assert all("not-a-real-key" not in c["url"] for c in http.calls)
    assert all(c["params"]["token"] == "not-a-real-key" for c in http.calls)


def test_full_page_at_page_budget_holds_cursor_and_marks_gap():
    http = FakeHttp(
        [
            ("/api/v2/news", 0, FakeResponse([
                _article(1, updated="Mon, 05 Oct 2026 10:30:01 -0400"),
                _article(2, updated="Mon, 05 Oct 2026 10:30:02 -0400"),
            ])),
            ("/api/v2/news-removed", 0, FakeResponse({"items": []})),
        ]
    )
    client = benzinga_news.BenzingaNewsClient(
        token="k",
        http_get=http,
        page_size=2,
        max_pages=1,
    )

    batch = client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert batch.gap_unresolved is True
    assert batch.next_cursor_epoch == 100
    assert batch.hold_reasons == ("news_page_budget_exhausted",)


def test_failed_or_rate_limited_page_raises_sanitized_error_without_advancing_any_cursor():
    http = FakeHttp(
        [
            (
                "/api/v2/news",
                0,
                FakeResponse(
                    {"error": "token=DO_NOT_LEAK"},
                    status=429,
                    headers={"Retry-After": "7"},
                ),
            )
        ]
    )
    client = benzinga_news.BenzingaNewsClient(
        token="SUPERSECRET",
        http_get=http,
        sleep=lambda _: None,
    )

    with pytest.raises(benzinga_news.BenzingaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "http_429"
    assert exc.value.retry_after_seconds == 7
    assert "SUPERSECRET" not in str(exc.value)
    assert "DO_NOT_LEAK" not in str(exc.value)


def test_malformed_news_page_refuses_instead_of_silently_advancing():
    http = FakeHttp(
        [
            ("/api/v2/news", 0, FakeResponse({"items": []})),
        ]
    )
    client = benzinga_news.BenzingaNewsClient(token="k", http_get=http)

    with pytest.raises(benzinga_news.BenzingaProtocolError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "news_page_not_array"


def test_removed_page_accepts_documented_items_shape_and_requires_updated_clock():
    http = FakeHttp(
        [
            ("/api/v2/news", 0, FakeResponse([])),
            (
                "/api/v2/news-removed",
                0,
                FakeResponse({"items": [{"id": 9}]}),
            ),
        ]
    )
    client = benzinga_news.BenzingaNewsClient(token="k", http_get=http)

    with pytest.raises(benzinga_news.BenzingaProtocolError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "removed_item_invalid"


def test_route_revision_uses_qualified_aliases_and_keeps_unbound_story_unindexed():
    universe = _universe()
    bound = normalize_news(
        _article(
            1,
            updated="Mon, 05 Oct 2026 10:30:01 -0400",
            ticker="NVDA",
        ),
        transport="benzinga_rest",
        received_at=POLL_AT,
    )
    unbound = normalize_news(
        _article(
            2,
            updated="Mon, 05 Oct 2026 10:30:02 -0400",
            ticker="ZZZZ",
        ),
        transport="benzinga_rest",
        received_at=POLL_AT,
    )

    a = benzinga_news.route_revision(bound, universe)
    b = benzinga_news.route_revision(unbound, universe)

    assert a.security_ids == ("sec-NVDA",)
    assert a.universe_revision == "sp500-r1"
    assert b.security_ids == ()
    assert b.universe_revision == "sp500-r1"


def test_stream_frame_normalizes_actual_news_and_ignores_heartbeat_but_refuses_bad_json():
    rev = benzinga_news.normalize_stream_frame(
        json.dumps(_stream_payload()),
        received_at=POLL_AT,
    )
    assert rev is not None
    assert rev.source_item_id == "1"
    assert rev.action == "created"

    assert (
        benzinga_news.normalize_stream_frame(
            json.dumps({"kind": "heartbeat"}),
            received_at=POLL_AT,
        )
        is None
    )
    with pytest.raises(benzinga_news.BenzingaProtocolError) as exc:
        benzinga_news.normalize_stream_frame("{bad-json", received_at=POLL_AT)
    assert exc.value.code == "stream_invalid_json"


def test_stream_observation_commit_does_not_mutate_rest_cursor(tmp_path):
    universe = _universe()
    db = tmp_path / "qbus.sqlite3"
    stream_revision = benzinga_news.normalize_stream_frame(
        json.dumps(_stream_payload()),
        received_at=POLL_AT,
    )
    assert stream_revision is not None
    routed = benzinga_news.route_revision(stream_revision, universe)

    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([], expected_cursor=None, next_cursor="100")
        receipt = store.commit_observations([routed])
        assert receipt.applied_states == 1
        assert store.current_cursor() == "100"
        assert store.snapshot(
            "sec-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows[0].source_item_id == "1"


def test_complete_catchup_commits_rows_and_cursor_together(tmp_path):
    universe = _universe()
    http = FakeHttp(
        [
            ("/api/v2/news", 0, FakeResponse([
                _article(1, updated="Mon, 05 Oct 2026 10:30:01 -0400"),
            ])),
            ("/api/v2/news-removed", 0, FakeResponse({"items": []})),
        ]
    )
    client = benzinga_news.BenzingaNewsClient(
        token="k",
        http_get=http,
        page_size=100,
    )
    db = tmp_path / "qbus.sqlite3"

    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        result = benzinga_news.catch_up_once(
            client=client,
            store=store,
            universe=universe,
            observed_at=POLL_AT,
        )
        assert result.committed is True
        assert result.gap_unresolved is False
        assert store.current_cursor() == str(int(POLL_AT.timestamp()))
        assert store.snapshot(
            "sec-NVDA",
            limit=10,
            cursor=None,
            rights=store_mod.NewsReadRights.all_internal(),
        ).rows[0].source_item_id == "1"


def test_incomplete_catchup_never_commits_rows_or_cursor(tmp_path):
    universe = _universe()
    http = FakeHttp(
        [
            ("/api/v2/news", 0, FakeResponse([
                _article(i, updated="Mon, 05 Oct 2026 10:30:01 -0400")
                for i in (1, 2)
            ])),
            ("/api/v2/news-removed", 0, FakeResponse({"items": []})),
        ]
    )
    client = benzinga_news.BenzingaNewsClient(
        token="k",
        http_get=http,
        page_size=2,
        max_pages=1,
    )
    db = tmp_path / "qbus.sqlite3"

    with store_mod.NewsStore(db, source_key="benzinga-rest") as store:
        result = benzinga_news.catch_up_once(
            client=client,
            store=store,
            universe=universe,
            observed_at=POLL_AT,
        )
        assert result.committed is False
        assert result.gap_unresolved is True
        assert store.current_cursor() is None
        assert store.counts()["revisions"] == 0