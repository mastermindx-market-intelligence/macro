"""Prefix-causality and outcome-maturity regression baseline.

Acceptance A06, A07, A20 for the R2 timing repair
(research/CRYPTO_SCIENCE_R2_TIMING_REPAIR_RESULTS_2026-09-28.md on
fd8095012e91). Narrow lock of resampling/feature paths the impulse backtest
consumes and of its outcome labels. Not a new study, not a new threshold.

Existing assertions are called, not copied:
  tests/test_btc_signals.py::test_completed_three_day_closes_all_prefixes_and_invalid_bins
  tests/test_btc_signals.py::test_completed_three_day_closes_preserve_membership_and_completion_date
  tests/test_btc_signals.py::test_bottom_pressure_matches_every_recent_prefix_without_repainting
  tests/test_btc_impulse_radar.py::test_causal_z_is_leak_free
  tests/test_btc_impulse_radar.py::test_observations_are_prefix_invariant_with_full_source_history
  tests/test_btc_impulse_falsifier.py::test_labels_are_strictly_forward_provable_by_hand
  tests/test_btc_impulse_falsifier.py::test_labels_keep_tail_unknown_and_denominator_mature_only
  tests/test_btc_impulse_falsifier.py::test_labels_do_not_treat_three_observations_as_three_days_across_gaps
  tests/test_btc_impulse_falsifier.py::test_lift_and_permutation_have_no_evidence_when_no_outcome_matured

The backtest (engine/btc_impulse_radar_backtest.py validate) consumes close,
_labels, and radar.fire_series. fire_series consumes _causal_z. The R2
prefix repair's resamplers are _completed_three_day_closes (3D, left-closed,
epoch-anchored) and the weekly last() inside bottom_pressure. btc_inputs
intraday_vol_daily is the input-layer day resample; validate() does not call it.
"""
from __future__ import annotations

import inspect

import numpy as np
import pandas as pd

from engine import btc_impulse_radar as R
from engine import btc_impulse_radar_backtest as BT
from engine import btc_inputs
from engine import btc_signals as S
from tests.test_btc_impulse_radar import (
    _base_sig,
    _calm_ranges,
    _dvol,
    _neutral_sopr,
    _observations,
    _sopr,
)

SEED = 20261012


def _ohlc(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({
        "open": close,
        "high": close * 1.01,
        "low": close * 0.99,
        "close": close,
    })


def _finite_price(values) -> pd.Series:
    """True only for finite numbers. Booleans and missing are not prices."""
    num = pd.to_numeric(values, errors="coerce")
    return num.where(np.isfinite(num))


def test_cites_existing_prefix_and_maturity_assertions():
    """A06/A07. Re-run the repaired regular-path locks instead of restating them."""
    from tests.test_btc_impulse_falsifier import (
        test_labels_are_strictly_forward_provable_by_hand,
        test_labels_do_not_treat_three_observations_as_three_days_across_gaps,
        test_labels_keep_tail_unknown_and_denominator_mature_only,
        test_lift_and_permutation_have_no_evidence_when_no_outcome_matured,
    )
    from tests.test_btc_impulse_radar import (
        test_causal_z_is_leak_free,
        test_observations_are_prefix_invariant_with_full_source_history,
    )
    from tests.test_btc_signals import (
        test_bottom_pressure_matches_every_recent_prefix_without_repainting,
        test_completed_three_day_closes_all_prefixes_and_invalid_bins,
        test_completed_three_day_closes_preserve_membership_and_completion_date,
    )

    test_completed_three_day_closes_preserve_membership_and_completion_date()
    test_completed_three_day_closes_all_prefixes_and_invalid_bins()
    test_bottom_pressure_matches_every_recent_prefix_without_repainting()
    test_causal_z_is_leak_free()
    test_observations_are_prefix_invariant_with_full_source_history()
    test_labels_are_strictly_forward_provable_by_hand()
    test_labels_keep_tail_unknown_and_denominator_mature_only()
    test_labels_do_not_treat_three_observations_as_three_days_across_gaps()
    test_lift_and_permutation_have_no_evidence_when_no_outcome_matured()


def test_resampled_features_match_on_prefix_versus_extension():
    """A06. First N bars keep the same feature values when N+k bars are fed.

    Irregularities: a NaN hole on a Sunday week boundary, a dropped 3D bin
    edge (calendar gap), and the epoch-anchored 3D boundary itself. Pandas
    resample('3D', closed='left') anchors at 1970-01-01, so a midnight exactly
    on that edge opens the next bin and must not join the previous one.
    """
    rng = np.random.default_rng(SEED)
    idx = pd.date_range("2024-01-01", periods=84, freq="D")
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0004, 0.02, len(idx)))), index=idx)
    sundays = idx[idx.day_name() == "Sunday"]
    close.loc[sundays[1]] = np.nan
    epoch = pd.Timestamp("1970-01-01")
    edges = [d for d in idx if int((d - epoch).days) % 3 == 0]
    gap = next(d for d in edges if d > sundays[1] and d != sundays[1])
    close = close.drop(gap)
    px = _ohlc(close)

    full_bp = S.bottom_pressure(px)
    full_3d = S._completed_three_day_closes(close)
    cuts = sorted(set([12, 20, 27, len(close) // 2, len(close) - 7, len(close) - 1, len(close)]))
    for end in cuts:
        got_bp = S.bottom_pressure(px.iloc[:end])
        pd.testing.assert_series_equal(got_bp, full_bp.reindex(got_bp.index), check_freq=False)
        got_3d = S._completed_three_day_closes(close.iloc[:end])
        pd.testing.assert_series_equal(
            got_3d, full_3d.loc[: close.index[end - 1]], check_freq=False)

    # Hand boundary: 2024-01-01 is a 3D left edge (probe against this anchor).
    hand = pd.Series([10., 20., 30., 40., 50., 60., 70.],
                     index=pd.date_range("2024-01-01", periods=7))
    first = S._completed_three_day_closes(hand.iloc[:3])
    assert list(first.index) == [pd.Timestamp("2024-01-03")]
    assert first.iloc[0] == 30.0
    opened = S._completed_three_day_closes(hand.iloc[:4])
    assert opened.iloc[0] == 30.0
    assert pd.Timestamp("2024-01-04") not in opened.index or pd.isna(opened.get(pd.Timestamp("2024-01-04"), np.nan))
    # Jan 4 00:01 is not a daily bar. It must not be dropped into the prior bin.
    straddling = hand.iloc[:4].copy()
    straddling.index = list(hand.index[:3]) + [pd.Timestamp("2024-01-04 00:01")]
    try:
        S._completed_three_day_closes(straddling)
    except ValueError:
        pass
    else:
        raise AssertionError("A bar off the daily boundary must not enter a 3D bin")

    # Week boundary used by bottom_pressure: W, closed right, label right (Sunday).
    # Adding Sunday must not rewrite Monday-Saturday.
    bp_sat = S.bottom_pressure(_ohlc(hand.iloc[:6]))
    bp_sun = S.bottom_pressure(_ohlc(hand.iloc[:7]))
    pd.testing.assert_series_equal(bp_sat, bp_sun.iloc[:6], check_freq=False)
    holed = hand.copy()
    holed.iloc[6] = np.nan
    bp_hole = S.bottom_pressure(_ohlc(holed))
    pd.testing.assert_series_equal(bp_sat, bp_hole.iloc[:6], check_freq=False)

    # Feature path validate() actually calls: fire_series / _causal_z.
    sig = _base_sig(n=150)
    sig_idx = sig.index
    sig = sig.copy()
    sig.loc[sig_idx[60], "close"] = np.nan
    sig = sig.drop(sig_idx[40])
    dv = _dvol(sig_idx, _calm_ranges(len(sig_idx)))
    sp = _sopr(sig_idx, _neutral_sopr(len(sig_idx)))
    fires = _observations(sig, dv, sp)
    for end in (50, 90, 120, len(sig)):
        got = _observations(sig.iloc[:end], dv, sp)
        pd.testing.assert_frame_equal(got, fires.iloc[:end], check_freq=False)
    z = R._causal_z(sig["close"], 30)
    longer = pd.concat([sig["close"], pd.Series([sig["close"].iloc[-1] * 1.01],
                                                index=[sig.index[-1] + pd.Timedelta(days=1)])])
    pd.testing.assert_series_equal(
        z, R._causal_z(longer, 30).iloc[:-1], check_freq=False, check_names=False)

    # Input-layer day resample. A bar at midnight belongs to the new day.
    hours = pd.date_range("2026-01-05 22:00", periods=8, freq="h")
    hi = pd.Series([10, 11, 20, 12, 13, 14, 15, 16.], index=hours)
    lo = pd.Series([9, 10, 19, 11, 12, 13, 14, 15.], index=hours)
    hourly = pd.DataFrame({"high": hi, "low": lo})
    assert hours[2] == pd.Timestamp("2026-01-06 00:00")
    vol = btc_inputs.intraday_vol_daily(hourly)
    pre = btc_inputs.intraday_vol_daily(hourly.iloc[:2])
    pd.testing.assert_series_equal(pre, vol.loc[pre.index])
    gapped = hourly.drop(hours[5])
    pd.testing.assert_series_equal(
        btc_inputs.intraday_vol_daily(gapped).loc[pre.index], pre)
    nan_hole = hourly.copy()
    nan_hole.loc[hours[4], "high"] = np.nan
    pd.testing.assert_series_equal(
        btc_inputs.intraday_vol_daily(nan_hole).loc[pre.index], pre)
    future = pd.concat([
        hourly,
        pd.DataFrame({"high": [40.], "low": [39.]}, index=[pd.Timestamp("2099-01-01 01:00")]),
    ])
    extended = btc_inputs.intraday_vol_daily(future)
    pd.testing.assert_series_equal(extended.loc[vol.index], vol)


def test_immature_and_same_bar_dual_barrier_stay_unknown():
    """A07. Exact sentinel is pandas.NA on dtype boolean, never False.

    _labels is close-only (engine/btc_impulse_radar_backtest.py). It has no
    high/low and no first-touch clock, so a bar whose wick could have printed
    both barriers has no knowable intrabar order. An incomplete forward window
    stays NA even after both close-thresholds have already printed on different
    bars. A finished window that meets both close thresholds is True and True:
    two close events, not a same-bar winner.
    """
    assert list(inspect.signature(BT._labels).parameters) == ["close"]
    assert BT.LABEL_H == 3 and BT.LABEL_THR == 0.05

    both_early = pd.Series([100.0, 90.0, 110.0], index=pd.date_range("2026-06-01", periods=3))
    down, up = BT._labels(both_early)
    assert str(down.dtype) == "boolean" and str(up.dtype) == "boolean"
    for series in (down, up):
        assert series.isna().all()
        assert all(v is pd.NA for v in series.tolist())
        assert all(v is not False and v is not True for v in series.tolist())

    # One future bar. Close sits inside the band; high=110 and low=90 are not
    # inputs. Order of those wick touches is unknown, and the horizon is short,
    # so the label stays NA rather than False.
    one_bar = pd.Series([100.0, 100.0], index=pd.date_range("2026-06-10", periods=2))
    down, up = BT._labels(one_bar)
    assert down.iloc[0] is pd.NA and up.iloc[0] is pd.NA
    assert down.iloc[0] is not False and up.iloc[0] is not False

    finished = pd.Series([100.0, 90.0, 110.0, 100.0],
                         index=pd.date_range("2026-06-01", periods=4))
    down, up = BT._labels(finished)
    assert down.iloc[0] == True and up.iloc[0] == True  # noqa: E712 — exact boolean
    assert down.iloc[1] is pd.NA and up.iloc[1] is pd.NA

    # Mature close path that never leaves the band. Exact value is False.
    # That is the close rule, not a claim that an unseen wick was ordered.
    flat = pd.Series([100.0, 100.0, 100.0, 100.0], index=pd.date_range("2026-07-01", periods=4))
    down, up = BT._labels(flat)
    assert down.iloc[0] == False and up.iloc[0] == False  # noqa: E712


def test_lift_skips_unknown_instead_of_counting_a_negative():
    """A07. Downstream _lift / _perm_p drop NA labels. fillna(False) would count them."""
    close = pd.Series([100., 100., 100., 94., 94., 94., 94., 94.],
                      index=pd.date_range("2026-08-01", periods=8))
    down, _up = BT._labels(close)
    assert down.iloc[:5].tolist() == [True, True, True, False, False]
    assert all(v is pd.NA for v in down.iloc[5:].tolist())
    fire = pd.Series([False, False, False, False, False, True, True, True], index=close.index)
    mask = pd.Series(True, index=close.index)
    base, lift, n = BT._lift(fire, down, mask)
    assert n == 0 and np.isnan(lift) and np.isclose(base, 0.6)
    assert np.isnan(BT._perm_p(fire, down, mask, 1.0, np.random.default_rng(SEED)))
    coerced = down.fillna(False)
    base_c, _lift_c, n_c = BT._lift(fire, coerced, mask)
    assert n_c == 3
    assert not np.isclose(base_c, base)


def test_garbage_prices_do_not_become_observations_or_rewrite_the_prefix():
    """A20. Boolean and non-finite values are not prices. Rows after the cutoff
    do not change feature values on the already-built prefix.

    A boolean True must not become 1.0 via to_numeric / astype(float). An
    unfinished horizon must stay NA when the only new row is boolean, non-finite,
    or dated off the three-day calendar.
    """
    flags = pd.Series([True, True, True], index=pd.date_range("2026-01-01", periods=3))
    got = S._completed_three_day_closes(flags)
    assert not np.isfinite(_finite_price(got)).any()

    mixed = pd.Series([100.0, True, 102.0, 103.0, 104.0, 105.0],
                      index=pd.date_range("2024-01-01", periods=6), dtype=object)
    got = S._completed_three_day_closes(mixed)
    assert pd.isna(got.iloc[0])
    assert not np.isfinite(_finite_price(got).fillna(np.nan)).iloc[0]

    idx = pd.date_range("2026-05-01", periods=6)
    base = pd.Series(100.0, index=idx)
    d0, u0 = BT._labels(base)
    assert d0.iloc[:3].tolist() == [False, False, False]
    assert all(v is pd.NA for v in d0.iloc[3:].tolist())

    def _extend(value, stamp):
        stamps = idx.append(pd.DatetimeIndex([stamp]))
        return pd.Series(list(base.astype(object).tolist()) + [value], index=stamps, dtype=object)

    for value, stamp in (
        (True, idx[-1] + pd.Timedelta(days=1)),
        (False, idx[-1] + pd.Timedelta(days=1)),
        (np.inf, idx[-1] + pd.Timedelta(days=1)),
        (-np.inf, idx[-1] + pd.Timedelta(days=1)),
        (np.nan, idx[-1] + pd.Timedelta(days=1)),
        (80.0, pd.Timestamp("2099-01-01")),
    ):
        d1, u1 = BT._labels(_extend(value, stamp))
        past_d = d1.iloc[: len(base)]
        past_u = u1.iloc[: len(base)]
        pd.testing.assert_series_equal(past_d[d0.notna()], d0[d0.notna()], check_freq=False)
        pd.testing.assert_series_equal(past_u[u0.notna()], u0[u0.notna()], check_freq=False)
        assert past_d[d0.isna()].isna().all()
        assert past_u[u0.isna()].isna().all()

    rng = np.random.default_rng(SEED)
    ix = pd.date_range("2024-03-01", periods=48, freq="D")
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0, 0.015, len(ix)))), index=ix)
    px = _ohlc(close)
    bp = S.bottom_pressure(px)
    td = S._completed_three_day_closes(close)
    for value, stamp in (
        (True, ix[-1] + pd.Timedelta(days=1)),
        (np.inf, ix[-1] + pd.Timedelta(days=1)),
        (np.nan, ix[-1] + pd.Timedelta(days=1)),
        (50.0, pd.Timestamp("2099-06-01")),
    ):
        ext_idx = ix.append(pd.DatetimeIndex([stamp]))
        cols = {}
        for name in px.columns:
            cols[name] = pd.Series(list(px[name].astype(object).tolist()) + [value],
                                   index=ext_idx, dtype=object)
        ext = pd.DataFrame(cols)
        got_bp = S.bottom_pressure(ext)
        pd.testing.assert_series_equal(bp, got_bp.iloc[: len(bp)], check_freq=False, check_names=False)
        got_td = S._completed_three_day_closes(ext["close"])
        pd.testing.assert_series_equal(
            td, got_td.loc[td.index], check_freq=False, check_names=False)
        fresh = got_td.loc[~got_td.index.isin(td.index)]
        if value is True or (isinstance(value, float) and not np.isfinite(value)):
            assert not np.isfinite(_finite_price(fresh)).any()


def test_backtest_has_no_fitted_scaler():
    """A20. btc_impulse_radar_backtest fits no scaler. The normaliser validate()
    reaches is radar._causal_z: trailing mean/std ending at t-1, so the fit
    window is rows strictly before t. Absence is the backtest source itself.
    """
    src = inspect.getsource(BT)
    for token in ("StandardScaler", "MinMaxScaler", "RobustScaler", "fit_transform", ".fit("):
        assert token not in src, token
    assert not any("scaler" in name.lower() for name in dir(BT))

    rng = np.random.default_rng(SEED)
    s = pd.Series(rng.normal(0, 1, 90), index=pd.date_range("2024-01-01", periods=90))
    s.iloc[40] = np.nan
    z = R._causal_z(s, 30)
    mu = s.rolling(30).mean().shift(1)
    sd = s.rolling(30).std().shift(1)
    pd.testing.assert_series_equal(z, (s - mu) / sd.replace(0.0, np.nan))
    # Moments at t do not include s[t] and do not include a row appended after t.
    cutoff = 70
    prefix = s.iloc[:cutoff]
    z_prefix = R._causal_z(prefix, 30)
    # A boolean is not fed as 1.0. Non-finite suffix rows stay out of the prefix fit.
    numeric_ext = pd.concat([prefix, pd.Series([1e6, np.inf, np.nan], index=[
        prefix.index[-1] + pd.Timedelta(days=1),
        prefix.index[-1] + pd.Timedelta(days=2),
        prefix.index[-1] + pd.Timedelta(days=3),
    ])])
    pd.testing.assert_series_equal(
        z_prefix, R._causal_z(numeric_ext, 30).iloc[:cutoff], check_freq=False)
    assert np.allclose(
        z_prefix.iloc[cutoff - 1], z.iloc[cutoff - 1], equal_nan=True)


def test_intraday_prior_day_survives_a_later_nonfinite_bar():
    """A20 input resample. A later non-finite hour must not rewrite the prior day.

    Boolean hours crash intraday_vol_daily today (bool division). That defect is
    in engine/btc_inputs.py, which this lane does not edit; see
    research/crypto_science/patches/cx-t05-20261012__btc_inputs.py.patch.
    """
    hours = pd.date_range("2026-01-05 20:00", periods=8, freq="h")
    hi = pd.Series(np.linspace(11, 18, 8), index=hours)
    lo = hi - 1.0
    hourly = pd.DataFrame({"high": hi, "low": lo})
    base = btc_inputs.intraday_vol_daily(hourly)
    poisoned = hourly.copy()
    poisoned.loc[hours[-1], "high"] = np.inf
    got = btc_inputs.intraday_vol_daily(poisoned)
    pd.testing.assert_series_equal(got.iloc[:1], base.iloc[:1])
