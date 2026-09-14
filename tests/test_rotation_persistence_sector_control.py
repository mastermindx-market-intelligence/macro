"""Contract tests for the preregistered RPH-1 daily sector control."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.research.rotation_persistence.contracts import ContractError
from scripts.research.rotation_persistence.sector_control import (
    AUTHORITY,
    SECTORS,
    _outcome_rows,
    aggregate_completed_bars,
    build_result,
    correlation_control,
    dispersion_control,
    leadership_surface,
    macd_bullish_crosses,
    macd_control,
)


def _panel(rows: int = 180) -> pd.DataFrame:
    idx = pd.bdate_range("2025-01-02", periods=rows)
    data: dict[str, np.ndarray] = {}
    for n, symbol in enumerate((*SECTORS, "SPY"), start=1):
        trend = np.linspace(100.0 + n, 140.0 + n * 2.0, rows)
        cycle = np.sin(np.arange(rows) / (5.0 + n / 10.0)) * (0.5 + n / 20.0)
        data[symbol] = trend + cycle
    return pd.DataFrame(data, index=idx)


def test_three_session_completed_bars_are_phase_explicit_and_drop_tail() -> None:
    panel = _panel(10)
    p0 = aggregate_completed_bars(panel, sessions=3, phase=0)
    p1 = aggregate_completed_bars(panel, sessions=3, phase=1)
    p2 = aggregate_completed_bars(panel, sessions=3, phase=2)

    assert list(p0.index) == [panel.index[2], panel.index[5], panel.index[8]]
    assert list(p1.index) == [panel.index[3], panel.index[6], panel.index[9]]
    assert list(p2.index) == [panel.index[4], panel.index[7]]
    pd.testing.assert_series_equal(p0["XLB"], panel.loc[p0.index, "XLB"], check_names=False)


def test_completed_bar_phase_must_be_inside_timeframe() -> None:
    with pytest.raises(ContractError, match="phase"):
        aggregate_completed_bars(_panel(20), sessions=3, phase=3)


def test_macd_refuses_to_emit_before_100_completed_bars() -> None:
    bars = aggregate_completed_bars(_panel(99), sessions=1, phase=0)
    crosses = macd_bullish_crosses(bars["XLB"], min_completed_bars=100)
    assert crosses.empty


def test_macd_never_marks_an_incomplete_three_session_tail() -> None:
    panel = _panel(305)
    bars = aggregate_completed_bars(panel, sessions=3, phase=1)
    crosses = macd_bullish_crosses(bars["XLB"], min_completed_bars=100)
    assert crosses.index.isin(bars.index).all()
    assert panel.index[-1] not in crosses.index or panel.index[-1] in bars.index


def test_leadership_surface_keeps_descriptive_and_predictive_estimands_separate() -> None:
    panel = _panel(180)
    out = leadership_surface(panel, lookback=5, horizons=(1, 5))
    assert set(out["horizons"]) == {"1", "5"}
    for horizon in ("1", "5"):
        cell = out["horizons"][horizon]
        assert set(cell) >= {"rank_persistence", "predictive_persistence", "top3_retention"}
        assert cell["rank_persistence"] is not cell["predictive_persistence"]


def test_result_contract_is_context_only_and_has_no_trade_authority(tmp_path: Path) -> None:
    panel = _panel(320)
    receipt = {
        "source_revision": "deadbeef",
        "files": {symbol: {"sha256": "0" * 64} for symbol in (*SECTORS, "SPY")},
        "common_rows": len(panel),
        "first_session": panel.index[0].date().isoformat(),
        "last_session": panel.index[-1].date().isoformat(),
    }
    result = build_result(panel, receipt, produced_at="2026-09-12T21:00:00Z")
    assert result["schema_version"] == "research.rotation_persistence_sector_control_rph1.v1"
    assert result["authority"] == AUTHORITY
    assert result["authority"] == {
        "is_context_only": True,
        "may_rank": False,
        "may_gate": False,
        "may_size": False,
        "may_trade": False,
        "may_modify_prophet": False,
        "may_modify_oracle": False,
    }


def test_future_outcomes_start_at_signal_close_and_use_strictly_later_session() -> None:
    panel = _panel(20)
    signal_date = panel.index[5]
    outcome_date = panel.index[8]
    panel.loc[signal_date, "XLB"] = 100.0
    panel.loc[outcome_date, "XLB"] = 115.0
    panel.loc[signal_date, "SPY"] = 200.0
    panel.loc[outcome_date, "SPY"] = 210.0
    empty = pd.Series([], index=pd.DatetimeIndex([]), dtype=bool)
    crosses = {symbol: empty.copy() for symbol in SECTORS}
    crosses["XLB"] = pd.Series([True], index=pd.DatetimeIndex([signal_date]))

    rows = _outcome_rows(panel, crosses, horizon=3)

    assert len(rows) == 1
    assert rows[0]["signal_date"] == signal_date
    assert rows[0]["outcome_date"] == outcome_date
    assert rows[0]["absolute_return"] == pytest.approx(0.15)
    assert rows[0]["spy_relative_return"] == pytest.approx(0.10)


def test_dispersion_and_correlation_remain_distinct_measured_controls() -> None:
    panel = _panel(340)
    dispersion = dispersion_control(panel)
    correlation = correlation_control(panel)

    assert dispersion["definition"].startswith("sample_std")
    assert correlation["definition"].startswith("mean_of_55")
    assert dispersion["windows"]["recent_20"]["state"] == "MEASURED"
    assert correlation["windows"]["recent_20"]["state"] == "MEASURED"
    assert dispersion["recent_20_vs_prior_252"]["state"] == "MEASURED"
    assert correlation["recent_20_vs_prior_252"]["state"] == "MEASURED"


def test_macd_control_reports_every_predeclared_phase_separately() -> None:
    control, hierarchy = macd_control(_panel(340))

    assert set(control["timeframes"]) == {"1D", "2D", "3D"}
    assert set(control["timeframes"]["1D"]["phases"]) == {"0"}
    assert set(control["timeframes"]["2D"]["phases"]) == {"0", "1"}
    assert set(control["timeframes"]["3D"]["phases"]) == {"0", "1", "2"}
    assert set(hierarchy) == {"1", "3", "5", "10"}


def test_history_floor_counts_100_completed_three_day_bars_plus_daily_outcome() -> None:
    panel = _panel(312)
    receipt = {
        "source_revision": "deadbeef",
        "files": {symbol: {"sha256": "0" * 64} for symbol in (*SECTORS, "SPY")},
        "common_rows": len(panel),
        "first_session": panel.index[0].date().isoformat(),
        "last_session": panel.index[-1].date().isoformat(),
    }

    result = build_result(panel, receipt, produced_at="2026-09-12T21:00:00Z")

    assert result["quality"]["state"] == "MEASURED"
    assert result["quality"]["latest_eligible_signal_position_by_phase"]["3D.p2"] == 301


def test_build_result_rejects_source_receipt_that_disagrees_with_panel() -> None:
    panel = _panel(320)
    receipt = {
        "source_revision": "deadbeef",
        "files": {symbol: {"sha256": "0" * 64} for symbol in (*SECTORS, "SPY")},
        "common_rows": len(panel) - 1,
        "first_session": panel.index[0].date().isoformat(),
        "last_session": panel.index[-1].date().isoformat(),
    }
    with pytest.raises(ContractError, match="source receipt"):
        build_result(panel, receipt, produced_at="2026-09-12T21:00:00Z")


def test_macd_warmup_blocks_a_real_early_cross() -> None:
    idx = pd.bdate_range("2026-01-02", periods=80)
    values = np.full(80, 100.0)
    values[60:] = np.linspace(110.0, 130.0, 20)
    closes = pd.Series(values, index=idx)

    unrestricted = macd_bullish_crosses(closes, min_completed_bars=1)
    frozen = macd_bullish_crosses(closes, min_completed_bars=100)

    assert len(unrestricted) >= 1
    assert frozen.empty
