"""Frozen descriptive replay for Fear/Greed v1; never imported by production.

Uses the actual production transforms and rules, no fitting. Revised observation
history is NOT publication-time history. Results have no trade/forecast authority.
Usage: python -m scripts.research_fear_greed_intelligence --as-of 2026-10-16
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Direct script execution must resolve this checkout, not the caller working directory.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from engine.fear_greed_intelligence import (_change, _features, classify_pivot_context,
                                          read_intelligence_inputs)
from engine.vol_velocity import vix_dynamics_frame
from lib import config

HORIZONS = (5, 10, 21)
COOLDOWN = 21
SEED = 20261017
REPLICATES = 2000
RULES = {
    "high_vix_level": "VIX level rank >=90 alone",
    "vix_relief": "Two downward VIX closes alone",
    "relief_broadening": "Relief plus stocks, participation and credit",
    "stress_broadening": "Stress plus stocks, participation and credit",
    "shock_watch": "Positive, extreme velocity and acceleration",
}
ERAS = {
    "all": ("2007-01-01", "2026-10-16"),
    "2007_2019": ("2007-01-01", "2019-12-31"),
    "2020_2026": ("2020-01-01", "2026-10-16"),
    "gfc_2007_2009": ("2007-01-01", "2009-12-31"),
    "covid_2020": ("2020-01-01", "2020-12-31"),
    "inflation_2022": ("2022-01-01", "2022-12-31"),
}


def episode_starts(mask: pd.Series) -> list[int]:
    """First observable start of a true run, at least 21 sessions apart."""
    flags = mask.fillna(False).astype(bool)
    starts = np.flatnonzero((flags & ~flags.shift(1, fill_value=False)).to_numpy())
    result, previous = [], -COOLDOWN
    for i in starts:
        if i - previous >= COOLDOWN:
            result.append(int(i))
            previous = i
    return result


def outcomes(spy: np.ndarray, starts: list[int], horizon: int, entry_lag=0) -> tuple[list, int]:
    rows, censored = [], 0
    for i in starts:
        entry, end = i + entry_lag, i + entry_lag + horizon
        window = spy[entry:end + 1]
        if end >= len(spy) or len(window) != horizon + 1 or not np.all(np.isfinite(window) & (window > 0)):
            censored += 1
            continue
        returns = 100 * (window[1:] / window[0] - 1)
        rows.append([float(returns[-1]), float(returns[-1] > 0),
                     float(min(0, returns.min())), float(returns.min() <= -5)])
    return rows, censored


def summarize(rows: list, censored: int, *, bootstrap=True) -> dict:
    keys = ("mean_return_pct", "positive_return_rate", "mean_worst_close_drawdown_pct", "drawdown_5pct_rate")
    out = {"n": len(rows), "censored": censored, "thin": len(rows) < 12}
    if not rows:
        return {**out, **{k: None for k in keys}, "ci95": None}
    a = np.asarray(rows)
    out.update({k: round(float(v), 5) for k, v in zip(keys, a.mean(axis=0))})
    out["ci95"] = None
    if bootstrap and len(rows) >= 12:
        # Circular moving blocks of three chronological events preserve short-run
        # episode dependence. Thin or nonstationary era cells are still disclosed.
        rng = np.random.default_rng(SEED)
        block_starts = rng.integers(0, len(a), size=(REPLICATES, int(np.ceil(len(a) / 3))))
        indices = ((block_starts[..., None] + np.arange(3)) % len(a)).reshape(REPLICATES, -1)[:, :len(a)]
        boot = a[indices].mean(axis=1)
        lo, hi = np.quantile(boot, [.025, .975], axis=0)
        out["ci95"] = {k: [round(float(x), 5), round(float(y), 5)] for k, x, y in zip(keys, lo, hi)}
    return out


def replay(as_of: str) -> dict:
    inputs = read_intelligence_inputs()
    if "vix" not in inputs or "spy" not in inputs:
        raise RuntimeError("VIX and SPY caches are required; run existing collection first")
    raw, clean = _features(inputs, as_of)
    vd = vix_dynamics_frame(clean["vix"], as_of)
    spy = clean["spy"].reindex(vd.index)
    changes = pd.DataFrame({"price": _change(spy), "breadth": _change(raw["breadth"]),
                            "credit": _change(raw["credit"])}).reindex(vd.index)
    states = []
    for (_, row), (_, ch) in zip(vd.iterrows(), changes.iterrows()):
        dynamic = {"mature": bool(pd.notna(row.acceleration_percentile)),
                   "phase": row.phase, "up_sessions": int(row.up_sessions), "down_sessions": int(row.down_sessions),
                   "velocity_percentile": round(row.velocity_percentile, 1), "acceleration_percentile": round(row.acceleration_percentile, 1)}
        checks = {k: (round(float(v), 3) if pd.notna(v) else None) for k, v in ch.items()}
        states.append(classify_pivot_context(dynamic, {**checks, "curve": None})["state"])
    state = pd.Series(states, index=vd.index)
    eligible = (changes.notna().all(axis=1) & vd.acceleration_percentile.notna()
                & spy.notna() & (vd.index >= "2007-01-01"))
    flags = {
        "high_vix_level": vd.level_percentile.ge(90),
        "vix_relief": vd.down_sessions.ge(2),
        "relief_broadening": state.eq("relief_broadening"),
        "stress_broadening": state.eq("stress_broadening"),
        "shock_watch": state.eq("shock_watch"),
    }
    starts = {k: episode_starts(v & eligible) for k, v in flags.items()}
    all_dates = vd.index[eligible]
    manifest = {}
    for relative in ("yahoo/_VIX.parquet", "yahoo/SPY.parquet", "yahoo/TLT.parquet",
                     "yahoo/_VIX3M.parquet", "yahoo/_VIX9D.parquet", "cboe/vvix.parquet",
                     "cboe/putcall.parquet", "fred/BAMLH0A0HYM2.parquet", "breadth/breadth.parquet"):
        p = config.data_dir() / relative
        if p.exists():
            manifest[relative] = hashlib.sha256(p.read_bytes()).hexdigest()
    result = {
        "schema": "mastermind.research_result.v1", "study": "fear_greed_intelligence_v1",
        "authority": "descriptive_only", "forecast_validated": False,
        "history_kind": "revised_observations_not_point_in_time", "as_of": as_of,
        "protocol": "research/FEAR_GREED_INTELLIGENCE_V1.md", "input_sha256": manifest,
        "code_sha256": {name: hashlib.sha256((config.ROOT / name).read_bytes()).hexdigest()
                        for name in ("engine/vol_velocity.py", "engine/fear_greed_intelligence.py",
                                     "scripts/research_fear_greed_intelligence.py")},
        "common_eligible_sessions": len(all_dates),
        "common_span": [str(all_dates.min().date()), str(all_dates.max().date())] if len(all_dates) else [],
        "event_cooldown_sessions": COOLDOWN, "bootstrap_seed": SEED,
        "bootstrap_replicates": REPLICATES, "bootstrap_event_block_length": 3,
        "rules": RULES, "eras": {},
        "limitations": ["No publication-time vintages or executable entry claim", "Changing breadth universe and revisions",
                        "No fitting, threshold search or CNN index return comparison", "No trading costs or portfolio sizing",
                        "Different rules select different dates; means do not prove superiority",
                        "Eligible-date baseline has overlapping returns and no confidence interval",
                        "Historical reconstruction is not prospective validation"],
    }
    for era, (first, last) in ERAS.items():
        within = (vd.index >= first) & (vd.index <= min(last, as_of))
        era_starts = {key: [i for i in values if within[i]] for key, values in starts.items()}
        summary = {"eligible_sessions": int((eligible & within).sum()), "rules": {}, "baseline": {}}
        for key, events in era_starts.items():
            summary["rules"][key] = {"event_dates": [vd.index[i].strftime("%Y-%m-%d") for i in events], "horizons": {}}
            for h in HORIZONS:
                rows, censored = outcomes(spy.to_numpy(), events, h)
                lagged, lagged_censored = outcomes(spy.to_numpy(), events, h, 1)
                summary["rules"][key]["horizons"][str(h)] = {
                    "signal_close": summarize(rows, censored),
                    "next_close_sensitivity": summarize(lagged, lagged_censored),
                }
        for h in HORIZONS:
            rows, censored = outcomes(spy.to_numpy(), np.flatnonzero(eligible & within).tolist(), h)
            summary["baseline"][str(h)] = summarize(rows, censored, bootstrap=False)
        result["eras"][era] = summary
    return result


def markdown(result: dict) -> str:
    lines = ["# Fear/Greed v1: frozen descriptive replay", "",
             "**Retrospective associations, not an executable backtest or accepted predictive signal.**", "",
             f"Observation cutoff: {result['as_of']}. Common eligible span: {' to '.join(result['common_span'])}; "
             f"{result['common_eligible_sessions']} sessions. Rules, horizons, cooldown and bootstrap were frozen before this run.", "",
             "Every rule uses the same eligible-date universe. Starts are at least 21 sessions apart within each rule. "
             "Confidence intervals use 2,000 moving-block resamples of three chronological events. No interval is published with fewer than 12 episodes.", ""]
    for era in ("all", "2007_2019", "2020_2026", "gfc_2007_2009", "covid_2020", "inflation_2022"):
        values = result["eras"][era]
        lines += [f"## {era.replace('_', ' ')}", "",
                  "| Rule / horizon | Episodes | Mean return | 95% interval | Positive | Mean worst close loss | 5% drawdown | Next-close mean |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for key, rule in values["rules"].items():
            for h in HORIZONS:
                v = rule["horizons"][str(h)]["signal_close"]
                lag = rule["horizons"][str(h)]["next_close_sensitivity"]
                if not v["n"]:
                    lines.append(f"| {key} / {h}d | 0 | — | — | — | — | — | — |")
                    continue
                ci = v["ci95"]["mean_return_pct"] if v["ci95"] else None
                ci_text = f"[{ci[0]:+.2f}, {ci[1]:+.2f}]%" if ci else "thin"
                next_text = f"{lag['mean_return_pct']:+.2f}%" if lag["n"] else "—"
                lines.append(f"| {key} / {h}d | {v['n']} | {v['mean_return_pct']:+.2f}% | {ci_text} | "
                             f"{100*v['positive_return_rate']:.1f}% | {v['mean_worst_close_drawdown_pct']:.2f}% | "
                             f"{100*v['drawdown_5pct_rate']:.1f}% | {next_text} |")
        b = values["baseline"]["21"]
        if b["n"]:
            lines += ["", f"Eligible-date 21-session baseline: mean {b['mean_return_pct']:+.2f}%, "
                      f"positive {100*b['positive_return_rate']:.1f}%, 5% drawdown {100*b['drawdown_5pct_rate']:.1f}% "
                      f"({b['n']} overlapping date outcomes; no confidence interval)."]
        lines.append("")
    lines += ["## Interpretation boundary", "",
              "A higher average following one rule does not establish an incremental edge: selection dates differ, "
              "returns have equity drift, early/late eras may disagree, and stored breadth/credit were not necessarily "
              "published by the indicated signal close. Next-close sensitivity is not a substitute for availability vintages. "
              "The production feature therefore remains an observable risk-direction and confirmation panel, with no pivot probability or trade authority.", "",
              "Exact inputs, code hashes, episode dates, censored counts and intervals for all metrics are retained in `replay.json`. "
              "Future testing must use the existing keep-first observation ledger and retain this null/uncertainty boundary.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of", default="2026-10-16")
    parser.add_argument("--output", type=Path, default=config.ROOT / "reports/fear_greed_intelligence")
    args = parser.parse_args()
    result = replay(args.as_of)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "replay.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (args.output / "REPLAY.md").write_text(markdown(result))
    print(json.dumps({"common_span": result["common_span"], "sessions": result["common_eligible_sessions"],
                      "events": {k: len(v["event_dates"]) for k, v in result["eras"]["all"]["rules"].items()}}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
