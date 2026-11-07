"""Pure research-expression intent codec (inactive; research intent only).

An intent binds one original outcome-blind preparation record to the native
frozen selection policy and to a NEW caller-supplied contract-terms source
observation. It is deliberately not an OA3 ExpressionReceipt: no capture
request is generated and no source authentication, runtime admission, durable
availability, publication or activation effect is claimed; every authority
flag stays false. No I/O, clock, network, provider, GitHub or activation
effect is performed and candidate outcome values are never read; the parent
owns all publisher I/O, manifest, CAS and review effects. ``terms_observation``
is a minimum caller-supplied input interface, never an authenticated producer
or runtime-admission receipt, and no term is defaulted from policy or root.
"""
from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

from engine import options_alpha_candidate_feed as candidates
from engine import options_alpha_expression_formation as formation
from engine import options_nbbo_cohort as cohort

INTENT_SCHEMA = "options.alpha_expression_intent/v1"
TERMS_SCHEMA = "options.contract_terms_observation/v1"
ELIGIBILITY = "research_intent_only_no_activation"
EXPRESSION_ID_PREFIX = "oaexprintent_"

# Frozen native selection policy digest; a policy edit needs an explicit
# versioned revision and is refused here.
FROZEN_SELECTION_POLICY_SHA256 = (
    "3eb42ad948cf8cfad731b319d66ca341e33661810e269cc447b0df53cbb92203"
)

# Exact incumbent formation binding shape; the decision receipt seals it.
_BINDING_KEYS = frozenset({
    "selection_policy_id", "selection_policy_sha256", "formation_policy",
    "oa3_ruler", "candidate_id", "candidate_decision_at",
    "candidate_first_observed_at", "candidate_source_prefix",
    "formation_campaign_revision_id", "formation_campaign_raw_sha256",
    "feed_raw_sha256", "feed_raw_bytes", "source_observed_at",
    "campaigns_observed_at", "selection_started_at", "decision_at",
    "catalog_observed_at", "contract", "catalog_identity_evidence",
    "research_position", "multiplier", "standard_deliverable",
})
_TERMS_KEYS = frozenset({
    "schema", "contract", "multiplier", "standard_deliverable",
    "deliverable_description", "effective_from", "effective_until",
    "source_available_at", "source_observed_at", "source_id",
    "raw_source_sha256", "raw_source_bytes",
})
_INTENT_KEYS = frozenset({
    "schema", "expression_id", "candidate_id",
    "candidate_frozen_formation_sha256", "preparation_receipt_sha256",
    "selection_policy_id", "selection_policy_sha256", "oa3_ruler",
    "contract", "terms_observation", "decision_at",
    "publication_available_at", "eligibility", "authority",
})
_RULER_KEYS = frozenset({"policy_id", "policy_version", "policy_sha256"})
_HEX64_RE = re.compile(r"[0-9a-f]{64}")


class IntentError(ValueError):
    """Malformed, replayed or causally inconsistent expression intent input."""


def _clock(value: Any, name: str, *, binding: bool = False) -> datetime:
    """Parse a clock; new-act and terms clocks must be canonical UTC Z."""
    if not isinstance(value, str):
        raise IntentError(f"{name} requires an aware ISO clock")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IntentError(f"{name} requires an aware ISO clock") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise IntentError(f"{name} requires an aware ISO clock")
    if not binding and (not value.endswith("Z")
                        or stamp.utcoffset() != timedelta(0)):
        raise IntentError(f"{name} must be a canonical UTC Z clock")
    return stamp


def _str(value: Any, name: str, *, hex64: bool = False) -> str:
    if not isinstance(value, str) or not (
            _HEX64_RE.fullmatch(value) if hex64 else value.strip()):
        raise IntentError(f"{name} must be a "
                          f"{'sha256 digest' if hex64 else 'nonempty'} string")
    return value


def _exact_object(raw: Any, keys: frozenset, name: str) -> dict:
    if not isinstance(raw, Mapping):
        raise IntentError(f"{name} must be an object")
    if set(raw) != keys:
        raise IntentError(f"{name} fields are not exact")
    return dict(raw)


def _frozen_policy() -> tuple[str, str]:
    """Return the frozen selection policy identity, refusing any drift."""
    policy_id = formation.POLICY.get("policy_id")
    digest = sha256(cohort.canonical_json_bytes(formation.POLICY)).hexdigest()
    if (formation.POLICY_SHA256 != FROZEN_SELECTION_POLICY_SHA256
            or digest != FROZEN_SELECTION_POLICY_SHA256
            or not isinstance(policy_id, str) or not policy_id):
        raise IntentError("frozen expression selection policy changed")
    return policy_id, formation.POLICY_SHA256


def _validated_ruler(raw: Any) -> dict:
    ruler = _exact_object(raw, _RULER_KEYS, "binding.oa3_ruler")
    _str(ruler["policy_id"], "oa3_ruler.policy_id")
    _str(ruler["policy_version"], "oa3_ruler.policy_version")
    _str(ruler["policy_sha256"], "oa3_ruler.policy_sha256", hex64=True)
    return ruler


def _candidate_identity(candidate: Any) -> tuple[str, Mapping, str]:
    """Read only candidate id and frozen formation; never outcome values."""
    if not isinstance(candidate, Mapping):
        raise IntentError("candidate must be an object")
    candidate_id = _str(candidate.get("candidate_id"), "candidate.candidate_id")
    frozen = candidate.get("frozen_formation")
    if not isinstance(frozen, Mapping):
        raise IntentError("candidate.frozen_formation must be an object")
    if not isinstance(frozen.get("source_prefix_receipt"), Mapping):
        raise IntentError("frozen_formation.source_prefix_receipt must be an object")
    _str(frozen.get("campaign_revision_id"),
         "frozen_formation.campaign_revision_id")
    frozen_sha = sha256(candidates.canonical_bytes(frozen)).hexdigest()
    return candidate_id, frozen, frozen_sha


def _validated_binding(preparation_record: Any, *, candidate_id: str,
                       frozen: Mapping) -> tuple[dict, str, datetime]:
    if not isinstance(preparation_record, Mapping):
        raise IntentError("preparation record must be an object")
    receipt = _str(preparation_record.get("decision_receipt_sha256"),
                   "preparation decision_receipt_sha256", hex64=True)
    binding = _exact_object(preparation_record.get("binding"), _BINDING_KEYS,
                            "preparation binding")
    digest = sha256(cohort.canonical_json_bytes(binding)).hexdigest()
    if digest != receipt:
        raise IntentError("preparation receipt does not digest its binding")
    policy_id, policy_sha256 = _frozen_policy()
    if (binding["selection_policy_id"] != policy_id
            or binding["selection_policy_sha256"] != policy_sha256):
        raise IntentError("binding policy is not the frozen selection policy")
    if binding["candidate_id"] != candidate_id:
        raise IntentError("binding candidate identity differs from candidate")
    if binding["candidate_source_prefix"] != frozen["source_prefix_receipt"]:
        raise IntentError("binding source prefix differs from frozen formation")
    if (binding["formation_campaign_revision_id"]
            != frozen["campaign_revision_id"]):
        raise IntentError("binding revision differs from frozen formation")
    return binding, receipt, _clock(binding["decision_at"],
                                    "binding.decision_at", binding=True)


def _contract(raw: Any, name: str) -> dict:
    try:
        return cohort.validate_contract(raw)
    except ValueError as exc:
        raise IntentError(f"{name} is not a valid exact contract") from exc


def _validated_terms(terms: Any, *, contract: Mapping,
                     decision: datetime) -> dict:
    """Validate the required minimum terms observation; no defaults apply."""
    terms = _exact_object(terms, _TERMS_KEYS, "terms_observation")
    if terms["schema"] != TERMS_SCHEMA:
        raise IntentError("terms_observation schema mismatch")
    if terms["contract"] != contract:
        raise IntentError("terms_observation contract differs from selection")
    if type(terms["multiplier"]) is not int or terms["multiplier"] != 100:
        raise IntentError("terms_observation multiplier must be exactly 100")
    if terms["standard_deliverable"] is not True:
        raise IntentError("terms_observation standard_deliverable must be true")
    _str(terms["deliverable_description"], "terms deliverable_description")
    _str(terms["source_id"], "terms source_id")
    _str(terms["raw_source_sha256"], "terms raw_source_sha256", hex64=True)
    if type(terms["raw_source_bytes"]) is not int or terms["raw_source_bytes"] <= 0:
        raise IntentError("terms raw_source_bytes must be a positive integer")
    available = _clock(terms["source_available_at"], "terms source_available_at")
    observed = _clock(terms["source_observed_at"], "terms source_observed_at")
    if not available <= observed <= decision:
        raise IntentError("terms source clocks violate availability order")
    effective_from = _clock(terms["effective_from"], "terms effective_from")
    if effective_from > decision:
        raise IntentError("terms_observation not yet effective at decision")
    if terms["effective_until"] is not None:
        until = _clock(terms["effective_until"], "terms effective_until")
        if decision >= until:
            raise IntentError("terms_observation expired at the decision")
    return copy.deepcopy(terms)


def _intent_id(intent: Mapping) -> str:
    payload = {key: value for key, value in intent.items()
               if key != "expression_id"}
    digest = sha256(candidates.canonical_bytes(payload)).hexdigest()
    return EXPRESSION_ID_PREFIX + digest


def make_expression_intent(*, candidate: dict, preparation_record: dict,
                           terms_observation: dict, decision_at: str) -> dict:
    """Build a research intent from one original preparation and new terms.

    The new ``decision_at`` is a separate actual selection act at or after the
    binding decision and is never copied from the candidate; the original
    preparation receipt, oa3 ruler and frozen policy identity are retained.
    """
    candidate_id, frozen, frozen_sha = _candidate_identity(candidate)
    binding, receipt, binding_decision = _validated_binding(
        preparation_record, candidate_id=candidate_id, frozen=frozen)
    decision = _clock(decision_at, "decision_at")
    if decision < binding_decision:
        raise IntentError("new selection decision predates the binding decision")
    contract = _contract(binding["contract"], "binding.contract")
    terms = _validated_terms(terms_observation, contract=contract,
                             decision=decision)
    intent = {
        "schema": INTENT_SCHEMA,
        "expression_id": None,
        "candidate_id": candidate_id,
        "candidate_frozen_formation_sha256": frozen_sha,
        "preparation_receipt_sha256": receipt,
        "selection_policy_id": binding["selection_policy_id"],
        "selection_policy_sha256": binding["selection_policy_sha256"],
        "oa3_ruler": copy.deepcopy(_validated_ruler(binding["oa3_ruler"])),
        "contract": copy.deepcopy(contract),
        "terms_observation": terms,
        "decision_at": decision_at,
        "publication_available_at": None,
        "eligibility": ELIGIBILITY,
        "authority": copy.deepcopy(formation.POLICY["authority"]),
    }
    intent["expression_id"] = _intent_id(intent)
    return intent


def validate_expression_intent(intent: Any) -> dict:
    """Return a validated deep copy; recheck keys, types, clocks, terms,
    contract, constant all-false authority and digest identity. No external
    source, publication or eligibility effect is claimed."""
    validated = _exact_object(intent, _INTENT_KEYS, "intent")
    if validated["schema"] != INTENT_SCHEMA:
        raise IntentError("intent schema mismatch")
    if validated["eligibility"] != ELIGIBILITY:
        raise IntentError("intent eligibility is not research-intent-only")
    if validated["publication_available_at"] is not None:
        raise IntentError("intent claims durable publication availability")
    policy_id, policy_sha256 = _frozen_policy()
    if (validated["selection_policy_id"] != policy_id
            or validated["selection_policy_sha256"] != policy_sha256):
        raise IntentError("intent policy is not the frozen selection policy")
    if (not isinstance(validated["authority"], dict)
            or validated["authority"] != formation.POLICY["authority"]
            or any(value is not False for value in validated["authority"].values())):
        raise IntentError("intent authority is not the all-false policy authority")
    _str(validated["candidate_id"], "intent.candidate_id")
    _str(validated["candidate_frozen_formation_sha256"],
         "intent candidate_frozen_formation_sha256", hex64=True)
    _str(validated["preparation_receipt_sha256"],
         "intent preparation_receipt_sha256", hex64=True)
    _validated_ruler(validated["oa3_ruler"])
    decision = _clock(validated["decision_at"], "intent.decision_at")
    contract = _contract(validated["contract"], "intent.contract")
    if contract != validated["contract"]:
        raise IntentError("intent.contract is not canonical")
    _validated_terms(validated["terms_observation"], contract=contract,
                     decision=decision)
    if _intent_id(validated) != validated["expression_id"]:
        raise IntentError("intent expression id digest mismatch")
    return copy.deepcopy(validated)
