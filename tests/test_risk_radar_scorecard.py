"""Hermetic tests for engine/risk_radar_scorecard.py.

Covers:
- every outcome label (true_positive, false_positive, tp_watch, tn_watch, calm_dd, calm_quiet)
- window math (full vs trailing 365d)
- min-n honesty floor (n=4 -> null, n=5 -> rate)
- malformed JSONL line skipped cleanly
- missing intl ledger -> fail-soft entry (no raise)
- ungraded backlog count (rows older than 7 days with graded=null)
- atomic write to both paths
- build() never raises with empty/absent everything
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from engine import risk_radar_audit as rra
from engine import risk_radar_scorecard as sc
from engine.alerts import alert_view, transition_state_change
from engine.market_state import _radar_to_rd

_ALL_MARKETS = ("us", *sc._INTL_MARKETS)
ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _asof(days_ago: int) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


def _graded(outcome: str) -> dict:
    """Synthetic graded block for a US forward-log row."""
    return {
        "base_px": 500.0,
        "fwd_dd": {"h5": -0.02, "h10": -0.03, "h21": -0.06},
        "hit": {"h5": {"dd5": False, "dd8": False}, "h10": {"dd5": False, "dd8": False},
                "h21": {"dd5": True, "dd8": False}},
        "outcome": outcome,
        "any_dd5_within_h21": outcome in ("true_positive", "tp_watch", "calm_dd"),
        "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _row(state: str, dominant_scare: str | None, days_ago: int, outcome: str) -> dict:
    return {
        "asof": _asof(days_ago),
        "state": state,
        "alert": state in ("elevated", "risk-off"),
        "dominant_scare": dominant_scare,
        "top_score": 75.0,
        "scares": {},
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "graded": _graded(outcome),
    }


def _ungraded_row(state: str, days_ago: int) -> dict:
    return {
        "asof": _asof(days_ago),
        "state": state,
        "alert": state in ("elevated", "risk-off"),
        "dominant_scare": "growth",
        "top_score": 60.0,
        "scares": {},
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "graded": None,
    }


def _recovery_graded(fwd_ret_h21: float) -> dict:
    """Synthetic graded block for a recovery log row."""
    return {
        "base_px": 500.0,
        "h21": {"fwd_ret": fwd_ret_h21, "mae": -0.02},
        "h63": {"fwd_ret": fwd_ret_h21 + 0.01, "mae": -0.01},
        "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _recovery_row(days_ago: int, fwd_ret_h21: float | None) -> dict:
    return {
        "asof": _asof(days_ago),
        "phase": "receding",
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "graded": _recovery_graded(fwd_ret_h21) if fwd_ret_h21 is not None else None,
    }


def _write_jsonl(p: Path, rows: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# build() — never raises on empty/absent everything
# ---------------------------------------------------------------------------

def test_build_empty_root(tmp_path):
    result = sc.build(root=tmp_path)
    assert result["schema"] == "risk_radar_scorecard.v1"
    assert "markets" in result
    assert set(result["markets"]) == {
        "us", "cn", "hk", "ca", "kr", "jp", "tw", "in", "au", "gb", "ez",
    }


def test_build_never_raises_with_nothing(tmp_path):
    # No files at all — must not raise, must return a dict
    result = sc.build(root=tmp_path)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Outcome labels — every label produces correct counts
# ---------------------------------------------------------------------------

@pytest.fixture()
def all_outcomes_root(tmp_path):
    rows = [
        _row("elevated", "credit", 100, "true_positive"),
        _row("risk-off", "rates", 101, "false_positive"),
        _row("watch", None, 102, "tp_watch"),
        _row("caution", "vol", 103, "tn_watch"),
        _row("calm", None, 104, "calm_dd"),
        _row("calm", None, 105, "calm_quiet"),
    ]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    return tmp_path


def test_alerts_counts(all_outcomes_root):
    result = sc.build(root=all_outcomes_root)
    alerts = result["markets"]["us"]["windows"]["full"]["alerts"]
    assert alerts["n"] == 2
    assert alerts["tp"] == 1
    assert alerts["fp"] == 1
    assert alerts["hit_rate"] is None  # n=2 < 5


def test_watch_caution_counts(all_outcomes_root):
    result = sc.build(root=all_outcomes_root)
    wc = result["markets"]["us"]["windows"]["full"]["watch_caution"]
    assert wc["n"] == 2
    assert wc["tp"] == 1
    assert wc["tn"] == 1


def test_calm_counts(all_outcomes_root):
    result = sc.build(root=all_outcomes_root)
    calm = result["markets"]["us"]["windows"]["full"]["calm"]
    assert calm["n"] == 2
    assert calm["dd_missed"] == 1
    assert calm["quiet"] == 1


def test_by_scare_counts(all_outcomes_root):
    result = sc.build(root=all_outcomes_root)
    by_scare = result["markets"]["us"]["windows"]["full"]["by_scare"]
    # Only alert rows (elevated/risk-off) contribute to by_scare
    assert "credit" in by_scare
    assert by_scare["credit"]["n"] == 1
    assert by_scare["credit"]["tp"] == 1
    assert by_scare["rates"]["fp"] == 1


# ---------------------------------------------------------------------------
# Min-n honesty floor: n=4 -> null, n=5 -> float
# ---------------------------------------------------------------------------

def test_min_n_null_at_4(tmp_path):
    rows = [_row("elevated", "credit", 10 + i, "true_positive") for i in range(4)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    alerts = result["markets"]["us"]["windows"]["full"]["alerts"]
    assert alerts["n"] == 4
    assert alerts["hit_rate"] is None


def test_min_n_rate_at_5(tmp_path):
    rows = [_row("elevated", "credit", 10 + i, "true_positive") for i in range(5)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    alerts = result["markets"]["us"]["windows"]["full"]["alerts"]
    assert alerts["n"] == 5
    assert alerts["hit_rate"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Window: full vs trailing 365d
# ---------------------------------------------------------------------------

def test_window_trailing_365_excludes_old_rows(tmp_path):
    old_rows = [_row("elevated", "credit", 400 + i, "true_positive") for i in range(5)]
    recent_rows = [_row("elevated", "credit", 10 + i, "false_positive") for i in range(5)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl",
                 old_rows + recent_rows)
    result = sc.build(root=tmp_path)
    full = result["markets"]["us"]["windows"]["full"]["alerts"]
    y1 = result["markets"]["us"]["windows"]["y1"]["alerts"]
    assert full["n"] == 10   # all rows
    assert y1["n"] == 5      # only the recent ones


def test_window_y1_excludes_old_but_inside_365_included(tmp_path):
    rows = [_row("elevated", "credit", 300 + i, "true_positive") for i in range(5)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    # All rows are 300-304 days ago — still within 365
    y1 = result["markets"]["us"]["windows"]["y1"]["alerts"]
    assert y1["n"] == 5


# ---------------------------------------------------------------------------
# Malformed JSONL line skipped
# ---------------------------------------------------------------------------

def test_malformed_line_skipped(tmp_path):
    p = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = [_row("elevated", "credit", 10, "true_positive"),
            _row("elevated", "credit", 11, "true_positive")]
    lines = [json.dumps(r) for r in rows]
    lines.insert(1, "NOT JSON {{{{")  # inject malformed
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    # Should not raise; should still parse the 2 valid rows
    result = sc.build(root=tmp_path)
    graded_n = result["markets"]["us"]["monitoring"]["graded_n"]
    assert graded_n == 2


# ---------------------------------------------------------------------------
# Missing intl ledger -> fail-soft entry
# ---------------------------------------------------------------------------

def test_missing_intl_ledger_fail_soft(tmp_path):
    # Only write US ledger; leave every intl ledger absent
    rows = [_row("elevated", "credit", 10, "true_positive")]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    # Should not raise; each intl market should have a fail-soft structure
    for market in sc._INTL_MARKETS:
        m = result["markets"][market]
        assert "monitoring" in m
        assert m["monitoring"]["log_fresh"] is False
        assert "windows" in m


# ---------------------------------------------------------------------------
# Ungraded backlog count
# ---------------------------------------------------------------------------

def test_ungraded_backlog_counts_old_rows(tmp_path):
    """Backlog = ungraded MORE than (21-bd maturation + 7-bd slack) BUSINESS days after as-of.

    UPDATED 2026-07-29 (radar audit item 9f). The old threshold was 7 CALENDAR days, which
    pinned the defect: a row cannot be graded until its longest horizon matures at 21 BUSINESS
    days (risk_radar_audit._grade_entry returns None before then), so every row between ~1 and
    ~5 weeks old was counted as backlog and steady state read as a stalled grader. Rows younger
    than maturation are now reported under `awaiting_maturity` instead.
    """
    cutoff = sc._UNGRADED_MATURATION_BD + sc._UNGRADED_BACKLOG_AGE   # 28 business days
    rows = [
        _ungraded_row("caution", 3),    # ~2 bd — working as designed
        _ungraded_row("caution", 21),   # ~15 bd — still inside maturation
        _ungraded_row("caution", 30),   # ~21 bd — matured, inside slack
        _ungraded_row("caution", 60),   # ~43 bd — IS backlog
        _ungraded_row("caution", 120),  # ~86 bd — IS backlog
        _row("elevated", "credit", 50, "true_positive"),  # graded, not counted
    ]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    monitoring = result["markets"]["us"]["monitoring"]
    assert monitoring["backlog_cutoff_bd"] == cutoff
    assert monitoring["ungraded_backlog"] == 2, monitoring
    # everything ungraded but younger than the cutoff is disclosed, not hidden
    assert monitoring["awaiting_maturity"] == 3, monitoring


def test_ungraded_inside_maturation_is_not_backlog(tmp_path):
    """A ledger writing daily and grading on schedule must report ZERO backlog — the
    steady-state regression the calendar-day threshold produced (audit item 9f)."""
    rows = [_ungraded_row("caution", d) for d in (1, 2, 3, 5, 8, 13, 20, 27)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    monitoring = sc.build(root=tmp_path)["markets"]["us"]["monitoring"]
    assert monitoring["ungraded_backlog"] == 0, monitoring
    assert monitoring["awaiting_maturity"] == 8, monitoring


def test_monitoring_today_is_injectable(tmp_path):
    """`today` is threaded through build() so the whole scorecard is reproducible from the
    ledger + one reference date, instead of three independent wall-clock reads (audit 9g)."""
    from datetime import date
    rows = [_ungraded_row("caution", 3)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    far = date.today().replace(year=date.today().year + 1)
    m_now = sc.build(root=tmp_path)["markets"]["us"]["monitoring"]
    m_far = sc.build(root=tmp_path, today=far)["markets"]["us"]["monitoring"]
    assert m_now["ungraded_backlog"] == 0 and m_now["awaiting_maturity"] == 1
    # a year later the same row IS a genuine backlog
    assert m_far["ungraded_backlog"] == 1, m_far
    assert m_far["log_fresh"] is False


def test_bd_between_counts_weekdays_only(tmp_path):
    from datetime import date
    # Fri 2026-07-24 -> Mon 2026-07-27 is ONE business day, not three calendar days
    assert sc._bd_between(date(2026, 7, 24), date(2026, 7, 27)) == 1
    assert sc._bd_between(date(2026, 7, 24), date(2026, 7, 31)) == 5
    assert sc._bd_between(date(2026, 7, 31), date(2026, 7, 24)) == 0


# ---------------------------------------------------------------------------
# Recovery block
# ---------------------------------------------------------------------------

def test_recovery_ok_rate(tmp_path):
    recovery_rows = [
        _recovery_row(50, 0.05),    # h21 > 0 = ok
        _recovery_row(51, 0.02),    # ok
        _recovery_row(52, -0.01),   # not ok
        _recovery_row(53, 0.03),    # ok
        _recovery_row(54, 0.01),    # ok
    ]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "recovery_log.jsonl", recovery_rows)
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", [])
    result = sc.build(root=tmp_path)
    rec = result["markets"]["us"]["windows"]["full"]["recovery"]
    assert rec is not None
    assert rec["n"] == 5
    assert rec["ok"] == 4
    assert rec["rate"] == pytest.approx(4 / 5)


def test_recovery_null_rate_below_min_n(tmp_path):
    recovery_rows = [_recovery_row(50 + i, 0.01) for i in range(4)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "recovery_log.jsonl", recovery_rows)
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", [])
    result = sc.build(root=tmp_path)
    rec = result["markets"]["us"]["windows"]["full"]["recovery"]
    assert rec is not None
    assert rec["rate"] is None   # n=4 < 5


def test_recovery_none_when_no_graded(tmp_path):
    # Ungraded recovery rows → recovery block should be None (no graded rows)
    recovery_rows = [_recovery_row(50, None), _recovery_row(51, None)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "recovery_log.jsonl", recovery_rows)
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", [])
    result = sc.build(root=tmp_path)
    rec = result["markets"]["us"]["windows"]["full"]["recovery"]
    assert rec is None


# ---------------------------------------------------------------------------
# Intl market entries (with data)
# ---------------------------------------------------------------------------

def test_intl_cn_market(tmp_path):
    rows = [_row("elevated", "breadth", 50 + i, "true_positive") for i in range(5)]
    for r in rows:
        r["market"] = "cn"
    _write_jsonl(tmp_path / "data" / "risk_radar_intl" / "cn_forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    cn = result["markets"]["cn"]
    assert cn["monitoring"]["graded_n"] == 5
    assert cn["windows"]["full"]["alerts"]["n"] == 5


def test_intl_kr_market(tmp_path):
    # One of the 7 markets added by the intl radar expansion (#2684);
    # 'fx' is the KR profile's FX-depreciation leg.
    rows = [_row("elevated", "fx", 50 + i, "true_positive") for i in range(5)]
    for r in rows:
        r["market"] = "kr"
    _write_jsonl(tmp_path / "data" / "risk_radar_intl" / "kr_forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    kr = result["markets"]["kr"]
    assert kr["monitoring"]["graded_n"] == 5
    assert kr["windows"]["full"]["alerts"]["n"] == 5
    assert kr["windows"]["full"]["alerts"]["hit_rate"] == pytest.approx(1.0)
    assert kr["windows"]["full"]["by_scare"]["fx"]["n"] == 5


# ---------------------------------------------------------------------------
# Atomic write — both paths get valid JSON
# ---------------------------------------------------------------------------

def test_write_both_paths(tmp_path):
    # Write some data
    rows = [_row("elevated", "credit", 30 + i, "true_positive") for i in range(5)]
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)

    returned = sc.write(root=tmp_path)
    assert isinstance(returned, dict)
    assert returned.get("schema") == "risk_radar_scorecard.v1"

    data_path = tmp_path / "data" / "risk_radar" / "scorecard.json"
    site_path = tmp_path / "site" / "riskdata" / "scorecard.json"

    assert data_path.exists(), "data/risk_radar/scorecard.json not written"
    assert site_path.exists(), "site/riskdata/scorecard.json not written"

    data_obj = json.loads(data_path.read_text())
    site_obj = json.loads(site_path.read_text())

    assert data_obj["schema"] == "risk_radar_scorecard.v1"
    assert site_obj["schema"] == "risk_radar_scorecard.v1"
    # Both copies must be identical
    assert data_obj == site_obj


def test_write_never_raises_empty(tmp_path):
    result = sc.write(root=tmp_path)
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# Monitoring block: log_fresh, last_logged_days_ago
# ---------------------------------------------------------------------------

def test_log_fresh_recent_row(tmp_path):
    rows = [_ungraded_row("caution", 1)]  # 1 day ago
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    assert result["markets"]["us"]["monitoring"]["log_fresh"] is True
    assert result["markets"]["us"]["monitoring"]["last_logged_days_ago"] == 1


def test_log_fresh_stale_row(tmp_path):
    rows = [_ungraded_row("caution", 5)]  # 5 days ago — still within 3d? No, fails
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl", rows)
    result = sc.build(root=tmp_path)
    assert result["markets"]["us"]["monitoring"]["log_fresh"] is False
    assert result["markets"]["us"]["monitoring"]["last_logged_days_ago"] == 5


# ---------------------------------------------------------------------------
# Schema guard: all required keys present in output
# ---------------------------------------------------------------------------

def test_schema_keys_present(tmp_path):
    result = sc.build(root=tmp_path)
    assert "schema" in result
    assert "generated_at" in result
    assert "markets" in result
    for market in _ALL_MARKETS:
        m = result["markets"][market]
        assert "monitoring" in m, f"{market} missing monitoring"
        assert "windows" in m, f"{market} missing windows"
        for wk in ("full", "y1"):
            w = m["windows"][wk]
            assert "alerts" in w, f"{market}/{wk} missing alerts"
            assert "watch_caution" in w
            assert "calm" in w
            assert "by_scare" in w
            assert "recovery" in w


# ---------------------------------------------------------------------------
# FIX 5: corrupt graded value drops only that row, not the whole market
# ---------------------------------------------------------------------------

def test_corrupt_graded_row_dropped_not_whole_market(tmp_path):
    """A row with graded='CORRUPT' (not a dict) must be skipped;
    valid rows in the same ledger are still counted."""
    rows = [
        _row("elevated", "credit", 10, "true_positive"),
        _row("elevated", "credit", 11, "true_positive"),
        _row("elevated", "credit", 12, "true_positive"),
        _row("elevated", "credit", 13, "true_positive"),
        _row("elevated", "credit", 14, "true_positive"),
    ]
    # Inject one corrupt row (graded is a scalar string, not a dict)
    corrupt_row = {
        "asof": _asof(15),
        "state": "elevated",
        "alert": True,
        "dominant_scare": "credit",
        "top_score": 80.0,
        "scares": {},
        "logged_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "graded": "CORRUPT",  # must be ignored, not crash
    }
    _write_jsonl(tmp_path / "data" / "risk_radar" / "forward_log.jsonl",
                 rows + [corrupt_row])
    result = sc.build(root=tmp_path)
    alerts = result["markets"]["us"]["windows"]["full"]["alerts"]
    # 5 valid rows should still be counted; corrupt row excluded from window math
    assert alerts["n"] == 5
    assert alerts["tp"] == 5
    assert alerts["hit_rate"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Publication velocity + explainable transitions (PR #7040)
# ---------------------------------------------------------------------------

def _leg(name: str, pctile: float) -> dict:
    return {"leg": name, "pctile": pctile, "confirmed": True,
            "era_robust": True, "lift_2020": 1.0}


def _ledger_row(asof: str, state: str, top_score: float,
                growth_score: float, growth_band: str,
                growth_legs: list[dict], credit_score: float = 55.0) -> dict:
    return {
        "asof": asof,
        "state": state,
        "dominant_scare": "growth",
        "top_score": top_score,
        "scares": {
            "growth": {"score": growth_score, "band": growth_band,
                       "firing_legs": growth_legs},
            "credit": {"score": credit_score, "band": "watch",
                       "firing_legs": [_leg("credit_oas_roc", 0.70)]},
        },
    }


def _current_snapshot() -> dict:
    return {
        "asof": "2026-09-09",
        "state": "watch",
        "dominant_scare": "growth",
        "dominant_label_en": "Growth scare",
        "dominant_label_zh": "增长恐慌",
        "top_score": 65.7,
        "scares": [
            {"scare": "growth", "label_en": "Growth scare", "label_zh": "增长恐慌",
             "score": 65.7, "band": "watch",
             "firing_legs": [_leg("growth_cyc_def", 0.81)]},
            {"scare": "credit", "label_en": "Credit stress", "label_zh": "信用压力",
             "score": 55.6, "band": "watch",
             "firing_legs": [_leg("credit_oas_roc", 0.69)]},
        ],
    }


def _write_ledger(root: Path, rows: list[dict]) -> None:
    p = root / "data" / "risk_radar" / "forward_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_publication_change_uses_strictly_earlier_row_and_explains_drivers(tmp_path) -> None:
    rows = [
        _ledger_row("2026-09-02", "caution", 70.0, 70.0, "caution",
                    [_leg("growth_cyc_def", 0.76), _leg("growth_defensives", 0.71)], 56.0),
        _ledger_row("2026-09-08", "caution", 75.1, 75.1, "caution",
                    [_leg("growth_cyc_def", 0.798), _leg("growth_defensives", 0.704)], 57.6),
        # Proves same-asof rows cannot become the comparator after the nightly append.
        _ledger_row("2026-09-09", "calm", 1.0, 1.0, "calm", [], 1.0),
    ]
    _write_ledger(tmp_path, rows)

    ch = rra.publication_change(_current_snapshot(), root=tmp_path)

    assert ch["available"] is True
    assert ch["basis"] == "prior_publication"
    assert ch["prior_asof"] == "2026-09-08"
    assert ch["score"] == {
        "current": 65.7, "prior": 75.1, "delta": -9.4, "direction": "easing"
    }
    assert ch["state"] == {"current": "watch", "prior": "caution", "changed": True}
    growth = next(s for s in ch["scares"] if s["scare"] == "growth")
    assert growth["prior"] == 75.1 and growth["current"] == 65.7
    assert growth["delta"] == -9.4 and growth["band_changed"] is True
    assert growth["cleared_legs"] == ["growth_defensives"]
    assert growth["added_legs"] == []
    assert ch["week"] == {
        "available": True, "asof": "2026-09-02", "score": 70.0, "delta": -4.3
    }
    assert "75.1→65.7" in ch["summary_en"]
    assert "Defensives outperforming cleared" in ch["summary_en"]
    assert "防御股跑赢解除" in ch["summary_zh"]


def test_publication_change_has_typed_absence_not_fake_zero(tmp_path) -> None:
    _write_ledger(tmp_path, [
        _ledger_row("2026-09-09", "watch", 65.7, 65.7, "watch",
                    [_leg("growth_cyc_def", 0.81)])
    ])
    ch = rra.publication_change(_current_snapshot(), root=tmp_path)
    assert ch["available"] is False
    assert ch["null_reason"] == "NO_EARLIER_PUBLICATION"
    assert ch["prior_asof"] is None
    assert ch["week"]["available"] is False
    assert ch["history"] == [{"asof": "2026-09-09", "state": "watch",
                              "dominant_scare": "growth", "top_score": 65.7}]


def test_snapshot_and_grade_attaches_change_without_advancing_second_ledger(monkeypatch) -> None:
    monkeypatch.setattr(rra, "log_snapshot", lambda snap, root=None: False)
    monkeypatch.setattr(rra, "grade_log", lambda root=None: 0)
    monkeypatch.setattr(rra, "scorecard", lambda root=None: {"n_graded": 3})
    monkeypatch.setattr(rra, "publication_change",
                        lambda snap, root=None: {"available": True, "prior_asof": "2026-09-08"})
    out = rra.snapshot_and_grade(_current_snapshot())
    assert out == {"n_graded": 3,
                   "publication_change": {"available": True, "prior_asof": "2026-09-08"}}


def test_radar_card_preserves_decimal_and_renders_compact_velocity(monkeypatch) -> None:
    monkeypatch.setattr("engine.market_state._rr_scorecard_track", lambda market: None)
    change = {
        "available": True,
        "prior_asof": "2026-09-08",
        "score": {"current": 65.7, "prior": 75.1, "delta": -9.4, "direction": "easing"},
        "week": {"available": True, "asof": "2026-09-02", "score": 70.0, "delta": -4.3},
        "summary_en": "Growth 75.1→65.7 · Caution→Watch · Defensives outperforming cleared",
        "summary_zh": "增长 75.1→65.7 · 警戒→关注 · 防御股跑赢解除",
    }
    rr = {
        **_current_snapshot(),
        "market": "us",
        "alert": False,
        "gross_factor": 1.0,
        "drawdown_prob": {"h5": 0.08, "h10": 0.12, "h21": 0.20,
                          "lift_h21": 1.1, "base_h5": 0.036,
                          "base_h10": 0.086, "base_h21": 0.178},
        "forward_log": {"n_graded": 3, "publication_change": change},
    }
    rd = _radar_to_rd(rr)
    assert rd["top_score"] == 65.7
    assert rd["change"] == change

    env = Environment(loader=FileSystemLoader(str(ROOT / "templates")),
                      autoescape=select_autoescape(["html", "xml"]),
                      undefined=StrictUndefined)
    tpl = env.from_string(
        '{% import "_risk_radar_card.html.j2" as rrc %}'
        '{{ rrc.risk_radar_card(rd, [], false) }}'
    )
    html = tpl.render(rd=rd)
    assert "65.7/100" in html
    assert "▼9.4" in html
    assert "Prev 75.1" in html and "1W 70.0" in html
    assert "Defensives outperforming cleared" in html


def test_transition_alert_names_added_and_cleared_flags() -> None:
    idx = pd.bdate_range("2026-09-08", periods=2)
    hist = pd.DataFrame({
        "quad": ["Q1", "Q1"],
        "transition_state": ["STABLE", "WEAKENING"],
        "n_flags": [1, 2],
        "growth_confidence": [0.6, 0.6],
        "inflation_confidence": [0.6, 0.6],
        "flag_breadth_price": [False, True],
        "flag_credit_equity": [True, False],
        "flag_ratio_inflection": [False, False],
        "flag_inflation_basket": [False, False],
        "flag_confidence_decay": [False, False],
        "flag_gex": [False, True],
        "flag_rotation_persistence": [False, False],
    }, index=idx)

    alert = transition_state_change(hist, pd.DataFrame())
    assert alert is not None
    assert "added: breadth/price divergence, dealer-gamma fragility" in alert.message
    assert "cleared: credit/equity divergence" in alert.message
    assert "flag_breadth_price" not in alert.message
    assert "新增：宽度/价格背离、做市商 Gamma 脆弱" in alert.message_zh
    assert "解除：信用/股票背离" in alert.message_zh

    view = alert_view(alert.rule, alert.severity, alert.message, alert.message_zh)
    assert view["message"].startswith(
        "The regime's footing went from steady to weakening (2 warning flags active)"
    )
    assert "added: breadth/price divergence" in view["message"]
    assert "新增：宽度/价格背离" in view["message_zh"]



def test_publication_change_skips_non_object_json_rows(tmp_path) -> None:
    """Valid JSON scalars/lists are malformed ledger rows, not fatal comparisons."""
    prior = _ledger_row(
        "2026-09-08", "caution", 75.1, 75.1, "caution",
        [_leg("growth_cyc_def", 0.798)],
    )
    p = tmp_path / "data" / "risk_radar" / "forward_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    malformed_object = {"asof": 17, "state": "risk-off", "top_score": 99.0}
    non_iso_object = {"asof": "2000", "state": "risk-off", "top_score": 98.0}
    p.write_text(
        "\n".join(
            (
                json.dumps(17),
                json.dumps(["bad"]),
                json.dumps(malformed_object),
                json.dumps(non_iso_object),
                json.dumps(prior),
            )
        ) + "\n",
        encoding="utf-8",
    )

    change = rra.publication_change(_current_snapshot(), root=tmp_path)

    assert change["available"] is True
    assert change["prior_asof"] == "2026-09-08"
    assert change["null_reason"] is None
    assert change["week"] == {"available": False, "null_reason": "NO_WEEK_REFERENCE"}
    assert all(point["asof"] != "17" for point in change["history"])


@pytest.mark.parametrize(
    ("current_asof", "prior_asof"),
    [
        ("2026-09-09T07:16:50+00:00", "2026-09-08"),
        ("2026-09-09", "2026-09-08T21:00:00-04:00"),
        ("2026-09-09 07:16:50+00:00", "2026-09-08 21:00:00-04:00"),
    ],
)
def test_publication_change_compares_date_and_timestamp_asofs(
    tmp_path, current_asof: str, prior_asof: str
) -> None:
    """ISO timestamp variants must retain publication-date identity, not fail comparison."""
    prior = _ledger_row(
        prior_asof, "caution", 75.1, 75.1, "caution",
        [_leg("growth_cyc_def", 0.798)],
    )
    _write_ledger(tmp_path, [prior])
    current = _current_snapshot()
    current["asof"] = current_asof

    change = rra.publication_change(current, root=tmp_path)

    assert change["available"] is True
    assert change["prior_asof"] == prior_asof
    assert change["score"]["prior"] == 75.1
    assert change["null_reason"] is None


def test_publication_change_invalid_current_asof_is_typed_absence(tmp_path) -> None:
    """A malformed current publication date must not trigger a permissive parser fallback."""
    prior = _ledger_row(
        "2026-09-08", "caution", 75.1, 75.1, "caution",
        [_leg("growth_cyc_def", 0.798)],
    )
    _write_ledger(tmp_path, [prior])
    current = _current_snapshot()
    current["asof"] = "today"

    change = rra.publication_change(current, root=tmp_path)

    assert change["available"] is False
    assert change["null_reason"] == "CURRENT_ASOF_INVALID"
    assert change["prior_asof"] is None



def test_publication_change_first_writer_wins_across_same_day_asof_formats(tmp_path) -> None:
    """Equivalent date/timestamp spellings are one publication day for ledger identity."""
    first = _ledger_row(
        "2026-09-08T02:00:00+00:00", "caution", 75.1, 75.1, "caution",
        [_leg("growth_cyc_def", 0.798)],
    )
    duplicate = _ledger_row(
        "2026-09-08", "calm", 1.0, 1.0, "calm", [],
    )
    _write_ledger(tmp_path, [first, duplicate])

    change = rra.publication_change(_current_snapshot(), root=tmp_path)

    assert change["available"] is True
    assert change["prior_asof"] == first["asof"]
    assert change["score"]["prior"] == 75.1


def test_publication_change_week_missing_score_is_typed_absence(tmp_path) -> None:
    """A dated but scoreless week row is provenance, not an available numeric reference."""
    week = _ledger_row(
        "2026-09-02", "caution", 70.0, 70.0, "caution",
        [_leg("growth_cyc_def", 0.76)],
    )
    week["top_score"] = None
    prior = _ledger_row(
        "2026-09-08", "caution", 75.1, 75.1, "caution",
        [_leg("growth_cyc_def", 0.798)],
    )
    _write_ledger(tmp_path, [week, prior])

    change = rra.publication_change(_current_snapshot(), root=tmp_path)

    assert change["available"] is True
    assert change["week"] == {
        "available": False,
        "null_reason": "WEEK_SCORE_MISSING",
        "asof": "2026-09-02",
        "score": None,
        "delta": None,
    }

def test_radar_card_partial_change_shape_fails_soft(monkeypatch) -> None:
    """A historical comparison with nullable numerics must not take down Jinja."""
    monkeypatch.setattr("engine.market_state._rr_scorecard_track", lambda market: None)
    change = {
        "available": True,
        "prior_asof": "2026-09-08",
        "score": {"current": 65.7, "prior": None, "delta": None},
        "week": {"available": True, "asof": "2026-09-02",
                 "score": None, "delta": None},
        "summary_en": "Risk Radar changed",
        "summary_zh": "风险雷达发生变化",
    }
    rr = {
        **_current_snapshot(),
        "market": "us",
        "alert": False,
        "gross_factor": 1.0,
        "drawdown_prob": {
            "h5": 0.08, "h10": 0.12, "h21": 0.20,
            "lift_h21": 1.1, "base_h5": 0.036,
            "base_h10": 0.086, "base_h21": 0.178,
        },
        "forward_log": {"n_graded": 3, "publication_change": change},
    }
    rd = _radar_to_rd(rr)
    env = Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
    )
    tpl = env.from_string(
        '{% import "_risk_radar_card.html.j2" as rrc %}'
        "{{ rrc.risk_radar_card(rd, [], false) }}"
    )

    html = tpl.render(rd=rd)

    assert "Risk Radar changed" in html
    assert "风险雷达发生变化" in html
    assert ">Prev " not in html
    assert ">1W " not in html


def test_transition_alert_nullable_metadata_falls_back_to_hysteresis() -> None:
    """Nullable optional state-machine metadata must not suppress a real alert."""
    idx = pd.bdate_range("2026-09-08", periods=2)
    hist = pd.DataFrame({
        "quad": ["Q1", "Q1"],
        "transition_state": ["STABLE", "WEAKENING"],
        "n_flags": [0, 0],
        "growth_confidence": [0.6, 0.6],
        "inflation_confidence": [0.6, 0.6],
        "flag_breadth_price": [False, False],
        "flag_credit_equity": [False, False],
        "flag_ratio_inflection": [False, False],
        "flag_inflation_basket": [False, False],
        "flag_confidence_decay": [False, False],
        "flag_gex": [False, False],
        "flag_rotation_persistence": [False, False],
        "pending_days": [float("nan"), float("nan")],
        "pending_quad": [pd.NA, pd.NA],
        "transition_state_raw": [pd.NA, pd.NA],
        "transition_ratcheted": [pd.NA, pd.NA],
        "transition_dwell_remaining": [float("nan"), float("nan")],
    }, index=idx)

    alert = transition_state_change(hist, pd.DataFrame())

    assert alert is not None
    assert (
        "flag set unchanged; transition hold/hysteresis moved the headline"
        in alert.message
    )
    assert "旗标集合未变；状态保持/滞后确认机制推动主状态变化" in alert.message_zh


def test_publication_change_translates_dominant_scare_in_both_languages(tmp_path) -> None:
    """A lead-scare handoff must never leak machine slugs into Chinese copy."""
    prior = _ledger_row(
        "2026-09-08", "caution", 72.0, 58.0, "watch",
        [_leg("growth_cyc_def", 0.70)],
    )
    prior["dominant_scare"] = "credit"
    _write_ledger(tmp_path, [prior])
    current = _current_snapshot()
    current["dominant_scare"] = "growth"

    change = rra.publication_change(current, root=tmp_path)

    assert "Lead Credit stress→Growth scare / defensive rotation" in change["summary_en"]
    assert "主导 信用压力→增长恐慌/防御轮动" in change["summary_zh"]
    assert "credit" not in change["summary_zh"]
    assert "growth" not in change["summary_zh"]



def test_transition_alert_nullable_flag_count_is_typed_zero() -> None:
    """A state transition survives absent count metadata and reports an honest zero."""
    idx = pd.bdate_range("2026-09-08", periods=2)
    hist = pd.DataFrame({
        "quad": ["Q1", "Q1"],
        "transition_state": ["STABLE", "WEAKENING"],
        "n_flags": [0, pd.NA],
        "growth_confidence": [0.6, 0.6],
        "inflation_confidence": [0.6, 0.6],
        "flag_breadth_price": [False, False],
    }, index=idx)

    alert = transition_state_change(hist, pd.DataFrame())

    assert alert is not None
    assert "(0 flags active)" in alert.message
    assert "（0 个预警激活）" in alert.message_zh

def test_transition_alert_missing_state_is_typed_absence() -> None:
    """A historical row without a transition state is absence, not an alert crash."""
    idx = pd.bdate_range("2026-09-08", periods=2)
    hist = pd.DataFrame({
        "quad": ["Q1", "Q1"],
        "transition_state": ["STABLE", pd.NA],
        "n_flags": [0, 0],
        "growth_confidence": [0.6, 0.6],
        "inflation_confidence": [0.6, 0.6],
    }, index=idx)

    assert transition_state_change(hist, pd.DataFrame()) is None
