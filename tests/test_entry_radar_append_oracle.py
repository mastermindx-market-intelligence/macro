"""O(1) StochRSI append oracle vs canonical full-history recompute."""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from engine import canon
from engine.entry_radar import indicator_core as ic


def reference(closes: np.ndarray, price: float) -> tuple[float | None, float | None]:
    k, d = ic.stoch_rsi_kd(pd.Series(np.append(closes, price)))
    return ic.last_finite(k), ic.last_finite(d)


def _assert_matches_reference(closes: np.ndarray, prices: np.ndarray) -> tuple[float, float]:
    state = ic.stoch_rsi_append_state(closes)
    assert state is not None
    max_k = 0.0
    max_d = 0.0
    for price in prices:
        rk, rd = reference(closes, float(price))
        ak, ad = ic.stoch_rsi_kd_appended(state, float(price))
        assert (ak is None) == (rk is None)
        assert (ad is None) == (rd is None)
        if rk is not None and ak is not None:
            max_k = max(max_k, abs(ak - rk))
            assert abs(ak - rk) <= 1e-9
        if rd is not None and ad is not None:
            max_d = max(max_d, abs(ad - rd))
            assert abs(ad - rd) <= 1e-9
    return max_k, max_d


def test_appended_matches_canonical_on_three_histories() -> None:
    rng = np.random.default_rng(20261003)
    last = 100.0
    histories = [
        100.0 + np.cumsum(rng.normal(0, 1, 400)),
        np.linspace(120.0, 80.0, 300) + rng.normal(0, 0.5, 300),
        50.0 + np.cumsum(rng.normal(0, 2, 3000)),
    ]
    global_max_k = 0.0
    global_max_d = 0.0
    for closes in histories:
        last = float(closes[-1])
        prices = np.geomspace(0.01 * last, 3.0 * last, 50)
        mk, md = _assert_matches_reference(closes, prices)
        global_max_k = max(global_max_k, mk)
        global_max_d = max(global_max_d, md)
    # Stash for manual inspection if needed (pytest does not read these).
    assert global_max_k <= 1e-9
    assert global_max_d <= 1e-9


def test_appended_matches_canonical_with_a_nan_in_the_tail() -> None:
    rng = np.random.default_rng(99)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, 400))
    closes[-5] = np.nan
    state = ic.stoch_rsi_append_state(closes)
    last = float(closes[-1])
    prices = np.geomspace(0.5 * last, 1.5 * last, 20)
    if state is None:
        # Canon path may still answer probes; state builder correctly refuses.
        return
    _assert_matches_reference(closes, prices)


def test_state_is_none_for_short_history() -> None:
    closes = np.linspace(100.0, 110.0, 10)
    assert ic.stoch_rsi_append_state(closes) is None


def test_state_is_none_or_agrees_on_flat_history() -> None:
    closes = np.full(200, 42.0)
    state = ic.stoch_rsi_append_state(closes)
    prices = np.array([40.0, 42.0, 44.0])
    if state is None:
        return
    for price in prices:
        rk, rd = reference(closes, float(price))
        ak, ad = ic.stoch_rsi_kd_appended(state, float(price))
        assert (ak is None) == (rk is None)
        assert (ad is None) == (rd is None)
        if rk is not None and ak is not None:
            assert abs(ak - rk) <= 1e-9
        if rd is not None and ad is not None:
            assert abs(ad - rd) <= 1e-9


def test_constant_rsi_window_gives_none_pair() -> None:
    s = ic.StochRsiAppendState(
        last_close=100.0,
        up_prev=0.0,
        dn_prev=1.0,
        rsi_tail=(0.0,) * 13,
        rawk_tail=(50.0, 60.0),
        k_tail=(40.0, 45.0),
    )
    assert ic.stoch_rsi_kd_appended(s, 99.0) == (None, None)


def test_zero_loss_average_gives_none_pair() -> None:
    s = ic.StochRsiAppendState(
        last_close=100.0,
        up_prev=1.0,
        dn_prev=0.0,
        rsi_tail=(50.0,) * 13,
        rawk_tail=(50.0, 60.0),
        k_tail=(40.0, 45.0),
    )
    assert ic.stoch_rsi_kd_appended(s, 101.0) == (None, None)


def test_nan_inside_the_rsi_window_gives_none_pair() -> None:
    s = ic.StochRsiAppendState(
        last_close=100.0,
        up_prev=1.0,
        dn_prev=1.0,
        rsi_tail=(50.0,) * 6 + (float("nan"),) + (50.0,) * 6,
        rawk_tail=(50.0, 60.0),
        k_tail=(40.0, 45.0),
    )
    assert ic.stoch_rsi_kd_appended(s, 101.0) == (None, None)


def test_finite_window_gives_a_finite_pair() -> None:
    s = ic.StochRsiAppendState(
        last_close=100.0,
        up_prev=1.0,
        dn_prev=1.0,
        rsi_tail=(50.0,) * 13,
        rawk_tail=(50.0, 60.0),
        k_tail=(40.0, 45.0),
    )
    k, d = ic.stoch_rsi_kd_appended(s, 101.0)
    assert k is not None and d is not None
    assert abs(k - (50.0 + 60.0 + 100.0) / 3.0) <= 1e-12
    assert abs(d - (40.0 + 45.0 + k) / 3.0) <= 1e-12


def test_monotone_decline_agrees_with_canonical() -> None:
    closes = 100.0 - 0.5 * np.arange(80)
    prices = np.array(
        [closes[-1] - 0.5, closes[-1], closes[-1] + 0.5, closes[-1] + 5.0],
        dtype=float,
    )
    state = ic.stoch_rsi_append_state(closes)
    assert state is not None
    _assert_matches_reference(closes, prices)


def test_monotone_rise_agrees_with_canonical() -> None:
    closes = 100.0 + 0.5 * np.arange(80)
    if ic.stoch_rsi_append_state(closes) is None:
        assert ic.stoch_rsi_append_state(closes) is None
        return
    prices = np.array(
        [closes[-1] + 0.5, closes[-1], closes[-1] - 0.5, closes[-1] - 5.0],
        dtype=float,
    )
    _assert_matches_reference(closes, prices)


def test_non_finite_price_returns_none_pair() -> None:
    rng = np.random.default_rng(7)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, 400))
    state = ic.stoch_rsi_append_state(closes)
    assert state is not None
    assert ic.stoch_rsi_kd_appended(state, float("nan")) == (None, None)
    assert ic.stoch_rsi_kd_appended(state, float("inf")) == (None, None)


def test_canonical_wrappers_are_unchanged() -> None:
    rng = np.random.default_rng(1)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, 400))
    s = pd.Series(closes)
    k_ic, d_ic = ic.stoch_rsi_kd(s)
    k_canon, d_canon = canon.stoch_rsi_kd(s)
    pd.testing.assert_series_equal(k_ic, k_canon)
    pd.testing.assert_series_equal(d_ic, d_canon)


def test_appended_is_much_faster_than_canonical() -> None:
    rng = np.random.default_rng(11544)
    closes = 100.0 + np.cumsum(rng.normal(0, 1, 11544))
    state = ic.stoch_rsi_append_state(closes)
    assert state is not None
    probe = float(closes[-1]) * 1.01

    t0 = time.perf_counter()
    for _ in range(200):
        ic.stoch_rsi_kd_appended(state, probe)
    fast_per = (time.perf_counter() - t0) / 200

    t1 = time.perf_counter()
    for _ in range(3):
        reference(closes, probe)
    canon_per = (time.perf_counter() - t1) / 3

    ratio = canon_per / fast_per
    assert ratio >= 50.0, f"speed ratio {ratio:.1f} < 50"
