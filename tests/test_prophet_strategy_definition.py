import copy
import hashlib
import json

import pytest

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

# ---------------------------------------------------------------------------
# B4 runtime owner-fact adapter: canonical identity -> incumbent source facts.

from datetime import date

from engine.prophet_entry_availability_sources import (
    RuntimeOwnerFactError,
    compose_runtime_owner_facts,
    evaluate_runtime_entry_availability,
)


class _B4Aliases:
    def __init__(self, symbol="UNIT", *, reverse="SEC:US-XNAS-AAPL"):
        self.symbol = symbol
        self.reverse = reverse

    def vendor_symbol_for(self, vendor, security_id, on):
        assert vendor == "store"
        assert security_id == "SEC:US-XNAS-AAPL"
        assert on == date(2026, 9, 18)
        return self.symbol

    def resolve(self, vendor, symbol, on):
        assert vendor == "store"
        assert symbol == self.symbol
        assert on == date(2026, 9, 18)
        return self.reverse


def _b4_runtime_sources(symbol="UNIT"):
    quote = {
        "price": 42.70,
        "quote_ts": "2026-09-18T19:30:00+00:00",
        "quote_ts_synthetic": False,
        "source": "polygon",
        "price_basis": "trade",
        "delay_min": 0.1,
        "prev_close": 42.10,
    }
    live = {
        "schema": "prophet_live.states/v1",
        "meta": {
            "session_et": "2026-09-18",
            "pass_ts": "2026-09-18T19:30:08Z",
        },
        "states": {
            symbol: {
                "state": "forming",
                "price": 42.70,
                "quote_age_min": 0.1,
                "basis_status": "RESOLVED",
                "basis_receipt": "sha256:" + "9" * 64,
            }
        },
    }
    entry = {
        symbol: {
            "entry_signal": {
                "status": "buy_now",
                "buy_zone": {"low": 41.80, "high": 43.25},
                "chase_above": 43.60,
                "stop": 40.95,
                "confluence_gated": False,
            }
        }
    }
    metrics = {"first_trigger_price": 41.72, "anchor_price": 42.10, "atr": 1.15}
    return {symbol: quote}, live, entry, metrics


def _b4_runtime_kwargs(symbol="UNIT", **extra):
    quotes, live, entry, metrics = _b4_runtime_sources(symbol)
    out = {
        "decision_at": "2026-09-18T19:30:08Z",
        "market_session": "2026-09-18",
        "alias_table": _B4Aliases(symbol),
        "quotes_by_symbol": quotes,
        "live_state_artifact": live,
        "entry_rows_by_symbol": entry,
        "metric_inputs": metrics,
    }
    out.update(extra)
    return out


def test_b4_runtime_adapter_binds_identity_quote_basis_and_geometry_without_minting_gates():
    facts = compose_runtime_owner_facts(
        _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs()
    )
    assert facts["quote"]["price"] == 42.70
    assert facts["quote"]["asof"] == "2026-09-18T19:30:00Z"
    assert facts["quote"]["basis_version"] == UNADJUSTED
    assert facts["geometry"]["basis_version"] == ADJUSTED
    assert facts["geometry"]["owner_status"] == "buy_now"
    assert facts["deterministic_gates"]["source_health"] == "PASS"
    assert facts["deterministic_gates"]["corporate_action_basis"] == "RESOLVED"
    assert facts["deterministic_gates"]["liquidity_fillability"] == "UNKNOWN"
    assert facts["deterministic_gates"]["risk_ceiling"] == "UNKNOWN"

    out = evaluate_runtime_entry_availability(
        _b4_projection(),
        episode_id=_b4_cid(),
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        **_b4_runtime_kwargs(),
    )
    assert out["state"] == "UNAVAILABLE_DATA"
    assert out["entry_open"] is False
    assert "LIQUIDITY_FILLABILITY_UNKNOWN" in out["blockers"]


def test_b4_runtime_adapter_has_no_ticker_equality_fallback():
    kwargs = _b4_runtime_kwargs()
    kwargs["alias_table"] = _B4Aliases("RENAMED")
    with pytest.raises(RuntimeOwnerFactError, match="live quote owner has no row"):
        compose_runtime_owner_facts(_b4_projection(), episode_id=_b4_cid(), **kwargs)

    kwargs = _b4_runtime_kwargs()
    kwargs["alias_table"] = _B4Aliases(reverse="SEC:OTHER")
    with pytest.raises(RuntimeOwnerFactError, match="does not round-trip"):
        compose_runtime_owner_facts(_b4_projection(), episode_id=_b4_cid(), **kwargs)


def test_b4_runtime_adapter_refuses_synthetic_dark_unresolved_or_mismatched_live_inputs():
    quotes, live, entry, metrics = _b4_runtime_sources()
    quotes["UNIT"]["quote_ts_synthetic"] = True
    with pytest.raises(RuntimeOwnerFactError, match="real source-market timestamp"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(),
            decision_at="2026-09-18T19:30:08Z", market_session="2026-09-18",
            alias_table=_B4Aliases(), quotes_by_symbol=quotes,
            live_state_artifact=live, entry_rows_by_symbol=entry, metric_inputs=metrics,
        )

    quotes, live, entry, metrics = _b4_runtime_sources()
    live["states"]["UNIT"]["state"] = "dark"
    with pytest.raises(RuntimeOwnerFactError, match="marks canonical store symbol dark"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs(
                live_state_artifact=live, quotes_by_symbol=quotes,
                entry_rows_by_symbol=entry, metric_inputs=metrics,
            )
        )

    quotes, live, entry, metrics = _b4_runtime_sources()
    live["states"]["UNIT"].pop("basis_receipt")
    with pytest.raises(RuntimeOwnerFactError, match="basis receipt"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs(
                live_state_artifact=live, quotes_by_symbol=quotes,
                entry_rows_by_symbol=entry, metric_inputs=metrics,
            )
        )

    quotes, live, entry, metrics = _b4_runtime_sources()
    live["states"]["UNIT"]["price"] = 42.71
    with pytest.raises(RuntimeOwnerFactError, match="disagree on price"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs(
                live_state_artifact=live, quotes_by_symbol=quotes,
                entry_rows_by_symbol=entry, metric_inputs=metrics,
            )
        )


def test_b4_runtime_adapter_refuses_unbound_external_gate_or_receipt_injection():
    gates = {
        "owner_confluence": "PASS",
        "risk_ceiling": "PASS",
        "liquidity_fillability": "PASS",
        "gap_velocity": "PASS",
        "session_eligibility": "PASS",
        "event_status": "ACTIVE",
        "structural_invalidation": "CLEAR",
    }
    with pytest.raises(RuntimeOwnerFactError, match="cannot inject gate verdicts"):
        evaluate_runtime_entry_availability(
            _b4_projection(),
            episode_id=_b4_cid(),
            strategy_definition=build_early_leadership_sector_rotation_definition(),
            **_b4_runtime_kwargs(owner_gate_facts=gates),
        )

    with pytest.raises(RuntimeOwnerFactError, match="cannot be attached"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(),
            **_b4_runtime_kwargs(owner_source_receipts=["sha256:" + "3" * 64]),
        )


def test_b4_runtime_adapter_binds_quote_clock_to_live_state_freshness_owner():
    facts = compose_runtime_owner_facts(
        _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs()
    )
    assert facts["quote"]["freshness"] == "FRESH"

    quotes, live, entry, metrics = _b4_runtime_sources()
    quotes["UNIT"]["quote_ts"] = "2026-09-17T19:30:00Z"
    with pytest.raises(RuntimeOwnerFactError, match="does not match live-state owner quote_age_min"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(),
            **_b4_runtime_kwargs(
                quotes_by_symbol=quotes, live_state_artifact=live,
                entry_rows_by_symbol=entry, metric_inputs=metrics,
            ),
        )

    quotes, live, entry, metrics = _b4_runtime_sources()
    live["states"]["UNIT"].pop("quote_age_min")
    with pytest.raises(RuntimeOwnerFactError, match="live_state.quote_age_min must be numeric"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(),
            **_b4_runtime_kwargs(
                quotes_by_symbol=quotes, live_state_artifact=live,
                entry_rows_by_symbol=entry, metric_inputs=metrics,
            ),
        )

    quotes, live, entry, metrics = _b4_runtime_sources()
    live["meta"]["pass_ts"] = "2026-09-18T19:30:07Z"
    with pytest.raises(RuntimeOwnerFactError, match="pass_ts must equal B4 decision clock"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(),
            **_b4_runtime_kwargs(
                quotes_by_symbol=quotes, live_state_artifact=live,
                entry_rows_by_symbol=entry, metric_inputs=metrics,
            ),
        )

    quotes, live, entry, metrics = _b4_runtime_sources()
    quotes["UNIT"]["quote_ts"] = "2026-09-18T19:30:09Z"
    with pytest.raises(RuntimeOwnerFactError, match="cannot be after B4 decision clock"):
        compose_runtime_owner_facts(
            _b4_projection(), episode_id=_b4_cid(),
            **_b4_runtime_kwargs(
                quotes_by_symbol=quotes, live_state_artifact=live,
                entry_rows_by_symbol=entry, metric_inputs=metrics,
            ),
        )
