"""Killing tests for MUT1C survivors on s1_decomposition and s1_infoleak.

SNI-local DRAFT contract consumers: identity strings are caller-supplied
opaque ids; this file never mints issuer or security identifiers. Fixtures
are synthetic. rank/gate/size/signal/escalation/trade authority stay false.
Each test_mut1c_* docstring names one non-equivalent surviving mutant.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/residual"),
)

from s1_decomposition import (  # noqa: E402
    MIN_OBS,
    beta_window_dates,
    daily_log_returns,
    decompose_unit,
    fit_ols,
    spec_hash,
    window_log_ret,
)
from s1_infoleak import STEP_TOLERANCE, detect, vintage_series  # noqa: E402


def _weekdays(n: int, start: date = date(2020, 1, 6)) -> list[date]:
    out: list[date] = []
    d = start
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


# --------------------------------------------------------------------------- #
# s1_decomposition
# --------------------------------------------------------------------------- #


def test_mut1c_s1_decomposition_decompose_unit_1():
    """s1_decomposition.py:152, `return row` -> `return None` (empty beta window)."""
    bars = [date(2020, 2, 3), date(2020, 2, 4)]
    closes = {bars[0]: 10.0, bars[1]: 11.0}
    row = decompose_unit(
        "M0", "US", 5, bars[0], date(2019, 12, 31), bars[0], bars[1],
        closes, bars, {}, {},
    )
    assert isinstance(row, dict)
    assert row["abstention"] == "ABSTAIN_INSUFFICIENT_HISTORY"


def test_mut1c_s1_decomposition_decompose_unit_2():
    """s1_decomposition.py:135, `subject_endpoint_fill__oc` False -> True."""
    bars = [date(2020, 2, 3), date(2020, 2, 4)]
    closes = {bars[0]: 10.0, bars[1]: 11.0}
    row = decompose_unit(
        "M0", "US", 5, bars[0], date(2019, 12, 31), bars[0], bars[1],
        closes, bars, {}, {},
    )
    assert row["subject_endpoint_fill__oc"] is False
    assert row["subject_endpoint_coverage__oc"] is False


def test_mut1c_s1_decomposition_fit_ols_1():
    """s1_decomposition.py:115, `np.ones((len(y), 1))` 1 -> 2 (empty X branch)."""
    y = np.asarray([1.0, 3.0, 5.0])
    X = np.zeros((3, 0))
    coef, resid = fit_ols(y, X)
    assert coef.shape == (1,)
    assert abs(float(coef[0]) - float(np.mean(y))) < 1e-12
    assert np.allclose(resid, y - coef[0])


def test_mut1c_s1_decomposition_fit_ols_2():
    """s1_decomposition.py:117, `resid = y - design @ coef` -> `y + design @ coef`."""
    y = np.asarray([1.0, 2.0, 4.0])
    X = np.asarray([[1.0], [2.0], [3.0]])
    coef, resid = fit_ols(y, X)
    design = np.column_stack([np.ones(len(X)), X])
    assert np.allclose(resid, y - design @ coef)
    assert not np.allclose(resid, y + design @ coef)


def test_mut1c_s1_decomposition_spec_hash_1():
    """s1_decomposition.py:64, `ensure_ascii=False` -> `True`."""
    sid = "SEC:SYN-\u03b1"
    got = spec_hash("M1", sid, ["SPY"], 5)
    spec = {
        "model": "M1",
        "subject_security_id": sid,
        "factors": ["SPY"],
        "window": 252,
        "min_obs": 200,
        "h": 5,
        "return": "log",
        "intercept": "excluded_from_common",
    }
    raw = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert got == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    escaped = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    assert got != hashlib.sha256(escaped.encode("utf-8")).hexdigest()


def test_mut1c_s1_decomposition_spec_hash_2():
    """s1_decomposition.py:64, `sort_keys=True` -> `False`."""
    sid = "SEC:SYN-00001"
    got = spec_hash("M1", sid, ["SPY"], 5)
    spec = {
        "model": "M1",
        "subject_security_id": sid,
        "factors": ["SPY"],
        "window": 252,
        "min_obs": 200,
        "h": 5,
        "return": "log",
        "intercept": "excluded_from_common",
    }
    raw_sorted = json.dumps(spec, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    raw_insert = json.dumps(spec, sort_keys=False, separators=(",", ":"), ensure_ascii=False)
    assert raw_sorted != raw_insert
    assert got == hashlib.sha256(raw_sorted.encode("utf-8")).hexdigest()


def test_mut1c_s1_decomposition_module_1():
    """s1_decomposition.py:25, `MIN_OBS = 200` -> `201`."""
    assert MIN_OBS == 200
    dates = _weekdays(201)
    closes = {d: 10.0 + 0.02 * i for i, d in enumerate(dates)}
    row = decompose_unit(
        "M0", "US", 5, dates[-1], dates[-1], dates[-1], dates[-1],
        closes, dates, {}, {},
    )
    assert row["n_obs__dc"] == 200
    assert row["abstention"] == "OK"


def test_mut1c_s1_decomposition_beta_window_dates_1():
    """s1_decomposition.py:106, `range(len(subject_dates) - 1)` 1 -> 2."""
    dates = [date(2020, 1, 6), date(2020, 1, 7), date(2020, 1, 8)]
    swapped = [dates[0], dates[2], dates[1]]
    with pytest.raises(ValueError, match="strictly increasing"):
        beta_window_dates(swapped, dates[2], window=5)


def test_mut1c_s1_decomposition_daily_log_returns_1():
    """s1_decomposition.py:80, `c <= 0` 0 -> 1 (positive close below 1 is valid)."""
    d0, d1 = date(2020, 1, 6), date(2020, 1, 7)
    closes = {d0: 0.5, d1: 1.0}
    got = daily_log_returns(closes, [d0, d1])
    assert d1 in got
    assert abs(got[d1] - math.log(1.0 / 0.5)) < 1e-12


def test_mut1c_s1_decomposition_window_log_ret_1():
    """s1_decomposition.py:95, `b <= 0` 0 -> 1 (positive coverage close below 1)."""
    fill, coverage = date(2020, 1, 6), date(2020, 1, 10)
    got = window_log_ret({fill: 2.0, coverage: 0.5}, fill, coverage)
    assert got is not None
    assert abs(got - math.log(0.5 / 2.0)) < 1e-12


def test_mut1c_s1_decomposition_window_log_ret_2():
    """s1_decomposition.py:95, `a <= 0` 0 -> 1 (positive fill close below 1)."""
    fill, coverage = date(2020, 1, 6), date(2020, 1, 10)
    got = window_log_ret({fill: 0.5, coverage: 2.0}, fill, coverage)
    assert got is not None
    assert abs(got - math.log(2.0 / 0.5)) < 1e-12


# --------------------------------------------------------------------------- #
# s1_infoleak
# --------------------------------------------------------------------------- #


def test_mut1c_s1_infoleak_module_1():
    """s1_infoleak.py:23, `STEP_TOLERANCE = 1e-6` -> `(1e-6*1.001)`."""
    assert STEP_TOLERANCE == 1e-6
    delta = 1.0005e-6
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [100.0, 100.0 * (1.0 + delta)], [100.0, 100.0])
    assert state == "OK"
    assert len(steps) == 1
    assert steps[0][0] == dates[1]


def test_mut1c_s1_infoleak_vintage_series_1():
    """s1_infoleak.py:41, `range(1, len(q))` 1 -> 2 (first adjacent pair is a step)."""
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [100.0, 105.0], [100.0, 100.0])
    assert state == "OK"
    assert len(steps) == 1
    assert steps[0][0] == dates[1]


def test_mut1c_s1_infoleak_vintage_series_2():
    """s1_infoleak.py:38, `len(q) < 2` 2 -> 3 (two usable bars are verifiable)."""
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [100.0, 101.0], [100.0, 101.0])
    assert state == "OK"
    assert steps == []


def test_mut1c_s1_infoleak_vintage_series_3():
    """s1_infoleak.py:40, `q[i]/q[i-1] - 1.0` -> `+ 1.0` (stored relative step)."""
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [100.0, 105.0], [50.0, 50.0])
    assert state == "OK"
    assert len(steps) == 1
    expected = abs((105.0 / 50.0) / (100.0 / 50.0) - 1.0)
    assert abs(steps[0][1] - expected) < 1e-12


def test_mut1c_s1_infoleak_vintage_series_4():
    """s1_infoleak.py:40, stored `1.0` -> `(1.0*1.001)`."""
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [100.0, 105.0], [50.0, 50.0])
    assert state == "OK"
    assert len(steps) == 1
    expected = abs(2.1 / 2.0 - 1.0)
    assert abs(steps[0][1] - expected) < 1e-12


def test_mut1c_s1_infoleak_vintage_series_5():
    """s1_infoleak.py:38, `len(q) < 2` -> `len(q) <= 2`."""
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [80.0, 80.0], [80.0, 80.0])
    assert state == "OK"
    assert steps == []


def test_mut1c_s1_infoleak_vintage_series_6():
    """s1_infoleak.py:34, `cp != cp or c != c` -> `and` (NaN close still skipped)."""
    dates = [date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)]
    close = [100.0, float("nan"), 105.0]
    cp = [100.0, 100.0, 100.0]
    steps, state = vintage_series(dates, close, cp)
    assert state == "OK"
    assert len(steps) == 1
    assert steps[0][0] == dates[2]


def test_mut1c_s1_infoleak_vintage_series_7():
    """s1_infoleak.py:34, `cp <= 0` 0 -> 1 (raw close in (0, 1] is usable)."""
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [0.5, 0.5], [0.5, 0.5])
    assert state == "OK"
    assert steps == []


def test_mut1c_s1_infoleak_vintage_series_8():
    """s1_infoleak.py:40, `q[i] / q[i-1]` -> `q[i] * q[i-1]` (stored relative step)."""
    dates = [date(2024, 1, 2), date(2024, 1, 3)]
    steps, state = vintage_series(dates, [100.0, 105.0], [50.0, 50.0])
    assert state == "OK"
    assert len(steps) == 1
    expected = abs(2.1 / 2.0 - 1.0)
    assert abs(steps[0][1] - 0.05) < 1e-12
    assert abs(steps[0][1] - expected) < 1e-12


def test_mut1c_s1_infoleak_detect_1():
    """s1_infoleak.py:52, `d <= last_bar` -> `d < last_bar`."""
    step_d = date(2024, 6, 13)
    hit = detect([(step_d, 0.05)], "OK", date(2024, 1, 2), step_d)
    assert hit is not None
    assert hit["first_offending_date"] == "2024-06-13"
    assert hit["count_of_steps_in_window"] == 1


def test_mut1c_s1_infoleak_detect_2():
    """s1_infoleak.py:52, `earliest_tune_anchor <= d` -> `earliest_tune_anchor < d`."""
    step_d = date(2024, 6, 13)
    hit = detect([(step_d, 0.05)], "OK", step_d, date(2024, 12, 31))
    assert hit is not None
    assert hit["first_offending_date"] == "2024-06-13"
