"""Exact original source packets for the three sealed E0 conditions.

This is an in-process consumer for the trusted study executor, not a request
handler or study grant. The executor still owes authenticated task/registration
joins and durable reservation before a study look. No allocation, provider,
annotation, outcome, persistence or acceptance is performed here.

Read the union of the query and both original condition selections once, using
the incumbent native source-card reader. Joint read cost is not an isolated
condition cost. Reviewer views suppress explicit method metadata; source dates
and evidence counts can still reveal a condition. Actual blinding is not proved.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from engine.neuralweb import market_memory_operating_cortex_service as evidence
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.research_factory import market_memory_e0_baselines as baselines

CONDITIONS = ("no_memory", "recency", "fixed_l1")
MAX_PACKET_BYTES = 2 * 1024 * 1024
_TOKEN = object()


class E0ConditionEvidenceError(ValueError):
    """A sealed condition or exact native source join was refused."""


@dataclass(frozen=True, slots=True, init=False)
class E0ConditionEvidence:
    _body: bytes
    _digest: str
    _selection: baselines.E0ConditionSelections
    _resources: bytes
    _seal: object

    def __init__(self, body, selection, resources, *, _key=None):
        if _key is not _TOKEN:
            raise E0ConditionEvidenceError("sealed_condition_evidence_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_selection", selection)
        object.__setattr__(self, "_resources", cohort.canonical(resources))
        object.__setattr__(self, "_seal", _TOKEN)


def build_condition_evidence(selection, reader, generation, *, policy) -> E0ConditionEvidence:
    """Read query plus exactly the native no-memory/recency/fixed-L1 union.

    The supplied generation is freshly authenticated by the native reader.
    All compared candidates remain subject to current source rights, including
    candidates absent from every returned packet. No caller rows/ranks are used.
    """
    selected = baselines.disclose_condition_selections(selection, policy=policy)
    source = cohort.disclose_retained_context_cohort(selection._retrieval._cohort, policy=policy)
    if selected["membership_sha256"] != source["membership_sha256"]:
        raise E0ConditionEvidenceError("condition_cohort_binding_mismatch")
    if tuple(item["condition"] for item in selected["conditions"]) != CONDITIONS:
        raise E0ConditionEvidenceError("exact_three_conditions_required")
    owner = selected["query_owner"]
    rows = {row["context_id"]: row for row in source["rows"]}
    query = selected["query"]
    query_row = rows.get(query["context_id"])
    if (query_row is None or query_row["query_id"] != owner["query_id"]
            or any(query_row[key] != query[key] for key in ("capture_id", "packet_sha256"))):
        raise E0ConditionEvidenceError("exact_query_source_binding_required")
    eligible = {row["context_id"] for row in selected["accounting"]
                if row["reason"] == "numerically_eligible"}
    refs = [("query", query, owner)]
    seen = {query["context_id"]}
    for condition in selected["conditions"]:
        identities = [ref["context_id"] for ref in condition["selected"]]
        if (len(identities) != condition["returned"] or len(set(identities)) != len(identities)
                or len(identities) > selected["requested_k"] or not set(identities) <= eligible
                or (condition["condition"] == "no_memory" and identities)):
            raise E0ConditionEvidenceError("original_condition_selection_required")
        for ref in condition["selected"]:
            row = rows.get(ref["context_id"])
            if row is None or any(row[key] != ref[key] for key in ref):
                raise E0ConditionEvidenceError("exact_selected_source_binding_required")
            if ref["context_id"] not in seen:
                refs.append(("selected_neighbor", ref, {**owner, "query_id": row["query_id"]}))
                seen.add(ref["context_id"])
    try:
        with pit.bounded_owner_reads(maximum_bytes=evidence.MAX_OWNER_PAYLOAD_BYTES):
            cards, resources = evidence._read_source_cards(
                reader, generation, owner=owner, refs=refs, policy=policy,
                retrieval_id="mme0selection_" + selected["condition_selection_sha256"])
    except pit.OwnerReadBudgetError as exc:
        raise E0ConditionEvidenceError("aggregate_owner_read_byte_bound_exceeded") from exc
    by_context = {card["context_id"]: card for card in cards}
    conditions = []
    for item in selected["conditions"]:
        chosen = [by_context[query["context_id"]]] + [by_context[ref["context_id"]]
                                                       for ref in item["selected"]]
        query_facts = {fact["field"]: fact["value"] for fact in chosen[0]["facts"]}
        conditions.append({"condition": item["condition"], "status": item["status"],
            "returned": item["returned"], "source_cards": chosen,
            "state_differences": [{"context_id": card["context_id"], "field": fact["field"],
                "query_value": query_facts[fact["field"]], "neighbor_value": fact["value"],
                "meaning": "different_dated_outputs_not_a_logical_contradiction"}
                for card in chosen[1:] for fact in card["facts"]
                if fact["value"] != query_facts[fact["field"]]]})
    value = {"schema": "research_factory.market_memory_e0_condition_evidence.v1",
        "authority": "display_only", "query": query, "query_owner": owner,
        "membership_sha256": selected["membership_sha256"],
        "condition_selection_sha256": selected["condition_selection_sha256"],
        "fixed_selection_sha256": selected["fixed_selection_sha256"],
        "method_spec": selected["method_spec"], "requested_k": selected["requested_k"],
        "accounting": selected["accounting"], "denominator": selected["denominator"],
        "conditions": conditions,
        "cost_scope": "joint_native_source_union_not_isolated_condition_cost",
        "source_reader_sha256": evidence._IMPORTED_SOURCE_SHA256,
        "limitations": ["original_house_output_not_constituent_truth",
            "subsequent_outcomes_not_attached", "semantic_entailment_not_assessed",
            "exact_registered_task_and_study_admission_not_established",
            "independent_reviewers_and_blinding_not_established"],
        "study_admitted": False, "labels_read": False, "provider_invoked": False,
        "evaluation_performed": False, "runtime_writes": False}
    body = cohort.canonical(value)
    if len(body) > MAX_PACKET_BYTES:
        raise E0ConditionEvidenceError("condition_evidence_byte_bound_exceeded")
    cap = E0ConditionEvidence(body, selection, resources, _key=_TOKEN)
    disclose_condition_evidence(cap, policy=policy)
    return cap


def disclose_condition_evidence(capability, *, policy) -> dict:
    """Trusted executor audit view; includes the condition identities."""
    if (type(capability) is not E0ConditionEvidence or capability._seal is not _TOKEN
            or type(capability._body) is not bytes or len(capability._body) > MAX_PACKET_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise E0ConditionEvidenceError("sealed_condition_evidence_required")
    selected = baselines.disclose_condition_selections(capability._selection, policy=policy)
    for resource in json.loads(capability._resources):
        evidence._authorize(policy, "disclose_real_synthesis_source", resource)
        evidence._authorize(policy, "use_retained_house_output_for_evidence_synthesis", resource)
    value = json.loads(capability._body)
    if selected["condition_selection_sha256"] != value["condition_selection_sha256"]:
        raise E0ConditionEvidenceError("condition_selection_changed")
    return value


def disclose_method_redacted_view(capability, *, condition: str, policy) -> dict:
    """One source view for an already authorized study executor.

    The executor selects its preregistered arm privately and controls exposure.
    This selector is not a user endpoint. It cannot establish reviewer blindness:
    no-memory is recognizable and source dates/counts remain financially useful.
    """
    if type(condition) is not str or condition not in CONDITIONS:
        raise E0ConditionEvidenceError("registered_condition_required")
    value = disclose_condition_evidence(capability, policy=policy)
    item = next(item for item in value["conditions"] if item["condition"] == condition)
    return {"schema": "research_factory.market_memory_e0_method_redacted_sources.v1",
        "authority": "display_only", "source_cards": item["source_cards"],
        "state_differences": item["state_differences"],
        "explicit_method_identity_redacted": True, "actual_blinding_established": False,
        "limitations": ["source_dates_and_counts_may_reveal_condition",
            "original_house_output_not_constituent_truth", "subsequent_outcomes_not_attached",
            "no_semantic_causal_predictive_or_action_authority"]}
