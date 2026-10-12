"""SNI-local DRAFT contract for cross-listing session, FX, parity, and bind guards.

This module CONSUMES owner-supplied values. It does not fork or re-implement
Data OS identity, Company Event/Earnings, FIF, Capital Structure, Stock
Identity, Options, Research Vault, or qledger/Evaluation. Identity ids are
caller-supplied opaque strings owned by Stock Identity / Data OS; unknown
identity stays unresolved / null and is never constructed here.

Holidays, halts, FX quotes, prices, and capital versions are caller-supplied.
Session tokens are declared trading-session state only. A residual parity
gap is descriptive (A24), never causal, never a news-impact claim. An
unestimable comparison abstains with a named GuardRefused code (A25); it
never returns a default 50/50.

Every authority flag (rank_authority, gate_authority, size_authority,
signal_authority, escalation_authority, trade_authority) stays false.
Callers who try to set any of them true are refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
from fractions import Fraction
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

AUTHORITY_FLAG_NAMES: tuple[str, ...] = (
    "rank_authority",
    "gate_authority",
    "size_authority",
    "signal_authority",
    "escalation_authority",
    "trade_authority",
)

AUTHORITY_FLAGS_FALSE: dict[str, bool] = {name: False for name in AUTHORITY_FLAG_NAMES}

REFUSAL_CODES: frozenset[str] = frozenset(
    {
        "MARKET_NOT_OPEN",
        "FX_STALE",
        "FX_PAIR_MISMATCH",
        "CAPITAL_VERSION_REQUIRED",
        "CAPITAL_VERSION_NOT_EFFECTIVE",
        "SAME_COUNTER",
        "CROSS_BIND_VENUE_CURRENCY",
        "PADDING_MISMATCH",
        "AUTHORITY_FLAG_FORBIDDEN",
    }
)

_HK_FALLBACK = timezone(timedelta(hours=8))


class GuardRefused(Exception):
    """Named abstain for a comparison that must not be formed."""

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in REFUSAL_CODES:
            raise ValueError(f"unknown refusal code: {code}")
        self.code = code
        super().__init__(detail or code)


class SessionState(Enum):
    OPEN = "OPEN"
    LUNCH = "LUNCH"
    CLOSED = "CLOSED"
    HOLIDAY = "HOLIDAY"
    HALTED = "HALTED"
    UNKNOWN = "UNKNOWN"


VENUES: dict[str, dict] = {
    "XHKG": {
        "tz": "Asia/Hong_Kong",
        "sessions": (("09:30", "12:00"), ("13:00", "16:00")),
        "lunch": ("12:00", "13:00"),
    },
    "XNYS": {
        "tz": "America/New_York",
        "sessions": (("09:30", "16:00"),),
    },
    "XNAS": {
        "tz": "America/New_York",
        "sessions": (("09:30", "16:00"),),
    },
}


def _zone(key: str):
    try:
        return ZoneInfo(key)
    except ZoneInfoNotFoundError:
        if key == "Asia/Hong_Kong":
            return _HK_FALLBACK
        raise


def _hhmm(token: str) -> time:
    hour_s, minute_s = token.split(":")
    return time(int(hour_s), int(minute_s))


def _in_half_open(clock: time, start_token: str, end_token: str) -> bool:
    return _hhmm(start_token) <= clock < _hhmm(end_token)


def _as_fraction(value) -> Fraction:
    if isinstance(value, Fraction):
        return value
    return Fraction(value)


def _require_aware(ts: datetime, label: str) -> datetime:
    if not isinstance(ts, datetime) or ts.tzinfo is None:
        raise ValueError(f"{label} must be a timezone-aware datetime")
    return ts


def refuse_if_authority_true(payload: Mapping | None = None, **flags) -> dict[str, bool]:
    """Return the six flags all False; raise if a caller sets any true."""
    merged: dict = {}
    if payload is not None:
        merged.update(payload)
    merged.update(flags)
    for name in AUTHORITY_FLAG_NAMES:
        if merged.get(name) is True:
            raise GuardRefused(
                "AUTHORITY_FLAG_FORBIDDEN",
                f"{name} must stay false",
            )
    return dict(AUTHORITY_FLAGS_FALSE)


@dataclass(frozen=True)
class Calendar:
    """Caller-supplied holiday and halt fixtures. Not a real exchange calendar."""

    holidays: Mapping[str, frozenset[date]] = field(default_factory=dict)
    halts: tuple = ()

    def __post_init__(self) -> None:
        frozen = {
            str(venue): frozenset(days) for venue, days in dict(self.holidays).items()
        }
        object.__setattr__(self, "holidays", frozen)
        object.__setattr__(self, "halts", tuple(self.halts))


@dataclass(frozen=True)
class FxQuote:
    """Caller-supplied FX quote. Rate is units of quote per one unit of base."""

    base: str
    quote: str
    rate: Fraction
    as_of_utc: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "rate", _as_fraction(self.rate))
        if self.rate <= 0:
            raise ValueError("fx rate must be > 0")
        _require_aware(self.as_of_utc, "fx.as_of_utc")
        object.__setattr__(self, "base", str(self.base))
        object.__setattr__(self, "quote", str(self.quote))


@dataclass(frozen=True)
class CapitalVersion:
    """Consumption record for a Capital Structure ADS/ordinary version.

    version_id is an opaque owner-supplied string. ads_ratio is ordinary
    shares per ADS and is never inferred here.
    """

    version_id: str
    owner: str
    ads_ratio: Fraction
    effective_from_utc: datetime

    def __post_init__(self) -> None:
        if self.owner != "capital_structure":
            raise ValueError("capital version owner must be capital_structure")
        object.__setattr__(self, "ads_ratio", _as_fraction(self.ads_ratio))
        if self.ads_ratio <= 0:
            raise ValueError("ads_ratio must be > 0")
        _require_aware(self.effective_from_utc, "effective_from_utc")
        object.__setattr__(self, "version_id", str(self.version_id))


def session_state(
    venue_mic: str,
    ts_utc: datetime,
    *,
    calendar: Calendar,
    local_code: str | None = None,
) -> SessionState:
    """Declare trading-session state at a UTC instant.

    Naive datetimes raise ValueError. An unknown venue returns UNKNOWN
    (never OPEN). Weekend is CLOSED; a fixture holiday wins (HOLIDAY).
    """
    _require_aware(ts_utc, "ts_utc")
    spec = VENUES.get(venue_mic)
    if spec is None:
        return SessionState.UNKNOWN

    local = ts_utc.astimezone(_zone(spec["tz"]))
    local_day = local.date()
    holidays = calendar.holidays.get(venue_mic, frozenset())
    if local_day in holidays:
        return SessionState.HOLIDAY
    if local.weekday() >= 5:
        return SessionState.CLOSED

    if local_code is not None:
        instant = ts_utc
        for halt_venue, halt_code, halt_start, halt_end in calendar.halts:
            if halt_venue != venue_mic or halt_code != local_code:
                continue
            start = _require_aware(halt_start, "halt start")
            end = _require_aware(halt_end, "halt end")
            if start <= instant < end:
                return SessionState.HALTED

    clock = local.timetz().replace(tzinfo=None)
    lunch = spec.get("lunch")
    if lunch is not None and _in_half_open(clock, lunch[0], lunch[1]):
        return SessionState.LUNCH
    for start_token, end_token in spec["sessions"]:
        if _in_half_open(clock, start_token, end_token):
            return SessionState.OPEN
    return SessionState.CLOSED


def _px_a_in_ccy_b(px_a: Fraction, ccy_a: str, ccy_b: str, fx: FxQuote) -> Fraction:
    pair = {fx.base, fx.quote}
    needed = {ccy_a, ccy_b}
    if pair != needed:
        raise GuardRefused(
            "FX_PAIR_MISMATCH",
            "fx.base/quote must match the two price currencies in either direction",
        )
    if ccy_a == ccy_b:
        return px_a
    if fx.base == ccy_a and fx.quote == ccy_b:
        return px_a * fx.rate
    if fx.base == ccy_b and fx.quote == ccy_a:
        return px_a / fx.rate
    raise GuardRefused(
        "FX_PAIR_MISMATCH",
        "fx.base/quote must match the two price currencies in either direction",
    )


def fx_compare(
    *,
    px_a,
    ccy_a: str,
    px_b,
    ccy_b: str,
    fx: FxQuote,
    as_of_utc: datetime,
    max_age: timedelta,
    state_a: SessionState,
    state_b: SessionState,
) -> Fraction:
    """Descriptive ratio (px_a in ccy_b) / px_b. Refuses unless both legs are OPEN."""
    refuse_if_authority_true()
    as_of = _require_aware(as_of_utc, "as_of_utc")
    if state_a is not SessionState.OPEN or state_b is not SessionState.OPEN:
        raise GuardRefused(
            "MARKET_NOT_OPEN",
            f"both legs must be OPEN (got {state_a.value}, {state_b.value})",
        )
    fx_as_of = _require_aware(fx.as_of_utc, "fx.as_of_utc")
    if fx_as_of > as_of:
        raise GuardRefused("FX_STALE", "fx quote is from the future relative to as_of_utc")
    if (as_of - fx_as_of) > max_age:
        raise GuardRefused("FX_STALE", "fx quote is older than max_age")
    price_a = _as_fraction(px_a)
    price_b = _as_fraction(px_b)
    if price_b == 0:
        raise ValueError("px_b must be non-zero")
    converted = _px_a_in_ccy_b(price_a, str(ccy_a), str(ccy_b), fx)
    return converted / price_b


def ads_ordinary_parity(
    *,
    ads_px,
    ads_ccy: str,
    ord_px,
    ord_ccy: str,
    fx: FxQuote,
    capital: CapitalVersion | None,
    as_of_utc: datetime,
    max_age: timedelta,
    state_ads: SessionState,
    state_ord: SessionState,
) -> dict:
    """Descriptive ADS/ordinary parity gap bound to a Capital Structure version."""
    refuse_if_authority_true()
    if capital is None:
        raise GuardRefused(
            "CAPITAL_VERSION_REQUIRED",
            "ADS/ordinary parity requires a Capital Structure version",
        )
    as_of = _require_aware(as_of_utc, "as_of_utc")
    if capital.effective_from_utc > as_of:
        raise GuardRefused(
            "CAPITAL_VERSION_NOT_EFFECTIVE",
            "capital version is not effective at as_of_utc",
        )
    ratio = fx_compare(
        px_a=ads_px,
        ccy_a=ads_ccy,
        px_b=ord_px,
        ccy_b=ord_ccy,
        fx=fx,
        as_of_utc=as_of,
        max_age=max_age,
        state_a=state_ads,
        state_b=state_ord,
    )
    parity_gap = ratio / capital.ads_ratio - 1
    return {
        "parity_gap": parity_gap,
        "capital_version_id": capital.version_id,
        "fx_as_of_utc": fx.as_of_utc,
        "descriptive_only": True,
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }


def _padding_only(code_a: str, code_b: str) -> bool:
    if code_a == code_b:
        return False
    return code_a.lstrip("0") == code_b.lstrip("0")


def _identity_receipt(receipt: dict | None) -> dict | None:
    if receipt is None:
        return None
    refuse_if_authority_true(receipt)
    if receipt.get("source_owner") == "stock_identity" and receipt.get("receipt_id"):
        return receipt
    return None


def bind_counters(a: dict, b: dict, *, receipt: dict | None = None) -> dict:
    """Bind two counters only with a Stock Identity receipt. Never mints an id."""
    refuse_if_authority_true(a)
    refuse_if_authority_true(b)
    venue_a, code_a, ccy_a = a["venue_mic"], str(a["local_code"]), a["currency"]
    venue_b, code_b, ccy_b = b["venue_mic"], str(b["local_code"]), b["currency"]
    if venue_a == venue_b and code_a == code_b and ccy_a == ccy_b:
        raise GuardRefused("SAME_COUNTER", "a counter cannot bind to itself")
    valid = _identity_receipt(receipt)
    if _padding_only(code_a, code_b) and valid is None:
        raise GuardRefused(
            "PADDING_MISMATCH",
            "leading-zero code variants require a stock_identity receipt",
        )
    if valid is None:
        if venue_a != venue_b or ccy_a != ccy_b:
            raise GuardRefused(
                "CROSS_BIND_VENUE_CURRENCY",
                "venue or currency differ; two counters never auto-bind",
            )
        raise GuardRefused(
            "CROSS_BIND_VENUE_CURRENCY",
            "two counters never auto-bind without a stock_identity receipt",
        )
    return {
        "bound": True,
        "receipt_id": valid["receipt_id"],
        "descriptive_only": True,
        "authority_flags": dict(AUTHORITY_FLAGS_FALSE),
    }
