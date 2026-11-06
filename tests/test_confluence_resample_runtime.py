"""Completed-bar runtime repair: same values/clocks without per-bucket Python."""
import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_series_equal

from engine.confluence_tiers import _completed_resample


def _accepted_reference(daily, rule):
    # Exact pre-repair ordinary calendar-rule path; a falsifier, not production code.
    last_obs = daily.index.max()
    raw = daily.resample(rule).last().dropna()
    raw = raw[raw.index <= last_obs]
    known = (daily.resample(rule).apply(lambda x: x.dropna().index.max())
             .reindex(raw.index).dropna())
    raw = raw.reindex(known.index)
    return raw, pd.Series(pd.to_datetime(known.values), index=known.index)


def _prices(shape, tz):
    index = pd.bdate_range("2017-01-03", "2026-09-16", tz=tz, name="session")
    daily = pd.Series(80 + np.sin(np.arange(len(index)) * .17) * 9,
                      index=index, name="close")
    if shape == "holes":
        daily.iloc[::7] = np.nan
        daily.iloc[-3:] = np.nan
        daily.loc["2022-03-01":"2022-06-30"] = np.nan
    elif shape == "unsorted":
        daily = daily.iloc[::-1]
    elif shape == "duplicates":
        daily = pd.concat([daily, daily.iloc[20:24].mul(1.1)]).sort_index(kind="stable")
    elif shape == "all_null":
        daily[:] = np.nan
    elif shape == "empty":
        daily = daily.iloc[:0]
    elif shape == "partial_tail":
        daily = daily.loc[:"2026-09-14"]
    elif shape == "only_open_bucket":
        daily = daily.loc["2026-09-15":"2026-09-16"]
    return daily


@pytest.mark.parametrize("rule", ("W-FRI", "ME"))
@pytest.mark.parametrize("tz", (None, "America/New_York", "Asia/Hong_Kong"))
@pytest.mark.parametrize("shape", ("clean", "holes", "unsorted", "duplicates",
                                  "all_null", "empty", "partial_tail", "only_open_bucket"))
def test_completed_bars_preserve_exact_accepted_values_and_knowledge_dates(rule, tz, shape):
    daily = _prices(shape, tz)
    frozen = daily.copy(deep=True)
    expected = _accepted_reference(daily, rule)
    actual = _completed_resample(daily, rule)
    for got, want in zip(actual, expected):
        assert_series_equal(got, want, check_exact=True)
    assert_series_equal(daily, frozen, check_exact=True)


@pytest.mark.parametrize("rule", ("W-FRI", "ME"))
def test_completed_bar_known_dates_do_not_execute_a_python_callback_per_bucket(monkeypatch, rule):
    daily = _prices("holes", None)
    expected = _accepted_reference(daily, rule)
    cls = type(daily.resample(rule))
    original = cls.apply
    calls = []

    def observed(self, function, *args, **kwargs):
        calls.append(function)
        return original(self, function, *args, **kwargs)

    monkeypatch.setattr(cls, "apply", observed)
    actual = _completed_resample(daily, rule)
    for got, want in zip(actual, expected):
        assert_series_equal(got, want, check_exact=True)
    assert calls == [], "full-universe runtime must not scale in Python callbacks per bucket"
