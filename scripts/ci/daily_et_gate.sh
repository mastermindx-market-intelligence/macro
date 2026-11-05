#!/usr/bin/env bash
# EXTRACTED-VERBATIM-FROM: .github/workflows/daily.yml
# et_gate original gate; size headroom, business body unchanged.
set -e
python3 - <<'PY'
import datetime
import os
from zoneinfo import ZoneInfo

EDT_CRON = "30 22 * * *"  # 18:30 ET while America/New_York is UTC-4 (EDT)
EST_CRON = "30 23 * * *"  # 18:30 ET while America/New_York is UTC-5 (EST)

now_env = os.environ.get("ET_GATE_NOW_UTC")  # test injection only
now = (datetime.datetime.fromisoformat(now_env) if now_env
       else datetime.datetime.now(datetime.timezone.utc))
if now.tzinfo is None:
    now = now.replace(tzinfo=datetime.timezone.utc)
offset = now.astimezone(ZoneInfo("America/New_York")).utcoffset()
# Any offset other than EDT's -4h resolves to the EST cron: with broken
# tzdata the nightly still runs exactly once (possibly an hour late),
# never zero times.
intended = EDT_CRON if offset == datetime.timedelta(hours=-4) else EST_CRON
fired = os.environ.get("FIRED_CRON", "")
event = os.environ.get("EVENT_NAME", "")
verdict = "true" if (event != "schedule" or fired == intended) else "false"
# Hours, not the raw timedelta: str(timedelta(hours=-4)) renders
# "-1 day, 20:00:00", which is the wrong thing to read at 3am.
off_h = offset.total_seconds() / 3600
print(f"::notice title=daily ET gate::event={event or '-'} fired={fired or '-'} "
      f"intended={intended} ny_utc_offset={off_h:+.0f}h -> run={verdict}", flush=True)
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
    fh.write(f"run={verdict}\n")
PY
