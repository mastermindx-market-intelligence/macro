"""Pure research consumers of the existing RS Pullback Phase-1 input owner.

The original v0 descriptor requires four preceding full 30m intervals in the
same supplied session. Follow-up functions describe one frozen reference and
its completed-minute confirmation, invalidation and expiry evidence. They do
not register a detector, own a lifecycle/store, issue forecasts or admit data.

Owner clocks, minute selection, identity/basis refusals, calendar and daily /
incumbent checks are reused unchanged. Private helper imports are a deliberate
provisional integration seam, not a new public API or data-qualification owner.
All results, including OBSERVED_MARKET results, remain not admitted.
"""
from __future__ import annotations

import copy
from datetime import timedelta
from typing import Any, Mapping

from engine.entry_radar.replay.rs_pullback_launch_data import (
    CALENDAR_INPUT_SCHEMA,
    InputContractError,
    _aggregate,
    _calendar_at,
    _clock,
    _iso,
    build_input_panel,
    digest,
)

SCHEMA = "mastermind.rs_pullback_launch.leader_pivot_descriptor.v0"
DEFINITION_ID = "completed30m-rejection-same-session-v0"
BAR_WIDTH = timedelta(minutes=30)
REFERENCE_COUNT = 4


def _seal(result: dict[str, Any]) -> dict[str, Any]:
    result["refusals"] = sorted(set(result["refusals"]))
    result["descriptor_sha256"] = digest(result)
    return result


def describe_candidate(bundle: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    """Evaluate one explicit candidate without writes, clocks or self-admission.

    A decision cutoff is a replay query, not proof of historical issuance. The
    price_structure_known_at field covers only the five price aggregates; the
    complete owner snapshot binds the additional context and input refusals.
    Full-bundle hashes are deliberately excluded from descriptor identity so
    future additions cannot change the earlier visible result. Hashes provide
    consistency, not authentication of a caller's source/receipt assertions.
    """
    if not isinstance(bundle, Mapping) or not isinstance(candidate_id, str) or not candidate_id:
        raise InputContractError("a bundle and nonempty candidate_id are required")
    candidates = bundle.get("candidates")
    if not isinstance(candidates, list):
        raise InputContractError("candidate population must be a list")
    matches = [c for c in candidates if isinstance(c, Mapping) and c.get("candidate_id") == candidate_id]
    if len(matches) != 1:
        raise InputContractError("candidate_id must select exactly one predeclared candidate")
    candidate = matches[0]
    selected_bundle = dict(bundle)
    selected_bundle["candidates"] = [candidate]
    panel = build_input_panel(selected_bundle)
    frame = panel["frames"][0]
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "definition_id": DEFINITION_ID,
        "input_kind": panel["input_kind"],
        "evidence_status": "SYNTHETIC_CONFORMANCE_ONLY" if panel["input_kind"] == "SYNTHETIC_CONFORMANCE"
                           else "DESCRIPTOR_BUILT_NOT_ADMITTED",
        "candidate_id": candidate_id,
        "session": frame["session"],
        "decision_at": frame["decision_at"],
        "state": "UNAVAILABLE",
        "condition_met": None,
        "eligible": frame["eligible"],
        "stream_binding": copy.deepcopy(frame["stream_bindings"].get("stock")),
        "catalyst_state": frame["catalyst_state"],
        "owner_snapshot_sha256": frame["snapshot_sha256"],
        "target_interval": None,
        "reference_bars": [],
        "reference_low": None,
        "price_structure_known_at": None,
        "pivot": None,
        "authority": copy.deepcopy(frame["authority"]),
        "source_admitted": False,
        "detector_registered": False,
        "outcomes_computed": False,
        "actual_issuance_proven": False,
        "issued_at": None,
        "refusals": list(frame["refusals"]),
    }
    if frame["availability"] != "available":
        return _seal(result)
    if frame["eligible"] is not True:
        result["state"] = "NOT_ELIGIBLE"
        result["refusals"].append("OWNER_NOT_ELIGIBLE")
        return _seal(result)

    cutoff = _clock(frame["decision_at"])
    target = frame["bars"]["stock"]["30"]
    start, end = _clock(target["start"]), _clock(target["end"])
    if end - start != BAR_WIDTH or target["expected_minutes"] != 30 or target["observed_minutes"] != 30:
        raise InputContractError("owner aggregate is not a complete 30m interval")
    result["target_interval"] = copy.deepcopy(target)
    calendar = bundle["calendar"]
    visible = _calendar_at(calendar, cutoff) if calendar.get("schema") == CALENDAR_INPUT_SCHEMA else calendar
    if visible is None:
        raise InputContractError("available owner frame has no visible calendar")
    opening = _clock(visible["sessions"][frame["session"]]["open"])
    first = start - REFERENCE_COUNT * BAR_WIDTH
    if first < opening:
        result["refusals"].append("INSUFFICIENT_SAME_SESSION_30M_HISTORY")
        return _seal(result)

    stream = candidate["streams"]["stock"]
    metadata = bundle["streams"][stream]
    for index in range(REFERENCE_COUNT):
        left = first + index * BAR_WIDTH
        reference = _aggregate(bundle.get("minutes", []), stream, metadata, left, left + BAR_WIDTH, cutoff)
        result["reference_bars"].append(reference)
        result["refusals"].extend(f"reference_{index}:{reason}" for reason in reference["refusals"])
    if result["refusals"]:
        return _seal(result)

    floor = min(bar["ohlcv"]["low"] for bar in result["reference_bars"])
    prices = target["ohlcv"]
    width = prices["high"] - prices["low"]
    met = (width > 0 and prices["low"] < floor and prices["close"] > floor
           and (prices["close"] - prices["low"]) / width >= 0.5)
    result["reference_low"] = floor
    result["price_structure_known_at"] = _iso(max(
        _clock(bar["known_at"]) for bar in [*result["reference_bars"], target]))
    result["condition_met"] = bool(met)
    result["state"] = "PIVOT_FORMED" if met else "NO_PIVOT"
    if met:
        result["pivot"] = {"low": prices["low"], "high": prices["high"],
                           "bar_start": target["start"], "bar_end": target["end"]}
    return _seal(result)


# Additive research-only follow-up. The v0 descriptor function stays unchanged.
from decimal import Decimal
import math
from engine.entry_radar.contracts import AUTHORITY_BLOCK
from engine.entry_radar.replay.rs_pullback_launch_data import _metadata_errors

REFERENCE_SCHEMA = "mastermind.rs_pullback_launch.frozen_pivot_reference.v1"
PROGRESS_SCHEMA = "mastermind.rs_pullback_launch.pivot_progress.v1"
PROGRESS_DEFINITION_ID = "completed1m-close-confirm-low-invalidate-v1"
MINUTE_WIDTH = timedelta(minutes=1)
MAX_REFERENCE_LIFE = timedelta(minutes=60)


def _number(value: Any) -> Decimal:
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise InputContractError("positive finite numeric research parameter required")
    return Decimal(str(value))


def _floor_minute(instant):
    return instant.replace(second=0, microsecond=0)


def _reference_value(formation, tick_size, episode_expires_at, session_open, session_close):
    """Check consistency only; a seal never authenticates a caller's evidence."""
    if not isinstance(formation, Mapping):
        raise InputContractError("formation must be a descriptor")
    try:
        sealed = {k: v for k, v in formation.items() if k != "descriptor_sha256"}
        if formation.get("descriptor_sha256") != digest(sealed):
            raise InputContractError("formation descriptor seal mismatch")
        if formation.get("schema") != SCHEMA or formation.get("definition_id") != DEFINITION_ID \
                or formation.get("state") != "PIVOT_FORMED" \
                or formation.get("condition_met") is not True or formation.get("eligible") is not True \
                or formation.get("authority") != AUTHORITY_BLOCK \
                or any(v is not False for v in formation["authority"].values()) \
                or any(formation.get(k) is not False for k in
                       ("source_admitted", "detector_registered", "outcomes_computed", "actual_issuance_proven")) \
                or formation.get("issued_at") is not None or formation.get("refusals"):
            raise InputContractError("only a sealed zero-authority formed pivot can be frozen")
        pivot = formation["pivot"]
        low, high, tick = _number(pivot["low"]), _number(pivot["high"]), _number(tick_size)
        tick = tick.normalize()  # Numeric 1 and 1.0 must share one reference identity.
        decision = _clock(formation["decision_at"])
        opening, closing = _clock(session_open), _clock(session_close)
        start, end = _clock(pivot["bar_start"]), _clock(pivot["bar_end"])
        episode_end = _clock(episode_expires_at)
        if low >= high or low - tick <= 0 or not opening <= start < end <= decision < closing \
                or end - start != BAR_WIDTH or episode_end <= decision:
            raise InputContractError("invalid pivot, session, buffer or expiry geometry")
        if _clock(formation["price_structure_known_at"]) > decision:
            raise InputContractError("formation prices not known at frozen decision")
        first = _floor_minute(decision)
        if first < decision:
            first += MINUTE_WIDTH
        value = {
            "schema": REFERENCE_SCHEMA,
            "definition_id": PROGRESS_DEFINITION_ID,
            "formation": copy.deepcopy(dict(formation)),
            "tick_size": str(tick),
            "buffer_basis": "CALLER_DECLARED_RESEARCH_PARAMETER_NOT_EXCHANGE_TICK_QUALIFICATION",
            "episode_expires_at": _iso(episode_end),
            "session_open": _iso(opening),
            "session_close": _iso(closing),
            "first_minute_start": _iso(first),
            "expires_at": _iso(min(episode_end, decision + MAX_REFERENCE_LIFE, closing)),
            "confirmation_level": str(high + tick),
            "invalidation_level": str(low - tick),
            "source_admitted": False,
            "actual_issuance_proven": False,
        }
        value["reference_sha256"] = digest(value)
        return value
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, InputContractError):
            raise
        raise InputContractError("malformed frozen research reference") from exc


def freeze_pivot_reference(bundle: Mapping[str, Any], candidate_id: str, *,
                           tick_size: float, episode_expires_at: str) -> dict[str, Any]:
    """Freeze one explicit research reference without creating or issuing an event.

    The parent supplies its episode deadline; life is capped at 60 minutes and
    this same session's close. A straddling minute is excluded entirely because
    its OHLC cannot isolate activity after a non-minute-aligned decision.
    Tick size is a declared research parameter, not an exchange-source claim.
    """
    formation = describe_candidate(bundle, candidate_id)
    if formation["state"] != "PIVOT_FORMED":
        raise InputContractError("a complete eligible formed pivot is required")
    cutoff = _clock(formation["decision_at"])
    calendar = bundle["calendar"]
    visible = _calendar_at(calendar, cutoff) if calendar.get("schema") == CALENDAR_INPUT_SCHEMA else calendar
    if visible is None:
        raise InputContractError("formation calendar is unavailable")
    law = visible["sessions"][formation["session"]]
    return _reference_value(formation, tick_size, episode_expires_at, law["open"], law["close"])


def _checked_reference(reference):
    if not isinstance(reference, Mapping):
        raise InputContractError("a frozen reference is required")
    try:
        tick = reference["tick_size"]
        if not isinstance(tick, str):
            raise InputContractError("frozen tick must retain its decimal text")
        # Only strings produced by our numeric freezer are accepted. This is
        # bounded research arithmetic, not arbitrary-precision price ingestion.
        rebuilt = _reference_value(reference["formation"], float(tick),
                                   reference["episode_expires_at"], reference["session_open"],
                                   reference["session_close"])
        if dict(reference) != rebuilt:
            raise InputContractError("frozen reference or derived-level mismatch")
        return rebuilt
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, InputContractError):
            raise
        raise InputContractError("malformed frozen reference") from exc


def describe_pivot_progress(bundle: Mapping[str, Any], candidate_id: str, *,
                            reference: Mapping[str, Any]) -> dict[str, Any]:
    """Stateless as-of observation projection; never a second event lifecycle.

    Uses one explicitly supplied frozen reference and a predeclared follow-up
    candidate. It neither reconstructs historical issuance nor advances a store.
    Event times and knowability differ: absence of an earlier invalidation is
    known only once every intervening minute in the examined prefix is known.
    A gap preserves an already witnessed confirmation but makes the later state
    unavailable. Terminal invalidation needs no price observations after itself.
    """
    ref = _checked_reference(reference)
    formation = ref["formation"]
    if not isinstance(bundle, Mapping) or not isinstance(candidate_id, str) or not candidate_id:
        raise InputContractError("a bundle and explicit follow-up candidate are required")
    candidates = bundle.get("candidates")
    if not isinstance(candidates, list):
        raise InputContractError("follow-up population must be a list")
    matches = [c for c in candidates if isinstance(c, Mapping) and c.get("candidate_id") == candidate_id]
    if len(matches) != 1:
        raise InputContractError("follow-up must select exactly one candidate")
    candidate = matches[0]
    cutoff = _clock(candidate["decision_at"])
    if candidate["session"] != formation["session"] or cutoff < _clock(formation["decision_at"]):
        raise InputContractError("follow-up precedes formation or belongs to another session")
    selected = dict(bundle)
    selected["candidates"] = [candidate]
    panel = build_input_panel(selected)
    frame = panel["frames"][0]
    value = {
        "schema": PROGRESS_SCHEMA,
        "definition_id": PROGRESS_DEFINITION_ID,
        "reference_sha256": ref["reference_sha256"],
        "candidate_id": candidate_id,
        "session": candidate["session"],
        "decision_at": _iso(cutoff),
        "input_kind": panel["input_kind"],
        "evidence_status": "SYNTHETIC_CONFORMANCE_ONLY" if panel["input_kind"] == "SYNTHETIC_CONFORMANCE"
                           else "PROGRESS_BUILT_NOT_ADMITTED",
        "state": "UNAVAILABLE",
        "confirmation": None,
        "invalidation": None,
        "expires_at": ref["expires_at"],
        "complete_minutes_evaluated": 0,
        "evaluated_through": ref["first_minute_start"],
        "prefix_revision_sha256": None,
        "prefix_known_at": formation["decision_at"],
        "owner_snapshot_sha256": frame["snapshot_sha256"],
        "current_context_availability": frame["availability"],
        "current_context_refusals": list(frame["refusals"]),
        "ordering_rule": "LOW_BREACH_BEFORE_FINAL_CLOSE",
        "source_admitted": False,
        "actual_issuance_proven": False,
        "detector_registered": False,
        "outcomes_computed": False,
        "authority": dict(AUTHORITY_BLOCK),
        "refusals": [],
    }

    def finish():
        value["refusals"] = sorted(set(value["refusals"]))
        value["progress_sha256"] = digest(value)
        return value

    if panel["input_kind"] != formation["input_kind"]:
        value["refusals"].append("INPUT_KIND_CHANGED")
        return finish()
    calendar = bundle["calendar"]
    try:
        visible = _calendar_at(calendar, cutoff) if calendar.get("schema") == CALENDAR_INPUT_SCHEMA else calendar
        law = (visible or {}).get("sessions", {}).get(candidate["session"])
        if not law or _clock(visible["known_at"]) > cutoff \
                or _iso(_clock(law["open"])) != ref["session_open"] \
                or _iso(_clock(law["close"])) != ref["session_close"]:
            value["refusals"].append("FROZEN_SESSION_NOT_BOUND")
            return finish()
    except (InputContractError, KeyError, TypeError):
        value["refusals"].append("FROZEN_SESSION_NOT_BOUND")
        return finish()
    stream = candidate["streams"]["stock"]
    metadata = bundle.get("streams", {}).get(stream, {})
    value["refusals"].extend(_metadata_errors(metadata, cutoff, candidate["session"]))
    original = formation["stream_binding"]
    if stream != original["stream"] or metadata.get("security_id") != original["security_id"] \
            or metadata.get("basis", {}).get("basis_id") != original["basis_id"] \
            or metadata.get("basis", {}).get("receipt_sha256") != original["basis_receipt_sha256"] \
            or metadata.get("identity", {}).get("receipt_sha256") != original["identity_receipt_sha256"]:
        value["refusals"].append("FROZEN_IDENTITY_OR_BASIS_CHANGED")
    if value["refusals"]:
        return finish()
    left = _clock(ref["first_minute_start"])
    expiry = _clock(ref["expires_at"])
    stop = min(_floor_minute(cutoff), expiry)
    prefix_known = _clock(formation["decision_at"])
    hashes = []
    upper, lower = Decimal(ref["confirmation_level"]), Decimal(ref["invalidation_level"])
    value["state"] = "WAITING_CONFIRMATION"
    while left + MINUTE_WIDTH <= stop:
        bar = _aggregate(bundle.get("minutes", []), stream, metadata, left, left + MINUTE_WIDTH, cutoff)
        if bar["availability"] != "available":
            value["state"] = "UNAVAILABLE"
            value["refusals"].extend("followup:" + x for x in bar["refusals"])
            return finish()
        hashes.append(bar["input_revision_sha256"])
        prefix_known = max(prefix_known, _clock(bar["known_at"]))
        value["complete_minutes_evaluated"] += 1
        value["evaluated_through"] = bar["end"]
        value["prefix_revision_sha256"] = digest(hashes)
        value["prefix_known_at"] = _iso(prefix_known)
        event = {"bar_start": bar["start"], "bar_end": bar["end"],
                 "known_at": _iso(prefix_known), "input_revision_sha256": bar["input_revision_sha256"],
                 "prefix_revision_sha256": value["prefix_revision_sha256"]}
        prices = bar["ohlcv"]
        if Decimal(str(prices["low"])) < lower:
            value["invalidation"] = {**event, "observed_low": prices["low"]}
            value["state"] = "INVALIDATED"
            return finish()
        if value["confirmation"] is None and Decimal(str(prices["close"])) > upper:
            value["confirmation"] = {**event, "observed_close": prices["close"]}
            value["state"] = "PIVOT_CONFIRMED"
        left += MINUTE_WIDTH
    if cutoff >= expiry:
        # A partial final minute cannot establish event absence before expiry.
        if left < expiry:
            value["state"] = "UNAVAILABLE"
            value["refusals"].append("PARTIAL_MINUTE_AT_EXPIRY")
        else:
            value["state"] = "EXPIRED"
    return finish()
