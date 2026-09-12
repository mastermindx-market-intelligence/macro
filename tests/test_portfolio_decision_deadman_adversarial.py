from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from scripts import check_portfolio_decision_deadman as deadman

UTC = timezone.utc
NOW = datetime(2026, 9, 12, 0, 55, tzinfo=UTC)


def _job(job_id: str, started: str, finished: str) -> dict:
    return {
        "id": job_id,
        "next_run_time": "2026-09-14T08:00:00+00:00",
        "last_started": started,
        "last_finished": finished,
        "last_status": "ok",
        "last_severity": None,
        "last_reason": None,
        "last_target_status": "queued",
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
                "autonomous_daily",
                "2026-09-11T23:10:00+00:00",
                "2026-09-11T23:16:27+00:00",
            ),
            "china_daily": _job(
                "china_daily",
                "2026-09-11T08:00:00+00:00",
                "2026-09-11T08:21:00+00:00",
            ),
            "hk_daily": _job(
                "hk_daily",
                "2026-09-11T09:00:00+00:00",
                "2026-09-11T09:23:00+00:00",
            ),
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


class PortfolioDecisionDeadmanAdversarialTests(unittest.TestCase):
    def test_ok_run_cannot_carry_severity(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"]["last_severity"] = "FREEZE"
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("unexpected severity" in failure for failure in failures), failures)

    def test_ok_run_cannot_carry_reason(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"]["last_reason"] = "cost_capped"
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("unexpected reason" in failure for failure in failures), failures)

    def test_ok_run_requires_known_target_vocabulary(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"]["last_target_status"] = "unknown_target"
        payload["decisions"]["autonomous"]["target_status"] = "unknown_target"
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("invalid target" in failure for failure in failures), failures)

    def test_executed_decision_requires_acceptance_asof(self):
        payload = healthy_snapshot()
        payload["decisions"]["autonomous"].update(
            asof=None,
            settled_asof="2026-09-11",
            target_status="executed",
            decision_effective=True,
            execution_evidence_status="receipt_verified",
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("asof is missing" in failure for failure in failures), failures)

    def test_executed_settlement_cannot_predate_acceptance(self):
        payload = healthy_snapshot()
        payload["decisions"]["autonomous"].update(
            asof="2026-09-12",
            settled_asof="2026-09-11",
            target_status="executed",
            decision_effective=True,
            execution_evidence_status="receipt_verified",
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("settled before" in failure for failure in failures), failures)

    def test_governed_warning_target_must_match_decision(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"].update(
            last_status="warn",
            last_severity="FREEZE",
            last_reason="rejected_packet_gate",
            last_target_status="rejected_packet_gate",
        )
        payload["decisions"]["autonomous"].update(
            target_status="frozen_risk_gate",
            decision_effective=False,
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("target mismatch" in failure for failure in failures), failures)

    def test_long_running_prior_cycle_cannot_launder_current_completion(self):
        payload = healthy_snapshot()
        payload["jobs"]["autonomous_daily"].update(
            last_started="2026-09-10T23:10:00+00:00",
            last_finished="2026-09-11T23:16:27+00:00",
        )
        failures = deadman.evaluate(payload, now=NOW)
        self.assertTrue(any("stale run" in failure for failure in failures), failures)

    def test_health_status_and_release_commit_are_required(self):
        payload = healthy_snapshot()
        payload["health"].update(status="degraded", commit="")
        failures = deadman.evaluate(payload, now=NOW)
        self.assertIn("health: status is not ok", failures)
        self.assertIn("health: release commit is missing", failures)

    def test_health_allowlist_strips_raw_provider_error(self):
        snapshot = healthy_snapshot()
        health = snapshot["health"] | {"raw_error": "secret-provider-error"}
        scheduler = {"jobs": list(snapshot["jobs"].values())}
        decisions = {
            book: {"decisions": [decision]}
            for book, decision in snapshot["decisions"].items()
        }
        sanitized = deadman.build_snapshot(health, scheduler, decisions, observed_at=NOW)
        self.assertNotIn("secret-provider-error", json.dumps(sanitized, sort_keys=True))

    def test_get_json_rejects_non_200(self):
        class Response:
            status = 503

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b"{}"

        with self.assertRaisesRegex(RuntimeError, "HTTP 503"):
            deadman._get_json(
                "http://127.0.0.1:8001",
                "/health",
                opener=lambda *_args, **_kwargs: Response(),
            )

    def test_get_json_rejects_non_object_payload(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return b"[]"

        with self.assertRaisesRegex(ValueError, "JSON object"):
            deadman._get_json(
                "http://127.0.0.1:8001",
                "/health",
                opener=lambda *_args, **_kwargs: Response(),
            )


if __name__ == "__main__":
    unittest.main()
