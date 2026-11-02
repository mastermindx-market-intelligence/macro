"""Audit the complete displayed US Risk Radar pullback probability surface.

No-fit descriptive research only. Frozen protocol:
research/grey_deer/RISK_RADAR_DISPLAYED_PROBABILITY_AUDIT_PREREG_2026-09-22.md
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.risk_radar import (
    _CONJ_BUMP,
    _PROB_CAL,
    _calib,
    _drawdown_prob,
    leading_signals,
    subscore_series,
)
from engine.risk_radar_backtest import _spy, state_accuracy, state_series
from scripts.research.risk_radar_state_ladder_calibration import (
    _fingerprint,
    _moving_block_indices,
    native_forward_labels,
)

OUT = ROOT / "research/grey_deer/evidence/displayed-probability-audit-20260922"
PROTOCOL_COMMIT = "f520eda41e0ff5051caf4bc019e198eabd949e49"
SOURCE_BASE = "912feaa2b13959a6cca4d3f1472188b4a4d702bb"
HORIZONS = (5, 10, 21)
WINDOWS = (("full", None), ("y2006", "2006-01-01"), ("y2020", "2020-01-01"))
BOOT_DRAWS = 1000
BOOT_SEED = 220922
THIN_N = 100


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def hot_tier_a_count(subs: pd.DataFrame, calib: dict) -> pd.Series:
    """Count Tier-A scare sub-scores at or above the shipped caution cut."""
    tier_a = [
        scare for scare, spec in calib["scares"].items()
        if spec.get("tier") == "A" and scare in subs.columns
    ]
    if not tier_a:
        return pd.Series(0, index=subs.index, dtype=int)
    return sum(
        (subs[scare] >= calib["bands"]["caution"]).astype(int)
        for scare in tier_a
    ).astype(int)


def displayed_probability_series(
    state: pd.Series, hot_count: pd.Series, calib: dict, horizon: int
) -> pd.Series:
    """Canonical displayed probability for every dated state/count pair."""
    hkey = f"h{horizon}"
    idx = state.index.intersection(hot_count.index)
    vals = []
    for day in idx:
        st = state.loc[day]
        n = hot_count.loc[day]
        if st is None or pd.isna(st) or n is None or pd.isna(n):
            vals.append(np.nan)
        else:
            vals.append(float(_drawdown_prob(str(st), int(n), calib)[hkey]))
    return pd.Series(vals, index=idx, dtype=float)


def _q90(values: list[float]) -> list[float] | None:
    clean = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if not len(clean):
        return None
    return [
        round(float(np.quantile(clean, .05)), 6),
        round(float(np.quantile(clean, .95)), 6),
    ]


def _cell_composition(frame: pd.DataFrame) -> list[dict]:
    rows = []
    grouped = frame.groupby(["state", "hot_count"], dropna=False)
    for (state, hot_count), group in grouped:
        rows.append({
            "state": str(state),
            "hot_count": int(hot_count),
            "n": int(len(group)),
        })
    return sorted(rows, key=lambda r: (r["state"], r["hot_count"]))


def _bootstrap(
    frame: pd.DataFrame,
    *,
    block: int,
    seed: int,
    draws: int = BOOT_DRAWS,
) -> dict:
    """Moving-block uncertainty for overall metrics and exact-cell observed rates."""
    if frame.empty:
        return {"brier": None, "calibration_gap": None, "cell_rates": {}}
    probs = frame["probability"].to_numpy(dtype=float)
    y = frame["event"].to_numpy(dtype=bool)
    cells = sorted(float(v) for v in frame["probability"].unique())
    rng = np.random.default_rng(seed)
    briers: list[float] = []
    gaps: list[float] = []
    cell_draws = {cell: [] for cell in cells}
    for _ in range(draws):
        take = _moving_block_indices(len(frame), block, rng)
        pb, yb = probs[take], y[take]
        briers.append(float(np.mean((pb - yb.astype(float)) ** 2)))
        gaps.append(float(pb.mean() - yb.mean()))
        for cell in cells:
            mask = pb == cell
            cell_draws[cell].append(float(yb[mask].mean()) if mask.any() else np.nan)
    return {
        "brier": _q90(briers),
        "calibration_gap": _q90(gaps),
        "cell_rates": {str(cell): _q90(values) for cell, values in cell_draws.items()},
    }


def summarize_window(
    state: pd.Series,
    hot_count: pd.Series,
    probability: pd.Series,
    labels: pd.DataFrame,
    *,
    block: int,
    seed: int,
) -> dict:
    idx = labels.index.intersection(state.dropna().index)
    idx = idx.intersection(probability.dropna().index)
    frame = pd.DataFrame({
        "state": state.reindex(idx),
        "hot_count": hot_count.reindex(idx).astype(int),
        "probability": probability.reindex(idx).astype(float),
        "event": labels.reindex(idx)["event"].astype(bool),
    }, index=idx)
    y = frame["event"].astype(float)
    p = frame["probability"]
    n = int(len(frame))
    base_rate = float(y.mean()) if n else None
    brier = float(np.mean((p - y) ** 2)) if n else None
    base_brier = float(np.mean((base_rate - y) ** 2)) if n else None
    skill = (
        1.0 - brier / base_brier
        if brier is not None and base_brier not in (None, 0.0)
        else None
    )
    mean_p = float(p.mean()) if n else None
    observed = base_rate
    gap = (mean_p - observed) if mean_p is not None and observed is not None else None

    cells = {}
    weighted_abs = 0.0
    weighted_sq = 0.0
    for cell, group in frame.groupby("probability"):
        cell = float(cell)
        cn = int(len(group))
        events = int(group["event"].sum())
        rate = events / cn if cn else None
        cell_gap = (rate - cell) if rate is not None else None
        if rate is not None and n:
            w = cn / n
            weighted_abs += w * abs(cell_gap)
            weighted_sq += w * (cell_gap ** 2)
        cells[str(cell)] = {
            "probability": cell,
            "n": cn,
            "events": events,
            "observed_rate": rate,
            "observed_minus_displayed": cell_gap,
            "thin": bool(cn < THIN_N),
            "composition": _cell_composition(group),
        }

    boot = _bootstrap(frame, block=block, seed=seed)
    for key, cell in cells.items():
        cell["observed_rate_ci90"] = boot["cell_rates"].get(key)

    return {
        "from": idx[0].isoformat() if n else None,
        "through": idx[-1].isoformat() if n else None,
        "n": n,
        "events": int(frame["event"].sum()) if n else 0,
        "base_rate": base_rate,
        "mean_displayed_probability": mean_p,
        "calibration_in_large_gap": gap,
        "calibration_in_large_gap_ci90": boot["calibration_gap"],
        "brier_score": brier,
        "brier_score_ci90": boot["brier"],
        "base_rate_brier_score": base_brier,
        "brier_skill_score": skill,
        "weighted_absolute_calibration_error": weighted_abs if n else None,
        "root_weighted_squared_calibration_error": float(np.sqrt(weighted_sq)) if n else None,
        "population_sha256": _fingerprint(labels.loc[idx]),
        "cells": cells,
        "bootstrap": {
            "method": "circular_moving_block",
            "block_observations": int(block),
            "draws": int(BOOT_DRAWS),
            "seed": int(seed),
            "ci": 0.90,
        },
    }


def _tracked_inputs() -> tuple[dict[str, str], list[str]]:
    paths = [
        "data/yahoo/SPY.parquet", "data/fred/BAMLH0A0HYM2.parquet",
        "data/yahoo/HYG.parquet", "data/yahoo/TLT.parquet",
        "data/yahoo/_MOVE.parquet", "data/fred/DFII10.parquet",
        "data/yahoo/SMH.parquet", "data/yahoo/XLU.parquet",
        "data/yahoo/XLP.parquet", "data/yahoo/XLY.parquet",
        "data/yahoo/_VIX.parquet", "data/yahoo/_VIX3M.parquet",
        "data/yahoo/_VIX9D.parquet", "data/cboe/putcall.parquet",
        "data/cboe/gex.parquet", "data/fred/DEXJPUS.parquet",
        "data/breadth/breadth.parquet", "data/risk_radar/calibration.json",
    ]
    hashes, missing = {}, []
    for rel in paths:
        path = ROOT / rel
        if path.exists():
            hashes[rel] = _hash(path)
        else:
            missing.append(rel)
    return hashes, missing


def _scope(labels: pd.DataFrame, lo: str | None) -> pd.DataFrame:
    if lo is None:
        return labels
    return labels.loc[labels.index >= pd.Timestamp(lo)]


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
    hot_count = hot_tier_a_count(subs, calib).reindex(idx)
    spy = _spy(drop_missing=False)

    results = {}
    canonical = {}
    for horizon in HORIZONS:
        hkey = f"h{horizon}"
        labels = native_forward_labels(spy, idx, horizon, .05)
        probability = displayed_probability_series(state, hot_count, calib, horizon)
        results[hkey] = {}
        canonical[hkey] = {}
        for widx, (name, lo) in enumerate(WINDOWS):
            scoped = _scope(labels, lo)
            summary = summarize_window(
                state, hot_count, probability, scoped,
                block=horizon,
                seed=BOOT_SEED + horizon * 10 + widx,
            )
            check = state_accuracy(calib, H=horizon, dd=.05, lo=lo)
            evidence = check.get("evaluation") or {}
            canonical[hkey][name] = {
                "n_days": check.get("n_days"),
                "outcomes_sha256": evidence.get("outcomes_sha256"),
                "confusion": evidence.get("confusion"),
            }
            if summary["n"] != check.get("n_days"):
                raise RuntimeError(f"canonical population count mismatch {hkey}/{name}")
            if summary["population_sha256"] != evidence.get("outcomes_sha256"):
                raise RuntimeError(f"canonical outcome fingerprint mismatch {hkey}/{name}")
            results[hkey][name] = summary

    inputs, missing = _tracked_inputs()
    source_paths = [
        "engine/risk_radar.py",
        "engine/risk_radar_backtest.py",
        "scripts/research/risk_radar_displayed_probability_audit.py",
        "research/grey_deer/RISK_RADAR_DISPLAYED_PROBABILITY_AUDIT_PREREG_2026-09-22.md",
    ]
    return {
        "schema": "risk_radar_displayed_probability_audit.v1",
        "protocol_commit": PROTOCOL_COMMIT,
        "source_base": SOURCE_BASE,
        "targets": {"depth": .05, "horizons": list(HORIZONS)},
        "windows": [name for name, _ in WINDOWS],
        "state_probability_surface": (calib.get("prob_cal") or _PROB_CAL),
        "conjunction_bump": dict(_CONJ_BUMP),
        "results": results,
        "canonical_crosscheck": canonical,
        "source_hashes": {rel: _hash(ROOT / rel) for rel in source_paths},
        "input_hashes": inputs,
        "missing_optional_inputs": missing,
        "authority": {
            "status": "descriptive_no_fit",
            "live_model_changed": False,
            "probability_changed": False,
            "gate_changed": False,
            "policy_changed": False,
        },
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100.0 * value:.1f}%"


def _pp(value: float | None) -> str:
    return "—" if value is None else f"{100.0 * value:+.1f}pp"


def render_markdown(result: dict) -> str:
    lines = [
        "# Risk Radar Displayed-Probability Audit — Results",
        "",
        f"Protocol commit: `{result['protocol_commit']}`.",
        "",
        "Historical reconstructed diagnostic only; no live probability or model value changed.",
        "",
    ]
    for hkey in ("h5", "h10", "h21"):
        lines += [f"## {hkey.upper()}", ""]
        lines.append(
            "| Window | n | Events | Base | Mean displayed | Gap | Brier | Base Brier | Brier skill | WACE | RWSCE |"
        )
        lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
        for wname, _ in WINDOWS:
            row = result["results"][hkey][wname]
            skill = row["brier_skill_score"]
            lines.append(
                f"| {wname} | {row['n']} | {row['events']} | {_pct(row['base_rate'])} "
                f"| {_pct(row['mean_displayed_probability'])} | {_pp(row['calibration_in_large_gap'])} "
                f"| {row['brier_score']:.4f} | {row['base_rate_brier_score']:.4f} "
                f"| {skill:.3f} | {row['weighted_absolute_calibration_error']:.4f} "
                f"| {row['root_weighted_squared_calibration_error']:.4f} |"
            )
        lines.append("")
        lines.append(
            "| Window | Displayed p | n | Events | Observed | 90% block CI | Obs-p | Thin | Composition |"
        )
        lines.append("|---|---:|---:|---:|---:|---|---:|---|---|")
        for wname, _ in WINDOWS:
            row = result["results"][hkey][wname]
            for cell in sorted(row["cells"].values(), key=lambda x: x["probability"]):
                ci = cell["observed_rate_ci90"]
                ci_text = "—" if ci is None else f"{_pct(ci[0])}..{_pct(ci[1])}"
                composition = ", ".join(
                    f"{c['state']}+{c['hot_count']}hot:{c['n']}"
                    for c in cell["composition"]
                )
                lines.append(
                    f"| {wname} | {_pct(cell['probability'])} | {cell['n']} | {cell['events']} "
                    f"| {_pct(cell['observed_rate'])} | {ci_text} "
                    f"| {_pp(cell['observed_minus_displayed'])} "
                    f"| {'YES' if cell['thin'] else ''} | {composition} |"
                )
        lines.append("")

    lines += [
        "## Evidence ceiling", "",
        "These are overlapping historical replay windows under the current code, not genuinely issued probabilities. "
        "Exact probability cells are not post-hoc bins: they are the discrete values the shipped function emits.",
        "",
        "No result in this audit authorizes a retune. Issued/prospective forecast evidence remains separate and higher authority.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    result = build_result()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    report = ROOT / "research/grey_deer/RISK_RADAR_DISPLAYED_PROBABILITY_AUDIT_RESULTS_2026-09-22.md"
    report.write_text(render_markdown(result) + "\n")
    compact = {
        h: {
            w: {
                "n": result["results"][h][w]["n"],
                "base_rate": result["results"][h][w]["base_rate"],
                "mean_p": result["results"][h][w]["mean_displayed_probability"],
                "brier_skill": result["results"][h][w]["brier_skill_score"],
                "wace": result["results"][h][w]["weighted_absolute_calibration_error"],
            }
            for w, _ in WINDOWS
        }
        for h in ("h5", "h10", "h21")
    }
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
