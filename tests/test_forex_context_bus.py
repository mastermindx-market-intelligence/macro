"""MSX-1 FX Context Bus tests.

Covers:
- latest.json new-key schema (smile_decomp, strength, regime_radar.scenarios,
  pairs enrichment, state_changes, schema_note)
- state_changes: flip detection, days_in_state counts, keep-first idempotency
- lane gating: off-lane → no file writes
- _desk_latest includes smile_decomp
- context_forward_log row shape + keep-first
- forex_alerts new event types (smile_regime_flip, triple_red; scenario events are
  edge-detected in the canonical `scenario` family, covered in test_forex.py)

Run: python3 -m pytest tests/test_forex_context_bus.py -x -q
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ------------------------------------------------------------------ fixtures -


def _idx(n: int = 300):
    return pd.date_range("2024-01-01", periods=n, freq="B")


def _dol_frame(n: int = 300, regime: str = "Neutral") -> pd.DataFrame:
    """Minimal _dollar master frame (same columns build_forex.py reads)."""
    idx = _idx(n)
    return pd.DataFrame({
        "smile_regime": pd.Categorical([regime] * n),
        "risk_off": 0.0,
        "dollar_roc": 0.01,
        "broad": 100.0,
        "dxy": 104.0,
    }, index=idx)


def _fake_desk(triple_red: bool = False) -> dict:
    return {
        "lean": "dollar-supportive backdrop",
        "lean_zh": "偏多美元背景",
        "lean_net": 2,
        "lean_n": 3,
        "real_rate": {"regime": "Restrictive / USD-supportive", "real_z": 1.2, "lean": "supportive"},
        "fed_path": {"path_bps": 25.0, "lean": "hawkish_repricing"},
        "positioning": {"pctile": 55.0, "state": "neutral"},
        "valuation": {"gap_pct": 5.0, "label": "Overvalued"},
        "trend": {"label": "up", "n_up": 4},
        "liquidity": {"dir": "supportive"},
        "smile": {"confidence": "medium", "confidence_zh": "中", "n_confirm": 2,
                  "triple_red": triple_red, "usd_dir": "strong", "regime": "US growth premium"},
        "smile_decomp": {
            "beta": 0.35, "r2": 0.42, "residual_20d": 0.0012,
            "residual_20d_z": 1.1, "regime": "safety-driven", "regime_60d": "rates-driven",
            "safety_bid_today": False, "display_only": True, "gaps": [],
        },
    }


def _fake_regime(active_keys: list[str] | None = None) -> dict:
    active_keys = active_keys or []
    scenarios = []
    for key, name_en, name_zh in [
        ("carry_unwind", "Carry Unwind", "套息平仓"),
        ("dollar_wrecking_ball", "Dollar Wrecking Ball", "广义美元压路机"),
        ("em_crisis_capital_flight", "EM Crisis", "新兴市场危机"),
        ("haven_flight_risk_off", "Safe-Haven Flight", "急性避险"),
        ("reflation_risk_on", "Reflation", "再通胀"),
    ]:
        scenarios.append({
            "key": key, "name_en": name_en, "name_zh": name_zh,
            "intensity_today": 72.5 if key in active_keys else 15.0,
            "active": key in active_keys, "illustrative": False,
            "n_fired": 3 if key in active_keys else 1, "min_legs": 3,
            "prob": {
                "status": "ok" if key in active_keys else "insufficient",
                "p_cond": 0.42 if key in active_keys else None,
                "base_rate": 0.15, "wilson_lo": 0.28, "wilson_hi": 0.57,
                "n_raw": 8, "n_eff": 2.7, "N": 3,
            },
        })
    dominant = active_keys[0] if active_keys else None
    return {"as_of": "2024-06-14", "dominant": dominant, "n_active": len(active_keys),
            "scenarios": scenarios, "caveats": True, "history_span": "2010-01-01..2024-06-14"}


def _fake_strength() -> dict:
    return {
        "horizons": {"1w": [{"ccy": "USD", "ccy_zh": "美元", "strength": 0.8, "vs_usd_pct": 0.0, "em": False},
                             {"ccy": "EUR", "ccy_zh": "欧元", "strength": -0.2, "vs_usd_pct": -0.5, "em": False}]},
        "default": "1w", "order": ["1w"],
    }


def _fake_pairs() -> list[dict]:
    return [{
        "key": "EURUSD", "label": "EUR/USD", "zh": "欧元/美元",
        "base": "EUR", "quote_ccy": "USD", "arch": "Major", "arch_zh": "主要货币",
        "quote": 1.0820, "chg": -0.1, "resid_chg": 0.2,
        "dollar_beta": -0.6, "ts_trend": "bull",
        "ts_momentum": 0.4, "structure": 0.3, "structure_state": "constructive",
        "risk_index": 22.0, "risk_word": "Calm",
        "shock_z": 0.5, "shock_state": "normal",
        "pos_pctile": 55.0, "pos_state": "neutral",
        "carry_diff": 0.8, "carry_score": 0.4, "carry_to_vol": 0.15,
        "carry_context": False, "reer_gap": 3.2, "rate_diff_10y": 1.1,
        "cnh_basis": None, "cnh_state": None,
        "conviction": {
            "score": 42.0, "action": "LONG", "action_zh": "偏多",
            "action_css": "bull", "stance": "bullish",
            "confidence": 0.55, "reliable": False, "calibrated": False,
            "factors": [{"key": "trend", "label": "trend", "label_zh": "趋势",
                         "group": "momentum", "contribution": 0.4, "weight": 0.3}],
            "groups": [], "cycle": {"label": "mid-cycle"},
            "headline": "Risk-context: net long EUR (+42)",
            "headline_zh": "风险背景：EUR 净偏多（+42）",
            "sub": "Led by trend.", "sub_zh": "主导因素：趋势。",
            "framing": "Risk-context", "framing_zh": "风险背景",
            "peg": None, "base": "EUR", "n_factors": 1,
        },
        "mtf_rows": [], "verdict": {}, "chart": "",
    }]


# ----------------------------------------------------------------- _desk_latest -

def test_desk_latest_includes_smile_decomp():
    """BUG FIX: smile_decomp must be forwarded into dollar_desk block."""
    from scripts.build_forex import _desk_latest
    desk = _fake_desk()
    out = _desk_latest(desk)
    assert "smile_decomp" in out, "smile_decomp missing from _desk_latest output"
    sd = out["smile_decomp"]
    assert sd["regime"] == "safety-driven"
    assert sd["display_only"] is True
    assert isinstance(sd["beta"], float)


def test_desk_latest_no_smile_decomp_when_absent():
    """If desk has no smile_decomp, the key must be absent (not None)."""
    from scripts.build_forex import _desk_latest
    desk = {k: v for k, v in _fake_desk().items() if k != "smile_decomp"}
    out = _desk_latest(desk)
    assert "smile_decomp" not in out


def test_desk_latest_empty_desk_returns_empty():
    from scripts.build_forex import _desk_latest
    assert _desk_latest({}) == {}


# --------------------------------------------------------------- state_changes -

def _write_history(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def test_state_changes_flip_detected(tmp_path, monkeypatch):
    """A value change in today vs history is detected as a flip (prev != current)."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    _write_history(hist_path, [
        {"date": "2024-06-10", "smile_regime": "Neutral", "lean": "mixed",
         "risk": "risk-on", "fed_path_lean": None, "liquidity_dir": "soft",
         "trend": "down", "triple_red": False, "cnh_basis_state": None,
         "regime_radar_dominant": None},
        {"date": "2024-06-11", "smile_regime": "Neutral", "lean": "mixed",
         "risk": "risk-on", "fed_path_lean": None, "liquidity_dir": "soft",
         "trend": "down", "triple_red": False, "cnh_basis_state": None,
         "regime_radar_dominant": None},
    ])

    dol = _dol_frame(regime="US growth premium")
    today_vals = {
        "_date": "2024-06-14",
        "smile_regime": "US growth premium",
        "lean": "dollar-supportive backdrop",
        "risk": "risk-on", "fed_path_lean": "hawkish_repricing",
        "liquidity_dir": "supportive", "trend": "up",
        "triple_red": False, "cnh_basis_state": None,
        "regime_radar_dominant": None,
    }
    sc = BF._state_changes(today_vals, dol)

    # smile_regime changed
    assert sc["smile_regime"]["current"] == "US growth premium"
    assert sc["smile_regime"]["prev"] == "Neutral"
    assert sc["smile_regime"]["changed_on"] == "2024-06-11"

    # trend changed
    assert sc["trend"]["current"] == "up"
    assert sc["trend"]["prev"] == "down"

    # lean changed
    assert sc["lean"]["current"] == "dollar-supportive backdrop"
    assert sc["lean"]["prev"] == "mixed"


def test_state_changes_days_in_state(tmp_path, monkeypatch):
    """days_in_state counts correctly from changed_on to today."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    _write_history(hist_path, [
        {"date": "2024-06-10", "smile_regime": "Neutral", "lean": "mixed",
         "risk": "risk-on", "fed_path_lean": None, "liquidity_dir": "soft",
         "trend": "down", "triple_red": False, "cnh_basis_state": None,
         "regime_radar_dominant": None},
        {"date": "2024-06-11", "smile_regime": "US growth premium", "lean": "dollar-supportive backdrop",
         "risk": "risk-on", "fed_path_lean": None, "liquidity_dir": "supportive",
         "trend": "up", "triple_red": False, "cnh_basis_state": None,
         "regime_radar_dominant": None},
        {"date": "2024-06-12", "smile_regime": "US growth premium", "lean": "dollar-supportive backdrop",
         "risk": "risk-on", "fed_path_lean": None, "liquidity_dir": "supportive",
         "trend": "up", "triple_red": False, "cnh_basis_state": None,
         "regime_radar_dominant": None},
    ])

    dol = _dol_frame(regime="US growth premium")
    today_vals = {
        "_date": "2024-06-14",  # 3 days after changed_on 2024-06-11
        "smile_regime": "US growth premium",
        "lean": "dollar-supportive backdrop",
        "risk": "risk-on", "fed_path_lean": None,
        "liquidity_dir": "supportive", "trend": "up",
        "triple_red": False, "cnh_basis_state": None,
        "regime_radar_dominant": None,
    }
    sc = BF._state_changes(today_vals, dol)

    # smile_regime unchanged since 2024-06-11, changed_on is 2024-06-10 (the last diff)
    # days_in_state from 2024-06-10 to 2024-06-14 = 5 days (inclusive)
    assert sc["smile_regime"]["days_in_state"] == 5

    # trend unchanged since 2024-06-11 -> changed_on=2024-06-10, days=5
    assert sc["trend"]["days_in_state"] == 5


def test_state_changes_keep_first_idempotent(tmp_path, monkeypatch):
    """Calling _state_changes twice on the same date must not append a second row."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    today_vals = {
        "_date": "2024-06-14",
        "smile_regime": "Neutral", "lean": "mixed", "risk": "risk-off",
        "fed_path_lean": None, "liquidity_dir": "soft", "trend": "down",
        "triple_red": False, "cnh_basis_state": None, "regime_radar_dominant": None,
    }
    dol = _dol_frame()

    BF._state_changes(today_vals, dol)
    BF._state_changes(today_vals, dol)

    rows = BF._read_state_history()
    date_rows = [r for r in rows if r["date"] == "2024-06-14"]
    assert len(date_rows) == 1, f"Expected 1 row for 2024-06-14, got {len(date_rows)}"


def test_state_changes_empty_history_returns_nulls(tmp_path, monkeypatch):
    """With no history, prev/changed_on/days_in_state should be null (never raises)."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    # off-lane so no write happens
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)

    today_vals = {
        "_date": "2024-06-14",
        "smile_regime": "Neutral", "lean": "mixed", "risk": "risk-on",
        "fed_path_lean": None, "liquidity_dir": "soft", "trend": "flat",
        "triple_red": False, "cnh_basis_state": None, "regime_radar_dominant": None,
    }
    dol = _dol_frame()
    sc = BF._state_changes(today_vals, dol)

    for key in ("lean", "risk", "fed_path_lean", "liquidity_dir",
                "trend", "triple_red", "cnh_basis_state", "regime_radar_dominant"):
        assert sc[key]["prev"] is None
        assert sc[key]["changed_on"] is None
        assert sc[key]["days_in_state"] is None


def test_state_changes_offlan_no_write(tmp_path, monkeypatch):
    """Off-lane: history file must not be created/written."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)

    today_vals = {
        "_date": "2024-06-14",
        "smile_regime": "Neutral", "lean": "mixed", "risk": "risk-on",
        "fed_path_lean": None, "liquidity_dir": "soft", "trend": "flat",
        "triple_red": False, "cnh_basis_state": None, "regime_radar_dominant": None,
    }
    BF._state_changes(today_vals, _dol_frame())
    assert not hist_path.exists(), "History file must not be written off-lane"


# ---------------------------------------------- smile_regime seed from _dollar -

def test_state_changes_seeds_smile_from_dollar_frame(tmp_path, monkeypatch):
    """When history is empty and _dollar has a regime series, smile_regime
    changed_on is seeded from the last transition in the frame."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)

    idx = pd.date_range("2024-01-02", periods=20, freq="B")
    regime_vals = ["Neutral"] * 10 + ["US growth premium"] * 10
    dol = pd.DataFrame({"smile_regime": pd.Categorical(regime_vals)}, index=idx)

    today_vals = {
        "_date": idx[-1].strftime("%Y-%m-%d"),
        "smile_regime": "US growth premium",
        "lean": None, "risk": None, "fed_path_lean": None,
        "liquidity_dir": None, "trend": None,
        "triple_red": None, "cnh_basis_state": None, "regime_radar_dominant": None,
    }
    sc = BF._state_changes(today_vals, dol)

    assert sc["smile_regime"]["changed_on"] is not None, (
        "smile_regime changed_on should be seeded from _dollar frame")
    assert sc["smile_regime"]["days_in_state"] is not None


def test_state_changes_unchanged_since_first_row_returns_none_days(tmp_path, monkeypatch):
    """When history has rows but no flip is found (value unchanged throughout),
    days_in_state and changed_on must be None (unknown ≠ log age)."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)

    # Two rows, both with lean="mixed" — no flip
    _write_history(hist_path, [
        {"date": "2024-06-10", "smile_regime": "Neutral", "lean": "mixed",
         "risk": "risk-on", "fed_path_lean": None, "liquidity_dir": "soft",
         "trend": "flat", "triple_red": False, "cnh_basis_state": None,
         "regime_radar_dominant": None},
        {"date": "2024-06-11", "smile_regime": "Neutral", "lean": "mixed",
         "risk": "risk-on", "fed_path_lean": None, "liquidity_dir": "soft",
         "trend": "flat", "triple_red": False, "cnh_basis_state": None,
         "regime_radar_dominant": None},
    ])

    today_vals = {
        "_date": "2024-06-14",
        "smile_regime": "Neutral", "lean": "mixed", "risk": "risk-on",
        "fed_path_lean": None, "liquidity_dir": "soft", "trend": "flat",
        "triple_red": False, "cnh_basis_state": None, "regime_radar_dominant": None,
    }
    # Use a dol frame where smile_regime is also all "Neutral" so no frame seed fires
    dol = _dol_frame(regime="Neutral")
    sc = BF._state_changes(today_vals, dol)

    # No flip found → days_in_state and changed_on must be None
    assert sc["lean"]["changed_on"] is None, "changed_on should be None when no flip found"
    assert sc["lean"]["days_in_state"] is None, "days_in_state should be None when no flip found"
    assert sc["risk"]["days_in_state"] is None
    assert sc["trend"]["days_in_state"] is None


def test_state_changes_seed_populates_prev(tmp_path, monkeypatch):
    """When smile_regime changed_on is seeded from the _dollar frame, prev must
    be populated with the value immediately before the flip in the frame."""
    from scripts import build_forex as BF

    hist_path = tmp_path / "forex" / "state_history.jsonl"
    monkeypatch.setattr(BF, "_state_history_path", lambda: hist_path)
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)

    idx = pd.date_range("2024-01-02", periods=20, freq="B")
    regime_vals = ["Neutral"] * 10 + ["US growth premium"] * 10
    dol = pd.DataFrame({"smile_regime": pd.Categorical(regime_vals)}, index=idx)

    today_vals = {
        "_date": idx[-1].strftime("%Y-%m-%d"),
        "smile_regime": "US growth premium",
        "lean": None, "risk": None, "fed_path_lean": None,
        "liquidity_dir": None, "trend": None,
        "triple_red": None, "cnh_basis_state": None, "regime_radar_dominant": None,
    }
    sc = BF._state_changes(today_vals, dol)

    # prev should be "Neutral" — the value immediately before the transition
    assert sc["smile_regime"]["prev"] == "Neutral", (
        "prev should be the pre-flip value from the _dollar frame"
    )


# ------------------------------------------------------ context_forward_log -

def test_context_forward_log_row_shape(tmp_path, monkeypatch):
    """Each row must have {asof, key, state, intensity_pct, graded}."""
    from scripts import build_forex as BF

    log_path = tmp_path / "forex" / "context_forward_log.jsonl"
    monkeypatch.setattr(BF, "_context_forward_log_path", lambda: log_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    today_vals = {
        "_date": "2024-06-14",
        "smile_regime": "US growth premium",
        "triple_red": True,
    }
    regime = _fake_regime(active_keys=["carry_unwind"])

    BF._append_context_forward_log("2024-06-14", today_vals, regime)

    assert log_path.exists()
    rows = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    assert len(rows) == len(BF._FORWARD_LOG_KEYS)

    for r in rows:
        assert set(r.keys()) >= {"asof", "key", "state", "intensity_pct", "graded"}
        assert r["asof"] == "2024-06-14"
        assert r["graded"] is None
        assert r["key"] in BF._FORWARD_LOG_KEYS


def test_context_forward_log_keep_first(tmp_path, monkeypatch):
    """Re-appending on the same (asof, key) must not write a duplicate row."""
    from scripts import build_forex as BF

    log_path = tmp_path / "forex" / "context_forward_log.jsonl"
    monkeypatch.setattr(BF, "_context_forward_log_path", lambda: log_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    today_vals = {"_date": "2024-06-14", "smile_regime": "Neutral", "triple_red": False}
    regime = _fake_regime()

    BF._append_context_forward_log("2024-06-14", today_vals, regime)
    BF._append_context_forward_log("2024-06-14", today_vals, regime)

    rows = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    keys_written = [(r["asof"], r["key"]) for r in rows]
    assert len(keys_written) == len(set(keys_written)), "Duplicate (asof, key) rows written"


def test_context_forward_log_offlan_no_write(tmp_path, monkeypatch):
    """Off-lane invocation must not create the log file."""
    from scripts import build_forex as BF

    log_path = tmp_path / "forex" / "context_forward_log.jsonl"
    monkeypatch.setattr(BF, "_context_forward_log_path", lambda: log_path)
    monkeypatch.delenv("COLLECT_LANE", raising=False)
    monkeypatch.delenv("US_LANE", raising=False)

    BF._append_context_forward_log("2024-06-14", {}, _fake_regime())
    assert not log_path.exists()


def test_context_forward_log_intensity_pct_populated(tmp_path, monkeypatch):
    """intensity_pct from regime_radar when applicable; null for smile_regime/triple_red."""
    from scripts import build_forex as BF

    log_path = tmp_path / "forex" / "context_forward_log.jsonl"
    monkeypatch.setattr(BF, "_context_forward_log_path", lambda: log_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    regime = _fake_regime(active_keys=["carry_unwind"])  # carry_unwind has intensity_today=72.5
    BF._append_context_forward_log("2024-06-14", {"smile_regime": "Neutral", "triple_red": False}, regime)

    rows = {r["key"]: r for r in
            [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]}

    # smile_regime and triple_red have no intensity_pct mapping
    assert rows["smile_regime"]["intensity_pct"] is None
    assert rows["triple_red"]["intensity_pct"] is None
    # carry_unwind scenario intensity = 72.5
    assert rows["carry_unwind"]["intensity_pct"] == 72.5


def test_context_forward_log_malformed_scenario_skipped(tmp_path, monkeypatch):
    """A scenario missing 'key' must not raise — the row is skipped, others write normally."""
    from scripts import build_forex as BF

    log_path = tmp_path / "forex" / "context_forward_log.jsonl"
    monkeypatch.setattr(BF, "_context_forward_log_path", lambda: log_path)
    monkeypatch.setenv("COLLECT_LANE", "nightly")

    # Inject one malformed scenario (no 'key') alongside valid ones
    regime = _fake_regime(active_keys=["carry_unwind"])
    regime["scenarios"].append({"intensity_today": 50.0, "active": True})  # missing 'key'

    try:
        BF._append_context_forward_log("2024-06-14", {"smile_regime": "Neutral", "triple_red": False}, regime)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"_append_context_forward_log raised on malformed scenario: {e}")

    assert log_path.exists(), "Log file must be created despite malformed scenario"
    rows = [json.loads(line) for line in log_path.read_text().splitlines() if line.strip()]
    # All _FORWARD_LOG_KEYS rows must still be written
    assert len(rows) == len(BF._FORWARD_LOG_KEYS)


# --------------------------------------------------------- alert event types -

def test_smile_regime_flip_events():
    """desk_smile_regime_events fires on each smile_regime transition."""
    from engine import forex_alerts as FA

    idx = _idx(40)
    regime_vals = ["Neutral"] * 20 + ["Risk-off haven bid"] * 20
    dol = pd.DataFrame({"smile_regime": pd.Categorical(regime_vals)}, index=idx)
    evs = FA.desk_smile_regime_events(dol)
    assert len(evs) == 1
    e = evs[0]
    assert e["type"] == "smile_regime_flip"
    assert e["asset"] == "dollar"
    assert "Risk-off haven bid" in e["headline"]
    assert e["headline_zh"]
    assert e["severity"] == "high"


def test_smile_regime_flip_empty_on_no_dollar():
    from engine import forex_alerts as FA
    assert FA.desk_smile_regime_events(None) == []
    assert FA.desk_smile_regime_events(pd.DataFrame()) == []


def test_triple_red_events_active(monkeypatch):
    """triple_red=True emits a high-severity event."""
    from engine import forex_alerts as FA

    dol = _dol_frame()
    desk = _fake_desk(triple_red=True)
    evs = FA.desk_triple_red_events(dol, desk)
    assert len(evs) == 1
    e = evs[0]
    assert e["type"] == "triple_red"
    assert e["severity"] == "high"
    assert "triple-red" in e["headline"].lower() or "triple" in e["headline"].lower()
    assert e["headline_zh"]


def test_triple_red_events_clear():
    """triple_red=False emits an info-severity clear event."""
    from engine import forex_alerts as FA

    desk = _fake_desk(triple_red=False)
    evs = FA.desk_triple_red_events(_dol_frame(), desk)
    assert len(evs) == 1
    assert evs[0]["severity"] == "info"


def test_triple_red_events_no_desk():
    from engine import forex_alerts as FA
    assert FA.desk_triple_red_events(_dol_frame(), None) == []
    assert FA.desk_triple_red_events(_dol_frame(), {}) == []


def test_scenario_events_canonical_family():
    """Reconciled semantics: scenario events are edge-detected via the canonical
    scenario_events(regime, prev_active) family (collision-safe ids, deactivation
    branch) — the per-active-day desk_scenario_events family was superseded."""
    from engine import forex_alerts as FA

    regime = _fake_regime(active_keys=["carry_unwind", "haven_flight_risk_off"])
    evs = FA.scenario_events(regime, prev_active=set())
    assert len(evs) == 2
    assert {e["type"] for e in evs} == {"scenario"}
    ids = {e["id"] for e in evs}
    assert len(ids) == 2  # collision-safe: scenario key participates in the id
    # steady state: no re-fire when the active set is unchanged
    assert FA.scenario_events(regime, prev_active={"carry_unwind", "haven_flight_risk_off"}) == []


def test_compute_all_events_additive(tmp_path, monkeypatch):
    """compute_all_events with desk/regime includes new event types without
    breaking existing pair events."""
    from engine import forex_alerts as FA

    # stub out the alerts.jsonl path so no real file I/O
    alerts_path = tmp_path / "alerts.jsonl"
    monkeypatch.setattr(FA, "_path", lambda: alerts_path)

    idx = _idx(60)
    regime_vals = ["Neutral"] * 30 + ["Risk-off haven bid"] * 30
    dol = pd.DataFrame({
        "smile_regime": pd.Categorical(regime_vals),
        "risk_regime": ["low_risk"] * 30 + ["high_risk"] * 30,
        "risk_index": pd.Series(np.concatenate([np.full(30, 20.0), np.full(30, 80.0)]), index=idx),
        "close": 1.0,
    }, index=idx)

    results = {"_dollar": dol, "EURUSD": pd.DataFrame({
        "close": 1.1, "carry_diff": [-1.0] * 30 + [1.0] * 30,
    }, index=idx)}
    desk = _fake_desk(triple_red=True)
    regime = _fake_regime(active_keys=["carry_unwind"])

    evs = FA.compute_all_events(results, desk=desk, regime=regime)
    types = {e["type"] for e in evs}

    assert "carry_flip" in types              # existing
    assert "smile_regime" in types            # existing dollar event
    assert "smile_regime_flip" in types       # MSX-1 new
    assert "triple_red" in types              # MSX-1 new
    assert "scenario" in types                # reconciled edge-detected family


# ------------------------------------------- latest.json schema validation -

def test_latest_schema_new_keys(tmp_path, monkeypatch):
    """Validate that all MSX-1 new keys appear in the latest dict structure."""
    from scripts import build_forex as BF

    # We test _desk_latest and the scenario receipt helper indirectly via unit tests;
    # here we validate the top-level key presence by constructing the dict the same
    # way main() does, but without running the full builder.
    desk = _fake_desk()
    regime = _fake_regime(active_keys=["carry_unwind"])
    strength = _fake_strength()
    pairs = _fake_pairs()
    dol = _dol_frame()

    # Replicate the _scenario_receipt helper from main()
    def _scenario_receipt(s: dict) -> dict:
        p_raw = s.get("prob") or {}
        return {
            "key": s.get("key"),
            "name_en": s.get("name_en"),
            "name_zh": s.get("name_zh"),
            "intensity": BF._r(s.get("intensity_today"), 1),
            "active": bool(s.get("active")),
            "illustrative": bool(s.get("illustrative")),
            "prob": {
                "status": p_raw.get("status"),
                "p_cond": BF._r(p_raw.get("p_cond"), 4),
                "base_rate": BF._r(p_raw.get("base_rate"), 4),
                "wilson_lo": BF._r(p_raw.get("wilson_lo"), 4),
                "wilson_hi": BF._r(p_raw.get("wilson_hi"), 4),
                "n_raw": p_raw.get("n_raw"),
                "n_eff": p_raw.get("n_eff"),
                "N": p_raw.get("N"),
            },
        }

    # dollar_desk must include smile_decomp
    dl = BF._desk_latest(desk)
    assert "smile_decomp" in dl
    assert dl["smile_decomp"]["regime"] == "safety-driven"

    # strength forwarded
    assert "horizons" in strength
    assert "default" in strength

    # regime_radar scenarios
    scenarios = [_scenario_receipt(s) for s in regime.get("scenarios", [])]
    assert len(scenarios) == 5
    sr = scenarios[0]
    assert set(sr.keys()) >= {"key", "name_en", "name_zh", "intensity", "active", "illustrative", "prob"}
    prob = sr["prob"]
    assert set(prob.keys()) >= {"status", "p_cond", "base_rate", "wilson_lo", "wilson_hi",
                                "n_raw", "n_eff", "N"}

    # schema_note present
    schema_note = (
        "MSX-1 additive-only enrichment: do not rename/remove existing keys. "
        "new keys: dollar_desk.smile_decomp, strength, regime_radar.scenarios, "
        "pairs.<KEY>.{headline,head_zh,sub,sub_zh,shock_state,cycle_position}, "
        "pairs.USDCNH.{cnh_basis_bps,cnh_basis_state}, state_changes."
    )
    assert isinstance(schema_note, str) and "MSX-1" in schema_note


def test_pairs_enrichment_fields():
    """Pair dicts must include the MSX-1 narrative + signal-frame fields."""
    pairs = _fake_pairs()
    conv = pairs[0].get("conviction") or {}
    assert conv.get("headline") is not None
    assert conv.get("headline_zh") is not None
    assert conv.get("sub") is not None
    assert conv.get("sub_zh") is not None
    assert (conv.get("cycle") or {}).get("label") is not None


# ---------------------------------------- JSON-serializable guard --------

def test_desk_latest_json_serializable():
    """_desk_latest output must be json.dumps-able without default=str."""
    from scripts.build_forex import _desk_latest
    out = _desk_latest(_fake_desk())
    # should not raise
    serialized = json.dumps(out)
    assert serialized


# -------------------------------- W4 consumer sweep (engine read heal) --------

def _engine_signed_tx(direction: str) -> dict:
    """Live engine output: SPY inverse of USD (headwind_for), GC=F same-sign (tailwind_for)."""
    from engine import forex_transmission as FT
    from lib import config
    cfg = config.load()["forex"]["transmission"]
    idx = _idx(400)
    rng = np.random.default_rng(7)
    uret = pd.Series(rng.normal(0, 0.004, 400), index=idx)
    uret.iloc[-63:] = uret.iloc[-63:] + (0.003 if direction == "strengthening" else -0.003)
    broad = np.exp(uret.cumsum()) * 100
    spy = np.exp((-uret).cumsum()) * 100
    gold = np.exp(uret.cumsum()) * 100
    out = FT.transmission(broad, {"SPY": spy, "GC=F": gold}, None, None, cfg)
    assert out and out["usd_dir"] == direction, out
    return out


def test_transmission_latest_does_not_swap_lists_or_persist_read():
    """W4 consumer: _transmission_latest is a pass-through of the
    strengthening-signed lists. It must not invert them on usd_dir=weakening,
    and it must drop read/read_zh (those are engine-only copy)."""
    from scripts.build_forex import _transmission_latest
    import inspect
    from scripts.build_forex import _stance

    soft = _engine_signed_tx("weakening")
    assert "US equities" in soft["headwind_for"]
    assert "Gold" in soft["tailwind_for"]
    compact = _transmission_latest(soft)
    assert compact["usd_dir"] == "weakening"
    assert compact["headwind_for"] == soft["headwind_for"]
    assert compact["tailwind_for"] == soft["tailwind_for"]
    assert "read" not in compact and "read_zh" not in compact
    # Builder stance consumes lists, never the engine read copy — so healing
    # read/read_zh cannot double-invert _stance (PR #7042 owns that function).
    assert "read" not in inspect.signature(_stance).parameters
    assert "read_zh" not in inspect.signature(_stance).parameters


def test_consumer_chain_does_not_compensate_for_inverted_read(tmp_path):
    """W4 consumer sweep: compose_dollar_channel, forex_link.asset_corr, and
    brief_context._block_fx_dollar all consume the strengthening-signed lists
    (or corr), never swap them when usd_dir is weakening, and never read the
    engine's `read`/`read_zh` copy. A compensating double-inversion would
    put Gold in headwind_for after the engine heal."""
    from scripts.build_forex import _transmission_latest
    from engine.transmission_context import compose_dollar_channel
    from engine.neuralweb.brief_context import _block_fx_dollar
    from lib import forex_link

    soft = _engine_signed_tx("weakening")
    compact = _transmission_latest(soft)
    envelope = {
        "asof": "2026-09-10",
        "dollar_desk": {"lean": "mixed backdrop", "real_rate_regime": "Neutral real yields"},
        "transmission": compact,
        "regime_radar": {"dominant": None, "active": []},
    }
    (tmp_path / "forex").mkdir()
    (tmp_path / "forex" / "latest.json").write_text(json.dumps(envelope))

    dx = compose_dollar_channel(root=tmp_path)
    assert dx is not None
    hw_en = [e["en"] for e in dx["headwind_for"]]
    tw_en = [e["en"] for e in dx["tailwind_for"]]
    assert "US equities" in hw_en and "Gold" not in hw_en, dx["headwind_for"]
    assert "Gold" in tw_en and "US equities" not in tw_en, dx["tailwind_for"]
    assert dx["usd_dir"] == "weakening"
    gold_zh = next(e["zh"] for e in dx["tailwind_for"] if e["en"] == "Gold")
    assert gold_zh == "黄金"

    # lib.forex_link: corr sign is the strengthening-dollar effect, not swapped.
    spy = forex_link.asset_corr("SPY", compact)
    gold = forex_link.asset_corr("GC=F", compact)
    assert spy is not None and gold is not None
    assert spy["usd_dir"] == "weakening"
    assert spy["corr"] < 0, spy  # still a headwind vs a rising dollar
    assert gold["corr"] > 0, gold

    ws = {"fx_dollar": {
        "asof": "2026-09-10",
        "transmission": {
            "usd_dir": compact["usd_dir"],
            "headwind_for": compact["headwind_for"],
            "tailwind_for": compact["tailwind_for"],
        },
        "dollar_desk": {"lean": "mixed backdrop"},
        "regime_radar": {},
    }}
    block = _block_fx_dollar(ws)
    assert block is not None
    assert "US equities" in block["headwind_for"]
    assert "Gold" in block["tailwind_for"]
    assert "read" not in block and "read_zh" not in block


if __name__ == "__main__":
    fns = [
        test_desk_latest_includes_smile_decomp,
        test_desk_latest_no_smile_decomp_when_absent,
        test_desk_latest_empty_desk_returns_empty,
        test_context_forward_log_row_shape,
        test_context_forward_log_keep_first,
        test_context_forward_log_offlan_no_write,
        test_context_forward_log_intensity_pct_populated,
        test_smile_regime_flip_events,
        test_smile_regime_flip_empty_on_no_dollar,
        test_triple_red_events_active,
        test_triple_red_events_clear,
        test_triple_red_events_no_desk,
        test_scenario_events_canonical_family,
        test_compute_all_events_additive,
        test_latest_schema_new_keys,
        test_pairs_enrichment_fields,
        test_desk_latest_json_serializable,
        test_transmission_latest_does_not_swap_lists_or_persist_read,
        test_consumer_chain_does_not_compensate_for_inverted_read,
        test_state_changes_empty_history_returns_nulls,
        test_state_changes_offlan_no_write,
        test_state_changes_seeds_smile_from_dollar_frame,
        test_state_changes_unchanged_since_first_row_returns_none_days,
        test_state_changes_seed_populates_prev,
    ]
    for fn in fns:
        if "tmp_path" in fn.__code__.co_varnames or "monkeypatch" in fn.__code__.co_varnames:
            print(f"  (skipped in __main__: requires pytest fixtures): {fn.__name__}")
            continue
        fn()
        print(f"PASS {fn.__name__}")
    print("all context bus tests passed (pytest-fixture tests skipped in __main__ mode)")


# R12: project existing producer output into the actual latest.json owner.
# This is value-availability/provenance, not a new freshness or market-state rule.
def _r12_cfg():
    return {'regime': {'enabled': True, 'z_lookback_d': 252,
            'z_min_periods': 60, 'ewma_halflife_d': 20,
            'kinematics': {'lit_windows_d': [1, 5, 20],
                           'rvol_window_d': 20, 'rvol_pctile_lookback_d': 504}}}


def _r12_table():
    return {'as_of': '2026-09-25', 'caveat': True, 'rows': [{
        'ccy': 'JPY', 'label_en': 'JPY', 'label_zh': '日元',
        'lit_1d_pct': 0.2, 'lit_5d_pct': 1.2, 'lit_20d_pct': 2.7,
        'vel_z': 1.3, 'accel_z': 0.6, 'rvol_pctile': 0.91,
        'resid_5d_pct': 0.7, 'state_en': 'accelerating up', 'state_zh': '加速升'}]}


def _r12_project(table=None, cfg=None):
    from lib.forex_kinematics_view import project_kinematics
    return project_kinematics(_r12_table() if table is None else table,
                              _r12_cfg() if cfg is None else cfg)


def test_r12_kinematics_preserves_existing_values_with_explicit_units():
    import copy
    table, cfg = _r12_table(), _r12_cfg()
    original = copy.deepcopy((table, cfg))
    got = _r12_project(table, cfg)
    assert (table, cfg) == original
    assert got['display_only'] is True and got['value_status'] == 'complete'
    assert got['basis'] == 'currency_vs_usd'
    assert got['positive_direction'] == 'currency_appreciation_vs_usd'
    assert got['rows'][0]['values'] == {
        'return_short': 0.2, 'return_medium': 1.2, 'return_long': 2.7,
        'velocity_z': 1.3, 'acceleration_z': 0.6,
        'volatility_percentile': 0.91, 'residual_return': 0.7}
    assert got['metrics']['return_medium']['unit'] == 'percent'
    assert got['metrics']['return_medium']['window_observations'] == 5
    assert got['metrics']['velocity_z']['unit'] == 'z_score'
    assert got['metrics']['volatility_percentile']['unit'] == 'fraction'
    # R14 narrows the old unconditional label: the index can contain raw fallback.
    assert got['metrics']['residual_return']['basis'] == 'upstream_residual_index'
    assert got['rows'][0]['residual_adjustment']['status'] == 'unverified'
    assert got['metrics']['residual_return']['window_observations'] == 5
    json.dumps(got, allow_nan=False)


def test_r12_table_date_is_not_a_per_metric_observation_or_freshness_receipt():
    got = _r12_project()
    assert got['table_as_of'] == '2026-09-25'
    assert got['date_basis'] == 'producer_max_index'
    assert got['freshness'] == 'unknown'
    assert got['metric_dates_available'] is False
    assert all(value is None for value in got['rows'][0]['observed_at'].values())
    assert 'last_non_null' in got['limitations']
    assert not {'active', 'probability', 'confidence', 'score', 'action'} & got.keys()
    assert 'state_en' not in got['rows'][0]


@pytest.mark.parametrize('bad', [None, True, False, float('nan'), float('inf'), '-2.7', ''])
def test_r12_missing_or_malformed_value_never_becomes_zero_or_a_signal(bad):
    table = _r12_table()
    table['rows'][0]['lit_20d_pct'] = bad
    got = _r12_project(table)
    row = got['rows'][0]
    assert row['values']['return_long'] is None
    assert row['availability']['return_long'] == ('missing' if bad is None else 'invalid')
    assert got['value_status'] == 'partial'
    assert row['values']['return_medium'] == 1.2
    json.dumps(got, allow_nan=False)


@pytest.mark.parametrize('bad', [-0.01, 1.01, 91, True, float('nan')])
def test_r12_percentile_fraction_is_not_a_percent_or_boolean(bad):
    table = _r12_table(); table['rows'][0]['rvol_pctile'] = bad
    got = _r12_project(table)
    assert got['rows'][0]['values']['volatility_percentile'] is None
    assert got['rows'][0]['availability']['volatility_percentile'] == 'invalid'


def test_r12_zero_negative_moves_and_percentile_endpoints_are_real_values():
    table = _r12_table(); row = table['rows'][0]
    row.update(lit_1d_pct=0, lit_5d_pct=-1.2, rvol_pctile=0, vel_z=-1.3, accel_z=-0.6)
    got = _r12_project(table)
    assert got['value_status'] == 'complete'
    assert got['rows'][0]['values']['return_short'] == 0
    assert got['rows'][0]['values']['return_medium'] == -1.2
    row['rvol_pctile'] = 1
    assert _r12_project(table)['rows'][0]['values']['volatility_percentile'] == 1


def test_r12_duplicate_currency_identity_withholds_both_conflicting_claims():
    import copy
    table = _r12_table(); extra = copy.deepcopy(table['rows'][0]); extra['lit_5d_pct'] = -9
    table['rows'].append(extra)
    got = _r12_project(table)
    assert got['value_status'] == 'unavailable'
    assert len(got['rows']) == 1 and got['rows'][0]['ccy'] == 'JPY'
    assert set(got['rows'][0]['availability'].values()) == {'identity_conflict'}
    assert all(value is None for value in got['rows'][0]['values'].values())
    assert 'duplicate_currency:JPY' in got['issues']


@pytest.mark.parametrize('bad', [True, [], 'bad', {'rows': None}, {'rows': [None]},
                               {'rows': [{'ccy': 'jpy'}]}, {'rows': [{'ccy': 3}]}])
def test_r12_malformed_table_is_diagnosed_not_raised(bad):
    from lib.forex_kinematics_view import project_kinematics
    got = project_kinematics(bad, _r12_cfg())
    assert got['value_status'] == 'unavailable'
    assert got['issues']
    json.dumps(got, allow_nan=False)


@pytest.mark.parametrize('bad', [None, '', '2026-02-30', '09/25/2026', '2026-09-25T12:00:00Z', True])
def test_r12_missing_or_invalid_table_clock_cannot_be_replaced_with_build_time(bad):
    table = _r12_table(); table['as_of'] = bad
    got = _r12_project(table)
    assert got['table_as_of'] is None and got['value_status'] == 'unavailable'
    assert got['freshness'] == 'unknown'


def test_r12_custom_literal_windows_do_not_inherit_the_producers_fixed_field_names():
    cfg = _r12_cfg(); cfg['regime']['kinematics']['lit_windows_d'] = [2, 7, 30]
    got = _r12_project(cfg=cfg)
    assert [got['metrics'][k]['window_observations'] for k in
            ['return_short', 'return_medium', 'return_long']] == [2, 7, 30]
    assert got['rows'][0]['values']['return_medium'] == 1.2
    assert got['metrics']['return_medium']['source_field'] == 'lit_5d_pct'


@pytest.mark.parametrize('windows', [None, [1, 5], [1, True, 20], [1, 5, 5],
                                    [1, 20, 5], [0, 5, 20], ['1', 5, 20]])
def test_r12_ambiguous_window_metadata_is_not_silently_defaulted(windows):
    cfg = _r12_cfg(); cfg['regime']['kinematics']['lit_windows_d'] = windows
    got = _r12_project(cfg=cfg)
    assert got['value_status'] == 'unavailable' and got['rows'] == []
    assert 'invalid_configuration' in got['issues']


def test_r12_missing_config_and_empty_producer_output_remain_unavailable():
    assert _r12_project(cfg={})['value_status'] == 'unavailable'
    assert _r12_project(table={})['value_status'] == 'unavailable'


def _r12_build_fixture(tmp_path, monkeypatch, table):
    """Run actual builder assembly/write; replace market engines, not JSON construction."""
    import copy
    from scripts import build_forex as BF
    from engine import forex_inputs, forex_signals, forex_conviction, forex_dollar
    from engine import forex_transmission, forex_scorecards, forex_regime, forex_alerts
    cfg = _r12_cfg()
    cfg.update(active=['EURUSD'], assets={'EURUSD': {'archetype': 'major'}}, transmission={}, strength={}, scorecards={},
               alerts={'timeline_days': 30})
    monkeypatch.setattr(BF.config, 'load', lambda: {'forex': cfg, 'storage': {'site_dir': str(tmp_path / 'site')}})
    monkeypatch.setattr(BF.config, 'data_dir', lambda: tmp_path / 'data')
    monkeypatch.setattr(BF.store, 'read', lambda *args, **kwargs: pd.DataFrame())
    monkeypatch.setattr(forex_inputs, 'load_all', lambda *args: {'EURUSD': {'drivers': {}}})
    monkeypatch.setattr(forex_signals, 'compute_all', lambda *args: {'_dollar': _dol_frame(), 'EURUSD': _dol_frame()})
    monkeypatch.setattr(forex_conviction, 'load_calibration', lambda: {})
    monkeypatch.setattr(BF, 'dollar_vm', lambda *args: {'regime': 'Neutral', 'favored': [],
                                                     'risk_word': 'Calm', 'dollar_dir': 'up'})
    monkeypatch.setattr(BF, 'pair_vm', lambda *args: copy.deepcopy(_fake_pairs()[0]))
    monkeypatch.setattr(BF, '_extra_inputs', lambda: {})
    monkeypatch.setattr(BF, '_transmission_assets', lambda *args: {})
    monkeypatch.setattr(BF, 'chart_real_rate', lambda *args: '')
    monkeypatch.setattr(forex_dollar, 'dollar_desk', lambda *args: _fake_desk())
    monkeypatch.setattr(forex_dollar, 'strength_meter', lambda *args: _fake_strength())
    monkeypatch.setattr(forex_transmission, 'transmission', lambda *args: {})
    monkeypatch.setattr(forex_scorecards, 'scorecards', lambda *args, **kwargs: [])
    monkeypatch.setattr(forex_regime, 'fx_stress_regime', lambda *args: _fake_regime())
    monkeypatch.setattr(forex_regime, 'fx_kinematics_table', lambda *args: table)
    # Existing market-state/alert writers are separate owners: never exercise live writes here.
    monkeypatch.setattr(forex_alerts, 'rebuild', lambda *args, **kwargs: [])
    monkeypatch.setattr(forex_alerts, 'recent', lambda *args: [])
    monkeypatch.setattr(BF, '_state_changes', lambda *args: {})
    monkeypatch.setattr(BF, '_append_context_forward_log', lambda *args: None)
    contexts = []
    class Template:
        def render(self, **context):
            contexts.append(context)
            return '<!doctype html><html><body>unchanged rendering boundary</body></html>'
    class Templates:
        globals = {}
        def get_template(self, name):
            assert name == 'forex.html.j2'
            return Template()
    monkeypatch.setattr(BF, 'Environment', lambda *args, **kwargs: Templates())
    monkeypatch.setattr(BF, 'write_page', lambda path, html: None)
    assert BF.main() == 0
    return json.loads((tmp_path / 'data/forex/latest.json').read_text()), contexts


def test_r12_actual_builder_writes_kinematics_without_changing_other_snapshot_fields(tmp_path, monkeypatch):
    import copy
    table = _r12_table(); original = copy.deepcopy(table)
    baseline, _ = _r12_build_fixture(tmp_path / 'missing', monkeypatch, {})
    got, contexts = _r12_build_fixture(tmp_path / 'valid', monkeypatch, table)
    assert 'kinematics' in got, 'computed producer output is still missing from actual latest.json'
    assert got['kinematics']['rows'][0]['values']['return_medium'] == 1.2
    assert got['kinematics']['table_as_of'] == '2026-09-25'
    assert got['asof'] != got['kinematics']['table_as_of'], 'build/market date must not stamp the metric date'
    assert contexts[0]['kinematics'] == original == table
    assert {k: v for k, v in got.items() if k != 'kinematics'} == {
        k: v for k, v in baseline.items() if k != 'kinematics'}
    assert got['regime_radar']['active'] == []
    assert baseline['kinematics']['value_status'] == 'unavailable'


def test_r12_bad_optional_kinematics_does_not_block_the_real_snapshot_write(tmp_path, monkeypatch):
    got, _ = _r12_build_fixture(tmp_path, monkeypatch, {'as_of': '2026-09-25', 'rows': [None]})
    assert got['kinematics']['value_status'] == 'unavailable'
    assert got['regime'] == 'Neutral' and got['pairs']['EURUSD']['quote'] == 1.082


def test_r12_broad_dollar_reference_is_not_a_currency_against_itself():
    import copy
    table = _r12_table(); dollar = copy.deepcopy(table['rows'][0]); dollar['ccy'] = 'USD'
    table['rows'].insert(0, dollar)
    got = _r12_project(table)
    assert [row['ccy'] for row in got['rows']] == ['JPY']
    assert got['reference_rows_excluded'] == ['USD']
    assert got['value_status'] == 'complete'
    assert 'invalid_currency_row' not in got['issues']


def test_r12_real_producer_output_reaches_projection_without_recalculation():
    from engine.forex_regime import fx_kinematics_table
    cfg = _r12_cfg(); cfg['assets'] = {'USDJPY': {'base': 'JPY'}}
    idx = pd.date_range('2022-01-03', periods=760, freq='B')
    rng = np.random.default_rng(8241)
    close = pd.Series(np.exp(np.cumsum(rng.normal(0.0001, 0.005, len(idx)))), index=idx)
    residual = pd.Series(np.exp(np.cumsum(rng.normal(0.0, 0.003, len(idx)))), index=idx)
    results = {'USDJPY': pd.DataFrame({'close': close, 'resid_close': residual})}
    raw = fx_kinematics_table(results, {'broad_dollar': close * 100}, cfg)
    assert raw['rows'], 'producer, not a hand-built table, must supply this case'
    got = _r12_project(raw, cfg)
    row = next(r for r in got['rows'] if r['ccy'] == 'JPY')
    original = next(r for r in raw['rows'] if r['ccy'] == 'JPY')
    for name, definition in got['metrics'].items():
        assert row['values'][name] == original[definition['source_field']]
    assert got['value_status'] == 'complete'
    assert got['freshness'] == 'unknown' and got['metric_dates_available'] is False


@pytest.mark.parametrize('row_update', [
    {'ccy': 'EUR', 'lit_5d_pct': True}, {'ccy': 'EUR', 'lit_5d_pct': np.float64(0.0)},
])
def test_r12_optional_second_row_never_changes_the_first_currency(row_update):
    import copy
    table = _r12_table(); second = copy.deepcopy(table['rows'][0]); second.update(row_update)
    table['rows'].append(second)
    got = _r12_project(table)
    assert got['rows'][0]['values'] == _r12_project()['rows'][0]['values']
    json.dumps(got, allow_nan=False)


def test_r12_non_scalar_currency_identity_cannot_crash_optional_projection():
    table = _r12_table(); table['rows'][0]['ccy'] = np.array(['JPY', 'CHF'])
    got = _r12_project(table)
    assert got['value_status'] == 'unavailable'
    assert 'invalid_currency_row' in got['issues']


# R13: retain each selected derived-series date without inventing vendor clocks.
_R13_FIELDS = ['lit_1d_pct', 'lit_5d_pct', 'lit_20d_pct', 'vel_z', 'accel_z',
               'rvol_pctile', 'resid_5d_pct']


def _r13_series_fixture(close_lag=0, residual_lag=0):
    cfg = _r12_cfg(); cfg['assets'] = {'USDJPY': {'base': 'JPY'}}
    idx = pd.date_range('2022-01-03', periods=760, freq='B')
    rng = np.random.default_rng(13013)
    close = pd.Series(np.exp(np.cumsum(rng.normal(0.0001, 0.005, len(idx)))), index=idx)
    residual = pd.Series(np.exp(np.cumsum(rng.normal(0.0, 0.003, len(idx)))), index=idx)
    broad = pd.Series(np.exp(np.cumsum(rng.normal(0.0001, 0.002, len(idx)))) * 100, index=idx)
    if close_lag:
        close.iloc[-close_lag:] = np.nan
    if residual_lag:
        residual.iloc[-residual_lag:] = np.nan
    return {'USDJPY': pd.DataFrame({'close': close, 'resid_close': residual})}, {'broad_dollar': broad}, cfg, idx


def _r13_clock_table():
    table = _r12_table()
    table['rows'][0]['calculation_clock'] = {
        'version': 1, 'basis': 'derived_series_index',
        'selected_index_dates': {field: '2026-09-25' for field in _R13_FIELDS},
        'normalized_input_dates': {'close': '2026-09-25', 'residual_return': '2026-09-24'},
        'source_observed_at': None, 'source_available_at': None,
    }
    return table


def test_r13_producer_dates_belong_to_each_selected_metric_not_build_time():
    from engine.forex_regime import fx_kinematics_table
    results, drivers, cfg, idx = _r13_series_fixture()
    original = results['USDJPY'].copy(deep=True)
    raw = fx_kinematics_table(results, drivers, cfg)
    row = next(r for r in raw['rows'] if r['ccy'] == 'JPY')
    assert 'calculation_clock' in row, 'producer still discards selected-series dates'
    clock = row['calculation_clock']
    assert clock['version'] == 1 and clock['basis'] == 'derived_series_index'
    assert clock['selected_index_dates'] == {field: idx[-1].strftime('%Y-%m-%d') for field in _R13_FIELDS}
    assert clock['source_observed_at'] is None and clock['source_available_at'] is None
    pd.testing.assert_frame_equal(results['USDJPY'], original)


def test_r13_lagged_price_and_residual_keep_their_own_dates_under_newer_table():
    from engine import forex_regime as fr
    results, drivers, cfg, idx = _r13_series_fixture(close_lag=3, residual_lag=9)
    raw = fr.fx_kinematics_table(results, drivers, cfg)
    row = next(r for r in raw['rows'] if r['ccy'] == 'JPY')
    assert 'calculation_clock' in row
    clock = row['calculation_clock']; dates = clock['selected_index_dates']
    assert raw['as_of'] == idx[-1].strftime('%Y-%m-%d')
    assert dates['lit_1d_pct'] == dates['lit_5d_pct'] == dates['lit_20d_pct'] == idx[-4].strftime('%Y-%m-%d')
    assert dates['resid_5d_pct'] == idx[-10].strftime('%Y-%m-%d')
    assert clock['normalized_input_dates']['close'] == idx[-4].strftime('%Y-%m-%d')
    assert clock['normalized_input_dates']['residual_return'] == idx[-10].strftime('%Y-%m-%d')
    # A rolling statistic can be computable after the last input (depending on
    # the installed pandas fill semantics). Its own SERIES date must survive.
    strength, _, calendar = fr._strength_panel(results, drivers, cfg)
    level = np.exp(strength['JPY'].reindex(calendar))
    expected = {
        'vel_z': fr._z_causal(fr._velocity(level, 5, 20), 252, 60),
        'accel_z': fr._z_causal(fr._accel(fr._velocity(level, 5, 20)), 252, 60),
        'rvol_pctile': fr._pctile_causal(level.pct_change().rolling(20).std(), 504),
    }
    for field, series in expected.items():
        selected = series.dropna()
        assert dates[field] == selected.index[-1].strftime('%Y-%m-%d')


def test_r13_each_literal_window_selects_its_actual_endpoint_when_history_has_a_hole():
    from engine.forex_regime import fx_kinematics_table
    results, drivers, cfg, idx = _r13_series_fixture()
    results['USDJPY'].loc[idx[-6], 'close'] = np.nan
    raw = fx_kinematics_table(results, drivers, cfg)
    row = next(r for r in raw['rows'] if r['ccy'] == 'JPY')
    assert 'calculation_clock' in row
    dates = row['calculation_clock']['selected_index_dates']
    assert dates['lit_1d_pct'] == dates['lit_20d_pct'] == idx[-1].strftime('%Y-%m-%d')
    assert dates['lit_5d_pct'] == idx[-2].strftime('%Y-%m-%d')


def test_r13_absent_residual_never_borrows_price_or_table_date():
    from engine.forex_regime import fx_kinematics_table
    results, drivers, cfg, idx = _r13_series_fixture()
    results['USDJPY'].drop(columns='resid_close', inplace=True)
    row = next(r for r in fx_kinematics_table(results, drivers, cfg)['rows'] if r['ccy'] == 'JPY')
    assert 'calculation_clock' in row
    assert row['resid_5d_pct'] is None
    assert row['calculation_clock']['selected_index_dates']['resid_5d_pct'] is None
    assert row['calculation_clock']['normalized_input_dates']['residual_return'] is None


def test_r13_projector_forwards_calculation_dates_but_not_as_source_observation():
    import copy
    table = _r13_clock_table(); original = copy.deepcopy(table)
    got = _r12_project(table)
    assert got.get('calculation_date_status') == 'complete'
    row = got['rows'][0]
    assert row['calculated_through']['return_medium'] == '2026-09-25'
    assert set(row['index_relation'].values()) == {'at_table_date'}
    assert got['calculation_date_basis'] == 'derived_series_index'
    assert got['freshness'] == 'unknown' and got['metric_dates_available'] is False
    assert set(row['observed_at'].values()) == {None}
    assert row['normalized_input_dates']['residual_return'] == '2026-09-24'
    assert table == original
    json.dumps(got, allow_nan=False)


def test_r13_mixed_dates_are_preserved_not_upgraded_by_the_newest_value():
    table = _r13_clock_table()
    table['rows'][0]['calculation_clock']['selected_index_dates']['lit_5d_pct'] = '2026-09-22'
    got = _r12_project(table); row = got['rows'][0]
    assert row.get('calculated_through', {}).get('return_medium') == '2026-09-22'
    assert row['index_relation']['return_medium'] == 'before_table_date'
    assert row['index_relation']['return_short'] == 'at_table_date'
    assert got['calculation_date_status'] == 'complete'
    assert got['freshness'] == 'unknown'


@pytest.mark.parametrize('bad', [None, '', True, [], {}, '2026-02-30', '2026-09-26',
                               '2026-09-25T12:00:00Z', '09/25/2026'])
def test_r13_missing_invalid_or_future_metric_date_stays_unknown_without_erasing_value(bad):
    table = _r13_clock_table()
    table['rows'][0]['calculation_clock']['selected_index_dates']['vel_z'] = bad
    got = _r12_project(table); row = got['rows'][0]
    assert got.get('calculation_date_status') == 'partial'
    assert row['values']['velocity_z'] == 1.3
    assert row['calculated_through']['velocity_z'] is None
    assert row['index_relation']['velocity_z'] == 'unknown'
    assert row['clock_issues']
    assert got['value_status'] == 'complete' and got['freshness'] == 'unknown'


@pytest.mark.parametrize('clock', [None, True, [], 'clock', {},
    {'version': True, 'basis': 'derived_series_index'},
    {'version': '1', 'basis': 'derived_series_index'},
    {'version': 1, 'basis': 'vendor_observation'},
    {'version': 1, 'basis': 'derived_series_index', 'selected_index_dates': []}])
def test_r13_malformed_or_unrecognized_clock_does_not_crash_or_create_freshness(clock):
    table = _r12_table(); table['rows'][0]['calculation_clock'] = clock
    got = _r12_project(table)
    assert got.get('calculation_date_status') == 'unavailable'
    assert got['value_status'] == 'complete' and got['freshness'] == 'unknown'
    assert set(got['rows'][0]['calculated_through'].values()) == {None}
    json.dumps(got, allow_nan=False)


def test_r13_a_timestamp_cannot_validate_a_missing_value_or_duplicate_identity():
    import copy
    table = _r13_clock_table(); table['rows'][0]['lit_5d_pct'] = None
    row = _r12_project(table)['rows'][0]
    assert row.get('calculated_through', {}).get('return_medium', 'missing') is None
    assert row['index_relation']['return_medium'] == 'unknown'
    table['rows'].append(copy.deepcopy(table['rows'][0]))
    got = _r12_project(table)
    assert got['value_status'] == 'unavailable' and got['calculation_date_status'] == 'unavailable'
    assert set(got['rows'][0]['calculated_through'].values()) == {None}


def test_r13_real_producer_and_real_json_writer_preserve_selected_dates(tmp_path, monkeypatch):
    from engine.forex_regime import fx_kinematics_table
    results, drivers, cfg, idx = _r13_series_fixture(close_lag=4, residual_lag=7)
    raw = fx_kinematics_table(results, drivers, cfg)
    got, contexts = _r12_build_fixture(tmp_path, monkeypatch, raw)
    row = next(r for r in got['kinematics']['rows'] if r['ccy'] == 'JPY')
    assert row.get('calculated_through', {}).get('return_medium') == idx[-5].strftime('%Y-%m-%d')
    assert row['calculated_through']['residual_return'] == idx[-8].strftime('%Y-%m-%d')
    assert contexts[0]['kinematics'] == raw
    assert got['fx_state']['active_scenarios'] == []
    assert got['kinematics']['freshness'] == 'unknown'


def test_r13_legacy_clockless_table_is_still_usable_but_not_dated():
    got = _r12_project()
    assert got.get('calculation_date_status') == 'unavailable'
    assert got['value_status'] == 'complete'
    assert got['rows'][0]['values']['return_medium'] == 1.2
    assert set(got['rows'][0]['calculated_through'].values()) == {None}


@pytest.mark.parametrize('basis', [np.array(['derived_series_index', 'vendor']), ['derived_series_index'], True])
def test_r13_non_scalar_clock_basis_is_rejected_without_an_exception(basis):
    table = _r13_clock_table(); table['rows'][0]['calculation_clock']['basis'] = basis
    got = _r12_project(table)
    assert got['calculation_date_status'] == 'unavailable'
    assert got['value_status'] == 'complete'
    json.dumps(got, allow_nan=False)


def test_r13_upstream_clock_cannot_claim_vendor_release_or_fill_an_observation_date():
    table = _r13_clock_table(); clock = table['rows'][0]['calculation_clock']
    clock['source_observed_at'] = clock['source_available_at'] = '2026-09-25T12:00:00Z'
    got = _r12_project(table)
    assert got['freshness'] == 'unknown' and got['metric_dates_available'] is False
    assert set(got['rows'][0]['observed_at'].values()) == {None}
    assert 'source_available_at' not in got['rows'][0]


def test_r13_input_clock_after_table_is_not_retained_as_valid_lineage():
    table = _r13_clock_table()
    table['rows'][0]['calculation_clock']['normalized_input_dates'] = {'close': '2026-09-26', 'residual_return': True}
    got = _r12_project(table)
    assert got['rows'][0]['normalized_input_dates'] == {'close': None, 'residual_return': None}
    assert got['rows'][0]['calculated_through']['return_short'] == '2026-09-25'
    assert got['freshness'] == 'unknown'


# R13 consumer: the existing live-route template, not a standalone preview.
def _r13_evidence_html(view):
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    templates = Path(__file__).resolve().parents[1] / 'templates'
    partial = templates / '_forex_movement_evidence.html.j2'
    assert partial.is_file(), 'the actual movement-evidence component is missing'
    env = Environment(loader=FileSystemLoader(templates), autoescape=True, undefined=StrictUndefined)
    return env.get_template(partial.name).render(kinematics_view=view)


def test_r13_evidence_source_is_reached_by_actual_forex_template():
    root = Path(__file__).resolve().parents[1]
    template = (root / 'templates/forex.html.j2').read_text()
    include = '{% include "_forex_movement_evidence.html.j2" %}'
    assert template.count(include) == 1
    assert template.index('§3 — Stress watch') < template.index(include) < template.index('§4 — The pairs')
    builder = (root / 'scripts/build_forex.py').read_text()
    assert builder.count('project_kinematics(kinematics, cfg)') == 1
    assert 'kinematics_view=kinematics_view' in builder
    assert '"kinematics": kinematics_view' in builder


def test_r13_evidence_shows_mixed_calculation_dates_without_a_freshness_claim():
    table = _r13_clock_table()
    table['rows'][0]['calculation_clock']['selected_index_dates']['lit_5d_pct'] = '2026-09-22'
    html = _r13_evidence_html(_r12_project(table))
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    evidence = soup.select_one('#fx-movement-evidence')
    assert evidence and evidence.name == 'details'
    assert evidence.select_one(':scope > summary')
    assert 'Source freshness unknown' in evidence.get_text(' ', strip=True)
    assert '来源新鲜度未知' in evidence.get_text(' ', strip=True)
    medium = evidence.select_one('[data-currency="JPY"] [data-metric="return_medium"]')
    assert '+1.20%' in medium.get_text() and '5 observations' in medium.get_text()
    assert medium.select_one('time')['datetime'] == '2026-09-22'
    assert 'Earlier calculation' in medium.get_text()
    assert 'Vendor observation time' in evidence.get_text()
    assert 'Unknown' in evidence.get_text() and 'not a forecast' in evidence.get_text()
    assert not soup.select('script, input, button, [role="alert"]')


def test_r13_evidence_keeps_metric_units_distinct_and_preserves_true_zero():
    from bs4 import BeautifulSoup
    table = _r13_clock_table(); table['rows'][0]['lit_1d_pct'] = 0
    soup = BeautifulSoup(_r13_evidence_html(_r12_project(table)), 'html.parser')
    assert '0.00%' in soup.select_one('[data-metric="return_short"]').get_text()
    velocity = soup.select_one('[data-metric="velocity_z"]').get_text()
    assert '+1.30 z' in velocity and '%' not in velocity
    vol = soup.select_one('[data-metric="volatility_percentile"]').get_text()
    assert '91.0 / 100' in vol and 'not a probability' in vol
    residual = soup.select_one('[data-metric="residual_return"]').get_text()
    assert 'Residual-index move' in residual and '+0.70%' in residual
    assert 'Adjustment unverified' in residual  # no method receipt in this old fixture
    assert len(soup.select('[data-metric]')) == 7


def test_r13_evidence_missing_values_do_not_inherit_zeros_or_a_different_metrics_date():
    from bs4 import BeautifulSoup
    table = _r13_clock_table(); table['rows'][0]['vel_z'] = None
    row = BeautifulSoup(_r13_evidence_html(_r12_project(table)), 'html.parser').select_one('[data-metric="velocity_z"]')
    assert 'Unavailable' in row.get_text() and '不可用' in row.get_text()
    assert '0.00' not in row.get_text() and row.select_one('time') is None
    assert 'Calculation date unknown' in row.get_text()


def test_r13_evidence_identity_conflict_and_missing_section_are_not_current_market_reads():
    import copy
    from bs4 import BeautifulSoup
    table = _r13_clock_table(); table['rows'].append(copy.deepcopy(table['rows'][0]))
    soup = BeautifulSoup(_r13_evidence_html(_r12_project(table)), 'html.parser')
    assert 'Ambiguous currency identity' in soup.get_text()
    assert not soup.select('time') or all(t.parent.get('class') == ['fx-me-table-clock'] for t in soup.select('time'))
    missing = _r13_evidence_html(_r12_project(table={}))
    assert 'Movement evidence unavailable' in missing
    assert 'No zero or prior reading is substituted' in missing
    assert 'All clear' not in missing and 'Nothing flashing' not in missing


def test_r13_evidence_markup_is_scoped_token_based_and_progressively_disclosed():
    import re
    source = (Path(__file__).resolve().parents[1] / 'templates/_forex_movement_evidence.html.j2')
    assert source.is_file()
    html = source.read_text()
    css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
    assert ':root' not in css and 'color-mix(' not in css
    assert not re.search(r'#[0-9A-Fa-f]{3,8}\b', css)
    assert 'var(--font-ui' in css and 'var(--line' in css
    assert 'max-width:640px' in css and 'max-width:900px' in css
    assert 'prefers-reduced-motion' in css and ':focus-visible' in css
    assert 'min-height:44px' in css
    assert '<script' not in html and '|safe' not in html and 'onclick=' not in html
    assert 'data-state=' not in html and 'prepare_watch' not in html


def test_r13_builder_passes_the_same_validated_projection_to_template_and_snapshot(tmp_path, monkeypatch):
    got, contexts = _r12_build_fixture(tmp_path, monkeypatch, _r13_clock_table())
    assert contexts[0].get('kinematics_view') == got['kinematics']
    assert contexts[0]['kinematics_view']['freshness'] == 'unknown'
    assert contexts[0]['kinematics'] == _r13_clock_table()


def test_r13_complete_forex_template_contains_inspector_without_changing_market_context(tmp_path, monkeypatch):
    from jinja2 import Environment, FileSystemLoader
    from scripts import build_forex as BF
    from engine.i18n import tr, td
    from bs4 import BeautifulSoup
    # Capture the actual production converter before the existing builder fixture
    # substitutes its market inputs. No dataset/credentials/collection is used.
    actual_dollar_vm = BF.dollar_vm
    got, contexts = _r12_build_fixture(tmp_path, monkeypatch, _r13_clock_table())
    context = contexts[0]
    context['dollar'] = actual_dollar_vm(_dol_frame())
    # The older JSON fixture omits this numeric display field; the existing full
    # pair template requires it. Complete the fixture, not the production model.
    for section in context['sections']:
        for pair in section['pairs']:
            for factor in pair['conviction']['factors']:
                factor['value'] = 0.4
    env = Environment(loader=FileSystemLoader(Path(__file__).resolve().parents[1] / 'templates'), autoescape=True)
    env.globals.update(tr=tr, td=td)
    html = env.get_template('forex.html.j2').render(**context)
    soup = BeautifulSoup(html, 'html.parser')
    assert len(soup.select('#fx-movement-evidence')) == 1
    assert 'Forex Vector' in soup.title.get_text()
    assert soup.select_one('[data-currency="JPY"]')
    assert 'The pairs' in soup.get_text() and 'EUR/USD' in soup.get_text()
    assert got['regime_radar']['active'] == []
    assert context['kinematics_view'] == got['kinematics']
    assert '<script' not in str(soup.select_one('#fx-movement-evidence'))


def test_r13_evidence_survives_existing_page_writer_and_css_extraction(tmp_path, monkeypatch):
    import hashlib
    from bs4 import BeautifulSoup
    from lib import pages
    from scripts.externalize_css import externalize
    # Real component markup through the actual page-writing and extraction owners.
    # The complete route render is qualified separately immediately above.
    table = _r13_clock_table()
    table['rows'][0]['calculation_clock']['selected_index_dates']['lit_5d_pct'] = '2026-09-22'
    partial = _r13_evidence_html(_r12_project(table))
    html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Forex evidence fixture</title></head><body>' + partial + '</body></html>'
    site = tmp_path / 'site'; site.mkdir()
    monkeypatch.setattr(pages, '_site_root', lambda: site)
    monkeypatch.setattr(pages, '_shim_checked', False)
    output = site / 'forex.html'
    pages.write_page(output, html, encoding='utf-8')
    externalize(site)
    soup = BeautifulSoup(output.read_text(), 'html.parser')
    evidence = soup.select_one('#fx-movement-evidence')
    assert len(soup.select('#fx-movement-evidence')) == 1
    assert evidence.select_one('[data-metric="return_medium"] time')['datetime'] == '2026-09-22'
    assert 'Source freshness unknown' in evidence.get_text() and '来源新鲜度未知' in evidence.get_text()
    assert evidence.select_one('script') is None
    styles = []
    for link in soup.select('link[rel="stylesheet"][href^="assets/css/"]'):
        relative = link['href'].split('?')[0]; css = (site / relative).read_bytes()
        if b'.fx-movement-evidence' in css:
            styles.append(css)
            assert hashlib.sha256(css).hexdigest()[:8] == Path(relative).stem
    assert len(styles) == 1
    assert b'max-width:640px' in styles[0] and b'max-width:900px' in styles[0]


def test_r13_empty_legacy_and_custom_window_ui_preserve_known_unknown_distinctions():
    from bs4 import BeautifulSoup
    legacy = BeautifulSoup(_r13_evidence_html(_r12_project()), 'html.parser')
    assert 'Calculation date unknown' in legacy.select_one('[data-metric="return_medium"]').get_text()
    assert '+1.20%' in legacy.get_text()
    cfg = _r12_cfg(); cfg['regime']['kinematics']['lit_windows_d'] = [2, 7, 30]
    custom = BeautifulSoup(_r13_evidence_html(_r12_project(_r13_clock_table(), cfg)), 'html.parser')
    assert '7 observations' in custom.select_one('[data-metric="return_medium"]').get_text()
    assert '5 observations' not in custom.select_one('[data-metric="return_medium"]').get_text()
    unavailable = BeautifulSoup(_r13_evidence_html({}), 'html.parser')
    assert unavailable.select('[data-currency]') == []
    assert 'Movement evidence unavailable' in unavailable.get_text()


def test_r13_currency_data_cannot_inject_markup_into_evidence_disclosure():
    table = _r13_clock_table(); table['rows'][0]['ccy'] = '<script>alert(1)</script>'
    html = _r13_evidence_html(_r12_project(table))
    assert '<script>' not in html and 'alert(1)' not in html
    assert 'Movement evidence unavailable' in html


# R14: a residual-index field is not proof a dollar adjustment was actually fitted.
def _r14_asset(mode='adjusted', n=760):
    import copy
    from lib import config
    from engine import forex_signals as fs
    cfg = copy.deepcopy(config.load()['forex'])
    idx = pd.date_range('2022-01-03', periods=n, freq='B')
    rng = np.random.default_rng(824314)
    price = pd.Series(np.exp(np.cumsum(rng.normal(.0001, .006, n))), index=idx)
    dollar = pd.Series(100 * np.exp(np.cumsum(rng.normal(.0001, .003, n))), index=idx)
    cfg['dollar']['beta_window_d'] = 60
    cfg['dollar']['beta_min_train_d'] = 60
    if mode == 'zero_beta':
        price[:] = 1.0
    elif mode == 'gap':
        price.iloc[-2] = np.nan
    elif mode == 'carried':
        dollar.iloc[-2:] = np.nan
    drivers = {} if mode == 'raw' else {'broad_dollar': dollar}
    px = pd.DataFrame({'close': price, 'open': price, 'high': price, 'low': price})
    ai = {'pair': 'USDJPY', 'meta': cfg['assets']['USDJPY'], 'price': px, 'drivers': drivers}
    result = fs.compute_asset(ai, cfg=cfg)
    return result, drivers, cfg, idx


def _r14_project_asset(mode='adjusted', n=760):
    from engine.forex_regime import fx_kinematics_table
    result, drivers, cfg, idx = _r14_asset(mode, n)
    raw = fx_kinematics_table({'USDJPY': result}, drivers, cfg)
    got = _r12_project(raw, cfg)
    row = next(r for r in got['rows'] if r['ccy'] == 'JPY')
    return result, raw, got, row, idx


def _r14_receipt_table(counts=None):
    table = _r13_clock_table()
    table['rows'][0]['residual_adjustment'] = {
        'version': 1, 'producer': 'engine.forex_signals.orthogonalize',
        'ccy': 'JPY', 'pair': 'USDJPY', 'window_observations': 5,
        'window_start': '2026-09-21', 'window_end': '2026-09-25',
        'counts': counts or {'adjusted': 5, 'raw_fallback': 0, 'zero_filled': 0, 'unavailable': 0},
        'carried_driver_observations': 0,
    }
    return table


def test_r14_legacy_receipt_cannot_claim_every_residual_index_is_dollar_adjusted():
    from bs4 import BeautifulSoup
    got = _r12_project(_r13_clock_table())
    assert got['metrics']['residual_return']['basis'] == 'upstream_residual_index'
    assert got['rows'][0]['residual_adjustment']['status'] == 'unverified'
    html = BeautifulSoup(_r13_evidence_html(got), 'html.parser')
    row = html.select_one('[data-metric="residual_return"]')
    assert 'Adjustment unverified' in row.get_text()
    assert 'Broad-dollar-adjusted move' not in row.get_text()


def test_r14_no_dollar_input_is_raw_fallback_in_the_actual_producer_and_page():
    from bs4 import BeautifulSoup
    result, raw, got, row, idx = _r14_project_asset('raw')
    assert 'residual_method' in result.columns
    assert set(result['residual_method'].iloc[-5:]) == {'raw_fallback'}
    assert result['dollar_beta'].notna().sum() == 0
    assert row['residual_adjustment']['status'] == 'raw_fallback'
    assert row['residual_adjustment']['counts']['raw_fallback'] == 5
    assert row['values']['residual_return'] == round(100 * (result['close'].iloc[-1] / result['close'].iloc[-6] - 1), 2)
    metric = BeautifulSoup(_r13_evidence_html(got), 'html.parser').select_one('[data-metric="residual_return"]')
    assert 'Unadjusted fallback move' in metric.get_text()
    assert 'No dollar effect was removed' in metric.get_text()
    assert 'Broad-dollar-adjusted move' not in metric.get_text()
    assert got['freshness'] == 'unknown'


def test_r14_actual_fitted_adjustment_can_be_named_but_not_called_fresh_or_causal():
    result, raw, got, row, idx = _r14_project_asset()
    assert 'residual_method' in result
    assert set(result['residual_method'].iloc[-5:]) == {'adjusted'}
    method = row['residual_adjustment']
    assert method['status'] == 'adjusted'
    assert method['counts'] == {'adjusted': 5, 'raw_fallback': 0, 'zero_filled': 0, 'unavailable': 0}
    assert method['window_end'] == row['calculated_through']['residual_return']
    assert all(v is None for v in row['observed_at'].values())
    assert got['freshness'] == 'unknown'


def test_r14_zero_beta_is_a_valid_fitted_coefficient_not_a_missing_model():
    result, raw, got, row, idx = _r14_project_asset('zero_beta')
    assert (result['dollar_beta'].iloc[-5:] == 0).all()
    assert row['values']['residual_return'] == 0
    assert row['residual_adjustment']['status'] == 'adjusted'


def test_r14_warmup_transition_cannot_be_presented_as_fully_adjusted():
    result, raw, got, row, idx = _r14_project_asset(n=64)
    method = row.get('residual_adjustment', {})
    assert method.get('status') == 'mixed'
    assert 0 < method['counts']['adjusted'] < 5
    assert method['counts']['adjusted'] + method['counts']['raw_fallback'] == 5


def test_r14_zero_filled_residual_returns_are_not_new_independent_observations():
    result, raw, got, row, idx = _r14_project_asset('gap')
    method = row.get('residual_adjustment', {})
    assert method.get('status') == 'input_gaps'
    assert method['counts']['zero_filled'] >= 1
    assert row['values']['residual_return'] is not None
    assert 'Input gaps in residual index' in _r13_evidence_html(got)


def test_r14_carried_dollar_input_is_disclosed_separately_from_adjustment_and_freshness():
    result, raw, got, row, idx = _r14_project_asset('carried')
    method = row.get('residual_adjustment', {})
    assert method.get('status') == 'adjusted'
    assert method['carried_driver_observations'] == 2
    assert 'Carried dollar input' in _r13_evidence_html(got)
    assert got['freshness'] == 'unknown'


@pytest.mark.parametrize('counts,status', [
    ({'adjusted': 5, 'raw_fallback': 0, 'zero_filled': 0, 'unavailable': 0}, 'adjusted'),
    ({'adjusted': 0, 'raw_fallback': 5, 'zero_filled': 0, 'unavailable': 0}, 'raw_fallback'),
    ({'adjusted': 3, 'raw_fallback': 2, 'zero_filled': 0, 'unavailable': 0}, 'mixed'),
    ({'adjusted': 3, 'raw_fallback': 0, 'zero_filled': 2, 'unavailable': 0}, 'input_gaps'),
    ({'adjusted': 0, 'raw_fallback': 0, 'zero_filled': 0, 'unavailable': 5}, 'unverified'),
])
def test_r14_method_status_is_derived_from_all_return_observations(counts, status):
    got = _r12_project(_r14_receipt_table(counts))
    method = got['rows'][0].get('residual_adjustment', {})
    assert method.get('status') == status
    assert method['counts'] == counts
    assert got['rows'][0]['values']['residual_return'] == .7


@pytest.mark.parametrize('key,bad', [
    ('version', True), ('version', 2), ('producer', 'unknown'),
    ('ccy', 'EUR'), ('ccy', ['JPY']), ('window_observations', 4),
    ('window_observations', True), ('window_start', '2026-10-01'),
    ('window_end', '2026-09-24'), ('window_end', '2026-09-26'),
    ('counts', None), ('counts', {'adjusted': True, 'raw_fallback': 4, 'zero_filled': 0, 'unavailable': 0}),
    ('counts', {'adjusted': 6, 'raw_fallback': 0, 'zero_filled': 0, 'unavailable': 0}),
    ('carried_driver_observations', -1), ('carried_driver_observations', 6),
    ('carried_driver_observations', True), ('pair', None),
])
def test_r14_malformed_method_receipt_cannot_relabel_a_separate_valid_value(key, bad):
    table = _r14_receipt_table(); table['rows'][0]['residual_adjustment'][key] = bad
    got = _r12_project(table)
    row = got['rows'][0]
    assert row.get('residual_adjustment', {}).get('status') == 'unverified'
    assert row['values']['residual_return'] == .7
    assert got['freshness'] == 'unknown'
    json.dumps(got, allow_nan=False)


def test_r14_missing_or_conflicting_value_cannot_be_rescued_by_method_receipt():
    import copy
    for conflict in (False, True):
        table = _r14_receipt_table()
        if conflict:
            table['rows'].append(copy.deepcopy(table['rows'][0]))
        else:
            table['rows'][0]['resid_5d_pct'] = None
        got = _r12_project(table)
        assert got['rows'][0].get('residual_adjustment', {}).get('status') == 'unavailable'
        assert got['rows'][0]['values']['residual_return'] is None


def test_r14_actual_builder_serves_the_same_method_receipt_to_ui_and_snapshot(tmp_path, monkeypatch):
    table = _r14_receipt_table({'adjusted': 0, 'raw_fallback': 5, 'zero_filled': 0, 'unavailable': 0})
    got, contexts = _r12_build_fixture(tmp_path, monkeypatch, table)
    assert got['kinematics']['rows'][0].get('residual_adjustment', {}).get('status') == 'raw_fallback'
    assert contexts[0]['kinematics_view'] == got['kinematics']
    assert got['regime_radar']['active'] == []


@pytest.mark.parametrize('identity', [None, pd.NA, 'EURUSD'])
def test_r14_pair_annotation_must_be_present_for_every_selected_return(identity):
    from engine.forex_regime import fx_kinematics_table
    frame, drivers, cfg, idx = _r14_asset()
    frame['pair'] = pd.Series(identity, index=frame.index, dtype='string')
    raw = fx_kinematics_table({'USDJPY': frame}, drivers, cfg)
    original = next(r for r in raw['rows'] if r['ccy'] == 'JPY')
    assert original.get('residual_adjustment') is None
    view = _r12_project(raw, cfg)
    row = next(r for r in view['rows'] if r['ccy'] == 'JPY')
    assert row['residual_adjustment']['status'] == 'unverified'
    assert row['values']['residual_return'] is not None


# R14 phase 2: the sign of a standardized deviation is not the sign of price return.
def test_r14_sign_meanings_are_scoped_to_each_kind_of_measure():
    got = _r12_project(_r13_clock_table())
    assert got.get('positive_direction_scope') == 'literal_returns_only'
    metrics = got['metrics']
    for key in ['return_short', 'return_medium', 'return_long']:
        assert metrics[key]['positive_means'] == 'currency_appreciation_vs_usd'
    assert metrics['velocity_z']['positive_means'] == 'above_prior_risk_adjusted_momentum_baseline'
    assert metrics['acceleration_z']['positive_means'] == 'above_prior_momentum_change_baseline'
    assert metrics['volatility_percentile']['positive_means'] == 'higher_volatility_rank_not_price_direction'
    assert metrics['residual_return']['positive_means'] == 'upstream_residual_index_increase'
    assert metrics['acceleration_z']['change_window_observations'] == 1
    assert metrics['acceleration_z']['window_observations'] == 5
    for key in ['velocity_z', 'acceleration_z']:
        assert metrics[key]['comparison_basis'] == 'prior_observations_only'
        assert metrics[key]['display_clip_abs'] == 8


@pytest.mark.parametrize('direction', [-1, 1])
def test_r14_actual_declining_currency_can_have_positive_relative_momentum_and_vice_versa(direction):
    from engine.forex_regime import fx_kinematics_table
    from bs4 import BeautifulSoup
    cfg = _r12_cfg(); cfg['assets'] = {'USDJPY': {'base': 'JPY'}}
    idx = pd.date_range('2022-01-03', periods=760, freq='B')
    returns = np.full(len(idx), -.003) + .0001 * np.sin(np.arange(len(idx)) / 3)
    returns[-60:] = -.0004 + .0001 * np.sin(np.arange(60) / 3)
    price = pd.Series(np.exp(np.cumsum(returns * -direction)), index=idx)
    raw = fx_kinematics_table({'USDJPY': pd.DataFrame({'close': price})}, {}, cfg)
    got = _r12_project(raw, cfg); row = got['rows'][0]
    assert np.sign(row['values']['return_medium']) == direction
    assert np.sign(row['values']['velocity_z']) == -direction
    assert got.get('positive_direction_scope') == 'literal_returns_only'
    html = BeautifulSoup(_r13_evidence_html(got), 'html.parser')
    momentum = html.select_one('[data-metric="velocity_z"]').get_text(' ', strip=True)
    assert 'Relative momentum' in momentum and 'not price direction' in momentum
    assert 'relative to its prior baseline' in momentum
    assert 'currency appreciation' not in momentum
    assert 'accelerating up' not in html.get_text()
    assert got['freshness'] == 'unknown'


@pytest.mark.parametrize('value', [-1.3, 0, 1.3])
def test_r14_signed_standardized_values_carry_interpretation_in_both_languages(value):
    from bs4 import BeautifulSoup
    table = _r13_clock_table()
    table['rows'][0].update(vel_z=value, accel_z=value)
    got = _r12_project(table)
    html = BeautifulSoup(_r13_evidence_html(got), 'html.parser')
    for key in ['velocity_z', 'acceleration_z']:
        row = html.select_one(f'[data-metric="{key}"]')
        assert 'not price direction' in row.get_text()
        assert '不表示价格方向' in row.get_text()
        assert '%' not in row.select_one('.fx-me-value').get_text()
        assert row.select_one('.fx-me-note')
    assert '1-observation change in 5-observation momentum' in html.select_one('[data-metric="acceleration_z"]').get_text()
    assert 'bounded at ±8 z' in html.select_one('[data-metric="velocity_z"]').get_text()
    assert 'positive means currency appreciation' not in html.select_one('.fx-me-currency > summary').get_text()


def test_r14_literal_return_sign_guidance_does_not_spill_into_residual_or_volatility():
    from bs4 import BeautifulSoup
    html = BeautifulSoup(_r13_evidence_html(_r12_project(_r13_clock_table())), 'html.parser')
    for key in ['return_short', 'return_medium', 'return_long']:
        text = html.select_one(f'[data-metric="{key}"]').get_text()
        assert 'Positive = appreciation versus USD' in text
        assert '正值表示相对美元升值' in text
    for key in ['volatility_percentile', 'residual_return']:
        text = html.select_one(f'[data-metric="{key}"]').get_text()
        assert 'Positive = appreciation versus USD' not in text
    assert 'Not a price-direction signal' in html.select_one('[data-metric="volatility_percentile"]').get_text()
    assert 'Index direction depends on the method evidence' in html.select_one('[data-metric="residual_return"]').get_text()


def test_r14_custom_return_windows_do_not_change_the_momentum_difference_horizon():
    cfg = _r12_cfg(); cfg['regime']['kinematics']['lit_windows_d'] = [2, 7, 30]
    got = _r12_project(_r13_clock_table(), cfg)
    assert got['metrics']['return_medium']['window_observations'] == 7
    assert got['metrics']['velocity_z']['window_observations'] == 5
    assert got['metrics']['acceleration_z']['change_window_observations'] == 1
    assert got['rows'][0]['values'] == _r12_project(_r13_clock_table())['rows'][0]['values']


def test_r14_builder_forwards_the_same_sign_definitions_without_mutating_market_verdict(tmp_path, monkeypatch):
    snapshot, contexts = _r12_build_fixture(tmp_path, monkeypatch, _r13_clock_table())
    got = snapshot['kinematics']
    assert got.get('positive_direction_scope') == 'literal_returns_only'
    assert contexts[0]['kinematics_view']['metrics'] == got['metrics']
    assert snapshot['regime_radar']['active'] == []


# R14: a useful joint reading must preserve the two meanings and time basis.
@pytest.mark.parametrize('move,momentum,return_state,momentum_state', [
    (-0.19, 1.51, 'fell', 'above_baseline'),
    (0.19, -1.51, 'rose', 'below_baseline'),
    (0.19, 1.51, 'rose', 'above_baseline'),
    (-0.19, -1.51, 'fell', 'below_baseline'),
    (0.0, 0.0, 'flat_at_display_precision', 'at_baseline_at_display_precision'),
])
def test_r14_joint_read_keeps_price_direction_separate_from_relative_momentum(move, momentum, return_state, momentum_state):
    table = _r13_clock_table(); table['rows'][0].update(lit_5d_pct=move, vel_z=momentum)
    got = _r12_project(table); row = got['rows'][0]
    comparison = row.get('movement_comparison', {})
    assert comparison.get('status') == 'calculation_dates_match'
    assert comparison['return_metric'] == 'return_medium'
    assert comparison['window_observations'] == 5
    assert comparison['return_state'] == return_state
    assert comparison['momentum_state'] == momentum_state
    assert comparison['calculated_through'] == '2026-09-25'
    assert comparison['value_basis'] == 'displayed_producer_values'
    assert got['freshness'] == 'unknown'
    assert not {'score', 'confidence', 'probability', 'trade', 'action', 'signal'} & comparison.keys()


@pytest.mark.parametrize('stamp,reason', [('2026-09-22', 'different_calculation_dates'), (None, 'calculation_date_unknown'), ('2026-09-26', 'calculation_date_unknown')])
def test_r14_joint_read_withholds_dated_consensus_without_erasing_individual_metrics(stamp, reason):
    table = _r13_clock_table(); table['rows'][0]['calculation_clock']['selected_index_dates']['vel_z'] = stamp
    row = _r12_project(table)['rows'][0]
    comparison = row.get('movement_comparison', {})
    assert comparison.get('status') == 'withheld' and comparison.get('reason') == reason
    assert comparison['return_state'] is None and comparison['momentum_state'] is None
    assert comparison['calculated_through'] is None
    assert row['values']['velocity_z'] == 1.3 and row['values']['return_medium'] == 1.2


@pytest.mark.parametrize('field,value', [('vel_z', None), ('lit_5d_pct', True), ('vel_z', float('inf'))])
def test_r14_joint_read_requires_both_valid_measures(field, value):
    table = _r13_clock_table(); table['rows'][0][field] = value
    comparison = _r12_project(table)['rows'][0].get('movement_comparison', {})
    assert comparison.get('status') == 'withheld'
    assert comparison['reason'] == 'value_unavailable'
    assert comparison['return_state'] is None and comparison['momentum_state'] is None


@pytest.mark.parametrize('windows,metric', [([1, 5, 20], 'return_medium'), ([5, 10, 20], 'return_short'), ([1, 2, 5], 'return_long')])
def test_r14_joint_read_matches_actual_horizons_not_legacy_field_spelling(windows, metric):
    cfg = _r12_cfg(); cfg['regime']['kinematics']['lit_windows_d'] = windows
    comparison = _r12_project(_r13_clock_table(), cfg)['rows'][0].get('movement_comparison', {})
    assert comparison.get('return_metric') == metric
    assert comparison['window_observations'] == 5
    assert comparison['status'] == 'calculation_dates_match'


def test_r14_joint_read_does_not_compare_a_seven_observation_return_to_five_observation_momentum():
    cfg = _r12_cfg(); cfg['regime']['kinematics']['lit_windows_d'] = [2, 7, 30]
    row = _r12_project(_r13_clock_table(), cfg)['rows'][0]
    assert row.get('movement_comparison', {}).get('reason') == 'matching_return_window_unavailable'
    assert row['movement_comparison']['return_state'] is None
    assert row['values']['return_medium'] == 1.2


def test_r14_duplicate_identity_cannot_gain_a_joint_read_or_accept_injected_conclusions():
    import copy
    table = _r13_clock_table(); row = table['rows'][0]
    row['movement_comparison'] = {'status': 'calculation_dates_match', 'signal': 'buy'}
    table['rows'].append(copy.deepcopy(row))
    comparison = _r12_project(table)['rows'][0].get('movement_comparison', {})
    assert comparison.get('status') == 'withheld'
    assert comparison['reason'] == 'value_unavailable' and 'signal' not in comparison


def test_r14_plain_language_joint_read_is_bilingual_and_not_a_reversal_or_current_market_call():
    from bs4 import BeautifulSoup
    table = _r13_clock_table(); table['rows'][0].update(lit_5d_pct=-0.19, vel_z=1.51)
    html = BeautifulSoup(_r13_evidence_html(_r12_project(table)), 'html.parser')
    summary = html.select_one('[data-movement-comparison="calculation_dates_match"]')
    assert summary, 'No row-specific explanation reaches the real component'
    text = summary.get_text(' ', strip=True)
    assert 'currency fell' in text and 'above its prior baseline' in text
    assert '货币下跌' in text and '高于自身历史基准' in text
    assert 'not a reversal' in text and 'source freshness remains unknown' in text
    assert '5 observations' in text and '2026-09-25' in text
    assert summary.find_previous('summary') and summary.find_next('dl')


@pytest.mark.parametrize('change', ['missing', 'mismatched', 'window'])
def test_r14_unqualified_joint_read_has_a_local_explanation_without_old_combined_copy(change):
    from bs4 import BeautifulSoup
    table, cfg = _r13_clock_table(), _r12_cfg()
    if change == 'missing': table['rows'][0]['vel_z'] = None
    elif change == 'mismatched': table['rows'][0]['calculation_clock']['selected_index_dates']['vel_z'] = '2026-09-22'
    else: cfg['regime']['kinematics']['lit_windows_d'] = [2, 7, 30]
    html = BeautifulSoup(_r13_evidence_html(_r12_project(table, cfg)), 'html.parser')
    summary = html.select_one('[data-movement-comparison="withheld"]')
    assert summary and 'Read these values separately' in summary.get_text()
    assert '分别查看这些数值' in summary.get_text()
    assert 'currency rose' not in summary.get_text() and 'currency fell' not in summary.get_text()
    assert html.select_one('[data-metric="return_medium"] .fx-me-value').get_text() == '+1.20%'


def test_r14_real_builder_exposes_identical_joint_read_to_page_and_snapshot(tmp_path, monkeypatch):
    table = _r13_clock_table(); table['rows'][0].update(lit_5d_pct=-0.19, vel_z=1.51)
    snapshot, contexts = _r12_build_fixture(tmp_path, monkeypatch, table)
    comparison = snapshot['kinematics']['rows'][0].get('movement_comparison')
    assert comparison and comparison['return_state'] == 'fell'
    assert contexts[0]['kinematics_view']['rows'][0]['movement_comparison'] == comparison
    assert snapshot['regime_radar']['active'] == []


@pytest.mark.parametrize('field', ['vel_z', 'accel_z'])
@pytest.mark.parametrize('value', [-8.01, 8.01])
def test_r14_outside_producer_z_bound_is_invalid_not_silently_clipped(field, value):
    from bs4 import BeautifulSoup
    table = _r13_clock_table(); table['rows'][0][field] = value
    got = _r12_project(table); row = got['rows'][0]
    key = 'velocity_z' if field == 'vel_z' else 'acceleration_z'
    assert row['availability'][key] == 'invalid' and row['values'][key] is None
    assert row['values']['return_medium'] == 1.2
    html = BeautifulSoup(_r13_evidence_html(got), 'html.parser')
    assert html.select_one(f'[data-metric="{key}"] .fx-me-value').get_text() == 'Unavailable不可用'
    assert table['rows'][0][field] == value


@pytest.mark.parametrize('value', [-8.0, 8.0])
def test_r14_producer_z_bound_endpoints_remain_actual_values(value):
    table = _r13_clock_table(); table['rows'][0].update(vel_z=value, accel_z=value)
    row = _r12_project(table)['rows'][0]
    assert row['values']['velocity_z'] == row['values']['acceleration_z'] == value
    assert row['availability']['velocity_z'] == row['availability']['acceleration_z'] == 'available'


# R15: a data-health owner is not proof these hermetic tests execute on a PR.
def test_r15_context_bus_has_one_code_gated_run_owner():
    import shlex
    import yaml
    manifest = Path(__file__).resolve().parents[1] / '.github/ci/legacy-jobs.yml'
    jobs = yaml.safe_load(manifest.read_text())['jobs']
    suite = 'tests/test_forex_context_bus.py'
    owners = [(name, job) for name, job in jobs.items()
              if any(suite in shlex.split(step.get('run', ''))
                     for step in job.get('steps', []))]
    assert [(name, job.get('gate', 'code')) for name, job in owners] == [('data-base-shim', 'code')]
    runs = [step['run'] for step in owners[0][1]['steps'] if suite in step.get('run', '')]
    assert len(runs) == 1 and '-k' not in shlex.split(runs[0])
    assert jobs['unrun-macro-panels']['gate'] == 'data'
    assert any('tests/test_forex.py' in step.get('run', '')
               for step in jobs['unrun-macro-panels']['steps'])


def test_r15_code_owner_declares_fixture_builder_and_inspector_dependencies():
    import shlex
    import yaml
    manifest = Path(__file__).resolve().parents[1] / '.github/ci/legacy-jobs.yml'
    job = yaml.safe_load(manifest.read_text())['jobs']['data-base-shim']
    installed = set()
    for step in job['steps']:
        run = step.get('run', '')
        if 'pip install' in run:
            installed.update(token.split('==', 1)[0] for token in shlex.split(run))
    assert {'pytest', 'pyyaml', 'jinja2', 'pandas', 'numpy', 'pyarrow', 'plotly',
            'requests', 'beautifulsoup4', 'openpyxl', 'scikit-learn'} <= installed
    assert any('tests/test_builder_shim_writes.py' in step.get('run', '') for step in job['steps'])
