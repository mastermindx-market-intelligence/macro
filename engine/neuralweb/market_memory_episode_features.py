"""Exact retained house-output coordinates; no fitting or latest-state reads.

The application supplies an authenticated policy, not a user permission flag.
Capabilities are loader-minted, immutable and local to this Python process.
They are not signatures or a security boundary against hostile Python code.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Context, Decimal, DivisionByZero, InvalidOperation, Overflow, ROUND_HALF_EVEN, localcontext
from hashlib import sha256
from typing import Protocol

from engine.neuralweb import market_memory as mm
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_projection as projection
from engine.neuralweb import market_memory_trusted as trusted

SCHEMA = "market_memory.episode_features.v1"
METHOD = "macro_house_state_fixed_range_distance.v1"
MAX_PROJECTION_BYTES = 128 * 1024
_TOKEN = object()
_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")
_QUERY = re.compile(r"mmquery_[a-f0-9]{64}\Z")
_SUBJECT = re.compile(r"mmsecurity_[a-f0-9]{64}\Z")
_GENERATION = re.compile(r"mmgeneration_[a-f0-9]{64}\Z")
_STORE = re.compile(r"mmstore_[a-f0-9]{64}\Z")
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_CATEGORIES = {
    "quad": ("Q1", "Q2", "Q3", "Q4"),
    "liquidity_overlay": ("expanding", "neutral", "contracting"),
    "cycle_tag": ("early", "mid", "late"),
}


class EpisodeFeatureError(ValueError):
    """Invalid projection, capability, policy or temporal input."""


class EpisodeFeatureAccessError(EpisodeFeatureError):
    """The trusted application policy refused this exact resource use."""


class EpisodeFeatureSourceError(EpisodeFeatureError):
    """Original owner closure is unavailable or invalid; never substitute it."""


class EpisodeFeaturePolicy(Protocol):
    """Trusted application boundary after its own caller authentication.

    check returns None on authorization and raises on denial. Literal user
    booleans and returned truthy values are not authorization decisions.
    """

    policy_id: str

    def check(self, action: str, resource: dict[str, str]) -> None: ...


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise EpisodeFeatureError("invalid_json_value") from exc


def _instant(value: object) -> datetime:
    if type(value) is not str or not _UTC.fullmatch(value):
        raise EpisodeFeatureError("exact_utc_instant_required")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00").astimezone(timezone.utc)
    except ValueError as exc:
        raise EpisodeFeatureError("invalid_utc_instant") from exc


def _policy(policy: EpisodeFeaturePolicy, action: str, resource: dict[str, str]) -> str:
    policy_id = getattr(policy, "policy_id", None)
    if (type(policy_id) is not str or not 1 <= len(policy_id) <= 256
            or not callable(getattr(policy, "check", None))):
        raise EpisodeFeatureAccessError("authenticated_application_policy_required")
    try:
        decision = policy.check(action, copy.deepcopy(resource))
    except Exception as exc:
        raise EpisodeFeatureAccessError("source_usage_not_admitted") from exc
    if decision is not None:
        raise EpisodeFeatureAccessError("policy_must_return_no_value_on_authorization")
    return policy_id


def fixed_comparison_descriptor() -> dict:
    """A design-frozen fixed descriptor, not a fitted normalizer or admission."""
    body = {
        "method": METHOD, "mode": "fixed_domain_range", "fit_status": "not_performed",
        "numeric_convention": "owner_binary64_exact_decimal_to_q18_half_even.v1",
        "coordinates": [
            {"id": name, "kind": "numeric", "unit": "dimensionless_house_regime_score",
             "domain": ["-1", "1"], "scale": "2", "weight": "0.2"}
            for name in ("growth_score", "inflation_score")
        ] + [{"id": name, "kind": "categorical", "vocabulary": list(vocabulary),
              "distance": "equal_0_mismatch_1", "weight": "0.2"}
             for name, vocabulary in _CATEGORIES.items()],
        "formula": "(abs(gq-gc)/2+abs(iq-ic)/2+I(quad_diff)+I(liquidity_diff)+I(cycle_diff))/5",
        "all_coordinates_required": True, "missingness": "no_imputation_no_dimension_drop",
        "training_eligible": False, "promotion_eligible": False,
        "usage_admission_granted": False,
    }
    digest = sha256(_canonical(body)).hexdigest()
    return {**body, "descriptor_id": "mmfixedscale_" + digest, "content_sha256": digest}


def fixed_decimal_context() -> Context:
    """Fresh complete context; never inherit or mutate caller Decimal state."""
    return Context(prec=80, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999,
                   capitals=1, clamp=0, flags=[],
                   traps=[InvalidOperation, DivisionByZero, Overflow])


def _numeric(value: object, name: str) -> dict:
    if type(value) is not float and type(value) is not int:
        raise EpisodeFeatureError("numeric_type_not_admitted:" + name)
    try:
        number = float(value)
        exact = Decimal.from_float(number)
        if not exact.is_finite() or not Decimal(-1) <= exact <= Decimal(1):
            raise EpisodeFeatureError("numeric_domain_not_admitted:" + name)
        with localcontext(fixed_decimal_context()):
            quantized = exact.quantize(Decimal("1e-18"), rounding=ROUND_HALF_EVEN)
    except (ValueError, OverflowError) as exc:
        raise EpisodeFeatureError("numeric_domain_not_admitted:" + name) from exc
    return {"id": name, "kind": "numeric", "status": "observed", "reason": None,
            "unit": "dimensionless_house_regime_score", "value_q18": format(quantized, ".18f"),
            "source_binary64_hex": number.hex(), "source_exact_decimal": format(exact, "f")}


@dataclass(frozen=True, slots=True, init=False)
class EpisodeFeatureCapability:
    """Opaque loader-only immutable bytes; disclosure always rechecks policy."""

    _body: bytes
    _digest: str
    _resource: bytes
    _seal: object

    def __init__(self, body: bytes, resource: bytes, *, _key: object = None):
        if _key is not _TOKEN:
            raise EpisodeFeatureError("owner_verified_capability_required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_digest", sha256(body).hexdigest())
        object.__setattr__(self, "_resource", resource)
        object.__setattr__(self, "_seal", _TOKEN)


def read_episode_feature_capability(
    reader: trusted.TrustedFileAsKnownAtReader,
    generation: pit.PinnedGenerationSnapshot,
    *, query_id: str, subject_id: str, query_cutoff: str,
    policy: EpisodeFeaturePolicy,
) -> EpisodeFeatureCapability:
    """Read one exact pinned original projection after application authorization.

    Comparison admission is checked separately and may remain refused while
    an entitled caller retains an original output with typed unknown masks.
    """
    if type(reader) is not trusted.TrustedFileAsKnownAtReader:
        raise EpisodeFeatureError("exact_trusted_owner_reader_required")
    if (type(generation) is not pit.PinnedGenerationSnapshot
            or generation.profile != trusted.TRUSTED_STORE_PROFILE):
        raise EpisodeFeatureError("exact_trusted_owner_generation_required")
    if any(type(value) is not str or not pattern.fullmatch(value) for value, pattern in (
        (generation.generation_id, _GENERATION), (generation.store_id, _STORE),
        (generation.generation_sha256, _DIGEST),
    )):
        raise EpisodeFeatureError("invalid_owner_generation_identity")
    if type(query_id) is not str or not _QUERY.fullmatch(query_id):
        raise EpisodeFeatureError("invalid_query_id")
    if type(subject_id) is not str or not _SUBJECT.fullmatch(subject_id):
        raise EpisodeFeatureError("invalid_subject_id")
    cutoff = _instant(query_cutoff)
    resource = {"store_id": generation.store_id, "generation_id": generation.generation_id,
                "generation_sha256": generation.generation_sha256,
                "query_id": query_id, "subject_id": subject_id, "query_cutoff": query_cutoff}
    policy_id = _policy(policy, "read_retained_macro_feature", resource)
    # Requested subject is not authority over the capture's actual subject.
    # Admit only receipt metadata first, then authenticate actual identities and
    # source rights before the public owner loads any packet/feature payload.
    metadata_resource = {key: value for key, value in resource.items() if key != "subject_id"}
    metadata_resource["requested_subject_id"] = subject_id
    _policy(policy, "read_retained_macro_capture_metadata", metadata_resource)
    try:
        metadata = reader.read_pinned_capture_receipt(generation, query_id=query_id)
    except pit.MarketMemoryPITError as exc:
        raise EpisodeFeatureSourceError("owner_source_qualification_failed") from exc
    if (metadata["query_id"] != query_id or metadata["store_id"] != generation.store_id
            or metadata["profile"] != trusted.TRUSTED_STORE_PROFILE
            or metadata["observed_feature_ids"] != ["macro.regime_state"]):
        raise EpisodeFeatureSourceError("owner_identity_or_allowlist_mismatch")
    resource = {**metadata_resource, "subject_id": metadata["subject"]["subject_id"],
                "capture_id": metadata["capture_id"], "context_id": metadata["context_id"],
                "source_receipt_ids": list(metadata["source_receipt_ids"]),
                "packet_sha256": metadata["packet_sha256"]}
    _policy(policy, "read_retained_macro_feature", resource)
    if resource["subject_id"] != subject_id:
        raise EpisodeFeatureSourceError("owner_identity_or_allowlist_mismatch")
    try:
        values = reader.read_pinned_capture_projections(generation, query_ids=(query_id,))
    except pit.MarketMemoryPITError as exc:
        raise EpisodeFeatureSourceError("owner_source_qualification_failed") from exc
    if type(values) is not tuple or len(values) != 1 or type(values[0]) is not trusted.PinnedTrustedCaptureProjection:
        raise EpisodeFeatureSourceError("owner_projection_shape_invalid")
    owner = values[0]
    receipt, packet = owner.receipt, owner.stored.packet
    if receipt != metadata:
        raise EpisodeFeatureSourceError("owner_receipt_changed_during_projection_read")
    if (receipt["query_id"] != query_id or receipt["store_id"] != generation.store_id
            or receipt["subject"]["subject_id"] != subject_id
            or packet["subject"]["subject_id"] != subject_id
            or receipt["context_id"] != packet["context_id"]
            or receipt["profile"] != trusted.TRUSTED_STORE_PROFILE
            or receipt["observed_feature_ids"] != ["macro.regime_state"]):
        raise EpisodeFeatureSourceError("owner_identity_or_allowlist_mismatch")
    feature = projection.validate_macro_regime_feature_object(owner.feature)
    snapshot = receipt["feature_snapshot"]
    feature_body = _canonical(feature)
    digest = sha256(feature_body).hexdigest()
    if (digest != snapshot["content_sha256"] or snapshot["snapshot_id"] != "mmsnap_" + digest
            or len(feature_body) != snapshot["content_bytes"]
            or feature["transform_version"] != "market_memory.macro_regime_transform.v1"
            or sha256(_canonical(packet)).hexdigest() != receipt["packet_sha256"]):
        raise EpisodeFeatureSourceError("owner_feature_or_packet_digest_mismatch")
    policy_flags = receipt["evidence_policy"]
    if (policy_flags.get("training_eligible") is not False
            or policy_flags.get("promotion_eligible") is not False
            or policy_flags.get("actual_output_only") is not True
            or policy_flags.get("role") != "context_only"):
        raise EpisodeFeatureSourceError("unsupported_source_usage_policy")
    observed = {"captured_at": receipt["captured_at"],
                "raw_source_observed_at": receipt["source_evidence"]["raw_source_observed_at"],
                "raw_source_built_at": receipt["source_evidence"]["raw_source_built_at"],
                "feature_as_of": feature["as_of"], **packet["clocks"]}
    if any(_instant(value) > cutoff for value in observed.values()):
        raise EpisodeFeatureError("feature_not_available_at_query_cutoff")
    coordinates = [_numeric(feature["state"][name], name)
                   for name in ("growth_score", "inflation_score")]
    for name, vocabulary in _CATEGORIES.items():
        value = feature["state"][name]
        if value not in vocabulary and value != "unknown":
            raise EpisodeFeatureError("category_not_admitted:" + name)
        known = value in vocabulary
        coordinates.append({"id": name, "kind": "categorical", "unit": "category",
                            "status": "observed" if known else "unavailable",
                            "reason": None if known else "owner_category_unknown",
                            "value": value if known else None})
    compare_allowed = True
    try:
        _policy(policy, "compare_retained_macro_feature", resource)
    except EpisodeFeatureAccessError:
        compare_allowed = False
    available = all(row["status"] == "observed" for row in coordinates)
    descriptor = fixed_comparison_descriptor()
    value = {"schema": SCHEMA, "basis": "retained_observed_house_macro_output",
             "owner": {"profile": generation.profile, **resource},
             "context_id": receipt["context_id"], "capture_id": receipt["capture_id"],
             "capture_receipt_sha256": sha256(_canonical(receipt)).hexdigest(),
             "source_receipt_ids": list(receipt["source_receipt_ids"]),
             "packet_sha256": receipt["packet_sha256"], "feature_snapshot": copy.deepcopy(snapshot),
             "source_feature_id": "macro.regime_state", "source_transform_version": feature["transform_version"],
             "descriptor_ref": {"descriptor_id": descriptor["descriptor_id"], "content_sha256": descriptor["content_sha256"]},
             "clocks": observed, "precision": "house_observed_instants_not_externally_authenticated",
             "measurement_period": {"value": feature["source_artifact"]["source_asof"],
                                    "precision": "date", "meaning": "house_source_session_label"},
             "coordinates": coordinates,
             "source_usage_admission": {"policy_id": policy_id, "capture_available": True,
                                        "comparison_eligible_at_projection": compare_allowed and available,
                                        "comparison_reason_at_projection": ("source_usage_not_admitted" if not compare_allowed
                                                              else "all_fixed_coordinates_observed" if available
                                                              else "registered_coordinates_unavailable"),
                                        "fit_eligible": False, "training_eligible": False, "promotion_eligible": False},
             "component_source_receipts_authenticated": False, "authority": dict(mm.AUTHORITY)}
    body = _canonical(value)
    if len(body) > MAX_PROJECTION_BYTES:
        raise EpisodeFeatureError("projection_byte_bound_exceeded")
    value["projection_id"] = "mmepisodefeatures_" + sha256(body).hexdigest()
    body = _canonical(value)
    if len(body) > MAX_PROJECTION_BYTES:
        raise EpisodeFeatureError("projection_byte_bound_exceeded")
    return EpisodeFeatureCapability(body, _canonical(resource), _key=_TOKEN)


def disclose_episode_features(
    capability: EpisodeFeatureCapability, *, policy: EpisodeFeaturePolicy,
    for_comparison: bool = False,
) -> dict:
    """Return a detached value only after checking current disclosure rights."""
    if (type(capability) is not EpisodeFeatureCapability or capability._seal is not _TOKEN
            or type(capability._body) is not bytes or len(capability._body) > MAX_PROJECTION_BYTES
            or sha256(capability._body).hexdigest() != capability._digest):
        raise EpisodeFeatureError("owner_verified_capability_required")
    if type(for_comparison) is not bool or type(capability._resource) is not bytes:
        raise EpisodeFeatureError("invalid_disclosure_request")
    resource = json.loads(capability._resource)
    value = json.loads(capability._body)
    if resource != {key: value["owner"][key] for key in resource}:
        raise EpisodeFeatureError("capability_resource_binding_mismatch")
    policy_id = _policy(policy, "disclose_retained_macro_feature", resource)
    comparison_authorized = True
    try:
        _policy(policy, "compare_retained_macro_feature", resource)
    except EpisodeFeatureAccessError:
        comparison_authorized = False
    admission = value["source_usage_admission"]
    current_eligible = comparison_authorized and admission["comparison_eligible_at_projection"]
    # This live decision is an envelope, excluded from stable projection_id.
    # Historical usage provenance remains unchanged in the sealed core.
    value["current_usage"] = {
        "policy_id": policy_id, "comparison_authorized": comparison_authorized,
        "comparison_eligible": current_eligible,
        "reason": ("source_usage_not_admitted" if not comparison_authorized
                   else admission["comparison_reason_at_projection"]),
        "included_in_projection_identity": False,
    }
    if for_comparison and not current_eligible:
        raise EpisodeFeatureAccessError("source_usage_not_admitted")
    return value


def require_fit_admission(capability: EpisodeFeatureCapability, *, policy: EpisodeFeaturePolicy) -> None:
    """The explicit fit boundary remains closed; fixed scaling is not fitting."""
    value = disclose_episode_features(capability, policy=policy)
    if value["source_usage_admission"]["fit_eligible"] is not True:
        raise EpisodeFeatureAccessError("source_usage_not_admitted")
    raise EpisodeFeatureAccessError("fit_implementation_not_admitted")
