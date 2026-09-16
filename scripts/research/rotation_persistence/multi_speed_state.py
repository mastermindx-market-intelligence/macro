"""Causal, outcome-blind Multi-Speed State Frame for rotation-persistence RPH-2.

This module describes information available at each completed daily session.  It does
not calculate forward returns, choose a timeframe, select an entry policy, rank trades,
or grant Prophet / execution authority.  The persisted producer reuses RPH-1's exact
complete-date price panel and source receipt; this module owns only the deterministic
state transform.
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd

from .contracts import AUTHORITY as BASE_AUTHORITY, ContractError

SCHEMA = "research.rotation_persistence_multi_speed_state_rph2.v1"
OPERATION_KEY = "multi-speed-state-rph2-20260916-sol-001"
SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
ALL_SYMBOLS = (*SECTORS, "SPY")
AUTHORITY = dict(BASE_AUTHORITY)
STRUCTURAL_LOOKBACK = 21
TACTICAL_LOOKBACK = 5
TOP_TIER_SIZE = 3
CORRELATION_WINDOW = 20
MACD_FAST_SPAN = 12
MACD_SLOW_SPAN = 26
MACD_SIGNAL_SPAN = 9


def _iso_date(value: Any) -> str:
    return pd.Timestamp(value).date().isoformat()


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int_or_none(value: Any) -> int | None:
    number = _finite_or_none(value)
    return None if number is None else int(number)


def _require_panel(panel: pd.DataFrame) -> None:
    missing = [symbol for symbol in ALL_SYMBOLS if symbol not in panel.columns]
    if missing:
        raise ContractError(f"price panel is missing columns: {', '.join(missing)}")
    if panel.empty:
        raise ContractError("price panel is empty")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise ContractError("price panel index must be a DatetimeIndex")
    if not panel.index.is_monotonic_increasing or not panel.index.is_unique:
        raise ContractError("price panel dates must be unique and increasing")
    values = panel.loc[:, ALL_SYMBOLS].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ContractError("price panel closes must be finite and positive")


def _validate_source_receipt(panel: pd.DataFrame, receipt: dict[str, Any]) -> None:
    try:
        common_rows = int(receipt["common_rows"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("source receipt requires common_rows") from exc
    if common_rows != len(panel):
        raise ContractError("source receipt common_rows disagrees with price panel")
    if receipt.get("first_session") != _iso_date(panel.index[0]):
        raise ContractError("source receipt first_session disagrees with price panel")
    if receipt.get("last_session") != _iso_date(panel.index[-1]):
        raise ContractError("source receipt last_session disagrees with price panel")
    if receipt.get("symbols") != list(ALL_SYMBOLS):
        raise ContractError("source receipt symbols must match the complete RPH-2 panel")
    files = receipt.get("files")
    if not isinstance(files, dict) or any(symbol not in files for symbol in ALL_SYMBOLS):
        raise ContractError("source receipt requires every sector and benchmark file")
    for symbol in ALL_SYMBOLS:
        file_receipt = files[symbol]
        sha = file_receipt.get("sha256") if isinstance(file_receipt, dict) else None
        try:
            valid = isinstance(sha, str) and len(sha) == 64 and int(sha, 16) >= 0
        except ValueError:
            valid = False
        if not valid:
            raise ContractError(f"source receipt has invalid sha256 for {symbol}")


def _alpha_for_span(span: int) -> float:
    return 2.0 / (float(span) + 1.0)


def _daily_alpha_for_completed_bar_span(span: int, sessions_per_bar: int = 3) -> float:
    """Daily alpha with the same exponential *decay* as one completed N-session EMA bar."""
    if span <= 0 or sessions_per_bar <= 0:
        raise ValueError("span and sessions_per_bar must be positive")
    retention_per_bar = 1.0 - _alpha_for_span(span)
    return 1.0 - retention_per_bar ** (1.0 / sessions_per_bar)


def _span_for_alpha(alpha: float) -> float:
    if not 0.0 < alpha <= 1.0:
        raise ValueError("alpha must be in (0, 1]")
    return 2.0 / alpha - 1.0


def memory_equivalent_parameters() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for label, span in (
        ("fast", MACD_FAST_SPAN),
        ("slow", MACD_SLOW_SPAN),
        ("signal", MACD_SIGNAL_SPAN),
    ):
        alpha = _daily_alpha_for_completed_bar_span(span, 3)
        out[label] = {
            "completed_3d_span": float(span),
            "daily_decay_matched_alpha": alpha,
            "daily_decay_matched_span": _span_for_alpha(alpha),
        }
    return out


def _horizon_tables(panel: pd.DataFrame, lookback: int) -> dict[str, pd.DataFrame]:
    closes = panel.loc[:, SECTORS].astype(float)
    trailing = closes / closes.shift(lookback) - 1.0
    ranks = trailing.rank(axis=1, method="average", ascending=False)
    percentiles = (len(SECTORS) - ranks) / (len(SECTORS) - 1)
    rank_velocity = ranks.shift(1) - ranks  # positive means rank improved
    return_velocity = trailing - trailing.shift(1)
    residency = pd.DataFrame(np.nan, index=panel.index, columns=SECTORS, dtype=float)
    for symbol in SECTORS:
        run = 0
        for pos, rank in enumerate(ranks[symbol].to_numpy(dtype=float)):
            if not math.isfinite(rank):
                run = 0
                continue
            if rank <= TOP_TIER_SIZE:
                run += 1
            else:
                run = 0
            residency.iat[pos, residency.columns.get_loc(symbol)] = float(run)
    return {
        "return": trailing,
        "rank": ranks,
        "percentile": percentiles,
        "rank_velocity": rank_velocity,
        "return_velocity": return_velocity,
        "top_tier_residency": residency,
    }


def _ema(series: pd.Series, *, span: int | None = None, alpha: float | None = None,
         min_periods: int | None = None) -> pd.Series:
    if (span is None) == (alpha is None):
        raise ValueError("provide exactly one of span or alpha")
    if min_periods is None:
        min_periods = span if span is not None else max(1, math.ceil(_span_for_alpha(float(alpha))))
    kwargs = {"adjust": False, "min_periods": int(min_periods)}
    if span is not None:
        return series.ewm(span=span, **kwargs).mean()
    return series.ewm(alpha=float(alpha), **kwargs).mean()


def _macd_histogram_standard(close: pd.Series) -> pd.Series:
    fast = _ema(close.astype(float), span=MACD_FAST_SPAN)
    slow = _ema(close.astype(float), span=MACD_SLOW_SPAN)
    line = fast - slow
    signal = _ema(line, span=MACD_SIGNAL_SPAN)
    return line - signal


def _macd_histogram_decay_matched_3d(close: pd.Series) -> pd.Series:
    params = memory_equivalent_parameters()
    fast_alpha = params["fast"]["daily_decay_matched_alpha"]
    slow_alpha = params["slow"]["daily_decay_matched_alpha"]
    signal_alpha = params["signal"]["daily_decay_matched_alpha"]
    fast = _ema(close.astype(float), alpha=fast_alpha)
    slow = _ema(close.astype(float), alpha=slow_alpha)
    line = fast - slow
    signal = _ema(line, alpha=signal_alpha)
    return line - signal


def _sign(value: Any) -> int | None:
    number = _finite_or_none(value)
    if number is None:
        return None
    if number > 0:
        return 1
    if number < 0:
        return -1
    return 0


def _cycle_table(histogram: pd.Series) -> pd.DataFrame:
    columns = [
        "sign", "bars_since_true_cross", "current_half_cycle_age",
        "latest_completed_sign", "latest_completed_length",
        "latest_completed_positive_length", "latest_completed_negative_length",
    ]
    rows: list[dict[str, Any]] = []
    last_nonzero_sign: int | None = None
    run_start: int | None = None
    last_cross: int | None = None
    latest_sign: int | None = None
    latest_length: int | None = None
    latest_positive: int | None = None
    latest_negative: int | None = None
    for pos, raw in enumerate(histogram.to_numpy(dtype=float)):
        sign = _sign(raw)
        if sign is None:
            rows.append({key: None for key in columns})
            continue
        if sign != 0:
            if last_nonzero_sign is None:
                last_nonzero_sign = sign
                run_start = pos
            elif sign != last_nonzero_sign:
                assert run_start is not None
                completed = pos - run_start
                latest_sign = last_nonzero_sign
                latest_length = completed
                if latest_sign > 0:
                    latest_positive = completed
                else:
                    latest_negative = completed
                last_cross = pos
                last_nonzero_sign = sign
                run_start = pos
        rows.append({
            "sign": sign,
            "bars_since_true_cross": None if last_cross is None else pos - last_cross,
            "current_half_cycle_age": (
                None if sign == 0 or run_start is None else pos - run_start + 1
            ),
            "latest_completed_sign": latest_sign,
            "latest_completed_length": latest_length,
            "latest_completed_positive_length": latest_positive,
            "latest_completed_negative_length": latest_negative,
        })
    return pd.DataFrame(rows, index=histogram.index, columns=columns)


def _macd_tables(panel: pd.DataFrame) -> dict[str, dict[str, pd.Series | pd.DataFrame]]:
    out: dict[str, dict[str, pd.Series | pd.DataFrame]] = {}
    for symbol in SECTORS:
        daily = _macd_histogram_standard(panel[symbol])
        decay = _macd_histogram_decay_matched_3d(panel[symbol])
        slope = (daily - daily.shift(3)) / 3.0
        acceleration = (slope - slope.shift(3)) / 3.0
        out[symbol] = {
            "daily_histogram": daily,
            "decay_matched_3d_histogram": decay,
            "slope_3": slope,
            "acceleration_3": acceleration,
            "cycle": _cycle_table(daily),
        }
    return out


def _mean_pairwise_correlation(window: pd.DataFrame) -> float | None:
    if len(window) < CORRELATION_WINDOW or window.isna().any().any():
        return None
    matrix = window.corr(method="pearson").to_numpy(dtype=float)
    upper = matrix[np.triu_indices(len(SECTORS), 1)]
    if len(upper) != len(SECTORS) * (len(SECTORS) - 1) // 2:
        return None
    return _finite_or_none(float(np.mean(upper)))


def market_state_rows(panel: pd.DataFrame) -> list[dict[str, Any]]:
    _require_panel(panel)
    closes = panel.loc[:, SECTORS].astype(float)
    daily = closes.pct_change(fill_method=None)
    trailing_5 = closes / closes.shift(TACTICAL_LOOKBACK) - 1.0
    trailing_21 = closes / closes.shift(STRUCTURAL_LOOKBACK) - 1.0
    rows: list[dict[str, Any]] = []
    for pos, session in enumerate(panel.index):
        dispersion = None
        if pos >= 1:
            values = daily.iloc[pos].to_numpy(dtype=float)
            if np.isfinite(values).all():
                dispersion = _finite_or_none(float(np.std(values, ddof=1)))
        corr = None
        if pos >= CORRELATION_WINDOW:
            corr = _mean_pairwise_correlation(
                daily.iloc[pos - CORRELATION_WINDOW + 1 : pos + 1]
            )
        p5 = None
        if pos >= TACTICAL_LOOKBACK:
            values = trailing_5.iloc[pos].to_numpy(dtype=float)
            if np.isfinite(values).all():
                p5 = float(np.mean(values > 0.0))
        p21 = None
        if pos >= STRUCTURAL_LOOKBACK:
            values = trailing_21.iloc[pos].to_numpy(dtype=float)
            if np.isfinite(values).all():
                p21 = float(np.mean(values > 0.0))
        rows.append({
            "session": _iso_date(session),
            "dispersion_daily": dispersion,
            "mean_pairwise_correlation_20": corr,
            "participation_positive_5": p5,
            "participation_positive_21": p21,
            "participation_denominator": len(SECTORS),
        })
    return rows


def sector_state_rows(panel: pd.DataFrame) -> list[dict[str, Any]]:
    _require_panel(panel)
    structural = _horizon_tables(panel, STRUCTURAL_LOOKBACK)
    tactical = _horizon_tables(panel, TACTICAL_LOOKBACK)
    macd = _macd_tables(panel)
    rows: list[dict[str, Any]] = []
    for pos, session in enumerate(panel.index):
        for symbol in SECTORS:
            cycle = macd[symbol]["cycle"]
            assert isinstance(cycle, pd.DataFrame)
            daily_hist = macd[symbol]["daily_histogram"]
            decay_hist = macd[symbol]["decay_matched_3d_histogram"]
            slope = macd[symbol]["slope_3"]
            acceleration = macd[symbol]["acceleration_3"]
            assert isinstance(daily_hist, pd.Series)
            assert isinstance(decay_hist, pd.Series)
            assert isinstance(slope, pd.Series)
            assert isinstance(acceleration, pd.Series)
            daily_value = _finite_or_none(daily_hist.iloc[pos])
            decay_value = _finite_or_none(decay_hist.iloc[pos])
            rows.append({
                "session": _iso_date(session),
                "symbol": symbol,
                "structural_return_21": _finite_or_none(structural["return"].at[session, symbol]),
                "structural_rank_21": _finite_or_none(structural["rank"].at[session, symbol]),
                "structural_percentile_21": _finite_or_none(structural["percentile"].at[session, symbol]),
                "structural_rank_velocity_21": _finite_or_none(structural["rank_velocity"].at[session, symbol]),
                "structural_return_velocity_21": _finite_or_none(structural["return_velocity"].at[session, symbol]),
                "structural_top3_residency_21": _finite_or_none(structural["top_tier_residency"].at[session, symbol]),
                "tactical_return_5": _finite_or_none(tactical["return"].at[session, symbol]),
                "tactical_rank_5": _finite_or_none(tactical["rank"].at[session, symbol]),
                "tactical_percentile_5": _finite_or_none(tactical["percentile"].at[session, symbol]),
                "tactical_rank_velocity_5": _finite_or_none(tactical["rank_velocity"].at[session, symbol]),
                "tactical_return_velocity_5": _finite_or_none(tactical["return_velocity"].at[session, symbol]),
                "tactical_top3_residency_5": _finite_or_none(tactical["top_tier_residency"].at[session, symbol]),
                "macd_histogram_daily": daily_value,
                "macd_histogram_sign": _int_or_none(cycle.at[session, "sign"]),
                "macd_histogram_slope_3": _finite_or_none(slope.iloc[pos]),
                "macd_histogram_acceleration_3": _finite_or_none(acceleration.iloc[pos]),
                "bars_since_true_macd_cross": _int_or_none(cycle.at[session, "bars_since_true_cross"]),
                "current_half_cycle_age": _int_or_none(cycle.at[session, "current_half_cycle_age"]),
                "latest_completed_half_cycle_sign": _int_or_none(cycle.at[session, "latest_completed_sign"]),
                "latest_completed_half_cycle_length": _int_or_none(cycle.at[session, "latest_completed_length"]),
                "latest_completed_positive_half_cycle_length": _int_or_none(cycle.at[session, "latest_completed_positive_length"]),
                "latest_completed_negative_half_cycle_length": _int_or_none(cycle.at[session, "latest_completed_negative_length"]),
                "macd_histogram_3d_decay_matched": decay_value,
                "macd_basis_sign_agreement": (
                    None if daily_value is None or decay_value is None
                    else _sign(daily_value) == _sign(decay_value)
                ),
            })
    return rows


def build_state_frame(panel: pd.DataFrame) -> dict[str, Any]:
    _require_panel(panel)
    return {
        "sector_rows": sector_state_rows(panel),
        "market_rows": market_state_rows(panel),
    }


def build_result(panel: pd.DataFrame, receipt: dict[str, Any], *, produced_at: str) -> dict[str, Any]:
    _require_panel(panel)
    _validate_source_receipt(panel, receipt)
    frame = build_state_frame(panel)
    return {
        "schema_version": SCHEMA,
        "operation_key": OPERATION_KEY,
        "produced_at": produced_at,
        "source": receipt,
        "parameters": {
            "sectors": list(SECTORS),
            "benchmark": "SPY",
            "structural_lookback_sessions": STRUCTURAL_LOOKBACK,
            "tactical_lookback_sessions": TACTICAL_LOOKBACK,
            "top_tier_size": TOP_TIER_SIZE,
            "correlation_window_sessions": CORRELATION_WINDOW,
            "macd": {"fast": MACD_FAST_SPAN, "slow": MACD_SLOW_SPAN, "signal": MACD_SIGNAL_SPAN},
            "memory_equivalent": memory_equivalent_parameters(),
            "memory_equivalent_note": (
                "Daily filters match only the exponential decay of completed 3-session MACD components; "
                "they are not information-equivalent to an actual completed 3D series."
            ),
        },
        "state_frame": frame,
        "authority": dict(AUTHORITY),
        "limitations": [
            "Outcome-blind state only: no forward return, payoff, policy selection, model promotion, or trade ranking is computed.",
            "The 3D decay-matched MACD basis matches memory decay only; it is not a completed-3D information substitute.",
            "The complete-date panel removes sessions missing from any required sector or SPY; source receipt records that basis.",
            "Source file hashes prove bytes read now, not point-in-time historical availability or correction timing.",
            "This research artifact grants no Prophet, execution, admission, sizing, or capital authority.",
        ],
    }
