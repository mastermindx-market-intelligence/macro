"""Risk Radar state-ladder calibration study.

Descriptive historical reconstruction only. Frozen protocol:
research/grey_deer/RISK_RADAR_STATE_LADDER_CALIBRATION_PREREG_2026-09-21.md
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

from engine.risk_radar import _PROB_CAL, _calib, leading_signals, subscore_series
from engine.risk_radar_backtest import _ORDER, _spy, state_accuracy, state_series

OUT = ROOT / "research/grey_deer/evidence/state-ladder-calibration-20260921"
PROTOCOL_COMMIT = "e9ff3d234df1f50137bfa38a50995a70f06c1164"
ORIGINAL_PROTOCOL_COMMIT = "22e779b1f4c7fbb27c1e204667d917c1d92727fa"
SOURCE_BASE = "7c6e35163c9f67087ffe174a7ab3810f47ce6a45"
HORIZONS = (5, 10, 21)
WINDOWS = (("full", None), ("y2006", "2006-01-01"), ("y2020", "2020-01-01"))
BOOT_DRAWS = 1000
BOOT_SEED = 260921
THIN_N = 100


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def native_forward_labels(
    spy: pd.Series, idx: pd.DatetimeIndex, horizon: int, depth: float = .05
) -> pd.DataFrame:
    """Complete native-price windows matching corrected replay semantics."""
    if type(horizon) is not int or horizon <= 0:
        raise ValueError("horizon must be a positive integer")
    pxs = spy.copy()
    if (
        not isinstance(pxs.index, pd.DatetimeIndex)
        or not pxs.index.is_unique
        or not pxs.index.is_monotonic_increasing
    ):
        raise ValueError("SPY observations require a unique ordered DatetimeIndex")
    bools = pxs.map(lambda value: isinstance(value, (bool, np.bool_)))
    px = pd.to_numeric(pxs, errors="coerce").where(~bools).to_numpy(dtype=float)
    good = np.isfinite(px) & (px > 0)
    rows = []
    for day, loc in zip(idx, pxs.index.get_indexer(idx)):
        if loc < 0 or loc + horizon >= len(px):
            continue
        window = px[loc:loc + horizon + 1]
        if not good[loc:loc + horizon + 1].all():
            continue
        loss = float(window[1:].min() / window[0] - 1.)
        rows.append({
            "date": day,
            "end": pxs.index[loc + horizon],
            "loss": loss,
            "event": bool(loss <= -depth),
        })
    if not rows:
        return pd.DataFrame(columns=["end", "loss", "event"])
    return pd.DataFrame(rows).set_index("date")


def _fingerprint(labels: pd.DataFrame) -> str:
    rows = [
        [d.isoformat(), row.end.isoformat(), float(row.loss).hex(), bool(row.event)]
        for d, row in labels.iterrows()
    ]
    return hashlib.sha256(
        json.dumps(rows, separators=(",", ":")).encode()
    ).hexdigest()


def _moving_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    if n <= 0 or block <= 0:
        raise ValueError("n and block must be positive")
    starts = rng.integers(0, n, size=int(np.ceil(n / block)))
    pieces = [(start + np.arange(block)) % n for start in starts]
    return np.concatenate(pieces)[:n]


def _q90(values: list[float]) -> list[float] | None:
    clean = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if not len(clean):
        return None
    return [round(float(np.quantile(clean, .05)), 6),
            round(float(np.quantile(clean, .95)), 6)]


def _bootstrap(
    states: pd.Series,
    outcomes: pd.Series,
    *,
    block: int,
    draws: int = BOOT_DRAWS,
    seed: int = BOOT_SEED,
) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    idx = states.index.intersection(outcomes.index)
    s = states.reindex(idx).to_numpy(dtype=object)
    y = outcomes.reindex(idx).to_numpy(dtype=bool)
    rng = np.random.default_rng(seed)
    state_draws = {state: [] for state in _ORDER}
    diff_draws = {f"{a}->{b}": [] for a, b in zip(_ORDER, _ORDER[1:])}
    for _ in range(draws):
        take = _moving_block_indices(len(idx), block, rng)
        sb, yb = s[take], y[take]
        rates = {}
        for state in _ORDER:
            mask = sb == state
            rate = float(yb[mask].mean()) if mask.any() else np.nan
            rates[state] = rate
            state_draws[state].append(rate)
        for a, b in zip(_ORDER, _ORDER[1:]):
            av, bv = rates[a], rates[b]
            diff_draws[f"{a}->{b}"].append(
                float(bv - av) if np.isfinite(av) and np.isfinite(bv) else np.nan
            )
    return state_draws, diff_draws


def summarize_window(
    state: pd.Series,
    labels: pd.DataFrame,
    configured: dict[str, float],
    *,
    block: int,
    seed: int,
) -> dict:
    idx = labels.index.intersection(state.dropna().index)
    s = state.reindex(idx)
    y = labels.loc[idx, "event"].astype(bool)
    base_rate = float(y.mean()) if len(y) else None
    state_draws, diff_draws = _bootstrap(s, y, block=block, seed=seed)
    cells = {}
    for name in _ORDER:
        mask = s.eq(name)
        n = int(mask.sum())
        events = int(y[mask].sum())
        rate = (events / n) if n else None
        config_p = configured.get(name)
        cells[name] = {
            "n": n,
            "events": events,
            "event_rate": rate,
            "event_rate_ci90": _q90(state_draws[name]),
            "lift_vs_base": (
                rate / base_rate if rate is not None and base_rate else None
            ),
            "configured_state_probability": config_p,
            "observed_minus_configured": (
                rate - config_p
                if rate is not None and isinstance(config_p, (int, float))
                else None
            ),
            "thin": bool(n < THIN_N),
        }
    adjacent = {}
    monotonic = True
    for a, b in zip(_ORDER, _ORDER[1:]):
        av = cells[a]["event_rate"]
        bv = cells[b]["event_rate"]
        diff = (bv - av) if av is not None and bv is not None else None
        adjacent[f"{a}->{b}"] = {
            "difference": diff,
            "difference_ci90": _q90(diff_draws[f"{a}->{b}"]),
        }
        if diff is None or diff < 0:
            monotonic = False
    return {
        "from": idx[0].isoformat() if len(idx) else None,
        "through": idx[-1].isoformat() if len(idx) else None,
        "n": int(len(idx)),
        "events": int(y.sum()),
        "base_rate": base_rate,
        "population_sha256": _fingerprint(labels.loc[idx]),
        "states": cells,
        "adjacent_differences": adjacent,
        "point_estimate_monotonic": bool(monotonic),
        "bootstrap": {
            "method": "circular_moving_block",
            "block_observations": int(block),
            "draws": BOOT_DRAWS,
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


def _window_labels(labels: pd.DataFrame, lo: str | None) -> pd.DataFrame:
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
    state = state_series(subs, calib).reindex(idx).where(known)
    spy = _spy(drop_missing=False)
    results = {}
    canonical = {}
    for horizon in HORIZONS:
        labels = native_forward_labels(spy, idx, horizon, .05)
        hkey = f"h{horizon}"
        configured = (calib.get("prob_cal") or _PROB_CAL).get(hkey, _PROB_CAL[hkey])
        results[hkey] = {}
        canonical[hkey] = {}
        for widx, (name, lo) in enumerate(WINDOWS):
            scoped = _window_labels(labels, lo)
            results[hkey][name] = summarize_window(
                state, scoped, configured,
                block=horizon,
                seed=BOOT_SEED + horizon * 10 + widx,
            )
            check = state_accuracy(calib, H=horizon, dd=.05, lo=lo)
            canonical[hkey][name] = {
                "n_days": check.get("n_days"),
                "confusion": (check.get("evaluation") or {}).get("confusion"),
                "outcomes_sha256": (check.get("evaluation") or {}).get("outcomes_sha256"),
            }
            ours = results[hkey][name]
            if ours["n"] != check.get("n_days"):
                raise RuntimeError(f"canonical population count mismatch {hkey}/{name}")
            if ours["population_sha256"] != canonical[hkey][name]["outcomes_sha256"]:
                raise RuntimeError(f"canonical outcome fingerprint mismatch {hkey}/{name}")
    inputs, missing = _tracked_inputs()
    calibration_sha = hashlib.sha256(
        json.dumps(calib, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()
    source_paths = [
        "engine/risk_radar.py",
        "engine/risk_radar_backtest.py",
        "scripts/research/risk_radar_state_ladder_calibration.py",
        "research/grey_deer/RISK_RADAR_STATE_LADDER_CALIBRATION_PREREG_2026-09-21.md",
    ]
    return {
        "schema": "risk_radar_state_ladder_calibration.v1",
        "protocol_commit": PROTOCOL_COMMIT,
        "source_base": SOURCE_BASE,
        "targets": {"depth": .05, "horizons": list(HORIZONS)},
        "state_order": list(_ORDER),
        "calibration_sha256": calibration_sha,
        "configured_probabilities": (calib.get("prob_cal") or _PROB_CAL),
        "source_hashes": {rel: _hash(ROOT / rel) for rel in source_paths},
        "input_hashes": inputs,
        "missing_optional_inputs": missing,
        "coverage": {
            "from": idx[0].isoformat(), "through": idx[-1].isoformat(),
            "rows": int(len(idx)), "signal_columns": list(sigs.columns),
            "subscore_columns": list(subs.columns),
        },
        "results": results,
        "canonical_crosscheck": canonical,
        "authority": {
            "status": "descriptive_only",
            "live_model_changed": False,
            "probability_changed": False,
            "gate_changed": False,
            "policy_changed": False,
        },
    }


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{100.0 * value:.1f}%"


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{100.0 * value:+.1f}pp"


def render_markdown(result: dict) -> str:
    lines = [
        "# Risk Radar State-Ladder Calibration Study — Results",
        "",
        f"Protocol commit: `{result['protocol_commit']}`.",
        "",
        "Descriptive reconstructed-history research only; no live model or probability changed.",
        "",
    ]
    for hkey in ("h5", "h10", "h21"):
        lines += [f"## {hkey.upper()} state cells", ""]
        lines.append(
            "| Window | State | n | Events | Observed | 90% block CI | "
            "Configured | Obs-config | Lift | Thin |"
        )
        lines.append("|---|---|---:|---:|---:|---|---:|---:|---:|---|")
        for wname, _ in WINDOWS:
            row = result["results"][hkey][wname]
            for state in _ORDER:
                cell = row["states"][state]
                ci = cell["event_rate_ci90"]
                ci_text = (
                    f"{_pct(ci[0])}..{_pct(ci[1])}" if ci is not None else "—"
                )
                lift = cell["lift_vs_base"]
                lines.append(
                    f"| {wname} | {state} | {cell['n']} | {cell['events']} "
                    f"| {_pct(cell['event_rate'])} | {ci_text} "
                    f"| {_pct(cell['configured_state_probability'])} "
                    f"| {_fmt_delta(cell['observed_minus_configured'])} "
                    f"| {lift:.2f}x" if lift is not None else
                    f"| {wname} | {state} | {cell['n']} | {cell['events']} "
                    f"| {_pct(cell['event_rate'])} | {ci_text} "
                    f"| {_pct(cell['configured_state_probability'])} "
                    f"| {_fmt_delta(cell['observed_minus_configured'])} | —"
                )
                lines[-1] += f" | {'YES' if cell['thin'] else ''} |"
        lines.append("")
        lines.append("| Window | Adjacent step | Rate difference | 90% block CI | Point monotonic |")
        lines.append("|---|---|---:|---|---|")
        for wname, _ in WINDOWS:
            row = result["results"][hkey][wname]
            for step, item in row["adjacent_differences"].items():
                ci = item["difference_ci90"]
                ci_text = (
                    f"{_fmt_delta(ci[0])}..{_fmt_delta(ci[1])}"
                    if ci is not None else "—"
                )
                lines.append(
                    f"| {wname} | {step} | {_fmt_delta(item['difference'])} "
                    f"| {ci_text} | {'YES' if row['point_estimate_monotonic'] else 'NO'} |"
                )
        lines.append("")

    lines += [
        "## Evidence ceiling", "",
        "Daily forward windows overlap, so the intervals use the preregistered moving-block bootstrap. "
        "This is a current-code historical reconstruction, not genuinely issued forecast history.",
        "",
        "Configured probabilities are shown as diagnostics only. Differences do not authorize "
        "retuning; any model change requires a separate preregistered candidate and promotion review.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    result = build_result()
    OUT.mkdir(parents=True, exist_ok=True)
    result_path = OUT / "result.json"
    result_path.write_text(json.dumps(result, indent=2, default=str) + "\n")
    report = ROOT / "research/grey_deer/RISK_RADAR_STATE_LADDER_CALIBRATION_RESULTS_2026-09-21.md"
    report.write_text(render_markdown(result) + "\n")
    compact = {}
    for hkey in ("h5", "h10", "h21"):
        compact[hkey] = {}
        for wname, _ in WINDOWS:
            row = result["results"][hkey][wname]
            compact[hkey][wname] = {
                "base_rate": row["base_rate"],
                "monotonic": row["point_estimate_monotonic"],
                "rates": {
                    state: row["states"][state]["event_rate"] for state in _ORDER
                },
                "configured": {
                    state: row["states"][state]["configured_state_probability"]
                    for state in _ORDER
                },
            }
    print(json.dumps(compact, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
