"""Pure, non-authoritative Prophet Daily Brief presentation compositor.

The compositor joins already-read owner receipts. It performs no file/network I/O,
selects no candidate, computes no B3/B4/D5 fact, owns no quote/plan/assessment
state, and creates no rank, score, sizing, order, retry, or trading authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
import json
import re
from typing import Any

from engine.prophet_entry_availability import (
    AVAILABILITY_STATES,
    EntryAvailabilityContractError,
    validate_entry_availability,
)

SCHEMA = "prophet.daily_brief_view/v1"

DECISION_STATES = frozenset({"NO_ENTRY_CLEARED", "ENTRY_CLEARED", "UNAVAILABLE"})
HEALTH_STATES = frozenset({"CURRENT", "PARTIAL", "STALE_QUOTE", "UNAVAILABLE", "EFFECT_UNKNOWN"})

_CANDIDATE_SCHEMA = "prophet.daily_brief_candidate_input/v1"
_PLAN_SCHEMA = "prophet.daily_brief_plan_input/v1"
_ASSESSMENT_SCHEMA = "prophet.daily_brief_assessment_input/v1"
_EVIDENCE_SCHEMA = "prophet.daily_brief_evidence_input/v1"
_ASSEMBLY_SCHEMA = "prophet.daily_brief_assembly_input/v1"
_RECOVERY_SCHEMA = "prophet.daily_brief_recovery_input/v1"

_BOUND_FIELDS = {
    "security_id", "episode_id", "candidate_generation_id", "market_session",
}
_NON_ENTRY_B4 = AVAILABILITY_STATES - {"ENTRY_OPEN", "UNAVAILABLE_DATA"}
_CANDIDATE_STATES = frozenset({"SELECTED"})
_PLAN_STATES = frozenset({"RELATED_SECURITY", "NONE", "UNAVAILABLE"})
_PLAN_RELATIONS = frozenset({"related_security", "none", "unavailable"})
_ASSESSMENT_STATES = frozenset({"CURRENT", "REVIEW_REQUIRED", "SUPERSEDED", "UNAVAILABLE"})
_EVIDENCE_STATES = frozenset({"CURRENT", "PARTIAL", "UNAVAILABLE"})
_ASSEMBLY_STATES = frozenset({"OK", "UNAVAILABLE", "EFFECT_UNKNOWN"})
_FORBIDDEN_KEYS = frozenset({
    "score", "probability", "weight", "size", "order", "broker", "fill",
    "position", "retry", "polling",
})
_RECEIPT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")

_AUTHORITY = {
    "can_rank": False,
    "can_set_entry": False,
    "can_size": False,
    "can_trade": False,
    "can_order": False,
    "can_retry": False,
    "can_publish_owner_facts": False,
}


class DailyBriefContractError(ValueError):
    """Raised when the presentation contract would invent or widen authority."""


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise DailyBriefContractError(f"daily brief is not canonical JSON: {exc}") from exc


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise DailyBriefContractError(f"{field} must be RFC3339 UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise DailyBriefContractError(f"{field} must be RFC3339 UTC") from exc
    if parsed.tzinfo is None:
        raise DailyBriefContractError(f"{field} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or any(ord(ch) < 32 for ch in value):
        raise DailyBriefContractError(f"{field} must be non-empty text")
    return value.strip()


def _receipt(value: object, field: str) -> str:
    text = _text(value, field)
    if not _RECEIPT_RE.fullmatch(text):
        raise DailyBriefContractError(f"{field} must be a sha256 receipt")
    return text


def _reject_forbidden(value: object, *, path: str = "input") -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key).lower()
            if key_text in _FORBIDDEN_KEYS:
                raise DailyBriefContractError(f"forbidden authority field {path}.{key}")
            _reject_forbidden(nested, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, nested in enumerate(value):
            _reject_forbidden(nested, path=f"{path}[{index}]")


def _bound_record(value: object, schema: str, name: str) -> Mapping[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("schema") != schema:
        return None
    for field in (*_BOUND_FIELDS, "owner_ref", "asof", "source_receipt", "state"):
        if not isinstance(value.get(field), str) or not str(value.get(field)).strip():
            return None
    try:
        _receipt(value.get("source_receipt"), f"{name}.source_receipt")
    except DailyBriefContractError:
        return None
    return value


def _binding(record: Mapping[str, object]) -> dict[str, str]:
    return {field: str(record[field]) for field in _BOUND_FIELDS}


def _owner_summary(record: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema": record["schema"],
        "owner_ref": record["owner_ref"],
        "state": record["state"],
        "source_receipt": record["source_receipt"],
    }


def _clock_is_future(value: object, now: datetime, field: str) -> bool:
    try:
        return _timestamp(value, field) > now
    except DailyBriefContractError:
        return True


def _recovery(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping) or value.get("schema") != _RECOVERY_SCHEMA:
        raise DailyBriefContractError("effect-unknown recovery requires exact recovery receipt")
    if value.get("state") != "EFFECT_UNKNOWN":
        raise DailyBriefContractError("effect-unknown recovery state mismatch")
    try:
        owner_ref = _text(value.get("owner_ref"), "recovery.owner_ref")
        operation_id = _text(value.get("operation_id"), "recovery.operation_id")
        carrier = _text(value.get("carrier"), "recovery.carrier")
        target = _text(value.get("target"), "recovery.target")
        _receipt(value.get("source_receipt"), "recovery.source_receipt")
    except DailyBriefContractError as exc:
        raise DailyBriefContractError("effect-unknown recovery requires operation/carrier/target") from exc
    del owner_ref  # ownership is validated but intentionally not widened into output authority.
    return {"operation_id": operation_id, "carrier": carrier, "target": target}


def _previous_fallback(previous: object, identity: Mapping[str, str]) -> dict[str, str] | None:
    if not isinstance(previous, Mapping):
        return None
    try:
        validate_daily_brief_view(previous)
    except DailyBriefContractError:
        return None
    if previous.get("identity") != dict(identity):
        return None
    return {
        "kind": "LAST_ACCEPTED_READ_ONLY",
        "view_id": str(previous["view_id"]),
        "decision_state": str(previous["decision_state"]),
        "health_state": str(previous["health_state"]),
    }


def compose_daily_brief(
    *,
    candidate: Mapping[str, object],
    entry_availability: Mapping[str, object] | None,
    plan: Mapping[str, object],
    assessment: Mapping[str, object],
    evidence: Mapping[str, object],
    assembly: Mapping[str, object],
    recovery: Mapping[str, object] | None,
    previous: Mapping[str, object] | None,
    now: str,
) -> dict[str, object]:
    """Compose one immutable Daily Brief presentation read model."""

    for name, value in (
        ("candidate", candidate), ("plan", plan), ("assessment", assessment),
        ("evidence", evidence), ("assembly", assembly), ("recovery", recovery),
    ):
        if value is not None:
            _reject_forbidden(value, path=name)

    now_dt = _timestamp(now, "now")
    issues: set[str] = set()

    cand = _bound_record(candidate, _CANDIDATE_SCHEMA, "candidate")
    plan_rec = _bound_record(plan, _PLAN_SCHEMA, "plan")
    assess = _bound_record(assessment, _ASSESSMENT_SCHEMA, "assessment")
    evid = _bound_record(evidence, _EVIDENCE_SCHEMA, "evidence")
    if cand is None:
        raise DailyBriefContractError("candidate selection receipt is malformed")
    if cand.get("state") not in _CANDIDATE_STATES:
        issues.add("SELECTION_UNAVAILABLE")
    if plan_rec is not None:
        relation = plan_rec.get("relation_state")
        exact_relation = plan_rec.get("exact_relation")
        plan_ids = plan_rec.get("plan_ids")
        if (plan_rec.get("state") not in _PLAN_STATES or relation not in _PLAN_RELATIONS
                or exact_relation not in {"unavailable", "available"}
                or not isinstance(plan_ids, list)
                or any(not isinstance(item, str) or not item for item in plan_ids)):
            issues.add("OWNER_INPUT_UNAVAILABLE")
    if assess is not None and assess.get("state") not in _ASSESSMENT_STATES:
        issues.add("OWNER_INPUT_UNAVAILABLE")
    if evid is not None and evid.get("state") not in _EVIDENCE_STATES:
        issues.add("OWNER_INPUT_UNAVAILABLE")
    if cand.get("state") != "SELECTED" or not isinstance(cand.get("selection_receipt"), str):
        issues.add("SELECTION_UNAVAILABLE")
    else:
        try:
            _receipt(cand.get("selection_receipt"), "candidate.selection_receipt")
        except DailyBriefContractError:
            issues.add("SELECTION_UNAVAILABLE")

    identity = _binding(cand)
    records = {"plan": plan_rec, "assessment": assess, "evidence": evid}
    if any(record is None for record in records.values()):
        issues.add("OWNER_INPUT_UNAVAILABLE")
    for record in records.values():
        if record is not None and _binding(record) != identity:
            issues.add("OWNER_BINDING_MISMATCH")

    clocks: dict[str, str | None] = {
        "candidate": str(cand.get("asof")),
        "quote": None,
        "plan": str(plan_rec.get("asof")) if plan_rec is not None else None,
        "assessment": str(assess.get("asof")) if assess is not None else None,
        "evidence": str(evid.get("asof")) if evid is not None else None,
        "assembly": str(assembly.get("assembled_at")) if isinstance(assembly, Mapping) else None,
    }
    for name, value in clocks.items():
        if value is not None and _clock_is_future(value, now_dt, f"clocks.{name}"):
            issues.add("FUTURE_OWNER_CLOCK")

    b4: Mapping[str, object] | None = None
    if entry_availability is None:
        issues.add("ENTRY_AVAILABILITY_UNAVAILABLE")
    elif isinstance(entry_availability, Mapping):
        try:
            validate_entry_availability(entry_availability)
            b4 = entry_availability
        except (EntryAvailabilityContractError, AssertionError, TypeError, ValueError):
            issues.add("ENTRY_AVAILABILITY_INVALID")
    else:
        issues.add("ENTRY_AVAILABILITY_INVALID")

    decision_state = "UNAVAILABLE"
    if b4 is not None:
        b4_binding = {
            "security_id": str(b4.get("security_id")),
            "episode_id": str(b4.get("episode_id")),
            "candidate_generation_id": str(b4.get("candidate_generation_id")),
            "market_session": str(b4.get("market_session")),
        }
        if b4_binding != identity:
            issues.add("OWNER_BINDING_MISMATCH")
        clocks["quote"] = str(b4.get("quote_asof"))
        if _clock_is_future(clocks["quote"], now_dt, "clocks.quote"):
            issues.add("FUTURE_OWNER_CLOCK")
        state = b4.get("state")
        if state == "ENTRY_OPEN":
            decision_state = "ENTRY_CLEARED"
        elif state in _NON_ENTRY_B4:
            decision_state = "NO_ENTRY_CLEARED"
        else:
            decision_state = "UNAVAILABLE"

    assembly_state = assembly.get("state") if isinstance(assembly, Mapping) else None
    if assembly_state not in _ASSEMBLY_STATES:
        issues.add("ASSEMBLY_UNAVAILABLE")
    if not isinstance(assembly, Mapping) or assembly.get("schema") != _ASSEMBLY_SCHEMA:
        issues.add("ASSEMBLY_UNAVAILABLE")
    else:
        try:
            _text(assembly.get("owner_ref"), "assembly.owner_ref")
            receipts = assembly.get("source_receipts")
            if not isinstance(receipts, Sequence) or isinstance(receipts, (str, bytes)) or not receipts:
                raise DailyBriefContractError("assembly.source_receipts missing")
            for item in receipts:
                _receipt(item, "assembly.source_receipts[]")
        except DailyBriefContractError:
            issues.add("ASSEMBLY_UNAVAILABLE")

    recovery_out: dict[str, str] | None = None
    if assembly_state == "EFFECT_UNKNOWN":
        recovery_out = _recovery(recovery)
        decision_state = "UNAVAILABLE"
    elif assembly_state not in {"OK", "UNAVAILABLE"}:
        issues.add("ASSEMBLY_UNAVAILABLE")
        decision_state = "UNAVAILABLE"
    elif assembly_state == "UNAVAILABLE":
        issues.add("ASSEMBLY_UNAVAILABLE")
        decision_state = "UNAVAILABLE"

    if issues & {
        "OWNER_BINDING_MISMATCH", "FUTURE_OWNER_CLOCK", "SELECTION_UNAVAILABLE",
        "OWNER_INPUT_UNAVAILABLE",
    }:
        decision_state = "UNAVAILABLE"

    evidence_state = evid.get("state") if evid is not None else None
    assessment_state = assess.get("state") if assess is not None else None
    blockers = set(b4.get("blockers") or []) if b4 is not None else set()

    if assembly_state == "EFFECT_UNKNOWN":
        health_state = "EFFECT_UNKNOWN"
    elif issues & {
        "OWNER_BINDING_MISMATCH", "FUTURE_OWNER_CLOCK", "SELECTION_UNAVAILABLE",
        "OWNER_INPUT_UNAVAILABLE", "ASSEMBLY_UNAVAILABLE",
    }:
        health_state = "UNAVAILABLE"
    elif b4 is not None and b4.get("state") == "UNAVAILABLE_DATA" and "QUOTE_STALE" in blockers:
        health_state = "STALE_QUOTE"
    elif evidence_state == "PARTIAL":
        health_state = "PARTIAL"
    elif evidence_state == "UNAVAILABLE" or assessment_state == "UNAVAILABLE":
        health_state = "UNAVAILABLE"
        decision_state = "UNAVAILABLE"
    elif b4 is None or b4.get("state") == "UNAVAILABLE_DATA":
        health_state = "UNAVAILABLE"
    else:
        health_state = "CURRENT"

    owners: dict[str, object] = {
        "candidate": _owner_summary(cand),
        "plan": _owner_summary(plan_rec) if plan_rec is not None else None,
        "assessment": _owner_summary(assess) if assess is not None else None,
        "evidence": _owner_summary(evid) if evid is not None else None,
        "entry_availability": (
            {
                "schema": b4.get("schema"),
                "state": b4.get("state"),
                "availability_id": b4.get("availability_id"),
            }
            if b4 is not None else None
        ),
        "assembly": (
            {"schema": assembly.get("schema"), "owner_ref": assembly.get("owner_ref"), "state": assembly_state}
            if isinstance(assembly, Mapping) else None
        ),
    }

    presentation: dict[str, object] = {
        "candidate": cand.get("display") if isinstance(cand.get("display"), Mapping) else {},
        "plan": (
            {
                "relation_state": plan_rec.get("relation_state"),
                "exact_relation": plan_rec.get("exact_relation"),
                "plan_ids": list(plan_rec.get("plan_ids") or []),
            }
            if plan_rec is not None else None
        ),
        "assessment": assess.get("summary") if assess is not None and isinstance(assess.get("summary"), Mapping) else None,
        "evidence": evid.get("coverage") if evid is not None and isinstance(evid.get("coverage"), Mapping) else None,
        "availability": (
            {"state": b4.get("state"), "blockers": list(b4.get("blockers") or []), "reasons": list(b4.get("reasons") or [])}
            if b4 is not None else None
        ),
    }
    _reject_forbidden(presentation, path="presentation")

    fallback = _previous_fallback(previous, identity) if health_state == "UNAVAILABLE" else None

    out: dict[str, object] = {
        "schema": SCHEMA,
        "identity": identity,
        "decision_state": decision_state,
        "health_state": health_state,
        "authority": dict(_AUTHORITY),
        "owners": owners,
        "clocks": clocks,
        "presentation": presentation,
        "issues": sorted(issues),
        "fallback": fallback,
        "recovery": recovery_out,
    }
    out["view_id"] = "pdbv:" + sha256(_canonical_json(out).encode("utf-8")).hexdigest()
    validate_daily_brief_view(out)
    return out


def validate_daily_brief_view(payload: Mapping[str, object]) -> None:
    if not isinstance(payload, Mapping):
        raise DailyBriefContractError("daily brief view must be an object")
    expected = {
        "schema", "identity", "decision_state", "health_state", "authority", "owners",
        "clocks", "presentation", "issues", "fallback", "recovery", "view_id",
    }
    if set(payload) != expected:
        raise DailyBriefContractError("daily brief view fields are not closed")
    if payload.get("schema") != SCHEMA:
        raise DailyBriefContractError("daily brief schema mismatch")
    if payload.get("decision_state") not in DECISION_STATES:
        raise DailyBriefContractError("daily brief decision state invalid")
    if payload.get("health_state") not in HEALTH_STATES:
        raise DailyBriefContractError("daily brief health state invalid")
    if payload.get("authority") != _AUTHORITY:
        raise DailyBriefContractError("daily brief authority must remain false")
    identity = payload.get("identity")
    if not isinstance(identity, Mapping) or set(identity) != _BOUND_FIELDS or not all(isinstance(identity.get(k), str) and identity.get(k) for k in _BOUND_FIELDS):
        raise DailyBriefContractError("daily brief identity binding invalid")
    _reject_forbidden(payload.get("presentation"), path="presentation")
    material = {key: value for key, value in payload.items() if key != "view_id"}
    expected_id = "pdbv:" + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    if payload.get("view_id") != expected_id:
        raise DailyBriefContractError("daily brief view_id mismatch")
