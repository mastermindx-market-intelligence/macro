"""Regression: a newly written nightly Prophet ledger close reaches the SAME index build.

This is a pure in-memory projection test; the canonical ledger advancer remains
the only writer and index count/lifecycle tests cover downstream aggregates.
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import scripts.build_prophet as bp  # noqa: E402


def _open(plan_id: str = "A-20261023") -> dict:
    return {
        "id": plan_id,
        "closed": False,
        "phase": "triggered",
        "clock_age_days": 8,
        "pulse": "8d · triggered",
        "pulse_zh": "8天 · 已触发",
        "what_to_do_now": ["Buy above trigger"],
        "what_to_do_now_zh": ["突破触发价买入"],
        "recommended_action": "buy",
        "state": {"recommended_action": "buy", "phase": "triggered"},
    }


def test_new_close_reconciles_both_languages_and_withholds_live_action():
    entry = _open()
    rows = [entry]
    bp._reconcile_same_build_closures(rows, {"A-20261023": "INVALIDATED"})
    assert entry["closed"] is True
    assert entry["pulse"] == bp._plan_pulse(8, "triggered", None, closed=True, outcome="INVALIDATED")[0]
    assert entry["pulse_zh"] == bp._plan_pulse(8, "triggered", None, closed=True, outcome="INVALIDATED")[1]
    assert entry["what_to_do_now"] == bp._closed_state_lines("INVALIDATED")[0]
    assert entry["what_to_do_now_zh"] == bp._closed_state_lines("INVALIDATED")[1]
    assert "Buy above" not in repr(entry)
    assert entry["recommended_action"] is None
    assert entry["state"]["recommended_action"] is None


def test_still_open_and_already_closed_are_not_rewritten():
    opened = _open("OPEN")
    closed = _open("ALREADY")
    closed.update(closed=True, pulse="existing historical pulse",
                  recommended_action=None)
    before = [dict(opened), dict(closed)]
    bp._reconcile_same_build_closures([opened, closed], {"ALREADY": "T1_HIT"})
    assert opened == before[0]
    assert closed == before[1]


def test_missing_id_and_unknown_outcome_degrade_safely():
    missing = _open("")
    fresh = _open("NEW")
    bp._reconcile_same_build_closures([missing, fresh], {"": "EXPIRED", "NEW": ""})
    assert missing["closed"] is False
    assert fresh["closed"] is True
    assert fresh["what_to_do_now"] == bp._closed_state_lines("")[0]
    assert fresh["what_to_do_now_zh"] == bp._closed_state_lines("")[1]
    assert fresh["recommended_action"] is None
