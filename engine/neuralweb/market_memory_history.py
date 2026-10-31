"""Descriptive daily historical experience inside the existing Market Memory.

Pure, network-free calculations. Inputs must be qualified by their existing
Data OS reader before this module is used by an artifact builder. No calculation
here grants PIT, identity, redistribution, ranking, or trading authority.
All horizons are OBSERVED BARS, not asserted exchange sessions. Source revisions
and adjustment vintages belong to the caller's retained input evidence.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
import math
import re
import statistics
from typing import Any

HISTORY_SCHEMA = "market_memory.daily_history.v1"
FEATURE_VERSION = "market_memory.descriptive_observed_bars.v1"
RETURN_HORIZONS = (1, 5, 21, 63)
MA_HORIZONS = (20, 50, 200)
_SYMBOL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,95}\Z")
BASES = frozenset({"raw", "tradj"})


class HistoricalExperienceError(ValueError):
    """Malformed or over-budget historical composition; never silently repaired."""


def _date(value: Any) -> str:
    if type(value) is not str:
        raise HistoricalExperienceError("explicit ISO market date required")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HistoricalExperienceError("explicit ISO market date required") from exc
    if parsed.isoformat() != value:
        raise HistoricalExperienceError("canonical ISO market date required")
    return value


def _range(start: str, end: str, basis: str) -> str:
    if _date(start) > _date(end):
        raise HistoricalExperienceError("reversed date range")
    if basis not in BASES:
        raise HistoricalExperienceError("explicit raw or tradj price basis required")
    return f"close_{basis}"


def _number(value: Any, what: str, *, positive: bool) -> float | None:
    if value is None:
        return None
    if type(value) not in (int, float):
        raise HistoricalExperienceError(f"invalid {what}: finite number or null required")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise HistoricalExperienceError(f"invalid {what}") from exc
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise HistoricalExperienceError(f"invalid {what}: finite nonnegative value required")
    return number


def _volume(value: Any) -> int | None:
    """Preserve exact raw share counts; a floating-point hint cannot invent bits."""
    if value is None:
        return None
    if type(value) is int:
        if 0 <= value <= 2**63 - 1:
            return value
    elif type(value) is float and math.isfinite(value):
        if 0 <= value <= 2**53 and value.is_integer():
            return int(value)
    raise HistoricalExperienceError("invalid volume: exact nonnegative int64 shares required")


def _series(data: Mapping, price: str, max_total_rows: int) -> dict:
    if not isinstance(data, Mapping) or not 1 <= len(data) <= 256:
        raise HistoricalExperienceError("one to 256 explicitly selected vendor symbols required")
    if type(max_total_rows) is not int or not 1 <= max_total_rows <= 1_000_000:
        raise HistoricalExperienceError("invalid total row budget")
    result: dict[str, tuple[list[str], list, list]] = {}
    total = 0
    for symbol, source in data.items():
        if type(symbol) is not str or not _SYMBOL.fullmatch(symbol):
            raise HistoricalExperienceError("invalid vendor symbol")
        if not isinstance(source, Sequence) or isinstance(source, (str, bytes)):
            raise HistoricalExperienceError("explicit bounded price sequence required")
        total += len(source)
        if total > max_total_rows:
            raise HistoricalExperienceError("historical total row budget exceeded")
        days, prices, volumes = [], [], []
        for row in source:
            if not isinstance(row, Mapping) or price not in row:
                raise HistoricalExperienceError("source missing requested price basis")
            day = _date(row.get("market_date"))
            if days and day <= days[-1]:
                raise HistoricalExperienceError("market dates must be strictly increasing")
            days.append(day)
            prices.append(_number(row[price], "price", positive=True))
            volumes.append(_volume(row.get("volume_raw")))
        result[symbol] = days, prices, volumes
    return result


def _pct(last: float | None, first: float | None) -> float | None:
    if last is None or first is None or first == 0:
        return None
    value = (last / first - 1.0) * 100.0
    return value if math.isfinite(value) else None


def _put(row: dict, key: str, value: float | None, reason: str) -> None:
    if value is not None and not math.isfinite(value):
        value, reason = None, "nonfinite_calculation"
    row[key] = value
    if value is None:
        row["missing"][key] = reason


def _window(values: list, index: int, length: int) -> tuple[list, str]:
    if index + 1 < length:
        return [], "insufficient_history"
    selected = values[index - length + 1:index + 1]
    if any(value is None for value in selected):
        return [], "missing_source_value"
    return selected, "nonfinite_calculation"


def build_daily_rows(
    data: Mapping[str, Sequence[Mapping[str, Any]]], *, start: str, end: str,
    benchmark: str, basis: str, max_total_rows: int = 1_000_000,
) -> list[dict[str, Any]]:
    """Compose outcome-free rows, using no observation later than each row.

    Benchmark-relative returns compare the SAME endpoint dates, not unrelated
    shifts of two gapped series. Warmup is loaded before the requested interval.
    Volatility is an unannualized sample standard deviation of observed-bar
    percentage returns; there is no fictitious 252-session continuity guarantee.
    """
    price = _range(start, end, basis)
    series = _series(data, price, max_total_rows)
    if benchmark not in series:
        raise HistoricalExperienceError("benchmark must be in explicit source universe")
    benchmark_prices = dict(zip(series[benchmark][0], series[benchmark][1]))
    output = []
    for symbol in sorted(series):
        days, values, volumes = series[symbol]
        for i, day in enumerate(days):
            if not start <= day <= end:
                continue
            row = {"market_date": day, "vendor_symbol": symbol,
                   price: values[i], "volume_raw": volumes[i], "missing": {}}
            if values[i] is None:
                row["missing"][price] = "missing_source_value"
            if volumes[i] is None:
                row["missing"]["volume_raw"] = "missing_source_value"
            for horizon in RETURN_HORIZONS:
                enough = i >= horizon
                value = _pct(values[i], values[i-horizon]) if enough else None
                reason = "insufficient_history" if not enough else "missing_source_value"
                if enough and values[i] is not None and values[i-horizon] is not None:
                    reason = "nonfinite_calculation"
                _put(row, f"return_{horizon}ob_pct", value, reason)
            for horizon in MA_HORIZONS:
                window, reason = _window(values, i, horizon)
                try:
                    value = _pct(values[i], statistics.fmean(window)) if window else None
                except (ArithmeticError, ValueError):
                    value, reason = None, "nonfinite_calculation"
                _put(row, f"sma_distance_{horizon}ob_pct", value, reason)
            window, reason = _window(values, i, 22)
            returns = [_pct(b, a) for a, b in zip(window, window[1:])]
            try:
                vol = statistics.stdev(returns) if len(returns) == 21 and None not in returns else None
            except (ArithmeticError, ValueError):
                vol = None
            _put(row, "realized_volatility_21ob_pct", vol, reason)
            window, reason = _window(values, i, 252)
            drawdown = _pct(values[i], max(window)) if window else None
            _put(row, "drawdown_252ob_pct", drawdown, reason)
            # Compare today's volume with the preceding 20 observations, not
            # a denominator including the event we are describing.
            window, reason = _window(volumes, i - 1, 20)
            ratio = None
            if window and volumes[i] is not None:
                try:
                    mean = statistics.fmean(window)
                    ratio = volumes[i] / mean if mean else None
                    if not mean:
                        reason = "zero_volume_baseline"
                except (ArithmeticError, ValueError):
                    reason = "nonfinite_calculation"
            elif window:
                reason = "missing_source_value"
            _put(row, "volume_ratio_20ob", ratio, reason)
            relative = None
            reason = "insufficient_history"
            if i >= 21:
                first = days[i - 21]
                if first not in benchmark_prices or day not in benchmark_prices:
                    reason = "benchmark_date_missing"
                else:
                    baseline = _pct(benchmark_prices[day], benchmark_prices[first])
                    own = row["return_21ob_pct"]
                    relative = own - baseline if own is not None and baseline is not None else None
                    reason = "missing_source_value"
            _put(row, "relative_return_21ob_pp", relative, reason)
            output.append(row)
    return sorted(output, key=lambda row: (row["market_date"], row["vendor_symbol"]))


def build_outcome_rows(
    data: Mapping[str, Sequence[Mapping[str, Any]]], *, start: str, end: str,
    basis: str, horizons: tuple[int, ...] = (1, 5, 21, 63),
    max_total_rows: int = 1_000_000,
) -> list[dict[str, Any]]:
    """Separate evaluator output; never passed to the historical state builder.

    Max adverse excursion is the lowest close relative to the entry close,
    bounded above by zero. It is NOT a peak-to-trough drawdown of a trade path.
    Right-censored horizons remain null; no optimistic dropping of late rows.
    """
    price = _range(start, end, basis)
    series = _series(data, price, max_total_rows)
    if (not isinstance(horizons, tuple) or not 1 <= len(horizons) <= 10
            or any(type(h) is not int or not 1 <= h <= 252 for h in horizons)
            or len(set(horizons)) != len(horizons)):
        raise HistoricalExperienceError("distinct bounded integer outcome horizons required")
    output = []
    for symbol in sorted(series):
        days, values, _ = series[symbol]
        for i, day in enumerate(days):
            if not start <= day <= end:
                continue
            row = {"market_date": day, "vendor_symbol": symbol, "missing": {}}
            for horizon in horizons:
                ret = drawdown = None
                if i + horizon >= len(values):
                    reason = "right_censored"
                else:
                    window = values[i:i + horizon + 1]
                    reason = "missing_source_value"
                    if None not in window:
                        ret = _pct(window[-1], window[0])
                        drawdown = _pct(min(window), window[0])
                        reason = "nonfinite_calculation"
                _put(row, f"forward_return_{horizon}ob_pct", ret, reason)
                _put(row, f"forward_max_drawdown_{horizon}ob_pct", drawdown, reason)
            output.append(row)
    return sorted(output, key=lambda row: (row["market_date"], row["vendor_symbol"]))


def select_day(rows: Sequence[Mapping[str, Any]], market_date: str) -> list[dict]:
    """Exact day lookup. No nearest-date or latest-value fallback."""
    target = _date(market_date)
    selected = []
    for row in rows:
        if row.get("market_date") == target:
            if any(str(key).startswith(("forward_", "outcome")) for key in row):
                raise HistoricalExperienceError("outcomes cannot enter a historical state selection")
            selected.append(dict(row))
    return selected
