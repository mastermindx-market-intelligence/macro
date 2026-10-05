"""Retain reference manifests for facts actually rendered by the native owner.

This is message metadata, not a fact store or a historical resolver. Values,
answer prose, model reasoning and source documents never enter the manifest.
No reader may infer current rights or retained source bytes from a fingerprint.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

SCHEMA = "brain.native_input_manifest.v1"
MAX_RECEIPT_BYTES = 262144
MAX_MANIFEST_BYTES = 65536
MAX_INPUTS = 32
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_FIELD = re.compile(r"[a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+\Z")
_STATUS = {"available", "unknown", "unavailable", "stale", "not_applicable", "rights_blocked"}
_SOURCE = ("source_id", "owner", "license_class", "dataset_id", "source_family", "delay", "artifact_id")
_PROVENANCE = ("kind", "owner_field_key", "formula_version", "field_lineage", "basis", "relationship", "owner_artifact", "alias_interpretation")


def _json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _string(value: Any, limit: int = 512, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not 1 <= len(value) <= limit:
        raise ValueError("invalid reference scalar")
    return value


def _entity(value: Any) -> dict:
    if not isinstance(value, dict) or value.get("type") not in {"security", "industry"}:
        raise ValueError("invalid entity")
    return {"type": value["type"], "id": _string(value.get("id"), 160)}


def _metadata(value: Any, keys: tuple[str, ...], required: tuple[str, ...]) -> dict:
    if not isinstance(value, dict) or not all(key in value for key in required):
        raise ValueError("missing owner metadata")
    return {key: _string(value[key], nullable=key not in required) for key in keys if key in value}


def retain_native_input_manifest(receipt: Any) -> dict:
    """Project one server native receipt atomically; a bad field loses no answer.

    The native executor includes only rendered typed facts in `facts`. Relationship
    failures remain disclosed as outside that census, never manufactured as facts.
    Hashes bind the exact owner receipt; they do not promise historical retrieval.
    """
    result: dict = {"schema": SCHEMA, "scope": "native_fact_answer",
                    "status": "unavailable", "source_retention": "references_only"}
    try:
        if not isinstance(receipt, dict) or receipt.get("schema") != "brain.native_fact_receipt.v1":
            raise ValueError("invalid native receipt")
        encoded = _json(receipt)
        if len(encoded) > MAX_RECEIPT_BYTES:
            return {**result, "reason": "receipt_too_large"}
        facts = receipt.get("facts")
        if not isinstance(facts, list) or len(facts) > MAX_INPUTS:
            raise ValueError("invalid fact census")
        inputs, seen = [], set()
        for fact in facts:
            if not isinstance(fact, dict):
                raise ValueError("invalid fact")
            field = _string(fact.get("field_id"), 160)
            fingerprint = _string(fact.get("fact_fingerprint"), 64)
            registry = _string(fact.get("registry_digest"), 64)
            entity = _entity(fact.get("entity"))
            key = (entity["type"], entity["id"], field)
            if (not _FIELD.fullmatch(field) or not _HASH.fullmatch(fingerprint)
                    or not _HASH.fullmatch(registry) or key in seen
                    or fact.get("status") not in _STATUS
                    or registry != receipt.get("registry_digest")):
                raise ValueError("inconsistent fact reference")
            seen.add(key)
            inputs.append({"entity": entity, "field_id": field, "fact_fingerprint": fingerprint,
                           "registry_digest": registry, "status": fact["status"],
                           "reason_code": _string(fact.get("reason_code"), 96, nullable=True),
                           "unit": _string(fact.get("unit"), 32),
                           **{key: _string(fact.get(key), 64, nullable=True)
                              for key in ("observed_at", "effective_at", "as_of")},
                           "source": _metadata(fact.get("source"), _SOURCE, ("source_id", "owner", "license_class")),
                           "provenance": _metadata(fact.get("provenance"), _PROVENANCE, ("kind", "owner_field_key"))})
        record = {**result, "status": "retained", "coverage": "rendered_typed_facts_only",
                  "native_receipt_sha256": hashlib.sha256(encoded).hexdigest(),
                  "planner_version": _string(receipt.get("planner_version"), 96),
                  "registry_digest": _string(receipt.get("registry_digest"), 64),
                  "inputs": inputs,
                  "relationship_payload_recorded": False,
                  "relationship_present": receipt.get("relationship_receipt") is not None,
                  "owner_failure_present": bool(receipt.get("failure") or receipt.get("rank_resolution_failure"))}
        if len(_json(record)) > MAX_MANIFEST_BYTES:
            return {**result, "reason": "manifest_too_large"}
        return record
    except (TypeError, ValueError, OverflowError, RecursionError):
        return {**result, "reason": "invalid_native_receipt"}
