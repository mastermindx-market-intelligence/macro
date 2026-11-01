"""SOURCE-ONLY whole-stamp PTSE publication preflight; no owner admission.

All operations are pure in-memory transformations. A caller supplies the complete
candidate grain, an already validated and pinned B1 snapshot, and independently
obtained receipt-manifest SHA256. Receipt owners/ids/digests are external inputs,
not authenticity claims this module can establish. The manifest pin must come
from the caller's trusted custody boundary, never from the packet under test.
Snapshot dataclass type checks likewise do not authenticate its provenance.

The first complete packet is immutable canonical bytes. Comparisons validate
both packets by rebuilding all rows from actual retained context bytes and the
independently supplied source reconstruction bundles. Changed inputs become
explicit lineage candidates; there is no store, retry clock, legacy W3 flag,
or write authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re
from typing import Any

from engine.us_candidate_episode import (
    CandidateEpisodeStoreSnapshot, ValidatedCandidateEpisodeGeneration,
)
from research.options_estate.ptse_candidate_relation import (
    PTSECandidateRelationError, candidate_source_event_id,
    resolve_candidate_episode_relation,
)
from research.options_estate.ptse_contract import ContextArtifact, validate_context
from research.options_estate.ptse_shadow_enrollment import (
    AUTHORITY, build_shadow_enrollment, validate_shadow_enrollment,
)

SCHEMA = "ptse.w3_complete_stamp/v1-research"
RECEIPT_SCHEMA = "ptse.w3_external_receipt_manifest/v1-research"
_RELATION_REFUSALS = {
    "CANDIDATE_B1_RELATION_UNAVAILABLE", "CANDIDATE_B1_RELATION_AMBIGUOUS",
}


class PTSEPublicationError(ValueError):
    """A typed refusal; no packet has been admitted or published."""
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _fail(code: str) -> None:
    raise PTSEPublicationError(code)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise PTSEPublicationError("MATERIAL_NOT_CANONICAL") from exc


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _clone(value: Any) -> Any:
    return json.loads(_canonical(value))


def _closed(value: Any, fields: set[str], code: str) -> Mapping:
    if not isinstance(value, Mapping) or set(value) != fields:
        _fail(code)
    return value


def _text(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        _fail(code)
    return value


def _sha(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        _fail("SHA256_INVALID")
    return value


def _stamp(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        _fail("STAMP_DATE_INVALID")
    try:
        if date.fromisoformat(value).isoformat() != value:
            _fail("STAMP_DATE_INVALID")
    except ValueError as exc:
        raise PTSEPublicationError("STAMP_DATE_INVALID") from exc
    return value


def _authority(value: Any) -> None:
    _closed(value, set(AUTHORITY), "AUTHORITY_FIELDS_NOT_CLOSED")
    if any(value[k] is not False for k in AUTHORITY):
        _fail("AUTHORITY_FORBIDDEN")


def _ref(value: Any) -> None:
    _closed(value, {"owner_ref", "artifact_id", "sha256"}, "RECEIPT_REF_INVALID")
    _text(value["owner_ref"], "RECEIPT_OWNER_REQUIRED")
    _text(value["artifact_id"], "RECEIPT_ID_REQUIRED")
    _sha(value["sha256"])


def b1_material_bytes(snapshot: CandidateEpisodeStoreSnapshot) -> bytes:
    """Exact path-independent material; requires previously validated B1 custody."""
    if type(snapshot) is not CandidateEpisodeStoreSnapshot or type(snapshot.generation) is not ValidatedCandidateEpisodeGeneration:
        _fail("PINNED_VALIDATED_B1_SNAPSHOT_REQUIRED")
    if not isinstance(snapshot.generation_id, str) or not re.fullmatch(r"peg:[0-9a-f]{64}", snapshot.generation_id):
        _fail("B1_GENERATION_ID_INVALID")
    g = snapshot.generation
    if any(type(v) is not tuple for v in (g.events, g.suppressions, g.episodes)) or not isinstance(g.receipt, Mapping):
        _fail("B1_VALIDATED_MATERIAL_REQUIRED")
    # Validate metadata across the complete B1 material before considering the
    # caller cohort. An empty population must not mask corrupt source metadata.
    for episode in g.episodes:
        if not isinstance(episode, Mapping):
            _fail("B1_SOURCE_METADATA_INVALID")
        for field in ("episode_id", "security_id", "company_id", "identity_epoch"):
            _text(episode.get(field), "B1_SOURCE_METADATA_INVALID")
        source_ids = episode.get("source_event_ids")
        if isinstance(source_ids, (str, bytes)) or not isinstance(source_ids, Sequence):
            _fail("B1_SOURCE_METADATA_INVALID")
        for source_id in source_ids:
            _text(source_id, "B1_SOURCE_METADATA_INVALID")
    return _canonical({"generation_id": snapshot.generation_id,
                       "events": g.events, "suppressions": g.suppressions,
                       "episodes": g.episodes, "receipt": g.receipt})


def _candidates(stamp: str, rows: Sequence, generation_id: str) -> tuple[list[dict], list[dict]]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        _fail("COMPLETE_CANDIDATE_POPULATION_REQUIRED")
    found = {}
    for raw in rows:
        if not isinstance(raw, Mapping) or not {"stamp_date", "ticker", "board_definition"} <= set(raw):
            _fail("CANDIDATE_GRAIN_FIELDS_REQUIRED")
        if _stamp(raw["stamp_date"]) != stamp:
            _fail("MIXED_CANDIDATE_STAMP")
        if "candidate_generation_id" in raw and raw["candidate_generation_id"] != generation_id:
            _fail("MIXED_CANDIDATE_GENERATION")
        for key in ("ticker", "board_definition"):
            _text(raw[key], "CANDIDATE_IDENTITY_REQUIRED")
            if ":" in raw[key]:
                _fail("CANDIDATE_IDENTITY_DELIMITER_FORBIDDEN")
        key = candidate_source_event_id(raw)
        if key in found:
            _fail("DUPLICATE_CANDIDATE_KEY")
        found[key] = _clone(raw)
    source_rows = [found[k] for k in sorted(found)]
    selected = [{k: r[k] for k in ("stamp_date", "ticker", "board_definition")}
                for r in source_rows]
    return selected, source_rows


def _context(raw: Any) -> ContextArtifact:
    if isinstance(raw, ContextArtifact):
        raw = raw.canonical_bytes
    if not isinstance(raw, (bytes, str)):
        _fail("CONTEXT_BYTES_REQUIRED")
    try:
        artifact = validate_context(raw)
    except ValueError as exc:
        raise PTSEPublicationError("CONTEXT_INVALID") from exc
    original = raw.encode("utf-8") if isinstance(raw, str) else raw
    if original != artifact.canonical_bytes:
        _fail("CONTEXT_BYTES_NOT_CANONICAL")
    _authority(artifact.to_dict()["assessment"]["authority"])
    return artifact


@dataclass(frozen=True)
class PublicationBundle:
    packet: bytes
    context_artifacts: tuple[tuple[str, bytes], ...]


def build_publication_packet(*, stamp_date: str, candidate_rows: Sequence,
                             b1_snapshot: CandidateEpisodeStoreSnapshot,
                             receipt_manifest: Mapping,
                             receipt_manifest_sha256: str,
                             contexts: Mapping[str, ContextArtifact | bytes | str]) -> PublicationBundle:
    """Compile one row per caller candidate, including unavailable/refusal rows.

    Candidates retain the incumbent source schema at the input boundary. Only
    stamp/ticker/board grain is selected into enrollment; the exact full sorted
    source population is bound by its external receipt digest without copying
    ranks, scores, or policy into this packet.
    Source-manifest/receipt consistency is checked against an independent digest
    pin; this cannot prove that the external owner issued the receipt.
    """
    stamp = _stamp(stamp_date)
    b1_bytes = b1_material_bytes(b1_snapshot)
    rows, source_rows = _candidates(stamp, candidate_rows, b1_snapshot.generation_id)
    keys = [candidate_source_event_id(r) for r in rows]
    if not isinstance(contexts, Mapping) or set(contexts) - set(keys):
        _fail("EXTRA_OR_INVALID_CONTEXT_KEYS")
    manifest = _clone(receipt_manifest)
    _closed(manifest, {"schema", "stamp_date", "candidate_generation_id",
                       "candidate_population_receipt", "b1_material_receipt",
                       "context_receipts"}, "MANIFEST_FIELDS_NOT_CLOSED")
    if _digest(_canonical(manifest)) != _sha(receipt_manifest_sha256):
        _fail("EXTERNAL_MANIFEST_PIN_MISMATCH")
    if manifest["schema"] != RECEIPT_SCHEMA or manifest["stamp_date"] != stamp:
        _fail("MANIFEST_SCHEMA_OR_STAMP_MISMATCH")
    if manifest["candidate_generation_id"] != b1_snapshot.generation_id:
        _fail("MANIFEST_GENERATION_MISMATCH")
    for field in ("candidate_population_receipt", "b1_material_receipt"):
        _ref(manifest[field])
    candidate_bytes = _canonical(source_rows)
    if manifest["candidate_population_receipt"]["sha256"] != _digest(candidate_bytes):
        _fail("CANDIDATE_MATERIAL_RECEIPT_MISMATCH")
    if manifest["b1_material_receipt"]["sha256"] != _digest(b1_bytes):
        _fail("B1_MATERIAL_RECEIPT_MISMATCH")
    receipts = manifest["context_receipts"]
    if not isinstance(receipts, Mapping) or set(receipts) != set(contexts):
        _fail("CONTEXT_RECEIPT_KEYS_MISMATCH")
    artifacts = {}
    validated = {}
    for key in sorted(contexts):
        art = _context(contexts[key])
        payload = art.to_dict()
        o, a = payload["observation"], payload["assessment"]
        if o["market_session"] != stamp:
            _fail("CONTEXT_STAMP_MISMATCH")
        if a["candidate_generation_id"] != b1_snapshot.generation_id:
            _fail("CONTEXT_GENERATION_MISMATCH")
        if a["action"] != "NEW_ENTRY" or o["evidence_grade"] != "PROSPECTIVE_FIRST_SEEN":
            _fail("CONTEXT_NOT_ADMITTED")
        receipt = receipts[key]
        _closed(receipt, {"artifact_ref", "observation_id", "assessment_id",
                          "source_manifest_ref", "calculation_receipt_ref"},
                "CONTEXT_RECEIPT_FIELDS_NOT_CLOSED")
        for field in ("artifact_ref", "source_manifest_ref", "calculation_receipt_ref"):
            _ref(receipt[field])
        if (receipt["artifact_ref"]["sha256"] != art.sha256 or
            receipt["observation_id"] != art.observation_id or
            receipt["assessment_id"] != art.assessment_id or
            receipt["source_manifest_ref"] != o["source_manifest_ref"] or
            receipt["calculation_receipt_ref"] != o["calculation_receipt_ref"]):
            _fail("CONTEXT_RECEIPT_IDENTITY_MISMATCH")
        artifacts[art.sha256] = art.canonical_bytes.decode("utf-8")
        validated[key] = art
    packet_rows = []
    for candidate in rows:
        key = candidate_source_event_id(candidate)
        art = validated.get(key)
        try:
            # Only the two relation refusals are recoverable denominator rows.
            # All malformed source metadata/context identity failures abort.
            resolve_candidate_episode_relation(candidate, b1_snapshot)
        except PTSECandidateRelationError as exc:
            if exc.code not in _RELATION_REFUSALS:
                raise PTSEPublicationError("B1_SOURCE_METADATA_INVALID") from exc
            packet_rows.append({"candidate_source_event_id": key,
                                "row_kind": "RELATION_REFUSED", "reason": exc.code,
                                "context_sha256": art.sha256 if art else None,
                                "authority": dict(AUTHORITY)})
            continue
        try:
            enrollment = build_shadow_enrollment(candidate_row=candidate,
                                                 b1_snapshot=b1_snapshot,
                                                 context=art)
            validate_shadow_enrollment(enrollment)
        except ValueError as exc:
            raise PTSEPublicationError("ENROLLMENT_REBUILD_REFUSED") from exc
        _authority(enrollment["authority"])
        packet_rows.append({"candidate_source_event_id": key, "row_kind": "ENROLLED",
                            "enrollment": enrollment})
    refused = sum(r["row_kind"] == "RELATION_REFUSED" for r in packet_rows)
    packet = {"schema": SCHEMA, "stamp_date": stamp,
              "candidate_generation_id": b1_snapshot.generation_id,
              "candidate_keys": keys,
              "candidate_population_sha256": _digest(candidate_bytes),
              "b1_material_sha256": _digest(b1_bytes),
              "receipt_manifest": manifest,
              "receipt_manifest_sha256": receipt_manifest_sha256,
              "context_artifact_sha256s": sorted(artifacts), "rows": packet_rows,
              "denominators": {"attempted": len(rows), "enrolled": len(rows) - refused,
                               "relation_refused": refused},
              "preflight_status": ("RELATION_REFUSED" if refused else
                                   "READY_FOR_EXISTING_PUBLICATION_OWNER"),
              "publication_authority": False, "authority": dict(AUTHORITY)}
    packet["packet_id"] = "ptse-w3:" + _digest(_canonical(packet))
    return PublicationBundle(_canonical(packet),
                             tuple((k, artifacts[k].encode("utf-8")) for k in sorted(artifacts)))


def _parse_packet(raw: bytes) -> dict:
    if type(raw) is not bytes:
        _fail("IMMUTABLE_PACKET_BYTES_REQUIRED")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                _fail("PACKET_DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    try:
        packet = json.loads(raw, object_pairs_hook=pairs)
    except (ValueError, UnicodeError) as exc:
        raise PTSEPublicationError("PACKET_JSON_INVALID") from exc
    if not isinstance(packet, dict) or _canonical(packet) != raw:
        _fail("PACKET_NOT_CANONICAL")
    return packet


def validate_publication_packet(packet: bytes, **reconstruction_inputs: Any) -> None:
    """Rebuild against externally supplied original source inputs and digest pin.

    The original full candidate population, original pinned validated B1 snapshot,
    manifest and its independent pin, and actual context bytes are required.
    Neither retained packet hashes nor owner descriptions authenticate a source.
    Exact full reconstruction verifies closed schemas, every enrollment/refusal,
    digest, denominator, and canonical identity; packet self-hashes do not suffice.
    """
    p = _parse_packet(packet)
    required = {"schema", "stamp_date", "candidate_generation_id", "candidate_keys",
                "candidate_population_sha256", "b1_material_sha256",
                "receipt_manifest", "receipt_manifest_sha256", "context_artifact_sha256s",
                "rows", "denominators", "preflight_status", "publication_authority",
                "authority", "packet_id"}
    _closed(p, required, "PACKET_FIELDS_NOT_CLOSED")
    _authority(p["authority"])
    if p["publication_authority"] is not False:
        _fail("PUBLICATION_AUTHORITY_FORBIDDEN")
    # Python equality aliases False and zero. Check nested authority before any
    # comparison, then use byte equality for the entire semantic reconstruction.
    if not isinstance(p["rows"], list):
        _fail("PACKET_ROWS_INVALID")
    for row in p["rows"]:
        if not isinstance(row, Mapping):
            _fail("PACKET_ROW_INVALID")
        if row.get("row_kind") == "ENROLLED":
            if not isinstance(row.get("enrollment"), Mapping):
                _fail("PACKET_ENROLLMENT_INVALID")
            _authority(row["enrollment"].get("authority"))
            try:
                validate_shadow_enrollment(row["enrollment"])
            except ValueError as exc:
                raise PTSEPublicationError("PACKET_ENROLLMENT_INVALID") from exc
        elif row.get("row_kind") == "RELATION_REFUSED":
            _authority(row.get("authority"))
        else:
            _fail("PACKET_ROW_KIND_INVALID")
    rebuilt = build_publication_packet(**reconstruction_inputs)
    if rebuilt.packet != packet:
        _fail("PACKET_SEMANTIC_REBUILD_MISMATCH")


@dataclass(frozen=True)
class PublicationPreflight:
    status: str
    reason: str | None
    first_packet: bytes
    candidate_packet: bytes
    candidate_context_artifacts: tuple[tuple[str, bytes], ...]
    lineage_first_packet_id: str
    lineage_candidate_packet_id: str
    publication_authority: bool = False


def preflight_publication(*, previous_packet: bytes | None = None,
                          previous_inputs: Mapping[str, Any] | None = None,
                          **inputs: Any) -> PublicationPreflight:
    """Independent PTSE freeze. The preserved first packet is never rewritten.

    Previous source inputs and pins must come from independent caller custody,
    not packet claims. Corrections become refused lineage candidates. No legacy
    W3 completion flag participates in this contract.
    """
    if previous_packet is not None:
        if not isinstance(previous_inputs, Mapping):
            _fail("INDEPENDENT_PREVIOUS_SOURCE_INPUTS_REQUIRED")
        validate_publication_packet(previous_packet, **previous_inputs)
    proposed = build_publication_packet(**inputs)
    new = _parse_packet(proposed.packet)
    if previous_packet is None:
        return PublicationPreflight("FIRST_PACKET", None, proposed.packet,
                                    proposed.packet, proposed.context_artifacts,
                                    new["packet_id"], new["packet_id"])
    old = _parse_packet(previous_packet)
    if old["stamp_date"] != new["stamp_date"]:
        _fail("REPLAY_STAMP_MISMATCH")
    if previous_packet == proposed.packet:
        return PublicationPreflight("IDENTICAL_REPLAY", None, previous_packet,
                                    proposed.packet, proposed.context_artifacts,
                                    old["packet_id"], new["packet_id"])
    old_keys, new_keys = set(old["candidate_keys"]), set(new["candidate_keys"])
    reason = ("POPULATION_CHANGED" if old_keys - new_keys and new_keys - old_keys else
              "CANDIDATES_OMITTED" if old_keys - new_keys else
              "CANDIDATES_ADDED" if new_keys - old_keys else "CONTENT_CHANGED")
    return PublicationPreflight("REVISION_REFUSED", reason, previous_packet,
                                proposed.packet, proposed.context_artifacts,
                                old["packet_id"], new["packet_id"])


__all__ = ["SCHEMA", "RECEIPT_SCHEMA", "PTSEPublicationError", "PublicationBundle", "PublicationPreflight",
           "b1_material_bytes", "build_publication_packet", "validate_publication_packet",
           "preflight_publication"]
