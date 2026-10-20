"""Audience projection helpers; ranking policy remains in news_common/qkernel.

No network, model call, source admission or storage authority lives here. A
representative is selected only after the caller has applied current source rights.
Feed chronology remains the store change sequence, independent of this choice.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlsplit

from engine.news_common import low_value_reason, quality_score, source_tier, ticker_template_reason

_RANK_CLOCK = datetime(2000, 1, 1, tzinfo=timezone.utc)


def display_text(value: object) -> str:
    """Decode vendor HTML entities as plain text; consumers must escape rendering."""
    return unescape(str(value or ""))


def publisher_identity(source: str, url: str = "") -> str:
    # Transport-scoped grants remain distinct even when the publisher is the same.
    if source == "benzinga":
        return "benzinga.com"
    if source.startswith("massive:"):
        return source.partition(":")[2]
    try:
        host = (urlsplit(url).hostname or "").lower()
    except ValueError:
        host = ""
    return host.removeprefix("www.") or source


def story_quality(*, title: str, url: str, source: str) -> tuple[int, str | None]:
    title = display_text(title)
    domain = publisher_identity(source, url)
    # Unknown ticker-tagged publishers get the existing conservative wire tier.
    # Use a fixed, equal age so a later rewrite cannot win on arrival recency.
    score = quality_score(
        title, domain, _RANK_CLOCK.isoformat(), now=_RANK_CLOCK,
        tier=source_tier(domain) or 3,
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
