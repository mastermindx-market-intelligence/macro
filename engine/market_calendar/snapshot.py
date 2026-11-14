"""Producer-only schedule and reference enrichment; never imported by the API."""
from __future__ import annotations
from datetime import date, datetime
from pathlib import Path
from app.market_calendar_contracts import day, number, NY


def official_schedule(start: str, end: str, now: datetime) -> dict:
    # Reuse the existing network-free schedule owner inside the fresh oneshot.
    from scripts.watch_release_publications import scheduled_releases, schedule_coverage
    begin, finish = date.fromisoformat(start), date.fromisoformat(end)
    fields = ("event_id", "type", "date", "label", "label_zh", "schedule_source", "scheduled_at")
    rows = [{key: row.get(key) for key in fields}
            for row in scheduled_releases(begin, (finish - begin).days)]
    return {"schema": "market-calendar.official-schedule.v1", "status": "ok",
            "from": start, "to": end, "asOf": now.isoformat(), "rows": rows,
            "coverage": schedule_coverage(now.astimezone(NY).date(), 140)}

def reference_metadata(root: Path) -> dict[str, dict]:
    """Read the incumbent partial GICS cache; never fan out to per-company APIs."""
    path = root / "data/polygon_universe/reference.parquet"
    if not path.exists():
        return {}
    try:
        import pandas as pd
        frame = pd.read_parquet(path)
        if len(frame) > 25000:
            return {}
        result = {}
        for ticker, row in frame.iterrows():
            key = str(row.get("ticker", ticker))
            sector = row.get("gics_sector")
            result[key] = {"sector": str(sector) if pd.notna(sector) else None}
        return result
    except (OSError, ValueError, KeyError, ImportError):
        return {}


def enrich(events: list[dict], ratios: dict, reference: dict) -> list[dict]:
    # Use the existing case-exact vendor identity mapping. TPC != TpC.
    from lib.massive_ticker import vendor_join_key
    by_symbol = {vendor_join_key(key): row for key, row in ratios.items()}
    sectors = {vendor_join_key(key): row for key, row in reference.items()}
    names = {event["symbol"]: event["name"] for event in events if event["kind"] == "earnings"}
    for event in events:
        if not event.get("symbol"):
            continue
        key = vendor_join_key(event["symbol"])
        metadata = by_symbol.get(key, {})
        event["sector"] = sectors.get(key, {}).get("sector")
        if (event["kind"] == "dividends" or event["marketCap"] is None or event.get("capAsOf")) and number(metadata.get("market_cap")) is not None:
            cap = number(metadata["market_cap"])
            if cap is not None and cap >= 0:
                event.update({"marketCap": cap, "capCurrency": "USD", "capAsOf": day(metadata.get("date"))})
        if event["kind"] == "dividends":
            event["name"] = names.get(event["symbol"], event["name"])
            event["dividend"]["yield"] = number(metadata.get("dividend_yield"))
            event["dividend"]["yieldAsOf"] = day(metadata.get("date"))
    return events

