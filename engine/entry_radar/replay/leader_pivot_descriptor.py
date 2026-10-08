"""Pure research consumer of the existing RS Pullback Phase-1 input owner.

Initial P0B-30M conformance tranche, not a registered Radar detector or source
admission. Requires four preceding full 30m intervals in the SAME supplied
session. Earlier-session carry, confirmation, invalidation, expiry, actual
issuance, market evaluation and consumer enrollment are not implemented here.

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
