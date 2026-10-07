#!/usr/bin/env python3
"""PB-C retrospective Treasury sensitivity derivation; no production effects.

Source: Treasury's documented daily XML feeds. Fetches 2024/2025 nominal and
real yearly files, then derives exactly the parent protocol's 2-year nominal
and 10-year real 5-NYSE-session +25bp shocks, with 5/10-prior-session exposure
windows. Does not fetch FRED, Nasdaq, Cboe, issuer prices, or event outcomes.
Raw XML is task-local cache only. Published outputs contain derived flags and
source digests, not raw quotes. This is a current historical vintage, not a
reconstruction of original intraday availability or a validated signal.
"""

import argparse
import bisect
import csv
import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET

BASE = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
START, END, WARMUP = date(2025, 1, 1), date(2025, 12, 31), date(2024, 10, 1)
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
}
FEEDS = {
    "nominal2y": ("daily_treasury_yield_curve", "BC_2YEAR"),
    "real10y": ("daily_treasury_real_yield_curve", "TC_10YEAR"),
}
HOLIDAYS = {date.fromisoformat(s) for s in (
    "2024-11-28", "2024-12-25", "2025-01-01", "2025-01-09",
    "2025-01-20", "2025-02-17", "2025-04-18", "2025-05-26",
    "2025-06-19", "2025-07-04", "2025-09-01", "2025-11-27", "2025-12-25",
)}
EARLY_CLOSES = {date.fromisoformat(s) for s in (
    "2024-11-29", "2024-12-24", "2025-07-03", "2025-11-28", "2025-12-24",
)}
CALENDAR_SOURCES = [
    "https://ir.theice.com/press/news-details/2023/NYSE-Group-Announces-2024-2025-and-2026-Holiday-and-Early-Closings-Calendar/default.aspx",
    "https://ir.theice.com/press/news-details/2024/NYSE-Group-Announces-2025-2026-and-2027-Holiday-and-Early-Closings-Calendar/default.aspx",
    "https://ir.theice.com/press/news-details/2024/The-New-York-Stock-Exchange-Will-Close-Markets-on-January-9-to-Honor-the-Passing-of-Former-President-Jimmy-Carter-on-National-Day-of-Mourning/default.aspx",
]


def day_range(start, end):
    while start <= end:
        yield start
        start += timedelta(days=1)


def nyse_sessions():
    return [d for d in day_range(WARMUP, END) if d.weekday() < 5 and d not in HOLIDAYS]


def read_year(year, instrument, cache):
    feed, field = FEEDS[instrument]
    url = f"{BASE}?data={feed}&field_tdr_date_value={year}"
    cache_file = cache / f"{feed}_{year}.xml"
    cache_receipt = cache / f"{feed}_{year}.receipt.json"
    if cache_file.exists():
        if not cache_receipt.exists():
            raise ValueError("Cache has no receipt; inspect before reusing")
        body = cache_file.read_bytes()
        receipt = json.loads(cache_receipt.read_text())
        if hashlib.sha256(body).hexdigest() != receipt["response_sha256"]:
            raise ValueError("Cache digest mismatch")
    else:
        with urlopen(url, timeout=30) as response:
            body = response.read()
            status = response.status
        ET.fromstring(body)  # Verify XML before storing it.
        receipt = {
            "url": url, "http_status": status,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "response_bytes": len(body),
            "response_sha256": hashlib.sha256(body).hexdigest(),
        }
        cache_file.write_bytes(body)
        cache_receipt.write_text(json.dumps(receipt, indent=2) + "\n")
    root = ET.fromstring(body)
    entries = root.findall("atom:entry", NS)
    rows = []
    for entry in entries:
        prop = entry.find("atom:content/m:properties", NS)
        if prop is None:
            raise ValueError("XML entry has no properties")
        raw_date = prop.findtext("d:NEW_DATE", namespaces=NS)
        raw_value = prop.findtext("d:" + field, namespaces=NS)
        if not raw_date:
            raise ValueError("Entry lacks NEW_DATE")
        obs_date = date.fromisoformat(raw_date[:10])
        if raw_value is None or not raw_value.strip():
            raise ValueError(f"Missing {field} on {obs_date}; no silent fill")
        rows.append((obs_date, Decimal(raw_value)))
    dates = [x[0] for x in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("Duplicate Treasury observation dates")
    if not entries or any(d.year != year for d in dates):
        raise ValueError("Empty or wrong-year Treasury response")
    receipt.update({
        "instrument": instrument, "field": field, "xml_entries": len(entries),
        "first_date": min(dates).isoformat(), "last_date": max(dates).isoformat(),
    })
    return rows, receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(Path(__file__).parent))
    parser.add_argument("--protocol", default="/workspace/scratch/7a0bb715b184/pbc/PB_C_ANNOUNCEMENT_STUDY_PREREG.md")
    args = parser.parse_args()
    out = Path(args.out)
    cache = out / "local_inputs"
    out.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    protocol = Path(args.protocol)
    spec = {
        "derived_from_parent_protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "protocol_freeze_utc": "2026-10-07 02:58:22 UTC",
        "instruments": FEEDS,
        "window": [START.isoformat(), END.isoformat()], "warmup_start": WARMUP.isoformat(),
        "shock": "yield[t] - yield[t-5 NYSE sessions] >=0.25 percentage points, separately for each instrument",
        "session_alignment": "At each NYSE session, last Treasury observation date on/before session; preserve source age",
        "exposure": "At calendar date d, any shock on previous 5 or 10 NYSE sessions strictly before d",
        "onset": "Qualifying shock preceded by at least 10 consecutive non-shock NYSE sessions",
        "vintage": "Current retrieved historical values; original release timestamps/vintages not certified",
        "calendar_sources": CALENDAR_SOURCES,
        "draft_reconciliation": "A pre-protocol nominal-10y helper was interrupted (exit130), produced no rate/result artifact, and was replaced. Nominal10y is not used.",
    }
    (out / "treasury_stress_spec.json").write_text(json.dumps(spec, indent=2) + "\n")
    sessions = nyse_sessions()
    if sum(d.year == 2025 for d in sessions) != 250:
        raise ValueError("Unexpected 2025 NYSE session count")
    source_receipts, instrument_rows = [], {}
    for instrument in FEEDS:
        raw_rows = []
        for year in (2024, 2025):
            rows, receipt = read_year(year, instrument, cache)
            raw_rows.extend(rows)
            source_receipts.append(receipt)
        raw_rows = sorted((d, v) for d, v in raw_rows if WARMUP <= d <= END)
        source_dates = [d for d, _ in raw_rows]
        source_values = [v for _, v in raw_rows]
        aligned = []
        for session in sessions:
            ix = bisect.bisect_right(source_dates, session) - 1
            if ix < 0:
                raise ValueError("Insufficient source warmup")
            age = (session - source_dates[ix]).days
            if age > 7:
                raise ValueError("Source observation stale by more than 7 days")
            aligned.append({
                "date": session, "value": source_values[ix],
                "source_date": source_dates[ix], "source_age": age,
            })
        for ix, row in enumerate(aligned):
            row["change5_bp"] = None if ix < 5 else 100 * (row["value"] - aligned[ix - 5]["value"])
            row["shock"] = None if ix < 5 else int(row["change5_bp"] >= 25)
        for ix, row in enumerate(aligned):
            prior = aligned[max(0, ix - 10):ix]
            row["episode_onset"] = int(row["shock"] == 1 and len(prior) == 10 and all(r["shock"] == 0 for r in prior))
        instrument_rows[instrument] = aligned
    calendar = []
    for day in day_range(START, END):
        ix = bisect.bisect_left(sessions, day) - 1
        if ix < 10:
            raise ValueError("Insufficient session warmup")
        record = {
            "date": day.isoformat(), "is_nyse_session": day in sessions,
            "previous_nyse_session": sessions[ix].isoformat(),
        }
        for instrument, rows in instrument_rows.items():
            lagged = rows[ix]
            record[instrument] = {
                "source_observation_date": lagged["source_date"].isoformat(),
                "source_age_calendar_days_at_event": (day - lagged["source_date"]).days,
                "stress_any_prior5": int(any(r["shock"] for r in rows[ix - 4:ix + 1])),
                "stress_any_prior10": int(any(r["shock"] for r in rows[ix - 9:ix + 1])),
                "shock_at_previous_session": lagged["shock"],
                "episode_onset_at_previous_session": lagged["episode_onset"],
            }
        calendar.append(record)
    (out / "rates_sensitivity_stress_calendar.json").write_text(json.dumps(calendar, indent=2) + "\n")
    with (out / "nyse_calendar_2025.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["date", "weekday", "close_time_et"])
        writer.writeheader()
        writer.writerows({"date": d.isoformat(), "weekday": d.weekday(), "close_time_et": "13:00" if d in EARLY_CLOSES else "16:00"} for d in sessions if d.year == 2025)
    aggregate = {}
    for instrument, rows in instrument_rows.items():
        observed_2025 = [r for r in rows if r["date"].year == 2025]
        aggregate[instrument] = {
            "shock_sessions": sum(r["shock"] for r in observed_2025),
            "episode_onset_sessions": [r["date"].isoformat() for r in observed_2025 if r["episode_onset"]],
            "prior5_exposed_calendar_days": sum(r[instrument]["stress_any_prior5"] for r in calendar),
            "prior10_exposed_calendar_days": sum(r[instrument]["stress_any_prior10"] for r in calendar),
            "prior5_exposed_nyse_sessions": sum(r[instrument]["stress_any_prior5"] for r in calendar if r["is_nyse_session"]),
            "prior10_exposed_nyse_sessions": sum(r[instrument]["stress_any_prior10"] for r in calendar if r["is_nyse_session"]),
            "equity_session_dates_using_prior_treasury_date": [r["date"].isoformat() for r in observed_2025 if r["source_age"] > 0],
        }
    manifest = {
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_documentation_url": "https://home.treasury.gov/treasury-daily-interest-rate-xml-feed",
        "source_receipts": source_receipts,
        "derived_calendar_days": len(calendar), "nyse_sessions_2025": 250,
        "aggregates": aggregate,
        "raw_market_values_in_published_outputs": False,
        "fred_nasdaq_cboe_raw_fetched_by_this_script": False,
        "limitations": [
            "Rates are separate sensitivity exposures; Nasdaq and VIX primary/secondary equity exposures remain unmeasured.",
            "Original release timestamps and source vintages are not certified; this is a prior-date retrospective proxy.",
            "Bank holidays and equity holidays differ: explicitly carried observations are listed, not silently filled with zero.",
            "Calendar-day flags repeat information across weekends. They are not independent stress episodes.",
            "No issuer event or equity-return outcome is estimated by this script.",
        ],
    }
    for name in ("treasury_stress_spec.json", "rates_sensitivity_stress_calendar.json", "nyse_calendar_2025.csv"):
        manifest.setdefault("artifact_sha256", {})[name] = hashlib.sha256((out / name).read_bytes()).hexdigest()
    (out / "treasury_stress_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
