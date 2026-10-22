"""Completed-bar condition evidence for Market Navigator, never a trading signal.

The incumbent price/calendar/source owner supplies complete ordered observations,
a generation identity, a final expected sequence number and a bound verifier.
A single quote cannot prove a cross or sustained hold. Historical gaps or unavailable
revisions abstain; absent owner verification may still be inspected, but no verdict
is emitted. Neither the event mathematics nor a test verifier authenticates a
market feed, proves a historical forecast or licenses a new public data use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Callable
from engine.market_navigator import AUTHORITY, ContractError, HORIZONS, _clock, _number, _ref

_SCHEMA = "market_navigator.price_confirmation/v1"
_EVENTS = frozenset({"cross_above", "cross_below", "hold_above", "hold_below"})
_UNITS = frozenset({"USD", "index_points"})


@dataclass(frozen=True)
class ClosedBar:
    """One owner-supplied price bar. Sequence IDs are owner calendar ordinals.

    No inference from wall-clock adjacency: weekends, holidays, halts and
    time-zone transitions belong to the actual calendar owner.
    """

    subject: str
    horizon: str
    generation_ref: str
    receipt_ref: str
    revision: str
    session_ref: str
    sequence: int
    begins_at: str
    ends_at: str
    available_at: str
    valid_until: str
    open: float
    high: float
    low: float
    close: float
    unit: str
    completed: bool

    def __post_init__(self) -> None:
        for value in (self.subject, self.generation_ref, self.receipt_ref,
                      self.revision, self.session_ref):
            _ref(value)
        if self.horizon not in HORIZONS:
            raise ContractError("unsupported bar horizon")
        if self.unit not in _UNITS or type(self.completed) is not bool:
            raise ContractError("bar must have supported unit and explicit completion")
        if type(self.sequence) is not int or not 0 <= self.sequence < 1_000_000_000:
            raise ContractError("bounded owner calendar sequence required")
        begin, end, avail, expiry = map(
            _clock, (self.begins_at, self.ends_at, self.available_at, self.valid_until))
        if not begin < end <= avail < expiry:
            raise ContractError("invalid bar measurement and availability clocks")
        values = [_number(v) for v in (self.open, self.high, self.low, self.close)]
        if min(values) <= 0 or not values[2] <= min(values[0], values[3]) <= max(values[0], values[3]) <= values[1]:
            raise ContractError("incoherent positive OHLC values")


@dataclass(frozen=True)
class LevelRule:
    """Predeclared conditional observation; original definition must predate query."""

    subject: str
    horizon: str
    event: str
    level: float
    unit: str
    minimum_bars: int
    rule_ref: str
    definition_available_at: str
    deadline: str

    def __post_init__(self) -> None:
        for value in (self.subject, self.rule_ref):
            _ref(value)
        if self.horizon not in HORIZONS or self.event not in _EVENTS:
            raise ContractError("unknown horizon/event")
        if self.unit not in _UNITS or _number(self.level) <= 0:
            raise ContractError("positive level and unit required")
        if type(self.minimum_bars) is not int or not 2 <= self.minimum_bars <= 16:
            raise ContractError("2-16 completed bars required")
        if _clock(self.definition_available_at) >= _clock(self.deadline):
            raise ContractError("rule must predate its deadline")


def inspect(
    *, rule: LevelRule, as_of: str, bars: tuple[ClosedBar, ...],
    expected_last_sequence: int | None = None,
    verify_owner: Callable[[LevelRule, tuple[ClosedBar, ...], int, datetime], bool] | None = None,
) -> dict[str, Any]:
    """Evaluate current contiguous closing prices after a real owner verification.

    The owner verifier must bind the original bar receipts, generation, calendar
    sequence, subject, rights and cutoff. Tests may supply a synthetic verifier;
    an HTTP client/LLM/analyst is NEVER allowed to supply one. A mathematical
    confirmation means only that the defined close relationship held, not that
    the market will continue, or that an options expression has positive expectancy.
    """
    if not isinstance(rule, LevelRule) or type(bars) is not tuple or len(bars) > 64:
        raise ContractError("typed bounded rule and bars required")
    if not all(isinstance(bar, ClosedBar) for bar in bars):
        raise ContractError("bar sequence must be typed")
    cutoff = _clock(as_of)
    if _clock(rule.definition_available_at) > cutoff:
        raise ContractError("rule definition was not known at cutoff")
    if expected_last_sequence is not None and (
            type(expected_last_sequence) is not int or
            not 0 <= expected_last_sequence < 1_000_000_000):
        raise ContractError("owner last sequence must be a bounded integer")
    outcome: dict[str, Any] = {
        "schema": _SCHEMA,
        "subject_binding_sha256": sha256(rule.subject.encode("utf-8")).hexdigest(),
        "horizon": rule.horizon, "event": rule.event,
        "unit": rule.unit, "level": rule.level,
        "definition_ref_sha256": sha256(rule.rule_ref.encode("utf-8")).hexdigest(),
        "definition_available_at": rule.definition_available_at,
        "deadline": rule.deadline, "as_of": cutoff.isoformat().replace("+00:00", "Z"),
        "minimum_bars": rule.minimum_bars, "status": "unresolved",
        "condition_met": None, "source_verified": False,
        "is_trading_signal": False, "probability": None,
        "authority": dict(AUTHORITY),
    }
    if cutoff >= _clock(rule.deadline):
        return outcome | {"status": "expired"}
    required = rule.minimum_bars + (1 if rule.event.startswith("cross_") else 0)
    if len(bars) < required or expected_last_sequence is None:
        return outcome | {"status": "coverage_incomplete"}
    window = bars[-required:]
    if any(bar.subject != rule.subject or bar.horizon != rule.horizon or bar.unit != rule.unit for bar in window):
        return outcome | {"status": "subject_horizon_or_unit_mismatch"}
    generation = window[0].generation_ref
    if any(bar.generation_ref != generation for bar in window):
        return outcome | {"status": "mixed_generation"}
    if any(left.sequence + 1 != right.sequence or _clock(left.ends_at) > _clock(right.begins_at)
           for left, right in zip(window, window[1:])):
        return outcome | {"status": "noncontiguous_owner_sequence"}
    if window[-1].sequence != expected_last_sequence:
        return outcome | {"status": "latest_expected_bar_missing"}
    if rule.horizon == "intraday" and any(bar.session_ref != window[0].session_ref for bar in window):
        return outcome | {"status": "intraday_session_boundary"}
    if any(not bar.completed or _clock(bar.ends_at) > cutoff for bar in window):
        return outcome | {"status": "incomplete_bar"}
    if any(_clock(bar.available_at) > cutoff for bar in window):
        return outcome | {"status": "not_yet_available"}
    if any(_clock(bar.valid_until) <= cutoff for bar in window):
        return outcome | {"status": "expired_source_revision"}
    if not callable(verify_owner):
        return outcome | {"status": "owner_verification_missing"}
    try:
        qualified = verify_owner(rule, window, expected_last_sequence, cutoff)
    except (ValueError, TypeError, PermissionError, OSError, RuntimeError):
        qualified = False
    if qualified is not True:
        return outcome | {"status": "owner_verification_failed"}
    closes = [bar.close for bar in window]
    trailing = closes[-rule.minimum_bars:]
    if rule.event in ("cross_above", "hold_above"):
        held = all(price > rule.level for price in trailing)
        met = held and (
            rule.event == "hold_above" or closes[0] <= rule.level
        )
    else:
        held = all(price < rule.level for price in trailing)
        met = held and (
            rule.event == "hold_below" or closes[0] >= rule.level
        )
    return outcome | {
        "status": "confirmed" if met else "not_confirmed",
        "condition_met": met,
        "source_verified": True,
        "first_qualified_bar_end": window[0].ends_at,
        "last_qualified_bar_end": window[-1].ends_at,
        "bar_count": len(window),
        "generation_sha256": sha256(generation.encode("utf-8")).hexdigest(),
    }


def qualified_observation(
    *, rule: LevelRule, as_of: str, bars: tuple[ClosedBar, ...],
    expected_last_sequence: int, verify_owner: Callable[[LevelRule, tuple[ClosedBar, ...], int, datetime], bool],
    receipt: "Receipt", key: str,
) -> "Observation | None":
    """Feed a Boolean *condition fact* into the existing scenario compositor.

    1.0/0.0 is a binary, dimensionless event observation (unit='ratio'), not
    an estimated chance. Only returns it after verifying the source slice and
    binding the new incumbent-issued receipt to the last measured bar, the
    exact source generation and a non-extended availability/expiry window.

    The application owns BOTH verifier and receipt. Neither may originate
    from user text, a request parameter, an AI model or untrusted metadata.
    If any part of that chain is missing, return None or fail closed.
    """
    from engine.market_navigator import Observation, Receipt, _id

    _id(key)
    if not isinstance(receipt, Receipt):
        raise ContractError("typed owner-issued derived receipt required")
    result = inspect(
        rule=rule, as_of=as_of, bars=bars,
        expected_last_sequence=expected_last_sequence, verify_owner=verify_owner)
    if result["status"] not in {"confirmed", "not_confirmed"} or not result["source_verified"]:
        return None
    required = rule.minimum_bars + (1 if rule.event.startswith("cross_") else 0)
    window = bars[-required:]
    if (_clock(receipt.observed_at) != _clock(window[-1].ends_at) or
            receipt.revision != window[-1].generation_ref or
            _clock(receipt.available_at) < max(_clock(bar.available_at) for bar in window) or
            _clock(receipt.valid_until) > min(_clock(bar.valid_until) for bar in window)):
        raise ContractError("derived receipt cannot revise or outlive qualified bar evidence")
    if receipt.disposition(_clock(as_of)) != "current":
        return None
    return Observation(
        key=key, subject=rule.subject, family="price",
        value=1.0 if result["condition_met"] else 0.0,
        unit="ratio", horizons=(rule.horizon,), receipt=receipt,
        quality="observed",
    )
