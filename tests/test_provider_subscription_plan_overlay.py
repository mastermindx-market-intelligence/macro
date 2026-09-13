from __future__ import annotations

import copy

import pytest

from engine.provider_subscription_plans import (
    SubscriptionPlanError,
    load_catalog,
    merge_overlay,
    resolve_plan,
)


def test_openai_has_dynamic_five_hour_and_weekly_contract():
    plan = resolve_plan("openai", "chatgpt_work_codex", "pro_20x")
    assert plan.known is True and plan.limits == ()
    assert {(row["horizon"], row["scope"]) for row in plan.dynamic_limits} == {
        ("five_hour", "shared_work_codex"),
        ("weekly", "shared_work_codex"),
    }


def test_anthropic_fable_is_relative_cap_not_additive_quota():
    plan = resolve_plan("anthropic", "claude_subscription", "max_20x")
    fable = next(row for row in plan.dynamic_limits if row["scope"] == "fable_models")
    assert fable["relative_fraction_of_parent"] == 0.5
    assert fable["parent_scope"] == "all_models"


def test_cursor_has_two_billing_cycle_pools_and_no_fake_weekly_window():
    plan = resolve_plan("cursor", "included_usage", "ultra")
    assert {(row["horizon"], row["scope"]) for row in plan.dynamic_limits} == {
        ("billing_cycle", "cursor_models"),
        ("billing_cycle", "other_models"),
    }


def test_xai_supergrok_and_bot_are_distinct_weekly_resources():
    supergrok = resolve_plan("xai", "supergrok", "supergrok")
    bot = resolve_plan("xai", "grok_bot", "included")
    assert supergrok.tier == "standard"
    assert supergrok.dynamic_limits[0]["scope"] == "supergrok_shared"
    assert bot.dynamic_limits[0]["scope"] == "grok_bot"


def test_unknown_dynamic_tier_still_fails_closed():
    plan = resolve_plan("cursor", "included_usage", None)
    assert plan.known is False
    assert plan.limits == ()
    assert plan.dynamic_limits == ()
    assert plan.reason == "UNKNOWN_TIER"


def test_overlay_cannot_replace_base_product():
    catalog = load_catalog(overlay_path=None)
    overlay = {
        "schema": "mastermind.provider_subscription_plan_overlay/v1",
        "providers": {
            "glm": {
                "products": {
                    "coding_plan": {
                        "tiers": {"max": {"limits": []}},
                    }
                }
            }
        },
    }
    with pytest.raises(SubscriptionPlanError, match="may not replace"):
        merge_overlay(catalog, overlay)
