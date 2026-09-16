"""Discriminating acceptance tests for the causal RPH-2 Multi-Speed State Frame."""
from __future__ import annotations

import ast
import inspect
import json
import math

import numpy as np
import pandas as pd
import pytest

from scripts.research.rotation_persistence.contracts import ContractError, strict_json_dumps
from scripts.research.rotation_persistence import multi_speed_state as mss
from scripts.research.rotation_persistence.multi_speed_state import (
    ALL_SYMBOLS,
    AUTHORITY,
    CORRELATION_WINDOW,
    MACD_FAST_SPAN,
    MACD_SIGNAL_SPAN,
    MACD_SLOW_SPAN,
    SCHEMA,
    SECTORS,
    STRUCTURAL_LOOKBACK,
    TACTICAL_LOOKBACK,
    _cycle_table,
    _daily_alpha_for_completed_bar_span,
    _macd_histogram_standard,
    _span_for_alpha,
    build_result,
    build_state_frame,
    market_state_rows,
    memory_equivalent_parameters,
    sector_state_rows,
)


def make_panel(n: int = 140) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-02", periods=n)
    t = np.arange(n, dtype=float)
    data: dict[str, np.ndarray] = {}
    for j, symbol in enumerate(SECTORS):
        base = 25.0 + 17.0 * j
        log_return = (
            0.00015 * (j - 5)
            + 0.004 * np.sin(t / (6.0 + j / 5.0) + j * 0.31)
            + 0.0015 * np.cos(t / 17.0 + j)
        )
        data[symbol] = base * np.exp(np.cumsum(log_return))
    spy_return = 0.0003 + 0.0025 * np.sin(t / 8.0) + 0.001 * np.cos(t / 19.0)
    data["SPY"] = 100.0 * np.exp(np.cumsum(spy_return))
    return pd.DataFrame(data, index=index)


def trend_panel(n: int = 40) -> pd.DataFrame:
    """High price level deliberately belongs to the weakest-return sector."""
    index = pd.bdate_range("2025-01-02", periods=n)
    step = np.arange(n, dtype=float)
    data: dict[str, np.ndarray] = {}
    for j, symbol in enumerate(SECTORS):
        base = 10_000.0 if j == 0 else 20.0 + j
        growth = 1.0005 + 0.00035 * j
        data[symbol] = base * np.power(growth, step)
    data["SPY"] = 100.0 * np.power(1.001, step)
    return pd.DataFrame(data, index=index)


def fake_receipt(panel: pd.DataFrame) -> dict:
    return {
        "source_revision": "fixture-revision",
        "data_dir": "fixture",
        "symbols": list(ALL_SYMBOLS),
        "files": {
            symbol: {"sha256": f"{i + 1:064x}"}
            for i, symbol in enumerate(ALL_SYMBOLS)
        },
        "union_rows": len(panel),
        "common_rows": len(panel),
        "excluded_rows": 0,
        "first_session": panel.index[0].date().isoformat(),
        "last_session": panel.index[-1].date().isoformat(),
    }


def row_for(rows: list[dict], session: pd.Timestamp, symbol: str) -> dict:
    key = session.date().isoformat()
    return next(row for row in rows if row["session"] == key and row["symbol"] == symbol)


def test_module_is_outcome_blind_and_does_not_import_authority_planes():
    source = inspect.getsource(mss)
    tree = ast.parse(source)
    forbidden = ("prophet", "trial_ledger", "oracle", "grader", "execution")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        assert not any(token in name.lower() for token in forbidden for name in names)
    assert "shift(-" not in source.replace(" ", "")


def test_state_frame_is_date_keyed_and_joinable():
    panel = make_panel(45)
    frame = build_state_frame(panel)
    assert len(frame["sector_rows"]) == len(panel) * len(SECTORS)
    assert len(frame["market_rows"]) == len(panel)
    sample = frame["sector_rows"][-1]
    assert sample["session"] == panel.index[-1].date().isoformat()
    assert sample["symbol"] in SECTORS
    assert "structural_return_21" in sample
    assert "tactical_return_5" in sample
    assert "macd_histogram_daily" in sample


def test_rank_is_horizon_return_rank_not_price_level_rank():
    panel = trend_panel()
    rows = sector_state_rows(panel)
    final = panel.index[-1]
    weak_high_price = row_for(rows, final, SECTORS[0])
    strong_low_price = row_for(rows, final, SECTORS[-1])
    assert panel.iloc[-1][SECTORS[0]] > panel.iloc[-1][SECTORS[-1]] * 100
    assert weak_high_price["structural_rank_21"] == pytest.approx(float(len(SECTORS)))
    assert weak_high_price["structural_percentile_21"] == pytest.approx(0.0)
    assert strong_low_price["structural_rank_21"] == pytest.approx(1.0)
    assert strong_low_price["structural_percentile_21"] == pytest.approx(1.0)


def test_top_tier_residency_is_symbol_specific():
    panel = trend_panel()
    rows = sector_state_rows(panel)
    final = panel.index[-1]
    leader = row_for(rows, final, SECTORS[-1])
    laggard = row_for(rows, final, SECTORS[0])
    assert leader["structural_top3_residency_21"] > 1
    assert laggard["structural_top3_residency_21"] == 0
    assert leader["tactical_top3_residency_5"] > 1
    assert laggard["tactical_top3_residency_5"] == 0


def test_prefix_invariance_exact_across_all_state_rows():
    full = make_panel(140)
    prefix = full.iloc[:100].copy()
    prefix_frame = build_state_frame(prefix)
    full_frame = build_state_frame(full)
    sector_count = len(prefix) * len(SECTORS)
    assert prefix_frame["sector_rows"] == full_frame["sector_rows"][:sector_count]
    assert prefix_frame["market_rows"] == full_frame["market_rows"][: len(prefix)]


def test_future_mutation_cannot_change_prefix():
    original = make_panel(120)
    mutated = original.copy()
    mutated.iloc[90:, : len(SECTORS)] *= np.linspace(2.0, 20.0, 30)[:, None]
    left = build_state_frame(original.iloc[:90])
    right = build_state_frame(mutated)
    assert left["sector_rows"] == right["sector_rows"][: 90 * len(SECTORS)]
    assert left["market_rows"] == right["market_rows"][:90]


def test_participation_21_has_no_negative_index_leakage():
    panel = make_panel(30)
    rows = market_state_rows(panel)
    for pos in range(STRUCTURAL_LOOKBACK):
        assert rows[pos]["participation_positive_21"] is None
    assert rows[STRUCTURAL_LOOKBACK]["participation_positive_21"] is not None
    for pos in range(TACTICAL_LOOKBACK):
        assert rows[pos]["participation_positive_5"] is None
    assert rows[TACTICAL_LOOKBACK]["participation_positive_5"] is not None
    assert all(row["participation_denominator"] == len(SECTORS) for row in rows)


def test_dispersion_and_correlation_match_declared_causal_definitions():
    panel = make_panel(60)
    rows = market_state_rows(panel)
    returns = panel.loc[:, SECTORS].pct_change(fill_method=None)
    pos = 35
    expected_dispersion = float(returns.iloc[pos].std(ddof=1))
    window = returns.iloc[pos - CORRELATION_WINDOW + 1 : pos + 1]
    matrix = window.corr().to_numpy(dtype=float)
    expected_corr = float(np.mean(matrix[np.triu_indices(len(SECTORS), 1)]))
    assert rows[pos]["dispersion_daily"] == pytest.approx(expected_dispersion)
    assert rows[pos]["mean_pairwise_correlation_20"] == pytest.approx(expected_corr)


def test_standard_macd_histogram_matches_independent_reference():
    close = make_panel(120)["XLE"]
    fast = close.ewm(span=MACD_FAST_SPAN, adjust=False, min_periods=MACD_FAST_SPAN).mean()
    slow = close.ewm(span=MACD_SLOW_SPAN, adjust=False, min_periods=MACD_SLOW_SPAN).mean()
    line = fast - slow
    signal = line.ewm(span=MACD_SIGNAL_SPAN, adjust=False, min_periods=MACD_SIGNAL_SPAN).mean()
    expected = line - signal
    actual = _macd_histogram_standard(close)
    pd.testing.assert_series_equal(actual, expected)


def test_3d_decay_matched_parameters_match_each_macd_component():
    params = memory_equivalent_parameters()
    spans = {"fast": MACD_FAST_SPAN, "slow": MACD_SLOW_SPAN, "signal": MACD_SIGNAL_SPAN}
    for label, span in spans.items():
        alpha_daily = params[label]["daily_decay_matched_alpha"]
        retention_bar = 1.0 - 2.0 / (span + 1.0)
        assert (1.0 - alpha_daily) ** 3 == pytest.approx(retention_bar, rel=1e-12)
        assert params[label]["daily_decay_matched_span"] == pytest.approx(
            _span_for_alpha(alpha_daily), rel=1e-12
        )
    assert params["slow"]["daily_decay_matched_span"] > 70.0
    assert params["fast"]["daily_decay_matched_span"] > 30.0
    assert params["signal"]["daily_decay_matched_span"] > 20.0


def test_true_cross_ignores_leading_zero_and_completes_prior_half_cycle():
    index = pd.bdate_range("2026-01-02", periods=7)
    histogram = pd.Series([np.nan, 0.0, 1.0, 2.0, -1.0, -2.0, 3.0], index=index)
    state = _cycle_table(histogram)
    assert pd.isna(state.iloc[2]["bars_since_true_cross"])
    assert pd.isna(state.iloc[3]["bars_since_true_cross"])
    assert state.iloc[4]["bars_since_true_cross"] == 0
    assert state.iloc[4]["latest_completed_sign"] == 1
    assert state.iloc[4]["latest_completed_length"] == 2
    assert state.iloc[5]["bars_since_true_cross"] == 1
    assert state.iloc[6]["bars_since_true_cross"] == 0
    assert state.iloc[6]["latest_completed_sign"] == -1
    assert state.iloc[6]["latest_completed_length"] == 2


def test_insufficient_history_is_explicit_null_not_tail_data():
    panel = make_panel(20)
    rows = sector_state_rows(panel)
    for symbol in SECTORS:
        row = row_for(rows, panel.index[-1], symbol)
        assert row["structural_return_21"] is None
        assert row["structural_rank_21"] is None
        assert row["structural_top3_residency_21"] is None
        assert row["tactical_return_5"] is not None


def test_build_result_is_strict_json_and_keeps_authority_off():
    panel = make_panel(120)
    result = build_result(panel, fake_receipt(panel), produced_at="2026-09-16T09:00:00Z")
    text = strict_json_dumps(result)
    assert "NaN" not in text and "Infinity" not in text
    decoded = json.loads(text)
    assert decoded["schema_version"] == SCHEMA
    assert decoded["authority"] == AUTHORITY
    assert decoded["authority"]["is_context_only"] is True
    assert decoded["authority"]["may_rank"] is False
    assert decoded["authority"]["may_trade"] is False

    keys: list[str] = []
    def collect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                keys.append(str(key).lower())
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
    collect(decoded["state_frame"])
    assert not any(token in key for key in keys for token in ("forward", "outcome", "payoff", "entry_policy"))


def test_source_receipt_must_bind_exact_panel():
    panel = make_panel(40)
    receipt = fake_receipt(panel)
    receipt["common_rows"] -= 1
    with pytest.raises(ContractError, match="common_rows"):
        build_result(panel, receipt, produced_at="2026-09-16T09:00:00Z")


def test_panel_contract_requires_all_eleven_sectors_and_spy():
    panel = make_panel(20).drop(columns=["XLRE"])
    with pytest.raises(ContractError, match="missing columns"):
        build_state_frame(panel)


def test_cli_reuses_rph1_loader_and_writes_atomic_strict_result(tmp_path, monkeypatch):
    from scripts.research import run_multi_speed_state_rph2 as runner

    panel = make_panel(120)
    receipt = fake_receipt(panel)
    calls = []

    def fake_load(data_dir, *, repo_root=None):
        calls.append((str(data_dir), Path(repo_root)))
        return panel, receipt

    from pathlib import Path
    monkeypatch.setattr(runner, "load_price_panel", fake_load)
    rc = runner.main(
        [
            "--data-dir", "data/yahoo",
            "--output-dir", "research/rph2-test-output",
            "--produced-at", "2026-09-16T09:00:00Z",
        ],
        repo_root=tmp_path,
    )
    assert rc == 0
    assert calls == [("data/yahoo", tmp_path.resolve())]
    output = tmp_path / "research" / "rph2-test-output" / runner.OUTPUT_FILENAME
    payload = json.loads(output.read_text())
    assert payload["schema_version"] == SCHEMA
    assert payload["source"]["common_rows"] == len(panel)
    assert not list(output.parent.glob(f".{output.name}.*"))
