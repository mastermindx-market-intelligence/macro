"""Regime outlook verdict mapping — loader, hash and lint (display research).

The mapping in ``config/regime_outlook_mapping_v1.json`` is the machine form of
Appendix A of
``research/macro_regime_intelligence/STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md``.
It says which already-published owner verdict each path condition reads, and
which owner tokens count as fitting, not fitting, or not telling the paths
apart.

It is an authored vocabulary. It was never tested against outcomes, and it
produces no rank, gate, size or forecast. This module only loads the file,
hashes it, and checks that it is internally consistent; it reads no market
artifact and takes no clock.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MAPPING_VERSION = "VERDICT_MAPPING_V1"
MAPPING_PATH = Path(__file__).resolve().parents[1] / "config" / "regime_outlook_mapping_v1.json"

READINGS = ("fits", "does_not_fit", "not_discriminating", "unknown")
FAMILY_READINGS = ("fits", "does_not_fit", "mixed", "not_discriminating", "unknown")
VERDICT_CLASSES = ("banded", "composite")
FIELD_KINDS = ("categorical", "market_pricing")
CLOCK_SEMANTICS = (
    "source_observation_date",
    "owner_snapshot_date",
    "release_schedule_date",
    "authored_date",
    "unknown",
)
OPEN_REASONS = (
    "no_admitted_owner_field",
    "no_owner_verdict",
    "sign_only_verdict",
    "vocabulary_not_audited",
    "unknown_date",
)
FAMILY_COVERAGE = ("admitted", "evidence_only", "no_owner")
PATH_FAMILIES = ("rates", "market_structure")

# The part of the file a reading depends on. A change under any of these keys
# is a new mapping version; a change to the note, the artifact list or the
# evidence-only list is not.
READING_TABLE_KEYS = ("fields", "paths", "families", "retired_condition_ids")
_TOKEN_COLUMNS = ("fits", "does_not_fit", "not_discriminating")


def load_mapping(path: Path | None = None) -> dict[str, Any]:
    """Return the mapping, refusing a file that names another version."""
    source = MAPPING_PATH if path is None else Path(path)
    mapping = json.loads(source.read_text(encoding="utf-8"))
    found = mapping.get("mapping_version")
    if found != MAPPING_VERSION:
        raise ValueError(f"{source} is mapping version {found!r}, not {MAPPING_VERSION!r}")
    return mapping


def mapping_sha256(path: Path | None = None) -> str:
    """sha256 of the mapping file's bytes — the value recorded beside the version."""
    source = MAPPING_PATH if path is None else Path(path)
    return hashlib.sha256(source.read_bytes()).hexdigest()


def reading_table_sha256(mapping: dict[str, Any]) -> str:
    """sha256 of the reading table alone, independent of notes and layout."""
    table = {key: mapping[key] for key in READING_TABLE_KEYS}
    canonical = json.dumps(table, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _row_key(condition: dict[str, Any]) -> tuple[str, str, str]:
    fits, does_not_fit, middle = (json.dumps(condition[column], sort_keys=True) for column in _TOKEN_COLUMNS)
    return fits, does_not_fit, middle


def lint_mapping(mapping: dict[str, Any]) -> list[str]:
    """Every way the mapping breaks its own rules; an empty list means clean.

    The rules (contract Appendix A, rule R-H):

    * a condition id is used once and a retired id is never reused;
    * a condition's family exists and equals its field's family;
    * the ``not_discriminating`` tokens are exactly the field's middle tokens,
      so a middle reading can never be authored into a side;
    * every token is one the owner publishes;
    * two conditions on one field are either the same row or its mirror, and
      they share a statement id exactly when they are the same row — one field
      cannot be read two inconsistent ways by two paths;
    * a condition with no admitted field authors no token and says why.
    """
    errors: list[str] = []

    if mapping.get("mapping_version") != MAPPING_VERSION:
        errors.append(f"mapping_version is {mapping.get('mapping_version')!r}")
    if tuple(mapping.get("readings", ())) != READINGS:
        errors.append("readings differ from the closed list")
    if tuple(mapping.get("family_readings", ())) != FAMILY_READINGS:
        errors.append("family_readings differ from the closed list")

    families: set[str] = set()
    for family in mapping["families"]:
        family_id = family["evidence_family_id"]
        if family_id in families:
            errors.append(f"{family_id}: family listed twice")
        families.add(family_id)
        if family["coverage"] not in FAMILY_COVERAGE:
            errors.append(f"{family_id}: coverage {family['coverage']!r} is not in the closed list")

    fields: dict[str, dict[str, Any]] = {}
    for field in mapping["fields"]:
        field_id = field["field_id"]
        if field_id in fields:
            errors.append(f"{field_id}: field listed twice")
        fields[field_id] = field
        if field["evidence_family_id"] not in families:
            errors.append(f"{field_id}: family not in A.0")
        if field["verdict_class"] not in VERDICT_CLASSES:
            errors.append(f"{field_id}: verdict_class {field['verdict_class']!r} is not in the closed list")
        if field["kind"] not in FIELD_KINDS:
            errors.append(f"{field_id}: kind {field['kind']!r} is not in the closed list")
        if field["clock"]["semantics"] not in CLOCK_SEMANTICS:
            errors.append(f"{field_id}: clock semantics {field['clock']['semantics']!r} is not in the closed list")
        if field["artifact"] not in mapping["artifacts"]:
            errors.append(f"{field_id}: artifact {field['artifact']!r} is not declared")

    retired = set(mapping["retired_condition_ids"])
    seen: set[str] = set()
    by_field: dict[str, list[dict[str, Any]]] = {}
    for path in mapping["paths"]:
        if path["family"] not in PATH_FAMILIES:
            errors.append(f"{path['path_id']}: family {path['family']!r} is not in the closed list")
        for condition in path["conditions"]:
            condition_id = condition["condition_id"]
            if condition_id in seen or condition_id in retired:
                errors.append(f"{condition_id}: duplicate or retired id")
            seen.add(condition_id)
            if condition["evidence_family_id"] not in families:
                errors.append(f"{condition_id}: family not in A.0")
            if not condition["rationale"]:
                errors.append(f"{condition_id}: no rationale")

            if condition["field_id"] is None:
                authored = any(condition[column] for column in _TOKEN_COLUMNS)
                if authored or condition["open_reason"] not in OPEN_REASONS:
                    errors.append(f"{condition_id}: open row authors a token or lacks a reason")
                continue

            if condition["open_reason"] is not None:
                errors.append(f"{condition_id}: a read row carries an open reason")
            field = fields.get(condition["field_id"])
            if field is None:
                errors.append(f"{condition_id}: field {condition['field_id']!r} is not admitted")
                continue
            if condition["evidence_family_id"] != field["evidence_family_id"]:
                errors.append(f"{condition_id}: family differs from its field's")
            if condition["not_discriminating"] != field["middle_tokens"]:
                errors.append(
                    f"{condition_id}: not_discriminating {condition['not_discriminating']} "
                    f"is not the field's middle {field['middle_tokens']}"
                )
            if not condition["fits"] or not condition["does_not_fit"]:
                errors.append(f"{condition_id}: a read row needs both a fitting and a not-fitting side")
            if isinstance(field["tokens"], list):
                # a categorical owner field; a numeric field is compared by
                # operator and has no token list to check against
                for column in _TOKEN_COLUMNS:
                    for token in condition[column]:
                        if token not in field["tokens"]:
                            errors.append(f"{condition_id}: {token!r} not an owner token")
            by_field.setdefault(condition["field_id"], []).append(condition)

    for field_id, rows in by_field.items():
        first = rows[0]
        base = _row_key(first)
        for condition in rows[1:]:
            key = _row_key(condition)
            same = key == base
            mirror = key == (base[1], base[0], base[2])
            if not (same or mirror):
                errors.append(
                    f"{condition['condition_id']}: neither identical to nor a mirror of "
                    f"{first['condition_id']} on {field_id}"
                )
            if same != (condition["statement_id"] == first["statement_id"]):
                errors.append(
                    f"{condition['condition_id']}: statement_id identity disagrees with row identity "
                    f"vs {first['condition_id']}"
                )
    return errors
