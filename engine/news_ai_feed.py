"""AI-native news feed connector — OPTIONAL, key-gated, degrade-safe.

The newer generation of financial-news APIs run an LLM over each article and
return precomputed per-article sentiment and sometimes explicit importance.
Sentiment confidence and company relevance are NOT importance measurements. This connector pulls that stream and normalises it into the
suite's standard display-headline shape, carrying the vendor's AI fields through
as ``ai_sentiment`` / ``ai_importance`` so the deterministic display ranker
(``news_common.rank_score``) can use them as INPUTS.

CONTRACT (house law):
  • DISPLAY-ONLY. Nothing here is ever a trade signal — the AI fields reshape
    display order only, exactly like the deterministic importance score. The
    news→score firewall is untouched.
  • KEY-GATED + DEGRADE-SAFE. With no key (or disabled), ``fetch()`` returns []
    and the whole news pipeline is byte-identical to the keyless build. It never
    raises into the build.
  • Default Finlight uses its documented POST /v2/articles contract; custom
    providers retain the legacy GET transport. Entity enrichment requires the
    appropriate vendor entitlement; this module never activates or buys it.
  • Missing publication times stay missing; receipt, indexing and revision
    clocks are separate. Only explicit importance can affect display order.

Default OFF. To light it up: set ``news_ai_feed.enabled: true`` in config and
export the API key (env ``FINLIGHT_KEY`` by default).
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from urllib.parse import urlparse

from lib import config
from engine import news_common as nc
from engine.ticker_shape import valid_us_ticker

log = logging.getLogger(__name__)

_DEFAULT_BASE = "https://api.finlight.me"
_TIMEOUT = 20

# int source-tier → the string tier the display ranker / aging cutoff key on.
_TIER_STR = {1: "tier1", 2: "quality", 3: "quality"}


def _cfg() -> dict:
    try:
        return config.load().get("news_ai_feed", {}) or {}
    except Exception:  # noqa: BLE001
        return {}


def _key(cfg: dict) -> str | None:
    return config.secret(cfg.get("api_key_env", "FINLIGHT_KEY"))


def enabled() -> bool:
    """True only when explicitly enabled AND a key resolves. Reads cfg + env."""
    cfg = _cfg()
    return bool(cfg.get("enabled", False)) and bool(_key(cfg))


def provider_label() -> str:
    return (_cfg().get("provider") or "finlight") if enabled() else ""


# --------------------------------------------------------------------------- #
# field extraction — tolerant of vendor field-name variants
# --------------------------------------------------------------------------- #
def _first(*vals):
    for v in vals:
        if v not in (None, "", []):
            return v
    return None


def _domain(url: str, source_name: str) -> str:
    try:
        host = urlparse(url or "").netloc.lower()
    except Exception:  # noqa: BLE001
        host = ""
    if host.startswith("www."):
        host = host[4:]
    return host or (source_name or "").lower().replace(" ", "")


def _text(value) -> str:
    """Only source strings are text; malformed objects are never stringified."""
    return value.strip() if isinstance(value, str) else ""


def _finite_number(value, *, upper: float) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and 0.0 <= number <= upper else None


def _iso(v, now: datetime) -> str:
    """Parse a source clock, NEVER replace an absent/bad one with receipt time.

    ``now`` is retained for callers using the old helper signature.
    """
    del now
    if v is None or v == "" or isinstance(v, bool):
        return ""
    try:
        if isinstance(v, (int, float)):
            stamp = float(v)
            if not math.isfinite(stamp):
                return ""
            stamp = stamp / 1000.0 if stamp > 1e12 else stamp
            return datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat()
        if not isinstance(v, str):
            return ""
        dt = datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


# Vendor listing labels only, not a new issuer/security identity map. Unknown
# venues are excluded WITH COUNT; company domicile is not a listing market.
_US_VENUES = frozenset({
    "XNAS", "XNYS", "XASE", "ARCX", "BATS", "NASDAQ", "NYSE", "AMEX",
    "NYSE ARCA", "NYSE AMERICAN", "NASDAQ GLOBAL SELECT MARKET",
    "NASDAQ GLOBAL MARKET", "NASDAQ CAPITAL MARKET",
})


def _ticker_fields(art: dict) -> tuple[list[str], int]:
    candidates = []
    excluded = 0
    raw = _first(art.get("tickers"), art.get("symbols"), art.get("entities"))
    if isinstance(raw, list):
        for value in raw:
            if isinstance(value, dict):
                value = _first(value.get("ticker"), value.get("symbol"), value.get("code"))
            candidates.append(value)
    elif raw is not None:
        excluded += 1

    companies = art.get("companies")
    if isinstance(companies, list):
        for company in companies:
            if not isinstance(company, dict):
                excluded += 1
                continue
            ticker = company.get("ticker")
            venue = _text(company.get("exchange")).upper()
            listing_country = ""
            primary = company.get("primaryListing")
            if not ticker and isinstance(primary, dict):
                ticker = primary.get("ticker")
                venue = _text(primary.get("exchangeCode")).upper()
                listing_country = _text(primary.get("exchangeCountry")).upper()
            if venue not in _US_VENUES or listing_country not in ("", "US"):
                excluded += 1
                continue
            candidates.append(ticker)
    elif companies is not None:
        excluded += 1

    valid: set[str] = set()
    for value in candidates:
        symbol = valid_us_ticker(value) if isinstance(value, str) else None
        if symbol is None:
            excluded += 1
        else:
            valid.add(symbol.upper())
    ordered = sorted(valid)
    excluded += max(0, len(ordered) - 8)
    return ordered[:8], excluded


def _tickers(art: dict) -> list[str]:
    return _ticker_fields(art)[0]


def _ai_importance(art: dict):
    """Only explicit importance → 0-100; confidence/relevance are different axes."""
    value = _finite_number(
        _first(art.get("importance"), art.get("importanceScore")), upper=100.0,
    )
    if value is None:
        return None
    return round(value * 100.0 if value <= 1.0 else value, 1)


def _ai_sentiment(art: dict):
    value = _first(art.get("sentiment"), art.get("sentimentLabel"), art.get("sentiment_score"))
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number) or not -1.0 <= number <= 1.0:
            return None
        return "pos" if number > 0.1 else "neg" if number < -0.1 else "neutral"
    return {
        "positive": "pos", "pos": "pos", "bullish": "pos",
        "negative": "neg", "neg": "neg", "bearish": "neg", "neutral": "neutral",
    }.get(_text(value).lower())


def _normalise_ai(art: dict, now: datetime) -> dict | None:
    title = _text(_first(art.get("title"), art.get("headline")))
    if not title:
        return None
    url = _text(_first(art.get("link"), art.get("url"), art.get("articleUrl")))
    source_name = _text(_first(art.get("source"), art.get("publisher"), art.get("domain")))
    domain = _domain(url, source_name)
    if nc.is_blocked(domain) or nc.low_value_reason(title, domain):
        return None
    publication = _first(art.get("publishDate"), art.get("published_at"),
                         art.get("publishedAt"), art.get("datetime"), art.get("date"))
    seendate = _iso(publication, now)
    timestamp_quality = "PUBLISHER_STATED" if seendate else (
        "CRAWL_BOUNDED" if publication is None else "CORRUPTED"
    )
    summary = _text(_first(art.get("summary"), art.get("description"), art.get("content")))[:400]
    tickers, ticker_exclusions = _ticker_fields(art)
    tier = nc.source_tier(domain) or 3     # AI-curated → tier-3 floor so it survives
    ai_sent = _ai_sentiment(art)
    out = {
        "title": title, "url": url, "domain": domain,
        "source": source_name or domain, "source_name": source_name or domain,
        "seendate": seendate, "summary": summary,
        "tickers": tickers, "sentiment": ai_sent, "tier": tier,
        "ai_ticker_exclusions": ticker_exclusions,
        "timestamp_quality": timestamp_quality,
        "_crawled_at": now.isoformat(),
        "provider_indexed_at": _iso(art.get("createdAt"), now) or None,
        "source_revised_at": _iso(art.get("revisedDate"), now) or None,
        "source_tier": _TIER_STR.get(tier, "quality"),
        "quality": nc.quality_score(title, domain, seendate, relevance=1.0, now=now, tier=tier),
        "provider": "ai_feed",
        "ai_sentiment": ai_sent, "ai_importance": _ai_importance(art),
        "ai_sentiment_confidence": _finite_number(art.get("confidence"), upper=1.0),
        "_id": nc.event_id(title, domain),
    }
    try:                                   # event identity feeds the display ranker
        from engine import news_events as _ne
        out["event"] = _ne.classify_event(title, summary)
    except Exception:  # noqa: BLE001 — display-only; never raises
        out["event"] = None
    return out


def fetch(now: datetime | None = None, limit: int | None = None) -> list[dict]:
    """Pull the AI feed and return normalised display-headline dicts (each carrying
    ``ai_sentiment`` / ``ai_importance``). Returns [] when disabled / keyless / on
    ANY error. NEVER raises into the build."""
    cfg = _cfg()
    if not cfg.get("enabled", False):
        return []
    key = _key(cfg)
    if not key:
        return []
    now = now or datetime.now(timezone.utc)
    base = (cfg.get("base_url") or _DEFAULT_BASE).rstrip("/")
    try:
        limit = int(limit if limit is not None else cfg.get("max_articles", 50))
    except (TypeError, ValueError, OverflowError):
        limit = 50
    limit = max(1, min(100, limit))
    query = cfg.get("query", "stock market OR earnings OR Federal Reserve OR US economy")
    try:
        import requests
    except Exception:  # noqa: BLE001
        return []
    try:
        params = {"query": query, "pageSize": limit, "language": "en"}
        headers = {"X-API-KEY": key, "Accept": "application/json"}
        if str(cfg.get("provider") or "finlight").lower() == "finlight":
            # https://docs.finlight.me/en/v2/rest-endpoints/ — POST body,
            # not URL params. Requires the configured vendor entitlement.
            r = requests.post(
                f"{base}/v2/articles", json={**params, "includeEntities": True},
                headers=headers, timeout=_TIMEOUT,
            )
        else:
            r = requests.get(
                f"{base}/v2/articles", params=params, headers=headers, timeout=_TIMEOUT,
            )
        if r.status_code != 200:
            log.warning("news_ai_feed http %s", r.status_code)
            return []
        payload = r.json()
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.warning("news_ai_feed fetch failed (%s)", e)
        return []

    arts = payload.get("articles") if isinstance(payload, dict) else payload
    if not isinstance(arts, list):
        return []
    out: list[dict] = []
    for art in arts:
        if isinstance(art, dict):
            try:
                h = _normalise_ai(art, now)
            except (TypeError, ValueError, OverflowError, AttributeError):
                log.warning("news_ai_feed: skipped malformed article")
                continue
            if h:
                out.append(h)
    log.info("news_ai_feed: %d AI-scored items via %s", len(out), provider_label() or "?")
    return out
