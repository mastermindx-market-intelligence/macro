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
    parse = official._parse_week_reference if event_type == "CLAIMS" else official._parse_month_reference
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
