"""Calendar composition using existing source artifacts and source-specific clocks."""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from app.market_calendar_contracts import NY, base_event, day, number, source_url, stamp, text

OFFICIAL_URLS = {
    "FOMC": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    "CPI": "https://www.bls.gov/schedule/news_release/cpi.htm",
    "PPI": "https://www.bls.gov/schedule/news_release/ppi.htm",
    "NFP": "https://www.bls.gov/schedule/news_release/empsit.htm",
    "GDP": "https://www.bea.gov/news/schedule",
    "PCE": "https://www.bea.gov/news/schedule",
    "CLAIMS": "https://www.dol.gov/ui/data.pdf",
}


def read_json(path: Path, limit: int = 24 * 1024 * 1024) -> dict:
    try:
        if path.stat().st_size > limit:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def age_seconds(value: object, now: datetime) -> float:
    parsed = stamp(value)
    return max(0, (now - datetime.fromisoformat(parsed)).total_seconds()) if parsed else float("inf")


def economic_events(snapshot: dict, start: str, end: str, now: datetime, publications: dict) -> tuple[list[dict], dict]:
    # The fresh producer projects the existing schedule owner. The API only
    # overlays the current publication sidecar, without importing producer code.
    today = now.astimezone(NY).date()
    observed = now.isoformat()
    schedule_state = snapshot.get("_official_schedule") or {}
    schedule = [row for row in schedule_state.get("rows", []) if isinstance(row, dict)
                and row.get("type") in OFFICIAL_URLS and row.get("event_id")
                and day(row.get("date")) and start <= row["date"] <= end
                and isinstance(row.get("label"), str)]
    lifecycle = {}
    if publications.get("schema") == "release_publications.v2":
        for row in list(publications.get("publications") or []) + list(publications.get("events") or []):
            if isinstance(row, dict) and row.get("event_id"):
                lifecycle[row["event_id"]] = row
    result = []
    for row in schedule:
        publication = lifecycle.get(row["event_id"], {})
        event = base_event("economics", "official:" + row["event_id"], row["date"], row["label"], "official", observed)
        computed = row.get("schedule_source") == "computed"
        event.update({"nameZh": row.get("label_zh"), "scheduledAt": stamp(row.get("scheduled_at")),
                      "session": "scheduled_time", "confirmation": "estimated" if computed or row["type"] == "FOMC" else "confirmed",
                      "sourceUrl": OFFICIAL_URLS.get(row["type"]),
                      "sourceLabel": row["type"], "importance": "medium" if row["type"] == "CLAIMS" else "high",
                      "updatedAt": stamp(publication.get("verified_at")),
                      "observedAt": stamp(publications.get("built")) or stamp(schedule_state.get("asOf"))})
        actual = publication.get("actual") if publication.get("data_ready") is True else None
        actual = actual if isinstance(actual, dict) else {}
        metrics = [{"id": text(m.get("metric_id"), 80), "value": number(m.get("value")),
                    "unit": text(m.get("unit"), 40), "period": text(m.get("period"), 80) or None}
                   for m in actual.get("metrics", []) if isinstance(m, dict) and number(m.get("value")) is not None][:12]
        if row["type"] == "FOMC" and actual and not metrics:
            metrics = [{"id": name, "value": number(actual[name]), "unit": "percent", "period": None}
                       for name in ("target_low", "target_high") if number(actual.get(name)) is not None]
        first = metrics[0] if metrics else {}
        previous_key = {"GDP": "prior_real_gdp_annualized", "CLAIMS": "prior_initial_claims"}.get(row["type"])
        prior = number(actual.get(previous_key)) if previous_key else None
        event["economic"] = {"actual": None if row["type"] == "FOMC" else first.get("value"), "consensus": None, "previous": prior,
                             "unit": first.get("unit"), "period": first.get("period"), "metrics": metrics,
                             "headline": text(actual.get("headline_en"), 600) or None,
                             "headlineZh": text(actual.get("headline_zh"), 600) or None}
        if actual:
            event["status"] = "reported"
            event["sourceUrl"] = source_url(actual.get("source_url")) or event["sourceUrl"]
        elif row["date"] < today.isoformat() or event["scheduledAt"] and event["scheduledAt"] < observed:
            event["status"] = "results_pending"
        result.append(event)
    coverage = schedule_state.get("coverage") or {"status": "unavailable"}
    unhealthy = any(isinstance(item, dict) and item.get("status") in {"error", "unavailable", "failed"}
                    for item in publications.get("source_health", []))
    return result, {"id": "official", "name": "Official economic releases", "kinds": ["economics"],
                    "status": ("unavailable" if not schedule_state.get("asOf") else
                               "partial" if unhealthy or schedule_state.get("status") != "ok" else
                               "ok" if age_seconds(publications.get("built"), now) <= 300 and
                                       age_seconds(schedule_state.get("asOf"), now) <= 900 else "stale"),
                    "asOf": stamp(publications.get("built")), "lastAttempt": stamp(publications.get("built")),
                    "from": start, "to": end, "records": len(result), "pages": 1,
                    "expectedRecords": None, "cadence": "Scheduled releases: existing one-minute publication watcher",
                    "note": "Selected US official releases. Consensus is not supplied. Computed and tentative dates are labeled.",
                    "scheduleCoverage": coverage}


def public_view(snapshot: dict, now: datetime, publications: dict,
                requested_from: str | None = None, requested_to: str | None = None,
                offset: int = 0, revision: str | None = None) -> dict:
    from app.market_calendar_contracts import SCHEMA, MAX_EVENTS
    if snapshot.get("schema") != SCHEMA or not isinstance(snapshot.get("events"), list):
        raise ValueError("calendar unavailable")
    coverage_from, coverage_to = day(snapshot.get("from")), day(snapshot.get("to"))
    if not coverage_from or not coverage_to or len(snapshot["events"]) > MAX_EVENTS:
        raise ValueError("invalid calendar range")
    start, end = requested_from or coverage_from, requested_to or coverage_to
    # Both incumbent artifacts can rotate independently while a client pages.
    snapshot_id = hashlib.sha256(json.dumps([snapshot.get("asOf"), publications.get("built")]).encode()).hexdigest()
    if revision and revision != snapshot_id:
        raise ValueError("snapshot changed")
    events = [e for e in snapshot["events"] if e.get("source") != "official" and
              (start <= e["date"] <= end or e.get("dividend") and any(
                  start <= (e["dividend"].get(field) or "") <= end for field in ("payDate", "recordDate")))]
    economics, economic_source = economic_events(snapshot, start, end, now, publications)
    sources = [dict(s) for s in snapshot.get("sources", []) if s.get("id") != "official"]
    for source in sources:
        if source["status"] == "ok" and source["id"] in {"yahoo", "yahoo-economic"}:
            today = now.astimezone(NY).date()
            partition_key = "_economic_partitions" if source["id"] == "yahoo-economic" else "_partitions"
            parts = [p for p in snapshot.get(partition_key, {}).values() if p["from"] <= end and p["to"] >= start]
            if any(p.get("status") != "ok" for p in parts):
                source["status"] = "partial"
            elif any(age_seconds(p.get("asOf"), now) > (
                    (900 if source["id"] == "yahoo-economic" else 1800)
                    if ((-1 <= (date.fromisoformat(p["from"]) - today).days <= 2) if source["id"] == "yahoo-economic"
                        else (-2 <= (date.fromisoformat(p["from"]) - today).days <= 10)) else 14400) for p in parts):
                source["status"] = "stale"
        elif source["status"] == "ok" and age_seconds(source.get("asOf"), now) > 172800:
            source["status"] = "stale"
    sources.append(economic_source)
    ordered = sorted(events + economics, key=lambda e: (e["date"], e["id"]))
    if not 0 <= offset <= len(ordered):
        raise ValueError("invalid page")
    page = ordered[offset:offset + 2000]
    return {"schema": SCHEMA, "asOf": snapshot.get("asOf"), "from": start, "to": end,
            "coverageFrom": coverage_from, "coverageTo": coverage_to,
            "snapshotId": snapshot_id, "nextCursor": offset + len(page) if offset + len(page) < len(ordered) else None,
            "total": len(ordered),
            "timezone": "America/New_York", "scope": "Provider US earnings universe, declared dividends, provider country economic calendars and selected official US releases",
            "events": page,
            "sources": sources, "refreshAfterSeconds": 60, "exportAllowed": True}
