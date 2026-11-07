"""Liquidity profile — guarded producer adapter over the native W5b chip.

Wraps ``engine.liquidity_chip.compute`` (20-session median dollar ADV, tier,
days-to-build) in the ``liquidity_profile.v1`` display payload.  Pure function:
no I/O, no writes, no network, no collectors — one DataFrame in, one dict out.

Authority: DISPLAY ONLY / decision_support_only.  The payload is not order-book
depth, not a liquidity forecast, and carries no rank / gate / sizing / trading
power.  Metrics are the EXACT native compute dict on a raw-close x raw-share-
volume basis over the full 20-session window ending at ``expected_session``;
``thinly_traded`` is True only for the native ``thin``/``illiquid`` tiers.

Refusal taxonomy — a payload is always returned, metrics stay null:
  READ_NO_COVERAGE  — frame absent/empty, fewer than WINDOW sessions, window
                      sessions missing, stale (frame ends before the expected
                      session), zero dollar-ADV, or unqualified currency
                      evidence (CURRENCY_NOT_QUALIFIED).
  READ_UNAVAILABLE  — malformed inputs: bad clocks, bad frame/index shape,
                      future rows, invalid close/volume values, missing or
                      invalid source sha256, invalid ingested_at.

Unknown values are ALWAYS null — never zero, never USD, never an invented
timezone, known_at, publication or validity time.  No portfolio, holdings or
user fields exist on the payload.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from engine.liquidity_chip import WINDOW, compute
from engine.liquidity_currency import qualify_currency
from lib.nyse_calendar import expected_last_session, is_session

# --------------------------------------------------------------------------- #
#  Fixed payload vocabulary (schema liquidity_profile.v1)                     #
# --------------------------------------------------------------------------- #
SCHEMA: str = "liquidity_profile.v1"
PRODUCER_OWNER: str = "engine.liquidity_chip"
PRODUCER_VERSION: int = 1
BASIS: str = "raw_close_times_raw_share_volume"
SAMPLE_SELECTION: str = "full_window"
RIGHTS_EVIDENCE: str = "research/licenses/MASSIVE_ENTITLEMENT_RECORD.md"

STATUS_OK: str = "READ_OK"
STATUS_NO_COVERAGE: str = "READ_NO_COVERAGE"
STATUS_UNAVAILABLE: str = "READ_UNAVAILABLE"

QUALIFIED_CURRENCY: str = "USD"
THIN_TIERS: tuple[str, ...] = ("thin", "illiquid")
CURRENCY_FIELDS: tuple[str, ...] = (
    "ticker", "currency", "source_sha256", "source_asof", "valid_from", "valid_through",
)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_NY_TZ = ZoneInfo("America/New_York")


# --------------------------------------------------------------------------- #
#  Small pure helpers                                                         #
# --------------------------------------------------------------------------- #
def _is_sha256(value: object) -> bool:
    """True for a 64-character hex digest string."""
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _parse_iso_date(value: object) -> "date | None":
    """Strict YYYY-MM-DD ISO date, else None."""
    if not isinstance(value, str) or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_iso_datetime(value: object) -> "datetime | None":
    """Parse an ISO-8601 datetime string; the result may still be naive."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _is_aware(moment: datetime) -> bool:
    return moment.tzinfo is not None and moment.utcoffset() is not None


def _utc_iso(moment: datetime) -> str:
    """Render an instant as ISO-8601 UTC with a Z suffix."""
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _frame_meta(frame: object) -> "tuple[int, str | None]":
    """Best-effort (row_count, last-row ISO date) that can never raise."""
    if not isinstance(frame, pd.DataFrame):
        return 0, None
    index = frame.index
    if len(index) == 0:
        return 0, None
    asof = index[-1].date().isoformat() if isinstance(index[-1], pd.Timestamp) else None
    return int(len(index)), asof


def _expected_sessions(end_date: date, count: int) -> "list[date] | None":
    """The *count* NYSE sessions ending at *end_date* (inclusive), oldest first.

    ``end_date`` itself must be a session (the caller checks).  Bounded walk:
    returns None when the calendar yields no such window (never expected).
    """
    sessions: list[date] = []
    day = end_date
    for _ in range(count * 4 + 40):
        if is_session(day):
            sessions.append(day)
            if len(sessions) == count:
                sessions.reverse()
                return sessions
        day -= timedelta(days=1)
    return None


def _as_finite_number(value: object) -> "float | None":
    """Finite Python float from a real number; None for bool/str/NaN/inf/other."""
    if isinstance(value, (bool, np.bool_)):
        return None
    if isinstance(value, (str, bytes, bytearray)):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _qualified_currency(
    evidence: object, ticker: str, recorded_date: date, window_start: date, window_end: date
) -> "dict | None":
    """Whitelisted currency block when the evidence qualifies, else None.

    The evidence must be a dict naming currency USD, a 64-hex source digest and
    ISO dates whose validity bounds cover the entire selected window and whose
    source_asof is not after the recorded date.  A current reference is never
    stretched to cover historical sessions.
    """
    if not isinstance(evidence, dict):
        return None
    if evidence.get("ticker") != ticker:
        return None
    if evidence.get("currency") != QUALIFIED_CURRENCY:
        return None
    if not _is_sha256(evidence.get("source_sha256")):
        return None
    source_asof = _parse_iso_date(evidence.get("source_asof"))
    valid_from = _parse_iso_date(evidence.get("valid_from"))
    valid_through = _parse_iso_date(evidence.get("valid_through"))
    if source_asof is None or valid_from is None or valid_through is None:
        return None
    if source_asof > recorded_date:
        return None
    if valid_from > window_start or valid_through < window_end:
        return None
    return {field: evidence[field] for field in CURRENCY_FIELDS}


# --------------------------------------------------------------------------- #
#  Guarded producer adapter                                                   #
# --------------------------------------------------------------------------- #
def project(
    frame: "pd.DataFrame | None",
    *,
    ticker: str,
    expected_session: date,
    recorded_at: datetime,
    ingested_at: "str | None",
    source_sha256: "str | None",
    currency_evidence: "dict | None",
) -> dict:
    """Build the ``liquidity_profile.v1`` display payload for one ticker.

    Returns a payload dict for every input: ``status == READ_OK`` with the exact
    native compute dict, or a typed refusal (READ_NO_COVERAGE /
    READ_UNAVAILABLE) with a reason string and null metrics.
    """
    observed_sessions, frame_asof = _frame_meta(frame)

    payload: dict = {
        "schema": SCHEMA,
        "ticker": ticker if isinstance(ticker, str) else repr(ticker),
        "producer": {
            "owner": PRODUCER_OWNER,
            "version": PRODUCER_VERSION,
            "engine": PRODUCER_OWNER + ".compute",
        },
        "authority": {
            "display_only": True,
            "decision_support_only": True,
            "rank": False,
            "gate": False,
            "sizing": False,
            "trading": False,
        },
        "basis": BASIS,
        "window_sessions": WINDOW,
        "sample_selection": SAMPLE_SELECTION,
        "scope": {"order_book_depth": False, "forecast": False},
        "status": STATUS_OK,
        "reason": None,
        "metrics": None,
        "sample_n": None,
        "thinly_traded": None,
        "coverage": {
            "expected_sessions": WINDOW,
            "observed_sessions": None,
            "source_rows": observed_sessions,
        },
        "recorded_at": None,
        "expected_session": (
            expected_session.isoformat()
            if isinstance(expected_session, date) and not isinstance(expected_session, datetime)
            else None
        ),
        "source_asof": frame_asof,
        "ingested_at": None,
        "published_at": None,
        "known_at": None,
        "source_sha256": source_sha256 if _is_sha256(source_sha256) else None,
        "currency": None,
        "rights_evidence": RIGHTS_EVIDENCE,
    }

    def refuse(status: str, reason: str) -> dict:
        payload["status"] = status
        payload["reason"] = reason
        return payload

    # -- gate 1: recorded_at clock (UTC-aware required) ----------------------- #
    if isinstance(recorded_at, datetime):
        recorded_raw = recorded_at
    elif isinstance(recorded_at, str):
        recorded_raw = _parse_iso_datetime(recorded_at)
    else:
        return refuse(STATUS_UNAVAILABLE, "RECORDED_AT_TYPE")
    if recorded_raw is None:
        return refuse(STATUS_UNAVAILABLE, "RECORDED_AT_INVALID")
    if not _is_aware(recorded_raw):
        return refuse(STATUS_UNAVAILABLE, "RECORDED_AT_NAIVE")
    recorded_utc = recorded_raw.astimezone(timezone.utc)
    payload["recorded_at"] = _utc_iso(recorded_utc)

    # -- gate 2: expected_session must name a real NYSE session --------------- #
    if not isinstance(expected_session, date) or isinstance(expected_session, datetime):
        return refuse(STATUS_UNAVAILABLE, "EXPECTED_SESSION_TYPE")
    if not is_session(expected_session):
        return refuse(STATUS_UNAVAILABLE, "EXPECTED_SESSION_NOT_TRADING_DAY")
    if expected_session > expected_last_session(recorded_utc):
        return refuse(STATUS_UNAVAILABLE, "EXPECTED_SESSION_NOT_COMPLETED")
    expected20 = _expected_sessions(expected_session, WINDOW)
    if expected20 is None:
        return refuse(STATUS_UNAVAILABLE, "EXPECTED_SESSION_CALENDAR")

    # -- gate 3: frame presence ------------------------------------------------ #
    if frame is None:
        payload["coverage"]["observed_sessions"] = 0
        return refuse(STATUS_NO_COVERAGE, "FRAME_ABSENT")
    if not isinstance(frame, pd.DataFrame):
        return refuse(STATUS_UNAVAILABLE, "FRAME_TYPE")
    if frame.empty:
        payload["coverage"]["observed_sessions"] = 0
        return refuse(STATUS_NO_COVERAGE, "FRAME_EMPTY")
    if "close" not in frame.columns or "volume" not in frame.columns:
        return refuse(STATUS_UNAVAILABLE, "COLUMNS_MISSING")

    # -- gate 4: index shape (stored NY session dates) ------------------------- #
    index = frame.index
    if not isinstance(index, pd.DatetimeIndex):
        return refuse(STATUS_UNAVAILABLE, "INDEX_TYPE")
    if index.tz is not None:
        return refuse(STATUS_UNAVAILABLE, "INDEX_TIMEZONE")
    if (index != index.normalize()).any():
        return refuse(STATUS_UNAVAILABLE, "INDEX_NOT_MIDNIGHT")
    if not index.is_monotonic_increasing:
        return refuse(STATUS_UNAVAILABLE, "INDEX_UNORDERED")
    if index.has_duplicates:
        return refuse(STATUS_UNAVAILABLE, "INDEX_DUPLICATED")

    dates = [stamp.date() for stamp in index]
    if dates[-1] > expected_session:
        return refuse(STATUS_UNAVAILABLE, "FUTURE_ROW")
    if any(not is_session(day) for day in dates):
        return refuse(STATUS_UNAVAILABLE, "INDEX_NOT_SESSION_DATES")
    payload["coverage"]["observed_sessions"] = len(set(dates).intersection(expected20))

    # -- gate 5: the required window must be fully covered --------------------- #
    if len(dates) < WINDOW:
        return refuse(STATUS_NO_COVERAGE, "INSUFFICIENT_SESSIONS")
    if dates[-1] != expected_session:
        return refuse(STATUS_NO_COVERAGE, "STALE_NO_EXPECTED_SESSION")
    if dates[-WINDOW:] != expected20:
        return refuse(STATUS_NO_COVERAGE, "WINDOW_SESSIONS_MISSING")

    # -- gate 6: source digest is required ------------------------------------- #
    if source_sha256 is None:
        return refuse(STATUS_UNAVAILABLE, "SOURCE_SHA256_REQUIRED")
    if not _is_sha256(source_sha256):
        return refuse(STATUS_UNAVAILABLE, "SOURCE_SHA256_INVALID")
    payload["source_sha256"] = source_sha256

    # -- gate 7: ingested_at, when present, is aware and inside bounds --------- #
    if ingested_at is not None:
        if isinstance(ingested_at, datetime):
            ingested_raw = ingested_at
        else:
            ingested_raw = _parse_iso_datetime(ingested_at)
        if ingested_raw is None or not _is_aware(ingested_raw):
            return refuse(STATUS_UNAVAILABLE, "INGESTED_AT_INVALID")
        ingested_utc = ingested_raw.astimezone(timezone.utc)
        if ingested_utc > recorded_utc:
            return refuse(STATUS_UNAVAILABLE, "INGESTED_AT_AFTER_RECORDED")
        if ingested_utc.astimezone(_NY_TZ).date() < dates[-1]:
            return refuse(STATUS_UNAVAILABLE, "INGESTED_AT_BEFORE_LATEST_BAR")
        payload["ingested_at"] = _utc_iso(ingested_utc)

    # -- gate 8: the selected window values must be clean ---------------------- #
    close_tail = frame["close"].tail(WINDOW)
    volume_tail = frame["volume"].tail(WINDOW)
    for close_value, volume_value in zip(close_tail, volume_tail):
        close_number = _as_finite_number(close_value)
        if close_number is None or close_number <= 0:
            return refuse(STATUS_UNAVAILABLE, "CLOSE_VALUE_INVALID")
        volume_number = _as_finite_number(volume_value)
        if volume_number is None or volume_number < 0:
            return refuse(STATUS_UNAVAILABLE, "VOLUME_VALUE_INVALID")
        if not math.isfinite(close_number * volume_number):
            return refuse(STATUS_UNAVAILABLE, "DOLLAR_VOLUME_OVERFLOW")

    # -- gate 9: native compute, unchanged ------------------------------------- #
    metrics = compute(close_tail, volume_tail)
    if metrics is None:
        # With the window fully validated above, the native chip only bails on
        # a non-positive dollar ADV (e.g. an all-zero-volume window).
        return refuse(STATUS_NO_COVERAGE, "ZERO_ADV_NO_COVERAGE")

    # -- gate 10: currency evidence -------------------------------------------- #
    if isinstance(currency_evidence, dict) and currency_evidence.get("schema") == "liquidity_currency_observations.v1":
        currency = qualify_currency(currency_evidence, ticker=ticker,
                                    sessions=expected20, recorded_at=recorded_utc)
    else:
        currency = _qualified_currency(
            currency_evidence, ticker, recorded_utc.date(), expected20[0], expected20[-1]
        )
    if currency is None:
        return refuse(STATUS_NO_COVERAGE, "CURRENCY_NOT_QUALIFIED")
    if currency.get("schema") == "liquidity_currency_dated.v1":
        currency["source_digest_basis"] = "canonical_json_sort_keys_compact_ascii"
    payload["currency"] = currency

    payload["metrics"] = dict(metrics)
    payload["sample_n"] = WINDOW
    payload["thinly_traded"] = metrics["tier"] in THIN_TIERS
    return payload
