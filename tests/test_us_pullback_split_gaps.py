"""Skipped-session splits and dividend-only hits. Synthetic stores, no network.

The guard names a session's splits and ex-dividends together. A raw close moves
on a split, not on a dividend. A session the store never stored can still be
the session a split executed.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from engine.close_pass.massive_close import CorpActions, SessionCloses
from lib import nyse_calendar
from lib import us_pullback_observation as pb
from lib.us_pullback_observation import SourceRefused, licensed_spy_closes, snapshot


FIXED_NOW = datetime(2026, 10, 9, 22, 0, tzinfo=timezone.utc)
EXPECTED = date(2026, 10, 9)
# Tuesday, no Wednesday row, Thursday and Friday stored. Wednesday is a session.
GAP_STAMPS = ("2026-10-06", "2026-10-08", "2026-10-09")
SKIPPED = "2026-10-07"


def store(stamps, closes):
    return pd.DataFrame({"close": list(closes)}, index=pd.to_datetime(list(stamps)))


def _no_tip(*args, **kwargs):
    raise AssertionError("the store already holds the expected session")


def _measure(rows, *, expected_session, is_session):
    close = rows[-1][1]
    peak = max(price for _, price in rows)
    return {
        "schema": "pullback_observation.v1",
        "available": True,
        "quality": "current",
        "phase": "underway",
        "active": True,
        "asof": expected_session.isoformat(),
        "expected_session": expected_session.isoformat(),
        "close": close,
        "peak_close": peak,
        "low_close": min(price for _, price in rows),
        "drawdown_pct": round(100.0 * (close / peak - 1.0), 4),
    }


def _read(frame, actions, *, session_closes=_no_tip):
    return snapshot(
        now=FIXED_NOW,
        read=lambda expected: licensed_spy_closes(
            expected, load=lambda ticker: frame, session_closes=session_closes,
            corp_actions=actions),
        observer=_measure)


def _gap(later):
    return store(GAP_STAMPS, (80.0, later, later))


@pytest.mark.parametrize("later, drawdown", [
    pytest.param(64.0, -20.0, id="ratio-0.80"),
    pytest.param(60.0, -25.0, id="ratio-0.75"),
])
def test_split_on_a_skipped_session_is_asked_and_refuses(later, drawdown):
    """The execution day is absent from the store. Asking only the next stored day misses it."""
    calls = []

    def actions(session):
        calls.append(session)
        if session == SKIPPED:
            return CorpActions(session=session, complete=True, tickers=frozenset({"SPY"}),
                               splits_n=1)
        return CorpActions(session=session, complete=True)

    out = _read(_gap(later), actions)
    assert (calls, out["available"], out["quality"], out["phase"], out["drawdown_pct"]) == (
        [SKIPPED], False, "price_basis_discontinuity", "unavailable", None)
    assert drawdown == round(100.0 * (later / 80.0 - 1.0), 4)


@pytest.mark.parametrize("later, drawdown", [
    pytest.param(64.0, -20.0, id="ratio-0.80"),
    pytest.param(60.0, -25.0, id="ratio-0.75"),
])
def test_skipped_session_with_no_named_action_stays_measurable(later, drawdown):
    calls = []

    def actions(session):
        calls.append(session)
        return CorpActions(session=session, complete=True)

    out = _read(_gap(later), actions)
    assert (calls, out["available"], out["phase"], out["quality"], out["drawdown_pct"]) == (
        [SKIPPED, "2026-10-08"], True, "underway", "current", drawdown)


def test_incomplete_guard_on_a_skipped_session_refuses():
    calls = []

    def actions(session):
        calls.append(session)
        if session == SKIPPED:
            return CorpActions(session=session, complete=False, reason="page cap")
        return CorpActions(session=session, complete=True)

    out = _read(_gap(64.0), actions)
    assert (calls, out["available"], out["quality"], out["drawdown_pct"]) == (
        [SKIPPED], False, "corporate_action_guard_down", None)


def test_dividend_only_stored_suspect_is_measurable_and_a_split_count_refuses():
    """100, 100, 85. SPY named, splits_n == 0, dividends_n == 1 is not a basis break."""
    stamps = ("2026-10-07", "2026-10-08", "2026-10-09")

    def run(**guard):
        calls = []

        def actions(session):
            calls.append(session)
            if guard.get("bare"):
                return SimpleNamespace(session=session, complete=True, tickers=frozenset({"SPY"}))
            return CorpActions(session=session, complete=True, tickers=frozenset({"SPY"}),
                               splits_n=guard["splits_n"], dividends_n=guard["dividends_n"])

        out = _read(store(stamps, (100.0, 100.0, 85.0)), actions)
        return calls, out

    calls, out = run(splits_n=0, dividends_n=1)
    assert (calls, out["available"], out["phase"], out["quality"], out["drawdown_pct"], out["close"]) == (
        ["2026-10-09"], True, "underway", "current", -15.0, 85.0)

    calls, out = run(splits_n=1, dividends_n=1)
    assert (calls, out["available"], out["quality"], out["drawdown_pct"]) == (
        ["2026-10-09"], False, "price_basis_discontinuity", None)

    calls, out = run(bare=True)
    assert (calls, out["available"], out["quality"]) == (
        ["2026-10-09"], False, "price_basis_discontinuity")


def _tip_close(price=89.0):
    def fetch(session, wanted):
        assert wanted == {"SPY"}
        return SessionCloses(session=session, closes={"SPY": price}, finalized=True)
    return fetch


def test_tip_dividend_is_appended_and_a_tip_split_is_held():
    landed = store(("2026-10-06", "2026-10-07", "2026-10-08"), (90.0, 88.5, 88.0))

    def read(guard, fetch):
        return licensed_spy_closes(
            EXPECTED, load=lambda ticker: landed, session_closes=fetch, corp_actions=guard)

    dividend = read(
        lambda session: CorpActions(session=session, complete=True, tickers=frozenset({"SPY"}),
                                    splits_n=0, dividends_n=1),
        _tip_close())
    assert dividend.hold is None
    assert dividend.appended == ({"session": "2026-10-09", "settlement": "final"},)
    assert dividend.rows[-1] == ("2026-10-09", 89.0)

    def no_close(*args, **kwargs):
        raise AssertionError("no close may be spliced past a split")

    held = read(
        lambda session: CorpActions(session=session, complete=True, tickers=frozenset({"SPY"}),
                                    splits_n=1, dividends_n=0),
        no_close)
    assert held.hold == "corporate_action_on_session"
    assert held.appended == ()
    assert held.rows[-1][0] == "2026-10-08"

    down = read(
        lambda session: CorpActions(session=session, complete=False, tickers=frozenset({"SPY"}),
                                    splits_n=0, dividends_n=1, reason="page cap"),
        no_close)
    assert down.hold == "corporate_action_guard_down"
    assert down.appended == ()


def _pair_covering(n_sessions, end=EXPECTED):
    """Earlier close plus the ``n_sessions`` NYSE sessions through ``end``."""
    span = []
    day = end
    while len(span) < n_sessions:
        if nyse_calendar.is_session(day):
            span.append(day)
        day -= timedelta(days=1)
    span.reverse()
    earlier = span[0] - timedelta(days=1)
    while not nyse_calendar.is_session(earlier):
        earlier -= timedelta(days=1)
    covered = nyse_calendar.sessions_between(earlier + timedelta(days=1), span[-1])
    assert covered == span and span[-1] == end
    return earlier, span


def test_max_suspects_counts_sessions_inside_one_gap():
    earlier, span = _pair_covering(pb.MAX_SUSPECTS)
    calls = []

    def actions(session):
        calls.append(session)
        return CorpActions(session=session, complete=True)

    got = licensed_spy_closes(
        EXPECTED,
        load=lambda ticker: store((earlier.isoformat(), span[-1].isoformat()), (100.0, 80.0)),
        session_closes=_no_tip, corp_actions=actions)
    assert calls == [day.isoformat() for day in span]
    assert len(calls) == pb.MAX_SUSPECTS
    assert date(2026, 10, 3).isoformat() not in calls  # Saturday inside the span
    assert got.hold is None and got.rows[-1] == (EXPECTED.isoformat(), 80.0)


def test_a_gap_past_max_suspects_refuses_without_a_query():
    earlier, span = _pair_covering(pb.MAX_SUSPECTS + 1)
    assert len(span) == pb.MAX_SUSPECTS + 1
    assert date(2026, 10, 3) not in span and not nyse_calendar.is_session(date(2026, 10, 3))
    calls = []

    def actions(session):
        calls.append(session)
        return CorpActions(session=session, complete=True)

    with pytest.raises(SourceRefused) as refused:
        licensed_spy_closes(
            EXPECTED,
            load=lambda ticker: store((earlier.isoformat(), span[-1].isoformat()), (100.0, 80.0)),
            session_closes=_no_tip, corp_actions=actions)
    assert refused.value.quality == "price_basis_discontinuity"
    assert calls == []
