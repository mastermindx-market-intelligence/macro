"""Pure, non-voting cross-asset observations for the existing Risk Envelope.

This module qualifies evidence and compares measured returns. It never estimates
expected return, ranks investments, reads a clock/store, or authorizes an action.
Availability is a caller-attested source fact, not established by a hash/schema.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from numbers import Real
from typing import Any

SCHEMA = "mastermind.multi_asset_context/v1"
METHOD_VERSION = "same_window_measured_return.v1"
MAX_OBSERVATIONS = 512
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@-]{0,255}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")
IDENTITIES = ("observation_id", "instrument_id", "revision_id", "source_id",
              "evidence_family_id", "asset_class", "market")
CLOCKS = ("period_start", "period_end", "available_at", "received_at", "valid_until")
FIELDS = IDENTITIES + ("currency", "return_basis", "return_value", "evidence_kind") + CLOCKS
EXTRAS = ("availability_basis", "vintage_basis", "rights_ref", "source_digest",
          "source_lineage", "evidence_families", "conversion", "source_session",
          "fx_base_currency", "fx_quote_currency", "fx_convention")


def authority() -> dict[str, bool]:
    return {key: False for key in ("can_rank", "can_gate", "can_size", "can_trade")}


def instant(value: Any) -> datetime:
    """Parse an explicitly timezone-aware ISO instant; never guess a timezone."""
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("aware_iso_instant_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("naive_instant")
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError("aware_iso_instant_required") from exc


def stamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, Real):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, ValueError, TypeError):
        return False


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _safe(value: Any, depth: int = 0) -> Any:
    """Bound JSON evidence normalization without repr(), code or source mutation."""
    if depth > 8:
        return {"invalid": "excessive_depth"}
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, str):
        if len(value) <= 4096:
            return value
        return {"invalid": "oversized_string", "sha256": hashlib.sha256(value.encode()).hexdigest()}
    if _number(value):
        return float(value)
    if isinstance(value, Real):
        return {"invalid": "nonfinite_or_overflow_number"}
    if isinstance(value, Mapping):
        if len(value) > 128 or not all(isinstance(k, str) for k in value):
            return {"invalid": "mapping_shape"}
        return {k: _safe(v, depth + 1) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        if len(value) > 512:
            return {"invalid": "oversized_sequence"}
        return [_safe(v, depth + 1) for v in value]
    return {"invalid": "unsupported_type"}


def _evidence(value: Any) -> Any:
    if not isinstance(value, Mapping):
        return {"invalid": "observation_not_mapping"}
    result = {key: _safe(value[key]) for key in FIELDS + EXTRAS + ("authority",)
              if key in value}
    for key in CLOCKS:
        if key in value:
            try:
                result[key] = stamp(instant(value[key]))
            except ValueError:
                pass
    return result


def _digest(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("ascii")).hexdigest()


def _unavailable(reasons: Sequence[str]) -> dict[str, Any]:
    return {"status": "UNAVAILABLE", "observation": None, "reasons": sorted(set(reasons))}


def qualify_observation(value: Mapping[str, Any], *, as_of: str) -> dict[str, Any]:
    """Qualify one return at an explicit cutoff; malformed rows become unavailable."""
    now = instant(as_of)
    if not isinstance(value, Mapping):
        return _unavailable(["observation_not_mapping"])
    reasons: list[str] = []
    for key in IDENTITIES:
        if not _identifier(value.get(key)):
            reasons.append("invalid_" + key)
    if not isinstance(value.get("currency"), str) or not _CURRENCY.fullmatch(value["currency"]):
        reasons.append("invalid_currency")
    if value.get("return_basis") not in ("price_return", "total_return"):
        reasons.append("unsupported_return_basis")
    if value.get("evidence_kind") != "measured_return":
        reasons.append("not_measured_return")
    if not _number(value.get("return_value")):
        reasons.append("invalid_return_value")
    elif float(value["return_value"]) < -1:
        reasons.append("return_below_total_loss")
    supplied_authority = value.get("authority")
    if supplied_authority is not None and (
        not isinstance(supplied_authority, Mapping)
        or any(v is not False for v in supplied_authority.values())
    ):
        reasons.append("authority_escalation")
    if "evidence_families" in value and (
        not isinstance(value["evidence_families"], list)
        or len(value["evidence_families"]) > 128
        or not all(_identifier(v) for v in value["evidence_families"])
    ):
        reasons.append("invalid_evidence_families")
    if "source_lineage" in value and (
        not isinstance(value["source_lineage"], list)
        or len(value["source_lineage"]) > 128
        or not all(isinstance(v, Mapping) and all(_identifier(v.get(k)) for k in
                   ("observation_id", "revision_id", "source_id", "evidence_family_id"))
                   for v in value["source_lineage"])
    ):
        reasons.append("invalid_source_lineage")
    clocks: dict[str, datetime] = {}
    for key in CLOCKS:
        try:
            clocks[key] = instant(value.get(key))
        except ValueError:
            reasons.append("invalid_" + key)
    if len(clocks) == len(CLOCKS):
        if clocks["period_start"] >= clocks["period_end"]:
            reasons.append("invalid_period")
        if clocks["period_end"] > clocks["available_at"]:
            reasons.append("available_before_period_end")
        if clocks["available_at"] > clocks["received_at"]:
            reasons.append("received_before_available")
        if clocks["available_at"] > now:
            reasons.append("not_yet_available")
        if clocks["received_at"] > now:
            reasons.append("not_yet_received")
        if clocks["valid_until"] < clocks["received_at"]:
            reasons.append("invalid_validity")
        if now >= clocks["valid_until"]:
            reasons.append("expired")
    if reasons:
        return _unavailable(reasons)
    normalized = {key: value[key] for key in IDENTITIES + ("currency", "return_basis", "evidence_kind")}
    normalized.update({key: stamp(clock) for key, clock in clocks.items()})
    normalized["return_value"] = float(value["return_value"])
    normalized.update({key: _safe(value[key]) for key in EXTRAS if key in value})
    return {"status": "QUALIFIED", "observation": normalized, "reasons": []}


def measured_comparison(candidate: Any, benchmark: Any) -> dict[str, Any]:
    """Arithmetic only; the caller must independently qualify both observations."""
    if (not _number(candidate) or not _number(benchmark)
            or float(candidate) < -1 or float(benchmark) < -1):
        return {"relative_return": None, "classification": None, "reasons": ["invalid_return_value"]}
    if float(benchmark) == -1:
        return {"relative_return": None, "classification": None, "reasons": ["benchmark_zero_wealth"]}
    try:
        relative = (1.0 + float(candidate)) / (1.0 + float(benchmark)) - 1.0
    except (OverflowError, ZeroDivisionError):
        relative = math.inf
    if not math.isfinite(relative):
        return {"relative_return": None, "classification": None, "reasons": ["relative_return_overflow"]}
    classification = ("POSITIVE_AND_OUTPERFORMING" if relative > 0 and candidate > 0
                      else "RELATIVE_RESILIENCE_ONLY" if relative > 0
                      else "UNDERPERFORMING" if relative < 0 else "IN_LINE")
    return {"relative_return": relative, "classification": classification, "reasons": []}


def compose_context(observations: Sequence[Mapping[str, Any]], *, as_of: str,
                    benchmark_instrument_id: str, base_currency: str) -> dict[str, Any]:
    """Compare measured, same-window/base/basis returns without performance ranking."""
    now = stamp(instant(as_of))
    if (not isinstance(observations, Sequence) or isinstance(observations, (str, bytes))
            or len(observations) > MAX_OBSERVATIONS):
        raise ValueError("bounded_observation_sequence_required")
    if not _identifier(benchmark_instrument_id):
        raise ValueError("benchmark_instrument_id_required")
    if not isinstance(base_currency, str) or not _CURRENCY.fullmatch(base_currency):
        raise ValueError("base_currency_required")
    duplicate_counts = {
        key: Counter(row.get(key) for row in observations
                     if isinstance(row, Mapping) and _identifier(row.get(key)))
        for key in ("instrument_id", "observation_id")
    }
    qualified: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for row in observations:
        checked = qualify_observation(row, as_of=now)
        reasons = list(checked["reasons"])
        for key, counts in duplicate_counts.items():
            if isinstance(row, Mapping) and _identifier(row.get(key)) and counts[row[key]] > 1:
                reasons.append("duplicate_" + key)
        if checked["observation"] and checked["observation"]["currency"] != base_currency:
            reasons.append("base_currency_mismatch")
        if reasons:
            exclusions.append({
                **{key: row.get(key) if isinstance(row, Mapping) and _identifier(row.get(key)) else None
                   for key in ("instrument_id", "observation_id", "revision_id")},
                "reasons": sorted(set(reasons)), "evidence_digest": _digest(_evidence(row)),
            })
        else:
            qualified.append(checked["observation"])
    qualified.sort(key=lambda row: row["instrument_id"])
    exclusions.sort(key=_json)
    benchmark = next((row for row in qualified if row["instrument_id"] == benchmark_instrument_id), None)
    comparisons: list[dict[str, Any]] = []
    reasons = [] if benchmark else ["benchmark_unavailable"]
    if benchmark:
        for row in qualified:
            if row["instrument_id"] == benchmark_instrument_id:
                continue
            errors = []
            if (row["period_start"], row["period_end"]) != (benchmark["period_start"], benchmark["period_end"]):
                errors.append("period_mismatch")
            if row["return_basis"] != benchmark["return_basis"]:
                errors.append("return_basis_mismatch")
            arithmetic = measured_comparison(row["return_value"], benchmark["return_value"])
            errors.extend(arithmetic["reasons"])
            relative = arithmetic["relative_return"] if not errors else None
            classification = arithmetic["classification"] if not errors else None
            comparisons.append({
                "instrument_id": row["instrument_id"], "benchmark_instrument_id": benchmark_instrument_id,
                "observation_id": row["observation_id"], "benchmark_observation_id": benchmark["observation_id"],
                "status": "UNAVAILABLE" if errors else "AVAILABLE", "reasons": errors,
                "candidate_return": row["return_value"], "benchmark_return": benchmark["return_value"],
                "relative_return": relative, "classification": classification,
                "currency": base_currency, "return_basis": row["return_basis"],
                "period_start": row["period_start"], "period_end": row["period_end"],
                "asset_class": row["asset_class"], "market": row["market"],
                "evidence_family_id": row["evidence_family_id"],
            })
    comparable = sum(row["status"] == "AVAILABLE" for row in comparisons)
    status = ("PARTIAL" if exclusions or comparable < len(comparisons) else "AVAILABLE") if comparable else "UNAVAILABLE"
    if benchmark and not comparable:
        reasons.append("no_comparable_returns")
    evidence = sorted((_evidence(row) for row in observations), key=_json)
    result = {
        "schema": SCHEMA, "method_version": METHOD_VERSION, "as_of": now,
        "benchmark_instrument_id": benchmark_instrument_id, "base_currency": base_currency,
        "status": status, "reasons": reasons, "display_only": True,
        "no_predictive_claim": True, "authority": authority(),
        "coverage": {"observations": len(observations), "qualified": len(qualified),
                     "excluded": len(exclusions), "comparable": comparable},
        "observations": qualified, "exclusions": exclusions, "comparisons": comparisons,
        "input_digest": _digest({"observations": evidence, "benchmark": benchmark_instrument_id,
                                 "base_currency": base_currency}),
    }
    result["context_digest"] = _digest(result)
    return result


def convert_currency(local: Mapping[str, Any], fx: Mapping[str, Any], *, as_of: str,
                     base_currency: str) -> dict[str, Any]:
    """Compound local return with a qualified base-per-local FX return, once."""
    instant(as_of)
    if not isinstance(base_currency, str) or not _CURRENCY.fullmatch(base_currency):
        raise ValueError("base_currency_required")
    left, right = qualify_observation(local, as_of=as_of), qualify_observation(fx, as_of=as_of)
    errors = ["local_" + reason for reason in left["reasons"]] + ["fx_" + reason for reason in right["reasons"]]
    if errors:
        return _unavailable(errors)
    a, b = left["observation"], right["observation"]
    if a["currency"] == base_currency or a.get("conversion") is not None:
        errors.append("already_converted_or_base_currency")
    if b["asset_class"] != "fx" or b["return_basis"] != "price_return":
        errors.append("invalid_fx_instrument_or_basis")
    if (b.get("fx_base_currency") != base_currency or b.get("fx_quote_currency") != a["currency"]
            or b.get("fx_convention") != "base_per_local" or b["currency"] != base_currency):
        errors.append("fx_direction_mismatch")
    if (a["period_start"], a["period_end"]) != (b["period_start"], b["period_end"]):
        errors.append("fx_period_mismatch")
    if errors:
        return _unavailable(errors)
    try:
        converted = (1.0 + a["return_value"]) * (1.0 + b["return_value"]) - 1.0
    except OverflowError:
        return _unavailable(["converted_return_overflow"])
    if not math.isfinite(converted):
        return _unavailable(["converted_return_overflow"])
    ancestry = [{k: row[k] for k in ("observation_id", "revision_id", "source_id", "evidence_family_id")}
                for row in (a, b)]
    identity = _digest({"local": a, "fx": b, "base_currency": base_currency})
    derived = dict(a)
    derived.update({
        "observation_id": "fx-converted:" + identity, "revision_id": identity,
        "currency": base_currency, "return_value": converted,
        "available_at": stamp(max(instant(a["available_at"]), instant(b["available_at"]))),
        "received_at": stamp(max(instant(a["received_at"]), instant(b["received_at"]))),
        "valid_until": stamp(min(instant(a["valid_until"]), instant(b["valid_until"]))),
        "source_lineage": ancestry,
        "evidence_families": sorted(set([a["evidence_family_id"], b["evidence_family_id"]]
                                       + a.get("evidence_families", []) + b.get("evidence_families", []))),
        "conversion": {"method": "compound_base_per_local.v1", "from_currency": a["currency"],
                       "to_currency": base_currency, "local_return": a["return_value"], "fx_return": b["return_value"]},
    })
    result = qualify_observation(derived, as_of=as_of)
    result["ancestry"] = ancestry
    return result
