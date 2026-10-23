"""Strict one-minute resolver for an ambiguous five-minute barrier interval.

This module is a PURE CONSUMER of the existing ``SessionTape`` contract.  It
opens no network client, reads/writes no file, owns no cache/store/lifecycle,
and emits no entry event.  Its one job is to answer a narrow research question:
when a five-minute OHLC bar touched BOTH a long target and adverse threshold,
can a COMPLETE, positive-volume one-minute tape determine which came first?

Fail-closed law: missing, duplicate, unordered, wrong-basis, zero-volume, or
malformed minute evidence returns ``unavailable``.  The resolver also requires a
non-empty source vintage, but a SessionTape carries no historical acquisition/
availability receipt; every result therefore states ``source_clock_proven=False``
and ``source_evidence_class=availability_time_unproven``.  Mathematical minute
bar close is not proof the vendor delivered that observation by that instant.
The resolver never fills a missing minute, sorts a broken tape, or chooses a flattering order.  If both
barriers are touched inside one minute and that minute opens between them, the
answer remains ``same_minute_ambiguous``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from engine.entry_radar import challengers as ch
from engine.session_digest import session_window_et

WINDOW_MINUTES = 5
AUTHORITY = "research_resolution_only"
SOURCE_EVIDENCE_CLASS = "availability_time_unproven"


class MinuteResolutionError(ValueError):
    """Caller supplied an invalid resolver contract, not uncertain market data."""


@dataclass(frozen=True, slots=True)
class MinuteResolution:
    status: str
    reason: str | None
    event_minute_start: datetime | None
    minutes_inspected: int
    complete_window: bool
    source_vintage: str
    price_basis: str
    interval_start: datetime
    interval_end: datetime
    entry: float
    target: float
    adverse: float
    source_clock_proven: bool = field(default=False, init=False)
    source_evidence_class: str = field(default=SOURCE_EVIDENCE_CLASS, init=False)
    authority: str = field(default=AUTHORITY, init=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "event_minute_start": (
                None if self.event_minute_start is None
                else self.event_minute_start.isoformat()
            ),
            "minutes_inspected": self.minutes_inspected,
            "complete_window": self.complete_window,
            "source_vintage": self.source_vintage,
            "price_basis": self.price_basis,
            "interval_start": self.interval_start.isoformat(),
            "interval_end": self.interval_end.isoformat(),
            "entry": self.entry,
            "target": self.target,
            "adverse": self.adverse,
            "source_clock_proven": self.source_clock_proven,
            "source_evidence_class": self.source_evidence_class,
            "authority": self.authority,
        }


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _contract(interval_start: datetime, interval_end: datetime,
              entry: float, target: float, adverse: float) -> None:
    if interval_start.tzinfo is None or interval_end.tzinfo is None:
        raise MinuteResolutionError("timezone_aware_interval_required")
    if interval_end - interval_start != timedelta(minutes=WINDOW_MINUTES):
        raise MinuteResolutionError("exact_five_minute_interval_required")
    if not all(_finite(x) and float(x) > 0 for x in (entry, target, adverse)):
        raise MinuteResolutionError("finite_positive_barriers_required")
    if not float(adverse) < float(entry) < float(target):
        raise MinuteResolutionError("long_barrier_order_required")


def _unavailable(tape: ch.SessionTape, *, reason: str,
                 interval_start: datetime, interval_end: datetime,
                 entry: float, target: float, adverse: float,
                 minutes_inspected: int = 0) -> MinuteResolution:
    return MinuteResolution(
        status="unavailable", reason=reason, event_minute_start=None,
        minutes_inspected=minutes_inspected, complete_window=False,
        source_vintage=tape.vintage, price_basis=tape.price_basis,
        interval_start=interval_start, interval_end=interval_end,
        entry=float(entry), target=float(target), adverse=float(adverse),
    )


def _valid_ohlcv(bar: ch.MinuteBar) -> bool:
    vals = (bar.open, bar.high, bar.low, bar.close, bar.volume)
    if not all(_finite(x) for x in vals):
        return False
    o, h, low, c, v = map(float, vals)
    return (
        min(o, h, low, c) > 0
        and v >= 0
        and low <= min(o, c) <= max(o, c) <= h
    )


def resolve_long_barrier_order(
    tape: ch.SessionTape,
    *,
    interval_start: datetime,
    interval_end: datetime,
    entry: float,
    target: float,
    adverse: float,
) -> MinuteResolution:
    """Resolve target-vs-adverse order inside one five-minute interval.

    A result other than ``unavailable`` requires exactly the five minute bars
    starting at ``interval_start + {0,1,2,3,4}m`` in that order, with positive
    volume and valid OHLC.  This is deliberately stricter than a charting use of
    sparse aggregate bars: a missing minute before a visible hit makes the hit
    order unknowable.
    """
    _contract(interval_start, interval_end, entry, target, adverse)
    if not str(tape.vintage).strip():
        return _unavailable(
            tape, reason="source_vintage_missing",
            interval_start=interval_start, interval_end=interval_end,
            entry=entry, target=target, adverse=adverse,
        )
    if tape.price_basis != ch.BASIS_ADJUSTED:
        return _unavailable(
            tape, reason="price_basis_mismatch",
            interval_start=interval_start, interval_end=interval_end,
            entry=entry, target=target, adverse=adverse,
        )
    session_open, session_close = session_window_et(tape.session)
    if interval_start < session_open or interval_end > session_close:
        return _unavailable(
            tape, reason="interval_outside_tape_session",
            interval_start=interval_start, interval_end=interval_end,
            entry=entry, target=target, adverse=adverse,
        )
    offset_seconds = (interval_start - session_open).total_seconds()
    if offset_seconds % (WINDOW_MINUTES * 60) != 0:
        raise MinuteResolutionError("session_five_minute_grid_required")

    window = tuple(
        bar for bar in tape.minutes
        if interval_start <= bar.start < interval_end
    )
    starts = [bar.start for bar in window]
    if any(a >= b for a, b in zip(starts, starts[1:])):
        return _unavailable(
            tape, reason="unordered_or_duplicate_minutes",
            interval_start=interval_start, interval_end=interval_end,
            entry=entry, target=target, adverse=adverse,
        )

    expected = [interval_start + timedelta(minutes=i) for i in range(WINDOW_MINUTES)]
    if starts != expected:
        return _unavailable(
            tape, reason="incomplete_minute_window",
            interval_start=interval_start, interval_end=interval_end,
            entry=entry, target=target, adverse=adverse,
        )

    for i, bar in enumerate(window, start=1):
        if not _valid_ohlcv(bar):
            return _unavailable(
                tape, reason="invalid_minute_ohlcv",
                interval_start=interval_start, interval_end=interval_end,
                entry=entry, target=target, adverse=adverse,
                minutes_inspected=i - 1,
            )
        if float(bar.volume) <= 0:
            return _unavailable(
                tape, reason="nonpositive_volume_minute",
                interval_start=interval_start, interval_end=interval_end,
                entry=entry, target=target, adverse=adverse,
                minutes_inspected=i - 1,
            )

    for i, bar in enumerate(window, start=1):
        o, h, low = float(bar.open), float(bar.high), float(bar.low)
        hit_target = h >= float(target)
        hit_adverse = low <= float(adverse)
        if hit_target and hit_adverse:
            if o >= float(target):
                status, reason = "target_first", "minute_open_at_or_beyond_target"
            elif o <= float(adverse):
                status, reason = "adverse_first", "minute_open_at_or_beyond_adverse"
            else:
                status, reason = "same_minute_ambiguous", "both_touched_inside_same_minute"
            return MinuteResolution(
                status=status, reason=reason, event_minute_start=bar.start,
                minutes_inspected=i, complete_window=True,
                source_vintage=tape.vintage, price_basis=tape.price_basis,
                interval_start=interval_start, interval_end=interval_end,
                entry=float(entry), target=float(target), adverse=float(adverse),
            )
        if hit_target:
            return MinuteResolution(
                status="target_first", reason="target_touched",
                event_minute_start=bar.start, minutes_inspected=i,
                complete_window=True, source_vintage=tape.vintage,
                price_basis=tape.price_basis, interval_start=interval_start,
                interval_end=interval_end, entry=float(entry),
                target=float(target), adverse=float(adverse),
            )
        if hit_adverse:
            return MinuteResolution(
                status="adverse_first", reason="adverse_touched",
                event_minute_start=bar.start, minutes_inspected=i,
                complete_window=True, source_vintage=tape.vintage,
                price_basis=tape.price_basis, interval_start=interval_start,
                interval_end=interval_end, entry=float(entry),
                target=float(target), adverse=float(adverse),
            )

    return MinuteResolution(
        status="neither", reason=None, event_minute_start=None,
        minutes_inspected=WINDOW_MINUTES, complete_window=True,
        source_vintage=tape.vintage, price_basis=tape.price_basis,
        interval_start=interval_start, interval_end=interval_end,
        entry=float(entry), target=float(target), adverse=float(adverse),
    )


__all__ = [
    "AUTHORITY", "SOURCE_EVIDENCE_CLASS", "MinuteResolution", "MinuteResolutionError", "WINDOW_MINUTES",
    "resolve_long_barrier_order",
]
