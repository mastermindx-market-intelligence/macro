"""Point-in-time/display-only invariants; fixtures are not performance evidence."""
from dataclasses import replace
import json

import pytest

from engine.market_navigator import (
    AUTHORITY, Condition, ContractError, Observation, Receipt, Scenario, compose,
    public_projection,
)

ASOF = "2026-10-21T20:01:00Z"


def receipt(**changes):
    args = dict(source_ref="internal://fixture/source", revision="fixture-v1",
                observed_at="2026-10-21T20:00:00Z", received_at="2026-10-21T20:00:01Z",
                available_at="2026-10-21T20:00:02Z", valid_until="2026-10-21T20:05:00Z")
    return Receipt(**(args | changes))


def obs(**changes):
    args = dict(key="price", subject="SPY:ARCX", family="price", value=773.09,
                unit="USD", horizons=("intraday",), receipt=receipt())
    return Observation(**(args | changes))


def scenario(**changes):
    args = dict(key="reclaim", subject="SPY:ARCX", horizon="intraday",
                definition_available_at="2026-10-21T19:00:00Z", definition_ref="fixture:rule-v1", deadline="2026-10-21T20:04:00Z",
                triggers=(Condition("price", "gte", 773, "USD"),),
                invalidations=(Condition("price", "lt", 772, "USD"),),
                support=("price",), counterevidence=("breadth",))
    return Scenario(**(args | changes))


def build(observations=None, scenarios=None, **kwargs):
    args = dict(subject="SPY:ARCX", horizon="intraday", as_of=ASOF,
                expected_market_session="2026-10-21",
                observations=(obs(),) if observations is None else observations,
                scenarios=(scenario(),) if scenarios is None else scenarios)
    return compose(**(args | kwargs))


def status(**kwargs):
    return build(**kwargs)["scenarios"][0]["status"]


def test_numeric_conditions_are_not_trade_authority():
    p = build()
    assert p["scenarios"][0]["status"] == "conditions_met"
    assert p["scenarios"][0]["probability"] is None
    assert p["readiness"] == "research_only"
    assert not any(p["authority"].values())
    assert p["scenarios"][0]["counterevidence"] == [{"key": "breadth", "status": "missing"}]


@pytest.mark.parametrize("value", [None, float("nan"), float("inf"), True, "773", 10**1000])
def test_invalid_numbers_do_not_become_neutral(value):
    if value is None:
        assert status(observations=(obs(value=None),)) == "unresolved"
    else:
        with pytest.raises(ContractError):
            obs(value=value)


@pytest.mark.parametrize("cutoff,expected", [
    ("2026-10-21T20:00:01Z", "not_yet_available"),
    ("2026-10-21T20:00:02Z", "current"),
    ("2026-10-21T20:05:00Z", "stale"),
])
def test_half_open_availability(cutoff, expected):
    assert build(as_of=cutoff)["observations"][0]["status"] == expected


@pytest.mark.parametrize("bad", ["2026-10-21", "2026-10-21T20:00:00", "no", None])
def test_naive_missing_bad_clocks_rejected(bad):
    with pytest.raises(ContractError):
        receipt(available_at=bad)


def test_revision_published_later_is_not_historically_known():
    revised = receipt(received_at="2026-10-22T10:00:00Z", available_at="2026-10-22T10:00:01Z")
    assert build(observations=(obs(receipt=revised),))["observations"][0]["status"] == "not_yet_available"


@pytest.mark.parametrize("changes", [
    {"received_at": "2026-10-21T19:00:00Z"},
    {"valid_until": "2026-10-21T19:00:00Z"},
    {"source_ref": ""}, {"revision": ""},
])
def test_receipt_contract(changes):
    with pytest.raises(ContractError):
        receipt(**changes)


@pytest.mark.parametrize("quality", ["user_claim", "synthetic"])
def test_screenshots_and_simulations_never_qualify(quality):
    assert status(observations=(obs(quality=quality),)) == "unresolved"


@pytest.mark.parametrize("changes,expected", [
    ({"subject": "QQQ:XNAS"}, "subject_mismatch"),
    ({"horizons": ("swing",)}, "horizon_mismatch"),
    ({"value": None}, "missing"),
])
def test_observation_eligibility(changes, expected):
    p = build(observations=(obs(**changes),))
    assert p["observations"][0]["status"] == expected
    assert p["observations"][0]["value"] is None
    assert p["scenarios"][0]["status"] == "unresolved"


def test_zero_is_real_not_missing():
    s = scenario(triggers=(Condition("price", "gte", 0, "USD"),),
                 invalidations=(Condition("price", "lt", 0, "USD"),))
    assert status(observations=(obs(value=0),), scenarios=(s,)) == "conditions_met"


def test_unit_mismatch_abstains():
    p = build(observations=(obs(unit="percent"),))
    assert p["scenarios"][0]["status"] == "unresolved"
    assert p["scenarios"][0]["triggers"][0]["reason"] == "unit_mismatch"


@pytest.mark.parametrize("value,expected", [(771, "invalidated"), (772.5, "waiting"), (773, "conditions_met")])
def test_condition_precedence(value, expected):
    assert status(observations=(obs(value=value),)) == expected


def test_true_invalidation_dominates_true_trigger():
    s = scenario(invalidations=(Condition("price", "gt", 770, "USD"),))
    assert status(scenarios=(s,)) == "invalidated"


def test_missing_invalidation_prevents_confirmation():
    s = scenario(invalidations=(Condition("credit", "gt", 5, "percent"),))
    assert status(scenarios=(s,)) == "unresolved"


def test_deadline_is_exclusive():
    assert status(as_of="2026-10-21T20:04:00Z") == "expired"


def test_scenario_horizon_cannot_be_silently_reused():
    assert status(scenarios=(scenario(horizon="swing"),)) == "horizon_mismatch"


def test_duplicate_source_or_scenario_refused():
    with pytest.raises(ContractError):
        build(observations=(obs(), obs()))
    with pytest.raises(ContractError):
        build(scenarios=(scenario(), scenario()))


def test_composition_is_order_independent_and_replayable():
    second = obs(key="breadth", value=55.26, unit="percent", family="breadth")
    p = build(observations=(obs(), second))
    q = build(observations=(second, obs()))
    assert p == q
    assert build(observations=(obs(value=772),))["context_digest"] != p["context_digest"]


def test_revision_identity_changes_digest():
    assert build()["context_digest"] != build(observations=(obs(receipt=receipt(revision="v2")),))["context_digest"]


def test_no_lifecycle_is_carried_between_calls():
    assert status(observations=(obs(value=771),)) == "invalidated"
    assert status() == "conditions_met"


def test_coincident_conditions_are_not_ranked():
    p = build(scenarios=(scenario(), scenario(key="other")))
    assert p["coincident_conditions"] is True
    assert all(s["probability"] is None for s in p["scenarios"])
    assert "preferred" not in p


def test_all_missing_still_has_honest_output():
    p = build(observations=())
    assert p["scenarios"][0]["status"] == "unresolved"
    assert p["canonical_market"]["status"] == "missing"


def state(**changes):
    return dict(schema="market_state.v1", asof="2026-10-21", verdict="MIXED",
                is_display_only=True, market="us") | changes


def test_incumbent_verdict_is_consumed_not_voted():
    p = build(market_state=state(verdict="RISK_OFF"), market_state_receipt=receipt())
    assert p["canonical_market"]["verdict"] == "RISK_OFF"
    assert "score" not in p["canonical_market"]
    assert p["scenarios"][0]["status"] == "conditions_met"


def test_fresh_file_cannot_launder_old_state_date():
    p = build(market_state=state(asof="2026-10-20"), market_state_receipt=receipt())
    assert p["canonical_market"]["status"] == "asof_mismatch"
    assert p["canonical_market"]["verdict"] is None


@pytest.mark.parametrize("changes", [{"stale_inputs": ["breadth"]}, {"degraded_components": ["vol"]}])
def test_degraded_state_is_not_current(changes):
    p = build(market_state=state(**changes), market_state_receipt=receipt())
    assert p["canonical_market"]["status"] == "degraded"
    assert p["canonical_market"]["verdict"] is None


@pytest.mark.parametrize("changes", [{"schema": "other"}, {"is_display_only": False}, {"asof": None}])
def test_malformed_state_refused(changes):
    with pytest.raises(ContractError):
        build(market_state=state(**changes), market_state_receipt=receipt())


def test_state_requires_receipt():
    with pytest.raises(ContractError):
        build(market_state=state())


def test_stale_state_cannot_lead_hero():
    p = build(as_of="2026-10-21T20:06:00Z", market_state=state(), market_state_receipt=receipt())
    assert p["canonical_market"]["verdict"] is None
    assert p["canonical_market"]["status"] == "stale"


def test_public_projection_strips_source_identity_and_never_escalates():
    p = public_projection(build(market_state=state(), market_state_receipt=receipt()))
    text = json.dumps(p)
    assert "internal://" not in text and "source_ref" not in text and "revision" not in text
    assert "subject" not in p
    assert p["authority"] == AUTHORITY


def test_mutation_or_authority_tampering_is_rejected():
    p = build()
    p["observations"][0]["value"] = 999
    with pytest.raises(ContractError):
        public_projection(p)
    p = build()
    p["authority"]["trading"] = True
    with pytest.raises(ContractError):
        public_projection(p)


@pytest.mark.parametrize("changes", [{"key": "../../etc"}, {"family": "certainty"},
    {"horizons": ()}, {"horizons": ("next_year",)}, {"quality": "verified_alpha"}])
def test_bounded_vocabulary(changes):
    with pytest.raises(ContractError):
        obs(**changes)


def test_conditions_are_not_code():
    with pytest.raises(ContractError):
        Condition("price", "eval", 773, "USD")
    with pytest.raises(ContractError):
        scenario(triggers=())
    with pytest.raises(ContractError):
        scenario(triggers=("__import__('os')",))


def test_timezone_equivalence():
    assert build(as_of="2026-10-21T16:01:00-04:00") == build()


def test_input_bounds():
    with pytest.raises(ContractError):
        build(scenarios=tuple(scenario(key=f"s{i}") for i in range(13)))
    with pytest.raises(ContractError):
        scenario(triggers=tuple(Condition("price", "gt", 1, "USD") for _ in range(17)))


def test_canonical_session_needs_calendar_owner_evidence():
    p = build(market_state=state(), market_state_receipt=receipt(), expected_market_session=None)
    assert p["canonical_market"]["status"] == "session_unverified"
    assert p["canonical_market"]["verdict"] is None


def test_stale_flag_from_saved_metadata_is_not_enough_to_claim_current():
    old = receipt(observed_at="2026-10-09T20:00:00Z", received_at="2026-10-09T20:00:01Z",
                  available_at="2026-10-09T20:00:02Z", valid_until="2026-10-23T00:00:00Z")
    p = build(market_state=state(asof="2026-10-09",freshness={"stale":False}),market_state_receipt=old)
    assert p["canonical_market"]["status"] == "stale"
    assert p["canonical_market"]["verdict"] is None


@pytest.mark.parametrize("changes", [{"freshness":{"any_input_stale":True}},
    {"input_vintages":{"credit":{"stale":True}}}])
def test_nested_input_degradation_is_preserved(changes):
    p = build(market_state=state(**changes), market_state_receipt=receipt())
    assert p["canonical_market"]["status"] == "degraded"


def test_incomplete_market_session_is_not_a_completed_close():
    p=build(market_state=state(),market_state_receipt=receipt(),expected_market_session="2026-10-20")
    assert p["canonical_market"]["status"] == "session_completion_unverified"


def test_calendar_settle_buffer_is_not_a_claim_that_the_session_is_unfinished():
    p=build(market_state=state(),market_state_receipt=receipt(),expected_market_session="2026-10-20",canonical_session_complete=True)
    assert p["canonical_market"]["status"] == "current"


def test_other_market_cannot_be_labeled_us_context():
    with pytest.raises(ContractError):
        build(market_state=state(market="hk"), market_state_receipt=receipt())


def test_future_written_rule_is_not_retroactively_known():
    with pytest.raises(ContractError, match="definition was unavailable"):
        build(scenarios=(scenario(definition_available_at="2026-10-21T20:02:00Z"),))


def test_rule_available_at_cutoff_is_known_and_revision_changes_identity():
    p=build(scenarios=(scenario(definition_available_at=ASOF),))
    assert p["scenarios"][0]["status"] == "conditions_met"
    assert build()["context_digest"] != build(scenarios=(scenario(definition_ref="fixture:rule-v2"),))["context_digest"]


def test_rule_subject_is_not_inferred_from_current_price():
    p=build(scenarios=(scenario(subject="QQQ:XNAS"),))
    assert p["scenarios"][0]["status"] == "subject_mismatch"
    assert p["scenarios"][0]["triggers"] == []


@pytest.mark.parametrize("changes", [{"definition_available_at":"2026-10-21"},
    {"definition_available_at":"2026-10-21T20:05:00Z"}, {"definition_ref":""}])
def test_rule_definition_contract(changes):
    with pytest.raises(ContractError): scenario(**changes)


def test_public_explanation_retains_conditions_counterevidence_and_known_clocks():
    p=public_projection(build())
    assert p["observations"][0]["observed_at"] == "2026-10-21T20:00:00Z"
    assert p["scenarios"][0]["triggers"][0]["threshold"] == 773
    assert p["scenarios"][0]["counterevidence"][0]["key"] == "breadth"
    assert "definition_ref" not in json.dumps(p)
    assert "internal://" not in json.dumps(p)


def test_future_availability_metadata_is_not_published_as_past_knowledge():
    p=public_projection(build(as_of="2026-10-21T20:00:01Z"))
    row=p["observations"][0]
    assert row["value"] is None
    assert row["observed_at"] is None and row["available_at"] is None


def test_public_explanation_lists_do_not_alias_internal_packet():
    raw=build(); exposed=public_projection(raw)
    exposed["scenarios"][0]["triggers"][0]["threshold"]=999
    exposed["scenarios"][0]["counterevidence"][0]["status"]="current"
    assert raw["scenarios"][0]["triggers"][0]["threshold"]==773
    assert raw["scenarios"][0]["counterevidence"][0]["status"]=="missing"
    assert public_projection(raw)["scenarios"][0]["triggers"][0]["threshold"]==773
