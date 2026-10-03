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

# These keys decide a reading — which file is read, which field, which tokens.
# ``note``, ``evidence_only``, ``possible_missing_as_zero`` and ``producer_pin``
# are outside because no path reading is computed from them in this version;
# the whole-file hash (``mapping_sha256``) still covers them.
READING_TABLE_KEYS = ("artifacts", "fields", "paths", "families", "retired_condition_ids")
_TOKEN_COLUMNS = ("fits", "does_not_fit", "not_discriminating")
GUARD_KINDS = (
    "default_token_needs",
    "owner_missing_token",
    "owner_publishes_null",
    "turn_watch_null",
    "credit_stress_leg",
    "component_not_degraded",
    "same_run_owner_copy",
    "sign_consistency",
)


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
    # Order-insensitive: sort each column's entries by their canonical text
    # before dumping the column. The column dump's field order inside the
    # condition's three columns is fixed (_TOKEN_COLUMNS); only the entries
    # within a column are sorted.
    def _sorted_dump(items: list[Any]) -> str:
        return json.dumps(sorted((json.dumps(item, sort_keys=True) for item in items)))

    fits, does_not_fit, middle = (_sorted_dump(condition[column]) for column in _TOKEN_COLUMNS)
    return fits, does_not_fit, middle


def _strict_token_ids(values: list[Any]) -> set[str]:
    """Type-strict token identity: json.dumps texts, so True != 1, None != 'null'."""
    return {json.dumps(value, sort_keys=True) for value in values}


def lint_mapping(mapping: dict[str, Any]) -> list[str]:
    """Every way the mapping breaks its own rules; an empty list means clean.

    The rules (contract Appendix A, rule R-H), one plain bullet each:

    * a condition id is used once and a retired id is never reused;
    * a condition's family exists and equals its field's family;
    * the ``not_discriminating`` tokens are exactly the field's middle tokens,
      so a middle reading can never be authored into a side;
    * every token is one the owner publishes (type-strict: True != 1,
      None != 'null');
    * two conditions on one field are either the same row or its mirror;
    * a condition with no admitted field authors no token and says why;
    * L1 — on a categorical read row, no token is in two of the three columns;
    * L2 — on a categorical read row, every non-None owner token is in one
      of the three columns;
    * L3 — two read rows share a ``statement_id`` exactly when they share a
      field id and a row key (checked across the whole mapping); an open
      row's ``statement_id`` is used by no other row, read or open;
    * L4 — a numeric read row's entries are {op, value} dicts with op one of
      le/ge/eq, value an int and not a bool, and together they partition the
      integers between the single le and the single ge with one eq each;
    * L5 — a ``turn_watch_null`` field is read by at most one row;
    * L6 — every guard kind is in the closed ``GUARD_KINDS`` list;
      ``default_token_needs`` has an owner-token ``default_token`` and a
      non-empty ``needs``; ``owner_missing_token`` has an owner-token
      ``missing_token``;
    * L7 — a rationale is non-empty and not whitespace only;
    * L8 — ``_row_key`` is order-insensitive: sort each column's entries
      before dumping.
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
            if not (condition["rationale"] and condition["rationale"].strip()):
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
                field_token_ids = _strict_token_ids(field["tokens"])

                # type-strict owner-token check (L0, the baseline; True != 1,
                # None != 'null')
                for column in _TOKEN_COLUMNS:
                    for token in condition[column]:
                        token_id = json.dumps(token, sort_keys=True)
                        if token_id not in field_token_ids:
                            errors.append(f"{condition_id}: {token!r} not an owner token")

                # L1 — no token is in two of the three columns
                seen_columns: dict[str, int] = {}
                for column_index, column in enumerate(_TOKEN_COLUMNS):
                    for token in condition[column]:
                        token_id = json.dumps(token, sort_keys=True)
                        if token_id in seen_columns:
                            errors.append(f"{condition_id}: token {token!r} is in two columns")
                        seen_columns[token_id] = column_index

                # L2 — every non-None owner token is in one of the three columns
                covered: set[str] = set()
                for column in _TOKEN_COLUMNS:
                    for token in condition[column]:
                        covered.add(json.dumps(token, sort_keys=True))
                for token in field["tokens"]:
                    if token is None:
                        continue
                    if json.dumps(token, sort_keys=True) not in covered:
                        errors.append(f"{condition_id}: owner token {token!r} is in no column")
            else:
                # L4 — a numeric read row's entries are {op, value} dicts and
                # together they partition the integers between one le and one ge
                all_entries: list[dict[str, Any]] = []
                malformed = False
                for column in _TOKEN_COLUMNS:
                    for entry in condition[column]:
                        all_entries.append(entry)
                for entry in all_entries:
                    if (
                        not isinstance(entry, dict)
                        or set(entry.keys()) != {"op", "value"}
                        or entry["op"] not in ("le", "ge", "eq")
                        or isinstance(entry["value"], bool)
                        or not isinstance(entry["value"], int)
                    ):
                        malformed = True
                        break
                if malformed:
                    errors.append(f"{condition_id}: numeric row has a malformed entry")
                else:
                    le_entries = [e for e in all_entries if e["op"] == "le"]
                    ge_entries = [e for e in all_entries if e["op"] == "ge"]
                    eq_values = sorted(e["value"] for e in all_entries if e["op"] == "eq")
                    if (
                        len(le_entries) != 1
                        or len(ge_entries) != 1
                        or le_entries[0]["value"] >= ge_entries[0]["value"]
                    ):
                        errors.append(f"{condition_id}: numeric row does not partition the integers")
                    else:
                        expected = list(range(le_entries[0]["value"] + 1, ge_entries[0]["value"]))
                        if eq_values != expected:
                            errors.append(f"{condition_id}: numeric row does not partition the integers")

            by_field.setdefault(condition["field_id"], []).append(condition)

    # Per-field pairwise check: identical-or-mirror, plus the (←) half of L3.
    # The (→) half lives below on the cross-field grouping by statement_id.
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

    # L3 — statement_id identity vs row identity, checked across the whole
    # mapping. The identical-or-mirror check above already lives on the
    # by_field pairwise block.
    read_rows_in_file_order: list[dict[str, Any]] = []
    all_rows_by_statement: dict[str, list[dict[str, Any]]] = {}
    for path in mapping["paths"]:
        for condition in path["conditions"]:
            all_rows_by_statement.setdefault(condition["statement_id"], []).append(condition)
            if condition["field_id"] is not None:
                read_rows_in_file_order.append(condition)

    for statement_id, group in all_rows_by_statement.items():
        for index, later in enumerate(group):
            for earlier in group[:index]:
                if (
                    later["field_id"] != earlier["field_id"]
                    or _row_key(later) != _row_key(earlier)
                ):
                    errors.append(
                        f"{later['condition_id']}: statement_id identity disagrees with row identity "
                        f"vs {earlier['condition_id']}"
                    )

    # L3-ii — an open row's statement_id is used by no other row, read or open
    for path in mapping["paths"]:
        for condition in path["conditions"]:
            if (
                condition["field_id"] is None
                and len(all_rows_by_statement[condition["statement_id"]]) > 1
            ):
                errors.append(f"{condition['condition_id']}: statement_id of an open row is reused")

    # L5 — a turn_watch_null field is read by at most one row
    for field_id, field in fields.items():
        if field.get("guard", {}).get("kind") == "turn_watch_null":
            if len(by_field.get(field_id, [])) > 1:
                errors.append(f"{field_id}: more than one row reads a turn watch")

    # L6 — guard kinds are closed; default_token_needs and owner_missing_token
    # carry an owner token and (for default_token_needs) a non-empty needs list
    for field_id, field in fields.items():
        guard = field.get("guard")
        if not guard:
            continue
        kind = guard.get("kind")
        if kind not in GUARD_KINDS:
            errors.append(f"{field_id}: guard kind {kind!r} is not in the closed list")
            continue
        if kind == "default_token_needs":
            owner_token_ids = _strict_token_ids(field["tokens"])
            if json.dumps(guard["default_token"], sort_keys=True) not in owner_token_ids:
                errors.append(f"{field_id}: guard default token is not an owner token")
            if not guard.get("needs"):
                errors.append(f"{field_id}: guard needs nothing")
        elif kind == "owner_missing_token":
            owner_token_ids = _strict_token_ids(field["tokens"])
            if json.dumps(guard["missing_token"], sort_keys=True) not in owner_token_ids:
                errors.append(f"{field_id}: guard missing token is not an owner token")

    return errors