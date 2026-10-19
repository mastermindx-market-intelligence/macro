"""Outcome-blind OA exact-expression source preparation; no activation or writes.

A preparation binds the immutable campaign contract and a new research decision.
It is deliberately not an OA3 ExpressionReceipt: current native sources do not
establish contract terms or durable expression availability. Candidate publication,
policy activation and existing-owner outcome persistence remain separate effects.
"""
from __future__ import annotations

import copy
from datetime import datetime
from hashlib import sha256
from typing import Any

from engine import options_alpha_candidate_feed as candidates
from engine import options_alpha_exact_option_outcome as oa3
from engine import options_nbbo_cohort as cohort
from engine import options_signal_campaign as campaigns_engine
from engine.options_alpha_expression_identity import (
    IdentityUnavailable,
    contract_from_group,
    theta_contract_identity_evidence,
)

POLICY = {
    "schema": "options.alpha_expression_selection_policy/v1",
    "policy_id": "oa_exact_campaign_contract_research/v1",
    "policy_version": 1,
    "status": "preregistered_inactive_source_preparation_only",
    "selection": "every_new_accepted_candidate_exact_formation_campaign_contract",
    "contract_choice": "no_chain_search_no_quote_or_outcome_predicates_no_ranking",
    "population": "oa3.long_single_leg_h60_nbbo/v1",
    "research_position": {"position": "long", "quantity_contracts": 1,
                          "single_leg": True, "package": False},
    "terms": "actual_source_evidence_required_never_policy_or_root_defaults",
    "clocks": "new_selection_act_and_durable_availability_never_source_clock_copy",
    "prospective_fence": "protected_policy_and_real_activation_before_new_candidate_formation",
    "outcomes": "never_input_to_formation_no_quote_access_before_freeze",
    "persistence": "incumbent_candidate_and_campaign_owners_no_parallel_ledger",
    "authority": {key: False for key in (
        "may_rank", "may_score", "may_gate", "may_size", "may_issue", "may_trade",
        "may_publish_pick", "may_train_prophet", "may_feed_neural_web",
        "may_compute_option_pnl", "may_activate", "may_capture_quotes")},
}
# Frozen canonical digest; a policy edit requires an explicit versioned revision.
POLICY_SHA256 = "3eb42ad948cf8cfad731b319d66ca341e33661810e269cc447b0df53cbb92203"
SCHEMA = "options.alpha_expression_preparation/v1"


class ExpressionPreparationError(ValueError):
    """Malformed, causally inconsistent or outcome-exposed source input."""


def _clock(value: str, name: str) -> datetime:
    if not isinstance(value, str):
        raise ExpressionPreparationError(f"{name} requires an aware ISO clock")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExpressionPreparationError(f"{name} requires an aware ISO clock") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ExpressionPreparationError(f"{name} requires an aware ISO clock")
    return stamp


def _physical_source(candidate: dict, source: campaigns_engine.LedgerSnapshot,
                     source_count: int) -> campaigns_engine.LedgerRow:
    # Reuse the incumbent identity, frozen formation, evidence digest and exact
    # versioned-prefix checks. No outcome ledger or context projection is read.
    candidates._validate_prior_candidate_source(
        candidate, campaigns=source, microstructure_map={},
        prior_source_ordinal=source_count,
    )
    receipt = dict(candidate["frozen_formation"]["source_prefix_receipt"])
    receipt.pop("schema")
    ordinal = campaigns_engine.verify_campaign_receipt(
        receipt, source, campaigns_engine.CAMPAIGNS_PATH)
    row = source.rows[ordinal - 1]
    if (campaigns_engine.canonical_bytes(row.value) != row.raw
            or sha256(row.raw).hexdigest() != row.sha256):
        raise ExpressionPreparationError("formation source bytes disagree with parsed row")
    campaigns_engine._validate_schema(row.value, "options.signal_campaign.v2.schema.json")
    return row


def prepare_expression_sources(
    feed_raw_bytes: bytes, *, campaigns: campaigns_engine.LedgerSnapshot,
    source_observed_at: str, campaigns_observed_at: str, selection_started_at: str, decision_at: str,
    theta_contracts_raw: bytes | None = None, catalog_observed_at: str | None = None,
) -> dict[str, Any]:
    """Prepare every candidate's exact contract without granting eligibility.

    Feed bytes must come from compose_candidate_feed BEFORE outcome enrichment.
    Source observation is the caller's actual read, never feed.generated_at.
    The new decision clocks describe preparation only; durable expression
    available_at is unknown and remains null. Supplied source metadata cannot
    activate this policy, admit a catalog as contract terms, or authorize writes.
    """
    if sha256(cohort.canonical_json_bytes(POLICY)).hexdigest() != POLICY_SHA256:
        raise ExpressionPreparationError("frozen expression policy changed")
    if not isinstance(feed_raw_bytes, bytes) or not feed_raw_bytes:
        raise ExpressionPreparationError("original candidate feed bytes required")
    try:
        feed = cohort.strict_json_object(feed_raw_bytes, label="candidate formation source")
    except (ValueError, TypeError) as exc:
        raise ExpressionPreparationError("invalid candidate formation source") from exc
    if isinstance(feed.get("formed_candidates"), list) and any(
            isinstance(item, dict) and "post_formation_outcomes" in item
            for item in feed["formed_candidates"]):
        raise ExpressionPreparationError("outcome-enriched source refused; use pre-enrichment composer output")
    try:
        candidates._validate_schema(feed, "options.alpha_candidate_feed.v2.schema.json")
    except ValueError as exc:
        raise ExpressionPreparationError("invalid candidate formation source") from exc
    observed = _clock(source_observed_at, "source_observed_at")
    campaign_observed = _clock(campaigns_observed_at, "campaigns_observed_at")
    started = _clock(selection_started_at, "selection_started_at")
    decision = _clock(decision_at, "decision_at")
    generated = _clock(feed["generated_at"], "source generated_at")
    if not (generated <= observed <= started <= decision and campaign_observed <= started):
        raise ExpressionPreparationError("source/selection/decision clock order violated")
    if theta_contracts_raw is not None:
        if catalog_observed_at is None:
            raise ExpressionPreparationError("catalog observation clock required")
        if _clock(catalog_observed_at, "catalog_observed_at") > started:
            raise ExpressionPreparationError("catalog must be observed before selection starts")
    elif catalog_observed_at is not None:
        raise ExpressionPreparationError("catalog clock without source bytes")
    if not isinstance(campaigns, campaigns_engine.LedgerSnapshot):
        raise ExpressionPreparationError("incumbent campaign snapshot required")
    receipt = dict(feed["source_receipts"]["campaigns"])
    receipt.pop("schema")
    try:
        count = campaigns_engine.verify_campaign_receipt(
            receipt, campaigns, campaigns_engine.CAMPAIGNS_PATH)
        source = campaigns.prefix(count)
    except ValueError as exc:
        raise ExpressionPreparationError("candidate campaign source prefix mismatch") from exc
    identities = [item["candidate_id"] for item in feed["formed_candidates"]]
    if len(identities) != len(set(identities)):
        raise ExpressionPreparationError("duplicate candidate identity")
    records = []
    for candidate in sorted(feed["formed_candidates"], key=lambda item: item["candidate_id"]):
        # Ordering is serialization only: every candidate is retained, no top-N.
        if not (_clock(candidate["source_formed_at"], "candidate source formation")
                <= _clock(candidate["first_observed_at"], "candidate first observation")
                <= _clock(candidate["decision_at"], "candidate decision") <= generated):
            raise ExpressionPreparationError("candidate source clocks postdate source observation")
        for update in candidate["versioned_updates"]:
            if not (_clock(update["formed_at"], "revision formation")
                    <= _clock(update["observed_at"], "revision observation") <= generated
                    and _clock(update["formed_at"], "revision formation") <= campaign_observed):
                raise ExpressionPreparationError("revision evidence postdates source clock")
        try:
            row = _physical_source(candidate, source, count)
            if candidate["source_formed_at"] != row.value["formed_at"]:
                raise ExpressionPreparationError("candidate source formation clock mismatch")
        except (ValueError, KeyError, TypeError) as exc:
            raise ExpressionPreparationError("candidate immutable formation binding invalid") from exc
        reasons = ["EXPRESSION_POLICY_INACTIVE", "PROSPECTIVE_ACTIVATION_FENCE_UNESTABLISHED",
                   "DURABLE_EXPRESSION_AVAILABILITY_UNESTABLISHED"]
        if (not feed["activation"]["all_preconditions_cleared"]
                or feed["activation"]["fence_state"] != "post_activation"):
            reasons.append("CANDIDATE_ACTIVATION_NOT_CLEARED")
        if candidate["current_disposition"]["state"] != "research_candidate":
            reasons.append("CANDIDATE_NOT_CURRENT_RESEARCH")
        contract, catalog = None, None
        try:
            contract = contract_from_group(row.value["group"])
        except IdentityUnavailable:
            reasons.append("EXACT_CONTRACT_IDENTITY_UNAVAILABLE")
        if contract is not None and theta_contracts_raw is not None:
            try:
                catalog = theta_contract_identity_evidence(theta_contracts_raw, contract)
            except IdentityUnavailable:
                reasons.append("CATALOG_IDENTITY_UNAVAILABLE")
        reasons.append("SOURCE_CONTRACT_TERMS_UNAVAILABLE")
        binding = {
            "selection_policy_id": POLICY["policy_id"],
            "selection_policy_sha256": POLICY_SHA256,
            "formation_policy": copy.deepcopy(feed["policy"]),
            "oa3_ruler": {"policy_id": oa3.FROZEN_POLICY_ID,
                          "policy_version": oa3.FROZEN_POLICY_VERSION,
                          "policy_sha256": oa3.FROZEN_POLICY_SHA256},
            "candidate_id": candidate["candidate_id"],
            "candidate_decision_at": candidate["decision_at"],
            "candidate_first_observed_at": candidate["first_observed_at"],
            "candidate_source_prefix": copy.deepcopy(candidate["frozen_formation"]["source_prefix_receipt"]),
            "formation_campaign_revision_id": row.value["campaign_revision_id"],
            "formation_campaign_raw_sha256": row.sha256,
            "feed_raw_sha256": sha256(feed_raw_bytes).hexdigest(),
            "feed_raw_bytes": len(feed_raw_bytes),
            "source_observed_at": source_observed_at,
            "campaigns_observed_at": campaigns_observed_at,
            "selection_started_at": selection_started_at,
            "decision_at": decision_at,
            "catalog_observed_at": catalog_observed_at,
            "contract": contract, "catalog_identity_evidence": catalog,
            "research_position": copy.deepcopy(POLICY["research_position"]),
            "multiplier": None, "standard_deliverable": None,
        }
        records.append({
            "status": "unavailable", "reasons": reasons, "binding": binding,
            "decision_receipt_sha256": sha256(cohort.canonical_json_bytes(binding)).hexdigest(),
            "expression": None, "expression_upstream_digest_sha256": None,
            "selection_frozen_before_outcomes": None, "available_at": None,
            "capture_request": None, "training_eligible": False,
        })
    return {
        "schema": SCHEMA, "policy": copy.deepcopy(POLICY), "policy_sha256": POLICY_SHA256,
        "records": records, "prepared_candidate_count": len(records),
        "activation": "not_performed", "outcome_write": "not_performed",
        "source_candidate_activation_claim": copy.deepcopy(feed["activation"]),
        "source_runtime_acceptance": "not_proven_by_preparation",
        "authority": copy.deepcopy(POLICY["authority"]),
    }
