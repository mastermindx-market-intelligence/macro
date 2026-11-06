"""Outcome-blind PB-D first-T2 cohort and frozen exact-pair mechanics.

This module performs no I/O, enrollment, scheduling, signal calculation, price
lookup, or qledger registration.  In particular, a PB-D morning cut is not a
qledger nightly registration date.  Supplied owner receipts are checked for
internal consistency; their authenticity is not established by this module.

Public JSON interface
---------------------
``freeze_cohort(payload)`` accepts only these top-level fields::

    operation_key, cohort_id, first_cut_date, through_cut_date,
    versions, schedule, cuts

``versions`` has seven nonempty string values: ``board_population``,
``technical``, ``config_digest``, ``attention``, ``label_spec``,
``benchmark_mapping`` and ``price_convention``.
They describe one frozen era and must be identical in every board receipt.

``schedule`` contains ``calendar_id='XNYS'``,
``timezone='America/New_York'``, ``source_id``, ``version``,
``validation_receipt_id``, ``validated=True``, ``validated_at``,
``coverage_start``, ``coverage_end`` and ``sessions``.  Each session has
``session_date``, ``market_open`` and ``market_close``.  The external calendar
owner must supply and attest a complete session list for the coverage interval;
structural checks here cannot detect an omitted holiday or session.  No weekday
calendar or 16:00 closing-time fallback exists.  The schedule must include the
three prior decision cuts and all 21 exit sessions for each requested cut.

Each item of ``cuts`` contains ``decision_date``, ``board_receipt`` (or null),
``rows`` and ``quality_by_observation``.  Include EVERY supplied-calendar session
from ``first_cut_date`` through ``through_cut_date``, including missing boards.
There can be at most 252 enrollment cuts.  The first cut and cohort identity are
research input declarations, not an activation or authority receipt.

A board receipt contains ``receipt_id``, ``population='us_prophet_v3'``,
``lane='buy'``, ``published=True``, ``board_session_date``,
``price_session_date``, ``board_as_of_at``, ``generated_at``, ``received_at``,
``price_as_of_at``, ``source_snapshot_sha256``, ``price_source_vintage`` and
``versions``.  Prices must be as of the immediately prior scheduled close;
as-of <= generation <= actual local receipt <= cut.  An absent, stale, malformed,
or late receipt quarantines the entire cut.  A version change ends the era.

Each row has ``observation_id``, ``canonical_issuer_id``, ``ticker_at_cut``,
``emitted_tier``, ``technical_attested``, ``technical_receipt_id``,
``native_event_id``, ``native_event_date``, ``native_t2_age``,
``native_t2_age_unit='native_2D_ticks'``, ``sector``, ``sector_benchmark``,
``benchmark_mapping_complete``, ``attention_n_recent``, and
``attention_coverage_complete``.  Nullable evidence, age, sector and count fields
preserve unknown.  The authoritative emitted tier is consumed, never recomputed;
T1 rows do not consume a first-T2 slot.  An emitted T2 DOES consume its issuer's
slot before technical, quality, attention, benchmark or matching exclusions.
Missing native age is therefore a retained quarantine, not a replacement chance.

Optional row ``firstness_history`` is a supplied owner-native absence receipt:
``receipt_id``, ``owner='us_prophet_v3'``, ``canonical_issuer_id``,
``coverage_first_cut_date``, ``coverage_through_cut_date``,
``coverage_complete=True``, ``no_prior_t2=True``, ``generated_at``,
``observed_at`` and ``source_snapshot_sha256``.  It must cover the whole earlier
cohort prefix and be available by this cut.  Without it, a prior quarantined
board leaves firstness unknown for newly seen issuers.  A later proof never
replaces an already consumed first observation.

``quality_by_observation`` maps stable observation IDs to immutable receipts
from ``engine.company_intelligence.pb_d_quality.build_quality_receipt``.
Quality is inspected only after the first emitted T2 is consumed.  Missing,
invalid, mismatched or late quality is UNKNOWN, never FALSE.  No outcome fields,
entry statuses, price arrays, or arbitrary row metadata are accepted.

Output is a JSON-compatible hash envelope with ``manifest``,
``manifest_sha256`` and append-only ``corrections``.  ``manifest['first_t2']``
retains every consumed first T2, ``pairs`` contains the original exact pairs,
and ``accounting`` gives all denominators.  ``rematch_omission`` derives a
prespecified sensitivity from the entire original eligible pool, including its
unmatched members, without reading outcomes or replacing first observations.
``verify_manifest`` detects edits; ``append_correction`` returns a new envelope
without changing the original manifest, its hash, Q states, or pairs.  Hashes
are integrity checks, not signatures.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, time, timezone
import hashlib
import json
import re
from typing import Any, Mapping
from zoneinfo import ZoneInfo


OPERATION_KEY = "PB-D-T2-EVENT-QUALITY-20261007"
SCHEMA = "pb_d_cohort_freeze.v1"
DESIGN_COMMIT = "df2091915159dab94f316718caa9b2662098eae4"
REFERENCE_CONFLUENCE_BLOB = "004eda921766922e146d35acc6ee2bc646e96854"
REFERENCE_SIGNAL_GATE_BLOB = "cccf77910f875925910e5adda14bbb33d6dc942d"
HORIZONS = (1, 5, 10, 21)
NY = ZoneInfo("America/New_York")
UTC = timezone.utc
VERSION_KEYS = frozenset({
    "board_population", "technical", "config_digest", "attention", "label_spec",
    "benchmark_mapping", "price_convention",
})
AUTHORITY_FLAGS = {key: False for key in (
    "enrollment", "registration", "ranking", "sizing", "entry", "alerts", "trading",
)}
_TIMESTAMP = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class CohortInputError(ValueError):
    """Malformed or incomplete input prevents an honest cohort freeze."""


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
        raise CohortInputError(f"{field} must be a mapping with string keys")
    return value


def _fields(value: Any, required: set | frozenset, field: str,
            optional: set | frozenset = frozenset()) -> Mapping[str, Any]:
    value = _mapping(value, field)
    missing, extra = required - value.keys(), value.keys() - required - optional
    if missing:
        raise CohortInputError(f"{field} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise CohortInputError(f"{field} unsupported fields: {', '.join(sorted(extra))}")
    return value


def _text(value: Any, field: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value or value != value.strip():
        raise CohortInputError(f"{field} must be a nonempty unpadded string")
    return value


def _identifier(value: Any, field: str) -> str:
    value = _text(value, field)
    if "|" in value:
        raise CohortInputError(f"{field} cannot contain the hash delimiter '|'")
    return value


def _date(value: Any, field: str) -> date:
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise CohortInputError(f"{field} must be an ISO date")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise CohortInputError(f"{field} is not a valid date") from exc


def _instant(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not _TIMESTAMP.fullmatch(value):
        raise CohortInputError(f"{field} must have seconds and an explicit timezone")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError as exc:
        raise CohortInputError(f"{field} is not a valid timestamp") from exc


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CohortInputError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise CohortInputError("input must be finite JSON data") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _versions(value: Any) -> dict[str, str]:
    value = _fields(value, VERSION_KEYS, "versions")
    return {key: _text(value[key], f"versions.{key}") for key in sorted(VERSION_KEYS)}


def _schedule(value: Any) -> tuple[dict, list[tuple[date, datetime, datetime]]]:
    value = _fields(value, {
        "calendar_id", "timezone", "source_id", "version", "validation_receipt_id",
        "validated", "validated_at", "coverage_start", "coverage_end", "sessions",
    }, "schedule")
    if value["calendar_id"] != "XNYS" or value["timezone"] != "America/New_York":
        raise CohortInputError("an explicit XNYS / America/New_York schedule is required")
    if value["validated"] is not True:
        raise CohortInputError("schedule needs an external calendar-owner validation receipt")
    normalized = {key: _text(value[key], f"schedule.{key}") for key in (
        "calendar_id", "timezone", "source_id", "version", "validation_receipt_id",
    )}
    start = _date(value["coverage_start"], "schedule.coverage_start")
    end = _date(value["coverage_end"], "schedule.coverage_end")
    if start > end:
        raise CohortInputError("schedule coverage is reversed")
    normalized.update({
        "validated": True,
        "validated_at": _utc(_instant(value["validated_at"], "schedule.validated_at")),
        "coverage_start": start.isoformat(), "coverage_end": end.isoformat(),
        "validation_scope": "supplied_owner_attestation_and_structural_checks_only",
    })
    if not isinstance(value["sessions"], list) or not value["sessions"]:
        raise CohortInputError("schedule.sessions must be a nonempty explicit list")
    sessions = []
    for entry in value["sessions"]:
        entry = _fields(entry, {"session_date", "market_open", "market_close"}, "session")
        day = _date(entry["session_date"], "session.session_date")
        opened = _instant(entry["market_open"], "session.market_open")
        closed = _instant(entry["market_close"], "session.market_close")
        if not start <= day <= end:
            raise CohortInputError("session is outside the attested schedule coverage")
        if opened.astimezone(NY).date() != day or closed.astimezone(NY).date() != day:
            raise CohortInputError("session clocks must belong to its New York session date")
        if opened >= closed:
            raise CohortInputError("session open must precede its explicit close")
        if sessions and (day <= sessions[-1][0] or opened <= sessions[-1][2]):
            raise CohortInputError("sessions must be unique and strictly chronological")
        sessions.append((day, opened, closed))
    normalized["sessions"] = [
        {"session_date": day.isoformat(), "market_open": _utc(opened),
         "market_close": _utc(closed)} for day, opened, closed in sessions
    ]
    return normalized, sessions


def _clock(normalized: Mapping[str, Any], sessions: list, day: date) -> dict:
    dates = [session[0] for session in sessions]
    if day not in dates:
        raise CohortInputError("decision date is not in the supplied session schedule")
    index = dates.index(day)
    if index < 3:
        raise CohortInputError("schedule must include three prior decision sessions")
    cut = datetime.combine(day, time(9, 15), NY).astimezone(UTC)
    if not sessions[index - 1][2] < cut < sessions[index][1]:
        raise CohortInputError("09:15 cut must follow the prior close and precede this open")
    if _instant(normalized["validated_at"], "schedule.validated_at") > cut:
        raise CohortInputError("schedule validation was unavailable at the decision cut")
    entry_index = next(i for i, session in enumerate(sessions) if session[2] > cut)
    if entry_index + max(HORIZONS) >= len(sessions):
        raise CohortInputError("schedule lacks explicit sessions through the H21 exit")
    freshness_start = datetime.combine(dates[index - 3], time(9, 15), NY).astimezone(UTC)
    return {
        "decision_date": day.isoformat(), "cut_at_utc": _utc(cut),
        "cut_at_new_york": cut.astimezone(NY).isoformat(),
        "board_session_date": dates[index - 1].isoformat(),
        "board_session_close_at_utc": _utc(sessions[index - 1][2]),
        "freshness_start_utc": _utc(freshness_start), "freshness_end_utc": _utc(cut),
        "freshness_interval": "(start,end]",
        "entry_session_date": dates[entry_index].isoformat(),
        "entry_close_at_utc": _utc(sessions[entry_index][2]),
        "exits": {
            f"H{h}": {"session_date": dates[entry_index + h].isoformat(),
                       "close_at_utc": _utc(sessions[entry_index + h][2])}
            for h in HORIZONS
        },
        "schedule_sha256": _digest(normalized),
    }


def decision_clock(schedule: Mapping[str, Any], decision_date: str) -> dict:
    """Resolve the morning cut and exact scheduled closes, without price access.

    All calendar gaps and early closes come from the supplied owner schedule.
    H1 is one completed session AFTER entry; H5 is five sessions after entry.
    """
    normalized, sessions = _schedule(schedule)
    return _clock(normalized, sessions, _date(decision_date, "decision_date"))


def issuer_order_hash(operation_key: str, cohort_id: str, canonical_issuer_id: str) -> str:
    """The preregistered SHA256(operation|cohort|canonical issuer) order."""
    pieces = [_identifier(value, field) for value, field in (
        (operation_key, "operation_key"), (cohort_id, "cohort_id"),
        (canonical_issuer_id, "canonical_issuer_id"),
    )]
    return hashlib.sha256("|".join(pieces).encode("utf-8")).hexdigest()


_BOARD_FIELDS = frozenset({
    "receipt_id", "population", "lane", "published", "board_session_date",
    "price_session_date", "board_as_of_at", "generated_at", "received_at",
    "price_as_of_at", "source_snapshot_sha256", "price_source_vintage", "versions",
})


def _board(receipt: Any, clock: Mapping[str, Any], versions: dict) -> tuple[dict | None, list]:
    if receipt is None:
        return None, ["MISSING_BOARD_RECEIPT"]
    if isinstance(receipt, Mapping) and receipt.keys() - _BOARD_FIELDS:
        raise CohortInputError("board_receipt has unsupported fields; outcome data are not accepted")
    # Bad receipt evidence quarantines the cut, retaining its raw JSON provenance.
    _canonical(receipt)
    try:
        receipt = _fields(receipt, _BOARD_FIELDS, "board_receipt")
        normalized = deepcopy(dict(receipt))
        _identifier(receipt["receipt_id"], "board_receipt.receipt_id")
        _sha(receipt["source_snapshot_sha256"], "board_receipt.source_snapshot_sha256")
        _text(receipt["price_source_vintage"], "board_receipt.price_source_vintage")
        issues = []
        if (receipt["population"] != "us_prophet_v3" or receipt["lane"] != "buy"
                or receipt["published"] is not True):
            issues.append("NOT_SUPPLIED_PUBLISHED_USV3_BUY_BOARD")
        if _versions(receipt["versions"]) != versions:
            issues.append("VERSION_ERA_CHANGED")
        for field in ("board_session_date", "price_session_date"):
            if _date(receipt[field], field).isoformat() != clock["board_session_date"]:
                issues.append(f"{field.upper()}_NOT_PREVIOUS_SESSION")
        instants = {field: _instant(receipt[field], field) for field in (
            "board_as_of_at", "generated_at", "received_at", "price_as_of_at",
        )}
        normalized.update({field: _utc(value) for field, value in instants.items()})
        prior_close = _instant(clock["board_session_close_at_utc"], "prior_close")
        cut = _instant(clock["cut_at_utc"], "cut")
        if instants["price_as_of_at"] != prior_close:
            issues.append("PRICE_AS_OF_NOT_PREVIOUS_SCHEDULED_CLOSE")
        if not (prior_close <= instants["board_as_of_at"] <= instants["generated_at"]
                <= instants["received_at"]):
            issues.append("CONTRADICTORY_BOARD_RECEIPT_CLOCKS")
        if any(value > cut for value in instants.values()):
            issues.append("BOARD_OR_PRICE_UNAVAILABLE_AT_CUT")
        return normalized, sorted(set(issues))
    except CohortInputError as exc:
        return deepcopy(receipt), [f"MALFORMED_BOARD_RECEIPT: {exc}"]


_ROW_FIELDS = frozenset({
    "observation_id", "canonical_issuer_id", "ticker_at_cut", "emitted_tier",
    "technical_attested", "technical_receipt_id", "native_event_id",
    "native_event_date", "native_t2_age", "native_t2_age_unit", "sector",
    "sector_benchmark", "benchmark_mapping_complete", "attention_n_recent",
    "attention_coverage_complete",
})
_HISTORY_FIELDS = frozenset({
    "receipt_id", "owner", "canonical_issuer_id", "coverage_first_cut_date",
    "coverage_through_cut_date", "coverage_complete", "no_prior_t2",
    "generated_at", "observed_at", "source_snapshot_sha256",
})


def _row(value: Any) -> dict:
    value = _fields(value, _ROW_FIELDS, "row", {"firstness_history"})
    result = deepcopy(dict(value))
    for key in ("observation_id", "canonical_issuer_id", "ticker_at_cut"):
        _identifier(value[key], f"row.{key}")
    for key in ("emitted_tier", "technical_receipt_id", "native_event_id", "sector",
                "sector_benchmark", "native_t2_age_unit"):
        _text(value[key], f"row.{key}", nullable=True)
    for key in ("technical_attested", "benchmark_mapping_complete", "attention_coverage_complete"):
        if value[key] is not None and type(value[key]) is not bool:
            raise CohortInputError(f"row.{key} must be true, false or null")
    for key in ("native_t2_age", "attention_n_recent"):
        if value[key] is not None and (type(value[key]) is not int or value[key] < 0):
            raise CohortInputError(f"row.{key} must be a nonnegative integer or null")
    if value["native_event_date"] is not None:
        _date(value["native_event_date"], "row.native_event_date")
    history = value.get("firstness_history")
    if history is not None:
        # Validate even when the supplied board prefix is complete and this
        # optional receipt will not be consulted.  Unused metadata is not an
        # escape hatch for outcome data or untyped arbitrary JSON.
        history = _fields(history, _HISTORY_FIELDS, "firstness_history")
        for key in ("receipt_id", "owner", "canonical_issuer_id"):
            _identifier(history[key], f"firstness_history.{key}")
        for key in ("coverage_first_cut_date", "coverage_through_cut_date"):
            _date(history[key], f"firstness_history.{key}")
        for key in ("generated_at", "observed_at"):
            _instant(history[key], f"firstness_history.{key}")
        for key in ("coverage_complete", "no_prior_t2"):
            if type(history[key]) is not bool:
                raise CohortInputError(f"firstness_history.{key} must be a strict boolean")
        _sha(history["source_snapshot_sha256"], "firstness_history.source_snapshot_sha256")
    return result


def _history_proves_first(row: dict, first_day: date, previous_day: date, cut: datetime) -> bool:
    history = row.get("firstness_history")
    if history is None:
        return False
    try:
        history = _fields(history, _HISTORY_FIELDS, "firstness_history")
        _identifier(history["receipt_id"], "firstness_history.receipt_id")
        _sha(history["source_snapshot_sha256"], "firstness_history.source_snapshot_sha256")
        return (
            history["owner"] == "us_prophet_v3"
            and history["canonical_issuer_id"] == row["canonical_issuer_id"]
            and history["coverage_complete"] is True and history["no_prior_t2"] is True
            and _date(history["coverage_first_cut_date"], "history start") == first_day
            and _date(history["coverage_through_cut_date"], "history end") == previous_day
            and _instant(history["generated_at"], "history generated_at")
            <= _instant(history["observed_at"], "history observed_at") <= cut
        )
    except CohortInputError:
        return False


def _verify_quality_receipt(receipt: Any) -> bool:
    """Pure owner-validator seam, also allowing isolated cohort unit tests."""
    from engine.company_intelligence.pb_d_quality import verify_quality_receipt

    return verify_quality_receipt(receipt)


def _quality(receipt: Any, issuer: str, clock: dict, label_spec: str) -> tuple[str, list[str], str | None]:
    if receipt is None:
        return "UNKNOWN", ["MISSING_QUALITY_RECEIPT"], None

    if _verify_quality_receipt(receipt) is not True:
        return "UNKNOWN", ["INVALID_QUALITY_RECEIPT"], None
    digest = receipt["receipt_sha256"]
    try:
        cut = _instant(clock["cut_at_utc"], "cut")
        if receipt.get("spec_version") != label_spec:
            return "UNKNOWN", ["QUALITY_LABEL_SPEC_VERSION_MISMATCH"], digest
        if receipt["issuer_id"] != issuer:
            return "UNKNOWN", ["QUALITY_ISSUER_MISMATCH"], digest
        if _instant(receipt["decision_cut"], "quality decision cut") != cut:
            return "UNKNOWN", ["QUALITY_CUT_MISMATCH"], digest
        if (_instant(receipt["freshness_start"], "quality freshness start")
                != _instant(clock["freshness_start_utc"], "freshness start")):
            return "UNKNOWN", ["QUALITY_FRESHNESS_WINDOW_MISMATCH"], digest
        completed_at = receipt.get("completed_at")
        reasons = receipt["q_reasons"]
        if not isinstance(reasons, list) or any(not isinstance(reason, str) for reason in reasons):
            return "UNKNOWN", ["INVALID_QUALITY_REASONS"], digest
        if completed_at is None:
            return "UNKNOWN", sorted(set(reasons + ["QUALITY_INCOMPLETE_AT_CUT"])), digest
        if _instant(completed_at, "quality completed_at") > cut:
            return "UNKNOWN", ["QUALITY_COMPLETED_AFTER_CUT"], digest
        if receipt["q"] not in ("TRUE", "FALSE", "UNKNOWN"):
            return "UNKNOWN", ["INVALID_QUALITY_STATE"], digest
        return receipt["q"], reasons[:], digest
    except (CohortInputError, KeyError, TypeError):
        return "UNKNOWN", ["MALFORMED_QUALITY_RECEIPT_CLOCKS"], digest


def _first_record(row: dict, clock: dict, board: dict, firstness: str,
                  quality_receipt: Any, operation: str, cohort: str) -> dict:
    issues = []
    if firstness == "UNKNOWN_BOARD_GAP":
        issues.append("FIRST_T2_STATUS_UNKNOWN_AFTER_BOARD_GAP")
    if row["technical_attested"] is not True or not row["technical_receipt_id"]:
        issues.append("MISSING_TECHNICAL_OWNER_ATTESTATION")
    if not row["native_event_id"] or row["native_event_date"] is None:
        issues.append("MISSING_NATIVE_T2_EVENT_IDENTITY")
    elif row["native_event_date"] > clock["board_session_date"]:
        issues.append("NATIVE_T2_EVENT_AFTER_BOARD_SESSION")
    if row["native_t2_age"] not in (0, 1, 2):
        issues.append("MISSING_OR_INVALID_NATIVE_T2_AGE")
    if row["native_t2_age_unit"] != "native_2D_ticks":
        issues.append("NATIVE_T2_AGE_UNIT_NOT_ATTESTED")
    if row["attention_coverage_complete"] is True and row["attention_n_recent"] is not None:
        attention = "TRUE" if row["attention_n_recent"] >= 3 else "FALSE"
    else:
        attention = "UNKNOWN"
        issues.append("UNKNOWN_RAW_ATTENTION")
    if (row["benchmark_mapping_complete"] is not True or row["sector"] is None
            or row["sector_benchmark"] is None):
        issues.append("INCOMPLETE_FROZEN_SECTOR_BENCHMARK_MAPPING")
    q, q_reasons, q_digest = _quality(
        quality_receipt, row["canonical_issuer_id"], clock, board["versions"]["label_spec"],
    )
    if q == "UNKNOWN":
        issues.append("UNKNOWN_PRIMARY_QUALITY")
    return {
        **row, "decision_date": clock["decision_date"],
        "decision_cut": clock["cut_at_utc"], "board_receipt_id": board["receipt_id"],
        "firstness": firstness, "primary_slot_consumed": True,
        "q": q, "q_reasons": q_reasons, "quality_receipt_sha256": q_digest,
        "raw_attention": attention,
        "issuer_order_sha256": issuer_order_hash(operation, cohort, row["canonical_issuer_id"]),
        "matching_eligible": not issues, "matching_exclusion_reasons": sorted(issues),
        "entry_session_date": clock["entry_session_date"],
        "entry_close_at_utc": clock["entry_close_at_utc"], "exits": deepcopy(clock["exits"]),
    }


def _match(first_t2: list[dict], operation: str, cohort: str) -> tuple[list, list]:
    # One frozen sector cannot silently map to two benchmarks on a date.
    mappings = defaultdict(set)
    for row in first_t2:
        if (row["benchmark_mapping_complete"] is True and row["sector"] is not None
                and row["sector_benchmark"] is not None):
            mappings[(row["decision_date"], row["sector"])].add(row["sector_benchmark"])
    strata = defaultdict(lambda: {"TRUE": [], "FALSE": []})
    unmatched, pairs = [], []
    for row in first_t2:
        if len(mappings[(row["decision_date"], row["sector"])]) > 1:
            row["matching_eligible"] = False
            row["matching_exclusion_reasons"] = sorted(set(
                row["matching_exclusion_reasons"] + ["INCONSISTENT_SECTOR_BENCHMARK_MAPPING"]
            ))
        if not row["matching_eligible"]:
            unmatched.append({"observation_id": row["observation_id"],
                              "canonical_issuer_id": row["canonical_issuer_id"],
                              "q": row["q"], "reasons": row["matching_exclusion_reasons"][:]})
            continue
        key = (row["decision_date"], row["sector"], row["raw_attention"], row["native_t2_age"])
        strata[key][row["q"]].append(row)
    for key, groups in sorted(strata.items()):
        treated, controls = [sorted(groups[q], key=lambda row: (
            row["issuer_order_sha256"], row["canonical_issuer_id"],
        )) for q in ("TRUE", "FALSE")]
        for t, c in zip(treated, controls):
            identity = "|".join([operation, cohort, key[0], t["canonical_issuer_id"], c["canonical_issuer_id"]])
            pairs.append({
                "pair_id": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
                "decision_date": key[0], "sector": key[1], "raw_attention": key[2],
                "native_t2_age": key[3], "native_t2_age_unit": "native_2D_ticks",
                "q1_observation_id": t["observation_id"],
                "q1_issuer_id": t["canonical_issuer_id"],
                "q0_observation_id": c["observation_id"],
                "q0_issuer_id": c["canonical_issuer_id"],
                "q1_order_sha256": t["issuer_order_sha256"],
                "q0_order_sha256": c["issuer_order_sha256"],
                "sector_benchmark": t["sector_benchmark"], "market_benchmark": "SPY",
                "entry_session_date": t["entry_session_date"],
                "entry_close_at_utc": t["entry_close_at_utc"], "exits": deepcopy(t["exits"]),
            })
        n = min(len(treated), len(controls))
        for leftovers, reason in (
            (treated[n:], "NO_CONTROL_IN_EXACT_STRATUM"),
            (controls[n:], "EXCESS_CONTROL_IN_EXACT_STRATUM"),
        ):
            unmatched.extend({"observation_id": row["observation_id"],
                              "canonical_issuer_id": row["canonical_issuer_id"],
                              "q": row["q"], "reasons": [reason]} for row in leftovers)
    unmatched.sort(key=lambda row: row["observation_id"])
    return pairs, unmatched


def freeze_cohort(payload: Mapping[str, Any]) -> dict:
    """Freeze first T2 observations and exact Q1:Q0 pairs before outcomes.

    This is a pure, from-the-declared-start replay over supplied decision receipts.
    It is not an incremental writer.  A caller must preserve an emitted envelope
    and append corrections instead of replacing that original as-known freeze.
    """
    payload = _fields(payload, {
        "operation_key", "cohort_id", "first_cut_date", "through_cut_date",
        "versions", "schedule", "cuts",
    }, "cohort payload")
    operation = _identifier(payload["operation_key"], "operation_key")
    if operation != OPERATION_KEY:
        raise CohortInputError("operation_key does not match the frozen PB-D design")
    cohort = _identifier(payload["cohort_id"], "cohort_id")
    first_day = _date(payload["first_cut_date"], "first_cut_date")
    through_day = _date(payload["through_cut_date"], "through_cut_date")
    if through_day < first_day:
        raise CohortInputError("cohort cut interval is reversed")
    versions = _versions(payload["versions"])
    schedule, sessions = _schedule(payload["schedule"])
    dates = [session[0] for session in sessions]
    if first_day not in dates or through_day not in dates:
        raise CohortInputError("cohort endpoints must be supplied-calendar sessions")
    expected_dates = [day for day in dates if first_day <= day <= through_day]
    if len(expected_dates) > 252:
        raise CohortInputError("the fixed cohort cannot exceed 252 enrollment sessions")
    if not isinstance(payload["cuts"], list):
        raise CohortInputError("cuts must be an explicit list")
    cuts = {}
    seen_observation_ids = set()
    for cut_input in payload["cuts"]:
        cut_input = _fields(cut_input, {
            "decision_date", "board_receipt", "rows", "quality_by_observation",
        }, "cut")
        day = _date(cut_input["decision_date"], "cut.decision_date")
        if day in cuts:
            raise CohortInputError("duplicate decision cut")
        if not isinstance(cut_input["rows"], list):
            raise CohortInputError("cut.rows must be an explicit list")
        rows = [_row(row) for row in cut_input["rows"]]
        issuers = [row["canonical_issuer_id"] for row in rows]
        if len(set(issuers)) != len(issuers):
            raise CohortInputError("duplicate canonical issuer on one cut needs owner resolution")
        row_ids = {row["observation_id"] for row in rows}
        if len(row_ids) != len(rows) or seen_observation_ids & row_ids:
            raise CohortInputError("observation_id must be unique across all supplied cuts")
        seen_observation_ids.update(row_ids)
        quality = _mapping(cut_input["quality_by_observation"], "quality_by_observation")
        if quality.keys() - row_ids:
            raise CohortInputError("quality receipt refers to an absent observation on its cut")
        cuts[day] = {**cut_input, "rows": sorted(rows, key=lambda row: row["canonical_issuer_id"])}
    if sorted(cuts) != expected_dates:
        raise CohortInputError("include every scheduled cut, with null board receipts for gaps")

    first_t2, repeats, other_rows, board_receipts, clocks = [], [], [], [], []
    consumed = {}
    prefix_complete = True
    era_ended_before = None
    for day in expected_dates:
        clock = _clock(schedule, sessions, day)
        clocks.append(clock)
        cut_input = cuts[day]
        board, board_issues = _board(cut_input["board_receipt"], clock, versions)
        if "VERSION_ERA_CHANGED" in board_issues and era_ended_before is None:
            era_ended_before = day.isoformat()
        if era_ended_before is not None:
            board_issues = sorted(set(board_issues + ["COHORT_TECHNICAL_OR_INPUT_ERA_ENDED"]))
        board_receipts.append({
            "decision_date": day.isoformat(), "receipt": board,
            "receipt_admissible": not board_issues, "issues": board_issues,
            "supplied_row_count": len(cut_input["rows"]),
        })
        if board_issues:
            prefix_complete = False
            other_rows.extend({
                "observation_id": row["observation_id"],
                "canonical_issuer_id": row["canonical_issuer_id"],
                "decision_date": day.isoformat(), "emitted_tier": row["emitted_tier"],
                "disposition": "BOARD_RECEIPT_QUARANTINED", "reasons": board_issues[:],
            } for row in cut_input["rows"])
            continue
        for row in cut_input["rows"]:
            issuer = row["canonical_issuer_id"]
            if row["emitted_tier"] != "T2":
                other_rows.append({
                    "observation_id": row["observation_id"], "canonical_issuer_id": issuer,
                    "decision_date": day.isoformat(), "emitted_tier": row["emitted_tier"],
                    "disposition": "NOT_EMITTED_T2", "reasons": [],
                })
                continue
            if issuer in consumed:
                repeats.append({
                    "observation_id": row["observation_id"], "canonical_issuer_id": issuer,
                    "decision_date": day.isoformat(), "native_event_id": row["native_event_id"],
                    "first_observation_id": consumed[issuer],
                    "disposition": "PRIMARY_SLOT_ALREADY_CONSUMED",
                })
                continue
            # The first-T2 slot is consumed BEFORE even reading this quality value.
            consumed[issuer] = row["observation_id"]
            firstness = "COMPLETE_SUPPLIED_BOARD_PREFIX"
            if not prefix_complete:
                previous_day = dates[dates.index(day) - 1]
                firstness = "OWNER_NATIVE_HISTORY_ATTESTATION" if _history_proves_first(
                    row, first_day, previous_day, _instant(clock["cut_at_utc"], "cut")
                ) else "UNKNOWN_BOARD_GAP"
            first_t2.append(_first_record(
                row, clock, board, firstness,
                cut_input["quality_by_observation"].get(row["observation_id"]), operation, cohort,
            ))

    pairs, unmatched = _match(first_t2, operation, cohort)
    known_q = sum(row["q"] in ("TRUE", "FALSE") for row in first_t2)
    eligible_treated = sum(row["matching_eligible"] and row["q"] == "TRUE" for row in first_t2)
    eligible_controls = sum(row["matching_eligible"] and row["q"] == "FALSE" for row in first_t2)
    exclusion_counts = Counter(reason for row in first_t2 for reason in row["matching_exclusion_reasons"])
    manifest = {
        "operation_key": operation, "cohort_id": cohort,
        "status": "FROZEN_RESEARCH_INPUTS_NOT_ENROLLED", "research_only": True,
        "enrollment_status": "NOT_ENROLLED",
        "authority_flags": dict(AUTHORITY_FLAGS),
        "provenance_scope": "structural_validation_of_supplied_owner_receipts_only",
        "design_commit": DESIGN_COMMIT,
        "reference_confluence_tiers_blob": REFERENCE_CONFLUENCE_BLOB,
        "reference_signal_gate_blob": REFERENCE_SIGNAL_GATE_BLOB,
        "first_cut_date": first_day.isoformat(), "through_cut_date": through_day.isoformat(),
        "fixed_enrollment_sessions": 252, "era_ended_before_cut": era_ended_before,
        "versions": versions, "schedule": schedule, "clocks": clocks,
        "board_receipts": board_receipts, "first_t2": first_t2,
        "repeated_t2_observations": repeats, "other_observations": other_rows,
        "pairs": pairs, "unmatched": unmatched,
        "accounting": {
            "scheduled_cuts": len(expected_dates),
            "admissible_board_cuts": sum(row["receipt_admissible"] for row in board_receipts),
            "quarantined_board_cuts": sum(not row["receipt_admissible"] for row in board_receipts),
            "supplied_board_rows": sum(len(cut["rows"]) for cut in cuts.values()),
            "first_observed_t2": len(first_t2),
            "firstness_unknown": sum(row["firstness"] == "UNKNOWN_BOARD_GAP" for row in first_t2),
            "quality_known": known_q, "quality_unknown": len(first_t2) - known_q,
            "quality_coverage_fraction": known_q / len(first_t2) if first_t2 else None,
            "q_true": sum(row["q"] == "TRUE" for row in first_t2),
            "q_false": sum(row["q"] == "FALSE" for row in first_t2),
            "eligible_q_true": eligible_treated, "eligible_q_false": eligible_controls,
            "frozen_pairs": len(pairs), "matched_q_true": len(pairs),
            "primary_matched_support_fraction": len(pairs) / eligible_treated if eligible_treated else None,
            "repeated_t2_excluded": len(repeats),
            "matching_exclusion_reasons": dict(sorted(exclusion_counts.items())),
        },
    }
    return {"schema": SCHEMA, "manifest": manifest,
            "manifest_sha256": _digest(manifest), "corrections": []}


_CORRECTION_FIELDS = frozenset({
    "correction_id", "target_observation_id", "original_claim_id", "reason",
    "correction_type", "available_at", "observed_at", "corrected_receipt_sha256",
})


def _correction(value: Any, manifest: Mapping[str, Any]) -> dict:
    value = _fields(value, _CORRECTION_FIELDS, "correction")
    result = deepcopy(dict(value))
    for key in ("correction_id", "target_observation_id", "original_claim_id", "reason"):
        _text(value[key], f"correction.{key}")
    if value["correction_type"] not in ("SOURCE_REVISION", "DATA_INTEGRITY_EXCEPTION"):
        raise CohortInputError("unsupported correction_type")
    _sha(value["corrected_receipt_sha256"], "correction.corrected_receipt_sha256")
    rows = {row["observation_id"]: row for row in manifest["first_t2"]}
    if value["target_observation_id"] not in rows:
        raise CohortInputError("correction target is not an original first-T2 observation")
    available = _instant(value["available_at"], "correction.available_at")
    observed = _instant(value["observed_at"], "correction.observed_at")
    original_cut = _instant(rows[value["target_observation_id"]]["decision_cut"], "original cut")
    if observed < available or observed <= original_cut:
        raise CohortInputError("appended correction must be observed after the original cut and availability")
    result.update({"available_at": _utc(available), "observed_at": _utc(observed)})
    return result


def verify_manifest(envelope: Mapping[str, Any]) -> bool:
    """Check content and correction-chain integrity; never attest provenance."""
    try:
        envelope = _fields(envelope, {"schema", "manifest", "manifest_sha256", "corrections"}, "envelope")
        if envelope["schema"] != SCHEMA or _digest(envelope["manifest"]) != envelope["manifest_sha256"]:
            return False
        manifest = _mapping(envelope["manifest"], "manifest")
        if (manifest["operation_key"] != OPERATION_KEY or manifest["research_only"] is not True
                or manifest["enrollment_status"] != "NOT_ENROLLED"
                or set(manifest["authority_flags"]) != set(AUTHORITY_FLAGS)
                or any(value is not False for value in manifest["authority_flags"].values())):
            return False
        if not isinstance(envelope["corrections"], list):
            return False
        previous, seen_ids, last_observed = None, set(), None
        for entry in envelope["corrections"]:
            entry = _fields(entry, {
                "correction", "original_manifest_sha256", "previous_correction_sha256", "correction_sha256",
            }, "correction entry")
            body = {key: value for key, value in entry.items() if key != "correction_sha256"}
            if (entry["original_manifest_sha256"] != envelope["manifest_sha256"]
                    or entry["previous_correction_sha256"] != previous
                    or _digest(body) != entry["correction_sha256"]):
                return False
            correction = _correction(entry["correction"], manifest)
            observed = _instant(correction["observed_at"], "correction observed_at")
            if correction["correction_id"] in seen_ids or (last_observed and observed < last_observed):
                return False
            seen_ids.add(correction["correction_id"])
            previous, last_observed = entry["correction_sha256"], observed
        return True
    except (CohortInputError, KeyError, TypeError, AttributeError):
        return False


def rematch_omission(envelope: Mapping[str, Any], omitted_issuer_ids: list[str] | tuple[str, ...]) -> dict:
    """Remove issuers from BOTH original eligible pools and rematch exactly.

    This derives the preregistered leave-one-issuer/leave-INTC-out sensitivity.
    It uses all originally eligible first-T2 records, including unmatched names;
    filtering the original pairs would produce a different and incorrect pool.
    No labels, cut clocks, frozen mappings or first-observation identities are
    reclassified.  Later observations and appended corrections cannot replace
    an original first record.  The original envelope is not modified.

    Omitted IDs must be distinct canonical issuers in the original eligible
    pool.  An empty list is an explicit no-op, useful when INTC is absent.  The
    derived receipt references original records by observation ID and binds
    their complete bytes through the parent and eligible-pool hashes.
    """
    if not verify_manifest(envelope):
        raise CohortInputError("cannot rematch a malformed or modified original manifest")
    if not isinstance(omitted_issuer_ids, (list, tuple)):
        raise CohortInputError("omitted_issuer_ids must be an explicit list or tuple")
    omitted = [_identifier(value, "omitted_issuer_id") for value in omitted_issuer_ids]
    if len(omitted) != len(set(omitted)):
        raise CohortInputError("duplicate omitted issuer IDs are not permitted")
    manifest = envelope["manifest"]
    original_pool = [row for row in manifest["first_t2"] if row["matching_eligible"]]
    eligible_ids = {row["canonical_issuer_id"] for row in original_pool}
    if set(omitted) - eligible_ids:
        raise CohortInputError("omitted issuer is outside the original eligible pool")
    omitted_set = set(omitted)
    retained = deepcopy([row for row in original_pool if row["canonical_issuer_id"] not in omitted_set])
    pairs, unmatched = _match(retained, manifest["operation_key"], manifest["cohort_id"])
    receipt = {
        "schema": "pb_d_cohort_omission.v1", "operation_key": manifest["operation_key"],
        "cohort_id": manifest["cohort_id"], "research_only": True,
        "enrollment_status": "NOT_ENROLLED", "authority_flags": dict(AUTHORITY_FLAGS),
        "provenance_scope": "derived_from_original_supplied_owner_receipts_only",
        "parent_manifest_sha256": envelope["manifest_sha256"],
        "parent_corrections_sha256": _digest(envelope["corrections"]),
        "original_eligible_pool_sha256": _digest(original_pool),
        "omitted_issuer_ids": sorted(omitted),
        "retained_observation_ids": [row["observation_id"] for row in retained],
        "first_cut_date": manifest["first_cut_date"], "through_cut_date": manifest["through_cut_date"],
        "versions": deepcopy(manifest["versions"]),
        "eligible_q1_count": sum(row["q"] == "TRUE" for row in retained),
        "eligible_q0_count": sum(row["q"] == "FALSE" for row in retained),
        "pairs": pairs, "unmatched": unmatched,
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def append_correction(envelope: Mapping[str, Any], correction: Mapping[str, Any]) -> dict:
    """Append source/integrity provenance without rewriting primary labels/pairs.

    DATA_INTEGRITY_EXCEPTION is evidence for a separately reported quarantine
    sensitivity.  It does not erase the original pair or rematch its survivors.
    """
    if not verify_manifest(envelope):
        raise CohortInputError("cannot append to a malformed or modified original manifest")
    correction = _correction(correction, envelope["manifest"])
    entries = envelope["corrections"]
    if any(entry["correction"]["correction_id"] == correction["correction_id"] for entry in entries):
        raise CohortInputError("correction_id already exists; do not replace or replay it")
    if entries and (_instant(correction["observed_at"], "correction observed_at")
                    < _instant(entries[-1]["correction"]["observed_at"], "last correction observed_at")):
        raise CohortInputError("corrections must append in observed-time order")
    body = {"correction": correction, "original_manifest_sha256": envelope["manifest_sha256"],
            "previous_correction_sha256": entries[-1]["correction_sha256"] if entries else None}
    result = deepcopy(dict(envelope))
    result["corrections"].append({**body, "correction_sha256": _digest(body)})
    return result
