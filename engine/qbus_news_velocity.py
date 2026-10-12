"""Descriptive per-security news-flow counts from the qbus news store.

``compute_news_velocity`` is a pure read of one security's indexed stories.
It reports how many distinct stories fall in the last 24 hours and 7 days,
beside that security's own trailing 28 UTC-day counts and their median.
Display-tier context only.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sqlite3

SCHEMA = "qbus.news_velocity.v1"
METHOD = (
    "distinct stories; withdrawn excluded; UTC calendar days; "
    "median of 28 prior days"
)
_HISTORY_CAP_DAYS = 28
_SUFFICIENT_HISTORY_DAYS = 20
_DAILY_WINDOW_DAYS = 28

# Rolling windows are closed at both ends: a story at exactly ``now - 24h``
# or exactly ``now`` is inside the 24h count. Day bins are UTC dates.
_STORY_SQL = """
SELECT i.source, i.source_item_id, p.published_at, p.received_at
FROM news_security_index AS i
JOIN news_states AS s
  ON s.source = i.source
 AND s.source_item_id = i.source_item_id
JOIN news_state_projection AS p
  ON p.source = i.source
 AND p.source_item_id = i.source_item_id
WHERE i.security_id = ?
  AND s.status != 'withdrawn'
ORDER BY i.source, i.source_item_id
"""


def compute_news_velocity(
    conn: sqlite3.Connection,
    *,
    security_id: str,
    now: datetime,
) -> dict:
    """Return schema ``qbus.news_velocity.v1`` for one security as of ``now``.

    ``conn`` is read with SELECT only. ``now`` must be timezone-aware; counts
    are computed after converting it to UTC. The same database and the same
    ``now`` produce the same dict.
    """
    if not isinstance(security_id, str):
        raise TypeError("security_id must be a str")
    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() is None
    ):
        raise ValueError("now must be a timezone-aware datetime")

    as_of = now.astimezone(timezone.utc)
    rows = conn.execute(_STORY_SQL, (security_id,)).fetchall()
    stories = _distinct_stories(rows)
    return _assemble(security_id, as_of, stories)


def _distinct_stories(
    rows: list[tuple[object, ...]],
) -> dict[tuple[str, str], tuple[datetime, str]]:
    """One entry per (source, source_item_id); the ordered row wins ties."""
    stories: dict[tuple[str, str], tuple[datetime, str]] = {}
    for source, source_item_id, published_at, received_at in rows:
        key = (str(source), str(source_item_id))
        if key in stories:
            continue
        when, basis = _effective_time(published_at, received_at)
        if when is None:
            continue
        stories[key] = (when, basis)
    return stories


def _effective_time(
    published_at: object, received_at: object
) -> tuple[datetime | None, str]:
    published = _parse_instant(published_at)
    if published is not None:
        return published, "published_at"
    return _parse_instant(received_at), "received_at"


def _parse_instant(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value).strip()
        if not text:
            return None
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _assemble(
    security_id: str,
    as_of: datetime,
    stories: dict[tuple[str, str], tuple[datetime, str]],
) -> dict:
    as_of_date = as_of.date()
    yesterday = as_of_date - timedelta(days=1)
    oldest = yesterday - timedelta(days=_DAILY_WINDOW_DAYS - 1)
    start_24h = as_of - timedelta(hours=24)
    start_7d = as_of - timedelta(days=7)

    count_24h = 0
    count_7d = 0
    daily = [0] * _DAILY_WINDOW_DAYS
    basis_counts = {"published_at": 0, "received_at": 0}
    first: datetime | None = None

    for when, basis in stories.values():
        basis_counts[basis] += 1
        if first is None or when < first:
            first = when
        if start_24h <= when <= as_of:
            count_24h += 1
        if start_7d <= when <= as_of:
            count_7d += 1
        offset = (when.date() - oldest).days
        if 0 <= offset < _DAILY_WINDOW_DAYS:
            daily[offset] += 1

    if first is None:
        history_days = 0
    else:
        span = (as_of_date - first.date()).days
        history_days = 0 if span < 0 else min(_HISTORY_CAP_DAYS, span)
    sufficient = history_days >= _SUFFICIENT_HISTORY_DAYS
    median = _median(daily) if sufficient else None

    return {
        "schema": SCHEMA,
        "security_id": security_id,
        "as_of": as_of.isoformat(),
        "count_24h": count_24h,
        "count_7d": count_7d,
        "daily_counts_28d": daily,
        "median_daily_28d": median,
        "history_days_observed": history_days,
        "sufficient_history": sufficient,
        "basis_counts": basis_counts,
        "method": METHOD,
        "label": _label(count_24h, median, sufficient),
    }


def _median(values: list[int]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _format_median(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return f"{value:.1f}"


def _story_phrase(count: int) -> str:
    if count == 1:
        return "1 story"
    return f"{count} stories"


def _label(count_24h: int, median: float | None, sufficient: bool) -> dict[str, str]:
    if not sufficient or median is None:
        return {
            "en": f"{_story_phrase(count_24h)} in 24h; not enough history yet",
            "zh": f"24小时内{count_24h}篇报道；历史数据不足",
        }
    shown = _format_median(median)
    return {
        "en": (
            f"{_story_phrase(count_24h)} in 24h; "
            f"typical day ~{shown} (28-day median)"
        ),
        "zh": f"24小时内{count_24h}篇报道；近28天中位数约每日{shown}篇",
    }
