from __future__ import annotations

import argparse
import json
import math
from bisect import bisect_left
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCHEMA = "skylit.r10.cross_instrument_mapping_feasibility/v2"
METHODS = ("additive_basis", "multiplicative_ratio")
REQUIRED_COLUMNS = ("source_ts", "target_ts", "source_price", "target_price")


class R10Refusal(ValueError):
    pass


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise R10Refusal(f"{label} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise R10Refusal(f"{label} must be a finite number") from exc
    if not math.isfinite(number):
        raise R10Refusal(f"{label} must be finite")
    return number


def _duration_ns(value: float, label: str, *, positive: bool) -> int:
    seconds = _finite_number(value, label)
    if seconds < 0 or (positive and seconds == 0):
        raise R10Refusal(f"{label} must be {'positive' if positive else 'non-negative'}")
    # Round the exact represented float to the nearest nanosecond, ties to even.
    # Python integers prevent overflow even when finite seconds * 1e9 would not.
    numerator, denominator = seconds.as_integer_ratio()
    quotient, remainder = divmod(numerator * 1_000_000_000, denominator)
    if remainder * 2 > denominator or (remainder * 2 == denominator and quotient % 2):
        quotient += 1
    if positive and quotient == 0:
        raise R10Refusal(f"{label} rounds below one nanosecond")
    return quotient


def _timestamps_ns(values: pd.Series, label: str) -> pd.Series:
    try:
        parsed = pd.to_datetime(values, utc=True, errors="coerce")
        parsed = parsed.astype("datetime64[ns, UTC]")
    except (TypeError, ValueError, OverflowError) as exc:
        raise R10Refusal(f"{label} must be representable UTC nanosecond timestamps") from exc
    if parsed.isna().any():
        raise R10Refusal(f"{label} contains invalid UTC nanosecond timestamps")
    return parsed


def _finite_mean(values: np.ndarray) -> float:
    try:
        total = math.fsum(float(value) for value in values)
    except OverflowError:
        # Only the exceptional intermediate-overflow path needs exact summation.
        # This also preserves tiny residuals when large signed errors cancel.
        total_exact = sum((Fraction.from_float(float(value)) for value in values), Fraction())
        return _finite_number(float(total_exact / len(values)), "mapping error mean")
    return _finite_number(total / len(values), "mapping error mean")


def _linear_nonnegative_quantile(values: np.ndarray, probability: float) -> float:
    ordered = np.sort(values)
    position = (len(ordered) - 1) * probability
    lower = int(math.floor(position))
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    left, right = float(ordered[lower]), float(ordered[upper])
    # Adjacent nonnegative values avoid overflow and preserve tiny quantiles.
    return _finite_number(left + (right - left) * weight, "mapping error quantile")


def _additive_error(source0: float, target0: float, source1: float, target1: float,
                    *, label: str = "additive mapping error") -> float:
    terms = (source1, -source0, -target1, target0)
    try:
        error = math.fsum(terms)
    except OverflowError:
        try:
            error = float(sum((Fraction.from_float(value) for value in terms), Fraction()))
        except OverflowError as exc:
            raise R10Refusal(f"{label} is not finite") from exc
    return _finite_number(error, label)


def _ratio_error(source: float, ratio: float, target: float) -> float:
    error = source * ratio - target
    if not math.isfinite(error):
        # A product can overflow even when its difference from target is finite.
        try:
            error = float(Fraction.from_float(source) * Fraction.from_float(ratio)
                          - Fraction.from_float(target))
        except OverflowError as exc:
            raise R10Refusal("multiplicative mapping error is not finite") from exc
    return _finite_number(error, "multiplicative mapping error")


def _clean_pairs(frame: pd.DataFrame, *, max_skew_seconds: float) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise R10Refusal(f"missing required columns: {missing}")
    duplicated = frame.columns[frame.columns.duplicated()]
    if any(column in REQUIRED_COLUMNS for column in duplicated):
        raise R10Refusal("duplicate required column labels")
    max_skew_seconds = _finite_number(max_skew_seconds, "max_skew_seconds")
    if max_skew_seconds < 0:
        raise R10Refusal("max_skew_seconds must be finite and non-negative")

    out = frame.loc[:, list(REQUIRED_COLUMNS)].copy()
    for col in ("source_ts", "target_ts"):
        out[col] = _timestamps_ns(out[col], col)
    for col in ("source_price", "target_price"):
        try:
            numeric = pd.to_numeric(out[col], errors="coerce")
            if np.iscomplexobj(numeric):
                raise R10Refusal(f"{col} must contain real prices")
            out[col] = numeric.astype(float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise R10Refusal(f"{col} must contain finite real prices") from exc

    invalid = (
        out["source_price"].isna()
        | out["target_price"].isna()
        | ~np.isfinite(out["source_price"])
        | ~np.isfinite(out["target_price"])
        | (out["source_price"] <= 0)
        | (out["target_price"] <= 0)
    )
    if invalid.any():
        raise R10Refusal(f"invalid synchronized price rows: {int(invalid.sum())}/{len(out)}")

    source_ns = out["source_ts"].astype("int64").tolist()
    target_ns = out["target_ts"].astype("int64").tolist()
    skew_ns = [abs(int(target) - int(source))
               for source, target in zip(source_ns, target_ns)]
    numerator, denominator = max_skew_seconds.as_integer_ratio()
    if any(skew * denominator > numerator * 1_000_000_000 for skew in skew_ns):
        worst = max(skew_ns) / 1e9
        raise R10Refusal(
            f"source/target timestamp skew exceeds gate: max={worst:.9g}s "
            f"gate={max_skew_seconds:.9g}s"
        )

    out["observed_at"] = out[["source_ts", "target_ts"]].max(axis=1)
    out["source_target_skew_seconds"] = [skew / 1e9 for skew in skew_ns]
    out = out.sort_values("observed_at", kind="mergesort").reset_index(drop=True)
    if out["observed_at"].duplicated().any():
        raise R10Refusal("duplicate synchronized observation timestamps")
    if len(out) < 8:
        raise R10Refusal("need at least 8 synchronized observations")
    return out

def _future_pairs(
    frame: pd.DataFrame,
    *,
    horizon_seconds: float,
    match_tolerance_seconds: float,
) -> pd.DataFrame:
    horizon_ns = _duration_ns(horizon_seconds, "horizon_seconds", positive=True)
    tolerance_ns = _duration_ns(match_tolerance_seconds, "match_tolerance_seconds", positive=False)
    timestamps = _timestamps_ns(frame["observed_at"], "observed_at")
    times_ns = [int(value) for value in timestamps.astype("int64")]
    if any(right <= left for left, right in zip(times_ns, times_ns[1:])):
        raise R10Refusal("synchronized observation timestamps must be strictly increasing")
    rows: list[dict[str, Any]] = []

    for i, t0 in enumerate(times_ns):
        wanted = t0 + horizon_ns
        j = bisect_left(times_ns, wanted)
        if j >= len(frame) or j <= i or times_ns[j] <= t0:
            continue
        overshoot = times_ns[j] - wanted
        if overshoot < 0 or overshoot > tolerance_ns:
            continue

        source0 = float(frame.at[i, "source_price"])
        target0 = float(frame.at[i, "target_price"])
        source1 = float(frame.at[j, "source_price"])
        target1 = float(frame.at[j, "target_price"])
        ratio0 = _finite_number(target0 / source0, "multiplicative ratio")
        if ratio0 <= 0:
            raise R10Refusal("multiplicative ratio is not representable as positive and finite")
        additive_error = _additive_error(source0, target0, source1, target1)
        ratio_error = _ratio_error(source1, ratio0, target1)

        rows.append({
            "origin_idx": i,
            "endpoint_idx": j,
            "origin_at": frame.at[i, "observed_at"],
            "endpoint_at": frame.at[j, "observed_at"],
            "match_overshoot_seconds": overshoot / 1e9,
            "additive_error": additive_error,
            "ratio_error": ratio_error,
        })

    return pd.DataFrame(rows)

def _method_stats(train: np.ndarray, test: np.ndarray) -> dict[str, Any]:
    try:
        train, test = np.asarray(train, dtype=float), np.asarray(test, dtype=float)
    except (TypeError, ValueError, OverflowError) as exc:
        raise R10Refusal("mapping errors must be finite one-dimensional arrays") from exc
    if train.ndim != 1 or test.ndim != 1:
        raise R10Refusal("mapping errors must be finite one-dimensional arrays")
    if train.size == 0 or test.size == 0:
        raise R10Refusal("temporal split leaves no train or test mapping observations")
    if not np.isfinite(train).all() or not np.isfinite(test).all():
        raise R10Refusal("mapping errors must be finite")
    train_abs, test_abs = np.abs(train), np.abs(test)
    q50 = _linear_nonnegative_quantile(train_abs, 0.50)
    q90 = _linear_nonnegative_quantile(train_abs, 0.90)
    q95 = _linear_nonnegative_quantile(train_abs, 0.95)
    scale = float(np.max(test_abs))
    rmse = 0.0 if scale == 0 else scale * math.sqrt(
        math.fsum((float(value) / scale) ** 2 for value in test) / len(test)
    )
    return {
        "train_n": int(train.size),
        "test_n": int(test.size),
        "train_abs_error_q50_target_points": q50,
        "train_abs_error_q90_target_points": q90,
        "train_abs_error_q95_target_points": q95,
        "test_mae_target_points": _finite_mean(test_abs),
        "test_rmse_target_points": _finite_number(rmse, "mapping error RMSE"),
        "test_bias_target_points": _finite_mean(test),
        "test_q90_interval_coverage": float(np.mean(test_abs <= q90)),
        "test_abs_error_q90_target_points": _linear_nonnegative_quantile(test_abs, 0.90),
        "test_abs_error_max_target_points": scale,
    }

def calibrate_mapping(
    frame: pd.DataFrame,
    *,
    source_instrument: str,
    target_instrument: str,
    target_contract: str | None = None,
    horizon_seconds: float = 900.0,
    max_skew_seconds: float = 2.0,
    match_tolerance_seconds: float = 5.0,
    train_fraction: float = 0.60,
    source_level: float | None = None,
) -> dict[str, Any]:
    if not source_instrument or not target_instrument:
        raise R10Refusal("source_instrument and target_instrument are required")
    if source_instrument == target_instrument:
        raise R10Refusal("source and target instruments must be distinct")
    train_fraction = _finite_number(train_fraction, "train_fraction")
    if not 0.5 <= train_fraction <= 0.9:
        raise R10Refusal("train_fraction must be within [0.5, 0.9]")

    pairs = _clean_pairs(frame, max_skew_seconds=max_skew_seconds)
    events = _future_pairs(
        pairs,
        horizon_seconds=horizon_seconds,
        match_tolerance_seconds=match_tolerance_seconds,
    )
    if events.empty:
        raise R10Refusal("no horizon-matched observations")

    split_idx = int(np.floor(len(pairs) * train_fraction))
    if split_idx < 2 or split_idx >= len(pairs) - 1:
        raise R10Refusal("temporal split is too small")

    # Purge any sample whose feature origin is in train but whose endpoint crosses
    # the temporal split. Test samples begin only once the origin itself is in the
    # untouched holdout region.
    train_events = events[events["endpoint_idx"] < split_idx].copy()
    test_events = events[events["origin_idx"] >= split_idx].copy()
    if train_events.empty or test_events.empty:
        raise R10Refusal("purged temporal split leaves no train or test events")

    method_stats = {
        "additive_basis": _method_stats(
            train_events["additive_error"].to_numpy(float),
            test_events["additive_error"].to_numpy(float),
        ),
        "multiplicative_ratio": _method_stats(
            train_events["ratio_error"].to_numpy(float),
            test_events["ratio_error"].to_numpy(float),
        ),
    }

    last = pairs.iloc[-1]
    source_now, target_now = float(last["source_price"]), float(last["target_price"])
    current_basis = _finite_number(target_now - source_now, "current additive basis")
    current_ratio = _finite_number(target_now / source_now, "current multiplicative ratio")
    if current_ratio <= 0:
        raise R10Refusal("current multiplicative ratio is not representable as positive and finite")
    current = {
        "observed_at": last["observed_at"].isoformat(),
        "source_price": float(last["source_price"]),
        "target_price": float(last["target_price"]),
        "source_target_skew_seconds": float(last["source_target_skew_seconds"]),
        "additive_basis_target_points": current_basis,
        "multiplicative_ratio": current_ratio,
    }

    mapping_example = None
    if source_level is not None:
        source_level = _finite_number(source_level, "source_level")
        if source_level <= 0:
            raise R10Refusal("source_level must be finite and positive")
        # Evaluate L + target_now - source_now without first rounding the basis.
        mapped_additive = _additive_error(source_now, target_now, source_level, 0.0,
                                           label="additive mapped level")
        mapped_ratio = _finite_number(source_level * current_ratio, "multiplicative mapped level")
        if mapped_ratio <= 0:
            raise R10Refusal("multiplicative mapped level is not representable as positive and finite")
        mapping_example = {
            "source_level": source_level,
            "benchmark_scope": "observed_source_target_spot_relation",
            "requested_level_coverage_qualified": False,
            "requested_level_interval": None,
            "additive_basis": {
                "mapped_target_level": mapped_additive,
                "spot_relation_drift_q90_benchmark_target_points": method_stats[
                    "additive_basis"
                ]["train_abs_error_q90_target_points"],
            },
            "multiplicative_ratio": {
                "mapped_target_level": mapped_ratio,
                "spot_relation_drift_q90_benchmark_target_points": method_stats[
                    "multiplicative_ratio"
                ]["train_abs_error_q90_target_points"],
            },
            "warning": (
                "the q90 value is a spot-relation benchmark, not a calibrated "
                "requested-level interval; it is not on native target options positioning"
            ),
        }

    return {
        "schema": SCHEMA,
        "status": "MAPPING_CALIBRATION_COMPLETE",
        "research_authority": "research_only",
        "outcome_labels_opened": False,
        "source_instrument": source_instrument,
        "target_instrument": target_instrument,
        "target_contract": target_contract,
        "target_native_positioning_claim": False,
        "input_contract": {
            "rows": int(len(pairs)),
            "max_skew_seconds": float(max_skew_seconds),
            "observed_skew_max_seconds": float(pairs["source_target_skew_seconds"].max()),
            "horizon_seconds": float(horizon_seconds),
            "timestamp_resolution": "nanoseconds",
            "duration_rounding": "nearest_nanosecond_ties_to_even",
            "effective_horizon_nanoseconds": _duration_ns(horizon_seconds, "horizon_seconds", positive=True),
            "effective_match_tolerance_nanoseconds": _duration_ns(match_tolerance_seconds, "match_tolerance_seconds", positive=False),
            "match_tolerance_seconds": float(match_tolerance_seconds),
            "train_fraction": float(train_fraction),
            "split_observation_index": split_idx,
            "purge_cross_boundary_pairs": True,
            "train_events": int(len(train_events)),
            "test_events": int(len(test_events)),
        },
        "methods": method_stats,
        "current_relation": current,
        "mapping_example": mapping_example,
        "limitations": [
            "this measures time-forward drift of the observed source-target price relation",
            "it does not establish native target options positioning",
            "spot-relation error quantiles do not qualify a fixed requested-level interval",
            "timestamp proximity does not establish source publication-time availability",
            "it does not choose a mapping method automatically",
            "it does not evaluate level reaction, return, PnL or trade outcomes",
            "contract-roll and overnight/RTH strata require explicit later cohorts",
            "fair-value/carry and dynamic regression methods are later Stage-0 arms",
        ],
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Research-only R10 cross-instrument mapping calibration"
    )
    p.add_argument("--csv", required=True, help="CSV with source_ts,target_ts,source_price,target_price")
    p.add_argument("--source-instrument", required=True)
    p.add_argument("--target-instrument", required=True)
    p.add_argument("--target-contract")
    p.add_argument("--horizon-seconds", type=float, default=900.0)
    p.add_argument("--max-skew-seconds", type=float, default=2.0)
    p.add_argument("--match-tolerance-seconds", type=float, default=5.0)
    p.add_argument("--train-fraction", type=float, default=0.60)
    p.add_argument("--source-level", type=float)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        frame = pd.read_csv(Path(args.csv))
        result = calibrate_mapping(
            frame,
            source_instrument=args.source_instrument,
            target_instrument=args.target_instrument,
            target_contract=args.target_contract,
            horizon_seconds=args.horizon_seconds,
            max_skew_seconds=args.max_skew_seconds,
            match_tolerance_seconds=args.match_tolerance_seconds,
            train_fraction=args.train_fraction,
            source_level=args.source_level,
        )
        payload = json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (OSError, pd.errors.ParserError, R10Refusal, ValueError, OverflowError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
