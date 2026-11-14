"""Publish the native calendar through the incumbent VPS snapshot lane.

No new timer, queue, auth, credential resolver or public provider artifact.
Earnings partitions refresh independently; successful pages never imply an
exhaustive worldwide universe. Failed refreshes preserve their last-good clocks.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.market_calendar.contracts import SCHEMA, NY, MAX_EVENTS, reconcile_events  # noqa: E402
from engine.market_calendar.providers import SourceFailure, dividends, massive_pages, yahoo_earnings, yahoo_economics  # noqa: E402
from engine.market_calendar.snapshot import enrich, reference_metadata, official_schedule
from app.market_calendar_projection import age_seconds, read_json  # noqa: E402
from lib.config import secret  # noqa: E402
from scripts.vps_live_orchestrator import atomic_write_json  # noqa: E402


def _daily_partitions(previous: dict, key: str, start) -> dict:
    result = {}
    for offset in range(84):
        day = (start + timedelta(days=offset)).isoformat()
        result[day] = {**previous.get(key, {}).get(day, {}), "from": day, "to": day}
    return result


def _progress(value: object, now: datetime) -> dict | None:
    return value if isinstance(value, dict) and age_seconds(value.get("asOf"), now) <= 10800 else None


def _acquire_yahoo(partitions: dict, events: list, now: datetime, deadline: float,
                   economic: bool, restricted: dict | None) -> tuple[list, dict | None]:
    observed, today = now.isoformat(), now.astimezone(NY).date()
    # Oldest attempt first prevents one failing nearby date monopolizing the lane.
    order = sorted(partitions.values(), key=lambda p: (
        p.get("lastAttempt") or "", abs((datetime.fromisoformat(p["from"]).date() - today).days)))
    for part in order:
        if restricted or time.monotonic() >= deadline - 1:
            break
        distance = (datetime.fromisoformat(part["from"]).date() - today).days
        near = -1 <= distance <= 2 if economic else -2 <= distance <= 10
        cadence = 300 if part.get("status") != "ok" else (300 if economic else 900) if near else 10800
        if age_seconds(part.get("lastAttempt"), now) < cadence:
            continue
        part["lastAttempt"] = observed
        try:
            fetch = yahoo_economics if economic else yahoo_earnings
            batch, meta = fetch(part["from"], part["to"], observed, deadline,
                                resume=_progress(part.get("_resume"), now))
            part["_resume"] = meta.pop("_resume", None)
            publish = not meta.get("discard") and (meta["complete"] or (batch and not part.get("completeAsOf")))
            if publish:
                events = [e for e in events if not (
                    (e["source"] == "yahoo-economic" if economic else e["kind"] == "earnings")
                    and part["from"] <= e["date"] <= part["to"])] + batch
                part.update({**meta, "asOf": meta.get("asOf") or observed, "records": len(batch),
                             "status": "ok" if meta["complete"] else "partial"})
                if meta["complete"]:
                    part["completeAsOf"] = part["asOf"]
            else:
                part.update({"status": "stale" if part.get("asOf") else "unavailable",
                             "error": meta.get("error", "partial_refresh")})
        except Exception as exc:
            code = str(exc) if isinstance(exc, SourceFailure) else "provider_unavailable"
            part.update({"status": "restricted" if code == "restricted" else "stale" if part.get("asOf") else "unavailable", "error": code})
            if code == "restricted":
                restricted = {"observedAt": observed, "error": code}
                break
    return events, restricted


def build(previous: dict, now: datetime, root: Path = ROOT, budget: float = 36) -> dict:
    now = now.astimezone(timezone.utc)
    observed = now.isoformat()
    today = now.astimezone(NY).date()
    monday = today - timedelta(days=today.weekday())
    start, end = monday - timedelta(days=14), monday + timedelta(days=69)
    deadline = time.monotonic() + budget
    try:
        schedule = official_schedule(start.isoformat(), end.isoformat(), now)
    except Exception:
        schedule = {**previous.get("_official_schedule", {}), "status": "unavailable"}
    prior_events = previous.get("events", []) if previous.get("schema") == SCHEMA else []
    yahoo_restricted = previous.get("_yahoo_restricted")
    events = [dict(e) for e in prior_events if isinstance(e, dict) and start.isoformat() <= e.get("date", "") <= end.isoformat()]
    partitions = _daily_partitions(previous, "_partitions", start)
    economic_partitions = _daily_partitions(previous, "_economic_partitions", start)
    # Reserve time for every source. Partial pages persist privately across runs.
    events, yahoo_restricted = _acquire_yahoo(partitions, events, now,
        deadline - budget * 22/36, False, yahoo_restricted)
    events, yahoo_restricted = _acquire_yahoo(economic_partitions, events, now,
        deadline - budget * 12/36, True, yahoo_restricted)
    key = secret("POLYGON_API_KEY") or secret("MASSIVE_API_KEY")
    old_sources = {s["id"]: s for s in previous.get("sources", [])}
    dividend_source = dict(old_sources.get("massive", {}))
    ratios_source = dict(old_sources.get("ratios", {}))
    ratios = previous.get("_ratios", {})
    resumes = dict(previous.get("_massive_progress", {}))
    for source in (dividend_source, ratios_source):
        source.setdefault("status", "not_configured" if not key else "unavailable")
    changed_range = dividend_source.get("from") != start.isoformat() or dividend_source.get("to") != end.isoformat()
    dividend_deadline = deadline - budget * 6/36
    if key and dividend_source["status"] != "restricted" and (changed_range or age_seconds(dividend_source.get("lastAttempt"), now) >= (86400 if dividend_source["status"] == "ok" else 300)) and time.monotonic() < dividend_deadline - 1:
        dividend_source["lastAttempt"] = observed
        try:
            batch, meta = dividends(start.isoformat(), end.isoformat(), observed, key, dividend_deadline,
                                   resume=_progress(resumes.get("dividends"), now))
            resumes["dividends"] = meta.pop("_resume", None)
            if not meta.get("discard") and (meta["complete"] or (batch and not dividend_source.get("completeAsOf"))):
                events = [e for e in events if e["kind"] != "dividends"] + batch
                dividend_source.update({**meta, "asOf": meta.get("asOf") or observed,
                    "from": start.isoformat(), "to": end.isoformat(), "status": "ok" if meta["complete"] else "partial"})
                if meta["complete"]:
                    dividend_source["completeAsOf"] = dividend_source["asOf"]
            else:
                dividend_source["status"] = "stale" if dividend_source.get("asOf") else "unavailable"
        except Exception as exc:
            code = str(exc) if isinstance(exc, SourceFailure) else "provider_unavailable"
            dividend_source.update({"status": "restricted" if code == "restricted" else "stale" if dividend_source.get("asOf") else "unavailable", "error": code})
    if key and ratios_source["status"] != "restricted" and age_seconds(ratios_source.get("lastAttempt"), now) >= (86400 if ratios_source["status"] == "ok" else 300) and time.monotonic() < deadline - 1:
        ratios_source["lastAttempt"] = observed
        try:
            rows, meta = massive_pages("/stocks/financials/v1/ratios", {"limit": 5000}, key, deadline,
                                      resume=_progress(resumes.get("ratios"), now), observed_at=observed)
            resumes["ratios"] = meta.pop("_resume", None)
            if not meta.get("discard") and (meta["complete"] or (rows and not ratios_source.get("completeAsOf"))):
                ratios = {str(row["ticker"]): {k: row.get(k) for k in ("market_cap", "date", "dividend_yield")}
                          for row in rows if row.get("ticker")}
                ratios_source.update({**meta, "asOf": meta.get("asOf") or observed,
                                     "status": "ok" if meta["complete"] else "partial"})
                if meta["complete"]:
                    ratios_source["completeAsOf"] = ratios_source["asOf"]
            else:
                ratios_source["status"] = "stale" if ratios else "unavailable"
        except Exception as exc:
            code = str(exc) if isinstance(exc, SourceFailure) else "provider_unavailable"
            ratios_source.update({"status": "restricted" if code == "restricted" else "stale" if ratios else "unavailable", "error": code})
    events = reconcile_events(events, prior_events, observed)
    events = enrich(events, ratios, reference_metadata(root))
    completed = [p for p in partitions.values() if p.get("asOf")]
    all_ok = all(p.get("status") == "ok" for p in partitions.values())
    earnings_status = "ok" if all_ok else "partial" if completed else "unavailable"
    if yahoo_restricted:
        earnings_status = "restricted"
    economic_observed = [p for p in economic_partitions.values() if p.get("asOf")]
    common = {"from": start.isoformat(), "to": end.isoformat(), "expectedRecords": None, "pages": 0, "asOf": None, "lastAttempt": None}
    sources = [
        {**common, "id": "yahoo", "name": "Yahoo Finance", "kinds": ["earnings"], "status": earnings_status,
         "asOf": min((p["asOf"] for p in completed), default=None),
         "lastAttempt": max((p.get("lastAttempt", "") for p in partitions.values()), default=None) or None,
         "records": sum(e["kind"] == "earnings" for e in events),
         "pages": sum(p.get("pages", 0) for p in partitions.values()),
         "cadence": "Reports from two days ago through ten days ahead: 15 minutes; other dates: 3 hours. Provider latency is not guaranteed.",
         "note": f"{sum(bool(p.get('completeAsOf')) for p in partitions.values())}/{len(partitions)} daily windows completed; {len(completed)} observed. Provider US universe; no active-stock or cap cutoff. Confirmation, EPS basis, currency and revenue are not supplied."},
        {**common, "id": "yahoo-economic", "name": "Yahoo economic calendar", "kinds": ["economics"],
         "status": "restricted" if yahoo_restricted else "ok" if all(p.get("status") == "ok" for p in economic_partitions.values()) else "partial" if economic_observed else "unavailable",
         "asOf": min((p["asOf"] for p in economic_observed), default=None),
         "lastAttempt": max((p.get("lastAttempt", "") for p in economic_partitions.values()), default=None) or None,
         "records": sum(e["source"] == "yahoo-economic" for e in events),
         "pages": sum(p.get("pages", 0) for p in economic_partitions.values()),
         "cadence": "Yesterday through two days ahead: every five minutes; other dates: every three hours. Provider latency is not guaranteed.",
         "note": f"{sum(bool(p.get('completeAsOf')) for p in economic_partitions.values())}/84 daily windows completed; {len(economic_observed)} observed. Provider country coverage, not a global completeness guarantee. Raw actual, consensus, prior and originally reported values are preserved; units and importance are not supplied. Official verification stays with the existing watcher."},
        {**common, **dividend_source, "id": "massive", "name": "Massive dividends", "kinds": ["dividends"],
         "records": sum(e["kind"] == "dividends" for e in events), "cadence": "Provider updated daily; refreshed daily",
         "note": "Declared cash dividends by ex-date. Original currency is preserved. Payment and record-date views include only the acquired ex-date window and may be incomplete."},
        {**common, **ratios_source, "id": "ratios", "name": "Massive capitalization", "kinds": ["earnings", "dividends"],
         "records": len(ratios), "cadence": "Provider daily snapshot; refreshed daily",
         "note": "Cap and provider dividend yield retain their observation date. Sector coverage uses the existing partial GICS cache."},
    ]
    return {"schema": SCHEMA, "asOf": observed, "from": start.isoformat(), "to": end.isoformat(),
            "events": events, "sources": sources, "_partitions": partitions, "_economic_partitions": economic_partitions, "_ratios": ratios,
            "_yahoo_restricted": yahoo_restricted, "_official_schedule": schedule, "_massive_progress": resumes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    args = parser.parse_args()
    snapshot = build(read_json(args.previous), datetime.now(timezone.utc))
    # Selection must remain readable. The HTTP projection pages at 2,000 rows;
    # this gate protects the complete private input and preserves last-good.
    if len(snapshot["events"]) > MAX_EVENTS or len(json.dumps(snapshot).encode()) > 24 * 1024 * 1024:
        raise ValueError("calendar publication exceeds bounded artifact capacity")
    atomic_write_json(args.out, snapshot, mode=0o640)
    print(json.dumps({"schema": SCHEMA, "events": len(snapshot["events"]),
                      "sources": {s["id"]: s["status"] for s in snapshot["sources"]}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
