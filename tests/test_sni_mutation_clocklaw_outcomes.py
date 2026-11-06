"""MUT5F killing tests for s2_clocklaw.py and s2_outcomes.py (2026-10-13).

SNI-local DRAFT contract tests. They consume owner-supplied session calendars
and synthetic price frames; they do not mint issuer or security identifiers
and they do not feed a rank, gate, size, signal, escalation, or trade path.
rank_authority, gate_authority, size_authority, signal_authority,
escalation_authority and trade_authority stay false. Fixtures are synthetic.
Residuals and event-study numbers are descriptive, never causal, never a
news-impact claim.

Each test_mut5f_* docstring names one non-equivalent mutant that survived
the pre-existing importer suite (file:line, original -> mutated).
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))

from s2_clocklaw import (  # noqa: E402
    CLOCK_CALENDARS,
    MARKET_US,
    SESSION_SPAN_START,
    ClockLawFailure,
    first_session_after_disclosure_date,
    session_dates,
)
from s2_outcomes import (  # noqa: E402
    ABSTAIN_RESOLVER_NONE,
    BABA_PATH,
    OutcomeEngine,
    _usable_close,
)
import lib.nyse_calendar as nyse_calendar  # noqa: E402
import s2_clocklaw as clocklaw  # noqa: E402
import s2_outcomes as s2_outcomes  # noqa: E402


class _Loader:
    def __init__(self, baba, spy):
        self.baba = baba
        self.spy = spy

    def read_parquet(self, path, columns=None):
        df = self.baba if path == BABA_PATH else self.spy
        return df if columns is None else df[[c for c in columns if c in df.columns]]


def _df(sess, closes, raw=None):
    raw = list(closes) if raw is None else list(raw)
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(sess),
            "close": list(closes),
            "close_price": raw,
        }
    )


def _engine(sess, baba_closes, spy_closes, baba_raw=None, spy_raw=None):
    return OutcomeEngine(
        _Loader(
            _df(sess, baba_closes, baba_raw),
            _df(sess, spy_closes, spy_raw),
        )
    )


def _d_and_d63(s_us: date):
    d = s_us - timedelta(days=1)
    while not nyse_calendar.is_session(d):
        d -= timedelta(days=1)
    d63 = d
    seen = 0
    while seen < s2_outcomes.TRAILING63_SESSIONS:
        d63 -= timedelta(days=1)
        if nyse_calendar.is_session(d63):
            seen += 1
    return d, d63


def _trail_sessions(s_us: date):
    d, d63 = _d_and_d63(s_us)
    sess = []
    cur = d63
    while cur <= s_us:
        if nyse_calendar.is_session(cur):
            sess.append(cur)
        cur += timedelta(days=1)
    return sess, d, d63


# ---------------------------------------------------------------------------
# s2_clocklaw
# ---------------------------------------------------------------------------

def test_mut5f_s2_clocklaw_module_1():
    """s2_clocklaw.py:95, SESSION_SPAN_START year 2019 -> 2020."""
    assert SESSION_SPAN_START == date(2019, 1, 1)
    us = session_dates(CLOCK_CALENDARS[MARKET_US])
    assert us[0] <= "2019-01-02"
    assert "2019-01-02" in us


def test_mut5f_s2_clocklaw_module_2():
    """s2_clocklaw.py:95, SESSION_SPAN_START month 1 -> 2 (date(2019, 1, 1))."""
    assert SESSION_SPAN_START == date(2019, 1, 1)
    us = session_dates(CLOCK_CALENDARS[MARKET_US])
    assert "2019-01-31" in us


def test_mut5f_s2_clocklaw_first_session_after_disclosure_date_1(monkeypatch):
    """s2_clocklaw.py:89, delete `if nxt is None: raise ClockLawFailure`."""
    monkeypatch.setattr(clocklaw, "next_session_strictly_after", lambda *a, **k: None)
    with pytest.raises(ClockLawFailure, match="no session found strictly after"):
        first_session_after_disclosure_date(date(2024, 6, 12), MARKET_US)


# ---------------------------------------------------------------------------
# s2_outcomes
# ---------------------------------------------------------------------------

def test_mut5f_s2_outcomes_episode_excess_1():
    """s2_outcomes.py:91, return ABSTAIN_RESOLVER_NONE dict -> return None."""
    sess = [date(2024, 3, 4), date(2024, 3, 5), date(2024, 3, 6)]
    eng = _engine(sess, [100.0, 101.0, 102.0], [200.0, 200.5, 201.0])
    out = eng.episode_excess(date(2024, 3, 5), 0)
    assert isinstance(out, dict)
    assert out["state"] == ABSTAIN_RESOLVER_NONE
    assert out["window"] is None


def test_mut5f_s2_outcomes_episode_excess_2():
    """s2_outcomes.py:108, round(subj - bench, 10) -> round(..., 11)."""
    sess = []
    d = date(2024, 3, 1)
    while len(sess) < 12:
        if nyse_calendar.is_session(d):
            sess.append(d)
        d += timedelta(days=1)
    s_us = sess[2]
    n = len(sess)
    baba = [100.0] * n
    spy = [100.0] * n
    eng = _engine(sess, baba, spy)
    w = eng.resolve_window(s_us, 5)
    assert w is not None and w.fill_date == s_us
    fill_i = sess.index(w.fill_date)
    cov_i = sess.index(w.coverage_date)
    baba[fill_i] = 100.0
    baba[cov_i] = 112.345678915
    spy[fill_i] = 100.0
    spy[cov_i] = 100.0
    eng = _engine(sess, baba, spy)
    subj = eng.leg_return(eng.baba_close, w.fill_date, w.coverage_date)
    bench = eng.leg_return(eng.spy_close, w.fill_date, w.coverage_date)
    x = subj - bench
    assert round(x, 10) != round(x, 11)
    out = eng.episode_excess(s_us, 5)
    assert out["state"] == "OK"
    assert out["excess"] == round(x, 10)


def test_mut5f_s2_outcomes_info_leak_scan_1():
    """s2_outcomes.py:162, round(float(steps.max()), 12) -> round(..., 13)."""
    sess = []
    d = date(2024, 3, 11)
    while len(sess) < 8:
        if nyse_calendar.is_session(d):
            sess.append(d)
        d += timedelta(days=1)
    n = len(sess)
    close = [100.0] * n
    raw = [100.0] * n
    raw[3] = 95.23809523804444
    eng = _engine(sess, close, [200.0] * n, baba_raw=raw, spy_raw=[200.0] * n)
    q = pd.Series(close, index=pd.to_datetime(sess)) / pd.Series(
        raw, index=pd.to_datetime(sess)
    )
    steps = (q / q.shift(1) - 1.0).abs().dropna()
    x = float(steps.max())
    assert round(x, 12) != round(x, 13)
    scan = eng.info_leak_scan(sess[0])
    assert scan["series"]["BABA"]["max_abs_step"] == round(x, 12)


def test_mut5f_s2_outcomes_trailing63_direction_1():
    """s2_outcomes.py:132, KeyError path `return 0` -> `return None`."""
    s_us = date(2024, 6, 3)
    assert nyse_calendar.is_session(s_us)
    eng = _engine([s_us], [110.0], [200.0])
    assert eng.trailing63_direction(s_us) == 0


def test_mut5f_s2_outcomes_trailing63_direction_2():
    """s2_outcomes.py:136, (baba_d / baba_d63 - 1.0) -> - 1.001."""
    s_us = date(2024, 6, 3)
    sess, d, d63 = _trail_sessions(s_us)
    baba = [100.0] * len(sess)
    spy = [100.0] * len(sess)
    baba[sess.index(d)] = 100.05
    baba[sess.index(d63)] = 100.0
    eng = _engine(sess, baba, spy)
    orig = (100.05 / 100.0 - 1.0) - (100.0 / 100.0 - 1.0)
    mut = (100.05 / 100.0 - 1.001) - (100.0 / 100.0 - 1.0)
    assert orig > 0
    assert mut < 0
    assert eng.trailing63_direction(s_us) == 1


def test_mut5f_s2_outcomes_trailing63_direction_3():
    """s2_outcomes.py:137, `1 if excess > 0` -> `>=` (zero excess must be 0)."""
    s_us = date(2024, 6, 3)
    sess, d, d63 = _trail_sessions(s_us)
    baba = [100.0] * len(sess)
    spy = [100.0] * len(sess)
    eng = _engine(sess, baba, spy)
    assert eng.trailing63_direction(s_us) == 0


def test_mut5f_s2_outcomes__usable_close_1():
    """s2_outcomes.py:43, except-path `return False` -> `return True`."""
    assert _usable_close("not-a-price") is False
    assert _usable_close(None) is False
    assert _usable_close(object()) is False
    assert _usable_close(100.0) is True
