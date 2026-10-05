from __future__ import annotations

import datetime as dt

from scripts import portfolio_decision_deadman as deadman
from tests.test_portfolio_decision_deadman import UTC, healthy_snapshot


def test_governed_hold_cannot_be_marked_effective() -> None:
    snapshot = healthy_snapshot()
    snapshot["jobs"]["autonomous_daily"].update(
        last_status="warn",
        last_reason="rejected_risk_gate",
        last_target_status="rejected_risk_gate",
    )
    snapshot["decisions"]["autonomous"]["latest"].update(
        target_status="rejected_risk_gate",
        decision_effective=True,
    )

    receipt = deadman.evaluate_snapshot(
        snapshot,
        scope="us",
        observed_at=dt.datetime(2026, 9, 12, 0, 30, tzinfo=UTC),
    )

    assert receipt["state"] == "ALERT"
    assert receipt["books"]["autonomous"]["reason"] == "governed_hold_marked_effective"
    assert receipt["exit_code"] == deadman.ALERT_EXIT
