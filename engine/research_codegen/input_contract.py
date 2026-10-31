"""Per-decision causal input envelope validation; inert structure only.

The trusted assigning caller supplies an expected request identity
(``research_codegen.request.v1``) separately from the candidate envelope
(``research_codegen.input.v1``).  This module compares inert structures:
it never reads a market store, never classifies labels, never invents a
missing ``available_at``, never coerces an explicit null value into zero, and
never grants execution, evaluation or authority.  A timestamp comparison is a
clock comparison between aware UTC instants; it authenticates nothing.

Deterministic observation order (documented contract): rows must be in
ascending order by ``(available_at, event_time, source_id, revision_id)``
compared as aware UTC instants for the timestamps and as exact strings for
the identifiers.  This is the specified deterministic equivalent of a stable
canonical sort; a differently ordered but otherwise valid envelope is a
violation, so downstream consumers see one fixed sequence.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
import re

from engine.research_codegen.contracts import (
    MAX_BYTES,
    MAX_CONTAINER_ITEMS,
    MAX_ID_CHARS,
    MAX_STRING_CHARS,
    is_exact_json,
    _closed,
    _candidate_id,
    _dedupe,
    _opaque_id,
    _sha,
)

INPUT_SCHEMA = "research_codegen.input.v1"
REQUEST_SCHEMA = "research_codegen.request.v1"

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_MAX_TIMESTAMP_CHARS = 40

ENVELOPE_KEYS = frozenset({
    "schema", "candidate_id", "fold_id", "entity_id", "decision_id", "cutoff",
    "input_policy_sha256", "observations",
})
REQUEST_KEYS = frozenset({
    "schema", "candidate_id", "fold_id", "entity_id", "decision_id", "cutoff",
    "input_policy_sha256", "allowed_source_ids",
})
OBSERVATION_KEYS = frozenset({
    "source_id", "revision_id", "event_time", "available_at", "received_at",
    "evidence_class", "value",
})
EVIDENCE_CLASSES = ("captured", "reconstructed")


def parse_timestamp(value: object) -> datetime:
    """Parse a bounded aware ISO-8601 timestamp into a UTC instant.

    Naive timestamps, non-strings, unknown formats, malformed text and
    overlong strings raise ``ValueError``.  Only exact ``str`` input reaches
    the parser, so no foreign ``__str__``/``__repr__`` is ever invoked.
    """
    if type(value) is not str or not value or len(value) > _MAX_TIMESTAMP_CHARS:
        raise ValueError("timestamp must be a short ISO-8601 string")
    text = value
    if text[-1] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    try:
        return parsed.astimezone(timezone.utc)
    except OverflowError:
        raise ValueError("timestamp UTC instant is out of range") from None


def _validate_request(request: object, errors: list) -> bool:
    """Structurally validate the separately supplied trusted request."""
    if not is_exact_json(request):
        errors.append("trusted_request: bounded finite exact JSON required")
        return False
    if not _closed(request, REQUEST_KEYS, "trusted_request", errors):
        return False
    if request["schema"] != REQUEST_SCHEMA:
        errors.append("trusted_request: wrong schema")
    if not _candidate_id(request["candidate_id"]):
        errors.append("trusted_request: malformed candidate_id")
    for field in ("fold_id", "entity_id", "decision_id"):
        if not _opaque_id(request[field]):
            errors.append("trusted_request: malformed " + field)
    if not _sha(request["input_policy_sha256"]):
        errors.append("trusted_request: malformed input_policy_sha256")
    try:
        parse_timestamp(request["cutoff"])
    except ValueError:
        errors.append("trusted_request: malformed or naive cutoff")
    allowed = request["allowed_source_ids"]
    if type(allowed) is not list or not allowed:
        errors.append("trusted_request: nonempty allowed_source_ids list required")
        return False
    if not all(_opaque_id(name) and len(name) <= MAX_ID_CHARS for name in allowed):
        errors.append("trusted_request: malformed allowed_source_ids entry")
        return False
    if len(set(allowed)) != len(allowed):
        errors.append("trusted_request: duplicate allowed_source_ids entry")
    return not errors


def _parse_row_timestamp(row: dict, field: str, label: str, errors: list):
    try:
        return parse_timestamp(row[field])
    except ValueError:
        errors.append(label + ": malformed or naive " + field)
        return None


def validate_input_envelope(envelope: object, *, trusted_request: object) -> list:
    """Validate one candidate input envelope against the trusted request.

    Returns a list of structural violations.  An empty list means the envelope
    structurally matches the trusted per-decision request; it is causal or
    complete-data evidence of nothing by itself.  Empty ``observations`` is a
    valid explicit zero-coverage result: downstream consumers must warm up or
    refuse, never invent a value.
    """
    errors: list = []
    envelope_exact = is_exact_json(envelope)
    if not envelope_exact:
        errors.append("envelope: bounded finite exact JSON required")
    _validate_request(trusted_request, errors)
    if errors:
        return _dedupe(errors)

    request = trusted_request
    cutoff = parse_timestamp(request["cutoff"])

    if not _closed(envelope, ENVELOPE_KEYS, "envelope", errors):
        return _dedupe(errors)
    if envelope["schema"] != INPUT_SCHEMA:
        errors.append("envelope: wrong schema")
    for field in ("candidate_id", "fold_id", "entity_id", "decision_id"):
        if envelope[field] != request[field]:
            errors.append("envelope: " + field + " does not match trusted request")
    if envelope["input_policy_sha256"] != request["input_policy_sha256"]:
        errors.append("envelope: input_policy_sha256 does not match trusted request")
    envelope_cutoff = _parse_row_timestamp(envelope, "cutoff", "envelope", errors)
    if envelope_cutoff is not None and envelope_cutoff != cutoff:
        errors.append("envelope: cutoff is not the trusted decision cutoff instant")

    rows = envelope["observations"]
    if type(rows) is not list or len(rows) > MAX_CONTAINER_ITEMS:
        errors.append("envelope.observations: bounded list required")
        return _dedupe(errors)

    allowed = set(request["allowed_source_ids"])
    seen_identity: set = set()
    previous_order = None
    for index, row in enumerate(rows):
        label = "envelope.observations[%d]" % index
        if not _closed(row, OBSERVATION_KEYS, label, errors):
            continue
        source = row["source_id"]
        # Safe type checks BEFORE any set membership or hashing.
        if type(source) is not str or not source or len(source) > MAX_ID_CHARS \
                or _ID.fullmatch(source) is None:
            errors.append(label + ": malformed source_id")
        elif source not in allowed:
            errors.append(label + ": source_id not allowed by trusted request")
        revision = row["revision_id"]
        if type(revision) is not str or not revision or len(revision) > MAX_STRING_CHARS:
            errors.append(label + ": malformed revision_id")
        event_at = _parse_row_timestamp(row, "event_time", label, errors)
        available = _parse_row_timestamp(row, "available_at", label, errors)
        raw_received = row["received_at"]
        received = None
        if raw_received is not None:
            received = _parse_row_timestamp(row, "received_at", label, errors)
        evidence = row["evidence_class"]
        if evidence not in EVIDENCE_CLASSES:
            errors.append(label + ": evidence_class must be 'captured' or 'reconstructed'")
        value = row["value"]
        if value is not None:
            # bool is never accepted as a numeric measurement.
            if isinstance(value, bool) or type(value) not in (int, float) \
                    or not math.isfinite(value):
                errors.append(label + ": value must be a finite number or explicit null")
        if event_at is None or available is None:
            continue
        if event_at > available:
            errors.append(label + ": event_time is after available_at")
        if available > cutoff:
            errors.append(label + ": available_at is after the decision cutoff")
        if received is not None:
            if received < available:
                errors.append(label + ": received_at precedes available_at")
            if evidence == "captured" and received > cutoff:
                errors.append(label + ": captured evidence received after the cutoff")
        elif evidence == "captured":
            errors.append(label + ": captured evidence requires received_at")
        # Reconstructed evidence may carry received_at null or after the cutoff;
        # it then stays evidence_class 'reconstructed' by the closed rule above.
        if type(source) is str and type(revision) is str:
            identity = (source, revision, event_at)
            if identity in seen_identity:
                errors.append(label + ": duplicate (source_id, revision_id, event_time)")
            seen_identity.add(identity)
            order_key = (available, event_at, source, revision)
            if previous_order is not None and order_key < previous_order:
                errors.append(label + ": observations not in deterministic order")
            previous_order = order_key
    if len(errors) > MAX_BYTES:
        del errors[MAX_BYTES:]
        errors.append("envelope: violation overflow")
    return _dedupe(errors)
