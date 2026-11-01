"""Deterministic tests for the one-night BOATS session runner.

No network, no provider, no R2, no real archive. The incumbent segment call
(``publish_boats_stream``) is stubbed at the runner's only boundary to it;
every validation the runner itself owns (timezone contract, overnight
calendar windows, budgets, clamps, lock, O_EXCL receipts, stop rules,
count accounting) runs for real against real files in a temp directory.

"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from scripts import run_boats_session as rbs  # noqa: E402
from scripts.build_ext_quotes import boats_session_date  # noqa: E402
from scripts.run_boats_session import (  # noqa: E402
    SessionConfig, SessionRefused, StartReceiptBlocked, HostTimezoneError,
    acquire_session_lock, clamp_segment, overnight_boundary_et, prepare_archive,
    run_session, validate_host_timezone, write_start_receipt,
)

VANCOUVER = ZoneInfo("America/Vancouver")
ET = ZoneInfo("America/New_York")


def et(*args, **kw) -> datetime:
    return datetime(*args, tzinfo=ET, **kw)


class FakeClock:
    """Deterministic wall + monotonic clock the segment stub can advance."""

    def __init__(self, start_utc: datetime, step_seconds: float = 600.0):
        self.utc = start_utc
        self.mono = 10_000.0
        self.step = step_seconds

    def now_utc(self) -> datetime:
        return self.utc

    def monotonic(self) -> float:
        return self.mono

    def advance(self, seconds: float) -> None:
        self.utc = self.utc + timedelta(seconds=seconds)
        self.mono += seconds


def make_segment_stub(clock: FakeClock, *, raw: int = 100, breaks: int = 0,
                      publication_ok=True, calls: list | None = None,
                      fail_once: Exception | None = None):
    state = {"fail_once": fail_once}

    def runner(*, max_seconds, max_messages, symbols, publish, archive_root):
        if calls is not None:
            calls.append({"max_seconds": max_seconds, "max_messages": max_messages,
                          "publish": publish, "symbols": len(symbols)})
        boom = state.pop("fail_once", None)
        if boom is not None:
            raise boom
        clock.advance(min(clock.step, max_seconds))
        return {"capture_id": "stub", "raw_messages": min(raw, max_messages),
                "transport_breaks": breaks,
                "bytes": 16, "segments": 1, "connections": 1,
                "publication_ok": publication_ok if publish else None,
                "publication": {"requested": publish}}

    return runner


class Harness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / "archive"
        self.archive.mkdir()
        self.symbols_file = Path(self.tmp.name) / "symbols.txt"
        self.symbols_file.write_text("# coverage\nSPY\nQQQ\n", encoding="utf-8")
        self.clock = FakeClock(datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc))  # 20:00 ET Sun

    def config(self, **kw) -> SessionConfig:
        base = dict(publish=True, symbols_file=str(self.symbols_file),
                    archive_root=str(self.archive), total_max_messages=80_000_000,
                    max_segments=32, segment_max_seconds=3600,
                    total_max_seconds=8 * 3600)
        base.update(kw)
        return SessionConfig(**base)

    def run_with(self, config, clock=None, segment=None, **kw):
        return run_session(
            config, clock=clock or self.clock,
            segment_runner=segment or make_segment_stub(clock or self.clock),
            archive_prep=lambda root: {"archive_root": str(root),
                                       "free_bytes": 50 * 1024 ** 3},
            local_tz=VANCOUVER, **kw)


class WindowAndCalendarTests(Harness):
    def test_overnight_start_and_et_midnight(self):
        # 20:00 ET Sunday evening opens the Monday overnight session; the
        # session identity survives ET midnight (00:30 ET same calendar date).
        self.assertEqual(boats_session_date(et(2026, 10, 18, 20, 0)), "2026-10-19")
        self.assertIsNone(boats_session_date(et(2026, 10, 18, 19, 59)))
        self.assertEqual(boats_session_date(et(2026, 10, 19, 0, 30)), "2026-10-19")
        self.assertEqual(boats_session_date(datetime(2026, 10, 19, 4, 30, tzinfo=timezone.utc)),
                         "2026-10-19")  # 00:30 ET

    def test_04et_boundary_is_outside(self):
        self.assertIsNone(boats_session_date(et(2026, 10, 19, 4, 0)))
        self.assertEqual(boats_session_date(et(2026, 10, 19, 3, 59)), "2026-10-19")
        self.assertEqual(overnight_boundary_et(et(2026, 10, 18, 20, 0)),
                         et(2026, 10, 19, 4, 0))

    def test_friday_evening_weekend_and_holiday_are_outside(self):
        # Friday evening would target a Saturday session: none.
        self.assertIsNone(boats_session_date(et(2026, 10, 16, 20, 0)))
        self.assertIsNone(boats_session_date(et(2026, 10, 17, 21, 0)))   # Saturday evening
        self.assertIsNone(boats_session_date(et(2026, 10, 17, 2, 0)))    # Saturday early
        # 2025-12-25 (Thursday) is Christmas: no session that night either side.
        self.assertIsNone(boats_session_date(et(2025, 12, 24, 21, 0)))
        self.assertIsNone(boats_session_date(et(2025, 12, 25, 2, 0)))

    def test_run_refuses_outside_window_with_no_effects(self):
        calls: list = []
        self.clock.utc = et(2026, 10, 16, 20, 0).astimezone(timezone.utc)  # Friday 20:00 ET
        result = self.run_with(self.config(), segment=make_segment_stub(self.clock, calls=calls))
        self.assertEqual(result["terminal_reason"], "outside_overnight_window")
        self.assertTrue(result["stopped_outside_window"])
        self.assertEqual(calls, [])
        self.assertFalse((self.archive / "run-receipts").exists())

    def test_clamp_segment_bounds(self):
        plan = clamp_segment(seconds_remaining=8 * 3600, seconds_to_boundary=8 * 3600,
                             messages_remaining=80_000_000, segment_max_seconds=3600)
        self.assertEqual(plan, {"max_seconds": 3600, "max_messages": 10_000_000})
        self.assertEqual(clamp_segment(seconds_remaining=90, seconds_to_boundary=8 * 3600,
                                       messages_remaining=80_000_000,
                                       segment_max_seconds=3600),
                         {"max_seconds": 90, "max_messages": 10_000_000})
        self.assertEqual(clamp_segment(seconds_remaining=8 * 3600,
                                       seconds_to_boundary=8 * 3600,
                                       messages_remaining=5, segment_max_seconds=3600),
                         {"max_seconds": 3600, "max_messages": 5})
        self.assertEqual(clamp_segment(seconds_remaining=0, seconds_to_boundary=600,
                                       messages_remaining=10, segment_max_seconds=3600), {})
        self.assertEqual(clamp_segment(seconds_remaining=600, seconds_to_boundary=0,
                                       messages_remaining=10, segment_max_seconds=3600), {})


class TimezoneTests(Harness):
    def test_market_open_candidates_cover_bc_permanent_time_and_older_hosts(self):
        # B.C. remains UTC-7 after March 2026. Older Mac databases may still
        # expose winter UTC-8. Exactly one candidate must reach 20:00 ET.
        from scripts.run_boats_session import scheduled_session_due
        for date, host_offset, expected_hour in (("2026-10-18", -7, 17),
                ("2026-11-01", -7, 18), ("2026-11-01", -8, 17),
                ("2027-01-03", -7, 18), ("2027-01-03", -8, 17)):
            host = timezone(timedelta(hours=host_offset))
            admitted = []
            for hour in (17, 18):
                moment = datetime.fromisoformat(date).replace(hour=hour, tzinfo=host)
                checked = validate_host_timezone(moment.astimezone(timezone.utc), local_tz=host)
                self.assertTrue(checked["host_timezone_ok"])
                if scheduled_session_due(moment): admitted.append(hour)
            self.assertEqual(admitted, [expected_hour])

    def test_scheduled_candidate_outside_market_open_has_no_archive_effect(self):
        from dataclasses import replace
        for moment in (et(2026, 10, 18, 19, 0), et(2026, 10, 18, 21, 0),
                       et(2026, 10, 18, 20, 15)):
            clock = FakeClock(moment.astimezone(timezone.utc))
            result = run_session(replace(self.config(), scheduled=True), clock=clock,
                archive_prep=lambda root: self.fail("scheduled no-op opened archive"),
                segment_runner=lambda **kw: self.fail("scheduled no-op opened stream"),
                local_tz=VANCOUVER)
            self.assertEqual(result["terminal_reason"], "scheduled_candidate_not_due")
            self.assertFalse((self.archive/"run-receipts").exists())

    def test_vancouver_zone_name_is_accepted_when_discoverable(self):
        # Historical Vancouver zone identity remains supported.
        moment = datetime(2025, 11, 2, 17, 0, tzinfo=VANCOUVER).astimezone(timezone.utc)
        checked = validate_host_timezone(moment, local_tz=VANCOUVER)
        self.assertTrue(checked["host_timezone_ok"])
        self.assertEqual(checked["host_zone"], "America/Vancouver")

    def test_same_offset_wrong_zone_is_refused(self):
        # An alias that happens to carry the right offset must not stand in
        # for the configured host zone.
        moment = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
        with self.assertRaises(HostTimezoneError):
            validate_host_timezone(moment, local_tz=ZoneInfo("Etc/GMT+7"))

    def test_host_timezone_mismatch_refuses_before_any_effect(self):
        calls: list = []
        for zone, name in ((ZoneInfo("America/New_York"), "ET host"),
                           (ZoneInfo("America/Chicago"), "offset off by 1h"),
                           (ZoneInfo("Asia/Tokyo"), "wrong side of the world")):
            clock = FakeClock(datetime(2026, 10, 19, 3, 0, tzinfo=timezone.utc))
            with self.assertRaises(HostTimezoneError, msg=name):
                run_session(self.config(), clock=clock,
                            segment_runner=make_segment_stub(clock, calls=calls),
                            archive_prep=lambda root: {"archive_root": str(root)},
                            local_tz=zone)
        self.assertEqual(calls, [])
        self.assertFalse((self.archive / "run-receipts").exists())

    def test_dry_run_records_mismatch_instead_of_raising(self):
        clock = FakeClock(datetime(2026, 10, 19, 3, 0, tzinfo=timezone.utc))
        result = run_session(self.config(publish=False), clock=clock,
                             segment_runner=make_segment_stub(clock),
                             archive_prep=lambda root: {"archive_root": str(root)},
                             local_tz=ZoneInfo("America/New_York"))
        self.assertEqual(result["terminal_reason"], "host_timezone_mismatch")
        self.assertFalse(result["host_timezone_ok"])


class ReceiptAndLockTests(Harness):
    def test_clean_success_writes_permanent_receipts_across_et_midnight(self):
        calls: list = []
        result = self.run_with(self.config(total_max_messages=80_000_000),
                          segment=make_segment_stub(self.clock, raw=100, calls=calls))
        self.assertEqual(result["terminal_reason"], "segment_cap_reached")
        self.assertEqual(result["segments_run"], 32)
        self.assertEqual(result["raw_messages_total"], 32 * 100)
        self.assertTrue(all(c["max_seconds"] <= 3600 for c in calls))
        self.assertTrue(all(c["max_messages"] <= 10_000_000 for c in calls))
        self.assertTrue(all(c["publish"] for c in calls))
        start = Path(result["start_receipt"]); final = Path(result["final_receipt"])
        self.assertTrue(start.is_file() and final.is_file())
        payload = json.loads(start.read_text())
        self.assertEqual(payload["kind"], "run-start")
        self.assertEqual(payload["trading_session"], "2026-10-19")
        self.assertEqual(payload["total_max_messages"], 80_000_000)
        # The clock started at 20:00 ET and crossed ET midnight mid-run.
        self.assertEqual(self.clock.utc.astimezone(ET).date().isoformat(), "2026-10-19")
        final_payload = json.loads(final.read_text())
        self.assertEqual(final_payload["terminal_reason"], "segment_cap_reached")
        self.assertEqual(final_payload["segments_run"], 32)
        # Receipts are owner-only and regular.
        self.assertEqual(oct(os.stat(start).st_mode & 0o777), "0o600")

    def test_duplicate_start_receipt_is_blocked_forever(self):
        write_start_receipt(self.archive, "2026-10-19", self.config(),
                            datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc), 2)
        receipt = self.archive / "run-receipts" / "run-start-2026-10-19.json"
        before = receipt.read_bytes()
        calls: list = []
        with self.assertRaises(StartReceiptBlocked):
            self.run_with(self.config(), segment=make_segment_stub(self.clock, calls=calls))
        self.assertEqual(calls, [])
        self.assertEqual(receipt.read_bytes(), before)
        self.assertFalse(any(self.archive.joinpath("run-receipts").glob("run-final-*")))
        fd = acquire_session_lock(self.archive)
        os.close(fd)

    def test_crash_receipt_blocks_same_session_replay(self):
        # A crashed run left only a start receipt: the next launch must refuse
        # before any stream effect, and must not touch the receipt.
        area = self.archive / "run-receipts"; area.mkdir()
        receipt = area / "run-start-2026-10-19.json"
        receipt.write_text('{"schema": "mastermind.boats_session_run.v1", '
                           '"kind": "run-start", "trading_session": "2026-10-19"}')
        calls: list = []
        with self.assertRaises(StartReceiptBlocked):
            self.run_with(self.config(), segment=make_segment_stub(self.clock, calls=calls))
        self.assertEqual(calls, [])
        self.assertEqual(len(list(area.glob("run-final-*"))), 0)

    def test_single_writer_kernel_lock_is_nonblocking(self):
        fd = acquire_session_lock(self.archive)
        try:
            with self.assertRaises(SessionRefused):
                acquire_session_lock(self.archive)
        finally:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        # Released: acquirable again.
        fd2 = acquire_session_lock(self.archive)
        os.close(fd2)


class BudgetAndStopRuleTests(Harness):
    def test_message_budget_exhaustion_stops_cleanly(self):
        calls: list = []
        result = self.run_with(self.config(total_max_messages=250),
                          segment=make_segment_stub(self.clock, raw=100, calls=calls))
        self.assertEqual(result["terminal_reason"], "message_budget_exhausted")
        self.assertEqual(result["segments_run"], 3)
        self.assertEqual(result["raw_messages_total"], 250)
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[-1]["max_messages"], 50)  # last segment clamped to budget

    def test_total_time_budget_is_enforced(self):
        clock = FakeClock(datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc), step_seconds=600)
        result = self.run_with(self.config(total_max_seconds=700),
                          clock=clock, segment=make_segment_stub(clock, raw=10))
        self.assertEqual(result["terminal_reason"], "time_budget_exhausted")
        self.assertEqual(result["segments_run"], 2)
        self.assertLessEqual(result["elapsed_seconds"], 8 * 3600)

    def test_segment_seconds_never_exceed_one_hour(self):
        calls: list = []
        clock = FakeClock(datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc), step_seconds=10)
        self.run_with(self.config(), clock=clock, segment=make_segment_stub(clock, calls=calls))
        self.assertTrue(calls)
        self.assertTrue(all(c["max_seconds"] <= 3600 for c in calls))

    def test_transport_break_stops_without_replay(self):
        calls: list = []
        result = self.run_with(self.config(),
                          segment=make_segment_stub(self.clock, breaks=1, calls=calls))
        self.assertEqual(result["terminal_reason"], "transport_break")
        self.assertEqual(len(calls), 1)  # never retried

    def test_publication_denial_stops_and_never_reopens(self):
        calls: list = []
        result = self.run_with(self.config(),
                          segment=make_segment_stub(self.clock, publication_ok=False,
                                                    calls=calls))
        self.assertEqual(result["terminal_reason"], "publication_not_ok")
        self.assertEqual(len(calls), 1)
        self.assertIs(result["publication_ok_last"], False)

    def test_raising_segment_stops_the_night(self):
        from scripts.build_ext_quotes import R2PublicationDenied
        calls: list = []
        result = self.run_with(
            self.config(),
            segment=make_segment_stub(self.clock, calls=calls,
                                      fail_once=R2PublicationDenied("R2 denied publication")))
        self.assertEqual(result["terminal_reason"], "exception:R2PublicationDenied")
        self.assertEqual(len(calls), 1)
        self.assertTrue(Path(result["final_receipt"]).is_file())  # durable evidence

    def test_empty_segments_stay_bounded(self):
        calls: list = []
        result = self.run_with(self.config(), segment=make_segment_stub(self.clock, raw=0,
                                                                   calls=calls))
        self.assertEqual(result["terminal_reason"], "segment_cap_reached")
        self.assertEqual(result["raw_messages_total"], 0)
        self.assertEqual(len(calls), 32)

    def test_count_overflow_is_terminal(self):
        # A corrupt/careless publisher return claiming more messages than its
        # own budget must be caught, not banked, and must end the night.
        def corrupt_segment(*, max_seconds, max_messages, symbols, publish, archive_root):
            return {"raw_messages": max_messages + 1, "transport_breaks": 0,
                    "bytes": 0, "publication_ok": True if publish else None}

        result = self.run_with(self.config(total_max_messages=100),
                               segment=corrupt_segment)
        self.assertEqual(result["terminal_reason"], "count_overflow")
        self.assertEqual(result["raw_messages_total"], 0)  # untrusted count not banked

    def test_window_close_ends_the_night_outside(self):
        # Start near 04:00 ET; the re-clamped window closes mid-session.
        clock = FakeClock(et(2026, 10, 19, 3, 55).astimezone(timezone.utc), step_seconds=600)
        result = self.run_with(self.config(), clock=clock,
                          segment=make_segment_stub(clock, raw=5))
        self.assertEqual(result["terminal_reason"], "overnight_window_closed")
        self.assertTrue(result["window_end_reached"])
        self.assertTrue(result["stopped_outside_window"])

    def test_wall_clock_regression_is_refused(self):
        calls: list = []
        clock = FakeClock(datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc))

        def runner(*, max_seconds, max_messages, symbols, publish, archive_root):
            clock.advance(-3600)  # NTP step backwards mid-night
            return {"raw_messages": 1, "transport_breaks": 0, "bytes": 0,
                    "publication_ok": True if publish else None}

        result = self.run_with(self.config(), clock=clock, segment=runner)
        self.assertEqual(result["terminal_reason"], "clock_regression")
        self.assertEqual(calls, [])


class PublisherBindingTests(unittest.TestCase):
    def test_segment_binds_configured_archive_and_reserve(self):
        from unittest.mock import patch
        with patch("collectors.tiingo_archive.Archive") as archive, patch(
                "scripts.build_ext_quotes.publish_boats_stream", return_value={"raw_messages": 0}) as publisher:
            rbs._run_segment(max_seconds=10, max_messages=100, symbols=["AAPL"],
                             publish=True, archive_root="/Volumes/Mastermind/market-data/tiingo")
        archive.assert_called_once_with(Path("/Volumes/Mastermind/market-data/tiingo"),
                                        free_floor=40 * 1024**3)
        self.assertIs(publisher.call_args.kwargs["archive"], archive.return_value)


class ConfigValidationTests(Harness):
    def test_budget_bounds(self):
        with self.assertRaises(SessionRefused):
            self.config(total_max_messages=80_000_001)
        with self.assertRaises(SessionRefused):
            self.config(total_max_messages=0)
        with self.assertRaises(SessionRefused):
            self.config(segment_max_seconds=3601)
        with self.assertRaises(SessionRefused):
            self.config(max_segments=33)
        with self.assertRaises(SessionRefused):
            self.config(total_max_seconds=8 * 3600 + 1)
        with self.assertRaises(SessionRefused):
            SessionConfig(publish=True, symbols_file="", archive_root="")
        # The documented ceiling itself is accepted.
        self.config(total_max_messages=80_000_000)

    def test_symbols_file_is_required_and_validated(self):
        empty = Path(self.tmp.name) / "empty.txt"; empty.write_text("")
        with self.assertRaises(SessionRefused):
            self.run_with(self.config(symbols_file=str(empty)))
        bad = Path(self.tmp.name) / "bad.txt"; bad.write_text("aapl\n")
        with self.assertRaises(SessionRefused):  # classified incumbent coverage refusal
            self.run_with(self.config(symbols_file=str(bad)))
        self.assertFalse((self.archive / "run-receipts").exists())


class DryRunAndArchiveTests(Harness):
    def test_default_dry_run_has_no_effects(self):
        calls: list = []
        result = self.run_with(self.config(publish=False),
                          segment=make_segment_stub(self.clock, calls=calls))
        self.assertEqual(result["terminal_reason"], "dry_run_plan")
        self.assertEqual(calls, [])
        self.assertIsNone(result["start_receipt"])
        self.assertFalse((self.archive / "run-receipts").exists())
        self.assertIn("first_segment_plan", result)

    def test_archive_reserve_gate(self):
        from unittest.mock import patch
        class Usage:
            def __init__(self, free): self.free = free
        with patch("collectors.tiingo_archive.require_external_root", return_value=self.archive) as mounted:
            with patch.object(rbs.shutil, "disk_usage", return_value=Usage(40 * 1024**3)):
                info = prepare_archive(str(self.archive))
                self.assertEqual(info["free_bytes"], 40 * 1024**3)
            mounted.assert_called_once_with(self.archive, check_mount=True)
            with patch.object(rbs.shutil, "disk_usage", return_value=Usage(40 * 1024**3 - 1)):
                with self.assertRaises(SessionRefused):
                    prepare_archive(str(self.archive))


class CliTests(Harness):
    def test_bounded_cli_keeps_lock_receipts_and_same_session_replay_guard(self):
        from unittest.mock import patch
        calls: list = []
        results: list = []
        stub = make_segment_stub(self.clock, raw=20_000, calls=calls)

        def locked_segment(**kwargs):
            with self.assertRaises(SessionRefused):
                acquire_session_lock(self.archive)
            return stub(**kwargs)

        def execute(config):
            result = self.run_with(config, segment=locked_segment)
            results.append(result)
            return result

        args = ["--publish", "--symbols-file", str(self.symbols_file),
                "--archive-root", str(self.archive), "--total-max-messages", "20000",
                "--total-max-seconds", "60", "--max-segments", "1",
                "--segment-max-seconds", "60"]
        with patch.object(rbs, "run_session", side_effect=execute):
            self.assertEqual(rbs.main(args), 5)  # bounded partial, not a full night
            start = self.archive / "run-receipts" / "run-start-2026-10-19.json"
            original_start = start.read_bytes()
            self.assertEqual(rbs.main(args), 4)  # no same-session second segment
        self.assertEqual(calls, [{"max_seconds": 60, "max_messages": 20_000,
                                 "publish": True, "symbols": 2}])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["terminal_reason"], "segment_cap_reached")
        self.assertEqual(results[0]["elapsed_seconds"], 60)
        self.assertTrue(results[0]["lock_released"])
        self.assertEqual(start.read_bytes(), original_start)
        receipt = json.loads(original_start)
        self.assertEqual(receipt["total_max_seconds"], 60)
        self.assertEqual(receipt["total_max_messages"], 20_000)
        final = json.loads(Path(results[0]["final_receipt"]).read_text())
        self.assertEqual(final["total_seconds_budget"], 60)
        self.assertEqual(final["raw_messages_total"], 20_000)
        self.assertEqual(final["segments_run"], 1)
        fd = acquire_session_lock(self.archive)
        os.close(fd)

    def test_cli_rejects_invalid_time_budget_before_runner_effects(self):
        from unittest.mock import patch
        args = ["--publish", "--symbols-file", str(self.symbols_file),
                "--archive-root", str(self.archive), "--total-max-messages", "20000"]
        invalid = [["--total-max-seconds", value] for value in ("-1", "0", "28801")]
        invalid.append(["--total-max-seconds", "60", "--max-segments", "1",
                        "--segment-max-seconds", "59"])
        with patch.object(rbs, "run_session") as runner:
            for options in invalid:
                with self.subTest(options=options):
                    self.assertEqual(rbs.main(args + options), 2)
            runner.assert_not_called()
        self.assertFalse((self.archive / "run-receipts").exists())

    def test_cli_default_time_budget_remains_full_session(self):
        from unittest.mock import patch
        results: list = []

        def execute(config):
            result = self.run_with(config)
            results.append(result)
            return result

        with patch.object(rbs, "run_session", side_effect=execute):
            self.assertEqual(rbs.main(["--symbols-file", str(self.symbols_file)]), 0)
        self.assertEqual(results[0]["total_seconds_budget"], 28_800)
        self.assertEqual(results[0]["first_segment_plan"]["max_seconds"], 3_600)
        self.assertFalse((self.archive / "run-receipts").exists())

    def test_cli_bounded_dry_run_does_not_open_archive_or_stream(self):
        from unittest.mock import patch
        results: list = []

        def execute(config):
            result = run_session(config, clock=self.clock, local_tz=VANCOUVER,
                archive_prep=lambda _: self.fail("dry-run opened archive"),
                segment_runner=lambda **_: self.fail("dry-run opened stream"))
            results.append(result)
            return result

        with patch.object(rbs, "run_session", side_effect=execute):
            self.assertEqual(rbs.main(["--symbols-file", str(self.symbols_file),
                "--total-max-seconds", "60", "--total-max-messages", "20000",
                "--max-segments", "1", "--segment-max-seconds", "60"]), 0)
        self.assertEqual(results[0]["terminal_reason"], "dry_run_plan")
        self.assertEqual(results[0]["first_segment_plan"],
                         {"max_seconds": 60, "max_messages": 20_000})
        self.assertIsNone(results[0]["start_receipt"])
        self.assertFalse((self.archive / "run-receipts").exists())

    def test_publish_requires_explicit_budget_and_paths(self):
        self.assertEqual(rbs.main(["--publish"]), 2)
        self.assertEqual(rbs.main(["--publish", "--total-max-messages", "1000"]), 2)
        self.assertEqual(rbs.main(["--publish", "--symbols-file", str(self.symbols_file)]), 2)
        self.assertEqual(rbs.main(["--publish", "--archive-root", str(self.archive)]), 2)
        self.assertFalse((self.archive / "run-receipts").exists())

    def test_publish_rejects_out_of_range_budget(self):
        self.assertEqual(rbs.main(["--publish", "--symbols-file", str(self.symbols_file),
                                   "--archive-root", str(self.archive),
                                   "--total-max-messages", "80000001"]), 2)
        self.assertEqual(rbs.main(["--publish", "--symbols-file", str(self.symbols_file),
                                   "--archive-root", str(self.archive),
                                   "--total-max-messages", "0"]), 2)


class ReviewRegressionTests(Harness):
    def test_real_os_zone_name_is_verified_without_injected_timezone(self):
        from unittest.mock import patch
        with patch.object(rbs.os, "readlink", return_value="/var/db/timezone/zoneinfo/America/Vancouver"):
            proof = validate_host_timezone(self.clock.utc)
            self.assertEqual(proof["host_zone"], "America/Vancouver")
            self.assertTrue(proof["host_timezone_ok"])
        for target in ("/usr/share/zoneinfo/Etc/GMT+7", "/unrecognized"):
            with patch.object(rbs.os, "readlink", return_value=target):
                with self.assertRaises(HostTimezoneError):
                    validate_host_timezone(self.clock.utc)

    def test_full_eight_hour_night_closes_cleanly(self):
        self.clock.step = 3600
        result = self.run_with(self.config())
        self.assertEqual(result["segments_run"], 8)
        self.assertEqual(result["terminal_reason"], "overnight_window_closed")
        self.assertTrue(result["window_end_reached"])
        receipt = json.loads(Path(result["start_receipt"]).read_text())
        self.assertEqual(receipt["host_zone"], "America/Vancouver")

    def test_too_short_segment_plan_is_refused(self):
        with self.assertRaisesRegex(SessionRefused, "cannot cover"):
            self.config(segment_max_seconds=600)

    def test_stop_receipt_retains_capture_and_publication_cause(self):
        result = self.run_with(self.config(),
            segment=make_segment_stub(self.clock, publication_ok=False))
        retained = json.loads(Path(result["final_receipt"]).read_text())
        self.assertEqual(retained["capture_ids"], ["stub"])
        self.assertEqual(retained["last_segment"]["publication"], {"requested": True})
        self.assertFalse(retained["window_end_reached"])

    def test_malformed_segment_return_stops_with_receipt_and_unbanked_counts(self):
        for index, payload in enumerate((None, {"raw_messages": 1, "bytes": "bad",
                "transport_breaks": 0}, {"raw_messages": 1, "bytes": 1,
                "transport_breaks": 0, "publication": object()})):
            archive = self.archive / str(index)
            archive.mkdir()
            result = self.run_with(self.config(archive_root=str(archive)),
                segment=lambda **_: payload)
            self.assertEqual(result["raw_messages_total"], 0)
            self.assertEqual(result["bytes_total"], 0)
            self.assertTrue(Path(result["final_receipt"]).is_file())
            self.assertTrue(result["lock_released"])

    def test_interrupt_leaves_terminal_evidence_and_blocks_replay(self):
        def interrupted(**_):
            rbs._interrupt(rbs.signal.SIGTERM, None)
        result = self.run_with(self.config(), segment=interrupted)
        self.assertEqual(result["terminal_reason"], "exception:SessionInterrupted")
        self.assertTrue(Path(result["final_receipt"]).is_file())
        with self.assertRaises(StartReceiptBlocked):
            self.run_with(self.config())

    def test_cli_distinguishes_closed_window_from_budget_partial_and_restores_signals(self):
        from unittest.mock import patch
        handlers = {sig: rbs.signal.getsignal(sig) for sig in (rbs.signal.SIGTERM, rbs.signal.SIGINT)}
        args = ["--publish", "--symbols-file", str(self.symbols_file),
                "--archive-root", str(self.archive), "--total-max-messages", "1000"]
        for reason, expected in [("overnight_window_closed", 0), ("outside_overnight_window", 0),
                                 ("message_budget_exhausted", 5), ("segment_cap_reached", 5),
                                 ("time_budget_exhausted", 5), ("publication_not_ok", 1)]:
            with patch.object(rbs, "run_session", return_value={"terminal_reason": reason}):
                self.assertEqual(rbs.main(args), expected)
            self.assertEqual({sig: rbs.signal.getsignal(sig) for sig in handlers}, handlers)

    def test_dst_change_sunday_is_closed_and_following_session_is_eight_hours(self):
        for year, month, day in [(2026, 3, 8), (2026, 11, 1)]:
            self.assertIsNone(boats_session_date(et(year, month, day, 1, 30)))
            start = et(year, month, day, 20, 0)
            self.assertIsNotNone(boats_session_date(start))
            self.assertEqual(rbs.seconds_until_boundary(start.astimezone(timezone.utc)), 28800)


if __name__ == "__main__":
    unittest.main()


def test_quote_calendar_candidates_require_new_york_entry_guard():
    import plistlib
    root = Path(__file__).resolve().parents[1]
    job = plistlib.loads((root/"ops/launchd/com.macro.extquotes.plist").read_bytes())
    assert job["StartCalendarInterval"] == [
        {"Weekday": day, "Hour": hour, "Minute": 0} for day in range(5) for hour in (17,18)]
    assert not job.get("KeepAlive") and not job.get("RunAtLoad") and "StartInterval" not in job
    assert "--publish --scheduled" in (root/"ops/launchd/run_ext_quotes_loop.sh").read_text()


def test_quote_job_uses_selected_runtime_and_existing_env_without_relaunch():
    import plistlib
    root = Path(__file__).resolve().parents[1]
    job = plistlib.loads((root / "ops/launchd/com.macro.extquotes.plist").read_bytes())
    runtime = "/Volumes/Mastermind/market-data/tiingo-runtime/current"
    args = job["ProgramArguments"]
    assert args[:4] == ["/bin/sh", runtime + "/ops/launchd/run_with_env.sh",
                       "/Users/chriswong/Documents/Cluade/Macro Dashboard/.env", "/usr/bin/env"]
    assert args[-2:] == ["/bin/sh", runtime + "/ops/launchd/run_ext_quotes_loop.sh"]
    assert "BOATS_REPO_ROOT=" + runtime in args[4:-2]
    assert "BOATS_TOTAL_MAX_MESSAGES=80000000" in args[4:-2]
    assert job["WorkingDirectory"] == runtime
    assert job["RunAtLoad"] is False and job["KeepAlive"] is False
    assert "StartInterval" not in job
    assert "flow-ops-wt" not in str(job)
