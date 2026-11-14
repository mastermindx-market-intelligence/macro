"""Pure calendar schema and value helpers shared by producer and API projection."""
from __future__ import annotations

import hashlib
import math
import re
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

SCHEMA = "market-calendar.v1"
MAX_BYTES = 8 * 1024 * 1024
MAX_EVENTS = 20000
NY = ZoneInfo("America/New_York")
SYMBOL = re.compile(r"^[A-Za-z0-9^][A-Za-z0-9.^=/\-]{0,31}$")


def number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def text(value: Any, limit: int = 240) -> str:
    return str(value).strip()[:limit] if value is not None else ""


def day(value: Any) -> str | None:
    candidate = text(value, 10)
    try:
        return date.fromisoformat(candidate).isoformat() if len(candidate) == 10 else None
    except ValueError:
        return None


def stamp(value: Any) -> str | None:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).isoformat() if dt.tzinfo else None
    except (TypeError, ValueError):
        return None


def source_url(value: Any) -> str | None:
    candidate = text(value, 1000)
    parsed = urlsplit(candidate)
    if parsed.scheme != "https" or parsed.username or parsed.password:
        return None
    allowed = {"finance.yahoo.com", "massive.com", "www.federalreserve.gov", "www.bls.gov",
               "www.bea.gov", "apps.bea.gov", "www.dol.gov", "fred.stlouisfed.org"}
    return candidate if parsed.hostname in allowed else None


def event_id(provider: str, identity: str) -> str:
    return provider + ":" + hashlib.sha256(identity.encode()).hexdigest()[:24]


def base_event(kind: str, identity: str, event_day: str, name: str,
               provider: str, observed_at: str, symbol: str | None = None) -> dict:
    return {
        "id": identity, "kind": kind, "symbol": symbol, "name": text(name), "nameZh": None,
        "date": event_day, "scheduledAt": None, "timezone": "America/New_York",
        "session": "unknown", "confirmation": "unknown", "status": "scheduled",
        "marketCap": None, "capCurrency": None, "capAsOf": None, "sector": None,
        "country": "US", "source": provider, "sourceUrl": None, "observedAt": observed_at,
        "updatedAt": None, "sourceLabel": None, "importance": "unknown",
        "earnings": None, "dividend": None, "economic": None,
        "scheduleConflict": False, "alternateDates": [], "changes": [],
    }

