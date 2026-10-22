"""Pure, exact-byte legacy conversion planning using the existing claims format.

The caller supplies immutable bytes and their expected identity. This module
authenticates neither their Git origin nor their publication/issuer history.
It performs no I/O, discovers no format, changes no production selector, and
does not install the empty base or run clocks. In particular, the plan's
expected root describes a VIRTUAL empty native seed, not the live legacy file.
The existing native materializer is not a legacy-cutover implementation.

All source bytes must fit the finite protocol profile. Planning retains the
input plus protocol snapshots/members; no streaming-memory or real-history
resource qualification is claimed. LF scanning avoids a second full row list.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Mapping

from engine.qledger_store_protocol import (
    BASE_PATH, ROOT_PATH, InMemorySource, MemberRef, ProtocolLimits,
    PublicationPlan, RootRecord, SnapshotIntegrityError, plan_append,
    validate_plan, validate_publication, verify_snapshot,
)


@dataclass(frozen=True)
class LegacyConversionPlan:
    source_id: str
    byte_count: int
    logical_digest: str
    plan: PublicationPlan
    members: Mapping[str, bytes]
    source_assurance: str = "CALLER_BYTES_ONLY_NOT_CUTOVER_ADMISSION"


def plan_legacy_conversion(
    raw_bytes: bytes, *, source_id: str, expected_byte_count: int,
    expected_logical_digest: str, transaction_id: str, limits: ProtocolLimits,
) -> LegacyConversionPlan:
    """Return a verified empty-base/one-append candidate, without materializing.

    Every ordered byte occurrence survives, including invalid JSON and blank
    records. Missing final LF is refused rather than repaired. The caller's
    source tag is descriptive, not a grant to adopt or publish that history.
    Remote/source custody and complete Git ancestry must be proven separately
    with the existing publication witnesses before any admitted cutover.
    """
    def refuse(code: str, detail: str) -> None:
        raise SnapshotIntegrityError(code, detail)

    if type(limits) is not ProtocolLimits:
        refuse("MALFORMED", "an exact protocol profile is required")
    # Recheck even a forged/tampered frozen instance against supported ceilings.
    ProtocolLimits(**asdict(limits))
    if type(raw_bytes) is not bytes or not raw_bytes or not raw_bytes.endswith(b"\n"):
        refuse("CONVERSION_INPUT", "nonempty immutable LF-terminated source bytes required")
    if type(expected_byte_count) is not int or expected_byte_count != len(raw_bytes):
        refuse("SOURCE_CHANGED", "legacy source byte count differs from its witness")
    if len(raw_bytes) > limits.logical_bytes:
        refuse("LIMIT", "legacy source exceeds the logical byte budget")
    digest = sha256(raw_bytes).hexdigest()
    if type(expected_logical_digest) is not str or expected_logical_digest != digest:
        refuse("SOURCE_CHANGED", "legacy source digest differs from its witness")

    empty_digest = sha256(b"").hexdigest()
    seed = InMemorySource({BASE_PATH: b""}, snapshot_id=source_id)
    root = RootRecord(MemberRef(BASE_PATH, empty_digest, 0), None, 0, 0,
                      empty_digest, limits.fingerprint)
    before = verify_snapshot(seed, root, limits=limits)

    def records():
        start = 0
        while start < len(raw_bytes):
            end = raw_bytes.find(b"\n", start) + 1
            if end - start > limits.part_bytes:
                refuse("CAPACITY", "single serialized row exceeds the part bound")
            # Final-LF validation guarantees progress; protocol enforces each
            # row's length and the finite row/part/catalog/snapshot budgets.
            yield raw_bytes[start:end]
            start = end

    plan = plan_append(before, transaction_id=transaction_id,
                       serialized_rows=records(), limits=limits)
    validate_plan(plan, limits=limits)
    if (plan.snapshot.root.logical_size != len(raw_bytes)
            or plan.snapshot.root.logical_digest != digest):
        refuse("CONFLICT", "conversion differs from its original logical stream")
    members = MappingProxyType({BASE_PATH: b"", **plan.members, ROOT_PATH: plan.root_bytes})
    if any(len(value) > limits.git_blob_bytes for value in members.values()):
        refuse("NONRETRYABLE_OVERSIZE", "conversion member exceeds the Git blob bound")
    # Complete candidate inventory verification, not a Git ancestry proof.
    source = InMemorySource(members, snapshot_id=source_id)
    validate_publication(source, plan.snapshot.root, (), limits=limits)
    return LegacyConversionPlan(source_id, len(raw_bytes), digest, plan, members)
