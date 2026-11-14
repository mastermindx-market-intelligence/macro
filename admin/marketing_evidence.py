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


def delivery_records(root: Any) -> dict[str, dict]:
    """Use the incumbent telemetry fold, including its monotonic send evidence."""
    from engine.marketing.telemetry import delivery_projection

    projected = delivery_projection(root)
    # The additive metrics-observation producer is Buffer-specific. A coincident
    # remote id from another backend cannot borrow that provider's observation.
    return {str(row["id"]): row for row in projected.get("items", [])
            if isinstance(row, dict) and row.get("id") and row.get("backend") == "buffer"}


def delivery_evidence(status: str, receipt: Any = None, metrics: Any = None,
                      *, projection: Any = None, now: datetime | None = None) -> dict:
    """Describe what an existing receipt proves, without inferring delivery time."""
    rec = receipt if isinstance(receipt, dict) else {}
    met = metrics if isinstance(metrics, dict) else {}
    evidence = projection if isinstance(projection, dict) else {}
    if str(rec.get("backend") or "").lower() != "buffer":
        evidence = {}
        met = {}  # the incumbent metrics ledger contains Buffer remote IDs
    now = _timestamp(now) or datetime.now(timezone.utc)
    external_candidates = (rec.get("external_url"), rec.get("url"))
    if evidence.get("state") != "unknown_degraded":
        external_candidates = (evidence.get("external_url"), *external_candidates,
                               met.get("external_url"))
    url = next((safe for raw in external_candidates if (safe := x_permalink(raw))), None)
    result = {"state": "unconfirmed", "label": "Delivery unconfirmed",
              "confirmed": False, "url": None, "scheduled_at": None,
              "provider_sent": None, "confirmed_at": None,
              "provider_sent_at": None, "channel_ready": None, "detail": "",
              "observation_stale": False, "observed_at": None,
              "visibility_checked_at": None, "provider_status": None,
              "scheduling_type": None, "notification_status": None}
    # A recalled/failed/in-flight row cannot inherit an earlier receipt's success.
    if status == "posting":
        return result | {"state": "sending", "label": "Sending · outcome pending"}
    if status != "posted":
        return result | {"state": "not_submitted", "label": "Not submitted"}
    result["url"] = url
    if evidence:
        if str(evidence.get("provider_id") or "") != str(rec.get("external_id") or ""):
            return result | {"state": "degraded", "label": "Delivery check incomplete", "url": None}
        result.update(observed_at=evidence.get("observed_at"),
                      observation_stale=evidence.get("observation_stale") is True,
                      provider_sent=evidence.get("provider_sent"),
                      provider_sent_at=evidence.get("provider_sent_at"),
                      channel_ready=evidence.get("channel_ready"),
                      provider_status=str(evidence.get("provider_status") or "")[:48] or None,
                      scheduling_type=str(evidence.get("scheduling_type") or "")[:48] or None,
                      notification_status=str(evidence.get("notification_status") or "")[:48] or None)
        publishing_error = evidence.get("publishing_error")
        result["detail"] = str(evidence.get("latest_lookup_error") or
            (publishing_error.get("message") if isinstance(publishing_error, dict) else "") or "")[:400]
        if evidence.get("state") == "provider_sent" and evidence.get("provider_sent") is True:
            try:
                visible_at = datetime.fromisoformat(str(evidence.get("x_visible_at") or "").replace("Z", "+00:00"))
                visible_at = visible_at.astimezone(timezone.utc) if visible_at.tzinfo is not None else None
            except (TypeError, ValueError, OverflowError):
                visible_at = None
            # A permalink and engagement metrics are not visibility attestations.
            # This distinct rung belongs to the existing telemetry/verifier owner.
            if visible_at and visible_at <= now:
                result["visibility_checked_at"] = visible_at.isoformat()
            if evidence.get("x_visible") is True and result["visibility_checked_at"] and url:
                return result | {"state": "confirmed", "label": "Observed on X",
                                 "confirmed": True, "confirmed_at": visible_at.isoformat()}
            if evidence.get("x_visible") is False and result["visibility_checked_at"]:
                return result | {"state": "not_visible", "label": "Not visible at the last X check"}
            return result | {"state": "provider_sent", "label": "Provider reports sent · visibility unverified"}
        if evidence.get("state") == "provider_failed":
            return result | {"state": "failed", "label": "Provider reports failed"}
        if evidence.get("state") == "unknown_degraded":
            return result | {"state": "degraded", "label": "Delivery check incomplete"}
    if str(rec.get("backend") or "").lower() == "buffer" and rec.get("external_id"):
        booked = _timestamp(evidence.get("due_at") if evidence else rec.get("booked_at"))
        observed_schedule = (evidence.get("provider_status") == "scheduled"
            and evidence.get("scheduling_type") == "automatic"
            and evidence.get("channel_ready") is not False)
        if booked and booked > now and (not evidence or observed_schedule):
            return result | {"state": "scheduled", "label": "Scheduled with Buffer",
                             "scheduled_at": booked.isoformat()}
        if url and not evidence.get("observed_at"):
            return result | {"state": "linked", "label": "X link recorded · visibility unverified"}
        return result | {"state": "accepted", "label": "Accepted by Buffer · confirmation pending"}
    if url:
        return result | {"state": "linked", "label": "X link recorded · visibility unverified"}
    return result


def delivery_summary(rows: list[dict]) -> dict:
    """Count unique folded items, never a truncated history or transition count."""
    unique = {str(row.get("id")): row for row in rows if row.get("id")}
    counts = {key: 0 for key in ("confirmed", "provider_sent", "linked", "scheduled", "accepted",
                                "sending", "unconfirmed", "failed", "degraded", "not_visible")}
    for row in unique.values():
        state = (row.get("delivery") or {}).get("state")
        if state in counts:
            counts[state] += 1
    pending = sum(counts[key] for key in ("scheduled", "accepted", "unconfirmed", "linked", "provider_sent"))
    return counts | {"pending_confirmation": pending,
                     "needs_delivery_check": pending + counts["failed"] + counts["degraded"] + counts["not_visible"],
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
