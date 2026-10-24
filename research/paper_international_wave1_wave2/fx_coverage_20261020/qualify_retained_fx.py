"""Qualify retained incumbent FX responses; never fetch or write the canonical data store."""
from __future__ import annotations
from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal, localcontext
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import shutil
import sys
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
from lib.intl_currency_observation import (
    SPECS, build_currency_observation, captured_source_context,
    currency_observation_view, provider_dataset_url,
)

TODAY = date(2026, 10, 20)
receipts = []
for name in ("incumbent_provider_probe.json", "additional_incumbent_provider_probe.json"):
    receipts.extend(json.loads((OUT/name).read_text()))
assert len(receipts) == len(SPECS) and {r["cc"] for r in receipts} == set(SPECS)
fixture = {"schema": "intl_currency_source_fixture.v1", "evaluated_at": TODAY.isoformat(), "cases": []}
report = {
    "schema": "intl_currency_qualification.v1",
    "qualified_at": datetime.now(timezone.utc).isoformat(),
    "evaluation_day": TODAY.isoformat(),
    "kind": "RETAINED_PROVIDER_RESPONSES_NOT_CANONICAL_STORE_ADMISSION",
    "quote_timezone": "Europe/London",
    "same_day_policy": "exclude evaluation day and recorded UTC capture day",
    "canonical_store_writes": False,
    "countries": [],
}
replay = {}
for cc in SPECS:
    receipt = next(r for r in receipts if r["cc"] == cc)
    url = provider_dataset_url(cc)
    assert receipt["status"] == 200 and receipt["attempts"] == 1
    assert receipt["url"] == receipt["final_url"] == url
    blob = gzip.decompress((OUT/receipt["archive"]).read_bytes())
    assert len(blob) == receipt["bytes"] and sha256(blob).hexdigest() == receipt["sha256"]
    body = json.loads(blob)
    chart = body["chart"]
    assert chart["error"] is None and len(chart["result"]) == 1
    row = chart["result"][0]
    meta = row["meta"]
    spec = SPECS[cc]
    assert meta["symbol"] in spec[3]
    assert meta["currency"] == (spec[0] if spec[2] == "local_per_USD" else "USD")
    assert meta["instrumentType"] == "CURRENCY" and meta["exchangeName"] == "CCY"
    assert meta["dataGranularity"] == "1d" and meta["range"] == "6mo"
    assert meta["exchangeTimezoneName"] == "Europe/London"
    assert len(row["indicators"]["quote"]) == 1
    stamps = row["timestamp"]
    quotes = row["indicators"]["quote"][0]["close"]
    assert len(stamps) == len(quotes) and 60 <= len(stamps) <= 200
    captured = datetime.fromisoformat(receipt["finished_at"]).astimezone(timezone.utc)
    assert captured.date() == TODAY
    zone = ZoneInfo(meta["exchangeTimezoneName"])
    observations, normalized = [], []
    missing = 0
    previous = None
    for stamp, value in zip(stamps, quotes):
        assert type(stamp) is int and (previous is None or stamp > previous)
        previous = stamp
        instant = datetime.fromtimestamp(stamp, timezone.utc)
        assert instant <= captured
        observed = instant.astimezone(zone).date().isoformat()
        if value is None:
            missing += 1
            continue
        assert type(value) in (int, float) and math.isfinite(value) and value > 0
        observations.append([observed, value])
        normalized.append({"timestamp_utc": instant.isoformat(), "quote_date": observed, "close": value})
    assert len(observations) == receipt["observation_count"]
    source = captured_source_context(cc, retrieved_at=receipt["finished_at"],
                                    response_sha256=receipt["sha256"], provider_symbol=meta["symbol"])
    result = build_currency_observation(cc, observations, today=TODAY, source=source)
    assert result["status"] == "available"
    view = currency_observation_view(result, cc, today=TODAY)
    assert view["available"] and view["quality"] == "current"
    # Independent endpoint selection from the complete normalized response.
    cutoff = min(TODAY, captured.date()).isoformat()
    daily = {}
    for observed, value in observations:
        if observed < cutoff:
            daily.setdefault(observed, set()).add(value)
    end = max(daily)
    end_date = date.fromisoformat(end)
    yy, mm = end_date.year, end_date.month - 3
    if mm <= 0:
        yy, mm = yy - 1, mm + 12
    target = date(yy, mm, min(end_date.day, monthrange(yy, mm)[1]))
    start = max(d for d in daily if d <= target.isoformat())
    assert len(daily[start]) == len(daily[end]) == 1
    a, b = next(iter(daily[start])), next(iter(daily[end]))
    assert result["start"] == {"date": start, "quote": a}
    assert result["end"] == {"date": end, "quote": b}
    with localcontext() as ctx:
        ctx.prec = 40
        da, db = Decimal(str(a)), Decimal(str(b))
        expected = ((da / db if spec[2] == "local_per_USD" else db / da) - 1) * 100
    assert math.isclose(float(expected), result["value"], rel_tol=1e-12, abs_tol=1e-12)
    expected_row = {
        "start": result["start"], "end": result["end"],
        "reference_target": target.isoformat(), "value_decimal": str(expected),
        "display_percent": f'{result["value"]:+.2f}%',
    }
    fixture["cases"].append({"cc": cc, "source": source,
                             "observations": observations, "expected": expected_row})
    replay[cc] = result
    (OUT/(cc+"_normalized_observations.json")).write_text(json.dumps(normalized, indent=2)+"\n")
    report["countries"].append({
        "cc": cc, "currency": spec[0], "configured_ticker": spec[1], "provider_symbol": meta["symbol"],
        "quote_convention": spec[2], "source_url": source["source_url"],
        "dataset_url": url, "retrieved_at": receipt["finished_at"],
        "raw_archive": receipt["archive"], "response_sha256": receipt["sha256"],
        "timestamp_rows": len(stamps), "valid_quotes": len(observations), "missing_quotes": missing,
        "excluded_on_or_after_capture_day": sum(d >= cutoff for d, v in observations),
        "reference_gap_days": view["reference_gap_days"], "expected": expected_row,
        "evidence_sha256": result["evidence_sha256"],
    })

fixture_path = ROOT/"tests/fixtures/intl_currency_observations_20261020.json"
fixture_path.write_text(json.dumps(fixture, indent=2)+"\n")
preview = OUT/"preview"
preview.mkdir(parents=True, exist_ok=True)
prior = OUT.parent/"fiscal_coverage_20261019/preview"
for name in ("country_inputs.json", "market_replay.json", "theme.css", "navigation-refresh.css"):
    path = prior/name
    if path.exists():
        shutil.copyfile(path, preview/name)
(preview/"currency_replay.json").write_text(json.dumps(replay, indent=2)+"\n")
report["fixture_sha256"] = sha256(fixture_path.read_bytes()).hexdigest()
report["currency_replay_sha256"] = sha256((preview/"currency_replay.json").read_bytes()).hexdigest()
report["passed"] = True
(OUT/"source_qualification.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps({"passed": True, "fixture_sha256": report["fixture_sha256"],
                  "countries": [{k:r[k] for k in ("cc", "currency", "expected", "reference_gap_days")}
                                for r in report["countries"]]}, indent=2))
