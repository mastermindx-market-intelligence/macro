"""Offline RS Pullback Launch Phase-1 input construction, under Entry Radar.

This module is a pure research adapter. It writes no ledger, registers no
detector, computes no firing state/outcome/score, and grants no authority.
Terminal's existing qualifier owns source qualification. This adapter consumes
its receipts and constructs complete OHLCV inputs only from explicitly observed
one-minute revisions. A successful synthetic run is not market-data admission.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from engine.entry_radar.contracts import AUTHORITY_BLOCK

INPUT_SCHEMA = "mastermind.rs_pullback_launch.phase1_input.v1"
PANEL_SCHEMA = "mastermind.rs_pullback_launch.phase1_panel.v1"
CENSUS_SCHEMA = "mastermind.rs_pullback_launch.phase1_census.v1"
ADMISSION_SCHEMA = "mastermind.rs_pullback_launch.phase1_admission.v1"
ROLES = ("stock", "spy", "qqq", "sector")
SOURCE_REQUIREMENTS = (
    "stable_security_identity", "price_volume_corporate_action_basis",
    "calendar_and_exceptional_sessions", "revision_retention_and_first_seen",
    "immutable_recoverable_inputs", "pit_daily_leader_context",
    "faithful_incumbent_assessment", "catalyst_coverage_state",
    "complete_pilot_population",
)
UNKNOWN = {"", "unknown", "not_recorded", "unavailable", None}


class InputContractError(ValueError):
    """Malformed research input, distinct from an honestly missing observation."""


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _clock(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise InputContractError("timestamp must be an ISO-8601 instant") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise InputContractError("naive/display-epoch timestamps are not UTC instants")
    return result.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(value: Any, length: int = 64) -> bool:
    return isinstance(value, str) and len(value) == length and all(
        c in "0123456789abcdef" for c in value)


def _has_receipt(value: Mapping[str, Any]) -> bool:
    return bool(value.get("source_ref")) and _sha(value.get("receipt_sha256"))


def assess_source_census(census: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate supplied source-owner evidence; never self-authorize admission.

    Required symbols come from the frozen census, not from successful files.
    A 5m positive control cannot replace a missing 1m stream. Even a technically
    complete census returns OWNER_REVIEW_REQUIRED, not an admission grant.
    """
    if census.get("schema") != CENSUS_SCHEMA:
        raise InputContractError("unsupported census schema")
    required = census.get("required_symbols", {})
    if set(required) != set(ROLES) or any(not required[x] for x in ROLES):
        raise InputContractError("census must freeze stock, SPY, QQQ and sector roles")
    reports = census.get("terminal_qualifier_reports", [])
    refusals: list[str] = []
    for role in ROLES:
        symbol = required[role]
        matches = [r for r in reports if r.get("symbol") == symbol
                   and r.get("timeframe") == "1m"]
        if len(matches) != 1:
            refusals.append(f"{role}:MISSING_OR_DUPLICATE_1M_OWNER_REPORT")
            continue
        report = matches[0]
        cutoff = report.get("cutoff", {})
        if report.get("status") != "available" or report.get("valid_rows", 0) <= 0:
            refusals.append(f"{role}:NO_1M_HISTORY")
        if cutoff.get("mode") != "as_observed" or cutoff.get("pit_proven") is not True \
                or cutoff.get("count", 0) <= 0:
            refusals.append(f"{role}:AS_OBSERVED_AVAILABILITY_UNPROVEN")
        if report.get("price_adjustment") in UNKNOWN \
                or report.get("volume_adjustment") in UNKNOWN:
            refusals.append(f"{role}:ADJUSTMENT_BASIS_UNRECORDED")
        if not _sha(report.get("sha256")):
            refusals.append(f"{role}:IMMUTABLE_INPUT_UNIDENTIFIED")
        if report.get("coverage", {}).get("window_complete_grid") is not True:
            refusals.append(f"{role}:INCOMPLETE_NOMINAL_GRID")
    evidence = census.get("requirements", {})
    for name in SOURCE_REQUIREMENTS:
        item = evidence.get(name, {})
        if item.get("status") != "PROVEN" or not item.get("evidence_refs"):
            refusals.append(f"{name}:NOT_PROVEN")
    return {
        "schema": ADMISSION_SCHEMA,
        "census_sha256": digest(census),
        "verdict": "NOT_ADMITTED" if refusals else "OWNER_REVIEW_REQUIRED",
        "technical_requirements_met": not refusals,
        "refusals": sorted(set(refusals)),
        "required_symbols": copy.deepcopy(required),
        "authority": dict(AUTHORITY_BLOCK),
        "scientific_claims": {"H1": "NOT_TESTED", "H2": "NOT_TESTED", "H3": "NOT_TESTED"},
        "market_outcomes_read": False,
        "admission_owner_decision_required": True,
    }


def _latest_context(records: list[dict[str, Any]], kind: str, security_id: str,
                    cutoff: datetime, session: str) -> tuple[dict[str, Any] | None, str | None]:
    visible = []
    for record in records:
        if record.get("kind") != kind or record.get("security_id") != security_id:
            continue
        if not record.get("known_at"):
            continue
        if _clock(record["known_at"]) > cutoff:
            continue
        # The current session's final daily values are forbidden intraday,
        # even when an upstream caller incorrectly backdates their receipt.
        if kind == "daily" and record.get("asof_session", "9999") >= session:
            continue
        visible.append(record)
    if not visible:
        return None, f"{kind}:UNAVAILABLE"
    if kind == "daily":
        # A correction to an older daily session must not displace the latest
        # completed daily context merely because its receipt arrived later.
        latest_session = max(x.get("asof_session", "") for x in visible)
        visible = [x for x in visible if x.get("asof_session") == latest_session]
    newest = max(_clock(x["known_at"]) for x in visible)
    tied = [x for x in visible if _clock(x["known_at"]) == newest]
    if len({canonical(x) for x in tied}) != 1:
        return None, f"{kind}:CONFLICTING_REVISION"
    chosen = copy.deepcopy(tied[0])
    if not _has_receipt(chosen):
        return None, f"{kind}:RECEIPT_MISSING"
    return chosen, None


def _metadata_errors(meta: Mapping[str, Any], cutoff: datetime, session: str) -> list[str]:
    errors = []
    identity = meta.get("identity", {})
    if not meta.get("security_id") or not _has_receipt(identity) \
            or not identity.get("known_at") or _clock(identity["known_at"]) > cutoff \
            or identity.get("valid_from", "9999") > session \
            or (identity.get("valid_until") and session >= identity["valid_until"]):
        errors.append("IDENTITY_NOT_BOUND_AT_DECISION")
    basis = meta.get("basis", {})
    if not _has_receipt(basis) or not basis.get("known_at") \
            or _clock(basis["known_at"]) > cutoff or not basis.get("basis_id") \
            or basis.get("price_adjustment") in UNKNOWN \
            or basis.get("volume_adjustment") in UNKNOWN \
            or not _sha(basis.get("corporate_actions_sha256")):
        errors.append("BASIS_NOT_BOUND_AT_DECISION")
    if meta.get("availability_basis") != "observed_first_seen":
        errors.append("FIRST_SEEN_NOT_OBSERVED")
    return errors


def _aggregate(rows: list[dict[str, Any]], stream: str, meta: Mapping[str, Any],
               start: datetime, end: datetime, cutoff: datetime) -> dict[str, Any]:
    """Complete [start,end) from exact 1m rows visible at cutoff, without fills."""
    groups: dict[datetime, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("stream") != stream:
            continue
        event_start = _clock(row["start"])
        if not start <= event_start < end:
            continue
        if not row.get("known_at") or _clock(row["known_at"]) > cutoff:
            continue
        groups.setdefault(event_start, []).append(row)
    expected = [start + timedelta(minutes=i) for i in range(int((end-start).total_seconds()/60))]
    errors, selected, missing = [], [], []
    if any(t not in expected for t in groups):
        errors.append("OFF_GRID_MINUTE")
    for instant in expected:
        versions = groups.get(instant, [])
        if not versions:
            missing.append(_iso(instant))
            continue
        known = max(_clock(r["known_at"]) for r in versions)
        newest = [r for r in versions if _clock(r["known_at"]) == known]
        if len({canonical(r) for r in newest}) != 1:
            errors.append("CONFLICTING_MINUTE_REVISION")
            continue
        row = newest[0]
        if _clock(row["end"]) != instant + timedelta(minutes=1) or known < _clock(row["end"]):
            errors.append("MINUTE_CLOCK_VIOLATION")
        if row.get("security_id") != meta.get("security_id"):
            errors.append("MINUTE_IDENTITY_MISMATCH")
        if row.get("basis_id") != meta.get("basis", {}).get("basis_id"):
            errors.append("MINUTE_BASIS_MISMATCH")
        if not _has_receipt(row) or not row.get("revision_id"):
            errors.append("MINUTE_REVISION_RECEIPT_MISSING")
        prices = [row.get(k) for k in ("open", "high", "low", "close")]
        vol = row.get("volume")
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or v <= 0 for v in prices) \
                or isinstance(vol, bool) or not isinstance(vol, (int, float)) \
                or not math.isfinite(vol) or vol < 0:
            errors.append("INVALID_OHLCV")
        elif not row["low"] <= min(row["open"], row["close"]) <= \
                max(row["open"], row["close"]) <= row["high"]:
            errors.append("INVALID_OHLCV_GEOMETRY")
        selected.append(row)
    if missing:
        errors.append("MISSING_OR_NOT_YET_KNOWN_MINUTE")
    result: dict[str, Any] = {
        "start": _iso(start), "end": _iso(end), "expected_minutes": len(expected),
        "observed_minutes": len(selected), "missing_starts": missing,
        "availability": "unavailable" if errors else "available",
        "refusals": sorted(set(errors)), "ohlcv": None, "known_at": None,
        "input_revision_sha256": None,
    }
    if not errors:
        result.update({
            "ohlcv": {"open": selected[0]["open"], "high": max(r["high"] for r in selected),
                      "low": min(r["low"] for r in selected), "close": selected[-1]["close"],
                      "volume": sum(r["volume"] for r in selected)},
            "known_at": _iso(max(_clock(r["known_at"]) for r in selected)),
            "input_revision_sha256": digest(selected),
        })
    return result


def build_input_panel(bundle: Mapping[str, Any]) -> dict[str, Any]:
    """Preserve every predeclared candidate, including unavailable/nonfire rows.

    Calendar sessions are supplied by the existing calendar owner with a receipt;
    this adapter does not invent another exchange calendar. Calendar timestamps
    and all bars are true UTC instants, never Terminal's ET display epochs.
    """
    if bundle.get("schema") != INPUT_SCHEMA:
        raise InputContractError("unsupported input schema")
    if bundle.get("input_kind") not in {"SYNTHETIC_CONFORMANCE", "OBSERVED_MARKET"}:
        raise InputContractError("input_kind must distinguish fixtures from market evidence")
    candidates = bundle.get("candidates", [])
    ids = [x.get("candidate_id") for x in candidates]
    if not ids or any(not x for x in ids) or len(ids) != len(set(ids)):
        raise InputContractError("nonempty unique predeclared candidate population required")
    calendar = bundle.get("calendar", {})
    if not _has_receipt(calendar):
        raise InputContractError("a frozen calendar-owner receipt is required")
    result = []
    for candidate in candidates:
        cutoff = _clock(candidate["decision_at"])
        session = candidate["session"]
        law = calendar.get("sessions", {}).get(session)
        roles = candidate.get("streams", {})
        if set(roles) != set(ROLES):
            raise InputContractError("each candidate must bind exactly the four input roles")
        frame: dict[str, Any] = {
            "candidate_id": candidate["candidate_id"], "session": session,
            "decision_at": _iso(cutoff), "availability": "unavailable",
            "eligible": None, "condition_met": None, "daily_context": None,
            "incumbent_assessment": None, "catalyst_state": "UNKNOWN",
            "bars": {}, "stream_bindings": {}, "refusals": [], "authority": dict(AUTHORITY_BLOCK),
            "calendar_receipt_sha256": calendar["receipt_sha256"],
            "label_endpoint": None, "label_status": "NOT_COMPUTED_PHASE1",
        }
        errors = frame["refusals"]
        if not law:
            errors.append("SESSION_NOT_IN_OWNER_CALENDAR")
            result.append(frame)
            continue
        opening, closing = _clock(law["open"]), _clock(law["close"])
        if opening >= closing or (closing-opening).total_seconds() % 60:
            raise InputContractError("invalid owner session window")
        if not opening <= cutoff <= closing:
            errors.append("DECISION_OUTSIDE_RTH")
            result.append(frame)
            continue
        if not calendar.get("known_at") or _clock(calendar["known_at"]) > cutoff:
            errors.append("CALENDAR_NOT_KNOWN_AT_DECISION")
            result.append(frame)
            continue
        # Diagnostic coverage endpoint only; no outcome/policy is computed.
        # A later policy study must bind a common episode-origin endpoint.
        endpoint = cutoff + timedelta(minutes=120)
        frame["label_endpoint"] = _iso(min(endpoint, closing))
        if endpoint > closing:
            frame["label_status"] = "CENSORED_SESSION_END"
        for role, stream in roles.items():
            meta = bundle.get("streams", {}).get(stream, {})
            meta_errors = _metadata_errors(meta, cutoff, session)
            errors.extend(f"{role}:{x}" for x in meta_errors)
            frame["stream_bindings"][role] = {
                "stream": stream, "security_id": meta.get("security_id"),
                "identity_receipt_sha256": meta.get("identity", {}).get("receipt_sha256"),
                "basis_id": meta.get("basis", {}).get("basis_id"),
                "basis_receipt_sha256": meta.get("basis", {}).get("receipt_sha256"),
            }
            frame["bars"][role] = {}
            for minutes in (15, 30):
                elapsed = (min(cutoff, closing) - opening).total_seconds()
                completed = int(elapsed // (minutes*60))
                if not completed:
                    frame["bars"][role][str(minutes)] = None
                    errors.append(f"{role}:NO_COMPLETED_{minutes}M_INTERVAL")
                    continue
                end = opening + timedelta(minutes=minutes*completed)
                start = end - timedelta(minutes=minutes)
                aggregate = _aggregate(bundle.get("minutes", []), stream, meta, start, end, cutoff)
                if meta_errors:
                    aggregate.update(availability="unavailable", ohlcv=None,
                                     known_at=None, input_revision_sha256=None)
                    aggregate["refusals"] = sorted(set(aggregate["refusals"] + meta_errors))
                frame["bars"][role][str(minutes)] = aggregate
                errors.extend(f"{role}:{minutes}m:{x}" for x in aggregate["refusals"])
        stock = bundle.get("streams", {}).get(roles["stock"], {}).get("security_id", "")
        daily, error = _latest_context(bundle.get("contexts", []), "daily", stock, cutoff, session)
        if error:
            errors.append(error)
        elif daily.get("asof_session") != law.get("previous_session"):
            errors.append("daily:STALE_ROW")
        else:
            payload = daily.get("payload", {})
            if type(payload.get("is_leader")) is not bool \
                    or type(payload.get("controlled_pullback")) is not bool:
                errors.append("daily:ELIGIBILITY_UNAVAILABLE")
            else:
                frame["daily_context"] = daily
                frame["eligible"] = payload["is_leader"] and payload["controlled_pullback"]
        incumbent, error = _latest_context(bundle.get("contexts", []), "incumbent", stock, cutoff, session)
        if error:
            errors.append(error)
        elif incumbent.get("asof_session") != session or not incumbent.get("valid_until") \
                or _clock(incumbent["valid_until"]) < cutoff:
            errors.append("incumbent:STALE_RECEIPT")
        else:
            payload = incumbent.get("payload", {})
            if payload.get("owner") != "engine.entry_signal.assess" \
                    or "buyable_input" not in payload or not _sha(payload.get("inputs_sha256")) \
                    or not _sha(payload.get("code_sha"), 40) or "assessment" not in payload:
                errors.append("incumbent:FAITHFUL_OWNER_RECEIPT_MISSING")
            else:
                frame["incumbent_assessment"] = incumbent
        catalyst, error = _latest_context(bundle.get("contexts", []), "catalyst", stock, cutoff, session)
        if not error and catalyst.get("asof_session") == session \
                and catalyst.get("valid_until") and _clock(catalyst["valid_until"]) >= cutoff:
            state = catalyst.get("payload", {}).get("coverage_state", "UNKNOWN")
            if state in {"EVENT_OBSERVED", "COVERED_NO_EVENT", "UNKNOWN"}:
                frame["catalyst_state"] = state
        # Unknown catalyst coverage remains explicit; it never becomes no news.
        frame["refusals"] = sorted(set(errors))
        if errors:
            frame["eligible"] = None
            frame["availability"] = "stale" if errors == ["daily:STALE_ROW"] else "unavailable"
        else:
            frame["availability"] = "available"
        result.append(frame)
    for frame in result:
        # This digest depends only on the visible snapshot. The complete input
        # bundle digest below legitimately changes when future inputs change.
        frame["snapshot_sha256"] = digest(frame)
    return {
        "schema": PANEL_SCHEMA, "input_kind": bundle["input_kind"],
        "input_bundle_sha256": digest(bundle), "population_count": len(candidates),
        "retained_count": len(result), "available_count": sum(r["availability"] == "available" for r in result),
        "status": "SYNTHETIC_CONFORMANCE_ONLY" if bundle["input_kind"] == "SYNTHETIC_CONFORMANCE"
                  else "INPUT_PANEL_BUILT_NOT_ADMITTED",
        "frames": result, "authority": dict(AUTHORITY_BLOCK),
        "detector_registered": False, "outcomes_computed": False,
    }
