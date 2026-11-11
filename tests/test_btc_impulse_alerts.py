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
from datetime import date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from engine import alert_triage  # noqa: E402
from engine import btc_alerts as A  # noqa: E402
from engine import btc_impulse_radar  # noqa: E402
from engine import signal_evidence as E  # noqa: E402
from engine import btc_impulse_radar_backtest  # noqa: E402
from lib import config  # noqa: E402


def _with_fire_series(fires, fn):
    orig = btc_impulse_radar.fire_series
    btc_impulse_radar.fire_series = lambda s=None: fires
    try:
        return fn()
    finally:
        btc_impulse_radar.fire_series = orig


def _gate(*, d2="leading", d3="leading", u1="leading", asof="2025-01-12"):
    specs = {
        "d2": ("down", 1.5, "Vol-of-vol jolt (DVOL range)"),
        "d3": ("down", 1.3, "SOPR profit-take spike"),
        "u1": ("up", 1.3, "SOPR capitulation (wash-out)"),
    }
    statuses = {"d2": d2, "d3": d3, "u1": u1}
    return {
        "ok": True, "asof": asof, "all_pass": False,
        "holdout_start": "2024-01-01", "label": "fwd(3d) +-5%",
        "legs": {
            key: {
                "status": status, "pass": status == "leading", "dir": specs[key][0],
                "label": specs[key][2], "floor": specs[key][1], "min_holdout_n": 30,
                "lift_holdout": 2.0, "perm_p": 0.01, "n_fires_holdout": 40,
            }
            for key, status in statuses.items()
        },
    }


GATE_LEADING = _gate()
GATE_REAL_SHAPE = _gate(d2="demoted", d3="demoted", u1="insufficient_n")

def _with_gate(gate, fn):
    orig = E.load_btc_gate
    E.load_btc_gate = lambda: gate
    try:
        return fn()
    finally:
        E.load_btc_gate = orig


def _crosses(gate):
    """All four observations are current on the explicitly bound board day."""
    idx = pd.date_range("2025-01-01", periods=12, freq="D")
    fires = pd.DataFrame({key: [False] * 11 + [True] for key in ("d2", "d3", "u1")}, index=idx)
    sig = pd.DataFrame({"close": pd.Series(60000.0, index=idx)})
    return _with_fire_series(fires, lambda: A.impulse_radar_events(
        sig, gate=gate, board_date=date(2025, 1, 12)))


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
        assert e["validation_asof"] == "2025-01-12"
        assert e["evidence"]["claim_eligible"] is False
        assert "BTC $60,000." in e["detail"] and "BTC $60,000." in e["detail_zh"]


def test_gated_edge_states_the_verdict_for_its_leg():
    by_leg = {e["id"].rsplit(":", 1)[1]: e for e in _crosses(GATE_REAL_SHAPE)}
    for key in ("d2", "d3", "d2d3"):
        assert by_leg[key]["evidence"]["status"] == "demoted"
        assert "demoted" in by_leg[key]["edge"] and "降级" in by_leg[key]["edge_zh"]
    assert by_leg["u1"]["evidence"]["status"] == "insufficient_n"
    assert "too small" in by_leg["u1"]["edge"] and "样本不足" in by_leg["u1"]["edge_zh"]


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
    gate = _gate(d3="demoted")
    by_leg = {e["id"].rsplit(":", 1)[1]: e for e in _crosses(gate)}
    assert by_leg["d2"]["tier"] == "act"
    assert by_leg["u1"]["tier"] == "act"
    assert by_leg["d3"]["tier"] == "context"
    assert by_leg["d2d3"]["tier"] == "context"


def test_absent_or_labels_only_gate_cannot_grant_action():
    for gate in ({}, {"legs": {key: {"status": "leading"} for key in ("d2", "d3", "u1")}}):
        events = _crosses(gate)
        assert len(events) == 4
        assert all(e["tier"] == "context" and e["severity"] == "info" for e in events)
        assert all(e["claim_eligible"] is False and not e["forward"] for e in events)


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
            rows = A.load_events(gate=GATE_REAL_SHAPE, board_date=date(2025, 1, 12))
            leading = A.load_events(gate=GATE_LEADING, board_date=date(2025, 1, 12))
            assert p.read_text() == "".join(json.dumps(e) + "\n" for e in stored + [other])
        finally:
            A._path = orig
    assert [r["id"] for r in rows] == [e["id"] for e in stored] + [other["id"]]
    assert all(r["tier"] == "context" and r["severity"] == "info" for r in rows[:-1])
    assert rows[-1] == other
    assert leading == stored + [other]


def test_gating_a_row_twice_changes_nothing():
    once = _crosses(GATE_REAL_SHAPE)
    twice = A._apply_leg_gate([dict(e) for e in once], gate=GATE_REAL_SHAPE, board_date=date(2025, 1, 12))
    assert twice == once


def test_legacy_status_vocabulary_cannot_override_current_permission():
    assert btc_impulse_radar.GATED_STATUSES == ("demoted", "insufficient_n")
    orig = btc_impulse_radar.GATED_STATUSES
    btc_impulse_radar.GATED_STATUSES = ("demoted",)
    try:
        by_leg = {e["id"].rsplit(":", 1)[1]: e for e in _crosses(GATE_REAL_SHAPE)}
    finally:
        btc_impulse_radar.GATED_STATUSES = orig
    assert by_leg["u1"]["tier"] == "context"
    assert by_leg["u1"]["evidence"]["status"] == "insufficient_n"
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
            payload = _with_gate(gate, lambda: alert_triage.build_triage(today=date(2025, 1, 12), max_items=100000))
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
        assert a["validation"]["current_status"] == a["evidence"]["status"]
        assert a["validation"]["current_permitted"] is False
        assert a["validation"]["note"] and a["validation"]["note_zh"]


def test_a_leg_that_passes_keeps_its_pill():
    board = _board(GATE_LEADING)
    assert set(board) == {"impulse_warn_down", "impulse_trigger_down", "impulse_warn_up"}
    for a in board.values():
        assert a["tier"] == "act"
        assert a["validation"]["verdict"] == "backtested"
        assert a["validation"]["current_permitted"] is True
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
    assert alert_triage._validation(*args)["verdict"] == "documented"
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


def test_demoted_fire_keeps_id_but_loses_action_authority():
    idx = pd.date_range("2025-01-01", periods=12, freq="D")
    fires = pd.DataFrame({
        "d2": pd.Series([False] * 11 + [True], index=idx),
        "d3": pd.Series(False, index=idx),
        "u1": pd.Series(False, index=idx),
    })
    sig = pd.DataFrame({"close": pd.Series(60000.0, index=idx)})
    evs = _with_fire_series(
        fires,
        lambda: A.impulse_radar_events(
            sig, gate=_gate(d2="demoted"), board_date=idx[-1].date()
        ),
    )
    assert len(evs) == 1
    e = evs[0]
    assert e["id"] == "impulse_warn_down:2025-01-12T00:00:d2"
    assert e["context"]["leg"] == "d2"
    assert e["signal_id"] == "btc_impulse.d2"
    assert e["tier"] == "context"
    assert e["observed_tier"] == "act"
    assert e["evidence"]["status"] == "demoted"
    assert e["evidence"]["claim_eligible"] is False
    assert "verified leading" not in e["edge"].lower()

def test_current_reader_freezes_one_gate_and_preserves_issue_claim_before_overlay(monkeypatch, tmp_path):
    row = _crosses(GATE_LEADING)[0]
    row.pop("original_claim")
    row["edge"] = "Historical predictive claim"
    row["forward"] = "Historical action instruction"
    path = tmp_path / "alerts.jsonl"
    before = json.dumps(row) + "\n"
    path.write_text(before)
    monkeypatch.setattr(A, "_path", lambda: path)
    calls = []
    monkeypatch.setattr(E, "load_btc_gate", lambda: calls.append("read") or GATE_REAL_SHAPE)
    denied = A.load_events(board_date=date(2025, 1, 12))[0]
    assert calls == ["read"]
    assert denied["original_claim"]["edge"] == row["edge"]
    assert denied["original_claim"]["forward"] == row["forward"]
    assert denied["source_asof"] == row["source_asof"] == "2025-01-12"
    assert denied["severity"] == "info" and denied["tier"] == "context"
    assert denied["forward"] == "" and row["edge"] not in denied["edge"]
    assert path.read_text() == before
    # A stored derived denial can recover under a valid current receipt, but its
    # historical predictive prose must not return to the live edge/forward fields.
    path.write_text(json.dumps(denied) + "\n")
    recovered = A.load_events(gate=GATE_LEADING, board_date=date(2025, 1, 12))[0]
    assert recovered["tier"] == "act" and recovered["severity"] == row["severity"]
    assert "leg_gate" not in recovered and calls == ["read"]
    assert recovered["original_claim"] == denied["original_claim"]
    assert recovered["forward"] == "" and row["edge"] not in recovered["edge"]
    assert recovered["source_asof"] == row["source_asof"]


def test_rebuild_projects_raw_history_with_its_single_frozen_gate(monkeypatch, tmp_path):
    row = _crosses(GATE_LEADING)[0]
    row.pop("original_claim")
    row["edge"] = "Original issue claim, before any demotion"
    path = tmp_path / "alerts.jsonl"
    path.write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(A, "_path", lambda: path)
    for name in ("daily_state_events", "risk_extreme_events", "impulse_radar_events",
                 "leverage_derisk_events", "flash_events"):
        monkeypatch.setattr(A, name, lambda *args, **kwargs: [])
    monkeypatch.setattr(A.store, "read", lambda *args: None)
    calls = []
    monkeypatch.setattr(E, "load_btc_gate", lambda: calls.append("read") or GATE_REAL_SHAPE)
    sig = pd.DataFrame({"close": [60000.0]}, index=pd.to_datetime(["2025-01-12"]))
    result = A.compute_all_events(sig, board_date=date(2025, 1, 12))
    assert calls == ["read"] and len(result) == 1
    assert result[0]["id"] == row["id"]
    assert result[0]["original_claim"]["edge"] == row["edge"]
    assert result[0]["tier"] == "context" and result[0]["severity"] == "info"
    assert result[0]["source_asof"] == row["source_asof"]


def test_current_gate_cannot_rejuvenate_expired_or_unproven_observations():
    rows = _crosses(GATE_LEADING)
    for row in rows:
        row["ts"] = "2025-01-09T00:00:00"
        row["source_asof"] = "2025-01-09"
    historical = A._apply_leg_gate(rows, gate=GATE_LEADING, board_date=date(2025, 1, 12))
    assert len(historical) == 4
    assert all(e["evidence"]["status"] == "expired" for e in historical)
    assert all(e["evidence"]["permitted_use"] == "history_only" for e in historical)
    assert all(e["tier"] == "context" and e["severity"] == "info" for e in historical)
    assert all(e["source_asof"] == "2025-01-09" for e in historical)
    incomplete = _gate()
    for leg in incomplete["legs"].values():
        leg.pop("n_fires_holdout")
    assert all(e["evidence"]["status"] == "leg_evidence_malformed" for e in _crosses(incomplete))


def test_passport_precedes_legacy_display_status():
    row = _crosses(GATE_LEADING)[0]
    validation = alert_triage._validation(
        "vector", row["type"], row["edge"], row["edge_zh"], {},
        passport=row["evidence"], leg_gate="demoted",
    )
    assert validation["current_permitted"] is True
    assert validation["verdict"] == "backtested"
    denied = _crosses(GATE_REAL_SHAPE)[0]
    validation = alert_triage._validation(
        "vector", denied["type"], "CALIBRATED", "已验证", {},
        passport=denied["evidence"], leg_gate="leading",
    )
    assert validation["current_permitted"] is False
    assert validation["verdict"] == "no_edge"


def _isolated_current_board(monkeypatch, gate, day, *, now=None, payload=False):
    monkeypatch.setattr(E, "load_btc_gate", lambda: gate)
    monkeypatch.setattr(alert_triage, "_load_context", lambda: {
        "_state": alert_triage.READ_OK, "cross_asset": {}, "risk_backdrop": {},
    })
    monkeypatch.setattr(alert_triage, "_macro_raw", lambda *args: alert_triage._read(
        "macro", alert_triage.READ_OK_ZERO, []))
    original = alert_triage._jsonl_raw
    monkeypatch.setattr(alert_triage, "_jsonl_raw", lambda source, *args: (
        original(source, *args) if source == "vector" else
        alert_triage._read(source, alert_triage.READ_OK_ZERO, [])))
    result = alert_triage.build_triage(today=day, now=now)
    return result if payload else result["alerts"][0]


@pytest.mark.parametrize("clock,reason", [
    ({"event_date": "2025-01-11", "date_precision": "date",
      "ts": "2025-01-12T00:00:00"}, "expired"),
    ({"event_ts": "2025-01-12T00:30:00+14:00", "date_precision": "timestamp",
      "ts": "2025-01-12T00:30:00+14:00"}, "expired"),
    ({"date_precision": "unknown", "ts": "2025-01-12T00:00:00"}, "source_time_invalid"),
])
def test_public_reader_and_triage_share_canonical_event_clock(monkeypatch, tmp_path, clock, reason):
    row = _crosses(GATE_LEADING)[0]
    row.update(clock, source_asof="2025-01-11")
    path = tmp_path / "alerts.jsonl"
    path.write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(A, "_path", lambda: path)
    gate = _gate(asof="2025-01-14")
    public = A.load_events(gate=gate, board_date=date(2025, 1, 14))[0]
    board = _isolated_current_board(monkeypatch, gate, date(2025, 1, 14))
    for view in (public, board):
        assert view["claim_eligible"] is False
        assert view["evidence"]["status"] == reason
        assert view["tier"] == "context"
        assert view["source_asof"] == "2025-01-11"
    assert public["severity"] == "info" and board["severity"] == "minor"
    if clock["date_precision"] == "unknown":
        assert public["evidence"]["event_state"] == board["evidence"]["event_state"] == "unknown_event_time"
    assert json.loads(path.read_text()) == row


@pytest.mark.parametrize("claim", ["legacy-invalid", ["legacy-invalid"],
                                    {"severity": [], "headline": ["invalid"]}])
def test_malformed_history_cannot_abort_or_override_current_projection(monkeypatch, tmp_path, claim):
    row = _crosses(GATE_LEADING)[0]
    row["original_claim"] = claim
    path = tmp_path / "alerts.jsonl"
    path.write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(A, "_path", lambda: path)
    board = _isolated_current_board(monkeypatch, GATE_LEADING, date(2025, 1, 12))
    assert board["claim_eligible"] is True
    assert isinstance(board["headline"], str)
    assert board["original_claim"] == claim
    assert json.loads(path.read_text()) == row


def test_utc_expiry_does_not_wait_for_new_york_board_rollover(monkeypatch, tmp_path):
    row = _crosses(GATE_LEADING)[0]
    row.pop("original_claim")
    row.update(id=row["id"].replace("2025-01-12", "2025-01-09"),
               ts="2025-01-09T00:00:00", source_asof="2025-01-09")
    path = tmp_path / "alerts.jsonl"
    path.write_text(json.dumps(row) + "\n")
    monkeypatch.setattr(A, "_path", lambda: path)
    gate = _gate(asof="2025-01-11")
    clock = datetime(2025, 1, 12, 1, tzinfo=timezone.utc)
    board = _isolated_current_board(monkeypatch, gate, None, now=clock, payload=True)
    public = A.load_events(gate=gate, board_date=clock.date())[0]
    assert board["board_date"] == "2025-01-11"
    assert board["alerts"][0]["age_days"] == 2
    for view in (public, board["alerts"][0]):
        assert view["claim_eligible"] is False
        assert view["evidence"]["event_state"] == "expired"
        assert view["evidence"]["generated_for"] == "2025-01-12"
    replay = _isolated_current_board(monkeypatch, gate, date(2025, 1, 11), now=clock)
    assert replay["claim_eligible"] is True
    assert replay["evidence"]["generated_for"] == "2025-01-11"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
