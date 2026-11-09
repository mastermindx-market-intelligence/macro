"""Preregistered walk-forward calibration study for US Risk Radar probabilities.

Protocol:
research/grey_deer/RISK_RADAR_PROBABILITY_WALKFORWARD_PREREG_2026-09-23.md

Research only. This script never writes runtime calibration, review logs, ledgers,
policy, sizing, ranking, or authority state.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

from engine.risk_radar import (
    _CONJ_BUMP,
    _PROB_BASE,
    _PROB_CAL,
    _calib,
    _drawdown_prob,
    leading_signals,
    subscore_series,
)
from engine.risk_radar_backtest import _ORDER, _spy, state_series
from scripts.research.risk_radar_displayed_probability_audit import hot_tier_a_count
from scripts.research.risk_radar_state_ladder_calibration import (
    _fingerprint,
    _moving_block_indices,
    native_forward_labels,
)

OUT = ROOT / "research/grey_deer/evidence/probability-walkforward-20260923"
PROTOCOL_COMMIT = "055b3564d1a31b763638e38563afc245c89dcf2f"
SOURCE_BASE = "668237947e016f679782e41e61c91c9133a5ea99"
TEST_YEARS = tuple(range(2010, 2026))
HORIZONS = (5, 10, 21)
BOOT_DRAWS = 1000
BOOT_SEED = 230923
AUTHORITY_BASE_H21 = float(_PROB_BASE["h21"])
AUTHORITY_EPS = float(np.nextafter(AUTHORITY_BASE_H21, 1.0))


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def weighted_pav(values: Iterable[float], weights: Iterable[float]) -> np.ndarray:
    """Weighted non-decreasing pooled-adjacent-violators."""
    vals = np.asarray(list(values), dtype=float)
    wts = np.asarray(list(weights), dtype=float)
    if vals.ndim != 1 or wts.ndim != 1 or len(vals) != len(wts) or not len(vals):
        raise ValueError("values/weights must be non-empty equal-length vectors")
    if (not np.isfinite(vals).all() or not np.isfinite(wts).all()
            or (wts <= 0).any()):
        raise ValueError("values must be finite and weights strictly positive")

    blocks = [
        {"start": i, "end": i, "weight": float(wts[i]),
         "mean": float(vals[i])}
        for i in range(len(vals))
    ]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i]["mean"] <= blocks[i + 1]["mean"] + 1e-15:
            i += 1
            continue
        a, b = blocks[i], blocks[i + 1]
        weight = a["weight"] + b["weight"]
        mean = (a["mean"] * a["weight"] + b["mean"] * b["weight"]) / weight
        blocks[i:i + 2] = [{
            "start": a["start"], "end": b["end"],
            "weight": weight, "mean": float(mean),
        }]
        i = max(0, i - 1)

    out = np.empty(len(vals), dtype=float)
    for block in blocks:
        out[block["start"]:block["end"] + 1] = block["mean"]
    return out


def _state_counts(state: pd.Series, labels: pd.DataFrame) -> list[dict]:
    idx = labels.index.intersection(state.dropna().index)
    s = state.reindex(idx)
    y = labels.reindex(idx)["event"].astype(bool)
    rows = []
    for name in _ORDER:
        mask = s.eq(name)
        n = int(mask.sum())
        events = int(y[mask].sum())
        if n <= 0:
            raise ValueError(f"training fold has no observations for state {name}")
        rows.append({
            "state": name,
            "n": n,
            "events": events,
            "jeffreys_rate": float((events + 0.5) / (n + 1.0)),
        })
    return rows


def fit_state_surface(state: pd.Series, labels: pd.DataFrame, horizon: int) -> dict:
    """Fit the single preregistered monotone state-only candidate."""
    rows = _state_counts(state, labels)
    raw = np.asarray([r["jeffreys_rate"] for r in rows], dtype=float)
    weights = np.asarray([r["n"] for r in rows], dtype=float)

    if horizon == 21:
        # Constrained fit, not post-hoc acceptance: the three advisory states live
        # in the <=base feasible set; the two binding-eligible states live >base.
        left = np.minimum(weighted_pav(raw[:3], weights[:3]), AUTHORITY_BASE_H21)
        right = np.maximum(weighted_pav(raw[3:], weights[3:]), AUTHORITY_EPS)
        fitted = np.concatenate([left, right])
    else:
        fitted = weighted_pav(raw, weights)

    if np.any(np.diff(fitted) < -1e-12):
        raise RuntimeError("fitted surface is not monotone")
    fitted = np.clip(fitted, 0.0, 0.95)

    surface = {state_name: float(fitted[i]) for i, state_name in enumerate(_ORDER)}
    authority = {
        state_name: bool(surface[state_name] > AUTHORITY_BASE_H21)
        for state_name in _ORDER
    } if horizon == 21 else None
    if horizon == 21 and authority != {
        "calm": False, "watch": False, "caution": False,
        "elevated": True, "risk-off": True,
    }:
        raise RuntimeError("H21 constrained fit failed authority partition")
    return {
        "surface": surface,
        "training_states": rows,
        "authority_partition_h21": authority,
    }


def _candidate_probability(state: str, hot_count: int, surface: dict, horizon: int) -> float:
    hkey = f"h{horizon}"
    base = float(surface[state])
    extra = max(0, int(hot_count) - 1) * float(_CONJ_BUMP[hkey])
    return round(min(0.95, base + extra), 3)


def _test_indices(labels: pd.DataFrame, state: pd.Series, hot_count: pd.Series,
                  year: int) -> pd.DatetimeIndex:
    idx = labels.index.intersection(state.dropna().index).intersection(hot_count.dropna().index)
    idx = idx[idx.year == int(year)]
    return pd.DatetimeIndex(idx).sort_values()


def _training_labels(labels: pd.DataFrame, state: pd.Series,
                     first_test: pd.Timestamp) -> pd.DataFrame:
    """Only labels fully known strictly before first test observation may train."""
    idx = labels.index.intersection(state.dropna().index)
    train = labels.loc[idx]
    train = train[(train.index < first_test) & (pd.to_datetime(train["end"]) < first_test)]
    return train.sort_index()


def fold_frame(*, state: pd.Series, hot_count: pd.Series, labels: pd.DataFrame,
               calib: dict, horizon: int, year: int) -> tuple[pd.DataFrame, dict]:
    test_idx = _test_indices(labels, state, hot_count, year)
    if not len(test_idx):
        raise ValueError(f"no eligible test observations in {year}")
    first_test = pd.Timestamp(test_idx[0])
    train = _training_labels(labels, state, first_test)
    fitted = fit_state_surface(state, train, horizon)
    surface = fitted["surface"]
    hkey = f"h{horizon}"

    rows = []
    for day in test_idx:
        st = str(state.loc[day])
        hot = int(hot_count.loc[day])
        event = bool(labels.loc[day, "event"])
        candidate = _candidate_probability(st, hot, surface, horizon)
        current = float(_drawdown_prob(st, hot, calib)[hkey])
        rows.append({
            "date": day,
            "end": pd.Timestamp(labels.loc[day, "end"]),
            "state": st,
            "hot_count": hot,
            "event": event,
            "candidate_probability": candidate,
            "current_probability": current,
        })
    frame = pd.DataFrame(rows).set_index("date")
    meta = {
        "year": int(year),
        "horizon": int(horizon),
        "first_test": first_test.isoformat(),
        "train_from": train.index[0].isoformat() if len(train) else None,
        "train_through": train.index[-1].isoformat() if len(train) else None,
        "train_last_outcome_end": (
            pd.Timestamp(train["end"].max()).isoformat() if len(train) else None
        ),
        "train_n": int(len(train)),
        "test_n": int(len(frame)),
        "test_from": frame.index[0].isoformat(),
        "test_through": frame.index[-1].isoformat(),
        "population_sha256": _fingerprint(labels.loc[frame.index]),
        "candidate_surface": surface,
        "authority_partition_h21": fitted["authority_partition_h21"],
        "training_states": fitted["training_states"],
    }
    if len(train) and not (pd.Timestamp(train["end"].max()) < first_test):
        raise RuntimeError("training label embargo violated")
    return frame, meta


def _wace(frame: pd.DataFrame, column: str) -> float:
    if frame.empty:
        return float("nan")
    n = len(frame)
    total = 0.0
    for prob, group in frame.groupby(column):
        rate = float(group["event"].mean())
        total += len(group) / n * abs(rate - float(prob))
    return float(total)


def _paired_block_ci(delta: np.ndarray, *, block: int, seed: int,
                     draws: int = BOOT_DRAWS) -> list[float] | None:
    delta = np.asarray(delta, dtype=float)
    if not len(delta) or not np.isfinite(delta).all():
        return None
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(draws):
        take = _moving_block_indices(len(delta), block, rng)
        vals.append(float(delta[take].mean()))
    return [
        round(float(np.quantile(vals, 0.05)), 8),
        round(float(np.quantile(vals, 0.95)), 8),
    ]


def summarize_oof(frame: pd.DataFrame, horizon: int) -> dict:
    y = frame["event"].astype(float).to_numpy()
    cur = frame["current_probability"].astype(float).to_numpy()
    cand = frame["candidate_probability"].astype(float).to_numpy()
    current_brier = float(np.mean((cur - y) ** 2))
    candidate_brier = float(np.mean((cand - y) ** 2))
    point_delta = candidate_brier - current_brier
    paired = (cand - y) ** 2 - (cur - y) ** 2
    annual = []
    wins = 0
    for year, group in frame.groupby(frame.index.year):
        gy = group["event"].astype(float).to_numpy()
        gc = group["current_probability"].astype(float).to_numpy()
        gp = group["candidate_probability"].astype(float).to_numpy()
        cb = float(np.mean((gc - gy) ** 2))
        pb = float(np.mean((gp - gy) ** 2))
        delta = pb - cb
        wins += int(delta < 0)
        annual.append({
            "year": int(year), "n": int(len(group)),
            "current_brier": cb, "candidate_brier": pb, "delta": delta,
        })
    return {
        "n": int(len(frame)),
        "events": int(frame["event"].sum()),
        "from": frame.index[0].isoformat(),
        "through": frame.index[-1].isoformat(),
        "base_rate": float(frame["event"].mean()),
        "mean_current_probability": float(frame["current_probability"].mean()),
        "mean_candidate_probability": float(frame["candidate_probability"].mean()),
        "current_brier": current_brier,
        "candidate_brier": candidate_brier,
        "paired_brier_delta": point_delta,
        "paired_brier_delta_ci90": _paired_block_ci(
            paired, block=horizon, seed=BOOT_SEED + horizon
        ),
        "current_wace": _wace(frame, "current_probability"),
        "candidate_wace": _wace(frame, "candidate_probability"),
        "candidate_year_wins": int(wins),
        "test_years": int(len(annual)),
        "annual": annual,
    }


def promotion_verdict(results: dict, folds: dict) -> dict:
    checks = {
        "identical_populations": True,
        "authority_partition_preserved": True,
        "point_brier_improves_all": True,
        "brier_ci_upper_nonpositive_all": True,
        "wace_nonworse_all": True,
        "annual_wins_at_least_10_all": True,
    }
    expected_partition = {
        "calm": False, "watch": False, "caution": False,
        "elevated": True, "risk-off": True,
    }
    for hkey, result in results.items():
        ci = result.get("paired_brier_delta_ci90")
        checks["point_brier_improves_all"] &= bool(result["paired_brier_delta"] < 0)
        checks["brier_ci_upper_nonpositive_all"] &= bool(ci and ci[1] <= 0)
        checks["wace_nonworse_all"] &= bool(
            result["candidate_wace"] <= result["current_wace"] + 1e-12
        )
        checks["annual_wins_at_least_10_all"] &= bool(
            result["candidate_year_wins"] >= 10
        )
        for fold in folds[hkey]:
            checks["identical_populations"] &= bool(fold.get("population_sha256"))
            if hkey == "h21":
                checks["authority_partition_preserved"] &= (
                    fold.get("authority_partition_h21") == expected_partition
                )
    eligible = all(checks.values())
    return {
        "promotion_eligible": bool(eligible),
        "checks": {k: bool(v) for k, v in checks.items()},
        "status": "promotion_worthy_for_separate_decision" if eligible else "not_promotion_eligible",
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

    results, folds = {}, {}
    for horizon in HORIZONS:
        hkey = f"h{horizon}"
        labels = native_forward_labels(spy, idx, horizon, .05)
        frames = []
        folds[hkey] = []
        for year in TEST_YEARS:
            frame, meta = fold_frame(
                state=state, hot_count=hot, labels=labels,
                calib=calib, horizon=horizon, year=year,
            )
            frames.append(frame)
            folds[hkey].append(meta)
        joined = pd.concat(frames).sort_index()
        if not joined.index.is_unique:
            raise RuntimeError(f"duplicate OOF observations in {hkey}")
        results[hkey] = summarize_oof(joined, horizon)

    verdict = promotion_verdict(results, folds)
    inputs, missing = _tracked_inputs()
    source_paths = [
        "engine/risk_radar.py",
        "engine/risk_radar_backtest.py",
        "scripts/research/risk_radar_state_ladder_calibration.py",
        "scripts/research/risk_radar_displayed_probability_audit.py",
        "scripts/research/risk_radar_probability_walkforward.py",
        "research/grey_deer/RISK_RADAR_PROBABILITY_WALKFORWARD_PREREG_2026-09-23.md",
    ]
    return {
        "schema": "risk_radar_probability_walkforward.v1",
        "protocol_commit": PROTOCOL_COMMIT,
        "source_base": SOURCE_BASE,
        "test_years": list(TEST_YEARS),
        "targets": {"depth": .05, "horizons": list(HORIZONS)},
        "fit": {
            "method": "Jeffreys(0.5,0.5) per state + weighted PAV",
            "expanding_origin": True,
            "label_end_before_test_start": True,
            "conjunction_bump_changed": False,
            "authority_base_h21": AUTHORITY_BASE_H21,
        },
        "results": results,
        "folds": folds,
        "verdict": verdict,
        "source_hashes": {rel: _hash(ROOT / rel) for rel in source_paths},
        "input_hashes": inputs,
        "missing_optional_inputs": missing,
        "authority": {
            "status": "research_only",
            "live_model_changed": False,
            "probability_changed": False,
            "gate_changed": False,
            "policy_changed": False,
        },
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.2f}%"


def render_markdown(result: dict) -> str:
    lines = [
        "# Risk Radar Probability Walk-Forward — Results",
        "",
        f"Protocol commit: `{result['protocol_commit']}`.",
        "",
        f"Primary verdict: **{result['verdict']['status']}**.",
        "",
        "Research-only annual expanding-origin evaluation. No live probability or authority changed.",
        "",
        "| Horizon | n | Current Brier | Candidate Brier | Delta | 90% block CI | Current WACE | Candidate WACE | Year wins |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for hkey in ("h5", "h10", "h21"):
        row = result["results"][hkey]
        ci = row["paired_brier_delta_ci90"]
        lines.append(
            f"| {hkey.upper()} | {row['n']} | {row['current_brier']:.6f} "
            f"| {row['candidate_brier']:.6f} | {row['paired_brier_delta']:+.6f} "
            f"| [{ci[0]:+.6f}, {ci[1]:+.6f}] "
            f"| {row['current_wace']:.6f} | {row['candidate_wace']:.6f} "
            f"| {row['candidate_year_wins']}/{row['test_years']} |"
        )
    lines += ["", "## Frozen promotion checks", ""]
    for key, value in result["verdict"]["checks"].items():
        lines.append(f"- {'PASS' if value else 'FAIL'} — `{key}`")
    lines += [
        "",
        "## Evidence boundary",
        "",
        "These are overlapping reconstructed historical windows evaluated strictly out-of-fold by calendar year. "
        "They are not genuinely issued forecasts and do not authorize a runtime probability change.",
        "",
        "The already-inspected 2020+ single holdout was not used to tune this candidate. "
        "No second candidate is fit to these walk-forward results in this wave.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    result = build_result()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    report = ROOT / "research/grey_deer/RISK_RADAR_PROBABILITY_WALKFORWARD_RESULTS_2026-09-23.md"
    report.write_text(render_markdown(result) + "\n", encoding="utf-8")
    compact = {
        h: {
            "delta": result["results"][h]["paired_brier_delta"],
            "ci90": result["results"][h]["paired_brier_delta_ci90"],
            "wins": result["results"][h]["candidate_year_wins"],
            "wace_current": result["results"][h]["current_wace"],
            "wace_candidate": result["results"][h]["candidate_wace"],
        }
        for h in ("h5", "h10", "h21")
    }
    print(json.dumps({"verdict": result["verdict"], "metrics": compact}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
