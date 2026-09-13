from __future__ import annotations

import copy

import pytest

from engine.provider_subscription_plans import SubscriptionPlanError, load_catalog, resolve_plan, validate_catalog


def _by_horizon(selection, horizon, metric):
    return next(row for row in selection.limits if row["horizon"] == horizon and row["metric"] == metric)


def test_unknown_tiers_never_imply_capacity():
    for provider, product in (
        ("glm", "coding_plan"),
        ("alibaba", "token_plan_personal"),
        ("minimax", "token_plan_current_m3"),
    ):
        selected = resolve_plan(provider, product, None)
        assert selected.known is False
        assert selected.limits == ()
        assert selected.reason == "UNKNOWN_TIER"


def test_glm_compute_windows_and_mcp_monthly_are_not_conflated():
    max_plan = resolve_plan("glm", "coding_plan", "max")
    assert _by_horizon(max_plan, "five_hour", "prompts")["limit"] == 1600
    assert _by_horizon(max_plan, "weekly", "prompts")["limit"] == 8000
    assert _by_horizon(max_plan, "monthly", "mcp_web_calls")["limit"] == 4000
    assert not any(row["horizon"] == "monthly" and row["metric"] == "prompts" for row in max_plan.limits)


def test_alibaba_personal_and_team_use_native_windows():
    personal = resolve_plan("alibaba", "token_plan_personal", "standard")
    assert _by_horizon(personal, "five_hour", "credits") == {
        "horizon": "five_hour", "window_type": "rolling", "metric": "credits", "limit": 3000,
        "enforced": False, "temporary_policy": True,
    }
    assert _by_horizon(personal, "weekly", "credits")["limit"] == 10000
    team = resolve_plan("alibaba", "token_plan_team", "premium")
    assert len(team.limits) == 1
    assert team.limits[0]["horizon"] == "billing_cycle"
    assert team.limits[0]["limit"] == 250000
    assert resolve_plan("alibaba", "token_plan_team", "max").tier == "premium"


def test_minimax_legacy_weekly_is_explicitly_conditional_and_ten_x():
    for tier, five_hour in (("starter", 1500), ("plus", 4500), ("max", 15000)):
        plan = resolve_plan("minimax", "token_plan_standard_legacy_m2_7", tier)
        five = _by_horizon(plan, "five_hour", "requests")
        week = _by_horizon(plan, "weekly", "requests")
        assert five["limit"] == five_hour
        assert week["limit"] == five_hour * 10
        assert week["conditional_since"] == "2026-03-23T00:00:00Z"


def test_current_minimax_marketing_reference_counts_do_not_become_hard_limits():
    catalog = load_catalog()
    max_row = catalog["providers"]["minimax"]["products"]["token_plan_current_m3"]["tiers"]["max"]
    assert max_row["limits"] == []
    assert max_row["reference_limits"]
    resolved = resolve_plan("minimax", "token_plan_current_m3", "max", catalog=catalog)
    assert resolved.known is True
    assert resolved.limits == ()


def test_catalog_rejects_unknown_as_unlimited_policy():
    catalog = copy.deepcopy(load_catalog())
    catalog["unknown_selection_policy"] = "ASSUME_UNLIMITED"
    with pytest.raises(SubscriptionPlanError, match="fail closed"):
        validate_catalog(catalog)
