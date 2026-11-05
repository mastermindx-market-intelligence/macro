"""Seal-adjacent pins for S2 clock-law half-days and non-finite abstains (X7-02).

SNI-local DRAFT contract tests. They CONSUME owner-supplied published half-day
closes from lib.exchange_holidays.early_close and synthetic price frames; they
do not re-implement Data OS identity, Company Event/Earnings, FIF, Capital
Structure, Stock Identity, Options, Research Vault, or qledger/Evaluation.
Identity ids are never minted here. rank_authority, gate_authority,
size_authority, signal_authority, escalation_authority and trade_authority
stay literal false; a caller that tries to set any of them true is refused.
Fixtures are synthetic. Residuals and event-study numbers are descriptive,
never causal, never a news-impact claim. An unestimable family ABSTAINS with
a named reason.

Sealed S2 v1.1 inputs never take the HK half-day session_part branch or the
non-finite-close abstain / leak-window clip, so seal_full_check is silent on
those branches. These tests exercise them directly without touching sealed
code or residual/event_response sources.
"""
from __future__ import annotations

import math
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_EVENT_RESPONSE = ROOT / "research" / "single_name_intelligence" / "event_response"
_EVALUATION = ROOT / "research" / "single_name_intelligence" / "evaluation"
sys.path.insert(0, str(_EVENT_RESPONSE))
sys.path.insert(0, str(ROOT))

pd = pytest.importorskip("pandas")

import s2_clocklaw as clocklaw  # noqa: E402
import s2_outcomes as s2_outcomes  # noqa: E402
from lib.exchange_holidays import early_close  # noqa: E402
from s2_clocklaw import (  # noqa: E402
    MARKET_HK,
    SESSION_SPAN_END,
    SESSION_SPAN_START,
    session_part,
    to_utc,
)
from s2_outcomes import (  # noqa: E402
    ABSTAIN_MISSING_ENDPOINT,
    BABA_PATH,
    INFO_LEAK_STEP_TOLERANCE,
    OutcomeEngine,
    _usable_close,
)
import lib.nyse_calendar as nyse_calendar  # noqa: E402

AUTHORITY_FLAGS = {
    "rank_authority": False,
    "gate_authority": False,
    "size_authority": False,
    "signal_authority": False,
    "escalation_authority": False,
    "trade_authority": False,
}
_AUTHORITY_KEYS = tuple(AUTHORITY_FLAGS)

HK_TZ = "Asia/Hong_Kong"
_LOCAL_1205 = time(12, 5)
_LOCAL_1210 = time(12, 10)
_HALF_DAY_1205_LABEL = "in_session"  # HK CAS still open until 12:10
_FULL_DAY_1205_LABEL = "midday_break"
SPAN_START = date(2019, 1, 1)
SPAN_END = date(2027, 12, 31)

BAD_CLOSES = (
    pytest.param(float("nan"), id="nan"),
    pytest.param(float("inf"), id="pinf"),
    pytest.param(float("-inf"), id="ninf"),
    pytest.param(0.0, id="zero"),
    pytest.param(-7.25, id="neg"),
)
BAD_CLOSE_VALUES = (float("nan"), float("inf"), float("-inf"), 0.0, -7.25)


def refuse_nonfalse_authority(flags=None) -> None:
    """Raise if any authority flag is not literal False."""
    obj = AUTHORITY_FLAGS if flags is None else flags
    if not isinstance(obj, dict):
        raise TypeError("authority flags must be a mapping")
    for k in _AUTHORITY_KEYS:
        if obj.get(k) is not False:
            raise ValueError(
                f"authority flag {k!r} is not literal False (got {obj.get(k)!r})"
            )


refuse_nonfalse_authority()


def _enumerate_hk_early_closes(start: date, end: date):
    """Every owner-published HK early close in [start, end]; never a hard-coded list."""
    out = []
    d = start
    one = timedelta(days=1)
    while d <= end:
        ec = early_close(MARKET_HK, d)
        if ec is not None:
            out.append((d, ec))
        d += one
    return tuple(out)


HK_HALF_DAYS = _enumerate_hk_early_closes(SPAN_START, SPAN_END)


def _hkt(day: date, clock: time) -> datetime:
    naive = datetime(
        day.year, day.month, day.day,
        clock.hour, clock.minute, clock.second, clock.microsecond,
    )
    return to_utc(naive, HK_TZ)


def _full_neighbor(day: date) -> date:
    for delta in (1, -1, 2, -2, 3, -3, 4, -4):
        adj = day + timedelta(days=delta)
        if adj < SPAN_START or adj > SPAN_END:
            continue
        if early_close(MARKET_HK, adj) is None:
            return adj
    raise AssertionError("no full-day neighbor for %s" % day.isoformat())


def _assert_half_day_1205_not_lunch() -> None:
    assert len(HK_HALF_DAYS) > 0
    for day, _ec in HK_HALF_DAYS:
        got = session_part(_hkt(day, _LOCAL_1205), MARKET_HK)
        assert got != _FULL_DAY_1205_LABEL, (
            "HK half-day %s 12:05 classified as lunch (%r)" % (day.isoformat(), got)
        )
        assert got == _HALF_DAY_1205_LABEL, (
            "HK half-day %s 12:05 -> %r expected %r"
            % (day.isoformat(), got, _HALF_DAY_1205_LABEL)
        )


def _assert_full_day_1205_is_lunch() -> None:
    assert len(HK_HALF_DAYS) > 0
    for day, _ec in HK_HALF_DAYS:
        adj = _full_neighbor(day)
        got = session_part(_hkt(adj, _LOCAL_1205), MARKET_HK)
        assert got == _FULL_DAY_1205_LABEL, (
            "HK full day %s 12:05 -> %r expected %r"
            % (adj.isoformat(), got, _FULL_DAY_1205_LABEL)
        )


class _Loader:
    def __init__(self, baba, spy):
        self.baba = baba
        self.spy = spy

    def read_parquet(self, path, columns=None):
        df = self.baba if path == BABA_PATH else self.spy
        if columns is None:
            return df
        return df[[c for c in columns if c in df.columns]]


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


def _nyse_sessions(n, start=date(2024, 1, 2)):
    out = []
    d = start
    while len(out) < n:
        if nyse_calendar.is_session(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def _good_pair(n):
    baba = [100.0 + i for i in range(n)]
    spy = [200.0 + 0.5 * i for i in range(n)]
    return baba, spy


def _resolved(sess, s_us, h=5):
    baba, spy = _good_pair(len(sess))
    eng = _engine(sess, baba, spy)
    w = eng.resolve_window(s_us, h)
    assert w is not None
    assert w.fill_date == s_us
    assert w.coverage_date in sess
    return w


def _business_days(n, start=date(2026, 6, 1)):
    out = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def _leak_engine(dates, jump_idx, *, persistent=True, series="BABA"):
    n = len(dates)
    close = [100.0 + 0.1 * i for i in range(n)]
    raw = list(close)
    if jump_idx is not None:
        if persistent:
            for j in range(jump_idx, n):
                raw[j] = close[j] / 1.01
        else:
            raw[jump_idx] = close[jump_idx] / 1.01
    baba_close, baba_raw = close, raw
    spy_close = [500.0] * n
    spy_raw = [500.0] * n
    if series == "SPY":
        baba_close = [100.0] * n
        baba_raw = [100.0] * n
        spy_close, spy_raw = close, raw
    return _engine(dates, baba_close, spy_close, baba_raw=baba_raw, spy_raw=spy_raw)


# ---------------------------------------------------------------------------
# 1. HK half-day session_part at local 12:05
# ---------------------------------------------------------------------------

def test_s2adj_00_enumerated_hk_half_day_count_positive():
    assert SPAN_START == date(2019, 1, 1)
    assert SPAN_END == date(2027, 12, 31)
    assert SESSION_SPAN_START <= SPAN_START
    assert SESSION_SPAN_END >= SPAN_END
    assert len(HK_HALF_DAYS) > 0
    for day, ec in HK_HALF_DAYS:
        assert SPAN_START <= day <= SPAN_END
        assert early_close(MARKET_HK, day) == ec
        assert isinstance(ec, time)


def test_s2adj_01_hk_half_day_1205_not_lunch_break():
    """Every owner-published HK early close: 12:05 is not the lunch label."""
    _assert_half_day_1205_not_lunch()


def test_s2adj_02_hk_full_day_1205_is_lunch_break():
    """The same wall clock on a full day is the midday-break label."""
    _assert_full_day_1205_is_lunch()


@pytest.mark.parametrize(
    "day,ec",
    HK_HALF_DAYS,
    ids=[d.isoformat() for d, _ in HK_HALF_DAYS],
)
def test_s2adj_03_each_hk_half_day_1205_in_session(day: date, ec: time):
    got = session_part(_hkt(day, _LOCAL_1205), MARKET_HK)
    assert got == _HALF_DAY_1205_LABEL
    assert got != _FULL_DAY_1205_LABEL
    # CAS still open: 12:05 is before the published early close.
    assert _LOCAL_1205 < ec


@pytest.mark.parametrize(
    "day,ec",
    HK_HALF_DAYS,
    ids=[d.isoformat() for d, _ in HK_HALF_DAYS],
)
def test_s2adj_04_each_hk_full_neighbor_1205_midday_break(day: date, ec: time):
    del ec
    adj = _full_neighbor(day)
    assert early_close(MARKET_HK, adj) is None
    got = session_part(_hkt(adj, _LOCAL_1205), MARKET_HK)
    assert got == _FULL_DAY_1205_LABEL


def test_s2adj_16_half_day_1210_after_close_full_day_lunch():
    assert len(HK_HALF_DAYS) > 0
    for day, ec in HK_HALF_DAYS:
        half = session_part(_hkt(day, _LOCAL_1210), MARKET_HK)
        assert half == "after_close", (
            "HK half-day %s 12:10 -> %r (ec=%s)" % (day.isoformat(), half, ec)
        )
        adj = _full_neighbor(day)
        full = session_part(_hkt(adj, _LOCAL_1210), MARKET_HK)
        assert full == _FULL_DAY_1205_LABEL, (
            "HK full day %s 12:10 -> %r" % (adj.isoformat(), full)
        )


def test_s2adj_01b_early_close_none_is_caught(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(clocklaw, "early_close", lambda m, d: None)
    with pytest.raises(AssertionError):
        _assert_half_day_1205_not_lunch()


# ---------------------------------------------------------------------------
# 2. Non-finite / non-positive closes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", BAD_CLOSES)
def test_s2adj_05_usable_close_rejects_nonfinite_nonpositive(bad):
    assert _usable_close(bad) is False


def test_s2adj_06_usable_close_accepts_positive_finite():
    assert _usable_close(0.01) is True
    assert _usable_close(1.0) is True
    assert _usable_close(1234.5) is True
    assert _usable_close("42.0") is True


def test_s2adj_17_usable_close_rejects_non_numeric():
    assert _usable_close(None) is False
    assert _usable_close("not-a-price") is False
    assert _usable_close(object()) is False
    assert _usable_close("") is False


@pytest.mark.parametrize("bad", BAD_CLOSES)
def test_s2adj_07_leg_return_abstains_on_bad_graded_endpoint(bad):
    sess = _nyse_sessions(30)
    s_us = sess[10]
    w = _resolved(sess, s_us, 5)
    baba, spy = _good_pair(len(sess))
    baba[sess.index(w.coverage_date)] = bad
    eng = _engine(sess, baba, spy)
    got = eng.leg_return(eng.baba_close, w.fill_date, w.coverage_date)
    assert got is None


@pytest.mark.parametrize("bad", BAD_CLOSES)
def test_s2adj_08_episode_excess_abstains_on_bad_graded_endpoint(bad):
    sess = _nyse_sessions(30)
    s_us = sess[10]
    w = _resolved(sess, s_us, 5)
    baba, spy = _good_pair(len(sess))
    baba[sess.index(w.coverage_date)] = bad
    eng = _engine(sess, baba, spy)
    out = eng.episode_excess(s_us, 5)
    assert out["state"] == ABSTAIN_MISSING_ENDPOINT
    assert "excess" not in out
    assert "subject_ret" not in out
    assert "bench_ret" not in out
    # A number must not be produced from a non-usable graded endpoint.
    for key in ("excess", "subject_ret", "bench_ret"):
        val = out.get(key)
        assert val is None or not isinstance(val, (int, float)) or (
            isinstance(val, float) and not math.isfinite(val) and False
        )


def test_s2adj_09_episode_excess_ok_on_positive_finite():
    sess = _nyse_sessions(30)
    s_us = sess[10]
    baba, spy = _good_pair(len(sess))
    eng = _engine(sess, baba, spy)
    w = eng.resolve_window(s_us, 5)
    assert w is not None and w.fill_date == s_us
    e0 = float(eng.baba_close.loc[pd.Timestamp(w.fill_date)])
    e1 = float(eng.baba_close.loc[pd.Timestamp(w.coverage_date)])
    b0 = float(eng.spy_close.loc[pd.Timestamp(w.fill_date)])
    b1 = float(eng.spy_close.loc[pd.Timestamp(w.coverage_date)])
    assert _usable_close(e0) and _usable_close(e1)
    hand = e1 / e0 - 1.0
    bench = b1 / b0 - 1.0
    got = eng.leg_return(eng.baba_close, w.fill_date, w.coverage_date)
    assert got == pytest.approx(hand)
    out = eng.episode_excess(s_us, 5)
    assert out["state"] == "OK"
    assert out["subject_ret"] == round(hand, 10)
    assert out["bench_ret"] == round(bench, 10)
    assert out["excess"] == round(hand - bench, 10)
    assert math.isfinite(out["excess"])


def test_s2adj_19_leg_return_accepts_positive_finite_fill_and_coverage():
    sess = _nyse_sessions(30)
    s_us = sess[10]
    w = _resolved(sess, s_us, 5)
    baba, spy = _good_pair(len(sess))
    eng = _engine(sess, baba, spy)
    got = eng.leg_return(eng.baba_close, w.fill_date, w.coverage_date)
    assert got is not None
    assert math.isfinite(got)


def test_s2adj_20_episode_excess_abstains_on_bad_fill_endpoint():
    sess = _nyse_sessions(30)
    s_us = sess[10]
    w = _resolved(sess, s_us, 5)
    for bad in BAD_CLOSE_VALUES:
        baba, spy = _good_pair(len(sess))
        baba[sess.index(w.fill_date)] = bad
        eng = _engine(sess, baba, spy)
        out = eng.episode_excess(s_us, 5)
        assert out["state"] == ABSTAIN_MISSING_ENDPOINT, bad
        assert "excess" not in out


# ---------------------------------------------------------------------------
# 3. info_leak_scan differencing (full series, then clip to window)
# ---------------------------------------------------------------------------

def test_s2adj_10_info_leak_step_inside_window_detected():
    dates = _business_days(40)
    k = 10
    eng = _leak_engine(dates, k, persistent=True)
    scan = eng.info_leak_scan(dates[k])
    assert scan["scanned"] is True
    assert scan["leak"] is True
    assert scan["first_tune_anchor"] == dates[k].isoformat()
    assert scan["last_bar"] == dates[-1].isoformat()
    assert scan["series"]["BABA"]["first_offending_date"] == dates[k].isoformat()
    assert scan["series"]["BABA"]["steps_above_tolerance"] >= 1
    assert scan["series"]["BABA"]["max_abs_step"] > INFO_LEAK_STEP_TOLERANCE
    assert scan["series"]["SPY"]["steps_above_tolerance"] == 0


def test_s2adj_11_info_leak_step_before_anchor_not_detected():
    dates = _business_days(40)
    k = 10
    eng = _leak_engine(dates, k, persistent=True)
    scan = eng.info_leak_scan(dates[k + 1])
    assert scan["scanned"] is True
    assert scan["leak"] is False
    assert scan["series"]["BABA"]["first_offending_date"] is None
    assert scan["series"]["BABA"]["steps_above_tolerance"] == 0
    assert scan["first_tune_anchor"] == dates[k + 1].isoformat()


def test_s2adj_12_info_leak_on_anchor_uses_full_series_then_clip():
    """A one-bar step ON first_tune_anchor is visible only if q is differenced
    on the full series and then clipped; filter-then-diff drops the first bar.
    """
    dates = _business_days(40)
    k = 10
    eng = _leak_engine(dates, k, persistent=False)
    on_anchor = eng.info_leak_scan(dates[k])
    assert on_anchor["leak"] is True
    assert on_anchor["series"]["BABA"]["first_offending_date"] == dates[k].isoformat()


def test_s2adj_18_info_leak_spy_step_inside_window_detected():
    dates = _business_days(24)
    k = 8
    eng = _leak_engine(dates, k, persistent=True, series="SPY")
    inside = eng.info_leak_scan(dates[k])
    assert inside["leak"] is True
    assert inside["series"]["SPY"]["first_offending_date"] == dates[k].isoformat()
    assert inside["series"]["BABA"]["steps_above_tolerance"] == 0
    before = eng.info_leak_scan(dates[k + 1])
    assert before["leak"] is False
    assert before["series"]["SPY"]["steps_above_tolerance"] == 0


def test_s2adj_21_info_leak_step_on_last_bar_detected():
    dates = _business_days(16)
    eng = _leak_engine(dates, len(dates) - 1, persistent=True)
    scan = eng.info_leak_scan(dates[0])
    assert scan["leak"] is True
    assert scan["last_bar"] == dates[-1].isoformat()
    assert scan["series"]["BABA"]["first_offending_date"] == dates[-1].isoformat()


# ---------------------------------------------------------------------------
# 4. Import-path guard and seal_full_check S2 listing
# ---------------------------------------------------------------------------

def test_s2adj_13_imports_from_event_response():
    clock_path = Path(clocklaw.__file__).resolve()
    outcomes_path = Path(s2_outcomes.__file__).resolve()
    expected = _EVENT_RESPONSE.resolve()
    assert clock_path.parent == expected, clock_path
    assert outcomes_path.parent == expected, outcomes_path
    posix_clock = clock_path.as_posix()
    posix_out = outcomes_path.as_posix()
    marker = "research/single_name_intelligence/event_response"
    assert marker in posix_clock
    assert marker in posix_out
    assert clock_path.name == "s2_clocklaw.py"
    assert outcomes_path.name == "s2_outcomes.py"


def test_s2adj_14_seal_full_check_s2_file_list_unaffected():
    """Public listing: s2_exceptions() and rel_files(S2_V1_1_REL).

    This adjacent test file is not an S2 seal input; the committed S2 file
    list must not grow to include it.
    """
    sys.path.insert(0, str(_EVALUATION))
    import seal_full_check  # noqa: WPS433

    exceptions = seal_full_check.s2_exceptions()
    assert set(exceptions) == {"trial_ledger.jsonl"}
    committed = ROOT / seal_full_check.S2_V1_1_REL
    assert committed.is_dir()
    listed = seal_full_check.rel_files(committed)
    assert listed, "committed S2 v1.1 run directory listed no files"
    assert all(not p.endswith("test_sni_s2_seal_adjacent.py") for p in listed)
    assert "tests/test_sni_s2_seal_adjacent.py" not in listed
    # Source tree of event_response is not the seal file list.
    assert "s2_clocklaw.py" not in listed
    assert "s2_outcomes.py" not in listed


def test_s2adj_15_authority_flags_refuse_true():
    refuse_nonfalse_authority(AUTHORITY_FLAGS)
    for key in _AUTHORITY_KEYS:
        assert AUTHORITY_FLAGS[key] is False
        poisoned = dict(AUTHORITY_FLAGS)
        poisoned[key] = True
        with pytest.raises(ValueError, match=key):
            refuse_nonfalse_authority(poisoned)
