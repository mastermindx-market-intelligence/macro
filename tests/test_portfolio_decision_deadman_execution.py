from __future__ import annotations

import datetime as dt

from scripts import portfolio_decision_deadman as deadman
from tests.test_portfolio_decision_deadman import UTC, healthy_snapshot


def _executed_snapshot(evidence: str) -> dict:
    snapshot = healthy_snapshot()
    snapshot["jobs"]["autonomous_daily"]["last_target_status"] = "executed"
    snapshot["decisions"]["autonomous"]["latest"].update(
        target_status="executed",
        decision_effective=True,
        execution_evidence_status=evidence,
    )
    return snapshot


def test_executed_decision_requires_receipt_verified_evidence() -> None:
    receipt = deadman.evaluate_snapshot(
        _executed_snapshot("legacy_unverified"),
        scope="us",
        observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC),
    )
    assert receipt["state"] == "ALERT"
    assert receipt["books"]["autonomous"]["reason"] == "execution_receipt_unverified"


def test_receipt_verified_execution_is_accepted() -> None:
    receipt = deadman.evaluate_snapshot(
        _executed_snapshot("receipt_verified"),
        scope="us",
        observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC),
    )
    assert receipt["state"] == "HEALTHY"
    assert receipt["books"]["autonomous"]["state"] == "DECISION_ACCEPTED"
