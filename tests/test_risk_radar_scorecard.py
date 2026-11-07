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

import pytest
import pandas as pd

from engine import risk_radar_scorecard as sc

_ALL_MARKETS = ("us", *sc._INTL_MARKETS)


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

# Fixed-protocol issued-probability audit (display only, not model promotion).
def _prob_rows(n=5, p=.2, base=.1, outcome=False):
    rows = []
    for i in range(n):
        row = _row("caution", "credit", 100 + i, "tn_watch")
        row["asof"] = (date(2026, 6, 1) + timedelta(days=i)).isoformat()
        row["logged_at"] = row["asof"] + "T21:00:00+00:00"
        row["graded"]["graded_at"] = "2026-08-01T12:00:00+00:00"
        row["drawdown_prob"] = {"measure": sc._PROBABILITY_TARGET}
        for h in ("h5", "h10", "h21"):
            row["drawdown_prob"][h] = p
            row["drawdown_prob"]["base_" + h] = base
            row["graded"]["hit"][h]["dd5"] = outcome
        rows.append(row)
    return rows


def _audit(rows):
    return sc.probability_audit(rows, today=date(2026, 9, 20))


def test_probability_oracle_and_no_input_mutation():
    from copy import deepcopy
    rows = _prob_rows(); before = deepcopy(rows); audit = _audit(rows)
    h = audit["horizons"]["h21"]
    assert (h["n"], h["mean_forecast"], h["observed_rate"], h["brier"]) == (5, .2, 0., .04)
    assert (h["paired_n"], h["paired_model_brier"], h["paired_base_brier"], h["paired_brier_delta"]) == (5, .04, .01, .03)
    assert rows == before and audit["current_model_validated"] is False


@pytest.mark.parametrize("n", [0, 1, 4])
def test_probability_small_sample_is_not_zero(n):
    h = _audit(_prob_rows(n))["horizons"]["h5"]
    assert h["n"] == n
    for key in ("mean_forecast", "observed_rate", "brier", "paired_brier_delta"):
        assert h[key] is None


@pytest.mark.parametrize("bad", [None, True, False, "0.2", -.1, 1.1, float("nan"), float("inf"), 10**400])
def test_probability_rejects_invalid_numbers_per_horizon(bad):
    rows = _prob_rows(); rows[0]["drawdown_prob"]["h5"] = bad
    a = _audit(rows)["horizons"]
    assert a["h5"]["n"] == 4 and a["h5"]["excluded"] == {"invalid_probability": 1}
    assert a["h21"]["n"] == 5


def test_probability_matched_baseline_never_uses_different_rows():
    rows = _prob_rows(6)
    rows[-1]["drawdown_prob"].update(h21=.9, base_h21=None)
    h = _audit(rows)["horizons"]["h21"]
    assert h["n"] == 6 and h["paired_n"] == 5 and h["missing_baseline_n"] == 1
    assert h["brier"] == pytest.approx(1.01 / 6, abs=1e-6)
    assert h["paired_model_brier"] == .04 and h["paired_brier_delta"] == .03
    for r in rows: r["drawdown_prob"].pop("base_h5")
    h = _audit(rows)["horizons"]["h5"]
    assert h["n"] == 6 and h["paired_n"] == 0 and h["paired_base_brier"] is None


@pytest.mark.parametrize("field,value", [
    ("asof", "2026-02-30"), ("asof", "2026-09-21"), ("asof", "20260601"),
    ("logged_at", "2026-06-01T21:00:00"), ("logged_at", "2026-08-02T00:00:00Z"),
    ("logged_at", None), ("graded_at", "2026-09-21T00:00:00Z"),
    ("graded_at", "2026-05-01T00:00:00Z"), ("graded_at", "bad"),
])
def test_probability_excludes_unusable_dates_and_receipts(field, value):
    rows = _prob_rows()
    target = rows[0]["graded"] if field == "graded_at" else rows[0]
    target[field] = value
    for h in _audit(rows)["horizons"].values():
        assert h["n"] == 4 and h["excluded_n"] == 1


def test_probability_duplicate_conflict_is_order_independent():
    from copy import deepcopy
    rows = _prob_rows(); rows.append(deepcopy(rows[0]))
    h = _audit(rows)["horizons"]["h21"]
    assert h["n"] == 5 and h["excluded"] == {"identical_duplicate": 1}
    rows[-1]["drawdown_prob"]["h21"] = .8
    h = _audit(rows)["horizons"]["h21"]
    assert h["n"] == 4 and h["excluded"] == {"conflicting_duplicate_date": 2}
    assert _audit(rows) == _audit(list(reversed(rows)))


def test_probability_requires_boolean_not_rounded_drawdown():
    rows = _prob_rows(); rows[0]["graded"]["hit"]["h5"]["dd5"] = "false"
    assert _audit(rows)["horizons"]["h5"]["n"] == 4


@pytest.mark.parametrize("value", [None, "other instrument", ">=8% SPY pullback"])
def test_probability_does_not_mix_targets(value):
    rows = _prob_rows(); rows[0]["drawdown_prob"]["measure"] = value
    assert _audit(rows)["horizons"]["h21"]["excluded"] == {"unmatched_target": 1}


def test_probability_bins_have_disjoint_closed_endpoint():
    rows = _prob_rows(7)
    for r, p in zip(rows, [0, .099, .1, .2, .4, .6, 1.]):
        r["drawdown_prob"]["h21"] = p
    bins = _audit(rows)["horizons"]["h21"]["bins"]
    assert [b["n"] for b in bins] == [2, 1, 1, 1, 2]
    assert all(b["observed_rate"] is None for b in bins)


def test_probability_existing_producer_uses_same_rows_without_advancing_ledger(tmp_path):
    import hashlib
    rows = _prob_rows(); p = tmp_path / "data/risk_radar/forward_log.jsonl"
    _write_jsonl(p, rows); before = hashlib.sha256(p.read_bytes()).hexdigest()
    result = sc.build(tmp_path, today=date(2026, 9, 20))
    assert result["markets"]["us"]["probability_audit"] == _audit(rows)
    assert "probability_audit" not in result["markets"]["cn"]
    assert result["markets"]["us"]["windows"]["full"] == sc._window(rows, [])
    assert hashlib.sha256(p.read_bytes()).hexdigest() == before
    assert not (tmp_path / "site/riskdata/scorecard.json").exists()


def test_probability_corrupt_and_ungraded_rows_are_accounted():
    a = _audit([None, 3, {"asof": "2026-06-01", "drawdown_prob": {"measure": sc._PROBABILITY_TARGET}}])
    assert a["horizons"]["h21"]["excluded"] == {"invalid_row": 2, "ungraded": 1}


@pytest.mark.parametrize("event_count", [0, 1, 5])
def test_probability_event_coverage_is_not_validation(event_count):
    rows = _prob_rows()
    for r in rows[:event_count]:
        for h in ("h5", "h10", "h21"): r["graded"]["hit"][h]["dd5"] = True
    result = _audit(rows)
    assert result["horizons"]["h21"]["both_outcomes_present"] is (0 < event_count < 5)
    assert result["current_model_validated"] is False
    assert result["publication_timing_verified"] is False
    assert result["sample_unit"] == "overlapping_daily_forecast"


def test_probability_denominators_account_for_every_parsed_row():
    from copy import deepcopy
    rows = _prob_rows(7); rows.append(deepcopy(rows[0])); rows.append(None)
    rows[1]["graded"] = None
    rows[2]["graded"]["hit"]["h5"]["dd5"] = 1
    rows[3]["drawdown_prob"]["h10"] = None
    rows[4]["drawdown_prob"].pop("base_h21")
    a = _audit(rows)
    for h in a["horizons"].values():
        assert h["n"] + h["excluded_n"] == len(rows)
        assert h["paired_n"] + h["missing_baseline_n"] == h["n"]
        assert sum(b["n"] for b in h["bins"]) == h["n"]



def test_caution_persistence_requires_five_known_consecutive_sessions():
    from scripts.research import risk_radar_caution_persistence as cp
    idx = pd.bdate_range("2026-01-01", periods=8)
    caution = pd.Series([1, 1, 1, 1, 1, 1, 1, 1], index=idx, dtype=bool)
    known = pd.Series([1, 1, 1, 1, 1, 1, 0, 1], index=idx, dtype=bool)
    persistent, eligible = cp.persistent_caution(caution, known, 5)
    assert persistent.iloc[4] and persistent.iloc[5]
    assert not eligible.iloc[6] and not eligible.iloc[7]
    assert not persistent.iloc[6] and not persistent.iloc[7]


def test_caution_persistence_rejects_invalid_streak_length():
    from scripts.research import risk_radar_caution_persistence as cp
    idx = pd.bdate_range("2026-01-01", periods=5)
    s = pd.Series(True, index=idx)
    for bad in (0, -1, True, 1.5):
        with pytest.raises(ValueError):
            cp.persistent_caution(s, s, bad)



def test_caution_persistence_daily_result_uses_one_population():
    from scripts.research import risk_radar_caution_persistence as cp
    idx = pd.bdate_range("2026-01-01", periods=8)
    state = pd.Series(
        ["calm", "caution", "caution", "caution", "caution", "caution", "caution", "calm"],
        index=idx,
    )
    known = pd.Series(True, index=idx)
    labels = pd.DataFrame({
        "end": idx,
        "loss": [-.01, -.01, -.01, -.01, -.06, -.06, -.06, -.01],
        "event": [False, False, False, False, True, True, True, False],
    }, index=idx)
    out = cp.daily_result(state, known, labels)
    assert out["n"] == 4  # only dates with a complete 5-session state history
    assert out["events"] == 3
    assert out["caution_plus"]["confusion"] == {"tp": 3, "fp": 0, "fn": 0, "tn": 1}
    assert out["persistent_caution_5"]["confusion"] == {"tp": 2, "fp": 0, "fn": 1, "tn": 1}
    assert out["caution_plus"]["n"] == out["persistent_caution_5"]["n"] == 4



def test_caution_persistence_native_labels_refuse_missing_price_window():
    from scripts.research import risk_radar_caution_persistence as cp
    idx = pd.bdate_range("2026-01-01", periods=6)
    spy = pd.Series([100., 99., float("nan"), 94., 100., 100.], index=idx)
    out = cp.native_forward_labels(spy, idx, horizon=2, depth=.05)
    assert idx[0] not in out.index
    assert idx[1] not in out.index
    assert idx[3] in out.index


def test_caution_persistence_event_view_records_pre_breach_persistence(monkeypatch):
    from scripts.research import risk_radar_caution_persistence as cp
    idx = pd.bdate_range("2026-01-01", periods=50)
    anchor = idx[25]
    spy = pd.Series(100., index=idx)
    spy.iloc[29:] = 94.
    state = pd.Series("calm", index=idx)
    state.iloc[17:27] = "caution"
    known = pd.Series(True, index=idx)
    monkeypatch.setattr(cp, "detect_events", lambda *a, **k: [anchor])
    out = cp.event_result(spy, idx, state, known)
    row = out["rows"][0]
    assert row["persistent_offset"] == -4
    assert row["persistent_before_breach"] is True
    assert out["persistent_by_t0"] == 1



def test_caution_persistence_event_view_marks_left_censored_window(monkeypatch):
    from scripts.research import risk_radar_caution_persistence as cp
    idx = pd.bdate_range("2026-01-01", periods=50)
    anchor = idx[25]
    spy = pd.Series(100., index=idx)
    spy.iloc[29:] = 94.
    state = pd.Series("caution", index=idx)
    known = pd.Series(True, index=idx)
    monkeypatch.setattr(cp, "detect_events", lambda *a, **k: [anchor])
    out = cp.event_result(spy, idx, state, known)
    row = out["rows"][0]
    assert row["persistent_offset"] == -21
    assert row["persistent_left_censored"] is True
    assert out["persistent_left_censored_n"] == 1
    assert out["persistent_exact_lead_n"] == 0
    assert out["persistent_median_lead_uncensored_sessions"] is None



def _attach_prospective_issue(row, *, engine_tag="a", calibration_tag="b",
                              epoch="2026-09-23-prospective-v1"):
    import hashlib
    source_files = {
        "engine/risk_radar.py": engine_tag * 64,
        "engine/indicators.py": "1" * 64,
        "lib/nyse_calendar.py": "2" * 64,
        "lib/store.py": "3" * 64,
        "lib/config.py": "4" * 64,
    }
    bundle = hashlib.sha256(
        json.dumps(source_files, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    identity = {
        "model_contract": "risk_radar_forward_model.v1",
        "risk_schema": "risk_radar.v2",
        "engine_source_sha256": engine_tag * 64,
        "source_bundle_sha256": bundle,
        "source_files_sha256": source_files,
        "calibration_sha256": calibration_tag * 64,
    }
    fingerprint = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    row["forecast_issue"] = {
        "contract": "risk_radar_forward_issue.v1",
        "epoch": epoch,
        "issued_at": row["logged_at"],
        "ledger_lane": "nightly",
        "first_writer_wins": True,
        **identity,
        "model_fingerprint": fingerprint,
    }
    return fingerprint


def test_prospective_probability_never_backfills_legacy_rows():
    rows = _prob_rows()
    p = _audit(rows)["prospective"]
    assert p["status"] == "not_started"
    assert p["ledger_issue_timing_verified"] is False
    assert p["current_model_validated"] is False
    assert p["same_model_issued_n"] == 0
    assert p["issue_excluded"] == {"missing_issue_receipt": len(rows)}


def test_prospective_probability_tracks_latest_exact_model_only():
    rows = _prob_rows(10)
    first_fp = None
    latest_fp = None
    for i, row in enumerate(rows):
        fp = _attach_prospective_issue(
            row,
            engine_tag="a" if i < 5 else "c",
            calibration_tag="b" if i < 5 else "d",
        )
        if i == 0:
            first_fp = fp
        if i == len(rows) - 1:
            latest_fp = fp
    p = _audit(rows)["prospective"]
    assert p["status"] == "accruing"
    assert p["ledger_issue_timing_verified"] is True
    assert p["public_publication_timing_verified"] is False
    assert p["current_model_validated"] is False
    assert p["model_fingerprints_seen"] == 2
    assert p["prior_model_issued_n"] == 5
    assert p["same_model_issued_n"] == 5
    assert p["same_model_graded_n"] == 5
    assert p["awaiting_maturity"] == 0
    assert p["latest_model_fingerprint"] == latest_fp
    assert latest_fp != first_fp
    assert p["horizons"]["h21"]["n"] == 5
    assert p["horizons"]["h21"]["mean_forecast"] == .2
    assert p["horizons"]["h21"]["brier"] == .04


def test_prospective_probability_rejects_tampered_and_tardy_receipts():
    rows = _prob_rows(7)
    for row in rows:
        _attach_prospective_issue(row)
    rows[0]["forecast_issue"]["model_fingerprint"] = "0" * 64
    rows[1]["forecast_issue"]["issued_at"] = "2026-06-10T21:00:00+00:00"
    rows[1]["logged_at"] = rows[1]["forecast_issue"]["issued_at"]
    p = _audit(rows)["prospective"]
    assert p["same_model_issued_n"] == 5
    assert p["issue_excluded"]["model_fingerprint_mismatch"] == 1
    assert p["issue_excluded"]["issue_not_session_timely"] == 1
    assert p["horizons"]["h21"]["n"] == 5


def test_prospective_ungraded_rows_accrue_without_validation():
    rows = _prob_rows(5)
    for row in rows:
        _attach_prospective_issue(row)
        row["graded"] = None
    p = _audit(rows)["prospective"]
    assert p["status"] == "accruing"
    assert p["ledger_issue_timing_verified"] is True
    assert p["same_model_issued_n"] == 5
    assert p["same_model_graded_n"] == 0
    assert p["awaiting_maturity"] == 5
    assert p["current_model_validated"] is False
    for h in ("h5", "h10", "h21"):
        assert p["horizons"][h]["n"] == 0
        assert p["horizons"][h]["brier"] is None


def test_prospective_issue_clock_must_match_first_write_clock():
    rows = _prob_rows(5)
    for row in rows:
        _attach_prospective_issue(row)
    rows[0]["forecast_issue"]["issued_at"] = "2026-06-01T22:00:00+00:00"
    p = _audit(rows)["prospective"]
    assert p["same_model_issued_n"] == 4
    assert p["issue_excluded"]["issue_clock_mismatch"] == 1
    assert p["current_model_validated"] is False



def test_prospective_real_issue_receipt_roundtrips_into_scorecard(tmp_path):
    from engine import risk_radar_audit as rra

    issued_at = "2026-09-23T21:00:00+00:00"
    snap = {
        "asof": "2026-09-23",
        "state": "caution",
        "alert": False,
        "dominant_scare": "credit",
        "top_score": 72.0,
        "scares": [],
        "drawdown_prob": {
            "measure": sc._PROBABILITY_TARGET,
            "h5": .03, "h10": .08, "h21": .16,
            "base_h5": .036, "base_h10": .086, "base_h21": .178,
            "conjunction_n": 1,
        },
    }
    receipt = rra._forward_issue_receipt(root=tmp_path, issued_at=issued_at)
    assert receipt and receipt["source_bundle_sha256"]
    row = rra._entry_from_snapshot(
        snap, issue_receipt=receipt, logged_at=issued_at
    )
    assert row is not None
    p = sc.probability_audit(
        [row], today=date(2026, 9, 23)
    )["prospective"]
    assert p["status"] == "accruing"
    assert p["ledger_issue_timing_verified"] is True
    assert p["same_model_issued_n"] == 1
    assert p["same_model_graded_n"] == 0
    assert p["awaiting_maturity"] == 1
    assert p["latest_source_bundle_sha256"] == receipt["source_bundle_sha256"]
    assert p["current_model_validated"] is False



def _readiness_fixture(*, n_issued=300, n_graded=250, candidate=.10, baseline=.60,
                       event_positions=None):
    event_positions = set(event_positions or [
        *range(10, 15), *range(60, 65), *range(110, 115),
        *range(160, 165), *range(210, 215),
    ])
    start = date(2025, 1, 1)
    cohort = [
        (start + timedelta(days=2 * i), {}, {})
        for i in range(n_issued)
    ]
    sample = []
    for i in range(n_graded):
        y = 1 if i in event_positions else 0
        sample.append((
            (start + timedelta(days=2 * i)).isoformat(),
            candidate, y, baseline,
        ))
    samples = {h: list(sample) for h in ("h5", "h10", "h21")}
    horizons = {
        h: {
            "paired_n": len(sample),
            "missing_baseline_n": 0,
            "excluded_n": 0,
        }
        for h in ("h5", "h10", "h21")
    }
    return cohort, samples, horizons


def test_prospective_validation_event_clusters_do_not_count_overlapping_days_as_episodes():
    sample = [
        ("d0", .1, 1, .2), ("d1", .1, 1, .2),
        ("d2", .1, 0, .2), ("d3", .1, 0, .2),
        ("d4", .1, 0, .2), ("d5", .1, 1, .2),
        ("d6", .1, 0, .2), ("d7", .1, 0, .2),
        ("d8", .1, 0, .2), ("d9", .1, 0, .2),
        ("d10", .1, 0, .2), ("d11", .1, 1, .2),
        ("d12", .1, 1, .2),
    ]
    assert sc._event_cluster_count(sample, 5) == 2


def test_prospective_validation_is_not_mature_before_frozen_sample_floor():
    cohort, samples, horizons = _readiness_fixture(n_issued=100, n_graded=80)
    out = sc._prospective_validation_readiness(cohort, samples, horizons)
    assert out["status"] == "not_mature"
    assert out["promotion_review_eligible"] is False
    assert out["current_model_validated"] is False
    assert out["public_validation_ready"] is False
    assert all(not h["mature"] for h in out["horizons"].values())


def test_prospective_validation_supportive_sample_only_earns_review_eligibility():
    cohort, samples, horizons = _readiness_fixture()
    out = sc._prospective_validation_readiness(cohort, samples, horizons)
    assert out["status"] == "mature_supportive"
    assert out["promotion_review_eligible"] is True
    assert out["full_surface_supportive"] is True
    assert out["authority_h21_supportive"] is True
    assert out["current_model_validated"] is False
    assert out["public_validation_ready"] is False
    for h in ("h5", "h10", "h21"):
        row = out["horizons"][h]
        assert row["mature"] is True
        assert row["event_clusters"] == 5
        assert row["brier_supportive"] is True
        assert row["calibration_supportive"] is True
        assert row["paired_brier_delta_ci90"][1] < 0
        assert row["calibration_gap_ci90"][0] <= 0 <= row["calibration_gap_ci90"][1]


def test_prospective_validation_mature_bad_probabilities_are_refuted():
    cohort, samples, horizons = _readiness_fixture(candidate=.60, baseline=.10)
    out = sc._prospective_validation_readiness(cohort, samples, horizons)
    assert out["status"] == "mature_refuting"
    assert out["promotion_review_eligible"] is False
    assert out["full_surface_supportive"] is False
    assert out["current_model_validated"] is False
    for h in ("h5", "h10", "h21"):
        assert out["horizons"][h]["mature"] is True
        assert out["horizons"][h]["brier_supportive"] is False


def test_prospective_validation_requires_complete_paired_baseline():
    cohort, samples, horizons = _readiness_fixture()
    horizons["h21"]["paired_n"] -= 1
    horizons["h21"]["missing_baseline_n"] = 1
    out = sc._prospective_validation_readiness(cohort, samples, horizons)
    assert out["status"] == "not_mature"
    assert out["horizons"]["h21"]["baseline_complete"] is False
    assert out["horizons"]["h21"]["mature"] is False


def test_prospective_audit_publishes_frozen_readiness_without_validating_legacy_rows():
    p = _audit(_prob_rows())["prospective"]
    r = p["validation_readiness"]
    assert r["definition"] == sc._PROSPECTIVE_VALIDATION_PROTOCOL
    assert r["protocol_commit"] == sc._PROSPECTIVE_VALIDATION_PROTOCOL_COMMIT
    assert r["status"] == "not_started"
    assert r["promotion_review_eligible"] is False
    assert r["current_model_validated"] is False
    assert r["public_validation_ready"] is False


# EW numerical support, frozen October-31 contract; synthetic data only.
# These are not prospective scorecards, forecasts, power or economic results.

def _legacy_bootstrap_reference(values, block, seed, draws=2000):
    import math
    import random
    vals = [float(v) for v in values]
    if not vals or any(not math.isfinite(v) for v in vals):
        return None, None
    n = len(vals); block = max(1, min(int(block), n)); rng = random.Random(int(seed))
    means = []
    for _ in range(int(draws)):
        sample = []
        for _b in range(math.ceil(n / block)):
            start = rng.randrange(n)
            sample.extend(vals[(start + j) % n] for j in range(block))
        means.append(sum(sample[:n]) / n)
    return means, [round(sc._quantile(means, .05), 8), round(sc._quantile(means, .95), 8)]


@pytest.mark.parametrize('values,block,seed', [
    ([.1, -.2, .3, .7, -.4], 3, 20261052),
    ([0.0], 21, 1), ([.5] * 23, 5, 71),
    ([(-1.)**i * (i + 1) / 31 for i in range(31)], 21, 20261052),
    ([0.1, 0.2, -0.7], 0, -7),
])
def test_ew_bootstrap_retains_original_samples_and_bounds(values, block, seed):
    means, bounds = _legacy_bootstrap_reference(values, block, seed)
    assert sc._moving_block_mean_samples(values, block, seed) == means
    assert sc._moving_block_mean_ci(values, block, seed) == bounds


def _ew_input():
    y = [0, 0, 1, 0, 1, 1, 0] * 5
    candidate = [.1 if value == 0 else .9 for value in y]
    return y, candidate, {'baseline-a': [.5] * len(y), 'baseline-b': [.4] * len(y)}


def test_ew_paired_brier_statistics_uses_shared_resamples_and_native_quantile():
    y, p, refs = _ew_input()
    out = sc.ew_paired_brier_statistics(y, p, refs, horizon=21)
    assert out['status'] == 'COMPUTED' and out['draws'] == 2000 and out['block'] == 21
    assert out['seed'] == 20261052 and out['row_count'] == len(y)
    for name, baseline in refs.items():
        diffs = [(a - z)**2 - (b - z)**2 for z, a, b in zip(y, p, baseline)]
        means, _ = _legacy_bootstrap_reference(diffs, 21, 20261052)
        row = out['comparisons'][name]
        assert row['bootstrap_means'] == means
        assert row['mean_delta'] == pytest.approx(sum(diffs) / len(y))
        assert row['tail_fraction_nonnegative'] == sum(x >= 0 for x in means) / 2000
        assert row['upper_bound_strict_look'] == sc._quantile(means, 1 - .05 / 6)
        assert row['upper_bound_stepdown_look'] == sc._quantile(means, 1 - .05 / 3)
    residuals = [a - z for a, z in zip(p, y)]
    means, _ = _legacy_bootstrap_reference(residuals, 21, 20261052)
    assert out['calibration']['bootstrap_means'] == means
    assert out['calibration']['interval90'] == [sc._quantile(means, .05), sc._quantile(means, .95)]


def test_ew_equal_predictions_do_not_become_positive_skill():
    y, p, _ = _ew_input()
    out = sc.ew_paired_brier_statistics(y, p, {'same': p}, horizon=5)
    assert out['comparisons']['same']['mean_delta'] == 0
    assert out['comparisons']['same']['tail_fraction_nonnegative'] == 1
    assert out['intersection_union_tail_fraction'] == 1
    assert out['primary_horizon'] is False


def test_ew_bad_comparator_cannot_hide_failure_against_better_one():
    y, p, _ = _ew_input()
    out = sc.ew_paired_brier_statistics(y, p, {'easy': [.5] * len(y), 'better': y}, horizon=21)
    assert out['comparisons']['easy']['tail_fraction_nonnegative'] == 0
    assert out['comparisons']['better']['tail_fraction_nonnegative'] == 1
    assert out['intersection_union_tail_fraction'] == 1


def test_ew_calibration_exposes_systematic_bias():
    out = sc.ew_paired_brier_statistics([0] * 35, [.2] * 35, {'base': [.5] * 35}, horizon=21)
    assert out['calibration']['mean_residual'] == pytest.approx(.2)
    assert out['calibration']['interval90'][0] > 0
    assert out['calibration']['contains_zero'] is False
    assert out['scientific_acceptance'] is False


@pytest.mark.parametrize('change,reason', [
    (lambda y,p,b: (y[:-1],p,b), 'unaligned_complete_rows_required'),
    (lambda y,p,b: (y,p[:-1],b), 'unaligned_complete_rows_required'),
    (lambda y,p,b: (y,p,{}), 'comparators_required'),
    (lambda y,p,b: (y,p,{'missing': None}), 'unaligned_complete_rows_required'),
    (lambda y,p,b: (y,[float('nan')] + p[1:],b), 'probability_out_of_range'),
    (lambda y,p,b: (y,[True] + p[1:],b), 'probability_out_of_range'),
    (lambda y,p,b: (y,[1.1] + p[1:],b), 'probability_out_of_range'),
    (lambda y,p,b: (y,p,{'bad': [-.1] + p[1:]}), 'probability_out_of_range'),
    (lambda y,p,b: ([None] + y[1:],p,b), 'binary_outcomes_required'),
    (lambda y,p,b: ([True] + y[1:],p,b), 'binary_outcomes_required'),
])
def test_ew_unqualified_rows_never_get_dropped_or_substituted(change, reason):
    y,p,b = change(*_ew_input())
    out = sc.ew_paired_brier_statistics(y,p,b,horizon=21)
    assert out['status'] == 'UNAVAILABLE' and out['reasons'] == [reason]
    assert not out['comparisons']


@pytest.mark.parametrize('horizon', [0, 1, 20, 22, '21', True])
def test_ew_unregistered_horizon_cannot_silently_change_definition(horizon):
    with pytest.raises(ValueError, match='registered_horizon_required'):
        sc.ew_paired_brier_statistics(*_ew_input(), horizon=horizon)


def test_ew_order_seed_and_inputs_are_deterministic():
    import copy
    y,p,b = _ew_input(); original = copy.deepcopy((y,p,b))
    first = sc.ew_paired_brier_statistics(y,p,b,horizon=10)
    second = sc.ew_paired_brier_statistics(y,p,dict(reversed(list(b.items()))),horizon=10)
    assert first == second and (y,p,b) == original
    assert list(first['comparisons']) == sorted(b)


def test_ew_stats_open_no_files_or_model_artifacts(monkeypatch):
    def forbidden(*a, **kw): raise AssertionError('math cannot open source or outcomes')
    monkeypatch.setattr('builtins.open', forbidden)
    out = sc.ew_paired_brier_statistics(*_ew_input(), horizon=21)
    assert out['status'] == 'COMPUTED'
    assert out['statistics_only'] and not out['scientific_acceptance']
    assert not out['source_qualification_checked'] and not out['maturity_checked']
    assert all(v is False for v in out['authority'].values())


def test_ew_vectors_above_work_budget_refused_before_bootstrap():
    out = sc.ew_paired_brier_statistics([0] * 5001, [.5] * 5001, {'b': [.5] * 5001}, horizon=21)
    assert out['reasons'] == ['bounded_rows_required']


def test_ew_holm_uses_registered_two_family_three_look_thresholds():
    out = sc.ew_holm_levels({'grey_deer_ew_mkt_v1': .002, 'grey_deer_ew_rs_v1': .012}, look=1)
    assert out['look_alpha'] == .05 / 3 and out['family_count'] == 2
    rows = {r['family']: r for r in out['families']}
    assert rows['grey_deer_ew_mkt_v1']['alpha'] == .05 / 6
    assert rows['grey_deer_ew_rs_v1']['alpha'] == .05 / 3
    assert all(r['numerical_null_rejected'] for r in rows.values())
    assert out['scientific_acceptance'] is False


def test_ew_absent_family_never_earns_holm_stepdown_credit():
    out = sc.ew_holm_levels({'grey_deer_ew_rs_v1': .012}, look=2)
    rows = {r['family']: r for r in out['families']}
    assert rows['grey_deer_ew_rs_v1']['alpha'] == .05 / 6
    assert rows['grey_deer_ew_rs_v1']['numerical_null_rejected'] is False
    assert rows['grey_deer_ew_mkt_v1']['status'] == 'UNAVAILABLE'


def test_ew_failed_first_family_blocks_the_second_holm_step():
    out = sc.ew_holm_levels({'grey_deer_ew_mkt_v1': .01, 'grey_deer_ew_rs_v1': .012}, look=3)
    assert all(not row['numerical_null_rejected'] for row in out['families'])
    assert out['families'][1]['status'] == 'STEP_DOWN_BLOCKED'


@pytest.mark.parametrize('fractions,look', [({}, 0), ({}, 4), ({}, True),
    ({'unknown_family': .001}, 1), ({'grey_deer_ew_mkt_v1': float('nan')}, 1),
    ({'grey_deer_ew_mkt_v1': True}, 1), ({'grey_deer_ew_mkt_v1': -.1}, 1)])
def test_ew_holm_rejects_changed_family_or_look_and_malformed_tails(fractions, look):
    with pytest.raises(ValueError): sc.ew_holm_levels(fractions, look=look)


def test_ew_complete_absence_is_not_evidence_of_no_effect():
    out = sc.ew_holm_levels({}, look=1)
    assert len(out['families']) == 2
    assert all(r['status'] == 'UNAVAILABLE' and not r['numerical_null_rejected'] for r in out['families'])


def test_ew_support_does_not_activate_registered_reader():
    from scripts import grey_deer_ew_forecast_reader as reader
    assert reader.SCORER_IMPLEMENTED is False


@pytest.mark.parametrize('count,alpha', [(17, .05/6), (34, .05/3)])
def test_ew_finite_bootstrap_disagreement_cannot_masquerade_as_joint_support(count, alpha):
    samples = [-.1] * (2000-count) + [0.] * count
    out = sc.ew_bootstrap_bound_agreement(samples, alpha=alpha)
    assert out['status'] == 'COMPUTED'
    assert out['nonnegative_count'] == count
    assert out['tail_fraction'] == count/2000
    assert out['counted_tail_rejected'] is False
    assert out['interpolated_bound_negative'] is True
    assert out['predicates_agree'] is False
    assert out['both_numerical_conditions_met'] is False
    assert out['disagreement_reason'] == 'finite_draw_tail_quantile_disagreement'
    assert out['scientific_acceptance'] is False


def test_ew_finite_bootstrap_agreement_is_not_a_validation_verdict():
    out = sc.ew_bootstrap_bound_agreement([-.1]*2000, alpha=.05/6)
    assert out['predicates_agree'] and out['both_numerical_conditions_met']
    assert out['disagreement_reason'] is None
    assert out['scientific_acceptance'] is False and out['maturity_checked'] is False
    assert out['source_qualification_checked'] is False
    assert all(v is False for v in out['authority'].values())


def test_ew_zero_bound_is_not_negative_and_cannot_reject():
    out = sc.ew_bootstrap_bound_agreement([0.]*2000, alpha=.05/3)
    assert out['upper_bound'] == 0
    assert not out['interpolated_bound_negative'] and not out['counted_tail_rejected']
    assert out['predicates_agree'] and not out['both_numerical_conditions_met']


@pytest.mark.parametrize('samples', [[], [-.1]*1999, [-.1]*2001,
    [False]+[-.1]*1999, [float('nan')]+[-.1]*1999, [float('inf')]+[-.1]*1999,
    ['-.1']+[-.1]*1999, [1.1]+[-.1]*1999, None])
def test_ew_bound_diagnostic_refuses_incomplete_nonfinite_or_non_brier_draws(samples):
    out = sc.ew_bootstrap_bound_agreement(samples, alpha=.05/6)
    assert out['status'] == 'UNAVAILABLE'
    assert out['both_numerical_conditions_met'] is False
    assert out['scientific_acceptance'] is False


@pytest.mark.parametrize('alpha', [0, .01, .1, True, None, float('nan')])
def test_ew_bound_diagnostic_cannot_select_a_friendlier_level(alpha):
    with pytest.raises(ValueError, match='registered_alpha_required'):
        sc.ew_bootstrap_bound_agreement([-.1]*2000, alpha=alpha)


def test_ew_paired_report_carries_diagnostic_at_both_registered_look_levels():
    out = sc.ew_paired_brier_statistics(*_ew_input(), horizon=21)
    for row in out['comparisons'].values():
        for key, alpha in [('strict_look',.05/6),('stepdown_look',.05/3)]:
            diagnostic = row['finite_draw_checks'][key]
            assert diagnostic == sc.ew_bootstrap_bound_agreement(row['bootstrap_means'], alpha=alpha)
            assert diagnostic['tail_fraction'] == row['tail_fraction_nonnegative']
            assert diagnostic['upper_bound'] == row['upper_bound_'+key]
            assert not diagnostic['scientific_acceptance']


def test_ew_finite_diagnostic_does_not_read_inputs_or_change_samples(monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError('no data access for numerical checks')
    monkeypatch.setattr('builtins.open', forbidden)
    samples = [-.1]*1983 + [0.]*17;before=list(samples)
    sc.ew_bootstrap_bound_agreement(samples, alpha=.05/6)
    assert samples == before


# Synthetic power-design checks do not read or fit any market/forward outcome.
@pytest.mark.parametrize('family', ['grey_deer_ew_mkt_v1','grey_deer_ew_rs_v1'])
def test_ew_synthetic_floor_design_has_exact_overlap_clusters_and_no_future_rows(family):
    from scripts import grey_deer_ew_power_diagnostic as power
    for index in (0,1,7,39,399):
        value=power.sample(family,index)
        assert len(value['outcomes']) == 200
        assert value['event_count'] == 20 and value['non_event_count'] == 180
        assert value['event_clusters'] == 5
        assert sc._event_cluster_count([(None,None,y) for y in value['outcomes']],21) == 5
        assert len(value['synthetic_adverse_indices']) == (12 if family.endswith('rs_v1') else 0)
        assert all(value['outcomes'][i] == 1 for i in value['synthetic_adverse_indices'])
        assert all(0 < p < 1 for p in value['candidate_null']+value['candidate_alternative'])
        assert all(0 < p < 1 for v in value['comparators'].values() for p in v)


def test_ew_synthetic_expected_skill_is_five_percent_not_outcome_selected():
    from scripts import grey_deer_ew_power_diagnostic as power
    value=power.sample('grey_deer_ew_mkt_v1',0)
    assert value['expected_candidate_brier'] == pytest.approx(.09 + .03**2)
    assert value['expected_alternative_brier_skill'] == pytest.approx(.05)
    assert 1-value['expected_candidate_brier']/value['expected_comparator_brier'] == pytest.approx(.05)
    null_loss=power.BASE_LOSS+power.COMPARATOR_AMPLITUDE**2
    assert null_loss == value['expected_comparator_brier']


def test_ew_synthetic_probabilities_do_not_depend_on_generated_outcomes(monkeypatch):
    from scripts import grey_deer_ew_power_diagnostic as power
    original=power._rng
    class ChangedLabels:
        def randint(self,*args): return 5
    base=power.sample('grey_deer_ew_mkt_v1',0)
    monkeypatch.setattr(power,'_rng',lambda f,i,s:ChangedLabels() if s=='labels' else original(f,i,s))
    changed=power.sample('grey_deer_ew_mkt_v1',0)
    assert changed['outcomes'] != base['outcomes']
    assert changed['candidate_alternative'] == base['candidate_alternative']
    assert changed['candidate_null'] == base['candidate_null']
    assert changed['comparators'] == base['comparators']


def test_ew_synthetic_noise_has_declared_blocks_and_independent_arms():
    from scripts import grey_deer_ew_power_diagnostic as power
    signs=power._signs('grey_deer_ew_mkt_v1',17,'candidate')
    transitions=[i for i in range(1,len(signs)) if signs[i]!=signs[i-1]]
    assert len(transitions)>0
    assert all((b-a)%21 == 0 for a,b in zip(transitions,transitions[1:]))
    assert signs != power._signs('grey_deer_ew_mkt_v1',17,'comparator:M0')
    assert signs == power._signs('grey_deer_ew_mkt_v1',17,'candidate')


@pytest.mark.parametrize('family,index',[('unregistered',0),('grey_deer_ew_mkt_v1',-1),
    ('grey_deer_ew_mkt_v1',1000),('grey_deer_ew_rs_v1',True)])
def test_ew_synthetic_unknown_family_or_replication_is_not_rebound(family,index):
    from scripts import grey_deer_ew_power_diagnostic as power
    with pytest.raises(ValueError): power.sample(family,index)


def test_ew_synthetic_condition_calls_original_paired_owner(monkeypatch):
    from scripts import grey_deer_ew_power_diagnostic as power
    from unittest.mock import Mock
    native=Mock(wraps=sc.ew_paired_brier_statistics)
    monkeypatch.setattr(sc,'ew_paired_brier_statistics',native)
    value=power.sample('grey_deer_ew_mkt_v1',0)
    out=power.evaluate_condition(value,'alternative')
    assert native.call_count==1 and native.call_args.kwargs=={'horizon':21}
    assert set(out['comparisons'])=={'M0','B1'}
    assert out['both_with_calibration'] == (
        out['tail_only_with_calibration'] and out['bound_only_with_calibration'])


def test_ew_small_synthetic_run_is_not_registered_power_or_model_acceptance(monkeypatch):
    from scripts import grey_deer_ew_power_diagnostic as power
    def forbidden(*a,**kw): raise AssertionError('pure diagnostic cannot read source or outcomes')
    monkeypatch.setattr('builtins.open',forbidden)
    out=power.run_diagnostic(1)
    assert out['status']=='INSUFFICIENT_REPLICATIONS'
    assert not out['registered_power_artifact'] and not out['scientific_acceptance']
    assert not out['outcome_data_read'] and not out['market_data_read'] and not out['model_fitted']
    assert all(v is False for v in out['authority'].values())
    assert all(not row['replication_floor_met'] and not row['power_threshold_met_in_this_design']
               for row in out['families'].values())
    assert out['design']['conceptual_counts_are_real_receipts'] is False


def test_ew_power_wilson_interval_is_mc_uncertainty_not_forecast():
    from scripts import grey_deer_ew_power_diagnostic as power
    zero=power._wilson(0,400);all_hits=power._wilson(400,400)
    assert zero[0]==0 and 0<zero[1]<.02
    assert .98<all_hits[0]<1 and all_hits[1]==1
    low,high=power._wilson(320,400)
    assert low<.8<high


@pytest.mark.parametrize('replications',[0,True,1001,'400'])
def test_ew_power_invalid_work_budget_is_not_silently_clamped(replications):
    from scripts import grey_deer_ew_power_diagnostic as power
    with pytest.raises(ValueError):power.run_diagnostic(replications)


def test_ew_power_runner_does_not_overwrite_frozen_or_prior_artifact(tmp_path,monkeypatch):
    from scripts import grey_deer_ew_power_diagnostic as power
    def forbidden(*args,**kwargs):raise AssertionError('must reject before simulation')
    monkeypatch.setattr(power,'run_diagnostic',forbidden)
    existing=tmp_path/power.OUTPUT_NAME;existing.write_text('retained original')
    for destination in (existing,tmp_path/'EW_POWER_v1.json'):
        with pytest.raises(SystemExit):
            power.main(['--output',str(destination),'--pre-run-ref','https://github.com/mastermindx-market-intelligence/macro/pull/10798'])
    assert existing.read_text()=='retained original'


def test_ew_power_runner_requires_source_link_before_execution(tmp_path,monkeypatch):
    from scripts import grey_deer_ew_power_diagnostic as power
    def forbidden(*args,**kwargs):raise AssertionError('must reject before simulation')
    monkeypatch.setattr(power,'run_diagnostic',forbidden)
    with pytest.raises(SystemExit):power.main(['--output',str(tmp_path/power.OUTPUT_NAME),'--pre-run-ref','chat-only'])
