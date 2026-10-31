"""Pure daily RS onset measurements over caller-supplied, unadmitted as-of receipts.

This is a research feature consumer, NOT a source admission/identity/calendar owner,
predictive detector, ranker, event publisher, alert or order. Caller-supplied
known-at clocks are coherence checks, not authenticated historical provenance.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
import math
from statistics import median
from typing import Any

from engine.entry_radar.contracts import AUTHORITY_BLOCK
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError, digest
from engine.leadership_rotation_context import Unmeasured, relative_wealth

INPUT_SCHEMA = "mastermind.rs_leadership.onset_daily_input.v0"
SCHEMA = "mastermind.rs_leadership.onset_daily_features.v0"
DEFINITION_ID = "daily-rs-relative-wealth-and-resilience-descriptive-v0"
HORIZONS = (1, 3, 5, 10, 20, 63)
STREAMS = ("stock", "benchmark")


def _clock(value: object) -> datetime:
    if not isinstance(value, str):
        raise InputContractError("aware UTC clock required")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InputContractError("invalid clock") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise InputContractError("naive clock refused")
    return result.astimezone(timezone.utc)


def _session(value: object) -> str:
    if not isinstance(value, str) or len(value) != 10:
        raise InputContractError("exchange session must be ISO date")
    try:
        if date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError as exc:
        raise InputContractError("invalid exchange session") from exc
    return value


def _price(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputContractError("price must be a finite positive number")
    try:
        result = float(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise InputContractError("price must be a finite positive number") from exc
    if not math.isfinite(result) or result <= 0:
        raise InputContractError("price must be a finite positive number")
    return result


def _finite_return(first: float, last: float) -> float | None:
    result = last / first - 1.0
    return result if math.isfinite(result) else None


def _unmeasured(reason: str) -> dict[str, Any]:
    return {"status": "unmeasured", "reason": reason}


def _iso(instant: datetime) -> str:
    return instant.isoformat().replace("+00:00", "Z")


def _finish(result: dict[str, Any]) -> dict[str, Any]:
    result["refusals"] = sorted(set(result["refusals"]))
    result["descriptor_sha256"] = digest(result)
    return result


def _meta(value: object) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InputContractError("two stream metadata records required")
    for key in ("security_id", "basis_id", "basis_kind"):
        if not isinstance(value.get(key), str) or not value[key]:
            raise InputContractError("stream identity and basis required")
    # Only identity/basis evidence that this descriptor actually consumes may
    # affect its digest. Unknown provider metadata is not an as-of measurement.
    return {
        "security_id": value["security_id"],
        "basis_id": value["basis_id"],
        "basis_kind": value["basis_kind"],
        "identity_known_at": _iso(_clock(value.get("identity_known_at"))),
        "basis_known_at": _iso(_clock(value.get("basis_known_at"))),
    }


def _select_visible(
    rows: object, streams: Mapping[str, Mapping[str, Any]],
    prefix: tuple[str, ...], expected_ends: Mapping[str, datetime],
    cutoff: datetime,
) -> dict[str, dict[str, dict[str, Any]]]:
    if not isinstance(rows, list):
        raise InputContractError("source rows must be a list")
    if len(rows) > 8192:
        raise InputContractError("source rows exceed research bound")
    included = set(prefix)
    selected: dict[str, dict[str, dict[str, Any]]] = {role: {} for role in STREAMS}
    timestamps: dict[tuple[str, str], datetime] = {}
    seen: set[tuple[str, str, str]] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise InputContractError("malformed source row")
        name = raw.get("stream")
        if name not in STREAMS:
            raise InputContractError("unknown source role")
        day = _session(raw.get("session"))
        if day not in included:
            continue  # Future session never rewrites an earlier selection.
        known = _clock(raw.get("known_at"))
        if known > cutoff:
            continue  # A later revision is not visible at the original decision.
        security, basis = streams[name]["security_id"], streams[name]["basis_id"]
        if raw.get("security_id") != security or raw.get("basis_id") != basis:
            raise InputContractError("visible security or adjustment basis mismatch")
        period_end = _clock(raw.get("period_end"))
        if not period_end <= known:
            raise InputContractError("daily bar known before its period ended")
        if period_end != expected_ends[day]:
            raise InputContractError("daily bar period-end mismatches declared session close")
        revision = raw.get("revision_id")
        if not isinstance(revision, str) or not revision:
            raise InputContractError("visible revision identity required")
        key = (name, day, revision)
        if key in seen:
            raise InputContractError("duplicate visible source revision")
        seen.add(key)
        close = _price(raw.get("close"))
        identity = (name, day)
        if identity in timestamps and timestamps[identity] == known:
            raise InputContractError("ambiguous same-clock source revisions")
        if identity not in timestamps or timestamps[identity] < known:
            selected[name][day] = {
                "session": day, "close": close,
                "known_at": _iso(known), "period_end": _iso(period_end),
                "revision_id": revision,
                "source_ref": raw.get("source_ref") if isinstance(raw.get("source_ref"), str) else None,
            }
            timestamps[identity] = known
    return selected


def describe_onset_features(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Compute nonpredictive daily relative wealth and down-market resilience.

    Required windows must have every native-calendar session and both streams.
    Incomplete windows abstain independently; no missing session is zero-filled.
    A future-only revision has no effect on the original output or digest.
    """
    if not isinstance(bundle, Mapping) or bundle.get("schema") != INPUT_SCHEMA:
        raise InputContractError("unsupported onset input schema")
    kind = bundle.get("input_kind")
    if kind not in ("SYNTHETIC_CONFORMANCE", "OBSERVED_MARKET"):
        raise InputContractError("input kind required")
    cutoff = _clock(bundle.get("decision_at"))
    target = _session(bundle.get("asof_session"))
    calendar = bundle.get("calendar")
    if not isinstance(calendar, Mapping) or not isinstance(calendar.get("sessions"), list):
        raise InputContractError("owner calendar session list required")
    days = tuple(_session(s) for s in calendar["sessions"])
    if not days or days != tuple(sorted(set(days))) or target not in days:
        raise InputContractError("calendar sessions must be unique ordered dates")
    prefix = days[:days.index(target) + 1]
    # A date label is not a bar close: preserve the owner calendar's actual
    # absolute session-end clock (including DST and exceptional closes).
    # Caller-supplied clocks are NEVER independently authenticated here.
    raw_ends = calendar.get("session_ends")
    if not isinstance(raw_ends, Mapping):
        raise InputContractError("per-session completed close clocks required")
    session_ends = {day: _clock(raw_ends.get(day)) for day in prefix}
    if any(session_ends[a] >= session_ends[b] for a, b in zip(prefix, prefix[1:])):
        raise InputContractError("owner session ends must strictly increase")
    streams = bundle.get("streams")
    if not isinstance(streams, Mapping) or set(streams) != set(STREAMS):
        raise InputContractError("stock and benchmark streams required")
    meta = {name: _meta(streams[name]) for name in STREAMS}
    if meta["stock"]["security_id"] == meta["benchmark"]["security_id"]:
        raise InputContractError("stock cannot serve as its own benchmark")

    result: dict[str, Any] = {
        "schema": SCHEMA, "definition_id": DEFINITION_ID, "input_kind": kind,
        "evidence_status": "SYNTHETIC_CONFORMANCE_ONLY" if kind == "SYNTHETIC_CONFORMANCE"
                           else "DESCRIPTOR_BUILT_NOT_ADMITTED",
        "asof_session": target, "decision_at": _iso(cutoff),
        "stock_security_id": meta["stock"]["security_id"],
        "benchmark_security_id": meta["benchmark"]["security_id"],
        "stock_basis_id": meta["stock"]["basis_id"],
        "benchmark_basis_id": meta["benchmark"]["basis_id"],
        "basis_kind": meta["stock"]["basis_kind"],
        "state": "UNAVAILABLE", "windows": {str(h): _unmeasured("not_evaluated") for h in HORIZONS},
        "acceleration_5": _unmeasured("not_evaluated"),
        "down_market_resilience_20": _unmeasured("not_evaluated"),
        "visible_input_sha256": None, "refusals": [],
        "source_admitted": False, "detector_registered": False,
        "ranking_authority": False, "actual_issuance_proven": False,
        "outcomes_computed": False, "issued_at": None,
        "authority": dict(AUTHORITY_BLOCK),
    }
    if _clock(calendar.get("known_at")) > cutoff:
        result["refusals"].append("CALENDAR_NOT_KNOWN_AT_DECISION")
        return _finish(result)
    if session_ends[target] > cutoff:
        result["refusals"].append("TARGET_SESSION_NOT_CLOSED_AT_DECISION")
        return _finish(result)
    if meta["stock"]["basis_kind"] != meta["benchmark"]["basis_kind"]:
        result["refusals"].append("MIXED_RETURN_BASIS")
        return _finish(result)
    if any(_clock(meta[n][field]) > cutoff for n in STREAMS
           for field in ("identity_known_at", "basis_known_at")):
        result["refusals"].append("IDENTITY_OR_BASIS_NOT_KNOWN_AT_DECISION")
        return _finish(result)

    selected = _select_visible(bundle.get("rows"), meta, prefix, session_ends, cutoff)
    # Exclude unseen future revisions, future sessions and unrelated input from
    # descriptor identity. Hashes are consistency, never source admission.
    result["visible_input_sha256"] = digest({
        "calendar": {"sessions": prefix, "session_ends": {d: _iso(session_ends[d]) for d in prefix},
                     "known_at": _iso(_clock(calendar["known_at"]))},
        "streams": {k: dict(v) for k, v in meta.items()},
        "selected": selected,
    })
    index = len(prefix) - 1

    def window(n: int, end_index: int) -> dict[str, Any]:
        if end_index < n:
            return _unmeasured("insufficient_completed_sessions")
        seq = prefix[end_index - n:end_index + 1]
        if any(day not in selected[role] for role in STREAMS for day in seq):
            return _unmeasured("missing_or_future_known_daily_observation")
        first_s, last_s = selected["stock"][seq[0]]["close"], selected["stock"][seq[-1]]["close"]
        first_b, last_b = selected["benchmark"][seq[0]]["close"], selected["benchmark"][seq[-1]]["close"]
        r_s, r_b = _finite_return(first_s, last_s), _finite_return(first_b, last_b)
        if r_s is None or r_b is None:
            return _unmeasured("nonfinite_window_return")
        rw = relative_wealth(r_s, r_b)
        if isinstance(rw, Unmeasured) or not isinstance(rw, (int, float)):
            return _unmeasured("invalid_relative_wealth")
        rows_used = [selected[role][day] for role in STREAMS for day in seq]
        return {
            "status": "measured", "value": float(rw), "unit": "fraction",
            "stock_return": r_s, "benchmark_return": r_b,
            "start_session": seq[0], "end_session": seq[-1],
            "known_at": max(row["known_at"] for row in rows_used),
            "input_sha256": digest(rows_used),
        }

    result["windows"] = {str(h): window(h, index) for h in HORIZONS}
    newest = result["windows"]["5"]
    old = window(5, index - 5)
    if newest["status"] == "measured" and old["status"] == "measured":
        result["acceleration_5"] = {
            "status": "measured", "value": newest["value"] - old["value"],
            "unit": "fraction", "definition": "change_between_adjacent_5_session_relative_wealth",
            "known_at": max(newest["known_at"], old["known_at"]),
        }
    else:
        result["acceleration_5"] = _unmeasured("incomplete_adjacent_5_session_windows")

    prior = result["windows"]["20"]
    if prior["status"] != "measured":
        result["down_market_resilience_20"] = _unmeasured("incomplete_20_session_window")
    else:
        tail = prefix[index - 20:index + 1]
        differences = []
        invalid_step = False
        for earlier, later in zip(tail, tail[1:]):
            s0, s1 = selected["stock"][earlier]["close"], selected["stock"][later]["close"]
            b0, b1 = selected["benchmark"][earlier]["close"], selected["benchmark"][later]["close"]
            stock_ret, benchmark_ret = _finite_return(s0, s1), _finite_return(b0, b1)
            if stock_ret is None or benchmark_ret is None:
                invalid_step = True
                break
            if benchmark_ret < 0:
                differences.append(stock_ret - benchmark_ret)
        if invalid_step:
            result["down_market_resilience_20"] = _unmeasured("nonfinite_daily_return")
        elif len(differences) < 3:
            result["down_market_resilience_20"] = _unmeasured("too_few_down_benchmark_sessions")
        else:
            middle = median(differences)
            result["down_market_resilience_20"] = (
                {"status": "measured", "value": middle, "unit": "fraction",
                 "down_sessions": len(differences),
                 "definition": "median_simple_return_excess_on_down_benchmark_sessions"}
                if math.isfinite(middle) else _unmeasured("nonfinite_resilience_median")
            )
    result["state"] = ("RESEARCH_METRICS_AVAILABLE" if any(
        x["status"] == "measured" for x in result["windows"].values()) else "UNAVAILABLE")
    return _finish(result)
