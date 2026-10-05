from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from scripts import portfolio_decision_deadman as deadman

UTC = dt.timezone.utc
FIX_SHA = "e61f2951136bdc03a7ec2f5f12f960af26656a4c"


def ts(day: str, clock: str) -> str:
    return f"{day}T{clock}+00:00"


def healthy_snapshot() -> dict:
    return {
        "schema": "mastermind.portfolio_decision_snapshot.v1",
        "observed_at": ts("2026-09-12", "00:30:00"),
        "release": {
            "fix_commit": FIX_SHA,
            "deployed_commit": "f" * 40,
            "release_contains_fix": True,
            "health_http": 200,
            "health_status": "ok",
            "health_commit": "f" * 40,
            "scheduler_http": 200,
        },
        "jobs": {
            "autonomous_daily": {
                "id": "autonomous_daily",
                "last_started": ts("2026-09-11", "23:10:00"),
                "last_finished": ts("2026-09-11", "23:16:27"),
                "last_status": "ok",
                "last_reason": None,
                "last_target_status": "queued",
                "next_run_time": ts("2026-09-14", "23:10:00"),
            },
            "china_daily": {
                "id": "china_daily",
                "last_started": ts("2026-09-11", "08:00:00"),
                "last_finished": ts("2026-09-11", "08:06:00"),
                "last_status": "ok",
                "last_reason": None,
                "last_target_status": "queued",
                "next_run_time": ts("2026-09-14", "08:00:00"),
            },
            "hk_daily": {
                "id": "hk_daily",
                "last_started": ts("2026-09-11", "09:00:00"),
                "last_finished": ts("2026-09-11", "09:06:00"),
                "last_status": "ok",
                "last_reason": None,
                "last_target_status": "queued",
                "next_run_time": ts("2026-09-14", "09:00:00"),
            },
        },
        "decisions": {
            "autonomous": {
                "http": 200,
                "error_class": None,
                "latest": {
                    "asof": "2026-09-11",
                    "target_status": "queued",
                    "decision_effective": True,
                    "execution_evidence_status": "none",
                },
            },
            "china": {
                "http": 200,
                "error_class": None,
                "latest": {
                    "asof": "2026-09-11",
                    "target_status": "queued",
                    "decision_effective": True,
                    "execution_evidence_status": "none",
                },
            },
            "hk": {
                "http": 200,
                "error_class": None,
                "latest": {
                    "asof": "2026-09-11",
                    "target_status": "queued",
                    "decision_effective": True,
                    "execution_evidence_status": "none",
                },
            },
        },
    }


def test_latest_due_date_uses_previous_weekday_for_us_after_midnight() -> None:
    observed = dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)
    assert deadman.latest_due_date(observed, hour=23, minute=10, grace_minutes=45) == dt.date(2026, 9, 11)


def test_healthy_queued_us_decision_is_accepted_without_claiming_execution() -> None:
    receipt = deadman.evaluate_snapshot(
        healthy_snapshot(), scope="us", observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)
    )
    assert receipt["state"] == "HEALTHY"
    assert receipt["books"]["autonomous"]["state"] == "DECISION_ACCEPTED"
    assert receipt["books"]["autonomous"]["decision"]["execution_evidence_status"] == "none"
    assert receipt["exit_code"] == 0


def test_missing_submission_pages_operator() -> None:
    snapshot = healthy_snapshot()
    snapshot["jobs"]["autonomous_daily"].update(
        last_status="error",
        last_reason="missing_submission",
        last_target_status="rejected_no_submission",
    )
    snapshot["decisions"]["autonomous"]["latest"].update(
        target_status="rejected_no_submission", decision_effective=False
    )
    receipt = deadman.evaluate_snapshot(
        snapshot, scope="us", observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)
    )
    assert receipt["state"] == "ALERT"
    assert receipt["books"]["autonomous"]["reason"] == "missing_submission"
    assert receipt["exit_code"] == deadman.ALERT_EXIT


def test_stale_scheduler_run_pages_operator_even_when_old_decision_was_valid() -> None:
    snapshot = healthy_snapshot()
    snapshot["jobs"]["autonomous_daily"].update(
        last_started=ts("2026-09-10", "23:10:00"),
        last_finished=ts("2026-09-10", "23:16:00"),
    )
    receipt = deadman.evaluate_snapshot(
        snapshot, scope="us", observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)
    )
    assert receipt["books"]["autonomous"]["reason"] == "scheduled_cycle_stale"
    assert receipt["exit_code"] == deadman.ALERT_EXIT


def test_market_closed_skip_is_accepted_without_fabricating_decision() -> None:
    snapshot = healthy_snapshot()
    snapshot["jobs"]["autonomous_daily"].update(
        last_status="skip", last_reason="market_closed", last_target_status=None
    )
    snapshot["decisions"]["autonomous"]["latest"] = {}
    receipt = deadman.evaluate_snapshot(
        snapshot, scope="us", observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)
    )
    assert receipt["state"] == "HEALTHY"
    assert receipt["books"]["autonomous"]["state"] == "EXPECTED_SKIP"
    assert receipt["books"]["autonomous"]["decision"] == {}


def test_governed_rejection_is_an_auditable_decision_not_missing_submission() -> None:
    snapshot = healthy_snapshot()
    snapshot["jobs"]["autonomous_daily"].update(
        last_status="warn",
        last_reason="rejected_risk_gate",
        last_target_status="rejected_risk_gate",
    )
    snapshot["decisions"]["autonomous"]["latest"].update(
        target_status="rejected_risk_gate", decision_effective=False
    )
    receipt = deadman.evaluate_snapshot(
        snapshot, scope="us", observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)
    )
    assert receipt["state"] == "HEALTHY"
    assert receipt["books"]["autonomous"]["state"] == "GOVERNED_HOLD"


def test_release_identity_mismatch_pages_operator_before_book_acceptance() -> None:
    snapshot = healthy_snapshot()
    snapshot["release"]["health_commit"] = "e" * 40
    receipt = deadman.evaluate_snapshot(
        snapshot, scope="us", observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC)
    )
    assert receipt["state"] == "ALERT"
    assert receipt["reason"] == "release_or_scheduler_unhealthy"
    assert receipt["books"] == {}


def test_asia_scope_requires_both_china_and_hk() -> None:
    snapshot = healthy_snapshot()
    snapshot["jobs"]["hk_daily"].update(
        last_status="error", last_reason="projection_failed", last_target_status="queued"
    )
    receipt = deadman.evaluate_snapshot(
        snapshot, scope="asia", observed_at=dt.datetime(2026, 9, 11, 10, 45, tzinfo=UTC)
    )
    assert receipt["books"]["china"]["state"] == "DECISION_ACCEPTED"
    assert receipt["books"]["hk"]["state"] == "ALERT"
    assert receipt["exit_code"] == deadman.ALERT_EXIT


def test_snapshot_sanitizers_drop_raw_provider_and_position_fields() -> None:
    decision = deadman.sanitize_decision(
        {
            "asof": "2026-09-11",
            "target_status": "queued",
            "decision_effective": True,
            "raw_error": "secret provider detail",
            "positions": [{"ticker": "AAPL", "weight": 0.5}],
        }
    )
    job = deadman.sanitize_job(
        {
            "id": "autonomous_daily",
            "last_status": "ok",
            "last_reason": None,
            "provider_error": "secret",
        }
    )
    assert set(decision) <= set(deadman.SAFE_DECISION_KEYS)
    assert set(job) <= set(deadman.SAFE_JOB_KEYS)
    assert "raw_error" not in json.dumps(decision)
    assert "provider_error" not in json.dumps(job)


def test_workflow_is_read_only_scheduled_and_fail_closed() -> None:
    workflow = Path(__file__).resolve().parents[1] / ".github/workflows/portfolio-decision-deadman.yml"
    text = workflow.read_text(encoding="utf-8")
    assert "30 0 * * 2-6" in text
    assert "45 10 * * 1-5" in text
    assert "contents: read" in text
    assert "VPS_DEPLOY_KEY" in text
    assert "scripts/portfolio_decision_deadman.py" in text
    assert "actions/upload-artifact@v4" in text
    assert "exit \"$(cat \"$RUNNER_TEMP/deadman.rc\")\"" in text
    forbidden = (
        "contents: write",
        "issues: write",
        "pull-requests: write",
        "method=\"POST\"",
        "method: POST",
        "/api/autonomous/run",
        "/api/china/run",
        "/api/hk/run",
        "MASTERMIND_AUTH_TOKEN",
        "force=true",
    )
    for token in forbidden:
        assert token not in text
