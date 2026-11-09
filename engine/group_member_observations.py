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

import numpy as np
import pandas as pd

from engine.company_intelligence.contracts import (
    ContractError,
    canonical_json_bytes,
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
    "minimum_observations", "aggregation", "value_type",
    "membership_digest", "observed_member_keys", "excluded_members",
    "numerator_member_keys", "numerator", "denominator", "value",
    "null_reason", "cohort_digest",
})
_EXCLUDED_KEYS = frozenset({"member_key", "null_reason", "estimability_reason"})
_COVERAGE_KEYS = frozenset({"catalogue_member_count", "metrics"})
_COVERAGE_METRIC_KEYS = frozenset({"observed", "excluded"})
_ESTIMABILITY_NULL_REASONS = {
    "missing_effective_observation": MissingReason.NO_COVERAGE.value,
    "insufficient_lookback": MissingReason.NOT_YET_AVAILABLE.value,
    "excluded_from_legacy_activity_cohort": MissingReason.NO_COVERAGE.value,
    "benchmark_unavailable": MissingReason.NO_COVERAGE.value,
    "unavailable_in_owner_projection": MissingReason.NO_COVERAGE.value,
}
_ESTIMABILITY_REASONS = frozenset(_ESTIMABILITY_NULL_REASONS)
_METRIC_SOURCE_BASIS = {
    "legacy_activity": "legacy_activity_state",
    "legacy_trend_50": "legacy_trend_50_state",
    "legacy_trend_200": "legacy_trend_200_state",
    "strict_trend_50": "total_return_close",
    "strict_trend_200": "total_return_close",
    "raw_daily_change": "raw_daily_change",
    "benchmark_relative_daily_change": "benchmark_relative_daily_change",
}

_METRIC_DEFS = {
    "legacy_activity": {
        "recipe_id": "group_pulse.legacy_activity.v1",
        "unit": "fraction", "basis": "absolute_spy_adjusted_activity",
        "benchmark_ref": "SPY", "window": 63, "minimum_observations": 63,
        "aggregation": "share_true", "value_type": "boolean",
    },
    "legacy_trend_50": {
        "recipe_id": "group_pulse.legacy_trend_50.v1",
        "unit": "fraction", "basis": "activity_conditioned_total_return_close",
        "benchmark_ref": None, "window": 50, "minimum_observations": 25,
        "aggregation": "share_true", "value_type": "boolean",
    },
    "legacy_trend_200": {
        "recipe_id": "group_pulse.legacy_trend_200.v1",
        "unit": "fraction", "basis": "activity_conditioned_total_return_close",
        "benchmark_ref": None, "window": 200, "minimum_observations": 100,
        "aggregation": "share_true", "value_type": "boolean",
    },
    "strict_trend_50": {
        "recipe_id": "group_pulse.strict_price_trend_50.v1",
        "unit": "fraction", "basis": "price_only_total_return_close",
        "benchmark_ref": None, "window": 50, "minimum_observations": 50,
        "aggregation": "share_true", "value_type": "boolean",
    },
    "strict_trend_200": {
        "recipe_id": "group_pulse.strict_price_trend_200.v1",
        "unit": "fraction", "basis": "price_only_total_return_close",
        "benchmark_ref": None, "window": 200, "minimum_observations": 200,
        "aggregation": "share_true", "value_type": "boolean",
    },
    "raw_daily_change": {
        "recipe_id": "group_pulse.raw_daily_change.v1",
        "unit": "decimal_return", "basis": "total_return_close_raw_change",
        "benchmark_ref": None, "window": 1, "minimum_observations": 1,
        "aggregation": "none", "value_type": "number",
    },
    "benchmark_relative_daily_change": {
        "recipe_id": "group_pulse.benchmark_relative_daily_change.v1",
        "unit": "decimal_return", "basis": "benchmark_relative_daily_change",
        "benchmark_ref": "SPY", "window": 1, "minimum_observations": 1,
        "aggregation": "none", "value_type": "number",
    },
}


def projection_digest(bundle: Mapping[str, Any]) -> str:
    """Digest the complete bundle with the self field excluded."""
    unsigned = {key: value for key, value in bundle.items() if key != "projection_digest"}
    return canonical_json_sha256(unsigned)


def raw_bytes_receipt(raw: bytes, *, source_ref: str, basis: str,
                      effective_at: object | None) -> dict[str, Any]:
    """Receipt the exact immutable bytes handed to a parser."""
    if not isinstance(raw, bytes):
        raise ContractError("raw receipt input must be bytes")
    if not isinstance(source_ref, str) or not source_ref:
        raise ContractError("raw receipt source_ref invalid")
    if not isinstance(basis, str) or not basis:
        raise ContractError("raw receipt basis invalid")
    effective = None if effective_at is None else _date(effective_at, field="effective_at")
    return {
        "kind": "raw_bytes",
        "source_ref": source_ref,
        "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
        "effective_at": effective,
        "basis": basis,
    }


def _date(value: object, *, field: str) -> str:
    return parse_date(value, field=field).isoformat()


def normalized_frame_receipt(frame: pd.DataFrame | pd.Series, *, source_ref: str,
                             basis: str, effective_at: object | None) -> dict[str, Any]:
    """Receipt one normalized numeric frame without rereading its mutable source."""
    if isinstance(frame, pd.Series):
        value = frame.to_frame(name=str(frame.name or "value"))
    elif isinstance(frame, pd.DataFrame):
        value = frame.copy()
    else:
        raise ContractError("normalized frame receipt requires a Series or DataFrame")
    if value.empty or value.index.has_duplicates or value.columns.has_duplicates:
        raise ContractError("normalized frame receipt requires non-empty unique axes")
    value.columns = [str(column) for column in value.columns]
    columns = sorted(value.columns)
    value = value.sort_index().reindex(columns=columns)
    try:
        numeric = value.astype("float64")
    except (TypeError, ValueError) as exc:
        raise ContractError("normalized frame receipt requires numeric values") from exc
    metadata = {
        "columns": columns,
        "index": [str(item) for item in numeric.index],
        "shape": [int(numeric.shape[0]), int(numeric.shape[1])],
        "dtype": "float64-le",
    }
    header = canonical_json_bytes(metadata)
    digest = sha256()
    digest.update(header)
    byte_count = len(header)
    for column in columns:
        array = numeric[column].to_numpy(dtype="<f8", copy=True)
        array[np.isnan(array)] = np.nan
        raw = array.tobytes(order="C")
        digest.update(raw)
        byte_count += len(raw)
    effective = None if effective_at is None else _date(effective_at, field="effective_at")
    return {
        "kind": "normalized_frame",
        "source_ref": source_ref,
        "sha256": digest.hexdigest(),
        "bytes": byte_count,
        "effective_at": effective,
        "basis": basis,
    }


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
    seen_source_refs: set[str] = set()
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
        if source_ref in seen_source_refs:
            raise ContractError(
                f"source_receipts[{index}].source_ref duplicate source_ref: {source_ref}"
            )
        seen_source_refs.add(source_ref)
        if not isinstance(basis, str) or not basis:
            raise ContractError(f"source_receipts[{index}].basis invalid")
        if not isinstance(digest, str) or not _SHA_RE.fullmatch(digest):
            raise ContractError(f"source_receipts[{index}].sha256 invalid")
        if not isinstance(byte_count, int) or isinstance(byte_count, bool) or byte_count <= 0:
            raise ContractError(f"source_receipts[{index}].bytes invalid")
        raw_effective = raw.get("effective_at")
        effective_at = (None if raw_effective is None else
                        _date(raw_effective, field=f"source_receipts[{index}].effective_at"))
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


def _metric_cell(*, value: bool | float | None, recipe_id: str, effective_at: str,
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
    excluded = [
        {
            "member_key": key,
            "null_reason": cells[key]["null_reason"],
            "estimability_reason": cells[key]["estimability_reason"],
        }
        for key in member_keys if key not in observed
    ]
    denominator = len(observed)
    if definition["aggregation"] == "share_true":
        numerator_keys = [key for key in observed if cells[key]["value"] is True]
        numerator: int | None = len(numerator_keys)
        value: float | None = None if denominator == 0 else numerator / denominator
        null_reason = (MissingReason.OK.value if value is not None
                       else MissingReason.NO_COVERAGE.value)
    else:
        numerator_keys = []
        numerator = None
        value = None
        null_reason = MissingReason.NOT_APPLICABLE.value
    return {
        **definition,
        "membership_digest": canonical_json_sha256(member_keys),
        "observed_member_keys": observed,
        "excluded_members": excluded,
        "numerator_member_keys": numerator_keys,
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "null_reason": null_reason,
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
                          generated_at: object,
                          benchmark_available: bool = True) -> dict[str, Any]:
    """Project one group from intermediates already computed by Group Pulse."""
    if not isinstance(group_id, str) or not group_id:
        raise ContractError("group_id invalid")
    effective_at = _date(as_of, field="as_of")
    generated = _timestamp(generated_at, field="generated_at")
    receipts = _normalise_receipts(source_receipts)
    price_receipt = next((row for row in receipts
                          if row["kind"] == "normalized_frame"
                          and "close" in row["basis"]), receipts[0])
    close_source_ref = price_receipt["source_ref"]
    raw_return_receipt = next((row for row in receipts
                               if row["basis"] == "raw_daily_change"), price_receipt)
    relative_receipt = next((row for row in receipts
                             if row["basis"] == "benchmark_relative_daily_change"),
                            price_receipt)
    membership_receipt = next((row for row in receipts
                               if row["basis"] == "curated_membership"), None)
    legacy_state_basis = {
        metric_id: _METRIC_SOURCE_BASIS[metric_id]
        for metric_id in ("legacy_activity", "legacy_trend_50", "legacy_trend_200")
    }
    legacy_state_refs: dict[str, str] = {}
    for metric_id, basis in legacy_state_basis.items():
        receipt = next((row for row in receipts if row["basis"] == basis), None)
        if receipt is None:
            raise ContractError(f"source receipt basis unavailable: {basis}")
        legacy_state_refs[metric_id] = receipt["source_ref"]
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

    legacy_sets: dict[str, tuple[list[str], list[str]]] = {
        "legacy_activity": (covered, active),
    }
    for metric_id, suffix in (("legacy_trend_50", "50"),
                              ("legacy_trend_200", "200")):
        observed = [
            key for key in covered
            if bool(_frame_value(panel.get(f"has_ma{suffix}"), as_of_ts, key))
        ]
        numerator = [
            key for key in observed
            if bool(_frame_value(panel.get(f"above_ma{suffix}"), as_of_ts, key))
        ]
        legacy_sets[metric_id] = (observed, numerator)

    for metric_id, (observed, numerator) in legacy_sets.items():
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
                panel, as_of_ts, key, observed=included,
                required=(63 if metric_id == "legacy_activity" else required),
                legacy_conditioned=metric_id != "legacy_activity",
            )
            cells[key] = _metric_cell(
                value=value,
                recipe_id=definition["recipe_id"],
                effective_at=effective_at,
                source_ref=legacy_state_refs[metric_id],
                available=available,
                required=required,
                included=included,
                missing=missing,
            )
            normalised_members[key]["metrics"][metric_id] = deepcopy(cells[key])
        metric_cells[metric_id] = cells

    for metric_id, window in (("strict_trend_50", 50),
                              ("strict_trend_200", 200)):
        definition = _METRIC_DEFS[metric_id]
        cells = {}
        for key in member_keys:
            available = _available_closes(panel, as_of_ts, key, window)
            included = available == window and _valid_close(
                _frame_value(panel.get("closes"), as_of_ts, key)
            )
            value: bool | None = None
            if included:
                series = panel["closes"].loc[:as_of_ts, key].tail(window).astype("float64")
                value = bool(float(series.iloc[-1]) > float(series.mean()))
            missing = _missing_detail(
                panel, as_of_ts, key, observed=included,
                required=window, legacy_conditioned=False,
            )
            cells[key] = _metric_cell(
                value=value,
                recipe_id=definition["recipe_id"],
                effective_at=effective_at,
                source_ref=close_source_ref,
                available=available,
                required=window,
                included=included,
                missing=missing,
            )
            normalised_members[key]["metrics"][metric_id] = deepcopy(cells[key])
        metric_cells[metric_id] = cells

    point_specs = (
        ("raw_daily_change", "rets", raw_return_receipt["source_ref"], False),
        ("benchmark_relative_daily_change", "spy_adj",
         relative_receipt["source_ref"], True),
    )
    for metric_id, frame_key, metric_source_ref, needs_benchmark in point_specs:
        definition = _METRIC_DEFS[metric_id]
        cells = {}
        for key in member_keys:
            raw_value = _frame_value(panel.get(frame_key), as_of_ts, key)
            included = _finite(raw_value) and (benchmark_available or not needs_benchmark)
            value = float(raw_value) if included else None
            if needs_benchmark and not benchmark_available:
                missing = (MissingReason.NO_COVERAGE.value, "benchmark_unavailable")
            elif not _finite(raw_value):
                missing = (MissingReason.NO_COVERAGE.value,
                           "missing_effective_observation")
            else:
                missing = (MissingReason.NO_COVERAGE.value,
                           "unavailable_in_owner_projection")
            cells[key] = _metric_cell(
                value=value,
                recipe_id=definition["recipe_id"],
                effective_at=effective_at,
                source_ref=metric_source_ref,
                available=(1 if _finite(raw_value) else 0),
                required=1,
                included=included,
                missing=missing,
            )
            normalised_members[key]["metrics"][metric_id] = deepcopy(cells[key])
        metric_cells[metric_id] = cells

    metrics = {
        metric_id: _aggregate(metric_id=metric_id, member_keys=member_keys, cells=cells)
        for metric_id, cells in metric_cells.items()
    }
    for metric_id in legacy_sets:
        _assert_legacy_match(metric_id, metrics[metric_id], legacy_pulse)

    membership_digest = canonical_json_sha256(member_keys)
    source_membership_ref = (membership_receipt["source_ref"] if membership_receipt
                             else f"group_pulse:membership:{group_id}")
    source_membership_digest = (membership_receipt["sha256"] if membership_receipt
                                else membership_digest)
    return {
        "group_id": group_id,
        "group_kind": GROUP_KIND,
        "source_membership_ref": source_membership_ref,
        "source_membership_digest": source_membership_digest,
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
    value_type = metric.get("value_type")
    if value_type == "boolean":
        if value is not None and not isinstance(value, bool):
            errors.append(f"{label}.value must be boolean or null")
    elif value_type == "number":
        if value is not None and not _finite(value):
            errors.append(f"{label}.value must be a finite number or null")
    else:
        errors.append(f"{label}: parent metric value_type invalid")
    reason = cell.get("null_reason")
    allowed_reasons = {item.value for item in MissingReason}
    if reason not in allowed_reasons:
        errors.append(f"{label}.null_reason invalid")
    estimability_reason = cell.get("estimability_reason")
    if value is None:
        if reason == MissingReason.OK.value:
            errors.append(f"{label}: null value cannot have OK null_reason")
        if estimability_reason not in _ESTIMABILITY_REASONS:
            errors.append(f"{label}.estimability_reason invalid")
        elif reason != _ESTIMABILITY_NULL_REASONS[estimability_reason]:
            errors.append(
                f"{label}: null_reason disagrees with estimability_reason"
            )
    else:
        if reason != MissingReason.OK.value:
            errors.append(f"{label}: observed value must have OK null_reason")
        if estimability_reason is not None:
            errors.append(f"{label}: observed cell cannot carry estimability_reason")
    if cell.get("recipe_id") != metric.get("recipe_id"):
        errors.append(f"{label}: recipe mismatch")
    try:
        effective = parse_date(cell.get("effective_at"), field=f"{label}.effective_at")
        if effective != as_of:
            direction = "future " if effective > as_of else "stale "
            errors.append(
                f"{label}: {direction}effective_at must equal bundle.as_of "
                f"({effective.isoformat()} != {as_of.isoformat()})"
            )
    except ContractError as exc:
        errors.append(str(exc))
    valid_counts = True
    for key in ("observations_available", "observations_required"):
        number = cell.get(key)
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            errors.append(f"{label}.{key} invalid")
            valid_counts = False
    if valid_counts:
        available = cell["observations_available"]
        required = cell["observations_required"]
        if required != metric.get("minimum_observations"):
            errors.append(f"{label}.observations_required disagrees with metric definition")
        window = metric.get("window")
        if isinstance(window, int) and available > window:
            errors.append(f"{label}.observations_available exceeds metric window")
    included = cell.get("included_in_aggregate")
    if not isinstance(included, bool):
        errors.append(f"{label}.included_in_aggregate invalid")
    else:
        expected_inclusion = member_key in (metric.get("observed_member_keys") or [])
        if included != expected_inclusion:
            errors.append(f"{label}: aggregate inclusion mismatch")
        if included and value is None:
            errors.append(f"{label}: included cell must carry an observed value")
        if included and valid_counts and cell["observations_available"] < cell["observations_required"]:
            errors.append(f"{label}: included cell has insufficient observations")
        if not included and value is not None:
            errors.append(f"{label}: excluded cell cannot carry an observed value")
        if value_type == "boolean" and included:
            expected_true = member_key in (metric.get("numerator_member_keys") or [])
            if value is not expected_true:
                errors.append(f"{label}: boolean value disagrees with numerator membership")


def _validate_metric(metric: Any, *, label: str, member_keys: list[str],
                     errors: list[str]) -> None:
    if not isinstance(metric, Mapping):
        errors.append(f"{label}: not an object")
        return
    _unknown_keys(metric, _METRIC_KEYS, label, errors)
    observed = metric.get("observed_member_keys")
    numerator_keys = metric.get("numerator_member_keys")
    excluded = metric.get("excluded_members")
    if (not isinstance(observed, list)
            or not all(isinstance(key, str) and key for key in observed)
            or len(observed) != len(set(observed))):
        errors.append(f"{label}: observed_member_keys invalid")
        observed = []
    elif observed != sorted(observed):
        errors.append(f"{label}: observed_member_keys must be deterministic")
    if (not isinstance(numerator_keys, list)
            or not all(isinstance(key, str) and key for key in numerator_keys)
            or len(numerator_keys) != len(set(numerator_keys))):
        errors.append(f"{label}: numerator_member_keys invalid")
        numerator_keys = []
    elif numerator_keys != sorted(numerator_keys):
        errors.append(f"{label}: numerator_member_keys must be deterministic")
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
        if row.get("estimability_reason") not in _ESTIMABILITY_REASONS:
            errors.append(f"{row_label}.estimability_reason invalid")
    if len(excluded_keys) != len(set(excluded_keys)):
        errors.append(f"{label}: duplicate excluded member")
    elif excluded_keys != sorted(excluded_keys):
        errors.append(f"{label}: excluded_members must be deterministic")
    if set(observed) | set(excluded_keys) != set(member_keys) or set(observed) & set(excluded_keys):
        errors.append(f"{label}: observed/excluded partition mismatch")
    denominator = metric.get("denominator")
    numerator = metric.get("numerator")
    if denominator != len(observed):
        errors.append(f"{label}: denominator does not match observed members")
    aggregation = metric.get("aggregation")
    value_type = metric.get("value_type")
    if aggregation not in {"share_true", "none"}:
        errors.append(f"{label}.aggregation invalid")
    if value_type not in {"boolean", "number"}:
        errors.append(f"{label}.value_type invalid")
    value = metric.get("value")
    null_reason = metric.get("null_reason")
    if aggregation == "share_true":
        if value_type != "boolean":
            errors.append(f"{label}: share_true requires boolean member values")
        if numerator != len(numerator_keys):
            errors.append(f"{label}: numerator does not match numerator members")
        if value is not None and not _finite(value):
            errors.append(f"{label}.value must be finite or null")
        expected = None if not observed else len(numerator_keys) / len(observed)
        if value is None:
            if expected is not None:
                errors.append(f"{label}: value missing despite nonzero denominator")
            if null_reason != MissingReason.NO_COVERAGE.value:
                errors.append(f"{label}: empty aggregate must disclose NO_COVERAGE")
        else:
            if expected is None or not math.isclose(
                    float(value), expected, rel_tol=0.0, abs_tol=1e-12):
                errors.append(f"{label}: value disagrees with numerator/denominator")
            if null_reason != MissingReason.OK.value:
                errors.append(f"{label}: observed aggregate must have OK null_reason")
    elif aggregation == "none":
        if numerator is not None or numerator_keys:
            errors.append(f"{label}: non-aggregate metric cannot carry a numerator")
        if value is not None:
            errors.append(f"{label}: non-aggregate metric cannot carry an aggregate value")
        if null_reason != MissingReason.NOT_APPLICABLE.value:
            errors.append(f"{label}: non-aggregate metric must disclose NOT_APPLICABLE")
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
    receipts: list[dict[str, Any]] = []
    receipt_refs: set[str] = set()
    receipt_by_ref: dict[str, dict[str, Any]] = {}
    membership_receipts: list[dict[str, Any]] = []
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
            receipts = _normalise_receipts(source.get("receipts") or [])
            receipt_refs = {row["source_ref"] for row in receipts}
            receipt_by_ref = {row["source_ref"]: row for row in receipts}
            for index, row in enumerate(receipts):
                effective_at = row.get("effective_at")
                if effective_at is not None:
                    effective = parse_date(
                        effective_at, field=f"bundle.source.receipts[{index}].effective_at"
                    )
                    if effective > as_of:
                        errors.append(
                            f"bundle.source.receipts[{index}]: future source receipt"
                        )
            membership_receipts = [
                row for row in receipts if row["basis"] == "curated_membership"
            ]
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
        if (not isinstance(member_keys, list)
                or not all(isinstance(key, str) and key for key in member_keys)
                or len(member_keys) != len(set(member_keys))):
            errors.append(f"{label}: member_keys invalid")
            member_keys = []
        elif member_keys != sorted(member_keys):
            errors.append(f"{label}: member_keys must be deterministic")
        if group.get("member_count") != len(member_keys):
            errors.append(f"{label}: member_count mismatch")
        membership_digest = group.get("source_membership_digest")
        membership_ref = group.get("source_membership_ref")
        if not isinstance(membership_digest, str) or not _SHA_RE.fullmatch(membership_digest):
            errors.append(f"{label}: source membership digest invalid")
        elif membership_receipts:
            if not any(row["source_ref"] == membership_ref and row["sha256"] == membership_digest
                       for row in membership_receipts):
                errors.append(f"{label}: membership receipt mismatch")
        elif (membership_ref != f"group_pulse:membership:{group_id}"
              or membership_digest != canonical_json_sha256(member_keys)):
            errors.append(f"{label}: membership receipt fallback mismatch")
        if group.get("legacy_pulse_digest") != legacy_digest:
            errors.append(f"{label}: legacy pulse digest mismatch")
        if not isinstance(members, Mapping) or set(members) != set(member_keys):
            errors.append(f"{label}: members do not match member_keys")
            members = {}
        if not isinstance(metrics, Mapping) or not metrics:
            errors.append(f"{label}: metrics invalid")
            metrics = {}
        if set(metrics) != set(_METRIC_DEFS):
            errors.append(
                f"{label}: metric set mismatch; expected {sorted(_METRIC_DEFS)}, "
                f"got {sorted(metrics)}"
            )
        for metric_id, metric in metrics.items():
            metric_label = f"{label}.metrics[{metric_id!r}]"
            _validate_metric(metric, label=metric_label,
                             member_keys=member_keys, errors=errors)
            expected_definition = _METRIC_DEFS.get(metric_id)
            if expected_definition is not None and isinstance(metric, Mapping):
                for field, expected in expected_definition.items():
                    if metric.get(field) != expected:
                        errors.append(
                            f"{metric_label}: definition mismatch for {field}; "
                            f"expected {expected!r}, got {metric.get(field)!r}"
                        )
        for member_key, member in members.items():
            member_label = f"{label}.members[{member_key!r}]"
            if not isinstance(member, Mapping):
                errors.append(f"{member_label}: not an object")
                continue
            _unknown_keys(member, _MEMBER_KEYS, member_label, errors)
            if member.get("member_key") != member_key:
                errors.append(f"{member_label}: member_key mismatch")
            source_symbol = member.get("source_symbol")
            if not isinstance(source_symbol, str) or not source_symbol:
                errors.append(f"{member_label}.source_symbol invalid")
            identity_ref = member.get("identity_ref")
            if identity_ref is not None and (
                    not isinstance(identity_ref, str) or not identity_ref):
                errors.append(f"{member_label}.identity_ref invalid")
            cells = member.get("metrics")
            if not isinstance(cells, Mapping) or set(cells) != set(metrics):
                errors.append(f"{member_label}: metric cells mismatch")
                continue
            for metric_id, cell in cells.items():
                if isinstance(cell, Mapping):
                    source_ref = cell.get("source_ref")
                    if source_ref not in receipt_refs:
                        errors.append(
                            f"{member_label}.metrics[{metric_id!r}]: source receipt missing"
                        )
                    else:
                        receipt = receipt_by_ref[source_ref]
                        if receipt.get("kind") != "normalized_frame":
                            errors.append(
                                f"{member_label}.metrics[{metric_id!r}]: "
                                "referenced source receipt must be normalized_frame"
                            )
                        expected_basis = _METRIC_SOURCE_BASIS.get(metric_id)
                        if (metric_id == "benchmark_relative_daily_change"
                                and cell.get("estimability_reason") == "benchmark_unavailable"):
                            expected_basis = "total_return_close"
                        if receipt.get("basis") != expected_basis:
                            errors.append(
                                f"{member_label}.metrics[{metric_id!r}]: source receipt basis "
                                f"mismatch ({receipt.get('basis')!r} != {expected_basis!r})"
                            )
                        receipt_effective = receipt.get("effective_at")
                        if (receipt_effective is None
                                or parse_date(
                                    receipt_effective,
                                    field=f"{member_label}.metrics[{metric_id!r}].source_receipt",
                                ) != as_of):
                            errors.append(
                                f"{member_label}.metrics[{metric_id!r}]: "
                                "referenced source receipt effective_at mismatch"
                            )
                _validate_cell(cell, label=f"{member_label}.metrics[{metric_id!r}]",
                               metric=metrics[metric_id], member_key=member_key,
                               as_of=as_of, errors=errors)
        if isinstance(members, Mapping) and set(members) == set(member_keys):
            for metric_id, metric in metrics.items():
                if not isinstance(metric, Mapping):
                    continue
                expected_excluded = []
                for member_key in member_keys:
                    member = members.get(member_key)
                    cells = member.get("metrics") if isinstance(member, Mapping) else None
                    cell = cells.get(metric_id) if isinstance(cells, Mapping) else None
                    if isinstance(cell, Mapping) and cell.get("included_in_aggregate") is False:
                        expected_excluded.append({
                            "member_key": member_key,
                            "null_reason": cell.get("null_reason"),
                            "estimability_reason": cell.get("estimability_reason"),
                        })
                if metric.get("excluded_members") != expected_excluded:
                    errors.append(
                        f"{label}.metrics[{metric_id!r}]: excluded member detail mismatch"
                    )
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
