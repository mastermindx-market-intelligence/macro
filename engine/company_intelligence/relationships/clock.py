"""The A24 knowledge clock: EDGAR acceptance time, America/New_York -> UTC.

Machine-readable twin of the contracts' ``x-gmi-clock-rule`` annotation: a
filing's knowledge instant is the sec-index-header acceptance stamp
(``sec_index_header_acceptance_et``, ``YYYYMMDDHHMMSS``) read as an
America/New_York wall clock and converted to UTC.  The EDGAR submissions JSON
``acceptanceDateTime`` is NOT a clock (see the annotation's ``not_a_clock``).

DST edges are refused, never guessed: a wall time that occurs twice
(fall-back) or never (spring-forward) raises :class:`ClockRefused`.  No wall
clock reads, no network, stdlib only.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SOURCE_TZ = "America/New_York"

_HEADER_PATTERN = re.compile(r"^\d{14}$")
_HEADER_FORMAT = "%Y%m%d%H%M%S"
_UTC_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class ClockRefused(ValueError):
    """The acceptance wall time cannot be converted without guessing (A24).

    ``args[0]`` is the refusal reason: ``format``, ``ambiguous`` or
    ``nonexistent``.
    """


def et_acceptance_to_utc(header: str) -> str:
    """Convert one sec-index-header acceptance stamp to ``...Z`` UTC.

    Raises :class:`ClockRefused` with reason ``format`` for anything that is
    not 14 digits, ``nonexistent`` for spring-forward gaps, and ``ambiguous``
    for fall-back repeats.
    """
    if not isinstance(header, str) or not _HEADER_PATTERN.match(header):
        raise ClockRefused("format")
    naive = datetime.strptime(header, _HEADER_FORMAT)
    tz = ZoneInfo(SOURCE_TZ)
    aware = naive.replace(tzinfo=tz, fold=0)
    # A spring-forward gap first: the round trip through UTC lands on a
    # different wall time, while a fall-back repeat still round-trips.
    if aware.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) != naive:
        raise ClockRefused("nonexistent")
    if naive.replace(tzinfo=tz, fold=1).utcoffset() != aware.utcoffset():
        raise ClockRefused("ambiguous")
    return aware.astimezone(timezone.utc).strftime(_UTC_FORMAT)
