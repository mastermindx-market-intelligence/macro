"""Measured-cost and demand reducers for the existing quota-economics preview.

Pure, bounded, no I/O and no storage. Inputs are an authoring projection of
owner-held terminal usage/outcome evidence, not another usage ledger. The result
never verifies an enrollment, authorizes a route, or promotes model suitability.
"""
from __future__ import annotations

import copy
import math
from decimal import Decimal, ROUND_DOWN
from typing import Any, Mapping

from engine.provider_quota_economics import (
    INPUT_SCHEMA, QuotaEconomicsError, identity, instant, number,
)

MEASURED_INPUT_SCHEMA = "mastermind.quota_economics_preview_input/v2"
MAX_USAGE_ROWS = 4096
COHORT_FIELDS = ("effort", "context_band", "rate_generation", "rate_band")
USAGE_KEYS = {
    "measurement_id", "revision", "attempt_id", "provider", "model_alias",
    "task_kind", "effort", "context_band", "rate_generation", "rate_band",
    "resource_id", "entitlement_generation", "unit", "amount",
    "duration_seconds", "completed_at", "observed_at", "accepted",
    "attribution", "evidence", "retracted",
}
IMMUTABLE_USAGE_KEYS = USAGE_KEYS - {
    "revision", "amount", "duration_seconds", "completed_at", "observed_at",
    "accepted", "attribution", "evidence", "retracted",
}


def _closed(row, keys, code):
    if not isinstance(row, Mapping) or set(row) != set(keys):
        raise QuotaEconomicsError(code)


def _integer(value, maximum, *, positive=False):
    if type(value) is not int or not (1 if positive else 0) <= value <= maximum:
        raise QuotaEconomicsError("INVALID_CALIBRATION_INTEGER")


def _calibration_policy(row, as_of):
    _closed(row, {"min_samples", "quantile", "safety_factor", "window_start_at", "history_complete"},
            "INVALID_CALIBRATION_POLICY")
    _integer(row["min_samples"], 1000, positive=True)
    if row["min_samples"] < 3:
        raise QuotaEconomicsError("CALIBRATION_SAMPLE_FLOOR")
    quantile, factor = number(row["quantile"]), number(row["safety_factor"])
    if not Decimal("0.5") <= quantile <= 1 or not 1 <= factor <= 5:
        raise QuotaEconomicsError("INVALID_CALIBRATION_SAFETY")
    start, now = instant(row["window_start_at"]), instant(as_of)
    if not 0 < now - start <= 32 * 86400 or type(row["history_complete"]) is not bool:
        raise QuotaEconomicsError("INVALID_CALIBRATION_COVERAGE")
    return start, now, quantile, factor


def current_measurements(rows, *, as_of):
    """Apply source revisions before cohort filtering; never resurrect retractions.

    No mutation is persisted. Duplicate deliveries are idempotent. Conflicting
    same-revision payloads or multiple measurements for one attempt/resource are
    refused rather than silently inflating sample size.
    """
    if not isinstance(rows, (list, tuple)) or len(rows) > MAX_USAGE_ROWS:
        raise QuotaEconomicsError("USAGE_INPUT_TOO_LARGE_OR_INVALID")
    now = instant(as_of)
    histories = {}
    for raw in rows:
        _closed(raw, USAGE_KEYS, "INVALID_USAGE_OBSERVATION")
        row = dict(raw)
        for key in ("measurement_id", "attempt_id", "provider", "model_alias", "task_kind",
                    "resource_id", "entitlement_generation", "unit", *COHORT_FIELDS):
            identity(row[key])
        _integer(row["revision"], 1000000)
        _integer(row["duration_seconds"], 32 * 86400, positive=True)
        number(row["amount"])
        if type(row["accepted"]) is not bool or type(row["retracted"]) is not bool:
            raise QuotaEconomicsError("INVALID_USAGE_OUTCOME")
        if row["evidence"] not in {"exact", "provider_reported", "estimated", "unknown"}:
            raise QuotaEconomicsError("INVALID_USAGE_EVIDENCE")
        if row["attribution"] not in {"provider_attempt", "exclusive_interval", "ambiguous"}:
            raise QuotaEconomicsError("INVALID_USAGE_ATTRIBUTION")
        completed, observed = instant(row["completed_at"]), instant(row["observed_at"])
        if observed < completed:
            raise QuotaEconomicsError("USAGE_OBSERVED_BEFORE_COMPLETION")
        history = histories.setdefault(row["measurement_id"], {})
        prior = history.get(row["revision"])
        if prior is not None and prior != row:
            raise QuotaEconomicsError("CONFLICTING_USAGE_REVISION")
        if history:
            witness = next(iter(history.values()))
            if any(witness[key] != row[key] for key in IMMUTABLE_USAGE_KEYS):
                raise QuotaEconomicsError("USAGE_REVISION_CHANGED_IDENTITY")
        history[row["revision"]] = row
    result, unavailable, duplicate_pairs = [], {}, set()
    for measurement_id in sorted(histories):
        versions = [histories[measurement_id][key] for key in sorted(histories[measurement_id])]
        times = [instant(row["observed_at"]) for row in versions]
        if times != sorted(times):
            raise QuotaEconomicsError("USAGE_REVISION_TIME_REVERSED")
        visible = [row for row in versions if instant(row["observed_at"]) <= now]
        if not visible:
            unavailable[measurement_id] = "FUTURE_OBSERVATION"
            continue
        row = visible[-1]
        pair = (row["attempt_id"], row["resource_id"], row["entitlement_generation"])
        if pair in duplicate_pairs:
            raise QuotaEconomicsError("MULTIPLE_MEASUREMENTS_FOR_ATTEMPT_RESOURCE")
        duplicate_pairs.add(pair)
        if row["retracted"]:
            unavailable[measurement_id] = "RETRACTED"
        elif row["evidence"] not in {"exact", "provider_reported"}:
            unavailable[measurement_id] = "UNSUPPORTED_EVIDENCE"
        elif row["attribution"] == "ambiguous":
            unavailable[measurement_id] = "AMBIGUOUS_SHARED_CONSUMPTION"
        else:
            result.append(row)
    return result, unavailable


def _upper(values, quantile):
    return sorted(values)[int((Decimal(len(values)) * quantile).to_integral_value(rounding="ROUND_CEILING")) - 1]


def _decimal_text(value):
    return str(value.quantize(Decimal("0.000000000001"), rounding=ROUND_DOWN).normalize())


def _derive_costs(document):
    policy = document["calibration"]
    start, now, quantile, factor = _calibration_policy(policy, document["as_of"])
    rows, exclusions = current_measurements(document["usage"], as_of=document["as_of"])
    spec = {key: copy.deepcopy(document[key]) for key in ("as_of", "resources", "options", "task", "policy")}
    spec["schema"] = INPUT_SCHEMA
    resources = {row["resource_id"]: row for row in spec["resources"]}
    options = {row["option_id"]: row for row in spec["options"]}
    if len(resources) != len(spec["resources"]) or len(options) != len(spec["options"]):
        raise QuotaEconomicsError("DUPLICATE_IDENTITY")
    if not isinstance(document["cohorts"], Mapping) or set(document["cohorts"]) != set(options):
        raise QuotaEconomicsError("INCOMPLETE_COST_COHORTS")
    receipts = []
    for option_id in sorted(options):
        option = options[option_id]
        cohort = document["cohorts"][option_id]
        _closed(cohort, COHORT_FIELDS, "INVALID_COST_COHORT")
        for value in cohort.values():
            identity(value)
        estimate = {"option_id": option_id, "status": "ESTIMATED_FROM_DECLARED_USAGE",
                    "resources": [], "duration_upper_seconds": None,
                    "useful_jobs_per_hour": None, "claim_cost_authority": False,
                    "statistical_upper_bound": False}
        durations, accepted_sets = {}, []
        linked = [r for r in resources.values() if option_id in r["applies_to"]]
        if set(option["costs"]) != {r["resource_id"] for r in linked}:
            raise QuotaEconomicsError("INCOMPLETE_RESOURCE_COSTS")
        failed = False
        for resource in linked:
            resource_id = resource["resource_id"]
            if resource["unit"] == "concurrent_sessions":
                # Slot cost is an existing execution constraint, never learned from tokens.
                continue
            matched = [row for row in rows
                if row["resource_id"] == resource_id
                and row["entitlement_generation"] == resource["entitlement_generation"]
                and row["unit"] == resource["unit"]
                and row["provider"] == option["provider"]
                and row["model_alias"] == option["model_alias"]
                and row["task_kind"] == spec["task"]["kind"]
                and all(row[key] == cohort[key] for key in COHORT_FIELDS)
                and start <= instant(row["completed_at"]) <= now]
            accepted = {row["attempt_id"] for row in matched if row["accepted"]}
            accepted_sets.append(accepted)
            receipt = {"resource_id": resource_id, "unit": resource["unit"],
                       "sample_count": len(matched), "accepted_count": len(accepted),
                       "rejected_count": sum(not row["accepted"] for row in matched),
                       "upper_native_cost": None, "reason": None}
            if len(matched) < policy["min_samples"]:
                receipt["reason"] = "INSUFFICIENT_COMPARABLE_SAMPLES"
            elif not accepted:
                receipt["reason"] = "NO_ACCEPTED_OUTCOME"
            else:
                amounts = [number(row["amount"]) for row in matched]
                # Failed work counts in the expense of obtaining an accepted result.
                upper = max(_upper(amounts, quantile), sum(amounts) / len(accepted)) * factor
                if not upper:
                    receipt["reason"] = "ZERO_NATIVE_COST_NOT_ROUTABLE"
                elif upper > Decimal("1e15"):
                    receipt["reason"] = "COST_ESTIMATE_OUT_OF_RANGE"
                else:
                    receipt["upper_native_cost"] = str(upper.quantize(Decimal("0.000000000001"), rounding="ROUND_CEILING").normalize())
            option["costs"][resource_id] = {"amount": receipt["upper_native_cost"], "unit": resource["unit"]}
            if receipt["reason"]:
                failed = True
            for row in matched:
                prior = durations.get(row["attempt_id"])
                pair = (row["duration_seconds"], row["accepted"])
                if prior is not None and prior != pair:
                    raise QuotaEconomicsError("INCONSISTENT_ATTEMPT_OUTCOME")
                durations[row["attempt_id"]] = pair
            estimate["resources"].append(receipt)
        if not estimate["resources"]:
            raise QuotaEconomicsError("MODEL_COMPUTE_RESOURCE_MISSING")
        if failed or not durations:
            estimate["status"] = "COST_ESTIMATE_UNAVAILABLE"
            option["duration_seconds"] = None
            option["useful_jobs_per_hour"] = None
        else:
            duration = math.ceil(_upper([pair[0] for pair in durations.values()], quantile) * factor)
            if duration > 32 * 86400:
                raise QuotaEconomicsError("DURATION_ESTIMATE_OUT_OF_RANGE")
            option["duration_seconds"] = duration
            estimate["duration_upper_seconds"] = duration
            common = set.intersection(*accepted_sets)
            if policy["history_complete"]:
                rate = Decimal(len(common)) * 3600 / Decimal(str(now - start))
                option["useful_jobs_per_hour"] = _decimal_text(rate)
                estimate["useful_jobs_per_hour"] = option["useful_jobs_per_hour"]
            else:
                option["useful_jobs_per_hour"] = None
                estimate["throughput_reason"] = "PARTIAL_HISTORY_NO_RATE_INFERENCE"
        receipts.append(estimate)
    return spec, receipts, exclusions


def _demand_reserves(spec, targets):
    """Derive shrinkable SOFT reserve proposals; preserve all supplied hard floors.

    A complete zero-demand declaration can release only this computed soft reserve.
    Unknown demand/cost protects the target, not an invented zero. Multi-target
    shortages share the remaining free balance proportionally, with round-down.
    """
    if not isinstance(targets, (list, tuple)) or len(targets) > 128:
        raise QuotaEconomicsError("INVALID_RESERVE_TARGETS")
    resources = {row["resource_id"]: row for row in spec["resources"]}
    options = {row["option_id"]: row for row in spec["options"]}
    grouped, seen = {}, set()
    for target in targets:
        _closed(target, {"resource_id", "option_id", "fraction", "demand_jobs", "demand_complete"},
                "INVALID_RESERVE_TARGET")
        resource_id, option_id = identity(target["resource_id"]), identity(target["option_id"])
        if resource_id not in resources or option_id not in options:
            raise QuotaEconomicsError("UNBOUND_RESERVE_TARGET")
        resource, option = resources[resource_id], options[option_id]
        if option_id not in resource["applies_to"] or resource["unit"] == "concurrent_sessions":
            raise QuotaEconomicsError("INVALID_RESERVE_RESOURCE")
        key = (resource_id, option["model_alias"])
        if key in seen:
            raise QuotaEconomicsError("DUPLICATE_RESERVE_BENEFICIARY")
        seen.add(key)
        fraction = number(target["fraction"])
        if fraction > 1 or type(target["demand_complete"]) is not bool:
            raise QuotaEconomicsError("INVALID_RESERVE_FRACTION_OR_COVERAGE")
        if target["demand_jobs"] is not None:
            _integer(target["demand_jobs"], 512)
        if target["demand_complete"] and target["demand_jobs"] is None:
            raise QuotaEconomicsError("COMPLETE_DEMAND_MISSING_COUNT")
        grouped.setdefault(resource_id, []).append((target, option, fraction))
    receipts = []
    for resource_id in sorted(grouped):
        resource = resources[resource_id]
        entries = grouped[resource_id]
        if sum(row[2] for row in entries) > 1:
            raise QuotaEconomicsError("RESERVE_TARGETS_OVERALLOCATE_LIMIT")
        hard = {key: number(value) for key, value in resource.get("reserves", {}).items()}
        fresh = (resource["evidence"] in {"exact", "provider_reported"}
                 and resource["limit"] is not None and resource["remaining"] is not None
                 and instant(resource["observed_at"]) <= instant(spec["as_of"]) < instant(resource["valid_until"])
                 and not (resource.get("reset_at") is not None
                          and resource["window_type"] in {"fixed", "billing_cycle"}
                          and instant(resource["reset_at"]) <= instant(spec["as_of"])))
        if not fresh:
            receipts.append({"resource_id": resource_id, "status": "RESERVE_SOURCE_UNKNOWN_HARD_FLOORS_RETAINED"})
            continue
        free = max(Decimal(0), number(resource["remaining"]) - number(resource.get("unobserved_holds", 0)) - sum(hard.values()))
        proposals = []
        for target, option, fraction in entries:
            alias = option["model_alias"]
            desired = number(resource["limit"]) * fraction
            cost = option["costs"][resource_id]["amount"]
            reason = "UNKNOWN_DEMAND_TARGET_PROTECTED"
            if target["demand_complete"] and target["demand_jobs"] == 0:
                desired, reason = Decimal(0), "NO_DEMAND_SOFT_RESERVE_RELEASED"
            elif target["demand_complete"] and cost is not None:
                desired = min(desired, number(cost) * target["demand_jobs"])
                reason = "MEASURED_COST_TIMES_DECLARED_DEMAND"
            elif target["demand_complete"]:
                reason = "UNKNOWN_COST_TARGET_PROTECTED"
            floor = hard.get(alias, Decimal(0))
            proposals.append((alias, max(Decimal(0), desired - floor), floor, reason))
        requested = sum(row[1] for row in proposals)
        scale = min(Decimal(1), free / requested) if requested else Decimal(1)
        new_reserves = dict(hard)
        for alias, extra, floor, reason in sorted(proposals):
            granted = (extra * scale).quantize(Decimal("0.000000000001"), rounding=ROUND_DOWN)
            new_reserves[alias] = floor + granted
            receipts.append({"resource_id": resource_id, "beneficiary_alias": alias,
                             "hard_floor": str(floor), "proposed_soft_reserve": str(granted),
                             "total_preview_reserve": str(floor + granted), "reason": reason,
                             "shortage_prorated": scale < 1, "runtime_reservation_created": False})
        resource["reserves"] = {key: _decimal_text(value) for key, value in new_reserves.items()}
    return receipts


def measured_preview(document):
    """Compile usage/demand into the same preview consumer, never a live claim."""
    from engine.provider_quota_economics import preview_document
    _closed(document, {"schema", "as_of", "resources", "options", "task", "policy",
                       "usage", "cohorts", "calibration", "reserve_targets"}, "INVALID_MEASURED_DOCUMENT")
    if document["schema"] != MEASURED_INPUT_SCHEMA:
        raise QuotaEconomicsError("INVALID_MEASURED_SCHEMA")
    try:
        spec, estimates, exclusions = _derive_costs(document)
        # Validate native resource/cost shape and all task gates before any reserve arithmetic.
        preview_document(spec)
        reserves = _demand_reserves(spec, document["reserve_targets"])
        result = preview_document(spec)
    except (KeyError, TypeError, AttributeError, IndexError):
        raise QuotaEconomicsError("INVALID_MEASURED_INPUT_SHAPE") from None
    result["cost_calibration"] = estimates
    result["measurement_exclusions"] = exclusions
    result["reserve_proposals"] = reserves
    result["derived_inputs"] = {"options": spec["options"], "resources": spec["resources"]}
    result["warnings"].append("DECLARED_USAGE_AND_DEMAND_NOT_VERIFIED_RUNTIME_AUTHORITY")
    return result
