"""Grey Deer W2: observed-move primitives against the frozen preregistration.

Synthetic series only. No market outcome is read here; the W3 runner is the
one place the frozen protocol touches real closes.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from lib import observed_moves as om

CLOSES = [100.0, 98.0, 99.0, 95.0, 97.0, 101.0, 100.0, 96.0, 99.0, 102.0]
NAN = float("nan")


def _series(values) -> pd.Series:
    idx = pd.bdate_range("2024-01-02", periods=len(values))
    return pd.Series(values, index=idx, dtype=float)


def _random_walk(n: int = 300, seed: int = 7) -> pd.Series:
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, 0.012, n)
    return _series(100.0 * np.exp(np.cumsum(steps)))


def _brute_forward_max_loss(values, h):
    out = []
    for t in range(len(values)):
        window = values[t + 1 : t + 1 + h]
        if len(window) < h:
            out.append(NAN)
        else:
            out.append(max(0.0, 1.0 - min(window) / values[t]))
    return out


@pytest.mark.parametrize(
    "h, expected",
    [
        (1, [0.02, 0.0, 1 - 95 / 99, 0.0, 0.0, 1 - 100 / 101, 0.04, 0.0, 0.0, NAN]),
        (2, [0.02, 1 - 95 / 98, 1 - 95 / 99, 0.0, 0.0, 1 - 96 / 101, 0.04, 0.0, NAN, NAN]),
        (3, [1 - 95 / 100, 1 - 95 / 98, 1 - 95 / 99, 0.0, 1 - 96 / 97, 1 - 96 / 101, 0.04, NAN, NAN, NAN]),
    ],
)
def test_forward_max_loss_hand_computed(h, expected):
    got = om.forward_max_loss(_series(CLOSES), h)
    np.testing.assert_allclose(got.to_numpy(), np.array(expected), rtol=0, atol=1e-12, equal_nan=True)


@pytest.mark.parametrize("h", om.HORIZONS)
def test_forward_max_loss_matches_brute_force(h):
    close = _random_walk()
    got = om.forward_max_loss(close, h)
    want = _brute_forward_max_loss(close.tolist(), h)
    np.testing.assert_allclose(got.to_numpy(), np.array(want), rtol=0, atol=1e-12, equal_nan=True)
    assert got.tail(h).isna().all()
    assert got.iloc[: len(close) - h].notna().all()


def test_forward_max_loss_is_zero_on_a_rising_path_never_negative():
    close = _series(np.linspace(100.0, 130.0, 40))
    got = om.forward_max_loss(close, 5)
    assert (got.dropna() == 0.0).all()
    assert (om.forward_max_loss(_random_walk(), 10).dropna() >= 0.0).all()


def test_forward_max_loss_reads_exactly_the_next_h_closes():
    close = _random_walk()
    h, t = 10, 120
    base = om.forward_max_loss(close, h)

    beyond = close.copy()
    beyond.iloc[t + h + 1 :] *= 0.5
    after = om.forward_max_loss(beyond, h)
    pd.testing.assert_series_equal(base.iloc[: t + 1], after.iloc[: t + 1])

    inside = close.copy()
    inside.iloc[t + h] = close.iloc[t] * 0.80
    assert om.forward_max_loss(inside, h).iloc[t] == pytest.approx(0.20, abs=1e-12)
    assert base.iloc[t] != pytest.approx(0.20, abs=1e-12)


def test_forward_max_loss_rejects_nonpositive_horizon():
    with pytest.raises(ValueError):
        om.forward_max_loss(_series(CLOSES), 0)


@pytest.mark.parametrize(
    "fn",
    [
        lambda s: om.trailing_drawdown(s, 63),
        lambda s: om.log_return(s, 5),
        lambda s: om.log_return(s, 10),
        lambda s: om.sma_gap(s, 21),
        lambda s: om.sma_gap(s, 63),
    ],
)
def test_features_are_causal(fn):
    close = _random_walk()
    t = 150
    base = fn(close)
    perturbed = close.copy()
    perturbed.iloc[t + 1 :] *= 1.7
    pd.testing.assert_series_equal(base.iloc[: t + 1], fn(perturbed).iloc[: t + 1])


def test_feature_warm_up_rows_are_nan_and_full_from_index_63():
    close = _random_walk()
    dd = om.trailing_drawdown(close, 63)
    assert dd.iloc[:62].isna().all() and dd.iloc[62:].notna().all()
    assert om.log_return(close, 10).iloc[:10].isna().all()
    assert om.log_return(close, 10).iloc[10:].notna().all()
    gap = om.sma_gap(close, 21)
    assert gap.iloc[:20].isna().all() and gap.iloc[20:].notna().all()
    frame = pd.concat(
        [dd, om.log_return(close, 5), om.log_return(close, 10), om.sma_gap(close, 21), om.sma_gap(close, 63)],
        axis=1,
    )
    assert frame.iloc[63:].notna().all().all()


def test_feature_values_hand_computed():
    close = _series(CLOSES)
    assert om.log_return(close, 3).iloc[3] == pytest.approx(math.log(95 / 100))
    assert om.sma_gap(close, 4).iloc[3] == pytest.approx(95 / np.mean([100, 98, 99, 95]) - 1)
    assert om.trailing_drawdown(close, 5).iloc[4] == pytest.approx(1 - 97 / 100)
    assert om.trailing_drawdown(close, 5).iloc[5] == pytest.approx(0.0)
    assert (om.trailing_drawdown(_random_walk(), 63).dropna() >= 0.0).all()


def test_loss_event_threshold_is_inclusive_and_immature_stays_absent():
    a = pd.Series([0.05, 0.0499999, NAN, 0.2, 0.0])
    y = om.loss_event(a)
    assert str(y.dtype) == "boolean"
    assert bool(y.iloc[0]) is True
    assert bool(y.iloc[1]) is False
    assert y.iloc[2] is pd.NA
    assert bool(y.iloc[3]) is True
    assert bool(y.iloc[4]) is False
    assert int(y.isna().sum()) == 1


def test_maturity_summary_counts_are_printed_not_hidden():
    summary = om.maturity_summary(om.forward_max_loss(_series(CLOSES), 3))
    assert summary == {"n_total": 10, "n_mature": 7, "n_immature": 3}


def test_price_basis_accepts_a_clean_series_and_the_inclusive_bounds():
    om.assert_price_basis(_random_walk())
    om.assert_price_basis(_series([100.0, 75.0]))
    om.assert_price_basis(_series([100.0, 76.0]))
    om.assert_price_basis(_series([75.0, 100.0]))
    om.assert_price_basis(_series([42.0]))


@pytest.mark.parametrize(
    "values",
    [
        [100.0, 101.0, 50.5, 51.0],
        [100.0, 74.99],
        [100.0, 133.4],
    ],
)
def test_price_basis_refuses_a_split_like_jump(values):
    with pytest.raises(om.PriceBasisDiscontinuity) as err:
        om.assert_price_basis(_series(values))
    assert err.value.code == "PRICE_BASIS_DISCONTINUITY"
    assert isinstance(err.value, ValueError)


def test_price_basis_refuses_rather_than_adjusts():
    close = _series([100.0, 101.0, 50.5, 51.0])
    before = close.copy()
    with pytest.raises(om.PriceBasisDiscontinuity):
        om.assert_price_basis(close)
    pd.testing.assert_series_equal(close, before)


@pytest.mark.parametrize(
    "index, code",
    [
        (pd.DatetimeIndex(["2024-01-02", "2024-01-02", "2024-01-03"]), "INDEX_NOT_STRICTLY_INCREASING"),
        (pd.DatetimeIndex(["2024-01-03", "2024-01-02", "2024-01-04"]), "INDEX_NOT_STRICTLY_INCREASING"),
    ],
)
def test_price_basis_refuses_a_bad_index(index, code):
    with pytest.raises(om.ObservedMoveRefusal) as err:
        om.assert_price_basis(pd.Series([100.0, 100.5, 101.0], index=index))
    assert err.value.code == code


@pytest.mark.parametrize("bad", [0.0, -1.0, NAN, float("inf")])
def test_price_basis_refuses_a_nonpositive_or_nonfinite_close(bad):
    with pytest.raises(om.ObservedMoveRefusal) as err:
        om.assert_price_basis(_series([100.0, bad, 100.0]))
    assert err.value.code == "NON_POSITIVE_OR_NON_FINITE_CLOSE"


def test_index_check_runs_before_the_value_checks():
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-02"])
    with pytest.raises(om.ObservedMoveRefusal) as err:
        om.assert_price_basis(pd.Series([100.0, 0.0], index=index))
    assert err.value.code == "INDEX_NOT_STRICTLY_INCREASING"


def test_realized_vol_is_not_reimplemented_here():
    assert not hasattr(om, "realized_vol")


def test_frozen_constants_match_the_preregistration():
    assert om.SPLIT_LIKE_RATIO == 0.75
    assert om.LOSS_THRESHOLD == 0.05
    assert om.HORIZONS == (5, 10, 21)
    assert om.DRAWDOWN_WINDOW == 63
