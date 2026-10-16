"""Dormant prerequisite assessment; structural matching with zero authority.

``assess_prerequisites`` is a pure, permanently dormant consumer.  It performs
manifest/protocol configuration agreement plus required-owner-reference
completeness and binding comparisons, and nothing else.  It never reads a
ledger or vault, never evaluates a candidate, never enables generation,
execution or evaluation, and never creates a truth ledger.  Every result
carries all enabled flags False and ``authority_granted`` False.  Even
structurally complete inert owner references remain zero-authority: trusted
origin, effective boundaries and history are unqualified here and require a
future independently accepted owner integration.

Receipts are closed ``research_codegen.owner_reference.v1`` objects binding
``evidence_id``, ``source_sha256`` and ``protocol_sha256``.  No
candidate-supplied ``accepted``/``pass``/``isolation`` flags exist in the
schema, so none can influence any outcome.
"""
from __future__ import annotations

from engine.research_codegen.contracts import (
    MANIFEST_KEYS,
    MAX_ID_CHARS,
    is_exact_json,
    validate_manifest,
    _closed,
    _dedupe,
    _opaque_id,
)

RECEIPT_SCHEMA = "research_codegen.owner_reference.v1"
RECEIPT_KEYS = frozenset({"schema", "evidence_id", "source_sha256",
                          "protocol_sha256"})

ASSESSMENT_SCHEMA = "research_codegen.admission_assessment.v1"

_NOTE = (
    "Structural manifest/config agreement and required-receipt completeness "
    "only. Trusted origin, effective boundaries and history are unqualified "
    "by this pure layer and require a future independently accepted owner "
    "integration. No new truth ledger is created."
)


def _receipt_errors(owner_receipts: object, manifest: dict,
                    required: list) -> list:
    errors: list = []
    if not is_exact_json(owner_receipts):
        return ["owner_receipts: bounded finite exact JSON required"]
    if type(owner_receipts) is not dict:
        return ["owner_receipts: exact JSON object required"]
    keys = list(owner_receipts)
    if not all(type(key) is str for key in keys):
        return ["owner_receipts: string receipt names required"]
    # Safe set operations only after exact-str type checks above.
    required_set = set(required)
    supplied_set = set(keys)
    for name in sorted(required_set - supplied_set):
        errors.append("owner_receipts." + name + ": required receipt missing")
    for name in sorted(supplied_set - required_set):
        errors.append("owner_receipts." + name + ": unexpected extra receipt")
    for name in sorted(required_set & supplied_set):
        receipt = owner_receipts[name]
        label = "owner_receipts." + name
        if not _closed(receipt, RECEIPT_KEYS, label, errors):
            continue
        if receipt["schema"] != RECEIPT_SCHEMA:
            errors.append(label + ": wrong schema")
        if not _opaque_id(receipt["evidence_id"]) \
                or len(receipt["evidence_id"]) > MAX_ID_CHARS:
            errors.append(label + ": malformed evidence_id")
        if receipt["source_sha256"] != manifest["source_sha256"]:
            errors.append(label + ": source_sha256 binding mismatch")
        if receipt["protocol_sha256"] != manifest["protocol_sha256"]:
            errors.append(label + ": protocol_sha256 binding mismatch")
    return errors


def assess_prerequisites(manifest: object, *, trusted_protocol: object,
                         owner_receipts: object) -> dict:
    """Compare inert manifest, trusted protocol and owner references.

    Returns a fixed dormant assessment dictionary.  Violations are structural
    only; their absence is not acceptance, and their presence never gates or
    authorizes anything.  This function can never return an enabled or
    admitted candidate.
    """
    errors: list = list(validate_manifest(manifest, trusted_protocol=trusted_protocol))
    manifest_shaped = (type(manifest) is dict and is_exact_json(manifest)
                       and set(manifest) == MANIFEST_KEYS)
    protocol_shaped = (type(trusted_protocol) is dict
                       and is_exact_json(trusted_protocol))
    if manifest_shaped and protocol_shaped and not errors:
        required = trusted_protocol["required_evidence"]
        if type(required) is list and all(type(name) is str for name in required) \
                and required:
            errors.extend(_receipt_errors(owner_receipts, manifest, required))
        else:
            errors.append("owner_receipts: trusted required_evidence not assessable")
    status = "PREREQUISITES_INVALID" if errors else "STRUCTURALLY_COMPLETE_DISABLED"
    return {
        "schema": ASSESSMENT_SCHEMA,
        "status": status,
        "violations": _dedupe(errors),
        "generation_enabled": False,
        "execution_enabled": False,
        "evaluation_enabled": False,
        "authority_granted": False,
        "trusted_origin_and_effective_boundaries": "UNQUALIFIED",
        "note": _NOTE,
    }
