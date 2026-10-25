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

import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping
from zoneinfo import ZoneInfo

from .db import DISCOVERY_HEALTHY, DISCOVERY_UNKNOWN
from .schemas import Status

# ---------------------------------------------------------------------------
# Measured posts-per-ET-hour profile (over 175 days). Bins are Eastern wall
# clock hours, with DST resolved by America/New_York on each UTC observation.
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

# Use actual Eastern wall-clock time for this EDT-measured hourly profile.
# A fixed -4h offset misclassifies Friday 23:30 EST as Saturday 00:30,
# under-reserving fresh arrivals when the backlog budget is enabled.
_ET_ZONE = ZoneInfo("America/New_York")


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
    return dt_utc.astimezone(_ET_ZONE).replace(tzinfo=None)


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


# ---------------------------------------------------------------------------
# Backfill admission — is spending a slot on stale history lawful RIGHT NOW?
# ---------------------------------------------------------------------------
# The old gate was one comparison, ``allow_backfill = quota > reserve``, where
# ``quota`` is bounded by the provider's rolling cap (70) and ``reserve`` was a
# RAW demand forecast in papers (measured 2026-10-22T07:16:48Z: 206.5 expected
# arrivals over BACKFILL_RESERVE_HOURS=24). A forecast that exceeds the entire
# physical allowance can NEVER be overtaken, so ``allow_backfill`` was
# permanently False and the 7,386-row backlog stalled forever — not conservatively,
# but UNREACHABLY, with no signal that anything was wrong. The three bounds below
# make the gate reachable, feasible and evidence-driven without ever raising the
# cap or inventing an allowance.


def _parse_ts(s: str | None) -> datetime | None:
    """Parse a stored ISO timestamp; anything unparseable is None, never a guess."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def effective_reserve(
    now: datetime,
    backfill_reserve_hours: float,
    *,
    cap: int,
    feasible_ratio: float,
    profile: HourlyProfile | None = None,
) -> tuple[float, float]:
    """``(forecast, reserve)`` — the demand forecast and the reservation applied.

    A reservation is only meaningful if it is FEASIBLE: you cannot hold back 206
    pull slots out of a 70-slot rolling budget. Clamping the forecast to
    ``cap * feasible_ratio`` — the largest share of the CAP that could physically
    be withheld — keeps the reserve honest (never phantom) and keeps every pull
    inside the same provider limit. ``feasible_ratio`` is a share of the existing
    cap, never an addition to it, so this cannot raise the provider allowance.

    The ceiling is ALSO clamped to the cap itself, so a mis-configured ratio
    cannot produce a reservation larger than the whole allowance: that limit is
    structural here rather than dependent on an operator typing a sane number.
    The forecast is returned alongside (never discarded) so the plan line can
    still report how far above the cap the raw demand actually sat.
    """
    forecast = expected_new_next_hours(now, backfill_reserve_hours, profile)
    cap_f = max(0.0, float(cap))
    ratio = float(feasible_ratio)
    # An invalid negative/NaN configuration must not silently erase the fresh
    # reserve and admit history. Hold the entire cap instead (fail closed).
    ceiling = cap_f if math.isnan(ratio) or ratio < 0 else min(cap_f, cap_f * ratio)
    return forecast, min(forecast, ceiling)


def backfill_used_24h(
    conn: sqlite3.Connection,
    account: str,
    now: datetime,
    *,
    new_window_hours: float,
    window_hours: float = 24.0,
) -> int:
    """Backfill pulls this account already spent in the trailing window.

    Read from the SAME rolling ledger the quota gauge uses (``account`` +
    ``downloaded_at``) rather than a new counter, so the ceiling is enforced
    against downloads that actually happened and no second source of truth is
    introduced. A NULL ``published_at`` counts as backfill, mirroring
    :func:`queue_depths` and :func:`next_candidate`.
    """
    dl_cutoff = _iso(now - timedelta(hours=window_hours))
    new_cutoff = new_cutoff_iso(now, new_window_hours)
    row = conn.execute(
        "SELECT COUNT(*) c FROM papers WHERE account=? "
        "AND downloaded_at IS NOT NULL AND downloaded_at >= ? "
        "AND (published_at IS NULL OR published_at < ?)",
        (account, dl_cutoff, new_cutoff),
    ).fetchone()
    return int(row["c"]) if row else 0


def discovery_is_current(
    health: Mapping[str, str] | None,
    now: datetime,
    *,
    max_age_hours: float,
) -> tuple[bool, str]:
    """``(ok, reason)`` — may backfill rely on this discovery evidence?

    Fail-closed at every step: absent, unparseable, FAILED, or merely OLD
    evidence all refuse. Only a HEALTHY observation inside ``max_age_hours``
    proves the fresh queue is actually empty, which is the only licence to spend
    quota on stale backlog. Invalid/non-finite age limits refuse admission;
    a future stamp beyond five minutes of clock skew is not current evidence.
    """
    if (isinstance(max_age_hours, bool)
            or not isinstance(max_age_hours, (int, float))
            or not math.isfinite(max_age_hours) or max_age_hours <= 0):
        return False, "DISCOVERY_CONFIG_INVALID"
    if not health:
        return False, "DISCOVERY_UNKNOWN"
    state = str(health.get("state") or DISCOVERY_UNKNOWN)
    if state != DISCOVERY_HEALTHY:
        return False, f"DISCOVERY_{state}"
    observed = _parse_ts(health.get("observed_at"))
    if observed is None:
        return False, "DISCOVERY_UNSTAMPED"
    age_seconds = (now - observed).total_seconds()
    # Both clocks are from this producer host. Permit at most ordinary small
    # clock skew; a future observation is not proof that discovery is current.
    if age_seconds < -300:
        return False, "DISCOVERY_FUTURE"
    if age_seconds / 3600.0 > max_age_hours:
        return False, "DISCOVERY_STALE"
    return True, "OK"


@dataclass(frozen=True)
class BackfillDecision:
    """Why backfill is (or is not) admissible, with the numbers behind the call."""

    allowed: bool
    reason: str
    forecast: float   # raw demand forecast (papers expected over the reserve horizon)
    reserve: float    # feasible reservation actually applied
    used_24h: int | None  # None until the incumbent ledger was actually read
    budget: int       # configured ceiling (0 = backfill disabled)

    def describe(self) -> str:
        return (
            f"{self.allowed}({self.reason}) "
            f"reserve={self.reserve:.1f}/forecast={self.forecast:.1f} "
            f"backfill_24h={self.used_24h if self.used_24h is not None else 'unmeasured'}/{self.budget}"
        )


def decide_backfill(
    conn: sqlite3.Connection,
    now: datetime,
    *,
    account: str,
    quota: int,
    cap: int,
    new_window_hours: float,
    backfill_reserve_hours: float,
    reserve_feasible_ratio: float = 0.0,
    backfill_budget: int = 0,
    profile: HourlyProfile | None = None,
    discovery: Mapping[str, str] | None = None,
    discovery_max_age_hours: float = 6.0,
) -> BackfillDecision:
    """May this account spend a slot on historical backfill right now?

    Three INDEPENDENT bounds, all of which must pass, each with its own reason:

    1. ``BUDGET`` — an operator-set per-account ceiling on backfill pulls per
       trailing 24h. Its default is 0, which is exactly the pre-existing
       (stalled) behaviour: this knob is the ONLY thing here that can enable a
       backfill pull, so the repair cannot invent an allowance by itself.
    2. ``DISCOVERY`` — evidence-driven. Only a recent HEALTHY discovery pass proves
       "no fresh candidates" is real rather than blindness, so an upstream
       discovery outage never spends the day's quota on stale backlog.
    3. ``RESERVE`` — the FEASIBLE reservation must still be covered by remaining
       quota, holding slots for imminent fresh arrivals.

    Fresh-first is NOT this function's job and is never bypassed by it:
    :func:`next_candidate` returns a new-window paper ahead of any backfill paper
    whenever one exists, so admitting backfill only changes what happens when the
    fresh queue is empty.
    """
    forecast, reserve = effective_reserve(
        now, backfill_reserve_hours,
        cap=cap, feasible_ratio=reserve_feasible_ratio, profile=profile,
    )
    budget = max(0, int(backfill_budget))
    if budget <= 0:
        return BackfillDecision(False, "BUDGET_DISABLED", forecast, reserve, None, budget)

    # The incumbent download ledger is a trailing 24h window. A shorter
    # "fresh" classification window makes legitimate recent downloads count
    # retroactively against the historical budget. Refuse opt-in backfill
    # rather than inventing a new tier ledger or charging the wrong class.
    if (type(new_window_hours) not in (int, float)
            or not math.isfinite(new_window_hours)
            or new_window_hours < 24.0):
        return BackfillDecision(
            False, "WINDOW_BELOW_LEDGER", forecast, reserve, None, budget
        )

    ok, why = discovery_is_current(
        discovery, now, max_age_hours=discovery_max_age_hours
    )
    if not ok:
        # No ledger probe on the refusal path: a blind collector must not even
        # pay for the query that a permitted pull would have justified.
        return BackfillDecision(False, why, forecast, reserve, None, budget)

    used = backfill_used_24h(
        conn, account, now, new_window_hours=new_window_hours
    )
    if quota <= reserve:
        return BackfillDecision(False, "RESERVE_HELD", forecast, reserve, used, budget)
    if used >= budget:
        return BackfillDecision(False, "BUDGET_SPENT", forecast, reserve, used, budget)
    return BackfillDecision(True, "OK", forecast, reserve, used, budget)
