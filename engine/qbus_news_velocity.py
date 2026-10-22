"""Descriptive per-security news-flow counts from the qbus news store.

``compute_news_velocity`` is a pure read of one security's indexed reports.
It reports how many distinct reports the reader may see (active status,
rights-allowed sources) fall in the last 24 hours and 7 days, beside that
security's own trailing 28 UTC-day counts and their median.
``compare_to_typical`` compares one 24h count with that median for display
only. Display-tier context only.
"""
from __future__ import annotations

from collections.abc import Collection
from datetime import datetime, timedelta, timezone
import math
import sqlite3

from engine.qbus_news_cluster import UNKNOWN_CLUSTER_POLICY_VERSION
from engine.qbus_news_editorial import NewsEditorialView

SCHEMA = "qbus.news_velocity.v1"
METHOD = (
    "distinct reports by source + source_item_id; active status only; "
    "rights-allowed sources only; UTC calendar days; median of 28 prior days"
)
FLOW_COMPARE_RULE = "flow_compare.v1"
BUSIER_MIN_RATIO = 2        # busier needs r24 >= BUSIER_MIN_RATIO * median
BUSIER_MIN_EXCESS = 3       # ... and r24 - median >= BUSIER_MIN_EXCESS
QUIETER_MIN_MEDIAN = 2      # quieter needs median >= QUIETER_MIN_MEDIAN
QUIETER_MAX_FRACTION = 0.5  # ... and r24 <= QUIETER_MAX_FRACTION * median

_HISTORY_CAP_DAYS = 28
_SUFFICIENT_HISTORY_DAYS = 20
_DAILY_WINDOW_DAYS = 28

# Rolling windows are closed at both ends: a report at exactly ``now - 24h``
# or exactly ``now`` is inside the 24h count. Day bins are UTC dates.
#
# The sixth column is the stored cluster policy stamp. Stores created before
# the column existed (and hand-built fixtures) lack it; the literal NULL keeps
# the query valid there and _distinct_stories labels those stories
# "unknown (pre-column)". The first two texts are byte-identical except for
# that one selected expression. The third text is for databases whose
# news_clusters table is absent while news_cluster_members survives: it keeps
# the members join and selects a literal NULL policy column, so member stories
# stay grouped and read "unknown (pre-column)". The fourth text is for
# databases with neither cluster table (a shape NewsStore never writes): it
# drops both cluster joins, so every report is its own story and no policy
# stamp exists.
_STORY_SQL = """
SELECT i.source, i.source_item_id, p.published_at, p.received_at, m.cluster_id,
       c.cluster_policy_version
FROM news_security_index AS i
JOIN news_states AS s
  ON s.source = i.source
 AND s.source_item_id = i.source_item_id
JOIN news_state_projection AS p
  ON p.source = i.source
 AND p.source_item_id = i.source_item_id
LEFT JOIN news_cluster_members AS m
  ON m.source = i.source
 AND m.source_item_id = i.source_item_id
LEFT JOIN news_clusters AS c
  ON c.cluster_id = m.cluster_id
WHERE i.security_id = ?
  AND s.status = 'active'
  AND s.source IN ({placeholders})
ORDER BY i.source, i.source_item_id
"""

_STORY_SQL_NO_POLICY_COLUMN = """
SELECT i.source, i.source_item_id, p.published_at, p.received_at, m.cluster_id,
       NULL
FROM news_security_index AS i
JOIN news_states AS s
  ON s.source = i.source
 AND s.source_item_id = i.source_item_id
JOIN news_state_projection AS p
  ON p.source = i.source
 AND p.source_item_id = i.source_item_id
LEFT JOIN news_cluster_members AS m
  ON m.source = i.source
 AND m.source_item_id = i.source_item_id
LEFT JOIN news_clusters AS c
  ON c.cluster_id = m.cluster_id
WHERE i.security_id = ?
  AND s.status = 'active'
  AND s.source IN ({placeholders})
ORDER BY i.source, i.source_item_id
"""

_STORY_SQL_MEMBERS_ONLY = """
SELECT i.source, i.source_item_id, p.published_at, p.received_at, m.cluster_id,
       NULL
FROM news_security_index AS i
JOIN news_states AS s
  ON s.source = i.source
 AND s.source_item_id = i.source_item_id
JOIN news_state_projection AS p
  ON p.source = i.source
 AND p.source_item_id = i.source_item_id
LEFT JOIN news_cluster_members AS m
  ON m.source = i.source
 AND m.source_item_id = i.source_item_id
WHERE i.security_id = ?
  AND s.status = 'active'
  AND s.source IN ({placeholders})
ORDER BY i.source, i.source_item_id
"""

_STORY_SQL_NO_CLUSTER_TABLES = """
SELECT i.source, i.source_item_id, p.published_at, p.received_at, NULL, NULL
FROM news_security_index AS i
JOIN news_states AS s
  ON s.source = i.source
 AND s.source_item_id = i.source_item_id
JOIN news_state_projection AS p
  ON p.source = i.source
 AND p.source_item_id = i.source_item_id
WHERE i.security_id = ?
  AND s.status = 'active'
  AND s.source IN ({placeholders})
ORDER BY i.source, i.source_item_id
"""


def _has_cluster_policy_column(conn: sqlite3.Connection) -> bool:
    rows = conn.execute("PRAGMA table_info(news_clusters)").fetchall()
    return any(str(row[1]) == "cluster_policy_version" for row in rows)


def _cluster_tables_present(conn: sqlite3.Connection) -> set[str]:
    """The subset of the two cluster tables that exists in ``conn``."""
    rows = conn.execute(
        "SELECT name FROM sqlite_master"
        " WHERE type='table'"
        " AND name IN ('news_clusters','news_cluster_members')"
    ).fetchall()
    return {str(row[0]) for row in rows}


def compute_news_velocity(
    conn: sqlite3.Connection,
    *,
    security_id: str,
    now: datetime,
    allowed_sources: Collection[str],
    curated: bool = False,
    allowed_url_sources: Collection[str] = (),
    allowed_teaser_sources: Collection[str] = (),
    editorial_view: NewsEditorialView | None = None,
) -> dict:
    """Return schema ``qbus.news_velocity.v1`` for one security as of ``now``.

    ``conn`` is read with SELECT only. ``now`` must be timezone-aware; counts
    are computed after converting it to UTC. ``allowed_sources`` is the
    request's read rights: only reports whose source is listed are counted.
    The same database, the same ``now`` and the same rights produce the same
    dict.
    """
    if not isinstance(security_id, str):
        raise TypeError("security_id must be a str")
    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() is None
    ):
        raise ValueError("now must be a timezone-aware datetime")
    if isinstance(allowed_sources, str):
        raise TypeError(
            "allowed_sources must be a collection of source ids, not a str"
        )
    counted_sources = sorted(set(allowed_sources))

    as_of = now.astimezone(timezone.utc)
    if not counted_sources:
        # "IN ()" is invalid SQLite, and there is nothing to count anyway.
        return _assemble(security_id, as_of, {}, counted_sources)
    placeholders = ",".join("?" for _ in counted_sources)
    present = _cluster_tables_present(conn)
    if present == {"news_clusters", "news_cluster_members"}:
        story_sql = (
            _STORY_SQL
            if _has_cluster_policy_column(conn)
            else _STORY_SQL_NO_POLICY_COLUMN
        )
    elif present == {"news_cluster_members"}:
        # Membership survives without its cluster rows: keep the members
        # join, and every member story reads as an unknown policy stamp.
        story_sql = _STORY_SQL_MEMBERS_ONLY
    else:
        story_sql = _STORY_SQL_NO_CLUSTER_TABLES
    curated_params: tuple[str, ...] = ()
    if curated:
        from engine.qbus_news_quality import curated_sql_clause, register_curated_reader
        register_curated_reader(conn, editorial_view)
        clause, curated_params = curated_sql_clause(
            tuple(source for source in allowed_url_sources if source in counted_sources),
            tuple(source for source in allowed_teaser_sources if source in counted_sources),
            editorial_view=editorial_view,
        )
        story_sql = story_sql.replace(
            "AND s.status = 'active'",
            f"AND s.status = 'active' {clause}",
        )
    rows = conn.execute(
        story_sql.format(placeholders=placeholders),
        (security_id, *curated_params, *counted_sources),
    ).fetchall()
    stories = _distinct_stories(rows)
    return _assemble(security_id, as_of, stories, counted_sources)


def compare_to_typical(
    r24: int,
    median: float | None,
    sufficient: bool,
    coverage: str,
) -> str | None:
    """Compare one 24h report count with a security's own 28-day median.

    The first matching row of flow_compare.v1 wins: partial coverage is
    None; thin history or a missing median is ``insufficient_history``;
    otherwise ``busier``/``quieter``/``typical`` from the module constants.
    Comparisons use the exact median, never a rounded one. Display only:
    the result never feeds ranking, sizing or gating.
    """
    if coverage not in ("complete", "partial"):
        raise ValueError("coverage must be 'complete' or 'partial'")
    if isinstance(r24, bool) or not isinstance(r24, int) or r24 < 0:
        raise ValueError("r24 must be an int >= 0")
    if median is not None:
        if isinstance(median, bool) or not isinstance(median, (int, float)):
            raise ValueError("median must be None or a finite number >= 0")
        if not math.isfinite(median) or median < 0:
            raise ValueError("median must be None or a finite number >= 0")

    if coverage == "partial":
        return None
    if not sufficient or median is None:
        return "insufficient_history"
    if r24 >= BUSIER_MIN_RATIO * median and r24 - median >= BUSIER_MIN_EXCESS:
        return "busier"
    if median >= QUIETER_MIN_MEDIAN and r24 <= QUIETER_MAX_FRACTION * median:
        return "quieter"
    return "typical"


def _distinct_stories(
    rows: list[tuple[object, ...]],
) -> dict[tuple[str, str], tuple[datetime, str, str, str | None]]:
    """One entry per (source, source_item_id); the ordered row wins ties.

    The entry carries the report's effective time, its time basis, its story
    key (the cluster id, or ``item:`` + source + ``\\x1f`` + source_item_id
    when the report sits in no cluster) and the policy label of the cluster
    that minted it: the stored stamp, ``None`` for no cluster, or
    ``UNKNOWN_CLUSTER_POLICY_VERSION`` when the cluster row is missing
    (deleted, or the clusters table absent while membership survives) or
    was minted before the stamp column existed.
    """
    stories: dict[
        tuple[str, str], tuple[datetime, str, str, str | None]
    ] = {}
    for (
        source,
        source_item_id,
        published_at,
        received_at,
        cluster_id,
        policy_version,
    ) in rows:
        key = (str(source), str(source_item_id))
        if key in stories:
            continue
        when, basis = _effective_time(published_at, received_at)
        if when is None:
            continue
        if cluster_id is None:
            story_key = "item:" + key[0] + "\x1f" + key[1]
            label = None
        elif policy_version is None:
            story_key = str(cluster_id)
            label = UNKNOWN_CLUSTER_POLICY_VERSION
        else:
            story_key = str(cluster_id)
            label = str(policy_version)
        stories[key] = (when, basis, story_key, label)
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
    stories: dict[tuple[str, str], tuple[datetime, str, str, str | None]],
    counted_sources: list[str],
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
    basis_counts_24h = {"published_at": 0, "received_at": 0}
    story_keys_24h: set[str] = set()
    policy_versions_24h: set[str] = set()
    first: datetime | None = None

    for when, basis, story_key, policy_label in stories.values():
        basis_counts[basis] += 1
        if first is None or when < first:
            first = when
        if start_24h <= when <= as_of:
            count_24h += 1
            basis_counts_24h[basis] += 1
            story_keys_24h.add(story_key)
            if policy_label is not None:
                policy_versions_24h.add(policy_label)
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
        "stories_24h": len(story_keys_24h),
        "cluster_policy_versions_24h": sorted(policy_versions_24h),
        "daily_counts_28d": daily,
        "median_daily_28d": median,
        "history_days_observed": history_days,
        "sufficient_history": sufficient,
        "basis_counts": basis_counts,
        "basis_counts_24h": basis_counts_24h,
        "sources_counted": list(counted_sources),
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


def _report_phrase(count: int) -> str:
    if count == 1:
        return "1 report"
    return f"{count} reports"


def _label(count_24h: int, median: float | None, sufficient: bool) -> dict[str, str]:
    if not sufficient or median is None:
        return {
            "en": f"{_report_phrase(count_24h)} in 24h; not enough history yet",
            "zh": f"24小时内{count_24h}篇报道；历史数据不足",
        }
    shown = _format_median(median)
    return {
        "en": (
            f"{_report_phrase(count_24h)} in 24h; "
            f"typical day ~{shown} (28-day median)"
        ),
        "zh": f"24小时内{count_24h}篇报道；近28天中位数约每日{shown}篇",
    }
