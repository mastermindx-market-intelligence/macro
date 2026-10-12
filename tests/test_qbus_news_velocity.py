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
    "stories_24h",
    "cluster_policy_versions_24h",
    "daily_counts_28d",
    "median_daily_28d",
    "history_days_observed",
    "sufficient_history",
    "basis_counts",
    "basis_counts_24h",
    "sources_counted",
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


def _cluster(
    conn: sqlite3.Connection,
    cluster_id: str,
    members: tuple[tuple[str, str], ...],
) -> None:
    """One news_clusters row plus one member row per (source, source_item_id)."""
    conn.execute(
        """
        INSERT INTO news_clusters(
            cluster_id, anchor_story_id, anchor_title,
            anchor_observed_at, subject_ids_json, event_family
        ) VALUES(?,?,?,?,?,?)
        """,
        (
            cluster_id,
            f"{cluster_id}:anchor",
            f"title {cluster_id}",
            "2026-10-11T00:00:00+00:00",
            "[]",
            "news",
        ),
    )
    for source, source_item_id in members:
        conn.execute(
            """
            INSERT INTO news_cluster_members(
                source, source_item_id, cluster_id, story_id
            ) VALUES(?,?,?,?)
            """,
            (source, source_item_id, cluster_id, cluster_id),
        )


def _velocity(
    db: Path,
    security_id: str,
    now: datetime = NOW,
    allowed_sources: tuple[str, ...] | frozenset[str] | set[str] = ("benzinga",),
) -> dict:
    _checkpoint(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        return compute_news_velocity(
            conn,
            security_id=security_id,
            now=now,
            allowed_sources=allowed_sources,
        )
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
        "en": "0 reports in 24h; not enough history yet",
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
        "en": "1 report in 24h; not enough history yet",
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
        "en": "0 reports in 24h; typical day ~0 (28-day median)",
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
        left = compute_news_velocity(
            first, security_id="sec-NVDA", now=NOW, allowed_sources=("benzinga",)
        )
        again = compute_news_velocity(
            first, security_id="sec-NVDA", now=NOW, allowed_sources=("benzinga",)
        )
        right = compute_news_velocity(
            second,
            security_id="sec-NVDA",
            now=same_instant,
            allowed_sources=("benzinga",),
        )
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
        "en": "12 reports in 24h; typical day ~3 (28-day median)",
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
                allowed_sources=("benzinga",),
            )
    finally:
        conn.close()


# --- Wave B1: rights-gated flow counts, stories vs reports, compare_to_typical ---

# Spec 3.5 banned vocabulary for the flow surfaces. The legacy BANNED_WORDS
# above stays as it is; these lists additionally cover the flow-rail copy.
# EN words are checked as whole words, ZH terms as substrings.
# Verbatim from WAVE_B_NEWS_FLOW_RAIL_SPEC_2026-10-12.md section 3.5 (EN 23, ZH 22); do not edit one list without the spec.
SPEC_BANNED_WORDS_EN = (
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
    "bullish",
    "bearish",
    "positive",
    "negative",
    "beat",
    "miss",
    "upgrade",
    "downgrade",
    "hot",
    "momentum",
    "impact",
)
SPEC_BANNED_WORDS_ZH = (
    "异常",
    "激增",
    "飙升",
    "警报",
    "预警",
    "评分",
    "分数",
    "信号",
    "验证",
    "排名",
    "置信",
    "情绪",
    "买",
    "卖",
    "利好",
    "利空",
    "看涨",
    "看跌",
    "超预期",
    "不及预期",
    "热度",
    "影响",
)

_ZERO_RESULT = {
    "count_24h": 0,
    "count_7d": 0,
    "daily_counts_28d": [0] * 28,
    "median_daily_28d": None,
    "history_days_observed": 0,
    "sufficient_history": False,
    "basis_counts": {"published_at": 0, "received_at": 0},
    "stories_24h": 0,
    "basis_counts_24h": {"published_at": 0, "received_at": 0},
    "sources_counted": [],
}


def test_flow_counts_only_allowed_sources(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    _insert(
        conn, security_id="sec-NVDA", item_id="b1", published=recent, received=recent
    )
    _insert(
        conn, security_id="sec-NVDA", item_id="b2", published=recent, received=recent
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="w1",
        published=recent,
        received=recent,
        source="restricted_wire",
    )
    _close_writer(conn, db)

    only_benzinga = _velocity(db, "sec-NVDA", allowed_sources=("benzinga",))
    assert only_benzinga["count_24h"] == 2
    assert only_benzinga["count_7d"] == 2
    assert only_benzinga["sources_counted"] == ["benzinga"]

    both = _velocity(
        db, "sec-NVDA", allowed_sources={"benzinga", "restricted_wire"}
    )
    assert both["count_24h"] == 3
    assert both["count_7d"] == 3
    assert both["sources_counted"] == ["benzinga", "restricted_wire"]

    as_tuple = _velocity(
        db, "sec-NVDA", allowed_sources=("benzinga", "restricted_wire")
    )
    as_list = _velocity(
        db, "sec-NVDA", allowed_sources=["benzinga", "restricted_wire"]
    )
    as_frozenset = _velocity(
        db, "sec-NVDA", allowed_sources=frozenset({"benzinga", "restricted_wire"})
    )
    assert as_tuple == both
    assert as_list == both
    assert as_frozenset == both

    _checkpoint(db)
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        with pytest.raises(TypeError) as excinfo:
            compute_news_velocity(
                conn,
                security_id="sec-NVDA",
                now=NOW,
                allowed_sources="benzinga",
            )
    finally:
        conn.close()
    assert str(excinfo.value) == (
        "allowed_sources must be a collection of source ids, not a str"
    )


def test_flow_counts_only_active_status(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="live",
        published=recent,
        received=recent,
        status="active",
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="gone",
        published=recent,
        received=recent,
        status="withdrawn",
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="held",
        published=recent,
        received=recent,
        # An unknown future status value must fail closed like withdrawn.
        status="quarantined",
    )
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["count_24h"] == 1
    assert result["count_7d"] == 1


def test_flow_empty_allowed_sources_counts_zero(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    for copy in range(3):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=f"r{copy}",
            published=recent,
            received=recent,
        )
    _close_writer(conn, db)
    _checkpoint(db)

    for empty in ((), frozenset()):
        statements: list[str] = []
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            conn.set_trace_callback(statements.append)
            result = compute_news_velocity(
                conn, security_id="sec-NVDA", now=NOW, allowed_sources=empty
            )
        finally:
            conn.close()
        for key, value in _ZERO_RESULT.items():
            assert result[key] == value, key
        assert statements == []


def test_allowed_sources_is_required_keyword():
    import inspect

    parameter = inspect.signature(compute_news_velocity).parameters[
        "allowed_sources"
    ]
    assert parameter.kind is inspect.Parameter.KEYWORD_ONLY
    assert parameter.default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        compute_news_velocity(conn=None, security_id="sec-NVDA", now=NOW)


def test_stories_24h_counts_distinct_clusters(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    old = NOW - timedelta(days=3)
    for item_id in ("a1", "a2", "a3"):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=item_id,
            published=recent,
            received=recent,
        )
    _insert(
        conn, security_id="sec-NVDA", item_id="a0", published=old, received=old
    )
    _cluster(
        conn,
        "cl-A",
        (
            ("benzinga", "a1"),
            ("benzinga", "a2"),
            ("benzinga", "a3"),
            ("benzinga", "a0"),
        ),
    )
    for item_id in ("b1", "b2"):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=item_id,
            published=recent,
            received=recent,
        )
    _cluster(conn, "cl-B", (("benzinga", "b1"), ("benzinga", "b2")))
    _insert(
        conn, security_id="sec-NVDA", item_id="c1", published=old, received=old
    )
    _cluster(conn, "cl-C", (("benzinga", "c1"),))
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["count_24h"] == 5
    assert result["stories_24h"] == 2
    assert result["count_7d"] == 7


def test_unclustered_report_is_its_own_story(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    recent = NOW - timedelta(hours=1)
    for item_id in ("u1", "u2"):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=item_id,
            published=recent,
            received=recent,
        )
    for item_id in ("p1", "p2"):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=item_id,
            published=recent,
            received=recent,
        )
    _cluster(conn, "cl-P", (("benzinga", "p1"), ("benzinga", "p2")))
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["count_24h"] == 4
    assert result["stories_24h"] == 3

    conn = _writer(db)
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="shared",
        published=recent,
        received=recent,
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="shared",
        published=recent,
        received=recent,
        source="restricted_wire",
    )
    _close_writer(conn, db)

    both = _velocity(
        db, "sec-NVDA", allowed_sources={"benzinga", "restricted_wire"}
    )

    assert both["count_24h"] == 6
    assert both["stories_24h"] == 5


def test_basis_counts_24h_windowed(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    in_window = NOW - timedelta(hours=2)
    old = NOW - timedelta(days=3)
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="pub1",
        published=in_window,
        received=in_window,
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="pub2",
        published=in_window,
        received=in_window,
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="rec1",
        published=None,
        received=in_window,
    )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="oldrec",
        published=None,
        received=old,
    )
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["basis_counts_24h"] == {"published_at": 2, "received_at": 1}
    assert sum(result["basis_counts_24h"].values()) == result["count_24h"] == 3
    assert result["basis_counts"] == {"published_at": 2, "received_at": 2}


def test_compare_to_typical_bands():
    from engine.qbus_news_velocity import (
        BUSIER_MIN_EXCESS,
        BUSIER_MIN_RATIO,
        FLOW_COMPARE_RULE,
        QUIETER_MAX_FRACTION,
        QUIETER_MIN_MEDIAN,
        compare_to_typical,
    )

    assert FLOW_COMPARE_RULE == "flow_compare.v1"
    assert BUSIER_MIN_RATIO == 2
    assert BUSIER_MIN_EXCESS == 3
    assert QUIETER_MIN_MEDIAN == 2
    assert QUIETER_MAX_FRACTION == 0.5

    rows = [
        # r24, median, sufficient, coverage, expected
        (0, 0, True, "complete", "typical"),
        (2, 0, True, "complete", "typical"),
        (3, 0, True, "complete", "busier"),
        (2, 1, True, "complete", "typical"),
        (5, 3, True, "complete", "typical"),
        (6, 3, True, "complete", "busier"),
        (1, 2, True, "complete", "quieter"),
        (0, 2, True, "complete", "quieter"),
        (2, 3, True, "complete", "typical"),
        (1, 3, True, "complete", "quieter"),
        (0, 1.5, True, "complete", "typical"),
        (6, 2.5, True, "complete", "busier"),
        (5, 2.5, True, "complete", "typical"),
        (1, 2.5, True, "complete", "quieter"),
        (9, 3, True, "partial", None),
        (9, None, False, "complete", "insufficient_history"),
        (0, None, False, "partial", None),
    ]
    for r24, median, sufficient, coverage, expected in rows:
        assert (
            compare_to_typical(r24, median, sufficient, coverage) == expected
        ), (r24, median, sufficient, coverage)
        # Rule row 1 wins over everything: any row under partial coverage is None.
        assert compare_to_typical(r24, median, sufficient, "partial") is None

    assert (
        compare_to_typical(5, 3, False, "complete") == "insufficient_history"
    )
    assert (
        compare_to_typical(5, None, True, "complete") == "insufficient_history"
    )

    with pytest.raises(ValueError):
        compare_to_typical(5, 3, True, "full")
    for bad_r24 in (-1, True, 1.0):
        with pytest.raises(ValueError):
            compare_to_typical(bad_r24, 3, True, "complete")
    for bad_median in (-0.5, float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            compare_to_typical(5, bad_median, True, "complete")


def test_window_boundaries_closed_both_ends(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)
    edges = (
        ("at-24h", NOW - timedelta(hours=24)),
        ("at-now", NOW),
        ("just-before-24h", NOW - timedelta(hours=24, seconds=1)),
        ("at-7d", NOW - timedelta(days=7)),
        ("just-before-7d", NOW - timedelta(days=7, seconds=1)),
        ("after-now", NOW + timedelta(seconds=1)),
    )
    for item_id, published in edges:
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=item_id,
            published=published,
            received=published,
        )
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")

    assert result["count_24h"] == 2
    assert result["count_7d"] == 4


def test_daily_counts_oldest_first(tmp_path):
    db = _new_db(tmp_path)
    conn = _writer(db)

    def at(day_offset: int, hour: int = 6) -> datetime:
        day = NOW.date() - timedelta(days=day_offset)
        return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)

    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="oldest",
        published=at(28),
        received=at(28),
    )
    for copy in range(2):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=f"y{copy}",
            published=at(1),
            received=at(1),
        )
    for copy in range(3):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=f"t{copy}",
            published=at(0, hour=10),
            received=at(0, hour=10),
        )
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="ancient",
        published=at(29),
        received=at(29),
    )
    _close_writer(conn, db)

    result = _velocity(db, "sec-NVDA")
    daily = result["daily_counts_28d"]

    assert len(daily) == 28
    assert daily[0] == 1
    assert daily[27] == 2
    assert sum(daily) == 3


def test_label_unit_is_reports_en_zh(tmp_path):
    thin_one = _new_db(tmp_path / "thin-one")
    conn = _writer(thin_one)
    recent = NOW - timedelta(hours=1)
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="solo",
        published=recent,
        received=recent,
    )
    _close_writer(conn, thin_one)

    thin_several = _new_db(tmp_path / "thin-several")
    conn = _writer(thin_several)
    for copy in range(4):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=f"n{copy}",
            published=recent,
            received=recent,
        )
    _close_writer(conn, thin_several)

    sufficient = _new_db(tmp_path / "sufficient")
    conn = _writer(sufficient)
    first = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="first",
        published=first,
        received=first,
    )
    for copy in range(4):
        _insert(
            conn,
            security_id="sec-NVDA",
            item_id=f"n{copy}",
            published=recent,
            received=recent,
        )
    _close_writer(conn, sufficient)

    thin_one_result = _velocity(thin_one, "sec-NVDA")
    thin_several_result = _velocity(thin_several, "sec-NVDA")
    sufficient_result = _velocity(sufficient, "sec-NVDA")

    assert thin_one_result["sufficient_history"] is False
    assert thin_several_result["sufficient_history"] is False
    assert sufficient_result["sufficient_history"] is True

    assert "1 report" in thin_one_result["label"]["en"]
    assert "4 reports" in thin_several_result["label"]["en"]
    assert "4 reports" in sufficient_result["label"]["en"]
    for result in (thin_one_result, thin_several_result, sufficient_result):
        label = result["label"]
        assert re.search(r"\bstor(?:y|ies)\b", label["en"]) is None
        assert "篇报道" in label["zh"]


def test_banned_words_en_zh(tmp_path):
    empty = _new_db(tmp_path / "empty")
    empty_result = _velocity(empty, "sec-EMPTY")

    thin = _new_db(tmp_path / "thin")
    conn = _writer(thin)
    recent = NOW - timedelta(hours=1)
    _insert(
        conn,
        security_id="sec-NVDA",
        item_id="recent",
        published=recent,
        received=recent,
    )
    _close_writer(conn, thin)
    thin_result = _velocity(thin, "sec-NVDA")

    full = _new_db(tmp_path / "full")
    conn = _writer(full)
    oldest = datetime(2026, 9, 13, 12, 0, tzinfo=UTC)
    for offset in range(28):
        day = oldest.date() + timedelta(days=offset)
        when = datetime(day.year, day.month, day.day, 12, 0, tzinfo=UTC)
        for copy in range(3):
            _insert(
                conn,
                security_id="sec-NVDA",
                item_id=f"d{offset}-{copy}",
                published=when,
                received=when,
            )
    _close_writer(conn, full)
    full_result = _velocity(full, "sec-NVDA")

    for result in (empty_result, thin_result, full_result):
        label = result["label"]
        lowered = label["en"].casefold()
        for word in SPEC_BANNED_WORDS_EN:
            assert (
                re.search(rf"\b{re.escape(word)}\b", lowered) is None
            ), word
        for term in SPEC_BANNED_WORDS_ZH:
            assert term not in label["zh"], term

    method_lowered = METHOD.casefold()
    for word in SPEC_BANNED_WORDS_EN:
        assert (
            re.search(rf"\b{re.escape(word)}\b", method_lowered) is None
        ), word
