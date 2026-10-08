"""Research-only conformance; reuse the existing Phase-1 synthetic fixture.

No acquired market data, outcome fitting, source admission or live registration.
Run together with tests/test_entry_radar_rs_pullback_phase1.py using pytest.
"""
from __future__ import annotations

import copy
import json
import unittest
from datetime import timedelta

from test_entry_radar_rs_pullback_phase1 import candidate, clock, fixture, iso
from engine.entry_radar.replay.leader_pivot_descriptor import describe_candidate
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError, digest


def witness():
    bundle = fixture(candidates=[candidate("pivot", "2026-10-06T16:00:00Z")])
    opening = clock("2026-10-06T13:30:00Z")
    lows = [104.0, 103.0, 102.0, 100.0, 99.0]
    for row in bundle["minutes"]:
        i = int((clock(row["start"]) - opening).total_seconds() / 60)
        if row["stream"] == "stock" and 0 <= i < 150:
            low = lows[i // 30]
            row.update(low=low, high=low + 2.0, open=low + 1.0, close=low + 1.0)
            if i >= 120:
                row.update(high=102.0, open=100.5, close=101.5)
    return bundle


def change_current(bundle, **values):
    for row in bundle["minutes"]:
        if row["stream"] == "stock" and "2026-10-06T15:30:00Z" <= row["start"] < "2026-10-06T16:00:00Z":
            row.update(values)


def stock_minute(bundle, offset):
    return next(r for r in bundle["minutes"] if r["stream"] == "stock" and r["revision_id"] == f"synthetic-stock-{offset}-v1")


class LeaderPivotDescriptorTests(unittest.TestCase):
    def result(self, bundle=None, state="PIVOT_FORMED"):
        result = describe_candidate(witness() if bundle is None else bundle, "pivot")
        self.assertEqual(result["state"], state)
        self.assertFalse(result["source_admitted"])
        self.assertFalse(result["detector_registered"])
        self.assertFalse(result["outcomes_computed"])
        self.assertFalse(result["actual_issuance_proven"])
        self.assertIsNone(result["issued_at"])
        self.assertTrue(all(v is False for v in result["authority"].values()))
        sealed = {k: v for k, v in result.items() if k != "descriptor_sha256"}
        self.assertEqual(result["descriptor_sha256"], digest(sealed))
        return result

    def test_completed_rejection_is_frozen(self):
        r = self.result()
        self.assertTrue(r["condition_met"])
        self.assertEqual(r["pivot"]["low"], 99.0)
        self.assertEqual(r["pivot"]["high"], 102.0)
        self.assertEqual(r["reference_low"], 100.0)
        self.assertEqual(r["target_interval"]["end"], "2026-10-06T16:00:00Z")
        self.assertEqual(len(r["reference_bars"]), 4)
        self.assertEqual(r["evidence_status"], "SYNTHETIC_CONFORMANCE_ONLY")

    def test_failed_reclaim_is_no_pivot_not_unavailable(self):
        b = witness(); change_current(b, close=99.5)
        r = self.result(b, "NO_PIVOT")
        self.assertIs(r["condition_met"], False)
        self.assertIsNone(r["pivot"])

    def test_equal_low_does_not_qualify(self):
        b = witness(); change_current(b, low=100.0)
        self.result(b, "NO_PIVOT")

    def test_close_equal_reference_does_not_qualify(self):
        b = witness(); change_current(b, close=100.0)
        self.result(b, "NO_PIVOT")

    def test_exact_half_range_passes_and_lower_does_not(self):
        b = witness(); change_current(b, close=100.5)
        self.result(b)
        change_current(b, close=100.49)
        self.result(b, "NO_PIVOT")

    def test_flat_bar_has_no_pivot(self):
        b = witness(); change_current(b, low=100.5, high=100.5, open=100.5, close=100.5)
        self.result(b, "NO_PIVOT")

    def test_ineligible_owner_is_not_overridden(self):
        b = witness(); b["contexts"][0]["payload"]["is_leader"] = False
        r = self.result(b, "NOT_ELIGIBLE")
        self.assertIsNone(r["condition_met"])

    def test_missing_prior_minute_cannot_skip_reference_bar(self):
        b = witness(); b["minutes"].remove(stock_minute(b, 0))
        r = self.result(b, "UNAVAILABLE")
        self.assertTrue(any("reference_0:MISSING_OR_NOT_YET_KNOWN_MINUTE" == x for x in r["refusals"]))
        self.assertIsNone(r["condition_met"])

    def test_missing_target_minute_is_not_nonfire(self):
        b = witness(); b["minutes"].remove(stock_minute(b, 130))
        self.result(b, "UNAVAILABLE")

    def test_delayed_prior_receipt_refuses_then_becomes_visible(self):
        b = witness(); stock_minute(b, 0)["known_at"] = "2026-10-06T16:00:02Z"
        self.result(b, "UNAVAILABLE")
        b["candidates"][0]["decision_at"] = "2026-10-06T16:00:02Z"
        r = self.result(b)
        self.assertEqual(r["price_structure_known_at"], "2026-10-06T16:00:02Z")

    def test_future_prices_leave_complete_descriptor_exact(self):
        b = witness(); before = self.result(b)
        for row in b["minutes"]:
            if row["known_at"] > "2026-10-06T16:00:00Z":
                row.update(open=800.0, high=900.0, low=700.0, close=850.0)
        self.assertEqual(before, self.result(b))

    def test_future_correction_changes_only_later_result(self):
        b = witness(); before = self.result(b)
        correction = copy.deepcopy(stock_minute(b, 0))
        correction.update(known_at="2026-10-06T16:01:00Z", revision_id="late-correction", low=90.0)
        b["minutes"].append(correction)
        self.assertEqual(before, self.result(b))
        b["candidates"][0]["decision_at"] = "2026-10-06T16:02:00Z"
        r = self.result(b, "NO_PIVOT")
        self.assertEqual(r["reference_low"], 90.0)
        self.assertEqual(before["pivot"]["low"], 99.0)

    def test_prior_identity_mismatch_refuses(self):
        b = witness(); stock_minute(b, 0)["security_id"] = "SYNTHETIC:other"
        self.result(b, "UNAVAILABLE")

    def test_prior_basis_mismatch_refuses(self):
        b = witness(); stock_minute(b, 0)["basis_id"] = "other"
        self.result(b, "UNAVAILABLE")

    def test_terminal_unproven_basis_remains_refused(self):
        b = witness(); stock_minute(b, 0)["source_ref"] = "terminal-minute-capture:synthetic"
        r = self.result(b, "UNAVAILABLE")
        self.assertIn("reference_0:TERMINAL_BASIS_UNPROVEN", r["refusals"])

    def test_stale_daily_input_remains_unavailable(self):
        b = witness(); b["contexts"][0]["asof_session"] = "2026-10-02"
        self.result(b, "UNAVAILABLE")

    def test_insufficient_same_session_history_refuses(self):
        b = witness(); b["candidates"][0]["decision_at"] = "2026-10-06T14:30:00Z"
        r = self.result(b, "UNAVAILABLE")
        self.assertIn("INSUFFICIENT_SAME_SESSION_30M_HISTORY", r["refusals"])

    def test_unfinished_current_bar_is_not_read(self):
        b = witness(); b["candidates"][0]["decision_at"] = "2026-10-06T15:59:59Z"
        self.result(b, "UNAVAILABLE")

    def test_early_close_keeps_full_target_and_no_outcome(self):
        b = witness(); b["calendar"]["sessions"]["2026-10-06"]["close"] = "2026-10-06T17:00:00Z"
        r = self.result(b)
        self.assertEqual(r["target_interval"]["end"], "2026-10-06T16:00:00Z")
        self.assertFalse(r["outcomes_computed"])

    def test_after_session_close_refuses(self):
        b = witness(); b["candidates"][0]["decision_at"] = "2026-10-06T20:01:00Z"
        self.result(b, "UNAVAILABLE")

    def test_market_label_cannot_self_admit(self):
        b = witness(); b["input_kind"] = "OBSERVED_MARKET"; b["source_admitted"] = True
        r = self.result(b)
        self.assertEqual(r["evidence_status"], "DESCRIPTOR_BUILT_NOT_ADMITTED")

    def test_unknown_and_duplicate_candidate_rejected(self):
        b = witness()
        with self.assertRaises(InputContractError): describe_candidate(b, "absent")
        b["candidates"].append(copy.deepcopy(b["candidates"][0]))
        with self.assertRaises(InputContractError): describe_candidate(b, "pivot")

    def test_unrelated_future_candidate_is_not_evaluated(self):
        b = witness(); before = self.result(b)
        b["candidates"].append(candidate("future", "not-an-instant"))
        self.assertEqual(before, self.result(b))

    def test_does_not_mutate_input(self):
        b = witness(); before = copy.deepcopy(b)
        self.result(b)
        self.assertEqual(b, before)

    def test_naive_decision_is_malformed_not_observed(self):
        b = witness(); b["candidates"][0]["decision_at"] = "2026-10-06T16:00:00"
        with self.assertRaises(InputContractError): describe_candidate(b, "pivot")

    def test_future_identity_receipt_refuses(self):
        b = witness(); b["streams"]["stock"]["identity"]["known_at"] = "2026-10-06T16:00:01Z"
        self.result(b, "UNAVAILABLE")

    def test_unknown_catalyst_does_not_become_no_news(self):
        b = witness(); b["contexts"] = [r for r in b["contexts"] if r["kind"] != "catalyst"]
        r = self.result(b)
        self.assertEqual(r["catalyst_state"], "UNKNOWN")

    def test_prior_nonfinite_price_rejected(self):
        b = witness(); stock_minute(b, 0)["low"] = float("nan")
        with self.assertRaises((InputContractError, ValueError)): describe_candidate(b, "pivot")

    def test_closed_session_stub_not_mislabelled_as_30m(self):
        b = witness(); b["calendar"]["sessions"]["2026-10-06"]["close"] = "2026-10-06T17:15:00Z"
        b["candidates"][0]["decision_at"] = "2026-10-06T17:15:00Z"
        r = self.result(b, "NO_PIVOT")
        self.assertEqual(r["target_interval"]["end"], "2026-10-06T17:00:00Z")
        self.assertEqual(clock(r["target_interval"]["end"]) - clock(r["target_interval"]["start"]), timedelta(minutes=30))


if __name__ == "__main__":
    unittest.main()
