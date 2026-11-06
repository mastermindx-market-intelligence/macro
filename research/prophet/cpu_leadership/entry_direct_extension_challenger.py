"""Pre-registered direct-extension challenger for CPU leadership recovery.

Research-only. Tests whether Mastermind's existing close-based ATR extension geometry adds
anti-chase separation inside the RS<.85 otherwise-clean population. No production authority.
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

from engine.theme_extension import (  # noqa: E402
    ATR_WINDOW, BAND_EXTENDED, MA_WINDOW, _atr_ext,
)
from research.prophet.cpu_leadership.entry_rs_threshold_inference import (  # noqa: E402
    infer_difference, paired_monthly_difference,
)
from research.prophet.cpu_leadership.entry_rs_threshold_study import (  # noqa: E402
    HORIZONS, _fwd_abs, _fwd_dd, _fwd_rel, _median_pct,
    _otherwise_clean_series, episode_onsets, load_us_proxy,
)
from scripts.calibrate_baskets import DD_RISK, _rs_features  # noqa: E402

SCHEMA = "prophet.cpu_leadership.direct_extension_challenger.v1"
RS_CHALLENGER = 0.85
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def atr_extension_series(
    lvl: pd.Series,
    ma_window: int = MA_WINDOW,
    atr_window: int = ATR_WINDOW,
) -> pd.Series:
    """Causal series form of engine.theme_extension._atr_ext."""
    s = lvl.astype(float)
    atr = s.diff().abs().ewm(
        alpha=1.0 / atr_window,
        adjust=False,
        min_periods=atr_window,
    ).mean()
    ma = s.rolling(ma_window, min_periods=ma_window // 2).mean()
    return (s - ma) / atr.replace(0, np.nan)


def assert_live_extension_parity(lvl: pd.Series) -> None:
    live = _atr_ext(lvl)
    series = atr_extension_series(lvl).dropna()
    research = float(series.iloc[-1]) if len(series) else None
    if live is None and research is None:
        return
    if live is None or research is None or not np.isclose(live, research, rtol=0, atol=1e-12):
        raise AssertionError(f"extension parity drift: live={live!r}, research={research!r}")
def _cohort_states(
    otherwise: pd.Series,
    rs: pd.Series,
    extension: pd.Series,
) -> dict[str, pd.Series]:
    eligible_rs = otherwise & rs.notna() & (rs < RS_CHALLENGER)
    middle = otherwise & rs.notna() & (rs >= 0.75) & (rs < RS_CHALLENGER)
    return {
        "rs085_atr_normal": eligible_rs & extension.notna() & (extension < BAND_EXTENDED),
        "rs085_atr_extended": eligible_rs & extension.notna() & (extension >= BAND_EXTENDED),
        "middle_075_085_atr_normal": middle & extension.notna() & (extension < BAND_EXTENDED),
        "middle_075_085_atr_extended": middle & extension.notna() & (extension >= BAND_EXTENDED),
    }


def build_episode_rows(panel: pd.DataFrame, bench: pd.Series) -> list[dict[str, Any]]:
    from scripts.calibrate_baskets import _panel_breadth

    breadth = _panel_breadth(panel)
    bench_v = bench.to_numpy(float)
    rows: list[dict[str, Any]] = []
    for ticker in panel.columns:
        lvl = panel[ticker].astype(float)
        features = _rs_features(lvl, bench)
        otherwise = _otherwise_clean_series(lvl, features, breadth)
        rs = features["rs_pctile"].reindex(lvl.index)
        extension = atr_extension_series(lvl).reindex(lvl.index)
        states = _cohort_states(otherwise, rs, extension)
        px = lvl.to_numpy(float)
        rs_v = rs.to_numpy(float)
        ext_v = extension.to_numpy(float)
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
                    "atr_extension": float(ext_v[i]),
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
                rows.append(row)
    return rows


def summarize_cohort(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {"n_episodes": 0}
    decades = (df["year"] // 10) * 10
    out: dict[str, Any] = {
        "n_episodes": int(len(df)),
        "n_sectors": int(df["ticker"].nunique()),
        "span": [str(df["date"].min()), str(df["date"].max())],
        "rs_pctile_median": round(float(df["rs_pctile"].median()), 4),
        "atr_extension_median": round(float(df["atr_extension"].median()), 4),
        "decade_counts": {
            str(int(decade)): int(count)
            for decade, count in decades.value_counts().sort_index().items()
        },
    }
    for horizon in HORIZONS:
        out[f"abs_{horizon}d_median_pct"] = _median_pct(df[f"abs_{horizon}d"])
        out[f"rel_{horizon}d_median_pct"] = _median_pct(df[f"rel_{horizon}d"])
    out["dd_21d_median_pct"] = _median_pct(df["dd_21d"])
    out["p_dd_21d_lt_8pct"] = round(float(df["dd_risk_21d"].mean()), 4)
    out["p_continuation_failure_21d"] = round(
        float(df["continuation_failure_21d"].mean()), 4
    )
    return out


def _episode_digest(rows: list[dict[str, Any]]) -> str:
    raw = json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()
def run_study(data_root: Path) -> dict[str, Any]:
    panel, bench, manifest = load_us_proxy(data_root)
    rows = build_episode_rows(panel, bench)
    frame = pd.DataFrame(rows)
    cohort_names = (
        "rs085_atr_normal",
        "rs085_atr_extended",
        "middle_075_085_atr_normal",
        "middle_075_085_atr_extended",
    )
    cohorts = {
        name: summarize_cohort(frame.loc[frame["cohort"] == name])
        for name in cohort_names
    }
    inference = {}
    for metric in ("rel_21d", "dd_21d", "dd_risk_21d", "continuation_failure_21d"):
        diff = paired_monthly_difference(
            rows, metric, "rs085_atr_extended", "rs085_atr_normal",
        )
        inference[metric] = infer_difference(diff)

    dep_paths = [
        ROOT / "engine/theme_extension.py",
        ROOT / "engine/basket_score.py",
        ROOT / "scripts/calibrate_baskets.py",
        ROOT / "research/prophet/cpu_leadership/entry_rs_threshold_study.py",
        ROOT / "research/prophet/cpu_leadership/entry_rs_threshold_inference.py",
    ]
    return {
        "schema": SCHEMA,
        "authority": {
            "can_rank": False,
            "can_gate": False,
            "can_size": False,
            "can_trade": False,
        },
        "construction": {
            "rs_challenger": RS_CHALLENGER,
            "atr_extended_boundary": BAND_EXTENDED,
            "ma_window": MA_WINDOW,
            "atr_window": ATR_WINDOW,
            "episode_unit": "contiguous_otherwise_clean_rs085_atr_band_onset",
            "dd_risk": DD_RISK,
            "horizons_sessions": list(HORIZONS),
        },
        "data": {
            "root": str(data_root),
            "panel_shape": list(panel.shape),
            "panel_span": [str(panel.index.min().date()), str(panel.index.max().date())],
            "manifest": manifest,
        },
        "source_dependencies": {
            str(path.relative_to(ROOT)): _sha256(path) for path in dep_paths
        },
        "cohorts": cohorts,
        "primary_inference": {
            "left": "rs085_atr_extended",
            "right": "rs085_atr_normal",
            "metrics": inference,
        },
        "episodes": {
            "n": int(len(rows)),
            "sha256": _episode_digest(rows),
        },
        "limitations": [
            "Long-history proxy uses sector-ETF level extension; live Theme Extension headlines median-member extension.",
            "The study evaluates anti-chase separation, not return-alpha origination.",
            "September-2026 AI-hardware examples are not used to choose thresholds.",
            "No production policy changes from this research artifact.",
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
