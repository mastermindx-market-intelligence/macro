"""Numerical equivalence and hard allocation bound for the existing CCW solver."""
import numpy as np
import pytest

from engine import corp_credit as credit


def inputs():
    rng = np.random.default_rng(4129)
    coupons = rng.uniform(0.0, 12.0, 97)
    tenors = rng.uniform(0.15, 55.0, 97)
    yields = rng.uniform(0.002, 0.23, 97)
    prices, _, _ = credit._pv_and_deriv_matrix(yields, np.zeros(97), coupons, tenors)
    return prices, coupons, tenors


@pytest.mark.parametrize('block_rows', [1, 7, 16, 97])
def test_blocking_preserves_original_result_and_solver_flags(monkeypatch, block_rows):
    data = inputs()
    baseline, original_flags = credit._ytm_solve_block(*data)
    monkeypatch.setattr(credit, 'YTM_BLOCK_ROWS', block_rows)
    result, flags = credit._ytm_solve(*data)
    np.testing.assert_allclose(result, baseline, rtol=1e-9, atol=1e-10, equal_nan=True)
    np.testing.assert_array_equal(flags, original_flags)
    valid = flags < 2
    pv, _, _ = credit._pv_and_deriv_matrix(result[valid], data[0][valid], data[1][valid], data[2][valid])
    np.testing.assert_allclose(pv, data[0][valid], atol=credit.YTM_CONV_TOL * 1.1, rtol=0)


def test_every_matrix_call_is_bounded(monkeypatch):
    data = inputs()
    original = credit._pv_and_deriv_matrix
    observed = []
    def bounded(yields, dirty, coupons, tenors):
        observed.append(len(yields))
        assert len(yields) <= 13
        return original(yields, dirty, coupons, tenors)
    monkeypatch.setattr(credit, '_pv_and_deriv_matrix', bounded)
    monkeypatch.setattr(credit, 'YTM_BLOCK_ROWS', 13)
    result, flags = credit._ytm_solve(*data)
    assert len(result) == 97
    assert observed
    assert len(flags) == 97


def test_row_order_and_input_arrays_are_preserved(monkeypatch):
    data = inputs()
    copies = [item.copy() for item in data]
    monkeypatch.setattr(credit, 'YTM_BLOCK_ROWS', 11)
    expected, expected_flags = credit._ytm_solve(*data)
    order = np.random.default_rng(24).permutation(len(data[0]))
    actual, actual_flags = credit._ytm_solve(*(item[order] for item in data))
    undo = np.argsort(order)
    np.testing.assert_allclose(actual[undo], expected, rtol=1e-9, atol=1e-10, equal_nan=True)
    np.testing.assert_array_equal(actual_flags[undo], expected_flags)
    for original, copy in zip(data, copies):
        np.testing.assert_array_equal(original, copy)


def test_empty_input_keeps_original_empty_behavior():
    values, flags = credit._ytm_solve(np.array([]), np.array([]), np.array([]))
    assert len(values) == len(flags) == 0


@pytest.mark.parametrize('data', [([99], [5, 6], [3]), ([[99]], [5], [3])])
def test_mismatched_shape_rejected_before_allocation(data):
    with pytest.raises(ValueError, match='equally sized'):
        credit._ytm_solve(*data)
