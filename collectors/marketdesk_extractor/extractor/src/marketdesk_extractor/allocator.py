"""Demand-aware download allocator — the pure decision core of the trickle loop.

MarketDesk caps PDF downloads to a rolling 24h window PER ACCOUNT while the
read/discovery API is uncapped, and posting volume is bursty and front-loaded
(weekday peak 06-09 ET). Our max pull rate sits far below the peak arrival rate,
so a queue is unavoidable — this module decides, at each tick, what a given
account should pull next so that:

  1. the freshest new research drains first, and
  2. leftover quota does historical backfill, but
  3. only after holding back enough quota for the new posts expected to arrive
     in the next few hours (the reserve).

WITHIN each tier the order is VALUE-FIRST, not recency-first: papers are scored at
discovery time (``score.py`` -> ``papers.local_priority_score``, higher = better)
and the tier is drained by ``score DESC, published_at DESC``. Recency alone was
the old ordering and it wasted slots — a zero-value note posted five minutes ago
outranked a Goldman initiation from an hour ago, and with ~200 papers/day posted
against a ~70/day pull budget that mis-ordering is paid for every single day. The
TIER split is still strictly recency-based (a new-window paper always drains
before ANY backfill paper, however highly scored), because a paper's value decays
with age and the new window is what the reserve is protecting.

Everything here is PURE: functions take ``now`` (a tz-aware UTC ``datetime``), an
open sqlite ``Connection``, and plain params — no network, no clock reads, no
config object — so the whole policy is unit-testable against a temp DB. The
trickle runner (``trickle.py``) supplies the clock, the sessions, and the I/O.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Mapping

from .schemas import Status

# ---------------------------------------------------------------------------
# Measured posts-per-ET-hour profile (over 175 days). ET = UTC-4 (EDT).
# Weekday ~208 posts/day, weekend ~85; ~60% of a day's posts land by 09 ET.
# Overridable: every consumer takes an optional ``profile`` argument.
# ---------------------------------------------------------------------------
WEEKDAY_HOURLY: dict[int, float] = {
    0: 7.5, 1: 1.5, 2: 0.2, 3: 0.3, 4: 1.5, 5: 8.1, 6: 20.6, 7: 34.2,
    8: 14.5, 9: 12.4, 10: 9.8, 11: 9.8, 12: 9.8, 13: 6.0, 14: 4.5, 15: 3.9,
    16: 4.5, 17: 9.0, 18: 13.1, 19: 14.3, 20: 4.5, 21: 2.6, 22: 4.2, 23: 9.7,
}
WEEKEND_HOURLY: dict[int, float] = {
    0: 5.9, 1: 0.1, 2: 0.0, 3: 1.5, 4: 0.0, 5: 0.0, 6: 1.5, 7: 5.0,
    8: 1.3, 9: 0.8, 10: 4.2, 11: 3.9, 12: 9.7, 13: 6.1, 14: 12.4, 15: 6.4,
    16: 5.8, 17: 3.5, 18: 4.0, 19: 3.2, 20: 2.4, 21: 2.4, 22: 1.8, 23: 3.3,
}

# ET offset. The measured profile is stated in EDT (UTC-4); see task brief.
_ET_OFFSET = timedelta(hours=-4)


class HourlyProfile:
    """Weekday/weekend posts-per-ET-hour lookup. Immutable, overridable."""

    def __init__(
        self,
        weekday: Mapping[int, float] | None = None,
        weekend: Mapping[int, float] | None = None,
    ) -> None:
        self.weekday = dict(weekday) if weekday is not None else dict(WEEKDAY_HOURLY)
        self.weekend = dict(weekend) if weekend is not None else dict(WEEKEND_HOURLY)

    def rate_at(self, dt_utc: datetime) -> float:
        """Expected posts/hour at the ET instant corresponding to ``dt_utc``."""
        et = _to_et(dt_utc)
        table = self.weekend if et.weekday() >= 5 else self.weekday
        return float(table.get(et.hour, 0.0))


DEFAULT_PROFILE = HourlyProfile()


def _to_et(dt_utc: datetime) -> datetime:
    """UTC (tz-aware) -> naive ET wall-clock used to index the profile."""
    if dt_utc.tzinfo is None:
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
    return (dt_utc.astimezone(timezone.utc) + _ET_OFFSET).replace(tzinfo=None)


def _iso(dt: datetime) -> str:
    """ISO string for lexicographic comparison against stored ``published_at``.

    Stored timestamps are tz-aware ISO-8601 (always ``+00:00``); we build the
    cutoff the same way so string ``>=`` / ``<`` ordering is correct.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def new_cutoff_iso(now: datetime, new_window_hours: float) -> str:
    """The ISO ``published_at`` boundary below which a paper is backfill, not new."""
    return _iso(now - timedelta(hours=new_window_hours))


def is_new(published_at: str | None, now: datetime, new_window_hours: float) -> bool:
    """Is a stored ``published_at`` within the new window? NULL/unknown → not new."""
    if not published_at:
        return False
    return published_at >= new_cutoff_iso(now, new_window_hours)


# ---------------------------------------------------------------------------
# Demand estimate (drives the backfill reserve)
# ---------------------------------------------------------------------------
def expected_new_next_hours(
    now: datetime, hours: float, profile: HourlyProfile | None = None
) -> float:
    """Estimated number of NEW posts arriving in ``[now, now + hours)``.

    Integrates the per-ET-hour profile across the window, hour by hour, so a
    window that straddles midnight or the weekday/weekend boundary is summed
    against the correct rate for each slice. ``hours`` may be fractional; the
    last partial hour contributes its fraction of that hour's rate.
    """
    profile = profile or DEFAULT_PROFILE
    if hours <= 0:
        return 0.0
    total = 0.0
    remaining = float(hours)
    cursor = now
    while remaining > 1e-9:
        # fraction of the CURRENT clock hour still ahead of the cursor
        minute_frac = (cursor.minute * 60 + cursor.second) / 3600.0
        slice_len = min(remaining, 1.0 - minute_frac)
        if slice_len <= 0:  # exactly on an hour boundary edge case
            slice_len = min(remaining, 1.0)
        total += profile.rate_at(cursor) * slice_len
        cursor = cursor + timedelta(hours=slice_len)
        remaining -= slice_len
    return total


# ---------------------------------------------------------------------------
# Candidate selection
# ---------------------------------------------------------------------------
# A paper is a download candidate iff it has not been pulled yet: DISCOVERED or
# BLOB_FOUND. FAILED is deliberately EXCLUDED — next_candidate is deterministic
# (newest-first), so a paper that fails and stays a candidate gets re-selected
# immediately and tight-loops, burning the rolling-download quota (observed: a
# non-PDF ZIP blob retried 7x in one tick). FAILED rows get one retry via the
# loop-start reset; permanently-unusable blobs are marked SKIPPED_UNSUPPORTED
# (also never a candidate).
_CANDIDATE_STATUSES = (
    Status.DISCOVERED.value,
    Status.BLOB_FOUND.value,
)

#: Public alias so other modules (``backlog.py``) can report on exactly the set
#: the allocator pulls from, instead of keeping a copy that can drift.
CANDIDATE_STATUSES = _CANDIDATE_STATUSES


def queue_depths(
    conn: sqlite3.Connection, now: datetime, *, new_window_hours: float
) -> tuple[int, int]:
    """(new_pending, backfill_pending) among downloadable candidates.

    ``new`` = published within the new window; ``backfill`` = older. Rows with a
    NULL ``published_at`` count as backfill (unknown age → not fresh).
    """
    cutoff = new_cutoff_iso(now, new_window_hours)
    q = ",".join("?" for _ in _CANDIDATE_STATUSES)
    new_n = conn.execute(
        f"SELECT COUNT(*) c FROM papers WHERE status IN ({q}) "
        "AND published_at IS NOT NULL AND published_at >= ?",
        (*_CANDIDATE_STATUSES, cutoff),
    ).fetchone()["c"]
    back_n = conn.execute(
        f"SELECT COUNT(*) c FROM papers WHERE status IN ({q}) "
        "AND (published_at IS NULL OR published_at < ?)",
        (*_CANDIDATE_STATUSES, cutoff),
    ).fetchone()["c"]
    return int(new_n), int(back_n)


def next_candidate(
    conn: sqlite3.Connection,
    now: datetime,
    *,
    new_window_hours: float,
    reserve: float = 0.0,  # kept for signature symmetry; gating is via allow_backfill
    allow_backfill: bool,
) -> str | None:
    """The ``blob_id`` this account should download next, or ``None``.

    Two tiers, drained strictly in order — VALUE-FIRST WITHIN each tier:

    Priority 1: downloadable papers published within the new window
                (``published_at >= now - new_window``), ordered
                ``local_priority_score DESC, published_at DESC``: the most
                valuable fresh paper first, recency breaking ties.
    Priority 2: (only when ``allow_backfill``) downloadable papers OLDER than the
                new window, ordered ``(published_at IS NULL), score DESC,
                published_at DESC`` — dated history before undated rows, then
                most valuable, then newest.

    A NULL ``local_priority_score`` is coalesced to 0, so an unscored row sorts
    below anything with real value rather than being dropped. The tiers never
    interleave: a new-window paper is pulled ahead of a HIGHER-scored backfill
    paper, because fresh research is what the reserve exists to protect.

    ``reserve`` is accepted but not applied here: the reserve is a whole-account
    budget decision made by the caller (``allow_backfill = available_quota >
    reserve``), not a per-candidate one. Keeping the param documents the contract
    and lets a caller pass it through unchanged.
    """
    cutoff = new_cutoff_iso(now, new_window_hours)
    q = ",".join("?" for _ in _CANDIDATE_STATUSES)

    new_row = conn.execute(
        f"SELECT blob_id FROM papers WHERE status IN ({q}) "
        "AND published_at IS NOT NULL AND published_at >= ? "
        "ORDER BY COALESCE(local_priority_score, 0) DESC, published_at DESC LIMIT 1",
        (*_CANDIDATE_STATUSES, cutoff),
    ).fetchone()
    if new_row is not None:
        return new_row["blob_id"]

    if not allow_backfill:
        return None

    back_row = conn.execute(
        f"SELECT blob_id FROM papers WHERE status IN ({q}) "
        "AND (published_at IS NULL OR published_at < ?) "
        "ORDER BY (published_at IS NULL), COALESCE(local_priority_score, 0) DESC, "
        "published_at DESC LIMIT 1",
        (*_CANDIDATE_STATUSES, cutoff),
    ).fetchone()
    if back_row is not None:
        return back_row["blob_id"]
    return None
