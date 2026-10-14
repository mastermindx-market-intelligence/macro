"""SNI-local DRAFT comparison-guard contract (A13 stale-FX / closed-market / proxy).

This module is an SNI-local DRAFT contract. It CONSUMES owner-supplied
price, FX, and instrument-role records. It does not re-implement Data OS
identity, Company Event/Earnings, FIF, Capital Structure, Stock Identity,
Options, Research Vault, or qledger/Evaluation. Identity ids are
caller-supplied opaque strings owned by Stock Identity / Data OS; this
guard never mints, derives, or guesses canonical HK/US issuer or security
identifiers from a ticker, name, code, or CIK. Unknown identity stays
UNRESOLVED / null. The guard never mints, derives, or guesses canonical
identifiers, FX rates, session states, or instrument roles. Session state
and instrument role are FIELDS supplied by the caller; the guard never
computes them from a clock, calendar, ticker, code, exchange, or name.

DRAFT, not wired into any owner or pipeline. It does not fetch, store,
normalise, convert, or repair anything. A contemporaneous cross-listing
price comparison is refused, not fixed, when the FX rate is stale relative
to either price, when either price was struck in a non-trading session
state, or when a proxy instrument is presented as the target instrument.
A basket ETF proxy is never a quote for a single issuer: proxy stays
proxy by the instrument_role field, never by ticker.

Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade path.
Every authority flag is literal false. A caller that tries to set any of
them true is refused (raise). Residuals and stress statistics stay
descriptive; this guard makes no causal or news-impact claim (A24). An
unestimable family is outside this module; the guard never invents a
default 50/50 (A25). This is a descriptive refusal contract, not a signal
or forecast.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timezone
from types import MappingProxyType
from typing import Mapping

REASONS: tuple[str, ...] = (
    "PRICE_MISSING",
    "PRICE_TS_MISSING",
    "PRICE_NONFINITE",
    "SESSION_STATE_UNKNOWN",
    "SESSION_NOT_TRADING",
    "FX_MISSING",
    "FX_TS_MISSING",
    "FX_NONFINITE",
    "FX_STALE",
    "PRICE_SKEW",
    "CURRENCY_PAIR_MISMATCH",
    "ROLE_UNKNOWN",
    "PROXY_AS_TARGET",
    "ISSUER_MISMATCH",
    "NOT_KNOWN_AS_OF",
)

SESSION_STATES_TRADING: tuple[str, ...] = (
    "continuous",
    "closing_auction",
)

SESSION_STATES_KNOWN: tuple[str, ...] = (
    "pre_open",
    "continuous",
    "lunch_break",
    "closing_auction",
    "closed",
    "halted",
    "suspended",
    "holiday",
)

INSTRUMENT_ROLES: tuple[str, ...] = (
    "target",
    "proxy",
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

_SESSION_KNOWN = frozenset(SESSION_STATES_KNOWN)
_SESSION_TRADING = frozenset(SESSION_STATES_TRADING)
_ROLES = frozenset(INSTRUMENT_ROLES)


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
class ComparisonVerdict:
    """Descriptive comparison refusal. Carries no converted price or forecast."""

    allowed: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        refuse_nonfalse_authority()
        ordered = tuple(code for code in REASONS if code in self.reasons)
        object.__setattr__(self, "reasons", ordered)
        object.__setattr__(self, "allowed", not ordered)

    @property
    def authority_flags(self) -> Mapping[str, bool]:
        return AUTHORITY_FLAGS


def _text_present(value: object) -> bool:
    """A field documented as an id, ref, code, label, owner reference or
    other opaque text counts as present ONLY when ``_text_present`` is True.

    The seat's FAMILY TEXT RULE — rejects ``None``, empty string, whitespace-only,
    leading/trailing whitespace, and non-str (int, float, bool, bytes, list,
    dict, set, etc.). Equality between two caller-supplied ids is evaluated
    only after both sides pass ``_text_present``; a non-text side is ABSENT
    (its *_MISSING-style reason) and never equals anything. Unhashable values
    never raise from a public guard function.
    """
    return (
        isinstance(value, str)
        and value != ""
        and not value[0].isspace()
        and not value[-1].isspace()
    )


def _blank(value: object) -> bool:
    """Legacy blank-check used for the numeric ``price`` slot only.

    Fields documented as ids / refs / codes / labels route through
    ``_text_present`` instead, per the seat's FAMILY TEXT RULE.
    """
    if value is None:
        return True
    if value == "":
        return True
    return False


def _present(fact: Mapping[str, object], key: str) -> bool:
    return _text_present(fact.get(key))


def _as_date(text: object) -> date | None:
    if not isinstance(text, str) or len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _as_datetime(text: object) -> datetime | None:
    if not isinstance(text, str) or text == "":
        return None
    if len(text) == 10:
        parsed = _as_date(text)
        if parsed is None:
            return None
        return datetime(parsed.year, parsed.month, parsed.day)
    body = text
    if body.endswith("Z"):
        body = body[:-1]
    try:
        return datetime.fromisoformat(body)
    except ValueError:
        return None


def _as_aware_datetime(text: object) -> datetime | None:
    """Parse ISO-8601 into a timezone-aware datetime. Naive/unparseable → None."""
    if not isinstance(text, str) or text == "":
        return None
    zulu = text.endswith("Z")
    parsed = _as_datetime(text)
    if parsed is None:
        return None
    if zulu and parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return None
    return parsed


def _finite_positive_real(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return value > 0
    if isinstance(value, float):
        return math.isfinite(value) and value > 0.0
    return False


def _freeze_reasons(items: list[str]) -> tuple[str, ...]:
    present = set(items)
    return tuple(code for code in REASONS if code in present)


def _not_known_as_of(known_at: object, as_of: object) -> bool:
    known_dt = _as_aware_datetime(known_at)
    as_of_dt = _as_aware_datetime(as_of)
    if known_dt is None or as_of_dt is None:
        return True
    return known_dt > as_of_dt


def _leg_reasons(
    leg: Mapping[str, object],
    *,
    as_of: str,
    requested_role: str,
) -> list[str]:
    found: list[str] = []
    price = leg.get("price")
    if _blank(price):
        found.append("PRICE_MISSING")
    elif not _finite_positive_real(price):
        found.append("PRICE_NONFINITE")
    if _as_aware_datetime(leg.get("price_ts")) is None:
        found.append("PRICE_TS_MISSING")
    session_state = leg.get("session_state")
    if not isinstance(session_state, str) or session_state not in _SESSION_KNOWN:
        found.append("SESSION_STATE_UNKNOWN")
    elif session_state not in _SESSION_TRADING:
        found.append("SESSION_NOT_TRADING")
    role = leg.get("instrument_role")
    if not isinstance(role, str) or role not in _ROLES:
        found.append("ROLE_UNKNOWN")
    elif _text_present(requested_role) and _text_present(role) and requested_role == "target" and role == "proxy":
        found.append("PROXY_AS_TARGET")
    if _not_known_as_of(leg.get("known_at"), as_of):
        found.append("NOT_KNOWN_AS_OF")
    return found


def _fx_reasons(
    left: Mapping[str, object],
    right: Mapping[str, object],
    fx: Mapping[str, object] | None,
    *,
    as_of: str,
    max_fx_staleness_seconds: int,
) -> list[str]:
    left_ccy = left.get("currency")
    right_ccy = right.get("currency")
    if _text_present(left_ccy) and _text_present(right_ccy) and left_ccy == right_ccy:
        return []
    found: list[str] = []
    if fx is None:
        found.append("FX_MISSING")
        return found
    if not isinstance(fx, Mapping):
        raise TypeError("fx must be a Mapping or None")
    rate = fx.get("rate")
    if not _finite_positive_real(rate):
        found.append("FX_NONFINITE")
    rate_ts = _as_aware_datetime(fx.get("rate_ts"))
    if rate_ts is None:
        found.append("FX_TS_MISSING")
    base = fx.get("base")
    quote = fx.get("quote")
    if (
        not _text_present(base)
        or not _text_present(quote)
        or not _text_present(left_ccy)
        or not _text_present(right_ccy)
        or {base, quote} != {left_ccy, right_ccy}
    ):
        found.append("CURRENCY_PAIR_MISMATCH")
    if rate_ts is not None:
        for leg in (left, right):
            price_ts = _as_aware_datetime(leg.get("price_ts"))
            if price_ts is None:
                continue
            age = abs((rate_ts - price_ts).total_seconds())
            if age > max_fx_staleness_seconds:
                found.append("FX_STALE")
                break
    if _not_known_as_of(fx.get("known_at"), as_of):
        found.append("NOT_KNOWN_AS_OF")
    return found


def check_comparison(
    left: Mapping,
    right: Mapping,
    fx: Mapping | None,
    *,
    as_of: str,
    max_fx_staleness_seconds: int = 300,
    max_price_skew_seconds: int = 60,
    requested_role: str = "target",
) -> ComparisonVerdict:
    """Refuse a contemporaneous cross-listing price comparison when FX is
    stale, a session is not trading, a proxy is presented as the target,
    or another named contract defect is present.

    Reports every applicable reason, de-duplicated, in REASONS order.
    Never short-circuits. Does not convert, repair, or forecast.
    """
    refuse_nonfalse_authority()
    if not isinstance(left, Mapping):
        raise TypeError("left must be a Mapping")
    if not isinstance(right, Mapping):
        raise TypeError("right must be a Mapping")
    if fx is not None and not isinstance(fx, Mapping):
        raise TypeError("fx must be a Mapping or None")
    reasons: list[str] = []
    reasons.extend(
        _leg_reasons(left, as_of=as_of, requested_role=requested_role)
    )
    reasons.extend(
        _leg_reasons(right, as_of=as_of, requested_role=requested_role)
    )
    left_iss = left.get("issuer_id")
    right_iss = right.get("issuer_id")
    if (
        not _text_present(left_iss)
        or not _text_present(right_iss)
        or left_iss != right_iss
    ):
        reasons.append("ISSUER_MISMATCH")
    reasons.extend(
        _fx_reasons(
            left,
            right,
            fx,
            as_of=as_of,
            max_fx_staleness_seconds=max_fx_staleness_seconds,
        )
    )
    left_ts = _as_aware_datetime(left.get("price_ts"))
    right_ts = _as_aware_datetime(right.get("price_ts"))
    if left_ts is not None and right_ts is not None:
        skew = abs((left_ts - right_ts).total_seconds())
        if skew > max_price_skew_seconds:
            reasons.append("PRICE_SKEW")
    frozen = _freeze_reasons(reasons)
    return ComparisonVerdict(allowed=not frozen, reasons=frozen)