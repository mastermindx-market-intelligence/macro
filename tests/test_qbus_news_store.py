"""Transactional persistence tests for qbus live-news revisions.

Task-4 tests are hermetic and never touch the production qbus parquet or provider network.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import os
import sqlite3

import pytest

from engine.qbus_news_contract import normalize_news


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 2, 0, tzinfo=UTC)


def _rest_payload(
    *,
    item_id: int,
    title: str,
    updated: datetime,
    tickers: tuple[str, ...] = ("NVDA",),
) -> dict:
    stamp = updated.astimezone(UTC).isoformat().replace("+00:00", "Z")
    published = (updated - timedelta(seconds=1)).astimezone(UTC).isoformat().replace("+00:00", "Z")
    return {
        "id": item_id,
        "created": published,
        "updated": stamp,
        "title": title,
        "teaser": f"teaser:{title}",
        "body": f"body:{title}",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": [{"name": "News"}],
        "stocks": [{"name": t} for t in tickers],
        "tags": [{"name": "breaking"}],
    }


def _routed(
    store_mod,
    *,
    item_id: int = 1,
    title: str = "Nvidia launches accelerator",
    minute: int = 0,
    security_ids: tuple[str, ...] = ("sec-NVDA",),
    tickers: tuple[str, ...] = ("NVDA",),
):
    received = T0 + timedelta(minutes=minute, seconds=5)
    revision = normalize_news(
        _rest_payload(
            item_id=item_id,
            title=title,
            updated=T0 + timedelta(minutes=minute),
            tickers=tickers,
        ),
        transport="benzinga_rest",
        received_at=received,
    )
    return store_mod.RoutedRevision(
        revision=revision,
        security_ids=security_ids,
        universe_revision="sp500-r1",
    )


def _removed(store_mod, *, item_id: int = 1, minute: int = 2):
    event = T0 + timedelta(minutes=minute)
    payload = {
        "id": f"msg-delete-{item_id}",
        "api_version": "websocket/v1",
        "kind": "news",
        "data": {
            "action": "Deleted",
            "id": item_id,
            "timestamp": event.isoformat().replace("+00:00", "Z"),
        },
    }
    revision = normalize_news(
        payload,
        transport="benzinga_ws",
        received_at=event + timedelta(seconds=1),
    )
    return store_mod.RoutedRevision(
        revision=revision,
        security_ids=(),
        universe_revision="sp500-r1",
    )


def _massive_conflict(store_mod, *, item_id: int = 1, title: str = "Mirror differs"):
    payload = {
        "benzinga_id": item_id,
        "published": T0.isoformat().replace("+00:00", "Z"),
        "last_updated": (T0 + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        "title": title,
        "teaser": "mirror",
        "body": "mirror body",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": ["News"],
        "tickers": ["NVDA"],
        "tags": ["breaking"],
    }
    revision = normalize_news(
        payload,
        transport="massive_benzinga_v2",
        received_at=T0 + timedelta(hours=1, seconds=2),
    )
    return store_mod.RoutedRevision(
        revision=revision,
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )


def test_store_module_and_required_interfaces_exist():
    from engine import qbus_news_store as m

    assert m.SCHEMA == "qbus.news_store.v1"
    assert callable(m.NewsStore)
    assert callable(m.RoutedRevision)
    assert callable(m.NewsReadRights)


def test_first_commit_is_atomic_and_snapshot_is_security_indexed(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        receipt = store.commit([_routed(m)], expected_cursor=None, next_cursor="c1")
        assert receipt.cursor == "c1"
        assert receipt.inserted_revisions == 1
        assert receipt.applied_states == 1
        assert receipt.first_sequence == receipt.last_sequence == 1

        snap = store.snapshot(
            "sec-NVDA",
            limit=20,
            cursor=None,
            rights=m.NewsReadRights.all_internal(),
        )
        assert snap.security_id == "sec-NVDA"
        assert snap.rows[0].source == "benzinga"
        assert snap.rows[0].source_item_id == "1"
        assert snap.rows[0].title == "Nvidia launches accelerator"
        assert snap.rows[0].sequence == 1
        assert snap.rows[0].universe_revision == "sp500-r1"
        assert store.current_cursor() == "c1"


def test_cursor_compare_and_swap_refuses_stale_writer_without_side_effect(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m, item_id=1)], expected_cursor=None, next_cursor="c1")
        before = store.counts()
        with pytest.raises(m.CursorConflict) as exc:
            store.commit(
                [_routed(m, item_id=2, minute=1)],
                expected_cursor=None,
                next_cursor="c2",
            )
        assert exc.value.expected is None
        assert exc.value.actual == "c1"
        assert store.current_cursor() == "c1"
        assert store.counts() == before
        assert store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=m.NewsReadRights.all_internal()
        ).rows[0].source_item_id == "1"


def test_exact_replay_advances_cursor_but_does_not_emit_duplicate_change(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    routed = _routed(m)
    with m.NewsStore(db, source_key="benzinga-live") as store:
        first = store.commit([routed], expected_cursor=None, next_cursor="c1")
        replay = store.commit([routed], expected_cursor="c1", next_cursor="c2")
        assert first.last_sequence == 1
        assert replay.inserted_revisions == 0
        assert replay.duplicate_revisions == 1
        assert replay.first_sequence is None
        assert replay.last_sequence is None
        assert store.current_cursor() == "c2"
        assert store.counts()["changes"] == 1


def test_newer_update_moves_security_index_in_same_transaction(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m)], expected_cursor=None, next_cursor="c1")
        update = _routed(
            m,
            title="Nvidia accelerator story corrected to AVGO",
            minute=1,
            security_ids=("sec-AVGO",),
            tickers=("AVGO",),
        )
        receipt = store.commit([update], expected_cursor="c1", next_cursor="c2")
        assert receipt.applied_states == 1
        assert store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=m.NewsReadRights.all_internal()
        ).rows == ()
        avgo = store.snapshot(
            "sec-AVGO", limit=20, cursor=None, rights=m.NewsReadRights.all_internal()
        )
        assert avgo.rows[0].title == "Nvidia accelerator story corrected to AVGO"
        assert avgo.rows[0].sequence == 2


def test_explicit_withdrawal_removes_index_and_emits_remove_change(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m)], expected_cursor=None, next_cursor="c1")
        receipt = store.commit([_removed(m)], expected_cursor="c1", next_cursor="c2")
        assert receipt.withdrawn_states == 1
        assert store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=m.NewsReadRights.all_internal()
        ).rows == ()
        page = store.changes(
            after_sequence=0,
            limit=20,
            rights=m.NewsReadRights.all_internal(),
        )
        assert [x.kind for x in page.rows] == ["upsert", "remove"]
        assert page.rows[-1].source_item_id == "1"


def test_lower_authority_mirror_conflict_is_recorded_but_not_projected(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m, title="Direct source")], expected_cursor=None, next_cursor="c1")
        receipt = store.commit(
            [_massive_conflict(m, title="Mirror differs")],
            expected_cursor="c1",
            next_cursor="c2",
        )
        assert receipt.inserted_revisions == 1
        assert receipt.conflict_revisions == 1
        assert receipt.applied_states == 0
        assert store.counts()["revisions"] == 2
        assert store.counts()["changes"] == 1
        snap = store.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=m.NewsReadRights.all_internal()
        )
        assert snap.rows[0].title == "Direct source"


def test_transaction_rolls_back_revision_state_index_change_and_cursor_on_failure(tmp_path, monkeypatch):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    original = m.reduce_revision
    calls = 0

    def fail_second(previous, incoming, *, restoration_qualified=False):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic reducer crash")
        return original(
            previous,
            incoming,
            restoration_qualified=restoration_qualified,
        )

    monkeypatch.setattr(m, "reduce_revision", fail_second)
    with m.NewsStore(db, source_key="benzinga-live") as store:
        with pytest.raises(RuntimeError, match="synthetic reducer crash"):
            store.commit(
                [
                    _routed(m, item_id=1),
                    _routed(m, item_id=2, minute=1),
                ],
                expected_cursor=None,
                next_cursor="c2",
            )
        assert store.current_cursor() is None
        assert store.counts() == {
            "revisions": 0,
            "states": 0,
            "security_index": 0,
            "changes": 0,
            "legacy_items": 0,
        }


def test_restart_preserves_cursor_state_and_index(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m)], expected_cursor=None, next_cursor="c1")
    with m.NewsStore(db, source_key="benzinga-live") as reopened:
        assert reopened.current_cursor() == "c1"
        rows = reopened.snapshot(
            "sec-NVDA", limit=20, cursor=None, rights=m.NewsReadRights.all_internal()
        ).rows
        assert len(rows) == 1 and rows[0].source_item_id == "1"


def test_revision_id_collision_with_different_persisted_bytes_refuses(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    routed = _routed(m)
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([routed], expected_cursor=None, next_cursor="c1")
        impossible = replace(
            routed.revision,
            title="different bytes but forged same revision id",
        )
        with pytest.raises(m.RevisionCollision):
            store.commit(
                [replace(routed, revision=impossible)],
                expected_cursor="c1",
                next_cursor="c2",
            )
        assert store.current_cursor() == "c1"


def test_read_rights_filter_source_and_fields_without_changing_canonical_state(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m)], expected_cursor=None, next_cursor="c1")
        none = store.snapshot(
            "sec-NVDA",
            limit=20,
            cursor=None,
            rights=m.NewsReadRights(allowed_sources=frozenset()),
        )
        assert none.rows == ()
        metadata_only = store.snapshot(
            "sec-NVDA",
            limit=20,
            cursor=None,
            rights=m.NewsReadRights(
                allowed_sources=frozenset({"benzinga"}),
                allow_title=True,
                allow_url=False,
                allow_teaser=False,
            ),
        )
        assert metadata_only.rows[0].title == "Nvidia launches accelerator"
        assert metadata_only.rows[0].url == ""
        assert metadata_only.rows[0].teaser == ""
        assert store.counts()["states"] == 1


def test_changes_are_sequence_cursor_bounded_and_rights_filtered(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m, item_id=1)], expected_cursor=None, next_cursor="c1")
        store.commit([_routed(m, item_id=2, minute=1)], expected_cursor="c1", next_cursor="c2")
        first = store.changes(
            after_sequence=0,
            limit=1,
            rights=m.NewsReadRights.all_internal(),
        )
        assert [x.sequence for x in first.rows] == [1]
        assert first.next_sequence == 1
        assert first.has_more is True
        second = store.changes(
            after_sequence=first.next_sequence,
            limit=10,
            rights=m.NewsReadRights.all_internal(),
        )
        assert [x.sequence for x in second.rows] == [2]
        denied = store.changes(
            after_sequence=0,
            limit=10,
            rights=m.NewsReadRights(allowed_sources=frozenset()),
        )
        assert denied.rows == ()


def test_database_file_is_private_and_can_be_opened_read_only(tmp_path):
    from engine import qbus_news_store as m

    db = tmp_path / "qbus.sqlite3"
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([_routed(m)], expected_cursor=None, next_cursor="c1")
    assert (os.stat(db).st_mode & 0o077) == 0
    ro = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        assert ro.execute("select count(*) from news_revisions").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            ro.execute("delete from news_revisions")
    finally:
        ro.close()