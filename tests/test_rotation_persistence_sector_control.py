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
    aggregate_completed_bars,
    build_result,
    leadership_surface,
    macd_bullish_crosses,
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
