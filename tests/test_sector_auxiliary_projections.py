"""Literal-owner parity for captured aggregate breadth and earnings projections."""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engine import basket_score, theme_scoring
from lib import config
from tests.fixtures import base_market_concentration_84f1b72 as old_breadth
from tests.fixtures import base_earnings_calendar_84f1b72 as old_earnings

DAY = date(2026, 11, 3)


def tape(count=30):
    return pd.DataFrame({"adv": np.arange(count) + 230, "dec": np.arange(count) + 200,
        "pct_above_50": np.arange(count) * .2 + 50, "pct_above_200": np.arange(count) * .1 + 55,
        "nh": np.arange(count) + 5, "nl": np.arange(count) + 3},
        index=pd.bdate_range(end=DAY, periods=count))


def observe(call):
    try:
        return "value", call()
    except Exception as exc:
        return "exception", type(exc), str(exc)


def earnings(vintage=None):
    return pd.DataFrame({"as_of": [vintage or DAY.isoformat()] * 3,
                         "next_date": ["2026-11-04", None, "2026-11-06T15:00:00Z"]},
                        index=["abc", "DEF", "ghi"])


def legacy_earnings(frame, owner, tmp_path, monkeypatch, panel=None):
    path = tmp_path / "earnings" / "earnings.parquet"
    path.parent.mkdir(exist_ok=True)
    path.touch()
    with monkeypatch.context() as mp:
        mp.setattr(config, "data_dir", lambda: tmp_path)
        mp.setattr(pd, "read_parquet", lambda path: frame.copy(deep=True))
        return owner._acquire_earnings_calendar(
            {"idx": pd.DatetimeIndex([pd.Timestamp(DAY)])} if panel is None else panel)


@pytest.mark.parametrize("count", [0, 1, 2, 3, 5, 20, 21, 35])
def test_daily_and_original_row_windows_match_literal_owner(count, tmp_path, monkeypatch):
    frame = tape(count)
    before = frame.copy(deep=True)
    with monkeypatch.context() as mp:
        mp.setattr(config, "data_dir", lambda: tmp_path)
        mp.setattr(pd, "read_parquet", lambda path: frame)
        expected = old_breadth.market_concentration()
        actual = basket_score.market_concentration()
    assert actual == expected == basket_score.market_concentration_from_inputs(frame)
    pd.testing.assert_frame_equal(frame, before)


@pytest.mark.parametrize("case", ["zero_dec", "negative_dec", "broad", "narrow", "missing_adv", "nan_adv",
                                  "missing_optional", "negative_window", "missing_dec"])
def test_original_breadth_edges_and_present_failure_semantics(case, tmp_path, monkeypatch):
    frame = tape()
    if case == "zero_dec":
        frame["dec"] = 0
    elif case == "negative_dec":
        frame["dec"] = -10
    elif case == "broad":
        frame["adv"], frame["pct_above_50"] = 400, 70
    elif case == "narrow":
        frame["adv"], frame["pct_above_50"] = 100, 20
    elif case == "missing_adv":
        frame = frame.drop(columns="adv")
    elif case == "nan_adv":
        frame.iloc[-1, frame.columns.get_loc("adv")] = np.nan
    elif case == "missing_optional":
        frame = frame.drop(columns=["nh", "pct_above_200"])
    elif case == "negative_window":
        frame.iloc[:-1, frame.columns.get_loc("dec")] = -1000
    else:
        frame = frame.drop(columns="dec")
    with monkeypatch.context() as mp:
        mp.setattr(config, "data_dir", lambda: tmp_path)
        mp.setattr(pd, "read_parquet", lambda path: frame)
        original = observe(old_breadth.market_concentration)
        legacy = observe(basket_score.market_concentration)
    assert legacy == original == observe(lambda: basket_score.market_concentration_from_inputs(frame))


@pytest.mark.parametrize("region,folder", [("us", "breadth"), ("hk", "hk_breadth"), ("china", "china_breadth"),
                                          ("canada", "canada_breadth"), ("intl", "intl_breadth"), ("unknown", "breadth")])
def test_legacy_region_acquisition_path_unchanged(region, folder, tmp_path, monkeypatch):
    paths = []
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(pd, "read_parquet", lambda path: paths.append(path) or tape())
    assert basket_score.market_concentration(region) == old_breadth.market_concentration(region)
    assert paths == [tmp_path / folder / "breadth.parquet"] * 2


@pytest.mark.parametrize("days", [-2, 0, 1, 13, 14, 15, 40])
def test_earnings_original_fourteen_calendar_day_rule(days, tmp_path, monkeypatch):
    frame = earnings((DAY - timedelta(days=days)).isoformat())
    expected = legacy_earnings(frame, old_earnings, tmp_path, monkeypatch)
    assert legacy_earnings(frame, theme_scoring, tmp_path, monkeypatch) == expected
    assert theme_scoring.earnings_calendar_from_inputs(frame, panel_session=DAY) == expected
    assert bool(expected) == (days <= 14)  # Preserve incumbent treatment of future dated vintages.


@pytest.mark.parametrize("case", ["timezone", "invalid_asof", "empty_asof", "no_asof", "duplicate",
                                  "nan_date", "pdna_date", "empty", "bad_next_date"])
def test_earnings_projection_and_whole_calendar_failure_parity(case, tmp_path, monkeypatch):
    frame = earnings()
    if case == "timezone":
        frame["as_of"] = "2026-10-20T23:30:00-04:00"
    elif case == "invalid_asof":
        frame["as_of"] = "not-an-absolute-date"
    elif case == "empty_asof":
        frame["as_of"] = None
    elif case == "no_asof":
        frame = frame.drop(columns="as_of")
    elif case == "duplicate":
        frame.index = ["abc", "ABC", "abc"]
    elif case == "nan_date":
        frame["next_date"] = ["nan", np.nan, "None"]
    elif case == "pdna_date":
        frame["next_date"] = ["2026-11-04", pd.NA, "2026-11-06"]
    elif case == "empty":
        frame = frame.iloc[:0]
    else:
        frame["next_date"] = [0, "", "not-a-date"]
    before = frame.copy(deep=True)
    expected = legacy_earnings(frame, old_earnings, tmp_path, monkeypatch)
    assert legacy_earnings(frame, theme_scoring, tmp_path, monkeypatch) == expected
    assert theme_scoring.earnings_calendar_from_inputs(frame, panel_session=DAY) == expected
    pd.testing.assert_frame_equal(frame, before)


def test_resolved_absence_and_relative_vintage_do_not_invoke_clock():
    assert basket_score.market_concentration_from_inputs(None) == {}
    assert theme_scoring.earnings_calendar_from_inputs(None, panel_session=DAY) == {}
    assert theme_scoring.earnings_calendar_from_inputs(earnings("today"), panel_session=DAY) == {}
    assert theme_scoring.earnings_calendar_from_inputs(earnings(), panel_session=None) == {}
    assert theme_scoring.earnings_calendar_from_inputs(earnings(), panel_session="today") == {}


def test_pure_projections_do_not_reach_ambient_read_or_relative_clock(monkeypatch):
    frame, earn = tape(), earnings()
    stamp = pd.Timestamp
    def forbidden(*args, **kwargs):
        raise AssertionError("ambient source reached")
    def absolute(value, *args, **kwargs):
        assert value is not None and value not in ("today", "now")
        return stamp(value, *args, **kwargs)
    with monkeypatch.context() as mp:
        mp.setattr(config, "data_dir", forbidden)
        mp.setattr(pd, "read_parquet", forbidden)
        mp.setattr(Path, "read_text", forbidden)
        mp.setattr(pd, "Timestamp", absolute)
        assert basket_score.market_concentration_from_inputs(frame)["ad_m"] > 0
        assert theme_scoring.earnings_calendar_from_inputs(earn, panel_session=DAY)["ABC"] == "2026-11-04"


def test_invalid_panel_still_precedes_legacy_earnings_path_acquisition(monkeypatch):
    calls = []
    monkeypatch.setattr(config, "data_dir", lambda: calls.append("data_dir") or Path("/unused"))
    assert theme_scoring._acquire_earnings_calendar({}) == old_earnings._acquire_earnings_calendar({}) == {}
    assert calls == []


def test_legacy_read_failure_remains_optional(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OSError("fixture-only missing source")
    monkeypatch.setattr(config, "data_dir", unavailable)
    assert basket_score.market_concentration() == old_breadth.market_concentration() == {}
    panel = {"idx": pd.DatetimeIndex([pd.Timestamp(DAY)])}
    assert theme_scoring._acquire_earnings_calendar(panel) == old_earnings._acquire_earnings_calendar(panel) == {}
