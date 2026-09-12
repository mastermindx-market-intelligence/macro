from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from scripts import check_portfolio_decision_deadman as deadman

UTC = timezone.utc
NOW = datetime(2026, 9, 12, 0, 55, tzinfo=UTC)


def _job(job_id: str, started: str, finished: str, *, status: str = "ok",
         reason=None, target: str | None = "queued") -> dict:
    return {
        "id": job_id,
        "next_run_time": "2026-09-14T08:00:00+00:00",
        "last_started": started,
        "last_finished": finished,
        "last_status": status,
        "last_severity": None,
        "last_reason": reason,
        "last_target_status": target,
    }


def healthy_snapshot() -> dict:
    return {
        "schema": deadman.SNAPSHOT_SCHEMA,
        "observed_at": NOW.isoformat(),
        "health": {
            "status": "ok",
            "commit": "e61f2951136bdc03a7ec2f5f12f960af26656a4c",
            "paper_only": True,
            "reasoning_policy_ok": True,
            "scheduled_portfolio_reasoning_available": True,
            "scheduled_portfolio_reasoning_policy_ok": True,
            "scheduler_running": True,
            "scheduled_runtime_ok": True,
            "reasoning_primary": "claude_oauth_fallback",
        },
        "jobs": {
            "autonomous_daily": _job(
                "autonomous_daily", "2026-09-11T23:10:00+00:00",
                "2026-09-11T23:16:27+00:00"),
            "china_daily": _job(
                "china_daily", "2026-09-11T08:00:00+00:00",
                "2026-09-11T08:21:00+00:00"),
            "hk_daily": _job(
                "hk_daily", "2026-09-11T09:00:00+00:00",
                "2026-09-11T09:23:00+00:00"),
        },
        "decisions": {
            book: {
                "asof": "2026-09-11",
                "target_status": "queued",
                "decision_effective": True,
                "execution_evidence_status": "none",
            }
            for book in ("autonomous", "china", "hk")
        },
    }


class PortfolioDecisionDeadmanTests(unittest.TestCase):
    def test_healthy_post_close_cycles_pass(self):
        self.assertEqual(deadman.evaluate(healthy_snapshot(), now=NOW), [])

    def test_exact_missing_submission_recurrence_fails_loudly(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"].update(
            last_status="error", last_severity="FREEZE",
            last_reason="missing_submission",
            last_target_status="rejected_no_submission",
        )
        payload["decisions"]["autonomous"].update(
            target_status="rejected_no_submission", decision_effective=False,
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("autonomous_daily" in f and "missing_submission" in f for f in failures), failures)

    def test_stale_prior_day_run_does_not_pass(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"].update(
            last_started="2026-09-10T23:10:00+00:00",
            last_finished="2026-09-10T23:17:00+00:00",
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("autonomous_daily" in f and "stale" in f for f in failures), failures)

    def test_market_closed_is_the_only_accepted_skip(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"].update(
            last_status="skip", last_reason="market_closed", last_target_status=None,
        )
        payload["decisions"]["autonomous"] = {
            "asof": "2026-09-10",
            "target_status": "queued",
            "decision_effective": True,
            "execution_evidence_status": "none",
        }
        self.assertEqual(deadman.evaluate(payload, now=NOW), [])

        payload["jobs"]["autonomous_daily"].update(last_reason="cost_capped")
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("cost_capped" in f for f in failures), failures)

    def test_explicit_governed_rejection_is_a_visible_decision(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"].update(
            last_status="warn", last_severity="FREEZE",
            last_reason="rejected_packet_gate",
            last_target_status="rejected_packet_gate",
        )
        payload["decisions"]["autonomous"].update(
            target_status="rejected_packet_gate", decision_effective=False,
        )
        self.assertEqual(deadman.evaluate(payload, now=NOW), [])

    def test_reasoning_or_scheduler_degradation_fails_before_book_checks(self):
        payload = healthy_snapshot()
        payload["health"]["reasoning_policy_ok"] = False
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("reasoning_policy_ok" in f for f in failures), failures)

    def test_monday_check_uses_friday_us_and_monday_asia_deadlines(self):
        now = datetime(2026, 9, 14, 10, 45, tzinfo=UTC)
        payload = healthy_snapshot()
        payload["observed_at"] = now.isoformat()
        payload["jobs"]["china_daily"].update(
            last_started="2026-09-14T08:00:00+00:00",
            last_finished="2026-09-14T08:20:00+00:00",
        )
        payload["jobs"]["hk_daily"].update(
            last_started="2026-09-14T09:00:00+00:00",
            last_finished="2026-09-14T09:20:00+00:00",
        )
        payload["jobs"]["autonomous_daily"]["next_run_time"] = "2026-09-14T23:10:00+00:00"
        payload["jobs"]["china_daily"]["next_run_time"] = "2026-09-15T08:00:00+00:00"
        payload["jobs"]["hk_daily"]["next_run_time"] = "2026-09-15T09:00:00+00:00"
        payload["decisions"]["china"]["asof"] = "2026-09-14"
        payload["decisions"]["hk"]["asof"] = "2026-09-14"
        self.assertEqual(deadman.evaluate(payload, now=now), [])

    def test_stale_snapshot_and_past_next_run_fail_closed(self):
        payload = healthy_snapshot()
        payload["observed_at"] = "2026-09-11T22:00:00+00:00"
        payload["jobs"]["autonomous_daily"]["next_run_time"] = "2026-09-11T23:10:00+00:00"
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("snapshot" in f and "stale" in f for f in failures), failures)
        self.assertTrue(any("autonomous_daily" in f and "next_run_time" in f for f in failures), failures)

    def test_executed_decision_requires_verified_receipt(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"]["last_target_status"] = "executed"
        payload["decisions"]["autonomous"].update(
            target_status="executed", decision_effective=True,
            execution_evidence_status="none",
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("autonomous_daily" in f and "receipt" in f for f in failures), failures)

        payload["decisions"]["autonomous"]["execution_evidence_status"] = "receipt_verified"
        self.assertEqual(deadman.evaluate(payload, now=NOW), [])

    def test_snapshot_builder_strips_holdings_errors_and_provider_secrets(self):
        health = healthy_snapshot()["health"] | {
            "raw_error": "secret-provider-error",
            "credential": "do-not-copy",
        }
        scheduler = {"jobs": [
            healthy_snapshot()["jobs"]["autonomous_daily"] | {
                "raw_error": "provider-token-leak"
            },
            healthy_snapshot()["jobs"]["china_daily"],
            healthy_snapshot()["jobs"]["hk_daily"],
        ]}
        decisions = {
            book: {"decisions": [healthy_snapshot()["decisions"][book] | {
                "holdings": [{"ticker": "SECRET", "value": 1000000}],
                "brain_text": "private thesis",
                "raw_error": "provider-token-leak",
            }]}
            for book in ("autonomous", "china", "hk")
        }
        snapshot = deadman.build_snapshot(
            health, scheduler, decisions, observed_at=NOW
        )
        serialized = json.dumps(snapshot, sort_keys=True)
        for forbidden in ("holdings", "SECRET", "private thesis", "provider-token-leak", "credential"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(snapshot["decisions"]["autonomous"]["target_status"], "queued")


if __name__ == "__main__":
    unittest.main()
