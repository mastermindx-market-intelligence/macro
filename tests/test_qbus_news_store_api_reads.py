"""Read/API-facing invariants for the qbus live-news store."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

import pytest

from engine.qbus_news_contract import normalize_news
from engine import qbus_news_store as m


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 16, 0, tzinfo=UTC)


def _routed(
    *,
    item_id: int = 1,
    title: str = "Nvidia launches accelerator",
    minute: int = 0,
    security_ids=("SEC:US-XNAS-NVDA",),
    tickers=("NVDA",),
):
    t = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (t - timedelta(seconds=1)).isoformat(),
            "updated": t.isoformat(),
            "title": title,
            "teaser": "teaser",
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


def _removed(item_id: int = 1, minute: int = 3):
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


def test_ticker_move_change_targets_both_old_and_new_security(tmp_path):
    db = tmp_path / "q.sqlite3"
    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="1")
        store.commit(
            [
                _routed(
                    minute=2,
                    title="Story corrected to Broadcom",
                    security_ids=("SEC:US-XNAS-AVGO",),
                    tickers=("AVGO",),
                )
            ],
            expected_cursor="1",
            next_cursor="2",
        )

        nvda = store.changes_for_security(
            "SEC:US-XNAS-NVDA",
            after_sequence=1,
            limit=20,
            rights=_rights(),
        )
        avgo = store.changes_for_security(
            "SEC:US-XNAS-AVGO",
            after_sequence=1,
            limit=20,
            rights=_rights(),
        )

    assert [x.sequence for x in nvda.rows] == [2]
    assert [x.sequence for x in avgo.rows] == [2]
    assert nvda.rows[0].story_id == avgo.rows[0].story_id


def test_withdrawal_change_remains_addressable_to_prior_security(tmp_path):
    db = tmp_path / "q.sqlite3"
    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="1")
        store.commit([_removed()], expected_cursor="1", next_cursor="2")

        page = store.changes_for_security(
            "SEC:US-XNAS-NVDA",
            after_sequence=1,
            limit=20,
            rights=_rights(),
        )

    assert len(page.rows) == 1
    assert page.rows[0].kind == "remove"
    assert page.rows[0].security_ids == ("SEC:US-XNAS-NVDA",)


def test_changes_for_security_does_not_leak_other_tickers(tmp_path):
    db = tmp_path / "q.sqlite3"
    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(item_id=1, security_ids=("SEC:US-XNAS-NVDA",)),
                _routed(
                    item_id=2,
                    title="AMD story",
                    minute=1,
                    security_ids=("SEC:US-XNAS-AMD",),
                    tickers=("AMD",),
                ),
            ],
            expected_cursor=None,
            next_cursor="1",
        )

        nvda = store.changes_for_security(
            "SEC:US-XNAS-NVDA",
            after_sequence=0,
            limit=20,
            rights=_rights(),
        )

    assert [x.source_item_id for x in nvda.rows] == ["1"]


def test_story_returns_grouped_active_members_and_respects_field_rights(tmp_path):
    db = tmp_path / "q.sqlite3"
    with m.NewsStore(db, source_key="benzinga-rest") as store:
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
        story_id = store.snapshot(
            "SEC:US-XNAS-NVDA", limit=10, cursor=None, rights=_rights()
        ).rows[0].story_id

        detail = store.story(
            story_id,
            rights=m.NewsReadRights(
                allowed_sources=frozenset({"benzinga"}),
                allow_title=True,
                allow_url=False,
                allow_teaser=False,
            ),
        )

    assert detail is not None
    assert detail.story_id == story_id
    assert detail.item_count == 2
    assert detail.source_count == 1
    assert {x.source_item_id for x in detail.members} == {"1", "2"}
    assert all(x.url == "" and x.teaser == "" for x in detail.members)


def test_story_returns_none_after_last_member_withdrawn(tmp_path):
    db = tmp_path / "q.sqlite3"
    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="1")
        story_id = store.snapshot(
            "SEC:US-XNAS-NVDA", limit=10, cursor=None, rights=_rights()
        ).rows[0].story_id
        store.commit([_removed()], expected_cursor="1", next_cursor="2")
        assert store.story(story_id, rights=_rights()) is None


def test_read_only_open_never_creates_database_and_refuses_commit(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    with pytest.raises(m.StoreUnavailable):
        m.NewsStore.open_readonly(missing, source_key="benzinga-rest")
    assert not missing.exists()

    db = tmp_path / "q.sqlite3"
    with m.NewsStore(db, source_key="benzinga-rest") as store:
        store.commit([_routed()], expected_cursor=None, next_cursor="1")

    before = db.read_bytes()
    reader = m.NewsStore.open_readonly(db, source_key="benzinga-rest")
    try:
        rows = reader.snapshot(
            "SEC:US-XNAS-NVDA", limit=10, cursor=None, rights=_rights()
        ).rows
        assert len(rows) == 1
        with pytest.raises(m.ReadOnlyStore):
            reader.commit([], expected_cursor="1", next_cursor="2")
    finally:
        reader.close()
    assert db.read_bytes() == before


def test_read_only_open_refuses_wrong_schema_without_mutating_file(tmp_path):
    db = tmp_path / "wrong.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute("create table qbus_meta(key text primary key, value text not null)")
    conn.execute("insert into qbus_meta values('schema','wrong.v1')")
    conn.commit()
    conn.close()
    before = db.read_bytes()

    with pytest.raises(m.StoreSchemaError):
        m.NewsStore.open_readonly(db, source_key="benzinga-rest")

    assert db.read_bytes() == before
