"""Deterministic diagnostics beside the incumbent Options scenario owner.

No collection, pricing kernel, publication, empirical probability or trade effect.
Inputs are caller-supplied evidence; a digest proves byte identity, not source truth.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math

_AUTHORITY = {key: False for key in (
    "calibrated_probability", "actual_dealer_inventory", "executed_flow",
    "trading", "ranking", "portfolio", "sizing", "auto_exit", "can_publish",
)}
_VARIANCE_BASES = {"risk_neutral_integrated_variance", "atm_iv_squared_time_proxy"}
_VARIANCE_FIELDS = {
    "security_id", "window_start", "window_end", "variance_basis", "return_basis", "unit",
    "method_ref", "value", "source_ref", "source_revision", "observed_at", "known_at",
}


def _wire(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("input must be finite JSON data") from exc


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError(f"{field} must be nonempty bounded text")
    return value


def _clock(value, field):
    _text(value, field)
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an aware timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError(f"{field} must be an aware timestamp")
    return stamp.astimezone(timezone.utc)


def _number(value, field, *, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite JSON number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{field} must be finite") from exc
    if not math.isfinite(result) or (minimum is not None and result < minimum):
        raise ValueError(f"{field} is outside its finite domain")
    return result


def _seal(out, prefix):
    out["content_id"] = prefix + sha256(_wire(out).encode()).hexdigest()
    return out


def _variance_record(record, name, cutoff):
    if not isinstance(record, dict) or set(record) != _VARIANCE_FIELDS:
        raise ValueError(f"{name} must use the exact matched-variance contract")
    for key in ("security_id", "method_ref", "source_ref", "source_revision"):
        _text(record[key], f"{name}.{key}")
    if record["variance_basis"] not in _VARIANCE_BASES:
        raise ValueError("unknown variance basis")
    if record["return_basis"] not in {"log_return", "simple_return"}:
        raise ValueError("return_basis must distinguish log and simple returns")
    if record["unit"] != "return_decimal_squared":
        raise ValueError("variance must be integrated return-decimal-squared, not IV or vol points")
    start = _clock(record["window_start"], "window_start")
    end = _clock(record["window_end"], "window_end")
    observed = _clock(record["observed_at"], "observed_at")
    known = _clock(record["known_at"], "known_at")
    if not observed <= known <= cutoff or not start <= cutoff < end:
        raise ValueError("variance receipt violates decision-time availability or forward window")
    if not start < end:
        raise ValueError("variance window must be positive")
    _number(record["value"], "integrated variance", minimum=0)
    return start, end, observed


def build_event_variance_diagnostic(
    *, event_id: str, event_at: str, event_known_at: str, event_source_ref: str,
    as_of: str, observed: dict, counterfactual: dict,
    calendar_complete: bool | None = None, overlap_event_ids: list[str] | None = None,
    max_source_age_seconds: float = 60.0,
) -> dict:
    """Matched-window excess implied variance, conditional on an explicit baseline.

    ATM-IV-squared-time is preserved as a proxy, never relabeled model-free variance.
    The isolated-event value is withheld without known complete overlap coverage.
    A negative residual is retained; it is not floored to zero. No causal claim or
    physical event probability follows from a positive residual or its square root.
    """
    for value, name in ((event_id, "event_id"), (event_source_ref, "event_source_ref")):
        _text(value, name)
    cutoff = _clock(as_of, "as_of")
    event_clock = _clock(event_at, "event_at")
    if _clock(event_known_at, "event_known_at") > cutoff:
        raise ValueError("event was not known by decision time")
    max_age = _number(max_source_age_seconds, "max_source_age_seconds", minimum=0)
    if max_age == 0:
        raise ValueError("source-age limit must be positive")
    if calendar_complete is not None and not isinstance(calendar_complete, bool):
        raise ValueError("calendar_complete must be bool or null")
    if overlap_event_ids is not None:
        if not isinstance(overlap_event_ids, list):
            raise ValueError("overlap_event_ids must be a list or null")
        for item in overlap_event_ids:
            _text(item, "overlap event id")
        if len(set(overlap_event_ids)) != len(overlap_event_ids) or event_id in overlap_event_ids:
            raise ValueError("overlap IDs must be unique and exclude the selected event")
    o_start, o_end, o_time = _variance_record(observed, "observed", cutoff)
    b_start, b_end, b_time = _variance_record(counterfactual, "counterfactual", cutoff)
    if (o_start, o_end) != (b_start, b_end) or any(
        observed[key] != counterfactual[key] for key in ("security_id", "variance_basis", "return_basis", "unit")
    ):
        raise ValueError("observed and baseline must share instrument, window, basis and units")
    if o_time != b_time:
        raise ValueError("observed and baseline must share a valuation clock")
    if not o_start < event_clock <= o_end or event_clock <= cutoff:
        raise ValueError("selected event must remain ahead and lie inside the priced window")
    inputs = dict(event_id=event_id, event_at=event_at, event_known_at=event_known_at,
                  event_source_ref=event_source_ref, as_of=as_of, observed=observed,
                  counterfactual=counterfactual, calendar_complete=calendar_complete,
                  overlap_event_ids=overlap_event_ids, max_source_age_seconds=max_age)
    _wire(inputs)
    reasons = []
    if max((cutoff - o_time).total_seconds(), (cutoff - b_time).total_seconds()) > max_age:
        reasons.append("stale_variance_evidence")
    isolated = calendar_complete is True and overlap_event_ids == []
    attribution_reasons = ([] if isolated else
        ["overlap_present" if overlap_event_ids else "event_overlap_coverage_unknown"])
    residual = None if reasons else observed["value"] - counterfactual["value"]
    if residual is not None and not math.isfinite(residual):
        reasons.append("nonfinite_variance_difference")
        residual = None
    positive = residual is not None and residual >= 0
    out = {
        "schema": "options.event_variance_diagnostic/v1", "evidence_class": "BASELINE_CONDITIONAL",
        "inputs": deepcopy(inputs), "status": "unavailable" if reasons else "available",
        "excess_window_variance": residual,
        "isolated_event_variance": residual if isolated and positive else None,
        "isolated_event_rms_move_pct": 100 * math.sqrt(residual) if isolated and positive else None,
        "residual_state": "unavailable" if residual is None else
            "baseline_exceeds_observed" if residual < 0 else "nonnegative",
        "attribution_reasons": attribution_reasons +
            (["negative_residual"] if residual is not None and residual < 0 else []),
        "unavailable_reasons": reasons, "authority": dict(_AUTHORITY),
        "warnings": [
            "Difference is conditional on the supplied counterfactual, not identified event causality.",
            "Risk-neutral option pricing and an ATM proxy are not physical probabilities.",
            "Square root of excess variance is an RMS scale, not expected absolute return or direction.",
            "Caller-supplied source references are not independently verified by this calculation.",
        ],
    }
    return _seal(out, "event-variance:")


def _verified_target(value):
    if not isinstance(value, dict) or value.get("schema") != "options.hedge_target_change/v1":
        raise ValueError("requires incumbent hedge-target artifact")
    content = {key: item for key, item in value.items() if key != "content_id"}
    expected = "hedge-target:" + sha256(_wire(content).encode()).hexdigest()
    if value.get("content_id") != expected:
        raise ValueError("hedge-target content identity mismatch")
    if value.get("evidence_class") != "SCENARIO" or value.get("authority") != _AUTHORITY:
        raise ValueError("requires a non-authoritative inventory scenario")
    return value


def compare_hedge_path_targets(*, checkpoint: dict, terminal: dict, path_ref: str) -> dict:
    """Remaining hedge-target adjustment along two explicitly paired scenario endpoints.

    Both endpoints share the original decision/anchor/source/universe and starting
    inventory. Endpoint IV, spot and ending inventory may differ along the supplied
    path. This is not observed flow or a live exhaustion detector. Notional uses the
    terminal spot times the remaining RISK UNITS, never subtraction of marked books.
    """
    _text(path_ref, "path_ref")
    a, b = _verified_target(checkpoint), _verified_target(terminal)
    reasons = []
    if any(value.get("status") != "complete_for_supplied_universe" for value in (a, b)):
        reasons.append("incomplete_scenario_endpoint")
    for key in ("root", "observed_at", "as_of", "spot", "source_receipt", "units",
                "inventory_scenario_id", "coverage"):
        if a.get(key) != b.get(key):
            reasons.append("incompatible_" + key)
    for key in ("pricing", "pricing_convention", "r", "q", "year_days", "max_source_age_seconds"):
        if a.get("assumptions", {}).get(key) != b.get("assumptions", {}).get(key):
            reasons.append("incompatible_pricing_assumption")
    def anchor_rows(value):
        return [{k: row.get(k) for k in ("contract_id", "option_root", "expiry", "right", "strike",
                 "multiplier", "settlement", "fixing_at", "iv", "n0")} for row in value["contracts"]]
    if anchor_rows(a) != anchor_rows(b):
        reasons.append("incompatible_anchor_book")
    if _clock(a["target_at"], "checkpoint.target_at") >= _clock(b["target_at"], "terminal.target_at"):
        reasons.append("unordered_scenario_endpoints")
    if _clock(a["target_at"], "checkpoint.target_at") < _clock(a["as_of"], "as_of"):
        reasons.append("checkpoint_precedes_decision")
    remaining = notional = None
    if not reasons:
        completed = _number(a["hedge"]["target_change"], "checkpoint target change")
        total = _number(b["hedge"]["target_change"], "terminal target change")
        remaining = total - completed
        notional = _number(b["target_spot"], "terminal spot", minimum=0) * remaining
        if not math.isfinite(remaining) or not math.isfinite(notional):
            reasons.append("nonfinite_remaining_target")
            remaining = notional = None
    out = {
        "schema": "options.hedge_path_diagnostic/v1", "evidence_class": "SCENARIO",
        "path_ref": path_ref, "checkpoint_content_id": a["content_id"], "terminal_content_id": b["content_id"],
        "as_of": a["as_of"], "checkpoint_at": a["target_at"], "terminal_at": b["target_at"],
        "status": "unavailable" if reasons else "available", "unavailable_reasons": sorted(set(reasons)),
        "remaining_target_change": remaining, "reference_notional_usd": notional,
        "remaining_direction": "unavailable" if remaining is None else
            "buy" if remaining > 0 else "sell" if remaining < 0 else "flat",
        "units": deepcopy(a["units"]), "authority": dict(_AUTHORITY),
        "actual_exhaustion_probability": None,
        "warnings": [
            "Conditional endpoint difference, not executed hedge volume or path turnover.",
            "Pairing is supplied by the caller; content integrity does not establish market truth.",
            "Remaining direction is hedge-target direction, not an equity-return forecast.",
            "Actual unwind exhaustion and directional-turn probabilities remain unvalidated.",
        ],
    }
    return _seal(out, "hedge-path:")
