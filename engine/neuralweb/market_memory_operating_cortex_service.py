"""W5B retained-source evidence, separate from immutable synthetic W5A.

This is a read-only consumer of the original trusted owner and sealed R2
selection. Byte-span closure proves what an original house output said. It
does not establish the meaning or usefulness of an analyst's narrative.
Application authentication, source-purpose admission and lifecycle stay with
their existing owners. No HTTP, model call, persistence or activation occurs.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_trusted as trusted

SCHEMA = "market_memory.operating_cortex_real_packet.v1"
PROFILE = "retained_original_house_macro_output.v1"
FIELDS = ("growth_score", "inflation_score", "quad", "liquidity_overlay", "cycle_tag")
MAX_PACKET_BYTES = 2 * 1024 * 1024
MAX_OWNER_PAYLOAD_BYTES = 64 * 1024 * 1024
MAX_CLAIMS = 32
_TOKEN = object()
_IMPORTED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()


class RealEvidenceError(ValueError):
    """Exact original evidence or a bounded consumer request was refused."""


@dataclass(frozen=True, slots=True)
class AnalystClaim:
    """An unassessed hypothesis; citations never turn it into a fact."""

    claim_id: str
    text: str
    context_ids: tuple[str, ...]
    fields: tuple[str, ...]
    falsifier: str | None = None

    def __post_init__(self):
        if (type(self.claim_id) is not str
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", self.claim_id)
                or type(self.text) is not str or not 1 <= len(self.text.encode()) <= 2048
                or type(self.context_ids) is not tuple or not 1 <= len(self.context_ids) <= 33
                or any(type(v) is not str or not re.fullmatch(r"mmctx_[a-f0-9]{64}", v)
                       for v in self.context_ids)
                or len(set(self.context_ids)) != len(self.context_ids)
                or type(self.fields) is not tuple or not self.fields
                or any(type(v) is not str or v not in FIELDS for v in self.fields)
                or len(set(self.fields)) != len(self.fields)
                or (self.falsifier is not None
                    and (type(self.falsifier) is not str or not 1 <= len(self.falsifier.encode()) <= 2048))):
            raise RealEvidenceError("bounded_analyst_claim_required")


@dataclass(frozen=True, slots=True, init=False)
class RealEvidenceCapability:
    _body: bytes
    _digest: str
    _retrieval: retrieval.EpisodeRetrievalCapability
    _resources: bytes
    _seal: object

    def __init__(self, body, selection, resources, *, _key=None):
        if _key is not _TOKEN:
            raise RealEvidenceError("owner_verified_real_evidence_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_retrieval", selection)
        object.__setattr__(self, "_resources", cohort.canonical(resources))
        object.__setattr__(self, "_seal", _TOKEN)


def _authorize(policy, action, resource):
    cohort.authorize(policy, action, resource)
    cohort.authorize(policy, "verify_retained_macro_retention", resource)


def _source_facts(feature: dict, receipt: dict) -> list[dict]:
    """Locate exact values within original canonical owner bytes, not prose."""
    body = cohort.canonical(feature)
    snapshot = receipt["feature_snapshot"]
    if (sha256(body).hexdigest() != snapshot["content_sha256"]
            or len(body) != snapshot["content_bytes"]):
        raise RealEvidenceError("original_feature_bytes_mismatch")
    state = feature["state"]
    state_body = cohort.canonical(state)
    marker = b'"state":' + state_body
    if body.count(marker) != 1:
        raise RealEvidenceError("unambiguous_original_state_span_required")
    state_offset = body.index(marker) + len(b'"state":')
    facts = []
    for name in FIELDS:
        value = state[name]
        token = cohort.canonical(name) + b":" + cohort.canonical(value)
        if state_body.count(token) != 1:
            raise RealEvidenceError("unambiguous_original_value_span_required")
        start = state_offset + state_body.index(token) + len(cohort.canonical(name)) + 1
        end = start + len(cohort.canonical(value))
        span = body[start:end]
        facts.append({"field": name, "value": value,
                      "meaning": "the_retained_house_output_reports_this_value",
                      "citation": {"snapshot_id": snapshot["snapshot_id"],
                                   "source_sha256": snapshot["content_sha256"],
                                   "source_bytes": len(body), "json_pointer": "/state/" + name,
                                   "start_byte": start, "end_byte_exclusive": end,
                                   "span_sha256": sha256(span).hexdigest(),
                                   "quoted_json": span.decode("utf-8")},
                      "structural_source_closure": True,
                      "underlying_component_truth_authenticated": False})
    return facts


def build_real_evidence_packet(
    selection: retrieval.EpisodeRetrievalCapability,
    reader: trusted.TrustedFileAsKnownAtReader,
    generation: pit.PinnedGenerationSnapshot,
    *, policy: object, claims: tuple[AnalystClaim, ...] = (),
) -> RealEvidenceCapability:
    """Bound all owner reads for this request, including pin authentication."""
    try:
        with pit.bounded_owner_reads(maximum_bytes=MAX_OWNER_PAYLOAD_BYTES):
            return _build_real_evidence_packet(
                selection, reader, generation, policy=policy, claims=claims,
            )
    except pit.OwnerReadBudgetError as exc:
        raise RealEvidenceError("aggregate_owner_read_byte_bound_exceeded") from exc


def _build_real_evidence_packet(
    selection, reader, generation, *, policy, claims,
) -> RealEvidenceCapability:
    """Resolve exactly the query and selected originals after current rights.

    No outcomes or alternative candidates are accepted here. Whole-pool
    disclosure remains governed by R2, including unreturned compared rows.
    """
    if (type(reader) is not trusted.TrustedFileAsKnownAtReader
            or type(generation) is not pit.PinnedGenerationSnapshot
            or generation.profile != trusted.TRUSTED_STORE_PROFILE):
        raise RealEvidenceError("exact_trusted_owner_and_generation_required")
    if (type(claims) is not tuple or len(claims) > MAX_CLAIMS
            or any(type(c) is not AnalystClaim for c in claims)
            or len({c.claim_id for c in claims}) != len(claims)):
        raise RealEvidenceError("bounded_unique_analyst_claims_required")
    selected = retrieval.disclose_episode_retrieval(selection, policy=policy)
    owner = selected["query_owner"]
    if any(owner[name] != getattr(generation, name) for name in
           ("store_id", "generation_id", "generation_sha256")):
        raise RealEvidenceError("exact_selection_generation_mismatch")
    metadata = {key: value for key, value in owner.items() if key != "subject_id"}
    metadata["requested_subject_id"] = owner["subject_id"]
    _authorize(policy, "read_real_synthesis_generation_metadata", metadata)
    # A private reader prevents unrelated requests evicting this identity pin.
    # Equal caller-supplied copies never cause one ancestry walk per source card.
    reader = trusted.TrustedFileAsKnownAtReader(reader.root)
    authenticated = reader.read_pinned_generation(
        generation_id=generation.generation_id, maximum_capture_count=256)
    if authenticated != generation:
        raise RealEvidenceError("exact_owner_generation_mismatch")
    generation = authenticated
    if len(selected["selected"]) > retrieval.MAX_K:
        raise RealEvidenceError("selected_context_bound_exceeded")
    refs = [("query", selected["query"], owner)] + [
        ("selected_neighbor", item["candidate"], item["candidate_owner"])
        for item in selected["selected"]]
    context_ids = {ref[1]["context_id"] for ref in refs}
    if len(context_ids) != len(refs):
        raise RealEvidenceError("duplicate_selected_context")
    if any(not set(c.context_ids) <= context_ids for c in claims):
        raise RealEvidenceError("claim_cites_unselected_context")
    resources = []
    receipts = []
    declared_bytes = 0
    for role, ref, ref_owner in refs:
        if any(ref_owner[name] != owner[name] for name in
               ("store_id", "generation_id", "generation_sha256", "subject_id", "query_cutoff")):
            raise RealEvidenceError("selected_subject_generation_or_cutoff_mismatch")
        resource = {**ref_owner, "retrieval_id": selected["retrieval_id"],
                    "context_id": ref["context_id"], "capture_id": ref["capture_id"]}
        metadata = {key: value for key, value in resource.items() if key != "subject_id"}
        metadata["requested_subject_id"] = ref_owner["subject_id"]
        _authorize(policy, "read_real_synthesis_capture_metadata", metadata)
        receipt = reader.read_pinned_capture_receipt(generation, query_id=ref_owner["query_id"])
        if (receipt["subject"]["subject_id"] != owner["subject_id"]
                or any(receipt[name] != ref[name] for name in
                       ("context_id", "capture_id", "packet_sha256"))):
            raise RealEvidenceError("original_selection_capture_mismatch")
        resource.update(subject_id=receipt["subject"]["subject_id"],
                        source_receipt_ids=list(receipt["source_receipt_ids"]),
                        packet_sha256=receipt["packet_sha256"],
                        feature_sha256=receipt["feature_snapshot"]["content_sha256"])
        _authorize(policy, "read_real_synthesis_source", resource)
        _authorize(policy, "use_retained_house_output_for_evidence_synthesis", resource)
        declared_bytes += len(cohort.canonical(receipt)) + receipt["packet_bytes"] + receipt["feature_snapshot"]["content_bytes"]
        if declared_bytes > MAX_OWNER_PAYLOAD_BYTES:
            raise RealEvidenceError("selected_original_payload_byte_bound_exceeded")
        receipts.append(receipt)
        resources.append(resource)
    originals = reader.read_pinned_capture_projections(
        generation, query_ids=tuple(item[2]["query_id"] for item in refs))
    if type(originals) is not tuple or len(originals) != len(refs):
        raise RealEvidenceError("complete_selected_originals_required")
    cards = []
    total_bytes = 0
    for (role, ref, _ref_owner), receipt, resource, original in zip(refs, receipts, resources, originals, strict=True):
        if type(original) is not trusted.PinnedTrustedCaptureProjection or original.receipt != receipt:
            raise RealEvidenceError("original_receipt_changed_during_read")
        _authorize(policy, "read_real_synthesis_source", resource)
        _authorize(policy, "use_retained_house_output_for_evidence_synthesis", resource)
        packet = original.stored.packet
        if (sha256(cohort.canonical(packet)).hexdigest() != ref["packet_sha256"]
                or packet["context_id"] != ref["context_id"]
                or packet["subject"]["subject_id"] != owner["subject_id"]):
            raise RealEvidenceError("original_packet_closure_mismatch")
        clocks = {"captured_at": receipt["captured_at"],
                  "raw_source_observed_at": receipt["source_evidence"]["raw_source_observed_at"],
                  "raw_source_built_at": receipt["source_evidence"]["raw_source_built_at"],
                  "feature_as_of": original.feature["as_of"], **packet["clocks"]}
        if any(cohort.utc_instant(v) > cohort.utc_instant(owner["query_cutoff"]) for v in clocks.values()):
            raise RealEvidenceError("source_unavailable_at_selection_cutoff")
        total_bytes += sum(len(cohort.canonical(v)) for v in (receipt, packet, original.feature))
        if total_bytes > MAX_OWNER_PAYLOAD_BYTES:
            raise RealEvidenceError("selected_original_payload_byte_bound_exceeded")
        cards.append({"role": role, "context_id": ref["context_id"], "capture_id": ref["capture_id"],
                      "packet_sha256": ref["packet_sha256"], "subject_id": owner["subject_id"],
                      "source_receipt_ids": list(receipt["source_receipt_ids"]),
                      "source_session": original.feature["source_artifact"]["source_asof"],
                      "clocks": clocks, "facts": _source_facts(original.feature, receipt),
                      "missing_feature_ids": list(receipt["missing_feature_ids"]),
                      "evidence_basis": "retained_original_house_output"})
    query_facts = {f["field"]: f["value"] for f in cards[0]["facts"]}
    differences = [{"context_id": card["context_id"], "field": fact["field"],
                    "query_value": query_facts[fact["field"]], "neighbor_value": fact["value"],
                    "meaning": "different_dated_outputs_not_a_logical_contradiction"}
                   for card in cards[1:] for fact in card["facts"]
                   if fact["value"] != query_facts[fact["field"]]]
    citations = {(card["context_id"], fact["field"]): fact["citation"]
                 for card in cards for fact in card["facts"]}
    audit = [{"claim_id": c.claim_id, "text": c.text, "context_ids": list(c.context_ids),
              "fields": list(c.fields), "structural_source_closure": True,
              "citation_refs": [{"context_id": context_id, **citations[(context_id, field)]}
                                for context_id in c.context_ids for field in c.fields],
              "entailment": "not_assessed", "unsupported_status": "unassessed_not_supported",
              "contradictory_evidence_review": "not_performed",
              "falsifier": c.falsifier, "falsifier_status": "named_not_tested" if c.falsifier else "missing"}
             for c in claims]
    value = {"schema": SCHEMA, "input_profile": PROFILE, "mode": selected["method_spec"]["mode"],
             "owner": owner, "retrieval_id": selected["retrieval_id"],
             "selection_sha256": selected["selection_sha256"],
             "method_spec_id": selected["method_spec"]["method_spec_id"],
             "denominator": selected["denominator"], "accounting": selected["accounting"],
             "status": selected["status"], "source_cards": cards,
             "state_differences": differences, "analyst_claim_audit": audit,
             "missing_evidence": ["component_source_vintages_not_authenticated",
                                  "cross_domain_evidence_not_bound", "subsequent_outcomes_not_attached",
                                  "contradictory_external_evidence_not_assessed",
                                  "independent_usefulness_study_not_run"],
             "claims": {"semantic_entailment_established": False, "causal_claim_established": False,
                        "forecast_skill_established": False, "independent_episodes_established": False,
                        "training_eligible": False, "promotion_eligible": False,
                        "operational_source_admission_granted": False},
             "source_ref": {"module": "engine/neuralweb/market_memory_operating_cortex_service.py",
                            "sha256": _IMPORTED_SOURCE_SHA256,
                            "assurance": "local_import_source_bytes_not_external_runtime_attestation"},
             "authority": dict(mm.AUTHORITY)}
    value["packet_id"] = "mmrealcortex_" + sha256(cohort.canonical(value)).hexdigest()
    body = cohort.canonical(value)
    if len(body) > MAX_PACKET_BYTES:
        raise RealEvidenceError("real_evidence_packet_byte_bound_exceeded")
    capability = RealEvidenceCapability(body, selection, resources, _key=_TOKEN)
    disclose_real_evidence_packet(capability, policy=policy)
    return capability


def disclose_real_evidence_packet(capability: RealEvidenceCapability, *, policy: object) -> dict:
    if (type(capability) is not RealEvidenceCapability or capability._seal is not _TOKEN
            or type(capability._body) is not bytes or len(capability._body) > MAX_PACKET_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise RealEvidenceError("owner_verified_real_evidence_required")
    retrieval.disclose_episode_retrieval(capability._retrieval, policy=policy)
    for resource in json.loads(capability._resources):
        _authorize(policy, "disclose_real_synthesis_source", resource)
        _authorize(policy, "use_retained_house_output_for_evidence_synthesis", resource)
    return json.loads(capability._body)
