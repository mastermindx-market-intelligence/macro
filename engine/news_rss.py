"""Keyless RSS / Atom news collector — top-tier free wires & quality press.

The provider news APIs we already use (Polygon, Finnhub) only return their
*licensed aggregators* — Benzinga, Zacks, Motley Fool, Investing.com — never the
wires. That capped the whole feed at low-quality, clickbait-prone sources.

But every major outlet publishes a FREE, keyless RSS/Atom feed: WSJ, Bloomberg,
FT, CNBC, Fox Business, MarketWatch, Axios, The Guardian, BBC, NPR. And **Google
News RSS** aggregates *everyone* — Reuters, AP, and the rest — for any topic or
ticker query, carrying the real outlet in a `<source>` element so we can tier it.

This module pulls those, normalising each item into the same headline dict the
rest of the news suite consumes — {title, url, domain, source, seendate(ISO),
summary} — tagged with the article's real source DOMAIN so news_common.source_tier
ranks it tier-1/2 (above the aggregator floor). Google-News results are filtered
to allowlisted tiers, so a query for "Federal Reserve" keeps the Reuters/WSJ/AP
hits and drops the SEO blogs.

Keyless · cached · bounded-concurrency · degrade-NEVER-raise. Nothing here is a
scoring input; it only supplies higher-quality headlines to the display feeds.
"""
from __future__ import annotations

import concurrent.futures as cf
import logging
import re
import xml.etree.ElementTree as ET
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse

from engine import news_common as nc

# Per-call reject collector — set to a fresh list by the caller (build_news) to
# capture every dropped headline with its reason; None between builds.
_reject_collector: ContextVar[list | None] = ContextVar("rss_reject_collector", default=None)

log = logging.getLogger(__name__)

_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) macro-dashboard/1.0 (+research)"
_TIMEOUT = 12
_MAX_WORKERS = 8

# --------------------------------------------------------------------------- #
# Curated direct feeds — (feed_url, source_domain, scope). source_domain is what
# news_common.source_tier ranks on (clean article URLs come straight from <link>).
# scope routes the feed: "macro" (Fed/econ/policy), "market" (broad equity tape).
# --------------------------------------------------------------------------- #
DIRECT_FEEDS: list[tuple[str, str, str]] = [
    # FINANCIAL SECTIONS ONLY — the broad "home"/general feeds (FT home, BBC, Axios,
    # NPR) flooded macro with politics/world/sports; their *financial* coverage instead
    # arrives, topic-targeted, through the Google-News queries below. WSJ's free RSS is
    # frozen at Jan-2025 (omitted); fresh WSJ also arrives via Google News.
    # market tape
    ("https://feeds.bloomberg.com/markets/news.rss", "bloomberg.com", "market"),
    ("https://www.cnbc.com/id/100003114/device/rss/rss.html", "cnbc.com", "market"),
    ("https://www.cnbc.com/id/15839069/device/rss/rss.html", "cnbc.com", "market"),
    ("https://moxie.foxbusiness.com/google-publisher/markets.xml", "foxbusiness.com", "market"),
    ("http://feeds.marketwatch.com/marketwatch/topstories/", "marketwatch.com", "market"),
    # Axios is all-topic (politics-heavy); its financial coverage is kept by the
    # market-title gate downstream. The Economist's finance feed is finance-only.
    ("https://www.axios.com/feeds/feed.rss", "axios.com", "market"),
    ("https://www.economist.com/finance-and-economics/rss.xml", "economist.com", "market"),
    # macro / economy
    ("https://feeds.bloomberg.com/economics/news.rss", "bloomberg.com", "macro"),
    ("https://www.cnbc.com/id/20910258/device/rss/rss.html", "cnbc.com", "macro"),
    ("https://moxie.foxbusiness.com/google-publisher/economy.xml", "foxbusiness.com", "macro"),
    ("https://www.theguardian.com/business/economics/rss", "theguardian.com", "macro"),
    # --- 2026 revamp: added corporate/market breadth. Any feed that 404s, moves,
    # or rate-limits is silently skipped by _fetch (degrade-safe); the downstream
    # theme / quality / clickbait gates keep only the on-topic, reputable items. ---
    ("https://finance.yahoo.com/news/rssindex", "finance.yahoo.com", "market"),
    ("https://seekingalpha.com/market_currents.xml", "seekingalpha.com", "market"),
    ("https://www.nasdaq.com/feed/rssoutbound?category=Markets", "nasdaq.com", "market"),
    ("http://feeds.marketwatch.com/marketwatch/marketpulse/", "marketwatch.com", "market"),
    ("https://www.cnbc.com/id/100727362/device/rss/rss.html", "cnbc.com", "market"),
    ("https://www.cnbc.com/id/10000664/device/rss/rss.html", "cnbc.com", "macro"),
]

# Google-News topic queries per scope — the primary WIRE channel (Reuters / AP / WSJ /
# FT / Bloomberg, filtered to tier≤thresh). Topic-targeted, so always financial.
GOOGLE_MACRO_QUERIES = [
    "Federal Reserve interest rate decision", "US inflation CPI PCE report",
    "US jobs report payrolls unemployment", "Treasury yields bond market",
    "US economy GDP growth", "Fed Powell monetary policy", "tariffs trade policy economy",
]
GOOGLE_MARKET_QUERIES = [
    "S&P 500 stock market today", "Wall Street stocks rally selloff",
    "stock market earnings results", "Nasdaq Dow Jones today",
    # Source-pinned wires whose own RSS is dead (Reuters) or not section-split (Axios)
    # — guarantee a baseline of their coverage. These return the outlet's GENERAL feed,
    # so _google_news tags them origin="feed" → gated on market relevance downstream
    # (drops their sports/world/caption items, keeps the market reporting). AP is NOT
    # source-pinned: its general wire is crime/world-heavy and the market gate's "drug"
    # (pharma) keyword lets narcotics stories through — AP still arrives, on-topic, via
    # the topic queries above (and via GDELT in the macro feed).
    'site:reuters.com (stocks OR "Wall Street" OR markets OR earnings OR "S&P 500" OR Fed OR economy)',
    'site:axios.com (markets OR business OR stocks OR economy OR Fed)',
]

_GNEWS = ("https://news.google.com/rss/search?q={q}+when:{d}d&hl=en-US&gl=US&ceid=US:en")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


# --------------------------------------------------------------------------- #
# fetch + parse
# --------------------------------------------------------------------------- #
def _fetch(url: str) -> bytes | None:
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return r.read()
    except Exception as e:  # noqa: BLE001 — degrade, never raise
        log.debug("rss fetch failed %s (%s)", url, e)
        return None


def _to_iso(pubdate: str) -> str:
    if not pubdate:
        return ""
    try:
        dt = parsedate_to_datetime(pubdate)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError, IndexError):
        return ""


def _clean(text: str | None) -> str:
    """Strip HTML tags + collapse whitespace from an RSS description/summary."""
    if not text:
        return ""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()


def _domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except (ValueError, AttributeError):
        return ""


def _child(item, *names):
    """First matching child text across namespaces (tag local-name match)."""
    for ch in item:
        if ch.tag.split("}")[-1] in names:
            return ch
    return None


def _parse(raw: bytes, source_domain: str | None, from_google: bool) -> list[dict]:
    """Parse RSS/Atom bytes into normalised headline dicts. Never raises."""
    out: list[dict] = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        log.debug("rss parse error (%s)", e)
        return out
    items = root.findall(".//item")
    atom = items or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for it in atom:
        title_el = _child(it, "title")
        title = _clean(title_el.text if title_el is not None else "")
        link_el = _child(it, "link")
        url = (link_el.text or link_el.get("href", "")) if link_el is not None else ""
        date_el = _child(it, "pubDate", "updated", "published", "date")
        seendate = _to_iso(date_el.text if date_el is not None else "")
        desc_el = _child(it, "description", "summary", "content")
        summary = _clean(desc_el.text if desc_el is not None else "")
        # Author/byline (dc:creator | author | creator). Atom nests <author><name>;
        # used to drop pick-mill columns (TipRanks/Zacks) a trusted outlet re-runs.
        auth_el = _child(it, "creator", "author")
        author = _clean(auth_el.text if auth_el is not None else "")
        if not author and auth_el is not None:
            name_el = _child(auth_el, "name")
            author = _clean(name_el.text if name_el is not None else "")

        if from_google:
            # title carries " - Source"; the <source> element holds the real outlet.
            src_el = _child(it, "source")
            src_name = (src_el.text or "").strip() if src_el is not None else ""
            src_url = src_el.get("url", "") if src_el is not None else ""
            domain = _domain_of(src_url) or _domain_of(url)
            if title and src_name and title.endswith(f" - {src_name}"):
                title = title[: -(len(src_name) + 3)].strip()
            summary = ""  # google-news descriptions are just a relink anchor
            source = src_name or domain
        else:
            domain = source_domain or _domain_of(url)
            source = domain
        if not title or not url:
            continue
        # Drop pick-mill / advertorial / advice junk at the source so it never reaches
        # any feed, count or per-ticker index (the only place a byline is available).
        _col = _reject_collector.get()
        if nc.is_blocked(domain):
            if _col is not None and len(_col) < 200:
                _col.append({"title": title, "domain": domain, "reason": "blocked_source"})
            continue
        _lv_reason = nc.low_value_reason(title, domain, author)
        if _lv_reason is not None:
            if _col is not None and len(_col) < 200:
                _col.append({"title": title, "domain": domain, "reason": _lv_reason})
            continue
        out.append({"title": title, "url": url, "domain": domain,
                    "source": source, "seendate": seendate, "summary": summary})
    return out


# --------------------------------------------------------------------------- #
# collectors
# --------------------------------------------------------------------------- #
def _google_news(query: str, window_days: int = 2, min_tier: int = 2) -> list[dict]:
    """Google-News RSS for a query, kept only where the real source is tier ≤ min_tier
    (1=wires, 2=incl. quality press). Drops the SEO/blog long tail."""
    raw = _fetch(_GNEWS.format(q=quote_plus(query), d=int(window_days)))
    if not raw:
        return []
    items = _parse(raw, None, from_google=True)
    # A topic query ("US jobs report") is relevant by construction. A SOURCE-pinned
    # query ("site:reuters.com …") is NOT: Google returns that outlet's general
    # coverage (sports/world/photo captions leak in), so its results must clear the
    # same relevance gate as a broad section feed — hence origin="feed".
    pinned = query.lower().lstrip().startswith("site:")
    origin = "feed" if pinned else "query"
    kept = []
    for a in items:
        t = nc.source_tier(a["domain"])
        if 0 < t <= min_tier:
            a["origin"] = origin
            kept.append(a)
    return kept


def _gather(tasks: list) -> list[dict]:
    """Run fetch+parse tasks concurrently (bounded). tasks = list of callables → list[dict]."""
    out: list[dict] = []
    if not tasks:
        return out
    with cf.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        for res in ex.map(lambda fn: fn(), tasks):
            if res:
                out.extend(res)
    return out


def _direct(scope: str) -> list[dict]:
    feeds = [(u, dom) for (u, dom, sc) in DIRECT_FEEDS if sc == scope or scope == "all"]

    def _pull(u, d):
        arts = _parse(_fetch(u) or b"", d, from_google=False)
        for a in arts:
            a["origin"] = "feed"         # broad section feed → gate on relevance downstream
        return arts
    return _gather([lambda u=u, d=d: _pull(u, d) for (u, d) in feeds])


def _dedupe(arts: list[dict]) -> list[dict]:
    seen, out = set(), []
    for a in arts:
        key = nc.event_id(a["title"], a["domain"])
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
    return out


def _recent(arts: list[dict], max_age_days: float) -> list[dict]:
    """Drop items older than max_age_days (a frozen feed must never surface stale news).
    Undated items are kept — they're rare and recency_weight scores them neutrally."""
    if not max_age_days:
        return arts
    now = datetime.now(timezone.utc)
    out = []
    for a in arts:
        dt = nc._parse_iso(a.get("seendate", ""))
        if dt is None or (now - dt).total_seconds() <= max_age_days * 86400:
            out.append(a)
    return out


def collect(scope: str = "all", queries: list[str] | None = None,
            window_days: int = 2, min_tier: int = 2, max_age_days: float = 5.0) -> list[dict]:
    """Top-tier RSS headlines for a scope ('macro' | 'market' | 'all'), merging the
    curated DIRECT feeds with optional Google-News topic queries. Deduped + recency-
    filtered (no stale feed content). Never raises."""
    tasks = [lambda q=q: _google_news(q, window_days, min_tier) for q in (queries or [])]
    arts = _direct(scope) + _gather(tasks)
    return _recent(_dedupe(arts), max_age_days)


def macro_headlines(window_days: int = 2, min_tier: int = 2) -> list[dict]:
    """Reliable macro wires — direct macro feeds + Google-News macro queries. The
    replacement for the flaky GDELT-only macro scorecard."""
    return collect("macro", GOOGLE_MACRO_QUERIES, window_days, min_tier)


def market_headlines(window_days: int = 2, min_tier: int = 2) -> list[dict]:
    """Broad equity-tape headlines from the wires + quality press."""
    return collect("market", GOOGLE_MARKET_QUERIES, window_days, min_tier)


def query(q: str, window_days: int = 3, min_tier: int = 2,
          max_age_days: float = 7.0) -> list[dict]:
    """Targeted Google-News query (e.g. a sector phrase or '<company> stock'). tier-2+
    by default — quality press & wires only, so single-name coverage stays clean (no
    fool.com / SEO blogs). Recency-filtered."""
    return _recent(_dedupe(_google_news(q, window_days, min_tier)), max_age_days)


def batch(queries: dict[str, str], window_days: int = 3, min_tier: int = 2,
          max_age_days: float = 7.0) -> dict[str, list[dict]]:
    """Run many labelled Google-News queries CONCURRENTLY → {label: [items]}. The
    per-name / per-sector fan-out for the financial feed. Never raises."""
    keys = list(queries)
    if not keys:
        return {}
    with cf.ThreadPoolExecutor(max_workers=_MAX_WORKERS) as ex:
        results = list(ex.map(
            lambda k: query(queries[k], window_days, min_tier, max_age_days), keys))
    return dict(zip(keys, results))


# --------------------------------------------------------------------------- #
# Reject-log helpers (build_news uses these to harvest the rss feed bucket)
# --------------------------------------------------------------------------- #
def start_reject_log() -> tuple[list[dict], object]:
    """Activate the per-call reject collector.  Returns (collector_list, token).
    Call stop_reject_log(token) when done.  Never raises."""
    col: list[dict] = []
    tok = _reject_collector.set(col)
    return col, tok


def stop_reject_log(token: object) -> None:
    """Reset the reject collector (deactivate).  Idempotent.  Never raises."""
    try:
        _reject_collector.reset(token)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001
        pass


# Research intake shares this collector, the incumbent press scheduler/state and
# IntelligenceStore. It never enters the marketing candidate or seen ledgers.
_RESEARCH_MAX_BYTES = 1024 * 1024
_RESEARCH_MAX_ITEMS = 150
_RESEARCH_FETCH_SECONDS = 5.0


def _research_iso(value: str) -> str:
    """RSS and Atom dates; missing/invalid remains unknown, never ingestion-now."""
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return ""
        return dt.astimezone(timezone.utc).isoformat()
    except ValueError:
        return _to_iso(value)


def _research_fetch(spec: dict, applied: dict) -> dict:
    """Conditional, bounded fetch. Returned validators are proposals, not ACKs."""
    if spec.get("transport") == "gdelt":
        from engine.gdelt_client import get_articles
        articles, reason = get_articles(
            {"query": spec["query"], "mode": "artlist", "format": "json", "maxrecords": 100,
             "sort": "datedesc", "timespan": "6h"},
            timeout=5, max_attempts=1, max_response_bytes=_RESEARCH_MAX_BYTES,
            total_timeout_s=_RESEARCH_FETCH_SECONDS,
        )
        if articles is None:
            raise OSError(reason or "GDELT unavailable")
        return {"status": 200, "articles": articles}

    import email
    import os
    import selectors
    import shutil
    import subprocess
    import tempfile
    import time
    from urllib.parse import urljoin

    if not shutil.which("curl"):
        raise OSError("curl unavailable")
    allowed = set(spec.get("allowed_hosts") or [])

    def checked(url):
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.hostname not in allowed
                or parsed.username or parsed.password or parsed.port not in (None, 443)):
            raise ValueError("unapproved feed destination")
        return url

    url = checked(spec["url"])
    deadline = time.monotonic() + _RESEARCH_FETCH_SECONDS
    headers = ["Accept: application/rss+xml, application/atom+xml, application/xml", "Accept-Encoding: identity"]
    for state_key, header in (("applied_etag", "If-None-Match"), ("applied_last_modified", "If-Modified-Since")):
        if applied.get(state_key):
            value = str(applied[state_key])[:1024]
            if "\r" in value or "\n" in value:
                raise ValueError("invalid conditional validator")
            headers.append(header + ": " + value)
    for _hop in range(4):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("feed total deadline")
        # curl's hard total deadline includes DNS, TLS, headers and body. The
        # reader independently caps bytes; killing this owned child terminates
        # a trickling response instead of leaving a blocked executor thread.
        with tempfile.TemporaryFile() as header_file:
            command = ["curl", "-q", "--silent", "--show-error", "--proto", "=https",
                       "--max-time", str(remaining), "--max-filesize", str(_RESEARCH_MAX_BYTES),
                       "--dump-header", f"/dev/fd/{header_file.fileno()}", "--user-agent", _UA]
            for header in headers:
                command.extend(["--header", header])
            command.append(url)
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                       pass_fds=(header_file.fileno(),))
            body = bytearray()
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    while True:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise TimeoutError("feed total deadline")
                        if not selector.select(remaining):
                            raise TimeoutError("feed total deadline")
                        chunk = os.read(process.stdout.fileno(), 16384)
                        if not chunk:
                            break
                        body.extend(chunk)
                        if len(body) > _RESEARCH_MAX_BYTES:
                            raise ValueError("feed exceeds size limit")
                if process.wait(timeout=max(0.01, deadline - time.monotonic())) != 0:
                    raise OSError("feed request failed")
            finally:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=1)
                process.stdout.close()
            header_file.seek(0)
            raw_headers = header_file.read(65537)
            if len(raw_headers) > 65536:
                raise ValueError("feed headers too large")
        blocks = [b for b in raw_headers.split(b"\r\n\r\n") if b.startswith(b"HTTP/")]
        if not blocks:
            raise ValueError("missing feed HTTP response")
        first, _, rest = blocks[-1].partition(b"\r\n")
        status = int(first.split()[1])
        response_headers = email.message_from_bytes(rest)
        if status in (301, 302, 303, 307, 308):
            url = checked(urljoin(url, response_headers.get("Location", "")))
            continue
        return {"status": status, "body": bytes(body),
                "etag": response_headers.get("ETag", "")[:1024],
                "last_modified": response_headers.get("Last-Modified", "")[:1024]}
    raise ValueError("feed redirect limit")

def _research_parse(raw: bytes, spec: dict, *, now: datetime) -> list[dict]:
    """Source identity and revision are separate; absence is never retraction."""
    import hashlib
    import html
    import json
    from engine.marketing.story_spine import content_key, normalize_url

    if len(raw) > _RESEARCH_MAX_BYTES or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("unsupported feed document")
    root = ET.fromstring(raw)
    local = root.tag.split("}")[-1].lower()
    if local not in ("rss", "rdf", "feed"):
        raise ValueError("not an RSS or Atom feed")
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    rows = {}
    cutoff = now - timedelta(days=7)

    def field(item, names):
        for name in names:
            child = _child(item, name)
            if child is not None:
                return "".join(child.itertext()).strip()
        return ""

    for entry in entries:
        headline = html.unescape(_clean(field(entry, ["title"])))[:500]
        article = ""
        for child in entry:
            if child.tag.split("}")[-1] == "link" and child.get("rel", "alternate") == "alternate":
                article = (child.get("href") or child.text or "").strip()
                break
        parsed = urlparse(article)
        if (not headline or parsed.scheme not in ("https", "http") or not parsed.hostname
                or parsed.username or parsed.password):
            continue
        # Some feeds mix institutional releases with authored work. An explicit
        # source path boundary excludes the latter and cannot be satisfied by a
        # query string or by a different publisher's similarly named path.
        prefixes = spec.get("allowed_path_prefixes", [])
        if prefixes and (parsed.hostname.lower() not in spec.get("allowed_hosts", [])
                         or not any(("/" + parsed.path.lstrip("/")).startswith(part)
                                    for part in prefixes)):
            continue
        if any(part in article for part in spec.get("exclude_url_parts", [])):
            continue
        published = _research_iso(field(entry, ["pubDate", "published", "date"]))
        updated = _research_iso(field(entry, ["updated", "modified"]))
        pub_dt = datetime.fromisoformat(published) if published else None
        update_dt = datetime.fromisoformat(updated) if updated else None
        if update_dt and update_dt > now + timedelta(minutes=5):
            updated, update_dt = "", None
        known_dates = [d for d in (pub_dt, update_dt) if d and d <= now + timedelta(minutes=5)]
        if known_dates and max(known_dates) < cutoff:
            continue
        timestamp_quality = "published" if published else "unknown"
        if pub_dt and pub_dt > now + timedelta(minutes=5):
            published = ""
            timestamp_quality = "future_source_stamp"
        upstream = field(entry, ["guid", "id"])[:1000]
        # Incumbent exact URL normalization; a feed's stable upstream ID takes
        # precedence so amended article URLs do not create a fresh source item.
        key = "upstream:" + upstream if upstream else content_key({"url": article, "headline": headline})
        sid = "research:" + spec["id"] + ":" + hashlib.sha256(key.encode()).hexdigest()[:24]
        summary = html.unescape(_clean(field(entry, ["description", "summary"])))[:800] if spec.get("content_use") == "attributed_feed_excerpt" else ""
        item = {"id": sid, "feed_id": spec["id"], "source_item_id": upstream or normalize_url(article),
                "headline": headline, "summary": summary, "url": article,
                "canonical_url": normalize_url(article), "published_at": published,
                "source_updated_at": updated, "timestamp_quality": timestamp_quality, "source_name": spec["publisher"],
                "source_type": spec.get("source_type", "official"),
                "category": spec.get("category", "economy"), "language": spec.get("language", "en"),
                "coverage_regions": spec.get("coverage_regions", []),
                "attribution": spec.get("attribution", spec["publisher"]),
                "source_use_url": spec["terms_url"], "content_use": spec["content_use"]}
        meaningful = [item[k] for k in ("headline", "summary", "url", "published_at", "source_updated_at")]
        item["source_revision"] = hashlib.sha256(json.dumps(meaningful, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        previous = rows.get(sid)
        if previous and previous["source_revision"] != item["source_revision"]:
            old_date, new_date = previous["source_updated_at"], item["source_updated_at"]
            if not old_date or not new_date or old_date == new_date:
                raise ValueError("ambiguous source revisions")
            if old_date > new_date:
                continue
        rows[sid] = item
        if len(rows) > _RESEARCH_MAX_ITEMS:
            raise ValueError("eligible feed batch exceeds acceptance bound")
    return list(rows.values())


def _research_gdelt(articles: list[dict], spec: dict, *, now: datetime) -> list[dict]:
    """GDELT metadata only. seendate is indexing time, never publication time."""
    import hashlib
    import json
    from engine.marketing.story_spine import content_key, normalize_url
    items = []
    languages = {"english": "en", "chinese": "zh", "japanese": "ja", "korean": "ko", "russian": "ru",
                 "spanish": "es", "french": "fr", "german": "de", "arabic": "ar", "portuguese": "pt",
                 "italian": "it", "turkish": "tr", "ukrainian": "uk", "hindi": "hi", "indonesian": "id",
                 "vietnamese": "vi", "thai": "th", "hebrew": "he", "polish": "pl", "dutch": "nl"}
    for row in articles[:100]:
        url = str(row.get("url") or "")
        domain = _domain_of(url)
        title = _clean(row.get("title"))[:500]
        if not title or urlparse(url).scheme not in ("http", "https") or not domain:
            continue
        # Incumbent publisher-quality policy, not a new source truth ranking.
        if not 0 < nc.source_tier(domain) <= 2:
            continue
        indexed = _research_iso(row.get("seendate", ""))
        timestamp_quality = "indexed_not_published" if indexed else "unknown"
        if indexed and datetime.fromisoformat(indexed) > now + timedelta(minutes=5):
            indexed = ""
            timestamp_quality = "future_index_stamp"
        identity = content_key({"url": url, "headline": title})
        items.append({"id": "research:" + spec["id"] + ":" + hashlib.sha256(identity.encode()).hexdigest()[:24],
            "feed_id": spec["id"], "source_item_id": normalize_url(url),
            "source_revision": hashlib.sha256(json.dumps([title, url], ensure_ascii=False).encode()).hexdigest(),
            "headline": title, "summary": "", "url": url, "canonical_url": normalize_url(url),
            "published_at": "", "source_updated_at": "", "timestamp_quality": timestamp_quality,
            "provider_indexed_at": indexed,
            "source_name": domain, "source_type": "reporting", "category": spec["category"],
            "language": languages.get(str(row.get("language") or "").lower(), "und"), "publisher_country": str(row.get("sourcecountry") or ""),
            "coverage_regions": spec.get("coverage_regions", []),
            "attribution": "Article metadata: The GDELT Project. Reporting belongs to the linked publisher.",
            "source_use_url": "https://www.gdeltproject.org/", "content_use": "attributed_headline_link"})
    return items


def poll_research_feeds(specs: list[dict], applied_state: dict, *, now: datetime,
                        fetcher=None) -> list[dict]:
    """Return due feed outcomes without consuming source revisions/validators."""
    fetcher = fetcher or _research_fetch
    due = []
    for spec in specs[:30]:
        if not spec.get("enabled") or spec.get("content_use") not in ("attributed_headline_link", "attributed_feed_excerpt") or not spec.get("terms_url"):
            continue
        state = applied_state.get(spec["id"], {})
        last = _research_iso(state.get("last_attempt_at", ""))
        interval = max(60, min(3600, int(spec.get("poll_seconds", 120))))
        delay = min(900, interval * 2 ** min(3, int(state.get("failures", 0))))
        if last and (now - datetime.fromisoformat(last)).total_seconds() < delay:
            continue
        due.append((spec, state))

    # One GDELT turn per tick. Least-recently-attempted selection uses the
    # existing feed state and never bypasses its cross-process pacing floor.
    gdelt_due = [pair for pair in due if pair[0].get("transport") == "gdelt"]
    if gdelt_due:
        chosen = min(gdelt_due, key=lambda pair: pair[1].get("last_attempt_at", ""))
        due = [pair for pair in due if pair[0].get("transport") != "gdelt" or pair is chosen]

    def poll(pair):
        spec, state = pair
        outcome = {"feed_id": spec["id"], "publisher": spec["publisher"], "observed_at": now.isoformat(), "items": []}
        try:
            response = fetcher(spec, state)
            status = int(response.get("status", 0))
            if status not in (200, 304):
                raise ValueError("feed HTTP status " + str(status))
            outcome.update(status=status, etag=response.get("etag", ""), last_modified=response.get("last_modified", ""))
            if status == 200:
                outcome["items"] = (_research_gdelt(response["articles"], spec, now=now) if spec.get("transport") == "gdelt" else _research_parse(response["body"], spec, now=now))
            outcome["error"] = ""
        except Exception as exc:  # one source must never stop the other feeds
            outcome.update(status=0, error=type(exc).__name__)
        return outcome

    if not due:
        return []
    with cf.ThreadPoolExecutor(max_workers=min(4, len(due))) as executor:
        return list(executor.map(poll, due))
