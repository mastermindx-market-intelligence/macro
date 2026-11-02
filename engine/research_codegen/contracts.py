"""Bounded structural validators for inert research-codegen JSON contracts.

Every function here inspects plain built-in JSON trees supplied by a trusted
caller.  Nothing reads files, imports candidate code, parses candidate paths,
executes work, or performs I/O.  An empty violation list means the structure
matched the separately supplied trusted configuration; it never authenticates
a caller, an owner or a protocol, and never grants generation, execution,
evaluation, routing or publication authority.  Authority fields are fixed
display-only constants.

Design rules enforced by this module:

* Exact built-in JSON only.  ``dict``/``list``/``str``/``int``/``float``/
  ``bool``/``None`` subclasses and arbitrary objects are refused without ever
  invoking custom ``__eq__``/``__iter__``/``__len__``/``repr``/``str`` or
  hashing a custom object.
* Size, depth, node and byte limits are checked before any container is
  traversed, so pathological payloads are refused cheaply.  The limits are
  conservative structural bounds, never a runtime budget.
* Huge integers are refused by magnitude comparison before any canonical
  serialization or float conversion.
* ``bool`` never masquerades as a numeric identifier, count or measurement.
* Non-finite floats (NaN, Infinity) are refused everywhere.
* Schemas are closed: unknown keys are violations, so a candidate cannot
  smuggle code text, evaluator module paths, thresholds, actor references,
  holdout/baseline selectors, statistics, or pass/authority flags.
"""
from __future__ import annotations

import hashlib
import json
import math
import re

# Conservative structural limits (validator bounds, not runtime budgets).
MAX_DEPTH = 16
MAX_NODES = 8192
MAX_CONTAINER_ITEMS = 1024
MAX_STRING_CHARS = 4096
MAX_BYTES = 262144
MAX_INT_ABS = 2 ** 63 - 1
MAX_ID_CHARS = 128
MAX_FAMILY_CHARS = 40  # exclusive upper bound, matching the frozen family rule

MANIFEST_SCHEMA = "research_codegen.manifest.v1"
PROTOCOL_SCHEMA = "research_codegen.protocol.v1"
CANDIDATE_ID_PREFIX = "rf-codegen-"

_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_FAMILY = re.compile(r"rf\.[a-z_]+\.[a-z0-9_]+\Z")
_CANDIDATE_ID = re.compile(r"rf-codegen-[A-Za-z0-9][A-Za-z0-9_.:-]{0,117}\Z")

MANIFEST_KEYS = frozenset({
    "schema", "candidate_id", "source_sha256", "config_sha256",
    "protocol_sha256", "input_policy_sha256", "runtime_sha256",
    "evaluator_sha256", "trial_family", "lineage", "morphology", "authority",
})
LINEAGE_KEYS = frozenset({
    "original_root_id", "parent_candidate_id", "refinement_generation",
})
PROTOCOL_KEYS = frozenset({
    "schema", "protocol_sha256", "input_policy_sha256", "runtime_sha256",
    "evaluator_sha256", "trial_family", "original_root_id",
    "required_evidence",
})


def is_exact_json(value: object) -> bool:
    """Return True only for a bounded tree of exact built-in JSON types.

    The walk is iterative and type-dispatched on ``type(x) is ...``, so no
    custom ``__eq__``, ``__iter__``, ``__len__``, ``__hash__``, ``repr`` or
    ``str`` of a foreign object is ever invoked.  Depth, node, item, string
    and byte limits are enforced before descending.  Subclasses of the built-in
    containers and scalars are refused (``bool`` included, where a plain
    ``bool`` value is accepted as itself and never as a number).
    """
    pending: list[tuple[object, int]] = [(value, 0)]
    seen: set[int] = set()
    nodes = 0
    string_chars = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            return False
        kind = type(item)
        if kind is dict or kind is list:
            if id(item) in seen or len(item) > MAX_CONTAINER_ITEMS:
                return False
            seen.add(id(item))
            if kind is dict:
                for key, child in item.items():
                    if type(key) is not str or len(key) > MAX_STRING_CHARS:
                        return False
                    string_chars += len(key)
                    pending.append((child, depth + 1))
            else:
                for child in item:
                    pending.append((child, depth + 1))
            if len(pending) + nodes > MAX_NODES:
                return False
        elif kind is str:
            string_chars += len(item)
            if len(item) > MAX_STRING_CHARS:
                return False
        elif kind is int:
            if abs(item) > MAX_INT_ABS:
                return False
        elif kind is float:
            if not math.isfinite(item):
                return False
        elif item is not None and kind is not bool:
            return False
        if string_chars > MAX_BYTES:
            return False
    try:
        body = json.dumps(value, allow_nan=False, ensure_ascii=True,
                          sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return False
    return len(body) <= MAX_BYTES


def canonical_json_sha256(value: object) -> str:
    """Hash a bounded exact-JSON configuration tree canonically.

    Canonical form: ``sort_keys=True``, ``separators=(",", ":")``,
    ``ensure_ascii=True``, ``allow_nan=False``.  Raises ``ValueError`` when the
    value is not bounded exact JSON.  This hashes configuration structure
    only; raw source identities remain lowercase hash strings that are
    compared, never parsed or computed here.
    """
    if not is_exact_json(value):
        raise ValueError("canonical_json_sha256 requires bounded exact JSON")
    body = json.dumps(value, allow_nan=False, ensure_ascii=True,
                      sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def _closed(value: object, keys: frozenset, label: str, errors: list) -> bool:
    """Require an exact plain dict with exactly the closed key set."""
    if type(value) is not dict or set(value) != keys:
        errors.append(label + ": closed object required")
        return False
    return True


def _sha(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _opaque_id(value: object) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _candidate_id(value: object) -> bool:
    return type(value) is str and _CANDIDATE_ID.fullmatch(value) is not None


def _family(value: object) -> bool:
    return (type(value) is str and len(value) < MAX_FAMILY_CHARS
            and _FAMILY.fullmatch(value) is not None)


def _evidence_name(value: object) -> bool:
    return type(value) is str and len(value) <= MAX_ID_CHARS and bool(value) \
        and _ID.fullmatch(value) is not None


def _dedupe(errors: list) -> list:
    return list(dict.fromkeys(errors))


def validate_protocol(protocol: object) -> list:
    """Structurally validate a trusted protocol configuration.

    This checks the closed shape and internal consistency of a separately
    supplied trusted configuration.  It cannot prove that the configuration
    really originates from a lawful protocol owner.
    """
    errors: list = []
    if not is_exact_json(protocol):
        return ["trusted_protocol: bounded finite exact JSON required"]
    if not _closed(protocol, PROTOCOL_KEYS, "trusted_protocol", errors):
        return errors
    if protocol["schema"] != PROTOCOL_SCHEMA:
        errors.append("trusted_protocol: wrong schema")
    for field in ("protocol_sha256", "input_policy_sha256", "runtime_sha256",
                  "evaluator_sha256"):
        if not _sha(protocol[field]):
            errors.append("trusted_protocol: malformed " + field)
    if not _family(protocol["trial_family"]):
        errors.append("trusted_protocol: invalid trial_family")
    if not _opaque_id(protocol["original_root_id"]):
        errors.append("trusted_protocol: malformed original_root_id")
    required = protocol["required_evidence"]
    if type(required) is not list or not required:
        errors.append("trusted_protocol: nonempty required_evidence list required")
    elif all(_evidence_name(name) for name in required):
        if len(set(required)) != len(required):
            errors.append("trusted_protocol: duplicate required_evidence name")
    else:
        errors.append("trusted_protocol: malformed required_evidence name")
    return errors


def validate_manifest(manifest: object, *, trusted_protocol: object) -> list:
    """Structurally validate a candidate manifest against a trusted protocol.

    ``trusted_protocol`` is a separately supplied expected configuration; it is
    never read from the manifest.  Agreement of hashes and identities is a
    configuration comparison only and never proves protocol or owner
    authenticity.  The manifest is closed: no code text, evaluator module or
    path, thresholds, actor references, holdout/baseline selectors, statistics
    or pass/authority flags can appear.
    """
    errors: list = []
    manifest_exact = is_exact_json(manifest)
    if not manifest_exact:
        errors.append("manifest: bounded finite exact JSON required")
    errors.extend(validate_protocol(trusted_protocol))
    if errors:
        return _dedupe(errors)
    if not _closed(manifest, MANIFEST_KEYS, "manifest", errors):
        return errors
    if manifest["schema"] != MANIFEST_SCHEMA:
        errors.append("manifest: wrong schema")
    if not _candidate_id(manifest["candidate_id"]):
        errors.append("manifest: malformed candidate_id")
    for field in ("source_sha256", "config_sha256", "protocol_sha256",
                  "input_policy_sha256", "runtime_sha256", "evaluator_sha256"):
        if not _sha(manifest[field]):
            errors.append("manifest: malformed " + field)
    if manifest["morphology"] != "research_feature":
        errors.append("manifest: morphology must be exactly 'research_feature'")
    if manifest["authority"] != "display_only":
        errors.append("manifest: authority must be exactly 'display_only'")
    if not _family(manifest["trial_family"]):
        errors.append("manifest: invalid trial_family")

    lineage = manifest["lineage"]
    lineage_shaped = type(lineage) is dict and set(lineage) == LINEAGE_KEYS
    if _closed(lineage, LINEAGE_KEYS, "manifest.lineage", errors):
        if not _opaque_id(lineage["original_root_id"]):
            errors.append("manifest.lineage: malformed original_root_id")
        parent = lineage["parent_candidate_id"]
        if parent is not None and not _candidate_id(parent):
            errors.append("manifest.lineage: malformed parent_candidate_id")
        if parent is not None and parent == manifest["candidate_id"]:
            errors.append("manifest.lineage: candidate cannot be its own parent")
        generation = lineage["refinement_generation"]
        if type(generation) is not int or isinstance(generation, bool):
            errors.append("manifest.lineage: refinement_generation must be an exact int")
        elif not 0 <= generation <= 2:
            errors.append("manifest.lineage: refinement_generation outside 0..2")
        elif generation > 0 and parent is None:
            errors.append("manifest.lineage: generation>0 requires parent_candidate_id")
        elif generation == 0 and parent is not None:
            errors.append("manifest.lineage: lineage reset refused for generation 0 with parent")

    trusted = trusted_protocol
    for field in ("protocol_sha256", "input_policy_sha256", "runtime_sha256",
                  "evaluator_sha256"):
        if manifest[field] != trusted[field]:
            errors.append("manifest: " + field + " does not match trusted protocol")
    if manifest["trial_family"] != trusted["trial_family"]:
        errors.append("manifest: trial_family does not match trusted protocol")
    if lineage_shaped and lineage["original_root_id"] != trusted["original_root_id"]:
        errors.append("manifest.lineage: original_root_id does not match trusted protocol")
    return _dedupe(errors)
