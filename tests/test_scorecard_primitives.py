"""Phase A signal-quality scorecard primitives in engine/validation.py:
rank IC, Newey-West (HAC) t-stat, IC summary, Benjamini-Hochberg FDR. These rank
signals on one comparable scale and keep the significance honest under overlapping
windows (HAC) and many-signal screening (FDR). Pure numpy/pandas — no network.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engine.validation import (benjamini_hochberg, ic_summary, newey_west_tstat,
                               rank_ic)


def test_rank_ic_sign_and_range():
    rng = np.random.default_rng(0)
    f = pd.Series(rng.normal(size=200))
    assert rank_ic(f, f) == 1.0                      # perfect monotone
    assert rank_ic(-f, f) == -1.0                    # perfectly inverted
    assert abs(rank_ic(pd.Series(rng.normal(size=200)), f)) < 0.25  # noise ~ 0


def test_rank_ic_thin_overlap_is_nan():
    assert np.isnan(rank_ic(pd.Series([1, 2, 3]), pd.Series([3, 2, 1])))  # <10 joint


def test_rank_ic_min_names_keyword_default_is_byte_compatible():
    sig = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9])
    fwd = pd.Series([9, 8, 7, 6, 5, 4, 3, 2, 1])
    assert np.isnan(rank_ic(sig, fwd))
    assert np.isnan(rank_ic(sig, fwd, min_names=10))
    two = rank_ic(pd.Series([1, 2]), pd.Series([2, 1]), min_names=2)
    assert abs(two + 1.0) < 1e-12


def test_newey_west_inflates_se_under_autocorrelation():
    rng = np.random.default_rng(1)
    raw = rng.normal(0.05, 1.0, 400)
    smooth = pd.Series(np.convolve(raw, np.ones(5) / 5, "same"))   # positive autocorrelation
    nw = newey_west_tstat(smooth, lags=8)
    plain_se = smooth.std(ddof=0) / np.sqrt(len(smooth))
    assert nw["se"] > plain_se                       # HAC se must exceed the naive se
    assert 0.0 <= nw["p"] <= 1.0


def test_newey_west_unrounded_keyword_default_is_byte_compatible():
    x = pd.Series([0.10, 0.11, 0.09, 0.12, 0.08, 0.10, 0.13, 0.07, 0.11, 0.09])
    rounded = newey_west_tstat(x, lags=4)
    explicit = newey_west_tstat(x, lags=4, unrounded=False)
    assert rounded == explicit
    raw = newey_west_tstat(x, lags=4, unrounded=True)
    assert raw["n"] == rounded["n"]
    assert raw["lags"] == rounded["lags"]
    assert rounded["mean"] == round(raw["mean"], 5)
    assert rounded["se"] == round(raw["se"], 5)
    assert rounded["t"] == round(raw["t"], 3)
    assert rounded["p"] == round(raw["p"], 4)


def test_ic_summary_fields_and_annualization():
    rng = np.random.default_rng(2)
    ics = pd.Series(rng.normal(0.03, 0.08, 40))
    s = ic_summary(ics, periods_per_year=4)
    assert s["n"] == 40 and -1 <= s["mean_ic"] <= 1
    # annualized IC-IR = IC-IR * sqrt(periods)
    assert abs(s["ic_ir_ann"] - s["ic_ir"] * 2.0) < 1e-6
    assert s["t_hac"] is not None


def test_ic_summary_too_short():
    assert ic_summary(pd.Series([0.1, 0.2, 0.3]))["n"] == 3
    assert "mean_ic" not in ic_summary(pd.Series([0.1, 0.2, 0.3]))


def test_benjamini_hochberg_controls_panel():
    bh = benjamini_hochberg({"a": 0.001, "b": 0.4, "c": 0.5, "d": 0.6, "e": 0.8}, alpha=0.10)
    assert bh["a"]["reject"] is True                 # the one genuine signal
    assert all(not bh[k]["reject"] for k in ("b", "c", "d", "e"))
    # q-values are monotone-capped and >= the raw p
    assert bh["a"]["q"] >= 0.001 and bh["e"]["q"] <= 1.0


def test_benjamini_hochberg_empty():
    assert benjamini_hochberg({}) == {}
    assert benjamini_hochberg({"a": None, "b": float("nan")}) == {}
