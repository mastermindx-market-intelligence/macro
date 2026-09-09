"""Policy Watch current-source composer — display-only, read-only leaf.

Public: build_current(root, now=None) -> dict. Consumes the existing official
cache, FOMC statement store/ledger, and decision_dates(). Never writes, never
networks, never calls a model. Build time is not evidence.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from engine.marketing import fomc_diff, fomc_statements

log = logging.getLogger(__name__)

_CACHE_DIR = Path("data") / "macro" / "official_news_cache"
_CACHE_NAME = re.compile(r"^official_v3_(\d{4}-\d{2}-\d{2})\.json$")
_CACHE_MAX_BYTES = 8 * 1024 * 1024
_ARTICLE_ROW_CAP = 400
_HEADLINE_CAP = 4
_ADMITTED_HOSTS = frozenset({"federalreserve.gov", "www.federalreserve.gov"})
_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
_ENFORCE_RE = re.compile(r"enforcement", re.I)
_MONETARY_PATH = "/newsevents/pressreleases/monetary"
_SPEECH_PATH = "/newsevents/speech/"


def build_current(root: Path, now: datetime | None = None) -> dict:
    """Compose a display-only current-source view. Read-only. Never raises out."""
    root = Path(root)
    clock = _as_utc(now)
    today = clock.date()
    calendar = _calendar(today)
    headlines = _headlines(root, clock)
    statement, comparison = _statement(root, today)
    return {
        "schema": "policy_watch_current.v1",
        "as_of": clock.date().isoformat(),
        "build_time_is_not_evidence": True,
        "calendar": calendar,
        "headlines": headlines,
        "statement": statement,
        "comparison": comparison,
    }


def _as_utc(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now.astimezone(timezone.utc)


def _parse_day(value: object) -> date | None:
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _parse_dt(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(raw.replace("+00:00", "+0000").replace("Z", "+0000"), fmt)
                break
            except ValueError:
                dt = None
        if dt is None:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _calendar(today: date) -> dict:
    dates = fomc_statements.decision_dates()
    parsed = [d for d in (_parse_day(x) for x in dates) if d is not None]
    coverage_start = parsed[0].isoformat() if parsed else None
    coverage_end = parsed[-1].isoformat() if parsed else None
    future = [d for d in parsed if d >= today]
    if parsed and today > parsed[-1]:
        return {
            "state": "schedule_needs_updating",
            "coverage_start": coverage_start,
            "coverage_end": coverage_end,
            "meetings": [],
            "calendar_url": _CALENDAR_URL,
        }
    meetings = []
    for d in future[:3]:
        meetings.append({
            "date": d.isoformat(),
            "days_to": (d - today).days,
            "event_en": "FOMC decision",
            "event_zh": "FOMC决议",
        })
    return {
        "state": "scheduled" if meetings else "schedule_needs_updating",
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "meetings": meetings,
        "calendar_url": _CALENDAR_URL,
    }


def _admit_url(url: object) -> tuple[str, str] | None:
    """Return (canonical, kind) or None. Exact Fed host, https, no credentials."""
    raw = str(url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme != "https":
        return None
    if parsed.username or parsed.password:
        return None
    host = (parsed.hostname or "").lower()
    if host not in _ADMITTED_HOSTS:
        return None
    path = parsed.path or ""
    if _ENFORCE_RE.search(path):
        return None
    kind = None
    if path.startswith(_SPEECH_PATH):
        kind = "speech"
    elif path.startswith(_MONETARY_PATH) or path.startswith("/newsevents/pressreleases/monetary"):
        kind = "monetary"
    else:
        return None
    canonical = urlunparse(("https", "www.federalreserve.gov", path.rstrip("/") or "/", "", "", ""))
    return canonical, kind


def _article_item(article: dict, now: datetime) -> dict | None:
    admitted = _admit_url(article.get("url"))
    if admitted is None:
        return None
    canonical, kind = admitted
    title = str(article.get("title") or "").strip()
    if not title or _ENFORCE_RE.search(title):
        return None
    published = _parse_dt(article.get("seendate") or article.get("published_at"))
    if published is None or published > now:
        return None
    return {
        "title": title,
        "url": canonical,
        "published_at": published.isoformat(),
        "kind": kind,
        "source_lang": article.get("source_lang") or "en",
    }


def _select_items(articles: object, now: datetime) -> list[dict]:
    if not isinstance(articles, list):
        return []
    seen: set[str] = set()
    items: list[dict] = []
    for article in articles[:_ARTICLE_ROW_CAP]:
        if not isinstance(article, dict):
            continue
        item = _article_item(article, now)
        if item is None or item["url"] in seen:
            continue
        seen.add(item["url"])
        items.append(item)
    items.sort(key=lambda row: row["published_at"], reverse=True)
    return items[:_HEADLINE_CAP]


def _cache_files(root: Path) -> list[tuple[date, Path]]:
    folder = root / _CACHE_DIR
    if not folder.is_dir():
        return []
    found: list[tuple[date, Path]] = []
    try:
        names = list(folder.iterdir())
    except OSError as exc:
        log.warning("policy_watch_current: cache dir unreadable %s: %s", folder, exc)
        return []
    for path in names:
        m = _CACHE_NAME.match(path.name)
        if not m:
            continue
        day = _parse_day(m.group(1))
        if day is None:
            continue
        found.append((day, path))
    found.sort(key=lambda row: row[0], reverse=True)
    return found


def _load_cache(path: Path) -> dict | None:
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > _CACHE_MAX_BYTES:
        return None
    try:
        text = path.read_text(encoding="utf-8")
        blob = json.loads(text)
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None
    if not isinstance(blob, dict) or not isinstance(blob.get("articles"), list):
        return None
    return blob


def _headlines_from_blob(blob: dict, saved_date: str, now: datetime, state: str) -> dict:
    fetched_at = blob.get("fetched_at")
    if fetched_at is not None:
        fetched_at = str(fetched_at)
    return {
        "state": state,
        "saved_date": saved_date,
        "fetched_at": fetched_at,
        "verified_at": None,
        "fresh": False,
        "items": _select_items(blob.get("articles"), now),
    }


def _headlines(root: Path, now: datetime) -> dict:
    files = _cache_files(root)
    if not files:
        return {
            "state": "missing",
            "saved_date": None,
            "fetched_at": None,
            "verified_at": None,
            "fresh": False,
            "items": [],
        }
    newest_day, newest_path = files[0]
    newest_blob = _load_cache(newest_path)
    if newest_blob is None:
        last_good = None
        for day, path in files[1:]:
            blob = _load_cache(path)
            if blob is None:
                continue
            last_good = _headlines_from_blob(blob, day.isoformat(), now, "last_good")
            break
        return {
            "state": "invalid_newest",
            "saved_date": newest_day.isoformat(),
            "fetched_at": None,
            "verified_at": None,
            "fresh": False,
            "items": [],
            "last_good": last_good,
        }
    view = _headlines_from_blob(newest_blob, newest_day.isoformat(), now, "ok")
    if not view["items"]:
        view["state"] = "empty"
    return view


def _ledger_by_date(root: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for row in fomc_statements.ledger_rows(root):
        day = _parse_day(row.get("date"))
        if day is None:
            continue
        out[day.isoformat()] = row
    return out


def _statement(root: Path, today: date) -> tuple[dict, dict]:
    dates = fomc_statements.decision_dates()
    past = [d for d in dates if _parse_day(d) is not None and _parse_day(d) <= today]
    empty_comparison = {"state": "unavailable", "prior_date": None, "highlights": [],
                         "added_phrases": [], "removed_phrases": []}
    none_stmt = {
        "state": "none",
        "decision_date": None,
        "url": None,
        "facts": None,
        "collected_at": None,
        "seed": False,
        "source_date": None,
    }
    if not past:
        return none_stmt, empty_comparison

    latest = past[-1]
    ledger = _ledger_by_date(root)
    paragraphs = fomc_statements.read_statement(latest, root)
    row = ledger.get(latest)
    if not paragraphs or row is None:
        awaiting = {
            "state": "awaiting_statement",
            "decision_date": latest,
            "url": fomc_statements.statement_url(latest),
            "facts": None,
            "collected_at": None,
            "seed": False,
            "source_date": None,
            "elapsed_decision": latest,
        }
        return awaiting, empty_comparison

    facts = fomc_diff.extract_facts(paragraphs)
    collected = row.get("fetched_at")
    statement = {
        "state": "recorded",
        "decision_date": latest,
        "url": row.get("url") or fomc_statements.statement_url(latest),
        "facts": facts,
        "collected_at": str(collected) if collected else None,
        "seed": bool(row.get("seed") or row.get("mode") == "seed"),
        "source_date": latest,
    }
    prior = fomc_statements.prior_decision_date(latest, root=root)
    prior_paragraphs = fomc_statements.read_statement(prior, root) if prior else []
    if not prior or not prior_paragraphs:
        return statement, empty_comparison
    diff = fomc_diff.diff_statements(prior_paragraphs, paragraphs)
    hl = fomc_diff.highlights(diff, limit=6)
    comparison = {
        "state": "available",
        "prior_date": prior,
        "highlights": hl,
        "added_phrases": list(diff.get("added_phrases") or []),
        "removed_phrases": list(diff.get("removed_phrases") or []),
        "added_sentences": list(diff.get("added_sentences") or []),
        "removed_sentences": list(diff.get("removed_sentences") or []),
    }
    return statement, comparison
