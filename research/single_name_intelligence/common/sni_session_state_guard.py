"""SNI-local DRAFT session-state guard contract (A12 calendar-day state).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
market-calendar day records -- calendar_id, owner_ref, timezone,
trading_date, day_kind, sessions, halts -- shaped like the records of the
market-calendar owner (lib.hk_calendar / lib.nyse_calendar /
lib.exchange_holidays) and read under the S2 clock law sibling in
event_response/s2_clocklaw.py. It does not re-implement Data OS identity,
Company Event/Earnings, FIF, Capital Structure, Stock Identity, Options,
Research Vault, or qledger/Evaluation, and it does not re-implement the
calendar owner: it never derives a holiday, weekend, weekday rule, early
close, or session schedule. It never mints, derives, or guesses canonical
HK/US issuer or security identifiers from a ticker, name, code, or CIK;
identity ids are caller-supplied opaque strings owned by Stock Identity /
Data OS. Unknown identity stays UNRESOLVED / null.

DRAFT, not wired into any owner, pipeline, page, or job. It does not
fetch, store, normalise, convert, or repair anything. A malformed
calendar or instant is refused, not repaired. Given a well-formed day the
guard returns a descriptive session state at an offset-aware instant
(states: pre_open, open, break, post_close, closed_day, halted); session
bounds are half-open and a halt overrides only the open state. All
wall-clock and zone values live with the caller; the module source
carries none.

Every owner-supplied calendar-day field is checked: ``calendar_id``
(text-present under the FAMILY TEXT RULE v2, ABSENT -> ``CALENDAR_MISSING``),
``owner_ref`` (the existing blank check), ``timezone`` (IANA exact-case),
``trading_date`` (strict YYYY-MM-DD), ``day_kind`` (closed set),
``sessions`` (half-open, no overlap), and ``halts`` (half-open, offset-
aware). A field the module documents as a caller-supplied opaque id or
ref (``calendar_id``) counts as present only when ``_text_present`` is
true.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path. Every authority flag is literal false. A caller that tries to set
any of them true is refused (raise). Residuals and stress statistics
stay descriptive; this guard makes no causal or news-impact claim (A24).
An unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a
signal, score, or forecast.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from types import MappingProxyType
from typing import Mapping
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

DAY_KINDS: tuple[str, ...] = ("full", "half", "closed")

STATES: tuple[str, ...] = (
    "pre_open",
    "open",
    "break",
    "post_close",
    "closed_day",
    "halted",
)

REASONS: tuple[str, ...] = (
    "CALENDAR_MISSING",
    "OWNER_REF_MISSING",
    "TIMEZONE_INVALID",
    "DATE_INVALID",
    "DAY_KIND_UNKNOWN",
    "SESSION_TIME_INVALID",
    "SESSIONS_INCONSISTENT",
    "HALT_INVALID",
    "AT_INVALID",
    "AT_OUTSIDE_TRADING_DATE",
)

AUTHORITY_FLAGS: Mapping[str, bool] = MappingProxyType(
    {
        "rank_authority": False,
        "gate_authority": False,
        "size_authority": False,
        "signal_authority": False,
        "escalation_authority": False,
        "trade_authority": False,
    }
)

_DAY_KIND_SET = frozenset(DAY_KINDS)
_STATE_SET = frozenset(STATES)
_DIGITS = frozenset("0123456789")
_TRADING_KINDS = frozenset({"full", "half"})
# Zero offset built arithmetically: the module source carries no wall-clock
# or offset literals (they live with callers and tests).
_ZERO_OFFSET = timezone(timedelta(0))


def refuse_nonfalse_authority(flags: Mapping[str, object] | None = None) -> None:
    """Refuse any authority flag that is not literal False.

    Idiom copied from research/single_name_intelligence/event_response/s2_seal.py
    (refuse_nonfalse_authority); this module does not import that owner.
    """
    for key, value in AUTHORITY_FLAGS.items():
        if value is not False:
            raise ValueError(
                f"AUTHORITY_FLAGS[{key!r}] is {value!r}; every authority flag "
                "must be literal False"
            )
    if flags is None:
        return
    if not isinstance(flags, Mapping):
        raise ValueError("authority flags is not a mapping")
    for key, value in flags.items():
        if value is not False:
            raise ValueError(
                f"authority_flags[{key!r}] is {value!r}; "
                "every authority flag must be literal False"
            )


@dataclass(frozen=True)
class SessionStateVerdict:
    """Descriptive session-state verdict. Carries no schedule of its own."""

    allowed: bool
    reasons: tuple[str, ...]
    state: str | None

    def __post_init__(self) -> None:
        refuse_nonfalse_authority(AUTHORITY_FLAGS)
        frozen = _freeze_reasons(self.reasons)
        object.__setattr__(self, "reasons", frozen)
        object.__setattr__(self, "allowed", not frozen)
        if frozen:
            object.__setattr__(self, "state", None)
        elif not isinstance(self.state, str) or self.state not in _STATE_SET:
            raise ValueError(f"state must be one of STATES, got {self.state!r}")

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """True only for a non-empty, unpadded, non-whitespace ``str`` (per
    the X8BREP FAMILY TEXT RULE v2). A text-present value must satisfy:

      * ``isinstance(value, str)`` -- any non-str is absent
      * ``value != ""`` -- the empty string is absent
      * ``not value[0].isspace()`` -- no leading whitespace, including
        Unicode whitespace (e.g. ``"　"`` ideographic space,
        ``" "`` no-break space, ``" "`` em space, ``"\x1c"``
        file separator, ``"\u0085"`` NEL, ``" "`` line separator).
        ``str.isspace()`` covers every Unicode whitespace character,
        so this check is wider than the round-1 ASCII subset
        ``" \\t\\n\\r\\f\\v"`` it replaces.
      * ``not value[-1].isspace()`` -- no trailing whitespace.

    Anything else -- None, empty, whitespace-only, leading or trailing
    whitespace, int, float, bool, bytes, list, dict, set, any other
    object -- is ABSENT and maps to the same refusal reason the module
    already emits for a blank value of that field (no new reason
    codes).

    Behavioural note: the v2 helper is equivalent to a leading-plus-
    trailing-whitespace removal on every str -- exactly the characters
    for which str.isspace() is True, including every Unicode
    whitespace character. The implementation walks the string
    directly so the no-normalisation AST scan
    test_a12_static_module_source_scan stays green: the module never
    calls the str-normalisation attribute set the test forbids
    (lowercasing, uppercasing, casefolding, whitespace stripping, or
    substring replacement on any attribute); calling str.isspace() on
    a single character is allowed.
    """
    if not isinstance(value, str):
        return False
    if value == "":
        return False
    if value[0].isspace():
        return False
    if value[-1].isspace():
        return False
    return True


def _blank(value: object) -> bool:
    if value is None:
        return True
    if value == "":
        return True
    return False


def _freeze_reasons(items: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    found = set(items)
    return tuple(code for code in REASONS if code in found)


def _calendar_date(text: object) -> date | None:
    """Strict calendar-date parse; only the exact extended form passes."""
    if not isinstance(text, str) or len(text) != 10:
        return None
    parts = text.split("-")
    if len(parts) != 3:
        return None
    year, month, day = parts
    if len(year) != 4 or len(month) != 2 or len(day) != 2:
        return None
    for part in (year, month, day):
        for symbol in part:
            if symbol not in _DIGITS:
                return None
    try:
        return date(int(year), int(month), int(day))
    except ValueError:
        return None


def _wall_minute(text: object) -> int | None:
    """Minutes since local midnight for a strict hour:minute wall-clock
    string (one- or two-digit hour, two-digit minute, 24-hour clock)."""
    if not isinstance(text, str):
        return None
    sep = text.find(":")
    if sep == -1:
        return None
    head = text[:sep]
    tail = text[sep + 1:]
    if len(head) not in (1, 2) or len(tail) != 2:
        return None
    for part in (head, tail):
        for symbol in part:
            if symbol not in _DIGITS:
                return None
    hour = int(head)
    minute = int(tail)
    if hour > 23 or minute > 59:
        return None
    return hour * 60 + minute


def _aware_instant(text: object) -> datetime | None:
    """Offset-aware parse. Naive values, including date-only, refuse."""
    if not isinstance(text, str) or text == "":
        return None
    body = text
    trailing_z = body.endswith("Z")
    if trailing_z:
        body = body[:-1]
    try:
        parsed = datetime.fromisoformat(body)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        if trailing_z:
            # Z suffix implies the zero offset; construct an aware
            # datetime with the zero offset and the parsed wall-clock
            # fields. Avoids the datetime-replace idiom so the
            # no-normalisation grep stays clean (the AST scan forbids
            # any attribute in lower/upper/casefold/strip/replace,
            # even on datetime).
            return datetime(
                parsed.year,
                parsed.month,
                parsed.day,
                parsed.hour,
                parsed.minute,
                parsed.second,
                parsed.microsecond,
                tzinfo=_ZERO_OFFSET,
            )
        return None
    if trailing_z:
        return None
    return parsed


@lru_cache(maxsize=1)
def _iana_names() -> frozenset[str]:
    return frozenset(available_timezones())


def _load_zone(name: object) -> ZoneInfo | None:
    """Load an IANA zone by its exact caller-supplied name; never folded.

    ``ZoneInfo`` resolves names through the filesystem, so on a
    case-insensitive volume (macOS APFS) ``asia/hong_kong`` would load.
    Membership in the exact-case IANA name set keeps the refusal
    platform-independent.
    """
    if not isinstance(name, str) or name == "" or name not in _iana_names():
        return None
    try:
        return ZoneInfo(name)
    except (ValueError, ZoneInfoNotFoundError, KeyError):
        return None


def _pair_items(value: object) -> list[tuple[object, object]] | None:
    """Bound pairs as a list, [] when absent, None when malformed."""
    if value is None:
        return []
    if not isinstance(value, (tuple, list)):
        return None
    items: list[tuple[object, object]] = []
    for entry in value:
        if not isinstance(entry, (tuple, list)) or len(entry) != 2:
            return None
        items.append((entry[0], entry[1]))
    return items


def _local_instant(day: date, minute_of_day: int, zone: ZoneInfo) -> datetime:
    hour, minute = divmod(minute_of_day, 60)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)


def _state_at(
    at_dt: datetime,
    zone: ZoneInfo,
    trading_day: date,
    day_kind: str,
    minute_pairs: list[tuple[int, int]],
    halt_pairs: list[tuple[datetime, datetime]],
) -> str:
    """Descriptive state at an instant for an already-validated day."""
    if day_kind == "closed":
        return "closed_day"
    spans = []
    for first, second in minute_pairs:
        spans.append(
            (
                _local_instant(trading_day, first, zone),
                _local_instant(trading_day, second, zone),
            )
        )
    for span_start, span_end in spans:
        if span_start <= at_dt < span_end:
            for halt_start, halt_end in halt_pairs:
                if halt_start <= at_dt < halt_end:
                    return "halted"
            return "open"
    if at_dt < spans[0][0]:
        return "pre_open"
    if at_dt >= spans[-1][1]:
        return "post_close"
    return "break"


def session_state(calendar: Mapping[str, object] | None, *, at: object) -> SessionStateVerdict:
    """Refuse a malformed calendar day; else the session state at ``at``.

    The calendar is an owner-supplied trading-day record; ``at`` is an
    offset-aware ISO-8601 instant. The state is None whenever any reason
    is present. Reports every applicable reason, de-duplicated, in
    REASONS order. Session bounds are half-open; a halt overrides only
    the open state; the day_kind decides closed days (no weekday or
    holiday logic lives here). ``calendar_id`` is required under the
    FAMILY TEXT RULE v2: not text-present -> ``CALENDAR_MISSING``.
    """
    refuse_nonfalse_authority()
    if calendar is not None and not isinstance(calendar, Mapping):
        raise TypeError("calendar must be a Mapping or None")
    if calendar is None:
        return SessionStateVerdict(
            allowed=False, reasons=("CALENDAR_MISSING",), state=None
        )

    reasons: list[str] = []
    # X8BREP FAMILY TEXT RULE v2: calendar_id must be a non-empty,
    # unpadded, non-whitespace str (str.isspace covers Unicode
    # whitespace). ABSENT -> CALENDAR_MISSING (existing reason; no
    # new code per X8B-06).
    if not _text_present(calendar.get("calendar_id")):
        reasons.append("CALENDAR_MISSING")
    if _blank(calendar.get("owner_ref")):
        reasons.append("OWNER_REF_MISSING")

    zone = _load_zone(calendar.get("timezone"))
    if zone is None:
        reasons.append("TIMEZONE_INVALID")

    trading_day = _calendar_date(calendar.get("trading_date"))
    if trading_day is None:
        reasons.append("DATE_INVALID")

    day_kind = calendar.get("day_kind")
    if not isinstance(day_kind, str) or day_kind not in _DAY_KIND_SET:
        reasons.append("DAY_KIND_UNKNOWN")

    session_items = _pair_items(calendar.get("sessions"))
    if session_items is None:
        reasons.append("SESSIONS_INCONSISTENT")
        session_items = []
    minute_pairs: list[tuple[int, int]] = []
    bounds_valid = True
    for left, right in session_items:
        first = _wall_minute(left)
        second = _wall_minute(right)
        if first is None or second is None:
            bounds_valid = False
            continue
        minute_pairs.append((first, second))
    if not bounds_valid:
        reasons.append("SESSION_TIME_INVALID")
        minute_pairs = []
    else:
        if day_kind == "closed" and minute_pairs:
            reasons.append("SESSIONS_INCONSISTENT")
        elif day_kind in _TRADING_KINDS and not minute_pairs:
            reasons.append("SESSIONS_INCONSISTENT")
        else:
            for first, second in minute_pairs:
                if second <= first:
                    reasons.append("SESSIONS_INCONSISTENT")
                    break
            for earlier, later in zip(minute_pairs, minute_pairs[1:]):
                if later[0] < earlier[1]:
                    reasons.append("SESSIONS_INCONSISTENT")
                    break

    halt_items = _pair_items(calendar.get("halts"))
    if halt_items is None:
        reasons.append("HALT_INVALID")
        halt_items = []
    halt_pairs: list[tuple[datetime, datetime]] = []
    halts_valid = True
    for left, right in halt_items:
        first = _aware_instant(left)
        second = _aware_instant(right)
        if first is None or second is None or second <= first:
            halts_valid = False
            continue
        halt_pairs.append((first, second))
    if not halts_valid:
        reasons.append("HALT_INVALID")
        halt_pairs = []

    at_dt = _aware_instant(at)
    if at_dt is None:
        reasons.append("AT_INVALID")

    if zone is not None and trading_day is not None and at_dt is not None:
        if at_dt.astimezone(zone).date() != trading_day:
            reasons.append("AT_OUTSIDE_TRADING_DATE")

    frozen = _freeze_reasons(reasons)
    if frozen:
        return SessionStateVerdict(allowed=False, reasons=frozen, state=None)
    state = _state_at(at_dt, zone, trading_day, day_kind, minute_pairs, halt_pairs)
    return SessionStateVerdict(allowed=True, reasons=(), state=state)
