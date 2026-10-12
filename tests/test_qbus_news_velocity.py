"""Descriptive news-flow counts. Hermetic: fixtures only, no network."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import re
import sqlite3
from pathlib import Path

import pytest

from engine.qbus_news_velocity import METHOD, SCHEMA, compute_news_velocity


UTC = timezone.utc
NOW = datetime(2026, 10, 11, 15, 0, tzinfo=UTC)
EDT = timezone(timedelta(hours=-4))

# Words that must not appear in either label. Whole words, case-insensitive.
BANNED_WORDS = (
    "unusual",
    "spike",
    "alert",
    "score",
    "signal",
    "validated",
    "rank",
    "ranking",
    "confidence",
    "sentiment",
    "buy",
    "sell",
)

_OUTPUT_KEYS = {
    "schema",
    "security_id",
    "as_of",
    "count_24h",
    "count_7d",
    "daily_counts_28d",
    "median_daily_28d",
    "history_days_observed",
    "sufficient_history",
    "basis_counts",
    "method",
    "label",
}


def _new_db(tmp_path: Path) -> Path:
    from engine.qbus_news_store import NewsStore

    db = tmp_path / "news.sqlite3"
    with NewsStore(db, source_key="benzinga-live"):
        pass
    _checkpoint(db)
    return db


def _checkpoint(db: Path) -> None:
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _writer(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _insert(
    conn: sqlite3.Connection,
    *,
    security_id: str,
    item_id: str,
    published: datetime | None,
    received: datetime,
    status: str = "active",
    source: str = "benzinga",
) -> None:
    source_item_id = str(item_id)
    revision_id = f"rev-{source}-{source_item_id}-{status}"
    published_text = None if published is None else published.astimezone(UTC).isoformat()
    received_text = received.astimezone(UTC).isoformat()
    conn.execute(
        """
        INSERT INTO news_revisions(
            revision_id, source, source_item_id, identity_json, revision_json
        ) VALUES(?,?,?,?,?)
        """,
        (revision_id, source, source_item_id, "{}", "{}"),
    )
    conn.execute(
        """
        INSERT INTO news_states(
            source, source_item_id, current_revision_id, status,
            state_json, last_sequence, universe_revision
        ) VALUES(?,?,?,?,?,?,?)
        """,
        (source, source_item_id, revision_id, status, "{}", 1, "u1"),
    )
    conn.execute(
        """
        INSERT INTO news_state_projection(
            source, source_item_id, title, url, teaser,
            published_at, updated_at, received_at
        ) VALUES(?,?,?,?,?,?,?,?)
        """,
        (
            source,
            source_item_id,
            f"title {source_item_id}",
            f"https://example.invalid/{source_item_id}",
            "",
            published_text,
            published_text,
            received_text,
        ),
    )
    conn.execute(
        """
        INSERT INTO news_security_index(security_id, source, source_item_id)
        VALUES(?,?,?)
        """,
        (security_id, source, source_item_id),
    )


def _close_writer(conn: sqlite3.Connection, db: Path) -> None:
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    _checkpoint(db)


def _velocity(db: Path, security_id: str, now: datetime = NOW) -> dict:
    _checkpoint(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        return compute_news_velocity(conn, security_id=security_id, now=now)
    finally:
        conn.close()


def _assert_banned_absent(text: str) -> None:
    lowered = text.casefold()
    for word in BANNED_WORDS:
        match = re.search(rf"\b{re.escape(word)}\b", lowered)
        assert match is None, word


def _rest_payload(*, item_id: int, published: datetime, title: str) -> dict:
    updated = published + timedelta(seconds=1)
    stamp = published.astimezone(UTC).isoformat().replace("+00:00", "Z")
    updated_stamp = updated.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return {
        "id": item_id,
        "created": stamp,
        "updated": updated_stamp,
        "title": title,
        "teaser": "A short teaser",
        "body": "Full article content",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": [{"name": "News"}],
        "stocks": [{"name": "NVDA"}],
        "tags": [{"name": "breaking"}],
    }


def _massive_payload(*, item_id: int, published: datetime, title: str) -> dict:
    updated = published + timedelta(seconds=1)
    stamp = published.astimezone(UTC).isoformat().replace("+00:00", "Z")
    updated_stamp = updated.astimezone(UTC).isoformat().replace("+00:00", "Z")
    return {
        "benzinga_id": item_id,
        "published": stamp,
        "last_updated": updated_stamp,
        "title": title,
        "teaser": "A short teaser",
        "body": "Full article content",
        "url": f"https://www.benzinga.com/news/{item_id}",
        "channels": ["News"],
        "tickers": ["NVDA"],
        "tags": ["breaking"],
    }


def test_empty_security_has_zero_counts(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    other_at = NOW - timedelta(hours=1)
    _insert(
        conn,
        security_id="sec-OTHER",
        item_id="other-1",
        published=other_at,
        received=other_at,
    )
    _close_writer(conn, db)

    result = _velocity(db, "sec-EMPTY")

    assert set(result) == _OUTPUT_KEYS
    assert result["schema"] == SCHEMA
    assert result["security_id"] == "sec-EMPTY"
    assert result["as_of"] == "2026-10-11T15:00:00+00:00"
    assert result["count_24h"] == 0
    assert result["count_7d"] == 0
    assert result["daily_counts_28d"] == [0] * 28
    assert result["median_daily_28d"] is None
    assert result["history_days_observed"] == 0
    assert result["sufficient_history"] is False
    assert result["basis_counts"] == {"published_at": 0, "received_at": 0}
    assert result["method"] == METHOD
    assert result["label"] == {
        "en": "0 stories in 24h; not enough history yet",
        "zh": "24小时内0篇报道；历史数据不足",
    }


def test_withdrawn_story_is_excluded(tmp_path):
    """A withdrawn story still sitting in the security index is not counted.

    The store itself deletes the index row on withdrawal. This fixture puts
    the row back so the status filter is what keeps the count at the live story.
    """
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore, RoutedRevision

    db = tmp_path / "news.sqlite3"
    published = NOW - timedelta(hours=2)
    withdrawn_at = NOW - timedelta(hours=1)
    live = RoutedRevision(
        revision=normalize_news(
            _rest_payload(item_id=1, published=published, title="Live story"),
            transport="benzinga_rest",
            received_at=published,
        ),
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )
    doomed = RoutedRevision(
        revision=normalize_news(
            _rest_payload(item_id=2, published=published, title="Pulled story"),
            transport="benzinga_rest",
            received_at=published,
        ),
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )
    removal_payload = {
        "id": "msg-delete-2",
        "api_version": "websocket/v1",
        "kind": "news",
        "data": {
            "action": "Deleted",
            "id": 2,
            "timestamp": withdrawn_at.isoformat().replace("+00:00", "Z"),
        },
    }
    removal = RoutedRevision(
        revision=normalize_news(
            removal_payload,
            transport="benzinga_ws",
            received_at=withdrawn_at,
        ),
        security_ids=(),
        universe_revision="sp500-r1",
    )
    with NewsStore(db, source_key="benzinga-live") as store:
        store.commit([live, doomed], expected_cursor=None, next_cursor="c1")
        receipt = store.commit([removal], expected_cursor="c1", next_cursor="c2")
        assert receipt.withdrawn_states == 1

    conn = _writer(db)
    conn.execute(
        """
        INSERT INTO news_security_index(security_id, source, source_item_id)
        VALUES(?,?,?)
        """,
        ("sec-NVDA", "benzinga", "2"),
    )
    status, published_at, received_at = conn.execute(
        """
        SELECT s.status, p.published_at, p.received_at
        FROM news_states AS s
        JOIN news_state_projection AS p
          ON p.source = s.source AND p.source_item_id = s.source_item_id
        WHERE s.source_item_id = '2'
        """
    ).fetchone()
    indexed = conn.execute(
        "SELECT COUNT(*) FROM news_security_index WHERE security_id = 'sec-NVDA'"
    ).fetchone()[0]
    _close_writer(conn, db)

    assert status == "withdrawn"
    assert published_at is None
    assert received_at is not None
    assert indexed == 2

    result = _velocity(db, "sec-NVDA")
    assert result["count_24h"] == 1
    assert result["count_7d"] == 1
    assert result["basis_counts"] == {"published_at": 1, "received_at": 0}


def test_syndicated_duplicate_is_counted_once(tmp_path):
    """Benzinga REST plus a Massive mirror of the same item is one story.

    A third, different item is present so collapsing everything to one story
    fails the assertion, and counting each revision (there are three) does too.
    """
    from engine.qbus_news_contract import normalize_news
    from engine.qbus_news_store import NewsStore, RoutedRevision

    db = tmp_path / "news.sqlite3"
    published = NOW - timedelta(hours=1)
    direct = RoutedRevision(
        revision=normalize_news(
            _rest_payload(item_id=42, published=published, title="Shared wire"),
            transport="benzinga_rest",
            received_at=published,
        ),
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )
    mirror = RoutedRevision(
        revision=normalize_news(
            _massive_payload(item_id=42, published=published, title="Shared wire"),
            transport="massive_benzinga_v2",
            received_at=published + timedelta(seconds=5),
        ),
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )
    other = RoutedRevision(
        revision=normalize_news(
            _rest_payload(item_id=43, published=published, title="Second story"),
            transport="benzinga_rest",
            received_at=published,
        ),
        security_ids=("sec-NVDA",),
        universe_revision="sp500-r1",
    )
    with NewsStore(db, source_key="benzinga-live") as store:
        store.commit([direct], expected_cursor=None, next_cursor="c1")
        mirrored = store.commit([mirror], expected_cursor="c1", next_cursor="c2")
        store.commit([other], expected_cursor="c2", next_cursor="c3")
        assert mirrored.duplicate_revisions == 1
        assert mirrored.applied_states == 0

    check = sqlite3.connect(db)
    revisions = check.execute("SELECT COUNT(*) FROM news_revisions").fetchone()[0]
    indexed = check.execute(
        "SELECT COUNT(*) FROM news_security_index WHERE security_id = 'sec-NVDA'"
    ).fetchone()[0]
    check.close()
    assert revisions == 3
    assert indexed == 2

    result = _velocity(db, "sec-NVDA")
    assert result["count_24h"] == 2
    assert result["count_7d"] == 2
    assert sum(result["basis_counts"].values()) == 2


def test_window_edges_24h_and_7d(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    fixtures = (
        ("at-now", NOW, True, True, None),
        ("at-24h", NOW - timedelta(hours=24), True, True, 27),
        ("before-24h", NOW - timedelta(hours=24, microseconds=1), False, True, 27),
        ("at-7d", NOW - timedelta(days=7), False, True, 21),
        ("before-7d", NOW - timedelta(days=7, microseconds=1), False, False, 21),
        ("after-now", NOW + timedelta(microseconds=1), False, False, None),
        ("oldest-bin", datetime(2026, 9, 13, 0, 0, tzinfo=UTC), False, False, 0),
        ("before-oldest", datetime(2026, 9, 12, 23, 59, 59, tzinfo=UTC), False, False, None),
    )
    expected_24h = 0
    expected_7d = 0
    expected_daily = [0] * 28
    for item_id, published, in_24h, in_7d, daily_index in fixtures:
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=item_id,
            published=published,
            received=published,
        )
        expected_24h += int(in_24h)
        expected_7d += int(in_7d)
        if daily_index is not None:
            expected_daily[daily_index] += 1
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["count_24h"] == expected_24h == 2
    assert result["count_7d"] == expected_7d == 4
    assert result["daily_counts_28d"] == expected_daily
    assert result["daily_counts_28d"][0] == 1
    assert result["daily_counts_28d"][21] == 2
    assert result["daily_counts_28d"][27] == 2
    assert sum(result["daily_counts_28d"]) == 5
    # First indexed story is 2026-09-12; the span is 29 UTC days, capped at 28.
    assert result["history_days_observed"] == 28
    assert result["sufficient_history"] is True
    assert result["median_daily_28d"] == 0.0
    assert result["basis_counts"] == {"published_at": 8, "received_at": 0}


def test_thin_history_says_not_enough(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    # 2026-09-22 is 19 UTC calendar days before 2026-10-11.
    first = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
    _insert(conn, security_id="sec-NVDA", item_id="recent", published=recent, received=recent)
    _insert(conn, security_id="sec-NVDA", item_id="first", published=first, received=first)
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["history_days_observed"] == 19
    assert result["sufficient_history"] is False
    assert result["median_daily_28d"] is None
    assert result["count_24h"] == 1
    assert result["count_7d"] == 1
    assert result["label"] == {
        "en": "1 story in 24h; not enough history yet",
        "zh": "24小时内1篇报道；历史数据不足",
    }
    assert "not enough history yet" in result["label"]["en"]
    assert "历史数据不足" in result["label"]["zh"]


def test_twenty_days_of_history_is_sufficient(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    # 2026-09-21 is 20 UTC calendar days before 2026-10-11.
    first = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
    _insert(conn, security_id="sec-NVDA", item_id="first", published=first, received=first)
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["history_days_observed"] == 20
    assert result["sufficient_history"] is True
    assert result["median_daily_28d"] == 0.0
    assert result["count_24h"] == 0
    assert result["label"] == {
        "en": "0 stories in 24h; typical day ~0 (28-day median)",
        "zh": "24小时内0篇报道；近28天中位数约每日0篇",
    }
    assert "not enough history yet" not in result["label"]["en"]
    assert "历史数据不足" not in result["label"]["zh"]


def test_published_at_null_falls_back_to_received_at(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    by_published = NOW - timedelta(hours=1)
    # Receipt is far outside the windows; only published_at places this story.
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="has-published",
        published=by_published,
        received=NOW - timedelta(days=40),
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="receipt-only",
        published=None,
        received=NOW - timedelta(hours=2),
    )
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["count_24h"] == 2
    assert result["count_7d"] == 2
    assert result["basis_counts"] == {"published_at": 1, "received_at": 1}
    assert result["sufficient_history"] is False


def test_same_db_and_now_are_byte_identical(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    published = NOW - timedelta(hours=3)
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="one",
        published=published,
        received=published,
    )
    _close_writer(conn, db)
    _checkpoint(db)

    same_instant = datetime(2026, 10, 11, 11, 0, tzinfo=EDT)
    uri = f"file:{db}?mode=ro"
    first = sqlite3.connect(uri, uri=True)
    second = sqlite3.connect(uri, uri=True)
    try:
        first.execute("PRAGMA query_only=ON")
        second.execute("PRAGMA query_only=ON")
        left = compute_news_velocity(first, security_id="sec-NVDA", now=NOW)
        again = compute_news_velocity(first, security_id="sec-NVDA", now=NOW)
        right = compute_news_velocity(second, security_id="sec-NVDA", now=same_instant)
    finally:
        first.close()
        second.close()

    left_bytes = json.dumps(left, sort_keys=True).encode("utf-8")
    again_bytes = json.dumps(again, sort_keys=True).encode("utf-8")
    right_bytes = json.dumps(right, sort_keys=True).encode("utf-8")
    assert left_bytes == again_bytes == right_bytes
    assert left["as_of"] == "2026-10-11T15:00:00+00:00"


def test_labels_are_bilingual_and_avoid_banned_words(tmp_path):
    thin = _new_db(tmp_path / "thin")
    conn = _writer(thin)
    recent = NOW - timedelta(hours=1)
    first = datetime(2026, 9, 22, 12, 0, tzinfo=UTC)
    _insert(conn, security_id="sec-NVDA", item_id="recent", published=recent, received=recent)
    _insert(conn, security_id="sec-NVDA", item_id="first", published=first, received=first)
    _close_writer(conn, thin)
    thin_result = _velocity(thin, "sec-NVDA")

    full = _new_db(tmp_path / "full")
    conn = _writer(full)
    oldest = datetime(2026, 9, 13, 12, 0, tzinfo=UTC).date()
    for offset in range(28):
        day = oldest + timedelta(days=offset)
        published = datetime(day.year, day.month, day.day, 12, 0, tzinfo=UTC)
        for copy in range(3):
            _insert(
                conn,
                security_id="sec-NVDA",
                item_id=f"d{offset}-{copy}",
                published=published,
                received=published,
            )
    today = datetime(2026, 10, 11, 14, 0, tzinfo=UTC)
    for copy in range(12):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=f"today-{copy}",
            published=today,
            received=today,
        )
    _close_writer(conn, full)
    full_result = _velocity(full, "sec-NVDA")

    assert full_result["count_24h"] == 12
    assert full_result["count_7d"] == 30
    assert full_result["daily_counts_28d"] == [3] * 28
    assert full_result["median_daily_28d"] == 3.0
    assert full_result["sufficient_history"] is True
    assert full_result["label"] == {
        "en": "12 stories in 24h; typical day ~3 (28-day median)",
        "zh": "24小时内12篇报道；近28天中位数约每日3篇",
    }

    for result in (thin_result, full_result):
        label = result["label"]
        assert set(label) == {"en", "zh"}
        assert label["en"]
        assert label["zh"]
        assert label["en"] != label["zh"]
        _assert_banned_absent(label["en"])
        _assert_banned_absent(label["zh"])
        _assert_banned_absent(json.dumps(result, sort_keys=True))


def test_naive_now_is_rejected(tmp_path):
    db = _new_db(tmp_path)
    _checkpoint(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        with pytest.raises(ValueError):
            compute_news_velocity(
                conn,
                security_id="sec-NVDA",
                now=datetime(2026, 10, 11, 15, 0, 0),
            )
    finally:
        conn.close()
