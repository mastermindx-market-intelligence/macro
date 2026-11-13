"""S&P 500/400/600 constituent-change ANNOUNCEMENTS — the free, authoritative detection
feed for the index-addition run-up (validated in scripts/validate_index_reconstitution.py).

S&P Dow Jones Indices announces changes ~3-5 trading days before the effective date (the
canonical "index effect" run-up window). The official press feed is keyless and static:

  • RSS index:  https://press.spglobal.com/index.php?s=2429&pagetemplate=rss
                (a rolling ~5-item feed → must be polled daily and ACCUMULATED)
  • each "… Set to Join S&P …" item links to a static HTML page carrying a table:
    Effective Date | Index Name | Action | Company Name | Ticker | GICS Sector
    e.g. "June 16, 2026  S&P SmallCap 600  Addition  First Advantage  FA  Industrials"

We poll the RSS, fetch each NEW announcement page, regex-parse the table, and APPEND to a
git-tracked parquet keyed by (announce_url, ticker, action). Keyless; degrades to the
existing cache if the page is unreachable (Akamai walls the spdji media-center, not these
press pages — but be defensive). The pure-vs-migration cohort tag (only PURE adds carry the
run-up) is computed downstream in engine/index_changes.py against the PIT membership.
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import unescape

import pandas as pd

from lib import config

log = logging.getLogger(__name__)

_RSS = "https://press.spglobal.com/index.php?s=2429&pagetemplate=rss"
_UA = "Mozilla/5.0 (Macro Dashboard research; longr2512@gmail.com)"
_JOIN_RE = re.compile(r"set to join|to join the s&p|join s&p", re.I)
_INDEX_CANON = {"500": "sp500", "MidCap 400": "sp400", "SmallCap 600": "sp600"}
_GICS = ("Information Technology|Health Care|Financials|Consumer Discretionary|"
         "Consumer Staples|Industrials|Energy|Materials|Utilities|Real Estate|"
         "Communication Services")
# Effective | "S&P <idx>" | Addition/Deletion | Company … | TICKER | <GICS sector>
_ROW_RE = re.compile(
    r"([A-Z][a-z]+ \d{1,2}, \d{4})\s+S&P\s+(500|MidCap 400|SmallCap 600)\s+"
    r"(Addition|Deletion)\s+(.+?)\s+([A-Z][A-Z.\-]{0,5})\s+(" + _GICS + r")")


def _cache_path():
    p = config.data_dir() / "sp_index_changes" / "changes.parquet"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _date_iso(x) -> str | None:
    d = pd.to_datetime(str(x), errors="coerce")
    return None if pd.isna(d) else d.strftime("%Y-%m-%d")


def parse_rss(text: str) -> list[dict]:
    """'Set to Join' items → [{url, announce_date}] from the press RSS. PURE."""
    # Decode XML character references and CDATA exactly once, before matching
    # titles or constructing requests. Reject malformed feeds as a whole; the
    # existing fetch boundary logs the failure and preserves the cache.
    if re.search(r"<!DOCTYPE", text, re.I):
        raise ValueError("RSS document types are not supported")
    root = ET.fromstring(text)
    namespace = root.tag.rpartition("}")[0] + "}" if root.tag.startswith("{") else ""
    if root.tag != namespace + "rss":
        raise ValueError("Expected an RSS document")
    channel = root.find(namespace + "channel")
    if channel is None:
        raise ValueError("RSS channel missing")
    out = []
    for item in channel.findall(namespace + "item"):
        title = item.findtext(namespace + "title") or ""
        link = item.findtext(namespace + "link") or ""
        pub = item.findtext(namespace + "pubDate")
        if not _JOIN_RE.search(title) or not link.strip():
            continue
        out.append({"url": link.strip(),
                    "announce_date": _date_iso(pub) if pub else None,
                    "title": title.strip()})
    return out


def parse_changes_page(html: str, url: str, announce_date: str | None) -> list[dict]:
    """The change-table rows from one announcement page. PURE.
    Returns [{ticker, index, action, effective_date, announce_date, company, announce_url}]."""
    plain = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html)))
    out = []
    for eff, idx, action, company, ticker, _sector in _ROW_RE.findall(plain):
        out.append({
            "ticker": ticker.strip().upper(),
            "index": _INDEX_CANON.get(idx.strip(), idx.strip()),
            "action": action.lower(),                       # addition / deletion
            "effective_date": _date_iso(eff),
            "announce_date": announce_date,
            "company": company.strip()[:80],
            "announce_url": url,
        })
    return out


def fetch_index_changes() -> pd.DataFrame:
    """Poll the RSS, fetch NEW announcement pages, parse + APPEND to the git-tracked cache.
    Idempotent on (announce_url, ticker, action). Poll failures degrade to the cache.
    Return-only attrs["index_changes_poll"] reports whether this poll completed;
    it is not persisted as historical cache metadata or evidence freshness.
    """
    import requests
    cache = _cache_path()
    prev = pd.read_parquet(cache) if cache.exists() else pd.DataFrame()
    seen_urls = set(prev["announce_url"]) if not prev.empty else set()

    poll_errors = []
    sess = requests.Session()
    sess.headers.update({"User-Agent": _UA})
    try:
        r = sess.get(_RSS, timeout=30)
        if r.status_code != 200:
            poll_errors.append("rss_http_error")
            items = []
        else:
            items = parse_rss(r.text)
    except Exception as e:  # noqa: BLE001
        log.warning("sp_index_changes: RSS fetch failed (%s) — keeping cache", e)
        poll_errors.append("rss_fetch_or_parse_error")
        items = []

    fresh = []
    for it in items:
        if it["url"] in seen_urls:
            continue
        try:
            pg = sess.get(it["url"], timeout=30)
            if pg.status_code != 200:
                poll_errors.append("page_http_error")
                log.info("sp_index_changes: page %s -> HTTP %d (skip)", it["url"][-30:], pg.status_code)
                continue
            rows = parse_changes_page(pg.text, it["url"], it["announce_date"])
            if not rows:
                poll_errors.append("page_parse_error")
                log.warning("sp_index_changes: announcement %s yielded no parseable rows; "
                            "keeping cache (not a verified no-change feed)", it["url"])
                continue
            fresh.extend(rows)
            log.info("sp_index_changes: %s -> %d rows", it["url"].split("/")[-1][:40], len(rows))
        except Exception as e:  # noqa: BLE001
            poll_errors.append("page_fetch_or_parse_error")
            log.warning("sp_index_changes: page fetch failed %s (%s)", it["url"][-30:], e)

    poll = {"complete": not poll_errors, "errors": sorted(set(poll_errors))}
    if not fresh:
        prev.attrs["index_changes_poll"] = poll
        return prev
    fdf = pd.DataFrame(fresh)
    fdf["_seen"] = datetime.now(timezone.utc).isoformat()
    combined = pd.concat([prev, fdf], ignore_index=True) if not prev.empty else fdf
    combined = combined.drop_duplicates(["announce_url", "ticker", "action"], keep="first").reset_index(drop=True)
    combined.to_parquet(cache)
    log.info("sp_index_changes: +%d rows (cache=%d)", len(fdf), len(combined))
    combined.attrs["index_changes_poll"] = poll
    return combined


def load_changes() -> pd.DataFrame:
    p = _cache_path()
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    fetch_index_changes()
