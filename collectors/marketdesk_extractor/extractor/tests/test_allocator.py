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


def test_post_dst_fall_back_uses_real_eastern_hour_and_weekday():
    # 2026-11-07T04:30Z is Friday 23:30 EST, not Saturday 00:30 EDT.
    # Misclassifying it as the weekend reserves 4.55 rather than 11.60
    # prospective new posts over the next four hours.
    stamp = datetime(2026, 11, 7, 4, 30, tzinfo=timezone.utc)
    assert allocator._to_et(stamp) == datetime(2026, 11, 6, 23, 30)
    assert allocator.expected_new_next_hours(stamp, 4) == pytest.approx(11.60)


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


# ---------------------------------------------------------------------------
# Bounded, evidence-driven backfill admission
# ---------------------------------------------------------------------------
# Measured on M1 at 2026-10-22T07:16:48Z from the real installed code and DB:
# cap=70/24h, BACKFILL_RESERVE_HOURS=24, NEW_WINDOW_HOURS=48, 0 known-new
# pending, 7,386 backfill pending. The old gate was one comparison —
# ``allow_backfill = quota > reserve`` — with ``reserve`` the RAW demand
# forecast. At those settings the forecast is 206.5 papers against a 70-pull
# allowance, so the condition was UNREACHABLE for all time and the backlog
# stalled permanently, with nothing in the logs saying so. These tests pin the
# repaired gate's three bounds and, more importantly, its refusals: backfill
# stays off unless an operator grants a budget, discovery evidence must be real
# and recent, and the reservation must be holdable.
M1_NOW = datetime(2026, 10, 22, 7, 16, 48, tzinfo=timezone.utc)  # Thursday 03:16 ET
M1_CAP = 70
M1_FORECAST_24H = 206.5   # measured from expected_new_next_hours(), not hand-written


def _health(state, *, age_h: float = 0.0, observed_at: str | None = None, **extra):
    """A discovery-health record shaped like ``db.discovery_health``'s return."""
    record = {
        "state": state,
        "observed_at": observed_at
        if observed_at is not None
        else _iso(M1_NOW - timedelta(hours=age_h)),
    }
    record.update(extra)
    return record


def _healthy(age_h: float = 0.5):
    return _health(db.DISCOVERY_HEALTHY, age_h=age_h)


def _decide(conn, **over):
    """``decide_backfill`` with the M1 production settings as the baseline."""
    kwargs = dict(
        account="acct",
        quota=M1_CAP,
        cap=M1_CAP,
        new_window_hours=48,
        backfill_reserve_hours=24,
        reserve_feasible_ratio=0.5,
        backfill_budget=0,
        discovery=_healthy(),
    )
    kwargs.update(over)
    return allocator.decide_backfill(conn, M1_NOW, **kwargs)


# --- 1. the defect's precondition, and the feasible-reserve repair ---------
def test_raw_forecast_exceeds_the_whole_allowance_at_m1_settings():
    """Pin WHY the old gate was unreachable, from the real measured numbers."""
    forecast = allocator.expected_new_next_hours(M1_NOW, 24)
    assert forecast == pytest.approx(M1_FORECAST_24H, abs=0.05)
    assert forecast > M1_CAP
    # The old comparison, reproduced verbatim: 70 > 206.5 is False, forever.
    assert not (M1_CAP > forecast)


def test_effective_reserve_clamps_the_forecast_to_what_can_be_withheld():
    forecast, reserve = allocator.effective_reserve(
        M1_NOW, 24, cap=M1_CAP, feasible_ratio=0.5
    )
    # The forecast is REPORTED, not erased — the clamp must stay auditable.
    assert forecast == pytest.approx(M1_FORECAST_24H, abs=0.05)
    assert reserve == pytest.approx(M1_CAP * 0.5)
    # The point of the repair: the reservation is now holdable, so the gate fires.
    assert M1_CAP > reserve


def test_effective_reserve_passes_a_small_forecast_through_untouched():
    forecast, reserve = allocator.effective_reserve(
        M1_NOW, 0.25, cap=M1_CAP, feasible_ratio=0.5
    )
    assert reserve == pytest.approx(forecast)
    assert reserve < M1_CAP * 0.5


@pytest.mark.parametrize("ratio", [0.0, 0.25, 0.5, 1.0, 5.0, 100.0])
def test_reserve_ceiling_never_exceeds_the_provider_cap(ratio):
    """Even a badly mis-set ratio cannot reserve more than the whole allowance."""
    _, reserve = allocator.effective_reserve(M1_NOW, 24, cap=M1_CAP, feasible_ratio=ratio)
    assert 0.0 <= reserve <= M1_CAP


# --- 2. the discovery-evidence gate fails closed ---------------------------
@pytest.mark.parametrize(
    "health, expected",
    [
        (None, "DISCOVERY_UNKNOWN"),
        ({}, "DISCOVERY_UNKNOWN"),
        (_health(db.DISCOVERY_UNKNOWN), "DISCOVERY_UNKNOWN"),
        (_health(db.DISCOVERY_FAILED), "DISCOVERY_FAILED"),
        (_health(db.DISCOVERY_FAILED, age_h=100.0), "DISCOVERY_FAILED"),
        (_health(db.DISCOVERY_HEALTHY, age_h=99.0), "DISCOVERY_STALE"),
        (_health(db.DISCOVERY_HEALTHY, observed_at="not-a-timestamp"), "DISCOVERY_UNSTAMPED"),
        (_health(db.DISCOVERY_HEALTHY, observed_at=""), "DISCOVERY_UNSTAMPED"),
    ],
)
def test_discovery_gate_refuses_anything_not_recent_and_healthy(health, expected):
    ok, why = allocator.discovery_is_current(health, M1_NOW, max_age_hours=6.0)
    assert ok is False
    assert why == expected


def test_discovery_gate_admits_a_recent_healthy_pass():
    ok, why = allocator.discovery_is_current(_healthy(age_h=1.0), M1_NOW, max_age_hours=6.0)
    assert (ok, why) == (True, "OK")


def test_a_future_discovery_stamp_cannot_grant_indefinite_freshness():
    """Clock skew must fail closed, not hand out a free pass."""
    health = _health(db.DISCOVERY_HEALTHY, observed_at=_iso(M1_NOW + timedelta(days=7)))
    ok, why = allocator.discovery_is_current(health, M1_NOW, max_age_hours=6.0)
    assert (ok, why) == (False, "DISCOVERY_FUTURE")


@pytest.mark.parametrize("max_age", [float("nan"), float("inf"), -1.0, 0.0, True])
def test_invalid_discovery_age_limit_refuses_backfill(max_age):
    ok, why = allocator.discovery_is_current(
        _healthy(age_h=1.0), M1_NOW, max_age_hours=max_age
    )
    assert (ok, why) == (False, "DISCOVERY_CONFIG_INVALID")


def test_discovery_future_timestamp_refused_beyond_clock_skew():
    too_future = _health(
        db.DISCOVERY_HEALTHY,
        observed_at=_iso(M1_NOW + timedelta(hours=1)),
    )
    near_future = _health(
        db.DISCOVERY_HEALTHY,
        observed_at=_iso(M1_NOW + timedelta(minutes=3)),
    )
    assert allocator.discovery_is_current(
        too_future, M1_NOW, max_age_hours=6
    ) == (False, "DISCOVERY_FUTURE")
    assert allocator.discovery_is_current(
        near_future, M1_NOW, max_age_hours=6
    ) == (True, "OK")


@pytest.mark.parametrize("ratio", [float("nan"), -0.2])
def test_invalid_reserve_ratio_cannot_erase_fresh_protection(ratio):
    _, reserve = allocator.effective_reserve(
        M1_NOW, 24, cap=M1_CAP, feasible_ratio=ratio
    )
    assert reserve == M1_CAP


# --- 3. decide_backfill — three independent bounds -------------------------
def test_backfill_refuses_new_window_shorter_than_rolling_download_ledger(conn):
    # A 12h 'new' window would reclassify fresh downloads as historical within
    # the same rolling 24h budget, so it cannot authorize a backfill pull.
    d = _decide(conn, new_window_hours=12, backfill_budget=5)
    assert (d.allowed, d.reason) == (False, "WINDOW_BELOW_LEDGER")


def test_backfill_is_disabled_by_default_so_no_allowance_is_invented(conn):
    """The shipped default is the OLD behaviour: no backfill, no new spend."""
    decision = _decide(conn, backfill_budget=0)
    assert (decision.allowed, decision.reason) == (False, "BUDGET_DISABLED")
    assert decision.budget == 0


def test_backfill_stays_off_even_when_discovery_is_perfect_and_quota_is_surplus(conn):
    """Healthy discovery alone must not create backfill."""
    assert _decide(conn, backfill_budget=0, discovery=_healthy()).allowed is False


@pytest.mark.parametrize(
    "discovery, reason",
    [
        (_health(db.DISCOVERY_FAILED), "DISCOVERY_FAILED"),
        (_health(db.DISCOVERY_UNKNOWN), "DISCOVERY_UNKNOWN"),
        (_healthy(age_h=48.0), "DISCOVERY_STALE"),
        (None, "DISCOVERY_UNKNOWN"),
    ],
)
def test_no_backfill_is_spent_while_discovery_cannot_see_the_feed(conn, discovery, reason):
    """The outage case: upstream discovery down must not drain quota on stale rows."""
    decision = _decide(conn, backfill_budget=25, discovery=discovery)
    assert (decision.allowed, decision.reason) == (False, reason)
    assert decision.used_24h is None
    assert "backfill_24h=unmeasured/" in decision.describe()


def test_backfill_is_admitted_only_with_budget_healthy_discovery_and_surplus(conn):
    decision = _decide(conn, backfill_budget=5, discovery=_healthy(), quota=70)
    assert (decision.allowed, decision.reason) == (True, "OK")
    # Every number the caller needs to audit the call.
    assert decision.reserve == pytest.approx(35.0)
    assert decision.forecast == pytest.approx(M1_FORECAST_24H, abs=0.05)
    assert decision.used_24h == 0
    assert decision.budget == 5


def test_reserve_is_held_when_quota_does_not_cover_the_feasible_reservation(conn):
    held = _decide(conn, backfill_budget=5, discovery=_healthy(), quota=35)
    assert (held.allowed, held.reason) == (False, "RESERVE_HELD")

    # One slot above the feasible reserve is exactly where it starts to admit.
    admitted = _decide(conn, backfill_budget=5, discovery=_healthy(), quota=36)
    assert (admitted.allowed, admitted.reason) == (True, "OK")


def test_budget_is_a_hard_ceiling_rather_than_a_rate_hint(conn):
    """5 backfill pulls already spent against a budget of 2 → stop."""
    for i in range(5):
        _insert(
            conn, f"spent{i}",
            published_at=M1_NOW - timedelta(hours=200),
            downloaded_at=M1_NOW - timedelta(hours=1),
            account="acct",
        )
    decision = _decide(conn, backfill_budget=2, discovery=_healthy())
    assert (decision.allowed, decision.reason) == (False, "BUDGET_SPENT")
    assert decision.used_24h == 5


# --- 4. backfill_used_24h reads the SAME ledger as the quota gauge ----------
def test_backfill_used_24h_counts_only_backfill_pulls(conn):
    # a fresh, new-window pull — must NOT consume the backfill budget
    _insert(conn, "fresh_pull", published_at=M1_NOW - timedelta(hours=2),
            downloaded_at=M1_NOW - timedelta(hours=1), account="acct")
    # an undated pull counts as backfill (unknown age → not fresh), as in queue_depths
    _insert(conn, "undated_pull", published_at=None,
            downloaded_at=M1_NOW - timedelta(hours=1), account="acct")
    # an old backfill pull
    _insert(conn, "old_pull", published_at=M1_NOW - timedelta(hours=300),
            downloaded_at=M1_NOW - timedelta(hours=2), account="acct")
    # a backfill pull from a DIFFERENT account — per-account ledger, not global
    _insert(conn, "other_acct_pull", published_at=M1_NOW - timedelta(hours=300),
            downloaded_at=M1_NOW - timedelta(hours=2), account="someone_else")
    # a backfill pull that aged out of the trailing window
    _insert(conn, "aged_out_pull", published_at=M1_NOW - timedelta(hours=300),
            downloaded_at=M1_NOW - timedelta(hours=25), account="acct")
    used = allocator.backfill_used_24h(conn, "acct", M1_NOW, new_window_hours=48)
    assert used == 2   # undated + old; NOT fresh_pull, other account, or aged-out


# --- 5. invariants the repair must never break -----------------------------
def test_admitting_backfill_never_bypasses_the_fresh_tier(conn):
    """Backfill may only ever be chosen when the fresh queue is EMPTY."""
    _insert(conn, "stale_gold", published_at=M1_NOW - timedelta(hours=400), score=99)
    _insert(conn, "fresh_dud", published_at=M1_NOW - timedelta(hours=1), score=0)

    # Even with backfill admitted AND a far higher-scored backfill row waiting,
    # the new-window paper is returned.
    got = allocator.next_candidate(
        conn, M1_NOW, new_window_hours=48, reserve=0.0, allow_backfill=True
    )
    assert got == "fresh_dud"

    # Only once the fresh queue drains does the backfill row become reachable.
    conn.execute("UPDATE papers SET status=? WHERE blob_id='fresh_dud'",
                 (Status.COMPLETE.value,))
    conn.commit()
    got = allocator.next_candidate(
        conn, M1_NOW, new_window_hours=48, reserve=0.0, allow_backfill=True
    )
    assert got == "stale_gold"


def test_backfill_cannot_spend_outside_the_provider_cap(conn):
    """Total pulls for an account stay bounded by the cap; backfill only reorders."""
    for i in range(M1_CAP):
        _insert(conn, f"full{i}", published_at=M1_NOW - timedelta(hours=300),
                downloaded_at=M1_NOW - timedelta(hours=1), account="acct")
    assert db.available_quota(conn, "acct", M1_CAP, M1_NOW) == 0
    decision = _decide(conn, backfill_budget=100, discovery=_healthy(), quota=0)
    assert decision.allowed is False
    # And the ledger the ceiling reads is the same one the quota gauge reads.
    assert db.trailing_24h_count(conn, "acct", M1_NOW) == M1_CAP
    assert allocator.backfill_used_24h(conn, "acct", M1_NOW, new_window_hours=48) == M1_CAP


def test_the_gate_decides_for_one_account_without_inventing_another(conn):
    """Per-account keys: one account's spend is never another account's allowance."""
    _insert(conn, "spent_by_other", published_at=M1_NOW - timedelta(hours=300),
            downloaded_at=M1_NOW - timedelta(hours=1), account="acct2")
    decision = _decide(conn, backfill_budget=5, discovery=_healthy())
    assert decision.allowed is True           # acct's own budget is untouched
    assert decision.used_24h == 0             # acct2's spend is not acct's


def test_decision_is_deterministic(conn):
    """Same inputs, same decision — the gate must not flap between calls."""
    first = _decide(conn, backfill_budget=5, discovery=_healthy())
    second = _decide(conn, backfill_budget=5, discovery=_healthy())
    assert first == second


def test_describe_reports_the_evidence(conn):
    decision = _decide(conn, backfill_budget=5, discovery=_healthy())
    text = decision.describe()
    assert "True(OK)" in text
    assert "forecast=206.5" in text
    assert "backfill_24h=0/5" in text


# --- 6. the durable discovery-health contract (existing meta KV) -----------
def test_absent_discovery_health_reads_unknown_not_healthy(conn):
    """A DB predating the contract must never be inferred healthy."""
    assert db.discovery_health(conn)["state"] == db.DISCOVERY_UNKNOWN


def test_discovery_health_roundtrip_and_reason_clearing(conn):
    stamp = _iso(M1_NOW)
    db.set_discovery_health(conn, state=db.DISCOVERY_FAILED, observed_at=stamp,
                            reason="DISCOVER_ERROR:Timeout", found_new=0)
    failed = db.discovery_health(conn)
    assert failed["state"] == db.DISCOVERY_FAILED
    assert "Timeout" in failed["reason"]
    assert failed["found_new"] == "0"

    db.set_discovery_health(conn, state=db.DISCOVERY_HEALTHY,
                            observed_at=_iso(M1_NOW), found_new=12)
    healthy = db.discovery_health(conn)
    assert healthy["state"] == db.DISCOVERY_HEALTHY
    assert healthy["reason"] == ""          # nothing outstanding to explain
    assert healthy["found_new"] == "12"


def test_discovery_health_rejects_an_unsupported_state(conn):
    with pytest.raises(ValueError):
        db.set_discovery_health(conn, state="SORT_OF_FINE", observed_at=_iso(M1_NOW))


def test_discovery_health_rejects_an_empty_timestamp(conn):
    with pytest.raises(ValueError):
        db.set_discovery_health(conn, state=db.DISCOVERY_HEALTHY, observed_at="  ")


def test_a_corrupt_state_value_degrades_to_unknown(conn):
    db.set_meta(conn, db.DISCOVERY_STATE_KEY, "gibberish")
    assert db.discovery_health(conn)["state"] == db.DISCOVERY_UNKNOWN
