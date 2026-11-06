"""MUT1B killing tests for s1_stats.py and s1_direction.py (2026-10-13).

SNI-local DRAFT contract tests. They consume caller-supplied synthetic bars
and counts; they do not mint issuer or security identifiers and they do not
feed a rank, gate, size, signal, escalation, or trade path. Authority flags
stay false. Fixtures are synthetic.

Each test_mut1b_* docstring names one non-equivalent mutant that survived
the pre-existing suite (file:line, original -> mutated).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"),
)

from s1_direction import (  # noqa: E402
    _leg_close,
    direction_always_long,
    direction_trailing63,
)
from s1_manifest import last_session_before, session_n_back  # noqa: E402


def _nyse_sessions(n: int = 80, start: date = date(2024, 1, 2)):
    from lib import nyse_calendar as cal

    cur, out = start, []
    while len(out) < n:
        if cal.is_session(cur):
            out.append(cur)
        cur += timedelta(days=1)
    return out, cal


def test_mut1b_s1_direction_direction_always_long_1():
    """s1_direction.py:22, return 1 -> return None."""
    assert direction_always_long(date(2024, 6, 3)) == 1


def test_mut1b_s1_direction_direction_always_long_2():
    """s1_direction.py:22, constant 1 -> 2."""
    assert direction_always_long(date(2019, 12, 31)) == 1
    assert direction_always_long(date(2020, 1, 2)) == 1


def test_mut1b_s1_direction__leg_close_1():
    """s1_direction.py:27, BoolOp `or` -> `and` in _leg_close guard."""
    d = date(2024, 1, 2)
    assert _leg_close({d: 0.0}, d) is None
    nan = float("nan")
    got = _leg_close({d: nan}, d)
    assert got is None
    assert _leg_close({d: 10.0}, d) == 10.0
    assert _leg_close({}, d) is None


def test_mut1b_s1_direction__leg_close_2():
    """s1_direction.py:27, constant 0 -> 1 in `v == 0` zero-price guard."""
    d = date(2024, 1, 3)
    assert _leg_close({d: 0.0}, d) is None
    assert _leg_close({d: 1.0}, d) == 1.0
    # public observable: a zero close at D(s) abstains (direction 0).
    dates, cal = _nyse_sessions()
    s = dates[70]
    d_s = last_session_before(cal.is_session, s)
    d63 = session_n_back(cal.is_session, d_s, 63)
    subj = {dt: 100.0 + i for i, dt in enumerate(dates)}
    bench = {dt: 50.0 for dt in dates}
    subj[d_s] = 0.0
    assert d63 in subj and d63 in bench
    assert direction_trailing63(subj, bench, s, cal.is_session) == 0


def test_mut1b_s1_direction_direction_trailing63_1():
    """s1_direction.py:33, default n 63 -> 64."""
    dates, cal = _nyse_sessions()
    s = dates[70]
    d_s = last_session_before(cal.is_session, s)
    d63 = session_n_back(cal.is_session, d_s, 63)
    d64 = session_n_back(cal.is_session, d_s, 64)
    assert d63 is not None and d64 is not None and d64 != d63
    subj = {dt: 100.0 + i for i, dt in enumerate(dates)}
    bench = {dt: 50.0 for dt in dates}
    del subj[d64]
    assert d63 in subj
    assert direction_trailing63(subj, bench, s, cal.is_session) == 1
    assert direction_trailing63(subj, bench, s, cal.is_session, 63) == 1
    assert direction_trailing63(subj, bench, s, cal.is_session, 64) == 0
