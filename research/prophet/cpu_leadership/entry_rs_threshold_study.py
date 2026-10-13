"""Pre-registered RS anti-chase threshold study for Prophet CPU leadership recovery.

Research-only. Reuses the existing basket calibration substrate and incumbent clean-entry
semantics. It never mutates production thresholds, rankings, entry permissions or stores.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.basket_score import clean_entry as live_clean_entry  # noqa: E402
from scripts.calibrate_baskets import (  # noqa: E402
    DD_RISK, REGION_SECTORS, _panel_breadth, _rs_features,
)

THRESHOLDS = (0.75, 0.85)
HORIZONS = (5, 10, 21)
SCHEMA = "prophet.cpu_leadership.rs_threshold_study.v1"
def _safe_name(name: str) -> str:
    return name.replace("^", "_").replace("=", "_").replace("/", "_").replace(" ", "_")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_close(data_root: Path, group: str, ticker: str) -> tuple[pd.Series | None, dict[str, Any]]:
    path = data_root / group / f"{_safe_name(ticker)}.parquet"
    if not path.exists():
        return None, {"ticker": ticker, "path": str(path), "status": "missing"}
    df = pd.read_parquet(path)
    if df.empty or "close" not in df.columns:
        return None, {"ticker": ticker, "path": str(path), "status": "invalid"}
    df.index = pd.to_datetime(df.index)
    s = df["close"].astype(float).sort_index().dropna()
    return s, {
        "ticker": ticker,
        "path": str(path),
        "status": "ok",
        "sha256": _sha256(path),
        "rows": int(len(s)),
        "start": str(s.index.min().date()),
        "end": str(s.index.max().date()),
    }
def load_us_proxy(data_root: Path) -> tuple[pd.DataFrame, pd.Series, list[dict[str, Any]]]:
    spec = REGION_SECTORS["us"]
    group = spec["group"]
    manifest: list[dict[str, Any]] = []
    cols: dict[str, pd.Series] = {}
    for ticker in spec["core"] + spec["late"]:
        s, receipt = _read_close(data_root, group, ticker)
        manifest.append(receipt)
        if s is not None and len(s) > 200:
            cols[ticker] = s
    panel = pd.DataFrame(cols)
    keep = [ticker for ticker in spec["core"] if ticker in panel.columns]
    panel = panel.dropna(subset=keep) if keep else panel.dropna()

    bench, receipt = _read_close(data_root, group, spec["bench"])
    manifest.append(receipt)
    if panel.empty or bench is None or panel.shape[1] < 4:
        raise ValueError("insufficient committed US proxy data")
    bench = bench.reindex(panel.index).ffill()
    valid = bench.notna()
    return panel.loc[valid], bench.loc[valid], manifest


def _rsi_series(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)
def clean_entry_at_threshold(
    lvl: pd.Series,
    fp: dict[str, Any] | None,
    breadth_d: dict[str, Any] | None,
    rsi_val: float | None,
    *,
    threshold: float,
) -> dict[str, Any]:
    """Incumbent clean_entry with only the RS cutoff parameterized for research."""
    s = lvl.dropna()
    reasons: list[str] = []
    q = 0.0
    accel = (fp or {}).get("accel_z")
    rs_p = (fp or {}).get("rs_pctile")
    if accel is not None and accel > 0.3:
        q += 0.30
        reasons.append("accelerating")
    not_ext = rs_p is None or rs_p < threshold
    if not_ext:
        q += 0.20
        reasons.append("not extended")
    if rsi_val is not None and rsi_val < 65:
        q += 0.15
        reasons.append("RSI room")
    pct50 = (breadth_d or {}).get("pct50")
    if pct50 is not None and pct50 >= 0.5:
        q += 0.15
        reasons.append("breadth supportive")
    if len(s) >= 60:
        sma200 = s.rolling(200, min_periods=60).mean().iloc[-1]
        if pd.notna(sma200) and s.iloc[-1] > sma200:
            q += 0.10
            reasons.append("above 200d trend")
    if len(s) >= 20:
        w = min(20, len(s))
        recent_dd = s.iloc[-1] / s.iloc[-w:].max() - 1.0
        if -0.08 < recent_dd < -0.004:
            q += 0.10
            reasons.append("shallow pullback")
    nh = (breadth_d or {}).get("nh", 0)
    nl = (breadth_d or {}).get("nl", 0)
    breaking = (
        (pct50 is not None and pct50 < 0.4)
        or (nh - nl) < 0
        or (accel is not None and accel < -0.5)
    )
    return {
        "flag": bool(q >= 0.6 and not_ext and not breaking),
        "quality": round(min(q, 1.0), 3),
        "reasons": reasons[:4],
        "directional": False,
    }


def assert_incumbent_parity(
    lvl: pd.Series,
    fp: dict[str, Any] | None,
    breadth_d: dict[str, Any] | None,
    rsi_val: float | None,
) -> None:
    incumbent = live_clean_entry(lvl, fp, breadth_d, rsi_val)
    research = clean_entry_at_threshold(
        lvl, fp, breadth_d, rsi_val, threshold=0.75,
    )
    if incumbent != research:
        raise AssertionError(f"0.75 research parity drift: {incumbent!r} != {research!r}")


def _fwd_abs(values: np.ndarray, i: int, horizon: int) -> float:
    if i + horizon >= len(values) or not np.isfinite(values[i]):
        return math.nan
    return float(values[i + horizon] / values[i] - 1.0)


def _fwd_rel(values: np.ndarray, bench: np.ndarray, i: int, horizon: int) -> float:
    a = _fwd_abs(values, i, horizon)
    b = _fwd_abs(bench, i, horizon)
    return float(a - b) if np.isfinite(a) and np.isfinite(b) else math.nan
def _fwd_dd(values: np.ndarray, i: int, horizon: int) -> float:
    if i + horizon >= len(values) or not np.isfinite(values[i]):
        return math.nan
    future = values[i + 1:i + 1 + horizon]
    future = future[np.isfinite(future)]
    return float(future.min() / values[i] - 1.0) if len(future) else math.nan


def episode_onsets(state: pd.Series) -> pd.Series:
    clean = state.fillna(False).astype(bool)
    return clean & ~clean.shift(1, fill_value=False)


def first_threshold_release(
    otherwise_clean: np.ndarray,
    rs_pctile: np.ndarray,
    start: int,
    threshold: float,
    *,
    max_wait: int = 21,
) -> int | None:
    stop = min(len(otherwise_clean), start + max_wait + 1)
    for j in range(start + 1, stop):
        if bool(otherwise_clean[j]) and np.isfinite(rs_pctile[j]) and rs_pctile[j] < threshold:
            return j
    return None
def _otherwise_clean_series(
    lvl: pd.Series,
    features: dict[str, pd.Series],
    breadth: pd.DataFrame,
) -> pd.Series:
    idx = lvl.index
    accel = features["accel_z"].reindex(idx)
    rs_p = features["rs_pctile"].reindex(idx)
    rsi = _rsi_series(lvl).reindex(idx)
    pct50 = breadth["pct50"].reindex(idx)
    nh = breadth["nh"].reindex(idx)
    nl = breadth["nl"].reindex(idx)

    quality = pd.Series(0.20, index=idx, dtype=float)
    quality += (accel > 0.3).astype(float) * 0.30
    quality += (rsi < 65).fillna(False).astype(float) * 0.15
    quality += (pct50 >= 0.5).fillna(False).astype(float) * 0.15

    sma200 = lvl.rolling(200, min_periods=60).mean()
    quality += (lvl > sma200).fillna(False).astype(float) * 0.10
    recent_high = lvl.rolling(20, min_periods=20).max()
    recent_dd = lvl / recent_high - 1.0
    shallow = ((recent_dd > -0.08) & (recent_dd < -0.004)).fillna(False)
    quality += shallow.astype(float) * 0.10
    breaking = (
        ((pct50 < 0.4) & pct50.notna())
        | ((nh - nl) < 0)
        | ((accel < -0.5) & accel.notna())
    )
    return (
        (quality >= 0.60)
        & ~breaking.fillna(True)
        & lvl.notna()
        & rs_p.notna()
        & accel.notna()
    )


def _cohort_states(otherwise: pd.Series, rs: pd.Series) -> dict[str, pd.Series]:
    return {
        "allowed_lt075": otherwise & (rs < 0.75),
        "incremental_075_085": otherwise & (rs >= 0.75) & (rs < 0.85),
        "blocked_both_ge085": otherwise & (rs >= 0.85),
    }


def build_episode_rows(panel: pd.DataFrame, bench: pd.Series) -> list[dict[str, Any]]:
    breadth = _panel_breadth(panel)
    bench_v = bench.to_numpy(float)
    rows: list[dict[str, Any]] = []
    release_threshold = {
        "incremental_075_085": 0.75,
        "blocked_both_ge085": 0.85,
    }
    for ticker in panel.columns:
        lvl = panel[ticker].astype(float)
        features = _rs_features(lvl, bench)
        otherwise = _otherwise_clean_series(lvl, features, breadth)
        rs = features["rs_pctile"].reindex(lvl.index)
        states = _cohort_states(otherwise, rs)
        px = lvl.to_numpy(float)
        rs_v = rs.to_numpy(float)
        otherwise_v = otherwise.to_numpy(bool)

        for cohort, state in states.items():
            starts = np.flatnonzero(episode_onsets(state).to_numpy(bool))
            for i in starts:
                if i + max(HORIZONS) >= len(lvl):
                    continue
                row: dict[str, Any] = {
                    "cohort": cohort,
                    "ticker": ticker,
                    "date": str(lvl.index[i].date()),
                    "year": int(lvl.index[i].year),
                    "rs_pctile": float(rs_v[i]),
                }
                for horizon in HORIZONS:
                    row[f"abs_{horizon}d"] = _fwd_abs(px, i, horizon)
                    row[f"rel_{horizon}d"] = _fwd_rel(px, bench_v, i, horizon)
                row["dd_21d"] = _fwd_dd(px, i, 21)
                row["dd_risk_21d"] = bool(
                    np.isfinite(row["dd_21d"]) and row["dd_21d"] < DD_RISK
                )
                row["continuation_failure_21d"] = bool(
                    np.isfinite(row["rel_21d"]) and row["rel_21d"] <= 0
                )

                threshold = release_threshold.get(cohort)
                release_i = (
                    first_threshold_release(otherwise_v, rs_v, i, threshold)
                    if threshold is not None else None
                )
                row["release_threshold"] = threshold
                row["release_wait_sessions"] = (
                    None if release_i is None else int(release_i - i)
                )
                if release_i is None:
                    row["onset_to_release_abs"] = None
                    row["onset_to_release_rel"] = None
                else:
                    row["onset_to_release_abs"] = float(px[release_i] / px[i] - 1.0)
                    bench_move = float(bench_v[release_i] / bench_v[i] - 1.0)
                    row["onset_to_release_rel"] = (
                        row["onset_to_release_abs"] - bench_move
                    )
                rows.append(row)
    return rows


def _finite(values: pd.Series) -> np.ndarray:
    arr = pd.to_numeric(values, errors="coerce").to_numpy(float)
    return arr[np.isfinite(arr)]


def _median_pct(values: pd.Series) -> float | None:
    arr = _finite(values)
    return round(100 * float(np.median(arr)), 3) if len(arr) else None
def summarize_cohort(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"n_episodes": 0}
    decades = (df["year"] // 10) * 10
    result: dict[str, Any] = {
        "n_episodes": int(len(df)),
        "n_sectors": int(df["ticker"].nunique()),
        "span": [str(df["date"].min()), str(df["date"].max())],
        "rs_pctile_median": round(float(df["rs_pctile"].median()), 4),
        "decade_counts": {
            str(int(decade)): int(count)
            for decade, count in decades.value_counts().sort_index().items()
        },
    }
    for horizon in HORIZONS:
        result[f"abs_{horizon}d_median_pct"] = _median_pct(df[f"abs_{horizon}d"])
        result[f"rel_{horizon}d_median_pct"] = _median_pct(df[f"rel_{horizon}d"])
    result["dd_21d_median_pct"] = _median_pct(df["dd_21d"])
    result["p_dd_21d_lt_8pct"] = round(float(df["dd_risk_21d"].mean()), 4)
    result["p_continuation_failure_21d"] = round(
        float(df["continuation_failure_21d"].mean()), 4
    )
    if df["release_threshold"].notna().any():
        released = df["release_wait_sessions"].notna()
        result["release_within_21_rate"] = round(float(released.mean()), 4)
        waits = pd.to_numeric(df.loc[released, "release_wait_sessions"], errors="coerce")
        result["release_wait_sessions_median"] = (
            round(float(waits.median()), 2) if not waits.empty else None
        )
        result["onset_to_release_abs_median_pct"] = _median_pct(
            df.loc[released, "onset_to_release_abs"]
        )
        result["onset_to_release_rel_median_pct"] = _median_pct(
            df.loc[released, "onset_to_release_rel"]
        )
    return result


def _contrast(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    def delta(key: str, scale: float = 1.0) -> float | None:
        av, bv = a.get(key), b.get(key)
        if av is None or bv is None:
            return None
        return round((float(av) - float(bv)) * scale, 3)

    return {
        "rel_21d_median_delta_pp": delta("rel_21d_median_pct"),
        "dd_21d_median_delta_pp": delta("dd_21d_median_pct"),
        "dd_risk_delta_pp": delta("p_dd_21d_lt_8pct", 100.0),
        "continuation_failure_delta_pp": delta(
            "p_continuation_failure_21d", 100.0,
        ),
    }
def run_study(data_root: Path) -> dict[str, Any]:
    panel, bench, manifest = load_us_proxy(data_root)
    rows = build_episode_rows(panel, bench)
    frame = pd.DataFrame(rows)
    cohorts = {
        name: summarize_cohort(frame.loc[frame["cohort"] == name])
        for name in ("allowed_lt075", "incremental_075_085", "blocked_both_ge085")
    }
    return {
        "schema": SCHEMA,
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_trade": False,
        },
        "construction": {
            "thresholds": list(THRESHOLDS),
            "episode_unit": "contiguous_otherwise_clean_rs_band_onset",
            "dd_risk": DD_RISK,
            "horizons_sessions": list(HORIZONS),
            "proxy": "US SPDR sector panel plus SPY",
        },
        "data": {
            "root": str(data_root),
            "panel_shape": list(panel.shape),
            "panel_span": [str(panel.index.min().date()), str(panel.index.max().date())],
            "manifest": manifest,
        },
        "cohorts": cohorts,
        "contrasts": {
            "incremental_075_085_minus_allowed_lt075": _contrast(
                cohorts["incremental_075_085"], cohorts["allowed_lt075"],
            ),
            "blocked_both_ge085_minus_incremental_075_085": _contrast(
                cohorts["blocked_both_ge085"], cohorts["incremental_075_085"],
            ),
        },
        "episodes": rows,
        "limitations": [
            "Proxy sectors are not the live theme-member universe.",
            "The study tests RS cutoffs as anti-chase controls, not a return-alpha signal.",
            "No macro/crowding recommendation threshold is retuned or replayed.",
            "September-2026 CPU winners are not part of threshold selection.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    result = run_study(args.data_root.resolve())
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
