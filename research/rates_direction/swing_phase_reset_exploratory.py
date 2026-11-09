"""Seen-history exploratory phase/reset study for ^TNX.

This is a distinct hypothesis from the frozen crossover studies. It may identify
a candidate for prospective shadowing; it cannot establish predictive authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.trial_ledger import TrialLedger
from engine.validation import newey_west_tstat
from research.rates_direction import swing_proxy_pilot as p

FAMILY = "ric_swing_phase_reset_v1"
SOURCE_SHA = "1dc7e9121fd6aa36c5019beba303b629257eb1cab752ae937e4cef1aa8161b76"
CAPTURE_AT = "2026-09-24T14:17:57Z"
CUTOFF = "2026-06-24T00:00:00Z"
CANDIDATES = (
    "M_EARLY",
    "P_RESET",
    "R_RESET",
    "PR_RESET",
    "MPR_RESET",
    "SHALLOW_PR",
    "SHALLOW_MPR",
)
MODELS = ("unconditional", "trend5_vol", "phase_trend_vol") + CANDIDATES
LABELS = p.LABELS
SPEC = {
    **p.SPEC,
    "capture_at": CAPTURE_AT,
    "primary": "SHALLOW_MPR",
    "phase_ema_bars": 20,
    "phase_ema_slope_bars": 4,
    "reset_lookback_bars": 4,
    "curl_recency_bars": 3,
    "range_bars": 12,
    "strength_upper": 0.60,
    "strength_lower": 0.40,
    "evidence_tier": "seen_history_phase_reset_exploratory_not_validation",
}
FROZEN_PATHS = (
    "research/rates_direction/swing_phase_reset_exploratory.py",
    "research/rates_direction/SWING_PHASE_RESET_EXPLORATORY_V1.md",
    "tests/test_rates_swing_phase_reset_exploratory.py",
    "research/rates_direction/swing_proxy_pilot.py",
    "research/rates_direction/uploaded_formula_probe.py",
    "engine/validation.py",
)
FREEZE = ROOT / "research/rates_direction/swing_phase_reset_exploratory_freeze_v1.json"


def combine_same_direction(*states: pd.Series) -> pd.Series:
    frame = pd.concat(states, axis=1)
    up = (frame == 1).all(axis=1)
    down = (frame == -1).all(axis=1)
    return pd.Series(np.where(up, 1, np.where(down, -1, 0)), index=frame.index, dtype=int)


def reset_state(
    k: pd.Series,
    d: pd.Series,
    trend: pd.Series,
    lookback: int,
    low: float = 20.0,
    high: float = 80.0,
) -> pd.Series:
    """Trend-continuation reset after an oscillator visited the opposite extreme."""
    k = pd.to_numeric(k, errors="coerce").astype(float)
    d = pd.to_numeric(d, errors="coerce").astype(float)
    slope = k.diff()
    recent_low = k.rolling(lookback, min_periods=lookback).min()
    recent_high = k.rolling(lookback, min_periods=lookback).max()
    up = (trend == 1) & (recent_low < low) & (k > d) & (slope > 0)
    down = (trend == -1) & (recent_high > high) & (k < d) & (slope < 0)
    return pd.Series(np.where(up, 1, np.where(down, -1, 0)), index=k.index, dtype=int)


def recent_macd_curl(
    hist: pd.Series,
    trend: pd.Series,
    recency: int,
) -> pd.Series:
    """Early curl while MACD-RSI histogram is still on the opposite side of zero."""
    hist = pd.to_numeric(hist, errors="coerce").astype(float)
    slope = hist.diff()
    up_event = (trend == 1) & (hist < 0) & (slope > 0) & (slope.shift(1) <= 0)
    down_event = (trend == -1) & (hist > 0) & (slope < 0) & (slope.shift(1) >= 0)
    out = np.zeros(len(hist), dtype=int)
    last = -recency
    direction = 0
    for i in range(len(hist)):
        if bool(up_event.iloc[i]):
            last, direction = i, 1
        elif bool(down_event.iloc[i]):
            last, direction = i, -1
        if (
            i - last < recency
            and int(trend.iloc[i]) == direction
            and np.isfinite(slope.iloc[i])
            and np.sign(slope.iloc[i]) == direction
        ):
            out[i] = direction
    return pd.Series(out, index=hist.index, dtype=int)


def range_position(close: pd.Series, bars: int) -> pd.Series:
    close = pd.to_numeric(close, errors="coerce").astype(float)
    lo = close.rolling(bars, min_periods=bars).min()
    hi = close.rolling(bars, min_periods=bars).max()
    span = (hi - lo).replace(0, np.nan)
    return (close - lo) / span


def build_phase_features(bars: pd.DataFrame, spec: dict = SPEC) -> pd.DataFrame:
    """One-sided phase features. Any invalid expected bar resets all warmups."""
    out = pd.DataFrame(index=bars.index)
    for key in ("vol", "barrier_bp", "trend5", "phase_trend", "range_pos"):
        out[key] = np.nan
    for name in CANDIDATES:
        out[name] = 0
    out["eligible"] = False

    valid = bars.valid.astype(bool).to_numpy()
    i = 0
    while i < len(bars):
        if not valid[i]:
            i += 1
            continue
        end = i + 1
        while end < len(bars) and valid[end]:
            end += 1
        seg = bars.iloc[i:end]
        v = p.calculate(seg)
        close = pd.to_numeric(seg.close, errors="coerce").astype(float)

        ema = close.ewm(
            span=spec["phase_ema_bars"],
            adjust=False,
            min_periods=spec["phase_ema_bars"],
        ).mean()
        ema_slope = ema - ema.shift(spec["phase_ema_slope_bars"])
        trend = pd.Series(
            np.where(
                (close > ema) & (ema_slope > 0),
                1,
                np.where((close < ema) & (ema_slope < 0), -1, 0),
            ),
            index=seg.index,
            dtype=int,
        )

        f = pd.DataFrame(index=seg.index)
        f["trend5"] = np.sign(close.diff(spec["trend_bars"]))
        f["phase_trend"] = trend
        f["vol"] = (
            close.diff()
            .mul(spec["bp_per_source_unit"])
            .rolling(spec["volatility_bars"])
            .std()
        )
        f["barrier_bp"] = np.maximum(
            spec["barrier_floor_bp"],
            f["vol"] * np.sqrt(spec["horizon_bars"]),
        )
        f["range_pos"] = range_position(close, spec["range_bars"])

        f["M_EARLY"] = recent_macd_curl(v["hist"], trend, spec["curl_recency_bars"])
        f["P_RESET"] = reset_state(
            v["kp"], v["dp"], trend, spec["reset_lookback_bars"]
        )
        f["R_RESET"] = reset_state(
            v["kr"], v["dr"], trend, spec["reset_lookback_bars"]
        )
        f["PR_RESET"] = combine_same_direction(f["P_RESET"], f["R_RESET"])
        f["MPR_RESET"] = combine_same_direction(
            f["M_EARLY"], f["P_RESET"], f["R_RESET"]
        )
        strength = pd.Series(
            np.where(
                (trend == 1) & (f["range_pos"] >= spec["strength_upper"]),
                1,
                np.where(
                    (trend == -1) & (f["range_pos"] <= spec["strength_lower"]),
                    -1,
                    0,
                ),
            ),
            index=seg.index,
            dtype=int,
        )
        f["SHALLOW_PR"] = combine_same_direction(f["PR_RESET"], strength)
        f["SHALLOW_MPR"] = combine_same_direction(f["MPR_RESET"], strength)

        finite_formula = v[["m", "sig", "hist", "kp", "dp", "kr", "dr"]].notna().all(axis=1)
        f["eligible"] = (
            (np.arange(len(seg)) >= spec["warmup_bars"])
            & finite_formula
            & f["vol"].notna()
            & ema.notna()
            & f["range_pos"].notna()
        )
        out.loc[seg.index, f.columns] = f
        i = end

    for name in CANDIDATES:
        out[name] = out[name].fillna(0).astype(int)
    out["eligible"] = out["eligible"].fillna(False).astype(bool)
    return out


def _counts(labels: list[dict], y: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.bincount(y[mask], minlength=3).astype(float)


def walk_forward(
    bars: pd.DataFrame,
    features: pd.DataFrame,
    labels: list[dict],
    spec: dict = SPEC,
) -> list[dict]:
    n = len(bars)
    ids = np.arange(n)
    eligible = features.eligible.to_numpy(bool)
    y = np.array(
        [LABELS.index(row["label"]) if row["label"] in LABELS else -1 for row in labels]
    )
    ends = np.array([row["target_end_index"] for row in labels])
    vol = features.vol.to_numpy(float)
    trend5 = features.trend5.to_numpy(float)
    phase = features.phase_trend.to_numpy(float)
    states = {name: features[name].to_numpy(int) for name in CANDIDATES}
    rows: list[dict] = []
    shrink = spec["shrinkage"]

    for i in ids[eligible]:
        train_mask = eligible & (ids < i) & (ends < i) & (y >= 0)
        train = ids[train_mask]
        if len(train) < spec["minimum_training_labels"]:
            continue
        uncond = (_counts(labels, y, train_mask) + 1.0) / (len(train) + 3.0)
        median = float(np.median(vol[train_mask]))
        vol_bucket = vol > median

        old_same = train_mask & (trend5 == trend5[i]) & (vol_bucket == vol_bucket[i])
        old_base = (
            _counts(labels, y, old_same) + shrink * uncond
        ) / (int(old_same.sum()) + shrink)

        phase_same = train_mask & (phase == phase[i]) & (vol_bucket == vol_bucket[i])
        phase_base = (
            _counts(labels, y, phase_same) + shrink * uncond
        ) / (int(phase_same.sum()) + shrink)

        probs = {
            "unconditional": uncond.tolist(),
            "trend5_vol": old_base.tolist(),
            "phase_trend_vol": phase_base.tolist(),
        }
        now: dict[str, int] = {}
        for name in CANDIDATES:
            state = int(states[name][i])
            now[name] = state
            if state == 0:
                prob = phase_base
            else:
                matched = phase_same & (states[name] == state)
                prob = (
                    _counts(labels, y, matched) + shrink * phase_base
                ) / (int(matched.sum()) + shrink)
            probs[name] = prob.tolist()

        rows.append(
            {
                "origin_index": int(i),
                "origin": bars.index[i].isoformat(),
                "session": str(bars.session.iloc[i]),
                "training_n": int(len(train)),
                "last_training_target_end": max(
                    labels[int(j)]["target_end"] for j in train
                ),
                "probabilities": probs,
                "states": now,
                "phase_trend": int(phase[i]),
                "outcome": labels[int(i)],
                "seen_history_exploratory": True,
                "native_pine_parity": False,
                "historical_availability_qualified": False,
                "authority": False,
            }
        )
    return rows


def partition_rows(
    rows: list[dict], bars: pd.DataFrame, cutoff: str = CUTOFF
) -> dict[str, list[dict]]:
    cut = p._utc(cutoff)
    out = {"discovery": [], "seen_overlap": [], "boundary": []}
    for row in rows:
        if p._utc(row["origin"]) >= cut:
            out["seen_overlap"].append(row)
        elif (
            row["outcome"]["target_end_index"] < len(bars)
            and bars.index[row["outcome"]["target_end_index"]] < cut
        ):
            out["discovery"].append(row)
        else:
            out["boundary"].append(row)
    return out


def summarize(rows: list[dict], spec: dict = SPEC) -> dict:
    scored = [row for row in rows if row["outcome"]["label"] in LABELS]
    report = {
        "forecast_origins": len(rows),
        "scored_origins": len(scored),
        "outcome_counts": dict(Counter(row["outcome"]["label"] for row in rows)),
        "models": {},
        "primary": spec["primary"],
        "primary_promoted": False,
        "score_convention": "three-class sum Brier, range 0 to 2",
        "scope": spec["evidence_tier"],
        "authority": False,
    }
    if not scored:
        report["status"] = "INSUFFICIENT_TRAINING_OR_OUTCOMES"
        return report

    target = np.array([LABELS.index(row["outcome"]["label"]) for row in scored])
    truth = np.eye(3)[target]
    losses: dict[str, np.ndarray] = {}
    for name in MODELS:
        probabilities = np.array([row["probabilities"][name] for row in scored])
        loss = ((probabilities - truth) ** 2).sum(axis=1)
        losses[name] = loss
        item = {
            "n": len(scored),
            "brier": float(loss.mean()),
            "log_loss": float(
                -np.log(probabilities[np.arange(len(target)), target]).mean()
            ),
            "active_forecast_origins": 0,
            "episodes": [],
        }
        if name in CANDIDATES:
            item["active_forecast_origins"] = sum(
                row["states"][name] != 0 for row in rows
            )
            last_end = -1
            for row in rows:
                state = row["states"][name]
                if state and row["origin_index"] > last_end:
                    last_end = row["outcome"]["target_end_index"]
                    item["episodes"].append(
                        {
                            "origin": row["origin"],
                            "direction": state,
                            "outcome": row["outcome"]["label"],
                            "barrier_bp": row["outcome"]["barrier_bp"],
                            "up_excursion_bp": row["outcome"]["up_excursion_bp"],
                            "down_excursion_bp": row["outcome"]["down_excursion_bp"],
                        }
                    )
            resolved = [ep for ep in item["episodes"] if ep["outcome"] in LABELS]
            wins = sum(
                ep["outcome"] == ("up" if ep["direction"] > 0 else "down")
                for ep in resolved
            )
            item.update(
                nonoverlapping_episodes=len(item["episodes"]),
                resolved_episodes=len(resolved),
                wins=wins,
                hit_fraction=wins / len(resolved) if resolved else None,
                episode_counts=dict(Counter(ep["outcome"] for ep in item["episodes"])),
                enough_for_ranking=(
                    len(resolved) >= spec["minimum_active_episodes"]
                ),
            )
        report["models"][name] = item

    old = losses["trend5_vol"]
    phase = losses["phase_trend_vol"]
    report["models"]["phase_trend_vol"]["brier_improvement_vs_trend5_vol"] = float(
        (old - phase).mean()
    )
    report["models"]["phase_trend_vol"][
        "relative_brier_improvement_vs_trend5_vol"
    ] = float((old - phase).mean() / old.mean())

    for name in CANDIDATES:
        difference = phase - losses[name]
        by_day = (
            pd.Series(difference, index=[row["session"] for row in scored])
            .groupby(level=0)
            .mean()
        )
        report["models"][name].update(
            brier_improvement_vs_phase_trend_vol=float(difference.mean()),
            relative_brier_improvement=float(difference.mean() / phase.mean()),
            date_count=len(by_day),
            diagnostic_hac=newey_west_tstat(by_day, lags=3),
        )
    report["status"] = "SEEN_HISTORY_EXPLORATORY_NO_PROMOTION"
    return report


def file_hash(path: Path | str) -> str:
    return p.file_hash(path)


def verify(receipt: dict) -> None:
    if (
        receipt.get("source_sha256") != SOURCE_SHA
        or receipt.get("spec") != SPEC
        or receipt.get("cutoff") != CUTOFF
    ):
        raise ValueError("frozen source/spec mismatch")
    if set(receipt.get("files", {})) != set(FROZEN_PATHS):
        raise ValueError("incomplete freeze file set")
    for name, digest in receipt["files"].items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("post-freeze source change: " + name)


def freeze() -> None:
    if FREEZE.exists():
        raise FileExistsError("freeze receipt already exists")
    ledger = TrialLedger(path=ROOT / "data/trial_ledger.jsonl", family=FAMILY)
    prior = ledger.literal_n()
    if prior != 0:
        raise ValueError("phase-reset family already registered; reconcile")
    receipt = {
        "schema": "ric.swing_phase_reset.exploratory_freeze.v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "strategy_outcomes_opened_for_this_construction": False,
        "history_already_seen_by_prior_program_studies": True,
        "source_sha256": SOURCE_SHA,
        "spec": SPEC,
        "cutoff": CUTOFF,
        "files": {name: file_hash(ROOT / name) for name in FROZEN_PATHS},
        "ledger_before_sha256": file_hash(ROOT / "data/trial_ledger.jsonl"),
        "prior_family_trials": prior,
        "new_configs": len(CANDIDATES),
        "primary": "discovery:SHALLOW_MPR_vs_phase_trend_vol",
        "native_pine_parity": False,
        "authority": False,
    }
    with FREEZE.open("x") as fh:
        json.dump(receipt, fh, indent=2)
    print(json.dumps(receipt, indent=2))


def run(capture: Path, output: Path) -> None:
    receipt = json.loads(FREEZE.read_text())
    verify(receipt)
    if file_hash(capture) != SOURCE_SHA:
        raise ValueError("changed capture")
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    if file_hash(ledger_path) != receipt["ledger_before_sha256"]:
        raise ValueError("trial ledger changed; reconcile before registration")
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("phase-reset family state changed; reconcile")
    output.mkdir(parents=True, exist_ok=False)

    configs = [
        {
            "model": name,
            "spec": SPEC,
            "source_sha256": SOURCE_SHA,
            "freeze_sha256": file_hash(FREEZE),
            "sample": "two_year_seen_history_exploratory",
            "primary_partition_end_exclusive": CUTOFF,
        }
        for name in CANDIDATES
    ]
    registered = ledger.log_grid(
        configs,
        info_cutoff=SPEC["capture_at"],
        source="seen_history_phase_reset_exploratory",
        note=(
            "History already seen by prior crossover program; discovery only. "
            "No promotion without a new prospective shadow."
        ),
    )
    registration = {
        "family": FAMILY,
        "new_configs": registered,
        "literal_n": ledger.literal_n(),
        "ledger_before_sha256": receipt["ledger_before_sha256"],
        "ledger_after_sha256": file_hash(ledger_path),
        "freeze_sha256": file_hash(FREEZE),
    }
    (output / "registration.json").write_text(json.dumps(registration, indent=2))
    if registered != len(CANDIDATES) or ledger.literal_n() != len(CANDIDATES):
        raise ValueError("partial phase-reset registration; reconcile")

    hourly, bars, quality = p.parse_capture(
        json.loads(capture.read_text()), SPEC["capture_at"]
    )
    features = build_phase_features(bars, SPEC)
    labels = p.label_paths(hourly, bars, features, SPEC)
    rows = walk_forward(bars, features, labels, SPEC)
    parts = partition_rows(rows, bars)

    with (output / "predictions.jsonl").open("x") as fh:
        for row in rows:
            fh.write(json.dumps(row, allow_nan=False) + "\n")

    summary = {
        "schema": "ric.swing_phase_reset.exploratory_result.v1",
        "spec": SPEC,
        "quality": quality,
        "registration": registration,
        "source_sha256": SOURCE_SHA,
        "cutoff": CUTOFF,
        "prediction_sha256": file_hash(output / "predictions.jsonl"),
        "forecasts": len(rows),
        "eligible_feature_origins": int(features.eligible.sum()),
        "primary_partition": "discovery",
        "primary_candidate": SPEC["primary"],
        "boundary_origins": len(parts["boundary"]),
        "partitions": {
            name: summarize(group, SPEC)
            for name, group in parts.items()
            if name != "boundary"
        },
        "all_dates_diagnostic": summarize(rows, SPEC),
        "seen_history_exploratory": True,
        "native_pine_parity": False,
        "historical_availability_qualified": False,
        "authority": False,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False)
    )
    discovery = summary["partitions"]["discovery"]
    print(
        json.dumps(
            {
                "quality": quality,
                "forecasts": len(rows),
                "discovery_scored": discovery["scored_origins"],
                "phase_baseline": {
                    key: discovery["models"]["phase_trend_vol"].get(key)
                    for key in (
                        "brier",
                        "relative_brier_improvement_vs_trend5_vol",
                    )
                },
                "models": {
                    name: {
                        key: discovery["models"][name].get(key)
                        for key in (
                            "brier",
                            "relative_brier_improvement",
                            "active_forecast_origins",
                            "resolved_episodes",
                            "wins",
                            "enough_for_ranking",
                        )
                    }
                    for name in CANDIDATES
                },
                "output": str(output),
            },
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "run"])
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "freeze":
        freeze()
        return
    if args.capture is None or args.output is None:
        parser.error("run requires --capture and --output")
    run(args.capture, args.output)


if __name__ == "__main__":
    main()
