"""Read-only Events & News projection of the existing official actual owner.

No new actual registry, receipt identity, collector, ledger, forecast, or scoring
policy. ``release_actuals`` retains those decisions. This adapter adds event and
point-in-time DISPLAY constraints and returns new dictionaries without mutating
inputs. A builder may attach the result to an event's ``official_evidence``;
that production builder connection is deliberately not made by this module.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import math
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from engine import release_actuals as official

SCHEMA = "release_event_evidence.v1"
# Presentation depends on the canonical owner's registry, not a second mapping.
# Private-owner dependencies are intentional and pinned by adapter tests.
_NY = ZoneInfo("America/New_York")
_BINDING_FIELDS = (
    "receipt_id", "actual", "unit", "period", "official_reference_period",
    "source_url", "source_sha256", "observed_at", "verified_at", "source_released_at",
    "published_precision",
)


def _clock(row: Mapping[str, Any]) -> datetime | None:
    clocks = [official._parse_iso_timestamp(row.get("observed_at"))]
    for name in ("verified_at", "source_released_at"):
        if row.get(name) not in (None, ""):
            clocks.append(official._parse_iso_timestamp(row.get(name)))
    return max(clocks) if clocks and all(c is not None for c in clocks) else None


def _display_errors(row: dict[str, Any], defects_path: str | Path) -> list[str]:
    # Never replace or weaken the canonical validator.
    errors = official.receipt_integrity_errors(row, defects_path=defects_path)
    if type(row.get("actual")) not in (int, float) or type(row.get("actual_raw")) not in (int, float):
        errors.append("non_numeric_actual")
    precision = row.get("published_precision")
    expected_precision = 0 if row.get("unit") == "thousands" else 1
    actual = row.get("actual")
    if type(precision) is not int or precision != expected_precision:
        errors.append("published_precision_mismatch")
    elif type(actual) in (int, float) and math.isfinite(actual) and not math.isclose(
        actual, round(actual, precision), rel_tol=0.0, abs_tol=1e-10
    ):
        # Never round a stored result into a different displayed observation.
        errors.append("published_precision_mismatch")
    if official._parse_iso_timestamp(row.get("verified_at")) is None:
        errors.append("verification_time_missing")
    if row.get("automatic_scoring_eligible") is False:
        errors.append("receipt_explicitly_ineligible")
    try:
        url = row.get("source_url")
        parsed = urlsplit(url) if isinstance(url, str) else None
        if (not parsed or parsed.username or parsed.password or parsed.port not in (None, 443)
                or any(ord(c) < 33 for c in url) or "\\" in url):
            errors.append("unsafe_source_link")
    except ValueError:
        errors.append("unsafe_source_link")
    released = official._parse_iso_timestamp(row.get("source_released_at"))
    observed = official._parse_iso_timestamp(row.get("observed_at"))
    day = official._parse_iso_date(row.get("release_date"))
    if day and ((released and released.astimezone(_NY).date() != day)
                or (observed and observed.astimezone(_NY).date() < day)):
        errors.append("event_clock_date_mismatch")
    return errors


def _reference(event: Mapping[str, Any], event_type: str) -> tuple[str | None, str | None]:
    supplied = [event[k] for k in official._EXPLICIT_REFERENCE_FIELDS if event.get(k) not in (None, "")]
    if not supplied:
        return None, None
    if event_type == "CLAIMS":
        parse = official._parse_week_reference
    elif event_type == "GDP":
        parse = official._parse_quarter_reference
    else:
        parse = official._parse_month_reference
    values = [parse(v) for v in supplied]
    if any(v is None for v in values):
        return None, "invalid_reference_period"
    normalized = [v.isoformat() if hasattr(v, "isoformat") else v for v in values]
    if len(set(normalized)) != 1:
        return None, "reference_period_conflict"
    return normalized[0], None


def _metric_evidence(
    rows: list[dict[str, Any]], release: str, day: str, event_type: str,
    expected: str | None, cutoff: datetime, defects_path: str | Path,
) -> dict[str, Any]:
    metric_id, unit, _scale = official._SPEC_BY_RELEASE[release]
    result: dict[str, Any] = {
        "release": release, "metric_id": metric_id, "unit": unit,
        "status": "unavailable", "reason": "no_matching_receipt", "actual": None,
        "correction_pending": False,
    }
    matched = [r for r in rows if r.get("release") == release and r.get("release_date") == day]
    eligible: list[dict[str, Any]] = []
    withheld: set[str] = set()
    for row in matched:
        # Correction candidates cannot become first-published actuals.
        if row.get("row_type") == "correction_candidate":
            continue
        try:
            errors = _display_errors(row, defects_path)
        except (ValueError, TypeError, OverflowError):
            errors = ["malformed_receipt"]
        if errors:
            withheld.update(errors)
            continue
        available = _clock(row)
        if available is None or available > cutoff:
            withheld.add("not_available_as_of")
            continue
        if expected is not None:
            reference = (official._parse_week_reference(row.get("official_reference_period"))
                         if event_type == "CLAIMS" else row.get("period"))
            reference = reference.isoformat() if hasattr(reference, "isoformat") else reference
            if reference != expected:
                withheld.add("reference_period_mismatch")
                continue
        eligible.append(row)
    if not eligible:
        for reason, codes in (
            ("quarantined", {"known_source_binding_defect"}),
            ("quarantine_policy_unavailable", {"official_actual_defect_sidecar_invalid"}),
            ("reference_period_mismatch", {"reference_period_mismatch"}),
            ("verification_time_missing", {"verification_time_missing"}),
            ("published_precision_mismatch", {"published_precision_mismatch"}),
            ("not_available_as_of", {"not_available_as_of"}),
        ):
            if withheld & codes:
                result["reason"] = reason
                return result
        if withheld:
            result["reason"] = "receipt_integrity_failed"
        elif any(r.get("row_type") == "correction_candidate" for r in matched):
            result["reason"] = "no_canonical_first_receipt"
        return result
    periods = {r["period"] for r in eligible}
    if len(periods) != 1:
        result["reason"] = "ambiguous_reference_period"
        return result
    # Reusing an ID with conflicting evidence must not make list order decisive.
    by_id: dict[str, tuple[Any, ...]] = {}
    for row in eligible:
        binding = tuple(row.get(k) for k in _BINDING_FIELDS)
        if row["receipt_id"] in by_id and by_id[row["receipt_id"]] != binding:
            result["reason"] = "conflicting_first_receipts"
            return result
        by_id[row["receipt_id"]] = binding
    earliest = min(official._parse_iso_timestamp(r["observed_at"]) for r in eligible)
    first_ids = {r["receipt_id"] for r in eligible if official._parse_iso_timestamp(r["observed_at"]) == earliest}
    if len(first_ids) != 1:
        result["reason"] = "conflicting_first_receipts"
        return result
    first = official.canonical_actual(eligible, release, next(iter(periods)), defects_path=defects_path)
    if first is None:
        # The existing quarantine policy may have changed during the read.
        result["reason"] = "receipt_integrity_failed"
        return result
    pending = False
    for row in matched:
        if (row.get("row_type") != "correction_candidate"
                or row.get("supersedes_receipt_id") != first["receipt_id"]
                or row.get("period") != first["period"]
                or row.get("automatic_scoring_eligible") is not False):
            continue
        # Validate its evidence without adjudicating the candidate or returning its value.
        candidate = {**row, "row_type": "actual", "automatic_scoring_eligible": True}
        try:
            available = _clock(candidate)
            valid = not _display_errors(candidate, defects_path)
        except (ValueError, TypeError, OverflowError):
            valid, available = False, None
        if valid and available is not None and available <= cutoff:
            pending = True
    precision = first["published_precision"]
    result.update({k: first.get(k) for k in _BINDING_FIELDS})
    result.update({
        "status": "available", "reason": None, "publisher": first["publisher"],
        "available_at": _clock(first).isoformat(), "sequence": "first",
        "display_value": f'{first["actual"]:,.{precision}f}',
        "correction_pending": pending,
    })
    return result


def event_actual_evidence(
    event: Any, rows: Any, *, as_of: str,
    defects_path: str | Path = official.DEFAULT_DEFECTS_PATH,
) -> dict[str, Any]:
    """Project official receipts for one typed calendar event at an explicit cutoff.

    Match canonical type + exact scheduled date, never headline text or a nearby
    release. Explicit reference periods must agree. With no supplied period,
    multiple eligible periods are ambiguous, not guessed from date arithmetic.
    Missing quarantine policy, ambiguous first receipts and post-cutoff knowledge
    cannot be rendered as available. This does not grant any trading authority.
    """
    result: dict[str, Any] = {
        "schema": SCHEMA, "display_only": True, "authority": False,
        "status": "unavailable", "reason": None, "metrics": [], "as_of": None, "as_of_input": as_of if isinstance(as_of, str) else None,
        "event_type": None, "release_date": None, "available_count": 0,
    }
    if not isinstance(event, Mapping):
        result["reason"] = "invalid_event"
        return result
    event_type = event.get("type")
    day = official._parse_iso_date(event.get("date"))
    if not isinstance(event_type, str) or day is None:
        result["reason"] = "invalid_event"
        return result
    result.update(event_type=event_type, release_date=day.isoformat())
    # Bind presentation to the exact supplied reference fields as well as the
    # event/date/cutoff. A builder changing a field must recompute the projection;
    # otherwise a previously qualified result could survive on another period.
    result["reference_binding"] = {
        name: event.get(name) for name in official._EXPLICIT_REFERENCE_FIELDS
    }
    specs = official._TARGETS.get(event_type)
    if specs is None:
        result.update(status="unsupported", reason="unsupported_event_type")
        return result
    cutoff = official._parse_iso_timestamp(as_of)
    if cutoff is None:
        result["reason"] = "invalid_as_of"
        return result
    result["as_of"] = cutoff.isoformat()
    if day > cutoff.astimezone(_NY).date():
        result["reason"] = "not_available_as_of"
        return result
    expected, error = _reference(event, event_type)
    if error:
        result["reason"] = error
        return result
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        result["reason"] = "source_unavailable"
        return result
    try:
        policy_bytes = Path(defects_path).read_bytes()
        if official._known_receipt_defect_errors({}, defects_path=defects_path):
            result["reason"] = "quarantine_policy_unavailable"
            return result
    except (OSError, ValueError, TypeError):
        result["reason"] = "quarantine_policy_unavailable"
        return result
    result["quarantine_sha256"] = hashlib.sha256(policy_bytes).hexdigest()
    source = [r for r in rows if isinstance(r, dict)]
    result["source_partial"] = len(source) != len(rows)
    result["metrics"] = [
        _metric_evidence(source, release, day.isoformat(), event_type, expected, cutoff, defects_path)
        for release, _value_key, _metric_id, _unit, _scale in specs
    ]
    try:
        policy_stable = Path(defects_path).read_bytes() == policy_bytes
    except (OSError, ValueError, TypeError):
        policy_stable = False
    if not policy_stable:
        result.update(metrics=[], reason="quarantine_policy_changed")
        return result
    count = sum(m["status"] == "available" for m in result["metrics"])
    result.update(available_count=count, status="available" if count == len(specs) else "partial" if count else "unavailable")
    return result


def attach_event_actual_evidence(
    events: Any, rows: Any, *, as_of: str,
    defects_path: str | Path = official.DEFAULT_DEFECTS_PATH,
) -> list[Any] | None:
    """Return event copies; preserve absent/empty/partial input distinctions."""
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return None
    return [
        {**event, "official_evidence": event_actual_evidence(event, rows, as_of=as_of, defects_path=defects_path)}
        if isinstance(event, dict) else event
        for event in events
    ]


def attach_recent_event_actual_evidence(
    events: Any,
    rows: Any,
    *,
    as_of: str,
    lookback_days: int = 7,
    defects_path: str | Path = official.DEFAULT_DEFECTS_PATH,
) -> list[Any] | None:
    """Attach evidence to supplied events plus recent typed releases in the ledger.

    This is a read-only bridge for a forward calendar: recently published releases
    would otherwise disappear from macro_catalysts before their first-result
    receipt can be inspected. It synthesizes only calendar-shaped rows whose
    type/date are already encoded by the canonical receipt owner.
    """
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return None
    cutoff = official._parse_iso_timestamp(as_of)
    if cutoff is None or type(lookback_days) is not int or lookback_days < 0 or lookback_days > 31:
        return attach_event_actual_evidence(events, rows, as_of=as_of, defects_path=defects_path)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return attach_event_actual_evidence(events, rows, as_of=as_of, defects_path=defects_path)

    copied = [dict(event) if isinstance(event, dict) else event for event in events]
    keys = {
        (event.get("type"), event.get("date"))
        for event in copied
        if isinstance(event, dict)
    }
    recent: set[tuple[str, str]] = set()
    cutoff_day = cutoff.astimezone(_NY).date()
    for row in rows:
        if not isinstance(row, dict) or row.get("row_type") != "actual":
            continue
        event_type = official._EVENT_BY_RELEASE.get(str(row.get("release") or ""))
        day = official._parse_iso_date(row.get("release_date"))
        if event_type is None or day is None:
            continue
        age = (cutoff_day - day).days
        if 0 <= age <= lookback_days:
            recent.add((event_type, day.isoformat()))

    for event_type, day in sorted(recent, key=lambda item: item[1], reverse=True):
        if (event_type, day) in keys:
            continue
        copied.append({
            "type": event_type,
            "date": day,
            "is_context_only": True,
            "source": "official_actual_ledger",
            "result_only": True,
        })
        keys.add((event_type, day))
    return attach_event_actual_evidence(copied, rows, as_of=as_of, defects_path=defects_path)


EXPECTATION_SCHEMA = "release_event_expectations.v1"
_BENCHMARK_KEYS = (
    "naive_prior", "trailing_3m", "trailing_4w", "ar_model", "cleveland_nowcast",
)

# Existing release-radar consumer policy degrades context after two calendar days.
# Keep this popup at least as conservative; this does not change the producer.
_FORECAST_MAX_AGE_DAYS = 2


def _finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _expectation_reference_binding(event: Mapping[str, Any]) -> dict[str, Any]:
    return {name: event.get(name) for name in official._EXPLICIT_REFERENCE_FIELDS}


def _clean_benchmark_set(value: Any, unit: str) -> dict[str, Any]:
    """Return only owner-defined display benchmarks; never relabel them as survey data."""
    if not isinstance(value, Mapping):
        return {}
    out: dict[str, Any] = {}
    for key in _BENCHMARK_KEYS:
        if _finite_number(value.get(key)):
            out[key] = value[key]
    market = value.get("market_implied")
    if isinstance(market, Mapping):
        source = market.get("source")
        asof = market.get("asof")
        median = market.get("implied_median")
        item: dict[str, Any] = {}
        if isinstance(source, str) and source in {"kalshi", "polymarket"}:
            item["source"] = source
        if isinstance(asof, str):
            item["asof"] = asof
        if _finite_number(median):
            item["implied_median"] = median
        # CPI-family implied medians share the percent target basis. Payroll
        # market ladders currently arrive as raw job counts while the model
        # target is thousands and carry no explicit unit contract. Fail closed.
        if item.get("source") and "implied_median" in item and unit == "percent":
            out["market_implied"] = item
    return out


def _forecast_point(row: Mapping[str, Any], unit: str) -> dict[str, Any]:
    """Project the producer-declared primary model context without choosing a new winner."""
    base = {
        "status": "model_point_unavailable",
        "reason": "model_point_unavailable",
        "point": None,
        "display_value": None,
        "p10": None,
        "p90": None,
        "basis": None,
        "cold_start": False,
        "n_scored_basis": None,
    }
    projection = row.get("projection")
    if not isinstance(projection, Mapping):
        return base
    if projection.get("mode") == "benchmark_only":
        return {**base, "status": "benchmark_only", "reason": "benchmark_only"}

    if row.get("primary_forecast_basis") == "combined_v1_benchmark_augmented":
        combined = row.get("combined")
        if (
            not isinstance(combined, Mapping)
            or combined.get("display_only") is not True
            or combined.get("authority") is not False
            or not _finite_number(combined.get("combined_point"))
        ):
            return {**base, "reason": "primary_model_context_invalid"}
        point = combined["combined_point"]
        p10 = combined.get("p10") if _finite_number(combined.get("p10")) else None
        p90 = combined.get("p90") if _finite_number(combined.get("p90")) else None
        parts = combined.get("combined_components")
        cold = bool(isinstance(parts, Mapping) and parts.get("cold_start") is True)
        n_scored = combined.get("n_scored_basis")
        if type(n_scored) is not int or n_scored < 0:
            n_scored = None
        basis = "combined_v1_benchmark_augmented"
    else:
        point = projection.get("point")
        if not _finite_number(point):
            return base
        p10 = projection.get("p10") if _finite_number(projection.get("p10")) else None
        p90 = projection.get("p90") if _finite_number(projection.get("p90")) else None
        cold = False
        n_scored = None
        basis = "champion_model"

    precision = 0 if unit == "thousands" else 2
    return {
        **base,
        "status": "experimental_model_context",
        "reason": None,
        "point": point,
        "display_value": f"{point:,.{precision}f}",
        "p10": p10,
        "p90": p90,
        "basis": basis,
        "cold_start": cold,
        "n_scored_basis": n_scored,
    }


def _future_expectation_metric(
    release: str,
    event_day: str,
    expected_period: str | None,
    forecast: Mapping[str, Any],
) -> dict[str, Any]:
    metric_id, unit, _scale = official._SPEC_BY_RELEASE[release]
    result: dict[str, Any] = {
        "release": release,
        "metric_id": metric_id,
        "unit": unit,
        "status": "unavailable",
        "reason": "no_matching_forecast_context",
        "period": expected_period,
        "benchmarks": {},
    }
    rows = forecast.get("upcoming")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        result["reason"] = "forecast_source_unavailable"
        return result
    matched = [
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("release_type") == release
        and row.get("release_date") == event_day
        and (expected_period is None or row.get("period") == expected_period)
    ]
    if len(matched) != 1:
        result["reason"] = "ambiguous_forecast_context" if matched else "no_matching_forecast_context"
        return result
    row = matched[0]
    period = row.get("period")
    if not isinstance(period, str) or not period:
        result["reason"] = "forecast_period_unavailable"
        return result

    point = _forecast_point(row, unit)
    benchmarks = _clean_benchmark_set(row.get("benchmark_set"), unit)
    result.update(point)
    result.update({
        "period": period,
        "benchmarks": benchmarks,
        "market_implied_status": (
            "unit_basis_unqualified"
            if unit == "thousands"
            and isinstance(row.get("benchmark_set"), Mapping)
            and isinstance(row.get("benchmark_set", {}).get("market_implied"), Mapping)
            and _finite_number(row.get("benchmark_set", {}).get("market_implied", {}).get("implied_median"))
            else None
        ),
        "model_epoch": row.get("model_epoch") if isinstance(row.get("model_epoch"), str) else None,
        "target_epoch": row.get("target_epoch") if isinstance(row.get("target_epoch"), str) else None,
        "cutoff_label": row.get("cutoff_label") if isinstance(row.get("cutoff_label"), str) else None,
        "basis_warning": row.get("basis_warning") if isinstance(row.get("basis_warning"), str) else None,
        "input_completeness": row.get("input_completeness") if _finite_number(row.get("input_completeness")) else None,
    })
    if result["status"] == "model_point_unavailable" and benchmarks:
        result["status"] = "benchmark_context"
    return result


def _scored_expectation_metric(
    release: str,
    event_day: str,
    official_metric: Mapping[str, Any],
    forecast: Mapping[str, Any],
) -> dict[str, Any]:
    metric_id, unit, _scale = official._SPEC_BY_RELEASE[release]
    period = official_metric.get("period")
    result: dict[str, Any] = {
        "release": release,
        "metric_id": metric_id,
        "unit": unit,
        "period": period,
        "status": "comparison_withheld",
        "reason": "no_matching_frozen_model_context",
        "point": None,
        "difference": None,
    }
    if not isinstance(period, str) or official_metric.get("status") != "available":
        result["reason"] = "official_result_unavailable"
        return result
    rows = forecast.get("last_scored_all_forward")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        result["reason"] = "forecast_source_unavailable"
        return result
    candidates = [
        row for row in rows
        if isinstance(row, Mapping)
        and row.get("row_type") == "scored"
        and row.get("model") in (None, "")
        and row.get("release") == release
        and row.get("period") == period
        and row.get("release_date") == event_day
        and row.get("actual_receipt_id") == official_metric.get("receipt_id")
    ]
    if len(candidates) != 1:
        result["reason"] = "ambiguous_frozen_model_context" if candidates else "no_matching_frozen_model_context"
        return result
    row = candidates[0]
    frozen_day = official._parse_iso_date(row.get("frozen_asof_night"))
    release_day = official._parse_iso_date(event_day)
    if frozen_day is None or release_day is None or frozen_day >= release_day:
        result["reason"] = "frozen_cutoff_invalid"
        return result
    row_actual = row.get("actual")
    official_actual = official_metric.get("actual")
    if (
        not _finite_number(row_actual)
        or not _finite_number(official_actual)
        or not math.isclose(row_actual, official_actual, rel_tol=0.0, abs_tol=1e-10)
    ):
        result["reason"] = "actual_binding_mismatch"
        return result
    evaluation = row.get("evaluation")
    if not isinstance(evaluation, Mapping) or evaluation.get("eligible") is not True:
        result["reason"] = "evaluation_ineligible"
        defects = evaluation.get("excluded_defect_ids") if isinstance(evaluation, Mapping) else None
        if isinstance(defects, Sequence) and not isinstance(defects, (str, bytes)):
            result["excluded_defect_ids"] = [str(v) for v in defects if isinstance(v, str)]
        return result
    point = row.get("frozen_projection_point")
    actual = official_metric.get("actual")
    if not _finite_number(point) or not _finite_number(actual):
        result["reason"] = "model_point_unavailable"
        return result

    difference = actual - point
    precision = 0 if unit == "thousands" else 2
    result.update({
        "status": "historical_model_comparison",
        "reason": None,
        "point": point,
        "display_value": f"{point:,.{precision}f}",
        "difference": difference,
        "difference_display": f"{difference:+,.{precision}f}",
        "p10": row.get("frozen_projection_p10") if _finite_number(row.get("frozen_projection_p10")) else None,
        "p90": row.get("frozen_projection_p90") if _finite_number(row.get("frozen_projection_p90")) else None,
        "frozen_asof_night": row.get("frozen_asof_night") if isinstance(row.get("frozen_asof_night"), str) else None,
        "model_epoch": row.get("model_epoch") if isinstance(row.get("model_epoch"), str) else None,
        "target_epoch": row.get("target_epoch") if isinstance(row.get("target_epoch"), str) else None,
        "cutoff_label": row.get("cutoff_label") if isinstance(row.get("cutoff_label"), str) else None,
        "evaluation_basis": evaluation.get("basis") if isinstance(evaluation.get("basis"), str) else None,
    })
    return result


def event_expectation_context(
    event: Any,
    forecast: Any,
    *,
    as_of: str,
    official_evidence: Any = None,
) -> dict[str, Any]:
    """Read-only release benchmark/model context; never a street-survey substitute."""
    result: dict[str, Any] = {
        "schema": EXPECTATION_SCHEMA,
        "display_only": True,
        "authority": False,
        "status": "unavailable",
        "reason": None,
        "as_of_input": as_of if isinstance(as_of, str) else None,
        "artifact_asof": None,
        "event_type": None,
        "release_date": None,
        "reference_binding": None,
        "street_survey_status": "unavailable",
        "metrics": [],
    }
    if not isinstance(event, Mapping):
        result["reason"] = "invalid_event"
        return result
    event_type = event.get("type")
    day = official._parse_iso_date(event.get("date"))
    if not isinstance(event_type, str) or day is None:
        result["reason"] = "invalid_event"
        return result
    result.update(
        event_type=event_type,
        release_date=day.isoformat(),
        reference_binding=_expectation_reference_binding(event),
    )
    specs = official._TARGETS.get(event_type)
    if specs is None:
        result.update(status="unsupported", reason="unsupported_event_type")
        return result

    if (
        not isinstance(forecast, Mapping)
        or forecast.get("schema") != "release_forecast.v2"
        or forecast.get("display_only") is not True
    ):
        result["reason"] = "forecast_source_unavailable"
        return result
    authority = forecast.get("authority")
    if (
        not isinstance(authority, Mapping)
        or any(authority.get(key) is not False for key in ("can_score", "can_size", "can_trade"))
    ):
        result["reason"] = "forecast_authority_contract_mismatch"
        return result
    methodology = forecast.get("methodology_status")
    if not isinstance(methodology, Mapping) or methodology.get("street_consensus") != "unavailable":
        result["reason"] = "forecast_methodology_contract_mismatch"
        return result

    cutoff = official._parse_iso_timestamp(as_of)
    artifact_asof = official._parse_iso_timestamp(forecast.get("asof"))
    if cutoff is None or artifact_asof is None:
        result["reason"] = "invalid_forecast_clock"
        return result
    if artifact_asof > cutoff:
        result["reason"] = "forecast_after_snapshot"
        return result
    artifact_age_days = (cutoff.date() - artifact_asof.date()).days
    result["artifact_asof"] = artifact_asof.isoformat()
    result["artifact_age_days"] = artifact_age_days
    result["freshness_max_age_days"] = _FORECAST_MAX_AGE_DAYS
    if artifact_age_days > _FORECAST_MAX_AGE_DAYS:
        result["reason"] = "forecast_stale"
        return result
    capture_health = forecast.get("capture_health")
    if isinstance(capture_health, Mapping):
        nightly_gap = capture_health.get("nightly_gap_days")
        result["nightly_gap_days"] = nightly_gap if type(nightly_gap) is int and nightly_gap >= 0 else None
        if type(nightly_gap) is int and nightly_gap > _FORECAST_MAX_AGE_DAYS:
            result["reason"] = "forecast_stale"
            return result
    result["methodology"] = {
        "forecast_epoch": methodology.get("forecast_epoch") if isinstance(methodology.get("forecast_epoch"), str) else None,
        "accuracy_claim": methodology.get("accuracy_claim") if isinstance(methodology.get("accuracy_claim"), str) else None,
    }

    expected, reference_error = _reference(event, event_type)
    if reference_error:
        result["reason"] = reference_error
        return result

    official_metrics: dict[str, Mapping[str, Any]] = {}
    if (
        isinstance(official_evidence, Mapping)
        and official_evidence.get("schema") == SCHEMA
        and official_evidence.get("display_only") is True
        and official_evidence.get("authority") is False
        and official_evidence.get("event_type") == event_type
        and official_evidence.get("release_date") == day.isoformat()
        and official_evidence.get("reference_binding") == result["reference_binding"]
        and official_evidence.get("as_of_input") == as_of
    ):
        metrics = official_evidence.get("metrics")
        if isinstance(metrics, Sequence) and not isinstance(metrics, (str, bytes)):
            for metric in metrics:
                if isinstance(metric, Mapping) and isinstance(metric.get("release"), str):
                    official_metrics[metric["release"]] = metric

    cutoff_day = cutoff.astimezone(_NY).date()
    projected: list[dict[str, Any]] = []
    for release, _value_key, _metric_id, _unit, _scale in specs:
        official_metric = official_metrics.get(release)
        if isinstance(official_metric, Mapping) and official_metric.get("status") == "available":
            projected.append(
                _scored_expectation_metric(
                    release, day.isoformat(), official_metric, forecast
                )
            )
            continue
        if day >= cutoff_day:
            projected.append(
                _future_expectation_metric(
                    release, day.isoformat(), expected, forecast
                )
            )
        else:
            metric_id, unit, _scale = official._SPEC_BY_RELEASE[release]
            projected.append({
                "release": release,
                "metric_id": metric_id,
                "unit": unit,
                "period": expected,
                "status": "unavailable",
                "reason": "official_result_required_for_historical_comparison",
                "benchmarks": {},
            })

    result["metrics"] = projected
    useful = [
        metric for metric in projected
        if metric.get("status") in {
            "experimental_model_context", "benchmark_only", "benchmark_context",
            "historical_model_comparison",
        }
    ]
    result["status"] = "available" if useful and len(useful) == len(projected) else "partial" if useful else "unavailable"
    return result


def attach_event_expectation_context(
    events: Any,
    forecast: Any,
    *,
    as_of: str,
) -> list[Any] | None:
    """Return event copies with benchmark/model context from the existing owner artifact."""
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)):
        return None
    out: list[Any] = []
    for event in events:
        if not isinstance(event, dict):
            out.append(event)
            continue
        copy = dict(event)
        copy["expectation_context"] = event_expectation_context(
            copy,
            forecast,
            as_of=as_of,
            official_evidence=copy.get("official_evidence"),
        )
        out.append(copy)
    return out


def compose_event_intelligence(
    events: Any,
    actual_rows: Any,
    forecast: Any,
    *,
    as_of: str,
    recent_lookback_days: int = 7,
    defects_path: str | Path = official.DEFAULT_DEFECTS_PATH,
) -> list[Any] | None:
    """Compose the two read-only evidence layers in their safe dependency order.

    Official receipts are projected first because a historical frozen-model
    comparison is only admissible when it binds the exact accepted first-result
    receipt. Future model/benchmark context may still render when the official
    source is unavailable. The inputs are not mutated and no source is fetched.
    """
    with_actuals = attach_recent_event_actual_evidence(
        events,
        actual_rows,
        as_of=as_of,
        lookback_days=recent_lookback_days,
        defects_path=defects_path,
    )
    if with_actuals is None:
        return None
    return attach_event_expectation_context(with_actuals, forecast, as_of=as_of)
