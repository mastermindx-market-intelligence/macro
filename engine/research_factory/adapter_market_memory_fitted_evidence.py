"""Exact COMPLETE fitted evidence for the existing context-only Factory runner.

Source composition only: no enrollment, provider, fit, query or lifecycle write.
The incumbent installed owner authenticates control/source/custody on every use.
"""
from dataclasses import dataclass
from hashlib import sha256
import json

from engine.neuralweb import market_memory_fitted_retrieval as retrieval
from engine.neuralweb import market_memory_fitted_evidence as evidence
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.research_factory import market_memory_fitted_factory_use as owner
from engine.research_factory import adapter_market_memory as candidate_owner
from engine.research_factory import schema

SCHEMA = "research_factory.market_memory_fitted_evidence_attachment.v2"
MAX_BYTES = 2 * 1024 * 1024
_TOKEN = object()
LIFECYCLE = {"projected_state": "proposed", "action": "no_action", "trial_accounting": "read_only",
    "transition_allowed": False, "count_allowed": False, "challenge_completed": False,
    "emission_enabled": False, "training_eligible": False, "promotion_eligible": False,
    "action_authority": False, "W2C_timely_admission": False, "effective_n": "not_estimated"}
LIMITATIONS = ["current_contextual_attachment_not_original_trial_query",
    "target_relevance_unassessed", "original_trial_not_evaluated",
    "contextual_purge_not_trial_label_interval_coverage",
    "citations_do_not_establish_entailment_or_predictive_skill",
    "component_source_vintages_not_authenticated", "subsequent_outcomes_not_attached",
    "historical_fit_or_index_existence_not_authenticated", "operational_study_not_admitted"]


class FittedMarketMemoryEvidenceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FittedMarketMemoryEvidenceInput:
    exact_trial_registration_bytes: bytes
    candidate_created_at: str
    attached_at: str
    selection: retrieval.FittedRetrievalCapability
    evidence: evidence.FittedEvidenceCapability
    policy: owner.FittedFactoryUsePolicy


@dataclass(frozen=True, slots=True, init=False)
class FittedMarketMemoryEvidenceAttachmentCapability:
    _body: bytes
    _digest: str
    _input: FittedMarketMemoryEvidenceInput
    _seal: object

    def __init__(self, body, request, *, _key=None):
        if _key is not _TOKEN:
            raise FittedMarketMemoryEvidenceError("owner_verified_fitted_attachment_required")
        for key, value in (("_body", body), ("_digest", sha256(body).hexdigest()),
                           ("_input", request), ("_seal", _TOKEN)):
            object.__setattr__(self, key, value)


def _require(ok, reason):
    if not ok:
        raise FittedMarketMemoryEvidenceError(reason)


def _joined(request):
    _require(type(request) is FittedMarketMemoryEvidenceInput
        and type(request.policy) is owner.FittedFactoryUsePolicy
        and type(request.selection) is retrieval.FittedRetrievalCapability
        and type(request.evidence) is evidence.FittedEvidenceCapability
        and type(request.exact_trial_registration_bytes) is bytes
        and 0 < len(request.exact_trial_registration_bytes) <= 256 * 1024,
        "bounded_typed_fitted_factory_input_required")
    binding = request.policy.disclose_binding()
    trial = binding["trial"]
    _require(sha256(request.exact_trial_registration_bytes).hexdigest() == trial["trial_registration_sha256"]
        and len(request.exact_trial_registration_bytes) == trial["bytes"]
        and request.candidate_created_at == binding["service"]["candidate_created_at"]
        and cohort.utc_instant(request.attached_at) >= max(
            cohort.utc_instant(request.candidate_created_at),
            cohort.utc_instant(binding["query_scope"]["query_cutoff"])),
        "exact_original_trial_and_attachment_clock_required")
    candidate = candidate_owner.build_market_memory_candidate(
        exact_trial_registration_bytes=request.exact_trial_registration_bytes,
        created_at=request.candidate_created_at)
    body = cohort.canonical(candidate)
    _require(sha256(body).hexdigest() == binding["candidate_sha256"]
        and len(body) == binding["candidate_bytes"]
        and candidate["artifacts"]["market_memory_conformance"]["spec"]["trial_registration_id"]
            == trial["trial_registration_id"], "exact_original_candidate_required")
    # Query scope alone is insufficient: reopen original COMPLETE and compare
    # the entire genuine disclosure, including native ranking and method/index.
    original, policy = request.policy.reopen_registered_fitted_query()
    _require(policy is request.policy, "same_fitted_factory_principal_required")
    native = retrieval.disclose_fitted_retrieval(request.selection, policy=policy)
    _require(native == retrieval.disclose_fitted_retrieval(original, policy=policy),
             "exact_original_complete_fitted_result_required")
    packet = evidence.disclose_fitted_evidence_packet(request.evidence, policy=policy)
    shared = ("query", "retrieval_id", "selection_sha256", "method", "index_id",
        "index_content_sha256", "membership_sha256", "requested_k", "denominator",
        "accounting", "status", "reason", "coverage", "authority")
    _require(all(packet[key] == native[key] for key in shared)
        and packet["owner"] == native["query_owner"]
        and packet["selection_claims"] == native["claims"], "exact_fitted_evidence_join_required")
    _require(len(packet["selected"]) == len(native["selected"]), "exact_ranked_fitted_sources_required")
    for rank, (row, selected) in enumerate(zip(packet["selected"], native["selected"], strict=True)):
        ref = selected["candidate"]
        _require(row["rank"] == rank and all(row[key] == ref[key] for key in
            ("capture_id", "context_id", "projection_id"))
            and row["fitted_feature_sha256"] == ref["feature_sha256"]
            and row["distance_q18"] == selected["distance_q18"]
            and row["arithmetic"] == selected["arithmetic"], "exact_ranked_fitted_sources_required")
    refs = [native["query"], *packet["selected"]]
    _require([(r["context_id"], r["capture_id"], r["packet_sha256"]) for r in refs] == [
        (c["context_id"], c["capture_id"], c["packet_sha256"]) for c in packet["source_cards"]],
        "ordered_original_fitted_source_join_required")
    _require(request.policy.disclose_binding() == binding
        and retrieval.disclose_fitted_retrieval(request.selection, policy=policy) == native
        and evidence.disclose_fitted_evidence_packet(request.evidence, policy=policy) == packet,
        "fitted_attachment_changed_during_join")
    return binding, candidate, native, packet


def _value(request):
    binding, candidate, native, packet = _joined(request)
    value = {"schema": SCHEMA, "authority": "display_only", "attached_at": request.attached_at,
        "candidate": candidate, "trial_binding": binding, "fitted_retrieval_join": native,
        "fitted_evidence_join": packet, "source_use": request.policy.disclosure(),
        "limitations": list(LIMITATIONS), "lifecycle": dict(LIFECYCLE)}
    value["attachment_id"] = "mmrffittedevidence_" + sha256(cohort.canonical(value)).hexdigest()
    errors = schema.validate_market_memory_fitted_evidence_attachment(value)
    _require(not errors, "canonical_fitted_attachment_required")
    return value


def build_fitted_market_memory_evidence_attachment(request):
    value = _value(request)
    body = cohort.canonical(value)
    _require(len(body) <= MAX_BYTES, "fitted_attachment_byte_limit")
    cap = FittedMarketMemoryEvidenceAttachmentCapability(body, request, _key=_TOKEN)
    # Reauthorization after envelope/source-use construction; changed input
    # refuses rather than silently replacing the immutable attachment.
    request.policy.disclose_binding()
    return cap


def disclose_fitted_market_memory_evidence_attachment(capability):
    _require(type(capability) is FittedMarketMemoryEvidenceAttachmentCapability
        and capability._seal is _TOKEN and type(capability._body) is bytes
        and len(capability._body) <= MAX_BYTES
        and sha256(capability._body).hexdigest() == capability._digest,
        "owner_verified_fitted_attachment_required")
    current = _value(capability._input)
    _require(cohort.canonical(current) == capability._body, "original_fitted_attachment_changed")
    capability._input.policy.disclose_binding()
    return json.loads(capability._body)
