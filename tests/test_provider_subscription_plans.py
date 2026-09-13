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


def test_glm_current_credits_and_legacy_prompt_generations_are_distinct():
    current = resolve_plan("glm", "coding_plan", "max")
    assert _by_horizon(current, "five_hour", "credits")["limit"] == 28000
    assert _by_horizon(current, "weekly", "credits")["limit"] == 140000
    assert not any(row["metric"] == "prompts" for row in current.limits)
    assert current.usage_policy["supported_tool_required"] is True
    assert current.usage_policy["background_automation_allowed"] is False

    legacy = resolve_plan("glm", "coding_plan_legacy_v2", "max")
    assert _by_horizon(legacy, "five_hour", "prompts")["limit"] == 1600
    assert _by_horizon(legacy, "weekly", "prompts")["limit"] == 8000
    assert _by_horizon(legacy, "monthly", "mcp_web_calls")["limit"] == 4000


def test_glm_current_team_credits_are_separate_from_individual():
    team = resolve_plan("glm", "coding_plan_team", "premium")
    assert _by_horizon(team, "five_hour", "credits")["limit"] == 35000
    assert _by_horizon(team, "weekly", "credits")["limit"] == 155000


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
    assert personal.usage_policy["interactive_only"] is True
    assert personal.usage_policy["background_automation_allowed"] is False


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
    assert resolved.usage_policy["payg_recommended_for_production"] is True


def test_catalog_rejects_unknown_as_unlimited_policy():
    catalog = copy.deepcopy(load_catalog())
    catalog["unknown_selection_policy"] = "ASSUME_UNLIMITED"
    with pytest.raises(SubscriptionPlanError, match="fail closed"):
        validate_catalog(catalog)
