#!/usr/bin/env python3
"""External liveness check for the fleet worktree GC — did the schedule actually FIRE?

WHY THIS CANNOT LIVE INSIDE THE JOB IT WATCHES (2026-09-29). Every receipt the worktree
GC produces — ``last_run.json``, ``last_attempt.json``, ``ledger.jsonl``, the stdout log —
is written BY the wrapper, so all of them can only ever describe a run that STARTED. None
of them can witness an absence. Measured cost of that blind spot: the agent was simply not
loaded between 2026-09-18 and 09-21, four consecutive days with no run at all, and nothing
anywhere reported it. ``launchctl``'s own ``runs`` counter cannot close the gap either —
it resets on re-bootstrap, so it is evidence about load history, not lifetime runs.

The only way to notice a run that never happened is to compare an EXPECTATION derived from
outside the job — its launchd schedule and the current clock — against the start markers in
its log. That is all this script does. It reads two files, writes nothing, and never touches
the sweeper, its config, or any worktree.

FOUR TRAPS THIS DELIBERATELY AVOIDS, each one measured on the real log:

1. ``== worktree-gc done rc=0 ==`` is a COMPLETION marker sharing the run-start marker's
   prefix. A naive ``grep -c '== worktree-gc '`` counts both: on the real log that is 75
   against 45 actual starts. A start is a marker whose payload is a single token AND parses
   as a timestamp — two independent filters, see START_RE.
2. The markers are stamped in UTC (``2026-09-28T12:17:06+00:00``) while
   ``StartCalendarInterval`` is LOCAL time. Comparing them without converting shifts whole
   days across the date boundary and invents both misses and runs.
3. "The log has nothing for today" is not "today was missed" — it is usually "today is not
   due yet". Read at 00:58 local against an 05:17 schedule, the identical file means the
   opposite of what it means at 06:00. A day is only EXPECTED once its scheduled instant has
   passed. (Family: a positional instrument answering "what is true so far" being read as
   "what will ever be true".)
4. A truncated, rotated, or newly created log has no markers for days that really did run.
   The window is therefore clipped to the OLDEST start marker present: this check reports on
   the span the log can actually speak for, and says so, rather than manufacturing a missing
   day out of a missing file.

Exit codes: 0 = every expected day has a start; 1 = at least one expected day has none;
2 = the check could not be performed (no plist, no log, or a schedule shape it refuses to
guess at). A 2 is never reported as health — a checker that cannot see fails loud.

Stdlib-only, like the job it watches. Report-only: it has no --apply and no write path.
"""
from __future__ import annotations

import argparse
import datetime as dt
import plistlib
import re
import sys
from pathlib import Path

DEFAULT_PLIST = Path.home() / "Library/LaunchAgents/com.macro.worktree-gc.plist"
DEFAULT_LOG = Path.home() / "Library/Logs/macro_worktree_gc/launchd.out.log"
DEFAULT_DAYS = 14

# A run-start marker. Trap 1 is closed TWICE over, and the redundancy is deliberate because
# each layer catches a different way of getting it wrong:
#   * this regex requires the payload to be ONE non-space token followed by ` ==`, and
#     `== worktree-gc done rc=0 ==` carries two, so a completion line never matches at all;
#   * and even if the pattern were loosened to `(.+)`, the payload still has to parse as a
#     timestamp below, so `done rc=0` would be discarded there instead.
# Measured by mutation: removing EITHER layer alone leaves the behaviour correct, which is
# exactly why neither may be deleted as "obviously redundant" — the other one is load-bearing
# only while it stands alone. `tests/test_worktree_gc_liveness.py` pins both independently.
START_RE = re.compile(r"^== worktree-gc (\S+) ==\s*$")


def parse_schedule(plist_path: Path) -> tuple[int, int] | None:
    """-> (hour, minute) local, or None when the shape is one we refuse to guess at.

    launchd accepts a dict OR a list of dicts, and a dict that omits Hour means "every hour".
    Only a single daily Hour+Minute is supported here: a check that guesses at a schedule it
    does not understand would report confident nonsense, and there is exactly one schedule in
    production. Anything else returns None and the caller exits 2.
    """
    try:
        data = plistlib.loads(plist_path.read_bytes())
    except Exception as exc:                            # noqa: BLE001 - any failure is fatal
        print("cannot read plist %s: %r" % (plist_path, exc))
        return None
    sched = data.get("StartCalendarInterval")
    if not isinstance(sched, dict):
        print("unsupported StartCalendarInterval shape: %r" % (sched,))
        return None
    hour, minute = sched.get("Hour"), sched.get("Minute")
    if not isinstance(hour, int) or not isinstance(minute, int):
        print("schedule is not a single daily Hour+Minute: %r" % (sched,))
        return None
    extra = set(sched) - {"Hour", "Minute"}
    if extra:
        print("schedule carries fields this check does not model: %s" % sorted(extra))
        return None
    return hour, minute


def parse_starts(log_path: Path) -> list[dt.datetime]:
    """Every run-start marker in the log, as AWARE datetimes preserving their instant.

    Deliberately NOT converted to a zone here. Bucketing into days is the caller's job and it
    must happen in ONE zone — the zone of `now` — because a run's date and the schedule's date
    have to be asked in the same calendar. Converting here to machine-local instead would put
    the two sides of the comparison in different zones the moment `--now` carries an offset of
    its own, which is exactly the trap-2 mistake one level over.
    """
    starts: list[dt.datetime] = []
    try:
        text = log_path.read_text(errors="replace")
    except OSError as exc:
        print("cannot read log %s: %r" % (log_path, exc))
        return starts
    for line in text.splitlines():
        m = START_RE.match(line)
        if not m:
            continue
        try:
            stamp = dt.datetime.fromisoformat(m.group(1))
        except ValueError:
            continue                                    # `done rc=0` lands here, by design
        if stamp.tzinfo is None:
            stamp = stamp.astimezone()                  # a bare stamp means host-local
        starts.append(stamp)
    return starts


def expected_days(hour: int, minute: int, now: dt.datetime, days: int,
                  oldest_start: dt.datetime | None) -> list[dt.date]:
    """Days whose scheduled instant has already passed, clipped to what the log can speak for.

    Trap 3 lives in the `due > now` test: today is expected only once its scheduled time is
    past. Trap 4 lives in the `oldest_start` clip: a day before the log's first marker is a
    day this file cannot answer for, and silence there is not evidence.
    """
    out: list[dt.date] = []
    for back in range(days, -1, -1):
        day = (now - dt.timedelta(days=back)).date()
        due = dt.datetime.combine(day, dt.time(hour, minute), tzinfo=now.tzinfo)
        if due > now:
            continue
        if oldest_start is not None and day < oldest_start.date():
            continue
        out.append(day)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plist", type=Path, default=DEFAULT_PLIST)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--days", type=int, default=DEFAULT_DAYS,
                    help="how far back to look (default %d)" % DEFAULT_DAYS)
    ap.add_argument("--now", default=None,
                    help="ISO timestamp to evaluate against; for tests. Default: the clock.")
    args = ap.parse_args(argv)

    if args.days < 0:
        print("--days must not be negative")
        return 2
    if not args.plist.exists():
        print("NO PLIST at %s — the agent is not installed, so no run is expected or missed."
              % args.plist)
        return 2
    sched = parse_schedule(args.plist)
    if sched is None:
        return 2
    hour, minute = sched

    if args.now:
        try:
            now = dt.datetime.fromisoformat(args.now)
        except ValueError:
            print("--now is not an ISO timestamp: %r" % args.now)
            return 2
        if now.tzinfo is None:
            now = now.astimezone()
    else:
        now = dt.datetime.now().astimezone()

    if not args.log.exists():
        print("NO LOG at %s — cannot distinguish 'never ran' from 'log not created yet'."
              % args.log)
        return 2
    starts = parse_starts(args.log)
    if not starts:
        print("NO START MARKERS in %s — the log exists but says nothing about runs." % args.log)
        return 2

    # ONE zone for both sides of the comparison — see parse_starts' docstring.
    starts = sorted(s.astimezone(now.tzinfo) for s in starts)
    seen = {s.date() for s in starts}
    want = expected_days(hour, minute, now, args.days, starts[0])
    missing = [d for d in want if d not in seen]

    print("schedule      %02d:%02d local, daily" % (hour, minute))
    print("now           %s" % now.isoformat(timespec="seconds"))
    print("log spans     %s .. %s (%d start markers)"
          % (starts[0].date(), starts[-1].date(), len(starts)))
    print("window        %d day(s) back, clipped to the log's first marker" % args.days)
    print("expected      %d day(s) whose scheduled time has passed" % len(want))
    for day in want:
        print("  %s  %s" % (day, "ok" if day in seen else "NO START"))

    today = now.date()
    if today not in want:
        print("note          today (%s) is not yet due at %02d:%02d — its absence is not a miss"
              % (today, hour, minute))

    if missing:
        print("MISSING %d scheduled start(s): %s"
              % (len(missing), ", ".join(str(d) for d in missing)))
        return 1
    print("OK every expected start is present")
    return 0


if __name__ == "__main__":
    sys.exit(main())
