"""Audience projection helpers; ranking policy remains in news_common/qkernel.

No network, model call, source admission or storage authority lives here. A
representative is selected only after the caller has applied current source rights.
Feed chronology remains the store change sequence, independent of this choice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlsplit

from engine.news_common import low_value_reason, quality_score, ticker_editorial_reason, ticker_template_reason
from engine.qkernel import publisher_category, publisher_domain, publisher_tier

EDITORIAL_POLICY_VERSION = "ticker_news.curated.v1"

_RANK_CLOCK = datetime(2000, 1, 1, tzinfo=timezone.utc)


def display_text(value: object) -> str:
    """Decode vendor HTML entities as plain text; consumers must escape rendering."""
    return unescape(str(value or ""))


def publisher_identity(source: str, url: str = "") -> str:
    # Transport-scoped grants remain distinct even when the publisher is the same.
    source = source.strip().lower()
    if source == "benzinga":
        return "benzinga.com"
    if source.startswith("massive:"):
        return publisher_domain(source.partition(":")[2])
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        host = ""
    return host.removeprefix("www.") or source


def story_quality(*, title: str, url: str, source: str) -> tuple[int, str | None]:
    title = display_text(title)
    domain = publisher_identity(source, url)
    # Use a fixed, equal age so a later rewrite cannot win on arrival recency.
    # A vendor or rights receipt cannot upgrade an unknown/blocked publisher.
    score = quality_score(
        title, domain, _RANK_CLOCK.isoformat(), now=_RANK_CLOCK,
        tier=publisher_tier(domain),
    )
    return score, low_value_reason(title, domain) or ticker_template_reason(title, domain)


def representative_key(row, rights=None) -> tuple:
    # Ranking observes the same field projection as the consuming audience.
    source = str(row["source"])
    if rights is not None:
        row = {**dict(row), **{
            field: row[field] if rights.allows(source, field) else ""
            for field in ("title", "url", "teaser")
        }}
    score, reason = story_quality(
        title=str(row["title"]), url=str(row["url"]), source=str(row["source"])
    )
    return (
        reason is None, score, bool(row["teaser"]),
        int(row["last_sequence"] or 0), str(row["source"]), str(row["source_item_id"]),
    )


def reporting_state(rows, rights=None) -> str:
    """Compare eligible current headlines without deciding which account is true."""
    from engine.qbus_news_cluster import _compatible

    titles = set()
    visible_reports = 0
    for row in rows:
        if rights is None or rights.allows(str(row["source"]), "title"):
            title = display_text(row["title"])
            if title:
                visible_reports += 1
                titles.add(title)
        if len(titles) > 32:
            return "comparison_limited"
    if visible_reports < 2:
        return "not_compared"
    ordered = sorted(titles)
    if any(
        not _compatible(title, prior)
        for index, title in enumerate(ordered)
        for prior in ordered[:index]
    ):
        return "reports_differ"
    return "no_material_difference"


def representatives_in_display_order(rows, rights=None, *, comparison=None):
    """Use quality within compatible reporting; keep material updates visible.

    A stable group can contain opposing facts after one source revises its item.
    Source prestige cannot decide that disagreement. Fall back to current
    journal order until reporting converges. This does not adjudicate truth.
    """
    rows = list(rows)
    comparison = comparison or reporting_state(rows, rights)
    if comparison in {"reports_differ", "comparison_limited"}:
        return sorted(
            rows,
            key=lambda row: (
                int(row["last_sequence"] or 0),
                str(row["source"]), str(row["source_item_id"]),
            ),
            reverse=True,
        )
    return sorted(rows, key=lambda row: representative_key(row, rights), reverse=True)

def curated_source(source: str) -> bool:
    """Only implemented publisher-preserving transports may enter this view."""
    key = str(source or "").strip().lower()
    if key != "benzinga" and not key.startswith("massive:"):
        return False
    return publisher_category(publisher_identity(key)) in {"reporting", "press_release"}


def curated_report(source: str, title: str) -> bool:
    return curated_source(source) and ticker_editorial_reason(
        display_text(title), publisher_identity(source),
    ) is None


def register_curated_reader(connection) -> None:
    """Pure SELECT predicate, evaluated before grouping and page limits."""
    connection.create_function("qbus_news_is_curated", 2, curated_report, deterministic=True)
