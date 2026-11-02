# engine/liquidity_currency.py
"""Dated trading-currency observation validator (evidence-only).

``qualify_currency`` qualifies a bounded provider-evidence receipt proving that
one ticker has matching USD source observations for exactly 20 dated sessions.

This module validates evidence only. The native liquidity formula, its
authority, and the actual trading calendar belong to the caller: sessions are
supplied by the parent and are never recomputed, extended, or normalized here.

The dated reference is retrospective: it is observed NOW from archived
request/response pairs. Provider-body metadata (filing dates, SLA hints and
similar) is never interpreted as a publication time, ``known_at`` is always
None, and no continuous validity interval is invented.

Any input that does not satisfy the bounded schema returns None. This module
never raises on hostile input and uses the Python standard library only.
"""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

INPUT_SCHEMA = "liquidity_currency_observations.v1"
OUTPUT_SCHEMA = "liquidity_currency_dated.v1"
SESSION_COUNT = 20
HTTP_OK = 200
MAX_BODY_BYTES = 131072
MAX_RECEIPT_BYTES = 3 * 1024 * 1024
TICKER_MAX_LENGTH = 32

_EVIDENCE_KEYS = frozenset({"schema", "ticker", "observations"})
_OBSERVATION_KEYS = frozenset(
    {
        "session",
        "request_path",
        "request_params",
        "request_started_at",
        "response_received_at",
        "http_status",
        "response_sha256",
        "response_body",
    }
)
_HEX_DIGITS = frozenset("0123456789abcdef")
_ZERO_OFFSET = timedelta(0)


def qualify_currency(evidence, *, ticker, sessions, recorded_at):
    """Return the dated-currency qualification dict, or None if unqualified.

    ``sessions`` is the parent-supplied actual calendar: exactly 20 distinct
    ascending ``datetime.date`` days. ``recorded_at`` is an aware datetime
    marking the observation cutoff. No input shape raises; every deviation
    from the bounded schema yields None.
    """
    try:
        return _qualify(evidence, ticker, sessions, recorded_at)
    except Exception:
        return None


def _qualify(evidence, ticker, sessions, recorded_at):
    if not isinstance(evidence, dict) or set(evidence) != _EVIDENCE_KEYS:
        return None
    if evidence["schema"] != INPUT_SCHEMA:
        return None
    if not _ticker_ok(ticker) or evidence["ticker"] != ticker:
        return None
    if not _recorded_at_ok(recorded_at):
        return None
    checked_sessions = _sessions_ok(sessions)
    if checked_sessions is None:
        return None

    observations = evidence["observations"]
    if not isinstance(observations, list) or len(observations) != SESSION_COUNT:
        return None

    started_at = []
    received_at = []
    for session, observation in zip(checked_sessions, observations):
        clocks = _observation_ok(observation, ticker, session, recorded_at)
        if clocks is None:
            return None
        started_at.append(clocks[0])
        received_at.append(clocks[1])

    try:
        receipt = json.dumps(
            evidence,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError):
        return None
    if len(receipt) > MAX_RECEIPT_BYTES:
        return None

    return {
        "schema": OUTPUT_SCHEMA,
        "ticker": ticker,
        "currency": "USD",
        "source_sha256": hashlib.sha256(receipt).hexdigest(),
        "source_asof": checked_sessions[-1].isoformat(),
        "dated_sessions": [day.isoformat() for day in checked_sessions],
        "observation_started_at": _utc_iso(min(started_at)),
        "observation_completed_at": _utc_iso(max(received_at)),
        "known_at": None,
        "published_at": None,
        "basis": "retrospective_dated_reference",
    }


def _ticker_ok(ticker):
    if not isinstance(ticker, str) or not ticker or len(ticker) > TICKER_MAX_LENGTH:
        return False
    return not any(char.isspace() or ord(char) < 33 for char in ticker)


def _recorded_at_ok(recorded_at):
    if not isinstance(recorded_at, datetime):
        return False
    if recorded_at.tzinfo is None or recorded_at.utcoffset() is None:
        return False
    return True


def _sessions_ok(sessions):
    if not isinstance(sessions, (list, tuple)) or len(sessions) != SESSION_COUNT:
        return None
    for day in sessions:
        # ``type(...) is date`` rejects datetime instances, str, int and bool.
        if type(day) is not date:
            return None
    for earlier, later in zip(sessions, sessions[1:]):
        if not earlier < later:
            return None
    return list(sessions)


def _observation_ok(observation, ticker, session, recorded_at):
    if not isinstance(observation, dict) or set(observation) != _OBSERVATION_KEYS:
        return None

    session_iso = session.isoformat()
    if observation["session"] != session_iso:
        return None
    if observation["request_path"] != "/v3/reference/tickers/" + ticker:
        return None

    params = observation["request_params"]
    if not isinstance(params, dict) or set(params) != {"date"}:
        return None
    if params["date"] != session_iso:
        return None

    status = observation["http_status"]
    if type(status) is not int or status != HTTP_OK:
        return None

    digest = observation["response_sha256"]
    if not isinstance(digest, str) or len(digest) != 64:
        return None
    if any(char not in _HEX_DIGITS for char in digest):
        return None

    body = observation["response_body"]
    if not isinstance(body, str):
        return None
    try:
        encoded_body = body.encode("utf-8")
    except (UnicodeEncodeError, LookupError):
        return None
    if len(encoded_body) > MAX_BODY_BYTES:
        return None
    if hashlib.sha256(encoded_body).hexdigest() != digest:
        return None

    started = _parse_utc(observation["request_started_at"])
    received = _parse_utc(observation["response_received_at"])
    if started is None or received is None:
        return None
    if not started <= received <= recorded_at:
        return None
    # A dated reference may not be requested after the request itself ran.
    if session > started.date():
        return None

    if not _body_ok(body, ticker):
        return None
    return started, received


def _body_ok(body, ticker):
    def strict_object(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError("duplicate provider JSON key")
            obj[key] = value
        return obj

    def reject_constant(value):
        raise ValueError("non-finite provider JSON constant")

    try:
        payload = json.loads(body, object_pairs_hook=strict_object,
                             parse_constant=reject_constant)
    except ValueError:
        return False
    if not isinstance(payload, dict):
        return False
    if payload.get("status") != "OK":
        return False
    results = payload.get("results")
    if not isinstance(results, dict):
        return False
    if results.get("ticker") != ticker:
        return False
    currency = results.get("currency_name")
    if not isinstance(currency, str) or currency.lower() != "usd":
        return False
    return True


def _parse_utc(text):
    """Parse an aware ISO timestamp and normalize to UTC; never guess a zone."""
    if not isinstance(text, str) or len(text) < 20 or text[10] != "T":
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    if moment.tzinfo is None or moment.utcoffset() is None:
        return None
    return moment.astimezone(timezone.utc)


def _utc_iso(moment):
    rendered = moment.isoformat()
    return rendered[:-6] + "Z" if rendered.endswith("+00:00") else rendered
