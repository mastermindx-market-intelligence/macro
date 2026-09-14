"""Deterministic research-only daily sector control for Leadership Persistence RPH-1."""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .contracts import AUTHORITY as BASE_AUTHORITY
from .contracts import ContractError

SCHEMA = "research.rotation_persistence_sector_control_rph1.v1"
OPERATION_KEY = "leadership-persistence-sector-control-rph1-20260912-sol-001"
SOURCE_REVISION = "8d198b42f6bff491a49b1f3467b56ca4bb673f80"
SECTORS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")
ALL_SYMBOLS = (*SECTORS, "SPY")
AUTHORITY = dict(BASE_AUTHORITY)
LEADERSHIP_HORIZONS = (1, 3, 5, 7, 10, 20)
FORWARD_HORIZONS = (1, 3, 5, 10)
SUMMARY_WINDOWS = ("all", "recent_20", "recent_60", "prior_252")
SIGNAL_WINDOWS = ("all", "recent_20", "recent_60")
MIN_OBSERVATIONS = 8
MACD_MIN_COMPLETED_BARS = 100


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iso_date(value: Any) -> str:
    return pd.Timestamp(value).date().isoformat()


def _as_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _require_panel(panel: pd.DataFrame, *, columns: Iterable[str] = ALL_SYMBOLS) -> None:
    required = tuple(columns)
    missing = [column for column in required if column not in panel.columns]
    if missing:
        raise ContractError(f"price panel is missing columns: {', '.join(missing)}")
    if panel.empty:
        raise ContractError("price panel is empty")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise ContractError("price panel index must be a DatetimeIndex")
    if not panel.index.is_monotonic_increasing or not panel.index.is_unique:
        raise ContractError("price panel dates must be unique and increasing")
    values = panel.loc[:, required].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ContractError("price panel closes must be finite and positive")


def _normalized_price_series(
    path: Path, symbol: str, *, logical_path: str
) -> tuple[pd.Series, dict[str, Any]]:
    if not path.is_file():
        raise ContractError(f"missing price file: {path}")
    frame = pd.read_parquet(path)
    if "close" not in frame.columns:
        raise ContractError(f"{symbol} parquet requires a close column")

    rows_read = int(len(frame))
    dates = pd.to_datetime(frame.index, errors="coerce", utc=True).tz_localize(None).normalize()
    normalized = pd.DataFrame(
        {"date": dates, "close": frame["close"].to_numpy(), "order": np.arange(rows_read)}
    )
    invalid_date_rows = int(normalized["date"].isna().sum())
    normalized = normalized.loc[normalized["date"].notna()].sort_values(
        ["date", "order"], kind="mergesort"
    )
    duplicate_mask = normalized["date"].duplicated(keep=False)
    duplicate_dates = sorted({_iso_date(value) for value in normalized.loc[duplicate_mask, "date"]})
    normalized = normalized.loc[~normalized["date"].duplicated(keep="first")].copy()
    normalized["close"] = pd.to_numeric(normalized["close"], errors="coerce")
    valid_close = np.isfinite(normalized["close"].to_numpy(dtype=float)) & (
        normalized["close"].to_numpy(dtype=float) > 0
    )
    invalid_close_rows = int((~valid_close).sum())
    normalized = normalized.loc[valid_close, ["date", "close"]]
    if normalized.empty:
        raise ContractError(f"{symbol} has no valid positive closes")

    series = pd.Series(
        normalized["close"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(normalized["date"]),
        name=symbol,
        dtype=float,
    )
    receipt = {
        "path": logical_path,
        "sha256": _sha256(path),
        "rows_read": rows_read,
        "rows_retained": int(len(series)),
        "invalid_rows": invalid_date_rows + invalid_close_rows,
        "invalid_date_rows": invalid_date_rows,
        "invalid_close_rows": invalid_close_rows,
        "duplicate_dates": duplicate_dates,
        "first_session": _iso_date(series.index[0]),
        "last_session": _iso_date(series.index[-1]),
    }
    return series, receipt


def load_price_panel(
    data_dir: Path, symbols: tuple[str, ...] = ALL_SYMBOLS
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Load exact complete-date close panel and byte-bind every input file."""
    requested_data_dir = Path(data_dir).expanduser()
    logical_data_dir = requested_data_dir.as_posix()
    resolved_data_dir = requested_data_dir.resolve()
    if not symbols or len(set(symbols)) != len(symbols):
        raise ContractError("symbols must be non-empty and unique")

    series_by_symbol: dict[str, pd.Series] = {}
    files: dict[str, dict[str, Any]] = {}
    union_index = pd.DatetimeIndex([])
    for symbol in symbols:
        logical_path = (requested_data_dir / f"{symbol}.parquet").as_posix()
        series, file_receipt = _normalized_price_series(
            resolved_data_dir / f"{symbol}.parquet", symbol, logical_path=logical_path
        )
        series_by_symbol[symbol] = series
        files[symbol] = file_receipt
        union_index = union_index.union(series.index)

    panel = pd.concat([series_by_symbol[symbol] for symbol in symbols], axis=1, join="inner")
    panel = panel.loc[:, list(symbols)].sort_index()
    if panel.empty:
        raise ContractError("price files have no complete common session")
    receipt = {
        "source_revision": SOURCE_REVISION,
        "data_dir": logical_data_dir,
        "symbols": list(symbols),
        "files": files,
        "union_rows": int(len(union_index)),
        "common_rows": int(len(panel)),
        "excluded_rows": int(len(union_index) - len(panel)),
        "first_session": _iso_date(panel.index[0]),
        "last_session": _iso_date(panel.index[-1]),
    }
    return panel, receipt


def aggregate_completed_bars(panel: pd.DataFrame, sessions: int, phase: int) -> pd.DataFrame:
    """Return final closes of positional completed bars for one explicit phase."""
    if not isinstance(sessions, int) or sessions <= 0:
        raise ContractError("sessions must be a positive integer")
    if not isinstance(phase, int) or phase < 0 or phase >= sessions:
        raise ContractError("phase must be inside the timeframe")
    if not isinstance(panel.index, pd.DatetimeIndex):
        raise ContractError("panel index must be a DatetimeIndex")
    if not panel.index.is_monotonic_increasing or not panel.index.is_unique:
        raise ContractError("panel dates must be unique and increasing")

    remaining = len(panel) - phase
    complete_rows = max(0, remaining // sessions * sessions)
    if complete_rows == 0:
        return panel.iloc[0:0].copy()
    stop = phase + complete_rows
    positions = np.arange(phase + sessions - 1, stop, sessions, dtype=int)
    return panel.iloc[positions].copy()


def _window_entries(entries: list[tuple[pd.Timestamp, float | None]]) -> dict[str, list]:
    prior_end = max(0, len(entries) - 20)
    return {
        "all": entries,
        "recent_20": entries[-20:],
        "recent_60": entries[-60:],
        "prior_252": entries[max(0, prior_end - 252) : prior_end],
    }


def _summary(
    entries: list[tuple[pd.Timestamp, float | None]], *, minimum: int = MIN_OBSERVATIONS
) -> dict[str, Any]:
    valid = [(date, value) for date, value in entries if value is not None and math.isfinite(value)]
    values = np.asarray([value for _, value in valid], dtype=float)
    state = "MEASURED" if len(values) >= minimum else "INSUFFICIENT_HISTORY"
    measured = state == "MEASURED"
    return {
        "state": state,
        "anchors": int(len(entries)),
        "n": int(len(values)),
        "start_date": _iso_date(valid[0][0]) if valid else None,
        "end_date": _iso_date(valid[-1][0]) if valid else None,
        "mean": float(values.mean()) if measured else None,
        "median": float(np.median(values)) if measured else None,
        "sample_std": float(values.std(ddof=1)) if measured else None,
    }


def _window_summaries(entries: list[tuple[pd.Timestamp, float | None]]) -> dict[str, dict]:
    return {name: _summary(window) for name, window in _window_entries(entries).items()}


def _spearman(left: pd.Series, right: pd.Series) -> float | None:
    aligned = pd.concat([left.astype(float), right.astype(float)], axis=1).dropna()
    if len(aligned) < 2 or aligned.iloc[:, 0].nunique() < 2 or aligned.iloc[:, 1].nunique() < 2:
        return None
    left_rank = aligned.iloc[:, 0].rank(method="average")
    right_rank = aligned.iloc[:, 1].rank(method="average")
    return _as_float(left_rank.corr(right_rank))


def _top_three(values: pd.Series) -> tuple[str, str, str]:
    ordered = sorted(SECTORS, key=lambda symbol: (-float(values[symbol]), symbol))
    return tuple(ordered[:3])  # type: ignore[return-value]


def leadership_surface(
    panel: pd.DataFrame,
    lookback: int,
    horizons: tuple[int, ...] = LEADERSHIP_HORIZONS,
) -> dict[str, Any]:
    """Measure rank memory, future-return association, and exact top-three retention."""
    _require_panel(panel, columns=SECTORS)
    if not isinstance(lookback, int) or lookback <= 0:
        raise ContractError("lookback must be a positive integer")
    if not horizons or any(not isinstance(h, int) or h <= 0 for h in horizons):
        raise ContractError("horizons must be positive integers")

    log_prices = np.log(panel.loc[:, SECTORS].astype(float))
    trailing = log_prices - log_prices.shift(lookback)
    output: dict[str, Any] = {
        "lookback_sessions": int(lookback),
        "chance_top3_retention": 3.0 / len(SECTORS),
        "horizons": {},
    }
    for horizon in horizons:
        rank_entries: list[tuple[pd.Timestamp, float | None]] = []
        predictive_entries: list[tuple[pd.Timestamp, float | None]] = []
        retention_entries: list[tuple[pd.Timestamp, float | None]] = []
        for position in range(lookback, len(panel) - horizon):
            anchor = panel.index[position]
            current = trailing.iloc[position]
            later = trailing.iloc[position + horizon]
            future_return = log_prices.iloc[position + horizon] - log_prices.iloc[position]
            rank_entries.append((anchor, _spearman(current, later)))
            predictive_entries.append((anchor, _spearman(current, future_return)))
            current_top = set(_top_three(current))
            later_top = set(_top_three(later))
            retention_entries.append((anchor, len(current_top & later_top) / 3.0))

        output["horizons"][str(horizon)] = {
            "eligible_anchors": int(len(rank_entries)),
            "rank_persistence": _window_summaries(rank_entries),
            "predictive_persistence": _window_summaries(predictive_entries),
            "top3_retention": _window_summaries(retention_entries),
        }
    return output


def _recent_prior_comparison(windows: dict[str, dict[str, Any]]) -> dict[str, Any]:
    recent = windows["recent_20"]
    prior = windows["prior_252"]
    if recent["state"] != "MEASURED" or prior["state"] != "MEASURED":
        return {
            "state": "INSUFFICIENT_HISTORY",
            "mean_difference": None,
            "mean_ratio": None,
            "median_difference": None,
            "median_ratio": None,
        }
    return {
        "state": "MEASURED",
        "mean_difference": recent["mean"] - prior["mean"],
        "mean_ratio": recent["mean"] / prior["mean"] if prior["mean"] != 0 else None,
        "median_difference": recent["median"] - prior["median"],
        "median_ratio": recent["median"] / prior["median"] if prior["median"] != 0 else None,
    }


def dispersion_control(panel: pd.DataFrame) -> dict[str, Any]:
    """Describe cross-sectional sample dispersion of complete-panel daily returns."""
    _require_panel(panel, columns=SECTORS)
    returns = panel.loc[:, SECTORS].pct_change(fill_method=None).iloc[1:]
    dispersion = returns.std(axis=1, ddof=1)
    entries = [(date, _as_float(value)) for date, value in dispersion.items()]
    windows = _window_summaries(entries)
    return {
        "definition": "sample_std_across_eleven_sector_daily_simple_returns",
        "windows": windows,
        "recent_20_vs_prior_252": _recent_prior_comparison(windows),
    }


def correlation_control(panel: pd.DataFrame, window: int = 20) -> dict[str, Any]:
    """Describe trailing-window mean of the 55 unique sector correlation pairs."""
    _require_panel(panel, columns=SECTORS)
    if not isinstance(window, int) or window < 2:
        raise ContractError("correlation window must be an integer of at least two")
    returns = panel.loc[:, SECTORS].pct_change(fill_method=None).iloc[1:]
    entries: list[tuple[pd.Timestamp, float | None]] = []
    upper = np.triu_indices(len(SECTORS), k=1)
    for end in range(window - 1, len(returns)):
        sample = returns.iloc[end - window + 1 : end + 1]
        matrix = sample.corr().to_numpy(dtype=float)
        pairs = matrix[upper]
        value = float(pairs.mean()) if np.isfinite(pairs).all() else None
        entries.append((returns.index[end], value))
    windows = _window_summaries(entries)
    return {
        "definition": "mean_of_55_unique_pairwise_pearson_correlations",
        "trailing_sessions": int(window),
        "windows": windows,
        "recent_20_vs_prior_252": _recent_prior_comparison(windows),
    }


def macd_bullish_crosses(
    closes: pd.Series, *, min_completed_bars: int = MACD_MIN_COMPLETED_BARS
) -> pd.Series:
    """Return eligible bullish histogram crosses on completed bars only."""
    if not isinstance(min_completed_bars, int) or min_completed_bars <= 0:
        raise ContractError("min_completed_bars must be a positive integer")
    values = pd.to_numeric(closes, errors="coerce").astype(float)
    if values.empty or not np.isfinite(values.to_numpy()).all() or (values <= 0).any():
        raise ContractError("MACD closes must be finite and positive")
    fast = values.ewm(span=12, adjust=False).mean()
    slow = values.ewm(span=26, adjust=False).mean()
    macd = fast - slow
    signal = macd.ewm(span=9, adjust=False).mean()
    histogram = macd - signal
    cross = (histogram > 0) & (histogram.shift(1) <= 0)
    eligible = pd.Series(
        np.arange(len(values), dtype=int) >= min_completed_bars - 1,
        index=values.index,
    )
    result = cross.loc[cross & eligible].astype(bool)
    result.name = "bullish_cross"
    return result


def _signal_cell(rows: list[dict[str, Any]], *, latest_dates: int | None) -> dict[str, Any]:
    dates = sorted({row["signal_date"] for row in rows})
    selected_dates = set(dates[-latest_dates:]) if latest_dates is not None else set(dates)
    selected = [row for row in rows if row["signal_date"] in selected_dates]
    absolute = np.asarray([row["absolute_return"] for row in selected], dtype=float)
    relative = np.asarray([row["spy_relative_return"] for row in selected], dtype=float)
    measured = len(selected) >= MIN_OBSERVATIONS
    return {
        "state": "MEASURED" if measured else "INSUFFICIENT_SIGNALS",
        "unique_signal_dates": int(len(selected_dates)),
        "n": int(len(selected)),
        "start_date": _iso_date(min(selected_dates)) if selected_dates else None,
        "end_date": _iso_date(max(selected_dates)) if selected_dates else None,
        "median_absolute_return": float(np.median(absolute)) if measured else None,
        "mean_absolute_return": float(absolute.mean()) if measured else None,
        "positive_absolute_rate": float((absolute > 0).mean()) if measured else None,
        "median_spy_relative_return": float(np.median(relative)) if measured else None,
        "mean_spy_relative_return": float(relative.mean()) if measured else None,
        "positive_spy_relative_rate": float((relative > 0).mean()) if measured else None,
    }


def _signal_windows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        "all": _signal_cell(rows, latest_dates=None),
        "recent_20": _signal_cell(rows, latest_dates=20),
        "recent_60": _signal_cell(rows, latest_dates=60),
    }


def _outcome_rows(
    panel: pd.DataFrame,
    crosses_by_symbol: dict[str, pd.Series],
    horizon: int,
) -> list[dict[str, Any]]:
    positions = {date: position for position, date in enumerate(panel.index)}
    rows: list[dict[str, Any]] = []
    for symbol in SECTORS:
        for signal_date in crosses_by_symbol[symbol].index:
            position = positions.get(signal_date)
            if position is None or position + horizon >= len(panel):
                continue
            sector_return = float(
                panel[symbol].iloc[position + horizon] / panel[symbol].iloc[position] - 1.0
            )
            spy_return = float(
                panel["SPY"].iloc[position + horizon] / panel["SPY"].iloc[position] - 1.0
            )
            rows.append(
                {
                    "symbol": symbol,
                    "signal_date": signal_date,
                    "outcome_date": panel.index[position + horizon],
                    "absolute_return": sector_return,
                    "spy_relative_return": sector_return - spy_return,
                }
            )
    return rows


def _phase_control(panel: pd.DataFrame, sessions: int, phase: int) -> tuple[dict[str, Any], dict[int, list[dict[str, Any]]]]:
    bars = aggregate_completed_bars(panel, sessions=sessions, phase=phase)
    crosses = {
        symbol: macd_bullish_crosses(bars[symbol], min_completed_bars=MACD_MIN_COMPLETED_BARS)
        for symbol in SECTORS
    }
    outcome_rows = {
        horizon: _outcome_rows(panel, crosses, horizon) for horizon in FORWARD_HORIZONS
    }
    return (
        {
            "sessions": int(sessions),
            "phase": int(phase),
            "completed_bars": int(len(bars)),
            "first_completed_bar": _iso_date(bars.index[0]) if len(bars) else None,
            "last_completed_bar": _iso_date(bars.index[-1]) if len(bars) else None,
            "cross_counts": {symbol: int(len(crosses[symbol])) for symbol in SECTORS},
            "outcomes": {
                str(horizon): _signal_windows(outcome_rows[horizon])
                for horizon in FORWARD_HORIZONS
            },
        },
        outcome_rows,
    )


def _hierarchy_descriptor(
    timeframes: dict[str, dict[str, Any]], horizon: int, window: str
) -> dict[str, Any]:
    medians: dict[str, float | None] = {}
    required = [("1D", "0"), ("2D", "0"), ("2D", "1"), ("3D", "0"), ("3D", "1"), ("3D", "2")]
    for timeframe, phase in required:
        cell = timeframes[timeframe]["phases"][phase]["outcomes"][str(horizon)][window]
        medians[f"{timeframe}.p{phase}"] = (
            cell["median_spy_relative_return"] if cell["state"] == "MEASURED" else None
        )
    if any(value is None for value in medians.values()):
        return {"label": "INSUFFICIENT_SIGNALS", "medians": medians}
    one_day = medians["1D.p0"]
    slower = [value for key, value in medians.items() if key != "1D.p0"]
    assert one_day is not None and all(value is not None for value in slower)
    if one_day > max(slower):
        label = "ONE_DAY_ABOVE_ALL_SLOWER_PHASES"
    elif one_day < min(slower):
        label = "ONE_DAY_BELOW_ALL_SLOWER_PHASES"
    else:
        label = "MIXED_PHASES"
    return {"label": label, "medians": medians}


def macd_control(panel: pd.DataFrame) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run phase-complete 1D/2D/3D MACD diagnostics and hierarchy descriptors."""
    _require_panel(panel)
    timeframes: dict[str, dict[str, Any]] = {}
    pooled_rows: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for sessions in (1, 2, 3):
        key = f"{sessions}D"
        phases: dict[str, dict[str, Any]] = {}
        for phase in range(sessions):
            phase_result, rows_by_horizon = _phase_control(panel, sessions, phase)
            phases[str(phase)] = phase_result
            for horizon, rows in rows_by_horizon.items():
                pooled_rows.setdefault((key, horizon), []).extend(rows)
        timeframes[key] = {
            "sessions": sessions,
            "phases": phases,
            "phase_pooled_non_independent": {
                str(horizon): _signal_windows(pooled_rows[(key, horizon)])
                for horizon in FORWARD_HORIZONS
            },
        }
    hierarchy = {
        str(horizon): {
            window: _hierarchy_descriptor(timeframes, horizon, window)
            for window in SIGNAL_WINDOWS
        }
        for horizon in FORWARD_HORIZONS
    }
    return (
        {
            "parameters": {
                "fast_span": 12,
                "slow_span": 26,
                "signal_span": 9,
                "adjust": False,
                "minimum_completed_bars": MACD_MIN_COMPLETED_BARS,
                "forward_horizons_daily_sessions": list(FORWARD_HORIZONS),
            },
            "timeframes": timeframes,
        },
        hierarchy,
    )


def _history_quality(panel: pd.DataFrame) -> dict[str, Any]:
    completed_by_phase: dict[str, int] = {}
    eligible_position_by_phase: dict[str, int] = {}
    forward_available_by_phase: dict[str, int] = {}
    for sessions in (1, 2, 3):
        for phase in range(sessions):
            key = f"{sessions}D.p{phase}"
            completed_by_phase[key] = int(
                len(aggregate_completed_bars(panel, sessions=sessions, phase=phase))
            )
            position = phase + sessions * MACD_MIN_COMPLETED_BARS - 1
            eligible_position_by_phase[key] = int(position)
            forward_available_by_phase[key] = max(0, int(len(panel) - 1 - position))
    enough = all(
        completed_by_phase[f"3D.p{phase}"] >= MACD_MIN_COMPLETED_BARS
        and forward_available_by_phase[f"3D.p{phase}"] >= max(FORWARD_HORIZONS)
        for phase in range(3)
    )
    return {
        "state": "MEASURED" if enough else "INSUFFICIENT_HISTORY",
        "common_sessions": int(len(panel)),
        "completed_bars_by_phase": completed_by_phase,
        "latest_eligible_signal_position_by_phase": eligible_position_by_phase,
        "daily_forward_sessions_available_by_phase": forward_available_by_phase,
        "minimum_completed_bars": MACD_MIN_COMPLETED_BARS,
        "largest_forward_horizon_daily_sessions": max(FORWARD_HORIZONS),
    }


def _validate_source_receipt(panel: pd.DataFrame, receipt: dict[str, Any]) -> None:
    try:
        common_rows = int(receipt["common_rows"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError("source receipt requires common_rows") from exc
    expected_first = _iso_date(panel.index[0])
    expected_last = _iso_date(panel.index[-1])
    if common_rows != len(panel):
        raise ContractError("source receipt common_rows disagrees with price panel")
    if receipt.get("first_session") != expected_first:
        raise ContractError("source receipt first_session disagrees with price panel")
    if receipt.get("last_session") != expected_last:
        raise ContractError("source receipt last_session disagrees with price panel")
    if not isinstance(receipt.get("source_revision"), str) or not receipt["source_revision"]:
        raise ContractError("source receipt requires source_revision")
    files = receipt.get("files")
    if not isinstance(files, dict) or any(symbol not in files for symbol in ALL_SYMBOLS):
        raise ContractError("source receipt requires every sector and benchmark file")
    for symbol in ALL_SYMBOLS:
        sha = files[symbol].get("sha256") if isinstance(files[symbol], dict) else None
        try:
            valid_sha = isinstance(sha, str) and len(sha) == 64 and int(sha, 16) >= 0
        except ValueError:
            valid_sha = False
        if not valid_sha:
            raise ContractError(f"source receipt has invalid sha256 for {symbol}")


def build_result(
    panel: pd.DataFrame, receipt: dict[str, Any], produced_at: str
) -> dict[str, Any]:
    """Compose the strict deterministic RPH-1 result from a normalized panel."""
    _require_panel(panel)
    _validate_source_receipt(panel, receipt)
    macd, hierarchy = macd_control(panel)
    return {
        "schema_version": SCHEMA,
        "operation_key": OPERATION_KEY,
        "produced_at": produced_at,
        "source": receipt,
        "parameters": {
            "sectors": list(SECTORS),
            "benchmark": "SPY",
            "leadership_lookbacks_sessions": [5, 21],
            "leadership_horizons_sessions": list(LEADERSHIP_HORIZONS),
            "summary_windows": list(SUMMARY_WINDOWS),
            "minimum_observations": MIN_OBSERVATIONS,
        },
        "quality": _history_quality(panel),
        "leadership": {
            "5": leadership_surface(panel, lookback=5),
            "21": leadership_surface(panel, lookback=21),
        },
        "dispersion": dispersion_control(panel),
        "correlation": correlation_control(panel),
        "macd_control": macd,
        "hierarchy": hierarchy,
        "authority": dict(AUTHORITY),
        "limitations": [
            "Daily repository Yahoo closes are an archive control, not exact vendor-chart parity.",
            "MACD marks use signal-session closes and ignore execution, spread, slippage and latency.",
            "Sector ETF behavior does not prove current theme or constituent behavior.",
            "Every result is research/display context only and cannot rank, gate, size or trade.",
        ],
    }


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(result: dict[str, Any]) -> str:
    """Render a deterministic bounded report without promoting trading authority."""
    source = result["source"]
    quality = result["quality"]
    lines = [
        "# Leadership Persistence RPH-1 — Daily Sector Control",
        "",
        f"**Operation:** `{result['operation_key']}`",
        "",
        f"**Produced at:** `{result['produced_at']}`",
        "",
        "**Authority:** research/display context only; no rank, gate, size, trade, Prophet or Oracle authority.",
        "",
        "## Source and quality",
        "",
        f"- Source revision: `{source.get('source_revision')}`",
        f"- Common sessions: {source.get('common_rows', quality['common_sessions'])}",
        f"- Retained range: {source.get('first_session')} through {source.get('last_session')}",
        f"- History state: `{quality['state']}`",
        "",
        "## Leadership surface",
        "",
        "| Lookback | Horizon | Recent rank rho | Recent predictive rho | Recent top-three retention |",
        "|---:|---:|---:|---:|---:|",
    ]
    for lookback in ("5", "21"):
        for horizon in LEADERSHIP_HORIZONS:
            cell = result["leadership"][lookback]["horizons"][str(horizon)]
            rank = cell["rank_persistence"]["recent_20"]
            predictive = cell["predictive_persistence"]["recent_20"]
            retention = cell["top3_retention"]["recent_20"]
            lines.append(
                f"| {lookback} | {horizon} | {_fmt(rank['mean'])} | "
                f"{_fmt(predictive['mean'])} | {_fmt(retention['mean'])} |"
            )

    dispersion = result["dispersion"]["recent_20_vs_prior_252"]
    correlation = result["correlation"]["recent_20_vs_prior_252"]
    lines.extend(
        [
            "",
            "## Dispersion and correlation controls",
            "",
            f"- Dispersion recent-minus-prior mean: {_fmt(dispersion['mean_difference'])}",
            f"- Dispersion recent/prior mean ratio: {_fmt(dispersion['mean_ratio'])}",
            f"- Correlation recent-minus-prior mean: {_fmt(correlation['mean_difference'])}",
            f"- Correlation recent/prior mean ratio: {_fmt(correlation['mean_ratio'])}",
            "",
            "## Phase-robust MACD hierarchy",
            "",
            "| Forward horizon | All | Recent 20 signal dates | Recent 60 signal dates |",
            "|---:|---|---|---|",
        ]
    )
    for horizon in FORWARD_HORIZONS:
        cells = result["hierarchy"][str(horizon)]
        lines.append(
            f"| {horizon} | `{cells['all']['label']}` | "
            f"`{cells['recent_20']['label']}` | `{cells['recent_60']['label']}` |"
        )

    lines.extend(["", "## Boundaries", ""])
    for item in result["limitations"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "The hierarchy is archive-specific descriptive evidence. It does not choose a production timeframe or create an entry instruction.",
            "",
        ]
    )
    return "\n".join(lines)
