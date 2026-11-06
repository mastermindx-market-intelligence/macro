"""One-shot helper that runs origin/main's dd20710c producer over the
committed fixture at tests/fixtures/am_edition_fixture/ at a fixed `now`,
then writes the legacy 7 + top-level surface (excluding time-sensitive
fields) as tests/fixtures/am_edition_legacy_snapshot_dd20710c.json.

Run only when the fixture changes. Not part of the test suite.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "am_edition_fixture"
PRODUCER_PATH = Path("/tmp/dd20710c_producer.py")
SNAPSHOT_PATH = REPO_ROOT / "tests" / "fixtures" / "am_edition_legacy_snapshot_dd20710c.json"

# Frozen `now` for byte-identity. 2026-09-08 15:00 UTC = Tuesday 11:00 ET
# (open session). Matches the test fixtures so the snapshot is reproducible.
FROZEN_NOW = datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)

# Legacy keys the producer shipped on origin/main dd20710c.
LEGACY_BLOCK_KEYS = {
    "session_clock", "tape_since_prior_close", "market_state", "regime",
    "cross_asset_plane", "todays_calendar", "prior_close_brief_ref",
}


def _load_dd20710c_producer():
    """Load dd20710c's producer module from the temp file (origin/main's blob)."""
    # dd20710c's `from lib import config, nyse_calendar, pages` needs the repo
    # root on sys.path. The producer file itself does sys.path.insert(0, ...
    # str(Path(__file__).resolve().parent.parent)) at module top, but the temp
    # file's parent is /tmp — so we add REPO_ROOT ourselves before exec.
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    spec = importlib.util.spec_from_file_location("dd20710c_producer", PRODUCER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dd20710c_producer"] = mod
    spec.loader.exec_module(mod)
    return mod


def _strip_time_sensitive(payload: dict) -> dict:
    """Remove fields that depend on `now` (generated_at + any age_minutes).
    The snapshot freezes the producer's SHAPE — any non-time field is fair
    game. age_minutes is recomputed from `now`, so the snapshot's value
    cannot be the consumer's value even at the same `now`.
    """
    payload = json.loads(json.dumps(payload))  # deep copy
    payload.pop("generated_at", None)
    payload.pop("session_date", None)  # also derived from now
    payload.pop("session_state", None)  # also derived from now
    payload.pop("prior_close_date", None)  # also derived from now
    payload.pop("null_count", None)  # may include session_clock's state in count
    payload.pop("morning_source_feasibility", None)
    payload.pop("morning_source_feasibility_cause_en", None)
    payload.pop("morning_source_feasibility_cause_zh", None)
    # Strip time-derived fields from each block
    for b in payload.get("blocks", []):
        b.pop("age_minutes", None)
        # session_clock's source_as_of IS now; strip it too.
        if b.get("key") == "session_clock":
            b.pop("source_as_of", None)
            b.pop("source_as_of_precision", None)
    return payload


def _filter_legacy(payload: dict) -> dict:
    """Keep only the legacy 7 blocks + the canonical top-level fields."""
    payload = _strip_time_sensitive(payload)
    payload["blocks"] = [b for b in payload.get("blocks", []) if b.get("key") in LEGACY_BLOCK_KEYS]
    return payload


def main() -> int:
    if not PRODUCER_PATH.exists():
        print(f"missing {PRODUCER_PATH}; run `git show dd20710cc4:scripts/build_am_edition.py > {PRODUCER_PATH}` first")
        return 1
    if not FIXTURE_DIR.exists():
        print(f"missing {FIXTURE_DIR}")
        return 1
    mod = _load_dd20710c_producer()
    site = FIXTURE_DIR / "site"
    data = FIXTURE_DIR / "data"
    payload = mod.build_payload(site, data, now=FROZEN_NOW)
    snapshot = _filter_legacy(payload)
    SNAPSHOT_PATH.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {SNAPSHOT_PATH}")
    print(f"blocks in snapshot: {[b.get('key') for b in snapshot['blocks']]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
