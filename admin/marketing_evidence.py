"""Read-only editorial projections over existing marketing records.

These labels do not change the outbox state machine. In particular, its legacy
``posted`` state can mean provider acceptance, not public X confirmation.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit


def _timestamp(value: object) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value or "").replace("Z", "+00:00"))
        return stamp.replace(tzinfo=timezone.utc) if stamp.tzinfo is None else stamp.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        return None


def x_permalink(value: object) -> str | None:
    """Accept only a public status URL; a provider ID is not an X receipt."""
    try:
        url = urlsplit(str(value or "").strip())
        if (url.scheme != "https" or url.username or url.password or url.port is not None
                or url.hostname not in {"x.com", "www.x.com", "twitter.com",
                                        "www.twitter.com", "mobile.twitter.com"}):
            return None
        path = url.path.rstrip("/")
        if not re.fullmatch(r"/(?:[A-Za-z0-9_]{1,15}|i/web)/status/[1-9][0-9]*(?:/(?:photo|video)/[1-4])?", path):
            return None
        return "https://x.com" + path
    except (TypeError, ValueError):
        return None


def delivery_evidence(status: str, receipt: Any = None, metrics: Any = None,
                      *, now: datetime | None = None) -> dict:
    """Describe what an existing receipt proves, without inferring delivery time."""
    rec = receipt if isinstance(receipt, dict) else {}
    met = metrics if isinstance(metrics, dict) else {}
    now = _timestamp(now) or datetime.now(timezone.utc)
    url = next((safe for raw in (rec.get("external_url"), rec.get("url"),
                                 met.get("external_url")) if (safe := x_permalink(raw))), None)
    result = {"state": "unconfirmed", "label": "Delivery unconfirmed",
              "confirmed": False, "url": None, "scheduled_at": None}
    # A recalled/failed/in-flight row cannot inherit an earlier receipt's success.
    if status == "posted" and url:
        return result | {"state": "confirmed", "label": "Confirmed on X",
                         "confirmed": True, "url": url}
    if status == "posting":
        return result | {"state": "sending", "label": "Sending · outcome pending"}
    if status != "posted":
        return result | {"state": "not_submitted", "label": "Not submitted"}
    if str(rec.get("backend") or "").lower() == "buffer" and rec.get("external_id"):
        booked = _timestamp(rec.get("booked_at"))
        if booked and booked > now:
            return result | {"state": "scheduled", "label": "Scheduled with Buffer",
                             "scheduled_at": booked.isoformat()}
        return result | {"state": "accepted", "label": "Accepted by Buffer · confirmation pending"}
    return result


def delivery_summary(rows: list[dict]) -> dict:
    """Count unique folded items, never a truncated history or transition count."""
    unique = {str(row.get("id")): row for row in rows if row.get("id")}
    counts = {key: 0 for key in ("confirmed", "scheduled", "accepted", "sending", "unconfirmed")}
    for row in unique.values():
        state = (row.get("delivery") or {}).get("state")
        if state in counts:
            counts[state] += 1
    return counts | {"pending_confirmation": counts["scheduled"] + counts["accepted"] + counts["unconfirmed"],
                     "scope": "all_recorded_items", "publication_time_known": False}


def editorial_review(source: Any) -> dict:
    """Only the existing advisory review crosses the admin boundary, bounded."""
    review = source.get("review") if isinstance(source, dict) else None
    if not isinstance(review, dict):
        return {}
    verdict = str(review.get("verdict") or "weak")
    issues = review.get("issues")
    return {"review": {
        "verdict": verdict if verdict in {"good", "weak", "bad", "pass", "reject"} else "weak",
        "issues": [str(x)[:180] for x in issues[:5]] if isinstance(issues, list) else [],
        "note": str(review.get("note") or "")[:400],
    }}


def retry_freshness(item: dict, *, now: datetime | None = None) -> dict:
    """Apply incumbent age budgets to a failed item's original evidence.

    An administrative retry does not refresh market evidence. This projection
    neither expires an item nor rewrites its source. Unscoped lanes keep their
    existing publisher checks; no new universal TTL is invented here.
    """
    from engine.marketing import outbox

    now = _timestamp(now) or datetime.now(timezone.utc)
    provenance = str(item.get("provenance") or "")
    result = {"eligible": True, "state": "unscoped", "reason": "Publisher freshness checks still apply."}
    if provenance == "content_studio":
        stamp = _timestamp(item.get("scheduled_at"))
        hours = outbox._STALE_QUEUED_HOURS
    elif provenance in outbox._WIRE_PROVENANCES:
        stamp = _timestamp(item.get("created_at")) or _timestamp(item.get("as_of"))
        hours = outbox._WIRE_TTL_HOURS_BY_KIND.get(str(item.get("kind") or ""), outbox._WIRE_TTL_HOURS_DEFAULT)
    else:
        return result
    if stamp is None:
        return result | {"eligible": False, "state": "unknown",
                         "reason": "Source time is missing. Review the evidence before retrying."}
    stale = now - stamp > timedelta(hours=hours)
    return {"eligible": not stale, "state": "stale" if stale else "current",
            "reason": ("Needs refreshed evidence. The original post is too old to retry."
                       if stale else "Within this lane's original freshness window."),
            "evidence_at": stamp.isoformat(), "max_age_hours": hours}
