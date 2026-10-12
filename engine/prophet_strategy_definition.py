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


# --------------------------------------------------------------------------- #
# Full Prophet sleeve catalog -- roadmap truth, never live strategy authority
# --------------------------------------------------------------------------- #

CATALOG_SCHEMA = "prophet.strategy_catalog/v1"
CATALOG_VERSION = "2026-09-30.v1"
CATALOG_ARCHITECTURE_REF = (
    "research/prophet_v4/"
    "PROPHET_STRATEGY_PLATFORM_AND_CYCLE_CAPTURE_ARCHITECTURE_FREEZE_2026-08-30.md"
)

_CATALOG_AUTHORITY = {
    "can_rank": False,
    "can_route_strategy": False,
    "can_gate_candidate_admission": False,
    "can_compute_b4_availability": False,
    "can_originate_plan": False,
    "can_change_entry_open": False,
    "can_size": False,
    "can_publish_trade_instruction": False,
    "can_execute": False,
    "can_trade": False,
    "can_activate_short": False,
    "can_activate_options": False,
}

_INITIAL_CORE = (
    "EARLY_LEADERSHIP_SECTOR_ROTATION",
    "QUALITY_EARNINGS_EXPECTATION_REVISION",
    "CYCLE_CAPTURE",
)

_RETAINED_LATER = (
    "POLICY_EVENT_SWING",
    "CATALYST_DISLOCATION",
    "LIQUIDITY_DEBASEMENT_REAL_ASSETS",
    "RANGE_MEAN_REVERSION",
    "DEFENSIVE_AVOIDANCE_HEDGE_RESEARCH",
)


def _catalog_sleeve(
    *,
    strategy_id: str,
    family_name: str,
    roadmap_class: str,
    definition_status: str,
    horizon_status: str,
    primary_horizon: str | None,
    supporting_horizons: list[str],
    horizon_narrative: str,
    user_job: str,
    economic_thesis: str,
    required_evidence: list[str],
    optional_context: list[str],
    regime_role: str,
    entry_owner: str,
    hold_law: str,
    primary_falsifiers: list[str],
    constraints: list[str],
    instrument_requirements: list[str],
    promotion_requirements: list[str],
    definition_ref: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "strategy_id": strategy_id,
        "family_name": family_name,
        "roadmap_class": roadmap_class,
        "definition_status": definition_status,
        "horizon": {
            "status": horizon_status,
            "primary": primary_horizon,
            "supporting": list(supporting_horizons),
            "narrative": horizon_narrative,
            "not_a_hold_law": True,
        },
        "user_job": user_job,
        "economic_thesis": economic_thesis,
        "required_evidence": list(required_evidence),
        "optional_context": list(optional_context),
        "regime_role": regime_role,
        "entry_owner": entry_owner,
        "hold_law": hold_law,
        "primary_falsifiers": list(primary_falsifiers),
        "constraints": list(constraints),
        "instrument_requirements": list(instrument_requirements),
        "promotion_requirements": list(promotion_requirements),
        "definition_ref": deepcopy(definition_ref),
        "authority": dict(_CATALOG_AUTHORITY),
    }


def _catalog_material() -> dict[str, object]:
    early = build_early_leadership_sector_rotation_definition()
    sleeves = [
        _catalog_sleeve(
            strategy_id="CYCLE_CAPTURE",
            family_name="Cyclical Washout Accumulation / Cycle Capture",
            roadmap_class="CORE_INITIAL",
            definition_status="SPEC_ONLY",
            horizon_status="RESEARCH_PROPOSAL_NOT_POLICY",
            primary_horizon="H252",
            supporting_horizons=["H126", "H504"],
            horizon_narrative="weeks to quarters or longer; exact holding law remains unpromoted",
            user_job=(
                "Find survivable cyclical assets after deep liquidation, identify a lawful "
                "base/pivot early enough for favorable asymmetry, and hold a core thesis "
                "through the valuable portion of a recovery without relabeling tactical losses."
            ),
            economic_thesis=(
                "A deep liquidation can create long-horizon asymmetry only when the decline is "
                "cyclical rather than permanent impairment, the issuer can survive the path, "
                "repair is source-qualified, and residual opportunity remains after financing, "
                "dilution, carry, and price incorporation."
            ),
            required_evidence=[
                "identity_instrument_basis",
                "liquidation_depth_and_path",
                "technical_base_and_pivot",
                "cycle_economic_state",
                "survivability_funding_and_dilution",
                "price_incorporation_and_residual_opportunity",
                "decision_time_quote_and_b4_geometry",
            ],
            optional_context=[
                "positioning_and_fragility",
                "commodity_supply_demand",
                "policy_currency_rates",
                "earnings_and_balance_sheet",
            ],
            regime_role="cycle-class eligibility and abstention; never a universal regime bonus",
            entry_owner="B4 / owner technical geometry; strategy thesis cannot waive Availability",
            hold_law=(
                "core-hold law is strategy-native and must distinguish ordinary volatility, "
                "failed pivot, structural invalidation, funding failure, distribution, and cycle maturity"
            ),
            primary_falsifiers=[
                "same killed two-week washout-turn seed under new thresholds",
                "secular impairment mistaken for cyclical liquidation",
                "survival or original-shareholder economics fail",
                "most supported upside already incorporated before entry",
            ],
            constraints=[
                "DNR:KILL-WASHOUT-TURN",
                "DNR:KILL-ROTATION-CYCLE-CONFLUENCE",
                "DNR:KILL-REGIME-SCORECARD",
                "DNR:KILL-FUSED-COMPOSITE",
                "DNR:KILL-PROPHET-POP-MERGE",
            ],
            instrument_requirements=[
                "equity/future/ETF/producer contracts remain distinct",
                "commodity curves/carry/roll required where applicable",
                "producer financing/dilution/hedging required where applicable",
            ],
            promotion_requirements=[
                "source readiness and rights",
                "failure-inclusive prospective evaluation",
                "B4 integration",
                "core/add/exit policy evidence",
                "downstream Portfolio/Risk acceptance",
            ],
        ),
        _catalog_sleeve(
            strategy_id="EARLY_LEADERSHIP_SECTOR_ROTATION",
            family_name="Early Leadership / Sector Rotation",
            roadmap_class="CORE_INITIAL",
            definition_status="CONTROL_DEFINED_SHADOW_ONLY",
            horizon_status="FROZEN_CONTROL_NEW_ENTRY_IDENTITY",
            primary_horizon="2_15_SESSIONS",
            supporting_horizons=["H5_RESEARCH", "H10_RESEARCH_PRIMARY", "H15_RESEARCH"],
            horizon_narrative="sessions to weeks; the 2-15-session field is entry identity, not a universal hold",
            user_job=(
                "Detect emerging company and group leadership early, select the right economic "
                "member, and act only while independent support and entry geometry still leave room."
            ),
            economic_thesis=(
                "Economic leadership and capital attention can propagate through related companies "
                "before all participants reprice, but sector beta, self-confirming peers, and extension "
                "must be separated from genuine company selection."
            ),
            required_evidence=[
                "canonical_candidate_identity",
                "company_relative_leadership",
                "leave_issuer_out_peer_support",
                "economic_subtheme_exposure",
                "setup_development_and_failure_state",
                "remaining_opportunity_and_owner_geometry",
            ],
            optional_context=[
                "earnings_support",
                "qualified_options_context",
                "macro_exposure_interactions",
            ],
            regime_role="descriptive and interaction research; broad regime constant cannot rank stocks",
            entry_owner="existing B4 / Early Leadership entry policy",
            hold_law="tactical plan owner; new-entry pause is not an automatic sale",
            primary_falsifiers=[
                "stock merely inherits sector move",
                "candidate creates its own peer confirmation",
                "winner discovered only after opportunity is consumed",
                "slower confirmation sacrifices more opportunity than it protects",
            ],
            constraints=[
                "no current-membership historical backfill",
                "no rotation-times-cycle confluence",
                "no universal stock bonus from row-constant macro",
            ],
            instrument_requirements=["US common-stock control first; other markets require native clocks and policy"],
            promotion_requirements=[
                "same-population incremental comparison",
                "date/issuer leakage controls",
                "prospective or OOS evidence",
                "cost and turnover evidence",
                "B4 remains separate authority",
            ],
            definition_ref={
                "schema": early["schema"],
                "strategy_definition_id": early["strategy_definition_id"],
                "strategy_version": early["strategy_version"],
                "entry_policy_version": early["entry_and_availability_requirements"]["entry_policy_version"],
            },
        ),
        _catalog_sleeve(
            strategy_id="QUALITY_EARNINGS_EXPECTATION_REVISION",
            family_name="Quality Earnings / Expectation Revision",
            roadmap_class="CORE_INITIAL",
            definition_status="SPEC_ONLY_FACTUAL_EVIDENCE_BUILDING",
            horizon_status="RESEARCH_PROPOSAL_NOT_POLICY",
            primary_horizon="H42",
            supporting_horizons=["H21", "H63"],
            horizon_narrative="weeks to months; proposed research checkpoints are not a printed holding duration",
            user_job=(
                "Identify a durable change in operating results or expectations that is source-comparable "
                "and not already fully incorporated into the current trade opportunity."
            ),
            economic_thesis=(
                "Markets may underreact to material operating/expectation changes, but seasonal earnings "
                "strength, true pre-release consensus surprise, later matched revisions, quality, and "
                "elapsed price response are different facts and must not be collapsed."
            ),
            required_evidence=[
                "exact_event_and_issuer_identity",
                "comparable_reported_financials",
                "source_availability_clock",
                "seasonal_eps_strength_separate_from_consensus",
                "pre_release_expectation_when_claimed",
                "matched_revision_when_claimed",
                "price_response_already_elapsed",
                "current_entry_geometry",
            ],
            optional_context=[
                "guidance",
                "cash_conversion_and_margin_quality",
                "diluted_share_transmission",
                "segment_change",
                "peer_and_sector_expectations",
            ],
            regime_role="context/interaction only; event quality is not overridden by broad regime scoring",
            entry_owner="B4 after source-qualified event and strategy-specific policy acceptance",
            hold_law="event/revision-native review; next material revision/report matters, but horizon is not yet frozen",
            primary_falsifiers=[
                "seasonal EPS momentum mislabeled as consensus beat",
                "later analyst data leaked into release-time decision",
                "headline gain fully incorporated before executable entry",
                "profit growth offset by dilution or poor cash quality",
            ],
            constraints=[
                "no fabricated consensus",
                "no current-event substitution for historical event",
                "no post-release gap credited before source availability",
                "no score promotion from source repair alone",
            ],
            instrument_requirements=["common-stock evidence first; option expression requires separate payoff/IV/execution proof"],
            promotion_requirements=[
                "B08 factual source qualification",
                "B14 user research journey",
                "B15 same-population model/entry/hold evaluation",
                "licensed expectation rights where used",
                "price-basis and event-clock integrity",
            ],
        ),
        _catalog_sleeve(
            strategy_id="POLICY_EVENT_SWING",
            family_name="Policy and Event Swing",
            roadmap_class="RETAINED_LATER",
            definition_status="SPEC_ONLY_RETAINED_B27",
            horizon_status="OWNER_SPEC_REQUIRED",
            primary_horizon=None,
            supporting_horizons=[],
            horizon_narrative="bounded around known or developing events; no copied Early Leadership horizon",
            user_job="Trade a source-qualified policy or event transmission only when timing, authority, exposure, and reversibility are explicit.",
            economic_thesis="A discrete event can reprice exposed businesses when its authority, availability, transmission path, and prior incorporation are correctly measured.",
            required_evidence=[
                "event_identity_authority_and_clock",
                "business_exposure_mapping",
                "reversibility_and_implementation_state",
                "price_response_control",
                "current_b4_geometry",
            ],
            optional_context=["policy_graph", "cross_asset_transmission", "options_path_context"],
            regime_role="event-specific applicability; no broad policy sentiment score",
            entry_owner="future accepted event-swing policy + B4",
            hold_law="event milestone/expiry law must be separately specified",
            primary_falsifiers=[
                "event not legally/operationally effective",
                "exposure mapping wrong or indirect",
                "price already incorporates event",
                "reversal/expiry risk dominates residual opportunity",
            ],
            constraints=["no undisclosed government action", "no LLM-minted authority", "no copied EL horizon"],
            instrument_requirements=["instrument must match event exposure; options need separate validation"],
            promotion_requirements=["Q23/B27 specification", "source/event clocks", "prospective controls", "strategy-specific entry/exit law"],
        ),
        _catalog_sleeve(
            strategy_id="CATALYST_DISLOCATION",
            family_name="Catalyst and Dislocation",
            roadmap_class="RETAINED_LATER",
            definition_status="SPEC_ONLY_RETAINED_B27",
            horizon_status="OWNER_SPEC_REQUIRED",
            primary_horizon=None,
            supporting_horizons=[],
            horizon_narrative="event/dislocation dependent; exact horizon not frozen",
            user_job="Exploit a verified disagreement between evidence state and price state without mistaking impairment for forced technical pressure.",
            economic_thesis="Forced selling, liquidity shocks, mechanical flows, or delayed evidence incorporation can create temporary mispricing when the underlying thesis remains intact.",
            required_evidence=[
                "dislocation_mechanism",
                "source_qualified_fundamental_state",
                "liquidity_and_forced_flow_evidence",
                "impairment_countercase",
                "current_b4_geometry",
            ],
            optional_context=["dark_pool_or_options_context", "ownership", "event_calendar"],
            regime_role="dislocation-specific; stress can create or invalidate the case",
            entry_owner="future accepted dislocation policy + B4",
            hold_law="reversion/catalyst resolution and impairment review must be frozen before use",
            primary_falsifiers=[
                "price decline reflects new fundamental impairment",
                "forced-flow claim unsupported",
                "liquidity makes theoretical entry unfillable",
                "no residual catalyst or reversion mechanism",
            ],
            constraints=["no proxy flow promoted to exact fund intent", "no universal bounce score"],
            instrument_requirements=["liquidity/fillability and event-specific instrument proof"],
            promotion_requirements=["Q23/B27 specification", "matched dislocation controls", "fill/cost evidence", "adverse-tail accounting"],
        ),
        _catalog_sleeve(
            strategy_id="LIQUIDITY_DEBASEMENT_REAL_ASSETS",
            family_name="Liquidity / Debasement / Real Assets",
            roadmap_class="RETAINED_LATER",
            definition_status="SPEC_ONLY_RETAINED_B27",
            horizon_status="OWNER_SPEC_REQUIRED",
            primary_horizon=None,
            supporting_horizons=[],
            horizon_narrative="sustained macro transmission; horizon must follow the specific instrument/economic mechanism",
            user_job="Identify sustained liquidity/inflation/debasement transmission through instruments whose economics actually benefit.",
            economic_thesis="Macro liquidity, real-rate, currency, and inflation forces can transmit into real assets and producers, but commodity economics and equity claims differ.",
            required_evidence=[
                "macro_source_and_clock",
                "real_rate_currency_liquidity_transmission",
                "instrument_specific_economics",
                "producer_cost_curve_or_balance_sheet_if_equity",
                "price_incorporation",
            ],
            optional_context=["term_structure", "inventory", "policy", "capital_flows"],
            regime_role="mechanism itself is macro-sensitive; no generic inflation hedge label",
            entry_owner="future instrument-native strategy policy + B4-equivalent owner",
            hold_law="macro/economic thesis and instrument-specific carry/funding/distribution law required",
            primary_falsifiers=[
                "instrument does not capture claimed macro exposure",
                "carry/roll/hedging overwhelms thesis",
                "producer financing/dilution offsets commodity upside",
                "macro move already priced",
            ],
            constraints=["no futures/ETF/producer equivalence", "no automatic leverage", "no copied US-stock constants"],
            instrument_requirements=["curve/carry/roll or producer financing/hedging as applicable"],
            promotion_requirements=["Q23/B27 instrument contract", "rights/data readiness", "cost/carry evidence", "market-native evaluation"],
        ),
        _catalog_sleeve(
            strategy_id="RANGE_MEAN_REVERSION",
            family_name="Range / Mean Reversion",
            roadmap_class="RETAINED_LATER",
            definition_status="SPEC_ONLY_RETAINED_B27",
            horizon_status="OWNER_SPEC_REQUIRED",
            primary_horizon=None,
            supporting_horizons=[],
            horizon_narrative="bounded non-trending environments; no general-purpose mean-reversion horizon frozen",
            user_job="Exploit bounded reversions only when the range/regime is demonstrated and transaction costs leave residual edge.",
            economic_thesis="Prices can revert within persistent non-trending structures, but breakout/trend transitions and repeated costs can destroy naive mean reversion.",
            required_evidence=[
                "range_state_and_boundaries",
                "trend_break_falsifier",
                "volatility_and_liquidity",
                "cost_and_turnover",
                "current_entry_geometry",
            ],
            optional_context=["breadth", "options_pin_context", "seasonality"],
            regime_role="requires a qualified non-trending state; regime evidence is applicability, not a stock bonus",
            entry_owner="future range policy + B4",
            hold_law="range target/invalidation/time law must be strategy-specific",
            primary_falsifiers=[
                "range is actually emerging trend",
                "costs consume gross reversion",
                "boundary chosen after outcome",
                "gap/illiquidity defeats assumed fills",
            ],
            constraints=["no general-purpose oversold bounce rule", "no hindsight-fitted box"],
            instrument_requirements=["session/liquidity rules specific to instrument"],
            promotion_requirements=["Q23/B27 specification", "range-definition preregistration", "cost-aware OOS/prospective evaluation"],
        ),
        _catalog_sleeve(
            strategy_id="DEFENSIVE_AVOIDANCE_HEDGE_RESEARCH",
            family_name="Defensive / Avoidance / Hedge Research",
            roadmap_class="RETAINED_LATER",
            definition_status="SPEC_ONLY_RETAINED_B27",
            horizon_status="OWNER_SPEC_REQUIRED",
            primary_horizon=None,
            supporting_horizons=[],
            horizon_narrative="risk-reduction/relative-value context; no directional-short horizon or authority implied",
            user_job="Reduce avoidable downside and identify relative defensive context without pretending inactivity is positive alpha.",
            economic_thesis="Certain environments or exposures can justify avoiding new risk, reducing model exposure, or studying hedges when the reduction improves the full path including missed recovery.",
            required_evidence=[
                "market_damage_and_repair_state",
                "breadth_and_leadership_health",
                "funding_liquidity_and_volatility",
                "portfolio_exposure",
                "hedge_instrument_payoff_if_used",
            ],
            optional_context=["options_path_risk", "credit", "macro_exposure"],
            regime_role="risk permission and portfolio context; not a cross-sectional long score",
            entry_owner="Portfolio/Risk and separately validated hedge-instrument owner",
            hold_law="reduction/re-entry/hedge expiry must be explicit and account for missed upside",
            primary_falsifiers=[
                "false alarm destroys more recovery than loss avoided",
                "hedge carry/slippage dominates benefit",
                "missing data mislabeled as danger",
                "relative defensiveness mislabeled as absolute positive return",
            ],
            constraints=[
                "DNR:KILL-DIRECTIONAL-SHORTING",
                "no automatic short authority",
                "no risk score averaged into stock rank",
            ],
            instrument_requirements=["borrow/options/hedge payoff and loss semantics required before any expression"],
            promotion_requirements=["Q23/B27 specification", "self-financing exposure path", "re-entry evidence", "Portfolio/Risk acceptance"],
        ),
    ]

    # Architecture order begins with the flagship Cycle sleeve even though the
    # first implemented control definition is Early Leadership.
    return {
        "schema": CATALOG_SCHEMA,
        "catalog_version": CATALOG_VERSION,
        "architecture_ref": CATALOG_ARCHITECTURE_REF,
        "platform_rule": "ONE_CANONICAL_PLATFORM_MULTIPLE_GOVERNED_SLEEVES",
        "initial_core_sleeves": list(_INITIAL_CORE),
        "retained_later_sleeves": list(_RETAINED_LATER),
        "sleeves": sleeves,
        "cross_sleeve_law": {
            "candidate_may_match_multiple_sleeves": True,
            "sleeve_disagreements_are_preserved": True,
            "universal_score_authorized": False,
            "row_constant_macro_may_rank_stocks": False,
            "availability_owner": "B4_OR_MARKET_NATIVE_EQUIVALENT",
            "portfolio_allocation_owner": "Portfolio/Risk",
            "missing_evidence": "ABSTAIN_OR_UNAVAILABLE_NOT_FAVORABLE_ZERO",
        },
        "authority": dict(_CATALOG_AUTHORITY),
    }


def build_strategy_catalog() -> dict[str, object]:
    """Return the frozen full roadmap catalog with zero live strategy authority."""
    material = _catalog_material()
    material["catalog_id"] = (
        "psc:" + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    )
    validate_strategy_catalog(material)
    return deepcopy(material)


def validate_strategy_catalog(payload: Mapping[str, object]) -> None:
    """Reject any silent widening of the architecture-backed sleeve roadmap."""
    if not isinstance(payload, Mapping):
        raise StrategyDefinitionContractError("strategy catalog must be an object")

    baseline = _catalog_material()
    expected = set(baseline) | {"catalog_id"}
    if set(payload) != expected:
        raise StrategyDefinitionContractError("strategy catalog fields are not closed")

    for key, value in baseline.items():
        if payload.get(key) != value:
            raise StrategyDefinitionContractError(
                f"strategy catalog field {key!r} diverges from the frozen roadmap"
            )

    if payload.get("authority") != _CATALOG_AUTHORITY:
        raise StrategyDefinitionContractError("strategy catalog authority must remain all false")

    for sleeve in payload.get("sleeves", []):
        if not isinstance(sleeve, Mapping) or sleeve.get("authority") != _CATALOG_AUTHORITY:
            raise StrategyDefinitionContractError("every sleeve authority must remain all false")

    material = {key: value for key, value in payload.items() if key != "catalog_id"}
    expected_id = "psc:" + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    if payload.get("catalog_id") != expected_id:
        raise StrategyDefinitionContractError("catalog_id mismatch")
