#!/usr/bin/env python3
"""Research-only coupled source, calendar, observation and append contracts.

The synthetic JSON codec is a deterministic test adapter, not a production
data source or store. The production resolver remains with existing owners.
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import math
import numbers
import re
from zoneinfo import ZoneInfo

CHINA = ZoneInfo("Asia/Shanghai")
ANCHORS = ("session_open", "session_close")
HEX64 = re.compile(r"[0-9a-f]{64}")
TICKER = re.compile(r"[0-9]{6}\.(SS|SZ|BJ)")


class EvidenceError(ValueError):
    """Unavailable or inconsistent evidence: no admitted mark or ledger write."""


def canonical_bytes(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise EvidenceError("NONCANONICAL_JSON") from exc


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def text(value, reason):
    if not isinstance(value, str) or not value or value.strip() != value:
        raise EvidenceError(reason)
    return value


def identity(value, reason="SOURCE_IDENTITY_UNAVAILABLE"):
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise EvidenceError(reason)
    return value


def ticker_id(value):
    if not isinstance(value, str) or TICKER.fullmatch(value) is None:
        raise EvidenceError("TICKER_INVALID")
    return value


def session_date(value):
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        raise EvidenceError("SESSION_INVALID")
    try:
        result = dt.date.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceError("SESSION_INVALID") from exc
    if result.isoformat() != value:
        raise EvidenceError("SESSION_INVALID")
    return result


def clock(value):
    if not isinstance(value, str):
        raise EvidenceError("CLOCK_UNAVAILABLE")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("CLOCK_INVALID") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise EvidenceError("CLOCK_TIMEZONE_MISSING")
    return result.astimezone(dt.timezone.utc)


def finite_positive(value, reason="PRICE_INVALID"):
    if isinstance(value, bool) or not isinstance(value, numbers.Real):
        raise EvidenceError(reason)
    try:
        result = float(value)
    except (OverflowError, TypeError, ValueError) as exc:
        raise EvidenceError(reason) from exc
    if not math.isfinite(result) or result <= 0:
        raise EvidenceError(reason)
    return result


def opening_refusal(bar):
    """Shared by retention and mark construction; never modifies observation."""
    if not isinstance(bar, dict):
        return "BAR_INVALID"
    op = bar.get("open")
    if op is None or isinstance(op, float) and math.isnan(op):
        return "OPEN_UNAVAILABLE"
    try:
        op = finite_positive(op, "OPEN_INVALID")
    except EvidenceError as exc:
        return str(exc)
    hi, lo = bar.get("high"), bar.get("low")
    if hi is None or lo is None:
        return "OPEN_RANGE_UNVERIFIED"
    if any(isinstance(v, float) and math.isnan(v) for v in (hi, lo)):
        return "OPEN_RANGE_UNVERIFIED"
    try:
        hi = finite_positive(hi, "RANGE_INVALID")
        lo = finite_positive(lo, "RANGE_INVALID")
    except EvidenceError as exc:
        return str(exc)
    if hi < lo:
        return "RANGE_INVALID"
    dust = max(abs(op), abs(hi), abs(lo), 1.0) * 1e-6
    if op < lo - dust or op > hi + dust:
        return "OPEN_OUTSIDE_RANGE"
    return None


def anchor_price(bar, anchor):
    if not isinstance(bar, dict):
        raise EvidenceError("BAR_INVALID")
    if anchor == "hl2_proxy":
        raise EvidenceError("HL2_EXACT_TIME_UNAVAILABLE")
    if anchor not in ANCHORS:
        raise EvidenceError("UNKNOWN_ANCHOR")
    field = "open" if anchor == "session_open" else "close"
    if anchor == "session_open":
        refused = opening_refusal(bar)
        if refused:
            raise EvidenceError(refused)
    if bar.get(field) is None:
        raise EvidenceError("PRICE_FIELD_UNAVAILABLE:" + field)
    return finite_positive(bar[field])


class CalendarFixture:
    """Validates structure and date binding, not exchange holiday truth."""

    def __init__(self, sessions):
        if not isinstance(sessions, dict) or not sessions:
            raise EvidenceError("CALENDAR_UNAVAILABLE")
        parsed = {}
        for session, anchors in sessions.items():
            day = session_date(session)
            if not isinstance(anchors, dict) or set(anchors) != set(ANCHORS):
                raise EvidenceError("CALENDAR_ANCHORS_INVALID")
            converted = {anchor: clock(anchors[anchor]) for anchor in ANCHORS}
            if any(t.astimezone(CHINA).date() != day for t in converted.values()):
                raise EvidenceError("CALENDAR_SESSION_CLOCK_MISMATCH")
            if converted["session_open"] >= converted["session_close"]:
                raise EvidenceError("CALENDAR_ANCHOR_ORDER_INVALID")
            parsed[session] = converted
        self._sessions = parsed
        self.calendar_id = digest({s: {a: t.isoformat() for a, t in v.items()}
                                   for s, v in parsed.items()})

    def resolve(self, session, anchor):
        session_date(session)
        if anchor not in ANCHORS:
            raise EvidenceError("UNKNOWN_ANCHOR")
        if session not in self._sessions:
            raise EvidenceError("SESSION_NOT_IN_CALENDAR")
        return self._sessions[session][anchor]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("SOURCE_DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _bad_constant(value):
    raise EvidenceError("SOURCE_NONFINITE_JSON")


def resolve_row(source_sha256, ticker, session, *, resolve_source, calendar):
    """Hash actual bytes, then resolve exact row and owned declared metadata.

    Real implementation must substitute the existing immutable Parquet owner
    plus genuine producer/basis receipts for this explicit test codec.
    """
    identity(source_sha256)
    ticker_id(ticker)
    session_date(session)
    try:
        blob = resolve_source(source_sha256)
    except (KeyError, FileNotFoundError) as exc:
        raise EvidenceError("SOURCE_BYTES_UNAVAILABLE") from exc
    if not isinstance(blob, bytes):
        raise EvidenceError("SOURCE_BYTES_UNAVAILABLE")
    if hashlib.sha256(blob).hexdigest() != source_sha256:
        raise EvidenceError("SOURCE_BYTES_HASH_MISMATCH")
    try:
        source = json.loads(blob, object_pairs_hook=_unique_object,
                            parse_constant=_bad_constant)
    except (UnicodeDecodeError, ValueError, TypeError, OverflowError, RecursionError) as exc:
        if isinstance(exc, EvidenceError):
            raise
        raise EvidenceError("SOURCE_CODEC_INVALID") from exc
    if not isinstance(source, dict) or source.get("schema") != "research.price_fixture.v2" or source.get("fixture_only") is not True:
        raise EvidenceError("RESEARCH_CODEC_REQUIRED")
    if ticker_id(source.get("ticker")) != ticker:
        raise EvidenceError("SOURCE_INSTRUMENT_MISMATCH")
    basis = text(source.get("basis_id"), "PRICE_BASIS_UNAVAILABLE")
    provider = text(source.get("provider_id"), "SOURCE_PROVIDER_UNAVAILABLE")
    adjustment = source.get("price_adjustment")
    if adjustment not in ("unadjusted", "vendor_adjusted_price"):
        raise EvidenceError("PRICE_ADJUSTMENT_UNAVAILABLE")
    if source.get("clock_kind") != "producer_available_at":
        raise EvidenceError("SOURCE_AVAILABILITY_UNVERIFIED")
    available = clock(source.get("available_at"))
    rows = source.get("rows")
    if not isinstance(rows, list) or not rows:
        raise EvidenceError("SOURCE_ROWS_UNAVAILABLE")
    by_session = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"session", "bar"} or not isinstance(row["bar"], dict):
            raise EvidenceError("SOURCE_ROW_INVALID")
        session_date(row["session"])
        if row["session"] in by_session:
            raise EvidenceError("SOURCE_DUPLICATE_SESSION")
        # The availability clock belongs to the complete immutable blob. An
        # earlier selected row cannot launder a later finalized row in it.
        if available < calendar.resolve(row["session"], "session_close"):
            raise EvidenceError("SOURCE_PRECEDES_FINALIZED_BAR")
        by_session[row["session"]] = row
    if session not in by_session:
        raise EvidenceError("SOURCE_ROW_UNAVAILABLE")
    row = by_session[session]
    return copy.deepcopy(row), {
        "sha256": source_sha256, "codec": source["schema"],
        "provider_id": provider, "clock_kind": source["clock_kind"],
        "available_at": available.isoformat(), "basis_id": basis,
        "price_adjustment": adjustment,
    }


def mark_from_source(*, ticker, session, anchor, source_sha256, resolve_source,
                     calendar, supplied_bar=None):
    if anchor == "hl2_proxy":
        raise EvidenceError("HL2_EXACT_TIME_UNAVAILABLE")
    if anchor not in ANCHORS:
        raise EvidenceError("UNKNOWN_ANCHOR")
    anchor_at = calendar.resolve(session, anchor)
    row, source = resolve_row(source_sha256, ticker, session,
                              resolve_source=resolve_source, calendar=calendar)
    if supplied_bar is not None and canonical_bytes(supplied_bar) != canonical_bytes(row["bar"]):
        raise EvidenceError("SUPPLIED_BAR_SOURCE_MISMATCH")
    price = anchor_price(row["bar"], anchor)
    return {
        "ticker": ticker, "session": session, "anchor": anchor,
        "anchor_at": anchor_at.isoformat(), "calendar_id": calendar.calendar_id,
        "price": price, "basis_id": source["basis_id"], "source": source,
        "bar_row_sha256": digest({"ticker": ticker, **row}),
        "execution_status": "MARK_ONLY",
    }


def validate_mark(mark, asof, *, resolve_source, calendar):
    if not isinstance(mark, dict):
        raise EvidenceError("MARK_INVALID")
    if mark.get("execution_status") != "MARK_ONLY":
        raise EvidenceError("EXECUTION_RECEIPT_NOT_IMPLEMENTED")
    source = mark.get("source")
    if not isinstance(source, dict):
        raise EvidenceError("SOURCE_IDENTITY_UNAVAILABLE")
    expected = mark_from_source(ticker=mark.get("ticker"), session=mark.get("session"),
                                anchor=mark.get("anchor"), source_sha256=source.get("sha256"),
                                resolve_source=resolve_source, calendar=calendar)
    if canonical_bytes(mark) != canonical_bytes(expected):
        raise EvidenceError("MARK_SOURCE_BINDING_MISMATCH")
    asof_clock = clock(asof)
    if clock(expected["anchor_at"]) > asof_clock:
        raise EvidenceError("FUTURE_ANCHOR_AT_GRADING")
    if clock(expected["source"]["available_at"]) > asof_clock:
        raise EvidenceError("FUTURE_SOURCE_AT_GRADING")
    return expected


def aligned_excess(stock_entry, stock_exit, benchmark_entry, benchmark_exit, *,
                   published_at, graded_at, resolve_source, calendar, entry_anchor_at=None):
    """Matched observed marks; no execution or total-return certification."""
    if published_at is None:
        raise EvidenceError("PUBLICATION_CLOCK_UNVERIFIED")
    marks = [validate_mark(m, graded_at, resolve_source=resolve_source, calendar=calendar)
             for m in (stock_entry, stock_exit, benchmark_entry, benchmark_exit)]
    se, sx, be, bx = marks
    if (se["session"], se["anchor"], se["anchor_at"]) != (be["session"], be["anchor"], be["anchor_at"]):
        raise EvidenceError("ENTRY_ANCHOR_MISMATCH")
    if (sx["session"], sx["anchor"], sx["anchor_at"]) != (bx["session"], bx["anchor"], bx["anchor_at"]):
        raise EvidenceError("EXIT_ANCHOR_MISMATCH")
    if session_date(se["session"]) >= session_date(sx["session"]):
        raise EvidenceError("NONPOSITIVE_SESSION_WINDOW")
    actual_entry = clock(se["anchor_at"])
    if entry_anchor_at is not None and clock(entry_anchor_at) != actual_entry:
        raise EvidenceError("ENTRY_CLOCK_BINDING_MISMATCH")
    if clock(published_at) > actual_entry:
        raise EvidenceError("PUBLICATION_AFTER_ENTRY_ANCHOR")
    for entry, leave in ((se, sx), (be, bx)):
        if entry["ticker"] != leave["ticker"]:
            raise EvidenceError("INSTRUMENT_MISMATCH")
        if entry["basis_id"] != leave["basis_id"]:
            raise EvidenceError("BASIS_ID_MISMATCH")
        if entry["source"]["sha256"] != leave["source"]["sha256"]:
            raise EvidenceError("WITHIN_INSTRUMENT_VINTAGE_MISMATCH")
    stock_return = (sx["price"] / se["price"] - 1.0) * 100.0
    benchmark_return = (bx["price"] / be["price"] - 1.0) * 100.0
    excess = stock_return - benchmark_return
    if not all(math.isfinite(x) for x in (stock_return, benchmark_return, excess)):
        raise EvidenceError("RETURN_ARITHMETIC_NONFINITE")
    return {
        "status": "ALIGNED_MARK_DIAGNOSTIC", "stock_return_pct": stock_return,
        "benchmark_return_pct": benchmark_return, "excess_pp": excess,
        "execution_status": "MARK_ONLY", "entry_anchor_at": se["anchor_at"],
        "exit_anchor_at": sx["anchor_at"], "calendar_id": calendar.calendar_id,
        "accounting": "Declared consistent price basis per instrument; total return, original decision knowability, costs and actual execution need separate evidence.",
    }


def legacy_snapshot(row):
    if not isinstance(row, dict):
        raise EvidenceError("LEGACY_ROW_INVALID")
    fields = ("date", "ticker", "entry", "basis_used", "t1_date", "corrupt_bar", "latched_asof")
    original = {key: copy.deepcopy(row.get(key)) for key in fields}
    return {"legacy_row_id": digest(original), "original": original,
            "qualification": "LEGACY_SOURCE_VINTAGE_UNVERIFIED"}


def seal_event(event):
    if not isinstance(event, dict):
        raise EvidenceError("EVENT_INVALID")
    if "event_id" in event:
        raise EvidenceError("EVENT_ALREADY_SEALED")
    result = copy.deepcopy(event)
    result["event_id"] = digest(event)
    return result


def _event(event):
    if not isinstance(event, dict):
        raise EvidenceError("EVENT_INVALID")
    base = {"event_id", "kind", "decision_id", "ticker", "entry_session", "price", "basis", "recorded_at"}
    kind = event.get("kind")
    extra = set() if kind == "original_entry" else {"correction_of", "reason"}
    if kind not in ("original_entry", "entry_correction"):
        raise EvidenceError("EVENT_KIND_UNSUPPORTED")
    if set(event) != base | extra:
        raise EvidenceError("EVENT_SCHEMA_INVALID")
    identity(event["event_id"], "EVENT_HASH_MISMATCH")
    if event["event_id"] != digest({k: v for k, v in event.items() if k != "event_id"}):
        raise EvidenceError("EVENT_HASH_MISMATCH")
    decision = text(event["decision_id"], "DECISION_LINK_UNAVAILABLE")
    ticker = ticker_id(event["ticker"])
    day = session_date(event["entry_session"])
    finite_positive(event["price"])
    text(event["basis"], "PRICE_BASIS_UNAVAILABLE")
    recorded = clock(event["recorded_at"])
    if recorded.astimezone(CHINA).date() < day:
        raise EvidenceError("EVENT_RECORDED_BEFORE_ENTRY_SESSION")
    if kind == "entry_correction":
        identity(event["correction_of"], "CORRECTION_TARGET_UNAVAILABLE")
        text(event["reason"], "CORRECTION_REASON_UNAVAILABLE")
    return (decision, ticker)


def _validate_ledger(ledger):
    if not isinstance(ledger, list):
        raise EvidenceError("LEDGER_INVALID")
    by_id, originals = {}, {}
    for row in ledger:
        key = _event(row)
        event_id = row["event_id"]
        if event_id in by_id:
            raise EvidenceError("LEDGER_DUPLICATE_EVENT_ID")
        if row["kind"] == "original_entry":
            if key in originals:
                raise EvidenceError("ORIGINAL_ENTRY_IMMUTABLE")
            originals[key] = row
        else:
            original = by_id.get(row["correction_of"])
            if original is None or original["kind"] != "original_entry":
                raise EvidenceError("CORRECTION_TARGET_UNAVAILABLE")
            if (original["decision_id"], original["ticker"]) != key or original["entry_session"] != row["entry_session"]:
                raise EvidenceError("CORRECTION_IDENTITY_MISMATCH")
            if clock(row["recorded_at"]) <= clock(original["recorded_at"]):
                raise EvidenceError("CORRECTION_NOT_AFTER_ORIGINAL")
        by_id[event_id] = row
    return by_id


def append_event(ledger, event):
    """Validate entire incumbent history before any idempotence fast path."""
    by_id = _validate_ledger(ledger)
    _event(event)
    if event["event_id"] in by_id:
        # Hash equality is not accepted without complete canonical body equality.
        if canonical_bytes(by_id[event["event_id"]]) != canonical_bytes(event):
            raise EvidenceError("EVENT_HASH_MISMATCH")
        return copy.deepcopy(ledger)
    proposed = [*copy.deepcopy(ledger), copy.deepcopy(event)]
    _validate_ledger(proposed)
    return proposed
