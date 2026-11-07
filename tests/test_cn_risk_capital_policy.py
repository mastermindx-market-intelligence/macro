"""Tests for the frozen China Risk Radar capital-policy research harness.

Synthetic, network-free, and forbidden from mutating data/ or live policy code.
"""
from __future__ import annotations

import inspect
import math

import numpy as np
import pandas as pd
import pytest

from scripts.research import cn_risk_capital_policy as cp


def _idx(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2020-01-02", periods=n)


def _states() -> pd.Series:
    return pd.Series(
        ["calm", "watch", "caution", "elevated", "risk-off"],
        index=_idx(5),
        dtype="object",
    )


def test_frozen_policy_mappings_are_exact():
    prereg = cp.load_preregistration()
    states = _states()
    returns = pd.Series(0.0, index=states.index)

    current = cp.target_gross("current_ladder", states, returns, prereg)
    assert current.tolist() == [1.0, 0.97, 0.90, 0.78, 0.62]

    binary = cp.target_gross("binary_loud_075", states, returns, prereg)
    assert binary.tolist() == [1.0, 1.0, 1.0, 0.75, 0.75]

    floor_075 = cp.target_gross("current_riskoff_075", states, returns, prereg)
    assert floor_075.tolist() == [1.0, 0.97, 0.90, 0.78, 0.75]

    constant = cp.target_gross("constant_075", states, returns, prereg)
    assert constant.tolist() == [0.75] * 5


def test_exposure_matched_constant_has_one_post_lag_definition():
    prereg = cp.load_preregistration()
    states = _states()
    returns = pd.Series([0.5, -0.4, 0.3, -0.2, 0.1], index=states.index)
    current_target = cp.target_gross("current_ladder", states, returns, prereg)
    current_frame = cp.execute_policy(returns, current_target, lag=1, cost_bps=10)

    matched = cp.matched_constant_target(current_frame, states.index)
    expected = float(current_frame["executed_gross"].mean())
    assert matched.tolist() == pytest.approx([expected] * len(states))
    with pytest.raises(KeyError, match="constructed from executed current-ladder gross"):
        cp.target_gross("matched_constant", states, returns, prereg)


def test_lag_and_turnover_cost_semantics():
    idx = _idx(4)
    returns = pd.Series([0.00, -0.10, 0.05, 0.04], index=idx)
    target = pd.Series([1.00, 0.50, 0.50, 0.75], index=idx)
    frame = cp.execute_policy(returns, target, lag=1, cost_bps=100)

    assert frame.index.tolist() == idx[1:].tolist()
    assert frame["executed_gross"].tolist() == [1.00, 0.50, 0.50]
    assert frame["turnover"].tolist() == [0.00, 0.50, 0.00]
    assert frame["transaction_cost"].tolist() == [0.00, 0.005, 0.00]
    assert frame["policy_return"].tolist() == pytest.approx([-0.10, 0.02, 0.02])
    assert frame["excess_vs_full"].tolist() == pytest.approx([0.00, -0.03, -0.02])


def test_vol_target_is_causal_clipped_and_initialized_at_one():
    prereg = cp.load_preregistration()
    idx = _idx(30)
    quiet = pd.Series([0.001] * 20 + [0.08, -0.08] * 5, index=idx)
    states = pd.Series("calm", index=idx)
    gross = cp.target_gross("vol_target_15", states, quiet, prereg)

    assert gross.iloc[:20].eq(1.0).all()
    assert gross.between(0.5, 1.0).all()
    assert gross.iloc[-1] < 1.0


def test_performance_metrics_cover_protection_and_cost():
    idx = _idx(4)
    returns = pd.Series([0.10, -0.10, 0.05, -0.20], index=idx)
    gross = pd.Series([1.0, 1.0, 0.5, 0.5], index=idx)
    frame = cp.execute_policy(returns, gross, lag=0, cost_bps=0)
    metrics = cp.performance_metrics(frame)

    assert metrics["total_return"] == pytest.approx((1.10 * 0.90 * 1.025 * 0.90) - 1.0)
    assert metrics["max_drawdown"] == pytest.approx(-0.16975)
    assert metrics["cvar_95"] == pytest.approx(-0.10)
    assert metrics["average_gross"] == pytest.approx(0.75)
    assert metrics["time_reduced"] == pytest.approx(0.50)
    assert metrics["missed_upside"] == pytest.approx(0.025)
    assert metrics["avoided_downside"] == pytest.approx(0.10)
    assert metrics["certainty_equivalent"] < metrics["annualized_mean_return"]


def test_loud_episode_rule_merges_ten_day_gap_and_filters_singletons():
    idx = _idx(60)
    states = pd.Series("calm", index=idx, dtype="object")
    states.iloc[[1, 2, 3]] = ["elevated", "risk-off", "elevated"]
    states.iloc[[14, 15, 16]] = ["risk-off", "risk-off", "elevated"]
    states.iloc[30] = "risk-off"
    states.iloc[[50, 51, 52]] = ["elevated", "elevated", "elevated"]

    episodes = cp.find_loud_episodes(states, max_non_loud_gap=10, min_loud_observations=3, post_window_sessions=21)
    assert len(episodes) == 2
    assert episodes[0]["start"] == idx[1]
    assert episodes[0]["end"] == idx[16]
    assert episodes[0]["loud_observations"] == 6
    assert episodes[0]["contains_risk_off"] is True
    assert episodes[0]["outcome_complete"] is True
    assert episodes[1]["start"] == idx[50]
    assert episodes[1]["contains_risk_off"] is False
    assert episodes[1]["outcome_complete"] is False


def test_episode_analysis_marks_downside_and_rebound_capture():
    idx = _idx(35)
    states = pd.Series("calm", index=idx, dtype="object")
    states.iloc[2:5] = "risk-off"
    returns = pd.Series(0.0, index=idx)
    returns.iloc[3] = -0.06
    returns.iloc[6:8] = 0.02
    target = pd.Series(1.0, index=idx)
    target.iloc[2:9] = 0.5
    frame = cp.execute_policy(returns, target, lag=0, cost_bps=0)
    episodes = cp.find_loud_episodes(states, max_non_loud_gap=10, min_loud_observations=3, post_window_sessions=21)
    result = cp.analyze_episodes(frame, states, episodes)

    assert len(result) == 1
    assert result[0]["downside_event"] is True
    assert result[0]["contains_risk_off"] is True
    assert result[0]["policy_excess"] > 0
    assert result[0]["recovery_capture"] < 1.0


def test_circular_block_bootstrap_is_deterministic():
    idx = _idx(80)
    benchmark = pd.Series(np.sin(np.arange(80)) / 100.0, index=idx)
    target_a = pd.Series(0.8, index=idx)
    target_b = pd.Series(1.0, index=idx)
    a = cp.execute_policy(benchmark, target_a, lag=0, cost_bps=0)
    b = cp.execute_policy(benchmark, target_b, lag=0, cost_bps=0)

    first = cp.bootstrap_pair(a, b, draws=100, block_sessions=7, seed=42, ci=0.90)
    second = cp.bootstrap_pair(a, b, draws=100, block_sessions=7, seed=42, ci=0.90)
    assert first == second
    assert set(first) >= {"cagr_diff", "max_drawdown_diff", "cvar_95_diff", "calmar_diff", "certainty_equivalent_diff"}
    assert all(len(value) == 3 for value in first.values())


def _base_adjudication_summary() -> dict:
    strong_current = {
        "cagr": 0.09, "max_drawdown": -0.27, "cvar_95": -0.018,
        "calmar": 0.34, "certainty_equivalent": 0.08,
    }
    full = {
        "cagr": 0.10, "max_drawdown": -0.35, "cvar_95": -0.021,
        "calmar": 0.28, "certainty_equivalent": 0.06,
    }
    matched = {
        "cagr": 0.075, "max_drawdown": -0.30, "cvar_95": -0.019,
        "calmar": 0.25, "certainty_equivalent": 0.055,
    }
    floor = {
        "cagr": 0.092, "max_drawdown": -0.285, "cvar_95": -0.0185,
        "calmar": 0.32, "certainty_equivalent": 0.075,
    }
    return {
        "historical_authority_eligible": True,
        "authority_effective_episode_n": 45,
        "authority_riskoff_episode_n": 20,
        "authority_elevated_only_episode_n": 25,
        "primary": {
            "current_ladder": strong_current,
            "constant_100": full,
            "matched_constant": matched,
            "binary_loud_075": strong_current,
            "current_riskoff_075": floor,
        },
        "bootstrap": {
            "current_vs_matched": {"certainty_equivalent_diff": [0.005, 0.02, 0.04]},
            "binary_vs_matched": {"certainty_equivalent_diff": [0.005, 0.02, 0.04]},
        },
        "positive_episode_fraction": {"current_ladder": 0.70, "binary_loud_075": 0.65},
        "crisis_concentration": {"current_ladder": 0.40, "binary_loud_075": 0.45},
        "sensitivity_pass": {"current_ladder": True, "binary_loud_075": True},
        "era_pass": {"current_ladder": True, "binary_loud_075": True},
        "loco_positive_count": {"current_ladder": 9, "binary_loud_075": 9},
    }


def test_adjudication_exact_current_ladder_pass():
    prereg = cp.load_preregistration()
    summary = _base_adjudication_summary()
    verdict, reasons = cp.adjudicate(summary, prereg)
    assert verdict == "CURRENT_LADDER_VALIDATED_FOR_ADVISORY_REFERENCE"
    assert reasons["exact_current_pass"] is True


def test_adjudication_prefers_supported_simple_policy_when_exact_n_fails():
    prereg = cp.load_preregistration()
    summary = _base_adjudication_summary()
    summary["authority_effective_episode_n"] = 30
    summary["authority_elevated_only_episode_n"] = 8
    verdict, reasons = cp.adjudicate(summary, prereg)
    assert verdict == "SIMPLER_POLICY_SUPPORTED"
    assert reasons["exact_current_pass"] is False
    assert reasons["simple_binary_pass"] is True


def test_adjudication_insufficient_independent_episodes():
    prereg = cp.load_preregistration()
    summary = _base_adjudication_summary()
    summary["authority_effective_episode_n"] = 12
    summary["authority_riskoff_episode_n"] = 5
    verdict, _ = cp.adjudicate(summary, prereg)
    assert verdict == "INSUFFICIENT_INDEPENDENT_EPISODES"


def test_adjudication_no_sizing_edge_when_matched_constant_dominates():
    prereg = cp.load_preregistration()
    summary = _base_adjudication_summary()
    summary["authority_effective_episode_n"] = 25
    summary["authority_elevated_only_episode_n"] = 5
    summary["primary"]["matched_constant"]["calmar"] = 0.50
    summary["primary"]["matched_constant"]["cvar_95"] = -0.010
    summary["bootstrap"]["binary_vs_matched"]["certainty_equivalent_diff"] = [-0.05, -0.03, -0.01]
    verdict, _ = cp.adjudicate(summary, prereg)
    assert verdict == "NO_SIZING_EDGE / DISPLAY_CONTEXT_ONLY"


def test_ui_language_never_calls_mapping_suggested_size():
    exact = cp.ui_language_verdict("CURRENT_LADDER_VALIDATED_FOR_ADVISORY_REFERENCE")
    assert exact["may_say_suggested_size"] is False
    assert exact["may_say_risk_budget_reference"] is True
    assert exact["may_show_x062_as_advice"] is True
    assert exact["should_round_plain_english_fraction"] is False

    held = cp.ui_language_verdict("HAZARD_VALID_BUT_EXACT_GROSS_UNVALIDATED")
    assert held["may_say_suggested_size"] is False
    assert held["may_say_risk_budget_reference"] is False
    assert held["may_show_x062_as_advice"] is False
    assert held["authority_level"] == "DISPLAY_CONTEXT_ONLY"


def test_live_mapping_assertion_reads_exact_source_constant():
    prereg = cp.load_preregistration()
    assert cp.assert_live_mapping_matches_prereg(prereg) == prereg["current_mapping"]


def test_sha256_fingerprint_is_order_and_value_sensitive(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("alpha\n")
    b.write_text("alpha\n")
    assert cp.sha256_file(a) == cp.sha256_file(b)
    b.write_text("beta\n")
    assert cp.sha256_file(a) != cp.sha256_file(b)


def test_crisis_recovery_loco_and_concentration_are_explicit():
    idx = _idx(12)
    returns = pd.Series(0.0, index=idx)
    returns.iloc[1:3] = -0.10
    returns.iloc[4:6] = 0.05
    gross = pd.Series(1.0, index=idx)
    gross.iloc[1:6] = 0.50
    frame = cp.execute_policy(returns, gross, lag=0, cost_bps=0)
    crises = {"synthetic": [idx[1].date().isoformat(), idx[2].date().isoformat()]}

    rows = cp.analyze_crises(frame, crises, recovery_sessions=3)
    assert len(rows) == 1
    assert rows[0]["protection_vs_full"] > 0
    assert 0 < rows[0]["recovery_capture"] < 1
    assert rows[0]["recovery_average_gross"] == pytest.approx(0.5)

    loco = cp.leave_one_crisis_out(frame, crises)
    assert len(loco) == 1
    assert loco[0]["excluded_crisis"] == "synthetic"
    assert loco[0]["n_sessions"] == 10

    concentration = cp.crisis_concentration([
        {"protection_vs_full": 1.0},
        {"protection_vs_full": 2.0},
        {"protection_vs_full": 1.0},
        {"protection_vs_full": -4.0},
    ])
    assert concentration == pytest.approx(0.5)


def test_forward_evidence_sentence_discloses_open_episode():
    forward = {
        "rows": 34,
        "matured_rows": 16,
        "matured_loud_rows": 5,
        "matured_state_counts": {"caution": 9, "elevated": 1, "risk-off": 4, "watch": 2},
        "independent_loud_episode_n": 1,
        "open_loud_episode_n": 1,
    }

    sentence = cp._forward_evidence_sentence(forward)

    assert "1 open loud episode remains ungraded" in sentence
    assert "only **1** completed independent episode" in sentence


def test_run_study_artifact_flag_cannot_shadow_writer():
    parameters = inspect.signature(cp.run_study).parameters
    assert "emit_artifacts" in parameters
    assert "write_artifacts" not in parameters
    assert callable(cp.write_artifacts)


def test_overlapping_outcome_windows_are_not_independent_authority_n():
    idx = _idx(70)
    states = pd.Series("calm", index=idx, dtype="object")
    states.iloc[1:4] = "risk-off"
    states.iloc[20:23] = "elevated"

    episodes = cp.find_loud_episodes(
        states,
        max_non_loud_gap=10,
        min_loud_observations=3,
        post_window_sessions=21,
    )
    assert len(episodes) == 2
    assert episodes[0]["outcome_complete"] is True
    assert episodes[0]["overlaps_next_episode"] is True
    assert episodes[0]["authority_independent"] is False
    assert episodes[1]["outcome_complete"] is True
    assert episodes[1]["overlaps_next_episode"] is False
    assert episodes[1]["authority_independent"] is True
    assert [episode["episode_id"] for episode in cp.authority_independent_episodes(episodes)] == [2]


def test_adjudication_fails_closed_when_history_is_not_authority_grade_pit():
    prereg = cp.load_preregistration()
    summary = _base_adjudication_summary()
    summary["historical_authority_eligible"] = False
    summary["authority_effective_episode_n"] = 1
    summary["authority_riskoff_episode_n"] = 1
    summary["authority_elevated_only_episode_n"] = 0

    verdict, reasons = cp.adjudicate(summary, prereg)
    assert verdict == "INSUFFICIENT_INDEPENDENT_EPISODES"
    assert reasons["exact_checks"]["historical_authority_eligible"] is False
    assert reasons["simple_checks"]["historical_authority_eligible"] is False


def test_historical_source_qualification_rejects_current_membership_backfill():
    qualification = cp.historical_source_qualification()
    assert qualification["construction_is_causal"] is True
    assert qualification["exact_state_uses_cn_breadth"] is True
    assert qualification["breadth_current_membership_backfill"] is True
    assert qualification["date_effective_membership_present"] is False
    assert qualification["source_vintage_metadata_present"] is False
    assert qualification["historical_authority_eligible"] is False
    assert qualification["classification"] == "CAUSAL_DEFINITION_CURRENT_NOT_AUTHORITY_GRADE_PIT"


def test_forward_episode_spacing_uses_market_sessions_not_graded_row_adjacency():
    sessions = pd.bdate_range("2026-01-02", "2026-02-06")
    rows = [
        {"asof": "2026-01-05", "state": "risk-off", "graded": {"fwd_dd": {"h21": -0.06}}},
        {"asof": "2026-01-06", "state": "risk-off", "graded": {"fwd_dd": {"h21": -0.05}}},
        {"asof": "2026-01-07", "state": "risk-off", "graded": {"fwd_dd": {"h21": -0.04}}},
        {"asof": "2026-02-02", "state": "elevated", "graded": {"fwd_dd": {"h21": -0.03}}},
        {"asof": "2026-02-03", "state": "elevated", "graded": {"fwd_dd": {"h21": -0.02}}},
        {"asof": "2026-02-04", "state": "elevated", "graded": {"fwd_dd": {"h21": -0.01}}},
    ]

    episodes = cp._forward_loud_episodes(
        rows,
        session_index=sessions,
        max_non_loud_gap=10,
        min_loud_observations=3,
    )

    assert len(episodes) == 2
    assert episodes[0]["start"] == "2026-01-05"
    assert episodes[0]["end"] == "2026-01-07"
    assert episodes[1]["start"] == "2026-02-02"
    assert episodes[1]["end"] == "2026-02-04"


def test_forward_ledger_withholds_open_episode_extended_by_unmatured_loud_row(tmp_path):
    sessions = pd.bdate_range("2026-01-02", "2026-02-20")
    rows = [
        {"asof": "2026-01-05", "state": "risk-off", "graded": {"fwd_dd": {"h21": -0.06}}},
        {"asof": "2026-01-06", "state": "risk-off", "graded": {"fwd_dd": {"h21": -0.05}}},
        {"asof": "2026-01-07", "state": "risk-off", "graded": {"fwd_dd": {"h21": -0.04}}},
        {"asof": "2026-01-12", "state": "elevated", "graded": None},
    ]
    path = tmp_path / "forward.jsonl"
    path.write_text("\n".join(__import__("json").dumps(row) for row in rows) + "\n")

    inventory = cp.forward_ledger_inventory(path, session_index=sessions)

    assert inventory["independent_loud_episode_n"] == 0
    assert inventory["open_loud_episode_n"] == 1
    assert inventory["all_episodes"][0]["outcome_complete"] is False


def test_forward_ledger_counts_independent_matured_loud_episode(tmp_path):
    sessions = pd.bdate_range("2026-01-02", "2026-02-20")
    rows = [
        {"asof": "2026-01-02", "state": "caution", "graded": {"outcome": "watch", "fwd_dd": {"h21": -0.01}}},
        {"asof": "2026-01-05", "state": "elevated", "graded": {"outcome": "hit", "fwd_dd": {"h21": -0.06}}},
        {"asof": "2026-01-06", "state": "risk-off", "graded": {"outcome": "hit", "fwd_dd": {"h21": -0.05}}},
        {"asof": "2026-01-07", "state": "risk-off", "graded": {"outcome": "miss", "fwd_dd": {"h21": -0.04}}},
        {"asof": "2026-01-08", "state": "watch", "graded": {"outcome": "watch", "fwd_dd": {"h21": -0.01}}},
        {"asof": "2026-02-02", "state": "risk-off", "graded": None},
    ]
    path = tmp_path / "forward.jsonl"
    path.write_text("\n".join(__import__("json").dumps(row) for row in rows) + "\n")

    inventory = cp.forward_ledger_inventory(path, session_index=sessions)
    assert inventory["matured_rows"] == 5
    assert inventory["matured_loud_rows"] == 3
    assert inventory["independent_loud_episode_n"] == 1
    assert inventory["riskoff_containing_episode_n"] == 1
    assert inventory["elevated_only_episode_n"] == 0
    assert inventory["historical_coefficients_estimable"] is False


def test_live_mapping_mismatch_fails_closed(monkeypatch):
    from engine import risk_radar_intl as radar

    prereg = cp.load_preregistration()
    monkeypatch.setitem(radar._GROSS, "risk-off", 0.61)
    with pytest.raises(RuntimeError, match="differs from frozen preregistration"):
        cp.assert_live_mapping_matches_prereg(prereg)
