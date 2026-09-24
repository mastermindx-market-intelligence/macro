"""Contract tests for the preregistered China Risk Radar revalidation harness."""
from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest


try:
    SUBJECT = importlib.import_module("scripts.research.cn_risk_radar_revalidation")
except ModuleNotFoundError:
    SUBJECT = None


def _fn(name: str):
    assert SUBJECT is not None, "revalidation module does not exist"
    fn = getattr(SUBJECT, name, None)
    assert callable(fn), f"missing callable: {name}"
    return fn


def test_forward_max_drawdown_uses_future_sessions_only_and_excludes_immature_rows():
    idx = pd.bdate_range("2024-01-02", periods=7)
    close = pd.Series([90.0, 100.0, 94.0, 96.0, 92.0, 101.0, 99.0], index=idx)

    result = _fn("forward_max_drawdown")(close, horizon=3)

    # The low current close at t0 must not enter its own future window.
    assert result.loc[idx[0]] == pytest.approx(0.0)
    assert result.loc[idx[1]] == pytest.approx(-0.08)
    assert result.loc[idx[2]] == pytest.approx((92.0 / 94.0) - 1.0)
    assert result.iloc[-3:].isna().all()


def test_binary_outcome_uses_inclusive_threshold_and_preserves_immaturity():
    idx = pd.bdate_range("2024-01-02", periods=5)
    drawdown = pd.Series([-0.0499, -0.05, -0.10, np.nan, 0.0], index=idx)

    result = _fn("binary_outcome")(drawdown, threshold=0.05)

    assert result.iloc[0] == 0
    assert result.iloc[1] == 1
    assert result.iloc[2] == 1
    assert pd.isna(result.iloc[3])
    assert result.iloc[4] == 0


def test_reconstruct_states_applies_exact_bands_and_context_cap():
    idx = pd.bdate_range("2024-01-02", periods=6)
    composite = pd.Series([0.57, 0.5801, 0.7201, 0.84, 0.92, 0.92], index=idx)
    gate = pd.Series([True, True, True, False, False, True], index=idx)

    result = _fn("reconstruct_states")(
        composite,
        gate,
        bands={"watch": 58.0, "caution": 72.0, "elevated": 83.0, "risk_off": 91.0},
    )

    assert result["state_ungated"].tolist() == [
        "calm", "watch", "caution", "elevated", "risk-off", "risk-off"
    ]
    assert result["state"].tolist() == [
        "calm", "watch", "caution", "caution", "caution", "risk-off"
    ]
    assert result["score"].tolist() == pytest.approx([57.0, 58.01, 72.01, 84.0, 92.0, 92.0])


def test_episode_ids_use_benchmark_session_distance_not_calendar_days():
    idx = pd.bdate_range("2024-01-02", periods=60)
    qualifying = pd.Series(False, index=idx)
    qualifying.iloc[[0, 1, 3, 46, 47]] = True

    ids = _fn("episode_ids")(qualifying, max_gap_sessions=42)

    assert ids.dropna().astype(int).tolist() == [0, 0, 0, 1, 1]
    assert ids.loc[~qualifying].isna().all()


def test_episode_summary_reports_rows_episodes_hits_and_effective_ceiling():
    idx = pd.bdate_range("2024-01-02", periods=100)
    condition = pd.Series(False, index=idx)
    condition.iloc[[0, 1, 2, 50, 51, 99]] = True
    outcome = pd.Series(0.0, index=idx)
    outcome.iloc[[1, 50]] = 1.0

    result = _fn("episode_summary") (
        condition=condition,
        outcome=outcome,
        horizon=21,
        episode_gap=42,
    )

    assert result == {
        "rows": 6,
        "episodes": 3,
        "hit_episodes": 2,
        "nonhit_episodes": 1,
        "nonoverlap_ceiling": 4,
        "effective_n_ceiling": 3,
    }


def test_core_discrimination_and_brier_metrics_have_known_values():
    idx = pd.bdate_range("2024-01-02", periods=4)
    outcome = pd.Series([0.0, 1.0, 0.0, 1.0], index=idx)
    probability = pd.Series([0.1, 0.9, 0.2, 0.8], index=idx)
    score = probability.copy()

    assert _fn("brier_score")(probability, outcome) == pytest.approx(0.025)
    assert _fn("brier_skill")(probability, outcome, baseline_probability=0.5) == pytest.approx(0.9)
    assert _fn("roc_auc")(score, outcome) == pytest.approx(1.0)
    assert _fn("average_precision")(score, outcome) == pytest.approx(1.0)


def test_lift_summary_uses_conditional_rate_over_full_base_rate():
    idx = pd.bdate_range("2024-01-02", periods=4)
    outcome = pd.Series([0.0, 1.0, 1.0, 1.0], index=idx)
    condition = pd.Series([False, True, False, True], index=idx)

    result = _fn("lift_summary")(condition, outcome)

    assert result["rows"] == 2
    assert result["hits"] == 2
    assert result["conditional_rate"] == pytest.approx(1.0)
    assert result["base_rate"] == pytest.approx(0.75)
    assert result["lift"] == pytest.approx(4.0 / 3.0)


def test_circular_moving_block_indices_are_seeded_and_locally_contiguous():
    sampler = _fn("circular_moving_block_indices")
    first = sampler(n=17, block_length=5, seed=7)
    second = sampler(n=17, block_length=5, seed=7)

    assert np.array_equal(first, second)
    assert len(first) == 17
    assert np.all((first[:4] + 1) % 17 == first[1:5])
    assert np.all((first[5:9] + 1) % 17 == first[6:10])


def test_moving_block_bootstrap_constant_statistic_has_degenerate_interval():
    frame = pd.DataFrame({"x": np.arange(30, dtype=float)})
    result = _fn("moving_block_bootstrap")(
        frame,
        statistic=lambda sample: 3.25,
        block_length=7,
        reps=100,
        seed=11,
    )

    assert result["estimate"] == pytest.approx(3.25)
    assert result["ci_low"] == pytest.approx(3.25)
    assert result["ci_high"] == pytest.approx(3.25)
    assert result["valid_reps"] == 100
    assert result["invalid_reps"] == 0


def test_block_permutation_is_reproducible_and_detects_strong_alignment():
    n = 240
    idx = pd.bdate_range("2020-01-02", periods=n)
    condition = pd.Series(False, index=idx)
    outcome = pd.Series(0.0, index=idx)
    for start in (20, 80, 140, 200):
        condition.iloc[start : start + 10] = True
        outcome.iloc[start : start + 10] = 1.0

    fn = _fn("circular_shift_permutation")
    first = fn(condition, outcome, reps=399, min_shift=42, seed=19)
    second = fn(condition, outcome, reps=399, min_shift=42, seed=19)

    assert first == second
    assert first["observed"] == pytest.approx(6.0)
    assert first["p_value"] <= 0.05
    assert first["valid_reps"] == 399


def test_state_calibration_table_preserves_fixed_state_order_and_probabilities():
    states = []
    probabilities = []
    outcomes = []
    for state, probability, hits in (
        ("calm", 0.2, 4),
        ("watch", 0.4, 8),
        ("caution", 0.6, 12),
        ("elevated", 0.7, 14),
        ("risk-off", 0.8, 16),
    ):
        states.extend([state] * 20)
        probabilities.extend([probability] * 20)
        outcomes.extend([1.0] * hits + [0.0] * (20 - hits))
    idx = pd.bdate_range("2020-01-02", periods=len(states))

    table = _fn("state_calibration_table")(
        pd.Series(states, index=idx),
        pd.Series(probabilities, index=idx),
        pd.Series(outcomes, index=idx),
        horizon=21,
        episode_gap=0,
    )

    assert [row["state"] for row in table] == [
        "calm", "watch", "caution", "elevated", "risk-off"
    ]
    assert [row["forecast"] for row in table] == pytest.approx([0.2, 0.4, 0.6, 0.7, 0.8])
    assert [row["observed"] for row in table] == pytest.approx([0.2, 0.4, 0.6, 0.7, 0.8])
    assert all(row["rows"] == 20 for row in table)


def test_detect_probability_inversions_requires_material_negative_step():
    table = [
        {"state": "calm", "observed": 0.20},
        {"state": "watch", "observed": 0.28},
        {"state": "caution", "observed": 0.34},
        {"state": "elevated", "observed": 0.50},
        {"state": "risk-off", "observed": 0.39},
    ]

    result = _fn("detect_probability_inversions")(table, material_delta=0.05)

    assert result == [
        {
            "lower_state": "elevated",
            "higher_state": "risk-off",
            "difference": pytest.approx(-0.11),
            "material": True,
        }
    ]


def test_calibration_intercept_slope_recovers_exact_grouped_calibration():
    probabilities = []
    outcomes = []
    for probability, hits in ((0.2, 20), (0.5, 50), (0.8, 80)):
        probabilities.extend([probability] * 100)
        outcomes.extend([1.0] * hits + [0.0] * (100 - hits))
    idx = pd.bdate_range("2020-01-02", periods=300)

    result = _fn("calibration_intercept_slope")(
        pd.Series(probabilities, index=idx),
        pd.Series(outcomes, index=idx),
    )

    assert result["qualified"] is True
    assert result["intercept"] == pytest.approx(0.0, abs=1e-5)
    assert result["slope"] == pytest.approx(1.0, abs=1e-5)


def test_crisis_exclusion_mask_embargoes_signals_whose_forward_window_intersects_crisis():
    idx = pd.bdate_range("2024-01-02", periods=12)
    mask = _fn("crisis_exclusion_mask")(
        idx,
        crisis_start=pd.Timestamp("2024-01-09"),
        crisis_end=pd.Timestamp("2024-01-11"),
        horizon=3,
    )

    # Jan 4 looks forward to Jan 5/8/9, so it must be excluded; Jan 3 does not intersect.
    assert bool(mask.loc[pd.Timestamp("2024-01-03")]) is True
    assert bool(mask.loc[pd.Timestamp("2024-01-04")]) is False
    assert bool(mask.loc[pd.Timestamp("2024-01-09")]) is False
    assert bool(mask.loc[pd.Timestamp("2024-01-12")]) is True


def test_chronological_split_half_is_deterministic_and_exhaustive():
    idx = pd.bdate_range("2024-01-02", periods=9)
    first, second = _fn("chronological_split_half")(idx)

    assert list(first) == list(idx[:4])
    assert list(second) == list(idx[4:])
    assert set(first).isdisjoint(set(second))


def test_verify_frozen_sources_accepts_exact_hash_and_rejects_drift(tmp_path):
    source = tmp_path / "engine" / "model.py"
    source.parent.mkdir(parents=True)
    source.write_text("frozen\n")
    expected = {"engine/model.py": _fn("sha256_file")(source)}

    manifest = _fn("verify_frozen_sources")(tmp_path, expected)
    assert manifest["engine/model.py"]["sha256"] == expected["engine/model.py"]

    source.write_text("drifted\n")
    with pytest.raises(RuntimeError, match="source hash drift"):
        _fn("verify_frozen_sources")(tmp_path, expected)


def test_verify_no_cn_overlay_rejects_unexpected_probability_override(tmp_path):
    overlay = tmp_path / "data" / "risk_radar_intl" / "cn_calibration.json"
    overlay.parent.mkdir(parents=True)
    overlay.write_text('{"prob_cal": {}}')

    with pytest.raises(RuntimeError, match="CN calibration overlay"):
        _fn("verify_no_cn_overlay")(tmp_path)

    overlay.unlink()
    assert _fn("verify_no_cn_overlay")(tmp_path) is None


def test_dataframe_file_manifest_records_hash_shape_dates_columns_and_role(tmp_path):
    path = tmp_path / "series.parquet"
    idx = pd.bdate_range("2020-01-02", periods=3)
    frame = pd.DataFrame({"close": [100.0, 101.0, 99.0], "volume": [1, 2, 3]}, index=idx)
    frame.to_parquet(path)

    result = _fn("dataframe_file_manifest")(path, role="canonical_benchmark", provider="repo_store")

    assert result["role"] == "canonical_benchmark"
    assert result["provider"] == "repo_store"
    assert result["rows"] == 3
    assert result["first_date"] == "2020-01-02"
    assert result["last_date"] == "2020-01-06"
    assert result["columns"] == ["close", "volume"]
    assert len(result["sha256"]) == 64


def test_delayed_expanding_base_uses_only_fully_matured_prior_outcomes():
    idx = pd.bdate_range("2024-01-02", periods=6)
    outcome = pd.Series([1.0, 0.0, 1.0, 0.0, 1.0, np.nan], index=idx)

    result = _fn("delayed_expanding_base")(outcome, horizon=2, min_history=2)

    assert result.iloc[:3].isna().all()
    assert result.iloc[3] == pytest.approx(0.5)   # y0/y1 only
    assert result.iloc[4] == pytest.approx(0.625) # y0/y1/y2, Jeffreys prior
    assert result.iloc[5] == pytest.approx(0.5)   # y0..y3, Jeffreys prior


def test_build_baseline_scores_uses_fixed_exact_sublegs_and_causal_rate_percentile():
    idx = pd.bdate_range("2024-01-02", periods=8)
    sublegs = {
        "cn_breadth": pd.Series(np.linspace(0.1, 0.8, 8), index=idx),
        "us_rate_2y": pd.Series(np.arange(8, dtype=float), index=idx),
        "us_real_rate": pd.Series(np.arange(8, dtype=float) + 1.0, index=idx),
        "us_rate_10y": pd.Series(np.arange(8, dtype=float) + 2.0, index=idx),
    }
    composite = pd.Series(np.linspace(0.2, 0.9, 8), index=idx)
    gate = pd.Series([False, False, True, True, False, True, True, True], index=idx)

    result = _fn("build_baseline_scores")(
        sublegs=sublegs,
        composite=composite,
        gate=gate,
        percentile_window=4,
    )

    assert result.columns.tolist() == ["breadth_only", "rates_only", "trend_context", "ungated_composite"]
    assert result["breadth_only"].equals(sublegs["cn_breadth"])
    assert result["trend_context"].tolist() == [0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0]
    assert result["ungated_composite"].equals(composite)
    assert result["rates_only"].iloc[-1] == pytest.approx(1.0)
    assert result["rates_only"].isna().sum() == 1


def test_align_replication_outcome_reuses_canonical_signal_columns_unchanged():
    idx = pd.bdate_range("2024-01-02", periods=6)
    signal = pd.DataFrame(
        {
            "score": [60.0, 70.0, 80.0, 90.0, 95.0, 50.0],
            "state": ["watch", "watch", "caution", "risk-off", "risk-off", "calm"],
            "gate": [True, True, True, True, True, False],
        },
        index=idx,
    )
    replication_close = pd.Series([100.0, 99.0, 94.0, 98.0, 97.0, 96.0], index=idx)

    result = _fn("align_replication_outcome")(
        signal,
        replication_close,
        horizon=2,
        threshold=0.05,
        outcome_name="y_5_2",
    )

    assert result.loc[idx[:4], ["score", "state", "gate"]].equals(signal.loc[idx[:4]])
    assert result["y_5_2"].iloc[0] == 1.0
    assert result["y_5_2"].iloc[-2:].isna().all()


def test_fixed_threshold_condition_never_estimates_cut_from_outcomes():
    score = pd.Series([0.82, 0.83, 0.90, 0.91])
    elevated, risk_off = _fn("fixed_threshold_conditions")(score)

    assert elevated.tolist() == [False, True, True, True]
    assert risk_off.tolist() == [False, False, False, True]


def test_probability_adjudication_keeps_well_calibrated_powered_cell():
    result = _fn("adjudicate_probability")(
        forecast=0.50,
        observed=0.48,
        block_ci=(0.34, 0.61),
        episode_ci=(0.32, 0.64),
        brier_skill_value=0.04,
        effective_n=28,
        hit_episodes=13,
        nonhit_episodes=15,
        material_inversion=False,
    )
    assert result["verdict"] == "KEEP"


def test_probability_adjudication_refuses_daily_n_when_episode_n_is_sparse():
    result = _fn("adjudicate_probability")(
        forecast=0.50,
        observed=0.50,
        block_ci=(0.20, 0.80),
        episode_ci=(0.10, 0.90),
        brier_skill_value=0.10,
        effective_n=7,
        hit_episodes=4,
        nonhit_episodes=3,
        material_inversion=False,
    )
    assert result["verdict"] == "INSUFFICIENT_EVIDENCE"


def test_probability_adjudication_marks_material_error_for_recalibration_or_removal():
    candidate = _fn("adjudicate_probability")(
        forecast=0.50,
        observed=0.34,
        block_ci=(0.25, 0.42),
        episode_ci=(0.22, 0.44),
        brier_skill_value=-0.01,
        effective_n=30,
        hit_episodes=10,
        nonhit_episodes=20,
        material_inversion=False,
    )
    removal = _fn("adjudicate_probability")(
        forecast=0.50,
        observed=0.20,
        block_ci=(0.12, 0.28),
        episode_ci=(0.10, 0.30),
        brier_skill_value=-0.08,
        effective_n=30,
        hit_episodes=6,
        nonhit_episodes=24,
        material_inversion=True,
    )
    assert candidate["verdict"] == "RECALIBRATION_CANDIDATE"
    assert removal["verdict"] == "FAIL / REMOVE"


def test_historical_lift_adjudication_applies_preregistered_robustness_and_tolerance():
    robust = _fn("adjudicate_historical_lift")(
        lift=2.05,
        ci=(1.25, 2.90),
        split_lifts=(1.70, 2.20),
        modern_lift=1.80,
        loco_lifts=(1.30, 1.45, 1.60),
        permutation_p=0.01,
        effective_n=24,
    )
    directional = _fn("adjudicate_historical_lift")(
        lift=2.00,
        ci=(0.82, 3.10),
        split_lifts=(1.40, 1.30),
        modern_lift=1.20,
        loco_lifts=(0.95, 1.30, 1.10),
        permutation_p=0.08,
        effective_n=18,
    )
    failed = _fn("adjudicate_historical_lift")(
        lift=0.90,
        ci=(0.60, 1.20),
        split_lifts=(0.85, 0.95),
        modern_lift=0.80,
        loco_lifts=(0.75, 0.88),
        permutation_p=0.70,
        effective_n=25,
    )

    assert robust["verdict"] == "KEEP"
    assert directional["verdict"] == "KEEP_BUT_RELABEL"
    assert failed["verdict"] == "FAIL / REMOVE"


def test_state_separation_adjudication_requires_episode_power():
    sparse = _fn("adjudicate_state_separation")(
        difference=0.20,
        ci=(-0.10, 0.40),
        elevated_effective_n=20,
        risk_off_effective_n=5,
        material_inversion=False,
    )
    directional = _fn("adjudicate_state_separation")(
        difference=0.08,
        ci=(-0.03, 0.20),
        elevated_effective_n=15,
        risk_off_effective_n=15,
        material_inversion=False,
    )
    robust = _fn("adjudicate_state_separation")(
        difference=0.12,
        ci=(0.00, 0.24),
        elevated_effective_n=16,
        risk_off_effective_n=18,
        material_inversion=False,
    )
    assert sparse["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert directional["verdict"] == "KEEP_BUT_RELABEL"
    assert robust["verdict"] == "KEEP"


def test_write_result_artifacts_is_deterministic_and_contains_all_claims(tmp_path):
    claims = {
        claim: {"verdict": "INSUFFICIENT_EVIDENCE", "basis": "fixture"}
        for claim in _fn("claim_keys")()
    }
    result = {
        "schema": "cn_risk_radar_revalidation.v1",
        "operation_key": "fixture",
        "base_sha": "abc",
        "prereg_sha": "def",
        "claims": claims,
        "targets": {},
        "forward_ledger": {},
        "discoveries": [],
    }

    first = _fn("write_result_artifacts")(result, tmp_path)
    first_json = (tmp_path / "results.json").read_bytes()
    first_report = (tmp_path / "REPORT.md").read_bytes()
    second = _fn("write_result_artifacts")(result, tmp_path)

    assert first == second
    assert first_json == (tmp_path / "results.json").read_bytes()
    assert first_report == (tmp_path / "REPORT.md").read_bytes()
    report = first_report.decode()
    for claim in claims:
        assert claim in report
    assert "generated_at" not in first_json.decode()


def test_check_only_cli_verifies_frozen_contract_without_writing_results(tmp_path, capsys):
    import json
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    rc = _fn("main")(
        [
            "--repo-root", str(repo_root),
            "--output-dir", str(tmp_path),
            "--check-only",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["schema"] == "cn_risk_radar_revalidation.check.v1"
    assert payload["base_sha"] == "8db6896dab2199a4b7fc61a005c225380cac7cd6"
    assert payload["prereg_sha"] == "db5590accaa03f78396ca91b6874f04b9bcf4cf3"
    assert payload["overlay"] == "absent"
    assert not (tmp_path / "results.json").exists()
