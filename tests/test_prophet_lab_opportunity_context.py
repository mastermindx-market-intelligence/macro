from copy import deepcopy
from dataclasses import dataclass

import pytest

from engine.prophet_candidate_state import project_candidate_states
from engine.prophet_entry_availability import evaluate_entry_availability
from engine.prophet_lab.contracts import ALL_FALSE_AUTHORITY
from engine.prophet_lab.opportunity_context import (
    OpportunityContextContractError,
    compose_opportunity_context,
    validate_opportunity_context,
)
from engine.prophet_strategy_definition import (
    build_early_leadership_sector_rotation_definition,
)


GEN = "peg:" + "a" * 64


def eid(label="1"):
    digest = label.encode("utf-8").hex().ljust(24, "0")[:24]
    return f"pe:SEC:US-XNAS-AAPL:epoch_0:sa:{digest}:1"


@dataclass(frozen=True)
class Gen:
    episodes: tuple


@dataclass(frozen=True)
class Snap:
    generation_id: str
    generation: Gen


def episode(state="ACTIVE", terminal_reason=None):
    return {
        "schema": "prophet.candidate_episode/v1",
        "episode_id": eid(),
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


def projection(*, generated_at="2026-09-18T19:30:00Z", state="ACTIVE"):
    return project_candidate_states(
        Snap(GEN, Gen((episode(state, "expired" if state == "EXPIRED" else None),))),
        market_session="2026-09-18",
        generated_at=generated_at,
        emergence_by_episode={
            eid(): {
                "state": "TRIGGERED",
                "reason": None,
                "source_system": "turn_watch",
                "source_token": "B1_OBSERVED",
                "source_ref": "pee:" + "b" * 64,
            }
        },
    )


def facts():
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


def availability(p=None):
    p = p or projection()
    return evaluate_entry_availability(
        p,
        episode_id=eid(),
        strategy_definition=build_early_leadership_sector_rotation_definition(),
        facts=facts(),
    )


def test_missing_b4_stays_unknown_and_mints_no_permission():
    out = compose_opportunity_context(projection(), episode_id=eid())
    assert out["fresh_entry"]["state"] == "UNAVAILABLE_DATA"
    assert out["fresh_entry"]["entry_open"] is None
    assert out["fresh_entry"]["availability_id"] is None
    assert out["fresh_entry"]["blockers"] == ["B4_NOT_AVAILABLE"]
    assert out["user_state"]["state"] == "NOT_JOINED"
    assert out["forecast"]["qualified"] is False
    assert out["forecast"]["heads"] is None
    assert out["authority"] == ALL_FALSE_AUTHORITY
    validate_opportunity_context(out)


def test_owner_issued_b4_is_projected_without_recomputing_it():
    p = projection()
    b4 = availability(p)
    out = compose_opportunity_context(p, episode_id=eid(), entry_availability=b4)
    assert out["fresh_entry"]["state"] == "ENTRY_OPEN"
    assert out["fresh_entry"]["entry_open"] is True
    assert out["fresh_entry"]["availability_id"] == b4["availability_id"]
    assert out["fresh_entry"]["strategy"]["strategy_definition_id"] == b4["strategy_definition_id"]
    assert out["fresh_entry"]["current_price"] == {
        "value": 42.7,
        "basis": "adjusted:v7",
        "asof": "2026-09-18T19:30:00Z",
        "age_seconds": 8,
    }
    assert out["fresh_entry"]["zone"] == b4["zone"]
    assert out["fresh_entry"]["source_receipts"] == b4["source_receipts"]


def test_b4_from_another_candidate_projection_is_refused():
    old = projection(generated_at="2026-09-18T19:29:00Z")
    b4 = availability(old)
    with pytest.raises(
        OpportunityContextContractError,
        match="candidate_state_projection_id",
    ):
        compose_opportunity_context(
            projection(),
            episode_id=eid(),
            entry_availability=b4,
        )


def test_terminal_episode_does_not_infer_a_fresh_entry_verdict():
    out = compose_opportunity_context(
        projection(state="EXPIRED"),
        episode_id=eid(),
    )
    assert out["native_phase"]["episode_lifecycle"]["state"] == "CLOSED"
    assert out["fresh_entry"]["state"] == "UNAVAILABLE_DATA"
    assert out["fresh_entry"]["entry_open"] is None


def test_unknown_episode_is_refused_not_joined_by_ticker():
    with pytest.raises(
        OpportunityContextContractError,
        match="exactly one canonical B3 row",
    ):
        compose_opportunity_context(projection(), episode_id=eid("other"))


def test_context_does_not_accept_or_infer_private_plan_or_forecast_state():
    p = projection()
    out = compose_opportunity_context(
        p,
        episode_id=eid(),
        entry_availability=availability(p),
    )
    assert out["user_state"] == {
        "state": "NOT_JOINED",
        "plan_ref": None,
        "position_ref": None,
        "reason": "PRIVATE_OWNER_NOT_READ",
    }
    assert out["evidence_summary"]["support"] is None
    assert out["evidence_summary"]["contradiction"] is None
    assert out["evidence_summary"]["next_observable"] is None
    assert out["forecast"] == {
        "qualified": False,
        "heads": None,
        "reason": "NO_QUALIFIED_OLI_FORECAST",
    }


def test_closed_contract_rejects_authority_or_user_state_laundering():
    out = compose_opportunity_context(projection(), episode_id=eid())
    bad = deepcopy(out)
    bad["authority"]["ranking"] = True
    with pytest.raises(OpportunityContextContractError, match="authority"):
        validate_opportunity_context(bad)

    bad = deepcopy(out)
    bad["user_state"]["state"] = "entered"
    with pytest.raises(OpportunityContextContractError, match="private user state"):
        validate_opportunity_context(bad)


def test_missing_b4_cannot_be_relabelled_as_false_entry_permission():
    out = compose_opportunity_context(projection(), episode_id=eid())
    bad = deepcopy(out)
    bad["fresh_entry"]["entry_open"] = False
    with pytest.raises(
        OpportunityContextContractError,
        match="unknown rather than a false verdict",
    ):
        validate_opportunity_context(bad)
