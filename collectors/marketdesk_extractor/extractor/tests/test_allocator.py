"""Unit tests for the pure allocator + the per-account rolling ledger.

Everything here runs against a temp sqlite DB seeded with papers at various
``published_at`` / ``downloaded_at`` / ``status`` / ``account`` values. NO
network, NO auth, NO Playwright — the whole download policy is exercised as pure
functions over a DB + an injected ``now``.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from marketdesk_extractor import allocator, db
from marketdesk_extractor.schemas import Status

NOW = datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)  # a Monday, 08:00 ET


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------
@pytest.fixture()
def conn(tmp_path: Path) -> sqlite3.Connection:
    c = db.connect(tmp_path / "alloc.sqlite")
    db.init_db(c)
    return c


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def _insert(
    conn: sqlite3.Connection,
    blob_id: str,
    *,
    published_at: datetime | None,
    status: Status = Status.DISCOVERED,
    downloaded_at: datetime | None = None,
    account: str | None = None,
    score: int | None = None,
) -> None:
    conn.execute(
        "INSERT INTO papers (blob_id, article_url, blob_url, title, published_at, "
        "status, downloaded_at, account, local_priority_score) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            blob_id,
            f"https://marketdesk.ai/library/browse?item={blob_id}",
            f"https://marketdesk.ai/files/{blob_id}/blob",
            f"title {blob_id}",
            _iso(published_at) if published_at else None,
            status.value,
            _iso(downloaded_at) if downloaded_at else None,
            account,
            score,
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# next_candidate — newest new first
# ---------------------------------------------------------------------------
def test_next_candidate_returns_newest_new_first(conn):
    _insert(conn, "old_new", published_at=NOW - timedelta(hours=10))
    _insert(conn, "newest_new", published_at=NOW - timedelta(hours=1))
    _insert(conn, "mid_new", published_at=NOW - timedelta(hours=5))
    got = allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    )
    assert got == "newest_new"


def test_next_candidate_prefers_new_over_backfill_even_when_backfill_allowed(conn):
    _insert(conn, "backfill_recent", published_at=NOW - timedelta(hours=60))
    _insert(conn, "new_paper", published_at=NOW - timedelta(hours=2))
    got = allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    )
    assert got == "new_paper"


def test_next_candidate_backfill_only_when_allowed(conn):
    # only backfill candidates exist (all older than the 48h new window)
    _insert(conn, "bf_older", published_at=NOW - timedelta(hours=200))
    _insert(conn, "bf_newer", published_at=NOW - timedelta(hours=60))

    # backfill disallowed -> None (we hold quota for expected new arrivals)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=False
    ) is None

    # backfill allowed -> newest-history first
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "bf_newer"


def test_failed_and_unsupported_are_not_candidates(conn):
    # A FAILED paper must NOT be re-selected: next_candidate is deterministic, so
    # re-picking a just-failed paper tight-loops and burns quota (a non-PDF ZIP
    # was observed retried 7x/tick). SKIPPED_UNSUPPORTED is likewise terminal.
    # Both are NEWER than the good row, yet the good DISCOVERED row must win.
    _insert(conn, "failed_newest", published_at=NOW - timedelta(hours=1),
            status=Status.FAILED)
    _insert(conn, "unsupported_2nd", published_at=NOW - timedelta(hours=2),
            status=Status.SKIPPED_UNSUPPORTED)
    _insert(conn, "good_new", published_at=NOW - timedelta(hours=3),
            status=Status.DISCOVERED)
    got = allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    )
    assert got == "good_new"


def test_next_candidate_none_when_nothing_eligible(conn):
    # a paper already past download is not a candidate
    _insert(conn, "done", published_at=NOW - timedelta(hours=1),
            status=Status.COMPLETE, downloaded_at=NOW, account="a")
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) is None


def test_next_candidate_includes_blob_found_excludes_failed(conn):
    # BLOB_FOUND is a live candidate (mid-pipeline, not yet downloaded).
    _insert(conn, "blob_found_new", published_at=NOW - timedelta(hours=3),
            status=Status.BLOB_FOUND)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=False
    ) == "blob_found_new"
    # FAILED is NOT a live candidate even though it is NEWER — re-selecting a
    # just-failed paper would tight-loop and burn quota; FAILED is retried only
    # via the loop-start reset.
    _insert(conn, "failed_newer", published_at=NOW - timedelta(hours=1),
            status=Status.FAILED)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=False
    ) == "blob_found_new"


def test_next_candidate_null_published_is_backfill_sorted_last(conn):
    _insert(conn, "null_pub", published_at=None)
    _insert(conn, "dated_backfill", published_at=NOW - timedelta(hours=100))
    # both are backfill; dated one sorts before the NULL one
    got = allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    )
    assert got == "dated_backfill"


# ---------------------------------------------------------------------------
# next_candidate — VALUE-first WITHIN a tier (local_priority_score)
# ---------------------------------------------------------------------------
def test_new_window_drains_highest_score_first(conn):
    """The defect this fixes: a zero-value paper posted minutes ago used to
    outrank a Goldman initiation from an hour ago, every single day."""
    _insert(conn, "junk_freshest", published_at=NOW - timedelta(minutes=5), score=0)
    _insert(conn, "goldman_initiation", published_at=NOW - timedelta(hours=1), score=88)
    _insert(conn, "mid", published_at=NOW - timedelta(minutes=30), score=40)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "goldman_initiation"


def test_equal_scores_fall_back_to_recency(conn):
    _insert(conn, "older_same_score", published_at=NOW - timedelta(hours=6), score=55)
    _insert(conn, "newer_same_score", published_at=NOW - timedelta(hours=2), score=55)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "newer_same_score"


def test_null_score_is_treated_as_zero(conn):
    # a NULL-scored paper must sort below ANY positive score (COALESCE -> 0), but
    # still above a genuinely 0-scored older paper on the recency tiebreak.
    _insert(conn, "unscored_newest", published_at=NOW - timedelta(minutes=10),
            score=None)
    _insert(conn, "scored_older", published_at=NOW - timedelta(hours=4), score=12)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "scored_older"

    _insert(conn, "zero_oldest", published_at=NOW - timedelta(hours=20), score=0)
    conn.execute("DELETE FROM papers WHERE blob_id='scored_older'")
    conn.commit()
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "unscored_newest"


def test_new_tier_beats_higher_scored_backfill(conn):
    """The tier split is NOT score-aware: fresh research always drains first,
    because that is exactly what the backfill reserve is protecting."""
    _insert(conn, "backfill_gold", published_at=NOW - timedelta(hours=60), score=99)
    _insert(conn, "new_junk", published_at=NOW - timedelta(hours=2), score=0)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "new_junk"


def test_backfill_tier_is_also_score_first(conn):
    _insert(conn, "bf_newest_junk", published_at=NOW - timedelta(hours=50), score=1)
    _insert(conn, "bf_older_valuable", published_at=NOW - timedelta(hours=200), score=77)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "bf_older_valuable"


def test_backfill_null_published_sorts_last_even_with_a_high_score(conn):
    """``(published_at IS NULL)`` is the FIRST backfill sort key, so an undated row
    never jumps the queue on score alone — its age is unknown, not zero."""
    _insert(conn, "undated_gold", published_at=None, score=99)
    _insert(conn, "dated_junk", published_at=NOW - timedelta(hours=100), score=1)
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "dated_junk"
    # ...but it is still reachable once the dated rows are gone
    conn.execute("DELETE FROM papers WHERE blob_id='dated_junk'")
    conn.commit()
    assert allocator.next_candidate(
        conn, NOW, new_window_hours=48, allow_backfill=True
    ) == "undated_gold"


def test_queue_depths_split_new_vs_backfill(conn):
    _insert(conn, "n1", published_at=NOW - timedelta(hours=1))
    _insert(conn, "n2", published_at=NOW - timedelta(hours=47))
    _insert(conn, "b1", published_at=NOW - timedelta(hours=49))
    _insert(conn, "b2", published_at=None)  # NULL -> backfill
    # a downloaded paper is NOT pending
    _insert(conn, "done", published_at=NOW, status=Status.COMPLETE,
            downloaded_at=NOW, account="a")
    new_n, back_n = allocator.queue_depths(conn, NOW, new_window_hours=48)
    assert new_n == 2
    assert back_n == 2


# ---------------------------------------------------------------------------
# trailing_24h_count / available_quota — per account, across the boundary
# ---------------------------------------------------------------------------
def test_trailing_24h_count_respects_boundary_and_account(conn):
    # account "a": one 1h ago (in), one 25h ago (out)
    _insert(conn, "a_in", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE, downloaded_at=NOW - timedelta(hours=1), account="a")
    _insert(conn, "a_out", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE, downloaded_at=NOW - timedelta(hours=25), account="a")
    # account "b": two in-window
    _insert(conn, "b_in1", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE, downloaded_at=NOW - timedelta(hours=2), account="b")
    _insert(conn, "b_in2", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE, downloaded_at=NOW - timedelta(hours=23), account="b")

    assert db.trailing_24h_count(conn, "a", NOW) == 1
    assert db.trailing_24h_count(conn, "b", NOW) == 2
    assert db.trailing_24h_count(conn, "c", NOW) == 0


def test_trailing_24h_boundary_is_exact(conn):
    # exactly 24h ago is OUT (cutoff is now-24h; >= cutoff means strictly younger
    # than 24h counts — a download exactly 24h old is at the boundary and, being
    # equal to the cutoff, still counts; one microsecond older does not).
    _insert(conn, "edge_in", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE,
            downloaded_at=NOW - timedelta(hours=24), account="a")
    _insert(conn, "edge_out", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE,
            downloaded_at=NOW - timedelta(hours=24, microseconds=1), account="a")
    assert db.trailing_24h_count(conn, "a", NOW) == 1


def test_available_quota(conn):
    for i in range(3):
        _insert(conn, f"a{i}", published_at=NOW - timedelta(days=5),
                status=Status.COMPLETE,
                downloaded_at=NOW - timedelta(hours=i + 1), account="a")
    assert db.available_quota(conn, "a", cap=70, now=NOW) == 67
    assert db.available_quota(conn, "a", cap=2, now=NOW) == 0  # never negative


def test_next_free_at_is_oldest_plus_window(conn):
    oldest = NOW - timedelta(hours=20)
    _insert(conn, "old", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE, downloaded_at=oldest, account="a")
    _insert(conn, "recent", published_at=NOW - timedelta(days=5),
            status=Status.COMPLETE, downloaded_at=NOW - timedelta(hours=1), account="a")
    free = db.next_free_at(conn, "a", NOW)
    assert free is not None
    # oldest in-window download ages out 24h after it happened
    assert abs((free - (oldest + timedelta(hours=24))).total_seconds()) < 1
    # a fresh/empty account has nothing to wait on
    assert db.next_free_at(conn, "empty", NOW) is None


# ---------------------------------------------------------------------------
# expected_new_next_hours — weekday vs weekend, boundaries
# ---------------------------------------------------------------------------
def test_expected_new_weekday_whole_hours():
    # Monday 00:00 ET == 04:00 UTC; sum weekday hrs 0..3 = 7.5+1.5+0.2+0.3 = 9.5
    mon_mid = datetime(2026, 7, 27, 4, 0, 0, tzinfo=timezone.utc)
    assert allocator.expected_new_next_hours(mon_mid, 4) == pytest.approx(9.5)


def test_expected_new_weekday_peak():
    # Monday 06:00 ET == 10:00 UTC; hrs 6,7,8 = 20.6+34.2+14.5 = 69.3
    mon_peak = datetime(2026, 7, 27, 10, 0, 0, tzinfo=timezone.utc)
    assert allocator.expected_new_next_hours(mon_peak, 3) == pytest.approx(69.3)


def test_expected_new_weekend_lower_than_weekday():
    # Saturday 00:00 ET == 04:00 UTC; weekend hrs 0..3 = 5.9+0.1+0.0+1.5 = 7.5
    sat_mid = datetime(2026, 7, 25, 4, 0, 0, tzinfo=timezone.utc)
    assert allocator.expected_new_next_hours(sat_mid, 4) == pytest.approx(7.5)
    # and the same wall-clock window is quieter on the weekend than the weekday
    mon_mid = datetime(2026, 7, 27, 4, 0, 0, tzinfo=timezone.utc)
    assert (allocator.expected_new_next_hours(sat_mid, 9)
            < allocator.expected_new_next_hours(mon_mid, 9))


def test_expected_new_fractional_hour():
    # 06:00 ET, half of hour 6 (20.6) -> 10.3
    mon_peak = datetime(2026, 7, 27, 10, 0, 0, tzinfo=timezone.utc)
    assert allocator.expected_new_next_hours(mon_peak, 0.5) == pytest.approx(10.3)


def test_expected_new_crosses_weekend_boundary():
    # Sunday 23:00 ET (weekend, hr23=3.3) -> Monday 00:00 ET (weekday, hr0=7.5)
    # 2026-07-26 is Sunday; 23:00 ET == 2026-07-27 03:00 UTC. 2h => 3.3 + 7.5 = 10.8
    sun_23 = datetime(2026, 7, 27, 3, 0, 0, tzinfo=timezone.utc)
    assert allocator.expected_new_next_hours(sun_23, 2.0) == pytest.approx(10.8)


def test_expected_new_zero_hours():
    assert allocator.expected_new_next_hours(NOW, 0) == 0.0
    assert allocator.expected_new_next_hours(NOW, -3) == 0.0


def test_expected_new_profile_is_overridable():
    flat = allocator.HourlyProfile(
        weekday={h: 1.0 for h in range(24)}, weekend={h: 1.0 for h in range(24)}
    )
    # a flat 1/hr profile integrates to exactly the window length
    assert allocator.expected_new_next_hours(NOW, 5, flat) == pytest.approx(5.0)
    assert allocator.expected_new_next_hours(NOW, 2.5, flat) == pytest.approx(2.5)
