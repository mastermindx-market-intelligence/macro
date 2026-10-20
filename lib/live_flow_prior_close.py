"""Prior-session close selector for the live Options Flow reader.

The reader needs the close of the NYSE session BEFORE a given session date,
from the dual-basis yahoo store:

  * ``close``       — split+dividend adjusted (total return);
  * ``close_price`` — split-adjusted, dividend-UNadjusted.

Flow moneyness relative to the prior close must use
``close_price``: a dividend-adjusted prior close silently shifts every level
by the accumulated dividend factor.  This module reads ``close_price`` ONLY —
there is no fallback to ``close``.

PURE by contract: no IO, no network, no git, no module state; the existing
``lib.nyse_calendar`` is reused, not extended.  Exactly two output paths: a
float, or ``None`` meaning "unknown", which leaves the reader's existing
unknown-close fallback in charge.  Every malformed input — invalid session
date, bad index, missing column, stale/missing/duplicate expected row,
non-numeric, non-finite or non-positive value — degrades to ``None``; the
selector never raises and never guesses.

The expected prior session is
``nyse_calendar.last_session_on_or_before(session_date - 1 day)``: the
calendar, not ``iloc[-1]``, decides which row is "the prior close", so
out-of-order rows and same-day or future rows cannot redirect the answer.
"""

from __future__ import annotations

import math
import numbers
import re
from datetime import date, timedelta

import numpy as np
import pandas as pd

from lib import nyse_calendar

__all__ = ["select_prior_close"]


def select_prior_close(frame: pd.DataFrame, session_date: str) -> float | None:
    """Close (dividend-unadjusted ``close_price``) of the session before
    ``session_date``, or ``None`` when it cannot be determined.

    ``session_date`` must be an ISO date that is itself an NYSE session.  The
    expected prior session is the last session strictly before it (weekend and
    holiday gaps skipped by the calendar).  The frame must carry a
    timezone-naive DatetimeIndex and hold EXACTLY ONE row for the expected
    date, whose ``close_price`` is a finite, strictly positive, non-boolean
    real number (pandas' native numeric dtypes).  Any other shape — stale or
    missing row, duplicate expected date, future-only store, adjusted-basis
    frame, non-numeric or non-positive value, bad index, invalid session date
    — is ``None``.
    """
    wanted = _parse_session_date(session_date)
    if wanted is None:
        return None

    try:
        expected = nyse_calendar.last_session_on_or_before(
            wanted - timedelta(days=1))
    except (ValueError, OverflowError):
        # Calendar rules broken (no session in its 30-day lookback) — an
        # honest unknown, never a guess.
        return None

    index = getattr(frame, "index", None)
    if not isinstance(index, pd.DatetimeIndex) or index.tz is not None:
        return None
    if index.hasnans or not index.equals(index.normalize()):
        return None
    if "close_price" not in getattr(frame, "columns", ()):
        return None

    # Match by DATE VALUE, not position: an out-of-order store, and rows for
    # the session itself or later, must not influence the prior close.
    try:
        rows = frame[index == pd.Timestamp(expected)]
        if len(rows) != 1:
            return None     # 0 = stale/missing, >1 = duplicate expected date
        value = rows["close_price"].iloc[0]
    except Exception:  # noqa: BLE001 — malformed frame degrades to unknown
        return None

    if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Real):
        return None
    try:
        close = float(value)
    except (TypeError, ValueError, OverflowError):   # exotic numeric subtype
        return None
    if not math.isfinite(close) or close <= 0.0:
        return None
    return close


def _parse_session_date(raw: str) -> date | None:
    """ISO string -> date, but only when that date is itself an NYSE session."""
    if not isinstance(raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None
    try:
        wanted = date.fromisoformat(raw)
    except ValueError:
        return None
    if not nyse_calendar.is_session(wanted):
        return None
    return wanted
