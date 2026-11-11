"""s1_infoleak.py — the sealed A23 INFO-LEAK predicate (D10).

For a series with BOTH `close` (adjusted total-return close) and `close_price`
(raw close), the adjustment factor is q_t = close_t / close_price_t. A step in
q (|q_t / q_{t-1} - 1| > 1e-6) marks a change of adjustment vintage.

If any step falls on a date >= the earliest TUNE anchor of any protocol using
that series and <= the input vintage (last bar), the adjustment vintage
post-dates the TUNE anchors: TUNE is RETIRED for every protocol using that
series (SL §7 class 3 / SL §8), visibly, via a run-local ledger row plus the
lane manifest. TRAIN is never retired.

Honesty note printed with every retirement: a window return is invariant to a
multiplicative adjustment constant across the window; the leak is the vintage,
not necessarily the value.

HK series carry no raw column: VINTAGE_UNVERIFIABLE — disclosed, NOT retired.
"""
from __future__ import annotations

from datetime import date

STEP_TOLERANCE = 1e-6


def vintage_series(dates: list[date], close: list[float],
                   close_price: list[float]) -> tuple[list[tuple[date, float]], str]:
    """(steps, state). steps = [(date, relative step)] where the adjustment
    factor moves by more than STEP_TOLERANCE. state is OK or
    VINTAGE_UNVERIFIABLE (no usable raw column)."""
    q: list[float] = []
    dOK: list[date] = []
    for d, c, cp in zip(dates, close, close_price):
        if c is None or cp is None or cp != cp or c != c or cp <= 0:
            continue
        q.append(float(c) / float(cp))
        dOK.append(d)
    if len(q) < 2:
        return [], "VINTAGE_UNVERIFIABLE"
    steps = [(dOK[i], abs(q[i] / q[i - 1] - 1.0))
             for i in range(1, len(q))
             if abs(q[i] / q[i - 1] - 1.0) > STEP_TOLERANCE]
    return steps, "OK"


def detect(steps: list[tuple[date, float]], state: str,
           earliest_tune_anchor: date, last_bar: date) -> dict | None:
    """The sealed predicate. None when no offending step exists in
    [earliest_tune_anchor, last_bar], or when the vintage is unverifiable."""
    if state != "OK":
        return None
    offending = [(d, s) for d, s in steps if earliest_tune_anchor <= d <= last_bar]
    if not offending:
        return None
    return {
        "series_state": state,
        "earliest_tune_anchor": earliest_tune_anchor.isoformat(),
        "last_bar": last_bar.isoformat(),
        "first_offending_date": offending[0][0].isoformat(),
        "count_of_steps_in_window": len(offending),
        "count_of_steps_total": len(steps),
        "contamination_class": "information_leak",
    }
