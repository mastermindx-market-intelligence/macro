"""Synthetic C0/P0 consumer exercise. Not a production schema, owner or adapter.

This module deliberately refuses non-synthetic inputs. It creates no native IDs,
permission, forecast, store, ledger, network call, or canonical lifecycle. Its
output is an ephemeral presentation fixture for existing-owner review.
"""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

PROFILE = "oli.consumer_preview.synthetic.v1"
SOURCE_NAMES = ("phase", "entry", "geometry", "quote", "support", "contradiction", "next_condition")
EXPECTED_OWNERS = {
    "phase": "prophet.candidate_state",
    "entry": "prophet.entry_availability",
    "geometry": "prophet.strategy_geometry",
    "quote": "market_data.quote",
    "support": "alpha.opportunity_evidence",
    "contradiction": "alpha.opportunity_evidence",
    "next_condition": "prophet.strategy_geometry",
}
AUTHORITY = dict.fromkeys(("can_originate_signal", "can_rank", "can_gate", "can_size", "can_execute", "can_mutate_plan"), False)
ABSENCES = {"UNAVAILABLE", "NOT_COVERED", "RIGHTS_BLOCKED", "TRANSPORT_UNAVAILABLE"}
BASE_REF_KEYS = {"owner", "schema", "native_id", "generation", "security_id", "identity_epoch"}
STRATEGY_REF_KEYS = {"strategy_owner", "strategy_id", "strategy_version"}
STRATEGY_SCOPED_OWNERS = {"prophet.candidate_state", "prophet.entry_availability",
                          "prophet.strategy_geometry", "portfolio.plan"}


class PreviewContractError(ValueError):
    """A synthetic input cannot safely demonstrate the proposed consumer contract."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise PreviewContractError(code)


def _keys(value: Any, required: set[str], optional: set[str] | None = None) -> None:
    _require(isinstance(value, dict), "OBJECT_REQUIRED")
    _require(required <= value.keys(), "REQUIRED_FIELD_MISSING")
    _require(value.keys() <= required | (optional or set()), "UNKNOWN_FIELD")


def _text(value: Any, field: str, limit: int = 1000) -> str:
    _require(isinstance(value, str) and 0 < len(value) <= limit, f"INVALID_TEXT:{field}")
    return value


def _clock(value: Any, field: str) -> datetime:
    _text(value, field, 80)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PreviewContractError(f"INVALID_CLOCK:{field}") from exc
    _require(result.tzinfo is not None and result.utcoffset() is not None, f"NAIVE_CLOCK:{field}")
    return result.astimezone(timezone.utc)


def _price(value: Any) -> str:
    _require(isinstance(value, str), "PRICE_REQUIRES_DECIMAL_STRING")
    _text(value, "price", 32)
    try:
        price = Decimal(value)
    except InvalidOperation as exc:
        raise PreviewContractError("INVALID_PRICE") from exc
    _require(price.is_finite() and price > 0, "INVALID_PRICE")
    return value


def _ref(value: Any, subject: dict, owner: str, strategy: dict) -> dict:
    keys = BASE_REF_KEYS | (STRATEGY_REF_KEYS if owner in STRATEGY_SCOPED_OWNERS else set())
    _keys(value, keys)
    for key in keys:
        _text(value[key], key, 240)
    _require(value["schema"].startswith("fixture."), "NATIVE_SCHEMA_NOT_ADMITTED")
    _require(value["native_id"].startswith("fixture:"), "NATIVE_ID_NOT_ADMITTED")
    _require(value["security_id"] == subject["security_id"], "SUBJECT_MISMATCH")
    _require(value["identity_epoch"] == subject["identity_epoch"], "IDENTITY_EPOCH_MISMATCH")
    _require(value["owner"] == owner, "OWNER_ROLE_MISMATCH")
    if owner in STRATEGY_SCOPED_OWNERS:
        _require(all(value["strategy_" + key] == strategy[key] for key in ("owner", "id", "version")),
                 "STRATEGY_REFERENCE_MISMATCH")
    return value


def _source(name: str, source: Any, subject: dict, strategy: dict, cut: datetime) -> dict:
    _keys(source, {"ref", "status", "observed_at", "known_at", "valid_until", "value", "correction_of"})
    ref = _ref(source["ref"], subject, EXPECTED_OWNERS[name], strategy)
    _text(source["status"], "status", 80)
    _require(source["status"] in ABSENCES | {"AVAILABLE"}, "UNKNOWN_AVAILABILITY")
    prior = source["correction_of"]
    if prior is not None:
        _ref(prior, subject, EXPECTED_OWNERS[name], strategy)
        _require(prior["schema"] == ref["schema"] and prior["native_id"] == ref["native_id"]
                 and prior["generation"] != ref["generation"], "INVALID_CORRECTION_LINEAGE")
    clocks = (source["observed_at"], source["known_at"], source["valid_until"])
    if source["status"] in ABSENCES:
        _require(source["value"] is None, "ABSENT_SOURCE_HAS_VALUE")
        _require(all(clock is None for clock in clocks), "ABSENT_SOURCE_HAS_CLOCK")
        return {**copy.deepcopy(source), "display_status": source["status"], "display_value": None}
    observed, known, expiry = (_clock(value, f"{name}.{key}") for key, value in zip(
        ("observed_at", "known_at", "valid_until"), clocks))
    _require(observed <= known <= expiry, "SOURCE_CLOCK_ORDER")
    if known > cut:
        status = "NOT_YET_KNOWN"
    elif cut >= expiry:
        status = "EXPIRED"
    else:
        status = "AVAILABLE"
    if status == "NOT_YET_KNOWN":
        return {**copy.deepcopy(source), "display_status": status, "display_value": None}
    _validate_value(name, source["value"], subject, strategy, cut)
    if name == "geometry":
        _require(_clock(source["value"]["basis_at"], "geometry.basis_at") <= observed,
                 "GEOMETRY_BASIS_AFTER_OBSERVATION")
    return {**copy.deepcopy(source), "display_status": status,
            "display_value": copy.deepcopy(source["value"]) if status == "AVAILABLE" else None}


def _validate_value(name: str, value: Any, subject: dict, strategy: dict, cut: datetime) -> None:
    if name == "phase":
        _keys(value, {"native_state", "reason"})
        _text(value["native_state"], "native_state", 80)
        _text(value["reason"], "reason")
    elif name == "entry":
        _keys(value, {"native_verdict", "reason", "phase_ref", "quote_ref", "geometry_ref"})
        _text(value["native_verdict"], "native_verdict", 80)
        _text(value["reason"], "reason")
        for dep in ("phase", "quote", "geometry"):
            _ref(value[dep + "_ref"], subject, EXPECTED_OWNERS[dep], strategy)
    elif name == "geometry":
        _keys(value, {"trigger", "invalidation", "currency", "price_basis", "basis_at", "opportunity_expires_at"})
        for key in ("trigger", "invalidation"):
            _price(value[key])
        for key in ("currency", "price_basis"):
            _text(value[key], key, 80)
        basis = _clock(value["basis_at"], "geometry.basis_at")
        expiry = _clock(value["opportunity_expires_at"], "geometry.opportunity_expires_at")
        _require(basis < expiry, "GEOMETRY_CLOCK_ORDER")
    elif name == "quote":
        _keys(value, {"price", "currency", "price_basis"})
        _price(value["price"])
        for key in ("currency", "price_basis"):
            _text(value[key], key, 80)
    else:
        _keys(value, {"text", "dependence_group"})
        _text(value["text"], "text")
        _text(value["dependence_group"], "dependence_group", 120)


def build_view(bundle: dict, *, audience: str = "public", viewer_id: str | None = None,
               private_plan: dict | None = None) -> dict:
    """Build a synthetic preview; never ingest a real source or mutate the input."""
    _keys(bundle, {"profile", "synthetic", "scenario", "subject", "strategy", "decision_at", "sources", "forecasts"})
    _require(bundle["profile"] == PROFILE and bundle["synthetic"] is True, "SYNTHETIC_ONLY")
    _require(audience in {"public", "private"}, "INVALID_AUDIENCE")
    _require(bundle["forecasts"] is None, "UNQUALIFIED_FORECAST")
    _text(bundle["scenario"], "scenario", 180)
    subject = bundle["subject"]
    _keys(subject, {"security_id", "identity_epoch", "ticker", "name"})
    for key in subject:
        _text(subject[key], key, 240)
    _require(subject["security_id"].startswith("fixture:security:"), "NATIVE_ID_NOT_ADMITTED")
    strategy = bundle["strategy"]
    _keys(strategy, {"owner", "id", "version", "label", "holding_horizon"})
    for key in strategy:
        _text(strategy[key], key, 240)
    _require(strategy["id"].startswith("fixture:"), "NATIVE_STRATEGY_NOT_ADMITTED")
    cut = _clock(bundle["decision_at"], "decision_at")
    _keys(bundle["sources"], set(SOURCE_NAMES))
    source_views = {name: _source(name, bundle["sources"][name], subject, strategy, cut) for name in SOURCE_NAMES}
    entry = source_views["entry"]
    if entry["display_status"] == "AVAILABLE":
        value = entry["display_value"]
        for dep in ("phase", "quote", "geometry"):
            other = source_views[dep]
            if other["display_status"] != "AVAILABLE":
                entry["display_status"] = "DEPENDENCY_UNAVAILABLE"
                entry["display_value"] = None
                break
            if value[dep + "_ref"] != other["ref"]:
                entry["display_status"] = "GENERATION_MISMATCH"
                entry["display_value"] = None
                break
            if _clock(other["known_at"], dep + ".known_at") > _clock(entry["known_at"], "entry.known_at"):
                entry["display_status"] = "DEPENDENCY_NOT_KNOWN_AT_ENTRY"
                entry["display_value"] = None
                break
        if entry["display_value"] is not None:
            geometry = source_views["geometry"]["display_value"]
            quote = source_views["quote"]["display_value"]
            if any(geometry[k] != quote[k] for k in ("currency", "price_basis")):
                entry["display_status"] = "BASIS_MISMATCH"
                entry["display_value"] = None
            elif _clock(geometry["opportunity_expires_at"], "opportunity_expires_at") <= cut:
                entry["display_status"] = "OPPORTUNITY_EXPIRED"
                entry["display_value"] = None
    plan_view = {"status": "PRIVATE_CONTEXT_NOT_JOINED", "native_state": None, "has_position": None}
    # Public composition never validates, echoes or serializes the private argument.
    if audience == "private":
        _text(viewer_id, "viewer_id", 240)
        if private_plan is None:
            plan_view["status"] = "PRIVATE_OWNER_UNAVAILABLE"
        else:
            _keys(private_plan, {"synthetic", "viewer_id", "ref", "native_state", "has_position", "known_at", "valid_until"})
            _require(private_plan["synthetic"] is True, "SYNTHETIC_ONLY")
            _require(private_plan["viewer_id"] == viewer_id, "PRIVATE_ACCOUNT_MISMATCH")
            _ref(private_plan["ref"], subject, "portfolio.plan", strategy)
            _text(private_plan["native_state"], "plan.native_state", 80)
            _require(private_plan["has_position"] is None or type(private_plan["has_position"]) is bool, "INVALID_POSITION_FACT")
            known = _clock(private_plan["known_at"], "plan.known_at")
            expiry = _clock(private_plan["valid_until"], "plan.valid_until")
            _require(known < expiry, "PLAN_CLOCK_ORDER")
            if known <= cut < expiry:
                plan_view = {"status": "AVAILABLE", "native_state": private_plan["native_state"],
                             "has_position": private_plan["has_position"], "ref": copy.deepcopy(private_plan["ref"])}
            else:
                plan_view["status"] = "PRIVATE_OWNER_EXPIRED_OR_FUTURE"
    output = {
        "profile": PROFILE, "synthetic": True, "scenario": bundle["scenario"],
        "subject": copy.deepcopy(subject), "strategy": copy.deepcopy(strategy),
        "decision_at": bundle["decision_at"], "audience": audience,
        "sources": source_views, "plan": plan_view,
        "forecasts": None, "forecast_status": "NOT_QUALIFIED",
        "authority": dict(AUTHORITY),
        "degradations": [{"source": name, "status": s["display_status"]}
                         for name, s in source_views.items() if s["display_status"] != "AVAILABLE"],
    }
    # Do not retain unavailable value bytes or future facts in the machine/UI view.
    for s in source_views.values():
        s.pop("value", None)
    output["content_sha256"] = hashlib.sha256(canonical_bytes(output)).hexdigest()
    return output


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
