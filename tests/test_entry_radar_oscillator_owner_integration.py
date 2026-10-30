"""Synthetic native-Macro-owner seam: not a market-data admission test."""
from __future__ import annotations

import copy
import unittest
from datetime import date

from engine.entry_radar.replay.oscillator_mtf_research import (
    aggregate_owner_windows, oscillator_events,
)
from engine.entry_radar.replay.rs_pullback_launch_data import (
    _aggregate, _metadata_errors, build_input_panel,
)
from tests.test_entry_radar_rs_pullback_phase1 import candidate, clock, fixture

SESSION = "2026-10-06"
CUTOFF = "2026-10-06T19:45:00Z"


def bundle():
    return fixture(candidates=[candidate("oscillator", CUTOFF)])


def reader(source):
    def native(symbol, start, end, cutoff):
        if symbol != "SYNTHETIC:stock":
            raise ValueError("source identity not in owner bundle")
        return _aggregate(source["minutes"], "stock", source["streams"]["stock"],
                          clock(start), clock(end), clock(cutoff))
    return native


def windows(source, minutes=120):
    day = date.fromisoformat(SESSION)
    cal = source["calendar"]["sessions"][SESSION]
    return aggregate_owner_windows(
        symbol="SYNTHETIC:stock", calendar={day: (cal["open"], cal["close"])},
        decision_utc=CUTOFF, minutes=minutes, read_aggregate=reader(source),
    )


class NativeOwnerSeam(unittest.TestCase):
    def test_phase1_eligibility_and_actual_owner_minute_aggregate_connect(self):
        source = bundle()
        panel = build_input_panel(source)
        self.assertEqual(panel["frames"][0]["availability"], "available")
        self.assertTrue(panel["frames"][0]["eligible"])
        self.assertEqual(_metadata_errors(source["streams"]["stock"], clock(CUTOFF), SESSION), [])
        for grain, full in ((120, 3), (180, 2)):
            with self.subTest(grain=grain):
                bars = windows(source, grain)
                self.assertEqual([x["status"] for x in bars[:-1]], ["FULL_KNOWN"] * full)
                self.assertEqual(bars[-1]["status"], "STUB_EXCLUDED")
                self.assertEqual(bars[-1]["stub_minutes"], 30)
                self.assertTrue(all(x["source_sha256"] for x in bars[:-1]))
                self.assertTrue(all(not x["source_admitted"] for x in bars))

    def test_missing_owner_minute_rejects_first_120m_bar(self):
        source = bundle()
        source["minutes"] = [x for x in source["minutes"] if not (
            x["stream"] == "stock" and x["revision_id"] == "synthetic-stock-0-v1")]
        bars = windows(source)
        self.assertEqual(bars[0]["status"], "UNAVAILABLE")
        self.assertIn("MISSING_OR_NOT_YET_KNOWN_MINUTE", bars[0]["refusals"])
        self.assertEqual(bars[1]["status"], "FULL_KNOWN")

    def test_future_correction_does_not_rewrite_past_known_bars(self):
        source = bundle()
        before = windows(source)
        correction = copy.deepcopy(next(x for x in source["minutes"]
                                        if x["stream"] == "stock"))
        correction.update(known_at="2026-10-06T20:30:00Z", revision_id="late-correction",
                          low=correction["low"] - 10.)
        source["minutes"].append(correction)
        after = windows(source)
        self.assertEqual(before, after)

    def test_source_basis_mismatch_preserves_owner_refusal(self):
        source = bundle()
        next(x for x in source["minutes"] if x["stream"] == "stock")["basis_id"] = "other-basis"
        bars = windows(source)
        self.assertEqual(bars[0]["status"], "UNAVAILABLE")
        self.assertIn("MINUTE_BASIS_MISMATCH", bars[0]["refusals"])

    def test_daily_owner_context_to_descriptive_indicator_preserves_no_authority(self):
        source = bundle()
        panel = build_input_panel(source)
        frame = panel["frames"][0]
        daily = frame["daily_context"]
        bars = windows(source)
        previous = source["calendar"]["sessions"][SESSION]["previous_session"]
        eligibility = {(x["symbol"], x["bar_end_utc"]): {
            "is_leader": frame["eligible"], "known_at_utc": daily["known_at"],
            "asof_session": previous, "expected_prior_session": previous,
            "receipt_sha256": daily["receipt_sha256"],
        } for x in bars if x["status"] == "FULL_KNOWN"}
        events = oscillator_events(bars=bars, indicator="CANON_RSI_MACD",
                                   eligibility=eligibility, decision_cutoff_utc=CUTOFF)
        self.assertEqual(len(events), len(bars))
        self.assertEqual(events[-1]["state"], "SOURCE_STUB_EXCLUDED")
        self.assertTrue(all(x["source_admitted"] is False for x in events))
        self.assertTrue(all(x["signal"] is None for x in events))  # insufficient 120m warm-up


if __name__ == "__main__":
    unittest.main()
