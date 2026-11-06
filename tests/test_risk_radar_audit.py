"""Tests for engine/risk_radar_audit.py — forward-outcome log + deterministic grading.

Uses a synthetic SPY path so true-positive / false-positive grading is deterministic.
"""
from __future__ import annotations

import pandas as pd

from engine import risk_radar_audit as rra


def _synthetic_spy():
    """Flat at 100, then a -8% air-pocket starting ~index 30. So an as-of a few days before the
    drop -> drawdown within 21bd (true positive); an as-of in the flat zone -> no drawdown (FP)."""
    idx = pd.bdate_range("2026-01-01", periods=70)
    px = [100.0] * len(idx)
    for i in range(30, 36):
        px[i] = 100.0 - (i - 29) * 1.4          # slide down to ~92 (-8%)
    for i in range(36, len(idx)):
        px[i] = 95.0                             # partial recover, stays down
    return pd.Series(px, index=idx)


def _snap(asof, state, alert):
    return {"asof": str(asof.date()), "state": state, "alert": alert,
            "dominant_scare": "growth", "top_score": 72.0,
            "scares": [{"scare": "growth", "score": 72.0, "band": state}],
            "drawdown_prob": {"h5": 0.04, "h10": 0.10, "h21": 0.20, "conjunction_n": 1}}


def test_log_is_idempotent(tmp_path):
    spy = _synthetic_spy()
    snap = _snap(spy.index[25], "elevated", True)
    assert rra.log_snapshot(snap, root=tmp_path) is True
    assert rra.log_snapshot(snap, root=tmp_path) is False     # same asof -> no dup
    rows = rra._read(rra._path(tmp_path))
    assert len(rows) == 1


def test_grade_true_and_false_positive(tmp_path, monkeypatch):
    spy = _synthetic_spy()
    monkeypatch.setattr(rra, "_spy", lambda: spy)
    rra.log_snapshot(_snap(spy.index[25], "elevated", True), root=tmp_path)   # ~5bd before the drop -> TP
    rra.log_snapshot(_snap(spy.index[5], "elevated", True), root=tmp_path)    # flat zone -> FP
    n = rra.grade_log(root=tmp_path)
    assert n == 2
    rows = {r["asof"]: r for r in rra._read(rra._path(tmp_path))}
    tp = rows[str(spy.index[25].date())]
    fp = rows[str(spy.index[5].date())]
    assert tp["graded"]["outcome"] == "true_positive"
    assert tp["graded"]["any_dd5_within_h21"] is True
    assert fp["graded"]["outcome"] == "false_positive"
    assert fp["graded"]["any_dd5_within_h21"] is False


def test_immature_entry_not_graded(tmp_path, monkeypatch):
    spy = _synthetic_spy()
    monkeypatch.setattr(rra, "_spy", lambda: spy)
    rra.log_snapshot(_snap(spy.index[-2], "elevated", True), root=tmp_path)   # no 21bd ahead -> immature
    assert rra.grade_log(root=tmp_path) == 0
    assert rra._read(rra._path(tmp_path))[0]["graded"] is None


def test_scorecard_precision_and_recall(tmp_path, monkeypatch):
    spy = _synthetic_spy()
    monkeypatch.setattr(rra, "_spy", lambda: spy)
    rra.log_snapshot(_snap(spy.index[25], "elevated", True), root=tmp_path)   # TP
    rra.log_snapshot(_snap(spy.index[5], "elevated", True), root=tmp_path)    # FP
    rra.log_snapshot(_snap(spy.index[10], "calm", False), root=tmp_path)      # calm, no dd
    rra.grade_log(root=tmp_path)
    sc = rra.scorecard(root=tmp_path)
    assert sc["n_graded"] == 3
    assert sc["n_alerts"] == 2 and sc["n_true_pos"] == 1 and sc["n_false_pos"] == 1
    assert sc["alert_precision"] == 0.5
    # the one FP must appear in recent_mistakes
    assert any(m["kind"] == "false_positive" for m in sc["recent_mistakes"])


def test_snapshot_and_grade_returns_scorecard(tmp_path, monkeypatch):
    spy = _synthetic_spy()
    monkeypatch.setattr(rra, "_spy", lambda: spy)
    sc = rra.snapshot_and_grade(_snap(spy.index[25], "elevated", True), root=tmp_path)
    assert isinstance(sc, dict) and "n_graded" in sc


def test_scorecard_empty_is_safe(tmp_path):
    assert rra.scorecard(root=tmp_path)["n_graded"] == 0



def _prospective_identity(tag: str) -> dict:
    engine = (tag * 64)[:64]
    calibration = ((chr(ord(tag) + 1) if tag != "f" else "e") * 64)[:64]
    source_files = {
        "engine/risk_radar.py": engine,
        "engine/indicators.py": "1" * 64,
        "lib/nyse_calendar.py": "2" * 64,
        "lib/store.py": "3" * 64,
        "lib/config.py": "4" * 64,
    }
    identity = {
        "model_contract": "risk_radar_forward_model.v1",
        "risk_schema": "risk_radar.v2",
        "engine_source_sha256": engine,
        "source_bundle_sha256": rra._sha256_json(source_files),
        "source_files_sha256": source_files,
        "calibration_sha256": calibration,
    }
    identity["model_fingerprint"] = rra._sha256_json(identity)
    return identity


def test_new_forward_row_carries_prospective_issue_identity(tmp_path, monkeypatch):
    spy = _synthetic_spy()
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setattr(
        rra, "_forward_model_identity", lambda root=None: _prospective_identity("a")
    )
    assert rra.log_snapshot(_snap(spy.index[25], "elevated", True), root=tmp_path)
    row = rra._read(rra._path(tmp_path))[0]
    issue = row["forecast_issue"]
    assert issue["contract"] == rra.FORWARD_ISSUE_CONTRACT
    assert issue["epoch"] == rra.FORWARD_PROSPECTIVE_EPOCH
    assert issue["ledger_lane"] == "nightly"
    assert issue["first_writer_wins"] is True
    assert issue["model_contract"] == "risk_radar_forward_model.v1"
    assert issue["issued_at"] == row["logged_at"]
    assert issue["model_fingerprint"] == _prospective_identity("a")["model_fingerprint"]


def test_duplicate_date_cannot_replace_first_model_receipt(tmp_path, monkeypatch):
    spy = _synthetic_spy()
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    identities = [_prospective_identity("a"), _prospective_identity("c")]
    monkeypatch.setattr(
        rra, "_forward_model_identity", lambda root=None: identities.pop(0)
    )
    snap = _snap(spy.index[25], "elevated", True)
    assert rra.log_snapshot(snap, root=tmp_path) is True
    first = rra._read(rra._path(tmp_path))[0]["forecast_issue"]["model_fingerprint"]
    assert rra.log_snapshot(snap, root=tmp_path) is False
    rows = rra._read(rra._path(tmp_path))
    assert len(rows) == 1
    assert rows[0]["forecast_issue"]["model_fingerprint"] == first
    assert first == _prospective_identity("a")["model_fingerprint"]


def test_forward_model_identity_rotates_on_calibration_overlay(tmp_path):
    before = rra._forward_model_identity(root=tmp_path)
    assert before and len(before["engine_source_sha256"]) == 64
    p = tmp_path / "data" / "risk_radar" / "calibration.json"
    p.parent.mkdir(parents=True)
    p.write_text('{"prob_cal":{"h21":{"elevated":0.26}}}')
    after = rra._forward_model_identity(root=tmp_path)
    assert after
    assert after["engine_source_sha256"] == before["engine_source_sha256"]
    assert after["calibration_sha256"] != before["calibration_sha256"]
    assert after["model_fingerprint"] != before["model_fingerprint"]


def test_model_identity_failure_does_not_stop_legacy_forward_logging(tmp_path, monkeypatch):
    spy = _synthetic_spy()
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    monkeypatch.setattr(rra, "_forward_model_identity", lambda root=None: None)
    assert rra.log_snapshot(_snap(spy.index[25], "elevated", True), root=tmp_path)
    row = rra._read(rra._path(tmp_path))[0]
    assert "forecast_issue" not in row
    assert row["logged_at"]
