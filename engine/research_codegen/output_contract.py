"""Fixed-schedule output envelope validation; inert structure only.

The trusted assigning caller supplies the expected schedule identity and the
complete ordered decision list (``research_codegen.schedule.v1``) separately
from the candidate output envelope (``research_codegen.output.v1``).  This
module enforces exact schedule conservation: every requested decision id
appears exactly once, in the trusted order, with no extras, duplicates, drops
or id shifts.  It validates closed inert rows only -- no candidate-supplied
timestamps, labels, statistics, p-values, eligibility, cost, sign, gate or
authority fields exist in the schema, and none can be smuggled in.  An empty
trusted schedule with an empty rows list is a valid explicit
zero-opportunity structural result.  Nothing here runs a candidate or proves
any integrated causal execution; a returned empty violation list is
structural evidence only.
"""
from __future__ import annotations

import math
import re

from engine.research_codegen.contracts import (
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

OUTPUT_SCHEMA = "research_codegen.output.v1"
SCHEDULE_SCHEMA = "research_codegen.schedule.v1"

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_MAX_REASON_CHARS = 512

ENVELOPE_KEYS = frozenset({
    "schema", "candidate_id", "fold_id", "entity_id", "input_policy_sha256",
    "rows",
})
SCHEDULE_KEYS = frozenset({
    "schema", "candidate_id", "fold_id", "entity_id", "input_policy_sha256",
    "decision_ids",
})
ROW_KEYS = frozenset({"decision_id", "status", "value", "reason"})
ROW_STATUSES = ("available", "missing", "warmup", "refused", "failed")


def _validate_schedule(schedule: object, errors: list) -> bool:
    """Structurally validate the separately supplied trusted schedule."""
    if not is_exact_json(schedule):
        errors.append("trusted_schedule: bounded finite exact JSON required")
        return False
    if not _closed(schedule, SCHEDULE_KEYS, "trusted_schedule", errors):
        return False
    if schedule["schema"] != SCHEDULE_SCHEMA:
        errors.append("trusted_schedule: wrong schema")
    if not _candidate_id(schedule["candidate_id"]):
        errors.append("trusted_schedule: malformed candidate_id")
    for field in ("fold_id", "entity_id"):
        if not _opaque_id(schedule[field]):
            errors.append("trusted_schedule: malformed " + field)
    if not _sha(schedule["input_policy_sha256"]):
        errors.append("trusted_schedule: malformed input_policy_sha256")
    decisions = schedule["decision_ids"]
    # Empty decision_ids is a valid explicit zero-opportunity schedule.
    if type(decisions) is not list or len(decisions) > MAX_CONTAINER_ITEMS:
        errors.append("trusted_schedule: bounded decision_ids list required")
        return False
    # Safe exact-str type checks BEFORE any set membership or hashing.
    if not all(type(name) is str and len(name) <= MAX_ID_CHARS
               and _ID.fullmatch(name) is not None for name in decisions):
        errors.append("trusted_schedule: malformed decision_ids entry")
        return False
    if len(set(decisions)) != len(decisions):
        errors.append("trusted_schedule: duplicate decision_ids entry")
    return not errors


def validate_output_envelope(envelope: object, *, trusted_schedule: object) -> list:
    """Validate one candidate output envelope against the trusted schedule.

    Returns a list of structural violations.  An empty list means the envelope
    conserves the fixed trusted schedule exactly; it is not a PASS and grants
    no authority.
    """
    errors: list = []
    if not is_exact_json(envelope):
        errors.append("envelope: bounded finite exact JSON required")
    schedule_ok = _validate_schedule(trusted_schedule, errors)
    if errors:
        return _dedupe(errors)
    schedule = trusted_schedule

    if not _closed(envelope, ENVELOPE_KEYS, "envelope", errors):
        return _dedupe(errors)
    if envelope["schema"] != OUTPUT_SCHEMA:
        errors.append("envelope: wrong schema")
    for field in ("candidate_id", "fold_id", "entity_id"):
        if envelope[field] != schedule[field]:
            errors.append("envelope: " + field + " does not match trusted schedule")
    if envelope["input_policy_sha256"] != schedule["input_policy_sha256"]:
        errors.append("envelope: input_policy_sha256 does not match trusted schedule")

    rows = envelope["rows"]
    decisions = schedule["decision_ids"]
    if type(rows) is not list or len(rows) > MAX_CONTAINER_ITEMS:
        errors.append("envelope.rows: bounded list required")
        return _dedupe(errors)
    if len(rows) != len(decisions):
        errors.append("envelope.rows: row count does not conserve the trusted schedule")

    for index, row in enumerate(rows):
        label = "envelope.rows[%d]" % index
        if not _closed(row, ROW_KEYS, label, errors):
            continue
        decision = row["decision_id"]
        # Positional conservation: the trusted order is the only order.
        if index < len(decisions):
            if type(decision) is not str or decision != decisions[index]:
                errors.append(label + ": decision_id does not match trusted schedule position")
        else:
            errors.append(label + ": unexpected extra row beyond the trusted schedule")
        status = row["status"]
        if status not in ROW_STATUSES:
            errors.append(label + ": status must be one of " + ",".join(ROW_STATUSES))
        value = row["value"]
        reason = row["reason"]
        if status == "available":
            # bool is never a numeric value; only finite strict numbers count.
            if isinstance(value, bool) or type(value) not in (int, float) \
                    or not math.isfinite(value):
                errors.append(label + ": available row requires a strict finite value")
            if reason is not None:
                errors.append(label + ": available row requires reason null")
        else:
            if value is not None:
                errors.append(label + ": non-available row requires value null")
            if type(reason) is not str or not reason or len(reason) > _MAX_REASON_CHARS:
                errors.append(label + ": non-available row requires a bounded reason")
    return _dedupe(errors)
