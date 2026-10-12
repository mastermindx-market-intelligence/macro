from __future__ import annotations

from datetime import datetime, timezone

import pytest

from engine.qbus_news_contract import NewsContractError, normalize_news

UTC = timezone.utc
RECEIVED = datetime(2026, 10, 4, 23, 0, 0, tzinfo=UTC)


def ws_payload(*, action="created", item_id=36444586, message_id="msg-1", title="Nvidia launches new accelerator", created="Sun, 04 Oct 2026 17:58:00 -0400", updated="Sun, 04 Oct 2026 17:58:01 -0400", event_ts="2026-10-04T21:58:02Z", body="Full article content", tickers=("NVDA",)):
    content = {
        "id": item_id,
        "author": "Benzinga Insights",
        "created": created,
        "updated": updated,
        "title": title,
        "teaser": "A short teaser",
        "body": body,
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": [{"name": "News"}, {"name": "Movers"}],
        "stocks": [{"name": t, "exchange": "NASDAQ"} for t in tickers],
        "tags": [{"name": "breaking"}],
    }
    return {
        "id": message_id,
        "api_version": "websocket/v1",
        "kind": "news",
        "data": {"action": action, "id": item_id, "timestamp": event_ts, "content": content},
    }


def rest_payload(*, item_id=36444586, title="Nvidia launches new accelerator", created="Sun, 04 Oct 2026 17:58:00 -0400", updated="Sun, 04 Oct 2026 17:58:01 -0400", body="Full article content", tickers=("NVDA",)):
    return {
        "id": item_id,
        "author": "Benzinga Insights",
        "created": created,
        "updated": updated,
        "title": title,
        "teaser": "A short teaser",
        "body": body,
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": [{"name": "News"}, {"name": "Movers"}],
        "stocks": [{"name": t, "exchange": "NASDAQ"} for t in tickers],
        "tags": [{"name": "breaking"}],
    }


def massive_payload(*, item_id=36444586, title="Nvidia launches new accelerator", published="2026-10-04T21:58:00Z", updated="2026-10-04T21:58:01Z", body="Full article content", tickers=("NVDA",)):
    return {
        "benzinga_id": item_id,
        "author": "Benzinga Insights",
        "published": published,
        "last_updated": updated,
        "title": title,
        "teaser": "A short teaser",
        "body": body,
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": ["News", "Movers"],
        "tickers": list(tickers),
        "tags": ["breaking"],
    }


def test_ws_created_normalizes_identity_clocks_and_metadata():
    r = normalize_news(ws_payload(), transport="benzinga_ws", received_at=RECEIVED)
    assert r.schema == "qbus.news_revision.v1"
    assert r.source == "benzinga"
    assert r.source_item_id == "36444586"
    assert r.transport == "benzinga_ws"
    assert r.message_id == "msg-1"
    assert r.action == "created"
    assert r.action_explicit is True
    assert r.published_at == datetime(2026, 10, 4, 21, 58, 0, tzinfo=UTC)
    assert r.updated_at == datetime(2026, 10, 4, 21, 58, 1, tzinfo=UTC)
    assert r.source_event_at == datetime(2026, 10, 4, 21, 58, 2, tzinfo=UTC)
    assert r.version_at == r.updated_at
    assert r.version_clock_domain == "benzinga_article_updated"
    assert r.provider_tickers == ("NVDA",)
    assert r.channels == ("News", "Movers")
    assert r.tags == ("breaking",)
    assert len(r.body_sha256) == 64
    assert len(r.content_hash) == 64
    assert len(r.revision_id) == 32


def test_ws_deleted_case_maps_to_canonical_removed_without_content():
    p = ws_payload(action="Deleted")
    p["data"].pop("content")
    r = normalize_news(p, transport="benzinga_ws", received_at=RECEIVED)
    assert r.action == "removed"
    assert r.action_explicit is True
    assert r.source_item_id == "36444586"
    assert r.title == ""
    assert r.body_sha256 == ""
    assert r.version_at == r.source_event_at
    assert r.version_clock_domain == "benzinga_stream_event"


def test_rest_is_honest_implicit_upsert_and_matches_direct_revision_bytes():
    ws = normalize_news(ws_payload(), transport="benzinga_ws", received_at=RECEIVED)
    rest = normalize_news(rest_payload(), transport="benzinga_rest", received_at=RECEIVED)
    assert rest.action == "updated"
    assert rest.action_explicit is False
    assert rest.source_item_id == ws.source_item_id
    assert rest.version_clock_domain == "benzinga_article_updated"
    assert rest.content_hash == ws.content_hash
    assert rest.revision_id == ws.revision_id


def test_massive_preserves_upstream_identity_but_uses_distinct_clock_domain():
    direct = normalize_news(rest_payload(), transport="benzinga_rest", received_at=RECEIVED)
    mirror = normalize_news(massive_payload(), transport="massive_benzinga_v2", received_at=RECEIVED)
    assert mirror.source == direct.source == "benzinga"
    assert mirror.source_item_id == direct.source_item_id
    assert mirror.transport == "massive_benzinga_v2"
    assert mirror.action == "updated" and mirror.action_explicit is False
    assert mirror.version_clock_domain == "massive_benzinga_system_updated"
    assert mirror.revision_id != direct.revision_id


def test_revision_identity_ignores_receipt_time_and_delivery_message_id():
    a = normalize_news(ws_payload(message_id="a"), transport="benzinga_ws", received_at=RECEIVED)
    b = normalize_news(ws_payload(message_id="b"), transport="benzinga_ws", received_at=datetime(2026, 10, 4, 23, 5, tzinfo=UTC))
    assert a.revision_id == b.revision_id
    assert a.content_hash == b.content_hash
    assert a.received_at != b.received_at


def test_same_headline_different_source_ids_remain_distinct():
    a = normalize_news(rest_payload(item_id=1, title="Fed holds rates"), transport="benzinga_rest", received_at=RECEIVED)
    b = normalize_news(rest_payload(item_id=2, title="Fed holds rates"), transport="benzinga_rest", received_at=RECEIVED)
    assert a.source_item_id != b.source_item_id
    assert a.revision_id != b.revision_id


def test_provider_ticker_spelling_is_not_uppercased_or_alias_rewritten():
    r = normalize_news(rest_payload(tickers=("brk.b", "BF.B")), transport="benzinga_rest", received_at=RECEIVED)
    assert r.provider_tickers == ("brk.b", "BF.B")


def test_clock_anomalies_are_preserved_and_flagged_not_clamped():
    r = normalize_news(
        ws_payload(created="Sun, 04 Oct 2026 17:58:10 -0400", updated="Sun, 04 Oct 2026 17:58:05 -0400", event_ts="2026-10-04T21:58:03Z"),
        transport="benzinga_ws",
        received_at=RECEIVED,
    )
    assert r.updated_at < r.published_at
    assert r.source_event_at < r.published_at
    assert set(r.clock_anomalies) == {"updated_before_published", "event_before_published"}


@pytest.mark.parametrize("value", [True, False])
def test_boolean_source_ids_are_rejected(value):
    with pytest.raises(NewsContractError) as exc:
        normalize_news(rest_payload(item_id=value), transport="benzinga_rest", received_at=RECEIVED)
    assert exc.value.code == "invalid_source_item_id"
    assert str(exc.value) == "qbus_news_contract:invalid_source_item_id"


def test_naive_received_at_is_rejected():
    with pytest.raises(NewsContractError) as exc:
        normalize_news(rest_payload(), transport="benzinga_rest", received_at=datetime(2026, 10, 4, 23, 0, 0))
    assert exc.value.code == "received_at_not_aware"


def test_invalid_provider_clock_is_rejected_without_payload_echo():
    p = rest_payload(updated="API_KEY=secret")
    with pytest.raises(NewsContractError) as exc:
        normalize_news(p, transport="benzinga_rest", received_at=RECEIVED)
    assert exc.value.code == "invalid_updated_at"
    assert "secret" not in str(exc.value)


def test_unsupported_action_and_transport_are_rejected():
    with pytest.raises(NewsContractError) as exc:
        normalize_news(ws_payload(action="replayed"), transport="benzinga_ws", received_at=RECEIVED)
    assert exc.value.code == "unsupported_action"
    with pytest.raises(NewsContractError) as exc2:
        normalize_news(rest_payload(), transport="mystery", received_at=RECEIVED)
    assert exc2.value.code == "unsupported_transport"


def test_oversized_title_and_body_are_rejected_with_stable_codes():
    p = rest_payload(title="x" * 4097)
    with pytest.raises(NewsContractError) as exc:
        normalize_news(p, transport="benzinga_rest", received_at=RECEIVED)
    assert exc.value.code == "title_too_large"
    p2 = rest_payload(body="x" * 5_000_001)
    with pytest.raises(NewsContractError) as exc2:
        normalize_news(p2, transport="benzinga_rest", received_at=RECEIVED)
    assert exc2.value.code == "body_too_large"


def test_normalizer_does_not_mutate_payload():
    p = ws_payload()
    before = repr(p)
    normalize_news(p, transport="benzinga_ws", received_at=RECEIVED)
    assert repr(p) == before
