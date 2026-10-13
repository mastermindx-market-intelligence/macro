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
from datetime import date, datetime, timedelta, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo

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



# The accepted export is an immutable projection of the existing Macro owners,
# not a second exchange calendar. A new export requires a new reviewed pin.
CALENDAR_INPUT_SCHEMA = "mastermind.rs_pullback_launch.calendar_input.v1"
CALENDAR_READ_SCHEMA = "mastermind.rs_pullback_launch.calendar_read.v1"
CALENDAR_MAX_BYTES = 1024 * 1024
CALENDAR_PROJECTION_SHA256 = "d803dc85fcf3318bc78392e1d645b7063881b86eec95cf06f51192e1d836de98"
CALENDAR_SOURCE_REVISION = "112eba2036fd1186e67b914e194f4fa541cfc4df"
CALENDAR_ARTIFACT_REF = (
    "https://github.com/mastermindx-market-intelligence/mastermind-terminal/blob/"
    "c616697d446591d396c6981dda7ba67345671ebc/terminal/lib/usEquitySessionProjection.json"
)
CALENDAR_SOURCE_FILES = {
    "engine/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "lib/__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "engine/session_digest.py": "25ae25d29f1a1e6ce7d38372bbfaaf03e18925072e41aaea8bc3c1c730a14191",
    "lib/nyse_calendar.py": "7c9167fd416babb64c3067ae7e6237615011ad79e26d826e57005486496410ce",
}


def bind_calendar_projection(projection_bytes: bytes, read_receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Retain exact as-read UTF-8 bytes and their receipt without parsing semantics.

    The caller supplies a receipt from the bounded reader, never a historical
    known-at label. Visible receipts verify consistency, not authenticity.
    Preserve this value with the original input bundle for replay; reading a
    replacement file cannot reconstruct an earlier acquisition.
    """
    if not isinstance(projection_bytes, bytes) or not 0 < len(projection_bytes) <= CALENDAR_MAX_BYTES:
        raise InputContractError("calendar projection byte limit")
    try:
        text = projection_bytes.decode("utf-8")
    except UnicodeError as exc:
        raise InputContractError("calendar projection must be UTF-8") from exc
    return {"schema": CALENDAR_INPUT_SCHEMA, "projection_json": text,
            "read_receipt": copy.deepcopy(dict(read_receipt))}


def _epoch_ns(value: datetime) -> int:
    delta = value - datetime(1970, 1, 1, tzinfo=timezone.utc)
    return ((delta.days * 86400 + delta.seconds) * 1000000 + delta.microseconds) * 1000


def _calendar_at(calendar: Mapping[str, Any], cutoff: datetime) -> dict[str, Any] | None:
    """Resolve one retained acquisition at a decision, without a revision store."""
    receipt = calendar.get("read_receipt", {})
    if not isinstance(receipt, Mapping):
        raise InputContractError("calendar read receipt must be an object")
    completed = receipt.get("read_completed_at_utc_ns")
    if type(completed) is not int or completed <= 0:
        raise InputContractError("calendar read completion clock required")
    # Do not inspect future payloads, their hashes, source metadata, or seal.
    # They are not evidence at this decision and must not affect its frame.
    if completed > _epoch_ns(cutoff):
        return None
    started = receipt.get("read_started_at_utc_ns")
    if type(started) is not int or not 0 < started <= completed:
        raise InputContractError("invalid calendar read clock order")
    if receipt.get("schema") != CALENDAR_READ_SCHEMA \
            or not isinstance(receipt.get("source_ref"), str) or not receipt["source_ref"].strip():
        raise InputContractError("invalid calendar read receipt")
    sealed = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if not _sha(receipt.get("receipt_sha256")) or digest(sealed) != receipt["receipt_sha256"]:
        raise InputContractError("calendar read receipt hash mismatch")
    text = calendar.get("projection_json")
    if not isinstance(text, str):
        raise InputContractError("calendar projection exact bytes missing")
    try:
        payload = text.encode("utf-8")
    except UnicodeEncodeError as exc:
        # Valid replay JSON can contain an escaped, unpaired surrogate.
        raise InputContractError("calendar projection must be UTF-8") from exc
    if not 0 < len(payload) <= CALENDAR_MAX_BYTES:
        raise InputContractError("calendar projection byte limit")
    if type(receipt.get("byte_length")) is not int or receipt["byte_length"] != len(payload) \
            or receipt.get("byte_sha256") != hashlib.sha256(payload).hexdigest():
        raise InputContractError("calendar as-read byte hash/length mismatch")
    if receipt.get("artifact_ref") != CALENDAR_ARTIFACT_REF \
            or receipt.get("source_revision") != CALENDAR_SOURCE_REVISION \
            or receipt.get("source_files") != CALENDAR_SOURCE_FILES:
        raise InputContractError("calendar source binding mismatch")

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise InputContractError("duplicate calendar JSON key")
            result[key] = value
        return result

    def reject_constant(value):
        raise InputContractError("nonfinite calendar JSON value")

    try:
        projection = json.loads(text, object_pairs_hook=unique_object,
                                parse_constant=reject_constant)
    except (ValueError, RecursionError) as exc:
        raise InputContractError("malformed calendar projection") from exc
    if not isinstance(projection, dict) \
            or not isinstance(projection.get("source"), dict) \
            or projection.get("schema") != "mastermind.us_equity_session_projection.v1" \
            or projection.get("timezone") != "America/New_York" \
            or projection.get("source", {}).get("repository") != "mastermindx-market-intelligence/macro" \
            or projection.get("source", {}).get("revision") != CALENDAR_SOURCE_REVISION \
            or projection.get("source", {}).get("files") != CALENDAR_SOURCE_FILES:
        raise InputContractError("invalid calendar projection owner")
    if receipt["byte_sha256"] != CALENDAR_PROJECTION_SHA256:
        raise InputContractError("unreviewed calendar projection bytes")
    coverage = projection["coverage"]
    first, last = coverage["start"], coverage["end"]
    windows = projection["sessions"]
    if first != "2016-01-01" or last != "2028-12-31" \
            or not isinstance(windows, dict) or len(windows) != 3267:
        raise InputContractError("invalid calendar projection coverage")
    sessions, previous = {}, None
    zone = ZoneInfo("America/New_York")
    for session, pair in sorted(windows.items()):
        try:
            day = date.fromisoformat(session)
        except (ValueError, TypeError) as exc:
            raise InputContractError("invalid calendar session date") from exc
        if session != day.isoformat() or not first <= session <= last \
                or not isinstance(pair, list) or len(pair) != 2 \
                or any(type(value) is not int for value in pair) \
                or not 0 <= pair[0] < pair[1] <= 1440:
            raise InputContractError("invalid calendar session window")
        midnight = datetime(day.year, day.month, day.day, tzinfo=zone)
        sessions[session] = {
            "open": _iso(midnight + timedelta(minutes=pair[0])),
            "close": _iso(midnight + timedelta(minutes=pair[1])),
            "previous_session": previous,
        }
        previous = session
    # Round UP to a representable microsecond; never backdate a nanosecond read.
    known = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
        microseconds=(completed + 999) // 1000)
    return {"source_ref": receipt["source_ref"], "receipt_sha256": receipt["receipt_sha256"],
            "known_at": _iso(known), "coverage": coverage, "sessions": sessions}


def _known_label(value: Any) -> bool:
    return isinstance(value, str) and value.strip().lower() not in UNKNOWN


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
    args = census.get("terminal_qualifier_args", {})
    try:
        window = {key: args[key] for key in ("from_date", "to_date")}
        if date.fromisoformat(window["from_date"]) > date.fromisoformat(window["to_date"]):
            raise ValueError("reversed qualification window")
        if type(args.get("cutoff_utc")) is not int or args["cutoff_utc"] <= 0 \
                or args.get("mode") != "as_observed":
            raise ValueError("invalid qualification cutoff")
    except (KeyError, TypeError, ValueError) as exc:
        raise InputContractError("freeze one valid owner qualification window and cutoff") from exc
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
        if cutoff.get("utc") != args["cutoff_utc"] or cutoff.get("mode") != args["mode"]:
            refusals.append(f"{role}:QUALIFICATION_CUTOFF_MISMATCH")
        if report.get("qualification_window") != window:
            refusals.append(f"{role}:QUALIFICATION_WINDOW_MISMATCH")
        if report.get("status") != "available" or report.get("valid_rows", 0) <= 0:
            refusals.append(f"{role}:NO_1M_HISTORY")
        if cutoff.get("mode") != "as_observed" or cutoff.get("pit_proven") is not True \
                or cutoff.get("count", 0) <= 0:
            refusals.append(f"{role}:AS_OBSERVED_AVAILABILITY_UNPROVEN")
        if not _known_label(report.get("price_adjustment")) \
                or not _known_label(report.get("volume_adjustment")):
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
    if not meta.get("security_id") or identity.get("security_id") != meta.get("security_id") \
            or not _has_receipt(identity) \
            or not identity.get("known_at") or _clock(identity["known_at"]) > cutoff \
            or identity.get("valid_from", "9999") > session \
            or (identity.get("valid_until") and session >= identity["valid_until"]):
        errors.append("IDENTITY_NOT_BOUND_AT_DECISION")
    basis = meta.get("basis", {})
    if not _has_receipt(basis) or not basis.get("known_at") \
            or _clock(basis["known_at"]) > cutoff or not basis.get("basis_id") \
            or not _known_label(basis.get("price_adjustment")) \
            or not _known_label(basis.get("volume_adjustment")) \
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
        # Receipt visibility comes first: a future row's payload, even if
        # malformed, cannot change the earlier decision prefix.
        if not row.get("known_at") or _clock(row["known_at"]) > cutoff:
            continue
        event_start = _clock(row["start"])
        if not start <= event_start < end:
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
        # No admitted factor/vintage path exists for retained Terminal minutes.
        # A caller scalar cannot turn source declaration provenance into proof.
        # This is input-contract consistency, not source authentication.
        source = row.get("source_observation")
        source_ref = row.get("source_ref")
        if (isinstance(source, Mapping) and
                source.get("observer_id") == "terminal.backfill_intraday") or (
                isinstance(source_ref, str) and source_ref.startswith("terminal-minute-capture:")):
            errors.append("TERMINAL_BASIS_UNPROVEN")
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
    bound_calendar = calendar.get("schema") == CALENDAR_INPUT_SCHEMA
    if not bound_calendar and not _has_receipt(calendar):
        raise InputContractError("a frozen calendar-owner receipt is required")
    result = []
    for candidate in candidates:
        cutoff = _clock(candidate["decision_at"])
        session = candidate["session"]
        calendar_invalid = False
        try:
            visible_calendar = _calendar_at(calendar, cutoff) if bound_calendar else calendar
        except InputContractError:
            # Bad visible source evidence closes this candidate, not the panel.
            # Keep every predeclared row, including earlier unseen decisions.
            # Implementation errors remain errors and are not converted here.
            visible_calendar = None
            calendar_invalid = True
        law = (visible_calendar or {}).get("sessions", {}).get(session)
        roles = candidate.get("streams", {})
        if set(roles) != set(ROLES):
            raise InputContractError("each candidate must bind exactly the four input roles")
        frame: dict[str, Any] = {
            "candidate_id": candidate["candidate_id"], "session": session,
            "decision_at": _iso(cutoff), "availability": "unavailable",
            "eligible": None, "condition_met": None, "daily_context": None,
            "incumbent_assessment": None, "catalyst_state": "UNKNOWN",
            "bars": {}, "stream_bindings": {}, "refusals": [], "authority": dict(AUTHORITY_BLOCK),
            "calendar_receipt_sha256": (visible_calendar or {}).get("receipt_sha256"),
            "label_endpoint": None, "label_status": "NOT_COMPUTED_PHASE1",
        }
        errors = frame["refusals"]
        if visible_calendar is None:
            errors.append("CALENDAR_INPUT_INVALID" if calendar_invalid
                          else "CALENDAR_NOT_KNOWN_AT_DECISION")
            result.append(frame)
            continue
        if bound_calendar:
            coverage = visible_calendar["coverage"]
            if not coverage["start"] <= session <= coverage["end"]:
                errors.append("CALENDAR_COVERAGE_UNKNOWN")
                result.append(frame)
                continue
            if law and not law["previous_session"]:
                errors.append("CALENDAR_PREDECESSOR_UNKNOWN")
                result.append(frame)
                continue
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
        if not visible_calendar.get("known_at") or _clock(visible_calendar["known_at"]) > cutoff:
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
            prior = visible_calendar.get("sessions", {}).get(law.get("previous_session"), {})
            prior_close = _clock(prior["close"]) if prior.get("close") else None
            payload = daily.get("payload", {})
            if prior_close is None or prior_close >= opening:
                errors.append("daily:COMPLETION_CLOCK_UNPROVEN")
            elif _clock(daily["known_at"]) < prior_close:
                errors.append("daily:RECEIPT_BEFORE_SESSION_CLOSE")
            elif type(payload.get("is_leader")) is not bool \
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
                    or (payload["buyable_input"] is not None and type(payload["buyable_input"]) is not bool) \
                    or not _sha(payload.get("code_sha"), 40) \
                    or not isinstance(payload.get("assessment"), Mapping) or not payload["assessment"]:
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
        **({"calendar_source_snapshot": copy.deepcopy(calendar)} if bound_calendar else {}),
        "schema": PANEL_SCHEMA, "input_kind": bundle["input_kind"],
        "input_bundle_sha256": digest(bundle), "population_count": len(candidates),
        "retained_count": len(result), "available_count": sum(r["availability"] == "available" for r in result),
        "status": "SYNTHETIC_CONFORMANCE_ONLY" if bundle["input_kind"] == "SYNTHETIC_CONFORMANCE"
                  else "INPUT_PANEL_BUILT_NOT_ADMITTED",
        "frames": result, "authority": dict(AUTHORITY_BLOCK),
        "detector_registered": False, "outcomes_computed": False,
    }
