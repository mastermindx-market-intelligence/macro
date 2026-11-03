"""Research-only first-green 30m comparator within the existing RS Pullback owner.

This is a deliberately specified observable comparator, NOT a claim to reproduce
a private strategy. No runtime detector, store, scheduler, issuance, outcome,
admitted source, rank, gate, trade or recommendation originates here.
"""
from __future__ import annotations

import copy
from datetime import timedelta
from decimal import Decimal
from typing import Any, Mapping

from engine.entry_radar.contracts import AUTHORITY_BLOCK
from engine.entry_radar.replay.leader_pivot_descriptor import (
    BAR_WIDTH, MAX_REFERENCE_LIFE, MINUTE_WIDTH, _floor_minute, _number,
)
from engine.entry_radar.replay.rs_pullback_launch_data import (
    CALENDAR_INPUT_SCHEMA, InputContractError, _aggregate, _calendar_at,
    _clock, _iso, _metadata_errors, build_input_panel, digest,
)

SCHEMA = "mastermind.rs_pullback_launch.first_green_descriptor.v0"
DEFINITION_ID = "first-green-after-immediate-red30m-v0"
REFERENCE_SCHEMA = "mastermind.rs_pullback_launch.first_green_reference.v0"
PROGRESS_SCHEMA = "mastermind.rs_pullback_launch.first_green_progress.v0"
PROGRESS_DEFINITION_ID = "completed1m-close-break-green30m-v0"


def _seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    value["refusals"] = sorted(set(value["refusals"]))
    value[field] = digest(value)
    return value


def _only_candidate(bundle: Mapping[str, Any], candidate_id: str):
    if not isinstance(bundle, Mapping) or not isinstance(candidate_id, str) or not candidate_id:
        raise InputContractError("bundle and nonempty candidate_id required")
    candidates = bundle.get("candidates")
    if not isinstance(candidates, list):
        raise InputContractError("candidate population must be a list")
    matches = [c for c in candidates if isinstance(c, Mapping) and c.get("candidate_id") == candidate_id]
    if len(matches) != 1:
        raise InputContractError("candidate_id must select exactly one predeclared candidate")
    return matches[0]


def _visible_session(bundle: Mapping[str, Any], instant, session: str):
    calendar = bundle["calendar"]
    visible = _calendar_at(calendar, instant) if calendar.get("schema") == CALENDAR_INPUT_SCHEMA else calendar
    if visible is None or not isinstance(visible, Mapping):
        raise InputContractError("decision calendar unavailable")
    law = visible["sessions"].get(session)
    if not isinstance(law, Mapping):
        raise InputContractError("decision session missing from calendar")
    return visible, law


def describe_first_green_candidate(bundle: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    """One explicit candidate, one completed green bar following one completed red bar.

    Immediate red-to-green is a bounded public-inspired research definition,
    not an assertion about hidden screening/exit rules. A red bar's close must
    be strictly below its open; a green bar's close strictly above its open.
    Doji/flat bars never qualify. A later correction has only as-of effect.
    """
    candidate = _only_candidate(bundle, candidate_id)
    selected = dict(bundle)
    selected["candidates"] = [candidate]
    panel = build_input_panel(selected)
    frame = panel["frames"][0]
    value: dict[str, Any] = {
        "schema": SCHEMA, "definition_id": DEFINITION_ID,
        "candidate_id": candidate_id, "session": frame["session"],
        "decision_at": frame["decision_at"], "input_kind": panel["input_kind"],
        "evidence_status": "SYNTHETIC_CONFORMANCE_ONLY" if panel["input_kind"] == "SYNTHETIC_CONFORMANCE"
                           else "DESCRIPTOR_BUILT_NOT_ADMITTED",
        "state": "UNAVAILABLE", "condition_met": None, "eligible": frame["eligible"],
        "owner_snapshot_sha256": frame["snapshot_sha256"],
        "stream_binding": copy.deepcopy(frame["stream_bindings"].get("stock")),
        "previous_bar": None, "target_bar": None,
        "previous_red": None, "current_green": None,
        "price_structure_known_at": None, "pivot": None,
        "source_admitted": False, "detector_registered": False,
        "actual_issuance_proven": False, "issued_at": None,
        "outcomes_computed": False, "authority": dict(AUTHORITY_BLOCK),
        "refusals": list(frame["refusals"]),
    }
    def finish():
        return _seal(value, "descriptor_sha256")

    if frame["availability"] != "available":
        return finish()
    if frame["eligible"] is not True:
        value["state"] = "NOT_ELIGIBLE"
        value["refusals"].append("OWNER_NOT_ELIGIBLE")
        return finish()
    cutoff = _clock(frame["decision_at"])
    target = frame["bars"]["stock"]["30"]
    if target is None or target["availability"] != "available" \
            or target["observed_minutes"] != 30 or target["expected_minutes"] != 30:
        raise InputContractError("complete owner 30m target required")
    start, end = _clock(target["start"]), _clock(target["end"])
    if end - start != BAR_WIDTH:
        raise InputContractError("owner 30m target duration mismatch")
    value["target_bar"] = copy.deepcopy(target)
    _, law = _visible_session(bundle, cutoff, frame["session"])
    opening = _clock(law["open"])
    prior_start = start - BAR_WIDTH
    if prior_start < opening:
        value["refusals"].append("NO_PREVIOUS_COMPLETED_SAME_SESSION_30M")
        return finish()
    stream = candidate["streams"]["stock"]
    prior = _aggregate(bundle.get("minutes", []), stream, bundle["streams"][stream],
                       prior_start, start, cutoff)
    value["previous_bar"] = copy.deepcopy(prior)
    value["refusals"].extend("previous:" + reason for reason in prior["refusals"])
    if value["refusals"]:
        return finish()
    old, current = prior["ohlcv"], target["ohlcv"]
    value["previous_red"] = bool(old["close"] < old["open"])
    value["current_green"] = bool(current["close"] > current["open"])
    value["price_structure_known_at"] = _iso(max(_clock(prior["known_at"]),
                                                    _clock(target["known_at"])))
    met = value["previous_red"] and value["current_green"]
    value["state"] = "FIRST_GREEN_FORMED" if met else "NO_FIRST_GREEN"
    value["condition_met"] = bool(met)
    if met:
        value["pivot"] = {
            "low": current["low"], "high": current["high"],
            "open": current["open"], "close": current["close"],
            "bar_start": target["start"], "bar_end": target["end"],
        }
    return finish()


def _reference_value(formation, buffer_size, episode_expires_at, session_open, session_close):
    """Recompute all fields; seals are integrity, not independent authentication."""
    if not isinstance(formation, Mapping):
        raise InputContractError("formation must be a descriptor")
    try:
        if formation.get("descriptor_sha256") != digest(
            {key: val for key, val in formation.items() if key != "descriptor_sha256"}
        ):
            raise InputContractError("formation seal mismatch")
        if formation.get("schema") != SCHEMA or formation.get("definition_id") != DEFINITION_ID \
                or formation.get("state") != "FIRST_GREEN_FORMED" \
                or formation.get("condition_met") is not True or formation.get("eligible") is not True \
                or formation.get("refusals") or formation.get("authority") != AUTHORITY_BLOCK \
                or any(v is not False for v in formation["authority"].values()) \
                or any(formation.get(key) is not False for key in (
                    "source_admitted", "detector_registered", "actual_issuance_proven",
                    "outcomes_computed"
                )) or formation.get("issued_at") is not None:
            raise InputContractError("only an eligible zero-authority formed green reference can freeze")
        pivot = formation["pivot"]
        low, high = _number(pivot["low"]), _number(pivot["high"])
        tick = _number(buffer_size).normalize()
        decision = _clock(formation["decision_at"])
        opening, closing = _clock(session_open), _clock(session_close)
        start, end = _clock(pivot["bar_start"]), _clock(pivot["bar_end"])
        deadline = _clock(episode_expires_at)
        if low >= high or low - tick <= 0 or not opening <= start < end <= decision < closing \
                or end - start != BAR_WIDTH or deadline <= decision \
                or _clock(formation["price_structure_known_at"]) > decision:
            raise InputContractError("invalid green pivot reference geometry")
        first = _floor_minute(decision)
        if first < decision:
            first += MINUTE_WIDTH
        value = {
            "schema": REFERENCE_SCHEMA, "definition_id": PROGRESS_DEFINITION_ID,
            "formation": copy.deepcopy(dict(formation)),
            "buffer_size": str(tick),
            "buffer_basis": "CALLER_DECLARED_RESEARCH_PARAMETER_NOT_EXCHANGE_TICK_QUALIFICATION",
            "episode_expires_at": _iso(deadline),
            "session_open": _iso(opening), "session_close": _iso(closing),
            "first_minute_start": _iso(first),
            "expires_at": _iso(min(deadline, decision + MAX_REFERENCE_LIFE, closing)),
            "confirmation_level": str(high + tick),
            "invalidation_level": str(low - tick),
            "source_admitted": False, "actual_issuance_proven": False,
        }
        value["reference_sha256"] = digest(value)
        return value
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        if isinstance(exc, InputContractError):
            raise
        raise InputContractError("malformed green reference") from exc


def freeze_first_green_reference(bundle: Mapping[str, Any], candidate_id: str, *,
                                 buffer_size: float, episode_expires_at: str) -> dict[str, Any]:
    """No event issuance, source admission or execution tick qualification."""
    formation = describe_first_green_candidate(bundle, candidate_id)
    if formation["state"] != "FIRST_GREEN_FORMED":
        raise InputContractError("complete eligible first-green formation required")
    _, law = _visible_session(bundle, _clock(formation["decision_at"]), formation["session"])
    return _reference_value(formation, buffer_size, episode_expires_at,
                            law["open"], law["close"])


def _checked_reference(reference):
    if not isinstance(reference, Mapping) or not isinstance(reference.get("buffer_size"), str):
        raise InputContractError("frozen green reference required")
    try:
        expected = _reference_value(reference["formation"], float(reference["buffer_size"]),
                                    reference["episode_expires_at"], reference["session_open"],
                                    reference["session_close"])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise InputContractError("invalid frozen green reference") from exc
    if dict(reference) != expected:
        raise InputContractError("green reference or levels changed after freeze")
    return expected


def describe_first_green_progress(bundle: Mapping[str, Any], candidate_id: str, *,
                                  reference: Mapping[str, Any]) -> dict[str, Any]:
    """Observe frozen 1m close confirmation or low invalidation through one as-of cutoff.

    Conservative rule: same-minute low breach precedes closing-price
    confirmation, because OHLCV cannot prove the intraminute event order.
    """
    ref = _checked_reference(reference)
    formed = ref["formation"]
    candidate = _only_candidate(bundle, candidate_id)
    cutoff = _clock(candidate["decision_at"])
    if candidate["session"] != formed["session"] or cutoff < _clock(formed["decision_at"]):
        raise InputContractError("follow-up must be later and in the frozen session")
    selected = dict(bundle)
    selected["candidates"] = [candidate]
    panel = build_input_panel(selected)
    frame = panel["frames"][0]
    value = {
        "schema": PROGRESS_SCHEMA, "definition_id": PROGRESS_DEFINITION_ID,
        "reference_sha256": ref["reference_sha256"],
        "candidate_id": candidate_id, "session": candidate["session"],
        "decision_at": _iso(cutoff), "input_kind": panel["input_kind"],
        "evidence_status": "SYNTHETIC_CONFORMANCE_ONLY" if panel["input_kind"] == "SYNTHETIC_CONFORMANCE"
                           else "PROGRESS_BUILT_NOT_ADMITTED",
        "state": "UNAVAILABLE", "confirmation": None, "invalidation": None,
        "expires_at": ref["expires_at"], "complete_minutes_evaluated": 0,
        "evaluated_through": ref["first_minute_start"],
        "prefix_revision_sha256": None, "prefix_known_at": formed["decision_at"],
        "owner_snapshot_sha256": frame["snapshot_sha256"],
        "current_context_availability": frame["availability"],
        "current_context_refusals": list(frame["refusals"]),
        "ordering_rule": "LOW_BREACH_BEFORE_FINAL_CLOSE",
        "source_admitted": False, "actual_issuance_proven": False,
        "detector_registered": False, "outcomes_computed": False,
        "authority": dict(AUTHORITY_BLOCK), "refusals": [],
    }
    def finish():
        return _seal(value, "progress_sha256")

    if panel["input_kind"] != formed["input_kind"]:
        value["refusals"].append("INPUT_KIND_CHANGED")
        return finish()
    try:
        visible, law = _visible_session(bundle, cutoff, candidate["session"])
        if _clock(visible["known_at"]) > cutoff \
                or _iso(_clock(law["open"])) != ref["session_open"] \
                or _iso(_clock(law["close"])) != ref["session_close"]:
            value["refusals"].append("FROZEN_SESSION_NOT_BOUND")
            return finish()
    except (InputContractError, KeyError, TypeError):
        value["refusals"].append("FROZEN_SESSION_NOT_BOUND")
        return finish()
    stream = candidate["streams"]["stock"]
    meta = bundle.get("streams", {}).get(stream, {})
    value["refusals"].extend(_metadata_errors(meta, cutoff, candidate["session"]))
    old = formed["stream_binding"]
    if stream != old["stream"] or meta.get("security_id") != old["security_id"] \
            or meta.get("basis", {}).get("basis_id") != old["basis_id"] \
            or meta.get("basis", {}).get("receipt_sha256") != old["basis_receipt_sha256"] \
            or meta.get("identity", {}).get("receipt_sha256") != old["identity_receipt_sha256"]:
        value["refusals"].append("FROZEN_IDENTITY_OR_BASIS_CHANGED")
    if value["refusals"]:
        return finish()
    left = _clock(ref["first_minute_start"])
    expiry = _clock(ref["expires_at"])
    stop = min(_floor_minute(cutoff), expiry)
    prefix_known = _clock(formed["decision_at"])
    hashes: list[str] = []
    upper, lower = Decimal(ref["confirmation_level"]), Decimal(ref["invalidation_level"])
    value["state"] = "WAITING_CONFIRMATION"
    while left + MINUTE_WIDTH <= stop:
        bar = _aggregate(bundle.get("minutes", []), stream, meta, left, left + MINUTE_WIDTH, cutoff)
        if bar["availability"] != "available":
            value["state"] = "UNAVAILABLE"
            value["refusals"].extend("followup:" + reason for reason in bar["refusals"])
            return finish()
        hashes.append(bar["input_revision_sha256"])
        prefix_known = max(prefix_known, _clock(bar["known_at"]))
        value["complete_minutes_evaluated"] += 1
        value["evaluated_through"] = bar["end"]
        value["prefix_revision_sha256"] = digest(hashes)
        value["prefix_known_at"] = _iso(prefix_known)
        event = {"bar_start": bar["start"], "bar_end": bar["end"],
                 "known_at": _iso(prefix_known),
                 "input_revision_sha256": bar["input_revision_sha256"],
                 "prefix_revision_sha256": value["prefix_revision_sha256"]}
        prices = bar["ohlcv"]
        if Decimal(str(prices["low"])) < lower:
            value["invalidation"] = {**event, "observed_low": prices["low"]}
            value["state"] = "INVALIDATED"
            return finish()
        if value["confirmation"] is None and Decimal(str(prices["close"])) > upper:
            value["confirmation"] = {**event, "observed_close": prices["close"]}
            value["state"] = "GREEN_BREAK_CONFIRMED"
        left += MINUTE_WIDTH
    if cutoff >= expiry:
        if left < expiry:
            value["state"] = "UNAVAILABLE"
            value["refusals"].append("PARTIAL_MINUTE_AT_EXPIRY")
        else:
            value["state"] = "EXPIRED"
    return finish()
