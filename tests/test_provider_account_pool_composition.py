"""Regression checks for secret-free observation composition; no provider I/O."""
from dataclasses import replace
import pytest
import engine.provider_account_pool as pool
NOW = "2026-09-14T10:00:00Z"
LATER = "2026-09-14T10:20:00Z"


def member(name, percent=0, observed=NOW, stale='2026-09-14T10:10:00Z'):
    return pool.AccountObservation(name,'available',observed,stale,
        pool.UsageWindow(percent,'2026-09-14T15:00:00Z'),
        pool.UsageWindow(percent,'2026-09-20T00:00:00Z'),
        pool.UsageWindow(percent,'2026-10-14T00:00:00Z'))


def snapshot(*rows):
    return pool.build_snapshot(pool_id='opencode-go',provider='opencode',product='go',
        generated_at=NOW,members=rows or (member('acct-a'), member('acct-b'), member('acct-c')))


def test_parser_float_percent_is_accepted_without_rounding():
    value=snapshot(member('acct-a', 20.25), member('acct-b', 20.1))
    assert pool.select_account(value).account_id=='acct-b'


def test_exclusions_do_not_rewrite_membership_generation():
    value=snapshot()
    result=pool.select_account(value,excluded_account_ids=('acct-a','acct-b'),now=NOW)
    assert result.account_id=='acct-c'
    assert result.pool_generation==value.generation


def test_stale_snapshot_is_rechecked_at_request_time():
    result=pool.select_account(snapshot(),now=LATER)
    assert result.account_id is None


def test_future_observation_is_not_capacity():
    value=snapshot(member('acct-a',observed='2026-09-14T10:05:00Z'))
    assert pool.select_account(value).account_id is None


def test_forged_generation_is_not_trusted():
    value=replace(snapshot(), generation='f'*64)
    with pytest.raises(pool.AccountPoolError):
        pool.select_account(value)


def test_auth_absence_of_effect_is_not_usage_authority():
    assert not pool.rollover_decision('proven_no_effect','auth').allowed


def usage_rows():
    return [dict(horizon=name, metric="provider_allocation", scope="account_shared",
        observed_at=NOW, used_percent=10.25, reset_at="2026-09-20T00:00:00Z", status="limited")
        for name in ("five_hour", "weekly", "monthly")]


def from_rows(rows, state="available"):
    return pool.observation_from_usage_rows(account_id="acct-a", state=state,
        observed_at=NOW, stale_after=LATER, quota_rows=rows)


def test_bridge_preserves_fraction_and_missing_window():
    row = from_rows(usage_rows()[:1])
    assert row.five_hour.used_percent == 10.25
    assert row.weekly.used_percent is None
    assert pool.select_account(snapshot(row), now=NOW).account_id is None


def test_provider_exhaustion_overrides_normalized_available_state():
    rows = usage_rows()
    rows[0]["status"] = "exhausted"
    row = from_rows(rows, state="AVAILABLE")
    assert row.state == "cooling"
    assert pool.select_account(snapshot(row), now=NOW).account_id is None


@pytest.mark.parametrize("field,value", [
    ("metric", "currency"), ("scope", "model_specific"),
    ("observed_at", "2026-09-14T09:59:00Z"),
])
def test_bridge_refuses_wrong_scope_metric_or_mixed_time(field, value):
    rows = usage_rows()
    rows[0][field] = value
    with pytest.raises(pool.AccountPoolError):
        from_rows(rows)


def test_duplicate_horizon_does_not_hide_exhaustion():
    rows = usage_rows()
    with pytest.raises(pool.AccountPoolError, match="duplicate"):
        from_rows(rows + [dict(rows[0], status="exhausted")])


def test_unknown_status_cannot_supply_capacity():
    rows = usage_rows()
    rows[0]["status"] = "invented"
    assert from_rows(rows).five_hour.used_percent is None


def test_clock_passage_does_not_fabricate_a_reset():
    row = replace(member("acct-a"), five_hour=pool.UsageWindow(1, NOW))
    assert pool.select_account(snapshot(row), now=NOW).account_id is None


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, -1, 101, "10"])
def test_invalid_percentage_types_fail_closed(value):
    with pytest.raises(pool.AccountPoolError):
        snapshot(member("acct-a", value))


@pytest.mark.parametrize("value", [" Session-1", "Session-1 ", "Session\n1", 12])
def test_pool_session_identity_cannot_be_silently_changed(value):
    with pytest.raises(pool.AccountPoolError):
        pool.select_account(snapshot(), session_id=value)
