"""Adversarial Task-5 regressions found after clustered serving review."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from collectors import massive_benzinga_news
from engine import qbus_news_store as m
from engine.qbus_news_contract import normalize_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 18, 0, tzinfo=UTC)


def _routed(
    *,
    item_id: int,
    title: str,
    minute: int = 0,
    security_ids=("sec-NVDA",),
    tickers=("NVDA",),
):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": f"teaser:{title}",
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": x} for x in tickers],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=t + timedelta(seconds=2),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=tuple(security_ids),
        universe_revision="sp500-r1",
    )


def _removed(item_id: int, minute: int):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": f"delete-{item_id}",
            "kind": "news",
            "data": {
                "action": "deleted",
                "id": item_id,
                "timestamp": t.isoformat(),
            },
        },
        transport="benzinga_ws",
        received_at=t + timedelta(seconds=1),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=(),
        universe_revision="sp500-r1",
    )


def _rights():
    return m.NewsReadRights.all_internal()


def test_partial_cluster_withdrawal_emits_live_representative_not_blank_removed_payload(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(item_id=1, title="Nvidia launches new AI accelerator"),
                _routed(
                    item_id=2,
                    title="Nvidia launches its new AI accelerator",
                    minute=1,
                ),
            ],
            expected_cursor=None,
            next_cursor="1",
        )
        prior_last = store.changes(
            after_sequence=0, limit=20, rights=_rights()
        ).rows[-1].sequence
        store.commit(
            [_removed(1, minute=2)],
            expected_cursor="1",
            next_cursor="2",
        )
        change = store.changes(
            after_sequence=prior_last, limit=20, rights=_rights()
        ).rows[-1]
        snap = store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=_rights()
        )

    assert change.kind == "upsert"
    assert change.story_id == snap.rows[0].story_id
    assert change.title == "Nvidia launches its new AI accelerator"
    assert change.source_item_id == "2"
    assert change.security_ids == ("sec-NVDA",)


def test_ticker_correction_change_targets_both_old_and_new_security(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [_routed(item_id=1, title="Nvidia launch")],
            expected_cursor=None,
            next_cursor="1",
        )
        store.commit(
            [
                _routed(
                    item_id=1,
                    title="Broadcom launch correction",
                    minute=2,
                    security_ids=("sec-AVGO",),
                    tickers=("AVGO",),
                )
            ],
            expected_cursor="1",
            next_cursor="2",
        )
        change = store.changes(
            after_sequence=1, limit=20, rights=_rights()
        ).rows[-1]

    assert set(change.security_ids) == {"sec-NVDA", "sec-AVGO"}


def test_last_member_withdrawal_targets_prior_security_not_empty_tuple(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [_routed(item_id=1, title="Nvidia launch")],
            expected_cursor=None,
            next_cursor="1",
        )
        store.commit(
            [_removed(1, minute=2)],
            expected_cursor="1",
            next_cursor="2",
        )
        change = store.changes(
            after_sequence=1, limit=20, rights=_rights()
        ).rows[-1]

    assert change.kind == "remove"
    assert change.security_ids == ("sec-NVDA",)


class _Response:
    status_code = 200
    headers = {}

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload

    def raise_for_status(self):
        return None


class _Http:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []

    def __call__(self, url, *, params, headers, timeout):
        self.calls.append(url)
        if not self.payloads:
            raise AssertionError("unexpected extra page request")
        return _Response(self.payloads.pop(0))


def test_massive_repeated_next_url_stops_and_marks_explicit_gap():
    repeated = "https://api.massive.com/benzinga/v2/news?cursor=same"
    http = _Http(
        [
            {
                "status": "OK",
                "results": [],
                "next_url": repeated,
                "request_id": "r1",
            },
            {
                "status": "OK",
                "results": [],
                "next_url": repeated,
                "request_id": "r2",
            },
        ]
    )
    client = massive_benzinga_news.MassiveBenzingaNewsClient(
        api_key="LOCAL",
        http_get=http,
        max_pages=10,
        clock=lambda: T0,
    )

    batch = client.fetch_latest()

    assert len(http.calls) == 2
    assert batch.gap_unresolved is True
    assert batch.hold_reasons == ("pagination_loop",)
    assert batch.next_url == repeated
