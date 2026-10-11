"""The basket-washout state cannot travel backward through a short/partial tape.

These cases guard the insertion-index aliasing bug: if the artifact's as_of and
the marker's confirmed_date both resolve to the final index insertion position,
the old subtraction returned zero instead of refusing future information.
"""
from __future__ import annotations

import pandas as pd

from engine import signal_quality as sq


def _qualifier(as_of: str) -> dict:
    return {
        "group_id": "test-sector",
        "basis": "sector",
        "peer_dd": -0.25,
        "as_of": as_of,
    }


def test_future_artifact_after_last_loaded_session_refused():
    sessions = pd.bdate_range("2026-10-01", periods=6)
    known_date = str(sessions[-1].date())
    future_artifact = "2026-10-19"
    assert pd.Timestamp(future_artifact) > pd.Timestamp(known_date)

    # Both timestamps previously collapsed to index insertion position len(sessions).
    assert sq._sessions_since(sessions, future_artifact, known_date) is None
    assert sq.reclaim_waiver_for(
        _qualifier(future_artifact), known_date, sessions
    ) is None


def test_future_artifact_cannot_convert_countertrend_reclaim_refusal():
    sessions = pd.bdate_range("2007-01-01", periods=30)
    known_date = str(sessions[-1].date())
    waiver = sq.reclaim_waiver_for(_qualifier("2026-10-19"), known_date, sessions)
    assert waiver is None

    # Hold passes, but there is no MA200 reclaim on either confirmation bar.
    frame = pd.DataFrame({
        "close": [10.0, 11.0, 11.0],
        "above200": [False, False, False],
        "w_bull": [False, False, False],
    })
    verdict, reason = sq._confirm_legs(0, frame, len(frame), waiver=waiver)
    assert verdict is False
    assert reason == sq.CT_RECLAIM_FAIL


def test_valid_same_session_and_recent_state_still_accepted():
    sessions = pd.bdate_range("2026-09-01", periods=30)
    known_date = str(sessions[-1].date())
    same = sq.reclaim_waiver_for(_qualifier(known_date), known_date, sessions)
    assert same is not None and same.stale_sessions == 0

    five_sessions_ago = str(sessions[-6].date())
    five = sq.reclaim_waiver_for(_qualifier(five_sessions_ago), known_date, sessions)
    assert five is not None
    assert five.stale_sessions == sq.WASHOUT_MAX_STALE_SESSIONS


def test_stale_state_still_refused_after_boundary_fix():
    sessions = pd.bdate_range("2026-09-01", periods=30)
    known_date = str(sessions[-1].date())
    six_sessions_ago = str(sessions[-7].date())
    assert sq.reclaim_waiver_for(
        _qualifier(six_sessions_ago), known_date, sessions
    ) is None
