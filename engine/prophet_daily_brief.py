"""Pure, non-authoritative Prophet Daily Brief presentation compositor.

The compositor joins already-read owner receipts. It performs no file/network I/O,
selects no candidate, computes no B3/B4/D5 fact, owns no quote/plan/assessment
state, and creates no rank, score, sizing, order, retry, or trading authority.

The Daily Brief quote owner is a separate, caller-supplied latest-quote reader
(``prophet.daily_brief_quote_input/v1``).  It is joined, never merged into the
B4 entry-availability receipt: a supplied quote cannot renew B4 clocks, recompute
B4 state, or promote a B4 result, and B4's ``quote_asof`` remains visible as its
own ``entry_availability_quote`` clock.  The quote receipt's shape is not
authentication: the caller owes native provenance and access validation for the
quote it supplies; this module validates only the presentation contract.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import re

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
_QUOTE_SCHEMA = "prophet.daily_brief_quote_input/v1"
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
_QUOTE_STATES = frozenset({"CURRENT", "STALE", "UNAVAILABLE"})
_ASSEMBLY_STATES = frozenset({"OK", "UNAVAILABLE", "EFFECT_UNKNOWN"})
_FORBIDDEN_KEYS = frozenset({
    "score", "probability", "weight", "size", "order", "broker", "fill",
    "position", "retry", "polling",
})
_RECEIPT_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_TIMESTAMP_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
)

# Issues that fail the whole view closed regardless of any owner's native state.
_HARD_ISSUES = frozenset({
    "OWNER_BINDING_MISMATCH", "FUTURE_OWNER_CLOCK", "MALFORMED_OWNER_CLOCK",
    "SELECTION_UNAVAILABLE", "OWNER_INPUT_UNAVAILABLE", "ASSEMBLY_UNAVAILABLE",
    "ENTRY_AVAILABILITY_UNAVAILABLE", "ENTRY_AVAILABILITY_INVALID",
})

_AUTHORITY = {
    "can_rank": False,
    "can_set_entry": False,
    "can_size": False,
    "can_trade": False,
    "can_order": False,
    "can_retry": False,
    "can_publish_owner_facts": False,
}

_CLOCK_FIELDS = frozenset({
    "candidate", "quote", "entry_availability", "entry_availability_quote",
    "plan", "assessment", "evidence", "assembly",
})


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
    if not isinstance(value, str) or not _TIMESTAMP_RE.fullmatch(value):
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


def _is_state(value: object, states: frozenset[str]) -> bool:
    """Membership test that tolerates unhashable malformed JSON values."""
    return isinstance(value, str) and value in states


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


def _clock_is_malformed(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return True
    try:
        _timestamp(value, "clock")
    except DailyBriefContractError:
        return True
    return False


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


def _quote_unavailable_presentation() -> dict[str, object]:
    # A quote that is unavailable or rejected may not carry any price fact.
    return {"state": "UNAVAILABLE", "observed_at": None, "price": None, "basis": None}


def _owner_string_list(value: object, issues: set[str]) -> list[str]:
    """Extract a B4 string list, failing closed on anything outside the contract."""
    if value is None:
        return []
    if (not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray))
            or not all(isinstance(item, str) for item in value)):
        issues.add("ENTRY_AVAILABILITY_INVALID")
        return []
    return list(value)


def _positive_number(value: object, field: str) -> float | int:
    """Positive finite non-bool number; huge integers stay exact."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DailyBriefContractError(f"{field} must be numeric")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise DailyBriefContractError(f"{field} must be finite")
        if value <= 0:
            raise DailyBriefContractError(f"{field} must be > 0")
        return value
    if value <= 0:
        raise DailyBriefContractError(f"{field} must be > 0")
    try:
        if not math.isfinite(float(value)):
            raise DailyBriefContractError(f"{field} must be finite")
    except OverflowError:
        pass  # an integer too large for float is still finite and exact
    return value


def _prices_agree(left: object, right: object) -> bool:
    """Exact integer comparison, tolerant float comparison, no raw exceptions."""
    try:
        if (isinstance(left, int) and isinstance(right, int)
                and not isinstance(left, bool) and not isinstance(right, bool)):
            return left == right
        return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=1e-12)
    except (TypeError, ValueError, OverflowError):
        return False


def _quote_owner(
    quote: object,
    *,
    identity: Mapping[str, str],
    now_dt: datetime,
    b4_quote_asof: object,
    b4_price: object,
    b4_basis: object,
    issues: set[str],
) -> tuple[dict[str, object] | None, dict[str, object], str | None, str]:
    """Validate the caller-supplied quote owner without ever merging it into B4.

    Returns ``(owners entry, presentation, quote clock, effective state)``.  Any
    malformed, contradictory or rejected quote degrades to a typed unavailable
    owner that carries no price/basis/time fact.
    """
    if quote is None:
        # Absence is explicitly unavailable; B4 is never used as a latest-quote owner.
        issues.add("QUOTE_UNAVAILABLE")
        return None, _quote_unavailable_presentation(), None, "UNAVAILABLE"

    def _as_text(value: object) -> str | None:
        return value if isinstance(value, str) else None

    summary: dict[str, object] = {
        "schema": _as_text(quote.get("schema")) if isinstance(quote, Mapping) else None,
        "owner_ref": _as_text(quote.get("owner_ref")) if isinstance(quote, Mapping) else None,
        "state": None,
        "source_receipt": _as_text(quote.get("source_receipt")) if isinstance(quote, Mapping) else None,
    }

    def degraded(native_state: object = None) -> tuple[dict[str, object], dict[str, object], str | None, str]:
        summary["state"] = (
            native_state if isinstance(native_state, str) and native_state in _QUOTE_STATES else "UNAVAILABLE"
        )
        return summary, _quote_unavailable_presentation(), None, "UNAVAILABLE"

    if not isinstance(quote, Mapping) or quote.get("schema") != _QUOTE_SCHEMA:
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded()
    for field in ("owner_ref", "source_receipt", "state", *_BOUND_FIELDS):
        if not isinstance(quote.get(field), str) or not quote.get(field).strip():
            issues.add("QUOTE_INPUT_UNAVAILABLE")
            return degraded()
    try:
        _receipt(quote.get("source_receipt"), "quote.source_receipt")
    except DailyBriefContractError:
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded()
    if not _is_state(quote.get("state"), _QUOTE_STATES):
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded()
    native_state = str(quote["state"])
    if _binding(quote) != dict(identity):
        issues.add("OWNER_BINDING_MISMATCH")
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded(native_state)

    if native_state == "UNAVAILABLE":
        if any(quote.get(field) is not None for field in ("observed_at", "price", "basis")):
            # An unavailable quote may not carry observed price facts.
            issues.add("QUOTE_INPUT_UNAVAILABLE")
            return degraded(native_state)
        summary["state"] = native_state
        return summary, _quote_unavailable_presentation(), None, "UNAVAILABLE"

    try:
        observed_at = _timestamp(quote.get("observed_at"), "quote.observed_at")
    except DailyBriefContractError:
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded(native_state)
    if observed_at > now_dt:
        issues.add("FUTURE_OWNER_CLOCK")
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded(native_state)
    try:
        price = _positive_number(quote.get("price"), "quote.price")
    except DailyBriefContractError:
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded(native_state)
    try:
        basis = _text(quote.get("basis"), "quote.basis")
    except DailyBriefContractError:
        issues.add("QUOTE_INPUT_UNAVAILABLE")
        return degraded(native_state)

    observed_text = str(quote.get("observed_at"))
    if b4_quote_asof is not None:
        try:
            b4_clock = _timestamp(b4_quote_asof, "entry_availability.quote_asof")
        except DailyBriefContractError:
            b4_clock = None
        if b4_clock is not None:
            if observed_at < b4_clock:
                # A quote read that predates the B4-bound quote is not a latest quote.
                issues.add("QUOTE_OLDER_THAN_ENTRY_AVAILABILITY")
                return degraded(native_state)
            if observed_at == b4_clock:
                same_price = (
                    isinstance(b4_price, (int, float))
                    and not isinstance(b4_price, bool)
                    and _prices_agree(price, b4_price)
                )
                same_basis = isinstance(b4_basis, str) and basis == b4_basis
                if not same_price or not same_basis:
                    issues.add("QUOTE_CONTRADICTS_ENTRY_AVAILABILITY")
                    return degraded(native_state)

    summary["state"] = native_state
    presentation = {
        "state": native_state,
        "observed_at": observed_text,
        "price": price,
        "basis": basis,
    }
    return summary, presentation, observed_text, native_state


def _plan_presentation(
    plan_rec: Mapping[str, object] | None, *, relation_valid: bool,
) -> dict[str, object] | None:
    """Present the plan relation, or a typed unavailable relation with no ids."""
    if plan_rec is None:
        return None
    relation = plan_rec.get("relation_state")
    exact_relation = plan_rec.get("exact_relation")
    plan_ids = plan_rec.get("plan_ids")
    valid_ids = (
        isinstance(plan_ids, list)
        and all(isinstance(item, str) and item.strip() == item and item for item in plan_ids)
        and len(plan_ids) == len({item for item in plan_ids})
    )
    if relation_valid and _is_state(relation, _PLAN_RELATIONS) and exact_relation == "unavailable" and valid_ids:
        return {
            "relation_state": str(relation),
            "exact_relation": "unavailable",
            "plan_ids": list(plan_ids),
        }
    return {"relation_state": "unavailable", "exact_relation": "unavailable", "plan_ids": []}


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
    quote: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Compose one immutable Daily Brief presentation read model."""

    for name, value in (
        ("candidate", candidate), ("plan", plan), ("assessment", assessment),
        ("evidence", evidence), ("assembly", assembly), ("recovery", recovery),
        ("quote", quote),
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
    if not _is_state(cand.get("state"), _CANDIDATE_STATES):
        issues.add("SELECTION_UNAVAILABLE")
    plan_relation_ok = False
    if plan_rec is not None:
        relation = plan_rec.get("relation_state")
        exact_relation = plan_rec.get("exact_relation")
        plan_ids = plan_rec.get("plan_ids")
        plan_state = plan_rec.get("state")
        valid_ids = (
            isinstance(plan_ids, list)
            and all(isinstance(item, str) and item.strip() == item and item for item in plan_ids)
            and len(plan_ids) == len({item for item in plan_ids})
        )
        expected_relation = {
            "RELATED_SECURITY": "related_security", "NONE": "none", "UNAVAILABLE": "unavailable",
        }.get(plan_state) if isinstance(plan_state, str) else None
        # This v1 receipt has no exact candidate-to-plan linkage proof. A related
        # security record therefore cannot promote itself into an exact plan.
        plan_relation_ok = (
            _is_state(plan_state, _PLAN_STATES)
            and _is_state(relation, _PLAN_RELATIONS)
            and relation == expected_relation
            and exact_relation == "unavailable"
            and valid_ids
            and not (plan_state == "RELATED_SECURITY" and not plan_ids)
            and not (plan_state in {"NONE", "UNAVAILABLE"} and bool(plan_ids))
        )
        if not plan_relation_ok:
            issues.add("OWNER_INPUT_UNAVAILABLE")
    if assess is not None and not _is_state(assess.get("state"), _ASSESSMENT_STATES):
        issues.add("OWNER_INPUT_UNAVAILABLE")
    if evid is not None and not _is_state(evid.get("state"), _EVIDENCE_STATES):
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
        "entry_availability": None,
        "entry_availability_quote": None,
        "plan": str(plan_rec.get("asof")) if plan_rec is not None else None,
        "assessment": str(assess.get("asof")) if assess is not None else None,
        "evidence": str(evid.get("asof")) if evid is not None else None,
        "assembly": str(assembly.get("assembled_at")) if isinstance(assembly, Mapping) else None,
    }
    for name, value in clocks.items():
        if value is not None and _clock_is_future(value, now_dt, f"clocks.{name}"):
            issues.add("FUTURE_OWNER_CLOCK")
        if _clock_is_malformed(value) and value is not None:
            issues.add("MALFORMED_OWNER_CLOCK")

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

    # Validate all presented B4 fields before deriving decision/health. The
    # native validator checks receipt identity but does not type these lists.
    b4_blockers = _owner_string_list(b4.get("blockers"), issues) if b4 is not None else []
    b4_reasons = _owner_string_list(b4.get("reasons"), issues) if b4 is not None else []

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
        clocks["entry_availability"] = str(b4.get("evaluated_at"))
        clocks["entry_availability_quote"] = str(b4.get("quote_asof"))
        for name in ("entry_availability", "entry_availability_quote"):
            if _clock_is_future(clocks[name], now_dt, f"clocks.{name}"):
                issues.add("FUTURE_OWNER_CLOCK")
        state = b4.get("state")
        if state == "ENTRY_OPEN":
            decision_state = "ENTRY_CLEARED"
        elif _is_state(state, _NON_ENTRY_B4):
            decision_state = "NO_ENTRY_CLEARED"
        else:
            decision_state = "UNAVAILABLE"

    # The quote owner is joined, never merged into B4: it supplies its own clock
    # and native state and cannot renew B4 clocks or recompute the B4 result.
    quote_owner, quote_presentation, quote_clock, quote_state = _quote_owner(
        quote,
        identity=identity,
        now_dt=now_dt,
        b4_quote_asof=clocks["entry_availability_quote"] if b4 is not None else None,
        b4_price=b4.get("current_price") if b4 is not None else None,
        b4_basis=b4.get("current_price_basis") if b4 is not None else None,
        issues=issues,
    )
    clocks["quote"] = quote_clock

    assembly_state = assembly.get("state") if isinstance(assembly, Mapping) else None
    if not _is_state(assembly_state, _ASSEMBLY_STATES):
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
    elif not _is_state(assembly_state, {"OK", "UNAVAILABLE"}):
        issues.add("ASSEMBLY_UNAVAILABLE")
        decision_state = "UNAVAILABLE"
    elif assembly_state == "UNAVAILABLE":
        issues.add("ASSEMBLY_UNAVAILABLE")
        decision_state = "UNAVAILABLE"

    if issues & _HARD_ISSUES:
        decision_state = "UNAVAILABLE"

    # A dark or stale latest quote blocks publication of any entry decision, but
    # it never changes the B4-owned availability state presented below.
    if quote_state in {"UNAVAILABLE", "STALE"}:
        decision_state = "UNAVAILABLE"

    evidence_state = evid.get("state") if evid is not None else None
    assessment_state = assess.get("state") if assess is not None else None
    blockers = set(b4_blockers)

    if assembly_state == "EFFECT_UNKNOWN":
        health_state = "EFFECT_UNKNOWN"
    elif issues & _HARD_ISSUES:
        health_state = "UNAVAILABLE"
    elif (evidence_state == "UNAVAILABLE" or assessment_state == "UNAVAILABLE"
          or (plan_rec is not None and plan_rec.get("state") == "UNAVAILABLE")):
        # An unavailable required owner must not be masked by a softer health state.
        health_state = "UNAVAILABLE"
        decision_state = "UNAVAILABLE"
    elif quote_state == "UNAVAILABLE":
        health_state = "UNAVAILABLE"
    elif quote_state == "STALE":
        # A natively stale quote cannot become current by assembly time.
        health_state = "STALE_QUOTE"
    elif b4 is not None and b4.get("state") == "UNAVAILABLE_DATA" and "QUOTE_STALE" in blockers:
        health_state = "STALE_QUOTE"
    elif b4 is None or b4.get("state") == "UNAVAILABLE_DATA":
        health_state = "UNAVAILABLE"
    elif evidence_state == "PARTIAL":
        health_state = "PARTIAL"
    else:
        health_state = "CURRENT"

    owners: dict[str, object] = {
        "candidate": _owner_summary(cand),
        "plan": _owner_summary(plan_rec) if plan_rec is not None else None,
        "assessment": _owner_summary(assess) if assess is not None else None,
        "evidence": _owner_summary(evid) if evid is not None else None,
        "quote": quote_owner,
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
        "plan": _plan_presentation(plan_rec, relation_valid=plan_relation_ok),
        "assessment": assess.get("summary") if assess is not None and isinstance(assess.get("summary"), Mapping) else None,
        "evidence": evid.get("coverage") if evid is not None and isinstance(evid.get("coverage"), Mapping) else None,
        "quote": quote_presentation,
        "availability": (
            {
                "state": b4.get("state"),
                "blockers": b4_blockers,
                "reasons": b4_reasons,
            }
            if b4 is not None else None
        ),
    }
    _reject_forbidden(presentation, path="presentation")
    # Freeze nested JSON values; returned views must not alias mutable owner input.
    presentation = json.loads(_canonical_json(presentation))

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
    if not _is_state(payload.get("decision_state"), DECISION_STATES):
        raise DailyBriefContractError("daily brief decision state invalid")
    if not _is_state(payload.get("health_state"), HEALTH_STATES):
        raise DailyBriefContractError("daily brief health state invalid")
    if payload.get("authority") != _AUTHORITY:
        raise DailyBriefContractError("daily brief authority must remain false")
    identity = payload.get("identity")
    if not isinstance(identity, Mapping) or set(identity) != _BOUND_FIELDS or not all(isinstance(identity.get(k), str) and identity.get(k) for k in _BOUND_FIELDS):
        raise DailyBriefContractError("daily brief identity binding invalid")
    clocks = payload.get("clocks")
    if (not isinstance(clocks, Mapping) or set(clocks) != _CLOCK_FIELDS
            or not all(value is None or isinstance(value, str) for value in clocks.values())):
        raise DailyBriefContractError("daily brief clocks invalid")
    issue_values = payload.get("issues")
    if not isinstance(issue_values, list) or not all(isinstance(item, str) for item in issue_values):
        raise DailyBriefContractError("daily brief issues invalid")
    _reject_forbidden(payload.get("presentation"), path="presentation")
    material = {key: value for key, value in payload.items() if key != "view_id"}
    expected_id = "pdbv:" + sha256(_canonical_json(material).encode("utf-8")).hexdigest()
    if payload.get("view_id") != expected_id:
        raise DailyBriefContractError("daily brief view_id mismatch")
