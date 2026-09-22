"""Out-of-sample US Risk Radar probability recalibration candidate study.

Frozen protocol:
research/grey_deer/RISK_RADAR_PROBABILITY_RECAL_OOS_PREREG_2026-09-22.md

Research only. Never writes live calibration, review logs, forward ledgers, or
runtime data.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.risk_radar import (
    _CONJ_BUMP,
    _PROB_BASE,
    _PROB_CAL,
    _STATE_ORDER,
    _calib,
    leading_signals,
    subscore_series,
)
from engine.risk_radar_backtest import _spy, state_series
from scripts.research.risk_radar_displayed_probability_audit import (
    displayed_probability_series,
    hot_tier_a_count,
    summarize_window,
)
from scripts.research.risk_radar_state_ladder_calibration import (
    _moving_block_indices,
    native_forward_labels,
)

PROTOCOL_COMMIT = "c64d72e14446f6f2e89924873aba7df2a67a9e02"
SOURCE_BASE = "9e9da53a671f3420b2cab9cca20b131c811a05df"
AUDIT_RESULT = ROOT / "research/grey_deer/evidence/displayed-probability-audit-20260922/result.json"
OUT = ROOT / "research/grey_deer/evidence/probability-recal-oos-20260922"
TRAIN_END = pd.Timestamp("2020-01-01")
HORIZONS = (5, 10, 21)
BOOT_DRAWS = 1000
BOOT_SEED = 260922
AUTHORITY_BELOW = ("calm", "watch", "caution")
AUTHORITY_ABOVE = ("elevated", "risk-off")


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def weighted_pav(values: list[float], weights: list[float]) -> list[float]:
    """Weighted non-decreasing pooled-adjacent-violators."""
    if len(values) != len(weights) or not values:
        raise ValueError("values and weights must have equal non-zero length")
    blocks: list[dict[str, Any]] = []
    for idx, (value, weight) in enumerate(zip(values, weights)):
        value, weight = float(value), float(weight)
        if not np.isfinite(value) or not np.isfinite(weight) or weight <= 0:
            raise ValueError("PAV requires finite values and positive weights")
        blocks.append({"lo": idx, "hi": idx, "weight": weight, "mean": value})
        while len(blocks) >= 2 and blocks[-2]["mean"] > blocks[-1]["mean"]:
            right = blocks.pop()
            left = blocks.pop()
            total = left["weight"] + right["weight"]
            mean = (
                left["mean"] * left["weight"] + right["mean"] * right["weight"]
            ) / total
            blocks.append({
                "lo": left["lo"], "hi": right["hi"], "weight": total, "mean": mean
            })
    out = [0.0] * len(values)
    for block in blocks:
        for idx in range(block["lo"], block["hi"] + 1):
            out[idx] = float(block["mean"])
    return out


def fit_state_surface(
    state: pd.Series, labels_by_horizon: dict[int, pd.DataFrame]
) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    """Fit state-only surfaces from pre-2020 labels with fixed Jeffreys smoothing."""
    surface: dict[str, dict[str, float]] = {}
    detail: dict[str, Any] = {}
    for horizon in HORIZONS:
        labels = labels_by_horizon[horizon]
        train_idx = labels.index[labels.index < TRAIN_END].intersection(state.dropna().index)
        rows = []
        smooth, weights = [], []
        for name in _STATE_ORDER:
            mask = state.reindex(train_idx) == name
            n = int(mask.sum())
            events = int(labels.reindex(train_idx).loc[mask, "event"].sum()) if n else 0
            p = (events + 0.5) / (n + 1.0)
            smooth.append(float(p))
            weights.append(float(n + 1.0))
            rows.append({"state": name, "n": n, "events": events, "jeffreys_rate": p})
        pooled = weighted_pav(smooth, weights)
        hkey = f"h{horizon}"
        surface[hkey] = {
            name: float(pooled[idx]) for idx, name in enumerate(_STATE_ORDER)
        }
        for idx, row in enumerate(rows):
            row["candidate_rate"] = float(pooled[idx])
        detail[hkey] = {
            "from": train_idx[0].isoformat() if len(train_idx) else None,
            "through": train_idx[-1].isoformat() if len(train_idx) else None,
            "n": int(len(train_idx)),
            "states": rows,
        }
    return surface, detail


def candidate_probability_series(
    state: pd.Series,
    hot_count: pd.Series,
    surface: dict[str, dict[str, float]],
    horizon: int,
) -> pd.Series:
    """Candidate displayed odds: fitted state probability + shipped conjunction bump."""
    hkey = f"h{horizon}"
    idx = state.index.intersection(hot_count.index)
    values = []
    for day in idx:
        st = state.loc[day]
        hot = hot_count.loc[day]
        if st is None or pd.isna(st) or hot is None or pd.isna(hot):
            values.append(np.nan)
            continue
        base = surface[hkey].get(str(st))
        if base is None:
            values.append(np.nan)
            continue
        p = min(0.95, float(base) + max(int(hot) - 1, 0) * _CONJ_BUMP[hkey])
        values.append(float(p))
    return pd.Series(values, index=idx, dtype=float)


def authority_partition(surface: dict[str, dict[str, float]]) -> dict:
    """Check the H21 above-base partition used by Market-State authority."""
    base = float(_PROB_BASE["h21"])
    h21 = surface["h21"]
    checks = {
        **{state: bool(float(h21[state]) < base) for state in AUTHORITY_BELOW},
        **{state: bool(float(h21[state]) > base) for state in AUTHORITY_ABOVE},
    }
    return {"base_h21": base, "checks": checks, "preserved": bool(all(checks.values()))}


def surface_valid(surface: dict[str, dict[str, float]]) -> dict:
    rows = {}
    ok = True
    for hkey in ("h5", "h10", "h21"):
        vals = [float(surface[hkey][state]) for state in _STATE_ORDER]
        monotonic = all(a <= b for a, b in zip(vals, vals[1:]))
        bounded = all(0.0 <= value <= 0.60 for value in vals)
        rows[hkey] = {"monotonic": monotonic, "bounded_0_0p60": bounded}
        ok = ok and monotonic and bounded
    return {"horizons": rows, "valid": bool(ok)}


def paired_brier_delta(
    current: pd.Series,
    candidate: pd.Series,
    labels: pd.DataFrame,
    *,
    block: int,
    seed: int,
    draws: int = BOOT_DRAWS,
) -> dict:
    """Paired moving-block delta: candidate Brier minus current Brier."""
    idx = labels.index.intersection(current.dropna().index).intersection(candidate.dropna().index)
    y = labels.reindex(idx)["event"].astype(float).to_numpy()
    pc = current.reindex(idx).astype(float).to_numpy()
    pn = candidate.reindex(idx).astype(float).to_numpy()
    delta = float(np.mean((pn - y) ** 2 - (pc - y) ** 2)) if len(idx) else None
    rng = np.random.default_rng(seed)
    draws_out = []
    for _ in range(draws):
        take = _moving_block_indices(len(idx), block, rng)
        draws_out.append(float(np.mean(
            (pn[take] - y[take]) ** 2 - (pc[take] - y[take]) ** 2
        )))
    ci = None
    if draws_out:
        ci = [
            round(float(np.quantile(draws_out, 0.05)), 6),
            round(float(np.quantile(draws_out, 0.95)), 6),
        ]
    return {"n": int(len(idx)), "delta": delta, "ci90": ci}


def promotion_verdict(result: dict) -> dict:
    checks: dict[str, bool] = {}
    checks["authority_partition"] = bool(result["authority_partition"]["preserved"])
    checks["surface_valid"] = bool(result["surface_validity"]["valid"])
    for hkey in ("h5", "h10", "h21"):
        cur = result["holdout"][hkey]["current"]
        cand = result["holdout"][hkey]["candidate"]
        checks[f"{hkey}_point_brier_no_worse"] = cand["brier_score"] <= cur["brier_score"] + 1e-15
        checks[f"{hkey}_wace_no_material_harm"] = (
            cand["weighted_absolute_calibration_error"]
            <= cur["weighted_absolute_calibration_error"] + 0.005
        )
        checks[f"{hkey}_population_match"] = bool(result["holdout"][hkey]["accepted_population_match"])
    h21_ci = result["holdout"]["h21"]["paired_brier_delta"]["ci90"]
    checks["h21_ci_upper_nonpositive"] = bool(h21_ci and h21_ci[1] <= 0.0)
    for hkey in ("h5", "h10"):
        ci = result["holdout"][hkey]["paired_brier_delta"]["ci90"]
        checks[f"{hkey}_ci_upper_within_0p002"] = bool(ci and ci[1] <= 0.002)
    return {"checks": checks, "promotion_eligible": bool(all(checks.values()))}


def build_result() -> dict:
    calib = _calib()
    sigs = leading_signals()
    if sigs is None or sigs.empty:
        raise RuntimeError("leading_signals returned no usable history")
    subs = subscore_series(sigs, calib)
    if subs is None or subs.empty:
        raise RuntimeError("subscore_series returned no usable history")
    idx = sigs.index
    known = subs.notna().any(axis=1)
    state = state_series(subs, calib, sigs=sigs).reindex(idx).where(known)
    hot = hot_tier_a_count(subs, calib).reindex(idx)
    spy = _spy(drop_missing=False)

    labels_by_horizon = {
        h: native_forward_labels(spy, idx, h, 0.05) for h in HORIZONS
    }
    candidate_surface, training = fit_state_surface(state, labels_by_horizon)

    accepted = json.loads(AUDIT_RESULT.read_text(encoding="utf-8"))
    holdout: dict[str, Any] = {}
    for horizon in HORIZONS:
        hkey = f"h{horizon}"
        labels = labels_by_horizon[horizon]
        labels = labels.loc[labels.index >= TRAIN_END]
        current_p = displayed_probability_series(state, hot, calib, horizon)
        candidate_p = candidate_probability_series(state, hot, candidate_surface, horizon)
        current_summary = summarize_window(
            state, hot, current_p, labels,
            block=horizon, seed=BOOT_SEED + horizon * 10,
        )
        candidate_summary = summarize_window(
            state, hot, candidate_p, labels,
            block=horizon, seed=BOOT_SEED + horizon * 10 + 1,
        )
        accepted_fp = accepted["results"][hkey]["y2020"]["population_sha256"]
        holdout[hkey] = {
            "current": current_summary,
            "candidate": candidate_summary,
            "paired_brier_delta": paired_brier_delta(
                current_p, candidate_p, labels,
                block=horizon, seed=BOOT_SEED + horizon * 100,
            ),
            "accepted_population_sha256": accepted_fp,
            "accepted_population_match": bool(
                current_summary["population_sha256"] == accepted_fp
                and candidate_summary["population_sha256"] == accepted_fp
            ),
        }

    result = {
        "schema": "risk_radar_probability_recal_oos.v1",
        "protocol_commit": PROTOCOL_COMMIT,
        "source_base": SOURCE_BASE,
        "fit": {
            "window": "pre_2020",
            "method": "Jeffreys(0.5,0.5) per shipped state + weighted PAV",
            "state_only": True,
            "conjunction_bump_changed": False,
            "candidate_surface": candidate_surface,
            "training": training,
        },
        "current_surface": {h: dict(v) for h, v in (calib.get("prob_cal") or _PROB_CAL).items()},
        "conjunction_bump": dict(_CONJ_BUMP),
        "authority_partition": authority_partition(candidate_surface),
        "surface_validity": surface_valid(candidate_surface),
        "holdout": holdout,
        "audit_source": {
            "path": str(AUDIT_RESULT.relative_to(ROOT)),
            "sha256": _hash(AUDIT_RESULT),
        },
        "authority": {
            "live_write": False,
            "calibration_json_written": False,
            "review_log_written": False,
            "forward_ledger_written": False,
        },
    }
    result["promotion"] = promotion_verdict(result)
    return result


def main() -> int:
    result = build_result()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    compact = {
        "candidate_surface": result["fit"]["candidate_surface"],
        "authority_partition": result["authority_partition"],
        "promotion": result["promotion"],
        "holdout": {
            h: {
                "current_brier": result["holdout"][h]["current"]["brier_score"],
                "candidate_brier": result["holdout"][h]["candidate"]["brier_score"],
                "paired_delta": result["holdout"][h]["paired_brier_delta"],
                "current_wace": result["holdout"][h]["current"]["weighted_absolute_calibration_error"],
                "candidate_wace": result["holdout"][h]["candidate"]["weighted_absolute_calibration_error"],
            }
            for h in ("h5", "h10", "h21")
        },
    }
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
