"""Publish the completed-session under-index readout using incumbent stores."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from engine.prophet_under_index import ELEVEN, LIMIT, METHOD, SECTORS, daily_fields, member_counts
from lib.nyse_calendar import expected_last_session, is_session

ROOT = Path(__file__).resolve().parents[1]


def load_close(price_dir: Path, ticker: str) -> pd.Series:
    frame = pd.read_parquet(price_dir / f"{ticker}.parquet")
    # Yahoo collector stores dividend-adjusted close separately from close_price.
    values = pd.to_numeric(frame["close"], errors="coerce")
    values.index = pd.to_datetime(values.index)
    values = values.sort_index()
    if not values.index.is_unique or values.index.tz is not None:
        raise ValueError("price dates must be unique and timezone-naive")
    return values[np.isfinite(values) & (values > 0)]


def build(root: Path = ROOT, now: datetime | None = None) -> dict:
    expected = pd.Timestamp(expected_last_session(now))
    price_dir = root / "data/yahoo"
    raw = {ticker: load_close(price_dir, ticker) for ticker in (*ELEVEN, "SPY")}
    calendar = pd.DatetimeIndex(sorted(set().union(*(set(raw[t].index) for t in ELEVEN))))
    calendar = calendar[(calendar >= "2018-06-19") & (calendar <= expected)]
    calendar = calendar[[is_session(d.date()) for d in calendar]]
    if calendar.empty:
        raise ValueError("no completed panel session")
    close = pd.DataFrame({t: raw[t].reindex(calendar) for t in ELEVEN})
    fields = daily_fields(close, raw["SPY"])
    row = json.loads(fields.tail(1).to_json(orient="records", date_format="iso", double_precision=15))[0]
    as_of = calendar[-1]
    # Never disguise a stale or partial live panel as today's description.
    fresh = as_of == expected and all(as_of in s.index for s in raw.values())
    if not fresh:
        row["reader_state"] = "n/a"
        row["display_form"] = "unavailable"
    membership = json.loads((root / "data/baskets/membership.json").read_text())["baskets"]
    drill = []
    for proxy, name in SECTORS.items():
        baskets = [b for key, b in membership.items()
                   if key.startswith("us_sector_") and b.get("etf_proxy") == proxy]
        if len(baskets) != 1:
            raise ValueError("one incumbent sector basket required per sector")
        members = [m["ticker"] for m in baskets[0]["members"]
                   if m.get("added", "0001-01-01") <= str(as_of.date())
                   and (not m.get("removed") or m["removed"] > str(as_of.date()))]
        prices = {}
        for ticker in members:
            if (price_dir / f"{ticker}.parquet").is_file():
                prices[ticker] = load_close(price_dir, ticker)
        drill.append({"sector": name, **member_counts(prices, members, calendar, as_of)})
    return {"schema": "prophet.under_index/v1", "date": str(as_of.date()),
            "expected_completed_session": str(expected.date()), "fresh": fresh,
            "basis": "screen readout; not research evidence", "method_label": METHOD,
            "limit_line": LIMIT, "description": "description only",
            "reader_state_method": "reader state; fixed visible rule; description only; nothing joined",
            "definitions": "EMITTER_SPEC rev 2 (2026-11-13)", **row, "sectors": drill}


def main():
    payload = build(now=datetime.now(timezone.utc))
    target = ROOT / "site/prophet/under_index.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, target)


if __name__ == "__main__":
    main()
