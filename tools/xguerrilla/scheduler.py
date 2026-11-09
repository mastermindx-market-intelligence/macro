"""Scheduling (§26.4): when a child acts is part of the identity, not an afterthought.

Two things are drawn here and nothing else: whether today is an idle day, and
the gap between actions. Gaps are lognormal with a 62-minute median and cv 0.55
— long quiet stretches, occasional bursts, no period. Idle days and gaps are
both derived from the persona seed, so a fixed seed replays the same day
exactly, which is what makes the tests assertable.

All times are timezone-aware in the persona's zone; a naive `now` is read as
already being in that zone.
"""
from __future__ import annotations
import math
import random
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

GAP_MEDIAN_MIN = 62.0
GAP_CV = 0.55
MAX_IDLE_SKIP_DAYS = 14
MIN_GAP_MIN = 0.5


def _lognormal(rng: random.Random, median: float, cv: float) -> float:
    """Draw with the requested median and coefficient of variation.

    mu is log(median) — the median of a lognormal is exp(mu). (The keystroke
    model in typing.py mean-matches instead; cadence is stated in medians, so
    here the median is what has to be true.)
    """
    sigma = math.sqrt(math.log1p(cv * cv))
    return rng.lognormvariate(math.log(median), sigma)


def _tz(persona) -> ZoneInfo:
    return ZoneInfo(persona.tz)


def _day_rng(persona, day: date, salt: str, extra: str = "") -> random.Random:
    return random.Random(f"{persona.handle}:{persona.seed}:{salt}:{day.isoformat()}{extra}")


def _is_idle(persona, day: date) -> bool:
    p = float(getattr(persona, "idle_day_p", 0.0) or 0.0)
    if p <= 0.0:
        return False
    if p >= 1.0:
        return True
    return _day_rng(persona, day, "idle").random() < p


def _window(persona, day: date) -> tuple[datetime, datetime]:
    """[start, end) in local time. hours=(8, 23) means 08:00 up to but not incl. 23:00."""
    tz = _tz(persona)
    start_h, end_h = persona.hours
    start = datetime.combine(day, time(int(start_h)), tzinfo=tz)
    if int(end_h) >= 24:
        end = datetime.combine(day + timedelta(days=1), time(0), tzinfo=tz)
    else:
        end = datetime.combine(day, time(int(end_h)), tzinfo=tz)
    return start, end


def _next_open(persona, day: date) -> datetime:
    """First window start on `day` or later that is not an idle day."""
    for _ in range(MAX_IDLE_SKIP_DAYS + 1):
        if not _is_idle(persona, day):
            return _window(persona, day)[0]
        day = day + timedelta(days=1)
    return _window(persona, day)[0]


def _localise(now: datetime, persona) -> datetime:
    return now.astimezone(_tz(persona)) if now.tzinfo else now.replace(tzinfo=_tz(persona))


def next_run(persona, now: datetime, rng: random.Random | None = None) -> datetime:
    """The next action time for this persona after `now`.

    Outside hours, or on an idle day, the answer is the next window start rather
    than a time that leaks activity into the persona's night.
    """
    local = _localise(now, persona)
    day = local.date()
    rng = rng or _day_rng(persona, day, "gap", extra=f":{local.isoformat()}")
    start, end = _window(persona, day)

    if local < start:
        return _next_open(persona, day)
    if local >= end or _is_idle(persona, day):
        return _next_open(persona, day + timedelta(days=1))

    candidate = local + timedelta(minutes=_lognormal(rng, GAP_MEDIAN_MIN, GAP_CV))
    if candidate >= end:
        # The gap ran past closing time; the child picks it up tomorrow.
        return _next_open(persona, day + timedelta(days=1))
    return candidate


def plan_day(persona, day: date, rng: random.Random | None = None,
             *, honour_idle: bool = False) -> list[datetime]:
    """Exactly `persona.actions_per_day` slots for `day`, monotonic, inside hours.

    The same lognormal gap model is drawn between slots; when the day's window
    is too short to hold the raw gaps they are scaled down together, which keeps
    the shape (short gaps stay short) while guaranteeing the window fits.

    `honour_idle=True` returns [] for an idle day. It is off by default so the
    count contract holds unconditionally; callers that own the calendar pass it.
    """
    n = int(persona.actions_per_day)
    if n <= 0:
        return []
    start, end = _window(persona, day)
    if honour_idle and _is_idle(persona, day):
        return []

    rng = rng or _day_rng(persona, day, "plan")
    avail = max((end - start).total_seconds() / 60.0 - 1.0, MIN_GAP_MIN)
    # How long after the window opens the child shows up. Without this every
    # packed day would start at exactly 08:00:00, which is its own tell.
    lead = rng.uniform(0.0, min(20.0, avail * 0.15))
    tail = rng.uniform(0.0, min(25.0, avail * 0.10))   # stops ending on the 22:59 bell
    gaps = [max(MIN_GAP_MIN, _lognormal(rng, GAP_MEDIAN_MIN, GAP_CV)) for _ in range(n - 1)]
    total = sum(gaps)
    scale = min(1.0, (avail - lead - tail) / total) if total > 0 else 0.0

    t = start + timedelta(minutes=lead)
    out = [t]
    for g in gaps:
        t = t + timedelta(minutes=g * scale)
        out.append(t)
    return out
