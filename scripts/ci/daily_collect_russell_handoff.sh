#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# collect original russell_cache_ready; size headroom, business body unchanged.
set -e
python - <<'PY_RUSSELL_HANDOFF'
import json
import os
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from lib.nyse_calendar import expected_last_session

expected = expected_last_session()
close_utc = datetime.combine(
    expected, time(16), tzinfo=ZoneInfo("America/New_York")
).astimezone(timezone.utc)
receipt = {}
try:
    receipt = json.loads(Path("data/run_status.json").read_text())
except (OSError, ValueError, TypeError):
    pass
source = ((receipt.get("sources") or {}).get("russell_breadth") or {})
def parse_utc(stamp):
    if not isinstance(stamp, str):
        return None
    try:
        instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if instant.tzinfo is None:
            instant = instant.replace(tzinfo=timezone.utc)
        return instant.astimezone(timezone.utc)
    except ValueError:
        return None

checked = parse_utc(source.get("checked_at"))
finished = parse_utc(receipt.get("last_run"))
started = parse_utc(os.environ.get("RUSSELL_COLLECT_STARTED_AT"))
now = datetime.now(timezone.utc)
cache = Path("data/russell_breadth/_closes_cache.parquet")
qualified = (
    source.get("status") == "ok"
    and source.get("last_date") == expected.isoformat()
    and started is not None and finished is not None and checked is not None
    and close_utc <= started <= finished <= checked <= now
    and cache.is_file() and cache.stat().st_size > 0
)
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
    out.write(f"qualified={'true' if qualified else 'false'}\n")
if qualified:
    print("::notice title=Russell cache handoff::qualified completed-session source; ready for same-run save")
else:
    print("::warning title=Russell cache handoff withheld::missing/unqualified current Russell source; engine remains exact-key-only")
PY_RUSSELL_HANDOFF
