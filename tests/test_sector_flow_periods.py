"""Sector board windows use shared dates, never last-good replacements."""
from __future__ import annotations

import json
import random

import numpy as np
import pandas as pd
import pytest

from collectors import sponsors
from lib import store


def _frame(a, b=None):
    if b is None:
        b = [0.0] * len(a)
    return pd.DataFrame(
        {"XLK_flow_mn": a, "XLF_flow_mn": b},
        index=pd.bdate_range("2026-11-02", periods=len(a)),
    )


def _board(monkeypatch, frame, periods=sponsors.FLOW_PERIODS):
    monkeypatch.setattr(sponsors, "flows_table", lambda: frame)
    return sponsors.sector_flow_periods(periods)


def _vals(result, ticker="XLK"):
    return next(row["vals"] for row in result["rows"] if row["ticker"] == ticker)


@pytest.mark.parametrize("frame", [None, pd.DataFrame(), _frame([None, None]) * np.nan])
def test_no_usable_flow_returns_none(monkeypatch, frame):
    assert _board(monkeypatch, frame) is None


def test_missing_latest_is_not_replaced_by_old_inflow(monkeypatch):
    result = _board(monkeypatch, _frame([100.0, None], [0.0, -50.0]))
    assert result["asof"] == "2026-11-03"
    assert _vals(result)["1D"] is None
    assert _vals(result, "XLF")["1D"] == -50.0
    assert result["net"]["1D"] is None


def test_interior_gap_does_not_pull_an_older_row_into_window(monkeypatch):
    result = _board(monkeypatch, _frame([100.0, 2.0, None, 4.0]))
    assert _vals(result)["1D"] == 4.0
    assert _vals(result)["3D"] is None
    assert result["net"]["3D"] is None


def test_gap_outside_window_does_not_poison_current_values(monkeypatch):
    result = _board(monkeypatch, _frame([None, 2.0, 3.0, 4.0]))
    assert _vals(result)["3D"] == 9.0
    assert result["net"]["3D"] == 9.0


def test_wholly_missing_latest_date_is_retained(monkeypatch):
    result = _board(monkeypatch, _frame([10.0, None], [-5.0, None]))
    assert result["asof"] == "2026-11-03"
    assert result["depth"] == 2
    assert all(value is None for value in result["net"].values())


def test_wholly_missing_interior_date_stays_in_window(monkeypatch):
    result = _board(monkeypatch, _frame([100.0, None, 2.0, 3.0], [0.0, None, 0.0, 0.0]))
    assert _vals(result)["1D"] == 3.0
    assert _vals(result)["3D"] is None
    assert result["depth"] == 4


def test_leading_diff_rows_only_are_excluded(monkeypatch):
    result = _board(monkeypatch, _frame([None, None, 2.0, 3.0], [None, None, 1.0, 1.0]))
    assert result["depth"] == 2
    assert _vals(result)["1M"] == 5.0
    assert result["net"]["1M"] == 7.0


def test_all_null_present_fund_is_not_omitted_from_net(monkeypatch):
    result = _board(monkeypatch, _frame([None, None], [2.0, 3.0]))
    assert len(result["rows"]) == 2
    assert _vals(result)["1D"] is None
    assert result["net"]["1D"] is None


@pytest.mark.parametrize("missing", [np.nan, np.inf, -np.inf, "unavailable"])
def test_nonfinite_and_invalid_cells_are_unavailable(monkeypatch, missing):
    result = _board(monkeypatch, _frame([100.0, missing], [0.0, -50.0]))
    assert _vals(result)["1D"] is None
    assert result["net"]["1D"] is None
    json.dumps(result, allow_nan=False)


def test_zero_is_measured_not_missing(monkeypatch):
    result = _board(monkeypatch, _frame([0.0, 0.0], [0.0, 0.0]))
    assert _vals(result)["1D"] == 0.0
    assert result["net"]["1M"] == 0.0


def test_opposing_signed_flows_can_cancel_to_zero(monkeypatch):
    result = _board(monkeypatch, _frame([100.0], [-100.0]))
    assert result["net"]["1D"] == 0.0


def test_unsorted_input_uses_chronological_windows(monkeypatch):
    frame = _frame([1.0, 2.0, 3.0, 4.0]).iloc[[3, 0, 2, 1]]
    result = _board(monkeypatch, frame)
    assert _vals(result)["1D"] == 4.0
    assert _vals(result)["3D"] == 9.0


def test_input_is_not_mutated(monkeypatch):
    frame = _frame([2.0, np.inf, 3.0]).iloc[::-1]
    before = frame.copy(deep=True)
    _board(monkeypatch, frame)
    pd.testing.assert_frame_equal(frame, before)


def test_custom_windows_preserve_requested_order(monkeypatch):
    result = _board(monkeypatch, _frame([1.0, 2.0, 3.0]), (("2D", 2), ("1D", 1)))
    assert result["labels"] == ["2D", "1D"]
    assert _vals(result) == {"2D": 5.0, "1D": 3.0}


def test_numeric_strings_are_valid_values(monkeypatch):
    result = _board(monkeypatch, _frame(["2.5", "-1.0"]))
    assert _vals(result)["1D"] == -1.0
    assert _vals(result)["3D"] == 1.5


def test_finite_inputs_cannot_publish_overflowed_window(monkeypatch):
    with np.errstate(over="ignore", invalid="ignore"):
        result = _board(monkeypatch, _frame([1e308, 1e308]))
    assert _vals(result)["1D"] == 1e308
    assert _vals(result)["3D"] is None
    json.dumps(result, allow_nan=False)


def test_finite_fund_totals_cannot_publish_overflowed_net(monkeypatch):
    result = _board(monkeypatch, _frame([1e308], [1e308]))
    assert _vals(result)["1D"] == 1e308
    assert result["net"]["1D"] is None
    json.dumps(result, allow_nan=False)


def test_complete_histories_preserve_existing_sums(monkeypatch):
    rng = random.Random(672)
    for size in range(1, 101):
        frame = _frame([rng.uniform(-100, 100) for _ in range(size)],
                       [rng.uniform(-100, 100) for _ in range(size)])
        result = _board(monkeypatch, frame)
        assert result["depth"] == size
        for label, count in sponsors.FLOW_PERIODS:
            totals = [float(frame[col].tail(count).sum()) for col in frame]
            assert _vals(result)[label] == totals[0]
            assert _vals(result, "XLF")[label] == totals[1]
            assert result["net"][label] == sum(totals)


def test_native_parquet_to_flow_path_withholds_stale_substitution(monkeypatch, tmp_path):
    dates = pd.to_datetime(["2026-11-06", "2026-11-09", "2026-11-10"])
    for ticker, nav, so in [
        ("XLK", [100.0, 100.0, None], [10.0, 11.0, 12.0]),
        ("XLF", [100.0, 100.0, 100.0], [10.0, 10.0, 9.5]),
    ]:
        pd.DataFrame({"nav": nav, "so_mn": so}, index=dates).to_parquet(tmp_path / f"{ticker}.parquet")
    monkeypatch.setattr(sponsors.config, "load", lambda: {"sponsors": {"sector_funds": ["XLK", "XLF"]}})
    monkeypatch.setattr(store, "read", lambda group, ticker: pd.read_parquet(tmp_path / f"{ticker}.parquet"))
    result = sponsors.sector_flow_periods()
    assert result["asof"] == "2026-11-10"
    assert result["depth"] == 2
    assert _vals(result)["1D"] is None
    assert _vals(result, "XLF")["1D"] == -50.0
    assert result["net"]["1D"] is None
