"""Passive fitted-retrieval to exact-source-evidence composition (opt-in).

This module is a read-only consumer of the native sealed fitted retrieval and
of the original trusted owner. It binds the fitted selection's own feature
identity to the exact original house outputs that the shared cortex read path
already authenticates. It never fits, stores, studies, activates or labels
anything, and it never fabricates or widens a capability, a policy or a claim.

Current Macro main carries neither the native fitted producer nor the
extracted shared cortex read helper. Both are resolved lazily and refused
clearly, before any owner byte is read, instead of substituting a local
approximation of either one.
"""
from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_trusted as trusted

SCHEMA = "market_memory.fitted_evidence_packet.v1"
PROFILE = "retained_original_house_macro_output.fitted_selection.v1"
MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_OWNER_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_SELECTED = 32
PRODUCER_MODULE = "engine.neuralweb.market_memory_fitted_retrieval"
HELPER_MODULE = "engine.neuralweb.market_memory_operating_cortex_service"
_TOKEN = object()
_IMPORTED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


class FittedEvidenceError(ValueError):
    """Exact native fitted selection, owner identity or source bytes refused."""


def _resolve_dependencies():
    """Resolve the native producer and the shared cortex read helper lazily.

    Both dependencies are optional on the current branch. Their absence is a
    plain refusal, never a locally rebuilt substitute and never a silent
    fallback to the baseline neighbour.
    """
    try:
        producer = importlib.import_module(PRODUCER_MODULE)
    except ImportError as exc:
        raise FittedEvidenceError("native_fitted_retrieval_producer_unavailable") from exc
    try:
        cortex = importlib.import_module(HELPER_MODULE)
    except ImportError as exc:
        raise FittedEvidenceError("shared_source_card_helper_unavailable") from exc
    if not hasattr(cortex, "_read_source_cards"):
        raise FittedEvidenceError("shared_source_card_helper_unavailable")
    if getattr(cortex, "MAX_OWNER_PAYLOAD_BYTES", None) != 64 * 1024 * 1024:
        raise FittedEvidenceError("shared_owner_read_ceiling_mismatch")
    return producer, cortex


@dataclass(frozen=True, slots=True, init=False)
class FittedEvidenceCapability:
    """A request-local sealed fitted-evidence result.

    Serialization never grants authority. The capability keeps the native
    fitted selection and the exact owner resources it was built from, so a
    disclosure can re-run every current right check.
    """

    _body: bytes
    _digest: str
    _selection: object
    _native_digest: str
    _resources: bytes
    _seal: object

    def __init__(self, body, selection, resources, *, native_digest=None, _key=None):
        if (_key is not _TOKEN or type(native_digest) is not str
                or len(native_digest) != 64):
            raise FittedEvidenceError("owner_verified_fitted_evidence_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_selection", selection)
        object.__setattr__(self, "_native_digest", native_digest)
        object.__setattr__(self, "_resources", cohort.canonical(resources))
        object.__setattr__(self, "_seal", _TOKEN)


def build_fitted_evidence_packet(
    selection: object,
    reader: trusted.TrustedFileAsKnownAtReader,
    generation: pit.PinnedGenerationSnapshot,
    *, policy: object,
) -> FittedEvidenceCapability:
    """Compose exact source evidence for one sealed native fitted selection.

    The native fitted retrieval is disclosed before any owner byte is read and
    again at every disclosure. The selection, not the caller, decides which
    neighbours exist and in which order; the shared cortex read path decides
    which original bytes a source card may cite.
    """
    producer, cortex = _resolve_dependencies()
    if type(selection) is not producer.FittedRetrievalCapability:
        raise FittedEvidenceError("exact_native_fitted_retrieval_capability_required")
    if (type(reader) is not trusted.TrustedFileAsKnownAtReader
            or type(generation) is not pit.PinnedGenerationSnapshot
            or generation.profile != trusted.TRUSTED_STORE_PROFILE):
        raise FittedEvidenceError("exact_trusted_owner_and_generation_required")
    try:
        with pit.bounded_owner_reads(maximum_bytes=MAX_OWNER_PAYLOAD_BYTES):
            return _build_fitted_evidence_packet(
                selection, reader, generation, policy=policy,
                producer=producer, cortex=cortex,
            )
    except pit.OwnerReadBudgetError as exc:
        raise FittedEvidenceError("aggregate_owner_read_byte_bound_exceeded") from exc


def _build_fitted_evidence_packet(
    selection, reader, generation, *, policy, producer, cortex,
) -> FittedEvidenceCapability:
    """Resolve the exact query and fitted neighbours after current rights.

    Nothing here builds a fitted or baseline capability, reads an outcome, or
    consults the baseline's own k=1 neighbour. Only the native fitted
    selection and the pinned generation decide what may be read.
    """
    # The native disclosure rechecks the selected training window and the
    # complete eligible comparison pool before any original byte is read.
    value = producer.disclose_fitted_retrieval(selection, policy=policy)
    owner = value["query_owner"]
    if any(owner[name] != getattr(generation, name) for name in
           ("store_id", "generation_id", "generation_sha256")):
        raise FittedEvidenceError("exact_selection_generation_mismatch")
    selected = value["selected"]
    if len(selected) > MAX_SELECTED:
        raise FittedEvidenceError("selected_context_bound_exceeded")
    # Generation metadata is authorized before the pinned index is consulted.
    metadata = {key: item for key, item in owner.items() if key != "subject_id"}
    metadata["requested_subject_id"] = owner["subject_id"]
    cortex._authorize(policy, "read_real_synthesis_generation_metadata", metadata)

    # The population is the one the native fitted capability was built over.
    # Its membership digest must equal the fitted selection's own membership
    # digest, which proves it is the same eligible pool. The baseline
    # capability's own k=1 neighbour is never read here: only the population
    # and the fitted selection decide what may be resolved.
    population = selection._eligibility._cohort
    cohort_value = cohort.disclose_retained_context_cohort(population, policy=policy)
    if cohort_value["membership_sha256"] != value["membership_sha256"]:
        raise FittedEvidenceError("fitted_population_membership_mismatch")
    capabilities = cohort.read_cohort_feature_capabilities(population, policy=policy)
    by_capture: dict[str, object] = {}
    for row, capability in zip(cohort_value["rows"], capabilities, strict=True):
        if capability is None:
            continue
        capture_id = row["capture_id"]
        if capture_id in by_capture:
            raise FittedEvidenceError("duplicate_capture_identity_in_population")
        by_capture[capture_id] = capability

    pinned = {entry.capture_id: entry for entry in generation.captures}
    query = value["query"]
    query_entry = pinned.get(query["capture_id"])
    if (query_entry is None
            or query_entry.context_id != query["context_id"]
            or query_entry.packet_sha256 != query["packet_sha256"]
            or query_entry.query_id != owner["query_id"]):
        raise FittedEvidenceError("exact_query_generation_identity_mismatch")
    query_capability = by_capture.get(query["capture_id"])
    if query_capability is None:
        raise FittedEvidenceError("query_projection_missing_from_population")
    query_disclosure = features.disclose_episode_features(
        query_capability, policy=policy, for_comparison=True)
    if (query_disclosure["owner"] != owner
            or any(query_disclosure[name] != query[name] for name in
                   ("projection_id", "context_id", "capture_id", "packet_sha256"))):
        raise FittedEvidenceError("query_owner_binding_mismatch")

    # The query source card is read first; the fitted neighbours follow in the
    # fitted ranking order, never in baseline order and never by nearest date.
    refs = [("query", {"capture_id": query_entry.capture_id,
                       "context_id": query_entry.context_id,
                       "packet_sha256": query_entry.packet_sha256}, owner)]
    disclosures = [query_disclosure]
    seen_capture = {query_entry.capture_id}
    seen_context = {query_entry.context_id}
    selected_rows = []
    for rank, item in enumerate(selected):
        candidate = item["candidate"]
        capture_id = candidate["capture_id"]
        context_id = candidate["context_id"]
        if capture_id in seen_capture or context_id in seen_context:
            raise FittedEvidenceError("duplicate_selected_context")
        seen_capture.add(capture_id)
        seen_context.add(context_id)
        entry = pinned.get(capture_id)
        if entry is None:
            raise FittedEvidenceError("fitted_candidate_not_in_pinned_generation")
        capability = by_capture.get(capture_id)
        if capability is None:
            raise FittedEvidenceError("fitted_candidate_projection_missing")
        disclosure = features.disclose_episode_features(
            capability, policy=policy, for_comparison=True)
        if (entry.context_id != context_id
                or entry.packet_sha256 != disclosure["packet_sha256"]
                or entry.query_id != disclosure["owner"]["query_id"]
                or disclosure["capture_id"] != capture_id
                or disclosure["context_id"] != context_id
                or any(disclosure["owner"][name] != owner[name] for name in
                       ("store_id", "generation_id", "generation_sha256",
                        "subject_id", "query_cutoff"))):
            raise FittedEvidenceError("fitted_candidate_identity_mismatch")
        # The fitted candidate must be the very owner projection that was
        # ranked. A different feature body, or a different projection id for
        # the same capture, is a different original.
        if (sha256(capability._body).hexdigest() != candidate["feature_sha256"]
                or disclosure["projection_id"] != candidate["projection_id"]):
            raise FittedEvidenceError("fitted_candidate_feature_digest_mismatch")
        refs.append(("selected_neighbor",
                     {"capture_id": entry.capture_id, "context_id": entry.context_id,
                      "packet_sha256": entry.packet_sha256},
                     disclosure["owner"]))
        disclosures.append(disclosure)
        selected_rows.append({
            "rank": rank,
            "context_id": context_id,
            "capture_id": capture_id,
            "projection_id": candidate["projection_id"],
            "fitted_feature_sha256": candidate["feature_sha256"],
            "owner_feature_sha256": disclosure["feature_snapshot"]["content_sha256"],
            "packet_sha256": entry.packet_sha256,
            "query_id": entry.query_id,
            "distance_q18": item.get("distance_q18"),
            "arithmetic": item.get("arithmetic"),
        })

    cards, resources = cortex._read_source_cards(
        reader, generation, owner=owner, refs=refs, policy=policy,
        retrieval_id=value["retrieval_id"],
    )
    for card, resource, disclosure in zip(cards, resources, disclosures, strict=True):
        digest = resource["feature_sha256"]
        if digest != disclosure["feature_snapshot"]["content_sha256"]:
            raise FittedEvidenceError("source_fact_feature_digest_mismatch")
        if (card["capture_id"] != resource["capture_id"]
                or card["context_id"] != resource["context_id"]
                or card["packet_sha256"] != resource["packet_sha256"]):
            raise FittedEvidenceError("source_card_identity_mismatch")
        for fact in card["facts"]:
            citation = fact["citation"]
            if (citation["source_sha256"] != digest
                    or citation["snapshot_id"] != "mmsnap_" + digest):
                raise FittedEvidenceError("source_fact_feature_digest_mismatch")

    query_facts = {fact["field"]: fact["value"] for fact in cards[0]["facts"]}
    differences = [{"context_id": card["context_id"], "field": fact["field"],
                    "query_value": query_facts[fact["field"]], "neighbor_value": fact["value"],
                    "meaning": "different_dated_outputs_not_a_logical_contradiction"}
                   for card in cards[1:] for fact in card["facts"]
                   if fact["field"] in query_facts and fact["value"] != query_facts[fact["field"]]]
    packet = {
        "schema": SCHEMA,
        "input_profile": PROFILE,
        "mode": value["method"]["eligibility_method_spec"]["mode"],
        "owner": owner,
        "query": value["query"],
        "retrieval_id": value["retrieval_id"],
        "selection_sha256": value["selection_sha256"],
        "method": value["method"],
        "method_id": value["method"]["method_id"],
        "index_id": value["index_id"],
        "index_content_sha256": value["index_content_sha256"],
        "membership_sha256": value["membership_sha256"],
        "requested_k": value["requested_k"],
        "denominator": value["denominator"],
        "accounting": value["accounting"],
        "status": value["status"],
        "reason": value["reason"],
        "coverage": value["coverage"],
        "selected": selected_rows,
        "source_cards": cards,
        "state_differences": differences,
        "missing_evidence": ["component_source_vintages_not_authenticated",
                             "cross_domain_evidence_not_bound",
                             "subsequent_outcomes_not_attached",
                             "contradictory_external_evidence_not_assessed",
                             "independent_usefulness_study_not_run",
                             "fitted_selection_better_than_baseline_not_established",
                             "normalizer_training_provenance_not_attested_by_this_packet"],
        "selection_claims": value["claims"],
        "claims": {"semantic_entailment_established": False,
                   "causal_claim_established": False,
                   "forecast_skill_established": False,
                   "independent_episodes_established": False,
                   "training_eligible": False,
                   "promotion_eligible": False,
                   "operational_source_admission_granted": False,
                   "operational_study_admission": False,
                   "action_admitted": False,
                   "source_activated": False},
        "source_ref": {"module": "engine/neuralweb/market_memory_fitted_evidence.py",
                       "sha256": _IMPORTED_SOURCE_SHA256,
                       "assurance": "local_import_source_bytes_not_external_runtime_attestation"},
        "authority": dict(mm.AUTHORITY),
    }
    packet["packet_id"] = "mmfittedevidence_" + sha256(cohort.canonical(packet)).hexdigest()
    body = cohort.canonical(packet)
    if len(body) > MAX_PACKET_BYTES:
        raise FittedEvidenceError("real_evidence_packet_byte_bound_exceeded")
    capability = FittedEvidenceCapability(
        body, selection, resources,
        native_digest=sha256(cohort.canonical(value)).hexdigest(), _key=_TOKEN)
    disclose_fitted_evidence_packet(capability, policy=policy)
    return capability


def disclose_fitted_evidence_packet(capability: FittedEvidenceCapability, *, policy: object) -> dict:
    """Return a detached fitted-evidence packet after every current recheck.

    The native fitted disclosure runs first and last, the per-original source
    use and retention rights are re-authorized in between, and the immutable
    binding to the original selection is compared before anything is returned.
    """
    producer, cortex = _resolve_dependencies()
    if (type(capability) is not FittedEvidenceCapability or capability._seal is not _TOKEN
            or type(capability._body) is not bytes or len(capability._body) > MAX_PACKET_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise FittedEvidenceError("owner_verified_fitted_evidence_required")
    native = producer.disclose_fitted_retrieval(capability._selection, policy=policy)
    value = json.loads(capability._body)
    if sha256(cohort.canonical(native)).hexdigest() != capability._native_digest:
        raise FittedEvidenceError("original_fitted_selection_changed")
    for resource in json.loads(capability._resources):
        cortex._authorize(policy, "disclose_real_synthesis_source", resource)
        cortex._authorize(policy, "use_retained_house_output_for_evidence_synthesis", resource)
    # Final recheck: a right revoked during the per-original source checks
    # must not escape merely because the packet was already sealed.
    final = producer.disclose_fitted_retrieval(capability._selection, policy=policy)
    if sha256(cohort.canonical(final)).hexdigest() != capability._native_digest:
        raise FittedEvidenceError("original_fitted_selection_changed")
    return value
