"""Versioned, authority-false Prophet strategy-definition owner projection.

This is the smallest machine-readable strategy identity required before B4 may
compute strategy/horizon-specific Availability.  It freezes one already
architected sleeve — Early Leadership / Sector Rotation — without changing B1
candidate admission, B3 state, ranking, plan origination, sizing, publication,
execution, or trade authority.

B4 itself remains outside this module.  A consumer that lacks an accepted
strategy definition must fail closed rather than infer policy identity from a
plan horizon, legacy entry status, ranker/model name, or display vocabulary.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from hashlib import sha256
import json

SCHEMA = "prophet.strategy_definition/v1"
DEFINITION_ERA = "prophet-strategy-definition-v1-2026-09-20"
STRATEGY_ID = "EARLY_LEADERSHIP_SECTOR_ROTATION"
STRATEGY_VERSION = "1"
ENTRY_POLICY_VERSION = "early-leadership-sector-rotation-entry-v1"

_AUTHORITY = {
    "can_rank": False,
    "can_gate_candidate_admission": False,
    "can_compute_b4_availability": False,
    "can_originate_plan": False,
    "can_change_entry_open": False,
    "can_size": False,
    "can_publish_trade_instruction": False,
    "can_execute": False,
    "can_trade": False,
}


class StrategyDefinitionContractError(ValueError):
    """Raised when a strategy definition weakens the frozen owner contract."""


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StrategyDefinitionContractError(
            f"strategy definition is not canonical JSON: {exc}"
        ) from exc


def _material() -> dict[str, object]:
    """Return the complete frozen control definition before content hashing."""

    return {
        "schema": SCHEMA,
        "definition_era": DEFINITION_ERA,
        "strategy_id": STRATEGY_ID,
        "strategy_version": STRATEGY_VERSION,
        "strategy_family": "Early Leadership / Sector Rotation",
        "scientific_status": "CONTROL_ONLY",
        "authority_tier": "SHADOW_ONLY",
        "supported_markets_and_instruments": [
            {
                "market": "US",
                "instrument_classes": ["COMMON_STOCK"],
                "candidate_owner_schema": "prophet.candidate_episode/v1",
            }
        ],
        "horizons": {
            "primary": "2_15_SESSIONS",
            "secondary": [],
            "horizon_role": "new_entry",
        },
        "economic_thesis": (
            "Early leadership and sector rotation may create tactical opportunity "
            "while a canonical candidate remains valid and owner-issued entry "
            "geometry shows residual room; the thesis does not authorize chasing "
            "an already-incorporated move."
        ),
        "setup_and_candidate_admission": {
            "candidate_source": "EXISTING_CANONICAL_B1_ONLY",
            "setup_species_source": "OWNER_REFERENCED_ONLY",
            "may_create_candidate_episode": False,
            "may_widen_population": False,
            "may_force_named_security": False,
            "unknown_or_unregistered_species": "ABSTAIN",
        },
        "evidence_families": {
            "required": [
                "candidate_lifecycle",
                "identity_and_basis",
                "decision_time_quote_freshness",
                "owner_entry_geometry",
            ],
            "optional_context_only": [
                "candidate_emergence",
                "candidate_maturity",
                "sector_and_theme_context",
                "macro_and_regime_context",
                "earnings_and_specialist_context",
            ],
            "narrative_or_llm_may_waive_required_fact": False,
        },
        "market_and_regime_eligibility": {
            "mode": "DESCRIPTIVE_CONTEXT_ONLY",
            "broad_regime_scorecard_authority": False,
            "cross_sectional_stock_bonus_from_row_constant_macro": False,
            "missing_required_owner_fact": "ABSTAIN",
        },
        "expected_economic_response": {
            "status": "NOT_ASSERTED_CONTROL_ONLY",
            "claim": None,
        },
        "expected_market_response": {
            "status": "HYPOTHESIS_ONLY",
            "hypothesis": (
                "recently emerging leadership can persist long enough to support "
                "a tactical sessions-to-weeks expression when entry geometry remains open"
            ),
        },
        "price_incorporation_test": {
            "owner_chase_boundary_required": True,
            "past_owner_chase_boundary": "RAN_DONT_CHASE",
            "may_override_owner_chase_boundary": False,
        },
        "residual_opportunity_test": {
            "owner_geometry_required": True,
            "decision": "DEFER_TO_B4",
            "definition_may_compute_entry_open": False,
        },
        "entry_and_availability_requirements": {
            "availability_owner_schema": "prophet.entry_availability/v1",
            "entry_policy_version": ENTRY_POLICY_VERSION,
            "candidate_identity_required": [
                "candidate_episode_id",
                "candidate_generation_id",
                "security_id",
                "identity_epoch",
            ],
            "decision_clocks_required": [
                "decision_at",
                "quote_asof",
                "basis_version",
            ],
            "owner_confluence_gate_may_be_waived": False,
            "owner_confluence_source_session_rule": "next_session_only/v1",
            "missing_or_stale_required_fact": "UNAVAILABLE_DATA",
            "definition_itself_may_set_availability": False,
        },
        "position_lifecycle_and_hold_law": {
            "mode": "NO_DUPLICATE_LIFECYCLE",
            "plan_identity_owner": "Existing Prophet plan owner",
            "portfolio_position_owner": "Portfolio/Risk",
            "core_hold_authority": False,
        },
        "invalidation_expiry_distribution_exit_review": {
            "candidate_terminal_state_blocks_new_entry": True,
            "identity_or_basis_unresolved_blocks_new_entry": True,
            "stale_or_dark_required_quote_blocks_new_entry": True,
            "owner_stop_is_binding_when_present": True,
            "definition_creates_universal_stop_engine": False,
            "distribution_and_exit_review_owner": "Existing plan / Evaluation / Portfolio owners",
        },
        "risk_facts_exposed_downstream": [
            "owner_entry_zone",
            "owner_chase_boundary",
            "owner_stop_when_present",
            "quote_freshness",
            "identity_basis_status",
        ],
        "benchmark_controls_costs_and_evaluation": {
            "evaluation_owner": "Evaluation OS / QLedger",
            "same_tape_control": "Current U.S. Prophet control",
            "costs_required_before_promotion": True,
            "prospective_or_oos_evidence_required_before_promotion": True,
            "promotion_claim": "NONE",
        },
        "authority": dict(_AUTHORITY),
    }


def build_early_leadership_sector_rotation_definition() -> dict[str, object]:
    """Return the immutable first proving strategy definition, still authority-false."""

    material = _material()
    material["strategy_definition_id"] = (
        "psd:" + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    )
    validate_strategy_definition(material)
    return deepcopy(material)


def validate_strategy_definition(payload: Mapping[str, object]) -> None:
    """Validate the closed owner definition and its content identity."""

    if not isinstance(payload, Mapping):
        raise StrategyDefinitionContractError("strategy definition must be an object")

    baseline = _material()
    expected = set(baseline) | {"strategy_definition_id"}
    if set(payload) != expected:
        raise StrategyDefinitionContractError("strategy definition fields are not closed")

    for key, value in baseline.items():
        if payload.get(key) != value:
            raise StrategyDefinitionContractError(
                f"strategy definition field {key!r} diverges from the frozen control"
            )

    if payload.get("authority") != _AUTHORITY:
        raise StrategyDefinitionContractError("strategy authority must remain all false")

    material = {
        key: value
        for key, value in payload.items()
        if key != "strategy_definition_id"
    }
    expected_id = "psd:" + sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()
    if payload.get("strategy_definition_id") != expected_id:
        raise StrategyDefinitionContractError("strategy_definition_id mismatch")
