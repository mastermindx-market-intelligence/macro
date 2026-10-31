"""EDGAR acceptance clocks resolved to true UTC (prereg §10 A2).

EDGAR exposes a filing's acceptance instant in two raw forms:

(a) the submissions-JSON ``acceptanceDateTime``, e.g. ``"2026-07-30T00:04:53.000Z"``.
    Its "Z" suffix is NOT true UTC: the value reads LATER than the true instant by
    the America/New_York offset (4 h under EDT, 5 h under EST).  Established in
    ``research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md`` §10 A2 on non-universe
    filings against the filing header's ``ACCEPTANCE-DATETIME``.
(b) the SGML header ``ACCEPTANCE-DATETIME``, e.g. ``"20260729160453"``: wall time in
    America/New_York.

Each helper returns an aware UTC datetime, or None when the value is absent,
malformed, or does not resolve to exactly one instant (fail closed, never a guessed
clock).  The form (a) arithmetic is the frozen WP31 evaluator's
(``scripts/c19_wp31_sources.py::_edgar_json_acceptance_utc``);
``tests/test_edgar_clock.py`` pins the two together.  Nothing here rewrites a
stored value: collectors still store form (a) raw, and a change that makes a
collector store true UTC must remove the reader-side correction in the same change
(prereg §10 A2).
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

__all__ = ["ET", "submissions_acceptance_utc", "sgml_acceptance_utc"]

_SGML_STAMP = re.compile(r"\d{14}")


def _parse_labelled_utc(value: Any) -> datetime | None:
    # Read the value at its face label: offset-less input counts as "UTC", an
    # explicit offset is honoured, anything unparseable is None.
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    return None


def submissions_acceptance_utc(value: Any) -> datetime | None:
    """True UTC from a submissions-JSON ``acceptanceDateTime`` (form a).

    With J the value at its face label and o = -NY offset at J, the true instant
    is U = J - o.  U is kept only when -NY offset at U equals o; the two differ
    only within hours of a DST transition (a weekend night), where the clock is
    unresolvable and None is returned.

    A2 was observed on daytime filings, where it does not matter whether EDGAR
    shifted the value by the offset at U or at J.  If it used the offset at U, a
    true acceptance in the hour before spring forward (01:00-01:59 EST, a Sunday)
    passes the check and resolves one hour late.  That hour, like both None
    windows, lies outside EDGAR's filing hours (17 CFR 232.12(c): 6 a.m. to
    10 p.m. Eastern, weekdays except Federal holidays).
    """
    j = _parse_labelled_utc(value)
    if j is None:
        return None
    offset = -j.astimezone(ET).utcoffset()
    u = j - offset
    if -u.astimezone(ET).utcoffset() != offset:
        return None
    return u


def sgml_acceptance_utc(value: Any) -> datetime | None:
    """True UTC from an SGML header ``ACCEPTANCE-DATETIME`` (form b).

    The value is ``YYYYMMDDHHMMSS`` wall time in America/New_York.  A wall time
    that is skipped (spring forward) or repeated (fall back) names no single
    instant and returns None.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not _SGML_STAMP.fullmatch(text):
        return None
    try:
        wall = datetime.strptime(text, "%Y%m%d%H%M%S")
    except ValueError:
        return None
    early, late = wall.replace(tzinfo=ET, fold=0), wall.replace(tzinfo=ET, fold=1)
    if early.utcoffset() != late.utcoffset():
        return None
    return early.astimezone(timezone.utc)
