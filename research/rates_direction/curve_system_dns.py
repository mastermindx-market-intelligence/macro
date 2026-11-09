"""Chronological 10Y curve-system forecast using fixed Nelson-Siegel factors.

Research only. Uses incumbent corrected Treasury history and the shared TrialLedger.
No live producer, collector, scheduler, signal, or trade authority is created.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.trial_ledger import TrialLedger
from engine.validation import newey_west_tstat

FAMILY = "ric_curve_system_dns_v1"
TENORS = ("1", "2", "3", "5", "7", "10")
MATURITIES_MONTHS = np.array([12.0, 24.0, 36.0, 60.0, 84.0, 120.0])
LAMBDA = 0.0609
HORIZONS = (5, 20, 60)
MODELS = ("no_change", "direct_ar10y", "dns_diag", "dns_var")
PRIMARY_MODEL = "dns_var"
PRIMARY_HORIZON = 20
SOURCE_FILES = {
    "1": ("data/fred/DGS1.parquet", "6b5e423be804de3da0f7380301fedbb9ce4f89f2d57cb307306c2eaa50054549"),
    "2": ("data/fred/DGS2.parquet", "0cb9aa029d0d435b013b25421ba8c9365b61dcda07deaea386061396760c4eec"),
    "3": ("data/fred/DGS3.parquet", "cb889793f79d91902537b944a217716f4b3e838faa255226419e7079c86996d9"),
    "5": ("data/fred/DGS5.parquet", "e32bbcf503b1bfc96dd7e7a1cf0523895b7ab19d9e9eeccc8a9661650ec51ca3"),
    "7": ("data/fred/DGS7.parquet", "97f8d99591f210b5ec0bb14aec90b679e5d5d88e74bd9e3c7170bf2a6cef774b"),
    "10": ("data/fred/DGS10.parquet", "7369b3a15097c9ff06e765ca76476f34263ad2ae3759827e878fdea44f6bfbf9"),
}
SPEC = {
    "lambda_per_month": LAMBDA,
    "tenors_years": list(TENORS),
    "maturities_months": MATURITIES_MONTHS.tolist(),
    "horizons_observed_dates": list(HORIZONS),
    "fit_min": 1260,
    "fit_max": 2520,
    "calibration_min": 126,
    "calibration_max": 252,
    "refit_every": 20,
    "max_gap_days": 4,
    "flat_band_bp": 2.0,
    "primary_period": ["2021-01-01", "2025-12-31"],
    "context_period": ["2010-01-01", "2020-12-31"],
    "primary_model": PRIMARY_MODEL,
    "primary_horizon": PRIMARY_HORIZON,
    "evidence_tier": "corrected_history_chronological_curve_system_research_only",
}
FREEZE = ROOT / "research/rates_direction/curve_system_dns_freeze_v1.json"
FROZEN_PATHS = (
    "research/rates_direction/curve_system_dns.py",
    "research/rates_direction/CURVE_SYSTEM_DNS_V1.md",
    "tests/test_curve_system_dns.py",
    "engine/validation.py",
)


def file_hash(path: Path | str) -> str:
    h = sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ns_design(
    maturities_months: np.ndarray = MATURITIES_MONTHS,
    lam: float = LAMBDA,
) -> np.ndarray:
    tau = np.asarray(maturities_months, dtype=float)
    if tau.ndim != 1 or len(tau) < 3 or np.any(~np.isfinite(tau)) or np.any(tau <= 0):
        raise ValueError("invalid maturity grid")
    if not np.isfinite(lam) or lam <= 0:
        raise ValueError("invalid Nelson-Siegel lambda")
    x = lam * tau
    slope = (1.0 - np.exp(-x)) / x
    curvature = slope - np.exp(-x)
    design = np.column_stack([np.ones(len(tau)), slope, curvature])
    if np.linalg.matrix_rank(design) < 3:
        raise ValueError("degenerate Nelson-Siegel design")
    return design


DESIGN = ns_design()
LOAD_10Y = DESIGN[-1].copy()


def load_panel(root: Path = ROOT) -> pd.DataFrame:
    cols: list[pd.Series] = []
    for tenor in TENORS:
        rel, expected = SOURCE_FILES[tenor]
        path = root / rel
        if file_hash(path) != expected:
            raise ValueError(f"source hash mismatch: {rel}")
        frame = pd.read_parquet(path)
        if frame.shape[1] != 1:
            raise ValueError(f"{rel} must have exactly one value column")
        series = pd.to_numeric(frame.iloc[:, 0], errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        )
        idx = pd.DatetimeIndex(series.index)
        if (
            idx.hasnans
            or idx.tz is not None
            or not idx.is_unique
            or not idx.equals(idx.normalize())
            or not idx.is_monotonic_increasing
        ):
            raise ValueError(f"invalid source date grid: {rel}")
        series.index = idx
        cols.append(series.rename(tenor))
    panel = pd.concat(cols, axis=1).dropna(how="any")
    if panel.empty or list(panel.columns) != list(TENORS):
        raise ValueError("empty or malformed common Treasury panel")
    return panel.astype(float)


def extract_factors(panel: pd.DataFrame) -> pd.DataFrame:
    if tuple(panel.columns) != TENORS or panel.isna().any().any():
        raise ValueError("factor extraction requires complete fixed-tenor panel")
    pinv = np.linalg.pinv(DESIGN)
    betas = panel.to_numpy(float) @ pinv.T
    if not np.isfinite(betas).all():
        raise ValueError("nonfinite Nelson-Siegel factors")
    return pd.DataFrame(
        betas,
        index=panel.index,
        columns=("level", "slope", "curvature"),
    )


def reconstruct_10y(beta: np.ndarray) -> np.ndarray:
    b = np.asarray(beta, dtype=float)
    if b.shape[-1] != 3:
        raise ValueError("expected three Nelson-Siegel factors")
    return b @ LOAD_10Y


def _ols(x: np.ndarray, y: np.ndarray) -> Callable[[np.ndarray], np.ndarray]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 2 or y.ndim not in (1, 2) or len(x) != len(y) or len(x) < x.shape[1] + 2:
        raise ValueError("invalid OLS fit matrix")
    design = np.column_stack([np.ones(len(x)), x])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)

    def predict(values: np.ndarray) -> np.ndarray:
        v = np.asarray(values, dtype=float)
        if v.ndim == 1:
            v = v.reshape(1, -1)
        return np.column_stack([np.ones(len(v)), v]) @ coef

    return predict


def _fit_predictors(
    panel: pd.DataFrame,
    factors: pd.DataFrame,
    fit: np.ndarray,
    horizon: int,
) -> dict[str, Callable[[np.ndarray], np.ndarray]]:
    y10 = panel["10"].to_numpy(float)
    beta = factors.to_numpy(float)

    direct = _ols(y10[fit, None], y10[fit + horizon])

    diag_models = [
        _ols(beta[fit, k, None], beta[fit + horizon, k])
        for k in range(3)
    ]

    def diag(values: np.ndarray) -> np.ndarray:
        v = np.asarray(values, dtype=float)
        if v.ndim == 1:
            v = v.reshape(1, -1)
        cols = [
            np.asarray(diag_models[k](v[:, k, None])).reshape(-1)
            for k in range(3)
        ]
        return np.column_stack(cols)

    var = _ols(beta[fit], beta[fit + horizon])

    return {
        "direct_ar10y": direct,
        "dns_diag": diag,
        "dns_var": var,
    }


def _point_changes(
    model: str,
    origins: np.ndarray,
    horizon: int,
    panel: pd.DataFrame,
    factors: pd.DataFrame,
    predictors: dict[str, Callable[[np.ndarray], np.ndarray]],
) -> np.ndarray:
    y10 = panel["10"].to_numpy(float)
    beta = factors.to_numpy(float)
    origins = np.asarray(origins, dtype=int)
    if model == "no_change":
        return np.zeros(len(origins), dtype=float)
    if model == "direct_ar10y":
        future = np.asarray(predictors[model](y10[origins, None])).reshape(-1)
    elif model in ("dns_diag", "dns_var"):
        forecast_beta = np.asarray(predictors[model](beta[origins]))
        future = reconstruct_10y(forecast_beta)
    else:
        raise ValueError("unsupported model")
    return (future - y10[origins]) * 100.0


def _target_ok(panel: pd.DataFrame, horizon: int, max_gap_days: int) -> np.ndarray:
    n = len(panel)
    gaps = panel.index.to_series().diff().dt.days.fillna(0)
    max_future_gap = gaps.rolling(horizon).max().shift(-horizon)
    ok = (max_future_gap <= max_gap_days).fillna(False).to_numpy(dtype=bool, copy=True)
    idx = np.arange(n)
    ok &= idx + horizon < n
    return ok


def walk_forward(
    panel: pd.DataFrame,
    horizon: int,
    spec: dict = SPEC,
) -> dict:
    if horizon not in HORIZONS:
        raise ValueError("unsupported horizon")
    factors = extract_factors(panel)
    y10 = panel["10"].to_numpy(float)
    n = len(panel)
    idx = np.arange(n)
    target_ok = _target_ok(panel, horizon, int(spec["max_gap_days"]))
    observed = np.full(n, np.nan)
    valid_targets = np.flatnonzero(target_ok)
    observed[valid_targets] = (
        y10[valid_targets + horizon] - y10[valid_targets]
    ) * 100.0

    rows: list[dict] = []
    state = None
    last_fit = -int(spec["refit_every"])

    for i in range(n):
        if state is None or i - last_fit >= int(spec["refit_every"]):
            matured = np.flatnonzero(target_ok & (idx + horizon < i))
            calibration = matured[-int(spec["calibration_max"]):]
            if len(calibration) < int(spec["calibration_min"]):
                continue
            fit_pool = matured[matured + horizon < calibration[0]]
            fit = fit_pool[-int(spec["fit_max"]):]
            if len(fit) < int(spec["fit_min"]):
                continue

            predictors = _fit_predictors(panel, factors, fit, horizon)
            residuals: dict[str, np.ndarray] = {}
            actual_cal = observed[calibration]
            for model in MODELS:
                point_cal = _point_changes(
                    model, calibration, horizon, panel, factors, predictors
                )
                residual = actual_cal - point_cal
                if not np.isfinite(residual).all():
                    raise ValueError("nonfinite residual calibration")
                residuals[model] = residual
            state = (predictors, residuals, fit, calibration)
            last_fit = i

        predictors, residuals, fit, calibration = state
        for model in MODELS:
            point = float(
                _point_changes(
                    model,
                    np.array([i]),
                    horizon,
                    panel,
                    factors,
                    predictors,
                )[0]
            )
            samples = point + residuals[model]
            band = float(spec["flat_band_bp"])
            denom = len(samples) + 3
            p_up = float((np.sum(samples > band) + 1) / denom)
            p_down = float((np.sum(samples < -band) + 1) / denom)
            p_flat = 1.0 - p_up - p_down
            rows.append(
                {
                    "origin": panel.index[i].date().isoformat(),
                    "origin_position": int(i),
                    "target_end": (
                        panel.index[i + horizon].date().isoformat()
                        if i + horizon < n
                        else None
                    ),
                    "target_end_position": int(i + horizon),
                    "tenor": "10y",
                    "horizon": int(horizon),
                    "horizon_basis": "common_DGS_observed_date_intervals_not_certified_sessions",
                    "model": model,
                    "forecast_bp": point,
                    "lower_bp": float(np.quantile(samples, 0.10)),
                    "upper_bp": float(np.quantile(samples, 0.90)),
                    "p_up": p_up,
                    "p_down": p_down,
                    "p_flat": p_flat,
                    "observed_change_bp": (
                        float(observed[i]) if np.isfinite(observed[i]) else None
                    ),
                    "fit_start": panel.index[fit[0]].date().isoformat(),
                    "fit_target_end": panel.index[fit[-1] + horizon].date().isoformat(),
                    "calibration_start": panel.index[calibration[0]].date().isoformat(),
                    "calibration_target_end": panel.index[
                        calibration[-1] + horizon
                    ].date().isoformat(),
                    "fit_n": int(len(fit)),
                    "calibration_n": int(len(calibration)),
                    "fit_origin": panel.index[last_fit].date().isoformat(),
                    "forecast_available_at": None,
                    "historical_availability_qualified": False,
                    "authority": False,
                }
            )

    return {
        "schema": "ric.curve_system_dns.research.v1",
        "spec": spec,
        "horizon": int(horizon),
        "factor_reconstruction_rmse_bp": float(
            np.sqrt(np.mean((reconstruct_10y(factors.to_numpy()) - y10) ** 2)) * 100
        ),
        "coverage": {
            "source_rows": int(n),
            "qualified_targets": int(target_ok.sum()),
            "forecast_origins": int(len(rows) // len(MODELS)),
            "start": panel.index.min().date().isoformat(),
            "end": panel.index.max().date().isoformat(),
        },
        "rows": rows,
        "authority": False,
    }


def _class_index(value: float, band: float) -> int:
    if value < -band:
        return 0
    if value > band:
        return 2
    return 1


def summarize(
    results: list[dict],
    *,
    start: str,
    end: str,
    spec: dict = SPEC,
) -> dict:
    all_rows = [row for result in results for row in result["rows"]]
    selected = [
        row
        for row in all_rows
        if start <= row["origin"] <= end
        and row["target_end"] is not None
        and row["target_end"] <= end
        and row["observed_change_bp"] is not None
    ]
    report = {
        "period": [start, end],
        "models": {},
        "primary_model": PRIMARY_MODEL,
        "primary_horizon": PRIMARY_HORIZON,
        "authority": False,
        "promotion": "withheld",
        "inference_limit": "HAC is diagnostic; retrospective corrected-history result is not prospective validation.",
    }
    band = float(spec["flat_band_bp"])

    for horizon in HORIZONS:
        horizon_rows = [r for r in selected if r["horizon"] == horizon]
        for model in MODELS:
            group = [r for r in horizon_rows if r["model"] == model]
            key = f"h{horizon}:{model}"
            if not group:
                report["models"][key] = {"n": 0, "status": "insufficient_history"}
                continue
            y = np.array([r["observed_change_bp"] for r in group], dtype=float)
            f = np.array([r["forecast_bp"] for r in group], dtype=float)
            probs = np.array(
                [[r["p_down"], r["p_flat"], r["p_up"]] for r in group],
                dtype=float,
            )
            classes = np.array([_class_index(v, band) for v in y], dtype=int)
            truth = np.eye(3)[classes]
            next_origin = -1
            nonoverlap = 0
            for row in group:
                if row["origin_position"] >= next_origin:
                    nonoverlap += 1
                    next_origin = row["target_end_position"]
            report["models"][key] = {
                "n": len(group),
                "nonoverlapping_windows": nonoverlap,
                "mse_bp2": float(np.mean((f - y) ** 2)),
                "mae_bp": float(np.mean(np.abs(f - y))),
                "direction_brier": float(np.mean(np.sum((probs - truth) ** 2, axis=1))),
                "direction_log_loss": float(
                    -np.mean(
                        np.log(
                            np.maximum(
                                probs[np.arange(len(classes)), classes],
                                1e-12,
                            )
                        )
                    )
                ),
                "direction_accuracy": float(
                    np.mean(
                        np.array([_class_index(v, band) for v in f], dtype=int)
                        == classes
                    )
                ),
                "span": [group[0]["origin"], group[-1]["origin"]],
            }

        base = report["models"][f"h{horizon}:no_change"]
        base_rows = [r for r in horizon_rows if r["model"] == "no_change"]
        for model in MODELS[1:]:
            group = [r for r in horizon_rows if r["model"] == model]
            if [r["origin"] for r in group] != [r["origin"] for r in base_rows]:
                raise ValueError("comparison origins do not match")
            delta = np.array(
                [
                    (b["observed_change_bp"] - b["forecast_bp"]) ** 2
                    - (m["observed_change_bp"] - m["forecast_bp"]) ** 2
                    for b, m in zip(base_rows, group)
                ],
                dtype=float,
            )
            item = report["models"][f"h{horizon}:{model}"]
            item["relative_mse_reduction_vs_no_change"] = float(
                delta.mean() / base["mse_bp2"]
            ) if base["mse_bp2"] > 0 else None
            item["paired_mse_hac"] = newey_west_tstat(
                delta.tolist(), lags=2 * horizon
            )

    primary = report["models"].get(f"h{PRIMARY_HORIZON}:{PRIMARY_MODEL}", {})
    report["primary_relative_mse_reduction"] = primary.get(
        "relative_mse_reduction_vs_no_change"
    )
    report["primary_passed_point_estimate"] = (
        report["primary_relative_mse_reduction"] is not None
        and report["primary_relative_mse_reduction"] > 0
    )
    return report


def freeze() -> None:
    if FREEZE.exists():
        raise FileExistsError("freeze receipt already exists")
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("curve-system family already registered; reconcile")
    for tenor, (rel, digest) in SOURCE_FILES.items():
        if file_hash(ROOT / rel) != digest:
            raise ValueError(f"source changed before freeze: {tenor}")
    panel = load_panel()
    receipt = {
        "schema": "ric.curve_system_dns.freeze.v1",
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "outcomes_opened_for_this_construction": False,
        "company_history_previously_examined": True,
        "spec": SPEC,
        "source_hashes": {rel: digest for rel, digest in SOURCE_FILES.values()},
        "source_coverage": {
            "rows": int(len(panel)),
            "start": panel.index.min().date().isoformat(),
            "end": panel.index.max().date().isoformat(),
        },
        "files": {name: file_hash(ROOT / name) for name in FROZEN_PATHS},
        "trial_ledger_before_sha256": file_hash(ledger_path),
        "prior_family_trials": 0,
        "new_configs": len(MODELS) * len(HORIZONS),
        "primary": f"h{PRIMARY_HORIZON}:{PRIMARY_MODEL}_vs_no_change",
        "authority": False,
    }
    FREEZE.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


def verify_freeze(receipt: dict) -> None:
    if receipt.get("spec") != SPEC:
        raise ValueError("frozen spec mismatch")
    if set(receipt.get("files", {})) != set(FROZEN_PATHS):
        raise ValueError("frozen file set mismatch")
    for name, digest in receipt["files"].items():
        if file_hash(ROOT / name) != digest:
            raise ValueError("post-freeze source change: " + name)
    for rel, digest in receipt.get("source_hashes", {}).items():
        if file_hash(ROOT / rel) != digest:
            raise ValueError("post-freeze Treasury source change: " + rel)


def run(output: Path) -> None:
    receipt = json.loads(FREEZE.read_text(encoding="utf-8"))
    verify_freeze(receipt)
    ledger_path = ROOT / "data/trial_ledger.jsonl"
    if file_hash(ledger_path) != receipt["trial_ledger_before_sha256"]:
        raise ValueError("trial ledger changed after freeze; reconcile")
    ledger = TrialLedger(path=ledger_path, family=FAMILY)
    if ledger.literal_n() != 0:
        raise ValueError("curve-system family state changed; reconcile")

    configs = [
        {
            "model": model,
            "horizon": horizon,
            "spec": SPEC,
            "freeze_sha256": file_hash(FREEZE),
            "source_hashes": receipt["source_hashes"],
        }
        for horizon in HORIZONS
        for model in MODELS
    ]
    registered = ledger.log_grid(
        configs,
        info_cutoff=receipt["frozen_at"],
        source="corrected_history_dynamic_curve_system",
        note="Fixed DNS factor dynamics; 2021-25 primary; no prospective or trade authority.",
    )
    if registered != len(configs) or ledger.literal_n() != len(configs):
        raise ValueError("partial curve-system registration; reconcile")

    output.mkdir(parents=True, exist_ok=False)
    registration = {
        "family": FAMILY,
        "registered": registered,
        "literal_n": ledger.literal_n(),
        "trial_ledger_before_sha256": receipt["trial_ledger_before_sha256"],
        "trial_ledger_after_sha256": file_hash(ledger_path),
        "freeze_sha256": file_hash(FREEZE),
    }
    (output / "registration.json").write_text(
        json.dumps(registration, indent=2) + "\n",
        encoding="utf-8",
    )

    panel = load_panel()
    results = [walk_forward(panel, horizon, SPEC) for horizon in HORIZONS]
    with (output / "predictions.jsonl").open("x", encoding="utf-8") as fh:
        for result in results:
            for row in result["rows"]:
                fh.write(json.dumps(row, allow_nan=False) + "\n")

    primary_start, primary_end = SPEC["primary_period"]
    context_start, context_end = SPEC["context_period"]
    summary = {
        "schema": "ric.curve_system_dns.result.v1",
        "spec": SPEC,
        "source_hashes": receipt["source_hashes"],
        "registration": registration,
        "factor_reconstruction_rmse_bp": {
            f"h{r['horizon']}": r["factor_reconstruction_rmse_bp"]
            for r in results
        },
        "coverage": {f"h{r['horizon']}": r["coverage"] for r in results},
        "primary": summarize(
            results, start=primary_start, end=primary_end, spec=SPEC
        ),
        "pre_primary_context": summarize(
            results, start=context_start, end=context_end, spec=SPEC
        ),
        "predictions_sha256": file_hash(output / "predictions.jsonl"),
        "historical_availability_qualified": False,
        "prospective_validation": False,
        "authority": False,
    }
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "primary": summary["primary"],
                "factor_reconstruction_rmse_bp": summary[
                    "factor_reconstruction_rmse_bp"
                ],
                "registration": registration,
                "output": str(output),
            },
            indent=2,
        )
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("freeze", "run"))
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.action == "freeze":
        freeze()
    else:
        if args.output is None:
            ap.error("run requires --output")
        run(args.output)


if __name__ == "__main__":
    main()
