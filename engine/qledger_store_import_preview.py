"""Inert, source-pinned qualification of a legacy claims stream for QLedger parts.

This module composes the accepted qledger_store_protocol; it is not a writer,
migrator, publisher, registration path, clock hook or recovery authority.
No filesystem, Git, network, runner or production source is accessed.
A caller-supplied byte string and digest are *not* an authoritative historical
capture: failed runner tails, claim/writer custody, old-binary exclusion and
publisher ancestry still need separate owner-bound admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1, sha256
import re

from engine import qledger_store_protocol as protocol


_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_INERT_ONLY = "CALLER_BYTES_ONLY_NOT_CUTOVER_ADMISSION"


class LegacyPreviewRefusal(ValueError):
    """Fail-closed source qualification, with no sensitive row contents in errors."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"legacy conversion preview refused: {code}")


@dataclass(frozen=True)
class LegacyConversionPreview:
    input_sha256: str
    input_bytes: int
    row_occurrences: int
    logical_sha256: str
    native_base_bytes: int
    root_digest: str
    part_sizes: tuple[int, ...]
    candidate_members: int
    introduced_git_blobs: int
    max_git_blob_bytes: int
    source_assurance: str = _INERT_ONLY
    eligible_for_cutover: bool = False


def _lines_exact(payload: bytes):
    """Yield LF-delimited raw byte occurrences; NEVER parse, strip or deduplicate."""
    start = 0
    while start < len(payload):
        end = payload.find(b"\n", start)
        if end < 0:
            # The explicit last-LF check in preview() must have rejected this.
            raise LegacyPreviewRefusal("UNTERMINATED_TAIL")
        yield payload[start : end + 1]
        start = end + 1


def _git_blob_oid(value: bytes) -> str:
    return sha1(b"blob " + str(len(value)).encode("ascii") + b"\0" + value).hexdigest()


def qualify_legacy_history(
    raw_bytes: bytes,
    *,
    expected_sha256: str,
    expected_size: int,
    limits: protocol.ProtocolLimits,
) -> LegacyConversionPreview:
    """Prove in-memory format capacity/fidelity; expose no materializable plan.

    Original historic rows (including malformed, duplicates and blanks) are
    preserved byte-for-byte in protocol parts, anchored to an empty canonical
    BASE_PATH.  No registration, replay, repair or first-issue restamping occurs.
    An exact caller checksum proves only that the supplied bytes were not
    modified during this function; it does NOT authenticate their capture.
    """
    if type(raw_bytes) is not bytes or not raw_bytes:
        raise LegacyPreviewRefusal("EMPTY_OR_NONBYTES")
    if type(limits) is not protocol.ProtocolLimits:
        raise LegacyPreviewRefusal("INVALID_LIMITS")
    if type(expected_size) is not int or expected_size != len(raw_bytes):
        raise LegacyPreviewRefusal("SIZE_MISMATCH")
    if type(expected_sha256) is not str or not _HASH_RE.fullmatch(expected_sha256):
        raise LegacyPreviewRefusal("INVALID_DIGEST")
    actual_digest = sha256(raw_bytes).hexdigest()
    if actual_digest != expected_sha256:
        raise LegacyPreviewRefusal("SOURCE_CHANGED")
    if not raw_bytes.endswith(b"\n"):
        raise LegacyPreviewRefusal("UNTERMINATED_TAIL")
    if len(raw_bytes) > limits.logical_bytes:
        raise LegacyPreviewRefusal("LOGICAL_CAPACITY")

    base = b""
    base_hash = sha256(base).hexdigest()
    original = protocol.RootRecord(
        protocol.MemberRef(protocol.BASE_PATH, base_hash, 0),
        None, 0, 0, base_hash, limits.fingerprint,
    )
    initial_source = protocol.InMemorySource(
        {protocol.BASE_PATH: base}, snapshot_id="preview:empty-base",
    )
    before = protocol.verify_snapshot(initial_source, original, limits=limits)

    plan = protocol.plan_replace_view(
        before,
        transaction_id="preview-" + actual_digest[:32],
        expected_view_digest=before.root.logical_digest,
        replacement_rows=_lines_exact(raw_bytes),
        limits=limits,
    )
    protocol.validate_plan(plan, limits=limits)

    # Candidate remains in memory; never offer it as a writer or Git artifact.
    members = {protocol.BASE_PATH: base, **plan.members, protocol.ROOT_PATH: plan.root_bytes}
    source = protocol.InMemorySource(
        members, snapshot_id="preview:" + actual_digest[:32],
    )
    verified = protocol.verify_snapshot(source, plan.snapshot.root, limits=limits)

    check = sha256()
    logical_size = 0
    with protocol.open_logical_bytes(verified) as stream:
        while block := stream.read(1024 * 1024):
            check.update(block)
            logical_size += len(block)
    if logical_size != len(raw_bytes) or check.hexdigest() != actual_digest:
        raise LegacyPreviewRefusal("LOGICAL_MISMATCH")

    # An owner-supplied real Git tree inventory is still separately required.
    # These Git blob identities cover only this *synthetic candidate* mapping.
    introduced_by_oid = {}
    for value in members.values():
        oid = _git_blob_oid(value)
        if oid in introduced_by_oid and introduced_by_oid[oid].size != len(value):
            raise LegacyPreviewRefusal("BLOB_ID_COLLISION")
        introduced_by_oid[oid] = protocol.BlobInfo(oid, len(value))
    blobs = tuple(introduced_by_oid[k] for k in sorted(introduced_by_oid))
    verdict = protocol.validate_publication(
        source, verified.root, blobs, limits=limits,
    )
    if not verdict.accepted or verdict.retryable:
        raise LegacyPreviewRefusal("PUBLICATION_PREFLIGHT")

    part_sizes = tuple(sorted(
        len(value) for path, value in members.items()
        if path.startswith(protocol.PART_PREFIX)
    ))
    if not part_sizes or verified.root.base.size != 0:
        raise LegacyPreviewRefusal("INVALID_EMPTY_BASE")

    return LegacyConversionPreview(
        input_sha256=actual_digest,
        input_bytes=logical_size,
        row_occurrences=raw_bytes.count(b"\n"),
        logical_sha256=verified.root.logical_digest,
        native_base_bytes=verified.root.base.size,
        root_digest=verified.receipt.root_digest,
        part_sizes=part_sizes,
        candidate_members=verdict.candidate_members,
        introduced_git_blobs=verdict.introduced_blobs,
        max_git_blob_bytes=max(blob.size for blob in blobs),
    )
