import copy
import hashlib
import json

import pytest

from engine.prophet_entry_policy import (
    EntryPolicyContractError,
    GAP_MAX_MOVE_FROM_OPEN_ATR,
    GAP_MAX_OPEN_ATR,
    GAP_MAX_SESSION_MOVE_ATR,
    GAP_POLICY_ERA,
    GAP_POLICY_VERSION,
    LIQUIDITY_MAX_FULL_SPREAD_BPS,
    LIQUIDITY_MAX_NBBO_AGE_SECONDS,
    LIQUIDITY_POLICY_ERA,
    LIQUIDITY_POLICY_VERSION,
    RISK_ATR_CEILING,
    RISK_POLICY_ERA,
    RISK_POLICY_VERSION,
    SESSION_POLICY_ERA,
    SESSION_POLICY_VERSION,
    evaluate_gap_velocity,
    evaluate_liquidity_fillability,
    evaluate_risk_ceiling,
    evaluate_session_eligibility,
)

from engine.prophet_strategy_definition import (
    ENTRY_POLICY_VERSION,
    SCHEMA,
    STRATEGY_ID,
    StrategyDefinitionContractError,
    build_early_leadership_sector_rotation_definition,
    validate_strategy_definition,
)


def test_first_strategy_definition_is_stable_complete_and_authority_false():
    left = build_early_leadership_sector_rotation_definition()
    right = build_early_leadership_sector_rotation_definition()

    assert left == right
    assert left["schema"] == SCHEMA
    assert left["strategy_id"] == STRATEGY_ID
    assert left["strategy_definition_id"].startswith("psd:")
    assert left["scientific_status"] == "CONTROL_ONLY"
    assert left["authority_tier"] == "SHADOW_ONLY"
    assert left["horizons"]["primary"] == "2_15_SESSIONS"
    assert left["entry_and_availability_requirements"]["entry_policy_version"] == ENTRY_POLICY_VERSION
    assert left["benchmark_controls_costs_and_evaluation"]["promotion_claim"] == "NONE"
    assert all(value is False for value in left["authority"].values())


def test_strategy_definition_cannot_widen_b1_or_force_a_security():
    payload = build_early_leadership_sector_rotation_definition()
    admission = payload["setup_and_candidate_admission"]
    assert admission["candidate_source"] == "EXISTING_CANONICAL_B1_ONLY"
    assert admission["may_create_candidate_episode"] is False
    assert admission["may_widen_population"] is False
    assert admission["may_force_named_security"] is False


def test_strategy_definition_does_not_mint_b4_authority():
    payload = build_early_leadership_sector_rotation_definition()
    entry = payload["entry_and_availability_requirements"]
    assert entry["availability_owner_schema"] == "prophet.entry_availability/v1"
    assert entry["definition_itself_may_set_availability"] is False
    assert payload["residual_opportunity_test"]["decision"] == "DEFER_TO_B4"
    assert payload["authority"]["can_compute_b4_availability"] is False
    assert payload["authority"]["can_change_entry_open"] is False


def test_strategy_definition_fail_closed_policy_is_explicit():
    payload = build_early_leadership_sector_rotation_definition()
    assert payload["market_and_regime_eligibility"]["missing_required_owner_fact"] == "ABSTAIN"
    assert payload["entry_and_availability_requirements"]["missing_or_stale_required_fact"] == "UNAVAILABLE_DATA"
    assert payload["price_incorporation_test"]["past_owner_chase_boundary"] == "RAN_DONT_CHASE"
    assert payload["entry_and_availability_requirements"]["owner_confluence_gate_may_be_waived"] is False


def test_strategy_definition_rejects_semantic_or_authority_mutation():
    payload = build_early_leadership_sector_rotation_definition()
    payload["authority"]["can_rank"] = True
    with pytest.raises(StrategyDefinitionContractError):
        validate_strategy_definition(payload)

    payload = build_early_leadership_sector_rotation_definition()
    payload["setup_and_candidate_admission"]["may_widen_population"] = True
    with pytest.raises(StrategyDefinitionContractError):
        validate_strategy_definition(payload)


def test_strategy_definition_rejects_content_hash_mismatch():
    payload = build_early_leadership_sector_rotation_definition()
    payload["strategy_definition_id"] = "psd:" + "0" * 64
    with pytest.raises(StrategyDefinitionContractError):
        validate_strategy_definition(payload)


def test_strategy_definition_is_deep_copy_safe():
    first = build_early_leadership_sector_rotation_definition()
    mutated = copy.deepcopy(first)
    mutated["supported_markets_and_instruments"][0]["market"] = "OTHER"
    second = build_early_leadership_sector_rotation_definition()
    assert second == first

# ---------------------------------------------------------------------------
# B4 first vertical: accepted strategy definition + canonical B3 identity +
# deterministic owner facts -> strategy/horizon-specific Availability.
# These tests intentionally ride the already-registered strategy-definition CI
# owner so B4 does not race the active shared legacy-job manifest carrier.

from dataclasses import dataclass

from engine.prophet_candidate_state import project_candidate_states
from engine.prophet_entry_availability import (
    EntryAvailabilityContractError,
    evaluate_entry_availability,
    validate_entry_availability,
)
from engine.prophet_live.interval import ADJUSTED, UNADJUSTED

_B4_GEN = "peg:" + "a" * 64


def _b4_cid(label="1", identity_epoch="epoch_0"):
    digest = label.encode("utf-8").hex().ljust(24, "0")[:24]
    return f"pe:SEC:US-XNAS-AAPL:{identity_epoch}:sa:{digest}:1"


@dataclass(frozen=True)
class _B4Gen:
    episodes: tuple


@dataclass(frozen=True)
class _B4Snap:
    generation_id: str
    generation: _B4Gen


def _b4_episode(state="ACTIVE", terminal_reason=None):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": _b4_cid(),
        "security_id": "SEC:US-XNAS-AAPL",
        "company_id": "ISS:US-XNAS-AAPL",
        "identity_epoch": "epoch_0",
        "episode_state": state,
        "terminal_reason": terminal_reason,
        "superseded_by": None,
        "opened_at": "2026-09-17T20:00:00Z",
        "opened_session": "2026-09-17",
        "correction_state": "current",
    }


def _b4_projection(
    state="ACTIVE",
    terminal_reason=None,
    generated_at="2026-09-18T19:30:00Z",
):
    return project_candidate_states(
        _B4Snap(_B4_GEN, _B4Gen((_b4_episode(state, terminal_reason),))),
        market_session="2026-09-18",
        generated_at=generated_at,
    )


def _b4_facts():
    return {
        "decision_at": "2026-09-18T19:30:08Z",
        "market_session": "2026-09-18",
        "quote": {
            "price": 42.70,
            "asof": "2026-09-18T19:30:00Z",
            "freshness": "FRESH",
            "basis_version": "adjusted:v7",
            "source_receipt": "sha256:" + "1" * 64,
        },
        "geometry": {
            "owner_status": "buy_now",
            "zone_low": 41.80,
            "zone_high": 43.25,
            "chase_above": 43.60,
            "invalidation_price": 40.95,
            "basis_version": "adjusted:v7",
            "source_receipt": "sha256:" + "2" * 64,
        },
        "deterministic_gates": {
            "owner_confluence": "PASS",
            "risk_ceiling": "PASS",
            "liquidity_fillability": "PASS",
            "gap_velocity": "PASS",
            "source_health": "PASS",
            "corporate_action_basis": "RESOLVED",
            "session_eligibility": "PASS",
            "event_status": "ACTIVE",
            "structural_invalidation": "CLEAR",
        },
        "metric_inputs": {
            "first_trigger_price": 41.72,
            "anchor_price": 42.10,
            "atr": 1.15,
        },
        "source_receipts": ["b3:source-owner-v1"],
    }


def _b4_evaluate(p=None, f=None, strategy=None):
    return evaluate_entry_availability(
        p or _b4_projection(),
        episode_id=_b4_cid(),
        strategy_definition=strategy or build_early_leadership_sector_rotation_definition(),
        facts=f or _b4_facts(),
    )


def _b4_rehash(payload):
    material = {key: value for key, value in payload.items() if key != "availability_id"}
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    payload["availability_id"] = "pea:" + hashlib.sha256(encoded).hexdigest()


def test_b4_entry_open_binds_canonical_identity_strategy_horizon_and_current_facts():
    out = _b4_evaluate()
    assert out["schema"] == "prophet.entry_availability/v1"
    assert out["state"] == "ENTRY_OPEN"
    assert out["entry_open"] is True
    assert out["episode_id"] == _b4_cid()
    assert out["candidate_generation_id"] == _B4_GEN
    assert out["security_id"] == "SEC:US-XNAS-AAPL"
    assert out["identity_epoch"] == "epoch_0"
    assert out["strategy_id"] == "EARLY_LEADERSHIP_SECTOR_ROTATION"
    assert out["horizon"] == "2_15_SESSIONS"
    assert out["horizon_role"] == "new_entry"
    assert out["blockers"] == []
    assert out["quote_age_seconds"] == 8
    assert out["zone"] == {"low": 41.8, "high": 43.25, "basis": "adjusted:v7"}
    assert out["current_price_basis"] == "adjusted:v7"
    assert out["availability_id"].startswith("pea:")
    validate_entry_availability(out)


def test_b4_rejects_future_candidate_projection_before_availability_evaluation():
    future_projection = _b4_projection(generated_at="2026-09-18T21:00:00Z")
    with pytest.raises(
        EntryAvailabilityContractError,
        match="candidate_projection.generated_at cannot be after decision_at",
    ):
        _b4_evaluate(p=future_projection)


def test_b4_stale_quote_ambiguous_basis_or_unknown_required_fact_fail_closed():
    stale = _b4_facts()
    stale["quote"]["freshness"] = "STALE"
    out = _b4_evaluate(f=stale)
    assert out["state"] == "UNAVAILABLE_DATA"
    assert "QUOTE_STALE" in out["blockers"]

    basis = _b4_facts()
    basis["deterministic_gates"]["corporate_action_basis"] = "AMBIGUOUS"
    out = _b4_evaluate(f=basis)
    assert out["state"] == "UNAVAILABLE_DATA"
    assert "CORPORATE_ACTION_BASIS_AMBIGUOUS" in out["blockers"]

    missing = _b4_facts()
    missing["deterministic_gates"]["liquidity_fillability"] = "UNKNOWN"
    out = _b4_evaluate(f=missing)
    assert out["state"] == "UNAVAILABLE_DATA"
    assert "LIQUIDITY_FILLABILITY_UNKNOWN" in out["blockers"]


def test_b4_optional_structural_overlay_unknown_does_not_deadlock_owner_stop():
    optional_overlay = _b4_facts()
    optional_overlay["deterministic_gates"]["structural_invalidation"] = "UNKNOWN"
    out = _b4_evaluate(f=optional_overlay)
    assert out["state"] == "ENTRY_OPEN"
    assert "STRUCTURAL_INVALIDATION_UNKNOWN" not in out["blockers"]

    numeric_stop = _b4_facts()
    numeric_stop["deterministic_gates"]["structural_invalidation"] = "UNKNOWN"
    numeric_stop["quote"]["price"] = numeric_stop["geometry"]["invalidation_price"]
    out = _b4_evaluate(f=numeric_stop)
    assert out["state"] == "INVALIDATED"
    assert "STRUCTURAL_INVALIDATION_BREACHED" in out["blockers"]


def test_b4_distinct_incumbent_price_families_require_owner_basis_resolution():
    # Production law keeps live vendor prints raw while entry geometry is computed
    # on the adjusted store.  A resolved incumbent basis audit makes those two
    # explicit families comparable without laundering the tape into an invented
    # adjusted quote.
    resolved = _b4_facts()
    resolved["quote"]["basis_version"] = UNADJUSTED
    resolved["geometry"]["basis_version"] = ADJUSTED
    out = _b4_evaluate(f=resolved)
    assert out["state"] == "ENTRY_OPEN"
    assert out["current_price_basis"] == UNADJUSTED
    assert out["zone"]["basis"] == ADJUSTED

    ambiguous = copy.deepcopy(resolved)
    ambiguous["deterministic_gates"]["corporate_action_basis"] = "AMBIGUOUS"
    out = _b4_evaluate(f=ambiguous)
    assert out["state"] == "UNAVAILABLE_DATA"
    assert "CORPORATE_ACTION_BASIS_AMBIGUOUS" in out["blockers"]


def test_b4_owner_chase_and_zone_relationship_route_without_rank_feedback():
    ran = _b4_facts()
    ran["quote"]["price"] = 44.00
    out = _b4_evaluate(f=ran)
    assert out["state"] == "RAN_DONT_CHASE"
    assert "PAST_OWNER_CHASE_BOUNDARY" in out["blockers"]

    wait = _b4_facts()
    wait["quote"]["price"] = 43.40
    out = _b4_evaluate(f=wait)
    assert out["state"] == "WAIT_PULLBACK"
    assert "CURRENT_PRICE_ABOVE_OWNER_ZONE" in out["blockers"]


def test_b4_owner_confluence_and_known_deterministic_blockers_cannot_be_waived():
    f = _b4_facts()
    f["deterministic_gates"]["owner_confluence"] = "FAIL"
    out = _b4_evaluate(f=f)
    assert out["state"] == "APPROACHING_ENTRY"
    assert "OWNER_CONFLUENCE_NOT_PASSED" in out["blockers"]

    cases = {
        "risk_ceiling": "RISK_TO_INVALIDATION_ABOVE_LANE_CEILING",
        "liquidity_fillability": "LIQUIDITY_FILLABILITY_FAILED",
        "gap_velocity": "GAP_VELOCITY_PROTECTION_FAILED",
        "session_eligibility": "SESSION_NOT_ELIGIBLE",
    }
    for key, reason in cases.items():
        f = _b4_facts()
        f["deterministic_gates"][key] = "FAIL"
        out = _b4_evaluate(f=f)
        assert out["state"] == "NOT_READY"
        assert reason in out["blockers"]


def test_b4_terminal_retracted_or_structurally_breached_inputs_are_invalidated():
    assert _b4_evaluate(p=_b4_projection("EXPIRED", "expired"))["state"] == "INVALIDATED"

    retracted = _b4_facts()
    retracted["deterministic_gates"]["event_status"] = "RETRACTED"
    assert _b4_evaluate(f=retracted)["state"] == "INVALIDATED"

    breached = _b4_facts()
    breached["deterministic_gates"]["structural_invalidation"] = "BREACHED"
    assert _b4_evaluate(f=breached)["state"] == "INVALIDATED"


def test_b4_owner_status_routes_wait_states_without_maturity_or_intelligence_feedback():
    expected = {
        "buy_soon": "APPROACHING_ENTRY",
        "await_confluence": "APPROACHING_ENTRY",
        "watch": "APPROACHING_ENTRY",
        "wait_pullback": "WAIT_PULLBACK",
        "extended": "WAIT_PULLBACK",
        "topping": "WAIT_PULLBACK",
        "hold": "WAIT_PULLBACK",
        "bounce_wait": "WAIT_PULLBACK",
        "exit": "NOT_READY",
        "avoid": "NOT_READY",
        "blocked": "NOT_READY",
    }
    for owner_status, state in expected.items():
        f = _b4_facts()
        f["geometry"]["owner_status"] = owner_status
        assert _b4_evaluate(f=f)["state"] == state


def test_b4_prohibited_score_theme_llm_or_maturity_inputs_are_rejected():
    for poisoned in (
        {"theme_strength": 0.99},
        {"intelligence_score": 100},
        {"llm_output": "BUY"},
        {"maturity_score": 1.0},
    ):
        f = _b4_facts()
        f.update(poisoned)
        with pytest.raises(EntryAvailabilityContractError, match="fields are not closed"):
            _b4_evaluate(f=f)


def test_b4_strategy_authority_mutation_cannot_mint_availability():
    strategy = build_early_leadership_sector_rotation_definition()
    strategy["authority"]["can_compute_b4_availability"] = True
    with pytest.raises(Exception):
        _b4_evaluate(strategy=strategy)


def test_b4_availability_identity_detects_mutation():
    out = _b4_evaluate()
    tampered = copy.deepcopy(out)
    tampered["state"] = "WAIT_PULLBACK"
    tampered["entry_open"] = False
    with pytest.raises(EntryAvailabilityContractError, match="availability_id mismatch"):
        validate_entry_availability(tampered)


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("strategy_definition_id", "psd:" + "0" * 64),
        ("strategy_id", "OTHER_STRATEGY"),
        ("strategy_version", "999"),
        ("horizon", "99_SESSIONS"),
        ("horizon_role", "hold_only"),
        ("entry_policy_version", "evil-v999"),
    ),
)
def test_b4_validator_rejects_rehashed_strategy_identity_mutation(field, value):
    tampered = copy.deepcopy(_b4_evaluate())
    tampered[field] = value
    _b4_rehash(tampered)
    with pytest.raises(
        EntryAvailabilityContractError,
        match=f"availability {field} diverges from accepted strategy definition",
    ):
        validate_entry_availability(tampered)


def _session_policy(decision_at: str, market_session: str):
    return evaluate_session_eligibility(
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        decision_at=decision_at,
        market_session=market_session,
    )


def test_b4_session_policy_passes_only_inside_actual_rth_window():
    out = _session_policy("2026-09-22T14:00:00Z", "2026-09-22")  # 10:00 ET
    assert out["verdict"] == "PASS"
    assert out["session_phase"] == "RTH"
    assert out["reason"] == "INSIDE_ACTUAL_RTH_WINDOW"
    assert out["session_open"].endswith("09:30:00-04:00")
    assert out["session_close"].endswith("16:00:00-04:00")
    assert out["extended_hours_eligible"] is False
    assert out["session_policy_version"] == SESSION_POLICY_VERSION
    assert out["session_policy_era"] == SESSION_POLICY_ERA
    assert out["calendar_owner"] == "lib.nyse_calendar.is_session"
    assert out["execution_window_owner"] == "engine.prophet_entry_policy._execution_session_window_et"
    assert out["execution_schedule_source"] == "NYSE_HOLIDAYS_AND_TRADING_HOURS_2026"
    assert out["execution_schedule_verified_on"] == "2026-09-22"
    assert out["supported_session_years"] == [2026]
    assert out["early_close_dates"] == ["2026-11-27", "2026-12-24"]
    assert out["policy_receipt"].startswith("pep:")
    assert out["session_receipt"].startswith("pes:")
    assert out["fact_receipt"].startswith("pepf:")
    assert out == _session_policy("2026-09-22T14:00:00Z", "2026-09-22")


def test_b4_session_policy_fails_closed_before_and_at_after_rth():
    pre = _session_policy("2026-09-22T13:29:59Z", "2026-09-22")
    assert (pre["verdict"], pre["session_phase"], pre["reason"]) == (
        "FAIL", "PREMARKET", "PREMARKET_NOT_ELIGIBLE_V1"
    )

    close = _session_policy("2026-09-22T20:00:00Z", "2026-09-22")
    assert (close["verdict"], close["session_phase"], close["reason"]) == (
        "FAIL", "AFTER_HOURS", "POST_RTH_NOT_ELIGIBLE_V1"
    )


def test_b4_session_policy_uses_actual_early_close_not_a_hardcoded_1600():
    # 2026-11-27 is the Friday after Thanksgiving: actual close is 13:00 ET.
    before = _session_policy("2026-11-27T17:59:59Z", "2026-11-27")
    assert before["verdict"] == "PASS"
    assert before["session_close"].endswith("13:00:00-05:00")

    at_close = _session_policy("2026-11-27T18:00:00Z", "2026-11-27")
    assert at_close["verdict"] == "FAIL"
    assert at_close["session_phase"] == "AFTER_HOURS"

    christmas_eve = _session_policy("2026-12-24T18:00:00Z", "2026-12-24")  # 13:00 ET
    assert christmas_eve["verdict"] == "FAIL"
    assert christmas_eve["session_close"].endswith("13:00:00-05:00")


def test_b4_session_policy_rejects_non_session_and_wrong_session_clocks():
    holiday = _session_policy("2026-11-26T15:00:00Z", "2026-11-26")
    assert (holiday["verdict"], holiday["session_phase"], holiday["reason"]) == (
        "FAIL", "NON_SESSION", "NON_SESSION_DATE"
    )
    assert holiday["session_open"] is None
    assert holiday["session_close"] is None

    july_observed = _session_policy("2026-07-03T15:00:00Z", "2026-07-03")
    assert (july_observed["verdict"], july_observed["session_phase"]) == ("FAIL", "NON_SESSION")
    assert july_observed["session_close"] is None

    wrong = _session_policy("2026-09-22T14:00:00Z", "2026-09-23")
    assert (wrong["verdict"], wrong["session_phase"], wrong["reason"]) == (
        "FAIL", "WRONG_SESSION", "DECISION_NOT_IN_MARKET_SESSION_DATE"
    )


def test_b4_session_policy_requires_aware_clock_and_accepted_strategy_definition():
    with pytest.raises(EntryPolicyContractError, match="offset-aware"):
        _session_policy("2026-09-22T10:00:00", "2026-09-22")

    mutated = build_early_leadership_sector_rotation_definition()
    mutated["strategy_definition_id"] = "psd:" + "0" * 64
    with pytest.raises(StrategyDefinitionContractError):
        evaluate_session_eligibility(
            strategy_definition=mutated,
            decision_at="2026-09-22T14:00:00Z",
            market_session="2026-09-22",
        )

    with pytest.raises(EntryPolicyContractError, match="outside NYSE_RTH_2026"):
        _session_policy("2027-01-04T15:00:00Z", "2027-01-04")


def _risk_policy(current_price=100.0, invalidation_price=97.0, atr=2.0):
    return evaluate_risk_ceiling(
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        current_price=current_price,
        invalidation_price=invalidation_price,
        atr=atr,
    )


def test_b4_risk_policy_uses_structural_atr_risk_not_universal_percent():
    out = _risk_policy(current_price=100.0, invalidation_price=97.0, atr=2.0)
    assert out["gate"] == "risk_ceiling"
    assert out["verdict"] == "PASS"
    assert out["reason"] == "STRUCTURAL_RISK_WITHIN_ATR_CEILING"
    assert out["risk_to_invalidation_atr"] == 1.5
    assert out["risk_to_invalidation_pct"] == 3.0
    assert out["risk_atr_ceiling"] == 2.0 == RISK_ATR_CEILING
    assert out["horizon"] == "2_15_SESSIONS"
    assert out["horizon_role"] == "new_entry"
    assert out["scientific_status"] == "CONTROL_ONLY"
    assert out["authority_tier"] == "SHADOW_ONLY"
    assert out["risk_policy_version"] == RISK_POLICY_VERSION
    assert out["risk_policy_era"] == RISK_POLICY_ERA
    assert out["threshold_status"] == "INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED"
    assert out["calibration_requirement"] == "PROSPECTIVE_OR_OOS_SAME_TAPE_WITH_COSTS"
    assert all(value is False for value in out["authority"].values())
    assert out["policy_receipt"].startswith("pep:")
    assert out["fact_receipt"].startswith("pepf:")
    assert out == _risk_policy(current_price=100.0, invalidation_price=97.0, atr=2.0)


def test_b4_risk_policy_boundary_is_two_atr_and_above_it_fails():
    boundary = _risk_policy(current_price=100.0, invalidation_price=96.0, atr=2.0)
    assert boundary["risk_to_invalidation_atr"] == 2.0
    assert boundary["verdict"] == "PASS"

    above = _risk_policy(current_price=100.0, invalidation_price=95.9, atr=2.0)
    assert above["risk_to_invalidation_atr"] == 2.05
    assert above["verdict"] == "FAIL"
    assert above["reason"] == "STRUCTURAL_RISK_ABOVE_ATR_CEILING"


def test_b4_risk_policy_fails_when_structural_invalidation_is_not_below_price():
    at_stop = _risk_policy(current_price=100.0, invalidation_price=100.0, atr=2.0)
    assert at_stop["verdict"] == "FAIL"
    assert at_stop["reason"] == "STRUCTURAL_INVALIDATION_NOT_BELOW_PRICE"
    assert at_stop["risk_to_invalidation_atr"] == 0.0

    above_price = _risk_policy(current_price=100.0, invalidation_price=101.0, atr=2.0)
    assert above_price["verdict"] == "FAIL"
    assert above_price["reason"] == "STRUCTURAL_INVALIDATION_NOT_BELOW_PRICE"


@pytest.mark.parametrize(
    ("field", "value"),
    (("current_price", 0.0), ("invalidation_price", -1.0), ("atr", 0.0), ("atr", float("nan"))),
)
def test_b4_risk_policy_refuses_unprovable_numeric_inputs(field, value):
    kwargs = {"current_price": 100.0, "invalidation_price": 97.0, "atr": 2.0}
    kwargs[field] = value
    with pytest.raises(EntryPolicyContractError, match=field):
        _risk_policy(**kwargs)


def test_b4_risk_policy_requires_the_accepted_strategy_identity():
    mutated = build_early_leadership_sector_rotation_definition()
    mutated["strategy_definition_id"] = "psd:" + "0" * 64
    with pytest.raises(StrategyDefinitionContractError):
        evaluate_risk_ceiling(
            strategy_definition=mutated,
            current_price=100.0,
            invalidation_price=97.0,
            atr=2.0,
        )



def _liquidity_policy(
    bid_price=99.95,
    ask_price=100.05,
    decision_at="2026-09-22T14:31:00Z",
    nbbo_asof="2026-09-22T14:30:00Z",
    nbbo_source="polygon_lastQuote",
    source_license="vendor_terms_personal_use",
):
    return evaluate_liquidity_fillability(
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        decision_at=decision_at,
        bid_price=bid_price,
        ask_price=ask_price,
        nbbo_asof=nbbo_asof,
        nbbo_source=nbbo_source,
        source_license=source_license,
    )


def test_b4_liquidity_policy_is_shadow_only_source_bound_and_deterministic():
    out = _liquidity_policy()
    assert out["gate"] == "liquidity_fillability"
    assert out["verdict"] == "PASS"
    assert out["reason"] == "NBBO_FRESH_AND_WITHIN_SPREAD_CONTROL"
    assert out["full_spread_bps"] == pytest.approx(10.0)
    assert out["half_spread_bps"] == pytest.approx(5.0)
    assert out["nbbo_age_seconds"] == 60.0
    assert out["max_full_spread_bps"] == LIQUIDITY_MAX_FULL_SPREAD_BPS == 50.0
    assert out["max_nbbo_age_seconds"] == LIQUIDITY_MAX_NBBO_AGE_SECONDS == 300.0
    assert out["scientific_status"] == "CONTROL_ONLY"
    assert out["authority_tier"] == "SHADOW_ONLY"
    assert out["liquidity_policy_version"] == LIQUIDITY_POLICY_VERSION
    assert out["liquidity_policy_era"] == LIQUIDITY_POLICY_ERA
    assert out["threshold_status"] == "INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED"
    assert out["capacity_status"] == "NOT_MODELED_IN_V1"
    assert all(value is False for value in out["authority"].values())
    assert out == _liquidity_policy()


def test_b4_liquidity_policy_spread_and_freshness_boundaries_fail_closed():
    spread_boundary = _liquidity_policy(bid_price=99.75, ask_price=100.25)
    assert spread_boundary["full_spread_bps"] == 50.0
    assert spread_boundary["verdict"] == "PASS"

    too_wide = _liquidity_policy(bid_price=99.74, ask_price=100.26)
    assert too_wide["verdict"] == "FAIL"
    assert too_wide["reason"] == "NBBO_SPREAD_ABOVE_FILLABILITY_CONTROL"

    stale = _liquidity_policy(
        decision_at="2026-09-22T14:35:00Z",
        nbbo_asof="2026-09-22T14:29:59Z",
    )
    assert stale["verdict"] == "FAIL"
    assert stale["reason"] == "NBBO_TOO_STALE_FOR_FILLABILITY_CONTROL"


@pytest.mark.parametrize(
    ("field", "value"),
    (("bid_price", 0.0), ("ask_price", -1.0), ("ask_price", float("nan"))),
)
def test_b4_liquidity_policy_refuses_unprovable_prices(field, value):
    kwargs = {"bid_price": 99.95, "ask_price": 100.05}
    kwargs[field] = value
    with pytest.raises(EntryPolicyContractError, match=field):
        _liquidity_policy(**kwargs)


def test_b4_liquidity_policy_requires_real_book_time_source_and_rights():
    with pytest.raises(EntryPolicyContractError, match="ask_price must be >"):
        _liquidity_policy(bid_price=100.0, ask_price=100.0)
    with pytest.raises(EntryPolicyContractError, match="nbbo_asof cannot be after"):
        _liquidity_policy(
            decision_at="2026-09-22T14:30:00Z",
            nbbo_asof="2026-09-22T14:30:01Z",
        )
    with pytest.raises(EntryPolicyContractError, match="nbbo_source"):
        _liquidity_policy(nbbo_source="other")
    with pytest.raises(EntryPolicyContractError, match="source_license"):
        _liquidity_policy(source_license="UNKNOWN")


def _gap_policy(current_price=100.5, day_open=100.0, prev_close=99.0, atr=2.0):
    return evaluate_gap_velocity(
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        current_price=current_price,
        day_open=day_open,
        prev_close=prev_close,
        atr=atr,
    )


def test_b4_gap_velocity_policy_is_shadow_only_atr_normalized_and_deterministic():
    out = _gap_policy()
    assert out["gate"] == "gap_velocity"
    assert out["verdict"] == "PASS"
    assert out["reason"] == "GAP_AND_VELOCITY_WITHIN_ATR_CONTROL"
    assert out["open_gap_atr"] == 0.5
    assert out["move_from_open_atr"] == 0.25
    assert out["session_move_atr"] == 0.75
    assert out["max_open_gap_atr"] == GAP_MAX_OPEN_ATR == 1.5
    assert out["max_move_from_open_atr"] == GAP_MAX_MOVE_FROM_OPEN_ATR == 1.0
    assert out["max_session_move_atr"] == GAP_MAX_SESSION_MOVE_ATR == 1.5
    assert out["scientific_status"] == "CONTROL_ONLY"
    assert out["authority_tier"] == "SHADOW_ONLY"
    assert out["gap_policy_version"] == GAP_POLICY_VERSION
    assert out["gap_policy_era"] == GAP_POLICY_ERA
    assert out["threshold_status"] == "INITIAL_OPERATION_CONSTANT_NOT_CALIBRATED"
    assert all(value is False for value in out["authority"].values())
    assert out == _gap_policy()


def test_b4_gap_velocity_policy_blocks_each_control_boundary_only_when_exceeded():
    open_boundary = _gap_policy(current_price=102.0, day_open=102.0, prev_close=99.0, atr=2.0)
    assert open_boundary["open_gap_atr"] == 1.5
    assert open_boundary["verdict"] == "PASS"

    open_fail = _gap_policy(current_price=102.1, day_open=102.1, prev_close=99.0, atr=2.0)
    assert open_fail["verdict"] == "FAIL"
    assert open_fail["reason"] == "OPEN_GAP_ABOVE_ATR_CONTROL"

    velocity_fail = _gap_policy(current_price=102.01, day_open=100.0, prev_close=100.0, atr=2.0)
    assert velocity_fail["verdict"] == "FAIL"
    assert velocity_fail["reason"] == "MOVE_FROM_OPEN_ABOVE_ATR_CONTROL"

    total_fail = _gap_policy(current_price=102.51, day_open=100.5, prev_close=99.5, atr=2.0)
    assert total_fail["open_gap_atr"] == 0.5
    assert total_fail["move_from_open_atr"] == pytest.approx(1.005)
    assert total_fail["session_move_atr"] == pytest.approx(1.505)
    assert total_fail["reason"] == "MOVE_FROM_OPEN_ABOVE_ATR_CONTROL"


def test_b4_gap_velocity_policy_can_reach_session_move_guard_independently():
    out = _gap_policy(current_price=102.1, day_open=100.2, prev_close=99.0, atr=2.0)
    assert out["open_gap_atr"] == 0.6
    assert out["move_from_open_atr"] == 0.95
    assert out["session_move_atr"] == 1.55
    assert out["verdict"] == "FAIL"
    assert out["reason"] == "SESSION_MOVE_ABOVE_ATR_CONTROL"


@pytest.mark.parametrize(
    ("field", "value"),
    (("current_price", 0.0), ("day_open", -1.0), ("prev_close", 0.0), ("atr", float("nan"))),
)
def test_b4_gap_velocity_policy_refuses_unprovable_numeric_inputs(field, value):
    kwargs = {"current_price": 100.5, "day_open": 100.0, "prev_close": 99.0, "atr": 2.0}
    kwargs[field] = value
    with pytest.raises(EntryPolicyContractError, match=field):
        _gap_policy(**kwargs)


def test_b4_new_policy_owners_require_the_accepted_strategy_identity():
    mutated = build_early_leadership_sector_rotation_definition()
    mutated["strategy_definition_id"] = "psd:" + "0" * 64
    with pytest.raises(StrategyDefinitionContractError):
        evaluate_liquidity_fillability(
            strategy_definition=mutated,
            decision_at="2026-09-22T14:31:00Z",
            bid_price=99.95,
            ask_price=100.05,
            nbbo_asof="2026-09-22T14:30:00Z",
            nbbo_source="polygon_lastQuote",
            source_license="vendor_terms_personal_use",
        )
    with pytest.raises(StrategyDefinitionContractError):
        evaluate_gap_velocity(
            strategy_definition=mutated,
            current_price=100.5,
            day_open=100.0,
            prev_close=99.0,
            atr=2.0,
        )
