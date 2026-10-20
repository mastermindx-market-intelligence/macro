"""S2 non-finite / missing close must abstain; info-leak step on the anchor.

SNI-local DRAFT contract tests. They consume owner-supplied opaque identity
strings and never mint issuer or security ids. rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and trade_authority
stay literal false. Fixtures are synthetic. Residuals and event-study numbers
are descriptive, never causal, never a news-impact claim.
"""
from __future__ import annotations

import math
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research/single_name_intelligence/event_response"))
sys.path.insert(0, str(ROOT))

pd = pytest.importorskip("pandas")

import lib.nyse_calendar as nyse_calendar  # noqa: E402
import s2_outcomes  # noqa: E402
from s2_outcomes import (  # noqa: E402
    ABSTAIN_MISSING_ENDPOINT,
    BABA_PATH,
    INFO_LEAK_STEP_TOLERANCE,
    OutcomeEngine,
)

KINDS = (
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="pinf"),
    pytest.param(float("-inf"), id="ninf"),
    pytest.param(0.0, id="zero"),
    pytest.param(-12.5, id="neg"),
)
LEGS = ("subject", "bench")
ENDPOINTS = ("fill", "coverage")
TRAIL_SLOTS = ("baba_d", "baba_d63", "spy_d", "spy_d63")
KIND_VALUES = (float("nan"), float("inf"), float("-inf"), 0.0, -12.5)


class _Loader:
    """Same in-memory parquet idiom as test_mnz_07_s2_window_missing."""

    def __init__(self, baba, spy):
        self.baba = baba
        self.spy = spy

    def read_parquet(self, path, columns=None):
        return self.baba if path == BABA_PATH else self.spy


def _nyse_sessions(n, start=date(2024, 1, 2)):
    out = []
    d = start
    while len(out) < n:
        if nyse_calendar.is_session(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def _df(sess, closes):
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(sess),
            "close": list(closes),
            "close_price": list(closes),
        }
    )


def _engine(sess, baba_closes, spy_closes):
    return OutcomeEngine(_Loader(_df(sess, baba_closes), _df(sess, spy_closes)))


def _good_pair(n):
    baba = [100.0 + i for i in range(n)]
    spy = [200.0 + 0.5 * i for i in range(n)]
    return baba, spy


def _inject(values, sess, when, bad):
    out = list(values)
    out[sess.index(when)] = bad
    return out


def _resolved_window(sess, s_us, h=5):
    baba, spy = _good_pair(len(sess))
    eng = _engine(sess, baba, spy)
    w = eng.resolve_window(s_us, h)
    assert w is not None
    assert w.fill_date == s_us
    assert w.coverage_date in sess
    return w


def _assert_s2nf_01(kind, leg, endpoint):
    sess = _nyse_sessions(30)
    s_us = sess[10]
    w = _resolved_window(sess, s_us, 5)
    baba, spy = _good_pair(len(sess))
    target = w.fill_date if endpoint == "fill" else w.coverage_date
    if leg == "subject":
        baba = _inject(baba, sess, target, kind)
    else:
        spy = _inject(spy, sess, target, kind)
    eng = _engine(sess, baba, spy)
    out = eng.episode_excess(s_us, 5)
    assert out["state"] == ABSTAIN_MISSING_ENDPOINT, (
        "kind=%r leg=%s endpoint=%s state=%r" % (kind, leg, endpoint, out.get("state"))
    )
    assert out.get("subject_ret") is None
    assert out.get("bench_ret") is None
    series = eng.baba_close if leg == "subject" else eng.spy_close
    assert eng.leg_return(series, w.fill_date, w.coverage_date) is None


def _d_and_d63(s_us):
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


def _trail_sessions(s_us):
    d, d63 = _d_and_d63(s_us)
    sess = []
    cur = d63
    while cur <= s_us:
        if nyse_calendar.is_session(cur):
            sess.append(cur)
        cur += timedelta(days=1)
    return sess, d, d63


def _assert_s2nf_02(kind, slot):
    s_us = date(2024, 6, 3)
    sess, d, d63 = _trail_sessions(s_us)
    baba = [100.0] * len(sess)
    spy = [200.0] * len(sess)
    baba[sess.index(d)] = 110.0
    if slot == "baba_d":
        baba[sess.index(d)] = kind
    elif slot == "baba_d63":
        baba[sess.index(d63)] = kind
    elif slot == "spy_d":
        spy[sess.index(d)] = kind
    else:
        spy[sess.index(d63)] = kind
    eng = _engine(sess, baba, spy)
    assert eng.trailing63_direction(s_us) == 0, (
        "kind=%r slot=%s -> %r" % (kind, slot, eng.trailing63_direction(s_us))
    )


def _assert_s2nf_03():
    sess = _nyse_sessions(30)
    s_us = sess[10]
    baba, spy = _good_pair(len(sess))
    eng = _engine(sess, baba, spy)
    w = eng.resolve_window(s_us, 5)
    assert w is not None and w.fill_date == s_us
    e0 = float(eng.baba_close.loc[pd.Timestamp(w.fill_date)])
    e1 = float(eng.baba_close.loc[pd.Timestamp(w.coverage_date)])
    hand = e1 / e0 - 1.0
    got = eng.leg_return(eng.baba_close, w.fill_date, w.coverage_date)
    assert got == pytest.approx(hand)
    b0 = float(eng.spy_close.loc[pd.Timestamp(w.fill_date)])
    b1 = float(eng.spy_close.loc[pd.Timestamp(w.coverage_date)])
    bench_hand = b1 / b0 - 1.0
    out = eng.episode_excess(s_us, 5)
    assert out["state"] == "OK"
    assert out["subject_ret"] == round(hand, 10)
    assert out["bench_ret"] == round(bench_hand, 10)
    assert out["excess"] == round(hand - bench_hand, 10)

    s_trail = date(2024, 6, 3)
    sess_t, d, d63 = _trail_sessions(s_trail)
    baba_t = [100.0] * len(sess_t)
    spy_t = [200.0] * len(sess_t)
    baba_t[sess_t.index(d)] = 110.0
    eng_t = _engine(sess_t, baba_t, spy_t)
    baba_d = 110.0
    baba_d63 = 100.0
    spy_d = 200.0
    spy_d63 = 200.0
    excess = (baba_d / baba_d63 - 1.0) - (spy_d / spy_d63 - 1.0)
    expect = 1 if excess > 0 else (-1 if excess < 0 else 0)
    assert eng_t.trailing63_direction(s_trail) == expect


def _leak_engine(dates, jump_idx):
    n = len(dates)
    close = [100.0 + 0.1 * i for i in range(n)]
    raw = list(close)
    if jump_idx is not None:
        for j in range(jump_idx, n):
            raw[j] = close[j] / 1.01
    baba = pd.DataFrame(
        {
            "Date": pd.to_datetime([d.isoformat() for d in dates]),
            "close": close,
            "close_price": raw,
        }
    )
    spy = pd.DataFrame(
        {
            "Date": pd.to_datetime([d.isoformat() for d in dates]),
            "close": [500.0] * n,
            "close_price": [500.0] * n,
        }
    )
    return OutcomeEngine(_Loader(baba, spy))


def _business_days(n, start=date(2026, 6, 1)):
    out = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _assert_s2nf_04():
    dates = _business_days(40)
    k = 10
    engine = _leak_engine(dates, k)
    on_anchor = engine.info_leak_scan(dates[k])
    assert on_anchor["leak"] is True
    assert on_anchor["series"]["BABA"]["first_offending_date"] == dates[k].isoformat()
    assert on_anchor["series"]["BABA"]["steps_above_tolerance"] >= 1
    assert isinstance(on_anchor["series"]["BABA"]["max_abs_step"], float)

    before = engine.info_leak_scan(dates[k + 1])
    assert before["leak"] is False
    assert before["series"]["BABA"]["first_offending_date"] is None
    assert before["series"]["BABA"]["steps_above_tolerance"] == 0

    last_engine = _leak_engine(dates, len(dates) - 1)
    on_last = last_engine.info_leak_scan(dates[0])
    assert on_last["leak"] is True
    assert on_last["series"]["BABA"]["first_offending_date"] == dates[-1].isoformat()
    assert on_last["last_bar"] == dates[-1].isoformat()


def _usable_close_truthy(x):
    return bool(x)


def _usable_close_accept_zero(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v >= 0.0


def _info_leak_filter_before_diff(self, first_tune_anchor, *args, **kwargs):
    out = {
        "scanned": bool(first_tune_anchor is not None),
        "first_tune_anchor": first_tune_anchor.isoformat() if first_tune_anchor else None,
        "last_bar": self.last_bar_date.isoformat(),
        "series": {},
    }
    if first_tune_anchor is None:
        return out
    lo = pd.Timestamp(first_tune_anchor)
    for name, close, raw in (
        ("BABA", self.baba_close, self.baba_close_price),
        ("SPY", self.spy_close, self.spy_close_price),
    ):
        common = close.index.intersection(raw.index)
        q = close.loc[common] / raw.loc[common]
        q = q[q.index >= lo]
        steps = (q / q.shift(1) - 1.0).abs().dropna()
        offenders = steps[steps > INFO_LEAK_STEP_TOLERANCE]
        out["series"][name] = {
            "first_offending_date": (
                offenders.index[0].date().isoformat() if len(offenders) else None
            ),
            "steps_above_tolerance": int(len(offenders)),
            "max_abs_step": (round(float(steps.max()), 12) if len(steps) else None),
        }
    out["leak"] = any(v["steps_above_tolerance"] > 0 for v in out["series"].values())
    return out


def _run_s2nf_01_to_04():
    for kind in KIND_VALUES:
        for leg in LEGS:
            for endpoint in ENDPOINTS:
                _assert_s2nf_01(kind, leg, endpoint)
        for slot in TRAIL_SLOTS:
            _assert_s2nf_02(kind, slot)
    _assert_s2nf_03()
    _assert_s2nf_04()


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("leg", LEGS)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
def test_s2nf_01(kind, leg, endpoint):
    _assert_s2nf_01(kind, leg, endpoint)


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("slot", TRAIL_SLOTS)
def test_s2nf_02(kind, slot):
    _assert_s2nf_02(kind, slot)


def test_s2nf_03():
    _assert_s2nf_03()


def test_s2nf_04():
    _assert_s2nf_04()


@pytest.mark.parametrize("mutant_id", ("m1", "m2", "m3"))
def test_s2nf_05_mutants_are_caught(monkeypatch, mutant_id):
    if mutant_id == "m1":
        monkeypatch.setattr(s2_outcomes, "_usable_close", _usable_close_truthy)
    elif mutant_id == "m2":
        monkeypatch.setattr(
            s2_outcomes.OutcomeEngine, "info_leak_scan", _info_leak_filter_before_diff
        )
    else:
        monkeypatch.setattr(s2_outcomes, "_usable_close", _usable_close_accept_zero)
    caught = False
    try:
        _run_s2nf_01_to_04()
    except (AssertionError, ZeroDivisionError, OverflowError, ValueError):
        caught = True
    assert caught, "mutant %s was not caught by s2nf_01..04" % mutant_id
