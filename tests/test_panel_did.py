"""Focused tests for the research-only common-adoption panel DiD estimator.

Run with ``pytest`` (from the repository root) or any plain test runner; the
file uses only ``assert`` plus stdlib/numpy so it degrades gracefully.

Discriminating checks, per the F10 engineering brief:
* seeded planted effect with unit/time shifts,
* explicit dummy-OLS oracle for the coefficient and residuals and an
  independently coded CR1 cluster sandwich for the covariance,
* known 2-period DiD mean-change equivalence,
* shift / row-order / column-order invariance,
* invalid masks and common-adoption rejections,
* grouped assignment clusters, insufficient clusters, exact fit (no fake
  certainty),
* CLI success/error behaviour and finite JSON output.
"""

from __future__ import annotations

import copy
import json
import math
import os
import subprocess
import sys

import numpy as np

from engine.panel_did import estimate_common_adoption_panel

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _periods(n):
    # strictly increasing ISO dates one day apart
    return ["2026-01-%02d" % (i + 1) for i in range(n)]


def _mask(n_units, n_periods, adoption_index, n_treated):
    d = np.zeros((n_units, n_periods))
    d[:n_treated, adoption_index:] = 1.0
    return d


def _labels(n, prefix):
    return ["%s%03d" % (prefix, i) for i in range(n)]


def _make_study(
    n_units=12,
    n_periods=8,
    adoption_index=4,
    n_treated=6,
    beta=2.5,
    seed=1234,
    noise_sd=0.5,
    unit_sd=1.0,
    time_sd=0.8,
    cluster_groups=None,
):
    rng = np.random.default_rng(seed)
    d = _mask(n_units, n_periods, adoption_index, n_treated)
    y = (
        rng.normal(0.0, unit_sd, size=(n_units, 1))
        + rng.normal(0.0, time_sd, size=(1, n_periods))
        + beta * d
        + rng.normal(0.0, noise_sd, size=(n_units, n_periods))
    )
    if cluster_groups is None:
        cluster_ids = _labels(n_units, "c")
    else:
        cluster_ids = [cluster_groups[i] for i in range(n_units)]
    return {
        "outcomes": y,
        "treatment": d,
        "unit_ids": _labels(n_units, "u"),
        "periods": _periods(n_periods),
        "cluster_ids": cluster_ids,
    }


def _within(y):
    """Reference two-way within transformation (documented in the research note)."""
    return y - y.mean(axis=1, keepdims=True) - y.mean(axis=0, keepdims=True) + y.mean()


def _dummy_ols_oracle(y, d):
    """Explicit OLS with an intercept, unit dummies, time dummies and D."""
    n, t = y.shape
    unit_index = np.repeat(np.arange(n), t)
    time_index = np.tile(np.arange(t), n)
    cols = [np.ones(n * t)]
    for i in range(1, n):
        cols.append((unit_index == i).astype(float))
    for s in range(1, t):
        cols.append((time_index == s).astype(float))
    cols.append(d.ravel())
    x = np.column_stack(cols)
    b, _, _, _ = np.linalg.lstsq(x, y.ravel(), rcond=None)
    resid = y.ravel() - x @ b
    return b, resid, x


def _cr1_oracle(x, resid, cluster_of_row):
    """Independently coded CR1 cluster sandwich (bread/meat form)."""
    n_obs, k = x.shape
    bread = np.linalg.inv(x.T @ x)
    scores = {}
    for r in range(n_obs):
        cid = cluster_of_row[r]
        if cid not in scores:
            scores[cid] = np.zeros(k)
        scores[cid] = scores[cid] + x[r] * resid[r]
    meat = np.zeros((k, k))
    for s in scores.values():
        meat = meat + np.outer(s, s)
    g = len(scores)
    correction = (g / (g - 1.0)) * ((n_obs - 1.0) / (n_obs - k))
    v = correction * (bread @ meat @ bread)
    return v, g


def _all_finite(obj):
    if isinstance(obj, float):
        return math.isfinite(obj)
    if isinstance(obj, dict):
        return all(_all_finite(v) for v in obj.values())
    if isinstance(obj, (list, tuple)):
        return all(_all_finite(v) for v in obj)
    return True


# ---------------------------------------------------------------------------
# estimator correctness
# ---------------------------------------------------------------------------


def test_planted_effect_recovered_with_shifts():
    study = _make_study(beta=2.5, noise_sd=0.5, seed=1234)
    res = estimate_common_adoption_panel(**study)
    assert res["status"] == "ok"
    est = res["estimate"]
    assert est["inference_status"] == "cluster_robust_cr1"
    assert abs(est["coefficient"] - 2.5) < 0.25
    assert 0.0 < est["p_value"] < 1.0
    lo, hi = est["ci95"]
    assert lo < est["coefficient"] < hi
    assert res["design"]["adoption_date"] == "2026-01-05"
    assert res["design"]["pre_periods"] == 4 and res["design"]["post_periods"] == 4


def test_matches_dummy_ols_oracle_coefficient_and_residuals():
    study = _make_study(n_units=9, n_periods=6, adoption_index=3, seed=77)
    y = np.asarray(study["outcomes"], dtype=float)
    d = np.asarray(study["treatment"], dtype=float)
    res = estimate_common_adoption_panel(**study)
    assert res["status"] == "ok"
    b_oracle, resid_oracle, _ = _dummy_ols_oracle(y, d)
    beta_oracle = float(b_oracle[-1])
    beta_module = res["estimate"]["coefficient"]
    assert math.isclose(beta_module, beta_oracle, rel_tol=1e-9, abs_tol=1e-12)
    # residuals: within transformation of y minus beta * within transformation of D
    resid_module = _within(y) - beta_module * _within(d)
    assert np.allclose(resid_module.ravel(), resid_oracle, rtol=1e-8, atol=1e-10)


def test_cluster_sandwich_oracle_matches_cr1_se():
    study = _make_study(n_units=10, n_periods=6, adoption_index=3, seed=99)
    y = np.asarray(study["outcomes"], dtype=float)
    d = np.asarray(study["treatment"], dtype=float)
    res = estimate_common_adoption_panel(**study)
    assert res["status"] == "ok"
    _, resid_oracle, x = _dummy_ols_oracle(y, d)
    n, t = y.shape
    cluster_of_row = np.repeat(study["cluster_ids"], t)
    v, g = _cr1_oracle(x, resid_oracle, cluster_of_row)
    se_oracle = math.sqrt(float(v[-1, -1]))
    assert g == res["design"]["n_clusters"] == 10
    assert math.isclose(res["estimate"]["se"], se_oracle, rel_tol=1e-7, abs_tol=1e-12)


def test_two_period_did_mean_change_equivalence():
    study = _make_study(n_units=8, n_periods=2, adoption_index=1, n_treated=4, beta=1.75, seed=5)
    y = np.asarray(study["outcomes"], dtype=float)
    d = np.asarray(study["treatment"], dtype=float)
    res = estimate_common_adoption_panel(**study)
    assert res["status"] == "ok"
    treated_rows = d[:, 1] == 1.0
    did = (y[treated_rows, 1].mean() - y[treated_rows, 0].mean()) - (
        y[~treated_rows, 1].mean() - y[~treated_rows, 0].mean()
    )
    assert math.isclose(res["estimate"]["coefficient"], did, rel_tol=1e-9, abs_tol=1e-12)


def test_unit_time_and_level_shift_invariance():
    study = _make_study(n_units=10, n_periods=6, adoption_index=3, seed=21)
    base = estimate_common_adoption_panel(**study)
    y = np.asarray(study["outcomes"], dtype=float).copy()
    unit_shift = np.arange(y.shape[0], dtype=float)[:, None] * 3.0
    time_shift = np.arange(y.shape[1], dtype=float)[None, :] * 2.0
    study["outcomes"] = y + unit_shift + time_shift + 17.0
    shifted = estimate_common_adoption_panel(**study)
    assert base["status"] == "ok" and shifted["status"] == "ok"
    assert math.isclose(
        base["estimate"]["coefficient"], shifted["estimate"]["coefficient"], rel_tol=1e-9
    )
    assert math.isclose(base["estimate"]["se"], shifted["estimate"]["se"], rel_tol=1e-8)


def test_row_order_and_period_label_invariance():
    study = _make_study(n_units=10, n_periods=6, adoption_index=3, seed=31)
    base = estimate_common_adoption_panel(**study)
    # Units (rows) carry no order: permuting rows with their labels and clusters
    # must not change the estimate.  Column order *is* semantic (periods must be
    # strictly increasing), so the matching invariance is relabelling the dates
    # while preserving their order.
    rng = np.random.default_rng(4242)
    row_perm = rng.permutation(10)
    row_permuted = {
        "outcomes": np.asarray(study["outcomes"])[row_perm, :],
        "treatment": np.asarray(study["treatment"])[row_perm, :],
        "unit_ids": [study["unit_ids"][i] for i in row_perm],
        "periods": list(study["periods"]),
        "cluster_ids": [study["cluster_ids"][i] for i in row_perm],
    }
    res = estimate_common_adoption_panel(**row_permuted)
    assert base["status"] == "ok" and res["status"] == "ok"
    assert math.isclose(
        base["estimate"]["coefficient"], res["estimate"]["coefficient"], rel_tol=1e-8
    )
    assert math.isclose(base["estimate"]["se"], res["estimate"]["se"], rel_tol=1e-8)

    relabeled = copy.deepcopy(study)
    relabeled["periods"] = ["2027-03-%02d" % (2 * i + 1) for i in range(6)]
    res2 = estimate_common_adoption_panel(**relabeled)
    assert res2["status"] == "ok"
    assert math.isclose(
        base["estimate"]["coefficient"], res2["estimate"]["coefficient"], rel_tol=1e-12
    )
    assert res2["design"]["adoption_date"] == "2027-03-07"


def test_bool_treatment_mask_accepted():
    study = _make_study(seed=11)
    float_res = estimate_common_adoption_panel(**study)
    bool_study = copy.deepcopy(study)
    bool_study["treatment"] = np.asarray(study["treatment"]).astype(bool)
    bool_res = estimate_common_adoption_panel(**bool_study)
    assert float_res["status"] == "ok" and bool_res["status"] == "ok"
    assert math.isclose(
        float_res["estimate"]["coefficient"], bool_res["estimate"]["coefficient"], rel_tol=1e-12
    )


def test_grouped_assignment_clusters_change_inference_and_counts():
    groups = ["g0"] * 3 + ["g1"] * 3 + ["g2"] * 3 + ["g3"] * 3  # 2 treated + 2 control clusters
    study = _make_study(n_units=12, n_periods=6, adoption_index=3, seed=13, cluster_groups=groups)
    grouped = estimate_common_adoption_panel(**study)
    per_unit = _make_study(n_units=12, n_periods=6, adoption_index=3, seed=13)
    individual = estimate_common_adoption_panel(**per_unit)
    assert grouped["status"] == "ok" and individual["status"] == "ok"
    assert grouped["design"]["n_clusters"] == 4
    assert grouped["design"]["treated_clusters"] == 2
    assert grouped["design"]["control_clusters"] == 2
    assert individual["design"]["n_clusters"] == 12
    assert grouped["design"]["treated_units"] == 6 and grouped["design"]["control_units"] == 6
    cluster_of_unit = {
        entry["cluster_id"]: entry["unit_ids"] for entry in grouped["design"]["clusters"]
    }
    assert cluster_of_unit["g0"] == ["u000", "u001", "u002"]
    assert not math.isclose(
        grouped["estimate"]["se"], individual["estimate"]["se"], rel_tol=1e-3
    )
    assert math.isclose(
        grouped["estimate"]["coefficient"], individual["estimate"]["coefficient"], rel_tol=1e-12
    )


def test_small_cluster_warning_and_reference_distribution():
    groups = ["g0", "g0", "g1", "g1", "g2", "g2", "g3", "g3"]
    study = _make_study(
        n_units=8, n_periods=6, adoption_index=3, n_treated=4, seed=17, cluster_groups=groups
    )
    res = estimate_common_adoption_panel(**study)
    assert res["status"] == "ok"
    est = res["estimate"]
    assert est["degrees_of_freedom"] == 3
    assert est["reference_distribution"] == "student_t"
    assert any("small_cluster_warning" in w for w in res["warnings"])


# ---------------------------------------------------------------------------
# inference ceilings: insufficient clusters and exact fit
# ---------------------------------------------------------------------------


def test_insufficient_clusters_gives_point_estimate_only():
    groups = ["g0"] * 4 + ["g1"] * 4  # one treated cluster, one control cluster
    study = _make_study(
        n_units=8, n_periods=6, adoption_index=3, n_treated=4, seed=19, cluster_groups=groups
    )
    res = estimate_common_adoption_panel(**study)
    assert res["status"] == "ok"
    est = res["estimate"]
    assert est["inference_status"] == "insufficient_clusters"
    assert est["se"] is None and est["ci95"] is None and est["p_value"] is None
    assert abs(est["coefficient"] - 2.5) < 0.5
    assert res["design"]["treated_clusters"] == 1 and res["design"]["control_clusters"] == 1


def test_exact_fit_reports_degenerate_variance_not_fake_certainty():
    n_units, n_periods, adoption_index, beta = 8, 6, 3, 3.0
    d = _mask(n_units, n_periods, adoption_index, n_units // 2)
    unit_effects = np.arange(n_units, dtype=float)[:, None]
    time_effects = np.arange(n_periods, dtype=float)[None, :]
    y = unit_effects + time_effects + beta * d  # exact fit, zero residual variation
    groups = ["g0", "g0", "g1", "g1", "g2", "g2", "g3", "g3"]  # passes the cluster gate
    res = estimate_common_adoption_panel(
        outcomes=y,
        treatment=d,
        unit_ids=_labels(n_units, "u"),
        periods=_periods(n_periods),
        cluster_ids=groups,
    )
    assert res["status"] == "ok"
    est = res["estimate"]
    assert est["inference_status"] == "degenerate_variance"
    assert est["se"] is None and est["ci95"] is None and est["p_value"] is None
    assert math.isclose(est["coefficient"], beta, rel_tol=1e-9)
    assert res["warnings"]  # the degenerate-uncertainty decision is surfaced, not silent


# ---------------------------------------------------------------------------
# invalid inputs -> typed abstentions
# ---------------------------------------------------------------------------


def _reason(res):
    assert res["status"] == "rejected", res
    assert res["reason_code"] and res["reason"]
    assert res["research_only"] is True
    return res["reason_code"]


def test_nonfinite_and_boolean_outcomes_rejected():
    study = _make_study(seed=23)
    bad = copy.deepcopy(study)
    bad["outcomes"] = np.asarray(study["outcomes"], dtype=float).copy()
    bad["outcomes"][2, 3] = np.nan
    assert _reason(estimate_common_adoption_panel(**bad)) == "nonfinite_outcomes"
    bad["outcomes"][2, 3] = np.inf
    assert _reason(estimate_common_adoption_panel(**bad)) == "nonfinite_outcomes"
    bool_study = copy.deepcopy(study)
    bool_study["outcomes"] = np.asarray(study["outcomes"]) > 0.0
    assert _reason(estimate_common_adoption_panel(**bool_study)) == "boolean_outcomes"


def test_shape_and_ragged_input_rejected():
    study = _make_study(seed=29)
    short = copy.deepcopy(study)
    short["treatment"] = np.asarray(study["treatment"])[:, :-1]
    assert _reason(estimate_common_adoption_panel(**short)) == "shape_mismatch"
    ragged = copy.deepcopy(study)
    ragged["outcomes"] = [list(map(float, row)) for row in np.asarray(study["outcomes"])]
    ragged["outcomes"][0] = ragged["outcomes"][0][:-1]
    res = estimate_common_adoption_panel(**ragged)
    assert res["status"] == "rejected"
    assert res["reason_code"] in ("invalid_input", "invalid_shape", "non_numeric_entries")


def test_invalid_treatment_paths_rejected():
    study = _make_study(n_units=8, n_periods=6, adoption_index=3, n_treated=4, seed=37)

    def _edited(mutate):
        edited = copy.deepcopy(study)
        edited["treatment"] = np.asarray(study["treatment"], dtype=float).copy()
        mutate(edited["treatment"])
        return edited

    def _stagger(d):
        d[1, :2] = 0.0
        d[1, 2:] = 1.0  # second treated unit adopts two periods earlier

    def _reversal(d):
        d[0, 4] = 0.0  # on then off

    def _always(d):
        d[:4, :] = 1.0  # treated units are treated from the first period: no pre-period

    def _fractional(d):
        d[0, 0] = 0.5

    assert _reason(estimate_common_adoption_panel(**_edited(_stagger))) == "staggered_adoption"
    assert _reason(estimate_common_adoption_panel(**_edited(_reversal))) == "invalid_treatment_path"
    assert _reason(estimate_common_adoption_panel(**_edited(_always))) == "no_pre_period"
    assert (
        _reason(estimate_common_adoption_panel(**_edited(_fractional)))
        == "invalid_treatment_values"
    )


def test_missing_arm_rejected():
    study = _make_study(n_units=8, n_periods=6, adoption_index=3, seed=41)
    all_treated = copy.deepcopy(study)
    all_treated["treatment"] = np.ones((8, 6))
    assert _reason(estimate_common_adoption_panel(**all_treated)) == "no_control_units"
    all_control = copy.deepcopy(study)
    all_control["treatment"] = np.zeros((8, 6))
    assert _reason(estimate_common_adoption_panel(**all_control)) == "no_treated_units"


def test_mixed_treatment_within_cluster_rejected():
    study = _make_study(n_units=8, n_periods=6, adoption_index=3, seed=43)
    mixed = copy.deepcopy(study)
    mixed["cluster_ids"] = ["m0"] * 8  # one cluster holds treated and control units
    assert _reason(estimate_common_adoption_panel(**mixed)) == "mixed_treatment_within_cluster"


def test_invalid_identifiers_and_periods_rejected():
    study = _make_study(n_units=8, n_periods=6, adoption_index=3, seed=47)

    dup = copy.deepcopy(study)
    dup["unit_ids"] = list(study["unit_ids"])
    dup["unit_ids"][3] = dup["unit_ids"][0]
    assert _reason(estimate_common_adoption_panel(**dup)) == "duplicate_unit_ids"

    empty = copy.deepcopy(study)
    empty["cluster_ids"] = list(study["cluster_ids"])
    empty["cluster_ids"][2] = ""
    assert _reason(estimate_common_adoption_panel(**empty)) == "invalid_label"

    wrong_len = copy.deepcopy(study)
    wrong_len["unit_ids"] = list(study["unit_ids"])[:-1]
    assert _reason(estimate_common_adoption_panel(**wrong_len)) == "length_mismatch"

    increasing = _periods(6)
    duplicated = list(increasing)
    duplicated[3] = duplicated[2]
    bad_period_lists = (
        ["2026-13-01"] + increasing[1:],  # impossible calendar date
        ["not-a-date"] + increasing[1:],  # not an ISO date
        ["20260101"] + increasing[1:],  # non-canonical form
        duplicated,  # repeated period
        list(reversed(increasing)),  # decreasing
    )
    for bad_periods in bad_period_lists:
        bad = copy.deepcopy(study)
        bad["periods"] = bad_periods
        assert _reason(estimate_common_adoption_panel(**bad)) == "invalid_periods"


def test_residual_degrees_of_freedom_must_be_positive():
    study = _make_study(n_units=2, n_periods=2, adoption_index=1, n_treated=1, seed=53)
    res = estimate_common_adoption_panel(**study)
    assert _reason(res) == "insufficient_observations"
    assert res["details"]["residual_df"] == 0


# ---------------------------------------------------------------------------
# output hygiene
# ---------------------------------------------------------------------------


def test_ok_result_is_json_safe_and_reports_assumption_ceilings():
    study = _make_study(seed=61)
    res = estimate_common_adoption_panel(**study, design_id="unit-test-design")
    assert res["status"] == "ok"
    text = json.dumps(res, allow_nan=False)  # raises on NaN/Infinity
    assert "NaN" not in text and "Infinity" not in text
    assert _all_finite(res)
    assert res["authority"] == "research_only"
    assert res["estimate_type"] == "descriptive_estimate"
    assert res["assumptions"]["parallel_trends"] == "NOT VERIFIED"
    assert res["assumptions"]["no_anticipation"] == "NOT VERIFIED"
    assert res["assumptions"]["no_spillover"] == "NOT VERIFIED"
    assert res["design_id"] == "unit-test-design"
    assert res["design"]["first_period"] == "2026-01-01"
    assert res["design"]["last_period"] == "2026-01-08"
    assert res["design"]["residual_df"] == res["design"]["NT"] - res["design"]["K"]
    assert res["limitations"]


# ---------------------------------------------------------------------------
# CLI contract
# ---------------------------------------------------------------------------


def _cli(payload_text):
    return subprocess.run(
        [sys.executable, "-m", "engine.panel_did"],
        input=payload_text,
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
    )


def _cli_payload(**overrides):
    study = _make_study(n_units=8, n_periods=6, adoption_index=3, seed=71)
    payload = {
        "outcomes": np.asarray(study["outcomes"]).tolist(),
        "treatment": np.asarray(study["treatment"]).tolist(),
        "unit_ids": study["unit_ids"],
        "periods": study["periods"],
        "cluster_ids": study["cluster_ids"],
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_cli_success_emits_finite_json_and_exits_zero():
    proc = _cli(_cli_payload())
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["status"] == "ok"
    assert out["estimate"]["inference_status"] == "cluster_robust_cr1"
    assert "NaN" not in proc.stdout and "Infinity" not in proc.stdout
    assert _all_finite(out)


def test_cli_malformed_request_exits_nonzero_with_typed_failure():
    for raw, expected_code in (
        ("{not json", "invalid_json"),
        ("[1, 2, 3]", "invalid_request"),
        ("{}", "missing_field"),
        (
            json.dumps({"outcomes": [], "treatment": [], "unit_ids": [], "periods": [],
                        "cluster_ids": [], "extra": 1}),
            "unknown_field",
        ),
    ):
        proc = _cli(raw)
        assert proc.returncode != 0
        out = json.loads(proc.stdout)
        assert out["status"] == "error"
        assert out["reason_code"] == expected_code


def test_cli_rejected_study_exits_nonzero_and_never_looks_like_success():
    study = _make_study(n_units=8, n_periods=6, adoption_index=3, n_treated=4, seed=71)
    staggered = {
        "outcomes": np.asarray(study["outcomes"]).tolist(),
        "treatment": np.asarray(study["treatment"]).tolist(),
        "unit_ids": list(study["unit_ids"]),
        "periods": list(study["periods"]),
        "cluster_ids": list(study["cluster_ids"]),
    }
    staggered["treatment"][1][:2] = [0.0, 0.0]
    staggered["treatment"][1][2:] = [1.0] * 4  # second treated unit adopts earlier
    proc = _cli(json.dumps(staggered))
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["status"] == "rejected"
    assert out["reason_code"] == "staggered_adoption"


def test_mixed_boolean_outcomes_are_rejected_before_numeric_coercion():
    study = _make_study()
    study['outcomes'] = study['outcomes'].tolist()
    study['outcomes'][0][0] = True
    result = estimate_common_adoption_panel(**study)
    assert result['status'] == 'rejected'
    assert result['reason_code'] == 'boolean_outcomes'


def test_probability_underflow_is_not_reported_as_exact_zero():
    study = _make_study(n_units=100, n_periods=4, adoption_index=2,
                        n_treated=50, beta=1, noise_sd=1e-10)
    result = estimate_common_adoption_panel(**study)
    estimate = result['estimate']
    assert result['status'] == 'ok'
    assert estimate['se'] > 0
    assert estimate['p_value'] is None
    assert estimate['p_value_status'] == 'numerical_underflow'
    assert 'underflow' in estimate['inference_detail']
