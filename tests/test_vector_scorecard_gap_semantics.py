"""Vector scorecard: a missing allocation is withheld, never a silent zero position.

Synthetic series only. Three tests carry a strict marker and fail until
research/crypto_science/patches/cx-r15fix-20261012__build_vector.py.patch
is applied. The all-present identity test has no marker: it must pass on the
unpatched one-liner and on the patched functions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.build_vector import alloc_equity, scorecard

# Keys the unpatched scorecard returns. withheld_days is the patched addition.
_KEYS = (
    "cagr", "sharpe", "sortino", "maxdd", "in_market",
    "hodl_cagr", "hodl_sharpe", "hodl_maxdd", "x_hodl",
)

def _close(n=8) -> pd.Series:
    idx = pd.bdate_range("2024-01-02", periods=n)
    # Modest moves so strategy equity stays positive and every metric is finite.
    return pd.Series(
        [100, 102, 99, 104, 101, 108, 103, 112][:n],
        index=idx,
        dtype="float64",
    )


def _unpatched_equity(close: pd.Series, alloc: pd.Series) -> pd.Series:
    ret = close.pct_change().fillna(0)
    pos = alloc.shift(1).reindex(ret.index).ffill().fillna(0)
    return (1 + pos * ret).cumprod()


def _unpatched_scorecard(close: pd.Series, alloc: pd.Series) -> dict:
    ret = close.pct_change().fillna(0)
    pos = alloc.shift(1).reindex(ret.index).ffill().fillna(0)
    strat = pos * ret
    yrs = (close.index[-1] - close.index[0]).days / 365.25
    eq = (1 + strat).cumprod()
    hodl = (1 + ret).cumprod()

    def cagr(e):
        return (e.iloc[-1]) ** (1 / yrs) - 1 if yrs and e.iloc[-1] > 0 else float("nan")

    def shp(r):
        return r.mean() / r.std() * np.sqrt(365) if r.std() else float("nan")

    def srt(r):
        dn = r[r < 0].std()
        return r.mean() / dn * np.sqrt(365) if dn else float("nan")

    def mdd(e):
        return float((e / e.cummax() - 1).min())

    return {
        "cagr": round(100 * cagr(eq)), "sharpe": round(shp(strat), 2),
        "sortino": round(srt(strat), 2), "maxdd": round(100 * mdd(eq)),
        "in_market": round(100 * (pos > 0).mean()),
        "hodl_cagr": round(100 * cagr(hodl)), "hodl_sharpe": round(shp(ret), 2),
        "hodl_maxdd": round(100 * mdd(hodl)), "x_hodl": round(eq.iloc[-1] / hodl.iloc[-1], 2),
    }


def _metric_equal(got, ref) -> bool:
    if type(got) is not type(ref):
        return False
    if pd.isna(got) and pd.isna(ref):
        return True
    return got == ref


def _gapped_alloc(close: pd.Series) -> pd.Series:
    """Three leading missing prints, then a real path with one internal hole.

    The internal hole must be carried by ffill, not counted as withheld.
    """
    alloc = pd.Series([1.0, 0.0, np.nan, 1.0, 0.5], index=close.index[3:], dtype="float64")
    return alloc.reindex(close.index)


@pytest.mark.xfail(strict=True, reason="cx-r15fix patch not applied yet — remove this marker in the commit that applies research/crypto_science/patches/cx-r15fix-20261012__build_vector.py.patch")
def test_leading_gap_is_excluded_not_counted_as_zero_return_days():
    close = _close()
    alloc = _gapped_alloc(close)
    trimmed_close = close.iloc[3:]
    trimmed_alloc = alloc.iloc[3:]
    card = scorecard(close, alloc)
    ref = _unpatched_scorecard(trimmed_close, trimmed_alloc)
    for key in _KEYS:
        assert _metric_equal(card[key], ref[key]), (key, card[key], ref[key])
    # The unpatched full-series formula counts the leading gap as flat days.
    full = _unpatched_scorecard(close, alloc)
    assert card["in_market"] != full["in_market"]
    eq = alloc_equity(close, alloc)
    assert eq.iloc[:3].isna().all()
    pd.testing.assert_series_equal(
        eq.iloc[3:], _unpatched_equity(trimmed_close, trimmed_alloc),
        check_freq=False, check_names=False,
    )
    flat = _unpatched_equity(close, alloc)
    assert flat.iloc[:3].notna().all()
    assert bool((eq.iloc[:3].fillna(0) != flat.iloc[:3]).all())


def test_all_present_series_matches_unpatched_formula():
    close = _close()
    alloc = pd.Series([0.0, 0.25, 0.5, 1.0, 0.0, 0.75, 1.0, 0.5], index=close.index, dtype="float64")
    assert alloc.notna().all()
    eq = alloc_equity(close, alloc)
    pd.testing.assert_series_equal(eq, _unpatched_equity(close, alloc))
    card = scorecard(close, alloc)
    ref = _unpatched_scorecard(close, alloc)
    for key, value in ref.items():
        assert _metric_equal(card[key], value), (key, card[key], value)
    assert set(ref) <= set(card)
    # Present only after the patch. Must be zero: nothing was withheld.
    if "withheld_days" in card:
        assert card["withheld_days"] == 0


@pytest.mark.xfail(strict=True, reason="cx-r15fix patch not applied yet — remove this marker in the commit that applies research/crypto_science/patches/cx-r15fix-20261012__build_vector.py.patch")
def test_withheld_days_equals_leading_missing_rows_not_ffill_holes():
    close = _close()
    alloc = _gapped_alloc(close)
    assert int(alloc.isna().sum()) == 4  # 3 leading + 1 internal hole
    card = scorecard(close, alloc)
    assert card["withheld_days"] == 3
    assert card["withheld_days"] == int(alloc_equity(close, alloc).isna().sum())


@pytest.mark.xfail(strict=True, reason="cx-r15fix patch not applied yet — remove this marker in the commit that applies research/crypto_science/patches/cx-r15fix-20261012__build_vector.py.patch")
def test_all_null_allocation_does_not_fabricate_zero_metrics():
    close = _close()
    alloc = pd.Series(np.nan, index=close.index, dtype="float64")
    card = scorecard(close, alloc)
    assert card["withheld_days"] == len(close)
    for key in _KEYS:
        assert pd.isna(card[key]), key
        assert card[key] != 0
    eq = alloc_equity(close, alloc)
    assert len(eq) == len(close)
    assert eq.isna().all()
