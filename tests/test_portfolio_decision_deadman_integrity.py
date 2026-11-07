from __future__ import annotations

import unittest
from pathlib import Path

from scripts import check_portfolio_decision_deadman as deadman
from tests.test_portfolio_decision_deadman import NOW, healthy_snapshot


class PortfolioDecisionDeadmanIntegrityBoundaryTests(unittest.TestCase):
    def test_future_run_timestamps_cannot_prove_completion(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"].update(
            last_started="2026-09-12T01:10:00+00:00",
            last_finished="2026-09-12T01:16:00+00:00",
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(
            any(
                "autonomous_daily" in failure and "future" in failure
                for failure in failures
            ),
            failures,
        )

    def test_decision_dates_must_be_exact_iso_dates(self):
        payload = healthy_snapshot()
        payload["decisions"]["autonomous"]["asof"] = "2026-09-11garbage"
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(
            any(
                "autonomous_daily" in failure and "date" in failure
                for failure in failures
            ),
            failures,
        )

    def test_release_commit_must_be_a_full_git_sha(self):
        payload = healthy_snapshot()
        payload["health"]["commit"] = "ok"
        failures = deadman.evaluate(payload, now=NOW)
        self.assertIn("health: release commit is invalid", failures)

    def test_next_run_must_remain_on_a_weekday(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"]["next_run_time"] = (
            "2026-09-12T23:10:00+00:00"
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(
            any(
                "autonomous_daily" in failure and "weekend" in failure
                for failure in failures
            ),
            failures,
        )

    def test_decision_response_identity_is_bound_to_requested_book(self):
        snapshot = healthy_snapshot()
        decisions = {
            book: {
                "portfolio": ("autonomous" if book == "china" else book),
                "scope": "mastermind_portfolio",
                "decisions": [snapshot["decisions"][book]],
            }
            for book in ("autonomous", "china", "hk")
        }
        collected = deadman.build_snapshot(
            snapshot["health"],
            {"jobs": list(snapshot["jobs"].values())},
            decisions,
            observed_at=NOW,
        )
        failures = deadman.evaluate(collected, now=NOW)
        self.assertIn("collection: decision_identity:china", failures)

    def test_decision_response_scope_is_bound(self):
        snapshot = healthy_snapshot()
        decisions = {
            book: {
                "portfolio": book,
                "scope": (
                    "other_scope" if book == "hk" else "mastermind_portfolio"
                ),
                "decisions": [snapshot["decisions"][book]],
            }
            for book in ("autonomous", "china", "hk")
        }
        collected = deadman.build_snapshot(
            snapshot["health"],
            {"jobs": list(snapshot["jobs"].values())},
            decisions,
            observed_at=NOW,
        )
        failures = deadman.evaluate(collected, now=NOW)
        self.assertIn("collection: decision_scope:hk", failures)

    def test_duplicate_scheduler_rows_fail_closed(self):
        snapshot = healthy_snapshot()
        failed = dict(snapshot["jobs"]["autonomous_daily"])
        failed.update(
            last_status="error",
            last_reason="missing_submission",
            last_target_status="rejected_no_submission",
        )
        scheduler = {
            "jobs": [
                failed,
                snapshot["jobs"]["autonomous_daily"],
                snapshot["jobs"]["china_daily"],
                snapshot["jobs"]["hk_daily"],
            ]
        }
        decisions = {
            book: {
                "portfolio": book,
                "scope": "mastermind_portfolio",
                "decisions": [snapshot["decisions"][book]],
            }
            for book in ("autonomous", "china", "hk")
        }
        collected = deadman.build_snapshot(
            snapshot["health"], scheduler, decisions, observed_at=NOW
        )
        failures = deadman.evaluate(collected, now=NOW)
        self.assertIn(
            "collection: scheduler_duplicate:autonomous_daily",
            failures,
        )


class PortfolioDecisionDeadmanWorkflowTrustTests(unittest.TestCase):
    def test_secret_bearing_check_requires_main_ref_trust_gate(self):
        workflow = Path(
            ".github/workflows/portfolio-decision-deadman.yml"
        ).read_text(encoding="utf-8")
        trust_job = workflow.find("  trust-gate:")
        check_job = workflow.find("  check:")
        secret_use = workflow.find("SSH_KEY: ${{ secrets.VPS_DEPLOY_KEY }}")

        self.assertGreaterEqual(trust_job, 0)
        self.assertGreaterEqual(check_job, 0)
        self.assertGreater(secret_use, check_job)
        self.assertLess(trust_job, check_job)
        self.assertIn("TRUSTED_REF: ${{ github.ref }}", workflow)
        self.assertIn('test "$TRUSTED_REF" = refs/heads/main', workflow)
        self.assertIn("needs: trust-gate", workflow[check_job:secret_use])


if __name__ == "__main__":
    unittest.main()
