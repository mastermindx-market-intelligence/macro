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

# ---------------------------------------------------------------------------
# TTI R1-B v4 — causal fresh-low / exhaustion / confirmation primitives
# Pure research helpers only: no I/O, trial registration, outcome computation,
# event emission, lifecycle, ranking, sizing, or trade authority.
# ---------------------------------------------------------------------------

def _turn_row(frame: pd.DataFrame, epoch: int, *, positive_volume: bool = False) -> dict[str, float] | None:
    """Return one valid OHLCV row at ``epoch``; ambiguity/missingness is unavailable."""
    if not isinstance(frame, pd.DataFrame) or any(col not in frame.columns for col in _REQUIRED):
        return None
    try:
        mask = frame.index.to_numpy() == int(epoch)
    except Exception:
        return None
    if int(np.count_nonzero(mask)) != 1:
        return None
    raw = frame.loc[mask, _REQUIRED].iloc[0]
    vals = tuple(raw[col] for col in _REQUIRED)
    if not all(_finite(x) for x in vals):
        return None
    o, h, low, c, v = map(float, vals)
    if min(o, h, low, c) <= 0 or v < 0 or not (low <= min(o, c) <= max(o, c) <= h):
        return None
    if positive_volume and v <= 0:
        return None
    return {"o": o, "h": h, "l": low, "c": c, "v": v}


def _turn_number(cfg: Mapping[str, Any], key: str) -> float:
    value = cfg.get(key)
    if not _finite(value):
        raise ValueError(f"invalid_turn_config:{key}")
    return float(value)


def _turn_int(cfg: Mapping[str, Any], key: str) -> int:
    value = cfg.get(key)
    if not isinstance(value, (int, np.integer)) or isinstance(value, (bool, np.bool_)):
        raise ValueError(f"invalid_turn_config:{key}")
    return int(value)


_RTH_OPEN_MINUTE_ET = 9 * 60 + 30
_R1B_V4_STUDY_ID = "tti-r1b-exhaustion-reclaim-v4"


def _turn_clock_offsets(cfg: Mapping[str, Any]) -> tuple[int, int]:
    """Validate the frozen v4 machine contract and return minutes from RTH open."""
    if cfg.get("study_id") != _R1B_V4_STUDY_ID:
        raise ValueError("r1b_v4_study_id_required")
    if cfg.get("decision_grain") != "5m" or cfg.get("direction") != "long_only":
        raise ValueError("r1b_v4_direction_or_grain_mismatch")
    required_true = (
        "normal_rth_only", "strict_new_session_low",
        "candidate_positive_volume_required", "candidate_zero_range_is_unavailable",
        "running_low_positive_volume_only",
        "recent_impulse_all_three_bars_positive_volume",
        "confirmation_positive_volume_required",
    )
    if any(cfg.get(key) is not True for key in required_true):
        raise ValueError("r1b_v4_required_boolean_mismatch")
    start_et = _turn_int(cfg, "candidate_decision_start_minute_et")
    end_et = _turn_int(cfg, "candidate_decision_end_minute_et")
    start = start_et - _RTH_OPEN_MINUTE_ET
    end = end_et - _RTH_OPEN_MINUTE_ET
    if start < 5 or end < start or start % 5 or end % 5:
        raise ValueError("invalid_candidate_clock")
    return start, end


def _turn_candidate(
    frame: pd.DataFrame, *, candidate_epoch: int, session_open_epoch: int,
    previous_close: float, atr: float, cfg: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Candidate-time snapshot only; reads no bar after the candidate."""
    if not (_finite(previous_close) and float(previous_close) > 0 and _finite(atr) and float(atr) > 0):
        raise ValueError("invalid_previous_close_or_atr")
    if (int(candidate_epoch) - int(session_open_epoch)) % BAR_SECONDS != 0:
        raise ValueError("candidate_off_five_minute_grid")
    decision_epoch = int(candidate_epoch) + BAR_SECONDS
    decision_offset_minutes = int((decision_epoch - int(session_open_epoch)) // 60)
    start_offset, end_offset = _turn_clock_offsets(cfg)
    if decision_offset_minutes < start_offset or decision_offset_minutes > end_offset:
        return None

    # A missing/duplicate/malformed prefix can hide an earlier low.  Require one
    # structurally valid row at every expected timestamp through the candidate;
    # zero-volume prior rows remain non-price evidence and are excluded from Lpre.
    prefix: list[tuple[int, dict[str, float]]] = []
    for epoch in range(int(session_open_epoch), int(candidate_epoch) + 1, BAR_SECONDS):
        row = _turn_row(frame, epoch)
        if row is None:
            return None
        prefix.append((epoch, row))
    candidate = prefix[-1][1]
    if candidate["v"] <= 0 or candidate["h"] == candidate["l"]:
        return None
    prior_price_rows = [row for _epoch, row in prefix[:-1] if row["v"] > 0]
    if not prior_price_rows:
        return None
    pre_low = min(row["l"] for row in prior_price_rows)
    if not candidate["l"] < pre_low:
        return None

    trailing_n = _turn_int(cfg, "recent_impulse_bars")
    if trailing_n <= 0 or len(prefix) < trailing_n:
        return None
    trailing = [row for _epoch, row in prefix[-trailing_n:]]
    if any(row["v"] <= 0 for row in trailing):
        return None

    atr_f = float(atr)
    displacement = (float(previous_close) - candidate["l"]) / atr_f
    impulse = (trailing[0]["o"] - candidate["l"]) / atr_f
    if displacement < _turn_number(cfg, "base_displacement_atr_min"):
        return None
    if impulse < _turn_number(cfg, "recent_impulse_atr_min"):
        return None
    close_location = (candidate["c"] - candidate["l"]) / (candidate["h"] - candidate["l"])
    extension = (pre_low - candidate["l"]) / atr_f
    forming = (
        close_location >= _turn_number(cfg, "exhaustion_close_location_min")
        and extension <= _turn_number(cfg, "exhaustion_extension_atr_max")
    )
    latency = _turn_int(cfg, "execution_latency_bars_after_decision")
    if latency < 1:
        raise ValueError("processing_latency_must_be_positive")
    return {
        "candidate_epoch": int(candidate_epoch),
        "decision_epoch": decision_epoch,
        "entry_epoch": decision_epoch + latency * BAR_SECONDS,
        "candidate_low": candidate["l"],
        "episode_low": candidate["l"],
        "pre_candidate_running_low": pre_low,
        "reclaim_level": pre_low,
        "continuation_level": candidate["l"] - _turn_number(cfg, "continuation_extension_atr") * atr_f,
        "displacement_atr": displacement,
        "recent_impulse_atr": impulse,
        "close_location": close_location,
        "fresh_low_extension_atr": extension,
        "forming": bool(forming),
        "decision_offset_minutes": decision_offset_minutes,
        "processing_latency_bars": latency,
    }


def _turn_confirmation_race(
    frame: pd.DataFrame, candidate: Mapping[str, Any], *, cfg: Mapping[str, Any],
) -> dict[str, Any]:
    """First reclaim/continuation close in the frozen three-bar window."""
    window = _turn_int(cfg, "confirmation_window_bars")
    if window <= 0:
        raise ValueError("invalid_confirmation_window")
    episode_low = float(candidate["candidate_low"])
    for delay in range(1, window + 1):
        bar_epoch = int(candidate["candidate_epoch"]) + delay * BAR_SECONDS
        row = _turn_row(frame, bar_epoch, positive_volume=True)
        if row is None:
            return {"race": "unavailable", "confirmation_delay_bars": None,
                    "confirmation_bar_epoch": None, "episode_low": episode_low}
        episode_low = min(episode_low, row["l"])
        if row["c"] > float(candidate["reclaim_level"]):
            race = "reclaim"
        elif row["c"] <= float(candidate["continuation_level"]):
            race = "continuation"
        else:
            continue
        confirmation_decision = bar_epoch + BAR_SECONDS
        latency = _turn_int(cfg, "execution_latency_bars_after_decision")
        return {
            "race": race,
            "confirmation_delay_bars": delay,
            "confirmation_bar_epoch": bar_epoch,
            "decision_epoch": confirmation_decision,
            "entry_epoch": confirmation_decision + latency * BAR_SECONDS,
            "episode_low": episode_low,
        }
    return {"race": "expired", "confirmation_delay_bars": None,
            "confirmation_bar_epoch": None, "episode_low": episode_low}


def _turn_event(selector: str, candidate: Mapping[str, Any], *,
                race: Mapping[str, Any] | None = None) -> dict[str, Any]:
    row = dict(candidate)
    row["selector"] = str(selector)
    row["race"] = None if race is None else race.get("race")
    if race is not None and race.get("confirmation_bar_epoch") is not None:
        row["confirmation_bar_epoch"] = int(race["confirmation_bar_epoch"])
        row["confirmation_delay_bars"] = int(race["confirmation_delay_bars"])
        row["decision_epoch"] = int(race["decision_epoch"])
        row["entry_epoch"] = int(race["entry_epoch"])
        row["episode_low"] = float(race["episode_low"])
    else:
        row["confirmation_bar_epoch"] = None
        row["confirmation_delay_bars"] = None
    row.pop("forming", None)
    return row


def _turn_entry_reference(frame: pd.DataFrame, event: Mapping[str, Any]) -> dict[str, Any]:
    """Attach the delayed price-reference availability without gating the fire."""
    row = _turn_row(frame, int(event["entry_epoch"]), positive_volume=True)
    out = dict(event)
    out["entry_reference_available"] = row is not None
    out["entry_open"] = None if row is None else float(row["o"])
    return out


def _turn_candidates(frame: pd.DataFrame, *, session_open_epoch: int,
                     previous_close: float, atr: float,
                     cfg: Mapping[str, Any]) -> list[dict[str, Any]]:
    start, end = _turn_clock_offsets(cfg)
    out: list[dict[str, Any]] = []
    for decision_offset in range(start, end + 1, 5):
        candidate_epoch = int(session_open_epoch) + decision_offset * 60 - BAR_SECONDS
        candidate = _turn_candidate(
            frame, candidate_epoch=candidate_epoch, session_open_epoch=int(session_open_epoch),
            previous_close=previous_close, atr=atr, cfg=cfg)
        if candidate is not None:
            out.append(candidate)
    return out


def scan_long_turn_events(
    frame: pd.DataFrame, *, session_open_epoch: int, previous_close: float,
    atr: float, cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """First qualifying event per frozen v4 selector, with causal clocks."""
    selector_order = tuple(str(x) for x in cfg.get("selectors", ()))
    expected = {
        "BASE_FRESH_LOW", "EXHAUSTION_FORMING", "RECLAIM_ONLY",
        "EXHAUSTION_RECLAIM", "CONTINUATION_RISK",
    }
    if set(selector_order) != expected or len(selector_order) != len(expected):
        raise ValueError("invalid_r1b_selector_set")
    found: dict[str, dict[str, Any]] = {}
    for candidate in _turn_candidates(
        frame, session_open_epoch=session_open_epoch, previous_close=previous_close,
        atr=atr, cfg=cfg):
        if "BASE_FRESH_LOW" not in found:
            found["BASE_FRESH_LOW"] = _turn_entry_reference(frame, _turn_event("BASE_FRESH_LOW", candidate))
        if candidate["forming"] and "EXHAUSTION_FORMING" not in found:
            found["EXHAUSTION_FORMING"] = _turn_entry_reference(frame, _turn_event("EXHAUSTION_FORMING", candidate))

        need_race = any(name not in found for name in
                        ("RECLAIM_ONLY", "EXHAUSTION_RECLAIM", "CONTINUATION_RISK"))
        if not need_race:
            continue
        race = _turn_confirmation_race(frame, candidate, cfg=cfg)
        if race["race"] == "reclaim":
            if "RECLAIM_ONLY" not in found:
                found["RECLAIM_ONLY"] = _turn_entry_reference(frame, _turn_event("RECLAIM_ONLY", candidate, race=race))
            if candidate["forming"] and "EXHAUSTION_RECLAIM" not in found:
                found["EXHAUSTION_RECLAIM"] = _turn_entry_reference(
                    frame, _turn_event("EXHAUSTION_RECLAIM", candidate, race=race))
        elif race["race"] == "continuation" and "CONTINUATION_RISK" not in found:
            found["CONTINUATION_RISK"] = _turn_entry_reference(frame, _turn_event("CONTINUATION_RISK", candidate, race=race))
    return tuple(found[name] for name in selector_order if name in found)


def base_turn_control_census(
    frame: pd.DataFrame, *, session_open_epoch: int, previous_close: float,
    atr: float, cfg: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """First lawful BASE anchor per 30-minute session bin; future labels ignored."""
    width = _turn_int(cfg, "clock_bin_minutes")
    if width <= 0 or 390 % width != 0:
        raise ValueError("invalid_clock_bin")
    found: dict[int, dict[str, Any]] = {}
    for candidate in _turn_candidates(
        frame, session_open_epoch=session_open_epoch, previous_close=previous_close,
        atr=atr, cfg=cfg):
        clock_bin = int(candidate["decision_offset_minutes"] // width)
        if clock_bin in found:
            continue
        row = _turn_entry_reference(frame, _turn_event("BASE_FRESH_LOW", candidate))
        row["clock_bin"] = clock_bin
        found[clock_bin] = row
    return tuple(found[key] for key in sorted(found))
