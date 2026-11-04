"""Kills for US pullback mutants the existing suites leave alive.

Synthetic stores and guard objects only. No network and no source files.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

from engine.close_pass.massive_close import CorpActions, SessionCloses
from lib import nyse_calendar
from lib import us_pullback_observation as pb
from lib.us_pullback_observation import (
    LicensedCloses, SourceRefused, licensed_spy_closes, snapshot,
)


EXPECTED = date(2026, 10, 9)


def store(stamps=("2026-10-06", "2026-10-07", "2026-10-08"), closes=(90.0, 88.5, 88.0),
          column="close"):
    return pd.DataFrame({column: list(closes)}, index=pd.to_datetime(list(stamps)))


def _landed(closes, stamps=("2026-10-07", "2026-10-08", "2026-10-09")):
    return lambda ticker: store(stamps=stamps, closes=closes)


def _sessions_ending(n, end=EXPECTED):
    found = []
    day = end
    while len(found) < n:
        if nyse_calendar.is_session(day):
            found.append(day.isoformat())
        day -= timedelta(days=1)
    return tuple(reversed(found))


def _recording(factory):
    calls = []

    def actions(session):
        calls.append(session)
        return factory(session)

    return calls, actions


def _quiet(session):
    return CorpActions(session=session, complete=True)


def final_close(price=89.0):
    def fetch(session, wanted):
        return SessionCloses(session=session, closes={"SPY": price}, finalized=True)
    return fetch


def _stub_observer(rows, *, expected_session, is_session):
    return {"schema": "pullback_observation.v1", "available": False,
            "quality": "stub", "phase": "unavailable"}


class _NoOffsetClock(datetime):
    """tzinfo is set, but the offset itself is missing."""

    def utcoffset(self):
        return None


def test_ratio_exactly_at_suspect_low_is_not_corroborated():
    """0.88 is the inclusive edge of the band; size alone does not call the guard."""
    calls, actions = _recording(_quiet)
    got = licensed_spy_closes(
        EXPECTED, load=_landed((100.0, 100.0, 88.0)),
        session_closes=final_close(), corp_actions=actions)
    assert calls == []
    assert got.hold is None and got.rows[-1] == ("2026-10-09", 88.0)


def test_ratio_exactly_at_the_reciprocal_ceiling_is_not_corroborated():
    """100/88 == 1/0.88 stays inside the band."""
    calls, actions = _recording(_quiet)
    got = licensed_spy_closes(
        EXPECTED, load=_landed((88.0, 88.0, 100.0)),
        session_closes=final_close(), corp_actions=actions)
    assert calls == []
    assert got.hold is None and got.rows[-1] == ("2026-10-09", 100.0)


def test_a_move_above_the_unrounded_reciprocal_is_corroborated():
    """114/100 = 1.14 sits above 1/0.88 and below the hard 4:3 ceiling."""
    calls, actions = _recording(_quiet)
    got = licensed_spy_closes(
        EXPECTED, load=_landed((100.0, 100.0, 114.0)),
        session_closes=final_close(), corp_actions=actions)
    assert calls == ["2026-10-09"]
    assert got.hold is None and got.rows[-1] == ("2026-10-09", 114.0)


def test_a_ratio_that_only_clears_the_band_after_rounding_stays_a_suspect():
    """87.995/100 is below 0.88; rounding it to 4 dp must not launder it."""
    ratio = 87.995 / 100.0
    assert ratio < pb.SUSPECT_LOW <= round(ratio, 4)
    calls, actions = _recording(_quiet)
    licensed_spy_closes(
        EXPECTED, load=_landed((100.0, 100.0, 87.995)),
        session_closes=final_close(), corp_actions=actions)
    assert calls == ["2026-10-09"]


def test_a_print_after_the_expected_session_is_not_a_stored_suspect():
    """Rows past ``expected`` are outside the stored window the guard corroborates."""
    calls, actions = _recording(_quiet)
    got = licensed_spy_closes(
        EXPECTED,
        load=_landed((100.0, 100.0, 100.0, 80.0),
                     stamps=("2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12")),
        session_closes=final_close(), corp_actions=actions)
    assert calls == []
    assert got.hold is None


def test_a_non_positive_stored_print_is_skipped_not_corroborated():
    """Adjacency matches level_break: only dated positive closes are paired."""
    calls, actions = _recording(_quiet)
    got = licensed_spy_closes(
        EXPECTED, load=_landed((100.0, -5.0, 97.0)),
        session_closes=final_close(), corp_actions=actions)
    assert calls == []
    assert got.hold is None
    assert ("2026-10-08", -5.0) in [(label, price) for label, price in got.rows]


def test_a_repeated_suspect_session_is_queried_once():
    calls, actions = _recording(_quiet)
    # Equal sessions sort by price, so both prints stay inside the hard band
    # (0.80 and 1.25) and both steps still name 2026-10-08.
    frame = store(stamps=("2026-10-07", "2026-10-08", "2026-10-08", "2026-10-09"),
                  closes=(100.0, 80.0, 100.0, 100.0))
    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: frame,
        session_closes=final_close(), corp_actions=actions)
    assert calls == ["2026-10-08"]
    assert got.hold is None


def test_suspect_pairs_follow_session_order_not_store_order():
    calls, actions = _recording(_quiet)
    got = licensed_spy_closes(
        EXPECTED,
        load=_landed((64.0, 80.0, 80.0),
                     stamps=("2026-10-09", "2026-10-07", "2026-10-08")),
        session_closes=final_close(), corp_actions=actions)
    assert calls == ["2026-10-09"]
    assert got.hold is None


def _suspect_closes(n_ratios):
    closes = [256.0]
    for _ in range(n_ratios):
        closes.append(closes[-1] * 0.875)
    return tuple(closes)


def test_exactly_eight_suspects_are_corroborated_rather_than_refused():
    closes = _suspect_closes(8)
    calls, actions = _recording(_quiet)
    got = licensed_spy_closes(
        EXPECTED, load=_landed(closes, stamps=_sessions_ending(len(closes))),
        session_closes=final_close(), corp_actions=actions)
    assert len(calls) == 8
    assert got.hold is None


def test_nine_suspects_refuse_without_calling_the_guard():
    closes = _suspect_closes(9)
    calls, actions = _recording(_quiet)
    with pytest.raises(SourceRefused) as refused:
        licensed_spy_closes(
            EXPECTED, load=_landed(closes, stamps=_sessions_ending(len(closes))),
            session_closes=final_close(), corp_actions=actions)
    assert refused.value.quality == "price_basis_discontinuity"
    assert calls == []


def test_four_unlanded_sessions_are_a_stalled_store():
    def no_network(*args, **kwargs):
        raise AssertionError("four sessions behind must not be patched")

    got = licensed_spy_closes(
        EXPECTED,
        load=lambda ticker: store(stamps=("2026-10-02", "2026-10-05"), closes=(90.0, 89.0)),
        session_closes=no_network, corp_actions=no_network)
    assert got.hold == "store_behind"
    assert got.appended == ()
    assert [row[0] for row in got.rows] == ["2026-10-02", "2026-10-05"]


def test_a_provisional_tip_stops_before_the_next_session():
    asked = []

    def fetch(session, wanted):
        asked.append(session)
        if session == "2026-10-08":
            return SessionCloses(session=session, closes={"SPY": 88.0}, finalized=False)
        return SessionCloses(session=session, closes={"SPY": 89.0}, finalized=True)

    got = licensed_spy_closes(
        EXPECTED,
        load=lambda ticker: store(stamps=("2026-10-06", "2026-10-07"), closes=(90.0, 89.0)),
        session_closes=fetch, corp_actions=lambda session: CorpActions(session=session, complete=True))
    assert asked == ["2026-10-08"]
    assert got.hold == "session_close_provisional"
    assert got.appended == ()
    assert got.rows[-1][0] == "2026-10-07"


def test_a_tip_missing_finalized_is_provisional():
    def fetch(session, wanted):
        return SimpleNamespace(session=session, closes={"SPY": 89.0})

    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: store(), session_closes=fetch,
        corp_actions=lambda session: CorpActions(session=session, complete=True))
    assert got.hold == "session_close_provisional"
    assert got.appended == ()
    assert got.rows[-1][0] == "2026-10-08"


def test_only_boolean_true_counts_as_a_settled_tip():
    def fetch(session, wanted):
        return SessionCloses(session=session, closes={"SPY": 89.0}, finalized=1)

    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: store(), session_closes=fetch,
        corp_actions=lambda session: CorpActions(session=session, complete=True))
    assert got.hold == "session_close_provisional"
    assert got.appended == ()


def test_a_tip_guard_missing_complete_holds_without_a_close():
    def no_close(*args, **kwargs):
        raise AssertionError("no close may be spliced past a guard with no complete flag")

    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: store(), session_closes=no_close,
        corp_actions=lambda session: SimpleNamespace())
    assert got.hold == "corporate_action_guard_down"
    assert got.appended == ()


def test_a_stored_guard_missing_complete_refuses():
    calls = []

    def actions(session):
        calls.append(session)
        return SimpleNamespace(tickers=frozenset())

    with pytest.raises(SourceRefused) as refused:
        licensed_spy_closes(
            EXPECTED, load=_landed((80.0, 64.0, 64.0)),
            session_closes=final_close(), corp_actions=actions)
    assert refused.value.quality == "corporate_action_guard_down"
    assert calls == ["2026-10-08"]


def test_a_tip_guard_missing_tickers_does_not_invent_an_action():
    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: store(), session_closes=final_close(),
        corp_actions=lambda session: SimpleNamespace(complete=True))
    assert got.hold is None
    assert got.appended == ({"session": "2026-10-09", "settlement": "final"},)
    assert got.rows[-1] == ("2026-10-09", 89.0)


def test_a_stored_guard_missing_tickers_leaves_the_move_measurable():
    calls = []

    def actions(session):
        calls.append(session)
        return SimpleNamespace(complete=True)

    got = licensed_spy_closes(
        EXPECTED, load=_landed((80.0, 64.0, 64.0)),
        session_closes=final_close(), corp_actions=actions)
    assert calls == ["2026-10-08"]
    assert got.hold is None and got.rows[-1] == ("2026-10-09", 64.0)


def test_an_incomplete_stored_guard_that_names_the_benchmark_is_guard_down():
    """Completeness is checked first: an unfinished ticker list is not a basis refusal."""
    def actions(session):
        return CorpActions(session=session, complete=False, tickers=frozenset({"SPY"}))

    with pytest.raises(SourceRefused) as refused:
        licensed_spy_closes(
            EXPECTED, load=_landed((80.0, 64.0, 64.0)),
            session_closes=final_close(), corp_actions=actions)
    assert refused.value.quality == "corporate_action_guard_down"


def test_an_incomplete_tip_guard_that_names_the_benchmark_is_guard_down():
    def no_close(*args, **kwargs):
        raise AssertionError("no close may be spliced past an incomplete guard")

    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: store(), session_closes=no_close,
        corp_actions=lambda session: CorpActions(
            session=session, complete=False, tickers=frozenset({"SPY"})))
    assert got.hold == "corporate_action_guard_down"
    assert got.appended == ()


def test_a_session_close_with_no_closes_mapping_is_held():
    def fetch(session, wanted):
        return SessionCloses(session=session, closes=None, finalized=True)

    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: store(), session_closes=fetch,
        corp_actions=lambda session: CorpActions(session=session, complete=True))
    assert got.hold == "session_close_unavailable"
    assert got.appended == ()
    assert got.rows[-1][0] == "2026-10-08"


def test_an_omitted_action_guard_is_still_filled_when_the_reader_is_injected(monkeypatch):
    from engine.close_pass import massive_close
    calls = []

    def actions(session):
        calls.append(session)
        return CorpActions(session=session, complete=True)

    def forbidden(*args, **kwargs):
        raise AssertionError("the injected session reader must stay injected")

    monkeypatch.setattr(massive_close, "corp_action_tickers", actions)
    monkeypatch.setattr(massive_close, "fetch_session_closes", forbidden)
    got = licensed_spy_closes(
        EXPECTED, load=lambda ticker: store(), session_closes=final_close(),
        corp_actions=None)
    assert calls == ["2026-10-09"]
    assert got.hold is None and got.rows[-1] == ("2026-10-09", 89.0)


def test_a_clock_whose_offset_is_missing_is_refused():
    now = _NoOffsetClock(2026, 10, 9, 22, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="aware datetime"):
        snapshot(now=now,
                 read=lambda expected: LicensedCloses(rows=[("2026-10-09", 100.0)]),
                 observer=_stub_observer)


def test_an_omitted_clock_is_the_current_utc_instant():
    before = datetime.now(timezone.utc)
    out = snapshot(
        read=lambda expected: LicensedCloses(rows=[("2026-01-05", 100.0)]),
        observer=_stub_observer)
    after = datetime.now(timezone.utc)
    produced = datetime.fromisoformat(out["produced_at"])
    assert before <= produced <= after
    assert produced.utcoffset() == timedelta(0)
    assert out["clock"] == "settled_close"
    assert out["valid_until"]
