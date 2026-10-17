"""Saved-output disclosure of one exact retained original macro capture.

This wrapper owns no users, tokens, rights database, capture lifecycle or
store writer.  It serves the already-persisted original output of one exact
trusted capture -- the unchanged packet and capture receipt, plus an explicit
projection of five original feature values -- through the installed registration and
the existing trusted owner readers.  The root wires the API/UI; this module
performs no route, template, or front-end work and writes nothing.

Order of authority on every call: the real server user and the installed
``source_use`` registration are resolved before any trusted reader or private
owner byte is touched; exact typed identities and the canonical UTC cutoff are
validated before the reader exists; all owner I/O (head identity, full pin
ancestry, receipt, projection, including failed reads) is charged to one
bounded owner-read scope.  There is no latest/nearest fallback, no
recomputation from the current regime, no snapshot guess, and no state
reconstruction from packet context features: a missing exact capture is a
typed not-found, and the returned evidence mode ``retained_actual_output`` is
explicitly separate from the named authorization-scope policy mode.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_retained_context_cohort as cohort
from engine.neuralweb import market_memory_retained_use as use
from engine.neuralweb import market_memory_trusted as trusted

SCHEMA = "market_memory.retained_saved_output.v1"
MODE = "retained_actual_output"
STATUS = "AVAILABLE"
# Default refusal bound for one canonical envelope.  Oversize is an error, never
# a truncation.
MAX_ENVELOPE_BYTES = 2 * 1024 * 1024
# The cheap HEAD identity observation admits at most this many captures before
# the full requested-generation pin is attempted.
_MAX_HEAD_OBSERVATION_CAPTURES = 256
_SEAL_PREFIX = b"market_memory.retained_saved_output.v1\x00"
_TOKEN = object()
_TYPED_IDS = {
    "generation_id": r"mmgeneration_[a-f0-9]{64}",
    "query_id": r"mmquery_[a-f0-9]{64}",
    "context_id": r"mmctx_[a-f0-9]{64}",
    "capture_id": r"mmcapture_[a-f0-9]{64}",
    "subject_id": r"mmsecurity_[a-f0-9]{64}",
}
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")


class RetainedSavedOutputError(pit.MarketMemoryPITError):
    """A saved-output capability or envelope boundary was not authentic."""


class RetainedSavedAccessError(RetainedSavedOutputError, PermissionError):
    """Current rights do not admit this saved-output use."""


class RetainedSavedCutoffUnsupported(pit.MarketMemoryQueryError):
    """The exact original was not available by the requested clock."""


def _typed_id(value: object, field: str) -> str:
    if type(value) is not str or not re.fullmatch(_TYPED_IDS[field], value):
        raise pit.MarketMemoryQueryError(f"{field} must be an exact typed identifier")
    return value


def _sha256_id(value: object, field: str) -> str:
    if type(value) is not str or not _SHA256.fullmatch(value):
        raise pit.MarketMemoryQueryError(f"{field} must be a lowercase SHA-256")
    return value


def _seal(request: bytes, owner: bytes, resources: tuple, originals: tuple,
          grant: use.RetainedHouseUsePolicy) -> str:
    bound = cohort.canonical({"resources": resources, "originals": originals,
        "grant": {"root": str(grant.root), "user_id": grant.user_id,
                  "registration_sha256": grant.registration_sha256,
                  "expected": grant.expected, "mode": grant.mode}})
    return sha256(_SEAL_PREFIX + request + b"\x00" + owner + b"\x00" + bound).hexdigest()


def _cutoff_instant(value: object) -> object:
    try:
        return cohort.utc_instant(value)
    except cohort.RetainedContextCohortError as exc:
        raise pit.MarketMemoryQueryError("query_cutoff must be canonical UTC") from exc


@dataclass(frozen=True)
class SavedOutputCapability:
    """Request-local sealed authority for one exact saved capture.

    The capability binds the canonical request identity, the canonical owner
    generation identity, the exact authenticated capture resource, the held
    house-use policy, and the pinned reader.  Every field participates in the
    seal, so a constructed or mutated body cannot pass as authority.
    """

    request: bytes
    owner: bytes
    resources: tuple
    seal: str
    grant: use.RetainedHouseUsePolicy
    reader: trusted.TrustedFileAsKnownAtReader
    originals: tuple
    _token: object = None

    def __post_init__(self):
        if (self._token is not _TOKEN or type(self.request) is not bytes or not self.request
                or type(self.owner) is not bytes or not self.owner
                or type(self.resources) is not tuple or len(self.resources) != 1
                or type(self.resources[0]) is not dict
                or type(self.originals) is not tuple or len(self.originals) != 3
                or type(self.seal) is not str
                or type(self.grant) is not use.RetainedHouseUsePolicy
                or type(self.reader) is not trusted.TrustedFileAsKnownAtReader
                or self.seal != _seal(self.request, self.owner, self.resources, self.originals, self.grant)):
            raise RetainedSavedOutputError("retained_saved_capability_required")


def _authorization_mode(registration: dict) -> str:
    # The named current-support policy mode is reused only as the existing
    # authorization scope; the returned saved evidence mode stays separate.
    mode = "current_contextual_support"
    if mode not in registration["modes"]:
        raise use.RetainedUseError("registered_saved_scope_mode_required")
    return mode


def _require_single_registered_subject(registration: dict, subject_id: str) -> None:
    if len(registration["allowed_subject_ids"]) != 1:
        raise use.RetainedUseError("single_registered_saved_subject_required")
    if subject_id != registration["allowed_subject_ids"][0]:
        raise use.RetainedUseError("actual_or_requested_subject_not_admitted")


def _recheck_original(original: trusted.PinnedTrustedCaptureProjection, receipt: dict,
                      *, capture_id: str, context_id: str, subject_id: str) -> dict:
    """Recheck the actual receipt, packet, feature, identities, and byte lengths."""
    packet, feature = original.stored.packet, original.feature
    if original.receipt != receipt:
        raise pit.MarketMemoryStoreError("saved projection receipt differs from its pinned receipt")
    if (packet["context_id"] != context_id or receipt["context_id"] != context_id
            or receipt["capture_id"] != capture_id or receipt["query_id"] != _typed_id(
                receipt["query_id"], "query_id")):
        raise pit.MarketMemoryStoreError("saved capture identity differs from the request")
    if (packet["subject"] != receipt["subject"] or packet["clocks"] != receipt["clocks"]
            or packet["subject"]["subject_id"] != subject_id):
        raise pit.MarketMemoryStoreError("saved packet query differs from its capture")
    packet_body = cohort.canonical(packet)
    if (sha256(packet_body).hexdigest() != receipt["packet_sha256"]
            or len(packet_body) != receipt["packet_bytes"]):
        raise pit.MarketMemoryStoreError("saved packet bytes differ from the owner receipt")
    feature_body = cohort.canonical(feature)
    snapshot = receipt["feature_snapshot"]
    if (sha256(feature_body).hexdigest() != snapshot["content_sha256"]
            or len(feature_body) != snapshot["content_bytes"]
            or feature["as_of"] != snapshot["as_of"]):
        raise pit.MarketMemoryStoreError("saved feature bytes differ from the owner receipt")
    evidence = receipt["source_evidence"]
    source_artifact = feature["source_artifact"]
    if (source_artifact["raw_sha256"] != evidence["raw_source_sha256"]
            or source_artifact["raw_bytes"] != evidence["raw_source_bytes"]
            or source_artifact["built_at"] != evidence["raw_source_built_at"]):
        raise pit.MarketMemoryStoreError("saved source evidence differs from its receipt")
    state = feature["state"]
    if any(name not in state for name in use.FIELDS):
        raise pit.MarketMemoryStoreError("saved feature state is not the five-field house output")
    return {"packet": packet, "feature": feature}


def _saved_clocks(receipt: dict, packet: dict, feature: dict) -> dict:
    clocks = {"captured_at": receipt["captured_at"],
              "raw_source_built_at": receipt["source_evidence"]["raw_source_built_at"],
              "raw_source_observed_at": receipt["source_evidence"]["raw_source_observed_at"],
              "feature_as_of": feature["as_of"]}
    clocks.update(copy.deepcopy(packet["clocks"]))
    return clocks


def _envelope(*, policy: use.RetainedHouseUsePolicy, generation: dict, receipt: dict,
              packet: dict, feature: dict, selection: dict) -> dict:
    from engine.neuralweb import market_memory_operating_cortex_service as evidence
    clocks = _saved_clocks(receipt, packet, feature)
    earliest = max(clocks.values(), key=cohort.utc_instant)
    try:
        facts = evidence._source_facts(feature, receipt)
    except evidence.RealEvidenceError as exc:
        raise RetainedSavedOutputError("original_saved_source_quotes_unavailable") from exc
    value = {
        "schema": SCHEMA,
        "mode": MODE,
        "status": STATUS,
        "generation": generation,
        "selection": selection,
        "context": copy.deepcopy(packet),
        "capture_receipt": copy.deepcopy(receipt),
        "feature_projection": {
            "schema": "market_memory.saved_house_feature_projection.v1",
            "as_of": feature["as_of"],
            "transform_version": feature["transform_version"],
            "source_artifact": copy.deepcopy(feature["source_artifact"]),
            "state": {name: copy.deepcopy(feature["state"][name]) for name in use.FIELDS},
            "original_feature_ref": copy.deepcopy(receipt["feature_snapshot"]),
        },
        "source_facts": facts,
        "exact_refs": {
            "packet": {"sha256": receipt["packet_sha256"], "bytes": receipt["packet_bytes"]},
            "feature": {"snapshot_id": receipt["feature_snapshot"]["snapshot_id"],
                        "sha256": receipt["feature_snapshot"]["content_sha256"],
                        "bytes": receipt["feature_snapshot"]["content_bytes"]},
            "source": {"raw_sha256": receipt["source_evidence"]["raw_source_sha256"],
                       "raw_bytes": receipt["source_evidence"]["raw_source_bytes"]},
        },
        "source_use": policy.disclosure(),
        "clocks": clocks,
        "earliest_supported_cutoff": earliest,
        "outcomes": {"status": "NOT_ATTACHED"},
        "evidence_policy": copy.deepcopy(receipt["evidence_policy"]),
    }
    if len(cohort.canonical(value)) > MAX_ENVELOPE_BYTES:
        raise pit.MarketMemoryStoreError("retained saved output exceeds its envelope bound")
    return value


def read_retained_saved(root: Path, *, user_id: str, generation_id: str,
                        generation_sha256: str, query_id: str, context_id: str,
                        capture_id: str, subject_id: str, query_cutoff: str
                        ) -> SavedOutputCapability:
    """Bind one exact retained capture into a sealed request-local capability."""
    _typed_id(generation_id, "generation_id")
    _sha256_id(generation_sha256, "generation_sha256")
    _typed_id(query_id, "query_id")
    _typed_id(context_id, "context_id")
    _typed_id(capture_id, "capture_id")
    _typed_id(subject_id, "subject_id")
    cutoff_instant = _cutoff_instant(query_cutoff)
    if type(user_id) is not str or not 1 <= len(user_id) <= 256:
        raise use.RetainedUseError("server_authenticated_user_required")
    root = Path(root)
    # The real server user and the installed registration precede every owner byte.
    use._enforce_current_site_user(user_id)
    registration, _digest = use.load_registration(root)
    _require_single_registered_subject(registration, subject_id)
    with pit.bounded_owner_reads(maximum_bytes=cohort.MAX_OWNER_BYTES):
        reader = trusted.TrustedFileAsKnownAtReader(trusted.default_trusted_store_root(root))
        head = reader.observe_generation_head(maximum_capture_count=_MAX_HEAD_OBSERVATION_CAPTURES)
        if head.store_id != registration["store_id"]:
            raise pit.MarketMemoryStoreError("registered_saved_store_required")
        pin = reader.read_pinned_generation(generation_id=generation_id,
                                            maximum_capture_count=cohort.MAX_CAPTURES)
        if (pin.store_id != registration["store_id"]
                or pin.generation_id != generation_id
                or pin.generation_sha256 != generation_sha256):
            raise pit.MarketMemoryContextNotFound(
                "exact saved generation is not published by the active ancestry")
        entries = [entry for entry in pin.captures if entry.query_id == query_id]
        if not entries:
            raise pit.MarketMemoryContextNotFound(
                "exact capture query is absent from the pinned saved generation")
        if len(entries) != 1:  # pragma: no cover - the pin validator proves this
            raise pit.MarketMemoryStoreError("pinned saved query index is ambiguous")
        entry = entries[0]
        if entry.context_id != context_id or entry.capture_id != capture_id:
            raise pit.MarketMemoryContextNotFound(
                "exact capture identity does not match the pinned saved generation")
        policy = use.RetainedHouseUsePolicy(root, user_id=user_id, store_id=pin.store_id,
            generation_id=pin.generation_id, generation_sha256=pin.generation_sha256,
            subject_id=subject_id, query_cutoff=query_cutoff,
            mode=_authorization_mode(registration))
        metadata = {**policy.expected, "capture_id": entry.capture_id,
                    "context_id": entry.context_id, "query_id": entry.query_id,
                    "requested_subject_id": subject_id}
        # Exact-capture metadata rights precede any private receipt read.
        policy.check("read_retained_macro_capture_metadata", metadata)
        receipt = reader.read_pinned_capture_receipt(pin, query_id=query_id)
        if (receipt["capture_id"] != capture_id or receipt["context_id"] != context_id
                or receipt["query_id"] != query_id):
            raise pit.MarketMemoryStoreError(
                "pinned saved receipt differs from the requested capture")
        actual_subject = receipt["subject"]["subject_id"]
        if actual_subject != subject_id:
            raise use.RetainedUseError("actual_or_requested_subject_not_admitted")
        resource = {**metadata, "subject_id": actual_subject,
                    "source_receipt_ids": list(receipt["source_receipt_ids"]),
                    "packet_sha256": receipt["packet_sha256"],
                    "feature_sha256": receipt["feature_snapshot"]["content_sha256"]}
        policy.check("read_retained_macro_capture", resource)
        policy.check("read_retained_macro_feature", resource)
        policy.check("verify_retained_macro_retention", resource)
        # One projection for the exact query, never the whole generation payload.
        projections = reader.read_pinned_capture_projections(pin, query_ids=(query_id,))
        if len(projections) != 1:
            raise pit.MarketMemoryStoreError("exact saved projection is not unique")
        checked = _recheck_original(projections[0], receipt, capture_id=capture_id,
                                    context_id=context_id, subject_id=subject_id)
        clocks = _saved_clocks(receipt, checked["packet"], checked["feature"])
        earliest = max(clocks.values(), key=cohort.utc_instant)
        if cohort.utc_instant(earliest) > cutoff_instant:
            raise RetainedSavedCutoffUnsupported(
                "query_cutoff precedes the retained actual clocks")
        generation = {"store_id": pin.store_id, "generation_id": pin.generation_id,
                      "generation_sha256": pin.generation_sha256,
                      "profile": trusted.TRUSTED_STORE_PROFILE}
        selection = {"query_id": query_id, "context_id": context_id,
                     "capture_id": capture_id, "subject_id": subject_id,
                     "instrument_id": checked["packet"]["subject"]["instrument_id"],
                     "query_cutoff": query_cutoff}
        # Final checks on the held capability before it is sealed.
        policy.check("disclose_retained_macro_capture", resource)
        policy.check("disclose_retained_macro_feature", resource)
        policy.check("use_retained_house_output_for_evidence_synthesis", resource)
        request = cohort.canonical({key: selection[key] for key in
                                    ("query_id", "context_id", "capture_id", "subject_id",
                                     "query_cutoff")})
        owner = cohort.canonical(generation)
        resources = (copy.deepcopy(resource),)
        originals = (copy.deepcopy(receipt), copy.deepcopy(checked["packet"]),
                     copy.deepcopy(checked["feature"]))
        return SavedOutputCapability(
            request=request, owner=owner, resources=resources,
            seal=_seal(request, owner, resources, originals, policy), grant=policy, reader=reader,
            originals=originals, _token=_TOKEN)


def disclose_retained_saved(capability: SavedOutputCapability) -> dict:
    """Return the detached saved-output envelope after final current checks."""
    if type(capability) is not SavedOutputCapability:
        raise RetainedSavedOutputError("retained_saved_capability_required")
    capability.__post_init__()
    grant = capability.grant
    held_packet, held_feature = capability.originals[1], capability.originals[2]
    try:
        request_identity = json.loads(capability.request.decode("utf-8"))
        generation = json.loads(capability.owner.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RetainedSavedOutputError("retained_saved_capability_required") from exc
    query_id = _typed_id(request_identity.get("query_id"), "query_id")
    context_id = _typed_id(request_identity.get("context_id"), "context_id")
    capture_id = _typed_id(request_identity.get("capture_id"), "capture_id")
    subject_id = _typed_id(request_identity.get("subject_id"), "subject_id")
    query_cutoff = request_identity.get("query_cutoff")
    _cutoff_instant(query_cutoff)
    _typed_id(generation.get("generation_id"), "generation_id")
    _sha256_id(generation.get("generation_sha256"), "generation_sha256")
    sealed = capability.resources[0]
    with pit.bounded_owner_reads(maximum_bytes=cohort.MAX_OWNER_BYTES):
        # Final current entitlement, registration, and revocation checks precede
        # any re-read of owner bytes, using the sealed capture resource.
        grant.check("disclose_retained_macro_capture", sealed)
        fresh = trusted.TrustedFileAsKnownAtReader(
            trusted.default_trusted_store_root(grant.root))
        pin = fresh.read_pinned_generation(generation_id=generation["generation_id"],
                                           maximum_capture_count=cohort.MAX_CAPTURES)
        if (pin.store_id != generation["store_id"]
                or pin.generation_sha256 != generation["generation_sha256"]):
            raise pit.MarketMemoryStoreError("retained saved generation is no longer published")
        entries = [entry for entry in pin.captures if entry.query_id == query_id]
        if len(entries) != 1:
            raise pit.MarketMemoryStoreError("retained saved capture left its pinned generation")
        receipt = fresh.read_pinned_capture_receipt(pin, query_id=query_id)
        if (receipt != capability.originals[0] or receipt["capture_id"] != capture_id
                or receipt["context_id"] != context_id
                or receipt["subject"]["subject_id"] != subject_id):
            raise pit.MarketMemoryStoreError(
                "retained saved capture no longer matches the sealed capability")
        resource = {**grant.expected, "capture_id": capture_id, "context_id": context_id,
                    "query_id": query_id, "requested_subject_id": subject_id,
                    "subject_id": subject_id,
                    "source_receipt_ids": list(receipt["source_receipt_ids"]),
                    "packet_sha256": receipt["packet_sha256"],
                    "feature_sha256": receipt["feature_snapshot"]["content_sha256"]}
        if resource != capability.resources[0]:
            raise RetainedSavedAccessError("retained_saved_capability_resource_changed")
        grant.check("disclose_retained_macro_feature", resource)
        grant.check("verify_retained_macro_retention", resource)
        grant.check("use_retained_house_output_for_evidence_synthesis", resource)
        projections = fresh.read_pinned_capture_projections(pin, query_ids=(query_id,))
        if len(projections) != 1:
            raise pit.MarketMemoryStoreError("exact saved projection is not unique")
        checked = _recheck_original(projections[0], receipt, capture_id=capture_id,
                                    context_id=context_id, subject_id=subject_id)
        if (checked["packet"] != held_packet or checked["feature"] != held_feature):
            raise pit.MarketMemoryStoreError(
                "retained saved original output differs from the sealed capability")
        cutoff_instant = _cutoff_instant(query_cutoff)
        clocks = _saved_clocks(receipt, checked["packet"], checked["feature"])
        if cohort.utc_instant(max(clocks.values(), key=cohort.utc_instant)) > cutoff_instant:
            raise RetainedSavedCutoffUnsupported(
                "query_cutoff precedes the retained actual clocks")
        selection = {"query_id": query_id, "context_id": context_id,
                     "capture_id": capture_id, "subject_id": subject_id,
                     "instrument_id": checked["packet"]["subject"]["instrument_id"],
                     "query_cutoff": query_cutoff}
        value = _envelope(policy=grant, generation=generation, receipt=receipt,
                         packet=checked["packet"], feature=checked["feature"],
                         selection=selection)
        # Owner I/O and envelope construction cannot reuse a now-revoked grant.
        for action in ("disclose_retained_macro_capture", "disclose_retained_macro_feature",
                       "verify_retained_macro_retention", "use_retained_house_output_for_evidence_synthesis"):
            grant.check(action, resource)
        return value


__all__ = [
    "MAX_ENVELOPE_BYTES",
    "MODE",
    "SCHEMA",
    "STATUS",
    "RetainedSavedAccessError",
    "RetainedSavedOutputError",
    "SavedOutputCapability",
    "disclose_retained_saved",
    "read_retained_saved",
]
