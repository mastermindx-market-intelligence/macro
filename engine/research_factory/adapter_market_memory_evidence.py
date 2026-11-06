"""Explicit contextual evidence consumption; no Research Factory lifecycle grant.

The original W6A candidate stays byte-for-byte canonical and proposed. A current
installed owner registration joins it to real retained source capabilities, not
to an invented historical trial query or evaluation result.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_operating_cortex_service as evidence
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_trusted as trusted
from engine.research_factory import adapter_market_memory as candidate_owner
from engine.research_factory import schema as factory_schema

SCHEMA = "research_factory.market_memory_evidence_attachment.v1"
MAX_BYTES = 2 * 1024 * 1024
_TOKEN = object()


class MarketMemoryEvidenceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class MarketMemoryEvidenceInput:
    exact_trial_registration_bytes: bytes
    candidate_created_at: str
    attached_at: str
    selection: retrieval.EpisodeRetrievalCapability
    evidence: evidence.RealEvidenceCapability
    policy: use.RetainedFactoryUsePolicy


@dataclass(frozen=True, slots=True, init=False)
class MarketMemoryEvidenceAttachmentCapability:
    _body: bytes
    _digest: str
    _input: MarketMemoryEvidenceInput
    _seal: object

    def __init__(self, body, request, *, _key=None):
        if _key is not _TOKEN:
            raise MarketMemoryEvidenceError("owner_verified_factory_evidence_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_input", request)
        object.__setattr__(self, "_seal", _TOKEN)


def _joined(request):
    if (type(request) is not MarketMemoryEvidenceInput
            or type(request.policy) is not use.RetainedFactoryUsePolicy
            or type(request.exact_trial_registration_bytes) is not bytes
            or not 0 < len(request.exact_trial_registration_bytes) <= 256 * 1024):
        raise MarketMemoryEvidenceError("bounded_typed_factory_evidence_input_required")
    binding = request.policy.disclose_binding()
    if (sha256(request.exact_trial_registration_bytes).hexdigest() != binding["trial_registration_sha256"]
            or request.candidate_created_at != binding["registered_at"]
            or cohort.utc_instant(request.attached_at) < cohort.utc_instant(binding["registered_at"])):
        raise MarketMemoryEvidenceError("exact_current_trial_binding_required")
    candidate = candidate_owner.build_market_memory_candidate(
        exact_trial_registration_bytes=request.exact_trial_registration_bytes,
        created_at=request.candidate_created_at)
    if candidate["artifacts"]["market_memory_conformance"]["spec"]["trial_registration_id"] != binding["trial_registration_id"]:
        raise MarketMemoryEvidenceError("trial_identity_mismatch")
    selected = retrieval.disclose_episode_retrieval(request.selection, policy=request.policy)
    packet = evidence.disclose_real_evidence_packet(request.evidence, policy=request.policy)
    if (selected["query"]["context_id"] != binding["context_id"]
            or selected["query"]["capture_id"] != binding["capture_id"]
            or selected["method_spec"]["method_spec_id"] != binding["method_spec_id"]
            or selected["method_spec"]["mode"] != binding["mode"]
            or selected["requested_k"] != binding["limit"]
            or packet["retrieval_id"] != selected["retrieval_id"]
            or packet["selection_sha256"] != selected["selection_sha256"]
            or packet["method_spec_id"] != binding["method_spec_id"]
            or packet["owner"] != selected["query_owner"]):
        raise MarketMemoryEvidenceError("exact_retained_evidence_join_required")
    for key in ("store_id", "generation_id", "generation_sha256", "subject_id", "query_cutoff", "query_id"):
        if selected["query_owner"][key] != binding[key]:
            raise MarketMemoryEvidenceError("binding_owner_mismatch")
    refs = [selected["query"], *[row["candidate"] for row in selected["selected"]]]
    if [(v["context_id"], v["capture_id"], v["packet_sha256"]) for v in refs] != [
            (v["context_id"], v["capture_id"], v["packet_sha256"]) for v in packet["source_cards"]]:
        raise MarketMemoryEvidenceError("ordered_original_source_join_required")
    return binding, candidate, selected, packet


def build_market_memory_evidence_attachment(request) -> MarketMemoryEvidenceAttachmentCapability:
    binding, candidate, selected, packet = _joined(request)
    value = {"schema": SCHEMA, "authority": "display_only", "attached_at": request.attached_at,
             "candidate": candidate, "trial_binding": binding,
             "contextual_retrieval_join": selected, "real_evidence_join": packet,
             "source_use": request.policy.disclosure(),
             "limitations": ["current_contextual_attachment_not_original_trial_query",
                             "target_relevance_unassessed", "original_trial_not_evaluated",
                             "contextual_purge_not_trial_label_interval_coverage",
                             "citations_do_not_establish_entailment_or_predictive_skill"],
             "lifecycle": {"projected_state": "proposed", "action": "no_action",
                           "trial_accounting": "read_only", "transition_allowed": False,
                           "count_allowed": False, "challenge_completed": False,
                           "emission_enabled": False, "training_eligible": False,
                           "promotion_eligible": False, "action_authority": False,
                           "W2C_timely_admission": False, "effective_n": "not_estimated"}}
    value["attachment_id"] = "mmrfevidence_" + sha256(cohort.canonical(value)).hexdigest()
    errors = factory_schema.validate_market_memory_evidence_attachment(value)
    if errors:
        raise MarketMemoryEvidenceError("; ".join(errors))
    body = cohort.canonical(value)
    if len(body) > MAX_BYTES:
        raise MarketMemoryEvidenceError("factory_evidence_byte_bound_exceeded")
    cap = MarketMemoryEvidenceAttachmentCapability(body, request, _key=_TOKEN)
    disclose_market_memory_evidence_attachment(cap)
    return cap


def disclose_market_memory_evidence_attachment(capability) -> dict:
    if (type(capability) is not MarketMemoryEvidenceAttachmentCapability
            or capability._seal is not _TOKEN or type(capability._body) is not bytes
            or len(capability._body) > MAX_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise MarketMemoryEvidenceError("owner_verified_factory_evidence_required")
    binding, candidate, selected, packet = _joined(capability._input)
    value = json.loads(capability._body)
    if (value["trial_binding"] != binding or value["candidate"] != candidate
            or value["contextual_retrieval_join"] != selected or value["real_evidence_join"] != packet):
        raise MarketMemoryEvidenceError("factory_evidence_binding_changed")
    capability._input.policy.disclosure()
    return value


def load_registered_factory_evidence(root: Path, *, binding_id: str,
                                     attached_at: str) -> MarketMemoryEvidenceInput:
    """Trusted existing CLI owner: registration and service checks precede reads."""
    root = Path(root)
    policy = use.RetainedFactoryUsePolicy(root, binding_id=binding_id)
    binding = policy.disclose_binding()
    path = root / binding["trial_record"]
    if not path.resolve().is_relative_to(root.resolve()):
        raise MarketMemoryEvidenceError("registered_trial_path_escaped")
    with path.open("rb") as stream:
        body = stream.read(256 * 1024 + 1)
    if len(body) > 256 * 1024 or sha256(body).hexdigest() != binding["trial_registration_sha256"]:
        raise MarketMemoryEvidenceError("original_trial_bytes_required")
    registration = policy.registration
    method = retrieval.RetainedContextMethodSpec(
        registration["method"]["purge_calendar_days"],
        registration["method"]["embargo_calendar_days"], binding["mode"])
    if method.disclosure()["method_spec_id"] != binding["method_spec_id"]:
        raise MarketMemoryEvidenceError("registered_factory_method_required")
    policy.disclose_binding()
    with pit.bounded_owner_reads(maximum_bytes=64 * 1024 * 1024):
        reader = trusted.TrustedFileAsKnownAtReader(trusted.default_trusted_store_root(root))
        selection, packet = mm.compose_retained_macro_capabilities(reader, policy=policy,
            **{k: binding[k] for k in ("query_id", "generation_id", "generation_sha256",
                                      "subject_id", "query_cutoff", "limit")}, method=method)
        request = MarketMemoryEvidenceInput(body, binding["registered_at"], attached_at,
                                            selection, packet, policy)
        _joined(request)
        return request
