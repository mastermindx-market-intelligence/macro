"""Pure primitives for Terminal Tactical Intelligence retrospective research.

No network, clock, filesystem, signal emission, or lifecycle authority lives here.
All inputs are caller-supplied five-minute frames and frozen config dictionaries.
"""
from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

BAR_SECONDS = 300
_REQUIRED = ("o", "h", "l", "c", "v")


def _finite(value: object) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, (bool, np.bool_)) and math.isfinite(float(value))


def _validate_index(frame: pd.DataFrame) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise ValueError("frame_required")
    if any(col not in frame.columns for col in _REQUIRED):
        raise ValueError("missing_ohlcv_column")
    if frame.index.has_duplicates:
        raise ValueError("duplicate_epoch")
    if not frame.index.is_monotonic_increasing:
        raise ValueError("unordered_epoch")
    if any(not isinstance(x, (int, np.integer)) for x in frame.index):
        raise ValueError("integer_epoch_required")


def _validate_rows(frame: pd.DataFrame) -> None:
    _validate_index(frame)
    for row in frame.loc[:, _REQUIRED].itertuples(index=False, name=None):
        o, h, low, c, v = row
        if not all(_finite(x) for x in row):
            raise ValueError("invalid_ohlcv")
        o, h, low, c, v = map(float, row)
        if min(o, h, low, c) <= 0 or v < 0 or not (low <= min(o, c) <= max(o, c) <= h):
            raise ValueError("invalid_ohlcv")


def closed_prefix(frame: pd.DataFrame, cutoff_utc: int) -> pd.DataFrame:
    """Return completed five-minute bars only; future row content/duplicates are irrelevant."""
    if not isinstance(frame, pd.DataFrame) or any(col not in frame.columns for col in _REQUIRED):
        raise ValueError("frame_required")
    if not isinstance(cutoff_utc, (int, np.integer)) or isinstance(cutoff_utc, (bool, np.bool_)):
        raise ValueError("integer_cutoff_required")
    if any(not isinstance(x, (int, np.integer)) for x in frame.index):
        raise ValueError("integer_epoch_required")
    mask = (frame.index.to_numpy(dtype="int64") + BAR_SECONDS) <= int(cutoff_utc)
    view = frame.loc[mask].copy(deep=True)
    _validate_index(view)
    return view


def segment_features(frame: pd.DataFrame) -> dict[str, Any]:
    """Describe one observed extended-session segment using positive-volume bars."""
    _validate_rows(frame)
    base: dict[str, Any] = {
        "input_rows": int(len(frame)), "observations": 0, "return": None,
        "efficiency": None, "above_bar_vwap_fraction": None, "bar_vwap_proxy": None,
        "first_open": None, "last_close": None, "low": None, "high": None,
        "volume": 0.0, "span_minutes": None, "max_gap_minutes": None,
        "price_reference": "hlc3_volume_proxy_not_trade_vwap",
    }
    evidence = frame.loc[frame["v"].astype(float) > 0].copy()
    if evidence.empty:
        return base
    starts = evidence.index.to_numpy(dtype="int64")
    first_open = float(evidence.iloc[0]["o"])
    last_close = float(evidence.iloc[-1]["c"])
    closes = evidence["c"].astype(float).to_numpy()
    path = abs(closes[0] - first_open)
    if len(closes) > 1:
        path += float(np.abs(np.diff(closes)).sum())
    signed_move = last_close - first_open
    efficiency = 0.0 if path == 0 else signed_move / path
    volume = evidence["v"].astype(float).to_numpy()
    typical = (evidence["h"].astype(float).to_numpy() + evidence["l"].astype(float).to_numpy() + closes) / 3.0
    cumulative_volume = np.cumsum(volume)
    expanding_proxy = np.cumsum(typical * volume) / cumulative_volume
    if len(starts) > 1:
        gaps = (starts[1:] - (starts[:-1] + BAR_SECONDS)) / 60.0
        max_gap = float(max(0.0, float(np.max(gaps))))
    else:
        max_gap = 0.0
    base.update({
        "observations": int(len(evidence)),
        "return": last_close / first_open - 1.0,
        "efficiency": float(efficiency),
        "above_bar_vwap_fraction": float(np.mean(closes > expanding_proxy)),
        "bar_vwap_proxy": float(expanding_proxy[-1]),
        "first_open": first_open, "last_close": last_close,
        "low": float(evidence["l"].astype(float).min()),
        "high": float(evidence["h"].astype(float).max()),
        "volume": float(volume.sum()),
        "span_minutes": float((starts[-1] + BAR_SECONDS - starts[0]) / 60.0),
        "max_gap_minutes": max_gap,
    })
    return base


def _known_number(value: object) -> float | None:
    return float(value) if _finite(value) else None


def _persistent(segment: Mapping[str, Any], cfg: Mapping[str, Any]) -> bool:
    ret = _known_number(segment.get("return")); eff = _known_number(segment.get("efficiency")); above = _known_number(segment.get("above_bar_vwap_fraction"))
    return ret is not None and eff is not None and above is not None and ret > 0 and eff >= float(cfg["path_efficiency_floor"]) and above >= float(cfg["above_expanding_bar_vwap_floor"])


def select_arms(feature_row: Mapping[str, Any], cfg: Mapping[str, Any]) -> tuple[str, ...]:
    if feature_row.get("comparable") is not True:
        return ()
    ah = feature_row.get("ah") or {}; pre = feature_row.get("pre") or {}
    persistent = _persistent(ah, cfg) and _persistent(pre, cfg)
    prior_return = _known_number(feature_row.get("prior_return")); three = _known_number(feature_row.get("three_day_change")); atr = _known_number(feature_row.get("atr20"))
    weakness = (prior_return is not None and prior_return < 0) or (three is not None and atr is not None and atr > 0 and three <= -float(cfg["weak_three_day_atr"]) * atr)
    prior_close = _known_number(feature_row.get("prior_close")); pre_close = _known_number(pre.get("last_close")); pre_ret = _known_number(pre.get("return")); pre_proxy = _known_number(pre.get("bar_vwap_proxy"))
    gap_up = prior_close is not None and pre_close is not None and pre_ret is not None and pre_close > prior_close and pre_ret > 0
    reclaim = weakness and pre_close is not None and pre_proxy is not None and pre_close > pre_proxy
    opening = feature_row.get("opening") or {}
    open_accept = False
    if persistent and opening.get("complete") is True:
        oc = _known_number(opening.get("last_close")); ov = _known_number(opening.get("bar_vwap_proxy")); ol = _known_number(opening.get("low")); pl = _known_number(pre.get("low"))
        open_accept = None not in (oc, ov, ol, pl, pre_close) and oc > pre_close and oc > ov and ol >= pl
    flags = {
        "ALL_EARLY": True, "GAP_UP": gap_up, "PERSISTENT": persistent,
        "WEAKNESS_PERSISTENT": persistent and weakness, "WEAKNESS_RECLAIM": reclaim,
        "ALL_LATE": True, "PERSISTENT_OPEN_ACCEPT": open_accept,
    }
    return tuple(name for name in cfg["selectors"] if flags.get(name, False))


def first_touch(frame: pd.DataFrame, entry: float, atr: float) -> str:
    _validate_index(frame)
    if not (_finite(entry) and _finite(atr)) or float(entry) <= 0 or float(atr) <= 0:
        raise ValueError("invalid_entry_or_atr")
    target = float(entry) + 0.5 * float(atr); adverse = float(entry) - 0.5 * float(atr)
    for high, low in frame.loc[:, ["h", "l"]].itertuples(index=False, name=None):
        if not (_finite(high) and _finite(low)) or float(low) <= 0 or float(high) < float(low):
            raise ValueError("invalid_path_bar")
        hit_target = float(high) >= target; hit_adverse = float(low) <= adverse
        if hit_target and hit_adverse: return "same_bar_ambiguous"
        if hit_target: return "target_first"
        if hit_adverse: return "adverse_first"
    return "neither"


def _censored(reason: str = "path_unavailable") -> dict[str, Any]:
    return {"status": "censored", "reason": reason, "raw_return": None, "benchmark_return": None,
            "beta_residual": None, "mfe": None, "mae": None, "touch": None,
            "entry_open": None, "exit_close": None, "execution_proven": False}


def _frame_columns_and_integer_index(frame: pd.DataFrame) -> bool:
    return isinstance(frame, pd.DataFrame) and all(col in frame.columns for col in _REQUIRED) and all(isinstance(x, (int, np.integer)) for x in frame.index)


def _exactly_one(frame: pd.DataFrame, epoch: int) -> bool:
    return int(np.count_nonzero(frame.index.to_numpy() == int(epoch))) == 1


def fixed_outcome(stock: pd.DataFrame, benchmark: pd.DataFrame, entry_epoch: int, end_epoch: int,
                  beta: float | None, atr: float | None, expected_epochs: Sequence[int]) -> dict[str, Any]:
    """Measure one fixed price-reference outcome on the explicit expected path only."""
    expected = [int(x) for x in expected_epochs]
    if not expected or entry_epoch not in expected or any(x >= int(end_epoch) for x in expected):
        return _censored("invalid_expected_path")
    if not _frame_columns_and_integer_index(stock):
        return _censored("stock_structure_unavailable")
    if any(not _exactly_one(stock, x) for x in expected):
        return _censored("stock_path_missing_or_ambiguous")
    path = stock.loc[expected].copy()
    try:
        _validate_rows(path)
    except ValueError:
        return _censored("stock_path_invalid")
    entry = float(path.loc[entry_epoch, "o"]); exit_close = float(path.iloc[-1]["c"])
    raw = exit_close / entry - 1.0
    mfe = max(0.0, float(path["h"].astype(float).max()) / entry - 1.0)
    mae = min(0.0, float(path["l"].astype(float).min()) / entry - 1.0)
    bench_ret = None
    if _frame_columns_and_integer_index(benchmark) and all(_exactly_one(benchmark, x) for x in expected):
        bench_path = benchmark.loc[expected].copy()
        try:
            _validate_rows(bench_path)
        except ValueError:
            bench_path = None
        if bench_path is not None:
            bench_entry = float(bench_path.loc[entry_epoch, "o"])
            bench_ret = float(bench_path.iloc[-1]["c"]) / bench_entry - 1.0
    b = _known_number(beta)
    residual = raw - b * bench_ret if b is not None and b >= 0 and bench_ret is not None else None
    touch = first_touch(path, entry, float(atr)) if _known_number(atr) is not None and float(atr) > 0 else None
    return {"status": "available", "reason": None, "raw_return": raw, "benchmark_return": bench_ret,
            "beta_residual": residual, "mfe": mfe, "mae": mae, "touch": touch,
            "entry_open": entry, "exit_close": exit_close, "execution_proven": False}
