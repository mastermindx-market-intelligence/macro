"""Complete pinned retained house-output cohort, separate from W2C admission.

Original objects remain actual output. Applying a newer method is hypothetical
or current contextual support. Rights come from the trusted application policy.
Process capabilities prevent accidental forgery, not hostile Python execution.
"""
from __future__ import annotations

import copy
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_episode_features as features
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted

SCHEMA = "market_memory.retained_context_cohort.v1"
GROUPING = "house_source_session_earliest_capture.v1"
MAX_CAPTURES = 256
MAX_OWNER_BYTES = 64 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
_TOKEN = object()
_IMPORTED_SOURCE_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
_SUBJECT = re.compile(r"mmsecurity_[a-f0-9]{64}\Z")
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")


class RetainedContextCohortError(ValueError):
    """Cohort source, identity, temporal or bound qualification refused."""


class RetainedContextAccessError(RetainedContextCohortError):
    """Current retention/use/disclosure rights refused; no private counts escape."""


def source_identity() -> dict:
    """Source-file coordinate at import, not an external runtime attestation."""
    return {"module": "engine/neuralweb/market_memory_retained_context_cohort.py",
            "sha256": _IMPORTED_SOURCE_SHA256,
            "assurance": "source_file_bytes_at_import_not_external_runtime_attestation"}


def canonical(value: object) -> bytes:
    return json.dumps(value, allow_nan=False, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def utc_instant(value: object) -> datetime:
    if type(value) is not str or not _UTC.fullmatch(value):
        raise RetainedContextCohortError("original_utc_clock_required")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError as exc:
        raise RetainedContextCohortError("original_utc_clock_required") from exc


def authorize(policy: object, action: str, resource: dict) -> None:
    if (type(getattr(policy, "policy_id", None)) is not str
            or not 1 <= len(policy.policy_id) <= 256
            or not callable(getattr(policy, "check", None))):
        raise RetainedContextAccessError("authenticated_application_policy_required")
    try:
        decision = policy.check(action, copy.deepcopy(resource))
    except Exception as exc:
        raise RetainedContextAccessError("source_usage_not_admitted") from exc
    if decision is not None:
        raise RetainedContextAccessError("policy_must_return_no_value_on_authorization")


@dataclass(frozen=True, slots=True, init=False)
class RetainedContextCohortCapability:
    _body: bytes
    _digest: str
    _resource: bytes
    _features: tuple[features.EpisodeFeatureCapability | None, ...]
    _seal: object

    def __init__(self, body: bytes, resource: bytes, projections: tuple, *, _key=None):
        if _key is not _TOKEN:
            raise RetainedContextCohortError("owner_verified_cohort_capability_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_resource", resource)
        object.__setattr__(self, "_features", projections)
        object.__setattr__(self, "_seal", _TOKEN)


def _verify(capability: RetainedContextCohortCapability) -> dict:
    if (type(capability) is not RetainedContextCohortCapability
            or capability._seal is not _TOKEN or type(capability._body) is not bytes
            or len(capability._body) > MAX_MANIFEST_BYTES
            or sha256(capability._body).hexdigest() != capability._digest
            or type(capability._resource) is not bytes
            or type(capability._features) is not tuple):
        raise RetainedContextCohortError("owner_verified_cohort_capability_required")
    value = json.loads(capability._body)
    if len(value["rows"]) != len(capability._features):
        raise RetainedContextCohortError("cohort_feature_closure_mismatch")
    return value


def read_retained_context_cohort(
    reader: trusted.TrustedFileAsKnownAtReader,
    generation: pit.PinnedGenerationSnapshot,
    *, subject_id: str, query_cutoff: str, policy: object,
) -> RetainedContextCohortCapability:
    """Authenticate every capture in an exact generation before grouping.

    Denominator is that generation, never all scheduled sessions/market history.
    Earliest capture representative is fixed before missingness/quality filtering.
    """
    if (type(reader) is not trusted.TrustedFileAsKnownAtReader
            or type(generation) is not pit.PinnedGenerationSnapshot
            or generation.profile != trusted.TRUSTED_STORE_PROFILE):
        raise RetainedContextCohortError("exact_trusted_owner_and_pin_required")
    if type(subject_id) is not str or not _SUBJECT.fullmatch(subject_id):
        raise RetainedContextCohortError("exact_subject_required")
    cutoff = utc_instant(query_cutoff)
    if len(generation.captures) > MAX_CAPTURES:
        raise RetainedContextCohortError("whole_generation_capture_bound_exceeded")
    resource = {"store_id": generation.store_id, "generation_id": generation.generation_id,
                "generation_sha256": generation.generation_sha256,
                "subject_id": subject_id, "query_cutoff": query_cutoff}
    authorize(policy, "read_retained_macro_cohort", resource)
    authorize(policy, "verify_retained_macro_retention", resource)
    authorize(policy, "use_retained_house_output_cohort_for_contextual_comparison", resource)
    # Public receipt metadata authenticates object lengths before bulk payload
    # reads. Refuse the whole cohort before loading oversized packet objects.
    declared_bytes = 0
    try:
        for entry in generation.captures:
            original_resource = {**resource, "capture_id": entry.capture_id,
                                 "context_id": entry.context_id, "query_id": entry.query_id,
                                 "requested_subject_id": subject_id}
            # The index does not declare the capture's subject. Permission for
            # the query subject cannot authorize another subject's metadata.
            del original_resource["subject_id"]
            authorize(policy, "read_retained_macro_capture_metadata", original_resource)
            receipt = reader.read_pinned_capture_receipt(generation, query_id=entry.query_id)
            actual_resource = {**original_resource, "subject_id": receipt["subject"]["subject_id"],
                               "source_receipt_ids": list(receipt["source_receipt_ids"]),
                               "packet_sha256": receipt["packet_sha256"]}
            authorize(policy, "read_retained_macro_capture", actual_resource)
            authorize(policy, "verify_retained_macro_retention", actual_resource)
            authorize(policy, "use_retained_house_output_cohort_for_contextual_comparison", actual_resource)
            declared_bytes += (len(canonical(receipt)) + receipt["packet_bytes"]
                               + receipt["feature_snapshot"]["content_bytes"])
            if declared_bytes > MAX_OWNER_BYTES:
                raise RetainedContextCohortError("aggregate_owner_byte_bound_exceeded")
        owners = reader.read_pinned_capture_projections(generation)
    except pit.MarketMemoryPITError as exc:
        raise RetainedContextCohortError("owner_generation_qualification_refused") from exc
    if type(owners) is not tuple or len(owners) != len(generation.captures):
        raise RetainedContextCohortError("complete_generation_denominator_required")
    rows: list[dict] = []
    seen: set[str] = set()
    total_bytes = 0
    for original in owners:
        if type(original) is not trusted.PinnedTrustedCaptureProjection:
            raise RetainedContextCohortError("exact_owner_projection_required")
        receipt, packet, feature = original.receipt, original.stored.packet, original.feature
        total_bytes += len(canonical(receipt)) + len(canonical(packet)) + len(canonical(feature))
        if total_bytes > MAX_OWNER_BYTES:
            raise RetainedContextCohortError("aggregate_owner_byte_bound_exceeded")
        context_id = receipt["context_id"]
        if context_id in seen:
            raise RetainedContextCohortError("duplicate_original_context")
        seen.add(context_id)
        actual_resource = {**resource, "requested_subject_id": subject_id,
                           "subject_id": receipt["subject"]["subject_id"],
                           "capture_id": receipt["capture_id"], "context_id": context_id,
                           "query_id": receipt["query_id"],
                           "source_receipt_ids": list(receipt["source_receipt_ids"]),
                           "packet_sha256": receipt["packet_sha256"]}
        authorize(policy, "read_retained_macro_capture", actual_resource)
        authorize(policy, "verify_retained_macro_retention", actual_resource)
        authorize(policy, "use_retained_house_output_cohort_for_contextual_comparison", actual_resource)
        source_asof = feature.get("source_artifact", {}).get("source_asof")
        try:
            source_session = date.fromisoformat(source_asof) if type(source_asof) is str else None
            if source_session is not None and source_session.isoformat() != source_asof:
                source_session = None
        except ValueError:
            source_session = None
        clocks = {"captured_at": receipt["captured_at"],
                  "raw_source_observed_at": receipt["source_evidence"]["raw_source_observed_at"],
                  "raw_source_built_at": receipt["source_evidence"]["raw_source_built_at"],
                  "feature_as_of": feature["as_of"], **packet["clocks"]}
        future = any(utc_instant(clock) > cutoff for clock in clocks.values())
        if receipt["subject"]["subject_id"] != subject_id:
            status = "other_subject"
        elif future:
            status = "future_capture"
        elif source_session is None:
            status = "unknown_source_session"
        else:
            status = "group_pending"
        rows.append({"context_id": context_id, "capture_id": receipt["capture_id"],
                     "query_id": receipt["query_id"], "subject_id": receipt["subject"]["subject_id"],
                     "packet_sha256": receipt["packet_sha256"],
                     "feature_snapshot": copy.deepcopy(receipt["feature_snapshot"]),
                     "capture_receipt_sha256": sha256(canonical(receipt)).hexdigest(),
                     "source_receipt_ids": list(receipt["source_receipt_ids"]),
                     "source_session": source_asof if source_session else None,
                     "clocks": clocks, "status": status})
    rows.sort(key=lambda row: row["context_id"])
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        if row["status"] == "group_pending":
            groups.setdefault((row["subject_id"], row["source_session"]), []).append(row)
    for group in groups.values():
        ordered = sorted(group, key=lambda row: (utc_instant(row["clocks"]["captured_at"]), row["context_id"]))
        for index, row in enumerate(ordered):
            row["status"] = "representative" if index == 0 else "revision_sibling"
            row["representative_context_id"] = ordered[0]["context_id"]
    projections: list[features.EpisodeFeatureCapability | None] = []
    # Representative selection is already complete; unknown coordinates cannot
    # cause a later revision to replace the original representative.
    for row in rows:
        if row["status"] != "representative":
            projections.append(None)
            continue
        capability = features.read_episode_feature_capability(
            reader, generation, query_id=row["query_id"], subject_id=subject_id,
            query_cutoff=query_cutoff, policy=policy,
        )
        value = features.disclose_episode_features(capability, policy=policy)
        if (value["context_id"] != row["context_id"]
                or value["capture_id"] != row["capture_id"]
                or value["feature_snapshot"] != row["feature_snapshot"]):
            raise RetainedContextCohortError("exact_original_feature_closure_mismatch")
        row["projection_id"] = value["projection_id"]
        if any(item["status"] != "observed" for item in value["coordinates"]):
            row["status"] = "representative_coordinates_unavailable"
        projections.append(capability)
    core = {"schema": SCHEMA, "basis": "retained_observed_house_macro_output",
            "grouping": GROUPING, "owner": resource, "rows": rows,
            "expected_capture_count": len(generation.captures)}
    membership_core = {**core, "rows": [
        {key: item for key, item in row.items() if key != "projection_id"}
        for row in rows
    ]}
    # P1 projection identity carries qualification-time policy provenance.
    # Original source identities define membership, not that usage envelope.
    digest = sha256(canonical(membership_core)).hexdigest()
    value = {**core, "membership_sha256": digest, "cohort_id": "mmretainedcohort_" + digest,
             "counts": dict(sorted(Counter(row["status"] for row in rows).items())),
             "complete_for_exact_generation": True, "scheduled_opportunity_coverage": "unknown",
             "component_source_receipts_authenticated": False,
             "fit_eligible": False, "training_eligible": False, "promotion_eligible": False,
             "rights_provenance": {"policy_id_at_qualification": policy.policy_id,
                                   "current_authorization_must_be_rechecked": True},
             "authority": dict(mm.AUTHORITY)}
    body = canonical(value)
    if len(body) > MAX_MANIFEST_BYTES:
        raise RetainedContextCohortError("cohort_manifest_byte_bound_exceeded")
    capability = RetainedContextCohortCapability(body, canonical(resource), tuple(projections), _key=_TOKEN)
    disclose_retained_context_cohort(capability, policy=policy)
    return capability


def disclose_retained_context_cohort(
    capability: RetainedContextCohortCapability, *, policy: object,
) -> dict:
    value = _verify(capability)
    resource = json.loads(capability._resource)
    authorize(policy, "disclose_retained_macro_cohort", resource)
    authorize(policy, "verify_retained_macro_retention", resource)
    authorize(policy, "use_retained_house_output_cohort_for_contextual_comparison", resource)
    for row in value["rows"]:
        original = {**resource, "requested_subject_id": resource["subject_id"],
                    "subject_id": row["subject_id"], "capture_id": row["capture_id"],
                    "context_id": row["context_id"], "query_id": row["query_id"],
                    "source_receipt_ids": list(row["source_receipt_ids"]),
                    "packet_sha256": row["packet_sha256"]}
        authorize(policy, "disclose_retained_macro_capture", original)
        authorize(policy, "verify_retained_macro_retention", original)
        authorize(policy, "use_retained_house_output_cohort_for_contextual_comparison", original)
    return value


def read_cohort_feature_capabilities(
    capability: RetainedContextCohortCapability, *, policy: object,
) -> tuple[features.EpisodeFeatureCapability | None, ...]:
    """Return original sealed projections aligned with the rights-checked rows."""
    disclose_retained_context_cohort(capability, policy=policy)
    return capability._features
