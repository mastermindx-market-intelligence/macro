"""Bottom Ledger clock contract — ONE lawful date representation for bottom-call capture,
maturity, grading, persistence, CLI ``--as-of`` and historical replay.

WHY THIS MODULE EXISTS
----------------------
The Bottom Ledger's forward advancer (scripts/grade_bottom_calls.py) derived "today" with
``pd.Timestamp.utcnow().normalize()`` — a **tz-aware** UTC timestamp — and compared it against
``pd.Timestamp(flag_date)``, which is **tz-naive** because every producer writes a plain
``YYYY-MM-DD``.  That comparison raises::

    TypeError: Cannot compare tz-naive and tz-aware timestamps

The workflow masked the crash with ``|| true``, so the advancer aborted BEFORE its first write
on every single run and the nightly still reported success.  Result: neither
``data/bottom_ledger/rows.parquet`` nor ``site/factordata/us_bottom_ledger.json`` has ever
existed.  A second, quieter defect had the same root: when a price index and a flag date
disagree on tz-awareness, ``bottom_ruler.grade_call`` resolves NO bar and returns ``None``
silently, so rows would accrue forever and never mature with no error at all.

The repair is not "strip the timezone at the crashing line".  It is: there is exactly one
date representation in this instrument, every boundary converts into it, and a value that
cannot be converted is REJECTED loudly instead of silently producing a wrong answer.

THE CONTRACT
------------
A **ledger date** is a *civil calendar date* — no clock, no timezone.

  * wire / persisted form : ``YYYY-MM-DD`` (str)
  * in-process form       : ``pd.Timestamp``, tz-naive, normalized to midnight

PROOF THAT DATE-ONLY IS THE INTENDED SEMANTIC CONTRACT (measured on real production data,
2026-09-18, not asserted):

  1. Every producer emits date-only.  ``data/us_board_ledger/snapshots.jsonl``: 41/41 ``as_of``
     values match ``YYYY-MM-DD``.  ``site/prophet/plans/*.json``: 422 plans, and every
     ``signal_date`` / ``observed_date`` / ``price_basis_date`` / ``entry_date`` present is
     ``YYYY-MM-DD``.  No producer has ever written a clock or an offset.
  2. Every price series is date-only: ``data/stocks/*.parquet`` and ``data/yahoo/*.parquet``
     carry a tz-naive, midnight-normalized ``DatetimeIndex`` — exchange **session dates**, not
     instants.
  3. ``bottom_ruler.grade_call`` locates the signal bar by *calendar-date* match against that
     index, never by instant equality.
  4. Every consumer throws the clock away at the boundary: the store writes
     ``grade_asof = str(as_of.date())`` and the display artifact writes
     ``"as_of": str(as_of.date())``.
  5. The CLI documents ``--as-of`` as ``YYYY-MM-DD``; ``LEDGER_BORN`` and
     ``FIRST_MATURITY_EST`` are date strings.

So the domain contains no instant anywhere.  A US trading session dated 2026-09-17 is an
exchange civil date; it is *not* the instant 2026-09-17T00:00:00Z.  Making the pipeline
tz-aware would therefore invent precision the data does not have and would force the price
index to be localized to a zone it was never stamped in.  Date-only is the contract.

THE ONE COERCION RULE
---------------------
``to_ledger_date(value)``: parse, then — if the value carries a UTC offset — take its **wall
clock at its own offset**, then normalize to midnight.

A value stamped with an offset already states which civil day it belongs to *in the zone that
stamped it*: a US bar at ``2026-09-17 16:00-04:00`` belongs to session 2026-09-17; an Asian bar
at ``2026-09-18 00:00+08:00`` belongs to session 2026-09-18.  Converting to UTC first would
mis-file the Asian bar a day early, so the wall clock at its own offset is the only
zone-agnostic reading.

This rule also **exactly preserves the previous default**: the old code's
``pd.Timestamp.utcnow().normalize()`` is a UTC-zoned value, whose wall clock at its own (+00)
offset is the UTC civil date.  ``today_ledger_date()`` returns precisely that, so the repair
introduces no silent semantic drift — it only stops the crash.  (It also drops
``Timestamp.utcnow``, which pandas has deprecated for removal.)

DST: the rule is DST-stable by construction.  A spring-forward gap cannot produce a timestamp,
and a fall-back repetition maps both readings of an ambiguous wall clock to the *same* civil
date.  No ledger date can shift because a zone changed its offset.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

__all__ = [
    "ClockContractError",
    "LEDGER_DATE_FMT",
    "to_ledger_date",
    "to_ledger_date_or_none",
    "ledger_date_str",
    "today_ledger_date",
    "to_ledger_date_index",
]

LEDGER_DATE_FMT = "%Y-%m-%d"

# values that are "absent" rather than "malformed" — they carry no date at all.
_NULLISH = {"", "none", "null", "nat", "nan", "n/a", "-"}


class ClockContractError(ValueError):
    """A value could not be read as a ledger date (civil calendar date).

    Raised instead of silently coercing, so a malformed date can never masquerade as a
    successful capture, maturity check or grade.
    """


def to_ledger_date(value: Any, *, field: str = "date") -> pd.Timestamp:
    """Coerce ``value`` to the contract: tz-naive, midnight-normalized ``pd.Timestamp``.

    Accepts ``str`` (``YYYY-MM-DD`` and any pandas-parseable form), ``datetime.date``,
    ``datetime.datetime``, ``numpy.datetime64`` and ``pd.Timestamp``.  A tz-aware input is read
    at its own offset's wall clock (see the module docstring), never converted to UTC first.
    A naive input that carries a time component keeps its civil date.

    Raises:
        ClockContractError: the value is missing, NaT, or not a date at all.  Callers that
            must tolerate one bad row catch this (or use ``to_ledger_date_or_none``); callers
            holding a process-wide value let it propagate so the run fails loudly.
    """
    if value is None:
        raise ClockContractError(f"{field}: missing (None) — a ledger date is required")
    if isinstance(value, str) and value.strip().lower() in _NULLISH:
        raise ClockContractError(f"{field}: empty/null date string {value!r}")
    try:
        ts = pd.Timestamp(value)
    except (ValueError, TypeError, OverflowError, pd.errors.OutOfBoundsDatetime) as exc:
        raise ClockContractError(f"{field}: {value!r} is not a date ({exc})") from exc
    if ts is pd.NaT or pd.isna(ts):
        raise ClockContractError(f"{field}: {value!r} parsed to NaT")
    if ts.tz is not None:
        # wall clock at the value's own offset — the civil day the stamp belongs to.
        ts = ts.tz_localize(None)
    return ts.normalize()


def to_ledger_date_or_none(value: Any) -> pd.Timestamp | None:
    """``to_ledger_date`` for row-level tolerance: ``None`` instead of raising.

    Use only where a single malformed row must be skipped and COUNTED — never to make a
    process-wide clock silently disappear.
    """
    try:
        return to_ledger_date(value)
    except ClockContractError:
        return None


def ledger_date_str(value: Any, *, field: str = "date") -> str:
    """The persisted/serialized form of a ledger date: ``YYYY-MM-DD``."""
    return to_ledger_date(value, field=field).strftime(LEDGER_DATE_FMT)


def today_ledger_date() -> pd.Timestamp:
    """Today as a ledger date — the UTC civil date, as a tz-naive normalized Timestamp.

    Identical in value to the previous ``pd.Timestamp.utcnow().normalize()`` default (see the
    module docstring), minus the tz-awareness that crashed every comparison and minus the
    pandas deprecation.  UTC has no DST, so this is stable across offset changes.
    """
    return to_ledger_date(pd.Timestamp.now("UTC"), field="today")


def to_ledger_date_index(index: Any, *, field: str = "index") -> pd.DatetimeIndex:
    """Coerce a datetime index (e.g. a price series index) to ledger dates.

    Applies the same one rule elementwise: a tz-aware index is read at its own offset's wall
    clock, then normalized.  This is the READER boundary that keeps a tz-stamped price file
    from silently resolving no signal bar in ``grade_call``.

    Raises:
        ClockContractError: the index cannot be read as datetimes at all.
    """
    try:
        idx = pd.DatetimeIndex(pd.to_datetime(index))
    except (ValueError, TypeError, pd.errors.OutOfBoundsDatetime) as exc:
        raise ClockContractError(f"{field}: not a datetime index ({exc})") from exc
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    return idx.normalize()
