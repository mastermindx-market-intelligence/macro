from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCHEMA = "skylit.r10.cross_instrument_mapping_feasibility/v1"
METHODS = ("additive_basis", "multiplicative_ratio")
REQUIRED_COLUMNS = ("source_ts", "target_ts", "source_price", "target_price")


class R10Refusal(ValueError):
    pass


def _clean_pairs(frame: pd.DataFrame, *, max_skew_seconds: float) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_COLUMNS) - set(frame.columns))
    if missing:
        raise R10Refusal(f"missing required columns: {missing}")
    if not np.isfinite(max_skew_seconds) or max_skew_seconds < 0:
        raise R10Refusal("max_skew_seconds must be finite and non-negative")

    out = frame.loc[:, list(REQUIRED_COLUMNS)].copy()
    for col in ("source_ts", "target_ts"):
        out[col] = pd.to_datetime(out[col], utc=True, errors="coerce")
    for col in ("source_price", "target_price"):
        out[col] = pd.to_numeric(out[col], errors="coerce")

    invalid = (
        out["source_ts"].isna()
        | out["target_ts"].isna()
        | ~np.isfinite(out["source_price"])
        | ~np.isfinite(out["target_price"])
        | (out["source_price"] <= 0)
        | (out["target_price"] <= 0)
    )
    if invalid.any():
        raise R10Refusal(f"invalid synchronized price rows: {int(invalid.sum())}/{len(out)}")

    skew = (out["target_ts"] - out["source_ts"]).abs().dt.total_seconds()
    if (skew > max_skew_seconds).any():
        worst = float(skew.max())
        raise R10Refusal(
            f"source/target timestamp skew exceeds gate: max={worst:.3f}s "
            f"gate={max_skew_seconds:.3f}s"
        )

    out["observed_at"] = out[["source_ts", "target_ts"]].max(axis=1)
    out["source_target_skew_seconds"] = skew.astype(float)
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
    if not np.isfinite(horizon_seconds) or horizon_seconds <= 0:
        raise R10Refusal("horizon_seconds must be finite and positive")
    if not np.isfinite(match_tolerance_seconds) or match_tolerance_seconds < 0:
        raise R10Refusal("match_tolerance_seconds must be finite and non-negative")

    times_ns = frame["observed_at"].astype("int64").to_numpy()
    horizon_ns = int(round(horizon_seconds * 1e9))
    tolerance_ns = int(round(match_tolerance_seconds * 1e9))
    rows: list[dict[str, Any]] = []

    for i, t0 in enumerate(times_ns):
        wanted = t0 + horizon_ns
        j = int(np.searchsorted(times_ns, wanted, side="left"))
        if j >= len(frame):
            continue
        overshoot = int(times_ns[j] - wanted)
        if overshoot < 0 or overshoot > tolerance_ns:
            continue

        source0 = float(frame.at[i, "source_price"])
        target0 = float(frame.at[i, "target_price"])
        source1 = float(frame.at[j, "source_price"])
        target1 = float(frame.at[j, "target_price"])
        basis0 = target0 - source0
        ratio0 = target0 / source0
        additive_error = (source1 + basis0) - target1
        ratio_error = (source1 * ratio0) - target1

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
    if train.size == 0 or test.size == 0:
        raise R10Refusal("temporal split leaves no train or test mapping observations")
    train_abs = np.abs(train)
    test_abs = np.abs(test)
    q50 = float(np.quantile(train_abs, 0.50))
    q90 = float(np.quantile(train_abs, 0.90))
    q95 = float(np.quantile(train_abs, 0.95))
    return {
        "train_n": int(train.size),
        "test_n": int(test.size),
        "train_abs_error_q50_target_points": q50,
        "train_abs_error_q90_target_points": q90,
        "train_abs_error_q95_target_points": q95,
        "test_mae_target_points": float(np.mean(test_abs)),
        "test_rmse_target_points": float(np.sqrt(np.mean(np.square(test)))),
        "test_bias_target_points": float(np.mean(test)),
        "test_q90_interval_coverage": float(np.mean(test_abs <= q90)),
        "test_abs_error_q90_target_points": float(np.quantile(test_abs, 0.90)),
        "test_abs_error_max_target_points": float(np.max(test_abs)),
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
    current_basis = float(last["target_price"] - last["source_price"])
    current_ratio = float(last["target_price"] / last["source_price"])
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
        source_level = float(source_level)
        if not np.isfinite(source_level) or source_level <= 0:
            raise R10Refusal("source_level must be finite and positive")
        mapping_example = {
            "source_level": source_level,
            "additive_basis": {
                "mapped_target_level": source_level + current_basis,
                "empirical_q90_mapping_drift_target_points": method_stats[
                    "additive_basis"
                ]["train_abs_error_q90_target_points"],
            },
            "multiplicative_ratio": {
                "mapped_target_level": source_level * current_ratio,
                "empirical_q90_mapping_drift_target_points": method_stats[
                    "multiplicative_ratio"
                ]["train_abs_error_q90_target_points"],
            },
            "warning": (
                "uncertainty is calibrated on source-target spot-relation drift, "
                "not on native target options positioning"
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
    except (OSError, pd.errors.ParserError, R10Refusal, ValueError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "REFUSED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
