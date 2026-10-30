"""Source-only 120m/180m conformance; no historical market backtest."""
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.entry_radar.replay.oscillator_mtf_research import (
    aggregate_owner_windows, oscillator_events,
)

SHA = "a" * 64


def schedule(day="2026-10-30", closing="16:00"):
    opened = pd.Timestamp(day + " 09:30", tz="America/New_York").tz_convert("UTC")
    ended = pd.Timestamp(day + " " + closing, tz="America/New_York").tz_convert("UTC")
    return {date.fromisoformat(day): (opened, ended)}


class Reader:
    def __init__(self, mode="ok"):
        self.calls = []
        self.mode = mode

    def __call__(self, sym, start, end, cutoff):
        self.calls.append((sym, start, end, cutoff))
        st, en = pd.Timestamp(start), pd.Timestamp(end)
        mins = int((en - st).total_seconds() // 60)
        ret = {"availability": "available", "start": start, "end": end,
               "expected_minutes": mins, "observed_minutes": mins,
               "known_at": (en + pd.Timedelta(seconds=2)).isoformat(),
               "ohlcv": {"open": 99., "high": 101., "low": 98., "close": 100., "volume": 5.},
               "input_revision_sha256": SHA, "refusals": []}
        if self.mode == "missing":
            ret.update(availability="unavailable", observed_minutes=mins - 1,
                       refusals=["MISSING_OR_NOT_YET_KNOWN_MINUTE"])
        elif self.mode == "future":
            ret["known_at"] = (pd.Timestamp(cutoff) + pd.Timedelta(seconds=1)).isoformat()
        elif self.mode == "wrong_basis":
            ret["input_revision_sha256"] = "wrong-sha"
        elif self.mode == "invalid":
            ret["ohlcv"]["low"] = 102.
        elif self.mode == "available_refusal":
            ret["refusals"] = ["OWNER_REFUSED_BASIS"]
        return ret


def run(grain=120, calendar=None, cutoff="2026-10-30T20:00:00Z", reader=None):
    if reader is None:
        reader = Reader()
    return aggregate_owner_windows(symbol="A", calendar=calendar or schedule(),
                                   decision_utc=cutoff, minutes=grain, read_aggregate=reader)


def eligible(rows, first_day="2026-10-29", is_leader=True, known_shift=0):
    out = {}
    for row in rows:
        if row["status"] != "FULL_KNOWN":
            continue
        when = pd.Timestamp(row["bar_end_utc"]) + pd.Timedelta(seconds=known_shift)
        out[(row["symbol"], row["bar_end_utc"])] = {
            "is_leader": is_leader, "known_at_utc": when.isoformat(),
            "asof_session": first_day, "expected_prior_session": "2026-10-29",
            "receipt_sha256": SHA,
        }
    return out


class MtfBars(unittest.TestCase):
    def test_120_three_full_and_one_stub(self):
        reader = Reader()
        rows = run(reader=reader)
        self.assertEqual([r["status"] for r in rows], ["FULL_KNOWN"]*3+["STUB_EXCLUDED"])
        self.assertEqual(len(reader.calls), 3)
        self.assertEqual(rows[-1]["stub_minutes"], 30)
        self.assertFalse(any(r["source_admitted"] for r in rows))

    def test_180_two_full_and_one_stub(self):
        reader = Reader()
        rows = run(grain=180, reader=reader)
        self.assertEqual([r["status"] for r in rows], ["FULL_KNOWN"]*2+["STUB_EXCLUDED"])
        self.assertEqual(len(reader.calls), 2)
        self.assertEqual(rows[0]["bar_end_utc"], "2026-10-30T16:30:00+00:00")

    def test_halfday_120_excludes_90m_stub(self):
        rows = run(calendar=schedule("2026-11-27", "13:00"),
                   cutoff="2026-11-27T19:00:00Z")
        self.assertEqual([r["status"] for r in rows], ["FULL_KNOWN", "STUB_EXCLUDED"])
        self.assertEqual(rows[-1]["stub_minutes"], 90)

    def test_halfday_180_excludes_30m_stub(self):
        rows = run(grain=180, calendar=schedule("2026-11-27", "13:00"),
                   cutoff="2026-11-27T19:00:00Z")
        self.assertEqual(rows[-1]["stub_minutes"], 30)

    def test_future_bar_not_read_or_scored(self):
        reader = Reader()
        rows = run(cutoff="2026-10-30T16:00:00Z", reader=reader)
        self.assertEqual(len(reader.calls), 1)
        self.assertEqual([r["status"] for r in rows[:3]],
                         ["FULL_KNOWN", "NOT_YET_OBSERVED", "NOT_YET_OBSERVED"])

    def test_late_owner_known_at_is_unavailable(self):
        rows = run(reader=Reader("future"))
        self.assertEqual({r["status"] for r in rows[:-1]}, {"UNAVAILABLE"})

    def test_missing_minutes_are_not_fabricated(self):
        rows = run(reader=Reader("missing"))
        self.assertEqual({r["status"] for r in rows[:-1]}, {"UNAVAILABLE"})
        self.assertIsNone(rows[0]["ohlcv"])

    def test_bad_sha_is_not_an_admitted_receipt(self):
        rows = run(reader=Reader("wrong_basis"))
        self.assertEqual(rows[0]["refusals"], ["INVALID_OR_LATE_OWNER_RECEIPT"])

    def test_available_with_owner_refusal_is_not_a_known_bar(self):
        rows = run(reader=Reader("available_refusal"))
        self.assertEqual(rows[0]["status"], "UNAVAILABLE")
        self.assertIn("INVALID_OR_LATE_OWNER_RECEIPT", rows[0]["refusals"])

    def test_invalid_owner_ohlc_is_refused(self):
        rows = run(reader=Reader("invalid"))
        self.assertEqual(rows[0]["status"], "UNAVAILABLE")

    def test_naive_calendar_refuses(self):
        cal = {date(2026,10,30): ("2026-10-30T09:30:00", "2026-10-30T16:00:00")}
        with self.assertRaisesRegex(ValueError, "naive/display"):
            run(calendar=cal)

    def test_future_session_has_no_reader_call(self):
        reader = Reader()
        rows = run(calendar=schedule("2026-11-02"), reader=reader)
        self.assertEqual(rows, [])
        self.assertFalse(reader.calls)

    def test_dst_changes_utc_open_without_rephasing(self):
        cal = {**schedule("2026-10-30"), **schedule("2026-11-02")}
        rows = run(calendar=cal, cutoff="2026-11-03T00:00:00Z")
        self.assertEqual(len([x for x in rows if x["status"] == "FULL_KNOWN"]), 6)
        self.assertEqual(rows[0]["bar_start_utc"], "2026-10-30T13:30:00+00:00")
        self.assertEqual(rows[4]["bar_start_utc"], "2026-11-02T14:30:00+00:00")

    def test_unrecognized_grain_refused(self):
        with self.assertRaisesRegex(ValueError, "120m/180m"):
            run(grain=30)


class OscillatorSignals(unittest.TestCase):
    def setUp(self):
        self.rows = run()
        self.elig = eligible(self.rows)
        self.key = (self.rows[1]["symbol"], self.rows[1]["bar_end_utc"])

    def supplied(self):
        result = {}
        for i, row in enumerate(self.rows):
            if row["status"] != "FULL_KNOWN":
                continue
            result[(row["symbol"],row["bar_end_utc"])] = {
                "fast": -3. if i == 0 else -1., "slow": -2.,
                "oversold": True, "known_at_utc": row["known_at_utc"],
                "source_sha256": SHA,
            }
        return result

    def test_supplied_below_zero_cross_requires_previous_bar(self):
        events = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=self.elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(events[0]["signal"])
        self.assertEqual(events[1]["state"], "CROSS_OBSERVED")
        self.assertTrue(events[1]["signal"])
        self.assertEqual(events[-1]["state"], "SOURCE_STUB_EXCLUDED")

    def test_future_exported_line_rejects_signal(self):
        supp = self.supplied()
        supp[self.key]["known_at_utc"] = "2026-11-02T00:00:00Z"
        events = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=self.elig, supplied=supp,
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(events[1]["signal"])

    def test_future_previous_line_cannot_backdate_cross(self):
        supp = self.supplied()
        first_key = (self.rows[0]["symbol"], self.rows[0]["bar_end_utc"])
        supp[first_key]["known_at_utc"] = "2026-11-02T00:00:00Z"
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                               eligibility=self.elig, supplied=supp,
                               decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_current_day_leader_cannot_backdate(self):
        elig = eligible(self.rows, first_day="2026-10-30")
        events = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(events[1]["state"], "ELIGIBILITY_UNAVAILABLE")

    def test_late_leader_receipt_is_refused(self):
        elig = eligible(self.rows, known_shift=86400)
        events = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(events[1]["signal"])

    def test_not_leader_is_not_a_buy(self):
        elig = eligible(self.rows, is_leader=False)
        events = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(events[1]["state"], "NOT_LEADER")
        self.assertIsNone(events[1]["signal"])

    def test_stale_historical_leader_receipt_refused(self):
        elig = eligible(self.rows, first_day="2026-10-20")
        events = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(events[1]["state"], "ELIGIBILITY_UNAVAILABLE")

    def test_mismatched_current_export_digest_refuses_signal(self):
        supp = self.supplied()
        supp[self.key]["source_sha256"] = "b"*64
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_mismatched_previous_export_digest_refuses_signal(self):
        supp = self.supplied()
        first_key = (self.rows[0]["symbol"], self.rows[0]["bar_end_utc"])
        supp[first_key]["source_sha256"] = "b"*64
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_export_line_precedes_source_receipt_refused(self):
        supp = self.supplied()
        supp[self.key]["known_at_utc"] = self.rows[1]["bar_end_utc"]
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_malformed_previous_export_clock_refuses_without_future_signal(self):
        supp = self.supplied()
        first_key = (self.rows[0]["symbol"], self.rows[0]["bar_end_utc"])
        supp[first_key]["known_at_utc"] = "2026-10-30T16:30:00"
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_mixed_120m_180m_bars_refused(self):
        combined = self.rows + run(grain=180)
        with self.assertRaisesRegex(ValueError, "mix 120m and 180m"):
            oscillator_events(bars=combined, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_duplicate_bar_identity_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate observed"):
            oscillator_events(bars=self.rows + [self.rows[0]], indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_forged_full_bar_with_refusal_refused(self):
        changed = [dict(x) for x in self.rows]
        changed[1]["refusals"] = ["OWNER_REFUSED_SOURCE"]
        with self.assertRaisesRegex(ValueError, "inconsistent full bar"):
            oscillator_events(bars=changed, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_modified_full_bar_bounds_refused(self):
        changed = [dict(x) for x in self.rows]
        changed[1]["bar_start_utc"] = changed[0]["bar_start_utc"]
        with self.assertRaisesRegex(ValueError, "inconsistent full bar"):
            oscillator_events(bars=changed, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_unknown_indicator_refused(self):
        with self.assertRaisesRegex(ValueError, "frozen known"):
            oscillator_events(bars=self.rows, indicator="NOT_MACD", eligibility=self.elig,
                              decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_source_gap_resets_oscillator_and_is_explicit(self):
        rows = self.rows.copy()
        rows[1] = dict(rows[1], status="UNAVAILABLE", ohlcv=None, known_at_utc=None)
        ev = oscillator_events(bars=rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=self.supplied(), decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "SOURCE_UNAVAILABLE")
        self.assertEqual(ev[2]["state"], "WARMUP_OR_OSCILLATOR_UNAVAILABLE")

    def test_price_macd_proxy_not_confused_with_canon_rsi_macd(self):
        a = oscillator_events(bars=self.rows, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")
        b = oscillator_events(bars=self.rows, indicator="PRICE_MACD_RSI_PROXY",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(a[0]["state"], "WARMUP_OR_OSCILLATOR_UNAVAILABLE")
        self.assertEqual(b[0]["state"], "WARMUP_OR_OSCILLATOR_UNAVAILABLE")
        self.assertNotEqual(a[0]["indicator"], b[0]["indicator"])

    def test_supplied_false_oversold_cannot_cross(self):
        supp = self.supplied()
        supp[self.key]["oversold"] = False
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "NO_CROSS")
        self.assertFalse(ev[1]["signal"])

    def test_source_entry_never_grants_signal_authority(self):
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=self.supplied(), decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertFalse(any(x["source_admitted"] for x in ev))


if __name__ == "__main__":
    unittest.main()
