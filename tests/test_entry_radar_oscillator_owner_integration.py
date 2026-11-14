"""Synthetic native-Macro-owner seam: not a market-data admission test."""
from __future__ import annotations

import copy
import unittest
from datetime import date

from engine.entry_radar.replay.oscillator_mtf_research import (
    aggregate_owner_windows, oscillator_events,
)
from engine.entry_radar.replay.rs_pullback_launch_data import (
    _aggregate, _metadata_errors, _latest_context, build_input_panel,
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
        # Preserve the *existing owner's* first-seen / identity / basis
        # refusals before invoking its existing minute aggregator. This
        # synthetic reader adapter does not grant any real market admission.
        metadata = source["streams"]["stock"]
        refusals = _metadata_errors(metadata, clock(cutoff), SESSION)
        if refusals:
            return {"availability": "unavailable", "refusals": refusals}
        return _aggregate(source["minutes"], "stock", metadata,
                          clock(start), clock(end), clock(cutoff))
    return native


def windows(source, minutes=120):
    day = date.fromisoformat(SESSION)
    cal = source["calendar"]["sessions"][SESSION]
    return aggregate_owner_windows(
        symbol="SYNTHETIC:stock", calendar={day: (cal["open"], cal["close"])},
        decision_utc=source["candidates"][0]["decision_at"], minutes=minutes,
        read_aggregate=reader(source),
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

    def test_inferred_first_seen_rejected_through_same_owner_preflight(self):
        source = bundle()
        source["streams"]["stock"]["availability_basis"] = "inferred"
        self.assertEqual(build_input_panel(source)["frames"][0]["availability"], "unavailable")
        bars = windows(source)
        self.assertEqual(bars[0]["status"], "UNAVAILABLE")
        self.assertIn("FIRST_SEEN_NOT_OBSERVED", bars[0]["refusals"])

    def test_future_metadata_basis_rejected_through_owner_preflight(self):
        source = bundle()
        source["streams"]["stock"]["basis"]["known_at"] = "2026-10-07T00:00:00Z"
        self.assertEqual(build_input_panel(source)["frames"][0]["availability"], "unavailable")
        bars = windows(source)
        self.assertEqual(bars[0]["status"], "UNAVAILABLE")
        self.assertIn("BASIS_NOT_BOUND_AT_DECISION", bars[0]["refusals"])

    def test_wrong_identity_rejected_through_owner_preflight(self):
        source = bundle()
        source["streams"]["stock"]["identity"]["security_id"] = "DIFFERENT"
        self.assertEqual(build_input_panel(source)["frames"][0]["availability"], "unavailable")
        bars = windows(source)
        self.assertEqual(bars[0]["status"], "UNAVAILABLE")
        self.assertIn("IDENTITY_NOT_BOUND_AT_DECISION", bars[0]["refusals"])

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
            "asof_session": daily["asof_session"], "expected_prior_session": previous,
            "receipt_sha256": daily["receipt_sha256"],
        } for x in bars if x["status"] == "FULL_KNOWN"}
        target = bars[-2]
        events = oscillator_events(bars=bars, indicator="CANON_RSI_MACD",
            eligibility=eligibility, decision_cutoff_utc=CUTOFF,
            prior_session_by_day={date.fromisoformat(SESSION): date.fromisoformat(previous)},
            original_decisions={(target["symbol"], target["bar_end_utc"]): source["candidates"][0]})
        self.assertEqual(len(events), len(bars))
        self.assertEqual(events[-1]["state"], "SOURCE_STUB_EXCLUDED")
        self.assertTrue(all(x["source_admitted"] is False for x in events))
        self.assertTrue(all(x["signal"] is None for x in events))  # insufficient 120m warm-up
        self.assertEqual(events[-2]["state"], "WARMUP_OR_OSCILLATOR_UNAVAILABLE")
        self.assertEqual(events[-2]["candidate_id"], source["candidates"][0]["candidate_id"])


    def test_actual_daily_receipt_is_not_rewritten_to_calendar_predecessor(self):
        source = bundle()
        for record in source["contexts"]:
            if record["kind"] == "daily":
                record["asof_session"] = "2026-10-02"
        panel = build_input_panel(source)
        self.assertIn("daily:STALE_ROW", panel["frames"][0]["refusals"])
        daily, error = _latest_context(source["contexts"], "daily", "SYNTHETIC:stock",
                                       clock(CUTOFF), SESSION)
        self.assertIsNone(error)
        self.assertEqual(daily["asof_session"], "2026-10-02")
        bars = windows(source)
        previous = source["calendar"]["sessions"][SESSION]["previous_session"]
        target = bars[-2]
        key = (target["symbol"], target["bar_end_utc"])
        eligibility = {key: {
            "is_leader": daily["payload"]["is_leader"], "known_at_utc": daily["known_at"],
            "asof_session": daily["asof_session"], "expected_prior_session": previous,
            "receipt_sha256": daily["receipt_sha256"],
        }}
        supplied = {(bar["symbol"], bar["bar_end_utc"]): {
            "fast": -1. if bar is target else -3., "slow": -2., "oversold": True,
            "known_at_utc": bar["known_at_utc"], "source_sha256": bar["source_sha256"],
        } for bar in bars if bar["status"] == "FULL_KNOWN"}
        events = oscillator_events(bars=bars, indicator="SUPPLIED_LINES",
            eligibility=eligibility, supplied=supplied, decision_cutoff_utc=CUTOFF,
            prior_session_by_day={date.fromisoformat(SESSION): date.fromisoformat(previous)},
            original_decisions={key: source["candidates"][0]})
        self.assertEqual(events[-2]["state"], "ELIGIBILITY_UNAVAILABLE")
        self.assertIsNone(events[-2]["signal"])
        self.assertEqual(eligibility[key]["asof_session"], "2026-10-02")

    def test_owner_candidate_clock_and_actual_daily_context_allow_finite_descriptive_state(self):
        source = bundle()
        frame = build_input_panel(source)["frames"][0]
        daily, bars = frame["daily_context"], windows(source)
        previous = source["calendar"]["sessions"][SESSION]["previous_session"]
        target = bars[-2]
        key = (target["symbol"], target["bar_end_utc"])
        supplied = {(bar["symbol"], bar["bar_end_utc"]): {
            "fast": -1. if bar is target else -3., "slow": -2., "oversold": True,
            "known_at_utc": bar["known_at_utc"], "source_sha256": bar["source_sha256"],
        } for bar in bars if bar["status"] == "FULL_KNOWN"}
        events = oscillator_events(bars=bars, indicator="SUPPLIED_LINES",
            eligibility={key: {"is_leader": frame["eligible"], "known_at_utc": daily["known_at"],
                "asof_session": daily["asof_session"], "expected_prior_session": previous,
                "receipt_sha256": daily["receipt_sha256"]}},
            supplied=supplied, decision_cutoff_utc=CUTOFF,
            prior_session_by_day={date.fromisoformat(SESSION): date.fromisoformat(previous)},
            original_decisions={key: source["candidates"][0]})
        self.assertEqual(events[-2]["state"], "CROSS_OBSERVED")
        self.assertEqual(events[-2]["candidate_id"], "oscillator")
        self.assertEqual(events[-2]["decision_at_utc"], "2026-10-06T19:45:00+00:00")
        self.assertEqual(events[-2]["issued_at_utc"], "2026-10-06T19:45:00+00:00")
        self.assertFalse(events[-2]["source_admitted"])

    def test_future_malformed_minute_payload_cannot_change_original_projection(self):
        source = bundle()
        before = windows(source)
        source["minutes"].append({"stream": "stock", "known_at": "2026-10-07T00:00:00Z",
                                  "start": "malformed future payload", "open": False})
        self.assertEqual(windows(source), before)

    def test_same_clock_conflicting_visible_minute_versions_remain_unavailable(self):
        source = bundle()
        conflict = copy.deepcopy(next(x for x in source["minutes"] if x["stream"] == "stock"))
        conflict["revision_id"] = "conflicting-same-clock"
        conflict["low"] -= 10.
        source["minutes"].append(conflict)
        bars = windows(source)
        self.assertEqual(bars[0]["status"], "UNAVAILABLE")
        self.assertIn("CONFLICTING_MINUTE_REVISION", bars[0]["refusals"])


if __name__ == "__main__":
    unittest.main()
