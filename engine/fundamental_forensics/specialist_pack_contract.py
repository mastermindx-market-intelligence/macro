"""Specialist pack result contract: envelope + per-pack catalogues.

Pure validator. No pack evaluation, mapping, or source I/O beyond reading the
JSON contract files under contracts/. Third-party imports are jsonschema and,
when present, referencing (yaml is permitted but unused).
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.validators import RefResolver

try:
    from referencing import Registry, Resource
    import referencing.jsonschema
    _HAS_REFERENCING = True
except ImportError:
    _HAS_REFERENCING = False


PACK_IDS = (
    "PK01",
    "PK02",
    "PK03",
    "PK04",
    "PK05",
    "PK06",
    "PK07",
    "PK08",
    "PK09",
    "PK10",
    "PK11",
    "PK12",
)

NUMERIC_TYPES = frozenset({"decimal", "integer", "ratio", "shares"})
NON_NUMERIC_TYPES = frozenset(
    {"text", "enum", "boolean", "duration_iso8601", "axis_member"}
)
QUALITY_COVERAGE_KEYS = (
    ("valued", "valued_fields"),
    ("missing", "missing_fields"),
    ("unsupported", "unsupported_fields"),
    ("not_evaluable", "not_evaluable_fields"),
    ("not_applicable", "not_applicable_fields"),
)
QUALITY_TO_COVERAGE = dict(QUALITY_COVERAGE_KEYS)
ABSENCE_STATES = frozenset(key for key, _ in QUALITY_COVERAGE_KEYS if key != "valued")

_CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
_ENVELOPE_PATH = _CONTRACTS / "specialist_pack_result.v1.schema.json"
_CATALOGUE_PATH = _CONTRACTS / "specialist_pack_catalogue.v1.schema.json"
_PACK_DIR = _CONTRACTS / "specialist_packs"
_PACKET_SCHEMA_PATH = _CONTRACTS / "financial_intelligence_packet.schema.json"


@lru_cache(maxsize=None)
def _read_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} is not a JSON object")
    return payload


def _load_json(path: Path) -> dict[str, Any]:
    return deepcopy(_read_json(str(path)))


def load_envelope_schema() -> dict[str, Any]:
    return _load_json(_ENVELOPE_PATH)


def load_catalogue_schema() -> dict[str, Any]:
    return _load_json(_CATALOGUE_PATH)


def load_pack_schema(pack_id: str) -> dict[str, Any]:
    if pack_id not in PACK_IDS:
        raise KeyError(f"unknown pack_id: {pack_id}")
    return _load_json(_PACK_DIR / f"pack.{pack_id.lower()}.v1.schema.json")


def pack_schema_digest(pack_id: str) -> str:
    schema = load_pack_schema(pack_id)
    payload = json.dumps(
        schema, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return sha256(payload).hexdigest()


def pack_content_digest(obj: Mapping) -> str:
    """Lowercase sha256 hex of the result with ``pack_content_sha256`` omitted.

    Canonical bytes are ``json.dumps(<obj without pack_content_sha256>,
    sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")``.
    ``validate_pack_result`` requires ``pack_content_sha256`` to equal this digest.
    """
    body = {key: value for key, value in obj.items() if key != "pack_content_sha256"}
    payload = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _error_path(error: Any) -> str:
    parts = list(error.absolute_path)
    return ".".join(str(part) for part in parts) if parts else "<root>"


def _envelope_validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    packet = _load_json(_PACKET_SCHEMA_PATH)
    if _HAS_REFERENCING:
        registry = Registry()
        for contents in (schema, packet):
            resource = Resource.from_contents(
                contents,
                default_specification=referencing.jsonschema.DRAFT202012,
            )
            registry = registry.with_resource(contents["$id"], resource)
        return Draft202012Validator(schema, registry=registry)
    store = {
        schema["$id"]: schema,
        packet["$id"]: packet,
    }
    resolver = RefResolver(base_uri=str(schema["$id"]), referrer=schema, store=store)
    return Draft202012Validator(schema, resolver=resolver)


def _mapping_rows(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _row_semantic_errors(fields: list[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    for index, row in enumerate(fields):
        row_type = row.get("type")
        value = row.get("value")
        text_value = row.get("text_value")
        quality_state = row.get("quality_state")
        non_value_state = row.get("non_value_state")
        if row_type in NUMERIC_TYPES and text_value is not None:
            errors.append(
                f"fields.{index}.text_value: numeric type requires text_value to be null"
            )
        if row_type in NON_NUMERIC_TYPES and value is not None:
            errors.append(
                f"fields.{index}.value: non-numeric type requires value to be null"
            )
        if quality_state == "valued":
            if row_type in NUMERIC_TYPES and value is None:
                errors.append(
                    f"fields.{index}.value: valued row requires a non-null value"
                )
            if row_type in NON_NUMERIC_TYPES and text_value is None:
                errors.append(
                    f"fields.{index}.text_value: valued row requires a non-null text_value"
                )
            if non_value_state is not None:
                errors.append(
                    f"fields.{index}.non_value_state: valued row requires non_value_state to be null"
                )
        elif quality_state in ABSENCE_STATES:
            if value is not None:
                errors.append(
                    f"fields.{index}.value: typed absence requires value to be null"
                )
            if text_value is not None:
                errors.append(
                    f"fields.{index}.text_value: typed absence requires text_value to be null"
                )
            if non_value_state != quality_state:
                errors.append(
                    f"fields.{index}.non_value_state: typed absence requires non_value_state to equal quality_state"
                )
    return errors


def _evidence_errors(
    fields: list[Mapping[str, Any]], checks: list[Mapping[str, Any]]
) -> list[str]:
    errors: list[str] = []
    field_ids = {
        row.get("field_id")
        for row in fields
        if isinstance(row.get("field_id"), str)
    }
    for index, row in enumerate(fields):
        if row.get("quality_state") == "valued":
            kind = row.get("evidence_kind")
            if kind == "xbrl_fact":
                ids = row.get("source_occurrence_ids")
                if not isinstance(ids, list) or not ids:
                    errors.append(
                        f"fields.{index}.source_occurrence_ids: valued xbrl_fact requires a non-empty list"
                    )
                if row.get("concept") is None:
                    errors.append(
                        f"fields.{index}.concept: valued xbrl_fact requires a non-null concept"
                    )
            elif kind == "text_span":
                span = row.get("source_span")
                if not isinstance(span, Mapping):
                    errors.append(
                        f"fields.{index}.source_span: valued text_span requires a source_span object"
                    )
                else:
                    start = span.get("start_offset")
                    end = span.get("end_offset")
                    if start is None:
                        errors.append(
                            f"fields.{index}.source_span: valued text_span requires a non-null start_offset"
                        )
                    if end is None:
                        errors.append(
                            f"fields.{index}.source_span: valued text_span requires a non-null end_offset"
                        )
                    if (
                        isinstance(start, int)
                        and isinstance(end, int)
                        and not end > start
                    ):
                        errors.append(
                            f"fields.{index}.source_span: valued text_span requires end_offset > start_offset"
                        )
            elif kind == "table_cell":
                cell = row.get("table_cell")
                if not isinstance(cell, Mapping):
                    errors.append(
                        f"fields.{index}.table_cell: valued table_cell requires a table_cell object"
                    )
                elif cell.get("table_id") is None:
                    errors.append(
                        f"fields.{index}.table_cell: valued table_cell requires a non-null table_id"
                    )
            elif kind == "formula":
                if row.get("formula_rule_id") is None:
                    errors.append(
                        f"fields.{index}.formula_rule_id: valued formula requires a non-null formula_rule_id"
                    )
                deps = row.get("dependency_field_ids")
                if not isinstance(deps, list) or not deps:
                    errors.append(
                        f"fields.{index}.dependency_field_ids: valued formula requires a non-empty list"
                    )
        deps = row.get("dependency_field_ids")
        if isinstance(deps, list):
            for dep in deps:
                if dep not in field_ids:
                    errors.append(
                        f"fields.{index}.dependency_field_ids: {dep!r} is not a field_id in this result"
                    )
    seen_check_ids: set[Any] = set()
    for index, check in enumerate(checks):
        check_id = check.get("check_id")
        if check_id in seen_check_ids:
            errors.append(f"checks.{index}.check_id: duplicate check_id {check_id!r}")
        else:
            seen_check_ids.add(check_id)
        evidence_ids = check.get("evidence_field_ids")
        if isinstance(evidence_ids, list):
            for field_id in evidence_ids:
                if field_id not in field_ids:
                    errors.append(
                        f"checks.{index}.evidence_field_ids: {field_id!r} is not a field_id in this result"
                    )
    return errors


def _coverage_errors(obj: Mapping[str, Any], fields: list[Mapping[str, Any]]) -> list[str]:
    errors: list[str] = []
    tallies = {key: 0 for _, key in QUALITY_COVERAGE_KEYS}
    for row in fields:
        coverage_key = QUALITY_TO_COVERAGE.get(row.get("quality_state"))
        if coverage_key is not None:
            tallies[coverage_key] += 1
    coverage = obj.get("coverage")
    if isinstance(coverage, Mapping):
        for _, key in QUALITY_COVERAGE_KEYS:
            declared = coverage.get(key)
            actual = tallies[key]
            if declared != actual:
                errors.append(f"coverage.{key}: declared {declared}, rows {actual}")
    applicability = obj.get("applicability")
    state = applicability.get("state") if isinstance(applicability, Mapping) else None
    if state != "applicable":
        for index, row in enumerate(fields):
            if row.get("quality_state") == "valued":
                errors.append(
                    f"fields.{index}.quality_state: valued row is not allowed when applicability.state is {state!r}"
                )
    return errors


def _catalogue_membership_errors(
    obj: Mapping[str, Any],
    pack_schema: Mapping[str, Any],
    fields: list[Mapping[str, Any]],
    checks: list[Mapping[str, Any]],
) -> list[str]:
    errors: list[str] = []
    catalogue_fields = {
        item.get("field_id"): item
        for item in _mapping_rows(pack_schema.get("fields"))
        if isinstance(item.get("field_id"), str)
    }
    catalogue_checks = {
        item.get("check_id"): item
        for item in _mapping_rows(pack_schema.get("checks"))
        if isinstance(item.get("check_id"), str)
    }
    present_ids: set[str] = set()
    for index, row in enumerate(fields):
        field_id = row.get("field_id")
        if isinstance(field_id, str):
            present_ids.add(field_id)
        catalogue = catalogue_fields.get(field_id)
        if catalogue is None:
            errors.append(
                f"fields.{index}.field_id: {field_id!r} is not in the pack catalogue"
            )
            continue
        if row.get("type") != catalogue.get("type"):
            errors.append(
                f"fields.{index}.type: {row.get('type')!r} does not equal catalogue type {catalogue.get('type')!r}"
            )
        catalogue_unit = catalogue.get("unit")
        if catalogue_unit is not None and row.get("unit") != catalogue_unit:
            errors.append(
                f"fields.{index}.unit: {row.get('unit')!r} does not equal catalogue unit {catalogue_unit!r}"
            )
        if row.get("quality_state") == "valued":
            allowed = catalogue.get("allowed_evidence_kinds")
            if not isinstance(allowed, list) or row.get("evidence_kind") not in allowed:
                errors.append(
                    f"fields.{index}.evidence_kind: {row.get('evidence_kind')!r} is not in allowed_evidence_kinds"
                )
    applicability = obj.get("applicability")
    app_state = applicability.get("state") if isinstance(applicability, Mapping) else None
    if app_state == "applicable":
        for item in _mapping_rows(pack_schema.get("fields")):
            if item.get("required") is True:
                field_id = item.get("field_id")
                if field_id not in present_ids:
                    errors.append(f"fields: required field_id {field_id!r} is absent")
    for index, check in enumerate(checks):
        check_id = check.get("check_id")
        if check_id not in catalogue_checks:
            errors.append(
                f"checks.{index}.check_id: {check_id!r} is not in the pack catalogue"
            )
    return errors


def catalogue_errors(pack_id: str) -> list[str]:
    """Return meta-schema errors plus duplicate catalogue field/check ids."""
    schema = load_catalogue_schema()
    pack = load_pack_schema(pack_id)
    validator = Draft202012Validator(schema)
    errors = [
        f"{_error_path(item)}: {item.message}"
        for item in sorted(validator.iter_errors(pack), key=lambda item: list(item.absolute_path))
    ]
    seen_fields: set[str] = set()
    for index, row in enumerate(_mapping_rows(pack.get("fields"))):
        field_id = row.get("field_id")
        if not isinstance(field_id, str):
            continue
        if field_id in seen_fields:
            errors.append(f"fields.{index}.field_id: duplicate field_id {field_id!r}")
        else:
            seen_fields.add(field_id)
    seen_checks: set[str] = set()
    for index, row in enumerate(_mapping_rows(pack.get("checks"))):
        check_id = row.get("check_id")
        if not isinstance(check_id, str):
            continue
        if check_id in seen_checks:
            errors.append(f"checks.{index}.check_id: duplicate check_id {check_id!r}")
        else:
            seen_checks.add(check_id)
    return errors


def validate_pack_result(obj: Any) -> list[str]:
    """Return Draft 2020-12 errors as ``path: message`` strings; empty means valid.

    Also requires ``pack_schema_digest`` to equal ``pack_schema_digest(pack_id)``,
    ``pack_schema_id`` to equal the pack file's ``pack_schema_id``, and
    ``pack_content_sha256`` to equal ``pack_content_digest(obj)``. Row semantics,
    evidence minima, coverage tallies, and specified-catalogue membership are
    enforced on the same result.
    """
    schema = load_envelope_schema()
    validator = _envelope_validator(schema)
    errors = [
        f"{_error_path(item)}: {item.message}"
        for item in sorted(validator.iter_errors(obj), key=lambda item: list(item.absolute_path))
    ]
    if not isinstance(obj, Mapping):
        return errors or ["<root>: instance is not an object"]
    pack_id = obj.get("pack_id")
    pack_schema = None
    if pack_id in PACK_IDS:
        pack_schema = load_pack_schema(pack_id)
        expected_id = pack_schema.get("pack_schema_id")
        expected_digest = pack_schema_digest(pack_id)
        given_id = obj.get("pack_schema_id")
        given_digest = obj.get("pack_schema_digest")
        if given_id != expected_id:
            errors.append(
                f"pack_schema_id: {given_id!r} does not match pack file {expected_id!r}"
            )
        if given_digest != expected_digest:
            errors.append(
                "pack_schema_digest: value does not equal the recomputed pack schema digest"
            )
    given_content = obj.get("pack_content_sha256")
    expected_content = pack_content_digest(obj)
    if given_content != expected_content:
        errors.append(
            "pack_content_sha256: value does not equal the recomputed pack content digest"
        )
    fields = _mapping_rows(obj.get("fields"))
    checks = _mapping_rows(obj.get("checks"))
    errors.extend(_row_semantic_errors(fields))
    errors.extend(_evidence_errors(fields, checks))
    errors.extend(_coverage_errors(obj, fields))
    if pack_schema is not None and pack_schema.get("catalogue_state") == "specified":
        errors.extend(_catalogue_membership_errors(obj, pack_schema, fields, checks))
    return errors
