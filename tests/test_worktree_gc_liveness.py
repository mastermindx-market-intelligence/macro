"""tests/test_worktree_gc_liveness.py — the only instrument that can witness a run that never ran.

WHY THIS SUITE EXISTS. Every receipt the fleet worktree GC produces is written BY the wrapper,
so all of them describe runs that STARTED and none of them can report an absence. Measured cost:
the LaunchAgent was not loaded 2026-09-18 → 09-21, four consecutive days with no sweep, and the
gap was found weeks later by hand. `scripts/worktree_gc_liveness.py` closes that by comparing an
expectation built OUTSIDE the job — its launchd schedule plus the clock — against the start
markers in its log.

A checker for a silent failure is itself easy to build silent, so every test below pins a
SENTENCE as well as an exit code: the recorded lesson is that a suite made only of exit codes
cannot tell a correct verdict from a correct-by-accident one, and the failure mode this script
exists to prevent is precisely a clean exit that means nothing.

COVERAGE
  1. a complete log → rc 0 and says so
  2. POSITIVE CONTROL: the real 4-day gap shape → rc 1, and every missing date is NAMED
  3. trap 1 — `== worktree-gc done rc=0 ==` shares the marker prefix and is NOT a start; a day
     carrying only a completion line is reported missing, and the marker count excludes them
  4. trap 2 — a marker is bucketed in the comparison's zone, not in its own printed offset
  5. trap 3 — before the scheduled instant, today is NOT expected; after it, the identical file
     is a miss. Same bytes, opposite verdicts, and that is the whole point
  6. trap 4 — days before the log's first marker are never reported missing (rotated log)
  7. refusals (no plist / unmodelled schedule / no markers) exit 2 AND explain themselves
  8. an unmodelled schedule is refused rather than guessed at, including the hourly shape
"""

from __future__ import annotations

import datetime as dt
import plistlib
from pathlib import Path

from scripts import worktree_gc_liveness as liveness

UTC = dt.timezone.utc
HOUR, MINUTE = 5, 17


def _plist(tmp_path: Path, sched=None) -> Path:
    """An installed-agent plist. Default: the production 05:17 daily schedule."""
    if sched is None:
        sched = {"Hour": HOUR, "Minute": MINUTE}
    p = tmp_path / "com.macro.worktree-gc.plist"
    p.write_bytes(plistlib.dumps({
        "Label": "com.macro.worktree-gc",
        "StartCalendarInterval": sched,
    }))
    return p


def _log(tmp_path: Path, lines: list[str], name: str = "launchd.out.log") -> Path:
    p = tmp_path / name
    p.write_text("\n".join(lines) + "\n")
    return p


def _start(day: str, hhmm: str = "12:17:06") -> str:
    """A run-start marker, stamped in UTC exactly as the wrapper writes it."""
    return "== worktree-gc %sT%s+00:00 ==" % (day, hhmm)


def _run(tmp_path, days, now, log_lines, sched=None, capsys=None):
    argv = ["--plist", str(_plist(tmp_path, sched)),
            "--log", str(_log(tmp_path, log_lines)),
            "--days", str(days), "--now", now]
    rc = liveness.main(argv)
    out = capsys.readouterr().out if capsys else ""
    return rc, out


# 1 ─────────────────────────────────────────────────────────────────────────────

def test_a_complete_log_passes_and_says_so(tmp_path, capsys):
    lines = [_start("2026-09-2%d" % d) for d in range(4, 9)]        # 24..28
    rc, out = _run(tmp_path, 4, "2026-09-28T23:00:00+00:00", lines, capsys=capsys)
    assert rc == 0
    assert "OK every expected start is present" in out
    assert "NO START" not in out


# 2 ─────────────────────────────────────────────────────────────────────────────

def test_positive_control_the_real_four_day_gap_is_found_and_named(tmp_path, capsys):
    """The exact shape of the measured incident: 09-18 → 09-21 absent, both sides present."""
    present = ["2026-09-15", "2026-09-16", "2026-09-17",
               "2026-09-22", "2026-09-23", "2026-09-24"]
    rc, out = _run(tmp_path, 9, "2026-09-24T23:00:00+00:00",
                   [_start(d) for d in present], capsys=capsys)
    assert rc == 1
    for missed in ("2026-09-18", "2026-09-19", "2026-09-20", "2026-09-21"):
        assert missed in out.split("MISSING")[1], "%s not named in the verdict" % missed
    assert "MISSING 4 scheduled start(s)" in out


# 3 ─────────────────────────────────────────────────────────────────────────────

def test_a_completion_marker_is_not_a_start(tmp_path, capsys):
    """`done rc=0` shares the prefix. Counting it would roughly double the run count and
    would silently excuse a day on which the job only ever printed a completion line."""
    lines = [_start("2026-09-26"), "== worktree-gc done rc=0 ==",
             _start("2026-09-27"), "== worktree-gc done rc=0 ==",
             "== worktree-gc done rc=2 =="]                          # 09-28's only line
    rc, out = _run(tmp_path, 2, "2026-09-28T23:00:00+00:00", lines, capsys=capsys)
    assert "(2 start markers)" in out, "completion markers were counted as starts"
    assert rc == 1
    assert "2026-09-28  NO START" in out


def test_both_layers_of_the_completion_marker_filter_are_pinned_separately(tmp_path):
    """Trap 1 is defended twice and the layers must be asserted independently.

    Measured by mutation: loosening the regex alone leaves behaviour correct because the
    timestamp parse then rejects the payload, and neutering the parse alone leaves it correct
    because the regex never matched. A suite that only checks the OUTCOME therefore cannot
    tell a tight regex from a loose one, and a later reader deleting "the redundant half"
    would see a green suite. So each layer gets its own assertion.
    """
    # layer 1 — the pattern itself refuses a two-token payload
    assert liveness.START_RE.match("== worktree-gc done rc=0 ==") is None
    assert liveness.START_RE.match("== worktree-gc 2026-09-28T12:17:06+00:00 ==") is not None
    # layer 2 — an unparseable single-token payload MATCHES the pattern and is discarded anyway
    assert liveness.START_RE.match("== worktree-gc notatimestamp ==") is not None
    log = _log(tmp_path, ["== worktree-gc notatimestamp ==",
                          "== worktree-gc done rc=0 =="], name="layers.log")
    assert liveness.parse_starts(log) == []


# 4 ─────────────────────────────────────────────────────────────────────────────

def test_markers_are_bucketed_in_the_comparisons_zone_not_their_own(tmp_path, capsys):
    """A 23:30Z marker is the NEXT day at +05:30 and the SAME day at UTC.

    Bucketing a marker by the calendar printed in its own offset — rather than by the zone the
    schedule is evaluated in — moves whole runs across the date boundary and invents a miss on
    one side and a phantom run on the other. Asked in two zones, the same bytes must land on
    two different days.
    """
    lines = [_start("2026-09-27", "23:30:00")]
    rc_utc, out_utc = _run(tmp_path, 0, "2026-09-27T23:59:00+00:00", lines, capsys=capsys)
    assert rc_utc == 0 and "2026-09-27  ok" in out_utc

    rc_ist, out_ist = _run(tmp_path, 0, "2026-09-28T23:59:00+05:30", lines, capsys=capsys)
    assert "2026-09-28  ok" in out_ist, "marker was not re-bucketed into the asking zone"
    assert rc_ist == 0


def test_parse_starts_preserves_the_instant(tmp_path):
    """The conversion must never move the moment, only the calendar it is read in."""
    log = _log(tmp_path, [_start("2026-09-27", "23:30:00")])
    (start,) = liveness.parse_starts(log)
    assert start.astimezone(UTC) == dt.datetime(2026, 9, 27, 23, 30, tzinfo=UTC)


# 5 ─────────────────────────────────────────────────────────────────────────────

def test_today_is_not_a_miss_until_its_scheduled_time_has_passed(tmp_path, capsys):
    """The same log, read twice, must mean opposite things — this is trap 3 in one test.

    At 00:58 local the 05:17 run has not come due; an absent marker is not a miss. At 06:00 the
    identical file is a genuine non-start. A checker that cannot tell those apart either cries
    wolf every night or stays silent through a real outage.
    """
    lines = [_start("2026-09-27"), _start("2026-09-28")]

    rc_early, out_early = _run(tmp_path, 1, "2026-09-29T00:58:00+00:00", lines, capsys=capsys)
    assert rc_early == 0
    assert "not yet due" in out_early
    assert "2026-09-29" not in out_early.split("expected")[1].split("note")[0]

    rc_late, out_late = _run(tmp_path, 1, "2026-09-29T06:00:00+00:00", lines, capsys=capsys)
    assert rc_late == 1
    assert "2026-09-29  NO START" in out_late


# 6 ─────────────────────────────────────────────────────────────────────────────

def test_days_before_the_logs_first_marker_are_never_reported_missing(tmp_path, capsys):
    """A rotated or freshly created log has no markers for days that really did run.

    Absence of a record is not a record of absence, and a checker that forgets that greets
    every log rotation with a fortnight of fabricated outages — which is how a real alert gets
    ignored.
    """
    lines = [_start("2026-09-27"), _start("2026-09-28")]
    rc, out = _run(tmp_path, 14, "2026-09-28T23:00:00+00:00", lines, capsys=capsys)
    assert rc == 0
    assert "2026-09-14" not in out and "2026-09-20" not in out
    assert "clipped to the log's first marker" in out


# 7 ─────────────────────────────────────────────────────────────────────────────

def test_a_missing_plist_refuses_and_explains(tmp_path, capsys):
    rc = liveness.main(["--plist", str(tmp_path / "absent.plist"),
                        "--log", str(_log(tmp_path, [_start("2026-09-28")])),
                        "--now", "2026-09-28T23:00:00+00:00"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "NO PLIST" in out and "not installed" in out


def test_a_log_without_markers_refuses_rather_than_reporting_health(tmp_path, capsys):
    rc = liveness.main(["--plist", str(_plist(tmp_path)),
                        "--log", str(_log(tmp_path, ["some unrelated line", "another"])),
                        "--now", "2026-09-28T23:00:00+00:00"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "NO START MARKERS" in out
    assert "OK every expected start" not in out


def test_a_missing_log_refuses(tmp_path, capsys):
    rc = liveness.main(["--plist", str(_plist(tmp_path)),
                        "--log", str(tmp_path / "absent.log"),
                        "--now", "2026-09-28T23:00:00+00:00"])
    out = capsys.readouterr().out
    assert rc == 2
    assert "NO LOG" in out


# 8 ─────────────────────────────────────────────────────────────────────────────

def test_an_unmodelled_schedule_is_refused_not_guessed(tmp_path, capsys):
    """launchd's `{Minute: 17}` means EVERY hour, not once a day. Silently reading it as a
    daily 00:17 would report 23 phantom misses a day, so the shape is refused instead."""
    rc, out = _run(tmp_path, 2, "2026-09-28T23:00:00+00:00",
                   [_start("2026-09-28")], sched={"Minute": 17}, capsys=capsys)
    assert rc == 2
    assert "not a single daily Hour+Minute" in out


def test_a_schedule_with_extra_fields_is_refused(tmp_path, capsys):
    """A Weekday/Day restriction means most days are not expected at all."""
    rc, out = _run(tmp_path, 2, "2026-09-28T23:00:00+00:00", [_start("2026-09-28")],
                   sched={"Hour": 5, "Minute": 17, "Weekday": 1}, capsys=capsys)
    assert rc == 2
    assert "does not model" in out


def test_a_list_of_intervals_is_refused(tmp_path, capsys):
    rc, out = _run(tmp_path, 2, "2026-09-28T23:00:00+00:00", [_start("2026-09-28")],
                   sched=[{"Hour": 5, "Minute": 17}, {"Hour": 17, "Minute": 5}], capsys=capsys)
    assert rc == 2
    assert "unsupported StartCalendarInterval shape" in out
