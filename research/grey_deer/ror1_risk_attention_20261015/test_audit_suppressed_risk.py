"""Regression checks for ROR-1 point-in-time warning-suppression ledger audit.

Synthetic fixtures only.  They do not validate a financial forecast.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_suppressed_risk import analyze  # expected RED: implementation not yet present


def row(day, *, state="caution", ungated="risk-off", clamp=True,
        graded=None, issue=True, alerts=False):
    return {
        "asof": day,
        "state": state,
        "state_ungated": ungated,
        "gate_clamped": clamp,
        "alert": alerts,
        "forecast_issue": (
            {"issued_at": day + "T23:00:00+00:00", "epoch": "prospective"}
            if issue else None
        ),
        "graded": graded,
    }


class SuppressionAuditTests(unittest.TestCase):
    def test_reports_suppression_severity_without_claiming_outcome(self):
        records = [
            row("2026-09-23", state="calm", ungated="calm", clamp=False),
            row("2026-09-24", ungated="elevated"),
            row("2026-09-25", ungated="risk-off"),
        ]
        s = analyze(records)
        self.assertEqual(s["n_records"], 3)
        self.assertEqual(s["n_issued"], 3)
        self.assertEqual(s["n_suppressed"], 2)
        self.assertEqual(s["suppressed_by_ungated_state"], {"elevated": 1, "risk-off": 1})
        self.assertEqual(s["n_issued_suppressed"], 2)
        self.assertEqual(s["n_suppressed_with_known_outcome"], 0)
        self.assertIsNone(s["suppressed_precision"])
        self.assertEqual(s["first_suppressed_source_session"], "2026-09-24")
        self.assertEqual(s["last_suppressed_source_session"], "2026-09-25")

    def test_delivered_severe_not_counted_suppressed(self):
        records = [
            row("2026-09-24", state="elevated", ungated="elevated", clamp=False, alerts=True),
            row("2026-09-25", state="caution", ungated="risk-off", clamp=True),
            row("2026-09-26", state="watch", ungated="watch", clamp=False),
        ]
        s = analyze(records)
        self.assertEqual(s["n_suppressed"], 1)
        self.assertEqual(s["n_public_alert"], 1)
        self.assertEqual(len(s["suppression_runs"]), 1)
        self.assertEqual(s["suppression_runs"][0]["records"], 1)

    def test_suppression_run_counts_recorded_observations_not_sessions(self):
        records = [
            row("2026-09-24", ungated="elevated"),
            row("2026-09-26", ungated="risk-off"),
            row("2026-10-01", ungated="risk-off"),
        ]
        s = analyze(records)
        self.assertEqual(len(s["suppression_runs"]), 1)
        self.assertEqual(s["suppression_runs"][0]["records"], 3)
        self.assertEqual(s["suppression_runs"][0]["continuity"], "recorded_rows_only")
        self.assertEqual(s["suppression_runs"][0]["first"], "2026-09-24")
        self.assertEqual(s["suppression_runs"][0]["last"], "2026-10-01")

    def test_future_outcomes_are_not_graded_until_present(self):
        records = [
            row("2026-09-24", graded=None),
            row("2026-09-25", graded={"hit": {"h21": {"dd5": True}}}),
            row("2026-09-26", graded={"hit": {"h21": {"dd5": False}}}),
        ]
        s = analyze(records)
        self.assertEqual(s["n_issued"], 3)
        self.assertEqual(s["n_graded"], 2)
        self.assertEqual(s["n_suppressed_with_known_outcome"], 2)
        self.assertEqual(s["n_suppressed_ungraded"], 1)
        self.assertIsNone(s["suppressed_precision"])  # not an issued alert or suitable forecast test

    def test_legacy_no_ungated_is_not_inferred(self):
        records = [{"asof": "2026-06-23", "state": "caution", "alert": False, "graded": {"outcome":"tn"}}]
        s = analyze(records)
        self.assertEqual(s["n_suppressed"], 0)
        self.assertEqual(s["n_unknown_ungated"], 1)
        self.assertEqual(s["n_graded"], 1)

    def test_rejects_nonmonotonic_or_duplicate_sessions(self):
        with self.assertRaises(ValueError):
            analyze([row("2026-09-24"), row("2026-09-24")])
        with self.assertRaises(ValueError):
            analyze([row("2026-09-25"), row("2026-09-24")])

    def test_rejects_inconsistent_claim_of_gate_clamped(self):
        with self.assertRaises(ValueError):
            analyze([row("2026-09-24", state="risk-off", ungated="risk-off", clamp=True)])

    def test_no_arbitrary_signal_permission_claim(self):
        s = analyze([row("2026-09-24")])
        self.assertEqual(s["scope"], "source_ledger_behavior_not_forecast_skill")
        self.assertNotIn("probability", s)
        self.assertNotIn("capital_action", s)


if __name__ == "__main__":
    unittest.main()
