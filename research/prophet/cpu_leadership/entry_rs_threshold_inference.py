"""Dependence-aware second-stage inference for the frozen RS-threshold study.

This module is downstream of ENTRY_RS_THRESHOLD_INFERENCE_PREREG_2026-09-21.md.
It reads the already-frozen descriptive episode artifact; it does not recompute or alter
cohorts, thresholds, outcomes, or production policy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import validation as V  # noqa: E402

STUDY_SCHEMA = "prophet.cpu_leadership.rs_threshold_study.v1"
INFERENCE_SCHEMA = "prophet.cpu_leadership.rs_threshold_inference.v1"
BLOCK_MONTHS = 3
BOOTSTRAP_DRAWS = 5000
BOOTSTRAP_SEED = 20260921
NW_LAGS = 3

CONTRASTS = {
    "A_incremental_075_085_minus_allowed_lt075": (
        "incremental_075_085", "allowed_lt075",
    ),
    "B_blocked_both_ge085_minus_incremental_075_085": (
        "blocked_both_ge085", "incremental_075_085",
    ),
}
METRICS = {
    "rel_21d": "rel_21d",
    "dd_21d": "dd_21d",
    "dd_risk_21d": "dd_risk_21d",
    "continuation_failure_21d": "continuation_failure_21d",
}
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_frozen_study(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != STUDY_SCHEMA:
        raise ValueError("unexpected frozen study schema")
    authority = payload.get("authority") or {}
    if any(authority.get(k) is not False for k in ("can_rank", "can_gate", "can_size", "can_trade")):
        raise ValueError("frozen study authority must remain all false")
    if not isinstance(payload.get("episodes"), list):
        raise ValueError("frozen study episodes missing")
    return payload


def monthly_cohort_means(episodes: list[dict[str, Any]], metric: str) -> pd.DataFrame:
    rows = pd.DataFrame(episodes)
    if rows.empty or metric not in rows.columns:
        return pd.DataFrame()
    rows = rows.loc[:, ["date", "cohort", metric]].copy()
    rows["date"] = pd.to_datetime(rows["date"], errors="coerce")
    rows[metric] = pd.to_numeric(rows[metric], errors="coerce")
    rows = rows.dropna(subset=["date", metric])
    if rows.empty:
        return pd.DataFrame()
    rows["month"] = rows["date"].dt.to_period("M").dt.to_timestamp()
    return rows.groupby(["month", "cohort"], sort=True)[metric].mean().unstack("cohort")


def paired_monthly_difference(
    episodes: list[dict[str, Any]],
    metric: str,
    left: str,
    right: str,
) -> pd.Series:
    monthly = monthly_cohort_means(episodes, metric)
    if monthly.empty or left not in monthly.columns or right not in monthly.columns:
        return pd.Series(dtype=float)
    pair = monthly[[left, right]].dropna()
    return (pair[left] - pair[right]).astype(float)
def moving_block_mean_ci(
    values: pd.Series | np.ndarray,
    *,
    block: int = BLOCK_MONTHS,
    draws: int = BOOTSTRAP_DRAWS,
    seed: int = BOOTSTRAP_SEED,
) -> dict[str, Any]:
    arr = np.asarray(pd.Series(values).dropna(), dtype=float)
    n = len(arr)
    if n < max(block * 2, 8):
        return {
            "n": n,
            "block": block,
            "draws": draws,
            "seed": seed,
            "mean_ci95": None,
        }
    if block < 1 or block > n:
        raise ValueError("invalid block length")
    starts = np.arange(0, n - block + 1)
    nblocks = int(np.ceil(n / block))
    offsets = np.arange(block)
    rng = np.random.default_rng(seed)
    means = np.empty(draws, dtype=float)
    for k in range(draws):
        chosen = rng.choice(starts, size=nblocks, replace=True)
        idx = (chosen[:, None] + offsets[None, :]).ravel()[:n]
        means[k] = float(arr[idx].mean())
    return {
        "n": n,
        "block": block,
        "draws": draws,
        "seed": seed,
        "mean_ci95": [
            round(float(np.percentile(means, 2.5)), 6),
            round(float(np.percentile(means, 97.5)), 6),
        ],
    }


def infer_difference(diff: pd.Series) -> dict[str, Any]:
    clean = pd.Series(diff).dropna().astype(float)
    nw = V.newey_west_tstat(clean, lags=NW_LAGS)
    boot = moving_block_mean_ci(clean)
    return {
        "n_overlapping_months": int(len(clean)),
        "span": (
            [str(clean.index.min().date()), str(clean.index.max().date())]
            if len(clean) and isinstance(clean.index, pd.DatetimeIndex)
            else None
        ),
        "mean": round(float(clean.mean()), 6) if len(clean) else None,
        "median": round(float(clean.median()), 6) if len(clean) else None,
        "newey_west": nw,
        "moving_block_bootstrap": boot,
    }
def run_inference(study_path: Path) -> dict[str, Any]:
    study = load_frozen_study(study_path)
    episodes = study["episodes"]
    results: dict[str, Any] = {}
    for name, (left, right) in CONTRASTS.items():
        metric_results: dict[str, Any] = {}
        for metric_name, field in METRICS.items():
            diff = paired_monthly_difference(episodes, field, left, right)
            metric_results[metric_name] = infer_difference(diff)
        results[name] = {
            "left": left,
            "right": right,
            "metrics": metric_results,
        }
    return {
        "schema": INFERENCE_SCHEMA,
        "source_study_schema": study["schema"],
        "source_study_path": str(study_path),
        "source_study_sha256": _sha256(study_path),
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_trade": False,
        },
        "method": {
            "aggregation": "mean per calendar month within cohort",
            "pairing": "only months containing both compared cohorts",
            "newey_west_lags": NW_LAGS,
            "moving_block_months": BLOCK_MONTHS,
            "bootstrap_draws": BOOTSTRAP_DRAWS,
            "bootstrap_seed": BOOTSTRAP_SEED,
        },
        "contrasts": results,
        "limitations": [
            "Second-stage inference was preregistered after the descriptive read and before this inference.",
            "Monthly aggregation reduces cross-sector and overlapping-window pseudo-replication but does not create causal identification.",
            "The US SPDR proxy is not the live theme-member universe.",
            "No result changes production thresholds without the existing promotion process.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = run_inference(args.study.resolve())
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
