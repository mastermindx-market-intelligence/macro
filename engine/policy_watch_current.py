"""Policy Watch current-source composer — display-only, read-only leaf.

Public: build_current(root, now=None) -> dict. Consumes the existing official
cache, FOMC statement store/ledger, and decision_dates(). Never writes, never
networks, never calls a model. Build/model time is not source evidence.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from zoneinfo import ZoneInfo

from engine.marketing import fomc_diff, fomc_statements

log = logging.getLogger(__name__)

_CACHE_DIR = Path("data") / "macro" / "official_news_cache"
_CACHE_NAME = re.compile(r"^official_v3_(\d{4}-\d{2}-\d{2})\.json$")
_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CACHE_MAX_BYTES = 8 * 1024 * 1024
_STMT_MAX_BYTES = 4 * 1024 * 1024
_LEDGER_MAX_BYTES = 2 * 1024 * 1024
_LEDGER_ROW_CAP = 500
_ARTICLE_ROW_CAP = 400
_HEADLINE_CAP = 4
_ACQUIRE_STALE = timedelta(hours=24)
_ADMITTED_HOSTS = frozenset({"federalreserve.gov", "www.federalreserve.gov"})
_CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
_ENFORCE_RE = re.compile(r"enforcement", re.I)
_MONETARY_PATH = "/newsevents/pressreleases/monetary"
_SPEECH_PATH = "/newsevents/speech/"
_RELEVANT_FED_FEED_MARKERS = (
    "press_monetary.xml",
    "press_all.xml",
    "speeches.xml",
)
_ET = ZoneInfo("America/New_York")


def build_current(root: Path, now: datetime | None = None) -> dict:
    """Compose a display-only current-source view. Read-only. Never raises out."""
    root = Path(root)
    clock = _normalize_now(now)
    calendar = _calendar(clock)
    headlines = _headlines(root, clock)
    statement, comparison = _statement(root, clock)
    return {
        "schema": "policy_watch_current.v1",
        "as_of": clock.astimezone(timezone.utc).date().isoformat(),
        "build_time_is_not_evidence": True,
        "calendar": calendar,
        "headlines": headlines,
        "statement": statement,
        "comparison": comparison,
    }


def _normalize_now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        # Naive clock is treated as UTC explicitly (not local wall time).
        return now.replace(tzinfo=timezone.utc)
    return now


def _parse_day(value: object) -> date | None:
    """Strict YYYY-MM-DD only — trailing junk fails rather than slicing."""
    raw = str(value or "").strip()
    if not _DAY_RE.fullmatch(raw):
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_dt(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _release_deadline(day: date) -> datetime:
    hour_s, minute_s = fomc_statements.STATEMENT_RELEASE_ET.split(":", 1)
    return datetime(
        day.year, day.month, day.day,
        int(hour_s), int(minute_s),
        tzinfo=_ET,
    )


def _decision_elapsed(day: date, now: datetime) -> bool:
    return now >= _release_deadline(day)


def _calendar(now: datetime) -> dict:
    today_et = now.astimezone(_ET).date()
    dates = fomc_statements.decision_dates()
    parsed = [d for d in (_parse_day(x) for x in dates) if d is not None]
    coverage_start = parsed[0].isoformat() if parsed else None
    coverage_end = parsed[-1].isoformat() if parsed else None
    future = [d for d in parsed if d >= today_et]
    if parsed and today_et > parsed[-1]:
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
            "days_to": (d - today_et).days,
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


def _admit_url(url: object, *, allow_query: bool = False) -> tuple[str, str] | None:
    """Return (canonical, kind) or None. Exact Fed host, https, no credentials."""
    raw = str(url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme != "https":
        return None
    if parsed.username or parsed.password:
        return None
    if parsed.port is not None:
        return None
    if not allow_query and (parsed.query or parsed.fragment):
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
    elif path.startswith(_MONETARY_PATH):
        kind = "monetary"
    else:
        return None
    canonical = urlunparse(("https", "www.federalreserve.gov", path.rstrip("/") or "/", "", "", ""))
    return canonical, kind


def _admit_headline_url(url: object) -> tuple[str, str] | None:
    # Headlines may arrive with fragments from feed entries; strip only after host check.
    raw = str(url or "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.port is not None:
        return None
    host = (parsed.hostname or "").lower()
    if host not in _ADMITTED_HOSTS:
        return None
    # Rebuild without query/credentials for dedup; reject non-https already done.
    cleaned = urlunparse(("https", host, parsed.path or "", "", "", ""))
    return _admit_url(cleaned, allow_query=False)


def _admit_statement_url(url: object, decision_date: str) -> str | None:
    expected = fomc_statements.statement_url(decision_date)
    if not expected:
        return None
    admitted = _admit_url(url, allow_query=False)
    if admitted is None:
        return None
    canonical, kind = admitted
    if kind != "monetary":
        return None
    expected_admitted = _admit_url(expected, allow_query=False)
    if expected_admitted is None:
        return None
    if canonical != expected_admitted[0]:
        return None
    # Decision date must appear in the monetary path (monetaryYYYYMMDDa.htm).
    ymd = decision_date.replace("-", "")
    if f"monetary{ymd}a" not in canonical:
        return None
    return canonical


def _article_item(article: dict, now: datetime) -> dict | None:
    admitted = _admit_headline_url(article.get("url"))
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
        "published_at": published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
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


def _is_relevant_fed_feed(feed: dict) -> bool:
    blob = f"{feed.get('name') or ''} {feed.get('url') or ''}".lower()
    return any(marker in blob for marker in _RELEVANT_FED_FEED_MARKERS)


def _fed_feed_health(blob: dict) -> str | None:
    """Return 'failed' if a relevant Fed feed failed, 'ok' if present+ok, else None."""
    feeds = blob.get("feeds")
    if not isinstance(feeds, list) or not feeds:
        return None
    relevant = [f for f in feeds if isinstance(f, dict) and _is_relevant_fed_feed(f)]
    if not relevant:
        return None
    if any(str(f.get("status") or "") != "ok" for f in relevant):
        return "failed"
    return "ok"


def _empty_headlines(state: str, saved_date: str | None = None) -> dict:
    return {
        "state": state,
        "saved_date": saved_date,
        "fetched_at": None,
        "verified_at": None,
        "fresh": False,
        "items": [],
        "acquisition_age_hours": None,
        "feed_status": None,
    }


def _headlines_from_blob(blob: dict, saved_date: str, now: datetime, *, force_state: str | None = None) -> dict:
    items = _select_items(blob.get("articles"), now)
    raw_fetched = blob.get("fetched_at")
    fetched_at = None
    acquired = None
    acquisition_invalid = False
    if raw_fetched is not None and str(raw_fetched).strip():
        acquired = _parse_dt(raw_fetched)
        if acquired is None or acquired > now:
            acquisition_invalid = True
        else:
            fetched_at = acquired.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    feed_health = _fed_feed_health(blob)
    feed_status = blob.get("feed_status")
    if feed_status is not None:
        feed_status = str(feed_status)

    age_hours = None
    fresh = False
    if acquired is not None and not acquisition_invalid:
        age = now - acquired
        age_hours = round(age.total_seconds() / 3600.0, 3)
        fresh = age <= _ACQUIRE_STALE

    if force_state:
        state = force_state
    elif acquisition_invalid:
        state = "invalid_newest"
        fresh = False
        items = []
    elif feed_health == "failed":
        state = "source_outage"
        fresh = False
    elif not items:
        # Successful Fed acquisition with zero admitted monetary/speech rows.
        if feed_health == "ok" or (feed_health is None and not acquisition_invalid and raw_fetched):
            state = "no_new"
        elif raw_fetched is None:
            state = "empty"
        else:
            state = "no_new"
        fresh = False
    elif acquired is None:
        # Legacy cache: filename day only — never fresh.
        state = "ok"
        fresh = False
    elif not fresh:
        state = "stale"
    else:
        state = "ok"

    return {
        "state": state,
        "saved_date": saved_date,
        "fetched_at": fetched_at,
        "verified_at": None,
        "fresh": fresh,
        "items": items if state != "invalid_newest" else [],
        "acquisition_age_hours": age_hours,
        "feed_status": feed_status,
        "fed_feed_health": feed_health,
    }


def _find_last_good(files: list[tuple[date, Path]], now: datetime, skip_day: date) -> dict | None:
    for day, path in files:
        if day == skip_day:
            continue
        if day > now.astimezone(timezone.utc).date():
            continue
        blob = _load_cache(path)
        if blob is None:
            continue
        view = _headlines_from_blob(blob, day.isoformat(), now, force_state="last_good")
        view["fresh"] = False
        return view
    return None


def _headlines(root: Path, now: datetime) -> dict:
    files = _cache_files(root)
    if not files:
        return _empty_headlines("missing")

    newest_day, newest_path = files[0]
    today_utc = now.astimezone(timezone.utc).date()

    if newest_day > today_utc:
        last_good = _find_last_good(files, now, newest_day)
        out = _empty_headlines("invalid_newest", newest_day.isoformat())
        out["last_good"] = last_good
        return out

    newest_blob = _load_cache(newest_path)
    if newest_blob is None:
        last_good = _find_last_good(files, now, newest_day)
        out = _empty_headlines("invalid_newest", newest_day.isoformat())
        out["last_good"] = last_good
        return out

    view = _headlines_from_blob(newest_blob, newest_day.isoformat(), now)
    if view["state"] == "invalid_newest":
        last_good = _find_last_good(files, now, newest_day)
        view["items"] = []
        view["fresh"] = False
        view["last_good"] = last_good
    return view


def _ledger_by_date(root: Path) -> dict[str, dict] | None:
    """Bounded ledger read. None => unreadable/oversized/malformed beyond use."""
    path = fomc_statements.ledger_path(root)
    if not path.exists():
        return {}
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > _LEDGER_MAX_BYTES:
        return None
    out: dict[str, dict] = {}
    try:
        with path.open(encoding="utf-8") as fh:
            for idx, line in enumerate(fh):
                if idx >= _LEDGER_ROW_CAP:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                day = _parse_day(row.get("date"))
                if day is None:
                    continue
                out[day.isoformat()] = row
    except OSError as exc:
        log.warning("policy_watch_current: ledger unreadable %s: %s", path, exc)
        return None
    return out


def _read_statement_bounded(root: Path, day: str) -> list[str] | None:
    """None => oversized/unreadable; [] => absent."""
    path = fomc_statements.store_path(day, root)
    if path is None or not path.exists():
        return []
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > _STMT_MAX_BYTES:
        return None
    paragraphs = fomc_statements.read_statement(day, root)
    return paragraphs


def _none_statement() -> dict:
    return {
        "state": "none",
        "decision_date": None,
        "url": None,
        "facts": None,
        "collected_at": None,
        "seed": False,
        "source_date": None,
    }


def _empty_comparison() -> dict:
    return {
        "state": "unavailable",
        "prior_date": None,
        "highlights": [],
        "added_phrases": [],
        "removed_phrases": [],
    }


def _statement(root: Path, now: datetime) -> tuple[dict, dict]:
    dates = fomc_statements.decision_dates()
    empty_comparison = _empty_comparison()
    elapsed = []
    for raw in dates:
        day = _parse_day(raw)
        if day is None:
            continue
        if _decision_elapsed(day, now):
            elapsed.append(day.isoformat())
    if not elapsed:
        return _none_statement(), empty_comparison

    latest = elapsed[-1]
    ledger = _ledger_by_date(root)
    if ledger is None:
        unavailable = {
            "state": "unavailable",
            "decision_date": latest,
            "url": None,
            "facts": None,
            "collected_at": None,
            "seed": False,
            "source_date": None,
            "reason": "ledger_unreadable",
        }
        return unavailable, empty_comparison

    paragraphs = _read_statement_bounded(root, latest)
    row = ledger.get(latest)
    if paragraphs is None:
        unavailable = {
            "state": "unavailable",
            "decision_date": latest,
            "url": None,
            "facts": None,
            "collected_at": None,
            "seed": False,
            "source_date": None,
            "reason": "statement_oversized_or_unreadable",
            "elapsed_decision": latest,
        }
        return unavailable, empty_comparison

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

    admitted_url = _admit_statement_url(row.get("url"), latest)
    if admitted_url is None:
        unavailable = {
            "state": "unavailable",
            "decision_date": latest,
            "url": None,
            "facts": None,
            "collected_at": None,
            "seed": False,
            "source_date": None,
            "reason": "statement_url_rejected",
            "elapsed_decision": latest,
        }
        return unavailable, empty_comparison

    facts = fomc_diff.extract_facts(paragraphs)
    collected = row.get("fetched_at")
    statement = {
        "state": "recorded",
        "decision_date": latest,
        "url": admitted_url,
        "facts": facts,
        "collected_at": str(collected) if collected else None,
        "seed": bool(row.get("seed") or row.get("mode") == "seed"),
        "source_date": latest,
    }

    prior = fomc_statements.prior_decision_date(latest, root=root)
    if not prior or _parse_day(prior) is None:
        return statement, empty_comparison
    prior_row = ledger.get(prior)
    prior_paragraphs = _read_statement_bounded(root, prior)
    if prior_row is None or prior_paragraphs is None or not prior_paragraphs:
        return statement, empty_comparison
    prior_url = _admit_statement_url(prior_row.get("url"), prior)
    if prior_url is None:
        return statement, empty_comparison

    diff = fomc_diff.diff_statements(prior_paragraphs, paragraphs)
    hl = [
        row for row in fomc_diff.highlights(diff, limit=6)
        if (row.get("removed_text") or row.get("added_text"))
    ]
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
