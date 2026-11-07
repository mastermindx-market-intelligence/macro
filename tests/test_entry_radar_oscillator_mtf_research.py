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
# Declared synthetic calendar facts, frozen before any observation is removed.
# This is not an exchange-calendar qualification.
SYNTHETIC_PREDECESSORS = {
    date(2026, 10, 30): date(2026, 10, 29),
    date(2026, 11, 2): date(2026, 10, 30),
    date(2026, 11, 3): date(2026, 11, 2),
    date(2026, 11, 25): date(2026, 11, 24),
    date(2026, 11, 27): date(2026, 11, 25),
}


def declared_events(**kwargs):
    """Existing conformance cases declare their fixed assessment cutoff up front."""
    kwargs.setdefault("prior_session_by_day", SYNTHETIC_PREDECESSORS)
    kwargs.setdefault("original_decisions", {
        (row["symbol"], row["bar_end_utc"]): {
            "candidate_id": "synthetic:" + row["symbol"] + ":" + row["bar_end_utc"],
            "decision_at": kwargs["decision_cutoff_utc"],
            "session": row["session_date"],
        } for row in kwargs["bars"] if row["status"] == "FULL_KNOWN"
    })
    return oscillator_events(**kwargs)


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


def eligible(rows, first_day=None, is_leader=True, known_shift=0):
    out = {}
    for row in rows:
        if row["status"] != "FULL_KNOWN":
            continue
        prior = SYNTHETIC_PREDECESSORS[date.fromisoformat(row["session_date"])].isoformat()
        when = pd.Timestamp(row["bar_end_utc"]) + pd.Timedelta(seconds=known_shift)
        out[(row["symbol"], row["bar_end_utc"])] = {
            "is_leader": is_leader, "known_at_utc": when.isoformat(),
            "asof_session": first_day if first_day is not None else prior,
            "expected_prior_session": prior,
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
        events = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=self.elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(events[0]["signal"])
        self.assertEqual(events[1]["state"], "CROSS_OBSERVED")
        self.assertTrue(events[1]["signal"])
        self.assertEqual(events[-1]["state"], "SOURCE_STUB_EXCLUDED")

    def test_future_exported_line_rejects_signal(self):
        supp = self.supplied()
        supp[self.key]["known_at_utc"] = "2026-11-02T00:00:00Z"
        events = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=self.elig, supplied=supp,
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(events[1]["signal"])

    def test_future_previous_line_cannot_backdate_cross(self):
        supp = self.supplied()
        first_key = (self.rows[0]["symbol"], self.rows[0]["bar_end_utc"])
        supp[first_key]["known_at_utc"] = "2026-11-02T00:00:00Z"
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                               eligibility=self.elig, supplied=supp,
                               decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_current_day_leader_cannot_backdate(self):
        elig = eligible(self.rows, first_day="2026-10-30")
        events = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(events[1]["state"], "ELIGIBILITY_UNAVAILABLE")

    def test_late_leader_receipt_is_refused(self):
        elig = eligible(self.rows, known_shift=86400)
        events = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(events[1]["signal"])

    def test_not_leader_is_not_a_buy(self):
        elig = eligible(self.rows, is_leader=False)
        events = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(events[1]["state"], "NOT_LEADER")
        self.assertIsNone(events[1]["signal"])

    def test_stale_historical_leader_receipt_refused(self):
        elig = eligible(self.rows, first_day="2026-10-20")
        events = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                                   eligibility=elig, supplied=self.supplied(),
                                   decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(events[1]["state"], "ELIGIBILITY_UNAVAILABLE")

    def test_mismatched_current_export_digest_refuses_signal(self):
        supp = self.supplied()
        supp[self.key]["source_sha256"] = "b"*64
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_mismatched_previous_export_digest_refuses_signal(self):
        supp = self.supplied()
        first_key = (self.rows[0]["symbol"], self.rows[0]["bar_end_utc"])
        supp[first_key]["source_sha256"] = "b"*64
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_export_line_precedes_source_receipt_refused(self):
        supp = self.supplied()
        supp[self.key]["known_at_utc"] = self.rows[1]["bar_end_utc"]
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_malformed_previous_export_clock_refuses_without_future_signal(self):
        supp = self.supplied()
        first_key = (self.rows[0]["symbol"], self.rows[0]["bar_end_utc"])
        supp[first_key]["known_at_utc"] = "2026-10-30T16:30:00"
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertIsNone(ev[1]["signal"])

    def test_missing_entire_owner_trading_session_is_refused(self):
        cal = {**schedule('2026-10-30'), **schedule('2026-11-02'),
               **schedule('2026-11-03')}
        rows = run(calendar=cal, cutoff='2026-11-04T00:00:00Z')
        rows = [row for row in rows if row['session_date'] != '2026-11-02']
        expected = {date(2026,11,2): date(2026,10,30),
                    date(2026,11,3): date(2026,11,2)}
        with self.assertRaisesRegex(ValueError, 'missing owner predecessor session'):
            declared_events(bars=rows, indicator='CANON_RSI_MACD',
                              eligibility=eligible(rows),
                              prior_session_by_day=expected,
                              decision_cutoff_utc='2026-11-04T00:00:00Z')

    def test_legitimate_weekend_contiguous_with_owner_prior_map(self):
        cal = {**schedule('2026-10-30'), **schedule('2026-11-02')}
        rows = run(calendar=cal, cutoff='2026-11-03T00:00:00Z')
        result = declared_events(bars=rows, indicator='CANON_RSI_MACD',
                    eligibility=eligible(rows),
                    prior_session_by_day=SYNTHETIC_PREDECESSORS,
                    decision_cutoff_utc='2026-11-03T00:00:00Z')
        self.assertFalse(any(x['state'] in {'SOURCE_OWNER_PREDECESSOR_UNKNOWN',
                                           'ELIGIBILITY_UNAVAILABLE'} for x in result))

    def test_multi_session_without_owner_predecessor_abstains(self):
        cal = {**schedule('2026-10-30'), **schedule('2026-11-02')}
        rows = run(calendar=cal, cutoff='2026-11-03T00:00:00Z')
        result = declared_events(bars=rows, indicator='SUPPLIED_LINES',
                    eligibility=eligible(rows), supplied=self.supplied(),
                    prior_session_by_day=None,
                    decision_cutoff_utc='2026-11-03T00:00:00Z')
        after = [x for x in result if x['bar_end_utc'].startswith('2026-11-02')
                 and x['state'] != 'SOURCE_STUB_EXCLUDED']
        self.assertTrue(after)
        self.assertTrue(all(x['state'] == 'SOURCE_OWNER_PREDECESSOR_UNKNOWN'
                            and x['signal'] is None for x in after))

    def test_missing_terminal_stub_between_sessions_refused(self):
        cal = {**schedule('2026-10-30'), **schedule('2026-11-02')}
        rows = run(calendar=cal, cutoff='2026-11-02T23:00:00Z')
        rows = [row for row in rows if not (
            row['session_date'] == '2026-10-30' and row['status'] == 'STUB_EXCLUDED')]
        with self.assertRaisesRegex(ValueError, 'missing terminal session stub'):
            declared_events(bars=rows, indicator='CANON_RSI_MACD', eligibility=eligible(rows),
                              decision_cutoff_utc='2026-11-02T23:00:00Z')

    def test_missing_last_full_bar_and_stub_cannot_bridge_next_session(self):
        cal = {**schedule('2026-10-30'), **schedule('2026-11-02')}
        rows = run(calendar=cal, cutoff='2026-11-02T23:00:00Z')
        rows = [row for row in rows if not (
            row['session_date'] == '2026-10-30' and
            row['bar_start_utc'] >= '2026-10-30T17:30:00+00:00')]
        with self.assertRaisesRegex(ValueError, 'missing terminal session stub'):
            declared_events(bars=rows, indicator='CANON_RSI_MACD', eligibility=eligible(rows),
                              decision_cutoff_utc='2026-11-02T23:00:00Z')

    def test_mixed_120m_180m_bars_refused(self):
        combined = self.rows + run(grain=180)
        with self.assertRaisesRegex(ValueError, "mix 120m and 180m"):
            declared_events(bars=combined, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_missing_first_full_bar_cannot_rephase_history(self):
        missing_open = self.rows[1:]
        with self.assertRaisesRegex(ValueError, "missing opening full bar"):
            declared_events(bars=missing_open, indicator="SUPPLIED_LINES",
                              eligibility=self.elig, supplied=self.supplied(),
                              decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_removed_middle_full_bar_cannot_create_false_crossover(self):
        missing_middle = [self.rows[0], self.rows[2], self.rows[3]]
        with self.assertRaisesRegex(ValueError, "missing full RTH slots"):
            declared_events(bars=missing_middle, indicator="SUPPLIED_LINES",
                              eligibility=self.elig, supplied=self.supplied(),
                              decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_duplicate_bar_identity_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate observed"):
            declared_events(bars=self.rows + [self.rows[0]], indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_forged_full_bar_with_refusal_refused(self):
        changed = [dict(x) for x in self.rows]
        changed[1]["refusals"] = ["OWNER_REFUSED_SOURCE"]
        with self.assertRaisesRegex(ValueError, "inconsistent full bar"):
            declared_events(bars=changed, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_modified_full_bar_bounds_refused(self):
        changed = [dict(x) for x in self.rows]
        changed[1]["bar_start_utc"] = changed[0]["bar_start_utc"]
        with self.assertRaisesRegex(ValueError, "missing or overlapping RTH bar"):
            declared_events(bars=changed, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_unknown_indicator_refused(self):
        with self.assertRaisesRegex(ValueError, "frozen known"):
            declared_events(bars=self.rows, indicator="NOT_MACD", eligibility=self.elig,
                              decision_cutoff_utc="2026-10-30T20:00:00Z")

    def test_source_gap_resets_oscillator_and_is_explicit(self):
        rows = self.rows.copy()
        rows[1] = dict(rows[1], status="UNAVAILABLE", ohlcv=None, known_at_utc=None)
        ev = declared_events(bars=rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=self.supplied(), decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "SOURCE_UNAVAILABLE")
        self.assertEqual(ev[2]["state"], "WARMUP_OR_OSCILLATOR_UNAVAILABLE")

    def test_price_macd_proxy_not_confused_with_canon_rsi_macd(self):
        a = declared_events(bars=self.rows, indicator="CANON_RSI_MACD",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")
        b = declared_events(bars=self.rows, indicator="PRICE_MACD_RSI_PROXY",
                              eligibility=self.elig, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(a[0]["state"], "WARMUP_OR_OSCILLATOR_UNAVAILABLE")
        self.assertEqual(b[0]["state"], "WARMUP_OR_OSCILLATOR_UNAVAILABLE")
        self.assertNotEqual(a[0]["indicator"], b[0]["indicator"])

    def test_supplied_false_oversold_cannot_cross(self):
        supp = self.supplied()
        supp[self.key]["oversold"] = False
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=supp, decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "NO_CROSS")
        self.assertFalse(ev[1]["signal"])

    def test_source_entry_never_grants_signal_authority(self):
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES", eligibility=self.elig,
                               supplied=self.supplied(), decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertFalse(any(x["source_admitted"] for x in ev))


    def test_two_agreeing_wrong_leader_dates_disagree_with_actual_owner(self):
        elig = eligible(self.rows)
        elig[self.key].update(asof_session="2026-10-20", expected_prior_session="2026-10-20")
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                             eligibility=elig, supplied=self.supplied(),
                             decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "ELIGIBILITY_UNAVAILABLE")
        self.assertIsNone(ev[1]["signal"])
        self.assertIsNone(ev[1]["issued_at_utc"])

    def test_first_session_requires_actual_owner_predecessor_for_eligibility(self):
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                             eligibility=self.elig, supplied=self.supplied(),
                             prior_session_by_day={},
                             decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "ELIGIBILITY_UNAVAILABLE")

    def test_missing_original_decisions_preserves_unavailable_population(self):
        ev = oscillator_events(bars=self.rows, indicator="SUPPLIED_LINES",
                               eligibility=self.elig, supplied=self.supplied(),
                               prior_session_by_day=SYNTHETIC_PREDECESSORS,
                               decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(len(ev), len(self.rows))
        self.assertTrue(all(x["state"] == "ORIGINAL_DECISION_UNAVAILABLE" for x in ev[:-1]))
        self.assertTrue(all(x["signal"] is None and x["issued_at_utc"] is None for x in ev))

    def test_malformed_original_decision_has_no_clock_fallback(self):
        for declaration in (None, {}, {"candidate_id": " "},
                {"candidate_id": "owner-id", "decision_at": "2026-10-30T20:00:00"},
                {"candidate_id": "owner-id", "decision_at": "2026-10-30T15:00:00Z"},
                {"candidate_id": "owner-id", "decision_at": "2026-10-31T00:00:00Z"},
                {"candidate_id": "owner-id", "decision_at": "2026-10-30T20:00:00Z",
                 "session": "2026-10-29"}):
            with self.subTest(declaration=declaration):
                ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
                    eligibility=self.elig, supplied=self.supplied(),
                    original_decisions={self.key: declaration},
                    decision_cutoff_utc="2026-10-30T20:00:00Z")
                self.assertEqual(ev[1]["state"], "ORIGINAL_DECISION_UNAVAILABLE")
                self.assertIsNone(ev[1]["signal"])
                self.assertIsNone(ev[1]["issued_at_utc"])

    def test_duplicate_original_candidate_identity_cannot_mint_two_opportunities(self):
        declaration = {"candidate_id": "same-owner-id", "decision_at": "2026-10-30T20:00:00Z"}
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
            eligibility=self.elig, supplied=self.supplied(),
            original_decisions={(self.rows[0]["symbol"], self.rows[0]["bar_end_utc"]): declaration,
                                self.key: dict(declaration)},
            decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[0]["state"], "ORIGINAL_DECISION_UNAVAILABLE")
        self.assertEqual(ev[1]["state"], "ORIGINAL_DECISION_UNAVAILABLE")

    def test_missing_consumed_warmup_projection_binding_refuses_original(self):
        rows = [dict(x) for x in self.rows]
        del rows[0]["projection_cutoff_utc"]
        ev = declared_events(bars=rows, indicator="SUPPLIED_LINES",
            eligibility=self.elig, supplied=self.supplied(),
            decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "SOURCE_ORIGINAL_VINTAGE_UNAVAILABLE")
        self.assertIsNone(ev[1]["signal"])

    def test_late_flat_projection_cannot_be_relabelled_as_earlier_original(self):
        ev = declared_events(bars=self.rows, indicator="SUPPLIED_LINES",
            eligibility=self.elig, supplied=self.supplied(),
            original_decisions={self.key: {"candidate_id": "original-owner-id",
                                           "decision_at": "2026-10-30T17:30:02Z"}},
            decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "SOURCE_ORIGINAL_VINTAGE_UNAVAILABLE")
        self.assertEqual(ev[1]["candidate_id"], "original-owner-id")
        self.assertEqual(ev[1]["decision_at_utc"], "2026-10-30T17:30:02+00:00")
        self.assertIsNone(ev[1]["issued_at_utc"])

    def test_supplied_current_and_prior_lines_must_be_visible_at_original_decision(self):
        decision = "2026-10-30T17:30:02Z"
        rows = run(cutoff=decision)
        declaration = {self.key: {"candidate_id": "line-original", "decision_at": decision}}
        arguments = dict(bars=rows, indicator="SUPPLIED_LINES", eligibility=eligible(rows),
                         original_decisions=declaration,
                         decision_cutoff_utc="2026-10-30T20:00:00Z")
        good = declared_events(supplied=self.supplied(), **arguments)
        self.assertEqual(good[1]["state"], "CROSS_OBSERVED")
        for key in (self.key, (rows[0]["symbol"], rows[0]["bar_end_utc"])):
            with self.subTest(line=key):
                supplied = self.supplied()
                supplied[key]["known_at_utc"] = "2026-10-30T17:31:00Z"
                ev = declared_events(supplied=supplied, **arguments)
                self.assertIsNone(ev[1]["signal"])
                self.assertIsNone(ev[1]["issued_at_utc"])
                self.assertEqual(ev[1]["candidate_id"], good[1]["candidate_id"])

    def test_eligibility_visible_only_by_late_replay_is_unavailable_at_original(self):
        decision = "2026-10-30T17:30:02Z"
        rows = run(cutoff=decision)
        elig = eligible(rows)
        elig[self.key]["known_at_utc"] = "2026-10-30T17:31:00Z"
        ev = declared_events(bars=rows, indicator="SUPPLIED_LINES",
            eligibility=elig, supplied=self.supplied(),
            original_decisions={self.key: {"candidate_id": "leader-original", "decision_at": decision}},
            decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "ELIGIBILITY_UNAVAILABLE")
        self.assertIsNone(ev[1]["signal"])

    def test_original_clock_and_complete_input_watermark_are_distinct(self):
        decision = "2026-10-30T18:00:00Z"
        rows = run(cutoff=decision)
        elig, supplied = eligible(rows), self.supplied()
        elig[self.key]["known_at_utc"] = "2026-10-30T17:30:04Z"
        supplied[self.key]["known_at_utc"] = "2026-10-30T17:30:03Z"
        ev = declared_events(bars=rows, indicator="SUPPLIED_LINES",
            eligibility=elig, supplied=supplied,
            original_decisions={self.key: {"candidate_id": "frozen-owner-opportunity", "decision_at": decision}},
            decision_cutoff_utc="2026-10-30T20:00:00Z")
        self.assertEqual(ev[1]["state"], "CROSS_OBSERVED")
        self.assertEqual(ev[1]["issued_at_utc"], "2026-10-30T18:00:00+00:00")
        self.assertEqual(ev[1]["inputs_known_at_utc"], "2026-10-30T17:30:04+00:00")
        self.assertEqual(ev[0]["state"], "ORIGINAL_DECISION_UNAVAILABLE")
        self.assertEqual(ev[2]["state"], "SOURCE_NOT_YET_OBSERVED")
        self.assertEqual(ev[-1]["state"], "SOURCE_STUB_EXCLUDED")

    def test_declared_weekend_and_early_close_keep_finite_owner_bound_controls(self):
        for calendar, cutoff in (
            ({**schedule("2026-10-30"), **schedule("2026-11-02")}, "2026-11-03T00:00:00Z"),
            ({**schedule("2026-11-25"), **schedule("2026-11-27", "13:00")}, "2026-11-27T19:00:00Z"),
        ):
            with self.subTest(cutoff=cutoff):
                rows = run(calendar=calendar, cutoff=cutoff)
                supplied = {(r["symbol"], r["bar_end_utc"]): {
                    "fast": -3. if i == 0 else -1., "slow": -2., "oversold": True,
                    "known_at_utc": r["known_at_utc"], "source_sha256": r["source_sha256"],
                } for i, r in enumerate(rows) if r["status"] == "FULL_KNOWN"}
                ev = declared_events(bars=rows, indicator="SUPPLIED_LINES",
                    eligibility=eligible(rows), supplied=supplied, decision_cutoff_utc=cutoff)
                last_full = [x for x in ev if x["state"] != "SOURCE_STUB_EXCLUDED"][-1]
                self.assertIsNotNone(last_full["signal"])
                self.assertNotEqual(last_full["state"], "ELIGIBILITY_UNAVAILABLE")


    def test_declared_opportunity_with_no_source_row_is_retained_unavailable(self):
        declaration = {("B", "2026-10-30T17:30:00+00:00"): {
            "candidate_id": "missing-owner-opportunity", "decision_at": "2026-10-30T20:00:00Z"}}
        for bars in ([], self.rows):
            with self.subTest(observed_rows=len(bars)):
                events = oscillator_events(bars=bars, indicator="CANON_RSI_MACD",
                    eligibility={}, original_decisions=declaration,
                    prior_session_by_day=SYNTHETIC_PREDECESSORS,
                    decision_cutoff_utc="2026-10-30T20:00:00Z")
                self.assertEqual(len(events), len(bars) + 1)
                absent = next(event for event in events if event["symbol"] == "B")
                self.assertEqual(absent["state"], "SOURCE_OPPORTUNITY_UNAVAILABLE")
                self.assertEqual(absent["candidate_id"], "missing-owner-opportunity")
                self.assertIsNone(absent["signal"])
                self.assertIsNone(absent["issued_at_utc"])


if __name__ == "__main__":
    unittest.main()
