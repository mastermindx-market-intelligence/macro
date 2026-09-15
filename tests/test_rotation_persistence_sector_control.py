"""Contract tests for the preregistered RPH-1 daily sector control."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.research.rotation_persistence.contracts import ContractError, strict_json_dumps
from scripts.research.rotation_persistence.sector_control import (
    AUTHORITY,
    SECTORS,
    _hierarchy_descriptor,
    _history_quality,
    _outcome_rows,
    _signal_cell,
    _spearman,
    _top_three,
    aggregate_completed_bars,
    build_result,
    correlation_control,
    dispersion_control,
    leadership_surface,
    macd_bullish_crosses,
    macd_control,
    render_markdown,
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
    assert result["quality"]["first_eligible_signal_position_by_phase"]["3D.p2"] == 301
    assert "latest_eligible_signal_position_by_phase" not in result["quality"]


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


def test_spearman_uses_average_ranks_and_pins_direction() -> None:
    index = ["a", "b", "c"]
    assert _spearman(pd.Series([1.0, 2.0, 3.0], index=index), pd.Series([4.0, 5.0, 6.0], index=index)) == pytest.approx(1.0)
    assert _spearman(pd.Series([1.0, 2.0, 3.0], index=index), pd.Series([6.0, 5.0, 4.0], index=index)) == pytest.approx(-1.0)
    assert _spearman(pd.Series([1.0, 1.0, 3.0], index=index), pd.Series([1.0, 2.0, 3.0], index=index)) == pytest.approx(0.8660254037844387)


def test_top_three_breaks_equal_leadership_by_ticker() -> None:
    values = pd.Series(0.0, index=SECTORS)
    values.loc[["XLY", "XLE", "XLB", "XLC"]] = 1.0

    assert _top_three(values) == ("XLB", "XLC", "XLE")


def test_leadership_surface_includes_final_matured_anchor_and_formula() -> None:
    index = pd.bdate_range("2026-01-02", periods=12)
    rates = np.linspace(0.001, 0.011, len(SECTORS))
    values = {
        symbol: np.exp(4.0 + rates[position] * np.arange(len(index)))
        for position, symbol in enumerate(SECTORS)
    }
    panel = pd.DataFrame(values, index=index)

    result = leadership_surface(panel, lookback=1, horizons=(1,))
    cell = result["horizons"]["1"]

    assert cell["eligible_anchors"] == 10
    assert cell["rank_persistence"]["all"]["end_date"] == index[-2].date().isoformat()
    assert cell["rank_persistence"]["all"]["mean"] == pytest.approx(1.0)
    assert cell["predictive_persistence"]["all"]["mean"] == pytest.approx(1.0)
    assert cell["top3_retention"]["all"]["mean"] == pytest.approx(1.0)


def test_signal_cell_discloses_sector_date_unit_and_latest_unique_dates() -> None:
    dates = pd.bdate_range("2026-01-02", periods=25)
    rows = [
        {
            "symbol": symbol,
            "signal_date": date,
            "outcome_date": date + pd.offsets.BDay(1),
            "absolute_return": 0.01,
            "spy_relative_return": 0.005,
        }
        for date in dates
        for symbol in ("XLB", "XLC")
    ]

    cell = _signal_cell(rows, latest_dates=20)

    assert cell["observation_unit"] == "sector_signal_date"
    assert cell["sector_date_observations"] == 40
    assert cell["n"] == 40
    assert cell["unique_signal_dates"] == 20
    assert cell["start_date"] == dates[5].date().isoformat()
    assert cell["end_date"] == dates[-1].date().isoformat()


def _fake_phase(value: float) -> dict:
    return {
        "completed_bars": 120,
        "first_completed_bar": "2025-01-03",
        "last_completed_bar": "2026-06-30",
        "outcomes": {
            "1": {
                "all": {
                    "state": "MEASURED",
                    "observation_unit": "sector_signal_date",
                    "sector_date_observations": 12,
                    "n": 12,
                    "unique_signal_dates": 9,
                    "start_date": "2025-06-02",
                    "end_date": "2026-06-20",
                    "median_spy_relative_return": value,
                }
            }
        },
    }


def test_hierarchy_descriptor_discloses_every_phase_sample_span() -> None:
    timeframes = {
        "1D": {"phases": {"0": _fake_phase(0.05)}},
        "2D": {"phases": {"0": _fake_phase(0.01), "1": _fake_phase(0.02)}},
        "3D": {
            "phases": {
                "0": _fake_phase(0.01),
                "1": _fake_phase(0.02),
                "2": _fake_phase(0.03),
            }
        },
    }

    descriptor = _hierarchy_descriptor(timeframes, horizon=1, window="all")

    assert descriptor["label"] == "ONE_DAY_ABOVE_ALL_SLOWER_PHASES"
    assert set(descriptor["phase_samples"]) == {
        "1D.p0", "2D.p0", "2D.p1", "3D.p0", "3D.p1", "3D.p2"
    }
    sample = descriptor["phase_samples"]["3D.p2"]
    assert sample["completed_bar_count"] == 120
    assert sample["completed_bar_start_date"] == "2025-01-03"
    assert sample["completed_bar_end_date"] == "2026-06-30"
    assert sample["observation_unit"] == "sector_signal_date"
    assert sample["sector_date_observations"] == 12
    assert sample["unique_signal_dates"] == 9
    assert sample["signal_start_date"] == "2025-06-02"
    assert sample["signal_end_date"] == "2026-06-20"


def test_leadership_reports_recent_to_all_history_comparison() -> None:
    cell = leadership_surface(_panel(80), lookback=5, horizons=(1,))["horizons"]["1"]
    comparison = cell["rank_persistence"]["recent_20_vs_all"]

    assert comparison["state"] == "MEASURED"
    assert comparison["mean_difference"] == pytest.approx(
        cell["rank_persistence"]["recent_20"]["mean"]
        - cell["rank_persistence"]["all"]["mean"]
    )
    assert comparison["median_difference"] == pytest.approx(
        cell["rank_persistence"]["recent_20"]["median"]
        - cell["rank_persistence"]["all"]["median"]
    )


def test_history_quality_names_first_eligible_position_and_refuses_short_forward_tail() -> None:
    short = _history_quality(_panel(311))
    measured = _history_quality(_panel(312))

    assert short["state"] == "INSUFFICIENT_HISTORY"
    assert short["daily_forward_sessions_available_by_phase"]["3D.p2"] == 9
    assert measured["state"] == "MEASURED"
    assert measured["first_eligible_signal_position_by_phase"]["3D.p2"] == 301
    assert "latest_eligible_signal_position_by_phase" not in measured


def test_strict_json_directly_refuses_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="strict JSON refuses"):
        strict_json_dumps({"bad": float("nan")})


def test_markdown_discloses_leadership_samples_and_phase_evidence() -> None:
    panel = _panel(340)
    receipt = {
        "source_revision": "deadbeef",
        "files": {symbol: {"sha256": "0" * 64} for symbol in (*SECTORS, "SPY")},
        "common_rows": len(panel),
        "first_session": panel.index[0].date().isoformat(),
        "last_session": panel.index[-1].date().isoformat(),
    }
    result = build_result(panel, receipt, produced_at="2026-09-12T21:00:00Z")
    report = render_markdown(result)
    recent = result["leadership"]["5"]["horizons"]["1"]["rank_persistence"]["recent_20"]

    assert "Recent anchors" in report
    assert "Recent N" in report
    assert "Recent std" in report
    assert "All-history N" in report
    assert "Recent-minus-all mean" in report
    assert f"| 5 | 1 | Rank persistence | {recent['anchors']} | {recent['n']} |" in report
    assert "## MACD phase evidence" in report
    assert "Sector-date observations" in report
    assert "Unique signal dates" in report
