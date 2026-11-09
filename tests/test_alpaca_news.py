"""Hermetic transport tests for the Alpaca (Benzinga content) news adapter.

No network: HTTP, WebSocket, and clocks are injected fakes. Credential-looking
strings are obvious fakes ("KEYID-FAKE"/"SECRET-FAKE").
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest
import requests

from collectors import alpaca_news
from collectors import benzinga_news
from engine import qbus_news_receipts as receipts_mod
from engine import qbus_news_store as store_mod
from engine.qbus_news_contract import NewsContractError, normalize_news
from engine.qbus_news_universe import qualify_universe


UTC = timezone.utc
POLL_AT = datetime(2026, 10, 11, 14, 30, 5, tzinfo=UTC)
RIGHTS_FILE = (
    Path(__file__).resolve().parents[1]
    / "config"
    / "ticker_news_rights_alpaca_benzinga.json"
)
KEY_ID = "KEYID-FAKE"
SECRET_KEY = "SECRET-FAKE"


def _item(
    item_id: int,
    *,
    source: str = "benzinga",
    updated: str = "2026-10-11T14:30:01Z",
    ticker: str = "NVDA",
) -> dict:
    return {
        "id": item_id,
        "headline": f"Story {item_id}",
        "author": "Benzinga News Desk",
        "created_at": "2026-10-11T14:29:00Z",
        "updated_at": updated,
        "summary": f"teaser {item_id}",
        "content": "FULL BODY MUST NOT BE MAPPED",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "symbols": [ticker],
        "source": source,
    }


def _page(news, *, next_token=None) -> dict:
    payload = {"news": list(news)}
    if next_token is not None:
        payload["next_page_token"] = next_token
    return payload


class FakeResponse:
    def __init__(self, payload, *, status=200, headers=None, content=None):
        self._payload = payload
        self.status_code = status
        self.headers = headers or {}
        self.content = (
            content
            if content is not None
            else json.dumps(payload).encode("utf-8")
        )

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            exc = requests.HTTPError(f"HTTP {self.status_code}")
            exc.response = self
            raise exc


class FakeHttp:
    def __init__(self, responses):
        self.responses = list(responses)
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
        if not self.responses:
            raise AssertionError("unexpected HTTP call")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class MutableClock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now = self.now + timedelta(seconds=seconds)


def _client(http, **kwargs):
    kwargs.setdefault("clock", MutableClock(POLL_AT))
    return alpaca_news.AlpacaNewsClient(
        key_id=KEY_ID,
        secret_key=SECRET_KEY,
        http_get=http,
        **kwargs,
    )


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
            ],
        },
        asof=asof,
    )


def _expected_rfc3339(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── REST request shape ───────────────────────────────────────────────────────


def test_rest_request_shape_credentials_in_headers_not_params():
    http = FakeHttp([FakeResponse(_page([_item(1)]))])
    client = _client(http, page_size=25)

    cursor = int(POLL_AT.timestamp()) - 65
    client.fetch_delta(cursor_epoch=cursor, observed_at=POLL_AT)

    assert len(http.calls) == 1
    call = http.calls[0]
    assert call["url"] == alpaca_news.REST_URL
    assert call["url"].startswith("https://")
    assert call["params"] == {
        "start": _expected_rfc3339(cursor - 3),
        "end": _expected_rfc3339(int(POLL_AT.timestamp())),
        "sort": "asc",
        "limit": 25,
        "include_content": "false",
    }
    assert call["headers"]["APCA-API-KEY-ID"] == KEY_ID
    assert call["headers"]["APCA-API-SECRET-KEY"] == SECRET_KEY
    assert KEY_ID not in str(call["params"])
    assert SECRET_KEY not in str(call["params"])
    assert KEY_ID not in call["url"]
    assert SECRET_KEY not in call["url"]


def test_rest_pagination_follows_next_page_token_until_null():
    http = FakeHttp(
        [
            FakeResponse(_page([_item(1)], next_token="tok-1")),
            FakeResponse(_page([_item(2)], next_token="tok-2")),
            FakeResponse(_page([_item(3)])),
        ]
    )
    client = _client(http)

    batch = client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert [r.source_item_id for r in batch.revisions] == ["1", "2", "3"]
    assert batch.news_pages == 3
    assert batch.removed_pages == 0
    assert batch.gap_unresolved is False
    assert batch.next_cursor_epoch == int(POLL_AT.timestamp())
    assert "page_token" not in http.calls[0]["params"]
    assert http.calls[1]["params"]["page_token"] == "tok-1"
    assert http.calls[2]["params"]["page_token"] == "tok-2"


def test_max_pages_exhaustion_holds_cursor_and_marks_gap():
    http = FakeHttp(
        [
            FakeResponse(_page([_item(1)], next_token="tok-1")),
            FakeResponse(_page([_item(2)], next_token="tok-2")),
        ]
    )
    client = _client(http, max_pages=2)

    batch = client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert batch.gap_unresolved is True
    assert batch.hold_reasons == ("news_page_budget_exhausted",)
    assert batch.next_cursor_epoch == 100
    assert [r.source_item_id for r in batch.revisions] == ["1", "2"]


def test_non_benzinga_publisher_items_are_dropped():
    http = FakeHttp(
        [
            FakeResponse(
                _page(
                    [
                        _item(1),
                        _item(2, source="Reuters"),
                        _item(3, source="BENZINGA "),
                    ]
                )
            )
        ]
    )
    client = _client(http)

    batch = client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert [r.source_item_id for r in batch.revisions] == ["1", "3"]


def test_benzinga_item_maps_title_teaser_url_tickers_and_no_body():
    http = FakeHttp([FakeResponse(_page([_item(1)]))])
    client = _client(http)

    batch = client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    revision = batch.revisions[0]
    assert revision.source == "benzinga"
    assert revision.transport == "alpaca_rest"
    assert revision.title == "Story 1"
    assert revision.teaser == "teaser 1"
    assert revision.url == "https://www.benzinga.com/news/1"
    assert revision.provider_tickers == ("NVDA",)
    assert revision.body_sha256 == ""  # bodies are never re-stored via Alpaca


def test_same_article_via_rest_and_ws_yields_identical_revision_id():
    http = FakeHttp([FakeResponse(_page([_item(1)]))])
    client = _client(http)

    rest_batch = client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    ws_revisions = alpaca_news.normalize_stream_frames(
        json.dumps([dict(_item(1), T="n")]).encode("utf-8"),
        received_at=POLL_AT + timedelta(seconds=17),
    )

    assert len(ws_revisions) == 1
    assert ws_revisions[0].revision_id == rest_batch.revisions[0].revision_id
    assert ws_revisions[0].content_hash == rest_batch.revisions[0].content_hash
    assert ws_revisions[0].transport == "alpaca_ws"


# ── transport errors, backoff, size caps ────────────────────────────────────


def test_429_raises_typed_error_then_backoff_active_without_http_call():
    clock = MutableClock(POLL_AT)
    http = FakeHttp([FakeResponse({}, status=429)])
    client = alpaca_news.AlpacaNewsClient(
        key_id=KEY_ID, secret_key=SECRET_KEY, http_get=http, clock=clock
    )

    with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "http_429"
    assert exc.value.retry_after_seconds == 60
    assert SECRET_KEY not in str(exc.value)

    # Deadline is in the future: refuse WITHOUT calling http_get again
    # (FakeHttp with an empty queue raises AssertionError on any call).
    with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)
    assert exc.value.code == "backoff_active"
    assert len(http.calls) == 1


def test_429_backoff_step_doubles_with_floor_and_cap_then_resets_on_success():
    clock = MutableClock(POLL_AT)
    http = FakeHttp(
        [FakeResponse({}, status=429) for _ in range(7)]
        + [FakeResponse(_page([]))]
        + [FakeResponse({}, status=429)]
    )
    client = alpaca_news.AlpacaNewsClient(
        key_id=KEY_ID, secret_key=SECRET_KEY, http_get=http, clock=clock
    )

    ladder = []
    for _ in range(7):
        with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
            client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)
        assert exc.value.code == "http_429"
        ladder.append(exc.value.retry_after_seconds)
        clock.advance(exc.value.retry_after_seconds)
    assert ladder == [60, 120, 240, 480, 900, 900, 900]

    # A successful page resets the ladder...
    batch = client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)
    assert batch.gap_unresolved is False

    # ...so the next 429 starts from the floor again.
    with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)
    assert exc.value.retry_after_seconds == 60


def test_429_honours_retry_after_header_capped_at_900():
    clock = MutableClock(POLL_AT)
    http = FakeHttp(
        [
            FakeResponse({}, status=429, headers={"Retry-After": "7"}),
            FakeResponse({}, status=429, headers={"Retry-After": "5000"}),
        ]
    )
    client = alpaca_news.AlpacaNewsClient(
        key_id=KEY_ID, secret_key=SECRET_KEY, http_get=http, clock=clock
    )

    with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)
    assert exc.value.retry_after_seconds == 7
    clock.advance(7)

    with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)
    assert exc.value.retry_after_seconds == 900


def test_401_is_a_typed_transport_error():
    http = FakeHttp([FakeResponse({}, status=401)])
    client = _client(http)

    with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "http_401"


def test_transport_exception_text_never_leaks_credentials():
    http = FakeHttp(
        [RuntimeError(f"connection reset key={KEY_ID} secret={SECRET_KEY}")]
    )
    client = _client(http)

    with pytest.raises(alpaca_news.AlpacaTransportError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "transport_runtimeerror"
    assert KEY_ID not in str(exc.value)
    assert SECRET_KEY not in str(exc.value)
    assert SECRET_KEY not in repr(exc.value)


def test_oversize_content_length_header_is_rejected():
    http = FakeHttp(
        [
            FakeResponse(
                _page([_item(1)]),
                headers={
                    "Content-Length": str(alpaca_news.MAX_RESPONSE_BYTES + 1)
                },
            )
        ]
    )
    client = _client(http)

    with pytest.raises(alpaca_news.AlpacaProtocolError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "response_too_large"


def test_oversize_response_body_is_rejected():
    http = FakeHttp(
        [
            FakeResponse(
                _page([_item(1)]),
                content=b"x" * (alpaca_news.MAX_RESPONSE_BYTES + 1),
            )
        ]
    )
    client = _client(http)

    with pytest.raises(alpaca_news.AlpacaProtocolError) as exc:
        client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)

    assert exc.value.code == "response_too_large"


def test_non_json_and_non_object_pages_are_typed_protocol_errors():
    bad_json = FakeResponse({"news": []})
    bad_json.json = lambda: (_ for _ in ()).throw(ValueError("not json"))
    for response, code in (
        (bad_json, "news_page_invalid_json"),
        (FakeResponse([1, 2, 3]), "news_page_not_object"),
        (FakeResponse({"data": []}), "news_not_list"),
    ):
        http = FakeHttp([response])
        client = _client(http)
        with pytest.raises(alpaca_news.AlpacaProtocolError) as exc:
            client.fetch_delta(cursor_epoch=100, observed_at=POLL_AT)
        assert exc.value.code == code


def test_repr_hides_credentials_and_constructor_validates():
    http = FakeHttp([])
    client = _client(http)

    assert KEY_ID not in repr(client)
    assert SECRET_KEY not in repr(client)
    assert repr(client) == "AlpacaNewsClient(page_size=50)"

    for kwargs in (
        {"key_id": ""},
        {"key_id": None},
        {"secret_key": ""},
        {"page_size": 0},
        {"page_size": alpaca_news.LIMIT_MAX + 1},
        {"max_pages": 0},
        {"overlap_seconds": -1},
        {"initial_lookback_seconds": -1},
    ):
        with pytest.raises(alpaca_news.AlpacaProtocolError) as exc:
            alpaca_news.AlpacaNewsClient(
                key_id=kwargs.get("key_id", KEY_ID),
                secret_key=kwargs.get("secret_key", SECRET_KEY),
                page_size=kwargs.get("page_size", 50),
                max_pages=kwargs.get("max_pages", 100),
                overlap_seconds=kwargs.get("overlap_seconds", 3),
                initial_lookback_seconds=kwargs.get(
                    "initial_lookback_seconds", 300
                ),
            )
        assert exc.value.code.startswith(("missing_", "invalid_"))


# ── catch-up duck typing against the real store ──────────────────────────────


def test_catch_up_once_drives_alpaca_client_against_real_store(tmp_path):
    universe = _universe()
    http = FakeHttp([FakeResponse(_page([_item(1)]))])
    client = _client(http)
    db = tmp_path / "qbus.sqlite3"

    with store_mod.NewsStore(db, source_key="alpaca-rest") as store:
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


# ── WebSocket frame normalization ────────────────────────────────────────────


def test_stream_control_frames_normalize_to_empty_list():
    frame = json.dumps(
        [
            {"T": "success", "msg": "connected"},
            {"T": "subscription", "news": ["*"]},
        ]
    )
    assert alpaca_news.normalize_stream_frames(frame, received_at=POLL_AT) == []


def test_stream_news_frame_benzinga_only():
    frame = json.dumps(
        [
            {"T": "n", **_item(1)},
            {"T": "n", **_item(2, source="globenewswire")},
        ]
    )
    revisions = alpaca_news.normalize_stream_frames(
        frame, received_at=POLL_AT
    )
    assert len(revisions) == 1
    assert revisions[0].source == "benzinga"
    assert revisions[0].transport == "alpaca_ws"
    assert revisions[0].title == "Story 1"


def test_stream_error_frame_raises_typed_code_never_msg():
    frame = json.dumps(
        [{"T": "error", "code": 401, "msg": f"bad key {SECRET_KEY}"}]
    )
    with pytest.raises(alpaca_news.AlpacaStreamError) as exc:
        alpaca_news.normalize_stream_frames(frame, received_at=POLL_AT)
    assert exc.value.code == "stream_error_401"
    assert SECRET_KEY not in str(exc.value)


def test_stream_frame_shape_errors():
    for raw, code in (
        (json.dumps({"T": "n"}), "stream_not_array"),
        ("{bad-json", "stream_invalid_json"),
        (b"\xff\xfe\xfd", "stream_non_utf8"),
        (json.dumps([{"T": "n"}, 42]), "stream_item_not_object"),
    ):
        with pytest.raises(alpaca_news.AlpacaStreamError) as exc:
            alpaca_news.normalize_stream_frames(raw, received_at=POLL_AT)
        assert exc.value.code == code


def test_stream_error_frame_without_code_is_unknown():
    frame = json.dumps([{"T": "error", "msg": "vague"}])
    with pytest.raises(alpaca_news.AlpacaStreamError) as exc:
        alpaca_news.normalize_stream_frames(frame, received_at=POLL_AT)
    assert exc.value.code == "stream_error_unknown"


# ── WebSocket handshake ──────────────────────────────────────────────────────


class HandshakeWS:
    def __init__(self, frames):
        self.frames = list(frames)
        self.sent = []

    def recv(self, timeout=None):
        if not self.frames:
            raise AssertionError("unexpected recv")
        frame = self.frames.pop(0)
        if isinstance(frame, BaseException):
            raise frame
        return frame

    def send(self, payload):
        self.sent.append(payload)


def test_handshake_sends_exactly_auth_then_subscribe():
    ws = HandshakeWS(
        [
            json.dumps([{"T": "success", "msg": "connected"}]),
            json.dumps([{"T": "success", "msg": "authenticated"}]),
            json.dumps([{"T": "subscription", "news": ["*"]}]),
        ]
    )

    alpaca_news.stream_handshake(ws, key_id=KEY_ID, secret_key=SECRET_KEY)

    assert ws.sent == [
        json.dumps({"action": "auth", "key": KEY_ID, "secret": SECRET_KEY}),
        json.dumps({"action": "subscribe", "news": ["*"]}),
    ]


def test_handshake_auth_error_carries_code_but_no_secret():
    ws = HandshakeWS(
        [
            json.dumps([{"T": "success", "msg": "connected"}]),
            json.dumps(
                [
                    {
                        "T": "error",
                        "code": 403,
                        "msg": f"auth failed for {SECRET_KEY}",
                    }
                ]
            ),
        ]
    )

    with pytest.raises(alpaca_news.AlpacaStreamError) as exc:
        alpaca_news.stream_handshake(ws, key_id=KEY_ID, secret_key=SECRET_KEY)

    assert exc.value.code == "stream_auth_error_403"
    assert SECRET_KEY not in str(exc.value)
    assert KEY_ID not in str(exc.value)
    assert SECRET_KEY not in repr(exc.value)


def test_handshake_budget_expires_without_completing():
    ws = HandshakeWS(
        [json.dumps([{"T": "quirk", "msg": "hello"}]) for _ in range(3)]
    )

    with pytest.raises(alpaca_news.AlpacaStreamError) as exc:
        alpaca_news.stream_handshake(
            ws, key_id=KEY_ID, secret_key=SECRET_KEY, max_frames=3
        )

    assert exc.value.code == "stream_handshake_budget"


def test_handshake_timeout_is_typed():
    ws = HandshakeWS([TimeoutError()])

    with pytest.raises(alpaca_news.AlpacaStreamError) as exc:
        alpaca_news.stream_handshake(ws, key_id=KEY_ID, secret_key=SECRET_KEY)

    assert exc.value.code == "stream_handshake_timeout"


# ── contract branch ──────────────────────────────────────────────────────────


def test_contract_missing_created_at_is_refused():
    payload = _item(1)
    del payload["created_at"]
    with pytest.raises(NewsContractError) as exc:
        normalize_news(payload, transport="alpaca_rest", received_at=POLL_AT)
    assert exc.value.code == "missing_published_at"


def test_contract_non_benzinga_source_is_refused():
    with pytest.raises(NewsContractError) as exc:
        normalize_news(
            _item(1, source="reuters"),
            transport="alpaca_rest",
            received_at=POLL_AT,
        )
    assert exc.value.code == "unsupported_source"


def test_contract_source_absent_is_refused_on_both_transports():
    for transport in ("alpaca_rest", "alpaca_ws"):
        payload = _item(1)
        del payload["source"]
        with pytest.raises(NewsContractError) as exc:
            normalize_news(payload, transport=transport, received_at=POLL_AT)
        assert exc.value.code == "unsupported_source"


def test_contract_source_case_and_space_variance_still_accepted():
    for transport in ("alpaca_rest", "alpaca_ws"):
        revision = normalize_news(
            _item(1, source="Benzinga "),
            transport=transport,
            received_at=POLL_AT,
        )
        assert revision.source == "benzinga"


# ── rights receipts ──────────────────────────────────────────────────────────


def _rights(**overrides):
    payload = {
        "schema": receipts_mod.RIGHTS_SCHEMA,
        "receipt_id": "rights-alpaca-test-a",
        "owner_ref": "source-rights/ALPACA-BENZINGA-TEST",
        "status": "approved",
        "source": "benzinga",
        "product_id": "macro-ticker-news",
        "audiences": ["site_full"],
        "effective_at": "2026-10-11T00:00:00Z",
        "expires_at": "2027-10-11T00:00:00Z",
        "capabilities": {
            "internal_ingestion": True,
            "historical_retention": True,
            "headline_display": True,
            "source_link_display": True,
            "teaser_display": True,
            "derivative_processing": True,
            "body_display": False,
            "image_display": False,
        },
    }
    payload.update(overrides)
    return payload


def test_committed_rights_file_loads_with_provider_alpaca():
    now = datetime(2026, 10, 12, tzinfo=UTC)
    qualified = receipts_mod.load_rights_receipt(RIGHTS_FILE, now=now)

    assert qualified is not None
    assert qualified.provider == "alpaca"
    assert qualified.source == "benzinga"
    assert qualified.receipt_id == "rights-alpaca-benzinga-news-2026-10-11"


def test_receipt_without_provider_field_qualifies_with_provider_none():
    receipt = receipts_mod.parse_rights_receipt(
        _rights(), now=datetime(2026, 10, 12, tzinfo=UTC)
    )
    assert receipt.provider is None


def test_receipt_with_oversized_provider_is_rejected():
    with pytest.raises(receipts_mod.NewsReceiptError) as exc:
        receipts_mod.parse_rights_receipt(
            _rights(provider="a" * 65),
            now=datetime(2026, 10, 12, tzinfo=UTC),
        )
    assert exc.value.code == "rights_provider"


def test_constants_pin_the_provider_surface():
    assert alpaca_news.REST_URL == "https://data.alpaca.markets/v1beta1/news"
    assert (
        alpaca_news.STREAM_URL
        == "wss://stream.data.alpaca.markets/v1beta1/news"
    )
    assert alpaca_news.PROVIDER == "alpaca"
    assert alpaca_news.CONTENT_SOURCE == "benzinga"
    assert alpaca_news.LIMIT_MAX == 50
    assert alpaca_news.MAX_RESPONSE_BYTES == 8 * 1024 * 1024
    assert alpaca_news.BACKOFF_CAP_SECONDS == 900
