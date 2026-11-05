"""O(1) RSI-MACD histogram append oracle vs canonical full-history recompute."""
from __future__ import annotations

import dataclasses

import numpy as np
import pandas as pd
import pytest

from engine.entry_radar import indicator_core as ic

WALK = 100.0 * np.exp(np.cumsum(np.random.default_rng(7).normal(0, 0.02, 200)))


def canonical(closes, price):
    return ic.last_finite(ic.rsi_macd_hist(pd.Series(np.append(closes, price))))


def test_appended_matches_canonical_on_fifty_walks() -> None:
    rng = np.random.default_rng(20261003)
    walks_with_hist = 0
    samples = 0
    for _ in range(50):
        n = int(rng.integers(30, 801))
        closes = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
        miss = rng.random(n) < 0.05
        miss[-1] = False
        closes = np.where(miss, np.nan, closes)
        kd = ic.stoch_rsi_append_state(closes)
        hs = ic.rsi_macd_hist_append_state(closes)
        if kd is None or hs is None:
            continue
        walks_with_hist += 1
        last = closes[-1]
        for price in (last * 0.95, last * 1.0001, last * 1.04, last):
            app = ic.rsi_macd_hist_appended(kd, hs, float(price))
            ref = canonical(closes, price)
            assert app is not None and ref is not None
            assert abs(app - ref) <= 1e-9
            samples += 1
    assert walks_with_hist == 46
    assert samples == 184


def test_state_is_none_until_the_histogram_is_warm() -> None:
    assert ic.rsi_macd_hist_append_state(WALK[:77]) is None
    assert ic.last_finite(ic.rsi_macd_hist(pd.Series(WALK[:77]))) is None
    assert ic.rsi_macd_hist_append_state(WALK[:78]) is not None
    assert ic.last_finite(ic.rsi_macd_hist(pd.Series(WALK[:78]))) is not None


def test_flat_and_only_up_histories_have_no_state() -> None:
    assert ic.rsi_macd_hist_append_state(np.full(200, 50.0)) is None
    assert ic.rsi_macd_hist_append_state(100.0 + np.arange(200.0)) is None
    assert canonical(np.full(200, 50.0), 49.0) is None


def test_no_state_when_the_last_close_is_missing_or_history_is_empty() -> None:
    walk_bad = WALK.copy()
    walk_bad[-1] = np.nan
    assert ic.rsi_macd_hist_append_state(walk_bad) is None
    assert ic.rsi_macd_hist_append_state([]) is None


def test_non_finite_price_returns_none() -> None:
    kd = ic.stoch_rsi_append_state(WALK)
    hs = ic.rsi_macd_hist_append_state(WALK)
    assert kd is not None and hs is not None
    assert ic.rsi_macd_hist_appended(kd, hs, float("nan")) is None
    assert ic.rsi_macd_hist_appended(kd, hs, float("inf")) is None


def test_missing_rsi_carries_both_averages() -> None:
    kd = ic.stoch_rsi_append_state(WALK)
    hs = ic.rsi_macd_hist_append_state(WALK)
    assert kd is not None and hs is not None
    kd0 = dataclasses.replace(kd, dn_prev=0.0)
    expected = (2.0 / 3.0) * ((hs.fast - hs.base) - hs.sig)
    assert ic.rsi_macd_hist_appended(kd0, hs, kd.last_close * 1.01) == pytest.approx(
        expected, abs=1e-12
    )


def test_one_average_step() -> None:
    assert ic._ewm_step(5.0, 5.0, 14) == 5.0
    assert ic._ewm_step(5.0, float("nan"), 14) == 5.0
    assert ic._ewm_step(0.0, 15.0, 14) == pytest.approx(2.0, abs=1e-12)


def test_state_is_a_frozen_record_of_three_floats() -> None:
    assert [f.name for f in dataclasses.fields(ic.RsiMacdHistAppendState)] == [
        "fast",
        "base",
        "sig",
    ]
    hs = ic.rsi_macd_hist_append_state(WALK)
    assert hs is not None
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        hs.fast = 0.0  # type: ignore[misc]


def test_indicator_core_constants_are_unchanged() -> None:
    assert (
        ic.INDICATOR_CORE["macd_fast"],
        ic.INDICATOR_CORE["macd_slow"],
        ic.INDICATOR_CORE["macd_signal"],
    ) == (14, 60, 5)
    assert len(ic.INDICATOR_CORE) == 17
