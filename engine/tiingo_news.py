"""Bounded Tiingo news observations for the existing News Intelligence/qbus owner.

No scheduler, archive, identity master, signal or rights authority is created here.
Tiingo publishedDate can be a publisher date OR Tiingo's discovery fallback. Our
receipt is independent of both provider clocks; no historical availability is
inferred from a present-day download. See https://www.tiingo.com/documentation/news.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timezone
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


def _ticker_lookup_index(universe: Mapping[str, object]) -> dict[str, set[str]]:
    """Pure candidate lookup; duplicate folded spellings remain ambiguous."""
    index: dict[str, set[str]] = {}
    for key in universe:
        if isinstance(key, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9.-]{0,15}", key):
            index.setdefault(key.replace(".", "-").casefold(), set()).add(key)
    return index


def _resolve_ticker_tags(tags: list[str], index: Mapping[str, set[str]]) -> dict:
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


def resolve_ticker_candidates(tags: list[str], universe: Mapping[str, object]) -> dict:
    """Route unique matches to the incumbent entity-map's exact ticker keys.

    Lower-case Tiingo tags are not Massive case-sensitive identities. Do not
    upper-case a tag into a new security or choose between TPC and TpC. This is
    display routing, not a dated Data OS identity grant.
    """
    return _resolve_ticker_tags(tags, _ticker_lookup_index(universe))


def audit_ticker_coverage(
    rows: list[object], universe: Mapping[str, object], *, received_at: datetime
) -> dict:
    """Aggregate-only QA against caller-supplied existing ticker keys.

    The result documents potential *display routing*, not security-identity
    admission, event entry, tag precision or an authorized publisher decision.
    No provider title, raw ticker value, source URL or identifier is returned.
    """
    when = _received(received_at)
    if not isinstance(universe, Mapping):
        raise ValueError("ticker_universe_invalid")
    # One index per sample, not one regex/folding pass across the universe
    # for every article (large research universes can contain 10k+ keys).
    index = _ticker_lookup_index(universe)
    valid = tagged = matched = ambiguous = unresolved = stranded_case = 0
    all_matched: set[str] = set()
    for row in rows:
        try:
            item = normalize_article(row, received_at=when)
        except TiingoArticleError:
            continue
        valid += 1
        tokens = item["tickers"]
        if not tokens:
            continue
        tagged += 1
        resolved = _resolve_ticker_tags(tokens, index)
        unique = resolved["tickers"]
        if unique:
            matched += 1
            all_matched.update(unique)
            # A headline with both exact-case AAPL and lower-case mu still
            # strands MU in today's per-ticker index. Count any unmatched
            # canonical symbol, not just rows with zero exact tags.
            vendor_index_keys = {token.replace(".", "-") for token in tokens}
            if any(symbol not in vendor_index_keys for symbol in unique):
                stranded_case += 1
        if resolved["ambiguous"]:
            ambiguous += 1
        if resolved["unresolved"]:
            unresolved += 1
    return {
        "sample_rows": len(rows),
        "valid_rows": valid,
        "ticker_tagged_rows": tagged,
        "unique_canonical_match_rows": matched,
        "ambiguous_ticker_rows": ambiguous,
        "unresolved_ticker_rows": unresolved,
        "matched_canonical_symbol_count": len(all_matched),
        "case_stranded_matched_rows": stranded_case,
        "no_unique_match_rows": tagged - matched,
        "diagnostic_basis": "caller_universe_display_candidate_not_identity_grant",
    }


def audit_requested_publication_window(
    rows: list[object], *, start_date: date, end_date: date, received_at: datetime
) -> dict:
    """Refuse a false historical date-window qualification from a 200 response.

    This pure reader guards only the vendor publishedDate envelope. Tiingo may
    substitute discovery time for publishedDate; even all in-window rows prove
    neither first availability, licensed history, completeness nor corrections.
    No story content, IDs, source URLs or credentials appear in the receipt.
    """
    when = _received(received_at)
    if (type(rows) is not list or type(start_date) is not date
            or type(end_date) is not date or start_date > end_date):
        raise ValueError("publication_window_invalid")
    good = bad = before = after = 0
    for raw in rows:
        try:
            item = normalize_article(raw, received_at=when)
        except TiingoArticleError:
            bad += 1
            continue
        published_date = date.fromisoformat(item["published_at"][:10])
        if published_date < start_date:
            before += 1
        elif published_date > end_date:
            after += 1
        else:
            good += 1
    if before or after:
        status = "publication_dates_outside_requested_window"
    elif bad:
        status = "malformed_vendor_row"
    elif not rows:
        status = "empty_response"
    else:
        status = "published_date_window_observed"
    return {
        "sample_rows": len(rows),
        "within_window_rows": good,
        "before_window_rows": before,
        "after_window_rows": after,
        "invalid_rows": bad,
        "window_status": status,
        "no_out_of_window_or_malformed_rows": bool(good and not (bad or before or after)),
        "historical_availability": "not_proven",
        "publication_clock_basis": PUBLICATION_TIME_BASIS,
        "only_validates_requested_publication_date_bounds": True,
    }


def fetch_articles(token: str, *, limit: int = 250,
                   only_with_tickers: bool = True,
                   get: Callable | None = None) -> tuple[list[dict], str]:
    """One fixed-origin bounded snapshot, tagged-only by default.

    The published consumer already discards untagged articles. Server-side
    filtering prevents untagged publisher concentration from exhausting the
    250-row window. Explicit False remains available for quality sampling.
    This is not a completeness, editorial-accuracy or ticker-identity claim.
    """
    if not isinstance(token, str) or not token.strip():
        return [], "no_key"
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        return [], "invalid_limit"
    if type(only_with_tickers) is not bool:
        return [], "invalid_ticker_filter"
    params = {"sortBy": "crawlDate", "limit": limit}
    if only_with_tickers:
        params["onlyWithTickers"] = "true"
    response = None
    started = monotonic()
    try:
        if get is None:
            import requests
            get = requests.get
        response = get(
            ENDPOINT, params=params,
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
    receipt_time = _received(received_at)
    reasons: Counter[str] = Counter()
    kept = []
    for raw in rows:
        try:
            kept.append(normalize_article(raw, received_at=receipt_time))
        except TiingoArticleError as exc:
            reasons[str(exc)] += 1
    sources = Counter(x["source"] for x in kept)
    lag = sorted(x["publication_crawl_delay_seconds"] / 60 for x in kept)
    # Provider crawl -> our independent observation is *apparent age*, not an
    # upstream publication SLA or proof that the article was historically seen.
    observed_age = sorted(
        (receipt_time - datetime.fromisoformat(x["provider_crawled_at"])).total_seconds() / 60
        for x in kept
    )
    ids = Counter(x["provider_id"] for x in kept)
    urls = Counter(x["url"].split("#", 1)[0] for x in kept)

    def quantile(values: list[float], q: float) -> float | None:
        return round(values[int((len(values) - 1) * q)], 1) if values else None

    return {
        "sample_rows": len(rows), "valid_rows": len(kept),
        "invalid_reasons": dict(reasons),
        "unique_ids": len({x["provider_id"] for x in kept}),
        "unique_titles": len({x["title"].casefold() for x in kept}),
        "ticker_tag_rate": round(sum(bool(x["tickers"]) for x in kept) / len(kept), 4) if kept else None,
        "description_rate": round(sum(bool(x["description"]) for x in kept) / len(kept), 4) if kept else None,
        "source_count": len(sources),
        "top_three_source_share": round(sum(v for _, v in sources.most_common(3)) / len(kept), 4) if kept else None,
        "crawl_delay_minutes_p50": quantile(lag, .5),
        "crawl_delay_minutes_p90": quantile(lag, .9),
        # Distinct arrival-clock axis. This describes only this retrieved slice.
        "provider_crawl_to_observation_minutes_p50": quantile(observed_age, .5),
        "provider_crawl_to_observation_minutes_p90": quantile(observed_age, .9),
        "observed_within_60m_of_provider_crawl_share": (
            round(sum(age <= 60 for age in observed_age) / len(observed_age), 4)
            if observed_age else None
        ),
        "duplicate_provider_id_rows": sum(n - 1 for n in ids.values()),
        "duplicate_url_rows": sum(n - 1 for n in urls.values()),
        "largest_source_share": round(max(sources.values()) / len(kept), 4) if kept else None,
        "apparent_age_scope": "one_observation_slice_not_provider_sla",
        "backfill_count": sum(x["delayed_observation"] for x in kept),
        "reported_publication_to_crawl_minutes_p50": quantile(lag, .5),
        "reported_publication_to_crawl_minutes_p90": quantile(lag, .9),
        "publication_time_basis": PUBLICATION_TIME_BASIS,
        "delayed_observation_count": sum(x["delayed_observation"] for x in kept),
        "editorial_accuracy": "not_measured", "entity_precision": "not_measured",
        "historical_completeness": "not_measured",
    }
