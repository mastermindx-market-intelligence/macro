"""Integration tests wiring the Task-3 cluster primitive into qbus serving state."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.qbus_news_contract import normalize_news
from engine import qbus_news_store as m


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)


def _routed(
    *,
    item_id: int,
    title: str,
    minute: int = 0,
    security_ids=("sec-NVDA",),
):
    updated = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (updated - timedelta(seconds=1)).isoformat(),
            "updated": updated.isoformat(),
            "title": title,
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=updated + timedelta(seconds=2),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=tuple(security_ids),
        universe_revision="sp500-r1",
    )


def _remove(item_id: int, *, minute: int):
    event = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": f"delete-{item_id}",
            "kind": "news",
            "data": {
                "action": "deleted",
                "id": item_id,
                "timestamp": event.isoformat(),
            },
        },
        transport="benzinga_ws",
        received_at=event + timedelta(seconds=1),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=(),
        universe_revision="sp500-r1",
    )


def _rights():
    return m.NewsReadRights.all_internal()


def test_near_duplicate_provider_items_render_as_one_cluster_row(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(item_id=1, title="Nvidia launches new AI accelerator"),
                _routed(item_id=2, title="Nvidia launches its new AI accelerator", minute=1),
            ],
            expected_cursor=None,
            next_cursor="1",
        )
        snap = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=_rights())

    assert len(snap.rows) == 1
    row = snap.rows[0]
    assert row.story_id.startswith("ev2_")
    assert row.source_count == 1
    assert row.item_count == 2


def test_same_words_different_security_do_not_cluster(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(
                    item_id=1,
                    title="Company launches new AI accelerator",
                    security_ids=("sec-NVDA",),
                ),
                _routed(
                    item_id=2,
                    title="Company launches its new AI accelerator",
                    minute=1,
                    security_ids=("sec-AMD",),
                ),
            ],
            expected_cursor=None,
            next_cursor="1",
        )
        nvda = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=_rights())
        amd = store.snapshot("sec-AMD", limit=20, cursor=None, rights=_rights())

    assert len(nvda.rows) == 1
    assert len(amd.rows) == 1
    assert nvda.rows[0].story_id != amd.rows[0].story_id


def test_material_number_difference_stays_two_stories(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(item_id=1, title="Nvidia guides revenue to $8.2B"),
                _routed(item_id=2, title="Nvidia guides revenue to $9.1B", minute=1),
            ],
            expected_cursor=None,
            next_cursor="1",
        )
        snap = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=_rights())

    assert len(snap.rows) == 2
    assert len({r.story_id for r in snap.rows}) == 2


def test_existing_item_update_keeps_cluster_id_even_if_headline_changes(tmp_path):
    first = _routed(item_id=1, title="Nvidia launches accelerator")
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit([first], expected_cursor=None, next_cursor="1")
        story_before = store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=_rights()
        ).rows[0].story_id
        store.commit(
            [_routed(item_id=1, title="Nvidia corrects accelerator launch details", minute=2)],
            expected_cursor="1",
            next_cursor="2",
        )
        row = store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=_rights()
        ).rows[0]

    assert row.story_id == story_before
    assert row.title == "Nvidia corrects accelerator launch details"


def test_withdrawing_one_cluster_member_keeps_other_active_member_visible(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(item_id=1, title="Nvidia launches new AI accelerator"),
                _routed(item_id=2, title="Nvidia launches its new AI accelerator", minute=1),
            ],
            expected_cursor=None,
            next_cursor="1",
        )
        store.commit([_remove(1, minute=2)], expected_cursor="1", next_cursor="2")
        snap = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=_rights())

    assert len(snap.rows) == 1
    assert snap.rows[0].item_count == 1
    assert snap.rows[0].source_item_id == "2"


def test_withdrawing_last_active_member_removes_cluster_from_snapshot(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit([_routed(item_id=1, title="Nvidia launches accelerator")],
                     expected_cursor=None, next_cursor="1")
        story_id = store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=_rights()
        ).rows[0].story_id
        receipt = store.commit([_remove(1, minute=2)], expected_cursor="1", next_cursor="2")
        snap = store.snapshot("sec-NVDA", limit=20, cursor=None, rights=_rights())
        changes = store.changes(after_sequence=0, limit=20, rights=_rights())

    assert snap.rows == ()
    assert receipt.withdrawn_states == 1
    assert changes.rows[-1].kind == "remove"
    assert changes.rows[-1].story_id == story_id


def test_cluster_pagination_uses_cluster_sequence_not_member_count(tmp_path):
    with m.NewsStore(tmp_path / "q.sqlite3", source_key="benzinga-rest") as store:
        store.commit(
            [
                _routed(item_id=1, title="Nvidia launches new AI accelerator"),
                _routed(item_id=2, title="Nvidia launches its new AI accelerator", minute=1),
                _routed(item_id=3, title="Nvidia CFO resigns", minute=2),
            ],
            expected_cursor=None,
            next_cursor="1",
        )
        first = store.snapshot("sec-NVDA", limit=1, cursor=None, rights=_rights())
        second = store.snapshot(
            "sec-NVDA", limit=5, cursor=first.next_cursor, rights=_rights()
        )

    assert len(first.rows) == 1
    assert first.has_more is True
    assert len(second.rows) == 1
    assert first.rows[0].story_id != second.rows[0].story_id