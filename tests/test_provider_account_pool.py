from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engine.provider_account_pool import (
    AccountObservation,
    AccountPoolError,
    UsageWindow,
    build_snapshot,
    member_eligible,
    rollover_decision,
    select_account,
)


NOW = datetime(2026, 9, 14, 6, 0, tzinfo=timezone.utc)


def iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def member(
    account: str,
    *,
    state: str = "available",
    five_hour: int | None = 0,
    weekly: int | None = 0,
    monthly: int | None = 0,
    stale_delta: int = 600,
    concurrency_used: int | None = None,
    concurrency_limit: int | None = None,
) -> AccountObservation:
    return AccountObservation(
        account_id=account,
        state=state,
        observed_at=iso(NOW - timedelta(seconds=10)),
        stale_after=iso(NOW + timedelta(seconds=stale_delta)),
        five_hour=UsageWindow(five_hour, iso(NOW + timedelta(hours=4))),
        weekly=UsageWindow(weekly, iso(NOW + timedelta(days=4))),
        monthly=UsageWindow(monthly, iso(NOW + timedelta(days=20))),
        concurrency_used=concurrency_used,
        concurrency_limit=concurrency_limit,
    )


def snapshot(*rows: AccountObservation):
    return build_snapshot(
        pool_id="opencode-go",
        provider="opencode",
        product="go",
        generated_at=iso(NOW),
        members=rows,
    )


def test_generation_is_membership_identity_not_dynamic_usage():
    first = snapshot(member("acct-a", five_hour=5), member("acct-b", weekly=20))
    second = snapshot(member("acct-b", weekly=80), member("acct-a", five_hour=60))
    assert first.generation == second.generation
    assert len(first.generation) == 64


def test_generation_changes_when_member_set_changes():
    first = snapshot(member("acct-a"), member("acct-b"))
    second = snapshot(member("acct-a"), member("acct-c"))
    assert first.generation != second.generation


def test_healthy_sticky_member_is_retained_for_context_affinity():
    value = snapshot(member("acct-a", five_hour=70), member("acct-b", five_hour=1))
    decision = select_account(value, sticky_account_id="acct-a", session_id="session-1")
    assert decision.account_id == "acct-a"
    assert decision.sticky_retained is True
    assert decision.pool_generation == value.generation


def test_exhausted_sticky_member_rolls_to_best_headroom():
    value = snapshot(
        member("acct-a", five_hour=100),
        member("acct-b", five_hour=20, weekly=20, monthly=20),
        member("acct-c", five_hour=10, weekly=90, monthly=10),
    )
    decision = select_account(value, sticky_account_id="acct-a", session_id="session-1")
    assert decision.account_id == "acct-b"
    assert decision.sticky_retained is False


def test_bottleneck_headroom_beats_low_rolling_usage():
    value = snapshot(
        member("acct-a", five_hour=1, weekly=99, monthly=99),
        member("acct-b", five_hour=20, weekly=20, monthly=20),
    )
    assert select_account(value).account_id == "acct-b"


def test_unknown_required_window_fails_closed():
    value = snapshot(member("acct-a", weekly=None), member("acct-b", weekly=30))
    assert not member_eligible(value, value.members[0])
    assert select_account(value).account_id == "acct-b"


def test_stale_cooling_and_full_concurrency_members_are_ineligible():
    value = snapshot(
        member("acct-a", stale_delta=-1),
        member("acct-b", state="cooling"),
        member("acct-c", concurrency_used=2, concurrency_limit=2),
    )
    decision = select_account(value)
    assert decision.account_id is None
    assert decision.reason == "no_eligible_account"


def test_equal_capacity_uses_stable_session_affinity_and_spreads_sessions():
    value = snapshot(member("acct-a"), member("acct-b"), member("acct-c"))
    first = select_account(value, session_id="session-42").account_id
    assert select_account(value, session_id="session-42").account_id == first
    selected = {select_account(value, session_id=f"session-{index}").account_id for index in range(60)}
    assert selected == {"acct-a", "acct-b", "acct-c"}


def test_rollover_requires_proven_no_effect_and_safe_refusal():
    assert rollover_decision("proven_no_effect", "usage_limit").allowed is True
    assert rollover_decision("proven_no_effect", "auth").allowed is False
    assert rollover_decision("effect_unknown", "usage_limit").allowed is False
    assert rollover_decision("effect_observed", "usage_limit").allowed is False
    assert rollover_decision("proven_no_effect", "timeout").allowed is False


def test_duplicate_accounts_are_rejected_after_normalization():
    with pytest.raises(AccountPoolError, match="duplicate account_id"):
        snapshot(member("ACCT-A"), member("acct-a"))


def test_invalid_usage_and_freshness_are_rejected():
    with pytest.raises(AccountPoolError, match="invalid usage percent"):
        snapshot(member("acct-a", five_hour=101))
    row = member("acct-a")
    bad = AccountObservation(
        row.account_id,
        row.state,
        row.stale_after,
        row.observed_at,
        row.five_hour,
        row.weekly,
        row.monthly,
    )
    with pytest.raises(AccountPoolError, match="stale_after precedes"):
        snapshot(bad)


def test_invalid_effect_state_is_rejected():
    with pytest.raises(AccountPoolError, match="invalid effect_state"):
        rollover_decision("maybe", "usage_limit")
