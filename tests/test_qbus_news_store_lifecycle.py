"""Lifecycle pins for qbus news reduction and the transactional store.

Each test names one frozen case (correction, withdrawal, duplicate delivery,
cross-transport delivery, stale revision, change cursor, read-only open,
field redaction). Builds use offline fixtures only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engine.qbus_news_contract import normalize_news
from engine.qbus_news_reducer import reduce_revision
from engine import qbus_news_store as m


UTC = timezone.utc
T0 = datetime(2026, 10, 5, 15, 0, tzinfo=UTC)
ALPACA_AT = datetime(2026, 10, 11, 14, 30, 5, tzinfo=UTC)


def _rights():
    return m.NewsReadRights.all_internal()


def _rest(
    *,
    item_id: int,
    title: str,
    minute: int = 0,
    teaser: str | None = None,
    security_ids: tuple[str, ...] = ("sec-NVDA",),
    tickers: tuple[str, ...] = ("NVDA",),
):
    updated = T0 + timedelta(minutes=minute)
    revision = normalize_news(
        {
            "id": item_id,
            "created": (updated - timedelta(seconds=1)).isoformat(),
            "updated": updated.isoformat(),
            "title": title,
            "teaser": teaser if teaser is not None else f"teaser:{title}",
            "url": f"https://www.benzinga.com/news/{item_id}",
            "stocks": [{"name": ticker} for ticker in tickers],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=updated + timedelta(seconds=2),
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=security_ids,
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


def _alpaca(transport: str, received_at: datetime):
    revision = normalize_news(
        {
            "id": 501,
            "headline": "Nvidia launches accelerator",
            "created_at": "2026-10-11T14:29:00Z",
            "updated_at": "2026-10-11T14:30:01Z",
            "summary": "alpaca-teaser-keep",
            "url": "https://www.benzinga.com/news/501",
            "symbols": ["NVDA"],
            "source": "benzinga",
        },
        transport=transport,
        received_at=received_at,
    )
    return m.RoutedRevision(
        revision=revision,
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )


def _open(tmp_path, source_key="benzinga-live"):
    return m.NewsStore(tmp_path / "q.sqlite3", source_key=source_key)


def _snap(store, security_id="sec-NVDA", rights=None):
    return store.snapshot(
        security_id,
        limit=20,
        cursor=None,
        rights=rights or _rights(),
    )


def _changes(store, *, after_sequence=0, rights=None, security_id=None):
    rights = rights or _rights()
    if security_id is None:
        return store.changes(after_sequence=after_sequence, limit=20, rights=rights)
    return store.changes_for_security(
        security_id,
        after_sequence=after_sequence,
        limit=20,
        rights=rights,
    )


def test_correction_of_open_story_updates_snapshot_once_and_emits_one_change(tmp_path):
    original = _rest(item_id=7, title="Nvidia launches accelerator", minute=0)
    corrected_title = "Broadcom shipment date fully rewritten"
    corrected = _rest(item_id=7, title=corrected_title, minute=4)

    reduced = reduce_revision(None, original.revision)
    assert reduced.disposition == "accepted"
    correction = reduce_revision(reduced.state, corrected.revision)
    assert correction.disposition == "accepted"
    assert correction.reason == "newer_same_domain_revision"
    assert correction.state.title == corrected_title
    assert correction.state.source_item_id == original.revision.source_item_id

    with _open(tmp_path) as store:
        store.commit([original], expected_cursor=None, next_cursor="c1")
        before = _snap(store)
        assert len(before.rows) == 1
        story_id = before.rows[0].story_id
        receipt = store.commit([corrected], expected_cursor="c1", next_cursor="c2")
        snap = _snap(store)
        feed = _changes(store)
        scoped = _changes(store, security_id="sec-NVDA")

    assert receipt.applied_states == 1
    assert receipt.duplicate_revisions == 0
    assert receipt.stale_revisions == 0
    assert len(snap.rows) == 1
    assert snap.rows[0].story_id == story_id
    assert snap.rows[0].title == corrected_title
    assert snap.rows[0].teaser == f"teaser:{corrected_title}"
    assert snap.rows[0].source_item_id == "7"
    assert [row.title for row in snap.rows].count(corrected_title) == 1
    assert original.revision.title not in [row.title for row in snap.rows]

    assert [row.kind for row in feed.rows] == ["upsert", "upsert"]
    corrected_rows = [row for row in feed.rows if row.title == corrected_title]
    assert len(corrected_rows) == 1
    assert corrected_rows[0].story_id == story_id
    assert corrected_rows[0].source_item_id == "7"
    assert [row.sequence for row in scoped.rows] == [row.sequence for row in feed.rows]
    assert [row.title for row in scoped.rows] == [row.title for row in feed.rows]


def test_withdrawal_of_open_single_source_story_is_absent_and_emitted_once(tmp_path):
    routed = _rest(item_id=1, title="Nvidia launches accelerator")
    removed = _remove(1, minute=3)
    active = reduce_revision(None, routed.revision)
    withdrawal = reduce_revision(active.state, removed.revision)
    assert withdrawal.disposition == "withdrawn"
    assert withdrawal.reason == "explicit_source_withdrawal"
    assert withdrawal.state.status == "withdrawn"
    assert withdrawal.state.title == ""

    with _open(tmp_path) as store:
        store.commit([routed], expected_cursor=None, next_cursor="c1")
        story_id = _snap(store).rows[0].story_id
        receipt = store.commit([removed], expected_cursor="c1", next_cursor="c2")
        snap = _snap(store)
        detail = store.story(story_id, rights=_rights())
        feed = _changes(store)
        scoped = _changes(store, security_id="sec-NVDA")

    assert receipt.withdrawn_states == 1
    assert receipt.applied_states == 0
    assert snap.rows == ()
    assert detail is None
    removes = [row for row in feed.rows if row.kind == "remove" and row.story_id == story_id]
    assert len(removes) == 1
    assert removes[0].source_item_id == "1"
    scoped_removes = [row for row in scoped.rows if row.kind == "remove"]
    assert len(scoped_removes) == 1
    assert scoped_removes[0].sequence == removes[0].sequence
    assert scoped_removes[0].security_ids == ("sec-NVDA",)


def test_withdrawal_of_visible_cluster_member_keeps_survivor_title_and_teaser(tmp_path):
    survivor_title = "Nvidia launches new AI accelerator"
    visible_title = "Nvidia launches its new AI accelerator"
    survivor_teaser = "survivor-teaser-alpha"
    visible_teaser = "visible-teaser-beta"
    survivor = _rest(
        item_id=11,
        title=survivor_title,
        minute=0,
        teaser=survivor_teaser,
    )
    visible = _rest(
        item_id=12,
        title=visible_title,
        minute=1,
        teaser=visible_teaser,
    )

    with _open(tmp_path) as store:
        store.commit([survivor, visible], expected_cursor=None, next_cursor="c1")
        before = _snap(store)
        assert len(before.rows) == 1
        assert before.rows[0].item_count == 2
        assert before.rows[0].source_item_id == "12"
        assert before.rows[0].title == visible_title
        assert before.rows[0].teaser == visible_teaser
        story_id = before.rows[0].story_id
        prior_last = _changes(store).rows[-1].sequence
        receipt = store.commit([_remove(12, minute=3)], expected_cursor="c1", next_cursor="c2")
        snap = _snap(store)
        detail = store.story(story_id, rights=_rights())
        fresh = [row for row in _changes(store, after_sequence=prior_last).rows]
        scoped = [
            row
            for row in _changes(
                store, after_sequence=prior_last, security_id="sec-NVDA"
            ).rows
        ]

    assert receipt.withdrawn_states == 1
    assert len(snap.rows) == 1
    row = snap.rows[0]
    assert row.story_id == story_id
    assert row.item_count == 1
    assert row.source_item_id == "11"
    assert row.title == survivor_title
    assert row.teaser == survivor_teaser
    assert row.url == "https://www.benzinga.com/news/11"
    assert row.title != ""
    assert row.teaser != ""
    assert visible_teaser not in (row.title, row.teaser, row.url)

    assert detail is not None
    assert detail.item_count == 1
    assert [member.source_item_id for member in detail.members] == ["11"]
    assert detail.members[0].title == survivor_title
    assert detail.members[0].teaser == survivor_teaser
    assert detail.members[0].url == "https://www.benzinga.com/news/11"

    assert len(fresh) == 1
    assert fresh[0].kind == "upsert"
    assert fresh[0].story_id == story_id
    assert fresh[0].source_item_id == "11"
    assert fresh[0].title == survivor_title
    assert fresh[0].teaser == survivor_teaser
    assert fresh[0].url == "https://www.benzinga.com/news/11"
    assert scoped == list(fresh)


def test_partial_cluster_withdrawal_never_refeeds_paged_cluster_and_pins_row_sequence(tmp_path):
    survivor_title = "Nvidia launches new AI accelerator"
    visible_title = "Nvidia launches its new AI accelerator"
    survivor = _rest(item_id=11, title=survivor_title, minute=0)
    visible = _rest(item_id=12, title=visible_title, minute=1)
    outside = _rest(item_id=30, title="Nvidia CFO resigns", minute=2)

    with _open(tmp_path) as store:
        store.commit(
            [survivor, visible, outside], expected_cursor=None, next_cursor="c1"
        )
        page_one = store.snapshot(
            "sec-NVDA", limit=1, cursor=None, rights=_rights()
        )
        assert [row.source_item_id for row in page_one.rows] == ["30"]
        assert page_one.next_cursor == 3
        page_two = store.snapshot(
            "sec-NVDA", limit=5, cursor=3, rights=_rights()
        )
        assert [row.source_item_id for row in page_two.rows] == ["12"]
        assert page_two.next_cursor == 2
        story_id = page_two.rows[0].story_id

        receipt = store.commit(
            [_remove(12, minute=3)], expected_cursor="c1", next_cursor="c2"
        )
        continuation = store.snapshot(
            "sec-NVDA", limit=5, cursor=2, rights=_rights()
        )
        fresh = _snap(store)
        scoped = _changes(store, security_id="sec-NVDA")

    assert receipt.withdrawn_states == 1
    # The client already received this cluster on page two (watermark 2). The
    # partial withdrawal moves the cluster watermark FORWARD to the withdrawal
    # upsert, so continuing from cursor 2 must not re-feed it.
    assert continuation.rows == ()
    assert continuation.next_cursor == 2
    assert continuation.has_more is False

    # Every visible row's sequence equals the latest change row addressed to
    # this security for that cluster, for corrections and withdrawals alike.
    latest_change: dict[str, int] = {}
    for row in scoped.rows:
        latest_change[row.story_id] = max(
            latest_change.get(row.story_id, 0), row.sequence
        )
    assert [row.source_item_id for row in fresh.rows] == ["11", "30"]
    assert fresh.rows[0].story_id == story_id
    assert fresh.rows[0].title == survivor_title
    withdrawal_upsert = [
        row for row in scoped.rows if row.source_item_id == "11"
    ][-1]
    assert fresh.rows[0].sequence == withdrawal_upsert.sequence
    for row in fresh.rows:
        assert row.sequence == latest_change[row.story_id]


def test_partial_withdrawal_representative_is_newest_survivor_of_three_member_cluster(tmp_path):
    oldest_title = "Nvidia launches new AI accelerator"
    middle_title = "Nvidia launches its new AI accelerator"
    newest_title = "Nvidia launches a new AI accelerator"
    oldest = _rest(
        item_id=21, title=oldest_title, minute=0, teaser="survivor-teaser-oldest"
    )
    middle = _rest(
        item_id=22, title=middle_title, minute=1, teaser="survivor-teaser-middle"
    )
    newest = _rest(
        item_id=23, title=newest_title, minute=2, teaser="teaser-newest"
    )

    with _open(tmp_path) as store:
        store.commit(
            [oldest, middle, newest], expected_cursor=None, next_cursor="c1"
        )
        before = _snap(store)
        assert len(before.rows) == 1
        assert before.rows[0].item_count == 3
        story_id = before.rows[0].story_id
        detail = store.story(story_id, rights=_rights())
        assert {member.source_item_id for member in detail.members} == {
            "21",
            "22",
            "23",
        }
        prior_last = _changes(store).rows[-1].sequence

        store.commit([_remove(23, minute=3)], expected_cursor="c1", next_cursor="c2")
        snap = _snap(store)
        fresh = _changes(store, after_sequence=prior_last).rows

    # The newest member was the representative; withdrawing it must promote
    # the newest SURVIVOR (item 22), not the oldest member.
    assert len(fresh) == 1
    assert fresh[0].kind == "upsert"
    assert fresh[0].story_id == story_id
    assert fresh[0].source_item_id == "22"
    assert fresh[0].title == middle_title
    assert fresh[0].teaser == "survivor-teaser-middle"

    assert len(snap.rows) == 1
    assert snap.rows[0].story_id == story_id
    assert snap.rows[0].item_count == 2
    assert snap.rows[0].source_item_id == "22"
    assert snap.rows[0].title == middle_title
    assert snap.rows[0].teaser == "survivor-teaser-middle"
    assert oldest_title not in (fresh[0].title, snap.rows[0].title)


def test_identical_revision_committed_twice_is_duplicate_without_second_change(tmp_path):
    first = _rest(item_id=3, title="Nvidia launches accelerator", minute=0)
    replay = _rest(item_id=3, title="Nvidia launches accelerator", minute=0)
    assert first.revision.content_hash == replay.revision.content_hash
    assert first.revision.revision_id == replay.revision.revision_id
    assert first.revision == replay.revision

    reduced = reduce_revision(None, first.revision)
    again = reduce_revision(reduced.state, replay.revision)
    assert again.disposition == "duplicate"
    assert again.reason == "same_revision"
    assert again.state == reduced.state
    assert again.added_tickers == () and again.removed_tickers == ()

    with _open(tmp_path) as store:
        opened = store.commit([first], expected_cursor=None, next_cursor="c1")
        before_snap = _snap(store)
        before_feed = _changes(store)
        before_counts = store.counts()
        receipt = store.commit([replay], expected_cursor="c1", next_cursor="c2")
        after_snap = _snap(store)
        after_feed = _changes(store)
        counts = store.counts()

    assert opened.inserted_revisions == 1
    assert opened.last_sequence == 1
    assert receipt.inserted_revisions == 0
    assert receipt.duplicate_revisions == 1
    assert receipt.applied_states == 0
    assert receipt.stale_revisions == 0
    assert receipt.first_sequence is None
    assert receipt.last_sequence is None
    assert after_snap.rows == before_snap.rows
    assert after_feed.rows == before_feed.rows
    assert len(after_feed.rows) == 1
    assert counts["changes"] == before_counts["changes"] == 1
    assert counts["revisions"] == 1
    assert counts["states"] == 1


def test_same_revision_via_alpaca_rest_then_ws_is_one_story_and_delivery_only(tmp_path):
    rest = _alpaca("alpaca_rest", ALPACA_AT)
    ws = _alpaca("alpaca_ws", ALPACA_AT + timedelta(seconds=17))
    assert rest.revision.revision_id == ws.revision.revision_id
    assert rest.revision.content_hash == ws.revision.content_hash
    assert rest.revision.transport != ws.revision.transport
    assert rest.revision.received_at != ws.revision.received_at

    reduced = reduce_revision(None, rest.revision)
    second = reduce_revision(reduced.state, ws.revision)
    assert second.disposition == "duplicate"
    assert second.reason == "same_revision"
    assert second.state.title == reduced.state.title
    assert second.state.last_received_at == ws.revision.received_at
    assert second.state.first_received_at == rest.revision.received_at

    with _open(tmp_path, source_key="alpaca-rest") as store:
        opened = store.commit([rest], expected_cursor=None, next_cursor="rest-1")
        story_id = _snap(store).rows[0].story_id
        cursor_before = store.current_cursor()
        receipt = store.commit_observations([ws])
        snap = _snap(store)
        feed = _changes(store)
        scoped = _changes(store, security_id="sec-NVDA")
        deliveries = store._conn.execute(
            """
            SELECT revision_id, transport, message_id, received_at
            FROM news_deliveries
            ORDER BY delivery_id
            """
        ).fetchall()
        counts = store.counts()

    assert opened.inserted_revisions == 1
    assert opened.applied_states == 1
    assert cursor_before == "rest-1"
    assert receipt.cursor == "rest-1"
    assert receipt.inserted_revisions == 0
    assert receipt.duplicate_revisions == 1
    assert receipt.applied_states == 0
    assert receipt.first_sequence is None
    assert receipt.last_sequence is None
    assert counts["revisions"] == 1
    assert counts["states"] == 1
    assert counts["changes"] == 1
    assert len(snap.rows) == 1
    assert snap.rows[0].story_id == story_id
    assert snap.rows[0].title == "Nvidia launches accelerator"
    assert snap.rows[0].teaser == "alpaca-teaser-keep"
    assert snap.rows[0].url == "https://www.benzinga.com/news/501"
    assert snap.rows[0].updated_at == rest.revision.updated_at
    assert snap.rows[0].received_at == ws.revision.received_at
    assert [row.kind for row in feed.rows] == ["upsert"]
    assert feed.rows[0].title == "Nvidia launches accelerator"
    assert [row.sequence for row in scoped.rows] == [feed.rows[0].sequence]
    assert len(deliveries) == 2
    assert [row["transport"] for row in deliveries] == ["alpaca_rest", "alpaca_ws"]
    assert {row["revision_id"] for row in deliveries} == {rest.revision.revision_id}
    assert [row["message_id"] for row in deliveries] == ["", ""]


def test_stale_older_revision_does_not_regress_projected_fields(tmp_path):
    newer = _rest(item_id=9, title="Newer headline", minute=5, teaser="teaser-newer")
    older = _rest(item_id=9, title="Older headline", minute=1, teaser="teaser-older")
    assert older.revision.updated_at < newer.revision.updated_at
    assert older.revision.content_hash != newer.revision.content_hash
    assert older.revision.revision_id != newer.revision.revision_id

    current = reduce_revision(None, newer.revision).state
    stale = reduce_revision(current, older.revision)
    assert stale.disposition == "stale"
    assert stale.reason == "older_same_domain_revision"
    assert stale.state == current
    assert stale.state.title == "Newer headline"
    assert stale.state.teaser == "teaser-newer"

    with _open(tmp_path) as store:
        store.commit([newer], expected_cursor=None, next_cursor="c1")
        before = _snap(store)
        before_feed = _changes(store)
        receipt = store.commit([older], expected_cursor="c1", next_cursor="c2")
        snap = _snap(store)
        feed = _changes(store)
        counts = store.counts()

    assert receipt.stale_revisions == 1
    assert receipt.inserted_revisions == 1
    assert receipt.duplicate_revisions == 0
    assert receipt.applied_states == 0
    assert receipt.conflict_revisions == 0
    assert receipt.first_sequence is None
    assert snap.rows == before.rows
    assert snap.rows[0].title == "Newer headline"
    assert snap.rows[0].teaser == "teaser-newer"
    assert snap.rows[0].url == before.rows[0].url
    assert snap.rows[0].updated_at == newer.revision.updated_at
    assert feed.rows == before_feed.rows
    assert len(feed.rows) == 1
    assert counts["changes"] == 1
    assert counts["states"] == 1
    assert counts["revisions"] == 2


def test_changes_cursor_malformed_foreign_and_older_than_retention(tmp_path):
    with _open(tmp_path) as local:
        local.commit(
            [
                _rest(item_id=1, title="First local story"),
                _rest(item_id=2, title="Second local story", minute=1),
            ],
            expected_cursor=None,
            next_cursor="local-cursor",
        )
        oldest = _changes(local)
        assert [row.sequence for row in oldest.rows] == [1, 2]
        assert oldest.rows[0].source_item_id == "1"
        assert oldest.rows[0].title == "First local story"

        malformed = (
            "cursor-from-elsewhere",
            "c1",
            "",
            None,
            -1,
            True,
            False,
            1.5,
        )
        for bad in malformed:
            with pytest.raises(m.StoreValidationError, match="invalid_sequence"):
                local.changes(after_sequence=bad, limit=20, rights=_rights())

        other_db = tmp_path / "other.sqlite3"
        with m.NewsStore(other_db, source_key="other-writer") as other:
            other.commit(
                [
                    _rest(item_id=100 + i, title=f"Foreign story {i}", minute=i)
                    for i in range(4)
                ],
                expected_cursor=None,
                next_cursor="foreign-cursor",
            )
            foreign_cursor = other.current_cursor()
            foreign_tail = _changes(other).rows[-1].sequence

        assert foreign_cursor == "foreign-cursor"
        assert foreign_tail == 4
        with pytest.raises(m.StoreValidationError, match="invalid_sequence"):
            local.changes(after_sequence=foreign_cursor, limit=20, rights=_rights())

        ahead = local.changes(after_sequence=foreign_tail, limit=20, rights=_rights())
        assert ahead.rows == ()
        assert ahead.next_sequence == foreign_tail
        assert ahead.has_more is False

        # A foreign integer watermark is a local sequence compare. It is not
        # authenticated against the other store and does not raise CursorConflict.
        overlapped = local.changes(after_sequence=1, limit=20, rights=_rights())
        assert [row.source_item_id for row in overlapped.rows] == ["2"]
        assert overlapped.rows[0].title == "Second local story"

        retained = local.changes(after_sequence=0, limit=20, rights=_rights())
        assert [row.sequence for row in retained.rows] == [1, 2]
        assert retained.rows[0].title == "First local story"
        assert local.current_cursor() == "local-cursor"


def test_readonly_missing_file_is_unavailable_and_commit_is_read_only(tmp_path):
    missing = tmp_path / "absent" / "news.sqlite3"
    with pytest.raises(m.StoreUnavailable, match="unavailable"):
        m.NewsStore.open_readonly(missing, source_key="benzinga-live")
    assert not missing.exists()
    assert not missing.parent.exists()

    db = tmp_path / "q.sqlite3"
    routed = _rest(item_id=1, title="Nvidia launches accelerator")
    extra = _rest(item_id=2, title="A second story", minute=1)
    with m.NewsStore(db, source_key="benzinga-live") as store:
        store.commit([routed], expected_cursor=None, next_cursor="c1")
    before = db.read_bytes()

    reader = m.NewsStore.open_readonly(db, source_key="benzinga-live")
    try:
        assert reader.snapshot(
            "sec-NVDA", limit=10, cursor=None, rights=_rights()
        ).rows[0].title == "Nvidia launches accelerator"
        with pytest.raises(m.ReadOnlyStore, match="read_only"):
            reader.commit([extra], expected_cursor="c1", next_cursor="c2")
        with pytest.raises(m.ReadOnlyStore, match="read_only"):
            reader.commit_observations([extra])
        assert reader.current_cursor() == "c1"
        assert len(reader.snapshot(
            "sec-NVDA", limit=10, cursor=None, rights=_rights()
        ).rows) == 1
    finally:
        reader.close()
    assert db.read_bytes() == before


def test_rights_redaction_parity_across_snapshot_story_and_changes(tmp_path):
    title = "Visible headline stays"
    teaser = "secret-teaser-must-hide"
    url = "https://www.benzinga.com/news/secret-url"
    updated = T0
    revision = normalize_news(
        {
            "id": 21,
            "created": (updated - timedelta(seconds=1)).isoformat(),
            "updated": updated.isoformat(),
            "title": title,
            "teaser": teaser,
            "url": url,
            "stocks": [{"name": "NVDA"}],
            "channels": [{"name": "News"}],
            "tags": [],
        },
        transport="benzinga_rest",
        received_at=updated + timedelta(seconds=2),
    )
    routed = m.RoutedRevision(
        revision=revision,
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )
    redacted = m.NewsReadRights(
        allowed_sources=frozenset({"benzinga"}),
        allow_title=True,
        allow_url=False,
        allow_teaser=False,
    )

    with _open(tmp_path) as store:
        store.commit([routed], expected_cursor=None, next_cursor="c1")
        snap = _snap(store, rights=redacted)
        story_id = snap.rows[0].story_id
        detail = store.story(story_id, rights=redacted)
        feed = _changes(store, rights=redacted)
        scoped = _changes(store, rights=redacted, security_id="sec-NVDA")
        full = _snap(store)
        full_detail = store.story(story_id, rights=_rights())
        full_feed = _changes(store)

    assert len(snap.rows) == 1
    assert snap.rows[0].title == title
    assert snap.rows[0].url == ""
    assert snap.rows[0].teaser == ""
    assert detail is not None
    assert len(detail.members) == 1
    assert detail.members[0].title == title
    assert detail.members[0].url == ""
    assert detail.members[0].teaser == ""
    assert len(feed.rows) == 1
    assert feed.rows[0].kind == "upsert"
    assert feed.rows[0].title == title
    assert feed.rows[0].url == ""
    assert feed.rows[0].teaser == ""
    assert scoped.rows[0].url == ""
    assert scoped.rows[0].teaser == ""
    assert scoped.rows[0].title == title
    for row in (snap.rows[0], detail.members[0], feed.rows[0], scoped.rows[0]):
        assert teaser not in (row.url, row.teaser, row.title)
        assert url not in (row.url, row.teaser)

    assert full.rows[0].url == url
    assert full.rows[0].teaser == teaser
    assert full_detail.members[0].url == url
    assert full_detail.members[0].teaser == teaser
    assert full_feed.rows[0].url == url
    assert full_feed.rows[0].teaser == teaser
