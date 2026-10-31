"""Entry Timing W2 estimator — synthetic-data contract tests (no outcome, price or registry read)."""
import numpy as np
import pytest

from research.prophet_v4 import entry_timing_w2_estimator as est


def _units(n_sessions, per_session, rng, block_shift=0.0, ell=44):
    sess = np.repeat(np.arange(n_sessions), per_session)
    vals = rng.normal(0.0, 1.0, size=len(sess)) + block_shift * ((sess // ell) % 2)
    return vals, sess


def test_t_quantile_df4_is_2_132():
    rng = np.random.default_rng(1)
    vals, sess = _units(220, 3, rng)
    fb = est.full_block_t_bounds(vals, sess, 220)
    assert fb["full_blocks"] == 5
    assert fb["t_quantile"] == pytest.approx(2.1318, abs=1e-3)


def test_full_block_count_and_empty_block_rule():
    rng = np.random.default_rng(2)
    vals, sess = _units(219, 2, rng)
    assert est.full_block_t_bounds(vals, sess, 219)["full_blocks"] == 4
    # a full block with no unit has no mean: no t bound, not identified
    vals, sess = _units(220, 2, rng)
    keep = (sess // 44) != 2
    idx = est.shared_index_set(220, resamples=200)
    rec = est.deciding_bounds(vals[keep], sess[keep], 220, index_set=idx)
    assert rec["identified"] is False and rec["t_full_blocks"]["empty_full_blocks"] == 1


def test_constant_values_give_the_constant():
    sess = np.repeat(np.arange(220), 2)
    vals = np.full(len(sess), 7.5)
    idx = est.shared_index_set(220, resamples=300)
    rec = est.deciding_bounds(vals, sess, 220, index_set=idx)
    assert rec["identified"] and rec["lower"] == pytest.approx(7.5) and rec["upper"] == pytest.approx(7.5)


def test_shared_index_set_makes_endpoints_commensurable():
    rng = np.random.default_rng(3)
    vals, sess = _units(230, 4, rng)
    idx = est.shared_index_set(230, resamples=500)
    a = est.mbb_bounds(vals, sess, 230, index_set=idx)
    b = est.mbb_bounds(2.0 * vals, sess, 230, index_set=idx)
    assert b["lower"] == pytest.approx(2 * a["lower"]) and b["upper"] == pytest.approx(2 * a["upper"])
    assert np.array_equal(idx, est.shared_index_set(230, resamples=500))   # deterministic


def test_deciding_bound_is_the_conservative_of_the_two():
    rng = np.random.default_rng(4)
    vals, sess = _units(264, 5, rng, block_shift=3.0)
    idx = est.shared_index_set(264, resamples=500)
    rec = est.deciding_bounds(vals, sess, 264, index_set=idx)
    assert rec["identified"] and rec["full_blocks"] == 6
    assert rec["lower"] == min(rec["mbb"]["lower"], rec["t_full_blocks"]["lower"])
    assert rec["upper"] == max(rec["mbb"]["upper"], rec["t_full_blocks"]["upper"])
    assert rec["lower_decided_by"] in ("mbb", "t") and rec["upper_decided_by"] in ("mbb", "t")


def test_floor_blocks_below_minimum_is_unidentified():
    rng = np.random.default_rng(5)
    vals, sess = _units(150, 3, rng)
    idx = est.shared_index_set(150, resamples=100)
    rec = est.deciding_bounds(vals, sess, 150, index_set=idx)
    assert rec["full_blocks"] == 3 and rec["identified"] is False
    assert est.deciding_bounds(vals, sess, 150, index_set=idx, full_blocks_min=3)["identified"] is True


def test_block_level_dependence_inflates_the_design_effect():
    rng = np.random.default_rng(6)
    vals, sess = _units(220, 20, rng, block_shift=2.0)
    d = est.dependence_diagnostic(vals, sess, 220, resamples=200)
    assert d["full_blocks"] == 5 and d["implied_design_effect"] > 5
    vals, sess = _units(220, 20, rng)
    assert est.dependence_diagnostic(vals, sess, 220, resamples=200)["implied_design_effect"] < 3


def test_t_bound_se_is_inflated_for_block_mean_autocorrelation():
    from research.prophet_v4.entry_timing_w2_estimator import se_inflation, lag1_autocorr, full_block_t_bounds
    assert se_inflation(0.0, 5) == 1.0
    assert abs(se_inflation(0.17, 5) - 1.165) < 0.005
    assert se_inflation(0.3, 5) > se_inflation(0.17, 5) > 1.0
    assert lag1_autocorr([1.0, 1.0, 1.0]) == 0.0
    assert lag1_autocorr([1, -1, 1, -1, 1, -1]) < 0.0
    # with the floor at zero the bound equals the naive t bound; with the floor it is wider
    n, ell = 5 * 44, 44
    rng = np.random.default_rng(3)
    values = rng.normal(0.0, 1.0, size=n)
    idx = np.arange(n)
    naive = full_block_t_bounds(values, idx, n, ell=ell, autocorr_floor=0.0)
    floored = full_block_t_bounds(values, idx, n, ell=ell, autocorr_floor=0.17)
    assert naive["se_inflation"] <= floored["se_inflation"]
    assert floored["lower"] <= naive["lower"] and floored["upper"] >= naive["upper"]
    assert floored["lag1_autocorr_used"] >= 0.17
