"""Regime outlook verdict mapping — loader, hash and lint (display research).

The mapping in ``config/regime_outlook_mapping_v1.json`` is the machine form of
Appendix A of
``research/macro_regime_intelligence/STATE_PATH_AND_SCIENCE_CONTRACT_2026-10-03.md``.
It says which already-published owner verdict each path condition reads, and
which owner tokens count as fitting, not fitting, or not telling the paths
apart.

It is an authored vocabulary. It was never tested against outcomes, and it
produces no rank, gate, size or forecast. This module loads the file, hashes
it, checks that it is internally consistent, and reads the owner files a
caller hands it into those four words. It opens no market artifact itself and
takes no clock.
"""

from __future__ import annotations

import hashlib
import json
import math
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

UNREADABLE_STATUSES = ("missing", "unknown_date", "future_dated", "stale", "partial")
ADMISSION_ISSUES = (
    "missing",
    "owner_default_on_missing",
    "contains_sign_only_leg",
    "owner_sign_inconsistent",
    "owner_did_not_write",
    "partial",
    "malformed",
)


def _dedupe_keep_first(*tuples: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for tup in tuples:
        for word in tup:
            if word not in seen:
                seen.add(word)
                out.append(word)
    return tuple(out)


READING_REASONS = _dedupe_keep_first(OPEN_REASONS, ADMISSION_ISSUES, UNREADABLE_STATUSES)


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


# ---------------------------------------------------------------------------
# Reading owner verdicts into path readings.
# ---------------------------------------------------------------------------


class _AbsentType:
    """Sentinel for a failed resolution. Distinct from None (JSON null)."""

    _instance: "_AbsentType | None" = None

    def __new__(cls) -> "_AbsentType":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "ABSENT"

    def __bool__(self) -> bool:
        return False


ABSENT = _AbsentType()


def resolve(doc: Any, path: list[Any]) -> Any:
    """Walk ``path`` into ``doc``; return ABSENT on any failed step.

    A string segment requires the current value to be a dict with that key.
    A dict segment requires the current value to be a list and selects the
    one element whose entries all equal the selector's. Anything else is
    ABSENT.
    """
    if not isinstance(doc, dict):
        return ABSENT
    cur: Any = doc
    for segment in path:
        if isinstance(segment, str):
            if not isinstance(cur, dict) or segment not in cur:
                return ABSENT
            cur = cur[segment]
        elif isinstance(segment, dict):
            if not isinstance(cur, list):
                return ABSENT
            matches = [
                item
                for item in cur
                if isinstance(item, dict)
                and all(item.get(k) == v for k, v in segment.items())
            ]
            if len(matches) != 1:
                return ABSENT
            cur = matches[0]
        else:
            return ABSENT
    return cur


def finite(x: Any) -> bool:
    """True only for a non-bool int or float that is a finite number."""
    if isinstance(x, bool):
        return False
    if not isinstance(x, (int, float)):
        return False
    return math.isfinite(x)


def same(a: Any, b: Any) -> bool:
    """Strict equality that distinguishes True from 1 and None from 0."""
    return type(a) is type(b) and a == b


def _matches(entry_list: list[Any], token: Any) -> bool:
    """True when ``token`` matches one entry of a condition column."""
    for entry in entry_list:
        if isinstance(entry, dict):
            op = entry.get("op")
            value = entry.get("value")
            if isinstance(token, bool) or not isinstance(token, (int, float)):
                continue
            if op == "le" and token <= value:
                return True
            if op == "ge" and token >= value:
                return True
            if op == "eq" and token == value:
                return True
        elif same(token, entry):
            return True
    return False


def admit_fields(mapping: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return the admission verdict for every field in the mapping.

    A missing artifact, a non-dict artifact, a missing path, a None the row
    does not list as a token, a guard refusal or a token outside the row's
    owner vocabulary is refused with the matching issue word. The function
    does not compare fields or paths and never touches the mapping or the
    artifacts in place.
    """
    fields = mapping["fields"]
    out: dict[str, dict[str, Any]] = {}
    for field in fields:
        field_id = field["field_id"]
        artifact_letter = field["artifact"]
        artifact_doc = artifacts.get(artifact_letter)
        if not isinstance(artifact_doc, dict):
            out[field_id] = {"admitted": False, "token": None, "issue": "missing"}
            continue

        token = resolve(artifact_doc, field["path"])
        if token is ABSENT:
            out[field_id] = {"admitted": False, "token": None, "issue": "missing"}
            continue

        if token is None:
            tokens_field = field.get("tokens")
            if not (isinstance(tokens_field, list) and None in tokens_field):
                out[field_id] = {"admitted": False, "token": None, "issue": "missing"}
                continue

        if field["kind"] == "market_pricing":
            if not (isinstance(token, int) and not isinstance(token, bool)):
                out[field_id] = {"admitted": False, "token": None, "issue": "malformed"}
                continue

        guard = field["guard"]
        kind = guard["kind"]
        issue: str | None = None

        if kind == "default_token_needs":
            if same(token, guard["default_token"]):
                ok = True
                for need_path in guard["needs"]:
                    if not finite(resolve(artifact_doc, need_path)):
                        ok = False
                        break
                if not ok:
                    issue = "owner_default_on_missing"
        elif kind == "owner_publishes_null":
            if token is None:
                issue = "missing"
        elif kind == "owner_missing_token":
            if same(token, guard["missing_token"]):
                issue = "missing"
        elif kind == "turn_watch_null":
            if token is None:
                status_val = resolve(artifact_doc, guard["status_path"])
                qualified_val = resolve(artifact_doc, guard["qualified_path"])
                status_ok = status_val == guard["status_required"]
                qualified_ok = qualified_val is True
                needs_ok = True
                for need_path in guard["needs"]:
                    if not finite(resolve(artifact_doc, need_path)):
                        needs_ok = False
                        break
                if not (status_ok and qualified_ok and needs_ok):
                    issue = "owner_default_on_missing"
        elif kind == "credit_stress_leg":
            if token is not True and token is not False:
                issue = "malformed"
            else:
                z = resolve(artifact_doc, guard["hy_oas_z_path"])
                n = resolve(artifact_doc, guard["nfci_path"])
                z_finite = finite(z)
                n_finite = finite(n)
                if token is True:
                    admitted = (z_finite and z > 1.00) or (n_finite and n < 0)
                else:
                    admitted = z_finite and n_finite and n < 0
                if not admitted:
                    if z_finite and n_finite:
                        issue = "contains_sign_only_leg"
                    else:
                        issue = "owner_default_on_missing"
        elif kind == "component_not_degraded":
            degraded_val = resolve(artifact_doc, guard["degraded_path"])
            if degraded_val is not False:
                issue = "partial"
        elif kind == "same_run_owner_copy":
            other_doc = artifacts.get(guard["copy_artifact"])
            copy_val = resolve(other_doc, guard["copy_path"])
            own_clock = resolve(artifact_doc, guard["own_clock_path"])
            copy_clock = resolve(other_doc, guard["copy_clock_path"])
            present_ok = copy_val is not ABSENT and copy_val is not None
            own_clock_ok = isinstance(own_clock, str) and len(own_clock) > 0
            copy_clock_ok = isinstance(copy_clock, str) and len(copy_clock) > 0
            clocks_equal = own_clock_ok and copy_clock_ok and own_clock == copy_clock
            if not (present_ok and own_clock_ok and copy_clock_ok and clocks_equal):
                issue = guard["fail_issue"]
        elif kind == "sign_consistency":
            other = resolve(artifact_doc, guard["other_path"])
            if not finite(other) or not (token * other <= 0):
                issue = guard["fail_issue"]

        if issue is not None:
            out[field_id] = {"admitted": False, "token": None, "issue": issue}
            continue

        tokens_field = field.get("tokens")
        if isinstance(tokens_field, list):
            if not any(same(token, entry) for entry in tokens_field):
                out[field_id] = {"admitted": False, "token": None, "issue": "malformed"}
                continue

        out[field_id] = {"admitted": True, "token": token, "issue": None}
    return out


def roll_up(readings: list[str]) -> str:
    """Reduce one family's condition readings to one family reading word.

    Members outside READINGS raise ValueError. ``unknown`` and
    ``not_discriminating`` are ignored; what remains decides the roll-up.
    An empty family rolls to ``unknown`` unless a member was
    ``not_discriminating``, in which case it rolls to ``not_discriminating``.
    """
    for r in readings:
        if r not in READINGS:
            raise ValueError(f"reading {r!r} is not one of {READINGS}")
    kept = [r for r in readings if r == "fits" or r == "does_not_fit"]
    fits = sum(1 for r in kept if r == "fits")
    does_not_fit = sum(1 for r in kept if r == "does_not_fit")
    if fits and does_not_fit:
        return "mixed"
    if fits:
        return "fits"
    if does_not_fit:
        return "does_not_fit"
    if any(r == "not_discriminating" for r in readings):
        return "not_discriminating"
    return "unknown"


def read_paths(
    mapping: dict[str, Any],
    artifacts: dict[str, Any],
    *,
    unreadable: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Read every path condition and roll it up by evidence family.

    Returns one dict per authored path, in the mapping's order, each with
    the keys ``path_id``, ``family``, ``conditions`` and ``family_readings``
    and nothing else. ``unreadable`` maps a field id to a clock status; a
    key that is not a field id or a value outside UNREADABLE_STATUSES raises
    ValueError before anything is read. The function never orders paths by
    a reading and never totals them.
    """
    field_ids = {f["field_id"] for f in mapping["fields"]}
    if unreadable:
        for fid, status in unreadable.items():
            if fid not in field_ids:
                raise ValueError(f"unknown field_id {fid!r} in unreadable")
            if status not in UNREADABLE_STATUSES:
                raise ValueError(
                    f"unreadable status {status!r} for {fid!r} is not in {UNREADABLE_STATUSES}"
                )

    admissions = admit_fields(mapping, artifacts)

    result: list[dict[str, Any]] = []
    for path in mapping["paths"]:
        conditions: list[dict[str, Any]] = []
        for cond in path["conditions"]:
            row: dict[str, Any] = {
                "condition_id": cond["condition_id"],
                "statement_id": cond["statement_id"],
                "field_id": cond["field_id"],
                "reading": None,
                "reason": None,
            }
            fid = cond["field_id"]
            if fid is None:
                row["reading"] = "unknown"
                row["reason"] = cond["open_reason"]
            elif unreadable is not None and fid in unreadable:
                row["reading"] = "unknown"
                row["reason"] = unreadable[fid]
            else:
                admission = admissions[fid]
                if not admission["admitted"]:
                    row["reading"] = "unknown"
                    row["reason"] = admission["issue"]
                else:
                    token = admission["token"]
                    reading: str | None = None
                    for column in _TOKEN_COLUMNS:
                        if _matches(cond[column], token):
                            reading = column
                            break
                    if reading is None:
                        row["reading"] = "unknown"
                        row["reason"] = "malformed"
                    else:
                        row["reading"] = reading
                        row["reason"] = None
            conditions.append(row)

        family_order: list[str] = []
        family_readings_map: dict[str, list[str]] = {}
        for cond_in, cond_out in zip(path["conditions"], conditions):
            fam = cond_in["evidence_family_id"]
            if fam not in family_readings_map:
                family_order.append(fam)
                family_readings_map[fam] = []
            family_readings_map[fam].append(cond_out["reading"])
        family_rows = [
            {"evidence_family_id": fam, "reading": roll_up(family_readings_map[fam])}
            for fam in family_order
        ]

        result.append(
            {
                "path_id": path["path_id"],
                "family": path["family"],
                "conditions": conditions,
                "family_readings": family_rows,
            }
        )
    return result
