import copy
from datetime import datetime, timedelta
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
    build_strategy_catalog,
    validate_strategy_catalog,
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
from lib.nyse_calendar import is_session

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
    emergence=None,
    market_session="2026-09-18",
):
    emergence_by_episode = None if emergence is None else {_b4_cid(): emergence}
    return project_candidate_states(
        _B4Snap(_B4_GEN, _B4Gen((_b4_episode(state, terminal_reason),))),
        market_session=market_session,
        generated_at=generated_at,
        emergence_by_episode=emergence_by_episode,
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

# ---------------------------------------------------------------------------
# B4 runtime owner-fact adapter: canonical identity -> incumbent source facts.

from datetime import date, timezone

from engine.prophet_entry_availability_sources import (
    RuntimeOwnerFactError,
    compose_runtime_owner_facts,
    evaluate_runtime_entry_availability,
)
from engine.prophet_live import live_states as LS


class _B4Aliases:
    def __init__(self, symbol="UNIT", *, reverse="SEC:US-XNAS-AAPL"):
        self.symbol = symbol
        self.reverse = reverse

    def vendor_symbol_for(self, vendor, security_id, on):
        assert vendor == "store"
        assert security_id == "SEC:US-XNAS-AAPL"
        assert on.isoformat()
        return self.symbol

    def resolve(self, vendor, symbol, on):
        assert vendor == "store"
        assert symbol == self.symbol
        assert on.isoformat()
        return self.reverse


def _b4_owner_live_artifact(
    symbol="UNIT",
    *,
    pass_at="2026-09-18T19:30:08Z",
    quote_ts="2026-09-18T19:30:00Z",
    quote_price=42.70,
    as_of_close=42.10,
    row_price_adjustment=None,
    cfg=None,
):
    """A REAL producer fixture: the live artifact is built by the owner's own evaluate.

    The runtime adapter consumes what ``scripts/prophet_live_evaluator.py`` actually
    publishes — a RESOLVED row carrying its measured ``basis_relation`` material,
    disclosure pair, quote_age_min and the artifact-level price_adjustment block — so
    these tests exercise the adapter against owner output, never against a hand-drawn
    stand-in.
    """
    decision = datetime.fromisoformat(pass_at.replace("Z", "+00:00"))
    quote_clock = datetime.fromisoformat(quote_ts.replace("Z", "+00:00"))
    pack_as_of = LS.last_completed_session(decision)
    entry = {"state": "buyable", "center_buyable": True, "as_of_close": as_of_close,
             "bar_date": pack_as_of, "probed": True, "buyable_in_band": True,
             "fade_px": as_of_close - 1.15, "fade_hi_px": as_of_close + 1.15,
             "band_lo_px": as_of_close - 4.0, "band_hi_px": as_of_close + 5.0}
    if row_price_adjustment is not None:
        entry["price_adjustment"] = row_price_adjustment
    counts = ({ADJUSTED: 1} if row_price_adjustment is None
              else {ADJUSTED: 0, row_price_adjustment: 1})
    pack = {"schema": "prophet_live.armed/v1", "as_of": pack_as_of,
            "built_at": f"{pack_as_of}T22:30:00Z", "names": {symbol: entry},
            "price_adjustment": ADJUSTED,
            "meta": {"universe_n": 1, "probed_n": 1, "armed_n": 1, "skipped": {},
                     "price_adjustment_counts": counts}}
    quotes = {symbol: {"price": quote_price, "prev_close": as_of_close, "change_pct": 1.43,
                       "ts_ms": None, "source": "polygon", "quote_ts": quote_ts,
                       "quote_ts_synthetic": False, "price_basis": "trade",
                       "delay_min": 0.1}}
    artifact = LS.evaluate(
        pack, quotes, None, now=decision, cfg=cfg or LS.live_cfg(None),
        quote_asof=quote_ts, delay_min=15,
        quote_age_of=lambda _q: (decision - quote_clock).total_seconds() / 60.0,
    )
    assert artifact["status"] == "live", artifact
    state = artifact["states"][symbol]
    assert state["basis_status"] == "RESOLVED", state
    assert "basis_relation" in state and "basis_receipt" in state
    return artifact


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
    live = _b4_owner_live_artifact(symbol)
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


def test_private_quote_projection_preserves_b4_clock_provenance_only_when_opted_in():
    from scripts import build_live_quotes as live_snapshot

    quotes, live, entry, metrics = _b4_runtime_sources()
    private_quotes = live_snapshot.to_worker_quotes(
        quotes,
        include_private_provenance=True,
    )
    facts = compose_runtime_owner_facts(
        _b4_projection(),
        episode_id=_b4_cid(),
        **_b4_runtime_kwargs(
            quotes_by_symbol=private_quotes,
            live_state_artifact=live,
            entry_rows_by_symbol=entry,
            metric_inputs=metrics,
        ),
    )
    assert facts["quote"]["asof"] == "2026-09-18T19:30:00Z"

    public_quotes = live_snapshot.to_worker_quotes(quotes)
    assert "quote_ts_synthetic" not in public_quotes["UNIT"]
    with pytest.raises(RuntimeOwnerFactError, match="real source-market timestamp"):
        compose_runtime_owner_facts(
            _b4_projection(),
            episode_id=_b4_cid(),
            **_b4_runtime_kwargs(
                quotes_by_symbol=public_quotes,
                live_state_artifact=live,
                entry_rows_by_symbol=entry,
                metric_inputs=metrics,
            ),
        )


def test_b4_runtime_adapter_binds_identity_quote_basis_and_geometry_without_minting_gates():
    facts = compose_runtime_owner_facts(
        _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs()
    )
    assert facts["quote"]["price"] == 42.70
    assert facts["quote"]["asof"] == "2026-09-18T19:30:00Z"
    assert facts["quote"]["basis_version"] == UNADJUSTED
    assert facts["geometry"]["basis_version"] == "UNKNOWN"
    assert facts["geometry"]["owner_status"] == "buy_now"
    assert facts["deterministic_gates"]["source_health"] == "PASS"
    assert facts["deterministic_gates"]["corporate_action_basis"] == "UNKNOWN"
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


def test_b4_runtime_adapter_binds_accepted_session_policy_without_widening_other_gates():
    strategy = build_early_leadership_sector_rotation_definition()
    facts = compose_runtime_owner_facts(
        _b4_projection(),
        episode_id=_b4_cid(),
        strategy_definition=strategy,
        **_b4_runtime_kwargs(),
    )
    gates = facts["deterministic_gates"]
    assert gates["session_eligibility"] == "PASS"
    assert gates["risk_ceiling"] == "UNKNOWN"
    assert gates["liquidity_fillability"] == "UNKNOWN"
    assert gates["gap_velocity"] == "UNKNOWN"
    assert any(str(receipt).startswith("pepf:") for receipt in facts["source_receipts"])

    out = evaluate_runtime_entry_availability(
        _b4_projection(),
        episode_id=_b4_cid(),
        strategy_definition=strategy,
        **_b4_runtime_kwargs(),
    )
    assert out["state"] == "UNAVAILABLE_DATA"
    assert out["entry_open"] is False
    assert "SESSION_ELIGIBILITY_UNKNOWN" not in out["blockers"]
    assert "RISK_CEILING_UNKNOWN" in out["blockers"]
    assert "LIQUIDITY_FILLABILITY_UNKNOWN" in out["blockers"]
    assert "GAP_VELOCITY_UNKNOWN" in out["blockers"]


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


def _b4_compose_with_live_mutations(mutate):
    """Compose against a copy of the real owner live artifact with one mutation."""
    kwargs = _b4_runtime_kwargs()
    polluted = copy.deepcopy(kwargs["live_state_artifact"])
    mutate(polluted["states"]["UNIT"])
    kwargs["live_state_artifact"] = polluted
    return compose_runtime_owner_facts, kwargs


def test_b4_runtime_adapter_treats_missing_basis_material_as_unavailable():
    """A legacy RESOLVED receipt WITHOUT measured material is unavailable, not a
    historical fallback: the digest alone commits to nothing a consumer can check."""
    kwargs = _b4_runtime_kwargs()
    kwargs["live_state_artifact"]["states"]["UNIT"].pop("basis_relation")
    with pytest.raises(RuntimeOwnerFactError, match="basis relation material"):
        compose_runtime_owner_facts(_b4_projection(), episode_id=_b4_cid(), **kwargs)


def test_b4_runtime_adapter_rejects_tampered_or_foreign_basis_material():
    def attempt(mutate, match):
        compose, kwargs = _b4_compose_with_live_mutations(mutate)
        with pytest.raises(RuntimeOwnerFactError, match=match):
            compose(_b4_projection(), episode_id=_b4_cid(), **kwargs)

    attempt(lambda st: st["basis_relation"].__setitem__("subject", "OTHER"),
            "binds a different subject")
    attempt(lambda st: st["basis_relation"].__setitem__("pack_as_of", "2026-09-10"),
            "does not bind the live pack cut")
    attempt(lambda st: st["basis_relation"].__setitem__("state", "UNRESOLVED"),
            "does not record a RESOLVED state")

    def tampered_gap(state):
        state["basis_relation"]["gap_pct"] = 9.9
        state["basis_receipt"] = LS.basis_relation_receipt(dict(state["basis_relation"]))
    attempt(tampered_gap, "not a positive measurement")

    def zero_tolerance(state):
        state["basis_relation"]["tol_pct"] = 0.0
        state["basis_receipt"] = LS.basis_relation_receipt(dict(state["basis_relation"]))
    attempt(zero_tolerance, "not a positive measurement")

    attempt(lambda st: st.__setitem__("basis_as_of_close", 41.0),
            "does not reproduce the measured basis gap")
    attempt(lambda st: st.__setitem__("basis_prev_close", 40.0),
            "does not reproduce the measured basis gap")


def test_b4_runtime_adapter_rejects_material_contradicting_row_or_meta_basis_law():
    def attempt(mutate, match):
        compose, kwargs = _b4_compose_with_live_mutations(mutate)
        with pytest.raises(RuntimeOwnerFactError, match=match):
            compose(_b4_projection(), episode_id=_b4_cid(), **kwargs)

    # A row-override the material does not record: the declaration and material disagree.
    attempt(lambda st: st.__setitem__("levels_adjustment", UNADJUSTED),
            "row/meta basis declaration")

    # A material whose quote family contradicts the artifact's stated quote basis.
    def foreign_quote_family(state):
        state["basis_relation"]["quote_adjustment"] = "other_basis"
        state["basis_receipt"] = LS.basis_relation_receipt(dict(state["basis_relation"]))
    attempt(foreign_quote_family, "stated quote basis")

    # A material whose levels family contradicts the artifact's stated levels basis.
    def foreign_levels_family(state):
        state["basis_relation"]["levels_adjustment"] = "other_basis"
        state["basis_receipt"] = LS.basis_relation_receipt(dict(state["basis_relation"]))
    attempt(foreign_levels_family, "row/meta basis declaration")


def test_b4_runtime_adapter_binds_private_quote_close_and_rung_to_measured_owner_inputs():
    kwargs = _b4_runtime_kwargs()
    kwargs["quotes_by_symbol"]["UNIT"].pop("prev_close")
    with pytest.raises(RuntimeOwnerFactError, match="previous close"):
        compose_runtime_owner_facts(_b4_projection(), episode_id=_b4_cid(), **kwargs)

    kwargs = _b4_runtime_kwargs()
    kwargs["quotes_by_symbol"]["UNIT"]["prev_close"] = 40.0
    with pytest.raises(RuntimeOwnerFactError, match="previous close"):
        compose_runtime_owner_facts(_b4_projection(), episode_id=_b4_cid(), **kwargs)

    kwargs = _b4_runtime_kwargs()
    kwargs["quotes_by_symbol"]["UNIT"].pop("price_basis")
    with pytest.raises(RuntimeOwnerFactError, match="vendor rung"):
        compose_runtime_owner_facts(_b4_projection(), episode_id=_b4_cid(), **kwargs)

    kwargs = _b4_runtime_kwargs()
    kwargs["quotes_by_symbol"]["UNIT"]["price_basis"] = "some_adjusted_basis"
    with pytest.raises(RuntimeOwnerFactError, match="vendor rung"):
        compose_runtime_owner_facts(_b4_projection(), episode_id=_b4_cid(), **kwargs)


def test_b4_runtime_adapter_pack_basis_cannot_attest_independent_entry_geometry():
    kwargs = _b4_runtime_kwargs()
    # The entry signal is a separate object with no native OHLC/geometry basis
    # receipt. Equal prices or a declared family cannot extend the pack receipt.
    signal = kwargs["entry_rows_by_symbol"]["UNIT"]["entry_signal"]
    signal["price_adjustment"] = ADJUSTED
    facts = compose_runtime_owner_facts(
        _b4_projection(), episode_id=_b4_cid(), **kwargs
    )
    assert facts["quote"]["basis_version"] == UNADJUSTED
    assert facts["geometry"]["basis_version"] == "UNKNOWN"
    assert facts["deterministic_gates"]["corporate_action_basis"] == "UNKNOWN"
    availability = evaluate_runtime_entry_availability(
        _b4_projection(), episode_id=_b4_cid(),
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        **kwargs,
    )
    assert availability["state"] == "UNAVAILABLE_DATA"
    assert "CORPORATE_ACTION_BASIS_UNKNOWN" in availability["blockers"]


def test_b4_runtime_adapter_propagates_measured_families_from_the_owner_material():
    facts = compose_runtime_owner_facts(
        _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs()
    )
    # The quote family is measured; independent entry geometry remains unattested.
    assert facts["quote"]["basis_version"] == LS.LIVE_QUOTE_ADJUSTMENT == UNADJUSTED
    assert facts["geometry"]["basis_version"] == "UNKNOWN"

    # Even an explicit raw-price armed pack cannot attest independent geometry.
    live = _b4_owner_live_artifact(row_price_adjustment=UNADJUSTED)
    state = live["states"]["UNIT"]
    assert state["levels_adjustment"] == UNADJUSTED
    assert state["basis_relation"]["levels_adjustment"] == UNADJUSTED
    kwargs = _b4_runtime_kwargs()
    kwargs["live_state_artifact"] = live
    exception_facts = compose_runtime_owner_facts(
        _b4_projection(), episode_id=_b4_cid(), **kwargs
    )
    assert exception_facts["geometry"]["basis_version"] == "UNKNOWN"
    assert exception_facts["quote"]["basis_version"] == UNADJUSTED




def _b4_signal_gate(
    symbol="UNIT",
    *,
    eligible=True,
    tier="T1",
    at_utc="2026-09-17T22:35:00Z",
    as_of="2026-09-17",
    decision_at="2026-09-18T14:00:00Z",
    market_session="2026-09-18",
):
    validity = {
        "schema": "signal_gate.validity/v1",
        "source_session": as_of,
        "emitted_at": at_utc,
        "expected_last_session": as_of,
        "lag_sessions": 0,
        "settled": True,
        "valid_for_decision_sessions": ["2026-09-18"],
        "expiry_session": "2026-09-18",
        "lineage_token": "unit-pair-001",
    }
    return {
        "as_of": as_of,
        "verdicts": {
            symbol: {
                "eligible": eligible,
                "tier_cascade": tier,
                "asof": as_of,
            }
        },
        "emit": {
            "pair_id": "unit-pair-001",
            "at_utc": at_utc,
            "writer": "build_stock_library",
        },
        "validity": validity,
        "_decision_at": decision_at,
        "_market_session": market_session,
    }


def _b4_confluence_case(**overrides):
    artifact = _b4_signal_gate(**overrides.get("artifact", {}))
    for key, value in overrides.get("validity", {}).items():
        artifact["validity"][key] = value
    decision_at = artifact.pop("_decision_at")
    market_session = artifact.pop("_market_session")
    decision_clock = datetime.fromisoformat(decision_at.replace("Z", "+00:00"))
    quote_clock = decision_clock - timedelta(seconds=8)
    quote_ts = quote_clock.isoformat(timespec="seconds").replace("+00:00", "Z")
    projection = _b4_projection(
        generated_at=quote_ts,
        market_session=market_session,
    )
    runtime_kwargs = _b4_runtime_kwargs(
        decision_at=decision_at,
        market_session=market_session,
        signal_gate_artifact=artifact,
        **overrides.get("runtime", {}),
    )
    runtime_kwargs["quotes_by_symbol"]["UNIT"]["quote_ts"] = quote_ts
    runtime_kwargs["live_state_artifact"]["meta"]["pass_ts"] = decision_at
    runtime_kwargs["live_state_artifact"]["meta"]["session_et"] = market_session
    return artifact, runtime_kwargs, projection


def _b4_confluence_gate(**overrides):
    _, runtime_kwargs, projection = _b4_confluence_case(**overrides)
    facts = compose_runtime_owner_facts(
        projection, episode_id=_b4_cid(), **runtime_kwargs
    )
    return facts["deterministic_gates"]["owner_confluence"], facts["source_receipts"]


def test_b4_runtime_adapter_binds_only_positive_pit_safe_owner_confluence():
    _, runtime_kwargs, projection = _b4_confluence_case()
    facts = compose_runtime_owner_facts(
        projection, episode_id=_b4_cid(), **runtime_kwargs
    )
    assert facts["deterministic_gates"]["owner_confluence"] == "PASS"
    assert (
        "signal-gate-pair:unit-pair-001@2026-09-17 "
        "verdict_asof=2026-09-17 emitted_at=2026-09-17T22:35:00Z"
    ) in facts["source_receipts"]
    assert facts["deterministic_gates"]["risk_ceiling"] == "UNKNOWN"

    _, not_buyable_kwargs, not_buyable_projection = _b4_confluence_case(
        artifact={"eligible": False, "tier": None}
    )
    not_buyable = compose_runtime_owner_facts(
        not_buyable_projection, episode_id=_b4_cid(), **not_buyable_kwargs
    )
    assert not_buyable["deterministic_gates"]["owner_confluence"] == "UNKNOWN"
    assert "signal-gate-pair:unit-pair-001@2026-09-17" not in not_buyable["source_receipts"]

    _, malformed_kwargs, malformed_projection = _b4_confluence_case(
        artifact={"eligible": "true"}
    )
    malformed_facts = compose_runtime_owner_facts(
        malformed_projection, episode_id=_b4_cid(), **malformed_kwargs
    )
    assert malformed_facts["deterministic_gates"]["owner_confluence"] == "UNKNOWN"


def test_b4_runtime_adapter_degrades_legacy_signal_gate_to_unknown_and_unavailable():
    artifact, runtime_kwargs, projection = _b4_confluence_case()
    artifact.pop("validity")
    runtime_kwargs["signal_gate_artifact"] = artifact
    facts = compose_runtime_owner_facts(
        projection, episode_id=_b4_cid(), **runtime_kwargs
    )
    assert facts["deterministic_gates"]["owner_confluence"] == "UNKNOWN"
    availability = evaluate_runtime_entry_availability(
        projection,
        episode_id=_b4_cid(),
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        **runtime_kwargs,
    )
    assert availability["state"] == "UNAVAILABLE_DATA"
    assert "OWNER_CONFLUENCE_UNKNOWN" in availability["blockers"]


def test_b4_confluence_non_mapping_artifact_is_unknown():
    artifact, runtime_kwargs, projection = _b4_confluence_case()
    runtime_kwargs["signal_gate_artifact"] = ["not-an-object"]
    facts = compose_runtime_owner_facts(projection, episode_id=_b4_cid(), **runtime_kwargs)
    verdict, receipts = facts["deterministic_gates"]["owner_confluence"], facts["source_receipts"]
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_malformed") for receipt in receipts)


def test_b4_confluence_c3_expired_pair_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        artifact={
            "at_utc": "2026-09-18T19:30:00Z",
            "as_of": "2026-09-18",
            "decision_at": "2026-09-21T14:00:00Z",
            "market_session": "2026-09-21",
        }
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_expired") for receipt in receipts)


def test_b4_confluence_c4_late_emission_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        artifact={"at_utc": "2026-09-18T15:00:00Z", "as_of": "2026-09-17"}
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_late_emission") for receipt in receipts)


def test_b4_confluence_c5_lineage_mismatch_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        validity={"lineage_token": "other-pair"}
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_lineage_mismatch") for receipt in receipts)


def test_b4_confluence_c6_stale_source_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        artifact={
            "at_utc": "2026-09-17T22:35:00Z",
            "as_of": "2026-09-16",
            "decision_at": "2026-09-18T14:00:00Z",
            "market_session": "2026-09-17",
        },
        validity={"valid_for_decision_sessions": ["2026-09-17"]},
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_stale_source") for receipt in receipts)


def test_b4_confluence_c7_ahead_unsettled_source_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        artifact={
            "at_utc": "2026-09-18T15:00:00Z",
            "as_of": "2026-09-18",
            "decision_at": "2026-09-21T14:00:00Z",
            "market_session": "2026-09-21",
        },
        validity={
            "expected_last_session": "2026-09-17",
            "lag_sessions": -1,
            "settled": False,
            "valid_for_decision_sessions": ["2026-09-21"],
        },
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_unsettled_source") for receipt in receipts)


def test_b4_confluence_c8_holiday_adjacent_pair_passes():
    artifact, runtime_kwargs, projection = _b4_confluence_case(
        artifact={
            "at_utc": "2026-11-25T22:35:00Z",
            "as_of": "2026-11-25",
            "decision_at": "2026-11-27T15:00:00Z",
            "market_session": "2026-11-27",
        },
        validity={"valid_for_decision_sessions": ["2026-11-27"], "expiry_session": "2026-11-27"},
    )
    facts = compose_runtime_owner_facts(
        projection, episode_id=_b4_cid(), **runtime_kwargs
    )
    assert is_session(date(2026, 11, 25)) and is_session(date(2026, 11, 27))
    assert facts["deterministic_gates"]["owner_confluence"] == "PASS"
    assert any(
        receipt.startswith("signal-gate-pair:unit-pair-001@2026-11-25")
        for receipt in facts["source_receipts"]
    )


def test_b4_confluence_c9_missing_symbol_row_is_unknown():
    artifact, runtime_kwargs, projection = _b4_confluence_case()
    artifact["verdicts"].pop("UNIT")
    runtime_kwargs["signal_gate_artifact"] = artifact
    facts = compose_runtime_owner_facts(
        projection, episode_id=_b4_cid(), **runtime_kwargs
    )
    assert facts["deterministic_gates"]["owner_confluence"] == "UNKNOWN"
    assert any(receipt.endswith("confluence_row_missing") for receipt in facts["source_receipts"])


def test_b4_confluence_c10_relabelled_source_session_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        validity={"source_session": "2026-09-16"}
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_session_mismatch") for receipt in receipts)


def test_b4_confluence_c11_same_session_pair_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        artifact={
            "at_utc": "2026-09-18T19:30:07Z",
            "as_of": "2026-09-18",
            "decision_at": "2026-09-18T19:30:08Z",
        },
        validity={"valid_for_decision_sessions": ["2026-09-18"], "expiry_session": "2026-09-18"},
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_session_mismatch") for receipt in receipts)


def test_b4_confluence_c12_stale_verdict_tape_is_unknown():
    artifact, runtime_kwargs, projection = _b4_confluence_case()
    artifact["verdicts"]["UNIT"]["asof"] = "2026-09-11"
    runtime_kwargs["signal_gate_artifact"] = artifact
    facts = compose_runtime_owner_facts(
        projection, episode_id=_b4_cid(), **runtime_kwargs
    )
    assert facts["deterministic_gates"]["owner_confluence"] == "UNKNOWN"
    assert any(receipt.endswith("confluence_tape_stale") for receipt in facts["source_receipts"])


def test_b4_confluence_c13_foreign_writer_is_unknown():
    artifact, runtime_kwargs, projection = _b4_confluence_case()
    artifact["emit"]["writer"] = "other"
    runtime_kwargs["signal_gate_artifact"] = artifact
    facts = compose_runtime_owner_facts(
        projection, episode_id=_b4_cid(), **runtime_kwargs
    )
    verdict, receipts = facts["deterministic_gates"]["owner_confluence"], facts["source_receipts"]
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_writer_mismatch") for receipt in receipts)


def test_b4_confluence_c14_emit_stamp_mismatch_is_unknown():
    verdict, receipts = _b4_confluence_gate(
        validity={"emitted_at": "2026-09-17T22:36:00Z"}
    )
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_malformed") for receipt in receipts)


def test_b4_confluence_c15_producer_lag_disagreement_is_unknown():
    verdict, receipts = _b4_confluence_gate(validity={"lag_sessions": 1})
    assert verdict == "UNKNOWN"
    assert any(receipt.endswith("confluence_malformed") for receipt in receipts)


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


def _b4_turn_watch_emergence(*, source_ref="pee:" + "b" * 64, source_token="B1_OBSERVED"):
    return {
        "state": "TRIGGERED",
        "reason": None,
        "source_system": "turn_watch",
        "source_token": source_token,
        "source_ref": source_ref,
    }


def test_b4_runtime_adapter_binds_event_active_only_from_current_b1_relation_receipt():
    relation = "pee:" + "b" * 64
    facts = compose_runtime_owner_facts(
        _b4_projection(emergence=_b4_turn_watch_emergence(source_ref=relation)),
        episode_id=_b4_cid(),
        **_b4_runtime_kwargs(),
    )
    assert facts["deterministic_gates"]["event_status"] == "ACTIVE"
    assert relation in facts["source_receipts"]

    unresolved = compose_runtime_owner_facts(
        _b4_projection(), episode_id=_b4_cid(), **_b4_runtime_kwargs()
    )
    assert unresolved["deterministic_gates"]["event_status"] == "UNKNOWN"
    assert relation not in unresolved["source_receipts"]


def test_b4_runtime_adapter_refuses_malformed_b1_relation_receipt_and_does_not_generalize_sources():
    with pytest.raises(RuntimeOwnerFactError, match="no exact B1 relation receipt"):
        compose_runtime_owner_facts(
            _b4_projection(
                emergence=_b4_turn_watch_emergence(source_ref="pee:not-a-receipt")
            ),
            episode_id=_b4_cid(),
            **_b4_runtime_kwargs(),
        )

    other = _b4_turn_watch_emergence()
    other["source_system"] = "entry_radar"
    facts = compose_runtime_owner_facts(
        _b4_projection(emergence=other),
        episode_id=_b4_cid(),
        **_b4_runtime_kwargs(),
    )
    assert facts["deterministic_gates"]["event_status"] == "UNKNOWN"

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
    assert out["execution_schedule_source"] == "NYSE_BETA_HOLIDAYS_AND_TRADING_HOURS_2026_2027"
    assert out["execution_schedule_verified_on"] == "2026-10-07"
    assert out["supported_session_years"] == [2026, 2027]
    assert out["early_close_dates"] == ["2026-11-27", "2026-12-24", "2027-11-26"]
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

    with pytest.raises(EntryPolicyContractError, match="outside NYSE_RTH_2026_2027"):
        _session_policy("2028-01-03T15:00:00Z", "2028-01-03")


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


# ---------------------------------------------------------------------------
# Full eight-sleeve roadmap catalog.  This is authority-false architecture
# truth only: it must not turn retained research avenues into live strategies.
# ---------------------------------------------------------------------------


def _catalog_by_id():
    catalog = build_strategy_catalog()
    return catalog, {row["strategy_id"]: row for row in catalog["sleeves"]}


def test_strategy_catalog_retains_all_eight_architecture_backed_sleeves():
    catalog, sleeves = _catalog_by_id()
    assert [row["strategy_id"] for row in catalog["sleeves"]] == [
        "CYCLE_CAPTURE",
        "EARLY_LEADERSHIP_SECTOR_ROTATION",
        "QUALITY_EARNINGS_EXPECTATION_REVISION",
        "POLICY_EVENT_SWING",
        "CATALYST_DISLOCATION",
        "LIQUIDITY_DEBASEMENT_REAL_ASSETS",
        "RANGE_MEAN_REVERSION",
        "DEFENSIVE_AVOIDANCE_HEDGE_RESEARCH",
    ]
    assert set(catalog["initial_core_sleeves"]) == {
        "EARLY_LEADERSHIP_SECTOR_ROTATION",
        "QUALITY_EARNINGS_EXPECTATION_REVISION",
        "CYCLE_CAPTURE",
    }
    assert set(catalog["retained_later_sleeves"]) == set(sleeves) - set(catalog["initial_core_sleeves"])


def test_catalog_preserves_only_existing_early_leadership_control_definition():
    _catalog, sleeves = _catalog_by_id()
    early = sleeves["EARLY_LEADERSHIP_SECTOR_ROTATION"]
    accepted = build_early_leadership_sector_rotation_definition()
    assert early["definition_status"] == "CONTROL_DEFINED_SHADOW_ONLY"
    assert early["definition_ref"]["strategy_definition_id"] == accepted["strategy_definition_id"]
    assert early["horizon"]["primary"] == "2_15_SESSIONS"
    for strategy_id, row in sleeves.items():
        if strategy_id == "EARLY_LEADERSHIP_SECTOR_ROTATION":
            continue
        assert row["definition_ref"] is None
        assert "CONTROL_DEFINED" not in row["definition_status"]


def test_earnings_and_cycle_horizons_are_research_proposals_not_hold_laws():
    _catalog, sleeves = _catalog_by_id()
    earnings = sleeves["QUALITY_EARNINGS_EXPECTATION_REVISION"]
    cycle = sleeves["CYCLE_CAPTURE"]
    assert earnings["horizon"] == {
        "status": "RESEARCH_PROPOSAL_NOT_POLICY",
        "primary": "H42",
        "supporting": ["H21", "H63"],
        "narrative": "weeks to months; proposed research checkpoints are not a printed holding duration",
        "not_a_hold_law": True,
    }
    assert cycle["horizon"]["status"] == "RESEARCH_PROPOSAL_NOT_POLICY"
    assert cycle["horizon"]["primary"] == "H252"
    assert cycle["horizon"]["supporting"] == ["H126", "H504"]
    assert cycle["horizon"]["not_a_hold_law"] is True


def test_retained_later_sleeves_do_not_copy_the_tactical_horizon():
    _catalog, sleeves = _catalog_by_id()
    for strategy_id in (
        "POLICY_EVENT_SWING",
        "CATALYST_DISLOCATION",
        "LIQUIDITY_DEBASEMENT_REAL_ASSETS",
        "RANGE_MEAN_REVERSION",
        "DEFENSIVE_AVOIDANCE_HEDGE_RESEARCH",
    ):
        horizon = sleeves[strategy_id]["horizon"]
        assert horizon["status"] == "OWNER_SPEC_REQUIRED"
        assert horizon["primary"] is None
        assert horizon["supporting"] == []
        assert "2_15_SESSIONS" not in json.dumps(horizon)


def test_catalog_keeps_regime_out_of_universal_cross_sectional_ranking():
    catalog, sleeves = _catalog_by_id()
    law = catalog["cross_sleeve_law"]
    assert law["universal_score_authorized"] is False
    assert law["row_constant_macro_may_rank_stocks"] is False
    assert law["candidate_may_match_multiple_sleeves"] is True
    assert law["sleeve_disagreements_are_preserved"] is True
    assert "general-purpose" in sleeves["RANGE_MEAN_REVERSION"]["constraints"][0].lower()


def test_cycle_catalog_does_not_launder_killed_washout_or_rotation_confluence():
    _catalog, sleeves = _catalog_by_id()
    cycle = sleeves["CYCLE_CAPTURE"]
    assert "DNR:KILL-WASHOUT-TURN" in cycle["constraints"]
    assert "DNR:KILL-ROTATION-CYCLE-CONFLUENCE" in cycle["constraints"]
    assert any("surviv" in fact for fact in cycle["required_evidence"])
    assert any("dilution" in fact for fact in cycle["required_evidence"])


def test_defensive_sleeve_does_not_mint_short_or_hedge_authority():
    catalog, sleeves = _catalog_by_id()
    defensive = sleeves["DEFENSIVE_AVOIDANCE_HEDGE_RESEARCH"]
    assert "DNR:KILL-DIRECTIONAL-SHORTING" in defensive["constraints"]
    assert defensive["authority"]["can_activate_short"] is False
    assert defensive["authority"]["can_activate_options"] is False
    assert catalog["authority"]["can_activate_short"] is False


def test_every_sleeve_has_mechanism_evidence_falsifiers_and_zero_authority():
    catalog, _sleeves = _catalog_by_id()
    for row in catalog["sleeves"]:
        assert row["user_job"]
        assert row["economic_thesis"]
        assert row["required_evidence"]
        assert row["primary_falsifiers"]
        assert row["promotion_requirements"]
        assert row["entry_owner"]
        assert row["hold_law"]
        assert all(value is False for value in row["authority"].values())


def test_strategy_catalog_is_stable_content_addressed_and_deep_copy_safe():
    left = build_strategy_catalog()
    right = build_strategy_catalog()
    assert left == right
    assert left["catalog_id"].startswith("psc:")
    left["sleeves"][0]["family_name"] = "MUTATED"
    assert build_strategy_catalog() == right


def test_strategy_catalog_rejects_semantic_authority_and_identity_mutation():
    payload = build_strategy_catalog()
    payload["sleeves"][2]["horizon"]["primary"] = "2_15_SESSIONS"
    with pytest.raises(StrategyDefinitionContractError, match="frozen roadmap"):
        validate_strategy_catalog(payload)

    payload = build_strategy_catalog()
    payload["authority"]["can_route_strategy"] = True
    with pytest.raises(StrategyDefinitionContractError):
        validate_strategy_catalog(payload)

    payload = build_strategy_catalog()
    payload["catalog_id"] = "psc:" + "0" * 64
    with pytest.raises(StrategyDefinitionContractError, match="catalog_id mismatch"):
        validate_strategy_catalog(payload)


# ---------------------------------------------------------------------------
# B4 native reader: canonical episode store + the two fixed private owner files.
# The fixture store is built THROUGH the incumbent owner functions (reconcile /
# apply_commands / build_all_candidates / the generation + HEAD content addresses)
# and revalidated by the store's own loader before any reader call.
# ---------------------------------------------------------------------------

from datetime import datetime, timedelta, timezone

import engine.prophet_entry_availability_sources as _sources
from engine.prophet_entry_availability_sources import read_native_b4_owner_inputs
from engine.stock_identity import fingerprint
from engine.us_candidate_episode import (
    DEFAULT_DEFINITION_ERA,
    GENERATION_MANIFEST_SCHEMA,
    HEAD_SCHEMA,
    PARQUET_JSON_FIELDS,
    RECONCILE_RECEIPT_SCHEMA,
    apply_commands,
    build_all_candidates,
    canonical_json as _core_canonical,
    load_candidate_episode_store_snapshot,
    reconcile_observations,
    validate_candidate_episode_generation,
)

import pyarrow as pa
import pyarrow.parquet as pq

_READER_SOURCE_RECEIPT = "sha256:" + "c" * 64

#: WHERE the fixture world's own read completes.  The reader re-ages the quote at
#: its OWN completion clock (the repair under test), so a world built around the
#: Sept-17 19:30Z quote must be READ at a truthful in-session moment — pinned here,
#: 15 minutes after the quote, inside the derived 25-minute ceiling the fixture
#: artifact discloses.  Individual tests re-pin their own completion moment; the
#: future-owner-clock rejection reads the same seam and is never weakened.
_READER_READ_AT = datetime(2026, 9, 17, 19, 45, 0, tzinfo=timezone.utc)

#: The QUALIFIED worlds' truthful synthetic source clocks: the observation is
#: known and the store recorded BEFORE the live pass and the read, so a fresh
#: same-session read is genuinely representable.  The default world keeps the
#: nightly 21:00Z recording of the shared fixture — and no fresh read of a
#: 19:30Z quote can follow that recording, which is exactly why the default
#: world's honest reads are the stale and cross-session ones.
_QUALIFIED_SOURCE_KNOWN_AT = "2026-09-17T19:00:00Z"
_QUALIFIED_RECORDED_AT = "2026-09-17T19:35:00Z"


@pytest.fixture(autouse=True)
def _b4_reader_own_read_clock(monkeypatch):
    """Pin the native reader's OWN completion clock for every test in this module."""
    monkeypatch.setattr(_sources, "_now_utc", lambda: _READER_READ_AT, raising=False)


def _b4_reader_observation(
    *,
    day="2026-09-17",
    ticker="UNIT",
    board="gap_continuation",
    security_id="SEC:US-XNAS-AAPL",
    company_id="ISS:US-XNAS-AAPL",
    known_at=None,
    anchor_time=None,
    anchor_kind="turn_watch_reset_low",
    source_event_id=None,
    source_receipt=_READER_SOURCE_RECEIPT,
):
    known_at = known_at or f"{day}T20:00:00Z"
    anchor = None
    if anchor_kind is not None:
        anchor = {"kind": anchor_kind, "time": anchor_time or f"{day}T19:55:00Z",
                  "price": 41.0, "basis": "adjusted_close",
                  "source_receipt": "sha256:" + "a" * 64}
    return {
        "security_id": security_id,
        "company_id": company_id,
        "ticker_at_observation": ticker,
        "identity_epoch": "epoch_0",
        "identity_epoch_state": "provisional",
        "identity_spec_schema": "stock_identity.fingerprint_spec.v1",
        "identity_spec_hash": fingerprint.spec_hash(),
        "anchor": anchor,
        "intake_class": "technical_emergence",
        "occurred_at": known_at,
        "known_at": known_at,
        "source_system": "candidate",
        "source_schema": "us_prophet_rank.candidates/v1",
        "source_event_id": source_event_id or f"candidate:{day}:{ticker}:{board}",
        "source_receipt": source_receipt,
    }


def _b4_reader_store(
    root,
    *,
    events,
    suppressions=(),
    candidate_inputs=1,
    suppressed_inputs=0,
    recorded_at="2026-09-17T21:00:00Z",
):
    """Persist one canonical generation through the incumbent content addresses."""
    import shutil

    root.mkdir(parents=True, exist_ok=True)
    staging = root / "generations" / "staging"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "events").mkdir(parents=True)
    (staging / "suppressions").mkdir(parents=True)
    files: dict[str, dict] = {}

    def write(relative: str, payload: bytes) -> None:
        (staging / relative).write_bytes(payload)
        files[relative] = {
            "sha256": "sha256:" + hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
        }

    def canonical_bytes(value) -> bytes:
        return _core_canonical(value).encode("utf-8") + b"\n"

    projection = build_all_candidates(events, suppression_count=len(suppressions))
    write("all_candidates.json", canonical_bytes(projection))

    parquet_rows = [
        {key: (_core_canonical(value) if key in PARQUET_JSON_FIELDS else value)
         for key, value in row.items()}
        for row in projection["episodes"]
    ]
    schema = pa.schema([
        (key, pa.int64() if key == "observation_count" else pa.string())
        for key in parquet_rows[0]
    ] if parquet_rows else [])
    sink = pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist(parquet_rows, schema=schema), sink)
    write("current.parquet", sink.getvalue().to_pybytes())

    ledger_sha256 = "sha256:" + hashlib.sha256(
        _core_canonical(tuple(events)).encode("utf-8")
    ).hexdigest()
    suppressed_from_inputs = max(len(suppressions), suppressed_inputs)
    receipt = {
        "schema": RECONCILE_RECEIPT_SCHEMA,
        "mode": "nightly",
        "gate": {"nightly_requested": True, "nightly_advance_enabled": True},
        "durable_write": True,
        "recorded_at": recorded_at,
        "definition_era": DEFAULT_DEFINITION_ERA,
        "source_hashes": {},
        "source_counts": {
            "turn_watch": {"input": 0, "mapped": 0, "suppressed": 0},
            "candidate": {"input": candidate_inputs,
                          "mapped": candidate_inputs - suppressed_from_inputs,
                          "suppressed": suppressed_from_inputs},
            "doors": {"input": 0, "mapped": 0, "suppressed": 0},
            "entry_radar": {"input": 0, "mapped": 0, "suppressed": 0},
        },
        "counts": {
            "input": candidate_inputs,
            "mapped": candidate_inputs - suppressed_from_inputs,
            "suppressed": suppressed_from_inputs,
            "ledger_suppressions": len(suppressions),
            "old_events": 0,
            "new_events": len(events),
            "appended_events": len(events),
        },
        "ledger_sha256": ledger_sha256,
        "projection_hashes": {
            "all_candidates.json": files["all_candidates.json"]["sha256"],
            "current.parquet": files["current.parquet"]["sha256"],
        },
        "source_receipts": [
            {"source": "turn_watch", "status": "ok", "rows": 0, "files": []},
            {"source": "candidate", "status": "ok",
             "rows": candidate_inputs - suppressed_from_inputs, "files": []},
            {"source": "doors", "status": "ok", "rows": 0, "files": []},
            {"source": "entry_radar", "status": "ok", "rows": 0, "files": []},
        ],
    }
    write("latest_receipt.json", canonical_bytes(receipt))

    if events:
        ordered = sorted(events, key=lambda row: (row["known_at"], row["source_system"],
                                                  row["source_event_id"]))
        write(f"events/{recorded_at[:7]}.jsonl",
              ("\n".join(_core_canonical(row) for row in ordered) + "\n").encode("utf-8"))
    if suppressions:
        ordered_suppressions = sorted(
            (_b4_reader_durable_suppression(row, recorded_at) for row in suppressions),
            key=lambda row: row["suppression_id"],
        )
        write(f"suppressions/{recorded_at[:7]}.jsonl",
              ("\n".join(_core_canonical(row) for row in ordered_suppressions) + "\n").encode("utf-8"))

    material = {"schema": GENERATION_MANIFEST_SCHEMA, "files": files}
    generation_id = "peg:" + hashlib.sha256(
        _core_canonical(material).encode("utf-8")
    ).hexdigest()
    manifest = {"schema": GENERATION_MANIFEST_SCHEMA, "generation_id": generation_id,
                "files": files}
    manifest["content_sha256"] = hashlib.sha256(_core_canonical({
        key: value for key, value in manifest.items() if key != "content_sha256"
    }).encode("utf-8")).hexdigest()
    final_dir = root / "generations" / generation_id
    if final_dir.exists():  # same bytes -> same content address: rebuild in place
        shutil.rmtree(final_dir)
    staging.rename(final_dir)
    (final_dir / "manifest.json").write_bytes(canonical_bytes(manifest))

    head = {"schema": HEAD_SCHEMA, "generation_id": generation_id,
            "manifest_sha256": "sha256:" + hashlib.sha256(
                (final_dir / "manifest.json").read_bytes()).hexdigest()}
    head["content_sha256"] = hashlib.sha256(_core_canonical({
        key: value for key, value in head.items() if key != "content_sha256"
    }).encode("utf-8")).hexdigest()
    (root / "HEAD.json").write_bytes(canonical_bytes(head))
    return generation_id


def _b4_reader_durable_suppression(row, recorded_at):
    """Complete the durable suppression envelope the nightly writer commits.

    ``reconcile_observations`` returns the content-addressed suppression without the
    two fields only the durable write adds (``recorded_at`` and ``content_sha256``);
    the ``suppression_id`` address deliberately excludes both, so sealing is additive.
    """
    sealed = {**row, "recorded_at": recorded_at}
    sealed["content_sha256"] = hashlib.sha256(_core_canonical({
        key: value for key, value in sealed.items() if key != "content_sha256"
    }).encode("utf-8")).hexdigest()
    return sealed


def _b4_reader_quote_row(*, symbol="UNIT", quote_price=42.70, prev_close=42.10,
                         quote_ts="2026-09-17T19:30:00Z", source="polygon",
                         private=True):
    from scripts.build_live_quotes import to_worker_quotes

    raw = {symbol: {"price": quote_price, "prev_close": prev_close, "change_pct": 0.58,
                    "ts_ms": None, "source": source, "quote_ts": quote_ts,
                    "quote_ts_synthetic": False, "price_basis": "trade",
                    "delay_min": 0.1}}
    rows = to_worker_quotes(raw, include_private_provenance=private)
    return rows[symbol]


def _b4_reader_world(
    tmp_path,
    *,
    observations=None,
    events=None,
    suppressions=(),
    candidate_inputs=1,
    session="2026-09-17",
    pass_at=None,
    quote_ts=None,
    quote_price=42.70,
    prev_close=42.10,
    live_artifact=None,
    quote_row_overrides=None,
    drop_private_provenance=False,
    envelope_overrides=None,
    write_quotes_file=True,
    write_live_file=True,
    source_known_at=None,
    store_recorded_at=None,
):
    source_event_id = f"candidate:{session}:UNIT:gap_continuation"
    recorded_at = store_recorded_at or f"{session}T21:00:00Z"
    pass_at = pass_at or f"{session}T19:30:08Z"
    quote_ts = quote_ts or f"{session}T19:30:00Z"
    if events is None:
        observations = observations if observations is not None else [
            _b4_reader_observation(day=session, source_event_id=source_event_id,
                                   known_at=source_known_at)
        ]
        observed = reconcile_observations(
            [], observations, recorded_at=recorded_at, definition_era=DEFAULT_DEFINITION_ERA
        )
        events, suppressions = observed.events, list(observed.suppressions)
    store_root = tmp_path / "data" / "us_prophet_rank" / "episodes"
    generation_id = _b4_reader_store(
        store_root, events=events, suppressions=list(suppressions),
        candidate_inputs=candidate_inputs,
        suppressed_inputs=len(list(suppressions)) if events is not None else 0,
        recorded_at=recorded_at,
    )
    snapshot = load_candidate_episode_store_snapshot(store_root)
    assert snapshot.generation_id == generation_id
    # Revalidation: the fixture store survives the incumbent full-generation reader.
    revalidated = validate_candidate_episode_generation(
        store_root / "generations" / generation_id
    )
    assert len(revalidated.episodes) == len(snapshot.generation.episodes)

    live_root = tmp_path / "native-live"
    if live_artifact is None:
        live_artifact = _b4_owner_live_artifact(
            "UNIT", pass_at=pass_at, quote_ts=quote_ts, quote_price=quote_price,
            as_of_close=prev_close,
        )
    row = _b4_reader_quote_row(symbol="UNIT", quote_price=quote_price,
                               prev_close=prev_close, quote_ts=quote_ts)
    if drop_private_provenance:
        row.pop("quote_ts")
        row.pop("quote_ts_synthetic")
    for key, value in (quote_row_overrides or {}).items():
        row[key] = value
    envelope = {
        "sessions": {"us": {"phase": "rth"}},
        "ts": int(datetime.fromisoformat(
            f"{session}T19:31:00Z".replace("Z", "+00:00")).timestamp() * 1000),
        "asof": f"{session}T19:31:00Z",
        "source": "snapshot",
        "quotes": {"UNIT": row},
        "meta": {"requested": 1, "resolved": 1, "offline": False},
    }
    for key, value in (envelope_overrides or {}).items():
        envelope[key] = value

    state_dir = live_root / "state"
    public_dir = live_root / "public" / "live"
    quotes_path = state_dir / "quotes_full.json"
    live_path = public_dir / "prophet_live.json"
    quotes_bytes = json.dumps(envelope, separators=(",", ":")).encode("utf-8") + b"\n"
    # The served owner file carries the publish step of the producing script (the
    # evaluator stamps meta.producer immediately before writing the served copy) —
    # reproduce that step exactly as the VPS file is actually written.
    published = copy.deepcopy(live_artifact)
    published.setdefault("meta", {})["producer"] = _sources._LIVE_OWNER_PRODUCER
    live_bytes = json.dumps(published, separators=(",", ":")).encode("utf-8") + b"\n"
    if write_quotes_file:
        state_dir.mkdir(parents=True, exist_ok=True)
        quotes_path.write_bytes(quotes_bytes)
    if write_live_file:
        public_dir.mkdir(parents=True, exist_ok=True)
        live_path.write_bytes(live_bytes)

    return {
        "tmp_path": tmp_path,
        "store_root": store_root,
        "generation_id": generation_id,
        "snapshot": snapshot,
        "source_event_id": source_event_id,
        "source_receipt": _READER_SOURCE_RECEIPT,
        "live_root": live_root,
        "quotes_path": quotes_path,
        "live_path": live_path,
        "quotes_bytes": quotes_bytes,
        "live_bytes": live_bytes,
        "quotes_digest": "sha256:" + hashlib.sha256(quotes_bytes).hexdigest(),
        "live_digest": "sha256:" + hashlib.sha256(live_bytes).hexdigest(),
        "live_artifact": live_artifact,
    }


def _b4_reader_run(world, **overrides):
    call = {
        "repo_root": world["tmp_path"],
        "snapshot": world["snapshot"],
        "candidate_source_event_id": world["source_event_id"],
        "candidate_source_receipt": world["source_receipt"],
        "native_live_root": world["live_root"],
        "alias_table": _B4Aliases("UNIT"),
    }
    call.update(overrides)
    return read_native_b4_owner_inputs(**call)


def _b4_reader_world_with_policy(tmp_path, policy=None, *, drop=False):
    """A world whose live owner discloses the given freshness policy (or none).

    The served owner file is rewritten exactly as the producing script writes it;
    everything else in the world is untouched.
    """
    world = _b4_reader_world(tmp_path)
    payload = json.loads(world["live_bytes"])
    if drop:
        payload["meta"].pop("quote_freshness_policy", None)
    else:
        payload["meta"]["quote_freshness_policy"] = policy
    world["live_path"].write_bytes(
        json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n")
    return world


def test_b4_native_reader_reads_the_qualified_private_owner_fact(tmp_path):
    world = _b4_reader_world(tmp_path, source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    out = _b4_reader_run(world)

    assert out["unavailable_reasons"] == []
    assert out["availability"] is None
    assert out["quote_freshness"] == "FRESH"
    quote_input = out["quote_input"]
    expected_quote_input = {
        "schema": "prophet.daily_brief_quote_input/v1",
        "owner_ref": "state/quotes_full.json",
        "live_owner_ref": "public/live/prophet_live.json",
        "asof": "2026-09-17T19:45:00Z",
        "quotes_source_receipt": world["quotes_digest"],
        "live_source_receipt": world["live_digest"],
        "live_policy": {
            "schema": "prophet_live.quote_freshness_policy/v1",
            "quote_max_age_min": 25.0,
            "resolution": "derived",
        },
        "state": "CURRENT",
        "security_id": "SEC:US-XNAS-AAPL",
        "episode_id": quote_input["episode_id"],
        "candidate_generation_id": world["generation_id"],
        "market_session": "2026-09-17",
        "observed_at": "2026-09-17T19:30:00Z",
        "read_completed_at": "2026-09-17T19:45:00Z",
        "price": 42.7,
        "basis": UNADJUSTED,
        "quote_age_at_own_read_min": 15.0,
    }
    # The input's receipt is the COMPOSITE binding — both owner files as read, the
    # disclosed policy the read was re-aged against, the native binding and both
    # clocks — not the quote file alone.
    expected_quote_input["source_receipt"] = _sources.quote_input_receipt(
        expected_quote_input)
    assert quote_input == expected_quote_input
    assert quote_input["source_receipt"] != world["quotes_digest"]
    # The read's own completion clock and session are disclosed facts.
    assert out["clocks"]["read_completed_at"] == "2026-09-17T19:45:00Z"
    assert out["clocks"]["read_session_et"] == "2026-09-17"
    assert out["observed"]["quote_age_at_own_read_min"] == 15.0
    assert out["owner_reads"]["prophet_live"]["quote_freshness_policy"] == {
        "schema": "prophet_live.quote_freshness_policy/v1",
        "quote_max_age_min": 25.0,
        "resolution": "derived",
    }
    assert quote_input["episode_id"].startswith("pe:SEC:US-XNAS-AAPL:epoch_0:sa:")
    # The existing Daily Brief consumer accepts the emitted receipt shape as its
    # quote owner input — the reader speaks the incumbent contract, not a new one.
    from engine.prophet_daily_brief import _QUOTE_SCHEMA, _bound_record

    assert _bound_record(quote_input, _QUOTE_SCHEMA, "quote") is quote_input

    assert out["binding"]["store_symbol"] == "UNIT"
    assert out["binding"]["market_session"] == "2026-09-17"
    assert out["native"]["source_system"] == "candidate"
    assert out["native"]["source_schema"] == "us_prophet_rank.candidates/v1"
    assert out["native"]["source_event_type"] == "OPENED"
    assert out["native"]["source_receipt"] == _READER_SOURCE_RECEIPT
    assert out["native"]["anchor"]["kind"] == "turn_watch_reset_low"
    assert out["native"]["store_byte_token"]["generation_id"] == world["generation_id"]
    assert out["basis"]["quote_family"] == UNADJUSTED
    assert out["basis"]["levels_family"] == ADJUSTED
    assert out["basis"]["prev_close"] == 42.10
    assert out["observed"]["quote_rung"] == "trade"
    assert out["clocks"]["quote_observed_at"] == "2026-09-17T19:30:00Z"
    assert "candidate_state_projection_id" not in json.dumps(out)
    # Every input byte is untouched by the read.
    assert world["quotes_path"].read_bytes() == world["quotes_bytes"]
    assert world["live_path"].read_bytes() == world["live_bytes"]


def test_b4_native_reader_reages_the_quote_at_its_own_read_completion(
        tmp_path, monkeypatch):
    """The repair: a Sept-17 19:30Z quote is NOT magically CURRENT at 21:01.

    The pass that produced the artifact gated the quote fresh at ITS pass; the read
    that consumes it re-answers the same question at the reader's OWN completion
    clock, against the artifact's OWN disclosed ceiling — never against today's
    config, and never by restamping the quote. The aged-out read publishes nothing.
    """
    world = _b4_reader_world(tmp_path)
    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 9, 17, 21, 1, 0, tzinfo=timezone.utc))
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["QUOTE_STALE_AT_OWN_READ"]
    assert out["quote_input"] is None and out["availability"] is None
    assert out["quote_freshness"] is None
    assert "91.0 min vs disclosed limit 25.0 min" in out["notes"][0]
    # No restamp: both owner files and the native store are untouched by the read.
    assert world["quotes_path"].read_bytes() == world["quotes_bytes"]
    assert world["live_path"].read_bytes() == world["live_bytes"]


def test_b4_native_reader_refuses_an_own_read_in_a_later_session(
        tmp_path, monkeypatch):
    """The read's own completion ET session must still be the candidate's session.

    The actual observed failure: the Sept-17 fixture read back on Oct 13 came back
    CURRENT with no reasons at all. Both honest checks now fire together — and a
    next-ET-session read at a fresh clock time fires the session check alone.
    """
    world = _b4_reader_world(tmp_path)
    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 10, 13, 0, 10, 30, tzinfo=timezone.utc))
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["READ_SESSION_CROSS_SESSION",
                                          "QUOTE_STALE_AT_OWN_READ"]
    assert out["quote_input"] is None and out["availability"] is None
    assert out["clocks"] is None, "a refused read publishes no clocks at all"

    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 9, 18, 19, 35, 0, tzinfo=timezone.utc))
    next_day = _b4_reader_run(world)
    # A day later the quote is ALSO a day stale — both honest checks fire.
    assert next_day["unavailable_reasons"] == ["READ_SESSION_CROSS_SESSION",
                                               "QUOTE_STALE_AT_OWN_READ"]
    assert next_day["quote_input"] is None
    assert "1445.0 min vs disclosed limit 25.0 min" in next_day["notes"][0]


def test_b4_native_reader_own_read_freshness_boundary_is_exact(
        tmp_path, monkeypatch):
    """The own-read gate is the SAME ``age <= limit`` comparison the lane runs.

    Exactly at the derived 25-minute ceiling the read is still CURRENT; half a
    minute past it the raw age exceeds the limit and the read publishes nothing,
    with the disclosed age at the native 1-dp rounding.
    """
    world = _b4_reader_world(tmp_path, source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 9, 17, 19, 55, 0, tzinfo=timezone.utc))
    fresh = _b4_reader_run(world)
    assert fresh["unavailable_reasons"] == []
    assert fresh["quote_input"]["state"] == "CURRENT"
    assert fresh["quote_input"]["quote_age_at_own_read_min"] == 25.0
    assert fresh["observed"]["quote_age_at_own_read_min"] == 25.0

    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 9, 17, 19, 55, 30, tzinfo=timezone.utc))
    stale = _b4_reader_run(world)
    assert stale["unavailable_reasons"] == ["QUOTE_STALE_AT_OWN_READ"]
    assert stale["quote_input"] is None
    assert "25.5 min vs disclosed limit 25.0 min" in stale["notes"][0]


def test_b4_native_reader_reages_against_the_artifacts_own_disclosed_policy(
        tmp_path, monkeypatch):
    """The verdict follows the ARTIFACT's disclosed ceiling, not the reader's.

    An explicit operator ceiling armed into the producing pass binds the read:
    15 minutes after the quote is fresh under the derived 25 but stale under an
    explicit 12 — and exactly at 12.0 it is fresh again. No in-code fallback.
    """
    strict_live = _b4_owner_live_artifact(
        "UNIT", pass_at="2026-09-17T19:30:08Z", quote_ts="2026-09-17T19:30:00Z",
        cfg=LS.live_cfg({"prophet_live": {"quote_max_age_min": 12}}),
    )
    assert strict_live["meta"]["quote_freshness_policy"] == {
        "schema": "prophet_live.quote_freshness_policy/v1",
        "quote_max_age_min": 12.0,
        "resolution": "explicit",
    }
    world = _b4_reader_world(tmp_path, live_artifact=strict_live,
                             source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 9, 17, 19, 45, 0, tzinfo=timezone.utc))
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["QUOTE_STALE_AT_OWN_READ"]
    assert "15.0 min vs disclosed limit 12.0 min" in out["notes"][0]

    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 9, 17, 19, 42, 0, tzinfo=timezone.utc))
    ok = _b4_reader_run(world)
    assert ok["unavailable_reasons"] == []
    assert ok["quote_input"]["live_policy"] == {
        "schema": "prophet_live.quote_freshness_policy/v1",
        "quote_max_age_min": 12.0,
        "resolution": "explicit",
    }
    assert ok["quote_input"]["source_receipt"] == _sources.quote_input_receipt(
        ok["quote_input"])


def test_b4_native_reader_binds_the_disclosed_threshold_into_the_input_receipt(
        tmp_path, monkeypatch):
    """No today's-config assumption in either direction.

    Whatever ceiling the owner plane actually discloses decides the read AND is
    bound into the composite receipt — the same qualifying read under a different
    disclosed policy yields a different receipt, and the live file bytes it was
    read from are committed beside the quote file bytes.
    """
    world = _b4_reader_world(tmp_path, source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    monkeypatch.setattr(_sources, "_now_utc",
                        lambda: datetime(2026, 9, 17, 19, 40, 0, tzinfo=timezone.utc))
    derived = _b4_reader_run(world)["quote_input"]
    assert derived["live_policy"]["quote_max_age_min"] == 25.0

    loosened = json.loads(world["live_bytes"])
    loosened["meta"]["quote_freshness_policy"]["quote_max_age_min"] = 1e9
    world["live_path"].write_bytes(
        json.dumps(loosened, separators=(",", ":")).encode("utf-8") + b"\n")
    loosened_input = _b4_reader_run(world)["quote_input"]
    assert loosened_input["live_policy"]["quote_max_age_min"] == 1e9
    assert loosened_input["source_receipt"] != derived["source_receipt"]
    assert loosened_input["live_source_receipt"] == "sha256:" + hashlib.sha256(
        world["live_path"].read_bytes()).hexdigest()
    assert _sources.quote_input_receipt(loosened_input) == \
        loosened_input["source_receipt"]


@pytest.mark.parametrize("bad_policy", [
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": float("nan"), "resolution": "derived"},
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": float("inf"), "resolution": "derived"},
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": 0, "resolution": "derived"},
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": -25.0, "resolution": "derived"},
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": True, "resolution": "derived"},
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": "25", "resolution": "derived"},
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": 25.0, "resolution": "today_guess"},
    {"schema": "prophet_live.quote_freshness_policy/v1",
     "quote_max_age_min": 25.0},
])
def test_b4_native_reader_refuses_malformed_disclosed_thresholds(tmp_path,
                                                                 bad_policy):
    """The disclosed bound must be a finite positive NON-BOOL number under a known
    resolution class; anything else types the whole read unavailable."""
    world = _b4_reader_world_with_policy(tmp_path, bad_policy)
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["LIVE_FRESHNESS_POLICY_MALFORMED"]
    assert out["quote_input"] is None and out["availability"] is None
    assert out["quote_freshness"] is None


def test_b4_native_reader_missing_historical_policy_cannot_fall_back(tmp_path):
    """An artifact from before the disclosure has NO lawful ceiling here.

    Today's config is never stamped onto it — the read types unavailable instead
    of re-aging against ``live_cfg``'s current derivation.
    """
    world = _b4_reader_world_with_policy(tmp_path, drop=True)
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["LIVE_FRESHNESS_POLICY_MISSING"]
    assert out["quote_input"] is None and out["availability"] is None
    assert out["quote_freshness"] is None


def test_b4_native_reader_refuses_a_dark_live_row(tmp_path):
    """A quote the owner itself published dark is not a latest quote."""
    world = _b4_reader_world(tmp_path)
    dark_row = json.loads(world["live_bytes"])
    dark_row["states"]["UNIT"] = {"state": "dark", "reason": "stale_quote"}
    world["live_path"].write_bytes(
        json.dumps(dark_row, separators=(",", ":")).encode("utf-8") + b"\n")
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["LIVE_ROW_DARK"]
    assert out["notes"][0] == "stale_quote"


def test_b4_native_reader_fixture_store_persists_and_revalidates(tmp_path):
    world = _b4_reader_world(tmp_path)
    token = attest = None
    from engine.us_candidate_episode import attest_candidate_episode_store_bytes

    token = attest_candidate_episode_store_bytes(world["store_root"])
    assert token.generation_id == world["generation_id"]
    reloaded = load_candidate_episode_store_snapshot(world["store_root"])
    assert _core_canonical(tuple(reloaded.generation.events)) == _core_canonical(
        tuple(world["snapshot"].generation.events)
    )


def test_b4_native_reader_refuses_a_source_digest_that_resolves_no_event(tmp_path):
    world = _b4_reader_world(tmp_path)
    out = _b4_reader_run(world, candidate_source_receipt="sha256:" + "f" * 64)
    assert out["unavailable_reasons"] == ["CANDIDATE_SOURCE_EVENT_NOT_FOUND"]
    assert out["quote_input"] is None and out["availability"] is None


def test_b4_native_reader_refuses_malformed_source_keys(tmp_path):
    world = _b4_reader_world(tmp_path)
    for bad_key in (
        "candidate:2026-9-17:UNIT:gap",
        "candidate:2026-02-30:UNIT:gap",
        "candidate:2026-09-17:UNIT",
        "watch:2026-09-17:UNIT:gap",
        "candidate",
    ):
        out = _b4_reader_run(world, candidate_source_event_id=bad_key)
        assert out["unavailable_reasons"] == ["CANDIDATE_SOURCE_KEY_INVALID"], bad_key


def test_b4_native_reader_refuses_a_suppressed_source_key(tmp_path):
    world = _b4_reader_world(
        tmp_path, observations=[_b4_reader_observation(anchor_kind=None)],
        candidate_inputs=1,
    )
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["CANDIDATE_SOURCE_KEY_SUPPRESSED"]
    assert out["quote_input"] is None and out["availability"] is None


def test_b4_native_reader_refuses_a_retracted_source_observation(tmp_path):
    opened = reconcile_observations(
        [], [_b4_reader_observation()], recorded_at="2026-09-17T21:00:00Z",
        definition_era=DEFAULT_DEFINITION_ERA,
    )
    episode_id_text = opened.episodes[0]["episode_id"]
    retraction = {
        "event_type": "RETRACTED", "episode_id": episode_id_text,
        "source_system": "operator", "source_schema": "candidate-command/v1",
        "source_event_id": "retract:1", "source_receipt": "sha256:" + "b" * 64,
        "occurred_at": "2026-09-17T20:30:00Z", "known_at": "2026-09-17T20:30:00Z",
        "correction_of": opened.events[0]["event_id"],
        "payload": {"reason": "source withdrew the observation"},
    }
    result = apply_commands(
        opened.events, [retraction], recorded_at="2026-09-17T21:00:00Z",
        definition_era=DEFAULT_DEFINITION_ERA,
    )
    world = _b4_reader_world(tmp_path, events=result.events, candidate_inputs=1)
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["CANDIDATE_SOURCE_EVENT_RETRACTED"]
    assert out["quote_input"] is None and out["availability"] is None


def test_b4_native_reader_refuses_identity_that_does_not_round_trip(tmp_path):
    world = _b4_reader_world(tmp_path)
    out = _b4_reader_run(world, alias_table=_B4Aliases("UNIT", reverse="SEC:OTHER"))
    assert out["unavailable_reasons"] == ["IDENTITY_ALIAS_UNRESOLVED"]


def test_b4_native_reader_refuses_synthetic_or_public_quote_rows(tmp_path):
    world = _b4_reader_world(
        tmp_path, quote_row_overrides={"quote_ts_synthetic": True}
    )
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_TS_SYNTHETIC"]

    world = _b4_reader_world(tmp_path, drop_private_provenance=True)
    assert _b4_reader_run(world)["unavailable_reasons"] == [
        "QUOTE_PRIVATE_PROVENANCE_MISSING"
    ]

    world = _b4_reader_world(tmp_path, quote_row_overrides={"source": "test"})
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_SOURCE_UNTRUSTED"]

    world = _b4_reader_world(
        tmp_path, quote_row_overrides={"basis": "adjusted_close"}
    )
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_RUNG_UNTRUSTED"]


def test_b4_native_reader_refuses_price_close_or_clock_drift(tmp_path):
    # Only the QUOTE row drifts; the live owner still measures 42.70.
    world = _b4_reader_world(tmp_path, quote_row_overrides={"price": 42.71})
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_PRICE_MISMATCH"]

    # Only the QUOTE row's previous close drifts from the owner's measured close.
    world = _b4_reader_world(tmp_path, quote_row_overrides={"prevClose": 40.0})
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_PREV_CLOSE_MISMATCH"]

    # A quote stamped after the live pass never becomes the pass's own observation.
    after_pass = datetime.fromisoformat("2026-09-17T19:31:30+00:00")
    world = _b4_reader_world(tmp_path, quote_row_overrides={
        "quote_ts": "2026-09-17T19:31:30Z",
        "ts": int(after_pass.timestamp() * 1000),
    })
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_AFTER_PASS"]

    # A quote_ts the live owner's measured quote_age_min does not agree with.
    drifted_clock = datetime.fromisoformat("2026-09-17T19:29:00+00:00")
    world = _b4_reader_world(tmp_path, quote_row_overrides={
        "quote_ts": "2026-09-17T19:29:00Z",
        "ts": int(drifted_clock.timestamp() * 1000),
    })
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_AGE_MISMATCH"]


def test_b4_native_reader_refuses_missing_or_offline_owner_planes(tmp_path):
    world = _b4_reader_world(tmp_path, write_quotes_file=False)
    assert _b4_reader_run(world)["unavailable_reasons"] == ["OWNER_FILE_MISSING"]

    world = _b4_reader_world(
        tmp_path, envelope_overrides={"meta": {"requested": 1, "resolved": 1,
                                               "offline": True}}
    )
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_ENVELOPE_OFFLINE"]

    world = _b4_reader_world(
        tmp_path, envelope_overrides={"source": "worker"}
    )
    assert _b4_reader_run(world)["unavailable_reasons"] == ["QUOTE_ENVELOPE_UNTRUSTED"]


def test_b4_native_reader_refuses_a_live_owner_that_is_not_the_native_producer(tmp_path):
    def world_with_live_payload(payload):
        world = _b4_reader_world(tmp_path)
        world["live_path"].write_bytes(
            json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        )
        return world

    foreign = json.loads(_b4_reader_world(tmp_path)["live_bytes"])
    foreign["meta"]["producer"] = "other/writer.py"
    out = _b4_reader_run(world_with_live_payload(foreign))
    assert out["unavailable_reasons"] == ["LIVE_OWNER_PRODUCER_MISMATCH"]

    dark_status = json.loads(_b4_reader_world(tmp_path)["live_bytes"])
    dark_status["status"] = "dark"
    out = _b4_reader_run(world_with_live_payload(dark_status))
    assert out["unavailable_reasons"] == ["LIVE_OWNER_NOT_LIVE"]


def test_b4_native_reader_refuses_a_live_session_off_the_candidate_source_day(tmp_path):
    world = _b4_reader_world(
        tmp_path, pass_at="2026-09-18T19:30:08Z", quote_ts="2026-09-18T19:30:00Z"
    )
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["SESSION_RELATION_UNREPRESENTABLE"]
    assert out["quote_input"] is None and out["availability"] is None


def test_b4_native_reader_refuses_a_tampered_basis_material_in_the_live_owner(tmp_path):
    tampered = copy.deepcopy(_b4_reader_world(tmp_path)["live_artifact"])
    state = tampered["states"]["UNIT"]
    state["basis_relation"]["subject"] = "OTHER"
    world = _b4_reader_world(tmp_path, live_artifact=tampered)
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["LIVE_BASIS_NOT_RESOLVED"]
    assert "binds a different subject" in out["notes"][0]


def test_b4_native_reader_refuses_a_snapshot_that_diverged_from_head(tmp_path):
    world = _b4_reader_world(tmp_path)
    # A later generation lands (a second candidate) and HEAD advances past the
    # snapshot the caller supplied — the caller's cut is no longer the store.
    _b4_reader_store(
        world["store_root"],
        events=reconcile_observations(
            world["snapshot"].generation.events,
            [_b4_reader_observation(
                source_event_id="candidate:2026-09-17:OTHER:gap_continuation",
                security_id="SEC:US-XNAS-OTHER", company_id="ISS:US-XNAS-OTHER",
                ticker="OTHER")],
            recorded_at="2026-09-17T21:00:00Z",
            definition_era=DEFAULT_DEFINITION_ERA,
        ).events,
        candidate_inputs=2,
        recorded_at="2026-09-17T21:00:00Z",
    )
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["SNAPSHOT_DIVERGED_FROM_HEAD"]


def test_b4_native_reader_refuses_bytes_that_change_between_reads(tmp_path, monkeypatch):
    world = _b4_reader_world(tmp_path)
    real_read = _sources._read_owner_bytes
    calls = {"n": 0}

    def flaky_read(path):
        calls["n"] += 1
        payload = real_read(path)
        if calls["n"] == 3 and path.name == "quotes_full.json":
            return payload + b" "
        return payload

    monkeypatch.setattr(_sources, "_read_owner_bytes", flaky_read)
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["OWNER_BYTES_CHANGED"]
    assert out["quote_input"] is None and out["availability"] is None


def test_b4_native_reader_rejects_future_owner_clocks(tmp_path):
    world = _b4_reader_world(tmp_path, session="2027-01-04")
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["FUTURE_OWNER_CLOCK"]
    assert out["quote_input"] is None and out["availability"] is None


def test_b4_native_reader_touches_no_network_scoring_or_write_plane(
    tmp_path, monkeypatch
):
    def boom(*args, **kwargs):
        raise AssertionError("reader touched a forbidden plane")

    import socket

    from engine.prophet_live import r2io
    from scripts import build_live_quotes

    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(_sources, "evaluate_entry_availability", boom)
    monkeypatch.setattr(r2io, "put_json", boom)
    monkeypatch.setattr(build_live_quotes, "build", boom)

    world = _b4_reader_world(tmp_path, source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == []
    assert out["availability"] is None and out["quote_input"] is not None


def test_b4_native_reader_rejects_caller_json_in_place_of_the_store_snapshot(tmp_path):
    world = _b4_reader_world(tmp_path)
    with pytest.raises(TypeError, match="CandidateEpisodeStoreSnapshot"):
        _b4_reader_run(world, snapshot={
            "generation_id": world["generation_id"], "json": True,
        })


def _b4_world_with_native_state_command(tmp_path, *, state=None, supersede=False):
    from engine.us_candidate_episode import episode_id as native_episode_id
    opened = reconcile_observations(
        [], [_b4_reader_observation(known_at=_QUALIFIED_SOURCE_KNOWN_AT)],
        recorded_at=_QUALIFIED_RECORDED_AT, definition_era=DEFAULT_DEFINITION_ERA)
    row = opened.episodes[0]
    command = {
        "event_type": "IDENTITY_SUPERSEDED" if supersede else "STATE_TRANSITIONED",
        "episode_id": row["episode_id"], "source_system": "stock_identity" if supersede else "operator",
        "source_schema": "stock_identity.epoch/v1" if supersede else "candidate-command/v1",
        "source_event_id": "identity:successor" if supersede else "state:" + state,
        "source_receipt": "sha256:" + "d" * 64,
        "occurred_at": "2026-09-17T19:05:00Z", "known_at": "2026-09-17T19:05:00Z",
        "payload": ({"successor_episode_id": native_episode_id(row["security_id"], "epoch_1", row["structural_anchor"], 1),
                     "reason": "native identity epoch superseded"} if supersede else
                    {"episode_state": state, "terminal_reason": "native terminal transition"}),
    }
    changed = apply_commands(opened.events, [command], recorded_at=_QUALIFIED_RECORDED_AT,
                             definition_era=DEFAULT_DEFINITION_ERA)
    world = _b4_reader_world(tmp_path, events=changed.events, candidate_inputs=1,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    actual = world["snapshot"].generation.episodes[0]
    assert "episode_lifecycle" not in actual
    assert actual["episode_state"] == ("ACTIVE" if supersede else state)
    assert bool(actual["superseded_by"]) is supersede
    return world


@pytest.mark.parametrize("state", ["INVALIDATED", "RESOLVED", "EXPIRED", "RETRACTED"])
def test_b4_native_reader_refuses_native_terminal_episode_state(tmp_path, state):
    world = _b4_world_with_native_state_command(tmp_path, state=state)
    before = {p: p.read_bytes() for p in world["store_root"].rglob("*") if p.is_file()}
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["CANDIDATE_EPISODE_TERMINAL"]
    assert out["quote_input"] is None and out["availability"] is None
    assert {p: p.read_bytes() for p in before} == before


def test_b4_native_reader_refuses_native_superseded_active_episode(tmp_path):
    world = _b4_world_with_native_state_command(tmp_path, supersede=True)
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["CANDIDATE_EPISODE_SUPERSEDED"]
    assert out["quote_input"] is None and out["availability"] is None


@pytest.mark.parametrize("field,value,missing", [
    ("episode_state", None, True), ("episode_state", None, False),
    ("episode_state", "SUPERSEDED", False), ("episode_state", [], False),
    ("terminal_reason", None, True), ("superseded_by", None, True),
])
def test_b4_native_reader_refuses_caller_malformed_native_owner_state(tmp_path, field, value, missing):
    world = _b4_reader_world(tmp_path, source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    row = world["snapshot"].generation.episodes[0]
    if missing:
        row.pop(field)
    else:
        row[field] = value
    out = _b4_reader_run(world)
    # The actual fixed store remains valid; a caller's counterfeit native row
    # cannot override it, including by copying B3 display vocabulary onto B1.
    assert out["unavailable_reasons"] == ["SNAPSHOT_DIVERGED_FROM_HEAD"]
    assert out["quote_input"] is None and out["availability"] is None


@pytest.mark.parametrize("field,value,missing", [
    ("episode_state", None, True), ("episode_state", None, False),
    ("episode_state", "SUPERSEDED", False), ("episode_state", [], False),
    ("terminal_reason", None, True), ("superseded_by", None, True),
])
def test_b4_native_reader_typed_failure_on_native_decoder_contract_regression(tmp_path, monkeypatch, field, value, missing):
    world = _b4_reader_world(tmp_path, source_known_at=_QUALIFIED_SOURCE_KNOWN_AT,
                             store_recorded_at=_QUALIFIED_RECORDED_AT)
    row = world["snapshot"].generation.episodes[0]
    if missing:
        row.pop(field)
    else:
        row[field] = value
    # Deliberate upstream decoder contract violation: both decoded cuts are the
    # same malformed result, while real store bytes remain untouched. This does
    # not claim malformed native bytes were accepted by the real B1 validator.
    monkeypatch.setattr(_sources, "load_candidate_episode_store_snapshot", lambda root: world["snapshot"])
    out = _b4_reader_run(world)
    assert out["unavailable_reasons"] == ["CANDIDATE_EPISODE_STATE_MALFORMED"]
    assert out["quote_input"] is None and out["availability"] is None
