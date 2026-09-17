"""Closed complete-member observations projected from one Group Pulse invocation.

This module is deliberately pure: it acquires no data, chooses no membership, owns no
clock or state machine, and grants no rank, gate, size, alert, Prophet, or trade authority.
It serializes the exact per-member intermediates already held by ``engine.group_pulse``.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha256
import math
import re
from typing import Any, Mapping, Sequence

import pandas as pd

from engine.company_intelligence.contracts import (
    ContractError,
    canonical_json_sha256,
    iso_timestamp,
    parse_date,
)
from lib.dataos.nulls import MissingReason

SCHEMA = "group_member_observations.v1"
AUTHORITY = "context_only"
GROUP_KIND = "curated_basket"

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")
_TOP_KEYS = frozenset({
    "schema", "authority", "as_of", "generated_at", "source", "groups",
    "projection_digest",
})
_SOURCE_KEYS = frozenset({"legacy_pulse_sha256", "legacy_pulse_bytes", "receipts"})
_RECEIPT_KEYS = frozenset({
    "kind", "source_ref", "sha256", "bytes", "effective_at", "basis",
})
_GROUP_KEYS = frozenset({
    "group_id", "group_kind", "source_membership_ref", "source_membership_digest",
    "member_count", "member_keys", "members", "metrics", "legacy_pulse_digest",
    "coverage_details",
})
_MEMBER_KEYS = frozenset({"member_key", "source_symbol", "identity_ref", "metrics"})
_CELL_KEYS = frozenset({
    "value", "null_reason", "estimability_reason", "recipe_id", "effective_at",
    "source_ref", "observations_available", "observations_required",
    "included_in_aggregate",
})
_METRIC_KEYS = frozenset({
    "recipe_id", "unit", "basis", "benchmark_ref", "window",
    "minimum_observations", "membership_digest", "observed_member_keys",
    "excluded_members", "numerator_member_keys", "numerator", "denominator",
    "value", "null_reason", "cohort_digest",
})
_EXCLUDED_KEYS = frozenset({"member_key", "null_reason", "estimability_reason"})
_COVERAGE_KEYS = frozenset({"catalogue_member_count", "metrics"})
_COVERAGE_METRIC_KEYS = frozenset({"observed", "excluded"})

_METRIC_DEFS = {
    "legacy_activity": {
        "recipe_id": "group_pulse.legacy_activity.v1",
        "unit": "fraction",
        "basis": "absolute_spy_adjusted_activity",
        "benchmark_ref": "SPY",
        "window": 63,
        "minimum_observations": 63,
    },
    "legacy_trend_50": {
        "recipe_id": "group_pulse.legacy_trend_50.v1",
        "unit": "fraction",
        "basis": "activity_conditioned_total_return_close",
        "benchmark_ref": None,
        "window": 50,
        "minimum_observations": 25,
    },
    "legacy_trend_200": {
        "recipe_id": "group_pulse.legacy_trend_200.v1",
        "unit": "fraction",
        "basis": "activity_conditioned_total_return_close",
        "benchmark_ref": None,
        "window": 200,
        "minimum_observations": 100,
    },
}


def projection_digest(bundle: Mapping[str, Any]) -> str:
    """Digest the complete bundle with the self field excluded."""
    unsigned = {key: value for key, value in bundle.items() if key != "projection_digest"}
    return canonical_json_sha256(unsigned)


def _date(value: object, *, field: str) -> str:
    return parse_date(value, field=field).isoformat()


def _timestamp(value: object, *, field: str) -> str:
    parsed = iso_timestamp(value)
    if parsed is None:
        raise ContractError(f"{field} must be an ISO timestamp")
    return parsed


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _frame_value(frame: Any, as_of: pd.Timestamp, member: str) -> Any:
    try:
        return frame.at[as_of, member]
    except (AttributeError, KeyError, TypeError):
        return None


def _valid_close(value: object) -> bool:
    return _finite(value) and float(value) > 0.0


def _available_closes(panel: Mapping[str, Any], as_of: pd.Timestamp,
                      member: str, window: int) -> int:
    closes = panel.get("closes")
    try:
        series = closes.loc[:as_of, member].tail(window)
    except (AttributeError, KeyError, TypeError):
        return 0
    return sum(1 for value in series.tolist() if _valid_close(value))


def _activity_observations(panel: Mapping[str, Any], as_of: pd.Timestamp,
                           member: str) -> int:
    closes = panel.get("closes")
    try:
        values = closes.loc[:as_of, member].tail(64).tolist()
    except (AttributeError, KeyError, TypeError):
        return 0
    count = 0
    for before, after in zip(values, values[1:]):
        if _valid_close(before) and _valid_close(after):
            count += 1
    return count


def _normalise_receipts(receipts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(receipts):
        if not isinstance(raw, Mapping) or set(raw) != _RECEIPT_KEYS:
            raise ContractError(f"source_receipts[{index}] fields mismatch")
        kind = raw.get("kind")
        if kind not in {"raw_bytes", "normalized_frame"}:
            raise ContractError(f"source_receipts[{index}].kind invalid")
        source_ref = raw.get("source_ref")
        basis = raw.get("basis")
        digest = raw.get("sha256")
        byte_count = raw.get("bytes")
        if not isinstance(source_ref, str) or not source_ref:
            raise ContractError(f"source_receipts[{index}].source_ref invalid")
        if not isinstance(basis, str) or not basis:
            raise ContractError(f"source_receipts[{index}].basis invalid")
        if not isinstance(digest, str) or not _SHA_RE.fullmatch(digest):
            raise ContractError(f"source_receipts[{index}].sha256 invalid")
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count < 0:
            raise ContractError(f"source_receipts[{index}].bytes invalid")
        effective_at = _date(raw.get("effective_at"), field=f"source_receipts[{index}].effective_at")
        out.append({
            "kind": kind,
            "source_ref": source_ref,
            "sha256": digest,
            "bytes": byte_count,
            "effective_at": effective_at,
            "basis": basis,
        })
    if not out:
        raise ContractError("source_receipts must not be empty")
    return out


def _missing_detail(panel: Mapping[str, Any], as_of: pd.Timestamp, member: str,
                    *, observed: bool, required: int, legacy_conditioned: bool) -> tuple[str, str | None]:
    close = _frame_value(panel.get("closes"), as_of, member)
    if not _valid_close(close):
        return MissingReason.NO_COVERAGE.value, "missing_effective_observation"
    available = (_activity_observations(panel, as_of, member)
                 if required == 63 else _available_closes(panel, as_of, member, required))
    if available < required:
        return MissingReason.NOT_YET_AVAILABLE.value, "insufficient_lookback"
    if legacy_conditioned and not observed:
        return MissingReason.NO_COVERAGE.value, "excluded_from_legacy_activity_cohort"
    return MissingReason.NO_COVERAGE.value, "unavailable_in_owner_projection"


def _metric_cell(*, value: bool | None, recipe_id: str, effective_at: str,
                 source_ref: str, available: int, required: int,
                 included: bool, missing: tuple[str, str | None]) -> dict[str, Any]:
    null_reason, estimability_reason = missing
    if value is not None:
        null_reason = MissingReason.OK.value
        estimability_reason = None
    return {
        "value": value,
        "null_reason": null_reason,
        "estimability_reason": estimability_reason,
        "recipe_id": recipe_id,
        "effective_at": effective_at,
        "source_ref": source_ref,
        "observations_available": int(available),
        "observations_required": int(required),
        "included_in_aggregate": bool(included),
    }


def _aggregate(*, metric_id: str, member_keys: list[str], cells: Mapping[str, dict]) -> dict[str, Any]:
    definition = _METRIC_DEFS[metric_id]
    observed = [key for key in member_keys if cells[key]["included_in_aggregate"]]
    numerator_keys = [key for key in observed if cells[key]["value"] is True]
    excluded = [
        {
            "member_key": key,
            "null_reason": cells[key]["null_reason"],
            "estimability_reason": cells[key]["estimability_reason"],
        }
        for key in member_keys if key not in observed
    ]
    denominator = len(observed)
    numerator = len(numerator_keys)
    value = None if denominator == 0 else numerator / denominator
    return {
        **definition,
        "membership_digest": canonical_json_sha256(member_keys),
        "observed_member_keys": observed,
        "excluded_members": excluded,
        "numerator_member_keys": numerator_keys,
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "null_reason": (MissingReason.OK.value if value is not None
                        else MissingReason.NO_COVERAGE.value),
        "cohort_digest": canonical_json_sha256(observed),
    }


def _legacy_share(legacy: Mapping[str, Any], metric_id: str) -> tuple[object, object]:
    participation = legacy.get("participation")
    if not isinstance(participation, Mapping):
        raise ContractError("legacy_pulse.participation invalid")
    if metric_id == "legacy_activity":
        return participation.get("activity_share"), legacy.get("n_covered")
    suffix = "50d" if metric_id == "legacy_trend_50" else "200d"
    return participation.get(f"trend_share_{suffix}"), participation.get(f"trend_n_{suffix}")


def _assert_legacy_match(metric_id: str, aggregate: Mapping[str, Any],
                         legacy: Mapping[str, Any]) -> None:
    expected_value, expected_denominator = _legacy_share(legacy, metric_id)
    actual_value = aggregate.get("value")
    if expected_value is None:
        matches_value = actual_value is None
    else:
        matches_value = (_finite(expected_value) and _finite(actual_value)
                         and round(float(expected_value), 4) == round(float(actual_value), 4))
    if not matches_value or expected_denominator != aggregate.get("denominator"):
        raise ContractError(
            f"{metric_id} disagrees with legacy pulse: "
            f"value={actual_value!r}/{expected_value!r} "
            f"denominator={aggregate.get('denominator')!r}/{expected_denominator!r}"
        )
    if metric_id == "legacy_activity":
        participation = legacy["participation"]
        if participation.get("activity_n") != aggregate.get("numerator"):
            raise ContractError("legacy_activity numerator disagrees with legacy pulse")


def project_group_members(*, group_id: str, member_records: Sequence[Mapping[str, Any]],
                          panel: Mapping[str, Any], as_of: object,
                          covered_members: Sequence[str], active_members: Sequence[str],
                          legacy_pulse: Mapping[str, Any],
                          source_receipts: Sequence[Mapping[str, Any]],
                          generated_at: object) -> dict[str, Any]:
    """Project one group from intermediates already computed by Group Pulse."""
    if not isinstance(group_id, str) or not group_id:
        raise ContractError("group_id invalid")
    effective_at = _date(as_of, field="as_of")
    generated = _timestamp(generated_at, field="generated_at")
    receipts = _normalise_receipts(source_receipts)
    source_ref = receipts[0]["source_ref"]
    if legacy_pulse.get("basket_id") != group_id:
        raise ContractError("legacy_pulse basket_id mismatch")
    if _date(legacy_pulse.get("as_of"), field="legacy_pulse.as_of") != effective_at:
        raise ContractError("legacy_pulse as_of mismatch")

    normalised_members: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(member_records):
        if not isinstance(raw, Mapping):
            raise ContractError(f"member_records[{index}] invalid")
        key = raw.get("member_key")
        symbol = raw.get("source_symbol")
        identity = raw.get("identity_ref")
        if not isinstance(key, str) or not key:
            raise ContractError(f"member_records[{index}].member_key invalid")
        if key in normalised_members:
            raise ContractError(f"duplicate member: {key}")
        if not isinstance(symbol, str) or not symbol:
            raise ContractError(f"member_records[{index}].source_symbol invalid")
        if identity is not None and (not isinstance(identity, str) or not identity):
            raise ContractError(f"member_records[{index}].identity_ref invalid")
        normalised_members[key] = {
            "member_key": key,
            "source_symbol": symbol,
            "identity_ref": identity,
            "metrics": {},
        }
    member_keys = sorted(normalised_members)
    members_set = set(member_keys)
    covered = sorted(set(covered_members))
    active = sorted(set(active_members))
    if not set(covered).issubset(members_set):
        raise ContractError("covered_members contains unknown member")
    if not set(active).issubset(set(covered)):
        raise ContractError("active_members must be a subset of covered_members")

    as_of_ts = pd.Timestamp(effective_at)
    metric_cells: dict[str, dict[str, dict[str, Any]]] = {}
    metric_sets: dict[str, tuple[list[str], list[str]]] = {
        "legacy_activity": (covered, active),
    }
    for metric_id, suffix in (("legacy_trend_50", "50"), ("legacy_trend_200", "200")):
        observed = [
            key for key in covered
            if bool(_frame_value(panel.get(f"has_ma{suffix}"), as_of_ts, key))
        ]
        numerator = [
            key for key in observed
            if bool(_frame_value(panel.get(f"above_ma{suffix}"), as_of_ts, key))
        ]
        metric_sets[metric_id] = (observed, numerator)

    for metric_id, (observed, numerator) in metric_sets.items():
        definition = _METRIC_DEFS[metric_id]
        required = int(definition["minimum_observations"])
        window = int(definition["window"])
        cells: dict[str, dict[str, Any]] = {}
        for key in member_keys:
            included = key in observed
            value = (key in numerator) if included else None
            available = (_activity_observations(panel, as_of_ts, key)
                         if metric_id == "legacy_activity"
                         else _available_closes(panel, as_of_ts, key, window))
            missing = _missing_detail(
                panel, as_of_ts, key, observed=included, required=(63 if metric_id == "legacy_activity" else required),
                legacy_conditioned=metric_id != "legacy_activity",
            )
            cells[key] = _metric_cell(
                value=value,
                recipe_id=definition["recipe_id"],
                effective_at=effective_at,
                source_ref=source_ref,
                available=available,
                required=required,
                included=included,
                missing=missing,
            )
            normalised_members[key]["metrics"][metric_id] = deepcopy(cells[key])
        metric_cells[metric_id] = cells

    metrics = {
        metric_id: _aggregate(metric_id=metric_id, member_keys=member_keys, cells=cells)
        for metric_id, cells in metric_cells.items()
    }
    for metric_id, aggregate in metrics.items():
        _assert_legacy_match(metric_id, aggregate, legacy_pulse)

    membership_digest = canonical_json_sha256(member_keys)
    return {
        "group_id": group_id,
        "group_kind": GROUP_KIND,
        "source_membership_ref": f"group_pulse:membership:{group_id}",
        "source_membership_digest": membership_digest,
        "member_count": len(member_keys),
        "member_keys": member_keys,
        "members": normalised_members,
        "metrics": metrics,
        "legacy_pulse_digest": None,
        "coverage_details": {
            "catalogue_member_count": len(member_keys),
            "metrics": {
                metric_id: {
                    "observed": metric["denominator"],
                    "excluded": len(metric["excluded_members"]),
                }
                for metric_id, metric in metrics.items()
            },
        },
    }


def assemble_member_bundle(*, groups: Mapping[str, Mapping[str, Any]], as_of: object,
                           generated_at: object,
                           source_receipts: Sequence[Mapping[str, Any]],
                           legacy_pulse_bytes: bytes) -> dict[str, Any]:
    """Bind projected groups to the exact legacy wire bytes from the same run."""
    if not isinstance(legacy_pulse_bytes, bytes) or not legacy_pulse_bytes:
        raise ContractError("legacy_pulse_bytes must be non-empty bytes")
    receipts = _normalise_receipts(source_receipts)
    legacy_digest = sha256(legacy_pulse_bytes).hexdigest()
    bound_groups: dict[str, dict[str, Any]] = {}
    for group_id in sorted(groups):
        group = deepcopy(dict(groups[group_id]))
        group["legacy_pulse_digest"] = legacy_digest
        bound_groups[group_id] = group
    bundle = {
        "schema": SCHEMA,
        "authority": AUTHORITY,
        "as_of": _date(as_of, field="as_of"),
        "generated_at": _timestamp(generated_at, field="generated_at"),
        "source": {
            "legacy_pulse_sha256": legacy_digest,
            "legacy_pulse_bytes": len(legacy_pulse_bytes),
            "receipts": receipts,
        },
        "groups": bound_groups,
        "projection_digest": "0" * 64,
    }
    bundle["projection_digest"] = projection_digest(bundle)
    errors = validate_member_bundle(bundle)
    if errors:
        raise ContractError("member observation bundle invalid: " + "; ".join(errors))
    return bundle


def _unknown_keys(value: Mapping[str, Any], expected: frozenset[str], label: str,
                  errors: list[str]) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing:
        errors.append(f"{label}: missing keys {missing}")
    if unknown:
        errors.append(f"{label}: unknown keys {unknown}")


def _validate_cell(cell: Any, *, label: str, metric: Mapping[str, Any],
                   member_key: str, as_of: date, errors: list[str]) -> None:
    if not isinstance(cell, Mapping):
        errors.append(f"{label}: not an object")
        return
    _unknown_keys(cell, _CELL_KEYS, label, errors)
    value = cell.get("value")
    if value is not None and not isinstance(value, bool) and not _finite(value):
        errors.append(f"{label}.value must be finite, boolean, or null")
    reason = cell.get("null_reason")
    allowed_reasons = {item.value for item in MissingReason}
    if reason not in allowed_reasons:
        errors.append(f"{label}.null_reason invalid")
    if value is None and reason == MissingReason.OK.value:
        errors.append(f"{label}: null value cannot have OK null_reason")
    if value is not None and reason != MissingReason.OK.value:
        errors.append(f"{label}: observed value must have OK null_reason")
    if cell.get("recipe_id") != metric.get("recipe_id"):
        errors.append(f"{label}: recipe mismatch")
    try:
        effective = parse_date(cell.get("effective_at"), field=f"{label}.effective_at")
        if effective > as_of:
            errors.append(f"{label}: future effective_at")
    except ContractError as exc:
        errors.append(str(exc))
    for key in ("observations_available", "observations_required"):
        number = cell.get(key)
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            errors.append(f"{label}.{key} invalid")
    included = cell.get("included_in_aggregate")
    if not isinstance(included, bool):
        errors.append(f"{label}.included_in_aggregate invalid")
    elif included != (member_key in (metric.get("observed_member_keys") or [])):
        errors.append(f"{label}: aggregate inclusion mismatch")


def _validate_metric(metric: Any, *, label: str, member_keys: list[str],
                     errors: list[str]) -> None:
    if not isinstance(metric, Mapping):
        errors.append(f"{label}: not an object")
        return
    _unknown_keys(metric, _METRIC_KEYS, label, errors)
    observed = metric.get("observed_member_keys")
    numerator_keys = metric.get("numerator_member_keys")
    excluded = metric.get("excluded_members")
    if not isinstance(observed, list) or len(observed) != len(set(observed)):
        errors.append(f"{label}: observed_member_keys invalid")
        observed = []
    if not isinstance(numerator_keys, list) or len(numerator_keys) != len(set(numerator_keys)):
        errors.append(f"{label}: numerator_member_keys invalid")
        numerator_keys = []
    if not set(observed).issubset(set(member_keys)):
        errors.append(f"{label}: observed contains unknown member")
    if not set(numerator_keys).issubset(set(observed)):
        errors.append(f"{label}: numerator contains unobserved or unknown member")
    excluded_keys: list[str] = []
    if not isinstance(excluded, list):
        errors.append(f"{label}: excluded_members invalid")
        excluded = []
    for index, row in enumerate(excluded):
        row_label = f"{label}.excluded_members[{index}]"
        if not isinstance(row, Mapping):
            errors.append(f"{row_label}: not an object")
            continue
        _unknown_keys(row, _EXCLUDED_KEYS, row_label, errors)
        key = row.get("member_key")
        if isinstance(key, str):
            excluded_keys.append(key)
        if row.get("null_reason") not in {item.value for item in MissingReason} - {MissingReason.OK.value}:
            errors.append(f"{row_label}.null_reason invalid")
    if len(excluded_keys) != len(set(excluded_keys)):
        errors.append(f"{label}: duplicate excluded member")
    if set(observed) | set(excluded_keys) != set(member_keys) or set(observed) & set(excluded_keys):
        errors.append(f"{label}: observed/excluded partition mismatch")
    denominator = metric.get("denominator")
    numerator = metric.get("numerator")
    if denominator != len(observed):
        errors.append(f"{label}: denominator does not match observed members")
    if numerator != len(numerator_keys):
        errors.append(f"{label}: numerator does not match numerator members")
    value = metric.get("value")
    if value is not None and not _finite(value):
        errors.append(f"{label}.value must be finite or null")
    expected = None if not observed else len(numerator_keys) / len(observed)
    if value is None:
        if expected is not None:
            errors.append(f"{label}: value missing despite nonzero denominator")
    elif expected is None or not math.isclose(float(value), expected, rel_tol=0.0, abs_tol=1e-12):
        errors.append(f"{label}: value disagrees with numerator/denominator")
    if metric.get("membership_digest") != canonical_json_sha256(member_keys):
        errors.append(f"{label}: membership digest mismatch")
    if metric.get("cohort_digest") != canonical_json_sha256(observed):
        errors.append(f"{label}: cohort digest mismatch")
    for field in ("recipe_id", "unit", "basis"):
        if not isinstance(metric.get(field), str) or not metric.get(field):
            errors.append(f"{label}.{field} invalid")
    for field in ("window", "minimum_observations"):
        number = metric.get(field)
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            errors.append(f"{label}.{field} invalid")


def validate_member_bundle(bundle: Any) -> list[str]:
    """Return closed-contract violations; an empty list means valid."""
    errors: list[str] = []
    if not isinstance(bundle, Mapping):
        return ["bundle: not an object"]
    _unknown_keys(bundle, _TOP_KEYS, "bundle", errors)
    if bundle.get("schema") != SCHEMA:
        errors.append("bundle.schema mismatch")
    if bundle.get("authority") != AUTHORITY:
        errors.append("bundle must remain context_only")
    try:
        as_of = parse_date(bundle.get("as_of"), field="bundle.as_of")
    except ContractError as exc:
        errors.append(str(exc))
        as_of = date.min
    if iso_timestamp(bundle.get("generated_at")) is None:
        errors.append("bundle.generated_at invalid")

    source = bundle.get("source")
    legacy_digest = None
    if not isinstance(source, Mapping):
        errors.append("bundle.source: not an object")
    else:
        _unknown_keys(source, _SOURCE_KEYS, "bundle.source", errors)
        legacy_digest = source.get("legacy_pulse_sha256")
        if not isinstance(legacy_digest, str) or not _SHA_RE.fullmatch(legacy_digest):
            errors.append("bundle.source.legacy_pulse_sha256 invalid")
        byte_count = source.get("legacy_pulse_bytes")
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
            errors.append("bundle.source.legacy_pulse_bytes invalid")
        try:
            _normalise_receipts(source.get("receipts") or [])
        except ContractError as exc:
            errors.append(str(exc))

    groups = bundle.get("groups")
    if not isinstance(groups, Mapping):
        errors.append("bundle.groups: not an object")
        groups = {}
    for group_id, group in groups.items():
        label = f"groups[{group_id!r}]"
        if not isinstance(group_id, str) or not group_id:
            errors.append(f"{label}: invalid key")
        if not isinstance(group, Mapping):
            errors.append(f"{label}: not an object")
            continue
        _unknown_keys(group, _GROUP_KEYS, label, errors)
        if group.get("group_id") != group_id:
            errors.append(f"{label}: group_id does not match key")
        if group.get("group_kind") != GROUP_KIND:
            errors.append(f"{label}: group_kind invalid")
        member_keys = group.get("member_keys")
        members = group.get("members")
        metrics = group.get("metrics")
        if not isinstance(member_keys, list) or len(member_keys) != len(set(member_keys)):
            errors.append(f"{label}: member_keys invalid")
            member_keys = []
        if member_keys != sorted(member_keys):
            errors.append(f"{label}: member_keys must be deterministic")
        if group.get("member_count") != len(member_keys):
            errors.append(f"{label}: member_count mismatch")
        if group.get("source_membership_digest") != canonical_json_sha256(member_keys):
            errors.append(f"{label}: source membership digest mismatch")
        if group.get("legacy_pulse_digest") != legacy_digest:
            errors.append(f"{label}: legacy pulse digest mismatch")
        if not isinstance(members, Mapping) or set(members) != set(member_keys):
            errors.append(f"{label}: members do not match member_keys")
            members = {}
        if not isinstance(metrics, Mapping) or not metrics:
            errors.append(f"{label}: metrics invalid")
            metrics = {}
        for metric_id, metric in metrics.items():
            _validate_metric(metric, label=f"{label}.metrics[{metric_id!r}]",
                             member_keys=member_keys, errors=errors)
        for member_key, member in members.items():
            member_label = f"{label}.members[{member_key!r}]"
            if not isinstance(member, Mapping):
                errors.append(f"{member_label}: not an object")
                continue
            _unknown_keys(member, _MEMBER_KEYS, member_label, errors)
            if member.get("member_key") != member_key:
                errors.append(f"{member_label}: member_key mismatch")
            cells = member.get("metrics")
            if not isinstance(cells, Mapping) or set(cells) != set(metrics):
                errors.append(f"{member_label}: metric cells mismatch")
                continue
            for metric_id, cell in cells.items():
                _validate_cell(cell, label=f"{member_label}.metrics[{metric_id!r}]",
                               metric=metrics[metric_id], member_key=member_key,
                               as_of=as_of, errors=errors)
        coverage = group.get("coverage_details")
        if not isinstance(coverage, Mapping):
            errors.append(f"{label}.coverage_details invalid")
        else:
            _unknown_keys(coverage, _COVERAGE_KEYS, f"{label}.coverage_details", errors)
            if coverage.get("catalogue_member_count") != len(member_keys):
                errors.append(f"{label}.coverage_details catalogue count mismatch")
            coverage_metrics = coverage.get("metrics")
            if not isinstance(coverage_metrics, Mapping) or set(coverage_metrics) != set(metrics):
                errors.append(f"{label}.coverage_details metric set mismatch")
            else:
                for metric_id, row in coverage_metrics.items():
                    row_label = f"{label}.coverage_details.metrics[{metric_id!r}]"
                    if not isinstance(row, Mapping):
                        errors.append(f"{row_label}: not an object")
                        continue
                    _unknown_keys(row, _COVERAGE_METRIC_KEYS, row_label, errors)
                    if row.get("observed") != metrics[metric_id].get("denominator"):
                        errors.append(f"{row_label}: observed count mismatch")
                    if row.get("excluded") != len(metrics[metric_id].get("excluded_members") or []):
                        errors.append(f"{row_label}: excluded count mismatch")

    recorded = bundle.get("projection_digest")
    if not isinstance(recorded, str) or not _SHA_RE.fullmatch(recorded):
        errors.append("bundle.projection_digest invalid")
    else:
        try:
            if recorded != projection_digest(bundle):
                errors.append("bundle.projection_digest mismatch")
        except ContractError:
            # A non-finite or unserialisable value is already a contract violation.
            if not any("finite" in error for error in errors):
                errors.append("bundle is not canonical JSON")
    return errors


def group_for_detail(bundle: Mapping[str, Any] | None, group_id: str,
                     expected_legacy_digest: str) -> dict[str, Any] | None:
    """Return a verified group for the existing detail renderer, else quiet absence."""
    if bundle is None or validate_member_bundle(bundle):
        return None
    source = bundle.get("source") or {}
    if source.get("legacy_pulse_sha256") != expected_legacy_digest:
        return None
    group = (bundle.get("groups") or {}).get(group_id)
    if not isinstance(group, Mapping) or group.get("legacy_pulse_digest") != expected_legacy_digest:
        return None
    return deepcopy(dict(group))
