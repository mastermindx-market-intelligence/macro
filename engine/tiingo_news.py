"""Tiingo news REST observation adapter for the existing News Intelligence/qbus owner.

One bounded fetch, no scheduler, store, credentials on disk, or ranking authority.
Caller chooses source rights, publisher filtering, persistence and presentation.
In particular publication, provider crawl and our first receipt are three distinct
clocks: historical Tiingo backfill never becomes a prospective first observation.
"""
from __future__ import annotations

from collections import Counter
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit
from typing import Callable, Mapping

ENDPOINT = "https://api.tiingo.com/tiingo/news"
MAX_LIMIT = 1000
MAX_TITLE = 4096
MAX_DESCRIPTION = 16384


class TiingoArticleError(ValueError):
    """Stable refusal code; provider payloads and credentials are never logged."""


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise TiingoArticleError(f"{field}_missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("timezone")
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        raise TiingoArticleError(f"{field}_invalid") from None


def _bounded_text(value: object, field: str, limit: int, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise TiingoArticleError(f"{field}_invalid")
    text = value.strip()
    if (required and not text) or len(text) > limit:
        raise TiingoArticleError(f"{field}_invalid")
    return text


def normalize_article(raw: Mapping[str, object], *, received_at: datetime) -> dict:
    """Pure validated observation. Does not certify Tiingo tags or publisher facts."""
    if not isinstance(raw, Mapping):
        raise TiingoArticleError("article_invalid")
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise TiingoArticleError("received_at_invalid")
    received = received_at.astimezone(timezone.utc)
    article_id = raw.get("id")
    if isinstance(article_id, bool) or not isinstance(article_id, int) or article_id < 1:
        raise TiingoArticleError("id_invalid")
    title = _bounded_text(raw.get("title"), "title", MAX_TITLE, required=True)
    url = _bounded_text(raw.get("url"), "url", 8192, required=True)
    parts = urlsplit(url)
    if (parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password
            or any(c in url for c in ("\\\"", "\x27", "<", ">", "\\x00", "\\n", "\\r", "\\t"))):
        raise TiingoArticleError("url_invalid")
    published = _utc(raw.get("publishedDate"), "published_at")
    crawled = _utc(raw.get("crawlDate"), "provider_crawled_at")
    if published > crawled.replace(microsecond=0) and (published - crawled).total_seconds() > 300:
        raise TiingoArticleError("publisher_clock_future")
    # The provider's old crawl clock proves neither OUR access nor our receipt.
    # For live / backfilled rows, our receipt is the conservative availability clock.
    available_at = max(received, crawled)
    source = _bounded_text(raw.get("source"), "source", 512) or parts.hostname.lower()
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", source) or ".." in source:
        raise TiingoArticleError("source_invalid")
    # Do not score a low-quality URL using a different, prestigious source tag.
    # A live 100-row sample had matching source and URL hosts throughout; future
    # mismatches are quarantined for manual review, not silently tier-boosted.
    url_host = parts.hostname.lower().removeprefix("www.")
    source_host = source.lower().removeprefix("www.")
    if url_host != source_host and not url_host.endswith("." + source_host):
        raise TiingoArticleError("source_url_mismatch")
    def tags(field: str) -> list[str]:
        v = raw.get(field) or []
        if not isinstance(v, list) or len(v) > 512:
            raise TiingoArticleError(f"{field}_invalid")
        out = []
        for value in v:
            token = _bounded_text(value, field, 128)
            if token and token not in out:
                out.append(token)
        return out
    return {
        "provider": "tiingo",
        "provider_id": article_id,
        "title": title,
        "url": url,
        "source": source.lower().removeprefix("www."),
        "description": _bounded_text(raw.get("description"), "description", MAX_DESCRIPTION),
        "tickers": tags("tickers"),
        "tags": tags("tags"),
        "published_at": published.isoformat(),
        "provider_crawled_at": crawled.isoformat(),
        "received_at": received.isoformat(),
        "first_available_at": available_at.isoformat(),
        "is_historical_backfill": (received - crawled).total_seconds() > 3600,
        "publication_crawl_delay_seconds": (crawled - published).total_seconds(),
    }


def fetch_articles(token: str, *, limit: int = 250,
                   get: Callable | None = None) -> tuple[list[dict], str]:
    """Bounded newest-crawl fetch. No pagination side effects or retry loop."""
    if not isinstance(token, str) or not token.strip():
        return [], "no_key"
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        return [], "invalid_limit"
    try:
        if get is None:
            import requests
            get = requests.get
        response = get(
            ENDPOINT,
            params={"sortBy": "crawlDate", "limit": limit},
            headers={"Accept": "application/json", "Authorization": "Token " + token},
            timeout=20,
        )
        if response.status_code != 200:
            return [], f"http_{int(response.status_code)}"
        body = response.json()
        if not isinstance(body, list):
            return [], "invalid_response"
        return body[:limit], "ok" if body else "no_rows"
    except Exception:  # Never log exception details: upstream clients may include Authorization.
        return [], "request_failed"


def audit_sample(rows: list[object], *, received_at: datetime) -> dict:
    """Aggregate data-quality diagnostics; no article text or credentials returned.

    This measures the supplied slice ONLY. No editorial truth or asset-tag
    precision is asserted. Quantiles are empirical and not long-run SLAs.
    """
    reasons: Counter[str] = Counter()
    kept: list[dict] = []
    for raw in rows:
        try:
            kept.append(normalize_article(raw, received_at=received_at))
        except TiingoArticleError as exc:
            reasons[str(exc)] += 1
    sources = Counter(x["source"] for x in kept)
    ids = {x["provider_id"] for x in kept}
    titles = {x["title"].casefold() for x in kept}
    lag = sorted(x["publication_crawl_delay_seconds"] / 60 for x in kept)
    def quantile(q: float) -> float | None:
        return round(lag[int((len(lag) - 1) * q)], 1) if lag else None
    return {
        "sample_rows": len(rows),
        "valid_rows": len(kept),
        "invalid_reasons": dict(reasons),
        "unique_ids": len(ids),
        "unique_titles": len(titles),
        "ticker_tag_rate": round(sum(bool(x["tickers"]) for x in kept) / len(kept), 4) if kept else None,
        "description_rate": round(sum(bool(x["description"]) for x in kept) / len(kept), 4) if kept else None,
        "source_count": len(sources),
        "top_three_source_share": round(sum(v for _, v in sources.most_common(3)) / len(kept), 4) if kept else None,
        "crawl_delay_minutes_p50": quantile(0.50),
        "crawl_delay_minutes_p90": quantile(0.90),
        "backfill_count": sum(x["is_historical_backfill"] for x in kept),
    }
