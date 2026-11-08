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
    canonical_json_sha256,
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



# These are declarations, never authenticated identities or permission grants.
ROLE_SCHEMA = "research_codegen.role_declarations.v1"
ROLE_NAMES = frozenset({"acquisition", "execution", "evaluation", "publication"})
ROLE_CAPABILITIES = {
    "acquisition": frozenset({"contents:read", "data:read"}),
    "execution": frozenset({"candidate:compute"}),
    "evaluation": frozenset({"evaluation:compute"}),
    "publication": frozenset({"contents:write", "pull_requests:write"}),
}
ROLE_KEYS = frozenset({"role", "principal_sha256", "issuer_sha256", "subject_sha256",
                       "alias_sha256s", "credential_reference_sha256", "capabilities", "provenance"})
PROVENANCE_KEYS = frozenset({"role", "principal_sha256", "binding_sha256", "reference_sha256"})


def _digest(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _identity_binding(manifest):
    return {**{key: manifest[key] for key in (
        "candidate_id", "source_sha256", "config_sha256", "protocol_sha256",
        "input_policy_sha256", "runtime_sha256", "evaluator_sha256", "trial_family")},
        "original_root_id": manifest["lineage"]["original_root_id"],
        "manifest_sha256": canonical_json_sha256(manifest)}


def _assess_role_declarations(manifest, declarations):
    """Pure closed-schema comparison; even consistent declarations are unattested.

    All identity/reference material is opaque digests. No credential value,
    URL, account lookup, signature verification or effective-permission probe
    belongs here. No violation echoes untrusted values.
    """
    binding = _identity_binding(manifest)
    errors = []
    declaration_digest = None
    if declarations is not None:
        if not is_exact_json(declarations):
            errors.append("role_declarations: bounded exact JSON required")
        elif not _closed(declarations, frozenset({"schema", "binding", "roles"}),
                         "role_declarations", errors):
            pass
        else:
            declaration_digest = canonical_json_sha256(declarations)
            if declarations["schema"] != ROLE_SCHEMA:
                errors.append("role_declarations: wrong schema")
            if declarations["binding"] != binding:
                errors.append("role_declarations: native identity binding mismatch")
            roles = declarations["roles"]
            if _closed(roles, ROLE_NAMES, "role_declarations.roles", errors):
                used = set()
                binding_digest = canonical_json_sha256(binding)
                for role in sorted(ROLE_NAMES):
                    row = roles[role]
                    label = "role_declarations." + role
                    if not _closed(row, ROLE_KEYS, label, errors):
                        continue
                    if row["role"] != role:
                        errors.append(label + ": role mismatch")
                    for key in ("principal_sha256", "issuer_sha256", "subject_sha256"):
                        if not _digest(row[key]):
                            errors.append(label + ": opaque identity digest required")
                    aliases = row["alias_sha256s"]
                    aliases_ok = (type(aliases) is list and len(aliases) <= 8
                                  and all(_digest(x) for x in aliases)
                                  and len(set(aliases)) == len(aliases))
                    if not aliases_ok:
                        errors.append(label + ": invalid aliases")
                    caps = row["capabilities"]
                    if not (type(caps) is list and all(type(x) is str for x in caps)
                            and len(caps) == len(set(caps))
                            and set(caps) <= ROLE_CAPABILITIES[role]):
                        errors.append(label + ": capability outside declared role")
                    credential = row["credential_reference_sha256"]
                    if credential is not None and (not _digest(credential)
                                                  or role in ("execution", "evaluation")):
                        errors.append(label + ": credential reference forbidden or malformed")
                    provenance = row["provenance"]
                    refs = []
                    if _closed(provenance, PROVENANCE_KEYS, label + ".provenance", errors):
                        if (provenance["role"] != role
                                or provenance["principal_sha256"] != row["principal_sha256"]
                                or provenance["binding_sha256"] != binding_digest):
                            errors.append(label + ": provenance binding mismatch")
                        if not _digest(provenance["reference_sha256"]):
                            errors.append(label + ": opaque provenance digest required")
                        else:
                            refs.append(provenance["reference_sha256"])
                    # Shared issuer origins are allowed; subjects/principals/aliases
                    # and evidence/credential references must not alias another role.
                    refs.extend(x for x in (row["principal_sha256"], row["subject_sha256"], credential)
                                if _digest(x))
                    if aliases_ok:
                        refs.extend(aliases)
                    if len(set(refs)) != len(refs) or used.intersection(refs):
                        errors.append(label + ": identity or reference collision")
                    used.update(refs)
    status = ("REFUSED" if errors else "UNKNOWN" if declarations is None
              else "DECLARED_SEPARATION_UNATTESTED")
    return {
        "schema": "research_codegen.identity_assessment.v1",
        "status": status,
        "binding": binding,
        "declaration_sha256": declaration_digest,
        "violations": _dedupe(errors),
        "authenticated_identity": "UNKNOWN",
        "credential_observation": "UNKNOWN",
        "effective_protection": "UNKNOWN",
        "generation_enabled": False,
        "execution_enabled": False,
        "evaluation_enabled": False,
        "authority_granted": False,
    }


def assess_prerequisites(manifest: object, *, trusted_protocol: object,
                         owner_receipts: object, role_declarations: object = None) -> dict:
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
    identity_assessment = None
    if manifest_shaped and protocol_shaped and not errors:
        identity_assessment = _assess_role_declarations(manifest, role_declarations)
        errors.extend(identity_assessment["violations"])
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
        "identity_assessment": identity_assessment,
        "generation_enabled": False,
        "execution_enabled": False,
        "evaluation_enabled": False,
        "authority_granted": False,
        "trusted_origin_and_effective_boundaries": "UNQUALIFIED",
        "note": _NOTE,
    }
