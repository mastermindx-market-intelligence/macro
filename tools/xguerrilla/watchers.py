"""Watchers (§26.4): reacting to what came at the child, at a human's pace.

Delay is drawn per kind, because the plausible latency differs: a follow or a
mention is a notification and gets looked at quickly; a like on someone else's
post is idle scrolling and can wait half an hour. Weighting follows the same
logic — directed events rank above ambient ones — and the budget is a hard
ceiling, since "reactive but steady" is the only shape that survives review.
"""
from __future__ import annotations
import heapq
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

KINDS = ("follow", "reply", "mention", "quote", "like")
WEIGHT = {"follow": 5, "mention": 5, "reply": 4, "quote": 3, "like": 2}
# Median minutes to react, by kind. Follow/mention quicker than like, as
# notification latency and idle-scroll latency are not the same behaviour.
DELAY_MEDIAN_MIN = {"follow": 7.0, "mention": 8.0, "reply": 14.0, "quote": 18.0, "like": 26.0}
DELAY_CV = 0.50
FLOOR_S = 4 * 60
CEIL_S = 90 * 60
MAX_AGE_H = 36


@dataclass(frozen=True)
class Event:
    kind: str
    actor: str
    post_id: str
    at: datetime

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown event kind {self.kind!r}")


def _lognormal(rng: random.Random, median: float, cv: float) -> float:
    """Median-parameterised lognormal (median of the draw is exp(mu))."""
    sigma = math.sqrt(math.log1p(cv * cv))
    return rng.lognormvariate(math.log(median), sigma)


def reaction_delay(rng: random.Random, kind: str) -> int:
    """Seconds to wait before reacting. Clamped to 4-90 minutes."""
    if kind not in DELAY_MEDIAN_MIN:
        raise ValueError(f"unknown event kind {kind!r}")
    draw = _lognormal(rng, DELAY_MEDIAN_MIN[kind] * 60.0, DELAY_CV)
    return int(min(CEIL_S, max(FLOOR_S, round(draw))))


@dataclass
class ReactionBudget:
    max_per_day: int = 8
    max_per_hour: int = 2

    def allow(self, now: datetime, spent_today: int, spent_last_hour: int) -> bool:
        return spent_today < self.max_per_day and spent_last_hour < self.max_per_hour

    def pay(self, heap: list, now: datetime | None = None) -> list:
        """Record one reaction at `now` on a heap of epoch seconds; prunes >24h."""
        stamp = _epoch(now or datetime.now(timezone.utc))
        heapq.heappush(heap, stamp)
        self.spent(heap, now or datetime.now(timezone.utc))
        return heap

    def spent(self, heap: list, now: datetime) -> tuple[int, int]:
        """(last 24h, last hour) counts, dropping anything older than a day."""
        ref = _epoch(now)
        while heap and heap[0] <= ref - 86400:
            heapq.heappop(heap)
        return sum(1 for t in heap if t > ref - 86400), sum(1 for t in heap if t > ref - 3600)

    def allow_from(self, heap: list, now: datetime) -> bool:
        return self.allow(now, *self.spent(heap, now))


def _epoch(dt: datetime) -> float:
    return (dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)).timestamp()


def select_targets(events, persona, rng: random.Random | None = None,
                   budget: ReactionBudget | None = None, now: datetime | None = None,
                   already_replied: set | None = None) -> list[Event]:
    """Ranked, deduped, budget-bounded batch of events worth a reaction.

    Stale (>36h) and already-answered actors are dropped; duplicates per actor
    collapse to the strongest event. Ranking is kind weight first, recency
    second, with a seeded draw breaking exact ties so the order is assertable.
    """
    budget = budget or ReactionBudget()
    already_replied = set(already_replied or ())
    now = now or datetime.now(timezone.utc)
    rng = rng or persona.rng("watchers")
    cutoff = _epoch(now) - MAX_AGE_H * 3600

    seen_actors: set[str] = set()
    ranked = []
    for ev in events:
        if _epoch(ev.at) < cutoff:
            continue
        if ev.actor in already_replied or ev.post_id in already_replied:
            continue
        if ev.actor in seen_actors:
            continue
        seen_actors.add(ev.actor)
        ranked.append((-WEIGHT[ev.kind], -_epoch(ev.at), rng.random(), ev))

    ranked.sort(key=lambda row: row[:3])
    cap = max(0, min(int(budget.max_per_hour), int(budget.max_per_day)))
    return [row[3] for row in ranked[:cap]]
