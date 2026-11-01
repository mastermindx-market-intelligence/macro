"""Impulse-radar + OI-crowding alert emitters (engine/btc_alerts.py).

Verifies the P1 contract: act-tier LEADING crosses emit warnings, two legs
co-firing emit the loud trigger, the OI-crowding de-risk break fires
INDEPENDENT of funding (watch-tier, low-conviction), and ids dedupe. A leg the
radar's re-check has not passed prints as background, never as act tier.

Run: .venv/bin/python -m tests.test_btc_impulse_alerts
"""
from __future__ import annotations

import inspect
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine import alert_triage  # noqa: E402
from engine import btc_alerts as A  # noqa: E402
from engine import btc_impulse_radar  # noqa: E402
from engine import btc_impulse_radar_backtest  # noqa: E402
from lib import config  # noqa: E402


def _with_fire_series(fires, fn):
    orig = btc_impulse_radar.fire_series
    btc_impulse_radar.fire_series = lambda s=None: fires
    try:
        return fn()
    finally:
        btc_impulse_radar.fire_series = orig


GATE_LEADING = {"asof": "2026-10-17", "legs": {k: {"status": "leading"} for k in ("d2", "d3", "u1")}}
# The shape of data/vector/impulse_legs_gate.json as of 2026-10-17.
GATE_REAL_SHAPE = {"asof": "2026-10-17", "all_pass": False,
                   "legs": {"d2": {"status": "demoted"}, "d3": {"status": "demoted"},
                            "u1": {"status": "insufficient_n"}}}


def _with_gate(gate, fn):
    orig = btc_impulse_radar_backtest.load_gate
    btc_impulse_radar_backtest.load_gate = lambda: gate
    try:
        return fn()
    finally:
        btc_impulse_radar_backtest.load_gate = orig


def _crosses(gate):
    """d2 and d3 co-fire on one day (two warnings and the trigger), u1 fires later."""
    idx = pd.date_range("2025-01-01", periods=12, freq="D")
    d2 = pd.Series(False, index=idx); d2.iloc[5] = True
    d3 = pd.Series(False, index=idx); d3.iloc[5] = True
    u1 = pd.Series(False, index=idx); u1.iloc[8] = True
    fires = pd.DataFrame({"d2": d2, "d3": d3, "u1": u1})
    sig = pd.DataFrame({"close": pd.Series(60000.0, index=idx)})
    return _with_gate(gate, lambda: _with_fire_series(fires, lambda: A.impulse_radar_events(sig)))


def test_act_warnings_trigger_and_up_and_dedup():
    evs = _crosses(GATE_LEADING)

    by_type = {}
    for e in evs:
        by_type.setdefault(e["type"], []).append(e)
    assert "impulse_warn_down" in by_type and "impulse_trigger_down" in by_type
    assert "impulse_warn_up" in by_type
    # down warnings + trigger are act-tier high; up is act-tier medium
    assert all(e["tier"] == "act" for e in evs)
    assert by_type["impulse_warn_down"][0]["severity"] == "high"
    assert by_type["impulse_warn_up"][0]["severity"] == "medium"
    # each carries an honest edge string + zh
    assert all(e["edge"] and e["headline_zh"] for e in evs)
    # ids are unique (idempotent dedupe key)
    ids = [e["id"] for e in evs]
    assert len(ids) == len(set(ids))


def test_gated_legs_print_as_background_not_act():
    """What a reader was told to act on: all three legs are gated on the real file's shape."""
    evs = _crosses(GATE_REAL_SHAPE)
    assert sorted(e["type"] for e in evs) == ["impulse_trigger_down", "impulse_warn_down",
                                              "impulse_warn_down", "impulse_warn_up"]
    assert all(e["tier"] == "context" and e["severity"] == "info" for e in evs)
    for e in evs:
        en = " ".join((e["headline"], e["detail"], e["edge"])).lower()
        zh = "".join((e["headline_zh"], e["detail_zh"], e["edge_zh"]))
        for word in ("de-risk", "act early", "trigger", "bounce", "leading", "top-exhaustion", "wash-out"):
            assert word not in en, (e["id"], word)
        for word in ("减仓", "尽早", "反弹", "领先", "顶部衰竭", "洗盘"):
            assert word not in zh, (e["id"], word)
        assert "Research-stage" in e["headline"] and "研究阶段" in e["headline_zh"]
        assert "as of 2026-10-17" in e["edge"] and "截至 2026-10-17" in e["edge_zh"]
        assert "BTC $60,000." in e["detail"] and "BTC $60,000." in e["detail_zh"]


def test_gated_edge_states_the_verdict_for_its_leg():
    by_leg = {e["id"].rsplit(":", 1)[1]: e for e in _crosses(GATE_REAL_SHAPE)}
    assert "lift floor or permutation test" in by_leg["d2"]["edge"]
    assert "提升下限或置换检验" in by_leg["d2"]["edge_zh"]
    assert "too few" in by_leg["u1"]["edge"] and "触发次数不足" in by_leg["u1"]["edge_zh"]
    assert "one of these legs" in by_leg["d2d3"]["edge"] and "其中一条腿" in by_leg["d2d3"]["edge_zh"]


def test_gated_row_leaves_the_home_feed_and_the_act_verbs():
    """The two places the tier and severity turn into a prompt on a reader's screen."""
    home = config.load()["home"]["alerts"]["vector_major_severities"]
    for e in _crosses(GATE_REAL_SHAPE):
        assert e["severity"] not in home
        band = alert_triage.severity_band(e["tier"], e["severity"])
        assert band == "minor"
        assert alert_triage.action_for(e["tier"], band, "") == ("context", "背景")
    for e in _crosses(GATE_LEADING):
        assert e["severity"] in home
        band = alert_triage.severity_band(e["tier"], e["severity"])
        assert alert_triage.action_for(e["tier"], band, "")[0] in ("high-conviction", "reduce risk")


def test_co_fire_is_gated_when_either_leg_is():
    gate = {"legs": {"d2": {"status": "leading"}, "d3": {"status": "demoted"}, "u1": {"status": "leading"}}}
    by_leg = {e["id"].rsplit(":", 1)[1]: e for e in _crosses(gate)}
    assert by_leg["d2"]["tier"] == "act"
    assert by_leg["u1"]["tier"] == "act"
    assert by_leg["d3"]["tier"] == "context"
    assert by_leg["d2d3"]["tier"] == "context"


def test_absent_gate_keeps_act_tier_as_the_gauge_does():
    assert all(e["tier"] == "act" for e in _crosses({}))
    assert all(e["tier"] == "act" for e in _crosses({"legs": {"d2": {}, "d3": {}, "u1": {}}}))


def test_stored_rows_read_back_gated_and_nothing_else_changes():
    """The stored log is what triage and the home feed read between rebuilds."""
    stored = _crosses(GATE_LEADING)
    other = {"id": "risk_regime:2025-01-02T00:00:high_risk", "ts": "2025-01-02T00:00:00", "source": "vector",
             "type": "risk_regime", "severity": "high", "tier": "act", "headline": "h", "detail": "d",
             "context": {"leg": "d2", "price": 1}}
    orig = A._path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "alerts.jsonl"
        p.write_text("".join(json.dumps(e) + "\n" for e in stored + [other]))
        A._path = lambda: p
        try:
            rows = _with_gate(GATE_REAL_SHAPE, A.load_events)
            leading = _with_gate(GATE_LEADING, A.load_events)
        finally:
            A._path = orig
    assert [r["id"] for r in rows] == [e["id"] for e in stored] + [other["id"]]
    assert all(r["tier"] == "context" and r["severity"] == "info" for r in rows[:-1])
    assert rows[-1] == other
    assert leading == stored + [other]


def test_gating_a_row_twice_changes_nothing():
    once = _crosses(GATE_REAL_SHAPE)
    twice = _with_gate(GATE_REAL_SHAPE, lambda: A._apply_leg_gate([dict(e) for e in once]))
    assert twice == once


def test_the_bell_uses_the_gauges_statuses():
    assert btc_impulse_radar.GATED_STATUSES == ("demoted", "insufficient_n")
    orig = btc_impulse_radar.GATED_STATUSES
    btc_impulse_radar.GATED_STATUSES = ("demoted",)
    try:
        by_leg = {e["id"].rsplit(":", 1)[1]: e for e in _crosses(GATE_REAL_SHAPE)}
    finally:
        btc_impulse_radar.GATED_STATUSES = orig
    assert by_leg["u1"]["tier"] == "act"
    assert by_leg["d2"]["tier"] == "context"


def _board(gate):
    """The board a reader gets when these rows are the stored log."""
    stored = _crosses(GATE_LEADING)
    orig = A._path
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "alerts.jsonl"
        p.write_text("".join(json.dumps(e) + "\n" for e in stored))
        A._path = lambda: p
        try:
            payload = _with_gate(gate, lambda: alert_triage.build_triage(today=date(2025, 1, 15), max_items=100000))
        finally:
            A._path = orig
    return {a["type"]: a for a in payload["alerts"] if a["source"] == "vector"}


def test_gated_row_does_not_carry_the_calibrated_pill():
    """The page prints validation.verdict as a pill beside the row's note. CALIBRATED beside
    "scores this leg zero" would tell the reader two opposite things."""
    board = _board(GATE_REAL_SHAPE)
    assert set(board) == {"impulse_warn_down", "impulse_trigger_down", "impulse_warn_up"}
    assert board["impulse_warn_down"]["validation"]["verdict"] == "no_edge"
    assert board["impulse_trigger_down"]["validation"]["verdict"] == "no_edge"
    assert board["impulse_warn_up"]["validation"]["verdict"] == "underpowered"
    for a in board.values():
        assert a["tier"] == "context" and a["action"] == "context"
        assert a["validation"]["backtested"] is False
        assert a["validation"]["note"] == a["edge"] and "zero" in a["edge"]
        assert a["validation"]["note_zh"] == a["edge_zh"] and "归零" in a["edge_zh"]


def test_a_leg_that_passes_keeps_its_pill():
    board = _board(GATE_LEADING)
    assert set(board) == {"impulse_warn_down", "impulse_trigger_down", "impulse_warn_up"}
    for a in board.values():
        assert a["tier"] == "act"
        assert a["validation"]["verdict"] == "calibrated"
        assert "leg_gate" not in a


def test_gated_row_stays_under_the_push_floor():
    """scripts/push_alerts.py sends every board row at or above alert_push.threshold. A leg the
    re-check has not passed must not go out as a message; one that passes still does."""
    floor = inspect.signature(alert_triage.push_priority_alerts).parameters["threshold"].default
    assert all(a["priority"] < floor for a in _board(GATE_REAL_SHAPE).values())
    assert all(a["priority"] >= floor for a in _board(GATE_LEADING).values())


def test_every_gated_status_has_its_own_pill():
    assert set(alert_triage._LEG_GATE_VERDICT) == set(btc_impulse_radar.GATED_STATUSES)
    args = ("vector", "impulse_warn_down", "edge", "边际", {}, {}, "")
    assert alert_triage._validation(*args)["verdict"] == "calibrated"
    assert alert_triage._validation(*args, leg_gate="a_status_added_later")["verdict"] == "documented"


def test_named_copy_carries_no_banned_word():
    ban = ("实时", "经验证", "已验证", "validated")
    lines = [A._edge_zh_from_verdict("CONFIRMED"), A._edge_from_verdict("CONFIRMED")]
    for type_ in ("flash_crash", "override_release", "oi_crowding_derisk"):
        conv = A._conviction(type_)
        lines += [conv["edge"], conv["edge_zh"]]
    assert all(line for line in lines)
    for line in lines:
        for word in ban:
            assert word not in line, (word, line)


def test_no_event_when_no_cross():
    idx = pd.date_range("2025-01-01", periods=10, freq="D")
    fires = pd.DataFrame({"d2": pd.Series(False, index=idx),
                          "d3": pd.Series(False, index=idx),
                          "u1": pd.Series(False, index=idx)})
    sig = pd.DataFrame({"close": pd.Series(60000.0, index=idx)})
    assert _with_fire_series(fires, lambda: A.impulse_radar_events(sig)) == []


def test_oi_crowding_fires_independent_of_funding():
    """OI crossing into elevated must emit a watch-tier de-risk nudge even with
    NO funding columns present — the funding-AND gate is broken."""
    n = 320
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    ratio = np.full(n, 0.012)
    ratio[-40:] = np.linspace(0.012, 0.05, 40)          # OI ramps into the top of its window
    sig = pd.DataFrame({
        "close": pd.Series(60000.0, index=idx),
        "oi_mcap_ratio": pd.Series(ratio, index=idx),
        "oi_change": pd.Series(0.01, index=idx),         # building (positive)
        # NOTE: deliberately NO funding columns -> proves funding-independence
    }, index=idx)
    evs = A.leverage_derisk_events(sig)
    assert evs, "expected an OI-crowding de-risk event from rising OI without funding"
    e = evs[-1]
    assert e["type"] == "oi_crowding_derisk"
    assert e["tier"] == "watch"                          # low-conviction, NOT act-tier
    assert "low-conviction" in e["edge"].lower()
    assert e["context"]["oi_state"] in ("elevated", "stretched")


def test_oi_declining_is_not_crowded():
    n = 320
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    ratio = np.full(n, 0.012); ratio[-40:] = np.linspace(0.012, 0.05, 40)
    sig = pd.DataFrame({
        "close": pd.Series(60000.0, index=idx),
        "oi_mcap_ratio": pd.Series(ratio, index=idx),
        "oi_change": pd.Series(-0.01, index=idx),        # DECLINING -> state 'declining', never crowded
    }, index=idx)
    assert A.leverage_derisk_events(sig) == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
