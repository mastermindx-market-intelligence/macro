"""Replay captured official bytes through the actual Macro feed producer.

This verification harness replaces only unrelated calendar/intl producers with
empty local stubs. It writes under this verification directory, never the live
site or data roots. It does not collect, publish, schedule, or evaluate outcomes.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import types
from unittest.mock import patch

PROGRAM = Path(__file__).resolve().parents[1]
REPOSITORY = PROGRAM.parents[1]
sys.path.insert(0, str(REPOSITORY))

import engine
from engine import treasury_auction_lifecycle as lifecycle
from scripts import build_feeds

AT = datetime(2026, 10, 8, 23, tzinfo=timezone.utc)


class FixedClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return AT


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_authority(value):
    if isinstance(value, dict):
        assert not ({"auction_stress", "treasury_auctions", "stressed", "band"} & value.keys())
        for child in value.values():
            assert_authority(child)
    elif isinstance(value, list):
        for child in value:
            assert_authority(child)


def replay(name: str, data: Path) -> dict:
    output = PROGRAM / "verification" / name
    calendar = types.ModuleType("engine.event_calendar")
    calendar.us_macro_events = lambda *args: []
    calendar.high_impact_strip = lambda *args: []
    calendar.commodity_events = lambda *args: []
    international = types.ModuleType("engine.risk_radar_intl")
    international.PROFILES = {}
    international.snapshot = lambda *args: {}
    with patch.object(build_feeds.config, "ROOT", output), \
         patch.object(build_feeds.config, "load", return_value={"storage": {"site_dir": "site"}}), \
         patch.object(build_feeds.config, "data_dir", return_value=data), \
         patch.object(build_feeds, "datetime", FixedClock), \
         patch.object(engine, "event_calendar", calendar, create=True), \
         patch.dict("sys.modules", {"engine.event_calendar": calendar, "engine.risk_radar_intl": international}):
        build_feeds.build()
    feed_path = output / "site/feeds/event_calendar.json"
    feed = json.loads(feed_path.read_text())
    context = feed["sovereign_auction_context"]
    direct = lifecycle.snapshot(data, as_of=AT, horizon_days=30)
    assert context == direct
    assert feed["horizon_days"] == 21 and context["coverage"]["horizon_days"] == 30
    assert context["is_context_only"] is True
    assert context["forecast_authority"] == "RESEARCH_ONLY"
    assert context["probabilities"] is None
    assert_authority(context)
    negative = lifecycle.snapshot(data, as_of="2026-10-08T22:00:00Z")
    assert not negative["events"]
    assert negative["source_observed_at"] is None
    assert negative["coverage"]["known_upcoming_count"] is None
    return {
        "name": name,
        "input_root": str(data.relative_to(PROGRAM)),
        "feed": str(feed_path.relative_to(PROGRAM)),
        "feed_sha256": sha(feed_path),
        "context_sha256": hashlib.sha256(json.dumps(context, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "status": context["status"],
        "source_observed_at": context["source_observed_at"],
        "event_count": len(context["events"]),
        "classes": dict(Counter(row["normalized_class"] for row in context["events"])),
        "physical_states": dict(Counter(row["physical_state"] for row in context["events"])),
        "coverage": context["coverage"],
        "source_health": context["source_health"],
        "negative_cutoff": "2026-10-08T22:00:00Z",
        "negative_receipts_excluded": negative["coverage"]["excluded_after_as_of_count"],
        "negative_observed_counts_are_null": True,
        "actual_builder_equals_pure_snapshot": True,
    }


def main():
    results = [
        replay("primary_runtime_feed", PROGRAM / "source_audit/forward_capture_primary"),
        replay("mac_host_feed", PROGRAM / "verification/current_capture"),
    ]
    assert results[0]["event_count"] == 74
    assert len(results[0]["source_health"]) == 4
    assert all(row["latest_attempt_status"] == "available" for row in results[0]["source_health"])
    assert any(row["latest_attempt_status"] != "available" for row in results[1]["source_health"])
    receipt = {
        "schema_version": "sovereign_auction_real_feed_verification_v1",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "query_cutoff": AT.isoformat(),
        "cutoff_is_verification_query_not_historical_forecast": True,
        "builder_sha256": sha(REPOSITORY / "scripts/build_feeds.py"),
        "lifecycle_sha256": sha(REPOSITORY / "engine/treasury_auction_lifecycle.py"),
        "captures_replayed_without_recapture_or_backdating": True,
        "unrelated_producers_stubbed": ["engine.event_calendar", "engine.risk_radar_intl"],
        "production_site_written": False,
        "published": False,
        "runs": results,
    }
    path = PROGRAM / "verification/real_source_feed_receipt.json"
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(path.relative_to(REPOSITORY)), "runs": [
        {key: row[key] for key in ["name", "status", "event_count", "classes", "feed_sha256"]}
        for row in results
    ]}, indent=2))


if __name__ == "__main__":
    main()
