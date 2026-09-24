from __future__ import annotations

import numpy as np
import pandas as pd

from research.rates_direction import swing_phase_reset_exploratory as s


def _series(values):
    return pd.Series(values, dtype=float)


def test_reset_state_requires_extreme_visit_turn_and_trend():
    k = _series([50, 15, 10, 18, 25])
    d = _series([45, 20, 15, 16, 20])
    trend = pd.Series([1, 1, 1, 1, 1], dtype=int)
    got = s.reset_state(k, d, trend, 4)
    assert got.iloc[-1] == 1

    neutral = trend.copy()
    neutral.iloc[-1] = 0
    assert s.reset_state(k, d, neutral, 4).iloc[-1] == 0


def test_reset_state_down_mirror():
    k = _series([50, 85, 90, 82, 75])
    d = _series([55, 80, 85, 84, 80])
    trend = pd.Series([-1, -1, -1, -1, -1], dtype=int)
    got = s.reset_state(k, d, trend, 4)
    assert got.iloc[-1] == -1


def test_macd_early_curl_is_opposite_side_of_zero_and_recent():
    hist = _series([-0.10, -0.20, -0.25, -0.20, -0.10, 0.02])
    trend = pd.Series([1] * len(hist), dtype=int)
    got = s.recent_macd_curl(hist, trend, 3)
    assert got.iloc[3] == 1
    assert got.iloc[4] == 1
    assert got.iloc[5] == 1

    positive = _series([0.10, 0.20, 0.25, 0.20, 0.10, -0.02])
    downtrend = pd.Series([-1] * len(positive), dtype=int)
    got_down = s.recent_macd_curl(positive, downtrend, 3)
    assert got_down.iloc[3] == -1
    assert got_down.iloc[4] == -1
    assert got_down.iloc[5] == -1


def test_range_position_and_shallow_strength_are_not_oscillator_votes():
    close = pd.Series(np.arange(1.0, 13.0))
    pos = s.range_position(close, 12)
    assert pos.iloc[-1] == 1.0
    flat = pd.Series([5.0] * 12)
    assert np.isnan(s.range_position(flat, 12).iloc[-1])


def test_combine_requires_same_nonzero_direction():
    idx = pd.RangeIndex(4)
    a = pd.Series([1, 1, -1, 0], index=idx)
    b = pd.Series([1, -1, -1, 1], index=idx)
    assert s.combine_same_direction(a, b).tolist() == [1, 0, -1, 0]


def _bars(n=190):
    idx = pd.date_range("2025-01-02T15:00:00Z", periods=n, freq="2h")
    x = np.arange(n, dtype=float)
    close = 4.4 + 0.0015 * x + 0.035 * np.sin(x / 5.5)
    open_ = close - 0.002 * np.cos(x / 4.0)
    high = np.maximum(open_, close) + 0.006
    low = np.minimum(open_, close) - 0.006
    return pd.DataFrame(
        {
            "start": idx - pd.Timedelta(hours=2),
            "duration_seconds": 7200,
            "session": [str(t.date()) for t in idx],
            "hour_ids": [(t - pd.Timedelta(hours=2), t - pd.Timedelta(hours=1)) for t in idx],
            "valid": True,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        },
        index=idx,
    )


def test_phase_features_are_prefix_invariant_to_future_mutation():
    bars = _bars()
    a = s.build_phase_features(bars)
    mutated = bars.copy()
    mutated.loc[mutated.index[140]:, "close"] += 0.50
    mutated.loc[mutated.index[140]:, "open"] += 0.50
    mutated.loc[mutated.index[140]:, "high"] += 0.50
    mutated.loc[mutated.index[140]:, "low"] += 0.50
    b = s.build_phase_features(mutated)
    cols = ["trend5", "phase_trend", "range_pos", *s.CANDIDATES, "eligible"]
    pd.testing.assert_frame_equal(a.loc[: bars.index[139], cols], b.loc[: bars.index[139], cols])


def test_invalid_expected_bar_resets_warmup():
    bars = _bars(210)
    bars.loc[bars.index[100], "valid"] = False
    features = s.build_phase_features(bars)
    assert not bool(features.loc[bars.index[100], "eligible"])
    assert not bool(features.loc[bars.index[160], "eligible"])
    assert bool(features.loc[bars.index[190], "eligible"])


def test_walk_forward_uses_only_matured_prior_targets_and_normalized_probabilities():
    n = 170
    idx = pd.date_range("2025-01-01T15:00:00Z", periods=n, freq="2h")
    bars = pd.DataFrame({"session": [str(t.date()) for t in idx]}, index=idx)
    f = pd.DataFrame(index=idx)
    f["eligible"] = True
    f["vol"] = 2.0
    f["trend5"] = 1
    f["phase_trend"] = 1
    for name in s.CANDIDATES:
        f[name] = 1 if name in ("P_RESET", "R_RESET") else 0

    labels = []
    for i in range(n):
        end = min(i + 12, n - 1)
        labels.append(
            {
                "label": ("up", "down", "no_hit")[i % 3],
                "target_end_index": end,
                "target_end": idx[end].isoformat(),
                "barrier_bp": 5.0,
                "up_excursion_bp": 6.0,
                "down_excursion_bp": -3.0,
            }
        )
    rows = s.walk_forward(bars, f, labels)
    assert rows
    for row in rows:
        origin = pd.Timestamp(row["origin"])
        assert pd.Timestamp(row["last_training_target_end"]) < origin
        for probs in row["probabilities"].values():
            assert np.isclose(sum(probs), 1.0)
            assert all(0.0 < x < 1.0 for x in probs)
