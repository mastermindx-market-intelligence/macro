"""Declared E0 reviewer metadata, without participant reads or admission authority.

The v1 plan's global participant references remain immutable. This v2 boundary
scopes their declared metadata to a task/slot; it authenticates neither the
participant nor the origin of any supplied bytes. Only owned static schemas are
loaded. No reader, execution carrier, store or permission callback is accepted.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


PREFIX = "research_factory.market_memory_e0_"
PLAN_SCHEMA = PREFIX + "reviewer_plan.v1"
SCOPE_SCHEMA = PREFIX + "review_metadata_scope.v2"
OWNER_CONTRACT = PREFIX + "review_metadata_owner.v2"
ACTION = "read_registered_reviewer_metadata.v2"
ROLES = ("principal_ref", "qualification_ref", "independence_ref")
ROLE_SCHEMAS = {
    role: PREFIX + "reviewer_" + role.removesuffix("_ref") + "_metadata.v2"
    for role in ROLES
}
_FLAGS = (
    "authenticated", "qualification_verified", "independence_verified",
    "exposure_verified", "operational_admission",
)


class ReviewMetadataError(ValueError):
    """Stable input-free refusal; supplied data never appears in the reason."""


def _fail(reason):
    raise ReviewMetadataError(reason)


def _canonical(value, limit):
    # Bound shape before serialization; forbid Python subclasses/coercion and
    # floating-point representations of fields whose native type is integer.
    pending = [(value, 0)]
    nodes = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > 20000 or depth > 16:
            _fail("json_shape_bound")
        kind = type(item)
        if kind is dict:
            if len(item) > 512:
                _fail("json_shape_bound")
            for key, child in item.items():
                if type(key) is not str or len(key) > limit:
                    _fail("json_native_type")
                pending.append((child, depth + 1))
        elif kind is list:
            if len(item) > 512:
                _fail("json_shape_bound")
            pending.extend((child, depth + 1) for child in item)
        elif kind is str:
            if len(item) > limit:
                _fail("json_size_bound")
        elif kind is int:
            if item.bit_length() > 64:
                _fail("json_integer_bound")
        elif kind is not bool and item is not None:
            _fail("json_native_type")
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _fail("json_encoding")
    if len(encoded) > limit:
        _fail("json_size_bound")
    return encoded


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("json_duplicate_key")
        result[key] = value
    return result


def _constant(_value):
    _fail("json_nonfinite")


def _parse(raw, limit):
    if type(raw) is not bytes or not 1 <= len(raw) <= limit:
        _fail("json_bytes_bound")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                           parse_constant=_constant)
    except ReviewMetadataError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        _fail("json_encoding")
    if _canonical(value, limit) != raw:
        _fail("json_not_canonical")
    return value


@lru_cache(maxsize=2)
def _validator(plan=False):
    directory = Path(__file__).resolve().parents[2] / "contracts" / "market_memory"
    name = "e0_reviewer_plan.v1.schema.json" if plan else "e0_review_metadata.v2.schema.json"
    schema = json.loads((directory / name).read_bytes())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _validate(value, *, plan=False):
    if not _validator(plan).is_valid(value):
        _fail("reviewer_plan_schema" if plan else "metadata_schema")
    # jsonschema uses regex search: the immutable v1 `$` patterns can accept
    # a terminal LF. Enforce whole native tokens without changing that schema.
    id_fields = {
        "schema", "object_id", "study_id", "task_id", "participant_id",
        "owner_contract", "action", "attempt_id", "worker_id", "quota_class",
        "adjudicator_principal_id",
    }
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is dict:
            for key, child in item.items():
                tokens = (child,) if key in id_fields else (
                    child if key in {"reviewer_principal_ids", "declared_distinct_from"} else ())
                if any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", token) is None
                       for token in tokens):
                    _fail("metadata_token")
                if key == "provider" and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", child) is None:
                    _fail("metadata_token")
                pending.append(child)
        elif type(item) is list:
            pending.extend(item)


def _verification():
    return {flag: False for flag in _FLAGS}


def _declarations():
    return {
        "verification": _verification(),
        "native_v2_owner_read_support": "not_implemented",
        "installed_permission": "not_verified",
    }


def _match_reference(ref, raw, schema, object_id):
    if (ref["schema"] != schema or ref["object_id"] != object_id
            or ref["bytes"] != len(raw)
            or ref["sha256"] != hashlib.sha256(raw).hexdigest()):
        _fail("reference_mismatch")


def plan_review_metadata_reads(scope, reviewer_plan_bytes):
    """Return detached declared descriptors; never read or authorize a target."""
    if type(scope) is not dict:
        _fail("scope_native_type")
    scope = _parse(_canonical(scope, 8192), 8192)
    _validate(scope)
    if scope.get("schema") != SCOPE_SCHEMA:
        _fail("scope_schema")
    plan = _parse(reviewer_plan_bytes, 262144)
    _validate(plan, plan=True)
    _match_reference(scope["reviewer_plan_ref"], reviewer_plan_bytes,
                     PLAN_SCHEMA, plan["object_id"])
    if plan["study_id"] != scope["study_id"]:
        _fail("study_mismatch")
    participants = [*plan["reviewers"], plan["adjudicator"]]
    ids = [p["principal_ref"]["object_id"] for p in participants]
    digests = [p["principal_ref"]["sha256"] for p in participants]
    if len(set(ids)) != 3 or len(set(digests)) != 3:
        _fail("participants_not_distinct")
    tasks = set()
    for assignment in plan["assignments"]:
        task_id = assignment["task_id"]
        if task_id in tasks:
            _fail("duplicate_task_assignment")
        tasks.add(task_id)
        if (set(assignment["reviewer_principal_ids"]) != set(ids[:2])
                or assignment["adjudicator_principal_id"] != ids[2]):
            _fail("assignment_participant_mismatch")
    if scope["task_id"] not in tasks:
        _fail("task_not_assigned")
    # Qualify the complete closed nine-ref set before accepting ANY payload.
    seen_ids, seen_hashes, total = set(), set(), 0
    reads = []
    for position, participant in enumerate(participants):
        for role in ROLES:
            ref = participant[role]
            if ref["schema"] != ROLE_SCHEMAS[role]:
                _fail("unsupported_participant_reference")
            if type(ref["bytes"]) is not int or not 1 <= ref["bytes"] <= 8192:
                _fail("participant_reference_bound")
            if ref["object_id"] in seen_ids or ref["sha256"] in seen_hashes:
                _fail("participant_reference_not_unique")
            seen_ids.add(ref["object_id"])
            seen_hashes.add(ref["sha256"])
            total += ref["bytes"]
            reads.append({
                "study_id": scope["study_id"], "task_id": scope["task_id"],
                "slot": scope["slot"],
                "participant_role": ("reviewer_1", "reviewer_2", "adjudicator")[position],
                "participant_id": ids[position], "evidence_role": role,
                "reference": ref,
            })
    if total > 65536:
        _fail("participant_aggregate_bound")
    result = {
        "schema": PREFIX + "review_metadata_read_plan.v2",
        "authority": "display_only", "scope": scope,
        "reviewer_plan_sha256": hashlib.sha256(reviewer_plan_bytes).hexdigest(),
        "reads": reads, **_declarations(),
    }
    result["plan_sha256"] = hashlib.sha256(_canonical(result, 65536)).hexdigest()
    return result


def validate_review_metadata_payload(scope, reviewer_plan_bytes, descriptor, payload_bytes):
    """Validate supplied declared metadata; no actor or read grant is verified."""
    plan = plan_review_metadata_reads(scope, reviewer_plan_bytes)
    descriptor_bytes = _canonical(descriptor, 8192)
    if not any(descriptor_bytes == _canonical(read, 8192) for read in plan["reads"]):
        _fail("descriptor_not_in_plan")
    descriptor = _parse(descriptor_bytes, 8192)
    metadata = _parse(payload_bytes, 8192)
    _validate(metadata)
    ref = descriptor["reference"]
    if metadata["schema"] != ROLE_SCHEMAS[descriptor["evidence_role"]]:
        _fail("payload_role_mismatch")
    _match_reference(ref, payload_bytes, metadata["schema"], metadata["object_id"])
    if (metadata["study_id"] != descriptor["study_id"]
            or metadata["participant_id"] != descriptor["participant_id"]):
        _fail("payload_binding_mismatch")
    if descriptor["evidence_role"] == "independence_ref":
        others = {read["participant_id"] for read in plan["reads"]}
        others.remove(descriptor["participant_id"])
        if set(metadata["declared_distinct_from"]) != others:
            _fail("independence_participants_mismatch")
    return {
        "schema": PREFIX + "review_metadata_validation.v2",
        "authority": "display_only", "scope": plan["scope"],
        "descriptor": descriptor, "metadata": metadata, **_declarations(),
    }
