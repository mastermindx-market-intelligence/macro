"""Bounded Tiingo news observations for the existing News Intelligence/qbus owner.

No scheduler, archive, identity master, signal or rights authority is created here.
Tiingo publishedDate can be a publisher date OR Tiingo's discovery fallback. Our
receipt is independent of both provider clocks; no historical availability is
inferred from a present-day download. See https://www.tiingo.com/documentation/news.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import json
import re
from time import monotonic
from typing import Callable, Mapping
from urllib.parse import urlsplit

ENDPOINT = "https://api.tiingo.com/tiingo/news"
MAX_LIMIT = 1000
MAX_TITLE = 4096
MAX_DESCRIPTION = 16384
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
PUBLICATION_TIME_BASIS = "publisher_or_tiingo_discovery_fallback"


class TiingoArticleError(ValueError):
    """Stable refusal code; never include a payload, request or credential."""


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise TiingoArticleError(f"{field}_missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        raise TiingoArticleError(f"{field}_invalid") from None


def _received(value: object) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise TiingoArticleError("received_at_invalid")
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise TiingoArticleError("received_at_invalid") from None


def _bounded_text(value: object, field: str, limit: int, *, required: bool = False) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise TiingoArticleError(f"{field}_invalid")
    text = value.strip()
    if (required and not text) or len(text) > limit or "\x00" in text:
        raise TiingoArticleError(f"{field}_invalid")
    return text


def normalize_article(raw: Mapping[str, object], *, received_at: datetime) -> dict:
    """Validate an observation, not a publisher fact or a canonical ticker identity."""
    if not isinstance(raw, Mapping):
        raise TiingoArticleError("article_invalid")
    received = _received(received_at)
    article_id = raw.get("id")
    if isinstance(article_id, bool) or not isinstance(article_id, int) or article_id < 1:
        raise TiingoArticleError("id_invalid")
    title = _bounded_text(raw.get("title"), "title", MAX_TITLE, required=True)
    url = _bounded_text(raw.get("url"), "url", 8192, required=True)
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().removeprefix("www.")
        port = parts.port
    except ValueError:
        raise TiingoArticleError("url_invalid") from None
    if (parts.scheme not in ("http", "https") or not host or parts.username
            or parts.password or port not in (None, 80, 443)
            or any(ord(ch) < 32 or ord(ch) in (34, 39, 60, 62, 92, 127) for ch in url)):
        raise TiingoArticleError("url_invalid")
    published = _utc(raw.get("publishedDate"), "published_at")
    crawled = _utc(raw.get("crawlDate"), "provider_crawled_at")
    if published > received or crawled > received:
        raise TiingoArticleError("clock_after_receipt")
    if (published - crawled).total_seconds() > 300:
        raise TiingoArticleError("publisher_clock_future")
    source = _bounded_text(raw.get("source"), "source", 253) or host
    if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?", source) or ".." in source:
        raise TiingoArticleError("source_invalid")
    source = source.lower().removeprefix("www.")
    if host != source and not host.endswith("." + source):
        raise TiingoArticleError("source_url_mismatch")

    def tags(field: str) -> list[str]:
        values = raw.get(field)
        if values is None:
            values = []
        if not isinstance(values, list) or len(values) > 512:
            raise TiingoArticleError(f"{field}_invalid")
        out = []
        for value in values:
            token = _bounded_text(value, field, 128)
            if token and token not in out:
                out.append(token)
        return out

    return {
        "provider": "tiingo", "provider_id": article_id,
        "title": title, "url": url, "source": source,
        "description": _bounded_text(raw.get("description"), "description", MAX_DESCRIPTION),
        "tickers": tags("tickers"), "tags": tags("tags"),
        "published_at": published.isoformat(),
        "publication_time_basis": PUBLICATION_TIME_BASIS,
        "provider_crawled_at": crawled.isoformat(),
        "received_at": received.isoformat(),
        "available_at": received.isoformat(),
        # Compatibility aliases: observation time/age, not verified first-seen history.
        "first_available_at": received.isoformat(),
        "is_historical_backfill": (received - crawled).total_seconds() > 3600,
        "delayed_observation": (received - crawled).total_seconds() > 3600,
        "publication_crawl_delay_seconds": (crawled - published).total_seconds(),
    }


def resolve_ticker_candidates(tags: list[str], universe: Mapping[str, object]) -> dict:
    """Route unique matches to the incumbent entity-map's exact ticker keys.

    Lower-case Tiingo tags are not Massive case-sensitive identities. Do not
    upper-case a tag into a new security or choose between TPC and TpC. This is
    display routing, not a dated Data OS identity grant.
    """
    index: dict[str, set[str]] = {}
    for key in universe:
        if isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]{0,15}", key):
            index.setdefault(key.replace(".", "-").casefold(), set()).add(key)
    resolved: set[str] = set()
    unknown, ambiguous = [], []
    for tag in tags:
        matches = index.get(tag.replace(".", "-").casefold(), set())
        if len(matches) == 1:
            resolved.update(matches)
        elif matches:
            ambiguous.append(tag)
        else:
            unknown.append(tag)
    return {"tickers": sorted(resolved), "unresolved": unknown, "ambiguous": ambiguous}


def fetch_articles(token: str, *, limit: int = 250,
                   get: Callable | None = None) -> tuple[list[dict], str]:
    """One fixed-origin bounded snapshot. No redirects, retries or completeness claim."""
    if not isinstance(token, str) or not token.strip():
        return [], "no_key"
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        return [], "invalid_limit"
    response = None
    started = monotonic()
    try:
        if get is None:
            import requests
            get = requests.get
        response = get(
            ENDPOINT, params={"sortBy": "crawlDate", "limit": limit},
            headers={"Accept": "application/json", "Authorization": "Token " + token.strip()},
            timeout=(5, 15), allow_redirects=False, stream=True,
        )
        if response.status_code != 200:
            return [], f"http_{int(response.status_code)}"
        media = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media not in ("application/json", "text/json"):
            return [], "invalid_content_type"
        chunks = []
        size = 0
        for chunk in response.iter_content(chunk_size=65536):
            size += len(chunk)
            if size > MAX_RESPONSE_BYTES:
                return [], "response_too_large"
            if monotonic() - started > 20:
                return [], "response_deadline"
            chunks.append(chunk)
        body = json.loads(b"".join(chunks))
        if not isinstance(body, list) or len(body) > limit:
            return [], "invalid_response"
        return body, "ok" if body else "no_rows"
    except Exception:
        return [], "request_failed"
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass


def audit_sample(rows: list[object], *, received_at: datetime) -> dict:
    """Aggregate only: field quality and concentration, not editorial accuracy."""
    _received(received_at)
    reasons: Counter[str] = Counter()
    kept = []
    for raw in rows:
        try:
            kept.append(normalize_article(raw, received_at=received_at))
        except TiingoArticleError as exc:
            reasons[str(exc)] += 1
    sources = Counter(x["source"] for x in kept)
    lag = sorted(x["publication_crawl_delay_seconds"] / 60 for x in kept)

    def quantile(q: float) -> float | None:
        return round(lag[int((len(lag) - 1) * q)], 1) if lag else None

    return {
        "sample_rows": len(rows), "valid_rows": len(kept),
        "invalid_reasons": dict(reasons),
        "unique_ids": len({x["provider_id"] for x in kept}),
        "unique_titles": len({x["title"].casefold() for x in kept}),
        "ticker_tag_rate": round(sum(bool(x["tickers"]) for x in kept) / len(kept), 4) if kept else None,
        "description_rate": round(sum(bool(x["description"]) for x in kept) / len(kept), 4) if kept else None,
        "source_count": len(sources),
        "top_three_source_share": round(sum(v for _, v in sources.most_common(3)) / len(kept), 4) if kept else None,
        "crawl_delay_minutes_p50": quantile(.5),
        "crawl_delay_minutes_p90": quantile(.9),
        "backfill_count": sum(x["delayed_observation"] for x in kept),
        "reported_publication_to_crawl_minutes_p50": quantile(.5),
        "reported_publication_to_crawl_minutes_p90": quantile(.9),
        "publication_time_basis": PUBLICATION_TIME_BASIS,
        "delayed_observation_count": sum(x["delayed_observation"] for x in kept),
        "editorial_accuracy": "not_measured", "entity_precision": "not_measured",
        "historical_completeness": "not_measured",
    }
