"""Pure preparation for the existing DataOS initial-reference publication format.

This module does not publish, read files, decode Parquet, supply an observation
clock, or admit an identity. The assigning owner must separately establish the
provenance of the supplied bytes/records and perform any authorized publication.
Native canonicalization and validation remain owned by ``lib.dataos.identity``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import re

from lib.dataos import identity as native


@dataclass(frozen=True, slots=True)
class InitialReferenceCandidate:
    """Detached preparation metadata, not publication or source-authenticity proof.

    ``original_receipt_sha256`` binds the exact supplied byte spelling. Candidate
    bytes are canonicalized separately. The false status fields are descriptions
    of this function's work, not access-control or publisher authorization tokens.
    """
    candidate_receipt_bytes: bytes
    original_receipt_sha256: str
    candidate_receipt_sha256: str
    generation_id: str
    artifact_sha256: tuple[tuple[str, str], ...]
    alias_semantic_sha256: str
    master_semantic_sha256: str
    published: bool = field(default=False, init=False)
    identity_admitted: bool = field(default=False, init=False)
    records_bound_to_artifacts: bool = field(default=False, init=False)


def build_initial_reference_candidate(
    receipt_before: bytes, artifact_bytes: dict[str, bytes], *,
    alias_records, master_records, code_version: str,
) -> InitialReferenceCandidate:
    """Prepare a detached candidate, refusing an existing publication/history.

The only anchor clock comes from the supplied original prospective reference.
The five physical artifacts and two semantic record sets are all sealed using
the native format. A successful return proves internal consistency only; these
supplied records are not independently bound to their Parquet bytes here.
"""
    receipt = native._ob_load(receipt_before, 9 * native._MIB)
    native._ob_require(type(receipt) is dict, "candidate receipt object")
    native._ob_require(not {"publication", "identity_observations"} & receipt.keys(),
                       "candidate requires unpublished initial receipt")
    original = receipt.get("prospective_reference")
    native._ob_require(type(original) is dict, "candidate original reference missing")
    clock = original.get("source_read_completed_at_utc_ns")
    native._ob_require(type(clock) is int, "candidate original owner clock")
    native._ob_ns(str(clock), "candidate original owner clock")
    native._ob_require(type(code_version) is str
                       and re.fullmatch("[0-9a-f]{40}", code_version) is not None,
                       "candidate code version")
    native._ob_require(type(artifact_bytes) is dict
                       and set(artifact_bytes) == set(native._ARTIFACT_NAMES),
                       "candidate complete artifact bytes")
    artifacts = dict(artifact_bytes)
    for name, raw in artifacts.items():
        native._ob_require(type(raw) is bytes and 0 < len(raw) <= 64 * native._MIB,
                           "candidate artifact byte bound " + name)
    aliases = native._ob_records(alias_records)
    master = native._ob_records(master_records)
    rows = json.loads(aliases)
    native._ob_require(not any(row.get(k) is not None for row in rows
                               for k in native._REVISION_FIELDS),
                       "candidate cannot replace revision history")
    # Match the native owner's base-prefix definition, including nullable
    # revision columns emitted by a shared table schema.
    base = [{k: v for k, v in row.items() if k not in native._REVISION_FIELDS}
            for row in rows]
    original_digest = native._ob_digest(original)
    anchor = {
        "schema": "mastermind.identity_anchor.v1",
        "anchor_id": "anchor:" + original_digest,
        "original_reference_sha256": original_digest,
        "original_native_rows_sha256": native._ob_record_digest(
            [row for row in base if row.get("vendor") == "polygon"]),
        "owner_read_completed_at_utc_ns": str(clock),
    }
    anchor["anchor_sha256"] = native._ob_digest(anchor)
    history = {"schema": native._OBSERVATION_SCHEMA, "anchor": anchor, "attempts": []}
    semantic = {
        "vendor_aliases.parquet": hashlib.sha256(aliases).hexdigest(),
        "security_master.parquet": hashlib.sha256(master).hexdigest(),
    }
    publication = {
        "schema": "mastermind.identity_publication.v1",
        "predecessor_receipt_sha256": None,
        "code_version": code_version,
        "artifacts": {name: {"sha256": hashlib.sha256(raw).hexdigest(),
                             "bytes": len(raw), "semantic_sha256": semantic.get(name)}
                      for name, raw in artifacts.items()},
        "history_sha256": native._ob_digest(history),
    }
    publication["generation_id"] = native._ob_digest(publication)
    receipt.update(publication=publication, identity_observations=history)
    candidate = native._ob_json(receipt, 9 * native._MIB)
    native.validate_reference_snapshot(
        candidate, artifacts, candidate,
        alias_records=rows, master_records=json.loads(master),
    )
    return InitialReferenceCandidate(
        candidate_receipt_bytes=candidate,
        original_receipt_sha256=hashlib.sha256(receipt_before).hexdigest(),
        candidate_receipt_sha256=hashlib.sha256(candidate).hexdigest(),
        generation_id=publication["generation_id"],
        artifact_sha256=tuple((name, publication["artifacts"][name]["sha256"])
                              for name in native._ARTIFACT_NAMES),
        alias_semantic_sha256=semantic["vendor_aliases.parquet"],
        master_semantic_sha256=semantic["security_master.parquet"],
    )


@dataclass(frozen=True, slots=True)
class ParquetBoundInitialCandidate:
    """Structural byte-to-record proof for an initial candidate, not publication.

    The exact five supplied Parquet byte buffers have been decoded by the
    existing Entry Radar/identity file adapter, and the same decoded
    alias/security-master rows were used by the native identity validator.
    Source HTTP authenticity, receipt origin, observation/read clock, writer
    locking, canonical publication, identity admission and any trading
    authority remain UNPROVEN.  The detached underlying candidate deliberately
    retains its original records_bound_to_artifacts=False.
    """

    candidate: InitialReferenceCandidate
    original_receipt_sha256: str
    artifact_sha256: tuple[tuple[str, str], ...]
    _decoded_record_counts: tuple[tuple[str, int], ...]
    alias_master_semantics_bound: bool = field(default=True, init=False)
    all_artifacts_parseable: bool = field(default=True, init=False)
    records_bound_to_artifacts: bool = field(default=False, init=False)
    source_authenticated: bool = field(default=False, init=False)
    published: bool = field(default=False, init=False)
    identity_admitted: bool = field(default=False, init=False)
    current_read_admitted: bool = field(default=False, init=False)

    @property
    def decoded_record_counts(self) -> dict[str, int]:
        """Return a fresh detached copy, not mutable internal provenance."""
        return dict(self._decoded_record_counts)


def build_parquet_bound_initial_candidate(
    receipt_before: bytes, artifact_bytes: dict[str, bytes], *,
    code_version: str,
) -> ParquetBoundInitialCandidate:
    """Bind exact caller-supplied Parquet bytes to the existing pure candidate.

    This is a deterministic, in-memory preparation only. It does not read a
    file, attribute timestamps, publish a generation, mint an identity or
    upgrade any existing refused market observation. The caller must separately
    prove actual file custody and the complete publisher/source clock.
    No independent Parquet parser, identity selector or lifecycle is created:
    the existing native file adapter supplies the only decoding semantics.
    """
    from engine.entry_radar.replay.identity_observation_snapshot import (
        REFERENCE_ARTIFACTS, _parquet_records,
    )

    native._ob_require(
        type(artifact_bytes) is dict
        and set(artifact_bytes) == set(REFERENCE_ARTIFACTS),
        "candidate complete artifact bytes",
    )
    files = dict(artifact_bytes)
    for name, raw in files.items():
        native._ob_require(
            type(raw) is bytes and 0 < len(raw) <= 64 * native._MIB,
            "candidate artifact byte bound " + name,
        )
    # Input bytes are immutable Python bytes. Decoding all five catches
    # malformed physical artifacts, not merely inconsistent declared digests.
    decoded = {
        name: _parquet_records(files[name], name)
        for name in REFERENCE_ARTIFACTS
    }
    candidate = build_initial_reference_candidate(
        receipt_before, files,
        alias_records=decoded["vendor_aliases.parquet"],
        master_records=decoded["security_master.parquet"],
        code_version=code_version,
    )
    return ParquetBoundInitialCandidate(
        candidate=candidate,
        original_receipt_sha256=hashlib.sha256(receipt_before).hexdigest(),
        artifact_sha256=tuple((name, hashlib.sha256(files[name]).hexdigest())
                              for name in REFERENCE_ARTIFACTS),
        _decoded_record_counts=tuple((name, len(decoded[name]))
                                     for name in REFERENCE_ARTIFACTS),
    )
