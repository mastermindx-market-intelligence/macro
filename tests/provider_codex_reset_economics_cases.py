from dataclasses import replace
from itertools import permutations

import pytest

from engine.provider_codex_reset_economics import (
    AccountObservation, BankedReset, PreviewPolicy, ResetEconomicsError,
    TaskQuote, Window, preview_codex_resets,
)

NOW = 1790899200


def account(name="a", *, week_left=100, short_left=100, week_in=500000,
            short_in=12000, resets=(), tasks=None, **kw):
    return AccountObservation(
        account_id=name, shared_resource_id="resource-" + name,
        provider_model="gpt-6.1-sol", suitability_tier="qualified-standard",
        observation_id="obs-" + name, calibration_id="measured-cohort-1",
        observed_at=NOW, valid_until=NOW + 600,
        short=Window(100, short_left, 0, NOW + short_in, 18000),
        weekly=Window(100, week_left, 0, NOW + week_in, 604800),
        banked_resets=tuple(resets),
        tasks=tuple(tasks) if tasks is not None else (task("j1"),),
        binding_verified=True, eligible=True, active_claims=0, effect_state="CLEAR",
        evidence_kind="provider_reported", renewal_semantics="first_use_after_reset",
        **kw,
    )


def task(name, *, ready=0, due=3600, duration=60, cost=10):
    return TaskQuote(name, NOW + ready, NOW + due, duration, cost, cost)


def preview(*rows, **kw):
    return preview_codex_resets(tuple(rows), now=NOW,
                               first_lawful_tier="qualified-standard", **kw)


def selected(p):
    return next(r for r in p["candidates"] if r["account_id"] == p["selected_account_id"])


def test_expiring_weekly_capacity_beats_fresh_account():
    p = preview(account("fresh"), account("expiring", week_left=30, week_in=1200))
    assert p["selected_account_id"] == "expiring"
    assert p["proposed_action"] == "RUN_CANDIDATE"


def test_no_work_never_spends_reset_or_starts_a_timer():
    p = preview(account(week_left=0, tasks=(), resets=(BankedReset("r", NOW + 600),)))
    assert p["selected_account_id"] is None
    assert p["proposed_action"] == "NONE"


def test_exhausted_account_uses_available_banked_reset_for_urgent_real_work():
    p = preview(account(week_left=0, resets=(BankedReset("r", NOW + 100000),)))
    assert p["proposed_action"] == "PROPOSE_BANKED_RESET_THEN_RUN"
    assert selected(p)["steps_forecast"][0]["banked_reset_id"] == "r"
    assert selected(p)["steps_forecast"][0]["start_at"] == NOW + 30


def test_imminent_free_reset_beats_spending_nonexpiring_banked_reset():
    p = preview(account(week_left=0, week_in=120, resets=(BankedReset("r", NOW + 100000),)))
    assert p["proposed_action"] == "WAIT_FOR_NATIVE_WINDOW_OR_DEMAND"
    assert selected(p)["steps_forecast"][0]["start_at"] == NOW + 120
    assert selected(p)["banked_resets_spent_forecast"] == 0


def test_free_reset_wait_is_not_allowed_to_miss_task_deadline():
    p = preview(account(week_left=0, week_in=1200, tasks=(task("j", due=600),),
                        resets=(BankedReset("r", NOW + 100000),)))
    assert p["proposed_action"] == "PROPOSE_BANKED_RESET_THEN_RUN"


def test_drain_before_reset_when_credit_survives_the_first_task():
    jobs = (task("one", cost=10), task("two", cost=10))
    p = preview(account(week_left=10, tasks=jobs, resets=(BankedReset("r", NOW + 500),)))
    steps = selected(p)["steps_forecast"]
    assert len(steps) == 2
    assert steps[0]["banked_reset_id"] is None
    assert steps[1]["banked_reset_id"] == "r"


def test_reset_before_drain_when_otherwise_credit_expires_and_work_cannot_finish():
    jobs = (task("one", duration=600, cost=10), task("two", cost=10))
    p = preview(account(week_left=10, tasks=jobs, resets=(BankedReset("r", NOW + 300),)))
    steps = selected(p)["steps_forecast"]
    assert len(steps) == 2
    assert steps[0]["banked_reset_id"] == "r"


def test_reset_is_finite_not_a_new_daily_or_weekly_entitlement():
    jobs = tuple(task("j" + str(i), cost=100, due=10000) for i in range(3))
    p = preview(account(week_left=0, tasks=jobs, resets=(BankedReset("r", NOW + 1000),)))
    assert selected(p)["completed_tasks_forecast"] == 1
    assert selected(p)["banked_resets_spent_forecast"] == 1


def test_reset_reanchors_week_and_cancels_the_original_free_refill():
    jobs = (task("first", cost=100, due=100), task("second", ready=300, due=1000, cost=100))
    p = preview(account(week_left=0, week_in=200, tasks=jobs,
                        resets=(BankedReset("r", NOW + 1000),)))
    assert selected(p)["completed_tasks_forecast"] == 1


def test_reset_is_not_done_before_future_work_arrives():
    p = preview(account(week_left=0, tasks=(task("future", ready=500),),
                        resets=(BankedReset("r", NOW + 400),)))
    assert p["selected_account_id"] is None


def test_noop_reset_not_spent_on_full_windows():
    p = preview(account(resets=(BankedReset("r", NOW + 100),)))
    assert selected(p)["banked_resets_spent_forecast"] == 0


def test_short_window_can_trigger_reset_even_with_weekly_capacity():
    p = preview(account(short_left=0, resets=(BankedReset("r", NOW + 500),)))
    assert p["proposed_action"] == "PROPOSE_BANKED_RESET_THEN_RUN"


def test_expired_token_and_token_expiring_during_operation_are_unusable():
    for expiry in (NOW - 1, NOW, NOW + 29, NOW + 30):
        p = preview(account(week_left=0, resets=(BankedReset("r", expiry),)))
        assert p["selected_account_id"] is None


@pytest.mark.parametrize("mutation,reason", [
    ({"eligible": False}, "BINDING_OR_ELIGIBILITY_UNPROVEN"),
    ({"binding_verified": False}, "BINDING_OR_ELIGIBILITY_UNPROVEN"),
    ({"evidence_kind": "estimated"}, "NATIVE_QUOTA_UNPROVEN"),
    ({"effect_state": "EFFECT_UNKNOWN"}, "ACCOUNT_EFFECT_OR_CLAIM_BUSY"),
    ({"active_claims": 1}, "ACCOUNT_EFFECT_OR_CLAIM_BUSY"),
    ({"renewal_semantics": "unknown"}, "RENEWAL_SEMANTICS_UNKNOWN"),
    ({"observed_at": NOW + 1}, "STALE_OR_FUTURE_OBSERVATION"),
    ({"observed_at": NOW - 601}, "STALE_OR_FUTURE_OBSERVATION"),
    ({"valid_until": NOW}, "STALE_OR_FUTURE_OBSERVATION"),
    ({"suitability_tier": "unqualified-cheap"}, "OUTSIDE_FIRST_LAWFUL_TIER"),
])
def test_candidate_gates_cannot_be_overridden_by_economics(mutation, reason):
    p = preview(replace(account(), **mutation))
    assert p["selected_account_id"] is None
    assert p["candidates"][0]["reason"] == reason


def test_observation_crossing_reset_requires_real_readback():
    a = account()
    p = preview(replace(a, weekly=replace(a.weekly, reset_at=NOW)))
    assert p["candidates"][0]["reason"] == "OBSERVATION_CROSSED_RESET_BOUNDARY"


@pytest.mark.parametrize("field", ["duration_seconds", "short_cost", "weekly_cost"])
def test_missing_measurements_are_not_zero_cost(field):
    p = preview(account(tasks=(replace(task("j"), **{field: None}),)))
    assert p["candidates"][0]["reason"] == "COST_OR_DURATION_UNKNOWN"


def test_reserves_remain_even_after_reset():
    a = account(week_left=0, resets=(BankedReset("r", NOW + 1000),))
    p = preview(replace(a, weekly=replace(a.weekly, reserve=95)))
    assert p["selected_account_id"] is None


def test_shared_quota_aliases_cannot_multiply_capacity():
    a, b = account("a"), account("b")
    with pytest.raises(ResetEconomicsError, match="shared quota"):
        preview(a, replace(b, shared_resource_id=a.shared_resource_id))


def test_candidates_must_represent_same_queue_not_better_invented_work():
    with pytest.raises(ResetEconomicsError, match="same owner demand"):
        preview(account("a"), account("b", tasks=(task("another"),)))


def test_same_inputs_replay_identically_including_input_order():
    rows = (account("c"), account("a"), account("b", week_left=50))
    results = [preview(*order) for order in permutations(rows)]
    assert all(p == results[0] for p in results)
    assert results[0]["selected_account_id"] == "b"


def test_existing_focus_is_preserved_only_after_real_priority_comparison():
    p = preview(account("a"), account("b"), preferred_account_id="b")
    assert p["selected_account_id"] == "b"
    p = preview(account("a", week_in=300), account("b"), preferred_account_id="b")
    assert p["selected_account_id"] == "a"


def test_budget_exhaustion_never_claims_an_optimum_or_routes_candidate():
    p = preview(account(tasks=(task("1"), task("2"))), policy=PreviewPolicy(max_states_per_account=1))
    assert p["selected_account_id"] is None
    assert p["candidates"][0]["reason"] == "FORECAST_STATE_BUDGET_EXCEEDED"


def test_no_live_authority_no_account_data_mutation_and_no_secret_fields():
    a = account()
    before = repr(a)
    p = preview(a)
    assert repr(a) == before
    assert p["authority"] == "NONE_PREVIEW_ONLY"
    assert p["live_admission"] is False
    assert p["revalidate_before_effect"] is True
    assert len(p["input_digest"]) == len(p["preview_digest"]) == 64
    assert not {"access_token", "refresh_token", "api_key", "email", "auth_data"}.intersection(p)


@pytest.mark.parametrize("field,value", [("short_cost", 0), ("weekly_cost", -1), ("duration_seconds", True)])
def test_invalid_measurements_are_rejected(field, value):
    with pytest.raises(ResetEconomicsError):
        preview(account(tasks=(replace(task("j"), **{field: value}),)))


def test_lower_measured_burn_beats_faster_expensive_model_in_same_qualified_tier():
    sol = account("sol", tasks=(task("j", duration=120, cost=10),))
    astra = replace(account("astra", tasks=(task("j", duration=60, cost=50),)), provider_model="gpt-6-astra")
    p = preview(astra, sol)
    assert p["selected_account_id"] == "sol"


def test_expensive_model_is_used_when_only_it_can_meet_the_deadline():
    sol = account("sol", tasks=(task("j", duration=120, due=90, cost=10),))
    astra = replace(account("astra", tasks=(task("j", duration=60, due=90, cost=50),)), provider_model="gpt-6-astra")
    p = preview(astra, sol)
    assert p["selected_account_id"] == "astra"


def test_credit_input_order_does_not_change_replay_digest():
    resets = (BankedReset("later", NOW + 6000), BankedReset("soon", NOW + 500))
    assert preview(account(week_left=0, resets=resets)) == preview(account(week_left=0, resets=tuple(reversed(resets))))


@pytest.mark.parametrize("policy", [PreviewPolicy(max_observation_age_seconds=601), PreviewPolicy(max_forecast_seconds=604801), PreviewPolicy(max_states_per_account=100001)])
def test_policy_cannot_weaken_freshness_or_bounded_work(policy):
    with pytest.raises(ResetEconomicsError, match="safety bounds"):
        preview(account(), policy=policy)


def test_unknown_first_measurement_does_not_hide_malformed_later_quote():
    jobs = (replace(task("first"), weekly_cost=None), replace(task("second"), short_cost=-1))
    with pytest.raises(ResetEconomicsError, match="short_cost"):
        preview(account(tasks=jobs))


def test_input_objects_are_immutable_and_both_rolling_windows_bind_each_task():
    jobs = (task("first", cost=60, due=30000), task("second", cost=60, due=30000))
    a = account(tasks=jobs, week_left=100, short_left=100, week_in=600, short_in=1200)
    p = preview(a)
    steps = selected(p)["steps_forecast"]
    assert steps[0]["start_at"] == NOW
    assert steps[1]["start_at"] == NOW + 1200
    assert a.weekly.remaining == 100
    assert a.short.remaining == 100


@pytest.mark.parametrize("soon_name,late_name", [("z-soon", "a-late"), ("a-soon", "z-late")])
def test_expiring_short_capacity_wins_independently_of_lexical_id(soon_name, late_name):
    jobs = (task("j", cost=20, duration=30),)
    soon = account(soon_name, short_left=20, short_in=60, tasks=jobs)
    late = account(late_name, short_left=20, short_in=18000, tasks=jobs)
    for order in ((soon, late), (late, soon)):
        assert preview(*order)["selected_account_id"] == soon_name


@pytest.mark.parametrize("absent", ["short", "weekly"])
def test_explicitly_inapplicable_window_is_not_fabricated(absent):
    quote = replace(task("j"), **{absent + "_cost": None})
    row = replace(account(tasks=(quote,), resets=(BankedReset("r", NOW + 900),)),
                  **{absent: None})
    result = preview(row)
    chosen = selected(result)
    assert chosen[absent + "_remaining"] is None
    assert chosen[absent + "_capacity"] is None
    assert chosen[absent + "_reset_at"] is None
    assert chosen["completed_tasks_forecast"] == 1
    assert chosen["banked_resets_spent_forecast"] == 0
    assert result["proposed_action"] == "RUN_CANDIDATE"
    assert result["live_admission"] is False


@pytest.mark.parametrize("absent", ["short", "weekly"])
@pytest.mark.parametrize("invented_cost", [0, 10, True])
def test_inapplicable_window_cannot_carry_a_fabricated_cost(absent, invented_cost):
    quote = replace(task("j"), **{absent + "_cost": invented_cost})
    with pytest.raises(ResetEconomicsError):
        preview(replace(account(tasks=(quote,)), **{absent: None}))


def test_absence_of_every_native_constraint_is_not_unlimited_capacity():
    quote = replace(task("j"), short_cost=None, weekly_cost=None)
    with pytest.raises(ResetEconomicsError):
        preview(replace(account(tasks=(quote,)), short=None, weekly=None))


@pytest.mark.parametrize("absent", ["short", "weekly"])
def test_single_window_still_requires_measurement_and_fresh_observation(absent):
    active = "weekly" if absent == "short" else "short"
    quote = replace(task("j"), **{absent + "_cost": None, active + "_cost": None})
    row = replace(account(tasks=(quote,)), **{absent: None})
    assert preview(row)["candidates"][0]["reason"] == "COST_OR_DURATION_UNKNOWN"
    row = replace(row, tasks=(replace(quote, **{active + "_cost": 10}),))
    row = replace(row, **{active: replace(getattr(row, active), reset_at=NOW)})
    assert preview(row)["candidates"][0]["reason"] == "OBSERVATION_CROSSED_RESET_BOUNDARY"


@pytest.mark.parametrize("with_reset", [False, True])
def test_identical_constraints_do_not_double_count_task_resource_value(with_reset):
    jobs = (task("one", cost=20), task("two", cost=20))
    row = account(tasks=jobs, week_left=0 if with_reset else 50,
                  week_in=1200, resets=(BankedReset("r", NOW + 100),) if with_reset else ())
    both = replace(row, short=row.weekly)
    only = replace(both, short=None,
                   tasks=tuple(replace(t, short_cost=None) for t in jobs))
    two, one = selected(preview(both)), selected(preview(only))
    for field in ("resource_value_forecast", "normalized_burn_forecast",
                  "steps_forecast", "banked_resets_spent_forecast"):
        assert two[field] == one[field]


def test_original_short_window_reward_ends_after_its_natural_renewal():
    from fractions import Fraction
    jobs = (task("one", cost=1, duration=120), task("two", cost=1))
    result = selected(preview(account(tasks=jobs, short_in=60)))
    assert result["completed_tasks_forecast"] == 2
    assert Fraction(result["resource_value_forecast"]) == Fraction(86400 - 60, 86400)


def test_reset_reanchors_short_window_and_cancels_its_old_refill():
    jobs = (task("first", cost=100, due=100),
            task("second", ready=300, due=1000, cost=100))
    row = account(short_left=0, short_in=200, tasks=jobs,
                  resets=(BankedReset("r", NOW + 1000),))
    row = replace(row, weekly=replace(row.weekly, capacity=1000, remaining=1000))
    result = selected(preview(row))
    assert result["completed_tasks_forecast"] == 1
    assert result["banked_resets_spent_forecast"] == 1


@pytest.mark.parametrize("scaled_window", ["short", "weekly"])
def test_native_unit_rescaling_preserves_economic_decision(scaled_window):
    jobs = (task("one", cost=5), task("two", cost=95))
    row = account(short_left=20, week_left=20, tasks=jobs,
                  resets=(BankedReset("r", NOW + 300),))
    window = getattr(row, scaled_window)
    scaled = replace(row, **{scaled_window: replace(window, capacity=window.capacity * 101,
        remaining=window.remaining * 101, reserve=window.reserve * 101)},
        tasks=tuple(replace(t, **{scaled_window + "_cost": getattr(t, scaled_window + "_cost") * 101}) for t in jobs))
    first, second = selected(preview(row)), selected(preview(scaled))
    for field in ("resource_value_forecast", "normalized_burn_forecast", "steps_forecast", "expiry_tiebreak_forecast"):
        assert first[field] == second[field]


@pytest.mark.parametrize("absent", ["short", "weekly"])
def test_natural_refill_during_reset_latency_does_not_spend_a_credit(absent):
    active = "weekly" if absent == "short" else "short"
    quote = replace(task("j", due=90, duration=30), **{absent + "_cost": None})
    row = replace(account(tasks=(quote,), resets=(BankedReset("r", NOW + 80),)),
                  **{absent: None})
    row = replace(row, **{active: replace(getattr(row, active), remaining=0, reset_at=NOW + 15)})
    chosen = selected(preview(row))
    assert chosen["banked_resets_spent_forecast"] == 0
    assert chosen["steps_forecast"][0]["start_at"] == NOW + 15


def test_exchanging_window_labels_preserves_the_constraint_decision():
    jobs = (replace(task("one", cost=15), short_cost=30),
            replace(task("two", ready=90, cost=45), short_cost=20))
    row = account(tasks=jobs, short_left=30, week_left=50, short_in=120,
                  week_in=600, resets=(BankedReset("r", NOW + 200),))
    swapped = replace(row, short=row.weekly, weekly=row.short,
                      tasks=tuple(replace(t, short_cost=t.weekly_cost, weekly_cost=t.short_cost)
                                  for t in jobs))
    before, after = selected(preview(row)), selected(preview(swapped))
    for field in ("resource_value_forecast", "normalized_burn_forecast", "steps_forecast", "expiry_tiebreak_forecast"):
        assert before[field] == after[field]


@pytest.mark.parametrize("window", ["short", "weekly"])
@pytest.mark.parametrize("names", [("z-soon", "a-late"), ("a-soon", "z-late")])
def test_nonmaximal_window_expiry_breaks_otherwise_equal_account_tie(window, names):
    soon_name, late_name = names
    jobs = (task("one", cost=20, duration=30),)
    common = {"short_in": 12000} if window == "weekly" else {"week_in": 60}
    field = "week_in" if window == "weekly" else "short_in"
    sooner, later = (43200, 500000) if window == "weekly" else (600, 18000)
    soon = account(soon_name, tasks=jobs, **common, **{field: sooner})
    late = account(late_name, tasks=jobs, **common, **{field: later})
    for order in ((soon, late), (late, soon)):
        result = preview(*order, preferred_account_id=late_name)
        candidates = {r["account_id"]: r for r in result["candidates"]}
        assert candidates[soon_name]["resource_value_forecast"] == candidates[late_name]["resource_value_forecast"]
        assert result["selected_account_id"] == soon_name
        assert result["proposed_action"] == "RUN_CANDIDATE"
        assert result["live_admission"] is False


@pytest.mark.parametrize("advantage", ["burn", "latency"])
def test_expiry_tiebreak_cannot_overrule_measured_burn_or_latency(advantage):
    fast_cheap = task("one", cost=10, duration=30)
    costlier = replace(fast_cheap, short_cost=20, weekly_cost=20) if advantage == "burn" else replace(fast_cheap, duration_seconds=60)
    efficient = account("efficient", tasks=(fast_cheap,), week_in=500000)
    expiring = account("expiring", tasks=(costlier,), week_in=43200)
    assert preview(expiring, efficient)["selected_account_id"] == "efficient"


@pytest.mark.parametrize("with_reset", [False, True])
def test_expiry_tiebreak_preserves_redundant_constraint_equivalence(with_reset):
    jobs = (task("one", cost=20), task("two", cost=20))
    row = account(tasks=jobs, week_left=0 if with_reset else 50, week_in=1200,
                  resets=(BankedReset("r", NOW + 100),) if with_reset else ())
    both = replace(row, short=row.weekly)
    only = replace(both, short=None, tasks=tuple(replace(t, short_cost=None) for t in jobs))
    duplicate, single = selected(preview(both)), selected(preview(only))
    assert duplicate["expiry_tiebreak_forecast"] == single["expiry_tiebreak_forecast"]
    assert duplicate["resource_value_forecast"] == single["resource_value_forecast"]
    assert duplicate["steps_forecast"] == single["steps_forecast"]


def test_expiry_tiebreak_drops_cancelled_or_expired_original_windows():
    from fractions import Fraction
    jobs = (task("one", cost=1, duration=120), task("two", cost=1))
    row = account(tasks=jobs, short_in=60, week_in=500000)
    assert Fraction(selected(preview(row))["expiry_tiebreak_forecast"]) == Fraction(1439, 2880)
    reset_row = account(week_left=0, resets=(BankedReset("r", NOW + 300),))
    assert selected(preview(reset_row))["expiry_tiebreak_forecast"] == "0"
