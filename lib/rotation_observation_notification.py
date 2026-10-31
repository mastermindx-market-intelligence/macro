"""lib/rotation_observation_notification.py -- the FROZEN consumer contract for
``category='sector_rotation_relative'`` defensive-rotation observations.

WHAT THIS IS
------------
This module is the ONE place that decides whether a
``macro.rotation_observation.v1`` payload is a well-formed, arithmetically honest,
still-current observation. It is **pure**: no IO, no clock, no calendar of its own, no
network, no randomness. Every input is injected. That is what makes the rules below
testable without a market, a database or a mail server.

WHAT THIS IS NOT
----------------
It is not a producer. It mints nothing, queues nothing and schedules nothing: the
parent's separate slice owns the source-transition/outbox producer, and nothing here
may be mistaken for one. It is not advice -- nothing in this module or in the copy it
enables may carry a crash probability, a fund flow, a buy/sell instruction, a leverage
number or a position size. It describes what two sessions of prices did; the reader
draws their own conclusion.

THE TWO GATES, AND WHY THEY ARE SEPARATE
----------------------------------------
:func:`validate` is **structural + arithmetic** and never consults a clock. It answers
"is this shape honest?" -- symbol grammar, date grammar, ``not_after > observed_at``,
and above all the relative-wealth identity below, so a producer bug cannot ship a
self-contradictory pair of percentages.

:func:`evaluate` adds the **temporal** gate and is the only function here that reads
the clock, and it takes ``now_utc`` by injection. It answers "is this still current?"
using the EXISTING :func:`lib.us_cash_calendar.expected_last_session` -- deliberately
NOT a second calendar. One published US cash-session slate has exactly one owner; a
second implementation of "what session should we be reporting" is how a half-day and a
holiday quietly disagree between producer and drain.

This is **end-of-day observation delivery, not an intraday forecast.** ``event_as_of``
is a settled market session, so ``expected_last_session(now_utc)`` is only equal to it
once that session's bar has settled (17:00 ET, 14:00 ET on a published half day). Before
that the row is legitimately not-current and is SUPPRESSED as expired rather than sent
early -- see ``REASON_EXPIRED``.

FAIL CLOSED, AND FAIL IN TWO DIFFERENT DIRECTIONS
-------------------------------------------------
The two failure modes are deliberately NOT collapsed, because the drain treats them
differently and a wrong collapse is a silent behaviour change:

* **INVALID / UNEVALUABLE** -- we could not establish that the payload is correct. The
  drain returns ``Decision(action='unevaluable', ...)``: the outbox row stays ``pending``
  and nothing is sent. An unknown calendar, a future clock, a malformed date and a
  structurally broken payload all land here. "We do not know" is never a licence to send.
* **EXPIRED** -- we established the payload was correct and it is now stale. The drain
  returns ``Decision(action='suppress', ...)``: terminal, ``status='suppressed'``, and
  counted in the run receipt. This is not a failure and must NOT be retried: the next
  tick would only re-derive the same expiry, and pushing ``deliver_after`` into the
  future to "rescue" the row would be an artificial deferral the contract forbids.

No retry owner, no new queue, no new lifecycle, no new status enum is introduced here.
``alert_outbox`` already admits ``suppressed`` under its migration0013 CHECK.

THE RELATIVE WEALTH IDENTITY
----------------------------
``ratio_return_pct`` is not a free number the producer reports alongside the two
absolute returns; it is a FUNCTION of them:

    ratio == ((1 + numerator/100) / (1 + denominator/100) - 1) * 100

Both absolute returns are therefore required to exceed ``-100`` (a total loss would make
the denominator zero and the ratio undefined), and the reported ratio must match the
identity within ``1e-6``. A payload that fails this is refused, not rounded -- a
"relative" number that disagrees with its own inputs is exactly the failure mode this
whole category exists to avoid.

A ``data_withdrawal`` carries ``values = None`` and MUST, because re-rendering a stale
positive pair after the evidence has been withdrawn would assert a measurement that no
longer has support.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

__all__ = [
    "SOURCE", "CATEGORY", "AUTHORITY", "KINDS", "MEASURED_KINDS",
    "REASON_INVALID", "REASON_EXPIRED",
    "OK", "EXPIRED", "INVALID", "UNEVALUABLE",
    "Observation", "Verdict",
    "claims_rotation_observation", "validate", "evaluate",
]

#: The frozen identity triple. A payload that does not carry exactly these is not ours.
SOURCE = "macro.rotation_observation.v1"
CATEGORY = "sector_rotation_relative"
AUTHORITY = "notification_only"

#: Every kind the mailer can compose. ``data_withdrawal`` is the only one that carries
#: no measurement; the other three carry the frozen two-session arithmetic.
KINDS: tuple[str, ...] = ("observed_change", "reversal", "data_withdrawal", "correction")
MEASURED_KINDS: tuple[str, ...] = ("observed_change", "reversal", "correction")

#: The drain's two existing Decision reasons. Named here so the exact strings that
#: land in ``alert_outbox.last_error`` are pinned by one owner, not spelled twice.
REASON_INVALID = "rotation_observation_invalid"
REASON_EXPIRED = "rotation_observation_expired"

#: ``evaluate`` outcomes. INVALID and UNEVALUABLE both fail closed but are kept
#: distinct so a test can prove each was reached deliberately.
OK = "ok"
EXPIRED = "expired"
INVALID = "invalid"
UNEVALUABLE = "unevaluable"

#: Uppercase market-symbol grammar. It admits ``BRK.B``, ``600519.SS``, ``ES=F`` and
#: ``BF-B`` and refuses everything else -- in particular ``<``, ``"``, ``/`` and ``:``
#: cannot appear, so a symbol can never carry HTML or steer a URL. The first character
#: is pinned to alphanumeric, so a leading ``^``/``.``/``-``/``=`` is out even though
#: that punctuation is legal in the tail class.
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.^=-]{0,19}$")

#: Strict ISO calendar date. ``date.fromisoformat`` alone is NOT enough: Python 3.11+
#: also accepts ``20260905`` and ``2026-W01-1``, so the shape is pinned first.
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_ID_MAX = 128
_REL_TOL = 1e-6


# --------------------------------------------------------------------------- #
# selectors and parsed shape
# --------------------------------------------------------------------------- #
def claims_rotation_observation(payload: Any) -> bool:
    """True iff ``payload`` claims THIS category -- the single routing selector.

    Deliberately keyed on :data:`CATEGORY` alone. The category is the user-consent
    surface (``alert_categories``), so it is the one field a payload cannot forge past
    a filter; ``source`` and ``authority`` are then judged by :func:`validate`, which
    **raises** rather than returning False. A row that says ``sector_rotation_relative``
    with a wrong source must not fall through to the generic user-authored-condition
    mail: that copy would tell the reader a condition they never set fired, which is a
    worse lie than sending nothing.
    """
    return isinstance(payload, dict) and payload.get("category") == CATEGORY


@dataclass(frozen=True)
class Observation:
    """A payload that has passed :func:`validate`. Values are normalized, not raw.

    ``observed_at`` / ``not_after`` are timezone-AWARE and normalized to UTC; the
    ``*_iso`` companions are the exact strings as supplied, so the mailer can echo the
    source's own formatting without re-deriving it.
    """
    kind: str
    observation_id: str
    previous_observation_id: str | None
    num: str
    den: str
    pair_id: str
    event_as_of: date
    event_as_of_iso: str
    source_as_of: date | None
    observed_at: datetime
    observed_at_iso: str
    not_after: datetime
    values: dict | None


@dataclass(frozen=True)
class Verdict:
    """:func:`evaluate`'s answer, already mapped onto the drain's Decision vocabulary."""
    status: str          # one of OK / EXPIRED / INVALID / UNEVALUABLE
    action: str          # 'send' | 'suppress' | 'unevaluable'
    reason: str          # the drain's Decision.reason ('ok' when sending)
    detail: str          # WHY, for the test and the log -- never rendered


# --------------------------------------------------------------------------- #
# scalar helpers
# --------------------------------------------------------------------------- #
def _bad(detail: str) -> ValueError:
    return ValueError(f"rotation observation invalid: {detail}")


def _req_str(payload: dict, key: str, *, max_len: int = _ID_MAX) -> str:
    v = payload.get(key)
    if not isinstance(v, str):
        raise _bad(f"{key} is not a string")
    if not v.strip():
        raise _bad(f"{key} is empty")
    if len(v) > max_len:
        raise _bad(f"{key} is longer than {max_len} chars")
    return v


def _opt_str(payload: dict, key: str, *, max_len: int = _ID_MAX) -> str | None:
    if key not in payload or payload.get(key) is None:
        return None
    return _req_str(payload, key, max_len=max_len)


def _symbol(payload: dict, key: str) -> str:
    v = payload.get(key)
    # The regex is the whole defence: no HTML metacharacter and no URL separator can
    # match it, so a symbol is safe to print and can never become a link.
    if not isinstance(v, str) or not _SYMBOL_RE.fullmatch(v):
        raise _bad(f"{key} is not a market symbol")
    return v


def _iso_date(value: Any, key: str) -> date:
    if not isinstance(value, str) or not _ISO_DATE_RE.fullmatch(value):
        raise _bad(f"{key} is not a strict YYYY-MM-DD date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise _bad(f"{key} is not a real calendar date") from None


def _opt_iso_date(value: Any, key: str) -> date | None:
    return None if value is None else _iso_date(value, key)


def _aware_utc(value: Any, key: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise _bad(f"{key} is not an ISO8601 string")
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise _bad(f"{key} is not a real ISO8601 datetime") from None
    if dt.tzinfo is None or dt.utcoffset() is None:
        # A naive datetime has no instant. Treating it as UTC would let a producer's
        # missing timezone silently move the observation; refuse it.
        raise _bad(f"{key} is not timezone-aware")
    try:
        return dt.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        raise _bad(f"{key} is outside the representable UTC range") from None


def _finite(value: Any, key: str) -> float:
    # bool is a subclass of int: `True` must not pass as 1.0. NaN/inf are refused --
    # a non-finite "return" is not a measurement, and it would poison the identity.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _bad(f"{key} is not a real number")
    try:
        f = float(value)
    except (OverflowError, ValueError):
        raise _bad(f"{key} is outside the finite numeric range") from None
    if not math.isfinite(f):
        raise _bad(f"{key} is not finite")
    return f


# --------------------------------------------------------------------------- #
# the structural + arithmetic contract
# --------------------------------------------------------------------------- #
def validate(payload: Any) -> Observation:
    """The PURE structural and arithmetic contract. Returns an :class:`Observation`.

    Raises :class:`ValueError` on every violation -- this function has exactly two
    outcomes, so a caller cannot accidentally treat "partly checked" as "passed". It
    reads no clock and consults no calendar; :func:`evaluate` layers the temporal gate
    on top of an already-validated payload.

    Unknown keys are tolerated on purpose. A producer may add a field this contract
    has not seen; refusing delivery over an unknown key would be a worse outcome than
    ignoring it. What is enforced is that the MAILER renders nothing outside the
    frozen set, so an added field can never reach a reader.
    """
    if not isinstance(payload, dict):
        raise _bad("payload is not an object")
    if payload.get("source") != SOURCE:
        raise _bad("source is not the rotation observation source")
    if payload.get("category") != CATEGORY:
        raise _bad("category is not the rotation observation category")
    if payload.get("authority") != AUTHORITY:
        raise _bad("authority is not notification_only")

    kind = payload.get("kind")
    if kind not in KINDS:
        raise _bad("kind is not one of the four observation kinds")

    observation_id = _req_str(payload, "observation_id")
    previous_observation_id = _opt_str(payload, "previous_observation_id")
    if previous_observation_id is None and kind != "observed_change":
        # A reversal, a correction and a withdrawal all assert something about an
        # earlier observation. With no reference there is nothing to reverse, correct
        # or withdraw, and the message would have to invent one.
        raise _bad(f"previous_observation_id is required for kind={kind}")

    if previous_observation_id == observation_id:
        raise _bad("previous_observation_id must reference a different observation")
    num = _symbol(payload, "num")
    den = _symbol(payload, "den")
    if num == den:
        raise _bad("num and den are the same symbol")
    pair_id = _req_str(payload, "pair_id")

    event_as_of = _iso_date(payload.get("event_as_of"), "event_as_of")
    observed_at = _aware_utc(payload.get("observed_at"), "observed_at")
    not_after = _aware_utc(payload.get("not_after"), "not_after")
    if not_after <= observed_at:
        raise _bad("not_after is not after observed_at")

    if "source_as_of" not in payload or "values" not in payload:
        raise _bad("source_as_of and values must be explicit, including nullable withdrawals")
    source_as_of = _opt_iso_date(payload.get("source_as_of"), "source_as_of")
    if kind in MEASURED_KINDS:
        if source_as_of is None:
            raise _bad("source_as_of is required for a measured kind")
        if source_as_of != event_as_of:
            # A measured observation whose source date is not its own session date
            # would be reporting a number for a session it did not measure.
            raise _bad("source_as_of does not equal event_as_of")
    elif source_as_of is not None and source_as_of > event_as_of:
        # A withdrawal may carry no source date, or the older date the evidence was
        # last seen at. Never a LATER one.
        raise _bad("source_as_of is after event_as_of for a withdrawal")

    values = payload.get("values")
    if kind in MEASURED_KINDS:
        values = _validate_values(values)
    elif values is not None:
        # The load-bearing withdrawal rule: a stale positive pair rendered after the
        # evidence was withdrawn would assert a measurement that no longer has support.
        raise _bad("values must be null for a data_withdrawal")

    return Observation(
        kind=kind, observation_id=observation_id, previous_observation_id=previous_observation_id,
        num=num, den=den, pair_id=pair_id,
        event_as_of=event_as_of, event_as_of_iso=str(payload["event_as_of"]),
        source_as_of=source_as_of,
        observed_at=observed_at, observed_at_iso=str(payload["observed_at"]),
        not_after=not_after, values=values,
    )


def _validate_values(values: Any) -> dict:
    if not isinstance(values, dict):
        raise _bad("values is not an object")
    sessions = values.get("sessions")
    # bool is a subclass of int, and `sessions: True` must not read as one session.
    if isinstance(sessions, bool) or not isinstance(sessions, int) or sessions != 2:
        raise _bad("values.sessions is not the integer 2")
    numerator = _finite(values.get("numerator_return_pct"), "values.numerator_return_pct")
    denominator = _finite(values.get("denominator_return_pct"), "values.denominator_return_pct")
    ratio = _finite(values.get("ratio_return_pct"), "values.ratio_return_pct")
    if numerator <= -100.0:
        raise _bad("values.numerator_return_pct is not above -100")
    if denominator <= -100.0:
        raise _bad("values.denominator_return_pct is not above -100")
    # denominator > -100 guarantees (1 + d/100) > 0, so this division is safe.
    expected = ((1.0 + numerator / 100.0) / (1.0 + denominator / 100.0) - 1.0) * 100.0
    if not math.isfinite(expected) or abs(expected - ratio) > _REL_TOL:
        raise _bad("values.ratio_return_pct breaks the relative wealth identity")
    return {
        "sessions": sessions,
        "numerator_return_pct": numerator,
        "denominator_return_pct": denominator,
        "ratio_return_pct": ratio,
    }


# --------------------------------------------------------------------------- #
# the temporal gate
# --------------------------------------------------------------------------- #
def _expected_session(instant: datetime) -> date | None:
    """``expected_last_session`` or None when the published calendar cannot answer.

    ``expected_last_session`` raises rather than guessing when it cannot find a session
    in the prior 30 days, and ``early_close`` reaches an announced-notice table that
    may not cover the year in hand. Both are "we do not know", and both must fail
    closed as UNEVALUABLE -- never as OK.

    The calendar is imported HERE, not at module scope, for two reasons. It keeps this
    module's structural half (``validate``) free of a calendar dependency, so
    ``app/mailer.py`` -- which composes and never times -- can import this module
    without pulling a trading calendar into its import graph. And an import failure
    inside the ``try`` is caught by the same handler as a lookup failure, so a broken
    calendar fails closed as UNEVALUABLE instead of raising through the drain.
    """
    try:
        from lib.us_cash_calendar import expected_last_session
        session = expected_last_session(instant)
        return session if type(session) is date else None
    except Exception:  # noqa: BLE001 -- a calendar failure is data, not a bug
        return None


def evaluate(payload: Any, *, now_utc: datetime | None) -> Verdict:
    """The full consumer gate: structural, arithmetic AND temporal. Pure + injected.

    ``now_utc`` MUST be a timezone-aware ``datetime``; a naive or missing clock is
    UNEVALUABLE rather than an assumed-UTC send, for the same reason a naive
    ``observed_at`` is refused. Ordering matters and is deliberate:

    1. shape/arithmetic      -> INVALID      (unevaluable, row stays pending)
    2. clock we cannot trust -> UNEVALUABLE  (unevaluable, row stays pending)
    3. observation in the future -> INVALID   (a future-dated row is malformed)
    4. ``event_as_of`` != ``expected_last_session(observed_at)`` -> INVALID
    5. calendar unanswerable -> UNEVALUABLE
    6. ``event_as_of`` != ``expected_last_session(now_utc)`` -> EXPIRED (suppressed)
    7. ``now_utc`` >= ``not_after`` -> EXPIRED (suppressed)
    8. otherwise -> OK (send)

    Steps 6 and 7 are terminal-by-design. Re-deriving them on a later tick produces the
    same answer, so this is a suppression, never a retry, and never a deferral pushed
    into the future.
    """
    try:
        obs = validate(payload)
    except ValueError as exc:
        return Verdict(INVALID, "unevaluable", REASON_INVALID, str(exc))

    if not isinstance(now_utc, datetime) or now_utc.tzinfo is None \
            or now_utc.utcoffset() is None:
        return Verdict(UNEVALUABLE, "unevaluable", REASON_INVALID,
                       "now_utc is not a timezone-aware datetime")
    try:
        now = now_utc.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        return Verdict(UNEVALUABLE, "unevaluable", REASON_INVALID,
                       "now_utc is outside the representable UTC range")

    if obs.observed_at > now:
        return Verdict(INVALID, "unevaluable", REASON_INVALID,
                       "observed_at is in the future relative to now_utc")

    expect_observed = _expected_session(obs.observed_at)
    if expect_observed is None:
        return Verdict(UNEVALUABLE, "unevaluable", REASON_INVALID,
                       "calendar could not resolve the session for observed_at")
    if obs.event_as_of != expect_observed:
        return Verdict(INVALID, "unevaluable", REASON_INVALID,
                       "event_as_of is not the session that observed_at settles")

    expect_now = _expected_session(now)
    if expect_now is None:
        return Verdict(UNEVALUABLE, "unevaluable", REASON_INVALID,
                       "calendar could not resolve the session for now_utc")
    if obs.event_as_of != expect_now:
        return Verdict(EXPIRED, "suppress", REASON_EXPIRED,
                       "event_as_of is no longer the last settled session")
    if now >= obs.not_after:
        # Exact expiry counts as expired: at not_after the observation is one instant
        # past its own validity, and >= is the boundary the contract names.
        return Verdict(EXPIRED, "suppress", REASON_EXPIRED,
                       "now_utc has reached not_after")
    return Verdict(OK, "send", "ok", "current and within not_after")
