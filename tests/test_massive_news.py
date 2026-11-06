"""Hermetic tests for the Massive general-news adapter.

No network, no credentials, no real ``requests`` dependency: the session and
clock are injected fakes. The ``engine.qbus_news_contract`` module resolved
here is the parent's real contract (or, in this isolated worker, its labeled
stand-in); the adapter must only interact through its documented interface.
"""

from __future__ import annotations

import datetime as _dt
import json
from typing import Any

import pytest

from engine.massive_news import (
    CODE_AUTH,
    CODE_HTTP,
    CODE_INVALID_NEXT_URL,
    CODE_MALFORMED_RESPONSE,
    CODE_PAGINATION_LOOP,
    CODE_RATE_LIMITED,
    CODE_ROW_MALFORMED,
    CODE_TRANSPORT,
    MassiveNewsClient,
    MassivePollError,
)

_UTC = _dt.timezone.utc
_ALLOWED = frozenset({"reuters.com", "bloomberg.com"})
_TOKEN = "test-token-not-a-secret"
_FIXED_NOW = _dt.datetime(2026, 10, 19, 12, 0, 0, tzinfo=_UTC)


def _row(
    external_id: str = "n1",
    published: str = "2026-10-19T11:00:00Z",
    homepage: str = "https://www.reuters.com/",
    name: str = "Reuters",
) -> dict[str, Any]:
    return {
        "id": external_id,
        "title": f"title {external_id}",
        "article_url": f"https://example.com/{external_id}",
        "description": f"desc {external_id}",
        "published_utc": published,
        "publisher": {"name": name, "homepage_url": homepage},
        "tickers": ["AAPL"],
        "insights": "must-not-propagate",
        "body": "must-not-propagate",
        "image": "must-not-propagate",
    }


def _page(results: list[dict[str, Any]] | Any, next_url: str | None = None) -> bytes:
    payload: dict[str, Any] = {"status": "ok", "results": results, "count": len(results) if isinstance(results, list) else 0}
    if next_url is not None:
        payload["next_url"] = next_url
    return json.dumps(payload).encode("utf-8")


class FakeResponse:
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.content), chunk_size):
            yield self.content[offset:offset+chunk_size]

    def close(self):
        pass


class FakeSession:
    """Requests-like fake: records calls, replays queued responses."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, *, params: Any = None, headers: Any = None,
            timeout: Any = None, allow_redirects: Any = None, stream: Any = None) -> FakeResponse:
        self.calls.append(
            {"url": url, "params": params, "headers": dict(headers or {}),
             "timeout": timeout, "allow_redirects": allow_redirects}
        )
        if not self._responses:
            raise AssertionError("fake session exhausted")
        return self._responses.pop(0)


class ExplodingSession(FakeSession):
    def get(self, *args: Any, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": args[0] if args else kwargs.get("url"), "headers": dict(kwargs.get("headers") or {})})
        raise ConnectionError(f"boom with token {_TOKEN} in the message")


def _client(session: FakeSession) -> MassiveNewsClient:
    return MassiveNewsClient(_TOKEN, session=session, clock=lambda: _FIXED_NOW)


def _poll(client: MassiveNewsClient, **kwargs: Any):
    kwargs.setdefault("since", _dt.datetime(2026, 10, 19, 10, 0, 0, tzinfo=_UTC))
    kwargs.setdefault("allowed_publishers", _ALLOWED)
    return client.poll(**kwargs)


# --------------------------------------------------------------------------- basic admission


def test_approved_publisher_admitted_and_fields_trimmed() -> None:
    session = FakeSession([FakeResponse(200, _page([_row("a1"), _row("a2", homepage="https://www.bloomberg.com/x")]))])
    batch = _poll(_client(session))

    assert batch.complete is True
    assert batch.pages == 1
    assert [r.source_item_id for r in batch.revisions] == ["a1", "a2"]
    assert batch.revisions[0].source == "massive:reuters.com"
    # received_at is the pre-flight request clock, UTC.
    assert batch.through == _FIXED_NOW
    assert batch.revisions[0].received_at == _FIXED_NOW
    assert batch.revisions[0].received_at.tzinfo is not None


def test_absent_publisher_skipped_not_normalized() -> None:
    session = FakeSession([FakeResponse(200, _page([_row("keep"), _row("skip", homepage="https://notallowed.example.com/")]))])
    batch = _poll(_client(session))

    assert [r.source_item_id for r in batch.revisions] == ["keep"]
    assert batch.complete is True


def test_unknown_publisher_shape_skipped() -> None:
    # publisher dict without homepage_url (and a missing publisher entirely):
    # no identity -> skipped, never normalized.
    session = FakeSession(
        [
            FakeResponse(
                200,
                _page([{**_row("no-homepage"), "publisher": {"name": "X"}}, _row("ok")]),
            )
        ]
    )
    batch = _poll(_client(session))
    assert [r.source_item_id for r in batch.revisions] == ["ok"]


def test_approved_fields_only_no_insights_body_image() -> None:
    seen: dict[str, Any] = {}

    import engine.massive_news as mn

    real = mn.normalize_massive_news

    def spy(payload, *, received_at):
        seen.update(payload)
        return real(payload, received_at=received_at)

    mn.normalize_massive_news = spy  # type: ignore[assignment]
    try:
        session = FakeSession([FakeResponse(200, _page([_row("a1")]))])
        _poll(_client(session))
    finally:
        mn.normalize_massive_news = real  # type: ignore[assignment]

    assert set(seen) <= {"id", "title", "article_url", "description", "published_utc", "publisher", "tickers", "keywords"}
    assert set(seen["publisher"]) <= {"name", "homepage_url"}


# --------------------------------------------------------------------------- pagination


def test_pagination_follows_valid_next_url_and_stops_cleanly() -> None:
    nxt = "https://api.massive.com/v2/reference/news?cursor=abc"
    session = FakeSession(
        [
            FakeResponse(200, _page([_row("p1")], next_url=nxt)),
            FakeResponse(200, _page([_row("p2")])),
        ]
    )
    batch = _poll(_client(session))

    assert batch.pages == 2
    assert batch.complete is True
    assert [r.source_item_id for r in batch.revisions] == ["p1", "p2"]
    assert session.calls[1]["url"] == nxt
    # Query params only ride on the fixed first request.
    assert session.calls[0]["params"] == {
        "published_utc.gte": "2026-10-19T10:00:00+00:00",
        "published_utc.lte": "2026-10-19T12:00:00+00:00",
        "sort": "published_utc",
        "order": "asc",
        "limit": 1000,
    }
    assert session.calls[1]["params"] is None


def test_polygon_io_next_url_allowed() -> None:
    nxt = "https://api.polygon.io/v2/reference/news?cursor=x"
    session = FakeSession([FakeResponse(200, _page([_row("p1")], next_url=nxt)), FakeResponse(200, _page([]))])
    batch = _poll(_client(session))
    assert batch.complete is True and batch.pages == 2


# --------------------------------------------------------------------------- empty allow-list / no network


def test_empty_allowlist_makes_no_network_call() -> None:
    session = FakeSession([])  # any call would explode the fake
    batch = _poll(_client(session), allowed_publishers=frozenset())

    assert batch.revisions == ()
    assert batch.pages == 0
    assert batch.complete is True
    assert batch.through == _FIXED_NOW
    assert session.calls == []


# --------------------------------------------------------------------------- page cap


def test_saturated_page_cap_reports_incomplete() -> None:
    nxt = "https://api.massive.com/v2/reference/news?cursor=more"
    session = FakeSession([FakeResponse(200, _page([_row("p1")], next_url=nxt))])
    batch = _poll(_client(session), max_pages=1)

    assert batch.pages == 1
    assert batch.complete is False
    assert [r.source_item_id for r in batch.revisions] == ["p1"]
    assert len(session.calls) == 1


# --------------------------------------------------------------------------- next_url strict gate


@pytest.mark.parametrize(
    "bad_next",
    [
        "http://api.massive.com/v2/reference/news?cursor=x",            # scheme
        "https://evil.example.com/v2/reference/news?cursor=x",          # foreign origin
        "https://api.massive.com/v2/reference/news?apiKey=t",           # auth query
        "https://api.massive.com/v2/reference/news?api%4Bey=t",
        "https://api.massive.com/v2/reference/news?token=t",            # auth query (token)
        "https://user:pw@api.massive.com/v2/reference/news",            # userinfo
        "https://api.massive.com/v2/reference/news?cursor=x#frag",      # fragment
        "https://api.massive.com:8443/v2/reference/news",               # port
        "https://api.massive.com/v2/other/news?cursor=x",               # path
    ],
)
def test_invalid_next_urls_fail_closed(bad_next: str) -> None:
    session = FakeSession([FakeResponse(200, _page([_row("p1")], next_url=bad_next))])
    with pytest.raises(MassivePollError) as err:
        _poll(_client(session))
    assert err.value.code == CODE_INVALID_NEXT_URL


def test_repeated_next_url_detected_as_loop() -> None:
    dup = "https://api.massive.com/v2/reference/news?cursor=same"
    session = FakeSession(
        [
            FakeResponse(200, _page([_row("p1")], next_url=dup)),
            FakeResponse(200, _page([_row("p2")], next_url=dup)),
        ]
    )
    with pytest.raises(MassivePollError) as err:
        _poll(_client(session))
    assert err.value.code == CODE_PAGINATION_LOOP


# --------------------------------------------------------------------------- sanitized HTTP errors


@pytest.mark.parametrize(
    ("status", "expected"),
    [(401, CODE_AUTH), (403, CODE_AUTH), (429, CODE_RATE_LIMITED), (500, CODE_HTTP), (302, CODE_HTTP)],
)
def test_http_errors_map_to_fixed_codes(status: int, expected: str) -> None:
    session = FakeSession([FakeResponse(status, b"{}")])
    with pytest.raises(MassivePollError) as err:
        _poll(_client(session))
    assert err.value.code == expected
    # Fixed codes only: no provider body, no URL, no token in the message.
    assert _TOKEN not in str(err.value)
    assert "http" not in str(err.value).lower() or expected == CODE_HTTP


def test_transport_error_never_leaks_exception_text_or_token() -> None:
    session = ExplodingSession([])
    with pytest.raises(MassivePollError) as err:
        _poll(_client(session))
    assert err.value.code == CODE_TRANSPORT
    message = str(err.value)
    assert _TOKEN not in message
    assert "boom" not in message


def test_auth_header_bearer_and_never_in_url() -> None:
    nxt = "https://api.massive.com/v2/reference/news?cursor=c"
    session = FakeSession([FakeResponse(200, _page([_row("p1")], next_url=nxt)), FakeResponse(200, _page([]))])
    _poll(_client(session))

    for call in session.calls:
        assert call["headers"].get("Authorization") == f"Bearer {_TOKEN}"
        url = call["url"]
        assert _TOKEN not in url
        assert "Bearer" not in url
        query = url.split("?", 1)[1] if "?" in url else ""
        for pair in query.split("&"):
            if pair:
                assert pair.split("=", 1)[0].lower() not in {"apikey", "api_key", "key", "token"}
    # Redirects are never followed.
    assert all(call["allow_redirects"] is False for call in session.calls)


# --------------------------------------------------------------------------- fail-closed malformed data


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",                                # unparsable JSON
        b'{"results": "nope"}',                     # results not a list
        b'{"results": [1, 2]}',                     # row not an object
        b'[]',                                      # top level not an object
        _page([{**_row("bad"), "published_utc": "not-a-timestamp"}]),  # row normalization fails
    ],
)
def test_malformed_response_shapes_fail_closed(body: bytes) -> None:
    session = FakeSession([FakeResponse(200, body)])
    with pytest.raises(MassivePollError) as err:
        _poll(_client(session))
    assert err.value.code in {CODE_MALFORMED_RESPONSE, CODE_ROW_MALFORMED}


def test_empty_results_page_completes_cleanly() -> None:
    session = FakeSession([FakeResponse(200, _page([]))])
    batch = _poll(_client(session))
    assert batch.revisions == ()
    assert batch.complete is True
    assert batch.pages == 1


def test_malformed_row_blocks_cursor_advancement() -> None:
    # Good rows precede a malformed one; the batch must fail closed rather
    # than return a complete cursor that would silently skip the bad page.
    rows = [_row("good1"), {**_row("bad-row"), "published_utc": 12345}]
    session = FakeSession([FakeResponse(200, _page(rows, next_url="https://api.massive.com/v2/reference/news?cursor=next"))])
    with pytest.raises(MassivePollError) as err:
        _poll(_client(session))
    assert err.value.code == CODE_ROW_MALFORMED
    assert len(session.calls) == 1  # never advanced to the next page


def test_oversized_response_and_row_bound_fail_closed() -> None:
    session = FakeSession([FakeResponse(200, b"x" * (8 * 1024 * 1024 + 1))])
    with pytest.raises(MassivePollError) as err:
        _poll(_client(session))
    assert err.value.code == "MASSIVE_PAYLOAD_TOO_LARGE"

    rows = [_row(f"r{i}") for i in range(1001)]
    session2 = FakeSession([FakeResponse(200, _page(rows))])
    with pytest.raises(MassivePollError) as err2:
        _poll(_client(session2))
    assert err2.value.code == "MASSIVE_ROWS_TOO_MANY"


# --------------------------------------------------------------------------- clock semantics


def test_through_is_preflight_utc_clock_not_publication_time() -> None:
    # Publication timestamp (11:00) is before the clock (12:00); even a row
    # stamped after the poll clock must not move `through` into the future.
    future_row = _row("f1", published="2026-10-19T13:30:00Z")
    session = FakeSession([FakeResponse(200, _page([future_row]))])
    batch = _poll(_client(session))
    assert batch.through == _FIXED_NOW
    assert batch.revisions[0].published_at > batch.through
    assert all(r.received_at == batch.through for r in batch.revisions)


def test_naive_clock_and_naive_since_rejected() -> None:
    client = MassiveNewsClient(_TOKEN, session=FakeSession([]), clock=lambda: _dt.datetime(2026, 10, 19, 12, 0, 0))
    with pytest.raises(ValueError):
        client.poll(since=_dt.datetime(2026, 10, 19, 10, 0, 0, tzinfo=_UTC), allowed_publishers=_ALLOWED)
    client2 = MassiveNewsClient(_TOKEN, session=FakeSession([]), clock=lambda: _FIXED_NOW)
    with pytest.raises(ValueError):
        client2.poll(since=_dt.datetime(2026, 10, 19, 10, 0, 0), allowed_publishers=_ALLOWED)


def test_empty_token_rejected() -> None:
    with pytest.raises(ValueError):
        MassiveNewsClient("", session=FakeSession([]))


def test_keywords_survive_admission_and_bind_the_report_revision():
    row = {**_row("tagged"), "keywords": ["earnings", "semiconductors"]}
    first = _poll(_client(FakeSession([FakeResponse(200, _page([row]))]))).revisions[0]
    changed = {**row, "keywords": ["guidance"]}
    second = _poll(_client(FakeSession([FakeResponse(200, _page([changed]))]))).revisions[0]
    assert set(first.tags) == {"earnings", "semiconductors"}
    assert set(second.tags) == {"guidance"}
    assert first.content_hash != second.content_hash


@pytest.mark.parametrize("publication_gap_hours,expected_clusters", [(20, 2), (1, 1)])
def test_historical_batch_grouping_keeps_publication_time_separate_from_receipt_time(
    tmp_path, publication_gap_hours, expected_clusters,
):
    from engine.qbus_news_store import NewsStore, RoutedRevision

    first_published = _FIXED_NOW - _dt.timedelta(hours=publication_gap_hours + 1)
    second_published = _FIXED_NOW - _dt.timedelta(hours=1)
    rows = [
        {**_row("history-a", published=first_published.isoformat()), "title": "Nvidia opens a new research center"},
        {**_row("history-b", published=second_published.isoformat(),
                homepage="https://www.bloomberg.com", name="Bloomberg"),
         "title": "Nvidia opens a new research center"},
    ]
    batch = _poll(
        _client(FakeSession([FakeResponse(200, _page(rows))])),
        since=_FIXED_NOW - _dt.timedelta(hours=24),
    )
    assert all(revision.received_at == _FIXED_NOW for revision in batch.revisions)
    assert [revision.published_at for revision in batch.revisions] == [first_published, second_published]
    with NewsStore(tmp_path / "historical.db", source_key="fixture") as store:
        store.commit_observations(tuple(
            RoutedRevision(revision, ("sec-NVDA",), "fixture")
            for revision in batch.revisions
        ))
        groups = store._conn.execute("SELECT count(*) FROM news_clusters").fetchone()[0]
        assert groups == expected_clusters
        assert {row[0] for row in store._conn.execute(
            "SELECT anchor_observed_at FROM news_clusters"
        )} == {_FIXED_NOW.isoformat()}


def test_cross_provider_group_uses_the_immutable_anchor_publication_after_a_correction(tmp_path):
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore, RoutedRevision

    title = "Nvidia opens a new research center"
    earlier = _FIXED_NOW - _dt.timedelta(hours=21)
    recent = _FIXED_NOW - _dt.timedelta(hours=1)
    def primary(published, received):
        return normalize_news({
            "id": "primary", "title": title, "url": "https://benzinga.com/primary",
            "created": published.isoformat(), "updated": received.isoformat(),
            "stocks": ["NVDA"],
        }, transport="benzinga_rest", received_at=received)
    with NewsStore(tmp_path / "cross-provider.db", source_key="fixture") as store:
        store.commit_observations((RoutedRevision(primary(earlier, _FIXED_NOW), ("sec-NVDA",), "fixture"),))
        store.commit_observations((RoutedRevision(
            primary(recent, _FIXED_NOW + _dt.timedelta(minutes=1)), ("sec-NVDA",), "fixture",
        ),))
        row = {**_row("different-event", published=recent.isoformat()), "title": title}
        revision = _poll(_client(FakeSession([FakeResponse(200, _page([row]))]))).revisions[0]
        store.commit_observations((RoutedRevision(revision, ("sec-NVDA",), "fixture"),))
        assert store._conn.execute("SELECT count(*) FROM news_clusters").fetchone()[0] == 2
        assert store._conn.execute(
            "SELECT count(*) FROM news_cluster_members WHERE source='benzinga'"
        ).fetchone()[0] == 1


def test_poll_coverage_clock_does_not_backdate_receipt_of_later_pages():
    clocks = iter([
        _FIXED_NOW,
        _FIXED_NOW + _dt.timedelta(seconds=2),
        _FIXED_NOW + _dt.timedelta(seconds=5),
    ])
    session = FakeSession([
        FakeResponse(200, _page([_row("page-a")], next_url="https://api.massive.com/v2/reference/news?cursor=b")),
        FakeResponse(200, _page([_row("page-b")])),
    ])
    batch = _poll(MassiveNewsClient(_TOKEN, session=session, clock=lambda: next(clocks)))
    assert batch.through == _FIXED_NOW
    assert [revision.received_at for revision in batch.revisions] == [
        _FIXED_NOW + _dt.timedelta(seconds=2), _FIXED_NOW + _dt.timedelta(seconds=5),
    ]
