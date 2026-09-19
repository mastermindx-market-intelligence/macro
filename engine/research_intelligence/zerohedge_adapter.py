"""ZeroHedge long-form adapter for the existing Research Intelligence organism.

The canonical breaking-feed item keeps ownership of source identity and relevance.
This adapter only recovers the full publisher RSS body from the same payload,
binds that body back to the canonical item, invokes the shared grounded RIO
extractor, and prepares a quote-free qbus metadata projection.
"""
from __future__ import annotations

from datetime import date, datetime
import xml.etree.ElementTree as ET
from typing import Any, Callable, Iterable

from engine import qbus, qkernel
from engine.marketing.breaking_feed import _strip_html, parse_feed
from engine.marketing.breaking_relevance import rank_items

from .extractor import analyze_document

ZEROHEDGE_SOURCE_KEY = "zerohedge_feed"
MIN_RESEARCH_BODY_CHARS = 800
_MAX_CLUSTER_CANDIDATES = 128
_CONTENT_TAG = "{http://purl.org/rss/1.0/modules/content/}encoded"


def _text(elem: Any) -> str:
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


def _rss_bodies_by_url(xml_text: str) -> dict[str, str]:
    """Return the longest publisher-provided body for each RSS item URL."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}
    channel = root.find("channel")
    if channel is None:
        channel = root
    bodies: dict[str, str] = {}
    for entry in channel.findall("item"):
        url = _text(entry.find("link"))
        if not url:
            continue
        description = _text(entry.find("description"))
        encoded = _text(entry.find(_CONTENT_TAG))
        body = _strip_html(max((description, encoded), key=len, default=""))
        if len(body) > len(bodies.get(url, "")):
            bodies[url] = body
    return bodies


def parse_zerohedge_feed(
    xml_text: str,
    source_cfg: dict[str, Any],
    *,
    min_body_chars: int = MIN_RESEARCH_BODY_CHARS,
) -> list[dict[str, Any]]:
    """Bind full RSS bodies to canonical breaking-feed identities."""
    if str(source_cfg.get("key") or "") != ZEROHEDGE_SOURCE_KEY:
        raise ValueError("ZeroHedge adapter requires the zerohedge_feed source")
    if str(source_cfg.get("kind") or "rss") != "rss":
        raise ValueError("ZeroHedge research adapter requires RSS input")
    minimum = max(1, int(min_body_chars))
    canonical = parse_feed(xml_text, source_cfg)
    bodies = _rss_bodies_by_url(xml_text)
    out: list[dict[str, Any]] = []
    for item in canonical:
        body = bodies.get(str(item.get("url") or ""), "")
        full = len(body) >= minimum and len(body) > len(str(item.get("body_snippet") or ""))
        out.append(
            {
                "feed_item": dict(item),
                "research_body": body if full else "",
                "body_state": "full" if full else "insufficient",
            }
        )
    return out


def select_candidates(
    articles: list[dict[str, Any]],
    *,
    now: datetime,
    breaking_cfg: dict[str, Any],
    limit: int = 5,
    root: Any = None,
) -> list[dict[str, Any]]:
    """Reuse incumbent deterministic breaking relevance to choose deep reads."""
    by_id = {
        str(article["feed_item"].get("id") or ""): article
        for article in articles
        if article.get("body_state") == "full" and article.get("research_body")
    }
    if not by_id or limit <= 0:
        return []
    scored = rank_items(
        [dict(article["feed_item"]) for article in by_id.values()],
        now=now,
        cfg=breaking_cfg,
        root=root,
    )
    selected: list[dict[str, Any]] = []
    for item in scored:
        article = by_id.get(str(item.get("id") or ""))
        if article is None:
            continue
        selected.append({"feed_item": item, "research_body": article["research_body"]})
        if len(selected) >= limit:
            break
    return selected


def analyze_candidate(
    candidate: dict[str, Any],
    *,
    model_id: str,
    call: Callable[..., tuple[str, str, str]] | None = None,
) -> dict[str, Any]:
    """Run the same grounded RIO contract used for institutional reports."""
    item = candidate.get("feed_item") or {}
    body = str(candidate.get("research_body") or "")
    document = {
        "id": str(item.get("id") or ""),
        "source_type": "qualitative_article",
        "source_name": str(item.get("source_name") or "ZeroHedge"),
        "institution": "",
        "desk": "",
        "title": str(item.get("headline") or ""),
        "published_at": str(item.get("published_at") or ""),
    }
    return analyze_document(document, body, model_id=model_id, call=call)


def _day(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _subjects(row: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for field in ("entities", "themes"):
        value = row.get(field)
        if isinstance(value, str):
            out.update(x for x in value.split(",") if x)
        elif isinstance(value, Iterable):
            out.update(str(x) for x in value if str(x))
    return out


def _representative_key(row: dict[str, Any]) -> tuple[int, str, str]:
    tier = row.get("source_tier")
    try:
        numeric = int(tier or 9)
    except (TypeError, ValueError):
        numeric = 9
    return (
        numeric,
        str(row.get("_crawled_at") or ""),
        str(row.get("item_id") or ""),
    )


def _bind_existing_event_key(
    row: dict[str, Any],
    existing_rows: Iterable[dict[str, Any]],
    *,
    window_days: int = 3,
    threshold: float = 0.6,
) -> dict[str, Any]:
    """Reuse qbus clustering law and an existing canonical event key when possible."""
    normalized = qbus.normalize_row(row)
    candidate_day = _day(normalized.get("seendate") or normalized.get("_crawled_at"))
    subjects = _subjects(normalized)
    hits: list[dict[str, Any]] = []
    for raw in existing_rows:
        existing = qbus.normalize_row(dict(raw))
        if subjects and not (subjects & _subjects(existing)):
            continue
        existing_day = _day(existing.get("seendate") or existing.get("_crawled_at"))
        if candidate_day is not None and existing_day is not None:
            if abs((candidate_day - existing_day).days) > window_days:
                continue
        if qkernel.title_similarity(
            existing.get("title", ""),
            normalized.get("title", ""),
            existing.get("lang", "auto"),
        ) < threshold:
            continue
        pair = qbus.assign_event_keys(
            [existing, normalized], thresh=threshold, window_days=window_days
        )
        if pair[0]["event_key"] == pair[1]["event_key"]:
            hits.append(existing)
        if len(hits) >= _MAX_CLUSTER_CANDIDATES:
            break
    if hits:
        representative = min(hits + [normalized], key=_representative_key)
        if representative is not normalized and representative.get("event_key"):
            normalized["event_key"] = str(representative["event_key"])
            return normalized
    normalized["event_key"] = qbus.assign_event_keys(
        hits + [normalized], thresh=threshold, window_days=window_days
    )[-1]["event_key"]
    return normalized


def qbus_projection(
    candidate: dict[str, Any],
    *,
    observed_at: str,
    existing_rows: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Build a quote-free qbus row from one scored, full-body candidate."""
    item = candidate.get("feed_item") or {}
    body = str(candidate.get("research_body") or "")
    matched = item.get("matched") if isinstance(item.get("matched"), dict) else {}
    entities = list(matched.get("tickers") or [])
    themes = list(
        dict.fromkeys(list(matched.get("sectors") or []) + list(matched.get("macro_keys") or []))
    )
    row = {
        "item_id": str(item.get("id") or ""),
        "desk": "research_intelligence",
        "source": str(item.get("source") or ZEROHEDGE_SOURCE_KEY),
        "source_tier": None,
        "lang": "en",
        "url": str(item.get("url") or ""),
        "title": str(item.get("headline") or ""),
        "body_sha256": qbus.body_sha256(body),
        "seendate": str(item.get("published_at") or ""),
        "_crawled_at": str(observed_at or ""),
        "timestamp_quality": "PUBLISHER_STATED",
        "entities": entities,
        "themes": themes,
        "importance_raw": float(item.get("salience") or 0.0),
    }
    return _bind_existing_event_key(row, existing_rows)
